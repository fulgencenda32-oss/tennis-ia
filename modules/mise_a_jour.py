# ============================================================
# MODULE MISE À JOUR
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import requests
import pickle
import re
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
API_KEY  = os.getenv("ALLSPORTS_API_KEY")
BASE_URL = "https://apiv2.allsportsapi.com/tennis/"

# Défini au niveau module pour compatibilité pickle
def simplifier_round(r):
    r = str(r).upper()
    if "QUARTER" in r or "QF" in r: return 4
    if "SEMI"    in r or "SF" in r: return 5
    if r in ["F","FINAL","THE FINAL"]: return 6
    if "R128" in r: return 1
    if "R64"  in r: return 2
    if "R32"  in r: return 3
    if "R16"  in r: return 3
    return 3

# ============================================================
# RÉCUPÉRATION MATCHS VIA API
# ============================================================
def get_matchs_api(date_debut, date_fin):
    try:
        r = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : API_KEY,
            "from"   : date_debut,
            "to"     : date_fin,
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") == 1:
                return data.get("result", [])
    except Exception as e:
        st.error(f"❌ Erreur API : {e}")
    return []

# ============================================================
# CONVERSION MATCHS AU FORMAT BASE
# ============================================================
def convertir_matchs(matchs_raw):
    nouveaux = []
    for m in matchs_raw:
        statut = str(m.get('event_status', '')).lower()
        if statut.lower() not in ['finished', 'fin', 'ft', 'retired']:
            continue
        score_raw = str(m.get('event_final_result', '') or '')
        joueur_a  = str(m.get('event_first_player',  '') or '')
        joueur_b  = str(m.get('event_second_player', '') or '')
        if not joueur_a or not joueur_b or not score_raw:
            continue
        sets = re.findall(r'(\d+)\s*-\s*(\d+)', score_raw)
        if not sets:
            continue
        sets_a = sum(1 for a, b in sets if int(a) > int(b))
        sets_b = len(sets) - sets_a
        winner = joueur_a if sets_a > sets_b else joueur_b
        loser  = joueur_b if sets_a > sets_b else joueur_a
        circuit = str(m.get('country_name', 'ATP') or 'ATP')
        genre   = 'F' if 'WTA' in circuit.upper() else 'M'
        nouveaux.append({
            'tourney_date' : str(m.get('event_date', '')),
            'tourney_name' : str(m.get('league_name', '') or ''),
            'surface'      : 'Hard',
            'circuit'      : circuit,
            'genre'        : genre,
            'round'        : str(m.get('league_round', 'R32') or 'R32'),
            'best_of'      : 3,
            'winner_name'  : winner,
            'loser_name'   : loser,
            'score'        : score_raw,
            'winner_rank'  : m.get('first_player_rank' if sets_a > sets_b else 'second_player_rank', None),
            'loser_rank'   : m.get('second_player_rank' if sets_a > sets_b else 'first_player_rank', None),
            'winner_age'   : None,
            'loser_age'    : None,
            'winner_ioc'   : None,
            'loser_ioc'    : None,
        })
    return nouveaux

# ============================================================
# MISE À JOUR INCRÉMENTALE ELO + FORME
# ============================================================
def mise_a_jour_incrementale(modeles, nouveaux_matchs):
    elo_g = defaultdict(lambda: 1500.0, modeles['elo_final'])
    elo_s = defaultdict(lambda: defaultdict(lambda: 1500.0))
    for surf, d in modeles['elo_final_surf'].items():
        for joueur, val in d.items():
            elo_s[surf][joueur] = val
    forme = dict(modeles['forme_final'])

    for m in nouveaux_matchs:
        w    = str(m['winner_name'])
        l    = str(m['loser_name'])
        surf = str(m.get('surface', 'Hard'))

        # Mise à jour ELO général
        ea = 1 / (1 + 10**((elo_g[l] - elo_g[w]) / 400))
        elo_g[w] += 32 * (1 - ea)
        elo_g[l] += 32 * (0 - (1 - ea))

        # Mise à jour ELO surface
        ea_s = 1 / (1 + 10**((elo_s[surf][l] - elo_s[surf][w]) / 400))
        elo_s[surf][w] += 32 * (1 - ea_s)
        elo_s[surf][l] += 32 * (0 - (1 - ea_s))

        # Mise à jour forme
        fw = forme.get(w, 0.5)
        fl = forme.get(l, 0.5)
        forme[w] = fw * 0.9 + 0.1 * 1.0
        forme[l] = fl * 0.9 + 0.1 * 0.0

    modeles['elo_final'] = dict(elo_g)
    for surf in ['Hard', 'Clay', 'Grass', 'Carpet']:
        modeles['elo_final_surf'][surf].update(dict(elo_s[surf]))
    modeles['forme_final'] = forme
    modeles['date_entrainement'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    return modeles

# ============================================================
# UPLOAD SUR HUGGINGFACE
# ============================================================
def upload_huggingface(modeles, chemin_pkl):
    try:
        import pickle
        import tempfile
        from huggingface_hub import HfApi

        # Utiliser simplifier_round défini au niveau module
        modeles["simplifier_round"] = simplifier_round

        # Sauvegarder le modèle temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            pickle.dump(modeles, f)
            chemin_tmp = f.name

        hf_token = os.getenv('HF_TOKEN') or os.getenv('Tennis_IA_Write')
        api = HfApi(token=hf_token)
        api.upload_file(
            path_or_fileobj=chemin_tmp,
            path_in_repo='data/modeles_tennis_v2.pkl',
            repo_id='Fulgence10/Tennis-IA',
            repo_type='space',
            commit_message=f'Mise à jour incrémentale {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        )
        os.unlink(chemin_tmp)
        return True
    except Exception as e:
        st.error(f"❌ Erreur upload : {e}")
        return False

# ============================================================
# PAGE MISE À JOUR
# ============================================================
def page_mise_a_jour(modeles, df_base):
    st.title("🔄 Mise à jour")
    st.markdown("---")

    # ── Statut connexion ──
    st.subheader("📡 Statut de la connexion API")
    col1, col2 = st.columns(2)
    with col1:
        if API_KEY:
            st.success(f"✅ Clé API trouvée : {API_KEY[:10]}...")
        else:
            st.error("❌ Clé API manquante")
    with col2:
        if st.button("🔍 Tester la connexion API"):
            try:
                r = requests.get(BASE_URL, params={
                    "met"    : "Fixtures",
                    "APIkey" : API_KEY,
                    "from"   : datetime.now().strftime('%Y-%m-%d'),
                    "to"     : datetime.now().strftime('%Y-%m-%d'),
                }, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") == 1:
                        nb = len(data.get("result", []))
                        st.success(f"✅ Connexion OK — {nb} matchs trouvés aujourd'hui")
                    else:
                        st.error(f"❌ Erreur API : {data.get('error', 'Inconnue')}")
                else:
                    st.error(f"❌ Erreur HTTP : {r.status_code}")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

    st.markdown("---")

    # ── Statut modèles ──
    st.subheader("🤖 Statut des modèles IA")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("🏆 Vainqueur", f"{modeles.get('acc_win', 0)*100:.1f}%")
    with col_m2:
        st.metric("🔢 Nb Sets", f"{modeles.get('acc_sets', 0)*100:.1f}%")
    with col_m3:
        st.metric("⚖️ Handicap", f"{modeles.get('acc_handi', 0)*100:.1f}%")
    with col_m4:
        date_entr = modeles.get('date_entrainement', 'N/A')
        st.metric("📅 Dernier entraînement", date_entr[:10] if date_entr != 'N/A' else 'N/A')

    st.markdown("---")

    # ── Statut base ──
    st.subheader("📊 Statut de la base de données")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        nb_joueurs = len(modeles.get('elo_final', {}))
        st.metric("👤 Joueurs en base", f"{nb_joueurs:,}")
    with col_b2:
        if df_base is not None:
            st.metric("🎾 Matchs en base", f"{len(df_base):,}")
        else:
            st.metric("🎾 Matchs en base", "Non disponible")
    with col_b3:
        st.metric("📅 Période", "2010 — 2026")

    st.markdown("---")

    # ── Mise à jour incrémentale ──
    st.subheader("⚡ Mise à jour incrémentale via API")
    st.info(
        "Récupère les nouveaux matchs depuis une date choisie, "
        "met à jour ELO et forme, et uploade le modèle sur HuggingFace."
    )

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        date_debut = st.date_input(
            "📅 Date de début",
            value=datetime.now().date() - timedelta(days=7),
            help="Récupère tous les matchs terminés depuis cette date"
        )
    with col_d2:
        date_fin = st.date_input(
            "📅 Date de fin",
            value=datetime.now().date(),
        )

    if st.button("🚀 Lancer la mise à jour incrémentale", type="primary"):
        if not API_KEY:
            st.error("❌ Clé API manquante !")
            return

        with st.spinner("📡 Récupération des matchs via API..."):
            matchs_raw = get_matchs_api(
                str(date_debut), str(date_fin)
            )

        st.info(f"📊 {len(matchs_raw)} matchs récupérés")

        with st.spinner("🔄 Conversion des matchs..."):
            nouveaux_matchs = convertir_matchs(matchs_raw)

        if not nouveaux_matchs:
            st.warning("⚠️ Aucun match terminé trouvé sur cette période.")
            return

        st.success(f"✅ {len(nouveaux_matchs)} matchs terminés trouvés !")

        # Aperçu des matchs
        df_apercu = pd.DataFrame(nouveaux_matchs)[
            ['tourney_date', 'winner_name', 'loser_name', 'score', 'circuit']
        ]
        st.dataframe(df_apercu.head(10), hide_index=True, use_container_width=True)

        with st.spinner("⚡ Mise à jour ELO et forme..."):
            modeles_maj = mise_a_jour_incrementale(modeles, nouveaux_matchs)

        st.success("✅ ELO et forme mis à jour !")

        with st.spinner("🚀 Upload sur HuggingFace..."):
            succes = upload_huggingface(modeles_maj, None)

        if succes:
            st.success("✅ Modèle uploadé sur HuggingFace ! L'app sera mise à jour dans 2-3 minutes.")
            st.balloons()
        else:
            st.warning("⚠️ Upload échoué — les mises à jour sont actives pour cette session uniquement.")

    st.markdown("---")

<<<<<<< HEAD
    # ── Mise à jour via fichiers CSV ──
    st.subheader("📁 Mise à jour via fichiers CSV")
    st.info(
        "Importez un ou plusieurs fichiers CSV contenant des matchs "
        "pour mettre à jour les modèles sans passer par l'API."
    )

    st.markdown("**Format CSV attendu :**")
    st.code(
        "winner_name, loser_name, surface, tourney_name, tourney_date, score, round, winner_rank, loser_rank, circuit, genre, best_of",
        language="text"
    )

    fichiers_csv = st.file_uploader(
        "📂 Importer des fichiers CSV",
        type=['csv'],
        accept_multiple_files=True,
        key="upload_csv_maj"
    )

    if fichiers_csv:
        tous_matchs = []
        for fichier in fichiers_csv:
            try:
                df_csv = pd.read_csv(fichier)
                st.success(f"✅ {fichier.name} — {len(df_csv)} matchs chargés")
                tous_matchs.append(df_csv)
            except Exception as e:
                st.error(f"❌ Erreur lecture {fichier.name} : {e}")

        if tous_matchs:
            df_total = pd.concat(tous_matchs, ignore_index=True)
            st.info(f"📊 Total : {len(df_total)} matchs à intégrer")
            st.dataframe(df_total.head(5), hide_index=True, use_container_width=True)

            if st.button("⚡ Mettre à jour les modèles avec ces CSV", type="primary"):
                matchs_csv = df_total.to_dict('records')
                with st.spinner("⚡ Mise à jour ELO et forme..."):
                    modeles_maj = mise_a_jour_incrementale(modeles, matchs_csv)
                st.success("✅ ELO et forme mis à jour !")
                with st.spinner("🚀 Upload sur HuggingFace..."):
                    succes = upload_huggingface(modeles_maj, None)
                if succes:
                    st.success("✅ Modèle uploadé sur HuggingFace !")
                    st.balloons()
                else:
                    st.warning("⚠️ Upload échoué — mises à jour actives pour cette session uniquement.")

    st.markdown("---")

=======
>>>>>>> 098ba87623553664ef7ea1b640b74340bdea2ece
    # ── Instructions réentraînement complet ──
    st.subheader("🖥️ Réentraînement complet hebdomadaire")
    st.info(
        "Pour le réentraînement complet, lancez le script sur votre PC une fois par semaine :"
    )
    st.code("python entrainement_hebdo.py", language="bash")
    st.markdown("""
    Ce script va :
    - Récupérer les nouveaux matchs via API
    - Les ajouter à la base complète
    - Réentraîner les 3 modèles sur toute la base
    - Uploader automatiquement sur HuggingFace
    """)
