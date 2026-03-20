
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

# Cle de chiffrement des cookies (fixe)
COOKIE_PASSWORD = "tennis-ia-secret-2026"

def get_cookie_manager():
    """Retourne le gestionnaire de cookies."""
    cookies = EncryptedCookieManager(prefix="tennis_ia_", password=COOKIE_PASSWORD)
    if not cookies.ready():
        st.stop()
    return cookies

def sauvegarder_session(uid, email, token):
    """Sauvegarde la session dans les cookies."""
    try:
        cookies = get_cookie_manager()
        cookies["uid"]   = uid
        cookies["email"] = email
        cookies["token"] = token
        cookies.save()
    except Exception as e:
        pass

def effacer_session_locale():
    """Efface la session des cookies."""
    try:
        cookies = get_cookie_manager()
        cookies["uid"]   = ""
        cookies["email"] = ""
        cookies["token"] = ""
        cookies.save()
    except Exception as e:
        pass

def restaurer_session():
    """
    Tente de restaurer la session depuis les cookies.
    Retourne True si restauree, False sinon.
    """
    if st.session_state.get("connecte", False):
        return True
    try:
        cookies = get_cookie_manager()
        uid   = cookies.get("uid",   "")
        email = cookies.get("email", "")
        token = cookies.get("token", "")
        if uid and email:
            from modules.auth import charger_profil_utilisateur, ADMIN_EMAIL
            profil = charger_profil_utilisateur(uid, email)
            if profil and profil.get("actif", True):
                st.session_state.user     = profil
                st.session_state.token    = token
                st.session_state.connecte = True
                return True
    except Exception as e:
        pass
    return False
