content = open("modules/matchs_du_jour.py", encoding="utf-8").read()

content = content.replace(
    'afficher_resultat_pred(data["res"], data["j_a"], data["j_b"], detecter_surface(data.get("tournoi", "")))',
    'afficher_resultat_pred(data["res"], data["j_a"], data["j_b"], detecter_surface(data.get("tournoi", "")))\n                        st.info("💡 Pour une prediction plus precise, utilisez l\'onglet Prediction avec toutes les donnees : surface exacte, round, format et cotes du match.")'
)

open("modules/matchs_du_jour.py", "w", encoding="utf-8").write(content)
print("OK" if "onglet Prediction" in open("modules/matchs_du_jour.py", encoding="utf-8").read() else "ECHEC")
