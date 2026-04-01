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
# 🔧 CACHE GLOBAL POUR ÉVITER ERREUR 429
# ============================================================
_FIREBASE_DB_CACHE = None
_FIREBASE_LAST_ERROR = None
_FIREBASE_ERROR_TIME = 0

def get_firebase_db_safe():
    """
    Connexion Firebase SÉCURISÉE avec cache et gestion erreur 429.
    Ne retente pas pendant 5 minutes après une erreur.
    """
    global _FIREBASE_DB_CACHE, _FIREBASE_LAST_ERROR, _FIREBASE_ERROR_TIME
    import time
    
    # Si erreur récente (moins de 5 min), ne pas retenter
    if _FIREBASE_LAST_ERROR and (time.time() - _FIREBASE_ERROR_TIME) < 300:
        return None
    
    # Si déjà connecté, retourner le cache
    if _FIREBASE_DB_CACHE is not None:
        return _FIREBASE_DB_CACHE
    
    import threading
    result = [None]
    error = [None]

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
        except Exception as e:
            error[0] = str(e)
            result[0] = None

    t = threading.Thread(target=_connecter, daemon=True)
    t.start()
    t.join(timeout=5)
    
    if error[0] and ("429" in error[0] or "quota" in error[0].lower()):
        _FIREBASE_LAST_ERROR = error[0]
        _FIREBASE_ERROR_TIME = time.time()
        return None
    
    _FIREBASE_DB_CACHE = result[0]
    return result[0]


# ============================================================
# VERIFICATION RESULTATS REELS VIA API
# ============================================================
def verifier_resultats_via_api(historique):
    try:
        from modules.api_rotation import appel_api
    except Exception:
        return 0, historique

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

        try:
            resultat = appel_api(
                {"met": "Fixtures", "from": date, "to": date},
                utiliser_cache=True
            )
        except Exception:
            continue

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
# CHARGEMENT HISTORIQUE — SÉCURISÉ
# ============================================================
def charger_historique(user_id=None, inclure_supprimes=False):
    """Charge l'historique avec protection contre erreur 429."""
    historique_firebase = []
    historique_local    = []

    # 🔧 Utiliser la fonction sécurisée
    db = get_firebase_db_safe()
    
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
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        st.warning("⚠️ Quota Firebase dépassé — utilisation du cache local")
                    historique_firebase = []
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.warning("⚠️ Quota Firebase dépassé — utilisation du cache local")
            historique_firebase = []

    # Toujours charger le local comme backup
    if os.path.exists(FICHIER_HISTORIQUE):
        try:
            with open(FICHIER_HISTORIQUE, 'r', encoding='utf-8') as f:
                historique_local = json.load(f)
        except:
            historique_local = []

    # Fusion
    if historique_firebase:
        dates_firebase = {h.get('date') for h in historique_firebase}
        for h in historique_local:
            if h.get('date') not in dates_firebase:
                historique_firebase.append(h)
        historique = sorted(
            historique_firebase,
            key=lambda x: x.get('date', ''),
            reverse=True
        )
    elif historique_local:
        historique = historique_local
    else:
        historique = []

    if user_id:
        historique = [h for h in historique if h.get('user_id') == user_id]

    if not inclure_supprimes:
        historique = [h for h in historique if not h.get('deleted', False)]

    return historique


# ============================================================
# SAUVEGARDE PREDICTION — SÉCURISÉE
# ============================================================
def sauvegarder_prediction(prediction):
    """Sauvegarde une prédiction avec protection erreur 429."""
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

    # 🔧 Firebase avec protection
    db = get_firebase_db_safe()
    firebase_ok = False
    if db:
        try:
            db.collection('predictions').add(prediction_clean)
            firebase_ok = True
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                pass  # Silencieux, on sauvegarde en local
            firebase_ok = False

    # Toujours sauvegarder en local
    historique = []
    if os.path.exists(FICHIER_HISTORIQUE):
        try:
            with open(FICHIER_HISTORIQUE, 'r', encoding='utf-8') as f:
                historique = json.load(f)
        except:
            historique = []
    historique.append(prediction_clean)
    try:
        with open(FICHIER_HISTORIQUE, 'w', encoding='utf-8') as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return firebase_ok


def sauvegarder_historique(historique):
    """Sauvegarde l'historique complet."""
    try:
        with open(FICHIER_HISTORIQUE, 'w', encoding='utf-8') as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except:
        pass

    db = get_firebase_db_safe()
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

    db = get_firebase_db_safe()
    if db:
        st.success("🔥 Connecté à Firebase — historique sauvegardé en ligne")
    else:
        st.warning("💾 Mode local — Firebase non connecté ou quota dépassé")

    user = st.session_state.get("user", {})
    user_id = user.get('uid', '')

    try:
        from modules.auth import is_admin, is_premium
        est_admin = is_admin()
        est_premium = is_premium()
    except:
        est_admin = False
        est_premium = False

    if est_admin:
        historique_complet = charger_historique(inclure_supprimes=True)
        historique = charger_historique(inclure_supprimes=False)
        nb_supprimes = len([h for h in historique_complet if h.get('deleted', False)])
        st.info(f"🛡️ Mode Admin — {len(historique_complet)} prédictions totales ({nb_supprimes} supprimées)")
        voir_supprimes = st.checkbox("🗑️ Afficher les prédictions supprimées", value=False)
        if voir_supprimes:
            historique = historique_complet
    else:
        historique = charger_historique(user_id=user_id, inclure_supprimes=False)

    if not historique:
        st.info("📭 Aucune prédiction dans l'historique.")
        return

    # Stats rapides
    total = len(historique)
    avec_res = [h for h in historique if h.get('resultat_reel')]
    corrects = [h for h in avec_res if h.get('resultat_reel', '').lower().split()[-1] == h.get('vainqueur', '').lower().split()[-1]]
    incorrects = [h for h in avec_res if h not in corrects]
    en_attente = total - len(avec_res)
    pct_ok = round(len(corrects) / len(avec_res) * 100, 1) if avec_res else 0

    # Série en cours
    serie_en_cours = 0
    for h in historique:
        if h.get('resultat_reel'):
            if h.get('resultat_reel', '').lower().split()[-1] == h.get('vainqueur', '').lower().split()[-1]:
                serie_en_cours += 1
            else:
                break

    col_stats, col_pie, col_resume = st.columns([1, 1, 1])

    with col_stats:
        st.metric("📊 Total", total)
        st.metric("✅ Corrects", len(corrects))
        st.metric("❌ Incorrects", len(incorrects))
        st.metric("⏳ En attente", en_attente)

    with col_pie:
        if avec_res:
            fig_pie = go.Figure([go.Pie(
                labels=['✅ Corrects', '❌ Incorrects', '⏳ En attente'],
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

    # Vérification automatique
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

    # Liste des prédictions
    st.subheader("📋 Détail des prédictions")

    for i, h in enumerate(historique[:50]):  # Limiter à 50 pour performance
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
            col_badge, col_match, col_resultat = st.columns([1, 4, 3])

            with col_badge:
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

        st.markdown("---")

    # Export CSV
    st.subheader("📥 Exporter")

    rows_csv = []
    for h in historique:
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