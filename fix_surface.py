content = open("modules/matchs_du_jour.py", encoding="utf-8").read()

mapping = """
SURFACE_TOURNOI = {
    # Hard
    "miami": "Hard", "australian open": "Hard", "us open": "Hard",
    "indian wells": "Hard", "cincinnati": "Hard", "montreal": "Hard",
    "toronto": "Hard", "madrid": "Hard", "dubai": "Hard",
    "doha": "Hard", "brisbane": "Hard", "auckland": "Hard",
    "beijing": "Hard", "shanghai": "Hard", "paris": "Hard",
    "vienna": "Hard", "basel": "Hard", "tokyo": "Hard",
    "washington": "Hard", "atlanta": "Hard", "los angeles": "Hard",
    # Clay
    "roland garros": "Clay", "monte carlo": "Clay", "barcelona": "Clay",
    "rome": "Clay", "hamburg": "Clay", "bucharest": "Clay",
    "estoril": "Clay", "munich": "Clay", "lyon": "Clay",
    "geneva": "Clay", "marrakech": "Clay", "casablanca": "Clay",
    "istanbul": "Clay", "bastad": "Clay", "gstaad": "Clay",
    "umag": "Clay", "kitzbuhel": "Clay", "winston-salem": "Clay",
    "roland": "Clay", "garros": "Clay",
    # Grass
    "wimbledon": "Grass", "halle": "Grass", "queens": "Grass",
    "eastbourne": "Grass", "s-hertogenbosch": "Grass", "nottingham": "Grass",
    "newport": "Grass", "mallorca": "Grass",
}

def detecter_surface(nom_tournoi):
    nom = str(nom_tournoi).lower()
    for mot, surface in SURFACE_TOURNOI.items():
        if mot in nom:
            return surface
    return "Hard"

"""

content = mapping + content
open("modules/matchs_du_jour.py", "w", encoding="utf-8").write(content)
print("OK" if "SURFACE_TOURNOI" in open("modules/matchs_du_jour.py", encoding="utf-8").read() else "ECHEC")
