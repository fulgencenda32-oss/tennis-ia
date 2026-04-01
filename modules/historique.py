# ============================================================
# MODULE HISTORIQUE — Firebase + Cloisonnement + Suppression douce + Archive 30j
# ============================================================
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

FICHIER_HISTORIQUE = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'historique.json'
)

# ============================================================
# VERIFICATION RESULTATS REELS VIA API
# ============================================================
def verifier_resultats_via_api(historique):
    """
    Pour chaque prédiction sans résultat réel,
    cherche le vrai résultat via l'API AllSports.
    Retourne (nombre trouvés, historique mis à jour).
    """
    from modules.api_rotation import appel_api

    trouves = 0
    a_verifier = [
        (i, h) for i, h in enumerate(historique)
        if not h.get('resultat_reel')
    ]

    if not a_verifier:
        return 0, historique

    barre = st.progress(0, text="Recherche des résultats en cours...")

    for idx, (i, h) in enumerate(a_verifier):
        joueur_a = h.get('joueur_a', '')
        joueur_b = h.get('joueur_b', '')
        date     = str(h.get('date', ''))[:10]  # format YYYY-MM-DD

        if not joueur_a or not joueur_b or not date:
            continue

        # Appel API pour ce jour
        resultat = appel_api(
            {"met": "Fixtures", "from": date, "to": date},
            utiliser_cache=True
        )

        if resultat["source"] == "erreur" or not resultat.get("data"):
            continue

        data = resultat["data"]
        if data.get("success") != 1:
            continue

        # Chercher le match dans les résultats
        for match in data.get("result", []):
            statut = str(match.get("event_status", "")).lower()
            if statut not in ["finished", "retired", "walk over"]:
                continue

            p1    = str(match.get("event_first_player", "")).lower()
            p2    = str(match.get("event_second_player", "")).lower()
            nom_a = joueur_a.lower().split()[-1]
            nom_b = joueur_b.lower().split()[-1]

            if nom_a in p1 and nom_b in p2:
                score          = str(match.get("event_final_result", ""))
                vainqueur_reel = str(match.get("event_first_player", ""))
                historique[i]['resultat_reel'] = vainqueur_reel
                historique[i]['score_reel']    = score
                trouves += 1
                break
            elif nom_b in p1 and nom_a in p2:
                score          = str(match.get("event_final_result", ""))
                vainqueur_reel = str(match.get("event_first_player", ""))
                historique[i]['resultat_reel'] = vainqueur_reel
                historique[i]['score_reel']    = score
                trouves += 1
                break

        barre.progress(
            (idx + 1) / len(a_verifier),
            text=f"Vérification {idx+1}/{len(a_verifier)}..."
        )

    barre.empty()
    return trouves, historique

# ============================================================
# CONNEXION FIREBASE
# ============================================================
def get_firebase_db():
    """Connexion Firebase avec timeout de 5 secondes maximum."""
    import threading

    result = [None]

    def _connecter():
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if not firebase_admin._apps:
                chemin_cle = os.path.join(
                    os.path.dirname(__file__), '..', 'data', 'firebase_key.json'
                )
                if os.path.exists(chemin_cle):
                    cred = credentials.Certificate(chemin_cle)
                    firebase_admin.initialize_app(cred)
                elif os.getenv('FIREBASE_KEY'):
                    cle_json = json.loads(os.getenv('FIREBASE_KEY'))
                    cred = credentials.Certificate(cle_json)
                    firebase_admin.initialize_app(cred)
                else:
                    return

            result[0] = firestore.client()
        except Exception:
            result[0] = None

    t = threading.Thread(target=_connecter, daemon=True)
    t.start()
    t.join(timeout=5)  # timeout 5 secondes max
    return result[0]

# ============================================================
# CHARGEMENT HISTORIQUE (Firebase + local) — avec filtrage par user_id
# ============================================================
def charger_historique(user_id=None, inclure_supprimes=False):
    """
    Charge l'historique des prédictions.
    - Si user_id est fourni : ne retourne que les prédictions de cet utilisateur
    - Si user_id est None : retourne TOUT (mode admin)
    - Si inclure_supprimes est False : masque les prédictions marquées deleted
    - Si inclure_supprimes est True : retourne tout (mode admin archive)
    """
    historique_firebase = []
    historique_local    = []

    # Chargement Firebase avec timeout
    db = get_firebase_db()
    if db:
        try:
            import concurrent.futures
            def _fetch():
                docs = db.collection('predictions').order_by(
                    'date', direction='DESCENDING'
                ).limit(500).stream()
                return [doc.to_dict() for doc in docs]

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_fetch)
                try:
                    historique_firebase = future.result(timeout=8)
                except concurrent.futures.TimeoutError:
                    historique_firebase = []
        except Exception:
            historique_firebase = []

    # Chargement local
    if os.path.exists(FICHIER_HISTORIQUE):
        try:
            with open(FICHIER_HISTORIQUE, 'r', encoding='utf-8') as f:
                historique_local = json.load(f)
        except:
            historique_local = []

    # Fusion Firebase + local
    if historique_firebase:
        dates_firebase = {h.get('date') for h in historique_firebase}
        for h in historique_local:
            if h.get('date') not in dates_firebase:
                historique_firebase.append(h)
                try:
                    if db:
                        db.collection('predictions').add(h)
                except:
                    pass
        historique = sorted(
            historique_firebase,
            key=lambda x: x.get('date', ''),
            reverse=True
        )
    elif historique_local:
        historique = historique_local
        # Si Firebase vide mais local non vide -> synchroniser
        if db:
            try:
                for h in historique_local:
                    db.collection('predictions').add(h)
            except:
                pass
    else:
        historique = []

    # ── FILTRAGE PAR USER_ID ──
    if user_id:
        historique = [h for h in historique if h.get('user_id') == user_id]

    # ── FILTRAGE DES SUPPRIMÉS ──
    if not inclure_supprimes:
        historique = [h for h in historique if not h.get('deleted', False)]

    return historique

# ============================================================
# SAUVEGARDE PREDICTION (Firebase + local) — avec user_id automatique
# ============================================================
def sauvegarder_prediction(prediction):
    """
    Sauvegarde une prédiction dans Firebase et en local.
    Ajoute automatiquement le user_id de l'utilisateur connecté.
    Convertit les types numpy pour compatibilité Firebase/JSON.
    """
    import numpy as np

    # ── Ajouter automatiquement le user_id si absent ──
    if 'user_id' not in prediction:
        user = st.session_state.get("user", {})
        prediction['user_id'] = user.get('uid', 'anonymous')
        prediction['user_email'] = user.get('email', '')

    # ── Convertir les types numpy pour Firebase/JSON ──
    prediction_clean = {}
    for k, v in prediction.items():
        try:
            if isinstance(v, (np.integer,)):
                prediction_clean[k] = int(v)
            elif isinstance(v, (np.floating,)):
                prediction_clean[k] = float(v)
            elif isinstance(v, np.ndarray):
                prediction_clean[k] = v.tolist()
            elif isinstance(v, (np.bool_,)):
                prediction_clean[k] = bool(v)
            else:
                prediction_clean[k] = v
        except:
            prediction_clean[k] = str(v)

    # ── Sauvegarde Firebase ──
    db = get_firebase_db()
    if db:
        try:
            db.collection('predictions').add(prediction_clean)
        except:
            pass

    # ── Sauvegarde locale en backup ──
    historique = []
    if os.path.exists(FICHIER_HISTORIQUE):
        try:
            with open(FICHIER_HISTORIQUE, 'r', encoding='utf-8') as f:
                historique = json.load(f)
        except:
            historique = []
    historique.append(prediction_clean)
    with open(FICHIER_HISTORIQUE, 'w', encoding='utf-8') as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

def sauvegarder_historique(historique):
    # Sauvegarde locale
    with open(FICHIER_HISTORIQUE, 'w', encoding='utf-8') as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    # Mise à jour Firebase
    db = get_firebase_db()
    if db:
        try:
            for h in historique:
                if h.get('resultat_reel') or h.get('deleted'):
                    docs = db.collection('predictions').where(
                        'joueur_a', '==', h.get('joueur_a')
                    ).where(
                        'joueur_b', '==', h.get('joueur_b')
                    ).where(
                        'date', '==', h.get('date')
                    ).stream()
                    for doc in docs:
                        update_data = {}
                        if h.get('resultat_reel'):
                            update_data['resultat_reel'] = h.get('resultat_reel')
                            update_data['score_reel'] = h.get('score_reel', '')
                        if h.get('deleted'):
                            update_data['deleted'] = True
                            update_data['deleted_at'] = h.get('deleted_at', '')
                        if update_data:
                            doc.reference.update(update_data)
        except:
            pass

# ============================================================
# SUPPRESSION DOUCE D'UNE PRÉDICTION
# ============================================================
def supprimer_prediction(historique, index):
    """
    Marque une prédiction comme supprimée (soft delete).
    La prédiction reste dans la base pour l'admin mais disparaît pour l'utilisateur.
    """
    if 0 <= index < len(historique):
        historique[index]['deleted'] = True
        historique[index]['deleted_at'] = datetime.now().isoformat()
        sauvegarder_historique(historique)
        return True
    return False

# ============================================================
# PAGE HISTORIQUE — avec cloisonnement + suppression douce + filtre 30j
# ============================================================
def page_historique():
    st.title("📚 Historique des prédictions")
    st.markdown("---")

    # Indicateur Firebase
    db = get_firebase_db()
    if db:
        st.success("🔥 Connecté à Firebase — historique sauvegardé en ligne")
    else:
        st.warning("💾 Mode local — Firebase non connecté")

    # ── Cloisonnement par utilisateur ──
    user = st.session_state.get("user", {})
    user_id = user.get('uid', '')
    user_email = user.get('email', 'Utilisateur')
    user_plan = user.get('plan', 'gratuit')

    from modules.auth import is_admin, is_premium
    est_admin = is_admin()
    est_premium = is_premium()

    if est_admin:
        # ── MODE ADMIN : voir tout, y compris supprimés ──
        historique_complet = charger_historique(inclure_supprimes=True)  # TOUT
        historique = charger_historique(inclure_supprimes=False)  # Sans supprimés (vue par défaut)

        nb_supprimes = len([h for h in historique_complet if h.get('deleted', False)])

        st.info(f"🛡️ Mode Admin — {len(historique_complet)} prédictions totales ({nb_supprimes} supprimées par les utilisateurs)")

        # Toggle pour voir les supprimés
        voir_supprimes = st.checkbox("🗑️ Afficher aussi les prédictions supprimées par les utilisateurs", value=False)
        if voir_supprimes:
            historique = historique_complet

    else:
        # ── MODE UTILISATEUR : voir seulement les siennes, non supprimées ──
        historique_toutes = charger_historique(user_id=user_id, inclure_supprimes=False)

        # ── Filtre 30 jours pour les gratuits ──
        date_limite = datetime.now() - timedelta(days=30)

        if est_premium:
            # Premium voit tout (ses données non supprimées)
            historique = historique_toutes
            st.caption(f"⭐ Compte Premium — {user_email} — Historique complet")
        else:
            # Gratuit voit seulement les 30 derniers jours
            historique = []
            masquees = 0
            for h in historique_toutes:
                try:
                    date_pred = datetime.strptime(str(h.get('date', ''))[:10], '%Y-%m-%d')
                    if date_pred >= date_limite:
                        historique.append(h)
                    else:
                        masquees += 1
                except:
                    # Si la date n'est pas parseable, on l'inclut par défaut
                    historique.append(h)

            st.caption(f"📌 Tes prédictions personnelles — {user_email} — 30 derniers jours")

            if masquees > 0:
                st.warning(
                    f"🔒 **{masquees} prédiction(s) masquée(s)** — "
                    f"Ton historique gratuit est limité aux 30 derniers jours.\n\n"
                    f"⭐ **Passe en Premium** pour voir tout ton historique depuis le début !"
                )

    if not historique:
        st.info(
            "📝 Aucune prédiction enregistrée pour l'instant."
            "\n\nFais ta première prédiction dans l'onglet 🎾 Prédiction !"
        )
        return

    # ── Résumé ──
    total    = len(historique)
    avec_res = [h for h in historique if h.get('resultat_reel')]
    corrects = [
        h for h in avec_res
        if h.get('resultat_reel') == h.get('vainqueur')
    ]
    pct_ok   = (
        round(len(corrects) / len(avec_res) * 100, 1)
        if avec_res else 0
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total prédictions", total)
    with col2:
        st.metric("✅ Résultats saisis", len(avec_res))
    with col3:
        st.metric("🎯 Prédictions correctes", len(corrects))
    with col4:
        st.metric("📊 Précision réelle", f"{pct_ok}%")

    st.markdown("---")

    # ── Bouton vérification automatique ──
    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        if st.button("🔍 Vérifier tous les résultats via API", type="primary"):
            a_verifier = [h for h in historique if not h.get('resultat_reel')]
            if not a_verifier:
                st.success("✅ Tous les résultats sont déjà renseignés !")
            else:
                with st.spinner(f"Recherche des résultats pour {len(a_verifier)} prédiction(s)..."):
                    trouves, historique = verifier_resultats_via_api(historique)
                if trouves > 0:
                    sauvegarder_historique(historique)
                    st.success(f"✅ {trouves} résultat(s) trouvé(s) et sauvegardés !")
                    st.rerun()
                else:
                    st.warning("⚠️ Aucun résultat trouvé — les matchs ne sont peut-être pas encore terminés.")
    with col_btn2:
        st.caption(f"⏳ {len([h for h in historique if not h.get('resultat_reel')])} prédiction(s) sans résultat réel")

    st.markdown("---")

    # ── Tableau historique avec bouton supprimer ──
    st.subheader("📋 Toutes les prédictions")

    for i, h in enumerate(historique):
        res_reel  = h.get('resultat_reel', '')
        vainqueur = h.get('vainqueur', '')
        if res_reel and vainqueur:
            correct = "✅" if res_reel.lower().split()[-1] == vainqueur.lower().split()[-1] else "❌"
        else:
            correct = "⏳"

        est_supprime = h.get('deleted', False)

        # ── Ligne de prédiction ──
        with st.container():
            col_info, col_res, col_action = st.columns([5, 3, 1])

            with col_info:
                # Badge supprimé (visible seulement pour admin)
                prefix = "🗑️ " if est_supprime else ""
                st.markdown(
                    f"**{prefix}{i+1}. {h.get('joueur_a', '?')} vs {h.get('joueur_b', '?')}**  \n"
                    f"📅 {h.get('date', 'N/A')} · 🎾 {h.get('surface', '?')} · 🏆 {h.get('tournoi', '?')}"
                )

            with col_res:
                st.markdown(
                    f"🤖 **{vainqueur}** ({h.get('proba_v', 0)}%)  \n"
                    f"Résultat : {res_reel if res_reel else '⏳ En attente'} {correct}"
                )

            with col_action:
                # Bouton supprimer (pas pour admin, et pas si déjà supprimé)
                if not est_admin and not est_supprime:
                    if st.button("🗑️", key=f"del_{i}_{h.get('date','')}", help="Supprimer cette prédiction"):
                        # On doit retrouver cette prédiction dans l'historique COMPLET (non filtré)
                        historique_complet_user = charger_historique(user_id=user_id, inclure_supprimes=False)
                        # Trouver l'index dans l'historique complet
                        for j, hc in enumerate(historique_complet_user):
                            if (hc.get('date') == h.get('date') and
                                hc.get('joueur_a') == h.get('joueur_a') and
                                hc.get('joueur_b') == h.get('joueur_b')):
                                historique_complet_user[j]['deleted'] = True
                                historique_complet_user[j]['deleted_at'] = datetime.now().isoformat()
                                break
                        sauvegarder_historique(historique_complet_user)
                        st.success("✅ Prédiction supprimée de ton historique")
                        st.rerun()

                # Admin : badge supprimé
                if est_admin and est_supprime:
                    st.caption(f"🗑️ Supprimé le {h.get('deleted_at', '?')[:10]}")

            st.markdown("---")

    # ── Saisir résultat réel ──
    st.subheader("✏️ Saisir le résultat réel")
    st.info("Après le match, saisis le vrai vainqueur pour affiner l'IA !")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        id_pred = st.number_input(
            "ID de la prédiction",
            min_value=1,
            max_value=total,
            value=total,
            step=1
        )
    with col_r2:
        pred = historique[id_pred - 1]
        choix_vainqueur = st.selectbox(
            "Vrai vainqueur",
            [pred.get('joueur_a', 'Joueur A'),
             pred.get('joueur_b', 'Joueur B')]
        )

    score_reel = st.text_input(
        "Score réel (optionnel)",
        placeholder="Ex: 6-3 6-4",
        key="score_reel"
    )

    if st.button("💾 Enregistrer le résultat", type="primary"):
        historique[id_pred - 1]['resultat_reel'] = choix_vainqueur
        if score_reel:
            historique[id_pred - 1]['score_reel'] = score_reel
        sauvegarder_historique(historique)
        st.success(f"✅ Résultat enregistré ! Vainqueur réel : {choix_vainqueur}")

    st.markdown("---")

    # ── Analyse par surface ──
    if avec_res:
        st.subheader("📊 Précision par surface")
        surfaces = {}
        for h in avec_res:
            surf = h.get('surface', 'Unknown')
            if surf not in surfaces:
                surfaces[surf] = {'total': 0, 'correct': 0}
            surfaces[surf]['total'] += 1
            if h.get('resultat_reel') == h.get('vainqueur'):
                surfaces[surf]['correct'] += 1

        surf_rows = []
        for surf, stats in surfaces.items():
            pct = round(stats['correct'] / stats['total'] * 100, 1)
            surf_rows.append({
                'Surface'  : surf,
                'Total'    : stats['total'],
                'Corrects' : stats['correct'],
                'Précision': f"{pct}%"
            })

        st.dataframe(
            pd.DataFrame(surf_rows),
            hide_index=True,
            use_container_width=True,
        )

    # ── Export ──
    st.markdown("---")
    st.subheader("📥 Exporter l'historique")

    # Construire le DataFrame pour l'export
    rows_export = []
    for i, h in enumerate(historique):
        res_reel  = h.get('resultat_reel', '')
        vainqueur = h.get('vainqueur', '')
        if res_reel and vainqueur:
            correct = "OUI" if res_reel.lower().split()[-1] == vainqueur.lower().split()[-1] else "NON"
        else:
            correct = "EN ATTENTE"

        rows_export.append({
            'ID'             : i + 1,
            'Date'           : h.get('date', 'N/A'),
            'Joueur A'       : h.get('joueur_a', 'N/A'),
            'Joueur B'       : h.get('joueur_b', 'N/A'),
            'Surface'        : h.get('surface', 'N/A'),
            'Tournoi'        : h.get('tournoi', 'N/A'),
            'Round'          : h.get('best_of', 'N/A'),
            'IA prédit'      : vainqueur,
            'Probabilité'    : f"{h.get('proba_v', 0)}%",
            'Score prédit'   : h.get('score_exact', 'N/A'),
            'Sets prédits'   : h.get('nb_sets', 'N/A'),
            'Handicap'       : h.get('handicap', 'N/A'),
            'Résultat réel'  : res_reel if res_reel else 'En attente',
            'Score réel'     : h.get('score_reel', '-'),
            'Correct ?'      : correct,
        })

    df_export = pd.DataFrame(rows_export)
    csv = df_export.to_csv(index=False)
    st.download_button(
        label     = "⬇️ Télécharger CSV",
        data      = csv,
        file_name = f"historique_predictions_{datetime.now().strftime('%Y%m%d')}.csv",
        mime      = "text/csv"
    )