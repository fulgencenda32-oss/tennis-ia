
import streamlit as st
from modules.auth import is_connecte, get_user, is_premium

PRIX = {
    "hebdomadaire": {"montant": 500, "label": "1 semaine", "duree": 7},
    "mensuel": {"montant": 2000, "label": "1 mois", "duree": 30},
    "annuel": {"montant": 18000, "label": "1 an (2 mois offerts)", "duree": 365},
}

WAVE_NUMBER = "+22507772650 53"
WHATSAPP_NUMBER = "22507772650 53"

def page_paiement():
    st.title("⭐ Passer Premium")
    st.markdown("---")

    if not is_connecte():
        st.warning("⚠️ Vous devez être connecté pour souscrire.")
        return

    user = get_user()

    if is_premium():
        st.success("✅ Vous êtes déjà Premium ! Profitez de toutes les fonctionnalités.")
        st.balloons()
        return

    # Header
    st.markdown("""
    <div style='text-align:center; padding:1.5rem; background:linear-gradient(135deg,#1a6b3a,#2d9e56); border-radius:16px; margin-bottom:24px;'>
        <h2 style='color:white; margin:0;'>⭐ Tennis IA Premium</h2>
        <p style='color:rgba(255,255,255,0.85); margin:8px 0 0 0;'>Prédictions illimitées + Value Bet + Analyses complètes</p>
    </div>
    """, unsafe_allow_html=True)

    # Comparaison gratuit vs premium
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **🆓 Plan Gratuit**
        - ❌ 2 prédictions/jour seulement
        - ❌ Pas de value bet
        - ❌ Accès limité
        """)
    with col2:
        st.markdown("""
        **⭐ Plan Premium**
        - ✅ Prédictions illimitées
        - ✅ Value Bet détecté
        - ✅ Toutes les fonctionnalités
        - ✅ Support prioritaire
        """)

    st.markdown("---")
    st.subheader("💰 Choisissez votre plan")

    col_h, col_m, col_a = st.columns(3)

    with col_h:
        st.markdown("""
        <div style='text-align:center; padding:20px; background:rgba(255,255,255,0.05); border:1px solid rgba(45,158,86,0.3); border-radius:12px;'>
            <h3 style='color:#4ade80;'>Hebdomadaire</h3>
            <h2 style='color:white;'>500 FCFA</h2>
            <p style='color:#888;'>1 semaine</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💳 Payer 500 FCFA", key="pay_hebdo", use_container_width=True):
            st.session_state["plan_choisi"] = "hebdomadaire"

    with col_m:
        st.markdown("""
        <div style='text-align:center; padding:20px; background:rgba(45,158,86,0.15); border:2px solid #2d9e56; border-radius:12px;'>
            <h3 style='color:#4ade80;'>⭐ Mensuel</h3>
            <h2 style='color:white;'>2 000 FCFA</h2>
            <p style='color:#888;'>1 mois — Le plus populaire</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💳 Payer 2 000 FCFA", key="pay_mensuel", use_container_width=True):
            st.session_state["plan_choisi"] = "mensuel"

    with col_a:
        st.markdown("""
        <div style='text-align:center; padding:20px; background:rgba(255,255,255,0.05); border:1px solid rgba(45,158,86,0.3); border-radius:12px;'>
            <h3 style='color:#4ade80;'>Annuel</h3>
            <h2 style='color:white;'>18 000 FCFA</h2>
            <p style='color:#888;'>1 an — 2 mois offerts !</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💳 Payer 18 000 FCFA", key="pay_annuel", use_container_width=True):
            st.session_state["plan_choisi"] = "annuel"

    # Instructions de paiement
    if st.session_state.get("plan_choisi"):
        plan = st.session_state["plan_choisi"]
        montant = PRIX[plan]["montant"]
        label = PRIX[plan]["label"]

        st.markdown("---")
        st.markdown(f"### 📱 Instructions de paiement — {montant} FCFA ({label})")

        st.info(f"""
**Étape 1 :** Envoyez **{montant} FCFA** via Wave au numéro :
## 📲 +225 07 77 26 50 53
**Nom :** Fulgence N'da

**Étape 2 :** Après le paiement, envoyez la **capture d'écran** sur WhatsApp avec votre **email de connexion Tennis IA**.

**Étape 3 :** Votre compte sera activé sous **24h**.
        """)

        # Bouton WhatsApp
        email_user = user.get("email", "")
        message = f"Bonjour, j'ai payé {montant} FCFA pour Tennis IA Premium ({label}). Mon email : {email_user}"
        wa_link = f"https://wa.me/{WHATSAPP_NUMBER}?text={message.replace(' ', '%20')}"

        st.markdown(f"""
        <a href="{wa_link}" target="_blank" style="
            display:block; text-align:center;
            background:linear-gradient(135deg,#25D366,#128C7E);
            color:white; padding:14px; border-radius:12px;
            font-size:1.1rem; font-weight:600; text-decoration:none;
            margin-top:16px;
        ">💬 Envoyer la preuve sur WhatsApp</a>
        """, unsafe_allow_html=True)

        st.caption("⚠️ Activation manuelle sous 24h après vérification du paiement.")
