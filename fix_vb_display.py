lines = open("modules/prediction.py", encoding="utf-8").readlines()

for i, line in enumerate(lines):
    if "# Value bet" in line and i > 600:
        insert_at = i
        break

nouveau = """
            # Comparaison IA vs Bookmaker + Value Bet
            if utiliser_cotes and cote_a and cote_b and cote_a > 1 and cote_b > 1:
                st.markdown("---")
                st.markdown("**📊 Prédiction IA vs Bookmaker**")

                # Calcul probas bookmaker normalisees
                raw_a = 1 / cote_a
                raw_b = 1 / cote_b
                total_raw = raw_a + raw_b
                prob_bk_a = round(raw_a / total_raw * 100, 1)
                prob_bk_b = round(raw_b / total_raw * 100, 1)

                col_ia, col_bk = st.columns(2)
                with col_ia:
                    st.markdown("**🤖 IA**")
                    st.metric(joueur_a, f"{res['proba_a']}%")
                    st.metric(joueur_b, f"{res['proba_b']}%")
                with col_bk:
                    st.markdown("**📊 Bookmaker**")
                    st.metric(joueur_a, f"{prob_bk_a}%", f"cote {cote_a}")
                    st.metric(joueur_b, f"{prob_bk_b}%", f"cote {cote_b}")

"""

lines.insert(insert_at, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").writelines(lines)
print("OK" if "Prediction IA vs Bookmaker" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
