import pandas as pd
df = pd.read_csv("data/BASE_FEATURES.csv", low_memory=False)

tous_noms = pd.concat([df["winner_name"], df["loser_name"]]).dropna().unique()

vrais_doublons = []
for nom in tous_noms:
    if ". " in str(nom) and "/" not in str(nom):
        partie = nom.split(". ", 1)
        if len(partie) == 2:
            nom_famille = partie[1].strip()
            for nom2 in tous_noms:
                if (nom2 != nom 
                    and "/" not in str(nom2)
                    and nom_famille.lower() in str(nom2).lower() 
                    and len(str(nom2)) > len(str(nom))):
                    vrais_doublons.append((nom, nom2))
                    break

print(f"Vrais doublons : {len(vrais_doublons)}")
for d in vrais_doublons[:20]:
    print(f"  '{d[0]}' <-> '{d[1]}'")
