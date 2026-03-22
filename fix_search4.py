content = open("modules/prediction.py", encoding="utf-8").read()

ancien = '''        if nom_b:
            suggestions_b = recherche_floue(nom_b, liste_joueurs)
            if suggestions_b:
                options_b = [
                    f"{j} (similarité {s:.0f}%)"
                    for j, s in suggestions_b
                ] + ["❌ Aucun de ces joueurs — aller dans Joueurs"]
                choix_b  = st.selectbox(
                    "Sélectionne le joueur B",
                    options_b, key="choix_b"'''

nouveau = '''        if nom_b:
            suggestions_b = recherche_floue(nom_b, liste_joueurs)
            if len(suggestions_b) < 3 and len(nom_b) >= 3:
                if st.button("🔍 Chercher aussi via API", key="btn_api_search_b"):
                    with st.spinner("Recherche API..."):
                        noms_api = recherche_api_joueur(nom_b)
                    if noms_api:
                        st.session_state["api_joueurs_b"] = noms_api
                noms_api_b = st.session_state.get("api_joueurs_b", [])
                if noms_api_b:
                    st.info(f"🌐 Trouvé via API : {', '.join(noms_api_b[:3])}")
                    for n in noms_api_b:
                        if n not in [j for j, _ in suggestions_b]:
                            suggestions_b.append((n, 75))
            if suggestions_b:
                options_b = [
                    f"{j} (similarite {s:.0f}%)"
                    for j, s in suggestions_b
                ] + ["❌ Aucun de ces joueurs — aller dans Joueurs"]
                choix_b  = st.selectbox(
                    "Selectionne le joueur B",
                    options_b, key="choix_b"'''

content = content.replace(ancien, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "btn_api_search_b" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
