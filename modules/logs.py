# ============================================================
# MODULE LOGS — Capture et affichage des erreurs en temps réel
# Tennis IA | Fulgence N'da
# ============================================================
import streamlit as st
import traceback
from datetime import datetime, timezone
from modules.auth import get_db

# ============================================================
# NIVEAUX DE SÉVÉRITÉ
# ============================================================
NIVEAUX = {
    "critique" : {"emoji": "🔴", "label": "Critique",      "couleur": "error"},
    "warning"  : {"emoji": "🟡", "label": "Avertissement", "couleur": "warning"},
    "info"     : {"emoji": "🔵", "label": "Info",          "couleur": "info"},
}

# ============================================================
# ENREGISTRER UNE ERREUR
# ============================================================
def log_erreur(erreur, contexte="", uid="", email="", onglet="", niveau="critique"):
    """
    Capture une erreur et la sauvegarde dans Firestore.
    À appeler dans les blocs except de l'app.

    Exemple d'utilisation :
        try:
            page_prediction(modeles, df_base)
        except Exception as e:
            from modules.logs import log_erreur
            log_erreur(e, contexte="page_prediction", onglet="Prédiction")
            st.error("Une erreur est survenue.")
    """
    try:
        db = get_db()
        if db is None:
            return

        # Récupérer infos utilisateur depuis session si non fournies
        if not uid and st.session_state.get("user"):
            uid   = st.session_state["user"].get("uid", "")
            email = st.session_state["user"].get("email", "anonyme")

        # Construire le log
        log = {
            "date"      : datetime.now(tz=timezone.utc).isoformat(),
            "niveau"    : niveau,
            "message"   : str(erreur)[:500],
            "traceback" : traceback.format_exc()[:1000],
            "contexte"  : str(contexte)[:100],
            "onglet"    : str(onglet)[:50],
            "uid"       : str(uid)[:50],
            "email"     : str(email)[:100],
            "resolu"    : False,
        }

        db.collection("logs_erreurs").add(log)

        # Vérifier si alerte critique nécessaire (5x la même erreur en 1h)
        _verifier_alerte_critique(str(erreur)[:100])

    except Exception:
        pass  # Ne jamais faire planter l'app à cause du logger


def log_info(message, contexte="", niveau="info"):
    """Log un événement informatif (non-erreur)."""
    try:
        db = get_db()
        if db is None:
            return
        db.collection("logs_erreurs").add({
            "date"     : datetime.now(tz=timezone.utc).isoformat(),
            "niveau"   : niveau,
            "message"  : str(message)[:500],
            "traceback": "",
            "contexte" : str(contexte)[:100],
            "onglet"   : "",
            "uid"      : "",
            "email"    : "",
            "resolu"   : False,
        })
    except Exception:
        pass


# ============================================================
# VÉRIFICATION ALERTE CRITIQUE
# ============================================================
def _verifier_alerte_critique(message_erreur):
    """Déclenche une alerte si la même erreur arrive 5x en 1h."""
    try:
        db = get_db()
        from datetime import timedelta
        il_y_a_1h = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        docs = (
            db.collection("logs_erreurs")
              .where("message", "==", message_erreur)
              .where("date", ">=", il_y_a_1h)
              .stream()
        )
        count = sum(1 for _ in docs)
        if count >= 5:
            # Sauvegarder alerte dans Firestore
            db.collection("alertes_critiques").document("derniere").set({
                "message"  : message_erreur,
                "count"    : count,
                "date"     : datetime.now(tz=timezone.utc).isoformat(),
                "vue"      : False,
            })
    except Exception:
        pass


# ============================================================
# SECTION ADMIN — Logs erreurs
# ============================================================
def section_logs_admin():
    st.subheader("🔴 Logs erreurs en temps réel")

    # ── Alerte critique en haut ──
    try:
        db = get_db()
        alerte_doc = db.collection("alertes_critiques").document("derniere").get()
        if alerte_doc.exists:
            alerte = alerte_doc.to_dict()
            if not alerte.get("vue", True):
                st.error(f"🚨 **ALERTE CRITIQUE** — L'erreur suivante s'est produite **{alerte.get('count')}x en 1h** :\n`{alerte.get('message')}`")
                if st.button("✅ Marquer l'alerte comme vue", key="btn_alerte_vue"):
                    db.collection("alertes_critiques").document("derniere").update({"vue": True})
                    st.rerun()
    except Exception:
        pass

    # ── Charger les logs ──
    def charger_logs(limit=200, filtre_niveau="Tous", filtre_resolu="Non résolus"):
        try:
            db = get_db()
            query = db.collection("logs_erreurs").order_by("date", direction="DESCENDING").limit(limit)
            docs  = query.stream()
            logs  = [{"id": d.id, **d.to_dict()} for d in docs]
            if filtre_niveau != "Tous":
                niveau_key = {"🔴 Critique": "critique", "🟡 Avertissement": "warning", "🔵 Info": "info"}.get(filtre_niveau, "")
                logs = [l for l in logs if l.get("niveau") == niveau_key]
            if filtre_resolu == "Non résolus":
                logs = [l for l in logs if not l.get("resolu", False)]
            elif filtre_resolu == "Résolus":
                logs = [l for l in logs if l.get("resolu", False)]
            return logs
        except Exception as e:
            st.error(f"Erreur chargement logs : {e}")
            return []

    # ── Métriques ──
    try:
        db   = get_db()
        tous = [{"id": d.id, **d.to_dict()} for d in db.collection("logs_erreurs").order_by("date", direction="DESCENDING").limit(500).stream()]
        nb_critique = sum(1 for l in tous if l.get("niveau") == "critique" and not l.get("resolu"))
        nb_warning  = sum(1 for l in tous if l.get("niveau") == "warning"  and not l.get("resolu"))
        nb_info     = sum(1 for l in tous if l.get("niveau") == "info"      and not l.get("resolu"))
        nb_resolus  = sum(1 for l in tous if l.get("resolu"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔴 Critiques (non résolus)", nb_critique)
        c2.metric("🟡 Avertissements",           nb_warning)
        c3.metric("🔵 Infos",                    nb_info)
        c4.metric("✅ Résolus",                   nb_resolus)
    except Exception:
        tous = []

    st.markdown("---")

    # ── Graphique erreurs par jour ──
    if tous:
        import plotly.graph_objects as go
        from collections import Counter
        dates_logs = {}
        for l in tous:
            jour = str(l.get("date", ""))[:10]
            niv  = l.get("niveau", "info")
            if jour:
                if jour not in dates_logs:
                    dates_logs[jour] = {"critique": 0, "warning": 0, "info": 0}
                dates_logs[jour][niv] = dates_logs[jour].get(niv, 0) + 1

        if dates_logs:
            jours   = sorted(dates_logs.keys())[-14:]
            fig_log = go.Figure()
            fig_log.add_trace(go.Bar(name="🔴 Critiques",
                x=jours, y=[dates_logs[j]["critique"] for j in jours], marker_color="#ef4444"))
            fig_log.add_trace(go.Bar(name="🟡 Warnings",
                x=jours, y=[dates_logs[j]["warning"] for j in jours], marker_color="#f59e0b"))
            fig_log.add_trace(go.Bar(name="🔵 Infos",
                x=jours, y=[dates_logs[j]["info"] for j in jours], marker_color="#3b82f6"))
            fig_log.update_layout(
                barmode="stack", height=220,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"), margin=dict(t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            )
            st.markdown("**📈 Erreurs par jour (14 derniers jours)**")
            st.plotly_chart(fig_log, use_container_width=True)

        # ── Top erreurs récurrentes ──
        st.markdown("**🔁 Erreurs les plus fréquentes**")
        messages = [l.get("message", "")[:80] for l in tous if not l.get("resolu")]
        if messages:
            compteur = Counter(messages).most_common(5)
            rows_top = [{"Erreur": msg[:60], "Occurrences": count} for msg, count in compteur]
            import pandas as pd
            st.dataframe(pd.DataFrame(rows_top), hide_index=True, use_container_width=True)

    st.markdown("---")

    # ── Filtres ──
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtre_niv = st.selectbox("Niveau", ["Tous", "🔴 Critique", "🟡 Avertissement", "🔵 Info"], key="log_niv")
    with col_f2:
        filtre_res = st.selectbox("Statut", ["Non résolus", "Résolus", "Tous"], key="log_res")
    with col_f3:
        nb_logs = st.selectbox("Nombre", [50, 100, 200], key="log_nb")

    logs = charger_logs(limit=nb_logs, filtre_niveau=filtre_niv, filtre_resolu=filtre_res)

    if not logs:
        st.success("✅ Aucune erreur trouvée !")
        return

    st.info(f"**{len(logs)}** log(s) affiché(s)")

    # ── Liste des logs ──
    for l in logs:
        niv_info = NIVEAUX.get(l.get("niveau", "info"), NIVEAUX["info"])
        lid      = l.get("id", "")
        date_str = str(l.get("date", ""))[:16].replace("T", " ")
        resolu   = l.get("resolu", False)

        with st.expander(
            f"{niv_info['emoji']} {date_str} — {l.get('message','?')[:60]}"
            + (" ✅" if resolu else "")
        ):
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                st.markdown(f"**Niveau :** {niv_info['emoji']} {niv_info['label']}")
                st.markdown(f"**Contexte :** `{l.get('contexte','—')}`")
                st.markdown(f"**Onglet :** {l.get('onglet','—')}")
            with col_i2:
                st.markdown(f"**Utilisateur :** {l.get('email','anonyme')}")
                st.markdown(f"**Date :** {date_str}")

            st.markdown(f"**Message :** `{l.get('message','—')}`")

            if l.get("traceback"):
                with st.expander("🔍 Traceback complet"):
                    st.code(l.get("traceback"), language="python")

            if not resolu:
                if st.button("✅ Marquer comme résolu", key=f"resolu_{lid}"):
                    try:
                        db = get_db()
                        db.collection("logs_erreurs").document(lid).update({
                            "resolu"     : True,
                            "date_resolu": datetime.now(tz=timezone.utc).isoformat(),
                        })
                        st.success("✅ Marqué comme résolu !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
            else:
                st.caption(f"✅ Résolu le {str(l.get('date_resolu',''))[:10]}")

    # ── Bouton purge ──
    st.markdown("---")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("🗑️ Purger tous les logs résolus", key="purge_logs"):
            try:
                db   = get_db()
                docs = db.collection("logs_erreurs").where("resolu", "==", True).stream()
                count = 0
                for doc in docs:
                    doc.reference.delete()
                    count += 1
                st.success(f"✅ {count} log(s) résolu(s) supprimé(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur purge : {e}")
    with col_p2:
        if st.button("🗑️ Purger TOUS les logs", key="purge_all_logs"):
            try:
                db   = get_db()
                docs = db.collection("logs_erreurs").limit(500).stream()
                count = 0
                for doc in docs:
                    doc.reference.delete()
                    count += 1
                st.success(f"✅ {count} log(s) supprimé(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur purge : {e}")
