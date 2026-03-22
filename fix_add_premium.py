lines = open("app.py", encoding="utf-8").readlines()
for i, line in enumerate(lines):
    if 'onglets.append("\U0001f6e1\ufe0f Admin")' in line or "Admin" in line and "onglets.append" in line:
        lines.insert(i + 1, '    onglets.append("\u2b50 Premium")\n')
        break
open("app.py", "w", encoding="utf-8").writelines(lines)
print("OK" if '\u2b50 Premium' in open("app.py", encoding="utf-8").read() else "ECHEC")
