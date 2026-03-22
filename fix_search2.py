lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "liste_joueurs = list(modeles" in line:
        insert_at = i + 1
        break

nouveau = """
    # Suggestion de match depuis API
    if "suggestion_match" not in st.session_state:
        st.session_state["suggestion_match"] = None
    if "api_joueurs_a" not in st.session_state:
        st.session_state["api_joueurs_a"] = []
    if "api_joueurs_b" not in st.session_state:
        st.session_state["api_joueurs_b"] = []

"""
lines.insert(insert_at, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
