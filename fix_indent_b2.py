lines = open("modules/prediction.py", encoding="utf-8").readlines()

# Trouver "joueur_b = st.session_state.get("joueur_b_auto")"
# et verifier que "if nom_b:" est bien indente apres "if not joueur_b:"
for i, line in enumerate(lines):
    if 'joueur_b = st.session_state.get("joueur_b_auto")' in line:
        # Verifier les lignes suivantes
        for j in range(i+1, min(i+5, len(lines))):
            if "if not joueur_b:" in lines[j]:
                # La ligne apres doit etre "if nom_b:" avec 16 espaces
                if j+1 < len(lines):
                    next_line = lines[j+1]
                    stripped = next_line.lstrip()
                    if "if nom_b:" in stripped or "suggestions_b" in stripped:
                        lines[j+1] = " " * 16 + stripped
                break
        break

open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK")
