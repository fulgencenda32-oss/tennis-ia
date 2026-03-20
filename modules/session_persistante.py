
import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta

COOKIE_NAME = "tennis_ia_session"

def get_cookie_manager():
    return stx.CookieManager()

def sauvegarder_session(uid, email, token):
    """Sauvegarde la session dans un cookie."""
    try:
        cookie_manager = get_cookie_manager()
        valeur = f"{uid}|||{email}|||{token}"
        expiry = datetime.now() + timedelta(days=30)
        cookie_manager.set(COOKIE_NAME, valeur, expires_at=expiry)
    except Exception as e:
        pass

def effacer_session_locale():
    """Efface le cookie de session."""
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.delete(COOKIE_NAME)
    except Exception as e:
        pass

def restaurer_session():
    """
    Tente de restaurer la session depuis le cookie.
    Retourne True si restauree, False sinon.
    """
    if st.session_state.get("connecte", False):
        return True
    try:
        cookie_manager = get_cookie_manager()
        valeur = cookie_manager.get(COOKIE_NAME)
        if valeur and "|||" in valeur:
            parties = valeur.split("|||")
            if len(parties) == 3:
                uid, email, token = parties
                if uid and email:
                    from modules.auth import charger_profil_utilisateur
                    profil = charger_profil_utilisateur(uid, email)
                    if profil and profil.get("actif", True):
                        st.session_state.user     = profil
                        st.session_state.token    = token
                        st.session_state.connecte = True
                        return True
    except Exception as e:
        pass
    return False
