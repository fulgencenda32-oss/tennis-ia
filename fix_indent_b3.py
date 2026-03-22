lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    lineno = i + 1
    # Ligne 568 : "                if nom_b:" -> 12 espaces
    if lineno == 568 and "if nom_b:" in line:
        lines[i] = "            if nom_b:\n"
    # Ligne 569 : "                suggestions_b" -> 16 espaces
    if lineno == 569 and "suggestions_b = recherche_floue" in line:
        lines[i] = "                suggestions_b = recherche_floue(nom_b, liste_joueurs)\n"
    # Ligne 570 : "            if len(suggestions_b)" -> 16 espaces
    if lineno == 570 and "if len(suggestions_b)" in line:
        lines[i] = "                if len(suggestions_b) < 3 and len(nom_b) >= 3:\n"

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
