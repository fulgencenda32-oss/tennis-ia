lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "suggestions_b = recherche_floue" in line:
        # Verifier indentation - doit etre 16 espaces
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        if current_indent < 16:
            lines[i] = " " * 16 + stripped
        break

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
