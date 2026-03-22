import pandas as pd
from rapidfuzz import process, fuzz

df = pd.read_csv("data/BASE_FEATURES.csv", low_memory=False)
liste = list(set(
    df["winner_name"].dropna().tolist() + 
    df["loser_name"].dropna().tolist()
))
liste = [n for n in liste if "/" not in str(n)]

def recherche_nouvelle(nom, liste_joueurs, limite=5, seuil=55):
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

print("=== Taylor Harry Fritz ===")
for j, s in recherche_nouvelle("Taylor Harry Fritz", liste):
    print(f"  {j} ({s:.0f}%)")

print("\n=== Taylor Fritz ===")
for j, s in recherche_nouvelle("Taylor Fritz", liste):
    print(f"  {j} ({s:.0f}%)")
