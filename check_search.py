import sys
sys.path.insert(0, ".")
from rapidfuzz import process, fuzz

# Simuler quelques joueurs de la base
liste = ["T. Fritz", "Taylor Fritz", "Fritz Wolmarans", "N. Djokovic", "C. Alcaraz"]

def recherche_floue_ancienne(nom, liste_joueurs, limite=5, seuil=55):
    resultats = process.extract(nom, liste_joueurs, scorer=fuzz.WRatio, limit=limite)
    return [(j, s) for j, s, _ in resultats if s >= seuil]

def recherche_floue_nouvelle(nom, liste_joueurs, limite=5, seuil=55):
    resultats = process.extract(nom, liste_joueurs, scorer=fuzz.WRatio, limit=limite)
    bons = [(j, s) for j, s, _ in resultats if s >= seuil]
    if len(bons) < 3:
        mots = nom.strip().split()
        for mot in mots:
            if len(mot) > 3:
                extras = process.extract(mot, liste_joueurs, scorer=fuzz.WRatio, limit=limite)
                for j, s, _ in extras:
                    if s >= seuil and j not in [b[0] for b in bons]:
                        bons.append((j, min(s, 85)))
    return sorted(bons, key=lambda x: x[1], reverse=True)[:limite]

print("=== Recherche 'Taylor Harry Fritz' ===")
print("Ancienne :", recherche_floue_ancienne("Taylor Harry Fritz", liste))
print("Nouvelle :", recherche_floue_nouvelle("Taylor Harry Fritz", liste))

print("\n=== Recherche 'Fritz' ===")
print("Ancienne :", recherche_floue_ancienne("Fritz", liste))
print("Nouvelle :", recherche_floue_nouvelle("Fritz", liste))
