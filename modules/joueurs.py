# ============================================================
# MODULE JOUEURS — VERSION CORRIGÉE v2
# Correction Bug #4 : gestion joueurs.csv + affichage erreurs
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from rapidfuzz import process, fuzz
import requests
import os
from dotenv import load_dotenv
import config as cfg

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
    except (ValueError, TypeError):
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
# JOINTURE FLOUE AVEC joueurs.csv
# ============================================================
def trouver_joueur_csv(nom, df_joueurs, seuil=70):
    """
    Cherche un joueur dans df_joueurs (joueurs.csv) via correspondance
    floue sur nom_complet. Retourne la ligne pandas (Series) ou None.
    """
    if df_joueurs is None or df_joueurs.empty:
        return None
    if 'nom_complet' not in df_joueurs.columns:
        return None
    noms_csv = df_joueurs['nom_complet'].dropna().tolist()
    if not noms_csv:
        return None
    resultats = process.extract(
        nom, noms_csv, scorer=fuzz.WRatio, limit=1
    )
    if resultats and resultats[0][1] >= seuil:
        nom_trouve = resultats[0][0]
        ligne = df_joueurs[df_joueurs['nom_complet'] == nom_trouve]
        if not ligne.empty:
            return ligne.iloc[0]
    return None

def safe_get(series, key, default=None):
    """Extrait une valeur d'une Series pandas de manière sécurisée."""
    try:
        if key in series.index:
            val = series[key]
            if pd.notna(val):
                return val
        return default
    except Exception:
        return default

# ============================================================
# CLASSEMENT VIA API
# ============================================================
def get_rank_api(nom):
    try:
        from datetime import datetime, timedelta
        today = datetime.now()
        date_fin   = today.strftime("%Y-%m-%d")
        date_debut = (today - timedelta(days=120)).strftime("%Y-%m-%d")
        res = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : API_KEY,
            "from"   : date_debut,
            "to"     : date_fin,
        }, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") == 1:
                nom_lower = nom.lower()
                for m in data.get("result", []):
                    p1 = str(m.get('event_first_player','')).lower()
                    p2 = str(m.get('event_second_player','')).lower()
                    if nom_lower in p1:
                        r = safe_int(m.get('first_player_rank', 0))
                        if 0 < r < 2000: return r
                    if nom_lower in p2:
                        r = safe_int(m.get('second_player_rank', 0))
                        if 0 < r < 2000: return r
    except Exception:
        pass
    return None

# ============================================================
# PROFIL JOUEUR
# ============================================================
def get_profil_joueur(nom, modeles, df_base, df_joueurs=None):
    elo_final = modeles['elo_final']
    elo_surf  = modeles['elo_final_surf']
    forme     = modeles['forme_final']

    elo_general = elo_final.get(nom, 1500)
    elo_hard    = elo_surf.get('Hard',  {}).get(nom, 1500)
    elo_clay    = elo_surf.get('Clay',  {}).get(nom, 1500)
    elo_grass   = elo_surf.get('Grass', {}).get(nom, 1500)

    # ── Enrichissement depuis joueurs.csv via jointure floue ──
    taille         = None
    main           = None
    date_naissance = None
    age_actuel     = None
    player_id      = None

    if df_joueurs is not None:
        j = trouver_joueur_csv(nom, df_joueurs)
        if j is not None:
            taille         = safe_get(j, 'taille_cm')
            main           = safe_get(j, 'main')
            date_naissance = safe_get(j, 'date_naissance')
            age_actuel     = safe_get(j, 'age_actuel')
            player_id      = safe_get(j, 'player_id')

    # ── Matchs depuis df_base ──
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
        mask   = None

    total_matchs = len(matchs)
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        victoires = len(matchs[matchs['winner_name'] == nom])
    else:
        victoires = 0
    pct_victoire = round(
        victoires / total_matchs * 100, 1
    ) if total_matchs > 0 else 0

    # ── Classement ──
    rank = None
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        for _, row in matchs.head(30).iterrows():
            if row['winner_name'] == nom:
                r = safe_int(row.get('winner_rank', 0))
            else:
                r = safe_int(row.get('loser_rank', 0))
            if 0 < r < 2000:
                rank = r
                break
    if rank is None:
        r_api = get_rank_api(nom)
        rank  = r_api if r_api else 'N/A'

    # ── Pays ──
    pays = 'N/A'
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        for _, row in matchs.head(10).iterrows():
            if row['winner_name'] == nom:
                p = str(row.get('winner_ioc', '') or '')
            else:
                p = str(row.get('loser_ioc', '') or '')
            if p and p not in ['nan', 'None', 'NaN', '']:
                pays = p
                break
    # Fallback depuis joueurs.csv
    if pays == 'N/A' and df_joueurs is not None:
        j = trouver_joueur_csv(nom, df_joueurs)
        if j is not None:
            pays_csv = safe_get(j, 'nationalite')
            if pays_csv:
                pays = str(pays_csv)

    # ── 5 derniers matchs ──
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

    # ── % victoires par surface ──
    def forme_surf(surf):
        if df_base is None or matchs.empty or mask is None:
            return 0
        m_s = df_base[mask & (df_base['surface'] == surf)]
        if len(m_s) == 0: return 0
        return round(
            len(m_s[m_s['winner_name'] == nom]) / len(m_s) * 100, 1
        )

    return {
        'nom'          : nom,
        'elo_general'  : round(elo_general),
        'elo_hard'     : round(elo_hard),
        'elo_clay'     : round(elo_clay),
        'elo_grass'    : round(elo_grass),
        'forme'        : round(forme.get(nom, 0.5) * 100, 1),
        'rank'         : rank,
        'pays'         : pays,
        'total_matchs' : total_matchs,
        'victoires'    : victoires,
        'pct_victoire' : pct_victoire,
        'hard_pct'     : forme_surf('Hard'),
        'clay_pct'     : forme_surf('Clay'),
        'grass_pct'    : forme_surf('Grass'),
        'derniers'     : derniers,
        # Nouvelles infos depuis joueurs.csv
        'taille'       : taille,
        'main'         : main,
        'date_naissance': date_naissance,
        'age_actuel'   : age_actuel,
        'player_id'    : player_id,
    }

# ============================================================
# CALCUL DES TENDANCES RÉCENTES
# ============================================================
def calculer_tendances(nom, modeles, df_base, nb_matchs=20):
    if df_base is None or df_base.empty:
        return None
    mask = (
        (df_base['winner_name'] == nom) |
        (df_base['loser_name']  == nom)
    )
    matchs = df_base[mask].copy()
    if matchs.empty:
        return None
    matchs['tourney_date'] = pd.to_datetime(matchs['tourney_date'], errors='coerce')
    matchs = matchs.sort_values('tourney_date', ascending=False).reset_index(drop=True)
    matchs = matchs.head(nb_matchs)

    resultats = []
    for _, row in matchs.iterrows():
        gagne      = row['winner_name'] == nom
        adversaire = row['loser_name'] if gagne else row['winner_name']
        resultats.append({
            'date'      : row['tourney_date'],
            'gagne'     : gagne,
            'surface'   : str(row.get('surface', 'Hard')),
            'adversaire': str(adversaire),
            'tournoi'   : str(row.get('tourney_name', 'N/A')),
            'round'     : str(row.get('round', 'N/A')),
            'score'     : str(row.get('score', 'N/A')),
        })

    if not resultats:
        return None

    total      = len(resultats)
    victoires  = sum(1 for r in resultats if r['gagne'])
    pct_global = round(victoires / total * 100, 1)

    recents    = resultats[:5]
    precedents = resultats[5:10]
    pct_recent = round(sum(1 for r in recents if r['gagne'])    / len(recents)    * 100, 1) if recents    else 0
    pct_prec   = round(sum(1 for r in precedents if r['gagne']) / len(precedents) * 100, 1) if precedents else 0
    delta_forme = round(pct_recent - pct_prec, 1)

    surfaces_stats = {}
    for surf in ['Hard', 'Clay', 'Grass']:
        m_surf = [r for r in resultats if r['surface'] == surf]
        if m_surf:
            v_surf = sum(1 for r in m_surf if r['gagne'])
            surfaces_stats[surf] = {
                'total'    : len(m_surf),
                'victoires': v_surf,
                'pct'      : round(v_surf / len(m_surf) * 100, 1),
            }

    serie      = 0
    serie_type = None
    for r in resultats:
        if serie_type is None:
            serie_type = 'V' if r['gagne'] else 'D'
            serie = 1
        elif (r['gagne'] and serie_type == 'V') or (not r['gagne'] and serie_type == 'D'):
            serie += 1
        else:
            break

    courbe = []
    for i in range(1, total + 1):
        sous = resultats[:i]
        courbe.append({
            'match': i,
            'pct'  : round(sum(1 for r in sous if r['gagne']) / i * 100, 1),
            'label': '✅' if resultats[i-1]['gagne'] else '❌',
            'adv'  : resultats[i-1]['adversaire'],
            'surf' : resultats[i-1]['surface'],
        })

    meilleure_surf = max(
        surfaces_stats, key=lambda s: surfaces_stats[s]['pct'], default='N/A'
    ) if surfaces_stats else 'N/A'

    return {
        'total': total, 'victoires': victoires, 'pct_global': pct_global,
        'pct_recent': pct_recent, 'pct_prec': pct_prec, 'delta_forme': delta_forme,
        'serie': serie, 'serie_type': serie_type,
        'surfaces': surfaces_stats, 'meilleure_surf': meilleure_surf,
        'courbe': courbe, 'resultats': resultats,
    }

# ============================================================
# AJOUT JOUEUR VIA API
# ============================================================
def ajouter_joueur_api(nom):
    try:
        from datetime import datetime, timedelta
        today      = datetime.now()
        date_fin   = today.strftime("%Y-%m-%d")
        date_debut = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        res = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : API_KEY,
            "from"   : date_debut,
            "to"     : date_fin,
        }, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") == 1:
                nom_lower = nom.lower().strip()
                mots      = nom_lower.split()
                trouves   = []
                for m in data.get("result", []):
                    p1     = str(m.get('event_first_player',  '')).lower()
                    p2     = str(m.get('event_second_player', '')).lower()
                    match1 = any(mot in p1 for mot in mots if len(mot) > 2)
                    match2 = any(mot in p2 for mot in mots if len(mot) > 2)
                    if match1 or match2:
                        trouves.append(m)
                return trouves[:10]
    except Exception as e:
        st.error(f"Erreur API : {e}")
    return []

# ============================================================
# PAGE JOUEURS — CORRECTION BUG #4
# ============================================================
def page_joueurs(modeles, df_base):
    st.title("👤 Profil Joueur")
    st.markdown("---")

    # ── Chargement de joueurs.csv (CORRECTION BUG #4) ──
    df_joueurs = None
    try:
        # ✅ UTILISE cfg.FICHIER_JOUEURS au lieu d'un chemin en dur
        chemin_joueurs = cfg.FICHIER_JOUEURS
        
        if os.path.exists(chemin_joueurs):
            df_joueurs = pd.read_csv(chemin_joueurs)
            st.success(f"✅ Fichier joueurs.csv chargé : {len(df_joueurs)} joueurs")
        else:
            # Fallback HuggingFace
            try:
                from huggingface_hub import hf_hub_download
                chemin_hf = hf_hub_download(
                    repo_id   = 'fulgence10/tennis-data',
                    filename  = 'joueurs.csv',
                    repo_type = 'dataset'
                )
                df_joueurs = pd.read_csv(chemin_hf)
                st.info(f"📥 Fichier joueurs.csv chargé depuis HuggingFace : {len(df_joueurs)} joueurs")
            except Exception as e_hf:
                st.warning(f"⚠️ Impossible de charger joueurs.csv depuis HuggingFace : {e_hf}")
    
    # ✅ AFFICHAGE COMPLET DE L'ERREUR avec st.exception()
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de joueurs.csv")
        st.exception(e)  # Affiche la stack trace complète

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
        lancer = st.button("Rechercher", type="primary")

    if nom_recherche and lancer:
        # ✅ GESTION D'ERREUR AMÉLIORÉE
        try:
            suggestions = recherche_floue(nom_recherche, liste_joueurs)
        except Exception as e:
            st.error("❌ Erreur lors de la recherche floue")
            st.exception(e)
            st.stop()

        if suggestions:
            options            = [f"{j} (similarité {s:.0f}%)" for j, s in suggestions]
            options_avec_autre = options + ["❌ Aucun de ces joueurs — rechercher via API"]
            choix              = st.selectbox("Sélectionne un joueur", options_avec_autre)

            # ── Cas "Aucun de ces joueurs" ──
            if choix == "❌ Aucun de ces joueurs — rechercher via API":
                st.session_state["joueur_choix_aucun"] = True
                st.session_state["joueur_nom_aucun"]   = nom_recherche
            else:
                st.session_state["joueur_choix_aucun"] = False

            if st.session_state.get("joueur_choix_aucun") and \
               st.session_state.get("joueur_nom_aucun") == nom_recherche:

                st.markdown("---")
                st.subheader(f"➕ Ajouter {nom_recherche} à la base")
                onglet_api2, onglet_csv2 = st.tabs(["🌐 Via API", "📁 Via CSV"])

                with onglet_api2:
                    if st.button("🔍 Rechercher via API", key="btn_api_from_similar"):
                        with st.spinner("Recherche en cours..."):
                            matchs_api = ajouter_joueur_api(nom_recherche)
                        if matchs_api:
                            st.session_state["matchs_api_similar"] = matchs_api
                            st.session_state["nom_api_similar"]    = nom_recherche
                        else:
                            st.session_state["matchs_api_similar"] = []
                            st.session_state["nom_api_similar"]    = nom_recherche
                            st.error(f"❌ {nom_recherche} non trouvé via API")
                            st.warning("💡 Essayez l'onglet 📁 Via CSV")

                    if st.session_state.get("matchs_api_similar") and \
                       st.session_state.get("nom_api_similar") == nom_recherche:
                        matchs_api = st.session_state["matchs_api_similar"]
                        st.success(f"✅ {len(matchs_api)} matchs trouvés pour {nom_recherche} !")
                        for m in matchs_api[:5]:
                            st.write(
                                f"• {m.get('event_date')} — "
                                f"{m.get('event_first_player')} vs {m.get('event_second_player')}"
                            )
                        if st.button("✅ Confirmer l'ajout à la base", key="confirmer_api2"):
                            nouveaux = [{
                                "winner_name" : m.get("event_first_player", ""),
                                "loser_name"  : m.get("event_second_player", ""),
                                "surface"     : m.get("event_ground", "Hard"),
                                "tourney_name": m.get("league_name", "Unknown"),
                                "tourney_date": m.get("event_date", "2026-01-01"),
                                "score"       : m.get("event_final_result", ""),
                                "round"       : m.get("event_round", "R32"),
                                "winner_rank" : m.get("first_player_rank", 500),
                                "loser_rank"  : m.get("second_player_rank", 500),
                            } for m in matchs_api]
                            from modules.mise_a_jour import mise_a_jour_incrementale
                            modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                            st.session_state["modeles"] = modeles_maj
                            if df_base is not None:
                                st.session_state["df_base"] = pd.concat(
                                    [df_base, pd.DataFrame(nouveaux)], ignore_index=True
                                )
                            st.session_state["matchs_api_similar"] = []
                            st.success(
                                f"✅ {nom_recherche} ajouté avec {len(nouveaux)} matchs ! "
                                f"Tapez à nouveau son nom pour le trouver."
                            )

                with onglet_csv2:
                    st.info("""📋 **Format CSV requis :**
Colonnes : winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank
Exemple : Kouassi Ange, Djokovic N., Clay, Roland Garros, 2026-01-15, 6-3 6-4, R32, 450, 1
Surface : Hard / Clay / Grass | Date : YYYY-MM-DD | Round : R32/QF/SF/F | Rank : 500 si inconnu""")
                    fichier_csv2 = st.file_uploader(
                        "📁 Upload CSV", type=["csv"], key="upload_joueur_similar"
                    )
                    if fichier_csv2:
                        df_up = pd.read_csv(fichier_csv2)
                        st.dataframe(df_up.head(5))
                        if st.button("✅ Confirmer l'ajout via CSV", key="confirmer_csv2"):
                            nouveaux = df_up.to_dict("records")
                            from modules.mise_a_jour import mise_a_jour_incrementale
                            modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                            st.session_state["modeles"] = modeles_maj
                            if df_base is not None:
                                st.session_state["df_base"] = pd.concat(
                                    [df_base, df_up], ignore_index=True
                                )
                            st.success(
                                f"✅ {nom_recherche} ajouté avec {len(nouveaux)} matchs ! "
                                f"Tapez à nouveau son nom pour le trouver."
                            )
                st.stop()

            # ── Affichage du profil ──
            # ✅ GESTION D'ERREUR AMÉLIORÉE
            if choix in options:
                joueur_sel = suggestions[options.index(choix)][0]

                try:
                    with st.spinner("⏳ Chargement du profil..."):
                        profil = get_profil_joueur(joueur_sel, modeles, df_base, df_joueurs)
                except Exception as e:
                    st.error(f"❌ Erreur lors du chargement du profil de {joueur_sel}")
                    st.exception(e)  # ✅ Affiche la stack trace complète
                    st.stop()

                st.markdown("---")

                # ── En-tête ──
                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                with col_p1:
                    st.metric("👤 Joueur", profil['nom'])
                with col_p2:
                    rank_display = f"#{profil['rank']}" if profil['rank'] != 'N/A' else 'N/A'
                    st.metric("🏅 Classement", rank_display)
                with col_p3:
                    st.metric("🌍 Pays", profil['pays'])
                with col_p4:
                    st.metric("📈 Forme", f"{profil['forme']}%")

                # Infos physiques depuis joueurs.csv (si disponibles)
                infos_dispo = any([
                    profil['taille'], profil['main'],
                    profil['age_actuel'], profil['date_naissance']
                ])
                if infos_dispo:
                    st.markdown("---")
                    st.subheader("📋 Informations joueur")
                    col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                    with col_i1:
                        taille_str = f"{int(profil['taille'])} cm" if profil['taille'] else 'N/A'
                        st.metric("📏 Taille", taille_str)
                    with col_i2:
                        main_str = {'R': '🤜 Droitier', 'L': '🤛 Gaucher'}.get(
                            str(profil['main']), str(profil['main']) if profil['main'] else 'N/A'
                        )
                        st.metric("🖐️ Main", main_str)
                    with col_i3:
                        age_str = f"{int(profil['age_actuel'])} ans" if profil['age_actuel'] else 'N/A'
                        st.metric("🎂 Âge", age_str)
                    with col_i4:
                        nais_str = str(profil['date_naissance'])[:10] if profil['date_naissance'] else 'N/A'
                        st.metric("📅 Naissance", nais_str)

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

                fig_elo = go.Figure(go.Bar(
                    x=['Général', 'Hard', 'Clay', 'Grass'],
                    y=[
                        profil['elo_general'], profil['elo_hard'],
                        profil['elo_clay'],    profil['elo_grass'],
                    ],
                    marker_color=['#2d9e56', '#2196F3', '#FF5722', '#4CAF50'],
                    text=[
                        profil['elo_general'], profil['elo_hard'],
                        profil['elo_clay'],    profil['elo_grass'],
                    ],
                    textposition='outside',
                ))
                fig_elo.update_layout(
                    height=280,
                    yaxis_range=[1400, max(
                        profil['elo_general'], profil['elo_hard'],
                        profil['elo_clay'],    profil['elo_grass'],
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
                    st.metric("🎾 Total matchs", f"{profil['total_matchs']:,}")
                with col_s2:
                    st.metric("✅ % Victoires", f"{profil['pct_victoire']}%")
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

                # ── Tendances récentes ──
                st.markdown("---")
                st.subheader("📈 Tendances récentes")
                col_sl, _ = st.columns([2, 3])
                with col_sl:
                    nb_t = st.slider(
                        "Nombre de matchs analysés",
                        min_value=5, max_value=50, value=20, step=5,
                        key=f"slider_t_{joueur_sel}"
                    )
                t = calculer_tendances(joueur_sel, modeles, df_base, nb_t)
                if t is None:
                    st.warning("⚠️ Pas assez de données pour calculer les tendances.")
                else:
                    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
                    with col_t1:
                        st.metric(
                            f"🏆 Bilan ({t['total']} matchs)",
                            f"{t['victoires']}V / {t['total'] - t['victoires']}D",
                            f"{t['pct_global']}%"
                        )
                    with col_t2:
                        fleche = "⬆️" if t['delta_forme'] > 0 else ("⬇️" if t['delta_forme'] < 0 else "➡️")
                        st.metric(
                            "📊 Forme (5 derniers)", f"{t['pct_recent']}%",
                            f"{fleche} {t['delta_forme']:+.1f}% vs 5 précédents"
                        )
                    with col_t3:
                        ic      = "🟢" if t['serie_type'] == 'V' else "🔴"
                        label_s = "Victoire(s)" if t['serie_type'] == 'V' else "Défaite(s)"
                        st.metric("🔥 Série en cours", f"{ic} {t['serie']} {label_s}")
                    with col_t4:
                        pct_ms = t['surfaces'].get(t['meilleure_surf'], {}).get('pct', 0)
                        st.metric("🎯 Meilleure surface", t['meilleure_surf'], f"{pct_ms}% de victoires")

                    # Courbe de forme
                    st.markdown("**📉 Évolution du taux de victoire**")
                    couleurs = ['#2d9e56' if r['gagne'] else '#ef4444' for r in t['resultats']]
                    fig_t = go.Figure()
                    fig_t.add_trace(go.Scatter(
                        x=[c['match'] for c in t['courbe']],
                        y=[c['pct']   for c in t['courbe']],
                        mode='lines+markers',
                        line=dict(color='#4ade80', width=2),
                        marker=dict(color=couleurs, size=10, line=dict(color='white', width=1)),
                        hovertemplate='<b>Match %{x}</b><br>%{y:.1f}%<br>%{text}<extra></extra>',
                        text=[
                            f"{c['label']} {c['adv'][:15]} ({c['surf']})"
                            for c in t['courbe']
                        ],
                    ))
                    fig_t.add_hline(
                        y=50, line_dash='dot',
                        line_color='rgba(255,255,255,0.3)',
                        annotation_text='50%'
                    )
                    fig_t.update_layout(
                        height=260,
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'), margin=dict(t=10, b=10),
                        xaxis=dict(title='Matchs (récent → ancien)', gridcolor='rgba(255,255,255,0.05)'),
                        yaxis=dict(title='% Victoires', range=[0, 105], gridcolor='rgba(255,255,255,0.1)'),
                    )
                    st.plotly_chart(fig_t, use_container_width=True)

                    # Stats par surface
                    if t['surfaces']:
                        st.markdown("**🏟️ Performance par surface (sur ces matchs)**")
                        surf_icons = {'Hard': '🏟️', 'Clay': '🌱', 'Grass': '🌿'}
                        cols_surf  = st.columns(len(t['surfaces']))
                        for i, (surf, stats) in enumerate(t['surfaces'].items()):
                            with cols_surf[i]:
                                st.metric(
                                    f"{surf_icons.get(surf,'🎾')} {surf}",
                                    f"{stats['victoires']}V / {stats['total'] - stats['victoires']}D",
                                    f"{stats['pct']}%",
                                    delta_color="normal" if stats['pct'] >= 50 else "inverse"
                                )
                                st.progress(int(stats['pct']))

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
                        opts_adv  = [f"{j} (similarité {s:.0f}%)" for j, s in sugg_adv]
                        choix_adv = st.selectbox(
                            "Sélectionne l'adversaire", opts_adv, key="choix_adv"
                        )
                        adversaire = sugg_adv[opts_adv.index(choix_adv)][0]

                        if df_base is None:
                            st.warning("⚠️ BASE_FEATURES.csv non disponible — H2H indisponible")
                        else:
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
                            h2h    = h2h.sort_values('tourney_date', ascending=False)
                            total_h = len(h2h)
                            wins_h  = len(h2h[h2h['winner_name'] == joueur_sel])

                            if total_h > 0:
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    st.metric("Total matchs", total_h)
                                with c2:
                                    st.metric(f"✅ {joueur_sel[:15]}", wins_h)
                                with c3:
                                    st.metric(f"✅ {adversaire[:15]}", total_h - wins_h)
                                rows_h = [{
                                    'Date'     : str(row['tourney_date'])[:10],
                                    'Tournoi'  : str(row.get('tourney_name', 'N/A')),
                                    'Surface'  : str(row.get('surface', 'N/A')),
                                    'Score'    : str(row.get('score', 'N/A')),
                                    'Vainqueur': str(row['winner_name']),
                                } for _, row in h2h.iterrows()]
                                st.dataframe(
                                    pd.DataFrame(rows_h),
                                    hide_index=True,
                                    use_container_width=True,
                                )
                            else:
                                st.info(f"Aucun match entre {joueur_sel} et {adversaire}")
                    else:
                        st.warning("Adversaire non trouvé")

        else:
            st.warning(f"⚠️ '{nom_recherche}' introuvable dans la base")

    # ══════════════════════════════════════════
    # SECTION AJOUT JOUEUR (toujours visible)
    # ══════════════════════════════════════════
    st.markdown("---")
    st.subheader("➕ Ajouter un joueur à la base")
    nom_ajout = st.text_input(
        "Nom du joueur à ajouter",
        placeholder="Ex: Kouassi Ange",
        key="nom_ajout"
    )

    if nom_ajout:
        onglet_api, onglet_csv = st.tabs(["🌐 Via API", "📁 Via CSV"])

        with onglet_api:
            if st.button("🔍 Rechercher via API", key="btn_api_ajout"):
                with st.spinner("Recherche en cours..."):
                    resultats = ajouter_joueur_api(nom_ajout)
                st.session_state["api_resultats"] = resultats
                st.session_state["api_nom"]       = nom_ajout

            if st.session_state.get("api_nom") == nom_ajout:
                resultats = st.session_state.get("api_resultats", [])
                if resultats:
                    st.success(f"✅ {len(resultats)} matchs trouvés pour {nom_ajout} !")
                    for m in resultats[:5]:
                        st.write(
                            f"• {m.get('event_date','')} — "
                            f"{m.get('event_first_player','')} vs {m.get('event_second_player','')}"
                        )
                    if st.button("✅ Confirmer l'ajout", key="btn_confirmer_api_ajout"):
                        nouveaux = [{
                            "winner_name" : m.get("event_first_player", ""),
                            "loser_name"  : m.get("event_second_player", ""),
                            "surface"     : m.get("event_ground", "Hard"),
                            "tourney_name": m.get("league_name", "Unknown"),
                            "tourney_date": m.get("event_date", "2026-01-01"),
                            "score"       : m.get("event_final_result", ""),
                            "round"       : m.get("event_round", "R32"),
                            "winner_rank" : m.get("first_player_rank", 500),
                            "loser_rank"  : m.get("second_player_rank", 500),
                        } for m in resultats]
                        from modules.mise_a_jour import mise_a_jour_incrementale
                        modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                        st.session_state["modeles"] = modeles_maj
                        if df_base is not None:
                            st.session_state["df_base"] = pd.concat(
                                [df_base, pd.DataFrame(nouveaux)], ignore_index=True
                            )
                        st.session_state["api_resultats"] = []
                        st.success(
                            f"✅ {nom_ajout} ajouté avec {len(nouveaux)} matchs ! "
                            f"Recherchez-le maintenant."
                        )
                elif st.session_state.get("api_nom"):
                    st.error(f"❌ {nom_ajout} non trouvé via API — essayez le CSV")

        with onglet_csv:
            st.info("""📋 **Format CSV requis :**
Colonnes : winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank
Exemple : Kouassi Ange, Djokovic N., Clay, Roland Garros, 2026-01-15, 6-3 6-4, R32, 450, 1
Surface : Hard / Clay / Grass | Date : YYYY-MM-DD | Round : R32/QF/SF/F | Rank : 500 si inconnu""")
            fichier_csv = st.file_uploader("📁 Upload CSV", type=["csv"], key="upload_joueur")
            if fichier_csv:
                df_up = pd.read_csv(fichier_csv)
                st.dataframe(df_up.head(5))
                if st.button("✅ Confirmer l'ajout via CSV", key="btn_confirmer_csv_ajout"):
                    nouveaux = df_up.to_dict("records")
                    from modules.mise_a_jour import mise_a_jour_incrementale
                    modeles_maj = mise_a_jour_incrementale(modeles, nouveaux)
                    st.session_state["modeles"] = modeles_maj
                    if df_base is not None:
                        st.session_state["df_base"] = pd.concat(
                            [df_base, df_up], ignore_index=True
                        )
                    st.success(
                        f"✅ {nom_ajout} ajouté avec {len(nouveaux)} matchs ! "
                        f"Recherchez-le maintenant."
                    )