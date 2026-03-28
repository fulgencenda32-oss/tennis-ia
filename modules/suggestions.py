# ============================================================
# MODULE SUGGESTIONS — Espace suggestions utilisateurs
# Tennis IA | Fulgence N'da
# ============================================================
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from modules.auth import get_db, get_user, is_connecte

# ============================================================
# UTILITAIRES
# ============================================================

def _today_str():
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

def _ts_to_str(val):
    if val is None:
        return "—"
    try:
        if hasattr(val, "timestamp"):
            return datetime.fromtimestamp(val.timestamp(), tz=timezone.utc).strftime("%d/%m/%Y %H:%M")
        return str(val)[:16].replace("T", " ")
    except Exception:
        return str(val)

# ============================================================
# LECTURE / ÉCRITURE FIRESTORE
# ============================================================

def _charger_suggestions(limit=100):
    try:
        db = get_db()
        docs = db.collection("suggestions").order_by(
            "votes", direction="DESCENDING"
        ).limit(limit).stream()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception:
        return []

def _sauvegarder_suggestion(suggestion):
    try:
        db = get_db()
        db.collection("suggestions").add(suggestion)
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")
        return False

def _voter(suggestion_id, uid):
    try:
        db = get_db()
        ref = db.collection("suggestions").document(suggestion_id)
        doc = ref.get()
        if not doc.exists:
            return False
        data = doc.to_dict()
        votants = data.get("votants", [])
        if uid in votants:
            return False  # déjà voté
        votants.append(uid)
        ref.update({"votes": len(votants), "votants": votants})
        return True
    except Exception as e:
        st.error(f"Erreur vote : {e}")
        return False

def _mettre_a_jour_statut(suggestion_id, nouveau_statut, reponse_admin=""):
    try:
        db = get_db()
        data = {"statut": nouveau_statut}
        if reponse_admin:
            data["reponse_admin"] = reponse_admin
            data["date_reponse"]  = datetime.now(tz=timezone.utc).isoformat()
        db.collection("suggestions").document(suggestion_id).update(data)
        return True
    except Exception as e:
        st.error(f"Erreur mise à jour : {e}")
        return False

def _supprimer_suggestion(suggestion_id):
    try:
        db = get_db()
        db.collection("suggestions").document(suggestion_id).delete()
        return True
    except Exception as e:
        st.error(f"Erreur suppression : {e}")
        return False

# ============================================================
# PAGE SUGGESTIONS (côté utilisateur)
# ============================================================

def page_suggestions():
    st.title("💡 Suggestions & Retours")
    st.markdown("---")

    if not is_connecte():
        st.warning("⚠️ Connectez-vous pour soumettre une suggestion.")
        return

    user = get_user()
    uid  = user.get("uid", "")

    # Limite 1 suggestion par jour
    derniere = user.get("derniere_suggestion", "")
    peut_suggerer = (derniere != _today_str())

    # ── Formulaire soumission ──
    st.subheader("📝 Soumettre une suggestion")

    if not peut_suggerer:
        st.info("⏳ Vous avez déjà soumis une suggestion aujourd'hui. Revenez demain !")
    else:
        categorie = st.selectbox(
            "Catégorie",
            ["🚀 Nouvelle fonctionnalité", "🐛 Bug", "❓ Question", "💬 Autre"]
        )
        titre = st.text_input("Titre de votre suggestion", placeholder="Ex: Ajouter les stats de double")
        description = st.text_area(
            "Description",
            placeholder="Décrivez votre idée ou le problème rencontré...",
            height=120
        )

        if st.button("📤 Envoyer ma suggestion", type="primary"):
            if not titre.strip():
                st.warning("⚠️ Donnez un titre à votre suggestion.")
            elif not description.strip():
                st.warning("⚠️ Ajoutez une description.")
            else:
                suggestion = {
                    "uid"        : uid,
                    "email"      : user.get("email", "Anonyme"),
                    "categorie"  : categorie,
                    "titre"      : titre.strip(),
                    "description": description.strip(),
                    "votes"      : 0,
                    "votants"    : [],
                    "statut"     : "📥 Reçue",
                    "reponse_admin": "",
                    "date"       : datetime.now(tz=timezone.utc).isoformat(),
                }
                if _sauvegarder_suggestion(suggestion):
                    # Mettre à jour date dernière suggestion
                    try:
                        db = get_db()
                        db.collection("users").document(uid).update({
                            "derniere_suggestion": _today_str()
                        })
                    except Exception:
                        pass
                    st.success("✅ Suggestion envoyée ! Merci pour votre retour.")
                    st.rerun()

    st.markdown("---")

    # ── Liste des suggestions ──
    st.subheader("🗳️ Toutes les suggestions")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtre_cat = st.selectbox("Filtrer par catégorie",
            ["Toutes", "🚀 Nouvelle fonctionnalité", "🐛 Bug", "❓ Question", "💬 Autre"])
    with col_f2:
        filtre_statut = st.selectbox("Filtrer par statut",
            ["Tous", "📥 Reçue", "🔍 En étude", "🛠️ En développement", "✅ Déployée"])

    suggestions = _charger_suggestions()

    if filtre_cat != "Toutes":
        suggestions = [s for s in suggestions if s.get("categorie") == filtre_cat]
    if filtre_statut != "Tous":
        suggestions = [s for s in suggestions if s.get("statut") == filtre_statut]

    if not suggestions:
        st.info("Aucune suggestion trouvée. Soyez le premier à en soumettre une !")
        return

    for s in suggestions:
        sid      = s.get("id", "")
        votes    = s.get("votes", 0)
        statut   = s.get("statut", "📥 Reçue")
        a_vote   = uid in s.get("votants", [])
        est_mien = s.get("uid") == uid

        with st.container():
            col_v, col_c = st.columns([1, 8])

            with col_v:
                st.markdown(f"<div style='text-align:center; padding:10px; background:rgba(45,158,86,0.15); border-radius:10px; margin-top:8px;'><b style='font-size:1.3rem; color:#4ade80'>{votes}</b><br><small>votes</small></div>", unsafe_allow_html=True)
                if not a_vote and not est_mien and sid:
                    if st.button("👍", key=f"vote_{sid}", help="Voter pour cette suggestion"):
                        if _voter(sid, uid):
                            st.success("Vote enregistré !")
                            st.rerun()
                elif a_vote:
                    st.caption("✅ Voté")

            with col_c:
                st.markdown(f"**{s.get('categorie','')} — {s.get('titre','')}**")
                st.caption(f"{statut} · {_ts_to_str(s.get('date'))} · par {s.get('email','?')[:25]}")
                st.markdown(s.get("description", ""))
                if s.get("reponse_admin"):
                    st.success(f"💬 Réponse : {s.get('reponse_admin')}")

            st.divider()

# ============================================================
# SECTION ADMIN — Gestion des suggestions
# ============================================================

def section_suggestions_admin():
    st.subheader("💡 Gestion des suggestions")

    suggestions = _charger_suggestions(limit=200)

    if not suggestions:
        st.info("Aucune suggestion reçue pour l'instant.")
        return

    # ── Métriques ──
    total     = len(suggestions)
    recues    = sum(1 for s in suggestions if s.get("statut") == "📥 Reçue")
    en_cours  = sum(1 for s in suggestions if s.get("statut") == "🛠️ En développement")
    deployees = sum(1 for s in suggestions if s.get("statut") == "✅ Déployée")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total",          total)
    c2.metric("📥 Reçues",         recues)
    c3.metric("🛠️ En dev",         en_cours)
    c4.metric("✅ Déployées",       deployees)

    st.markdown("---")

    # ── Filtres ──
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtre_cat = st.selectbox("Catégorie",
            ["Toutes", "🚀 Nouvelle fonctionnalité", "🐛 Bug", "❓ Question", "💬 Autre"],
            key="admin_filtre_cat")
    with col_f2:
        filtre_statut = st.selectbox("Statut",
            ["Tous", "📥 Reçue", "🔍 En étude", "🛠️ En développement", "✅ Déployée"],
            key="admin_filtre_statut")

    if filtre_cat != "Toutes":
        suggestions = [s for s in suggestions if s.get("categorie") == filtre_cat]
    if filtre_statut != "Tous":
        suggestions = [s for s in suggestions if s.get("statut") == filtre_statut]

    st.info(f"**{len(suggestions)}** suggestion(s) affichée(s) — triées par votes")

    # ── Tableau résumé ──
    rows = [{
        "Titre"     : s.get("titre", "—")[:40],
        "Catégorie" : s.get("categorie", "—"),
        "Votes"     : s.get("votes", 0),
        "Statut"    : s.get("statut", "—"),
        "Date"      : _ts_to_str(s.get("date")),
        "Email"     : s.get("email", "—")[:25],
    } for s in suggestions]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("---")

    # ── Gérer chaque suggestion ──
    st.markdown("**⚙️ Gérer une suggestion**")
    titres = [f"[{s.get('votes',0)} votes] {s.get('titre','—')[:50]}" for s in suggestions]
    choix  = st.selectbox("Choisir une suggestion", ["— Sélectionner —"] + titres, key="admin_choix_sugg")

    if choix and choix != "— Sélectionner —":
        idx = titres.index(choix)
        s   = suggestions[idx]
        sid = s.get("id", "")

        st.markdown(f"""
        > **Titre :** {s.get('titre')}
        > **Catégorie :** {s.get('categorie')}
        > **Description :** {s.get('description')}
        > **Votes :** {s.get('votes', 0)}
        > **Statut actuel :** {s.get('statut')}
        > **Soumis par :** {s.get('email')} le {_ts_to_str(s.get('date'))}
        """)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            nouveau_statut = st.selectbox("Changer le statut",
                ["📥 Reçue", "🔍 En étude", "🛠️ En développement", "✅ Déployée"],
                key="admin_nouveau_statut")
        with col_s2:
            reponse = st.text_input("Réponse publique (optionnel)",
                placeholder="Ex: Sera disponible dans la v6 !",
                key="admin_reponse")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Mettre à jour", type="primary", key="admin_update_sugg"):
                if _mettre_a_jour_statut(sid, nouveau_statut, reponse):
                    st.success(f"✅ Suggestion mise à jour → {nouveau_statut}")
                    st.rerun()
        with col_btn2:
            if st.button("🗑️ Supprimer", key="admin_delete_sugg"):
                if _supprimer_suggestion(sid):
                    st.success("✅ Suggestion supprimée.")
                    st.rerun()
