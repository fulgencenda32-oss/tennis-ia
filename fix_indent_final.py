lines = open("modules/prediction.py", encoding="utf-8").readlines()

new_lines = []
for i, line in enumerate(lines):
    lineno = i + 1
    if lineno == 470:
        new_lines.append("                if suggestions_a:\n")
    elif lineno in [471, 472, 473, 474]:
        new_lines.append("    " + line)
    else:
        new_lines.append(line)

open("modules/prediction.py", "w", encoding="utf-8").writelines(new_lines)
print("OK")
