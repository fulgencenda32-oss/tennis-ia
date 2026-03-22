contenu = """
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
    st.title("\u2b50 Passer Premium")
    st.markdown("---")

    if not is_connecte():
        st.warning("\u26a0\ufe0f Vous devez \u00eatre connect\u00e9 pour souscrire.")
        return

    user = get_user()

    if is_premium():
        st.success("\u2705 Vous \u00eates d\u00e9j\u00e0 Premium ! Profitez de toutes les fonctionnalit\u00e9s.")
        st.balloons()
        return

    # Header
    st.markdown(\"\"\"
    <div style='text-align:center; padding:1.5rem; background:linear-gradient(135deg,#1a6b3a,#2d9e56); border-radius:16px; margin-bottom:24px;'>
        <h2 style='color:white; margin:0;'>\u2b50 Tennis IA Premium</h2>
        <p style='color:rgba(255,255,255,0.85); margin:8px 0 0 0;'>Pr\u00e9dictions illimit\u00e9es + Value Bet + Analyses compl\u00e8tes</p>
    </div>
    \"\"\", unsafe_allow_html=True)

    # Comparaison gratuit vs premium
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(\"\"\"
        **\U0001f193 Plan Gratuit**
        - \u274c 2 pr\u00e9dictions/jour seulement
        - \u274c Pas de value bet
        - \u274c Acc\u00e8s limit\u00e9
        \"\"\")
    with col2:
        st.markdown(\"\"\"
        **\u2b50 Plan Premium**
        - \u2705 Pr\u00e9dictions illimit\u00e9es
        - \u2705 Value Bet d\u00e9tect\u00e9
        - \u2705 Toutes les fonctionnalit\u00e9s
        - \u2705 Support prioritaire
        \"\"\")

    st.markdown("---")
    st.subheader("\U0001f4b0 Choisissez votre plan")

    col_h, col_m, col_a = st.columns(3)

    with col_h:
        st.markdown(\"\"\"
        <div style='text-align:center; padding:20px; background:rgba(255,255,255,0.05); border:1px solid rgba(45,158,86,0.3); border-radius:12px;'>
            <h3 style='color:#4ade80;'>Hebdomadaire</h3>
            <h2 style='color:white;'>500 FCFA</h2>
            <p style='color:#888;'>1 semaine</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        if st.button("\U0001f4b3 Payer 500 FCFA", key="pay_hebdo", use_container_width=True):
            st.session_state["plan_choisi"] = "hebdomadaire"

    with col_m:
        st.markdown(\"\"\"
        <div style='text-align:center; padding:20px; background:rgba(45,158,86,0.15); border:2px solid #2d9e56; border-radius:12px;'>
            <h3 style='color:#4ade80;'>\u2b50 Mensuel</h3>
            <h2 style='color:white;'>2 000 FCFA</h2>
            <p style='color:#888;'>1 mois — Le plus populaire</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        if st.button("\U0001f4b3 Payer 2 000 FCFA", key="pay_mensuel", use_container_width=True):
            st.session_state["plan_choisi"] = "mensuel"

    with col_a:
        st.markdown(\"\"\"
        <div style='text-align:center; padding:20px; background:rgba(255,255,255,0.05); border:1px solid rgba(45,158,86,0.3); border-radius:12px;'>
            <h3 style='color:#4ade80;'>Annuel</h3>
            <h2 style='color:white;'>18 000 FCFA</h2>
            <p style='color:#888;'>1 an — 2 mois offerts !</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        if st.button("\U0001f4b3 Payer 18 000 FCFA", key="pay_annuel", use_container_width=True):
            st.session_state["plan_choisi"] = "annuel"

    # Instructions de paiement
    if st.session_state.get("plan_choisi"):
        plan = st.session_state["plan_choisi"]
        montant = PRIX[plan]["montant"]
        label = PRIX[plan]["label"]

        st.markdown("---")
        st.markdown(f"### \U0001f4f1 Instructions de paiement — {montant} FCFA ({label})")

        st.info(f\"\"\"
**\u00c9tape 1 :** Envoyez **{montant} FCFA** via Wave au num\u00e9ro :
## \U0001f4f2 +225 07 77 26 50 53
**Nom :** Fulgence N\'da

**\u00c9tape 2 :** Apr\u00e8s le paiement, envoyez la **capture d\'\u00e9cran** sur WhatsApp avec votre **email de connexion Tennis IA**.

**\u00c9tape 3 :** Votre compte sera activ\u00e9 sous **24h**.
        \"\"\")

        # Bouton WhatsApp
        email_user = user.get("email", "")
        message = f"Bonjour, j\'ai pay\u00e9 {montant} FCFA pour Tennis IA Premium ({label}). Mon email : {email_user}"
        wa_link = f"https://wa.me/{WHATSAPP_NUMBER}?text={message.replace(' ', '%20')}"

        st.markdown(f\"\"\"
        <a href="{wa_link}" target="_blank" style="
            display:block; text-align:center;
            background:linear-gradient(135deg,#25D366,#128C7E);
            color:white; padding:14px; border-radius:12px;
            font-size:1.1rem; font-weight:600; text-decoration:none;
            margin-top:16px;
        ">\U0001f4ac Envoyer la preuve sur WhatsApp</a>
        \"\"\", unsafe_allow_html=True)

        st.caption("\u26a0\ufe0f Activation manuelle sous 24h apr\u00e8s v\u00e9rification du paiement.")
"""
open("modules/paiement.py", "w", encoding="utf-8").write(contenu)
print("OK")
