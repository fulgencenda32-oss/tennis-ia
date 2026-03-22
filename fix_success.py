lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "profit = round(info" in line:
        # Verifier si st.success manque sur la ligne suivante
        if i+1 < len(lines) and lines[i+1].strip().startswith('f"'):
            lines.insert(i+1, "                    st.success(\n")
        break

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
