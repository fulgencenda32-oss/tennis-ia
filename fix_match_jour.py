content = open("modules/prediction.py", encoding="utf-8").read()

# Remplacer toute la section page_prediction debut
ancien = '''def page_prediction(modeles, df_base):
    st.title("🎾 Prédiction de match")
    st.markdown("---")

    liste_joueurs = list(modeles['elo_final'].keys())

    # Suggestion de match depuis API
    if "suggestion_match" not in st.session_state:
        st.session_state["suggestion_match"] = None
    if "api_joueurs_a" not in st.session_state:
        st.session_state["api_joueurs_a"] = []
    if "api_joueurs_b" not in st.session_state:
        st.session_state["api_joueurs_b"] = []


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
            # Enrichir avec API si peu de resultats
            if len(suggestions_a) < 3 and len(nom_a) >= 3:
                if st.button("🔍 Chercher aussi via API", key="btn_api_search_a"):
                    with st.spinner("Recherche API..."):
                        noms_api = recherche_api_joueur(nom_a)
                    if noms_api:
                        st.session_state["api_joueurs_a"] = noms_api
                noms_api_a = st.session_state.get("api_joueurs_a", [])
                if noms_api_a:
                    st.info(f"🌐 Trouvé via API : {', '.join(noms_api_a[:3])}")
                    for n in noms_api_a:
                        if n not in [j for j, _ in suggestions_a]:
                            suggestions_a.append((n, 75))'''

nouveau = '''def chercher_match_aujourd_hui(nom):
    """Cherche si le nom correspond a un match du jour via API."""
    cles = get_api_key()
    if not cles:
        return []
    cache_key = f"matchs_jour_search_{nom.lower().strip()}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    import requests
    from datetime import datetime
    aujourd_hui = datetime.now().strftime("%Y-%m-%d")
    mots = [m.lower() for m in nom.strip().split() if len(m) > 2]
    for cle in cles:
        try:
            r = requests.get("https://apiv2.allsportsapi.com/tennis/", params={
                "met": "Fixtures", "APIkey": cle,
                "from": aujourd_hui, "to": aujourd_hui,
            }, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get("success") == 1:
                    matchs_trouves = []
                    for m in data.get("result", []):
                        p1 = str(m.get("event_first_player", ""))
                        p2 = str(m.get("event_second_player", ""))
                        if "/" in p1 or "/" in p2:
                            continue
                        p1_lower = p1.lower()
                        p2_lower = p2.lower()
                        if any(mot in p1_lower or mot in p2_lower for mot in mots):
                            matchs_trouves.append({
                                "joueur_a": p1,
                                "joueur_b": p2,
                                "tournoi": m.get("league_name", ""),
                                "heure": m.get("event_time", ""),
                            })
                    st.session_state[cache_key] = matchs_trouves[:3]
                    return matchs_trouves[:3]
        except:
            continue
    return []

def page_prediction(modeles, df_base):
    st.title("🎾 Prédiction de match")
    st.markdown("---")

    liste_joueurs = list(modeles['elo_final'].keys())

    # Init session state
    for k in ["suggestion_match", "joueur_a_auto", "joueur_b_auto", "ignorer_api"]:
        if k not in st.session_state:
            st.session_state[k] = None
    if "api_joueurs_a" not in st.session_state:
        st.session_state["api_joueurs_a"] = []
    if "api_joueurs_b" not in st.session_state:
        st.session_state["api_joueurs_b"] = []

    # ── Colonnes joueurs ──
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Joueur A")
        nom_a = st.text_input(
            "Nom du joueur A",
            placeholder="Ex: Djokovic, Nadal...",
            key="nom_a",
            value=st.session_state.get("joueur_a_auto") or ""
        )

        # Recherche match du jour via API (prioritaire)
        if nom_a and len(nom_a) >= 3 and not st.session_state.get("ignorer_api"):
            matchs_api = chercher_match_aujourd_hui(nom_a)
            if matchs_api:
                st.markdown("---")
                for match in matchs_api[:2]:
                    st.success(
                        f"🎾 **Match trouvé aujourd\'hui :**\n\n"
                        f"**{match[\'joueur_a\']}** vs **{match[\'joueur_b\']}**\n\n"
                        f"🏆 {match[\'tournoi\']} {\'• \' + match[\'heure\'] if match[\'heure\'] else \'\'}"
                    )
                    col_ok, col_no = st.columns(2)
                    with col_ok:
                        if st.button(
                            f"✅ Utiliser ce match",
                            key=f"use_match_{match[\'joueur_a\']}_{match[\'joueur_b\']}"
                        ):
                            st.session_state["joueur_a_auto"] = match["joueur_a"]
                            st.session_state["joueur_b_auto"] = match["joueur_b"]
                            st.session_state["ignorer_api"] = True
                    with col_no:
                        if st.button("❌ Ignorer", key=f"ignore_{match[\'joueur_a\']}"):
                            st.session_state["ignorer_api"] = True
                st.markdown("---")

        joueur_a = st.session_state.get("joueur_a_auto")
        if not joueur_a:
            if nom_a:
                suggestions_a = recherche_floue(nom_a, liste_joueurs)
                if len(suggestions_a) < 3 and len(nom_a) >= 3:
                    if st.button("🔍 Chercher aussi via API", key="btn_api_search_a"):
                        with st.spinner("Recherche API..."):
                            noms_api = recherche_api_joueur(nom_a)
                        if noms_api:
                            st.session_state["api_joueurs_a"] = noms_api
                    noms_api_a = st.session_state.get("api_joueurs_a", [])
                    if noms_api_a:
                        st.info(f"🌐 Trouvé via API : {', \'.join(noms_api_a[:3])}")
                        for n in noms_api_a:
                            if n not in [j for j, _ in suggestions_a]:
                                suggestions_a.append((n, 75))'''

content = content.replace(ancien, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "chercher_match_aujourd_hui" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
