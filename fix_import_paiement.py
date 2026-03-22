content = open("app.py", encoding="utf-8").read()

# Ajouter import paiement
content = content.replace(
    "    from modules.matchs_du_jour import page_matchs_jour",
    "    from modules.matchs_du_jour import page_matchs_jour\n    from modules.paiement import page_paiement"
)

open("app.py", "w", encoding="utf-8").write(content)
print("OK" if "from modules.paiement import page_paiement" in open("app.py", encoding="utf-8").read() else "ECHEC")
