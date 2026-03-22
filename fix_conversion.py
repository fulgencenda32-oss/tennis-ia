lines = open("entrainement_hebdo.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "statut not in" in line:
        lines[i] = "    if statut not in ['finished', 'fin', 'ft', 'retired', 'walk over']:\n"
    if "sets = re.findall" in line:
        lines[i] = "    sets = re.findall(r'(\\d+)\\s*-\\s*(\\d+)', score_raw)\n"
        break

open("entrainement_hebdo.py", "w", encoding="utf-8").writelines(lines)

content = open("entrainement_hebdo.py", encoding="utf-8").read()
print("OK statut :", "retired" in content)
print("OK score  :", r"\s*-\s*" in content)
