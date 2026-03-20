# ============================================================
# MODULE HISTORIQUE — avec Firebase
# ============================================================
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

FICHIER_HISTORIQUE = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'historique.json'
)

# ============================================================
# CONNEXION FIREBASE
# ============================================================
def get_firebase_db():
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            # Option 1 : fichier local (PC)
            chemin_cle = os.path.join(
                os.path.dirname(__file__), '..', 'data', 'firebase_key.json'
            )
            if os.path.exists(chemin_cle):
                cred = credentials.Certificate(chemin_cle)
                firebase_admin.initialize_app(cred)
            # Option 2 : secret HuggingFace
            elif os.getenv('FIREBASE_KEY'):
                cle_json = json.loads(os.getenv('FIREBASE_KEY'))
                cred = credentials.Certificate(cle_json)
                firebase_admin.initialize_app(cred)
            else:
                return None

        return firestore.client()
    except Exception as e:
        return None

# ============================================================
# CHARGEMENT HISTORIQUE (Firebase + local)
# ============================================================
def charger_historique():
    historique_firebase = []
    historique_local    = []

    # Chargement Firebase
    db = get_firebase_db()
    if db:
        try:
            docs = db.collection('predictions').order_by(
                'date', direction='DESCENDING'
            ).limit(500).stream()
            historique_firebase = [doc.to_dict() for doc in docs]
        except:
            pass

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
        return sorted(
            historique_firebase,
            key=lambda x: x.get('date', ''),
            reverse=True
        )

    # Si Firebase vide mais local non vide -> synchroniser
    if historique_local and db:
        try:
            for h in historique_local:
                db.collection('predictions').add(h)
        except:
            pass

    return historique_local

# ============================================================
# SAUVEGARDE HISTORIQUE (Firebase + local)
# ============================================================
def sauvegarder_prediction(prediction):
    # Sauvegarde Firebase
    db = get_firebase_db()
    if db:
        try:
            db.collection('predictions').add(prediction)
        except:
            pass

    # Sauvegarde locale en backup
    historique = []
    if os.path.exists(FICHIER_HISTORIQUE):
        try:
            with open(FICHIER_HISTORIQUE, 'r', encoding='utf-8') as f:
                historique = json.load(f)
        except:
            historique = []
    historique.append(prediction)
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
                if h.get('resultat_reel'):
                    docs = db.collection('predictions').where(
                        'joueur_a', '==', h.get('joueur_a')
                    ).where(
                        'joueur_b', '==', h.get('joueur_b')
                    ).where(
                        'date', '==', h.get('date')
                    ).stream()
                    for doc in docs:
                        doc.reference.update({
                            'resultat_reel': h.get('resultat_reel'),
                            'score_reel': h.get('score_reel', '')
                        })
        except:
            pass

# ============================================================
# PAGE HISTORIQUE
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

    historique = charger_historique()

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

    # ── Tableau historique ──
    st.subheader("📋 Toutes les prédictions")

    rows = []
    for i, h in enumerate(historique):
        rows.append({
            'ID'             : i + 1,
            'Date'           : h.get('date', 'N/A'),
            'Joueur A'       : h.get('joueur_a', 'N/A'),
            'Joueur B'       : h.get('joueur_b', 'N/A'),
            'Surface'        : h.get('surface', 'N/A'),
            'Tournoi'        : h.get('tournoi', 'N/A'),
            'IA prédit'      : h.get('vainqueur', 'N/A'),
            'Probabilité'    : f"{h.get('proba_v', 0)}%",
            'Sets prédits'   : h.get('nb_sets', 'N/A'),
            'Résultat réel'  : h.get('resultat_reel', '⏳ En attente'),
        })

    df_hist = pd.DataFrame(rows)
    st.dataframe(df_hist, hide_index=True, use_container_width=True)

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
        st.rerun()

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
    csv = df_hist.to_csv(index=False)
    st.download_button(
        label     = "⬇️ Télécharger CSV",
        data      = csv,
        file_name = f"historique_predictions_{datetime.now().strftime('%Y%m%d')}.csv",
        mime      = "text/csv"
    )