lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    # Supprimer le st.success( orphelin
    if line.strip() == "st.success(":
        lines[i] = ""
    # Supprimer la ligne avec juste un guillemet
    if line.strip() == '"' or line.strip() == "'":
        lines[i] = ""
    # Supprimer la parenthese fermante orpheline apres
    if i > 0 and lines[i-1] == "" and line.strip() == ")":
        lines[i] = ""

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
