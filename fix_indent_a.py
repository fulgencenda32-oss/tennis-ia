lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "if suggestions_a:" in line and i > 400:
        # Verifier l indentation
        indent = len(line) - len(line.lstrip())
        # Doit etre dans le if nom_a (12 espaces minimum)
        if indent < 16:
            lines[i] = " " * 16 + "if suggestions_a:\n"
        break

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
