
SURFACE_TOURNOI = {
    # Hard
    "miami": "Hard", "australian open": "Hard", "us open": "Hard",
    "indian wells": "Hard", "cincinnati": "Hard", "montreal": "Hard",
    "toronto": "Hard", "madrid": "Hard", "dubai": "Hard",
    "doha": "Hard", "brisbane": "Hard", "auckland": "Hard",
    "beijing": "Hard", "shanghai": "Hard", "paris": "Hard",
    "vienna": "Hard", "basel": "Hard", "tokyo": "Hard",
    "washington": "Hard", "atlanta": "Hard", "los angeles": "Hard",
    # Clay
    "roland garros": "Clay", "monte carlo": "Clay", "barcelona": "Clay",
    "rome": "Clay", "hamburg": "Clay", "bucharest": "Clay",
    "estoril": "Clay", "munich": "Clay", "lyon": "Clay",
    "geneva": "Clay", "marrakech": "Clay", "casablanca": "Clay",
    "istanbul": "Clay", "bastad": "Clay", "gstaad": "Clay",
    "umag": "Clay", "kitzbuhel": "Clay", "winston-salem": "Clay",
    "roland": "Clay", "garros": "Clay",
    # Grass
    "wimbledon": "Grass", "halle": "Grass", "queens": "Grass",
    "eastbourne": "Grass", "s-hertogenbosch": "Grass", "nottingham": "Grass",
    "newport": "Grass", "mallorca": "Grass",
}

def detecter_surface(nom_tournoi):
    nom = str(nom_tournoi).lower()
    for mot, surface in SURFACE_TOURNOI.items():
        if mot in nom:
            return surface
    return "Hard"

# v2 - groupes par tournoi
# ============================================================
# MODULE MATCHS DU JOUR
# ============================================================
import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
BASE_URL = "https://apiv2.allsportsapi.com/tennis/"

# ── Rotation intelligente multi-clés API ──
from modules.api_rotation import appel_api

# ============================================================
# DETECTION HORS-LIGNE
# ============================================================
def est_hors_ligne():
    try:
        import requests as _req
        _req.get("https://www.google.com", timeout=3)
        return False
    except Exception:
        return True

# ============================================================
# RECUPERATION MATCHS
# ============================================================
def get_matchs_periode(date_debut, date_fin, api_key=None):
    """Récupère les matchs via rotation intelligente de clés API + cache."""
    resultat = appel_api(
        {"met": "Fixtures", "from": date_debut, "to": date_fin},
        utiliser_cache=True
    )
    if resultat["source"] == "erreur":
        st.error(resultat["message"])
        return []
    if resultat["source"] in ("cache", "cache_expire"):
        st.caption(f"📦 {resultat['message']}")
    data = resultat.get("data") or {}
    if data.get("success") == 1:
        return data.get("result", [])
    return []

# ============================================================
# TRAITEMENT MATCHS
# ============================================================
def traiter_matchs(matchs_raw, filtre_circuit="Tous", filtre_statut="Tous"):
    if not matchs_raw:
        return pd.DataFrame()
    rows = []
    for m in matchs_raw:
        statut   = str(m.get("event_status", "")).lower()
        circuit  = str(m.get("country_name", ""))
        joueur_a = str(m.get("event_first_player", ""))
        joueur_b = str(m.get("event_second_player", ""))
        if not joueur_a or not joueur_b:
            continue
        rows.append({
            "event_key" : str(m.get("event_key", "")),
            "Heure"     : str(m.get("event_time", "")),
            "Joueur A"  : joueur_a,
            "Joueur B"  : joueur_b,
            "Tournoi"   : str(m.get("league_name", "")),
            "Circuit"   : circuit,
            "Round"     : str(m.get("league_round", "")),
            "Score"     : str(m.get("event_final_result", "-")),
            "Statut"    : str(m.get("event_status", "")),
            "statut_low": statut,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if filtre_circuit != "Tous":
        df = df[df["Circuit"].str.contains(filtre_circuit, case=False, na=False)]
    if filtre_statut == "A venir":
        df = df[df["statut_low"].isin(["", "notstarted", "scheduled", "ns"])]
    elif filtre_statut == "En cours":
        df = df[df["statut_low"].isin(["inprogress", "live", "1st", "2nd", "3rd"])]
    elif filtre_statut == "Termines":
        df = df[df["statut_low"] == "finished"]
    return df.reset_index(drop=True)

# ============================================================
# RECHERCHE NOM DANS LA BASE
# ============================================================
def trouver_nom_base(nom, liste_joueurs):
    if "/" in nom:
        return None
    try:
        from rapidfuzz import process, fuzz
        resultats = process.extract(nom, liste_joueurs, scorer=fuzz.WRatio, limit=1)
        if resultats and resultats[0][1] >= 60:
            return resultats[0][0]
    except:
        pass
    return None

# ============================================================
# AFFICHAGE RESULTAT PREDICTION
# ============================================================
def afficher_resultat_pred(res, j_a, j_b, surface):
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Vainqueur", res["vainqueur"], f"{res['proba_v']}%")
    with c2: st.metric("Score", res["score_exact"])
    with c3: st.metric("Sets", f"{res['nb_sets']} sets")
    with c4: st.metric("Handicap", f"{res['handicap']} set(s)")
    stats = pd.DataFrame({
        "Statistique": ["ELO general", f"ELO {surface}", "Forme", "H2H", "Classement"],
        j_a: [res["elo_a"], res["elo_a_surf"], f"{res['forme_a']}%", res["h2h_a"], f"#{res['rank_a']}"],
        j_b: [res["elo_b"], res["elo_b_surf"], f"{res['forme_b']}%", res["h2h_b"], f"#{res['rank_b']}"],
    })
    st.dataframe(stats, hide_index=True, use_container_width=True)
    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=[j_a, j_b], y=[res["proba_a"], res["proba_b"]],
        marker_color=["#2d9e56", "#FF5722"],
        text=[f"{res['proba_a']}%", f"{res['proba_b']}%"],
        textposition="auto",
    ))
    fig.update_layout(yaxis_range=[0,100], height=250,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE MATCHS DU JOUR
# ============================================================
def page_matchs_jour(modeles, df_base):
    st.title("Matchs du jour")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        date_choisie = st.date_input("Date", value=datetime.now().date())
    with col2:
        filtre_circuit = st.selectbox("Circuit", ["Tous", "ATP", "WTA", "Challenger", "ITF", "Futures"])
    with col3:
        filtre_statut = st.selectbox("Statut", ["Tous", "A venir", "En cours", "Termines"])
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        charger = st.button("Charger", type="primary")

    predire_tous = st.button("Predire TOUS les matchs automatiquement")
    st.markdown("---")

    if charger or predire_tous or st.session_state.get("auto_charger"):
        st.session_state["auto_charger"] = False
        date_str     = str(date_choisie)
        date_str_fin = str(date_choisie + timedelta(days=1))

        if est_hors_ligne():
            st.warning("Mode hors-ligne - Matchs non disponibles.")
            return

        with st.spinner("Chargement des matchs..."):
            matchs_raw = get_matchs_periode(date_str, date_str)
            if not matchs_raw:
                matchs_raw = get_matchs_periode(date_str, date_str_fin)

        df_matchs = traiter_matchs(matchs_raw, filtre_circuit, filtre_statut)
        if df_matchs.empty:
            st.warning("Aucun match trouve.")
            return

        # Sauvegarder dans session_state pour persistance
        st.session_state["df_matchs_jour"] = df_matchs
        st.session_state["date_matchs"] = date_str

    # Lire depuis session_state
    if "df_matchs_jour" not in st.session_state:
        st.info("Cliquez sur Charger pour voir les matchs.")
        return

    df_matchs = st.session_state["df_matchs_jour"]
    date_str  = st.session_state.get("date_matchs", str(date_choisie))

    total    = len(df_matchs)
    termines = len(df_matchs[df_matchs["statut_low"] == "finished"])
    en_cours = len(df_matchs[df_matchs["statut_low"].isin(["inprogress","live"])])
    a_venir  = total - termines - en_cours

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total",    total)
    with c2: st.metric("A venir",  a_venir)
    with c3: st.metric("En cours", en_cours)
    with c4: st.metric("Termines", termines)
    st.markdown("---")

    liste_joueurs = list(modeles["elo_final"].keys())

    if "pred_resultats" not in st.session_state:
        st.session_state["pred_resultats"] = {}

    # ── Predire TOUS ──
    if predire_tous:
        st.subheader("Predictions automatiques")
        from modules.prediction import predire_match
        a_predire = df_matchs[~df_matchs["statut_low"].isin(["finished"])].head(30)
        if a_predire.empty:
            st.info("Aucun match a venir.")
        else:
            barre = st.progress(0)
            resultats = []
            for i, (_, match) in enumerate(a_predire.iterrows()):
                j_a_raw = match["Joueur A"]
                j_b_raw = match["Joueur B"]
                if "/" in j_a_raw or "/" in j_b_raw:
                    continue
                j_a = trouver_nom_base(j_a_raw, liste_joueurs) or j_a_raw
                j_b = trouver_nom_base(j_b_raw, liste_joueurs) or j_b_raw
                circ = match["Circuit"].upper()
                t = "WTA" if "WTA" in circ else "Challenger" if "CHALLENGER" in circ else "ITF" if "ITF" in circ else "ATP"
                try:
                    res = predire_match(j_a, j_b, modeles, df_base, surface=detecter_surface(t), tournoi=t)
                    resultats.append({
                        "Joueur A": j_a_raw, "Joueur B": j_b_raw,
                        "Tournoi": match["Tournoi"], "Vainqueur IA": res["vainqueur"],
                        "Probabilite": f"{res['proba_v']}%", "Score predit": res["score_exact"],
                        "Sets": res["nb_sets"], "Handicap": res["handicap"],
                    })
                except:
                    resultats.append({
                        "Joueur A": j_a_raw, "Joueur B": j_b_raw,
                        "Tournoi": match["Tournoi"], "Vainqueur IA": "N/A",
                        "Probabilite": "N/A", "Score predit": "N/A", "Sets": "N/A", "Handicap": "N/A",
                    })
                barre.progress((i+1)/len(a_predire))
            df_res = pd.DataFrame(resultats)
            st.success(f"{len(df_res)} predictions calculees !")
            st.dataframe(df_res, hide_index=True, use_container_width=True)
            csv = df_res.to_csv(index=False)
            st.download_button("Telecharger CSV", data=csv,
                file_name=f"predictions_{date_str}.csv", mime="text/csv")
        st.markdown("---")

    # ── Matchs EN COURS ──
    df_en_cours = df_matchs[df_matchs["statut_low"].isin(["inprogress","live"])]
    if not df_en_cours.empty:
        st.subheader(f"En cours ({len(df_en_cours)})")
        st.dataframe(df_en_cours[["Heure","Joueur A","Joueur B","Tournoi","Circuit","Score"]],
            hide_index=True, use_container_width=True)
        st.markdown("---")

    # ── Matchs TERMINES ──
    df_termines = df_matchs[df_matchs["statut_low"] == "finished"]
    if not df_termines.empty:
        st.subheader(f"Termines ({len(df_termines)})")
        st.dataframe(df_termines[["Heure","Joueur A","Joueur B","Tournoi","Circuit","Score"]],
            hide_index=True, use_container_width=True)
        st.markdown("---")

    # ── Matchs A VENIR groupes par tournoi ──
    df_a_venir = df_matchs[df_matchs["statut_low"].isin(["","notstarted","scheduled","ns"])]
    if not df_a_venir.empty:
        st.subheader(f"A venir ({len(df_a_venir)})")
        from modules.prediction import predire_match

        tournois = df_a_venir["Tournoi"].unique()
        for tournoi in tournois:
            df_t = df_a_venir[df_a_venir["Tournoi"] == tournoi].reset_index(drop=True)
            circuit = df_t.iloc[0]["Circuit"]
            with st.expander(f"{tournoi} — {circuit} ({len(df_t)} matchs)"):
                for i, (_, match) in enumerate(df_t.iterrows()):
                    j_a_raw   = match["Joueur A"]
                    j_b_raw   = match["Joueur B"]
                    event_key = match["event_key"]

                    # Ignorer doubles
                    if "/" in j_a_raw or "/" in j_b_raw:
                        continue

                    circ = match["Circuit"].upper()
                    t = "WTA" if "WTA" in circ else "Challenger" if "CHALLENGER" in circ else "ITF" if "ITF" in circ else "ATP"

                    col_h, col_a, col_vs, col_b, col_btn = st.columns([1, 3, 0.5, 3, 2])
                    with col_h:   st.markdown(f"**{match['Heure']}**")
                    with col_a:   st.markdown(f"{j_a_raw}")
                    with col_vs:  st.markdown("**vs**")
                    with col_b:   st.markdown(f"{j_b_raw}")
                    with col_btn:
                        if st.button("Predire", key=f"pred_{event_key}_{i}"):
                            j_a = trouver_nom_base(j_a_raw, liste_joueurs) or j_a_raw
                            j_b = trouver_nom_base(j_b_raw, liste_joueurs) or j_b_raw
                            try:
                                res = predire_match(j_a, j_b, modeles, df_base,
                                    surface="Hard", tournoi=t, round_match=str(match["Round"]))
                                st.session_state["pred_resultats"][event_key] = {
                                    "res": res, "j_a": j_a, "j_b": j_b,
                                    "j_a_raw": j_a_raw, "j_b_raw": j_b_raw
                                }
                            except Exception as e:
                                st.session_state["pred_resultats"][event_key] = {"erreur": str(e)}

                    # Afficher resultat si disponible
                    if event_key in st.session_state["pred_resultats"]:
                        data = st.session_state["pred_resultats"][event_key]
                        if "erreur" in data:
                            st.error(f"Erreur : {data['erreur']}")
                        else:
                            st.success(f"Vainqueur : {data['res']['vainqueur']} ({data['res']['proba_v']}%) | Score : {data['res']['score_exact']} | Sets : {data['res']['nb_sets']}")
                            afficher_resultat_pred(data["res"], data["j_a"], data["j_b"], detecter_surface(data.get("tournoi", "")))
                        st.info("💡 Pour une prediction plus precise, utilisez l'onglet Prediction avec toutes les donnees : surface exacte, round, format et cotes du match.")
                    st.divider()
