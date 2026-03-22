import pandas as pd
df = pd.read_csv("data/BASE_FEATURES.csv", low_memory=False)

tous_noms = pd.concat([df["winner_name"], df["loser_name"]]).dropna().unique()
doublons = []
for nom in tous_noms:
    if ". " in str(nom):
        partie = nom.split(". ", 1)
        if len(partie) == 2:
            nom_famille = partie[1].strip()
            for nom2 in tous_noms:
                if nom2 != nom and nom_famille.lower() in str(nom2).lower() and len(str(nom2)) > len(str(nom)):
                    doublons.append((nom, nom2))
                    break

print(f"Doublons detectes : {len(doublons)}")
for d in doublons[:15]:
    print(f"  {d[0]} <-> {d[1]}")
