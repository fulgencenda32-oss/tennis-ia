content = open("modules/prediction.py", encoding="utf-8").read()

content = content.replace(
    "def predire_match(joueur_a, joueur_b,",
    "def predire_match(joueur_a, joueur_b,"
)

# Normaliser les noms au debut de predire_match
ancien = "def predire_match(joueur_a, joueur_b, modeles, df_base,"
nouveau = "def predire_match(joueur_a, joueur_b, modeles, df_base,"
# Trouver la premiere ligne du corps de la fonction
import re
content = re.sub(
    r"(def predire_match\(joueur_a, joueur_b, modeles, df_base,.*?\n\s+\"\"\".*?\"\"\"?\n)",
    r"\1    joueur_a = normaliser_nom(joueur_a)\n    joueur_b = normaliser_nom(joueur_b)\n",
    content, flags=re.DOTALL, count=1
)

open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "normaliser_nom(joueur_a)" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC - ajout manuel necessaire")
