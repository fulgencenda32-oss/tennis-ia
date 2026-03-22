content = open("modules/prediction.py", encoding="utf-8").read()

ancien = '''        if nom_a:
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
                    joueur_a = None'''

nouveau = '''        if nom_a:
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
                            suggestions_a.append((n, 75))
            if suggestions_a:
                options_a = [
                    f"{j} (similarite {s:.0f}%)"
                    for j, s in suggestions_a
                ] + ["❌ Aucun de ces joueurs — aller dans Joueurs"]
                choix_a  = st.selectbox(
                    "Selectionne le joueur A",
                    options_a, key="choix_a"
                )
                if choix_a == "❌ Aucun de ces joueurs — aller dans Joueurs":
                    joueur_a = None'''

content = content.replace(ancien, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "btn_api_search_a" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
