# ============================================================
# MODULE JOUEURS
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY  = os.getenv("ALLSPORTS_API_KEY")
BASE_URL = "https://apiv2.allsportsapi.com/tennis/"

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

# ============================================================
# RECHERCHE FLOUE
# ============================================================
def recherche_floue(nom, liste_joueurs, limite=8, seuil=55):
    if not nom or len(nom) < 2:
        return []
    resultats = process.extract(
        nom, liste_joueurs,
        scorer=fuzz.WRatio, limit=limite,
    )
    return [
        (j, s) for j, s, _ in resultats if s >= seuil
    ]

# ============================================================
# CLASSEMENT VIA API
# ============================================================
def get_rank_api(nom):
    try:
        res = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : API_KEY,
            "from"   : "2026-01-01",
            "to"     : "2026-03-18",
        }, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") == 1:
                nom_lower = nom.lower()
                for m in data.get("result", []):
                    p1 = str(m.get('event_first_player','') ).lower()
                    p2 = str(m.get('event_second_player','')).lower()
                    if nom_lower in p1:
                        r = safe_int(m.get('first_player_rank', 0))
                        if 0 < r < 2000: return r
                    if nom_lower in p2:
                        r = safe_int(m.get('second_player_rank', 0))
                        if 0 < r < 2000: return r
    except:
        pass
    return None

# ============================================================
# PROFIL JOUEUR
# ============================================================
def get_profil_joueur(nom, modeles, df_base):
    elo_final = modeles['elo_final']
    elo_surf  = modeles['elo_final_surf']
    forme     = modeles['forme_final']

    elo_general = elo_final.get(nom, 1500)
    elo_hard    = elo_surf.get('Hard',  {}).get(nom, 1500)
    elo_clay    = elo_surf.get('Clay',  {}).get(nom, 1500)
    elo_grass   = elo_surf.get('Grass', {}).get(nom, 1500)

    if df_base is not None:
        mask = (
            (df_base['winner_name'] == nom) |
            (df_base['loser_name']  == nom)
        )
        matchs = df_base[mask].copy()
        matchs['tourney_date'] = pd.to_datetime(
            matchs['tourney_date'], errors='coerce'
        )
        matchs = matchs.sort_values(
            'tourney_date', ascending=False
        ).reset_index(drop=True)
    else:
        matchs = pd.DataFrame()

    total_matchs = len(matchs)
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        victoires = len(matchs[matchs['winner_name'] == nom])
    else:
        victoires = 0
    pct_victoire = round(
        victoires / total_matchs * 100, 1
    ) if total_matchs > 0 else 0

    # Classement — cherche dans la base
    rank = 500
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        for _, row in matchs.head(30).iterrows():
            if row['winner_name'] == nom:
                r = safe_int(row.get('winner_rank', 0))
            else:
                r = safe_int(row.get('loser_rank', 0))
            if 0 < r < 500:
                rank = r
                break
    # Si toujours 500 → API
    if rank == 500:
        r_api = get_rank_api(nom)
        if r_api:
            rank = r_api

    # Pays
    pays = 'N/A'
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        for _, row in matchs.head(10).iterrows():
            if row['winner_name'] == nom:
                p = str(row.get('winner_ioc', '') or '')
            else:
                p = str(row.get('loser_ioc', '') or '')
            if p and p not in ['nan','None','NaN','']:
                pays = p
                break

    # 5 derniers matchs
    derniers = []
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        for _, row in matchs.head(5).iterrows():
            gagne      = row['winner_name'] == nom
            adversaire = row['loser_name'] if gagne else row['winner_name']
            derniers.append({
                'Date'      : str(row['tourney_date'])[:10]
                              if pd.notna(row['tourney_date']) else 'N/A',
                'Tournoi'   : str(row.get('tourney_name', 'N/A')),
                'Surface'   : str(row.get('surface', 'N/A')),
                'Round'     : str(row.get('round', 'N/A')),
                'Adversaire': str(adversaire),
                'Score'     : str(row.get('score', 'N/A')),
                'Résultat'  : '✅ Victoire' if gagne else '❌ Défaite',
            })

    # % victoires par surface
    def forme_surf(surf):
        if df_base is None or matchs.empty:
            return 0
        m_s = df_base[mask & (df_base['surface'] == surf)]
        if len(m_s) == 0: return 0
        return round(
            len(m_s[m_s['winner_name'] == nom]) / len(m_s) * 100, 1
        )

    return {
        'nom'         : nom,
        'elo_general' : round(elo_general),
        'elo_hard'    : round(elo_hard),
        'elo_clay'    : round(elo_clay),
        'elo_grass'   : round(elo_grass),
        'forme'       : round(forme.get(nom, 0.5) * 100, 1),
        'rank'        : rank,
        'pays'        : pays,
        'total_matchs': total_matchs,
        'victoires'   : victoires,
        'pct_victoire': pct_victoire,
        'hard_pct'    : forme_surf('Hard'),
        'clay_pct'    : forme_surf('Clay'),
        'grass_pct'   : forme_surf('Grass'),
        'derniers'    : derniers,
    }

# ============================================================
# AJOUT JOUEUR VIA API
# ============================================================
def ajouter_joueur_api(nom):
    try:
        res = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : API_KEY,
            "from"   : "2025-01-01",
            "to"     : "2026-03-18",
        }, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") == 1:
                nom_lower = nom.lower()
                trouves   = []
                for m in data.get("result", []):
                    p1 = str(m.get('event_first_player',  '')).lower()
                    p2 = str(m.get('event_second_player', '')).lower()
                    if nom_lower in p1 or nom_lower in p2:
                        trouves.append(m)
                return trouves[:10]
    except Exception as e:
        st.error(f"Erreur API : {e}")
    return []

# ============================================================
# PAGE JOUEURS
# ============================================================
def page_joueurs(modeles, df_base):
    st.title("👤 Profil Joueur")
    st.markdown("---")

    liste_joueurs = list(modeles['elo_final'].keys())

    col1, col2 = st.columns([3, 1])
    with col1:
        nom_recherche = st.text_input(
            "🔍 Recherche un joueur",
            placeholder="Ex: Djokovic, Swiatek, Alcaraz...",
            key="recherche_joueur"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        lancer = st.button(
            "Rechercher", type="primary",
        )

    if nom_recherche and lancer:
        suggestions = recherche_floue(nom_recherche, liste_joueurs)

        if suggestions:
            options    = [
                f"{j} (similarité {s:.0f}%)"
                for j, s in suggestions
            ]
            # Ajout option "Aucun de ces joueurs"
            options_avec_autre = options + ["❌ Aucun de ces joueurs — rechercher via API"]
            choix      = st.selectbox(
                "Sélectionne un joueur", options_avec_autre
            )

            # Si l'utilisateur choisit "Aucun de ces joueurs"
            if choix == "❌ Aucun de ces joueurs — rechercher via API":
                st.markdown("---")
                st.subheader(f"➕ Ajouter {nom_recherche} à la base")
                onglet_api2, onglet_csv2 = st.tabs(["🌐 Via API", "📁 Via CSV"])
                with onglet_api2:
                    if st.button("🔍 Rechercher via API", key="btn_api_from_similar"):
                        with st.spinner("Recherche en cours..."):
                            matchs_api = ajouter_joueur_api(nom_recherche)
                        if matchs_api:
                            st.session_state["matchs_api_similar"] = matchs_api
                            st.session_state["nom_api_similar"] = nom_recherche
                        else:
                            st.session_state["matchs_api_similar"] = []
                            st.error(f"❌ {nom_recherche} non trouvé via API")
                            st.warning("💡 Essayez l'onglet 📁 Via CSV")
                    if st.session_state.get("matchs_api_similar") and st.session_state.get("nom_api_similar") == nom_recherche:
                        matchs_api = st.session_state["matchs_api_similar"]
                        st.success(f"✅ {len(matchs_api)} matchs trouvés pour {nom_recherche} !")
                        for m in matchs_api[:5]:
                            st.write(f"• {m.get('event_date')} — {m.get('event_first_player')} vs {m.get('event_second_player')}")
                        if st.button("✅ Confirmer l'ajout à la base", key="confirmer_api2"):
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
                                modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                                st.session_state["modeles"] = modeles_maj
                                df_new = pd.DataFrame(nouveaux)
                                if df_base is not None:
                                    st.session_state["df_base"] = pd.concat([df_base, df_new], ignore_index=True)
                                st.success(f"✅ {nom_recherche} ajouté ! Tapez à nouveau son nom pour le trouver.")
                                st.session_state["matchs_api_similar"] = []
                        else:
                            st.error(f"❌ {nom_recherche} non trouvé via API")
                            st.warning("💡 Essayez l'onglet 📁 Via CSV")
                with onglet_csv2:
                    st.info("""📋 **Format CSV requis :**
Colonnes : winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank
Exemple : Kouassi Ange, Djokovic N., Clay, Roland Garros, 2026-01-15, 6-3 6-4, R32, 450, 1
Surface : Hard / Clay / Grass | Date : YYYY-MM-DD | Round : R32/QF/SF/F | Rank : 500 si inconnu""")
                    fichier_csv2 = st.file_uploader("📁 Upload CSV", type=["csv"], key="upload_joueur_similar")
                    if fichier_csv2:
                        df_up = pd.read_csv(fichier_csv2)
                        st.dataframe(df_up.head(5))
                        if st.button("✅ Confirmer l'ajout via CSV", key="confirmer_csv2"):
                            nouveaux = df_up.to_dict("records")
                            from modules.mise_a_jour import mise_a_jour_incrementale
                            modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                            st.session_state["modeles"] = modeles_maj
                            if df_base is not None:
                                st.session_state["df_base"] = pd.concat([df_base, df_up], ignore_index=True)
                            st.success(f"✅ {nom_recherche} ajouté avec {len(nouveaux)} matchs ! Tapez à nouveau son nom pour le trouver.")
                st.stop()

            joueur_sel = suggestions[options.index(choix)][0]

            with st.spinner("⏳ Chargement du profil..."):
                profil = get_profil_joueur(
                    joueur_sel, modeles, df_base
                )

            st.markdown("---")

            # ── En-tête ──
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            with col_p1:
                st.metric("👤 Joueur", profil['nom'])
            with col_p2:
                st.metric("🏅 Classement", f"#{profil['rank']}")
            with col_p3:
                st.metric("🌍 Pays", profil['pays'])
            with col_p4:
                st.metric("📈 Forme", f"{profil['forme']}%")

            # Barre progression forme
            st.markdown("**Forme récente (10 derniers matchs)**")
            st.progress(int(profil['forme']))

            st.markdown("---")

            # ── ELO ──
            st.subheader("⚡ Score ELO")
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
            with col_e1:
                st.metric("🎯 Général", profil['elo_general'])
            with col_e2:
                st.metric("🏟️ Hard",    profil['elo_hard'])
            with col_e3:
                st.metric("🌱 Clay",    profil['elo_clay'])
            with col_e4:
                st.metric("🌿 Grass",   profil['elo_grass'])

            # Graphique ELO par surface
            import plotly.graph_objects as go
            fig_elo = go.Figure(go.Bar(
                x=['Général','Hard','Clay','Grass'],
                y=[
                    profil['elo_general'],
                    profil['elo_hard'],
                    profil['elo_clay'],
                    profil['elo_grass'],
                ],
                marker_color=['#2d9e56','#2196F3','#FF5722','#4CAF50'],
                text=[
                    profil['elo_general'],
                    profil['elo_hard'],
                    profil['elo_clay'],
                    profil['elo_grass'],
                ],
                textposition='outside',
            ))
            fig_elo.update_layout(
                height=280,
                yaxis_range=[1400, max(
                    profil['elo_general'],
                    profil['elo_hard'],
                    profil['elo_clay'],
                    profil['elo_grass'],
                ) + 100],
                margin=dict(t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            )
            st.plotly_chart(fig_elo, use_container_width=True)

            st.markdown("---")

            # ── Stats globales ──
            st.subheader("📊 Statistiques globales")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric(
                    "🎾 Total matchs",
                    f"{profil['total_matchs']:,}"
                )
            with col_s2:
                st.metric(
                    "✅ % Victoires",
                    f"{profil['pct_victoire']}%"
                )
            with col_s3:
                st.metric(
                    "Surfaces H / C / G",
                    f"{profil['hard_pct']}% / "
                    f"{profil['clay_pct']}% / "
                    f"{profil['grass_pct']}%"
                )

            st.markdown("---")

            # ── 5 derniers matchs ──
            st.subheader("📋 5 derniers matchs")
            if profil['derniers']:
                st.dataframe(
                    pd.DataFrame(profil['derniers']),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Aucun match trouvé")

            st.markdown("---")

            # ── H2H ──
            st.subheader("🤝 Face à face")
            nom_adv = st.text_input(
                "Recherche un adversaire",
                placeholder="Ex: Nadal, Federer...",
                key="h2h_adversaire"
            )
            if nom_adv:
                sugg_adv = recherche_floue(nom_adv, liste_joueurs)
                if sugg_adv:
                    opts_adv  = [
                        f"{j} (similarité {s:.0f}%)"
                        for j, s in sugg_adv
                    ]
                    choix_adv  = st.selectbox(
                        "Sélectionne l'adversaire",
                        opts_adv, key="choix_adv"
                    )
                    adversaire = sugg_adv[
                        opts_adv.index(choix_adv)
                    ][0]

                    if df_base is None:
                        st.warning("⚠️ BASE_FEATURES.csv non disponible — H2H indisponible")
                        return
                    mask_h2h = (
                        ((df_base['winner_name'] == joueur_sel) &
                         (df_base['loser_name']  == adversaire)) |
                        ((df_base['winner_name'] == adversaire) &
                         (df_base['loser_name']  == joueur_sel))
                    )
                    h2h = df_base[mask_h2h].copy()
                    h2h['tourney_date'] = pd.to_datetime(
                        h2h['tourney_date'], errors='coerce'
                    )
                    h2h     = h2h.sort_values(
                        'tourney_date', ascending=False
                    )
                    total_h = len(h2h)
                    wins_h  = len(
                        h2h[h2h['winner_name'] == joueur_sel]
                    )

                    if total_h > 0:
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.metric("Total matchs", total_h)
                        with c2:
                            st.metric(
                                f"✅ {joueur_sel[:15]}",
                                wins_h
                            )
                        with c3:
                            st.metric(
                                f"✅ {adversaire[:15]}",
                                total_h - wins_h
                            )
                        rows_h = []
                        for _, row in h2h.iterrows():
                            rows_h.append({
                                'Date'     : str(row['tourney_date'])[:10],
                                'Tournoi'  : str(row.get('tourney_name','N/A')),
                                'Surface'  : str(row.get('surface','N/A')),
                                'Score'    : str(row.get('score','N/A')),
                                'Vainqueur': str(row['winner_name']),
                            })
                        st.dataframe(
                            pd.DataFrame(rows_h),
                            hide_index=True,
                            use_container_width=True,
                        )
                    else:
                        st.info(
                            f"Aucun match entre "
                            f"{joueur_sel} et {adversaire}"
                        )
                else:
                    st.warning("Adversaire non trouvé")

        else:
            st.warning(f"⚠️ '{nom_recherche}' introuvable dans la base")
            st.markdown("---")
            st.subheader("➕ Ajouter ce joueur")
            onglet_api, onglet_csv = st.tabs(["🌐 Via API", "📁 Via CSV"])

            with onglet_api:
                if st.button("🔍 Rechercher via API", key="btn_api_joueur"):
                    with st.spinner("Recherche en cours..."):
                        matchs_api = ajouter_joueur_api(nom_recherche)
                    if matchs_api:
                        st.success(f"✅ {len(matchs_api)} matchs trouvés pour {nom_recherche} !")
                        for m in matchs_api[:5]:
                            st.write(
                                f"• {m.get('event_date')} — "
                                f"{m.get('event_first_player')} vs "
                                f"{m.get('event_second_player')}"
                            )
                        if st.button("✅ Confirmer l'ajout à la base", key="confirmer_api"):
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
                            modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                            st.session_state["modeles"] = modeles_maj
                            df_new = pd.DataFrame(nouveaux)
                            if df_base is not None:
                                st.session_state["df_base"] = pd.concat([df_base, df_new], ignore_index=True)
                            st.success(f"✅ {nom_recherche} ajouté avec succès ! Relancez la recherche.")
                    else:
                        st.error(f"❌ {nom_recherche} non trouvé via API")
                        st.markdown("---")
                        st.warning("💡 Essayez d'ajouter le joueur via CSV dans l'onglet 📁 Via CSV")

            with onglet_csv:
                st.info("""📋 **Format CSV requis :**
Colonnes : winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank
Exemple : Kouassi Ange, Djokovic N., Clay, Roland Garros, 2026-01-15, 6-3 6-4, R32, 450, 1
Surface : Hard / Clay / Grass | Date : YYYY-MM-DD | Round : R32/QF/SF/F | Rank : 500 si inconnu""")
                fichier_csv = st.file_uploader("📁 Upload CSV du joueur", type=["csv"], key="upload_joueur")
                if fichier_csv:
                    df_up = pd.read_csv(fichier_csv)
                    st.dataframe(df_up.head(5))
                    if st.button("✅ Confirmer l'ajout via CSV", key="confirmer_csv"):
                        nouveaux = df_up.to_dict("records")
                        from modules.mise_a_jour import mise_a_jour_incrementale
                        modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                        st.session_state["modeles"] = modeles_maj
                        if df_base is not None:
                            st.session_state["df_base"] = pd.concat([df_base, df_up], ignore_index=True)
                        st.success(f"✅ {nom_recherche} ajouté avec {len(nouveaux)} matchs ! Relancez la recherche.")