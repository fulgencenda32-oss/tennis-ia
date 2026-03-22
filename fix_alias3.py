lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "modele_win       = modeles" in line:
        lines.insert(i, "    joueur_a = normaliser_nom(joueur_a)\n")
        lines.insert(i+1, "    joueur_b = normaliser_nom(joueur_b)\n")
        break

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK" if "normaliser_nom(joueur_a)" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
