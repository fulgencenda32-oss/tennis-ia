
import streamlit as st
import streamlit.components.v1 as components
from modules.auth import charger_profil_utilisateur, ADMIN_EMAIL

def sauvegarder_session(uid, email, token):
    """Sauvegarde la session dans localStorage."""
    components.html(f"""
    <script>
        localStorage.setItem('tennis_ia_uid',   '{uid}');
        localStorage.setItem('tennis_ia_email', '{email}');
        localStorage.setItem('tennis_ia_token', '{token}');
    </script>
    """, height=0)

def effacer_session_locale():
    """Efface la session du localStorage."""
    components.html("""
    <script>
        localStorage.removeItem('tennis_ia_uid');
        localStorage.removeItem('tennis_ia_email');
        localStorage.removeItem('tennis_ia_token');
    </script>
    """, height=0)

def restaurer_session():
    """
    Tente de restaurer la session depuis localStorage.
    Retourne True si restauree, False sinon.
    """
    if st.session_state.get('connecte', False):
        return True

    components.html("""
    <script>
        const uid   = localStorage.getItem('tennis_ia_uid')   || '';
        const email = localStorage.getItem('tennis_ia_email') || '';
        const token = localStorage.getItem('tennis_ia_token') || '';
        const input = window.parent.document.querySelector('input[data-testid="stTextInput-session_restore"]');
        if (input && uid) {
            input.value = uid + '|||' + email + '|||' + token;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    </script>
    """, height=0)

    val = st.text_input("", key="session_restore", label_visibility="collapsed")
    if val and '|||' in val:
        parties = val.split('|||')
        if len(parties) == 3:
            uid, email, token = parties
            if uid and email:
                try:
                    profil = charger_profil_utilisateur(uid, email)
                    if profil and profil.get('actif', True):
                        st.session_state.user     = profil
                        st.session_state.token    = token
                        st.session_state.connecte = True
                        return True
                except:
                    pass
    return False
