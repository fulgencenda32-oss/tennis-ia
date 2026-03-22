# ============================================================
# TENNIS IA – Panel Admin complet
# Fichier : modules/admin.py
# Auteur  : Fulgence N'da
# ============================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# Réutilise get_db() déjà défini dans auth.py
from modules.auth import get_db

# ============================================================
# UTILITAIRES
# ============================================================

def _ts_to_str(val):
    """Convertit un timestamp Firestore ou une string ISO en texte lisible."""
    if val is None:
        return "—"
    try:
        if hasattr(val, "timestamp"):
            return datetime.fromtimestamp(val.timestamp(), tz=timezone.utc).strftime("%d/%m/%Y %H:%M")
        return str(val)[:16].replace("T", " ")
    except Exception:
        return str(val)


def _charger_tous_utilisateurs():
    """Retourne la liste de tous les utilisateurs depuis Firestore."""
    try:
        db = get_db()
        docs = db.collection("users").stream()
        users = []
        for doc in docs:
            d = doc.to_dict()
            d["uid"] = doc.id
            users.append(d)
        return users
    except Exception as e:
        st.error(f"Erreur lecture Firestore : {e}")
        return []


def _charger_predictions_utilisateur(uid):
    """Retourne les 50 dernières prédictions d'un utilisateur."""
    try:
        db = get_db()
        docs = (
            db.collection("predictions")
              .where("uid", "==", uid)
              .order_by("date", direction="DESCENDING")
              .limit(50)
              .stream()
        )
        return [d.to_dict() for d in docs]
    except Exception:
        return []


def _charger_toutes_predictions(limit=200):
    """Retourne les dernières prédictions toutes catégories."""
    try:
        db = get_db()
        docs = (
            db.collection("predictions")
              .order_by("date", direction="DESCENDING")
              .limit(limit)
              .stream()
        )
        return [d.to_dict() for d in docs]
    except Exception:
        return []


# ============================================================
# SECTION 1 – TABLEAU DE BORD GLOBAL
# ============================================================

def section_dashboard(users):
    st.subheader("📊 Tableau de bord global")

    total      = len(users)
    premium    = sum(1 for u in users if u.get("plan") == "premium")
    actifs     = sum(1 for u in users if u.get("actif", True))
    suspendus  = total - actifs
    pred_today = sum(u.get("predictions_aujourd_hui", 0) for u in users)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Utilisateurs",     total)
    c2.metric("⭐ Premium",          premium)
    c3.metric("🆓 Gratuit",          total - premium)
    c4.metric("🚫 Suspendus",        suspendus)
    c5.metric("🔮 Prédictions auj.", pred_today)

    st.markdown("---")

    # Graphique inscriptions par mois
    dates = []
    for u in users:
        d = u.get("date_inscription")
        if d:
            try:
                if hasattr(d, "timestamp"):
                    dates.append(datetime.fromtimestamp(d.timestamp(), tz=timezone.utc))
                else:
                    dates.append(pd.to_datetime(str(d)))
            except Exception:
                pass

    if dates:
        df_dates = pd.DataFrame({"date": dates})
        df_dates["mois"] = df_dates["date"].dt.to_period("M").astype(str)
        compte_mois = df_dates.groupby("mois").size().reset_index(name="inscriptions")
        st.markdown("**📈 Inscriptions par mois**")
        st.bar_chart(compte_mois.set_index("mois"))

    # Répartition plans
    st.markdown("**💰 Répartition des plans**")
    plans = pd.Series([u.get("plan", "gratuit") for u in users]).value_counts()
    st.bar_chart(plans)


# ============================================================
# SECTION 2 – GESTION DES UTILISATEURS
# ============================================================

def section_utilisateurs(users):
    st.subheader("👥 Gestion des utilisateurs")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtre_plan = st.selectbox("Plan", ["Tous", "gratuit", "premium"])
    with col_f2:
        filtre_actif = st.selectbox("Statut", ["Tous", "Actif", "Suspendu"])
    with col_f3:
        recherche = st.text_input("🔍 Rechercher (email / nom)")

    filtered = users[:]
    if filtre_plan != "Tous":
        filtered = [u for u in filtered if u.get("plan") == filtre_plan]
    if filtre_actif == "Actif":
        filtered = [u for u in filtered if u.get("actif", True)]
    elif filtre_actif == "Suspendu":
        filtered = [u for u in filtered if not u.get("actif", True)]
    if recherche:
        rech = recherche.lower()
        filtered = [
            u for u in filtered
            if rech in u.get("email", "").lower() or rech in u.get("nom", "").lower()
        ]

    st.info(f"**{len(filtered)}** utilisateur(s) trouvé(s)")

    if filtered:
        rows = [{
            "Email"          : u.get("email", "—"),
            "Nom"            : u.get("nom", "—"),
            "Plan"           : u.get("plan", "gratuit"),
            "Actif"          : "✅" if u.get("actif", True) else "🚫",
            "Pred. auj."     : u.get("predictions_aujourd_hui", 0),
            "Inscription"    : _ts_to_str(u.get("date_inscription")),
            "Dernière pred." : _ts_to_str(u.get("date_derniere_prediction")),
        } for u in filtered]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**⚙️ Actions sur un utilisateur**")

    emails = sorted([u.get("email", "") for u in users if u.get("email")])
    email_sel = st.selectbox("Choisir un utilisateur", ["— Sélectionner —"] + emails)

    if email_sel and email_sel != "— Sélectionner —":
        user_sel     = next((u for u in users if u.get("email") == email_sel), None)
        if user_sel:
            uid_sel      = user_sel.get("uid")
            plan_actuel  = user_sel.get("plan", "gratuit")
            actif_actuel = user_sel.get("actif", True)

            st.markdown(f"""
            > **Email :** {email_sel}
            > **Plan :** `{plan_actuel}`
            > **Statut :** {'✅ Actif' if actif_actuel else '🚫 Suspendu'}
            > **Inscrit le :** {_ts_to_str(user_sel.get('date_inscription'))}
            """)

            db = get_db()
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)

            with col_a1:
                duree = st.selectbox("Durée", ["7 jours", "30 jours", "365 jours"], key="duree_prem")
                if st.button("⭐ Activer Premium", key="btn_premium"):
                    try:
                        db.collection("users").document(uid_sel).update({
                            "plan"                    : "premium",
                            "actif"                   : True,
                            "duree_abonnement"        : duree,
                            "date_activation_premium" : datetime.now(tz=timezone.utc).isoformat()
                        })
                        st.success(f"✅ {email_sel} est Premium ({duree}) !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            with col_a2:
                if st.button("🔄 Repasser Gratuit", key="btn_gratuit"):
                    try:
                        db.collection("users").document(uid_sel).update({
                            "plan"                   : "gratuit",
                            "predictions_aujourd_hui": 0
                        })
                        st.success(f"✅ {email_sel} repassé en Gratuit.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            with col_a3:
                label_btn = "🚫 Suspendre" if actif_actuel else "✅ Réactiver"
                if st.button(label_btn, key="btn_suspend"):
                    try:
                        db.collection("users").document(uid_sel).update({"actif": not actif_actuel})
                        st.success("✅ Statut mis à jour.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            with col_a4:
                if st.button("🔁 Reset pred./jour", key="btn_reset"):
                    try:
                        db.collection("users").document(uid_sel).update({"predictions_aujourd_hui": 0})
                        st.success("✅ Compteur réinitialisé.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            with st.expander(f"📚 Prédictions de {email_sel}"):
                preds = _charger_predictions_utilisateur(uid_sel)
                if preds:
                    rows_p = [{
                        "Date"      : _ts_to_str(p.get("date")),
                        "Joueur A"  : p.get("joueur_a", "—"),
                        "Joueur B"  : p.get("joueur_b", "—"),
                        "IA predit"  : p.get("vainqueur", "-"),
                        "Surface"   : p.get("surface", "—"),
                    } for p in preds]
                    st.dataframe(pd.DataFrame(rows_p), use_container_width=True, hide_index=True)
                else:
                    st.info("Aucune prédiction pour cet utilisateur.")


# ============================================================
# SECTION 3 – HISTORIQUE GLOBAL DES PRÉDICTIONS
# ============================================================

def section_predictions():
    st.subheader("🔮 Historique global des prédictions")

    nb = st.slider("Nombre à charger", 50, 500, 100, step=50)
    preds = _charger_toutes_predictions(limit=nb)

    if not preds:
        st.info("Aucune prédiction trouvée.")
        return

    rows = [{
        "Date"      : _ts_to_str(p.get("date")),
        "Joueur A"  : p.get("joueur_a", "—"),
        "Joueur B"  : p.get("joueur_b", "—"),
        "IA predit" : p.get("vainqueur", "-"),
        "Proba"     : str(p.get("proba_v", "-")) + "%",
        "Tournoi"   : p.get("tournoi", "-"),
    } for p in preds]

    df_preds = pd.DataFrame(rows)
    st.dataframe(df_preds, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**📊 Répartition par surface**")
    st.bar_chart(df_preds["Surface"].value_counts(), height=250)


# ============================================================
# SECTION 4 – EXPORT CSV
# ============================================================

def section_export(users):
    st.subheader("📥 Export des données")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        st.markdown("**Export utilisateurs**")
        if st.button("📋 Générer CSV Utilisateurs"):
            rows = [{
                "UID"                : u.get("uid", ""),
                "Email"              : u.get("email", ""),
                "Nom"                : u.get("nom", ""),
                "Plan"               : u.get("plan", "gratuit"),
                "Actif"              : u.get("actif", True),
                "Role"               : u.get("role", "user"),
                "Predictions_jour"   : u.get("predictions_aujourd_hui", 0),
                "Date_inscription"   : _ts_to_str(u.get("date_inscription")),
                "Derniere_prediction": _ts_to_str(u.get("date_derniere_prediction")),
            } for u in users]
            csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
            st.download_button(
                label    = "⬇️ Télécharger utilisateurs.csv",
                data     = csv_bytes,
                file_name= f"tennis_ia_utilisateurs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime     = "text/csv"
            )
            st.success(f"✅ {len(rows)} utilisateurs exportés.")

    with col_e2:
        st.markdown("**Export prédictions**")
        nb_export = st.number_input("Nombre", min_value=50, max_value=5000, value=500, step=50)
        if st.button("📋 Générer CSV Prédictions"):
            preds = _charger_toutes_predictions(limit=int(nb_export))
            if preds:
                rows_p = [{
                    "Date"    : _ts_to_str(p.get("date")),
                    "UID"     : p.get("uid", ""),
                    "JoueurA" : p.get("joueur_a", ""),
                    "JoueurB" : p.get("joueur_b", ""),
                    "IA"      : p.get("vainqueur", ""),
                    "Surface" : p.get("surface", ""),
                    "Tournoi" : p.get("tournoi", ""),
                } for p in preds]
                csv_p = pd.DataFrame(rows_p).to_csv(index=False).encode("utf-8")
                st.download_button(
                    label    = "⬇️ Télécharger predictions.csv",
                    data     = csv_p,
                    file_name= f"tennis_ia_predictions_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime     = "text/csv"
                )
                st.success(f"✅ {len(preds)} prédictions exportées.")
            else:
                st.warning("Aucune prédiction à exporter.")


# ============================================================
# SECTION 5 – MESSAGE BROADCAST
# ============================================================

def section_broadcast():
    st.subheader("📢 Message broadcast")
    st.info("Ce message s'affichera à tous les utilisateurs au lancement de l'app.")

    col_b1, col_b2 = st.columns([3, 1])
    with col_b1:
        msg_type  = st.selectbox("Type", ["info", "success", "warning", "error"])
        msg_texte = st.text_area("Message", placeholder="Ex : Maintenance prévue ce soir à 22h...")
        cible     = st.selectbox("Cible", ["Tous", "Gratuit uniquement", "Premium uniquement"])

    with col_b2:
        st.markdown(" ")
        st.markdown(" ")
        if st.button("📤 Envoyer", use_container_width=True):
            if msg_texte.strip():
                try:
                    db = get_db()
                    db.collection("broadcast").document("message_actif").set({
                        "texte": msg_texte.strip(),
                        "type" : msg_type,
                        "cible": cible,
                        "date" : datetime.now(tz=timezone.utc).isoformat(),
                        "actif": True,
                    })
                    st.success("✅ Broadcast envoyé !")
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.warning("⚠️ Écris un message avant d'envoyer.")

        if st.button("🗑️ Désactiver", use_container_width=True):
            try:
                db = get_db()
                db.collection("broadcast").document("message_actif").update({"actif": False})
                st.success("✅ Broadcast désactivé.")
            except Exception as e:
                st.error(f"Erreur : {e}")


# ============================================================
# SECTION 6 – STATISTIQUES IA
# ============================================================

def section_stats_ia():
    st.subheader("🤖 Statistiques IA")

    preds = _charger_toutes_predictions(limit=500)
    if not preds:
        st.info("Pas encore assez de prédictions.")
        return

    st.metric("Total prédictions analysées", len(preds))

    tournois = pd.Series([p.get("tournoi", "Inconnu") for p in preds]).value_counts().head(10)
    st.markdown("**Top 10 tournois**")
    st.bar_chart(tournois, height=250)

    surfaces = pd.Series([p.get("surface", "Inconnu") for p in preds]).value_counts()
    st.markdown("**Repartition par surface**")
    st.bar_chart(surfaces, height=250)

    dates_pred = []
    for p in preds:
        d = p.get("date")
        if d:
            try:
                if hasattr(d, "timestamp"):
                    dates_pred.append(datetime.fromtimestamp(d.timestamp(), tz=timezone.utc).date())
                else:
                    dates_pred.append(pd.to_datetime(str(d)).date())
            except Exception:
                pass
    if dates_pred:
        counts = pd.DataFrame({"date": dates_pred}).groupby("date").size().tail(30)
        st.markdown("**Predictions par jour (30 derniers jours)**")
        st.line_chart(counts, height=250)


# ============================================================
# POINT D'ENTRÉE – appelé depuis auth.py
# ============================================================

def afficher_panel_admin_complet():
    """
    Remplace afficher_panel_admin() dans auth.py.
    Ajoute ceci dans auth.py :

        from modules.admin import afficher_panel_admin_complet

        def afficher_panel_admin():
            if not is_admin():
                return
            afficher_panel_admin_complet()
    """
    st.markdown("## 🛡️ Panel Administrateur")
    st.caption("Accès réservé · Fulgence N'da")
    st.markdown("---")

    with st.spinner("Chargement des données..."):
        users = _charger_tous_utilisateurs()

    admin_tabs = st.tabs([
        "📊 Dashboard",
        "👥 Utilisateurs",
        "🔮 Prédictions",
        "📥 Export CSV",
        "📢 Broadcast",
        "🤖 Stats IA",
    ])

    with admin_tabs[0]: section_dashboard(users)
    with admin_tabs[1]: section_utilisateurs(users)
    with admin_tabs[2]: section_predictions()
    with admin_tabs[3]: section_export(users)
    with admin_tabs[4]: section_broadcast()
    with admin_tabs[5]: section_stats_ia()
