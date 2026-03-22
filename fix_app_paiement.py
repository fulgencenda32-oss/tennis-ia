content = open("app.py", encoding="utf-8").read()

ancien = '''    from modules.matchs_du_jour import page_matchs_jour
    # Onglets de base
    onglets = [
        "📅 Matchs du jour",
        "🎾 Prédiction",
        "👤 Joueurs",
        "🔄 Mise à jour",
        "📚 Historique",
        "📊 Performance IA"
    ]'''

nouveau = '''    from modules.matchs_du_jour import page_matchs_jour
    from modules.paiement import page_paiement
    # Onglets de base
    onglets = [
        "📅 Matchs du jour",
        "🎾 Prédiction",
        "👤 Joueurs",
        "🔄 Mise à jour",
        "📚 Historique",
        "📊 Performance IA",
        "⭐ Premium",
    ]'''

content = content.replace(ancien, nouveau)

# Ajouter l'onglet Premium
ancien2 = '''    with tabs[5]:
        page_performance()'''

nouveau2 = '''    with tabs[5]:
        page_performance()
    with tabs[6]:
        page_paiement()'''

content = content.replace(ancien2, nouveau2)

# Corriger l'index admin
ancien3 = '''    if is_admin() and len(tabs) > 6:
        with tabs[6]:
            afficher_panel_admin()'''

nouveau3 = '''    if is_admin() and len(tabs) > 7:
        with tabs[7]:
            afficher_panel_admin()'''

content = content.replace(ancien3, nouveau3)

open("app.py", "w", encoding="utf-8").write(content)
print("OK" if "page_paiement" in open("app.py", encoding="utf-8").read() else "ECHEC")
