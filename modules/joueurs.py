# ============================================================
# MODULE JOUEURS
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
# EXTRACTION SÉCURISÉE D'UNE VALEUR DEPUIS UNE SERIES PANDAS
# ============================================================
def safe_get(series, key, default=None):
    """Extrait une valeur d'une Series pandas de manière sécurisée"""
    try:
        if key in series.index:
            val = series[key]
            if pd.notna(val):
                return val
        return default
    except:
        return default

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

    # ✅ NOUVEAU : Chercher infos détaillées dans joueurs.csv
    taille = None
    main = None
    date_naissance = None
    age_actuel = None
    player_id = None
    
    if df_joueurs is not None and 'nom_complet' in df_joueurs.columns:
        joueur_info = df_joueurs[df_joueurs['nom_complet'] == nom]
        if not joueur_info.empty:
            j = joueur_info.iloc[0]
            taille = safe_get(j, 'taille_cm')
            main = safe_get(j, 'main')
            date_naissance = safe_get(j, 'date_naissance')
            age_actuel = safe_get(j, 'age_actuel')
            player_id = safe_get(j, 'player_id')

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
        mask = None

    total_matchs = len(matchs)
    if total_matchs > 0 and 'winner_name' in matchs.columns:
        victoires = len(matchs[matchs['winner_name'] == nom])
    else:
        victoires = 0
    pct_victoire = round(
        victoires / total_matchs * 100, 1
    ) if total_matchs > 0 else 0

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
    if rank == 500:
        r_api = get_rank_api(nom)
        if r_api:
            rank = r_api

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
    
    if pays == 'N/A' and df_joueurs is not None and 'nom_complet' in df_joueurs.columns:
        joueur_info = df_joueurs[df_joueurs['nom_complet'] == nom]
        if not joueur_info.empty:
            pays_csv = safe_get(joueur_info.iloc[0], 'nationalite')
            if pays_csv:
                pays = str(pays_csv)

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

    def forme_surf(surf):
        if df_base is None or matchs.empty or mask is None:
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
        'taille'      : taille,
        'main'        : main,
        'date_naissance': date_naissance,
        'age_actuel'  : age_actuel,
        'player_id'   : player_id,
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

    total     = len(resultats)
    victoires = sum(1 for r in resultats if r['gagne'])
    pct_global = round(victoires / total * 100, 1)

    recents    = resultats[:5]
    precedents = resultats[5:10]
    pct_recent = round(sum(1 for r in recents if r['gagne']) / len(recents) * 100, 1) if recents else 0
    pct_prec   = round(sum(1 for r in precedents if r['gagne']) / len(precedents) * 100, 1) if precedents else 0
    delta_forme = round(pct_recent - pct_prec, 1)

    surfaces_stats = {}
    for surf in ['Hard', 'Clay', 'Grass']:
        m_surf = [r for r in resultats if r['surface'] == surf]
        if m_surf:
            v_surf = sum(1 for r in m_surf if r['gagne'])
            surfaces_stats[surf] = {
                'total': len(m_surf), 'victoires': v_surf,
                'pct': round(v_surf / len(m_surf) * 100, 1)
            }

    serie = 0
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

    meilleure_surf = max(surfaces_stats, key=lambda s: surfaces_stats[s]['pct'], default='N/A') if surfaces_stats else 'N/A'

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
        today = datetime.now()
        date_fin = today.strftime("%Y-%m-%d")
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
                mots = nom_lower.split()
                trouves = []
                for m in data.get("result", []):
                    p1 = str(m.get('event_first_player', '')).lower()
                    p2 = str(m.get('event_second_player', '')).lower()
                    match1 = any(mot in p1 for mot in mots if len(mot) > 2)
                    match2 = any(mot in p2 for mot in mots if len(mot) > 2)
                    if match1 or match2:
                        trouves.append(m)
                return trouves[:10]
    except Exception as e:
        st.error(f"Erreur API : {e}")
    return []

# ============================================================
# PAGE JOUEURS
# ============================================================
def page_joueurs(modeles, df_base):
    try:  # ✅ AJOUT : Wrapper global pour capturer toutes les erreurs
        st.title("👤 Profil Joueur")
        st.markdown("---")

        df_joueurs = None
        try:
            df_joueurs = pd.read_csv(cfg.FICHIER_JOUEURS)
        except FileNotFoundError:
            pass
        except Exception as e:
            st.warning(f"⚠️ Impossible de charger joueurs.csv : {e}")

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
                options = [f"{j} (similarité {s:.0f}%)" for j, s in suggestions]
                options_avec_autre = options + ["❌ Aucun de ces joueurs — rechercher via API"]
                choix = st.selectbox("Sélectionne un joueur", options_avec_autre)

                if choix == "❌ Aucun de ces joueurs — rechercher via API":
                    st.session_state["joueur_choix_aucun"] = True
                    st.session_state["joueur_nom_aucun"] = nom_recherche
                elif choix != "❌ Aucun de ces joueurs — rechercher via API":
                    st.session_state["joueur_choix_aucun"] = False

                if st.session_state.get("joueur_choix_aucun") and st.session_state.get("joueur_nom_aucun") == nom_recherche:
                    st.markdown("---")
                    st.subheader(f"➕ Ajouter {nom_recherche} à la base")
                    # [Le reste du code d'ajout reste identique...]
                    st.stop()

                joueur_sel = suggestions[options.index(choix)][0]

                with st.spinner("⏳ Chargement du profil..."):
                    profil = get_profil_joueur(joueur_sel, modeles, df_base, df_joueurs)

                st.markdown("---")

                # [Tout le reste du code d'affichage reste identique...]
                # Je ne le répète pas pour éviter la redondance
                # Utilise le code que tu as déjà pour l'affichage

            else:
                st.warning(f"⚠️ '{nom_recherche}' introuvable dans la base")

    except Exception as e:  # ✅ AJOUT : Capture de l'erreur globale
        st.error("❌ Une erreur est survenue dans le module Joueurs")
        st.exception(e)  # ✅ AFFICHE L'ERREUR COMPLÈTE