# ============================================================


# MODULE MISE ├Ç JOUR


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





# ============================================================


# R├ëCUP├ëRATION MATCHS VIA API


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


        st.error(f"ÔØî Erreur API : {e}")


    return []





# ============================================================


# CONVERSION MATCHS AU FORMAT BASE


# ============================================================


def convertir_matchs(matchs_raw):


    nouveaux = []


    for m in matchs_raw:


        statut = str(m.get('event_status', '')).lower()


        if statut not in ['finished', 'fin', 'ft']:


            continue


        score_raw = str(m.get('event_final_result', '') or '')


        joueur_a  = str(m.get('event_first_player',  '') or '')


        joueur_b  = str(m.get('event_second_player', '') or '')


        if not joueur_a or not joueur_b or not score_raw:


            continue


        sets = re.findall(r'(\d+)-(\d+)', score_raw)


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


# MISE ├Ç JOUR INCR├ëMENTALE ELO + FORME


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





        # Mise ├á jour ELO g├®n├®ral


        ea = 1 / (1 + 10**((elo_g[l] - elo_g[w]) / 400))


        elo_g[w] += 32 * (1 - ea)


        elo_g[l] += 32 * (0 - (1 - ea))





        # Mise ├á jour ELO surface


        ea_s = 1 / (1 + 10**((elo_s[surf][l] - elo_s[surf][w]) / 400))


        elo_s[surf][w] += 32 * (1 - ea_s)


        elo_s[surf][l] += 32 * (0 - (1 - ea_s))





        # Mise ├á jour forme


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





        # Sauvegarder le mod├¿le temporairement


        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:


            pickle.dump(modeles, f)


            chemin_tmp = f.name





        api = HfApi()


        api.upload_file(


            path_or_fileobj=chemin_tmp,


            path_in_repo='data/modeles_tennis_v2.pkl',


            repo_id='Fulgence10/Tennis-IA',


            repo_type='space',


            commit_message=f'Mise ├á jour incr├®mentale {datetime.now().strftime("%Y-%m-%d %H:%M")}'


        )


        os.unlink(chemin_tmp)


        return True


    except Exception as e:


        st.error(f"ÔØî Erreur upload : {e}")


        return False





# ============================================================


# PAGE MISE ├Ç JOUR


# ============================================================


def page_mise_a_jour(modeles, df_base):


    st.title("­ƒöä Mise ├á jour")


    st.markdown("---")





    # ÔöÇÔöÇ Statut connexion ÔöÇÔöÇ


    st.subheader("­ƒôí Statut de la connexion API")


    col1, col2 = st.columns(2)


    with col1:


        if API_KEY:


            st.success(f"Ô£à Cl├® API trouv├®e : {API_KEY[:10]}...")


        else:


            st.error("ÔØî Cl├® API manquante")


    with col2:


        if st.button("­ƒöì Tester la connexion API"):


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


                        st.success(f"Ô£à Connexion OK ÔÇö {nb} matchs trouv├®s aujourd'hui")


                    else:


                        st.error(f"ÔØî Erreur API : {data.get('error', 'Inconnue')}")


                else:


                    st.error(f"ÔØî Erreur HTTP : {r.status_code}")


            except Exception as e:


                st.error(f"ÔØî Erreur : {e}")





    st.markdown("---")





    # ÔöÇÔöÇ Statut mod├¿les ÔöÇÔöÇ


    st.subheader("­ƒñû Statut des mod├¿les IA")


    col_m1, col_m2, col_m3, col_m4 = st.columns(4)


    with col_m1:


        st.metric("­ƒÅå Vainqueur", f"{modeles.get('acc_win', 0)*100:.1f}%")


    with col_m2:


        st.metric("­ƒöó Nb Sets", f"{modeles.get('acc_sets', 0)*100:.1f}%")


    with col_m3:


        st.metric("ÔÜû´©Å Handicap", f"{modeles.get('acc_handi', 0)*100:.1f}%")


    with col_m4:


        date_entr = modeles.get('date_entrainement', 'N/A')


        st.metric("­ƒôà Dernier entra├«nement", date_entr[:10] if date_entr != 'N/A' else 'N/A')





    st.markdown("---")





    # ÔöÇÔöÇ Statut base ÔöÇÔöÇ


    st.subheader("­ƒôè Statut de la base de donn├®es")


    col_b1, col_b2, col_b3 = st.columns(3)


    with col_b1:


        nb_joueurs = len(modeles.get('elo_final', {}))


        st.metric("­ƒæñ Joueurs en base", f"{nb_joueurs:,}")


    with col_b2:


        if df_base is not None:


            st.metric("­ƒÄ¥ Matchs en base", f"{len(df_base):,}")


        else:


            st.metric("­ƒÄ¥ Matchs en base", "Non disponible")


    with col_b3:


        st.metric("­ƒôà P├®riode", "2010 ÔÇö 2026")





    st.markdown("---")





    # ÔöÇÔöÇ Mise ├á jour incr├®mentale ÔöÇÔöÇ


    st.subheader("ÔÜí Mise ├á jour incr├®mentale via API")


    st.info(


        "R├®cup├¿re les nouveaux matchs depuis une date choisie, "


        "met ├á jour ELO et forme, et uploade le mod├¿le sur HuggingFace."


    )





    col_d1, col_d2 = st.columns(2)


    with col_d1:


        date_debut = st.date_input(


            "­ƒôà Date de d├®but",


            value=datetime.now().date() - timedelta(days=7),


            help="R├®cup├¿re tous les matchs termin├®s depuis cette date"


        )


    with col_d2:


        date_fin = st.date_input(


            "­ƒôà Date de fin",


            value=datetime.now().date(),


        )





    if st.button("­ƒÜÇ Lancer la mise ├á jour incr├®mentale", type="primary"):


        if not API_KEY:


            st.error("ÔØî Cl├® API manquante !")


            return





        with st.spinner("­ƒôí R├®cup├®ration des matchs via API..."):


            matchs_raw = get_matchs_api(


                str(date_debut), str(date_fin)


            )





        st.info(f"­ƒôè {len(matchs_raw)} matchs r├®cup├®r├®s")





        with st.spinner("­ƒöä Conversion des matchs..."):


            nouveaux_matchs = convertir_matchs(matchs_raw)





        if not nouveaux_matchs:


            st.warning("ÔÜá´©Å Aucun match termin├® trouv├® sur cette p├®riode.")


            return





        st.success(f"Ô£à {len(nouveaux_matchs)} matchs termin├®s trouv├®s !")





        # Aper├ºu des matchs


        df_apercu = pd.DataFrame(nouveaux_matchs)[


            ['tourney_date', 'winner_name', 'loser_name', 'score', 'circuit']


        ]


        st.dataframe(df_apercu.head(10), hide_index=True, use_container_width=True)





        with st.spinner("ÔÜí Mise ├á jour ELO et forme..."):


            modeles_maj = mise_a_jour_incrementale(modeles, nouveaux_matchs)
            st.session_state['modeles'] = modeles_maj





        st.success("Ô£à ELO et forme mis ├á jour !")





        with st.spinner("­ƒÜÇ Upload sur HuggingFace..."):


            succes = upload_huggingface(modeles_maj, None)





        if succes:


            st.success("Ô£à Mod├¿le upload├® sur HuggingFace ! L'app sera mise ├á jour dans 2-3 minutes.")


            st.balloons()


        else:


            st.warning("ÔÜá´©Å Upload ├®chou├® ÔÇö les mises ├á jour sont actives pour cette session uniquement.")





    st.markdown("---")





    # ÔöÇÔöÇ Instructions r├®entra├«nement complet ÔöÇÔöÇ



    st.markdown("---")

    # -- Mise a jour via fichiers CSV --
    st.subheader("📁 Mise à jour via fichiers CSV")
    st.info("Importez un ou plusieurs fichiers CSV pour mettre à jour les modèles sans passer par l'API.")
    fichiers_csv = st.file_uploader("📂 Importer des fichiers CSV", type=['csv'], accept_multiple_files=True, key="upload_csv_maj")
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
            st.info(f"Total : {len(df_total)} matchs prêts pour mise à jour")
            if st.button("⚡ Mettre à jour les modèles avec ces CSV", type="primary"):
                with st.spinner("Mise à jour en cours..."):
                    matchs_csv = df_total.to_dict("records")
                    try:
                        modeles_maj = mise_a_jour_incrementale(modeles, matchs_csv)
                        st.session_state["modeles"] = modeles_maj
                        st.success("✅ Modèles mis à jour avec les CSV !")
                    except Exception as e:
                        st.error(f"❌ Erreur mise à jour : {e}")

    st.subheader("­ƒûÑ´©Å R├®entra├«nement complet hebdomadaire")


    st.info(


        "Pour le r├®entra├«nement complet, lancez le script sur votre PC une fois par semaine :"


    )


    st.code("python entrainement_hebdo.py", language="bash")


    st.markdown("""


    Ce script va :


    - R├®cup├®rer les nouveaux matchs via API


    - Les ajouter ├á la base compl├¿te


    - R├®entra├«ner les 3 mod├¿les sur toute la base


    - Uploader automatiquement sur HuggingFace


    """)


