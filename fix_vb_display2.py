content = open("modules/prediction.py", encoding="utf-8").read()

ancien = '''            # Value bet
            if res[\'value_bet_info\']:
                for info in res[\'value_bet_info\']:
                    st.success(
                        f"💰 VALUE BET sur **{info[\'joueur\']}** "
                        f"— Cote bookmaker : {info[\'cote\']} "
                        f"— Probabilite IA : {info[\'proba\']}% "
                        f"— Valeur : **+{info[\'valeur\']}%**"
                    )
            elif utiliser_cotes:
                st.info("❌ Pas de value bet detecte")'''

nouveau = '''            # Value bet
            if res[\'value_bet_info\']:
                st.markdown("---")
                for info in res[\'value_bet_info\']:
                    profit = round(info[\'valeur\'] * 100)
                    st.success(
                        f"💰 **VALUE BET detecte sur {info[\'joueur\']}**\\n\\n"
                        f"- IA predit : **{info[\'proba\']}%** de chances\\n"
                        f"- Bookmaker estime : **{round(100/info[\'cote\'], 1)}%** (cote {info[\'cote\']})\\n"
                        f"- Avantage mathematique : **+{info[\'valeur\']}%**\\n"
                        f"- Pour 10 000 FCFA mises → profit espere **{profit} FCFA**"
                    )
                st.warning(
                    "⚠️ Un value bet est une opportunite mathematique sur le long terme "
                    "— pas une garantie de victoire pour ce match specifique."
                )
            elif utiliser_cotes:
                st.info("❌ Pas de value bet detecte — les cotes sont bien calibrees par rapport a la prediction IA.")'''

content = content.replace(ancien, nouveau)
open("modules/prediction.py", "w", encoding="utf-8").write(content)
print("OK" if "opportunite mathematique" in open("modules/prediction.py", encoding="utf-8").read() else "ECHEC")
