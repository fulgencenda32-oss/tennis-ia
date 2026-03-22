import pandas as pd
df = pd.read_csv("data/BASE_FEATURES.csv", low_memory=False)

for nom in ["T. Fritz", "Taylor Fritz", "Taylor Harry Fritz"]:
    w = len(df[df["winner_name"] == nom])
    l = len(df[df["loser_name"] == nom])
    print(f"{nom} : {w+l} matchs ({w} victoires, {l} defaites)")
