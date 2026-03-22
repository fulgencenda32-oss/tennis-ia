import os, requests
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("ALLSPORTS_API_KEY", "")

r = requests.get("https://apiv2.allsportsapi.com/tennis/", params={
    "met": "Fixtures",
    "APIkey": key,
    "from": "2026-03-15",
    "to": "2026-03-22",
}, timeout=30)

data = r.json()
matchs = data.get("result", [])

# Afficher les statuts uniques
statuts = set()
for m in matchs:
    statuts.add(str(m.get("event_status", "")))

print(f"Statuts uniques trouves ({len(statuts)}) :")
for s in sorted(statuts):
    print(f"  '{s}'")

# Afficher un exemple de match termine
for m in matchs[:50]:
    score = m.get("event_final_result", "")
    statut = m.get("event_status", "")
    if score and score != "0 - 0":
        print(f"\nExemple match avec score :")
        print(f"  Statut : '{statut}'")
        print(f"  Score : '{score}'")
        print(f"  Joueurs : {m.get('event_first_player')} vs {m.get('event_second_player')}")
        break
