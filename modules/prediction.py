# ============================================================
# MODULE PRÉDICTION
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz
import json
import os
from datetime import datetime

# ============================================================
# CONVERSION SÉCURISÉE
# ============================================================
def safe_int(val, defaut=500):
    try:
        if val is None: return defaut
        s = str(val).strip()
        if s in ['', 'nan', 'None', 'NaN']: return defaut
        f = float(s)
        if np.isnan(f): return defaut
        return int(f)
    except:
        return defaut

def safe_float(val, defaut=500.0):
    try:
        if val is None: return defaut
        s = str(val).strip()
        if s in ['', 'nan', 'None', 'NaN']: return defaut
        f = float(s)
        if np.isnan(f): return defaut
        return f
    except:
        return defaut

# ============================================================
# RECHERCHE FLOUE
# ============================================================
def recherche_floue(nom, liste_joueurs, limite=5, seuil=55):
    if not nom or len(nom) < 2:
        return []
    resultats = process.extract(
        nom, liste_joueurs,
        scorer=fuzz.WRatio, limit=limite,
    )
    return [
        (joueur, score)
        for joueur, score, _ in resultats
        if score >= seuil
    ]

# ============================================================
# PRÉDICTION
# ============================================================
def predire_match(
    joueur_a, joueur_b,
    modeles, df_base,
    surface='Hard', tournoi='ATP',
    round_match='R32', best_of=3,
    cote_a=None, cote_b=None
):
    modele_win       = modeles['modele_win']
    modele_sets      = modeles['modele_sets']
    modele_handi     = modeles['modele_handi']
    FEATURES         = modeles['features']
    elo_final        = modeles['elo_final']
    elo_surf         = modeles['elo_final_surf']
    forme_final      = modeles['forme_final']
    dico_scores      = modeles['dico_scores']
    dico_scores_surf = modeles['dico_scores_surf']
    surface_map      = modeles['surface_map']
    circuit_map      = modeles['circuit_map']
    simplifier_round = modeles['simplifier_round']

    # ELO
    elo_a      = elo_final.get(joueur_a, 1500.0)
    elo_b      = elo_final.get(joueur_b, 1500.0)
    elo_a_surf = elo_surf.get(surface, {}).get(joueur_a, 1500.0)
    elo_b_surf = elo_surf.get(surface, {}).get(joueur_b, 1500.0)

    # Classement — conversion sécurisée
    def get_rank(joueur):
        if df_base is None:
            return 500
        mask = (
            (df_base['winner_name'] == joueur) |
            (df_base['loser_name']  == joueur)
        )
        rows = df_base[mask]
        if len(rows) == 0: return 500
        # Cherche la meilleure valeur disponible
        for _, row in rows.iloc[::-1].iterrows():
            if row['winner_name'] == joueur:
                r = safe_float(row.get('winner_rank', 0))
            else:
                r = safe_float(row.get('loser_rank', 0))
            if 0 < r < 2000:
                return r
        return 500

    rank_a = get_rank(joueur_a)
    rank_b = get_rank(joueur_b)

    # Forme
    forme_a = forme_final.get(joueur_a, 0.5)
    forme_b = forme_final.get(joueur_b, 0.5)

    # H2H
    if df_base is not None:
        mask_h2h = (
            ((df_base['winner_name'] == joueur_a) &
             (df_base['loser_name']  == joueur_b)) |
            ((df_base['winner_name'] == joueur_b) &
             (df_base['loser_name']  == joueur_a))
        )
        h2h_matchs = df_base[mask_h2h]
        total_h2h  = len(h2h_matchs)
        wins_a     = len(
            h2h_matchs[h2h_matchs['winner_name'] == joueur_a]
        )
    else:
        total_h2h = 0
        wins_a    = 0
    h2h_a = wins_a / total_h2h if total_h2h > 0 else 0.5
    h2h_b = 1 - h2h_a

    # Cotes
    if cote_a and cote_b and cote_a > 1 and cote_b > 1:
        proba_bk_a = 1 / cote_a
        proba_bk_b = 1 / cote_b
        total_bk   = proba_bk_a + proba_bk_b
        proba_bk_a /= total_bk
        proba_bk_b /= total_bk
        cote_diff  = proba_bk_a - proba_bk_b
    else:
        proba_bk_a = 0.5
        proba_bk_b = 0.5
        cote_diff  = 0.0

    # Encodage
    surf_enc    = surface_map.get(surface, 4)
    circuit_enc = circuit_map.get(tournoi, 0)
    genre_enc   = 1 if tournoi == 'WTA' else 0
    round_num   = simplifier_round(round_match)

    # Features
    X = pd.DataFrame([{
        'elo_diff'      : elo_a - elo_b,
        'elo_diff_surf' : elo_a_surf - elo_b_surf,
        'forme_diff'    : forme_a - forme_b,
        'h2h_diff'      : h2h_a - h2h_b,
        'fatigue_diff'  : 0.0,
        'rank_diff'     : rank_b - rank_a,
        'age_diff'      : 0.0,
        'surface_enc'   : surf_enc,
        'circuit_enc'   : circuit_enc,
        'genre_enc'     : genre_enc,
        'best_of'       : best_of,
        'round_num'     : round_num,
        'cote_diff'     : cote_diff,
        'cote_proba_A'  : proba_bk_a,
        'cote_proba_B'  : proba_bk_b,
    }])[FEATURES].fillna(0).astype('float32')

    # Prédictions
    proba_a    = float(modele_win.predict_proba(X)[0][1])
    nb_sets_p  = int(modele_sets.predict(X)[0]) + 2
    handicap_p = int(modele_handi.predict(X)[0]) + 1

    # Score exact
    cle      = (nb_sets_p, handicap_p)
    cle_surf = (nb_sets_p, handicap_p, surface)
    if cle_surf in dico_scores_surf:
        scores_surf = dico_scores_surf[cle_surf]
        if isinstance(scores_surf, list) and len(scores_surf) > 0:
            score_exact = np.random.choice(scores_surf)
        else:
            score_exact = scores_surf
    elif cle in dico_scores:
        scores_liste = dico_scores[cle]
        if isinstance(scores_liste, list) and len(scores_liste) > 0:
            score_exact = np.random.choice(scores_liste)
        else:
            score_exact = scores_liste
    else:
        scores_defaut_2 = ['6-4 6-3', '6-3 6-4', '6-2 6-4', '6-4 6-2', '7-5 6-3', '6-3 6-2', '7-6 6-4', '6-1 6-3']
        scores_defaut_3 = ['6-4 4-6 6-3', '7-5 4-6 6-4', '6-3 4-6 6-4', '6-4 3-6 7-5', '6-2 4-6 6-3', '7-6 4-6 6-3']
        if nb_sets_p == 2:
            score_exact = np.random.choice(scores_defaut_2)
        else:
            score_exact = np.random.choice(scores_defaut_3)

    vainqueur = joueur_a if proba_a >= 0.5 else joueur_b
    proba_v   = proba_a  if proba_a >= 0.5 else 1 - proba_a

    # Value bet
    value_bet_info = None
    if cote_a and cote_b and cote_a > 1 and cote_b > 1:
        if proba_a > (1 / cote_a):
            valeur = proba_a * cote_a - 1
            value_bet_info = {
                'joueur' : joueur_a,
                'cote'   : cote_a,
                'valeur' : round(valeur * 100, 1)
            }
        elif (1 - proba_a) > (1 / cote_b):
            valeur = (1 - proba_a) * cote_b - 1
            value_bet_info = {
                'joueur' : joueur_b,
                'cote'   : cote_b,
                'valeur' : round(valeur * 100, 1)
            }

    return {
        'joueur_a'       : joueur_a,
        'joueur_b'       : joueur_b,
        'vainqueur'      : vainqueur,
        'proba_a'        : round(proba_a * 100, 1),
        'proba_b'        : round((1 - proba_a) * 100, 1),
        'proba_v'        : round(proba_v * 100, 1),
        'nb_sets'        : nb_sets_p,
        'handicap'       : handicap_p,
        'score_exact'    : score_exact,
        'elo_a'          : round(elo_a),
        'elo_b'          : round(elo_b),
        'elo_a_surf'     : round(elo_a_surf),
        'elo_b_surf'     : round(elo_b_surf),
        'forme_a'        : round(forme_a * 100, 1),
        'forme_b'        : round(forme_b * 100, 1),
        'h2h_a'          : wins_a,
        'h2h_b'          : total_h2h - wins_a,
        'rank_a'         : safe_int(rank_a),
        'rank_b'         : safe_int(rank_b),
        'surface'        : surface,
        'tournoi'        : tournoi,
        'best_of'        : best_of,
        'value_bet'      : value_bet_info['joueur'] if value_bet_info else None,
        'value_bet_info' : value_bet_info,
        'cotes_fournies' : cote_a is not None,
        'date'           : datetime.now().strftime('%Y-%m-%d %H:%M'),
    }

# ============================================================
# PAGE PRÉDICTION
# ============================================================
def page_prediction(modeles, df_base):
    st.title("🎾 Prédiction de match")
    st.markdown("---")

    liste_joueurs = list(modeles['elo_final'].keys())

    # ── Colonnes joueurs ──
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Joueur A")
        nom_a = st.text_input(
            "Nom du joueur A",
            placeholder="Ex: Djokovic, Nadal...",
            key="nom_a"
        )
        joueur_a = None
        if nom_a:
            suggestions_a = recherche_floue(nom_a, liste_joueurs)
            if suggestions_a:
                options_a = [
                    f"{j} (similarité {s:.0f}%)"
                    for j, s in suggestions_a
                ] + ["❌ Aucun de ces joueurs — aller dans Joueurs"]
                choix_a  = st.selectbox(
                    "Sélectionne le joueur A",
                    options_a, key="choix_a"
                )
                if choix_a == "❌ Aucun de ces joueurs — aller dans Joueurs":
                    joueur_a = None
                    st.markdown("---")
                    st.markdown(f"### ➕ Ajouter **{nom_a}** à la base")
                    onglet_api_a, onglet_csv_a = st.tabs(["🌐 Via API", "📁 Via CSV"])
                    with onglet_api_a:
                        if st.button("🔍 Rechercher via API", key="api_a"):
                            from modules.joueurs import ajouter_joueur_api
                            with st.spinner("Recherche en cours..."):
                                matchs_api = ajouter_joueur_api(nom_a)
                            if matchs_api:
                                nouveaux = []
                                for m in matchs_api:
                                    nouveaux.append({
                                        "winner_name": m.get("event_first_player", ""),
                                        "loser_name": m.get("event_second_player", ""),
                                        "surface": m.get("event_ground", "Hard"),
                                        "tourney_name": m.get("league_name", "Unknown"),
                                        "tourney_date": m.get("event_date", "2026-01-01"),
                                        "score": m.get("event_final_result", ""),
                                        "round": m.get("event_round", "R32"),
                                        "winner_rank": m.get("first_player_rank", 500),
                                        "loser_rank": m.get("second_player_rank", 500),
                                    })
                                from modules.mise_a_jour import mise_a_jour_incrementale
                                import pandas as pd
                                modeles = mise_a_jour_incrementale(modeles, nouveaux)
                                df_new = pd.DataFrame(nouveaux)
                                if st.session_state.get("df_base") is not None:
                                    st.session_state["df_base"] = pd.concat([st.session_state["df_base"], df_new], ignore_index=True)
                                st.session_state["modeles"] = modeles
                                st.success(f"✅ {nom_a} ajouté avec {len(nouveaux)} matchs !")
                                st.rerun()
                            else:
                                st.error(f"❌ {nom_a} non trouvé via API")
                    with onglet_csv_a:
                        st.info("""📋 **Format CSV requis :**
Colonnes : winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank
Exemple : Kouassi Ange, Djokovic N., Clay, Roland Garros, 2026-01-15, 6-3 6-4, R32, 450, 1
Surface : Hard / Clay / Grass | Date : YYYY-MM-DD | Round : R32/QF/SF/F | Rank : 500 si inconnu""")
                        fichier_a = st.file_uploader("📁 Upload CSV joueur A", type=["csv"], key="csv_a")
                        if fichier_a:
                            import pandas as pd
                            df_up = pd.read_csv(fichier_a)
                            nouveaux = df_up.to_dict("records")
                            from modules.mise_a_jour import mise_a_jour_incrementale
                            modeles = mise_a_jour_incrementale(modeles, nouveaux)
                            if st.session_state.get("df_base") is not None:
                                st.session_state["df_base"] = pd.concat([st.session_state["df_base"], df_up], ignore_index=True)
                            st.session_state["modeles"] = modeles
                            st.success(f"✅ {nom_a} ajouté avec {len(nouveaux)} matchs !")
                            st.rerun()
                    st.markdown("---")
                else:
                    joueur_a = suggestions_a[
                        options_a.index(choix_a)
                    ][0]
                    elo_a = modeles['elo_final'].get(joueur_a, 1500)
                    st.info(f"ELO : **{round(elo_a)}**")
            else:
                st.warning(
                    f"⚠️ '{nom_a}' introuvable — "
                    "va dans l'onglet 👤 Joueurs pour l'ajouter"
                )

    with col2:
        st.subheader("Joueur B")
        nom_b = st.text_input(
            "Nom du joueur B",
            placeholder="Ex: Alcaraz, Sinner...",
            key="nom_b"
        )
        joueur_b = None
        if nom_b:
            suggestions_b = recherche_floue(nom_b, liste_joueurs)
            if suggestions_b:
                options_b = [
                    f"{j} (similarité {s:.0f}%)"
                    for j, s in suggestions_b
                ] + ["❌ Aucun de ces joueurs — aller dans Joueurs"]
                choix_b  = st.selectbox(
                    "Sélectionne le joueur B",
                    options_b, key="choix_b"
                )
                if choix_b == "❌ Aucun de ces joueurs — aller dans Joueurs":
                    joueur_b = None
                    st.markdown("---")
                    st.markdown(f"### ➕ Ajouter **{nom_b}** à la base")
                    onglet_api_b, onglet_csv_b = st.tabs(["🌐 Via API", "📁 Via CSV"])
                    with onglet_api_b:
                        if st.button("🔍 Rechercher via API", key="api_b"):
                            from modules.joueurs import ajouter_joueur_api
                            with st.spinner("Recherche en cours..."):
                                matchs_api = ajouter_joueur_api(nom_b)
                            if matchs_api:
                                nouveaux = []
                                for m in matchs_api:
                                    nouveaux.append({
                                        "winner_name": m.get("event_first_player", ""),
                                        "loser_name": m.get("event_second_player", ""),
                                        "surface": m.get("event_ground", "Hard"),
                                        "tourney_name": m.get("league_name", "Unknown"),
                                        "tourney_date": m.get("event_date", "2026-01-01"),
                                        "score": m.get("event_final_result", ""),
                                        "round": m.get("event_round", "R32"),
                                        "winner_rank": m.get("first_player_rank", 500),
                                        "loser_rank": m.get("second_player_rank", 500),
                                    })
                                from modules.mise_a_jour import mise_a_jour_incrementale
                                import pandas as pd
                                modeles = mise_a_jour_incrementale(modeles, nouveaux)
                                df_new = pd.DataFrame(nouveaux)
                                if st.session_state.get("df_base") is not None:
                                    st.session_state["df_base"] = pd.concat([st.session_state["df_base"], df_new], ignore_index=True)
                                st.session_state["modeles"] = modeles
                                st.success(f"✅ {nom_b} ajouté avec {len(nouveaux)} matchs !")
                                st.rerun()
                            else:
                                st.error(f"❌ {nom_b} non trouvé via API")
                    with onglet_csv_b:
                        st.info("""📋 **Format CSV requis :**
Colonnes : winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank
Exemple : Kouassi Ange, Djokovic N., Clay, Roland Garros, 2026-01-15, 6-3 6-4, R32, 450, 1
Surface : Hard / Clay / Grass | Date : YYYY-MM-DD | Round : R32/QF/SF/F | Rank : 500 si inconnu""")
                        fichier_b = st.file_uploader("📁 Upload CSV joueur B", type=["csv"], key="csv_b")
                        if fichier_b:
                            import pandas as pd
                            df_up = pd.read_csv(fichier_b)
                            nouveaux = df_up.to_dict("records")
                            from modules.mise_a_jour import mise_a_jour_incrementale
                            modeles = mise_a_jour_incrementale(modeles, nouveaux)
                            if st.session_state.get("df_base") is not None:
                                st.session_state["df_base"] = pd.concat([st.session_state["df_base"], df_up], ignore_index=True)
                            st.session_state["modeles"] = modeles
                            st.success(f"✅ {nom_b} ajouté avec {len(nouveaux)} matchs !")
                            st.rerun()
                    st.markdown("---")
                else:
                    joueur_b = suggestions_b[
                        options_b.index(choix_b)
                    ][0]
                    elo_b = modeles['elo_final'].get(joueur_b, 1500)
                    st.info(f"ELO : **{round(elo_b)}**")
            else:
                st.warning(
                    f"⚠️ '{nom_b}' introuvable — "
                    "va dans l'onglet 👤 Joueurs pour l'ajouter"
                )

    st.markdown("---")

    # ── Paramètres match ──
    col3, col4, col5, col6 = st.columns(4)

    with col3:
        surface = st.selectbox(
            "🎾 Surface",
            ["Hard", "Clay", "Grass", "Carpet", "Hard (Indoor)"],
            help="Hard=Dur · Clay=Terre battue · Grass=Gazon"
        )
    with col4:
        tournoi = st.selectbox(
            "🏆 Circuit",
            ["ATP", "WTA", "Challenger", "ITF", "Futures"],
            help="Sélectionne le circuit du tournoi"
        )
    with col5:
        round_match = st.selectbox(
            "🔢 Tour",
            ["R128", "R64", "R32", "R16", "QF", "SF", "F"],
            help="R32=3ème tour · QF=Quart · SF=Demi · F=Finale"
        )
    with col6:
        best_of = st.selectbox(
            "📋 Format",
            [3, 5],
            format_func=lambda x:
                f"Best of {x} "
                f"({'GC/Davis' if x==5 else 'Standard'})",
            help="Best of 3 = max 3 sets · Best of 5 = max 5 sets (Grands Chelems)"
        )

    st.markdown("---")

    # ── Cotes bookmakers ──
    st.subheader("💰 Cotes bookmakers (optionnel)")
    st.caption(
        "Entre les cotes de ton bookmaker pour détecter "
        "les value bets"
    )
    col7, col8, col9 = st.columns([2, 2, 1])

    with col7:
        cote_a = st.number_input(
            f"Cote {joueur_a if joueur_a else 'Joueur A'}",
            min_value=1.01, max_value=50.0,
            value=2.00, step=0.05, key="cote_a"
        )
    with col8:
        cote_b = st.number_input(
            f"Cote {joueur_b if joueur_b else 'Joueur B'}",
            min_value=1.01, max_value=50.0,
            value=2.00, step=0.05, key="cote_b"
        )
    with col9:
        st.markdown("<br>", unsafe_allow_html=True)
        utiliser_cotes = st.checkbox(
            "Activer", value=False,
            help="Coche pour utiliser les cotes"
        )

    st.markdown("---")

    # ── Bouton prédiction ──
    if st.button(
        "🔮 Lancer la prédiction",
        type="primary"
    ):
        if not joueur_a or not joueur_b:
            st.error(
                "❌ Sélectionne les deux joueurs ! "
                "Si un joueur est introuvable, "
                "va dans l'onglet 👤 Joueurs pour l'ajouter."
            )
        elif joueur_a == joueur_b:
            st.error("❌ Les deux joueurs doivent être différents !")
        else:
            from modules.auth import peut_faire_prediction, incrementer_compteur_predictions
            peut, message = peut_faire_prediction()
            if not peut:
                st.error(f"🔒 {message}")
                st.stop()
            with st.spinner("⏳ Calcul en cours..."):
                res = predire_match(
                    joueur_a, joueur_b,
                    modeles, df_base,
                    surface     = surface,
                    tournoi     = tournoi,
                    round_match = round_match,
                    best_of     = best_of,
                    cote_a = cote_a if utiliser_cotes else None,
                    cote_b = cote_b if utiliser_cotes else None,
                )

            incrementer_compteur_predictions()
            st.success("✅ Prédiction calculée !")

            # ── Zone Copier ──
            texte_copie = (
                f"🎾 TENNIS IA - Prediction\n"
                f"Match : {joueur_a} vs {joueur_b}\n"
                f"Surface : {surface} | Tournoi : {tournoi}\n"
                f"---------------------\n"
                f"Vainqueur : {res['vainqueur']} ({res['proba_v']}%)\n"
                f"Score exact : {res['score_exact']}\n"
                f"Nombre de sets : {res['nb_sets']}\n"
                f"Handicap : {res['handicap']} set(s)\n"
                f"---------------------\n"
                f"ELO : {joueur_a} {res['elo_a']} | {joueur_b} {res['elo_b']}\n"
                f"Forme : {joueur_a} {res['forme_a']}% | {joueur_b} {res['forme_b']}%\n"
                f"H2H : {joueur_a} {res['h2h_a']} | {joueur_b} {res['h2h_b']}"
            )
            st.markdown("**📋 Copier la prédiction :**")
            st.code(texte_copie, language=None)

            st.markdown("---")

            # ── Résultats ──
            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            with col_v1:
                st.metric(
                    "🏆 Vainqueur prédit",
                    res['vainqueur'],
                    f"{res['proba_v']}%"
                )
            with col_v2:
                st.metric("🎯 Score exact", res['score_exact'])
            with col_v3:
                st.metric(
                    "🔢 Nombre de sets",
                    f"{res['nb_sets']} sets"
                )
            with col_v4:
                st.metric(
                    "⚖️ Handicap",
                    f"{res['handicap']} set(s)"
                )

            st.markdown("---")

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown("**📊 Statistiques comparées**")
                stats_df = pd.DataFrame({
                    'Statistique' : [
                        'ELO général',
                        f'ELO {surface}',
                        'Forme récente',
                        'H2H (victoires)',
                        'Classement',
                    ],
                    joueur_a : [
                        res['elo_a'],
                        res['elo_a_surf'],
                        f"{res['forme_a']}%",
                        res['h2h_a'],
                        f"#{res['rank_a']}",
                    ],
                    joueur_b : [
                        res['elo_b'],
                        res['elo_b_surf'],
                        f"{res['forme_b']}%",
                        res['h2h_b'],
                        f"#{res['rank_b']}",
                    ]
                })
                st.dataframe(
                    stats_df, hide_index=True,
                    use_container_width=True
                )

            with col_d2:
                st.markdown("**🎯 Probabilités**")
                import plotly.graph_objects as go
                fig = go.Figure(go.Bar(
                    x=[joueur_a, joueur_b],
                    y=[res['proba_a'], res['proba_b']],
                    marker_color=['#2d9e56', '#FF5722'],
                    text=[
                        f"{res['proba_a']}%",
                        f"{res['proba_b']}%"
                    ],
                    textposition='auto',
                ))
                fig.update_layout(
                    yaxis_title="Probabilité (%)",
                    yaxis_range=[0, 100],
                    height=300,
                    margin=dict(t=20),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Value bet
            if res['value_bet_info']:
                info = res['value_bet_info']
                st.success(
                    f"💰 VALUE BET détecté sur "
                    f"**{info['joueur']}** "
                    f"— cote {info['cote']} "
                    f"— valeur **+{info['valeur']}%**"
                )
            elif utiliser_cotes:
                st.info("❌ Pas de value bet détecté")

            # Sauvegarde
            sauvegarder_prediction(res)
            st.caption(
                f"✅ Prédiction sauvegardée — {res['date']}"
            )

# ============================================================
# SAUVEGARDE HISTORIQUE
# ============================================================
def sauvegarder_prediction(res):
    fichier = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'historique.json'
    )
    historique = []
    if os.path.exists(fichier):
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                historique = json.load(f)
        except:
            historique = []

    # Conversion pour JSON
    res_json = {}
    for k, v in res.items():
        try:
            if isinstance(v, (np.integer,)): res_json[k] = int(v)
            elif isinstance(v, (np.floating,)): res_json[k] = float(v)
            else: res_json[k] = v
        except:
            res_json[k] = str(v)

    historique.append(res_json)
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)