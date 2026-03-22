content = open("modules/prediction.py", encoding="utf-8").read()

# Correction 1 : ajouter value= dans text_input joueur B
content = content.replace(
    '''        nom_b = st.text_input(
            "Nom du joueur B",
            placeholder="Ex: Alcaraz, Sinner...",
            key="nom_b"
        )
        joueur_b = None
        if nom_b:''',
    '''        nom_b = st.text_input(
            "Nom du joueur B",
            placeholder="Ex: Alcaraz, Sinner...",
            key="nom_b",
            value=st.session_state.get("joueur_b_auto") or ""
        )

        # Recherche match du jour via API (prioritaire)
        if nom_b and len(nom_b) >= 3 and not st.session_state.get("ignorer_api"):
            matchs_api_b = chercher_match_aujourd_hui(nom_b)
            if matchs_api_b:
                st.markdown("---")
                for match in matchs_api_b[:2]:
                    st.success(f"Match trouve aujourd\'hui : {match[\'joueur_a\']} vs {match[\'joueur_b\']} | {match[\'tournoi\']}")
                    col_ok2, col_no2 = st.columns(2)
                    with col_ok2:
                        if st.button("Utiliser ce match", key=f"use_match_b_{match[\'joueur_a\']}_{match[\'joueur_b\']}"):
                            st.session_state["joueur_a_auto"] = match["joueur_a"]
                            st.session_state["joueur_b_auto"] = match["joueur_b"]
                            st.session_state["ignorer_api"] = True
                    with col_no2:
                        if st.button("Ignorer", key=f"ignore_b_{match[\'joueur_a\']}"):
                            st.session_state["ignorer_api"] = True
                st.markdown("---")

        joueur_b = st.session_state.get("joueur_b_auto")
        if not joueur_b:
         if nom_b:'''
)

# Correction 2 : corriger l indentation du if nom_b
content = content.replace(
    "        joueur_b = st.session_state.get(\"joueur_b_auto\")\n        if not joueur_b:\n         if nom_b:",
    "        joueur_b = st.session_state.get(\"joueur_b_auto\")\n        if not joueur_b:\n            if nom_b:"
)

open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "joueur_b_auto" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
