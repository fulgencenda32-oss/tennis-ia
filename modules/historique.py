# ============================================================
# MODULE HISTORIQUE — Firebase + Cloisonnement + Suppression douce + Stats perso
# ============================================================
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go

FICHIER_HISTORIQUE = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'historique.json'
)

# ============================================================
# VERIFICATION RESULTATS REELS VIA API
# ============================================================
def verifier_resultats_via_api(historique):
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
        date     = str(h.get('date', ''))[:10]

        if not joueur_a or not joueur_b or not date:
            continue

        resultat = appel_api(
            {"met": "Fixtures", "from": date, "to": date},
            utiliser_cache=True
        )

        if resultat["source"] == "erreur" or not resultat.get("data"):
            continue

        data = resultat["data"]
        if data.get("success") != 1:
            continue

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
    t.join(timeout=5)
    return result[0]

# ============================================================
# CHARGEMENT HISTORIQUE
# ============================================================
def charger_historique(user_id=None, inclure_supprimes=False):
    historique_firebase = []
    historique_local    = []

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

    if os.path.exists(FICHIER_HISTORIQUE):
        try:
            with open(FICHIER_HISTORIQUE, 'r', encoding='utf-8') as f:
                historique_local = json.load(f)
        except:
            historique_local = []

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
        if db:
            try:
                for h in historique_local:
                    db.collection('predictions').add(h)
            except:
                pass
    else:
        historique = []

    if user_id:
        historique = [h for h in historique if h.get('user_id') == user_id]

    if not inclure_supprimes:
        historique = [h for h in historique if not h.get('deleted', False)]

    return historique

# ============================================================
# SAUVEGARDE PREDICTION
# ============================================================
def sauvegarder_prediction(prediction):
    import numpy as np

    if 'user_id' not in prediction:
        user = st.session_state.get("user", {})
        prediction['user_id'] = user.get('uid', 'anonymous')
        prediction['user_email'] = user.get('email', '')

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

    db = get_firebase_db()
    if db:
        try:
            db.collection('predictions').add(prediction_clean)
        except:
            pass

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
    with open(FICHIER_HISTORIQUE, 'w', encoding='utf-8') as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

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
# PAGE HISTORIQUE
# ============================================================
def page_historique():
    st.title("📚 Historique des prédictions")
    st.markdown("---")

    db = get_firebase_db()
    if db:
        st.success("🔥 Connecté à Firebase — historique sauvegardé en ligne")
    else:
        st.warning("💾 Mode local — Firebase non connecté")

    user = st.session_state.get("user", {})
    user_id = user.get('uid', '')
    user_email = user.get('email', 'Utilisateur')

    from modules.auth import is_admin, is_premium
    est_admin = is_admin()
    est_premium = is_premium()

    if est_admin:
        historique_complet = charger_historique(inclure_supprimes=True)
        historique = charger_historique(inclure_supprimes=False)
        nb_supprimes = len([h for h in historique_complet if h.get('deleted', False)])
        st.info(f"🛡️ Mode Admin — {len(historique_complet)} prédictions totales ({nb_supprimes} supprimées)")
        voir_supprimes = st.checkbox("🗑️ Afficher les prédictions supprimées", value=False)
        if voir_supprimes:
            historique = historique_complet
    else:
        historique_toutes = charger_historique(user_id=user_id, inclure_supprimes=False)
        date_limite = datetime.now() - timedelta(days=30)

        if est_premium:
            historique = historique_toutes
            st.caption(f"⭐ Compte Premium — {user_email} — Historique complet")
        else:
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
                    historique.append(h)

            st.caption(f"📌 Tes prédictions — {user_email} — 30 derniers jours")

            if masquees > 0:
                st.warning(
                    f"🔒 **{masquees} prédiction(s) masquée(s)** — "
                    f"Passe en Premium pour voir tout ton historique !"
                )

    if not historique:
        st.info("📝 Aucune prédiction enregistrée.\n\nFais ta première prédiction dans l'onglet 🎾 Prédiction !")
        return

    # ── Calcul des stats ──
    total = len(historique)
    avec_res = [h for h in historique if h.get('resultat_reel')]
    corrects = [h for h in avec_res if h.get('resultat_reel') == h.get('vainqueur')]
    incorrects = [h for h in avec_res if h.get('resultat_reel') != h.get('vainqueur')]
    en_attente = total - len(avec_res)
    pct_ok = round(len(corrects) / len(avec_res) * 100, 1) if avec_res else 0

    # ── Série en cours ──
    serie_en_cours = 0
    for h in avec_res:
        if h.get('resultat_reel') == h.get('vainqueur'):
            serie_en_cours += 1
        else:
            break

    # ── Métriques principales ──
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📋 Total", total)
    with col2:
        st.metric("✅ Correctes", len(corrects))
    with col3:
        st.metric("❌ Incorrectes", len(incorrects))
    with col4:
        st.metric("📊 Précision", f"{pct_ok}%")
    with col5:
        st.metric("🔥 Série", f"{serie_en_cours}")

    # ── Graphique circulaire ──
    if avec_res or en_attente > 0:
        col_graph, col_resume = st.columns([2, 1])

        with col_graph:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['✅ Correctes', '❌ Incorrectes', '⏳ En attente'],
                values=[len(corrects), len(incorrects), en_attente],
                marker_colors=['#2d9e56', '#e74c3c', '#f39c12'],
                hole=0.5,
                textinfo='percent+value',
                textfont_size=14
            )])
            fig_pie.update_layout(
                height=280,
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_resume:
            st.markdown("### 📈 Résumé")
            if pct_ok >= 70:
                st.success(f"🏆 Excellent ! Tu as {pct_ok}% de réussite")
            elif pct_ok >= 55:
                st.info(f"👍 Bien joué ! {pct_ok}% de réussite")
            elif pct_ok > 0:
                st.warning(f"📊 {pct_ok}% de réussite — continue !")
            else:
                st.info("⏳ Résultats en attente...")

            if serie_en_cours >= 5:
                st.success(f"🔥 Série de {serie_en_cours} victoires !")
            elif serie_en_cours >= 3:
                st.info(f"🔥 Série de {serie_en_cours} victoires")

    st.markdown("---")

    # ── Vérification automatique ──
    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        if st.button("🔍 Vérifier résultats via API", type="primary"):
            a_verifier = [h for h in historique if not h.get('resultat_reel')]
            if not a_verifier:
                st.success("✅ Tous les résultats sont renseignés !")
            else:
                with st.spinner(f"Recherche pour {len(a_verifier)} prédiction(s)..."):
                    trouves, historique = verifier_resultats_via_api(historique)
                if trouves > 0:
                    sauvegarder_historique(historique)
                    st.success(f"✅ {trouves} résultat(s) trouvé(s) !")
                    st.rerun()
                else:
                    st.warning("⚠️ Aucun résultat trouvé — matchs pas encore terminés ?")
    with col_btn2:
        st.caption(f"⏳ {en_attente} prédiction(s) sans résultat")

    st.markdown("---")

    # ── Liste des prédictions ──
    st.subheader("📋 Détail des prédictions")

    for i, h in enumerate(historique):
        res_reel  = h.get('resultat_reel', '')
        vainqueur = h.get('vainqueur', '')
        est_supprime = h.get('deleted', False)

        if res_reel and vainqueur:
            if res_reel.lower().split()[-1] == vainqueur.lower().split()[-1]:
                badge, couleur = "✅", "success"
            else:
                badge, couleur = "❌", "error"
        else:
            badge, couleur = "⏳", "warning"

        with st.container():
            col_badge, col_match, col_resultat, col_action = st.columns([1, 4, 3, 1])

            with col_badge:
                if couleur == "success":
                    st.markdown(f"<div style='font-size:2rem;text-align:center;'>{badge}</div>", unsafe_allow_html=True)
                elif couleur == "error":
                    st.markdown(f"<div style='font-size:2rem;text-align:center;'>{badge}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='font-size:2rem;text-align:center;'>{badge}</div>", unsafe_allow_html=True)

            with col_match:
                prefix = "🗑️ " if est_supprime else ""
                st.markdown(
                    f"**{prefix}{h.get('joueur_a', '?')} vs {h.get('joueur_b', '?')}**  \n"
                    f"📅 {str(h.get('date', ''))[:10]} · 🎾 {h.get('surface', '?')} · 🏆 {h.get('tournoi', '?')}"
                )

            with col_resultat:
                st.markdown(
                    f"🤖 **{vainqueur}** ({h.get('proba_v', 0)}%)  \n"
                    f"🏆 {res_reel if res_reel else 'En attente'} {h.get('score_reel', '')}"
                )

            with col_action:
                if not est_admin and not est_supprime:
                    if st.button("🗑️", key=f"del_{i}_{h.get('date','')}", help="Supprimer"):
                        historique_user = charger_historique(user_id=user_id, inclure_supprimes=False)
                        for j, hc in enumerate(historique_user):
                            if (hc.get('date') == h.get('date') and
                                hc.get('joueur_a') == h.get('joueur_a') and
                                hc.get('joueur_b') == h.get('joueur_b')):
                                historique_user[j]['deleted'] = True
                                historique_user[j]['deleted_at'] = datetime.now().isoformat()
                                break
                        sauvegarder_historique(historique_user)
                        st.success("✅ Supprimée")
                        st.rerun()

                if est_admin and est_supprime:
                    st.caption(f"🗑️ {h.get('deleted_at', '')[:10]}")

        st.markdown("---")

    # ── Saisie manuelle ──
    st.subheader("✏️ Saisir un résultat")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        id_pred = st.number_input("ID", min_value=1, max_value=total, value=1, step=1)
    with col_r2:
        pred = historique[id_pred - 1]
        choix = st.selectbox("Vainqueur réel", [pred.get('joueur_a', 'A'), pred.get('joueur_b', 'B')])

    score = st.text_input("Score (optionnel)", placeholder="6-3 6-4")

    if st.button("💾 Enregistrer", type="primary"):
        historique[id_pred - 1]['resultat_reel'] = choix
        if score:
            historique[id_pred - 1]['score_reel'] = score
        sauvegarder_historique(historique)
        st.success(f"✅ Enregistré : {choix}")
        st.rerun()

    st.markdown("---")

    # ── Stats par surface ──
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

        rows = []
        for surf, stats in surfaces.items():
            pct = round(stats['correct'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
            rows.append({'Surface': surf, 'Total': stats['total'], 'Corrects': stats['correct'], 'Précision': f"{pct}%"})

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── Export CSV ──
    st.markdown("---")
    st.subheader("📥 Exporter")

    rows_csv = []
    for i, h in enumerate(historique):
        res = h.get('resultat_reel', '')
        v = h.get('vainqueur', '')
        correct = "OUI" if res and v and res.lower().split()[-1] == v.lower().split()[-1] else ("NON" if res else "EN ATTENTE")
        rows_csv.append({
            'Date': h.get('date', ''), 'Joueur A': h.get('joueur_a', ''), 'Joueur B': h.get('joueur_b', ''),
            'Surface': h.get('surface', ''), 'IA': v, 'Proba': f"{h.get('proba_v', 0)}%",
            'Réel': res, 'Score': h.get('score_reel', ''), 'Correct': correct
        })

    csv = pd.DataFrame(rows_csv).to_csv(index=False)
    st.download_button("⬇️ Télécharger CSV", csv, f"historique_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")