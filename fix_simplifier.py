content = open("entrainement_hebdo.py", encoding="utf-8").read()

# Ajouter simplifier_round apres les imports
ajout = """
def simplifier_round(r):
    r = str(r).lower().strip()
    if any(x in r for x in ['final', 'f']): return 5
    if any(x in r for x in ['semi', 'sf']): return 4
    if any(x in r for x in ['quarter', 'qf']): return 3
    if any(x in r for x in ['r16', '16']): return 2
    if any(x in r for x in ['r32', '32']): return 1
    if any(x in r for x in ['r64', '64']): return 0
    if any(x in r for x in ['r128', '128']): return -1
    return 1

"""

content = content.replace(
    "load_dotenv()\n",
    "load_dotenv()\n" + ajout
)
open("entrainement_hebdo.py", "w", encoding="utf-8").write(content)
print("OK" if "def simplifier_round" in open("entrainement_hebdo.py", encoding="utf-8").read() else "ECHEC")
