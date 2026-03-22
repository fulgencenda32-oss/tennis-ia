lines = open("modules/prediction.py", encoding="utf-8").readlines()

# Trouver et corriger les lignes problematiques
for i, line in enumerate(lines):
    if "Match trouv" in line and "aujourd" in line:
        lines[i] = '                    st.success(f"Match trouve aujourd\'hui : {match[\'joueur_a\']} vs {match[\'joueur_b\']} | {match[\'tournoi\']}")\n'
    if "**{match[" in line and "joueur_a" in line and "joueur_b" in line:
        lines[i] = ""
    if "🏆 {match[" in line and "tournoi" in line and "heure" in line:
        lines[i] = ""

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
