import pandas as pd
df = pd.read_csv("data/BASE_FEATURES.csv", low_memory=False)
fritz = df[(df["winner_name"].str.contains("Fritz", case=False, na=False)) | 
           (df["loser_name"].str.contains("Fritz", case=False, na=False))]
print(f"Matchs avec Fritz : {len(fritz)}")
if len(fritz) > 0:
    noms = set(fritz["winner_name"].tolist() + fritz["loser_name"].tolist())
    noms_fritz = [n for n in noms if "fritz" in str(n).lower()]
    print(f"Noms trouvés : {noms_fritz[:5]}")
    print(f"Dernier match : {fritz['tourney_date'].max()}")
