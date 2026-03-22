content = open("app.py", encoding="utf-8").read()

# Mettre Premium avant Admin dans la liste
content = content.replace(
    '''    onglets = [
        "📅 Matchs du jour",
        "🎾 Prédiction",
        "👤 Joueurs",
        "🔄 Mise à jour",
        "📚 Historique",
        "📊 Performance IA",
        "⭐ Premium",
    ]
    # Ajouter onglet Admin si c\'est Fulgence N\'da
    if is_admin():
        onglets.append("🛡️ Admin")''',
    '''    onglets = [
        "📅 Matchs du jour",
        "🎾 Prédiction",
        "👤 Joueurs",
        "🔄 Mise à jour",
        "📚 Historique",
        "📊 Performance IA",
    ]
    # Ajouter onglet Admin si c\'est Fulgence N\'da
    if is_admin():
        onglets.append("🛡️ Admin")
    onglets.append("⭐ Premium")'''
)

# Corriger les index
content = content.replace(
    "    with tabs[6]:\n        page_paiement()\n",
    ""
)

# Ajouter Premium apres Admin
content = content.replace(
    "    if is_admin() and len(tabs) >= 8:\n        with tabs[7]:\n            afficher_panel_admin()",
    "    idx_premium = len(onglets) - 1\n    with tabs[idx_premium]:\n        page_paiement()\n    if is_admin():\n        with tabs[6]:\n            afficher_panel_admin()"
)

open("app.py", "w", encoding="utf-8").write(content)
print("OK" if "idx_premium" in open("app.py", encoding="utf-8").read() else "ECHEC")
