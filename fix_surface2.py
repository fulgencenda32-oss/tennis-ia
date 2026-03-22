content = open("modules/matchs_du_jour.py", encoding="utf-8").read()

# Correction ligne 247
content = content.replace(
    'res = predire_match(j_a, j_b, modeles, df_base, surface="Hard", tournoi=t)',
    'res = predire_match(j_a, j_b, modeles, df_base, surface=detecter_surface(t), tournoi=t)'
)

# Correction ligne 319
content = content.replace(
    'surface="Hard",\n                                    tournoi=t, round_match=str(match["Round"]))',
    'surface=detecter_surface(t),\n                                    tournoi=t, round_match=str(match["Round"]))'
)

# Correction ligne 334
content = content.replace(
    'afficher_resultat_pred(data["res"], data["j_a"], data["j_b"], "Hard")',
    'afficher_resultat_pred(data["res"], data["j_a"], data["j_b"], detecter_surface(data.get("tournoi", "")))'
)

open("modules/matchs_du_jour.py", "w", encoding="utf-8").write(content)
ok = open("modules/matchs_du_jour.py", encoding="utf-8").read()
print("OK ligne 247 :", "detecter_surface(t)" in ok)
print("OK ligne 334 :", 'detecter_surface(data.get' in ok)
