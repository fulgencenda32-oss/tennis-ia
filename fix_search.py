content = open("modules/prediction.py", encoding="utf-8").read()

# 1. Remplacer recherche_floue par version amelioree
ancien = '''def recherche_floue(nom, liste_joueurs, limite=5, seuil=55):
    if not nom or len(nom) < 2:
        return []
    resultats = process.extract(
        nom, liste_joueurs,
        scorer=fuzz.WRatio, limit=limite,
    )
    return [
        (joueur, score)
        for joueur, score, _ in resultats
        if score >= seuil
    ]'''

nouveau = '''def get_api_key():
    import os
    cles = [
        os.getenv("ALLSPORTS_API_KEY"),
        os.getenv("ALLSPORTS_API_KEY_2"),
        os.getenv("ALLSPORTS_API_KEY_3"),
    ]
    return [c for c in cles if c]

def recherche_floue(nom, liste_joueurs, limite=5, seuil=55):
    if not nom or len(nom) < 2:
        return []
    # Recherche directe
    resultats = process.extract(nom, liste_joueurs, scorer=fuzz.WRatio, limit=limite)
    bons = [(j, s) for j, s, _ in resultats if s >= seuil]
    # Si pas assez de resultats, chercher par nom de famille
    if len(bons) < 3:
        mots = nom.strip().split()
        for mot in mots:
            if len(mot) > 3:
                extras = process.extract(mot, liste_joueurs, scorer=fuzz.WRatio, limit=limite)
                for j, s, _ in extras:
                    if s >= seuil and j not in [b[0] for b in bons]:
                        bons.append((j, min(s, 85)))
    return sorted(bons, key=lambda x: x[1], reverse=True)[:limite]

def recherche_api_joueur(nom):
    cles = get_api_key()
    if not cles:
        return []
    cache_key = f"api_search_{nom.lower().strip()}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    import requests
    from datetime import datetime, timedelta
    date_fin = datetime.now().strftime("%Y-%m-%d")
    date_debut = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    for cle in cles:
        try:
            r = requests.get("https://apiv2.allsportsapi.com/tennis/", params={
                "met": "Fixtures", "APIkey": cle,
                "from": date_debut, "to": date_fin,
            }, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get("success") == 1:
                    matchs = data.get("result", [])
                    noms_trouves = []
                    mots = [m.lower() for m in nom.strip().split() if len(m) > 2]
                    for m in matchs:
                        p1 = str(m.get("event_first_player", ""))
                        p2 = str(m.get("event_second_player", ""))
                        for p in [p1, p2]:
                            if "/" not in p and any(mot in p.lower() for mot in mots):
                                if p not in noms_trouves:
                                    noms_trouves.append(p)
                    st.session_state[cache_key] = noms_trouves[:5]
                    return noms_trouves[:5]
        except:
            continue
    return []'''

content = content.replace(ancien, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "get_api_key" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
