import os, requests
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("ALLSPORTS_API_KEY", "")

r = requests.get("https://apiv2.allsportsapi.com/tennis/", params={
    "met": "Fixtures",
    "APIkey": key,
    "from": "2026-03-22",
    "to": "2026-03-22",
}, timeout=30)

data = r.json()
matchs = data.get("result", [])

print(f"Total matchs : {len(matchs)}")
for m in matchs[:5]:
    print(f"\nTournoi : {m.get('league_name')}")
    print(f"Surface : {m.get('surface') or m.get('event_surface') or 'NON TROUVE'}")
    print(f"Tous les champs : {list(m.keys())}")
    break
