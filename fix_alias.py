content = open("modules/prediction.py", encoding="utf-8").read()

aliases = """
# Dictionnaire alias noms joueurs
ALIAS_JOUEURS = {
    "Taylor Harry Fritz": "T. Fritz",
    "Taylor Fritz": "T. Fritz",
    "Novak Djokovic": "N. Djokovic",
    "Carlos Alcaraz": "C. Alcaraz",
    "Jannik Sinner": "J. Sinner",
    "Alexander Zverev": "A. Zverev",
    "Daniil Medvedev": "D. Medvedev",
    "Andrey Rublev": "A. Rublev",
    "Casper Ruud": "C. Ruud",
    "Holger Rune": "H. Rune",
    "Stefanos Tsitsipas": "S. Tsitsipas",
    "Felix Auger-Aliassime": "F. Auger-Aliassime",
    "Rafael Nadal": "R. Nadal",
    "Roger Federer": "R. Federer",
    "Andy Murray": "A. Murray",
    "Aryna Sabalenka": "A. Sabalenka",
    "Iga Swiatek": "I. Swiatek",
    "Coco Gauff": "C. Gauff",
    "Elena Rybakina": "E. Rybakina",
    "Jessica Pegula": "J. Pegula",
    "Paula Badosa": "P. Badosa",
    "Madison Keys": "M. Keys",
    "Emma Raducanu": "E. Raducanu",
    "Barbora Krejcikova": "B. Krejcikova",
    "Marketa Vondrousova": "M. Vondrousova",
    "Mirra Andreeva": "M. Andreeva",
    "Diana Shnaider": "D. Shnaider",
    "Linda Noskova": "L. Noskova",
    "Luca Van Assche": "L. van Assche",
    "Giovanni Mpetshi Perricard": "G. Mpetshi Perricard",
}

def normaliser_nom(nom):
    return ALIAS_JOUEURS.get(nom, nom)

"""

content = aliases + content
open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "ALIAS_JOUEURS" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
