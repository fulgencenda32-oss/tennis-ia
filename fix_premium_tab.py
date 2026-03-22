content = open("app.py", encoding="utf-8").read()

ancien = '''    # Ajouter onglet Admin si c\'est Fulgence N\'da
    if is_admin():
        onglets.append("\U0001f6e1\ufe0f Admin")
    tabs = st.tabs(onglets)
    with tabs[0]:
        page_matchs_jour(modeles, df_base)
    with tabs[1]:
        page_prediction(modeles, df_base)
    with tabs[2]:
        page_joueurs(modeles, df_base)
    with tabs[3]:
        page_mise_a_jour(modeles, df_base)
    with tabs[4]:
        page_historique()
    with tabs[5]:
        page_performance()
    # Panel Admin visible uniquement pour vous
    idx_premium = len(onglets) - 1
    with tabs[idx_premium]:
        page_paiement()
    if is_admin():
        with tabs[6]:
            afficher_panel_admin()'''

nouveau = '''    # Ajouter onglet Admin si c\'est Fulgence N\'da
    if is_admin():
        onglets.append("\U0001f6e1\ufe0f Admin")
    onglets.append("\u2b50 Premium")
    tabs = st.tabs(onglets)
    with tabs[0]:
        page_matchs_jour(modeles, df_base)
    with tabs[1]:
        page_prediction(modeles, df_base)
    with tabs[2]:
        page_joueurs(modeles, df_base)
    with tabs[3]:
        page_mise_a_jour(modeles, df_base)
    with tabs[4]:
        page_historique()
    with tabs[5]:
        page_performance()
    # Premium toujours en dernier
    with tabs[len(onglets) - 1]:
        page_paiement()
    # Panel Admin
    if is_admin():
        with tabs[6]:
            afficher_panel_admin()'''

content = content.replace(ancien, nouveau)
open("app.py", "w", encoding="utf-8").write(content)
print("OK" if "onglets.append" in open("app.py", encoding="utf-8").read() else "ECHEC")
