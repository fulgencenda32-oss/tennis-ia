# ============================================================
# MODULE MATCHS DU JOUR
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY  = os.getenv("ALLSPORTS_API_KEY")
BASE_URL = "https://apiv2.allsportsapi.com/tennis/"

# ============================================================
# RÉCUPÉRATION MATCHS
# ============================================================
@st.cache_data(ttl=1800)
def get_matchs_periode(date_debut, date_fin, api_key):
    try:
        r = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : api_key,
            "from"   : date_debut,
            "to"     : date_fin,
        }, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") == 1:
                return data.get("result", [])
    except Exception as e:
        st.error(f"Erreur API : {e}")
    return []

# ============================================================
# TRAITEMENT MATCHS
# ============================================================
def traiter_matchs(matchs_raw, filtre_circuit="Tous",
                   filtre_statut="Tous"):
    if not matchs_raw:
        return pd.DataFrame()

    rows = []
    for m in matchs_raw:
        statut    = str(m.get('event_status', '')).lower()
        circuit   = str(m.get('country_name', ''))
        joueur_a  = str(m.get('event_first_player',  ''))
        joueur_b  = str(m.get('event_second_player', ''))

        if not joueur_a or not joueur_b:
            continue

        rows.append({
            'event_key'  : str(m.get('event_key', '')),
            'Date'       : str(m.get('event_date', '')),
            'Heure'      : str(m.get('event_time', '')),
            'Joueur A'   : joueur_a,
            'Joueur B'   : joueur_b,
            'Tournoi'    : str(m.get('league_name', '')),
            'Circuit'    : circuit,
            'Round'      : str(m.get('league_round', '')),
            'Score'      : str(m.get('event_final_result', '-')),
            'Statut'     : str(m.get('event_status', '')),
            'statut_low' : statut,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if filtre_circuit != "Tous":
        df = df[df['Circuit'].str.contains(
            filtre_circuit, case=False, na=False
        )]

    if filtre_statut == "À venir":
        df = df[df['statut_low'].isin(
            ['', 'notstarted', 'scheduled', 'ns']
        )]
    elif filtre_statut == "En cours":
        df = df[df['statut_low'].isin(
            ['inprogress', 'live', '1st', '2nd', '3rd']
        )]
    elif filtre_statut == "Terminés":
        df = df[df['statut_low'] == 'finished']

    return df.reset_index(drop=True)

# ============================================================
# PAGE MATCHS DU JOUR
# ============================================================
def page_matchs_jour(modeles, df_base):
    st.title("📅 Matchs du jour")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        date_choisie = st.date_input(
            "📅 Date",
            value=datetime.now().date()
        )
    with col2:
        filtre_circuit = st.selectbox(
            "🏆 Circuit",
            ["Tous", "ATP", "WTA", "Challenger", "ITF", "Futures"]
        )
    with col3:
        filtre_statut = st.selectbox(
            "📊 Statut",
            ["Tous", "À venir", "En cours", "Terminés"]
        )
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        charger = st.button("🔄 Charger", type="primary")

    predire_tous = st.button("⚡ Prédire TOUS les matchs automatiquement")

    st.markdown("---")

    if charger or predire_tous or st.session_state.get('auto_charger'):
        st.session_state['auto_charger'] = False
        date_str     = str(date_choisie)
        date_str_fin = str(date_choisie + timedelta(days=1))

        with st.spinner("⏳ Chargement des matchs..."):
            key = os.getenv("ALLSPORTS_API_KEY")
            matchs_raw = get_matchs_periode(date_str, date_str, key)
            if not matchs_raw:
                matchs_raw = get_matchs_periode(date_str, date_str_fin, key)

        df_matchs = traiter_matchs(matchs_raw, filtre_circuit, filtre_statut)

        if df_matchs.empty:
            st.warning("⚠️ Aucun match trouvé. Essaie une autre date ou un autre filtre.")
            return

        total    = len(df_matchs)
        termines = len(df_matchs[df_matchs['statut_low'] == 'finished'])
        en_cours = len(df_matchs[df_matchs['statut_low'].isin(['inprogress','live'])])
        a_venir  = total - termines - en_cours

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("📋 Total",     total)
        with c2: st.metric("⏳ À venir",   a_venir)
        with c3: st.metric("🔴 En cours",  en_cours)
        with c4: st.metric("✅ Terminés",  termines)

        st.markdown("---")

        if predire_tous:
            st.subheader("⚡ Prédictions automatiques")
            from modules.prediction import predire_match

            a_predire = df_matchs[
                ~df_matchs['statut_low'].isin(['finished'])
            ].head(30)

            if a_predire.empty:
                st.info("Aucun match à venir à prédire.")
            else:
                barre     = st.progress(0)
                resultats = []

                for i, (_, match) in enumerate(a_predire.iterrows()):
                    j_a  = match['Joueur A']
                    j_b  = match['Joueur B']
                    circ = match['Circuit'].upper()
                    if 'WTA' in circ:          t = 'WTA'
                    elif 'CHALLENGER' in circ: t = 'Challenger'
                    elif 'ITF' in circ:        t = 'ITF'
                    else:                      t = 'ATP'

                    try:
                        res = predire_match(
                            j_a, j_b, modeles, df_base,
                            surface='Hard', tournoi=t,
                        )
                        resultats.append({
                            'Joueur A'    : j_a,
                            'Joueur B'    : j_b,
                            'Tournoi'     : match['Tournoi'],
                            'Vainqueur IA': res['vainqueur'],
                            'Probabilité' : f"{res['proba_v']}%",
                            'Score prédit': res['score_exact'],
                            'Sets'        : res['nb_sets'],
                            'Handicap'    : res['handicap'],
                        })
                    except:
                        resultats.append({
                            'Joueur A'    : j_a,
                            'Joueur B'    : j_b,
                            'Tournoi'     : match['Tournoi'],
                            'Vainqueur IA': 'N/A',
                            'Probabilité' : 'N/A',
                            'Score prédit': 'N/A',
                            'Sets'        : 'N/A',
                            'Handicap'    : 'N/A',
                        })

                    barre.progress((i+1) / len(a_predire))

                df_res = pd.DataFrame(resultats)
                st.success(f"✅ {len(df_res)} prédictions calculées !")
                st.dataframe(df_res, hide_index=True, use_container_width=True)

                csv = df_res.to_csv(index=False)
                st.download_button(
                    "⬇️ Télécharger CSV",
                    data      = csv,
                    file_name = f"predictions_{date_str}.csv",
                    mime      = "text/csv"
                )

            st.markdown("---")

        def emoji_statut(s):
            s = str(s).lower()
            if s == 'finished':                   return '✅'
            if s in ['inprogress', 'live']:        return '🔴'
            return '⏳'

        st.subheader(f"📋 {total} matchs — {date_str}")
        df_affich = df_matchs[[
            'Heure','Joueur A','Joueur B',
            'Tournoi','Circuit','Round','Score','Statut'
        ]].copy()
        df_affich.insert(0, '.', df_matchs['statut_low'].apply(emoji_statut))

        st.dataframe(df_affich, hide_index=True, use_container_width=True, height=400)

        st.markdown("---")

        st.subheader("🔮 Prédire un match individuel")
        options_matchs = [
            f"{row['Joueur A']} vs {row['Joueur B']} — {row['Tournoi']}"
            for _, row in df_matchs.iterrows()
        ]

        match_choisi = st.selectbox("Sélectionne un match", options_matchs, key="match_individuel")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            surface_ind = st.selectbox("Surface", ["Hard","Clay","Grass","Carpet"], key="surf_ind")
        with col_s2:
            best_of_ind = st.selectbox("Format", [3, 5], format_func=lambda x: f"Best of {x}", key="bo_ind")

        if st.button("🔮 Prédire ce match", type="primary"):
            idx   = options_matchs.index(match_choisi)
            match = df_matchs.iloc[idx]
            j_a   = match['Joueur A']
            j_b   = match['Joueur B']

            circ = match['Circuit'].upper()
            if 'WTA' in circ:          t = 'WTA'
            elif 'CHALLENGER' in circ: t = 'Challenger'
            elif 'ITF' in circ:        t = 'ITF'
            else:                      t = 'ATP'

            with st.spinner("⏳ Calcul en cours..."):
                from modules.prediction import predire_match
                try:
                    res = predire_match(
                        j_a, j_b, modeles, df_base,
                        surface     = surface_ind,
                        tournoi     = t,
                        round_match = str(match['Round']),
                        best_of     = best_of_ind,
                    )

                    st.success("✅ Prédiction calculée !")
                    st.markdown("---")

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("🏆 Vainqueur", res['vainqueur'], f"{res['proba_v']}%")
                    with c2:
                        st.metric("🎯 Score", res['score_exact'])
                    with c3:
                        st.metric("🔢 Sets", f"{res['nb_sets']} sets")
                    with c4:
                        st.metric("⚖️ Handicap", f"{res['handicap']} set(s)")

                    stats = pd.DataFrame({
                        'Statistique' : ['ELO général', f'ELO {surface_ind}', 'Forme récente', 'H2H', 'Classement'],
                        j_a : [res['elo_a'], res['elo_a_surf'], f"{res['forme_a']}%", res['h2h_a'], f"#{res['rank_a']}"],
                        j_b : [res['elo_b'], res['elo_b_surf'], f"{res['forme_b']}%", res['h2h_b'], f"#{res['rank_b']}"],
                    })
                    st.dataframe(stats, hide_index=True, use_container_width=True)

                    import plotly.graph_objects as go
                    fig = go.Figure(go.Bar(
                        x=[j_a, j_b],
                        y=[res['proba_a'], res['proba_b']],
                        marker_color=['#2d9e56','#FF5722'],
                        text=[f"{res['proba_a']}%", f"{res['proba_b']}%"],
                        textposition='auto',
                    ))
                    fig.update_layout(
                        yaxis_range=[0,100], height=280,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        margin=dict(t=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    st.error(f"❌ Erreur : {e}")