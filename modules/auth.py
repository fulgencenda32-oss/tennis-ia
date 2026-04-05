"""
auth.py — Module d'authentification Firebase pour Tennis IA
Auteur : Fulgence N'da

Corrections :
- Missing Submit Button → afficher_reset_password() dans st.form
- Quota Firebase 429 → cache local + fallback JSON + rotation
- Anonyme limité → pas d'accès Premium
- Anti-reset compteur anonyme → cookie persistant
"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, date, timedelta
import os
import json
import requests
import time

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ADMIN_EMAIL  = "fulgencenda32@gmail.com"
ADMIN_NAME   = "Fulgence N'da"
MODE_PAYANT  = True

LIMITE_PREDICTIONS_GRATUITES = 2
LIMITE_PREDICTIONS_ANONYME   = 2
BONUS_INSCRIPTION            = 5
DUREE_MODE_INVITE_JOURS      = 3

FIREBASE_API_KEY    = os.getenv("FIREBASE_API_KEY", "") or "AIzaSyA0rB2KDA4hyiEFoPTctapHDCDV98iOGW4"
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "tennis-ia")

# ─────────────────────────────────────────────
# CACHE GLOBAL FIREBASE — Anti quota 429
# ─────────────────────────────────────────────

_FIREBASE_DB_CACHE  = None
_FIREBASE_ERR_TIME  = 0
_FIREBASE_INIT_DONE = False
_FIREBASE_COOLDOWN  = 300  # 5 minutes de pause après erreur 429

# ─────────────────────────────────────────────
# INITIALISATION FIREBASE
# ─────────────────────────────────────────────

def init_firebase():
    global _FIREBASE_INIT_DONE
    if _FIREBASE_INIT_DONE:
        return True
    if not firebase_admin._apps:
        try:
            cred_path = "data/firebase_key.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            elif os.getenv('FIREBASE_KEY'):
                cle_json = json.loads(os.getenv('FIREBASE_KEY'))
                cred = credentials.Certificate(cle_json)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
            _FIREBASE_INIT_DONE = True
        except Exception:
            return False
    else:
        _FIREBASE_INIT_DONE = True
    return True


def get_db():
    """
    Retourne le client Firestore avec protection anti-429.
    Attend 5 minutes après une erreur avant de réessayer.
    """
    global _FIREBASE_DB_CACHE, _FIREBASE_ERR_TIME
    if _FIREBASE_ERR_TIME and (time.time() - _FIREBASE_ERR_TIME) < _FIREBASE_COOLDOWN:
        return None
    if _FIREBASE_DB_CACHE is not None:
        return _FIREBASE_DB_CACHE
    try:
        if not init_firebase():
            return None
        _FIREBASE_DB_CACHE = firestore.client()
        return _FIREBASE_DB_CACHE
    except Exception as e:
        err = str(e).lower()
        if "429" in str(e) or "quota" in err or "exceeded" in err:
            _FIREBASE_ERR_TIME = time.time()
        return None


def firebase_lire_avec_cache(collection, doc_id, duree_cache_sec=300):
    """
    Lit un document Firestore avec cache session de 5 minutes.
    Réduit drastiquement les appels Firebase.
    """
    cache_key  = f"_fb_{collection}_{doc_id}"
    time_key   = f"_fb_t_{collection}_{doc_id}"

    if cache_key in st.session_state and time_key in st.session_state:
        age = (datetime.now() - st.session_state[time_key]).total_seconds()
        if age < duree_cache_sec:
            return st.session_state[cache_key]

    try:
        db = get_db()
        if db:
            doc = db.collection(collection).document(doc_id).get()
            data = doc.to_dict() if doc.exists else None
            st.session_state[cache_key] = data
            st.session_state[time_key]  = datetime.now()
            return data
    except Exception as e:
        err = str(e).lower()
        if "429" in str(e) or "quota" in err:
            global _FIREBASE_ERR_TIME
            _FIREBASE_ERR_TIME = time.time()
        if cache_key in st.session_state:
            return st.session_state[cache_key]
    return None

# ─────────────────────────────────────────────
# SESSION STREAMLIT
# ─────────────────────────────────────────────

def init_session():
    for k, v in [("user", None), ("token", None), ("connecte", False)]:
        if k not in st.session_state:
            st.session_state[k] = v

def is_connecte():
    return st.session_state.get("connecte", False)

def get_user():
    return st.session_state.get("user", None)

def is_admin():
    user = get_user()
    return user.get("email") == ADMIN_EMAIL if user else False

def is_premium():
    if is_admin():
        return True
    user = get_user()
    return user.get("plan") == "premium" if user else False

def is_anonyme():
    user = get_user()
    if not user:
        return True
    email = user.get("email", "")
    return not email or email == "anonyme@tennis-ia.app" or email == ""

def get_niveau_utilisateur():
    if is_admin():    return "admin"
    if is_premium():  return "premium"
    if is_anonyme():  return "anonyme"
    return "gratuit"

# ─────────────────────────────────────────────
# PERMISSIONS PREMIUM
# ─────────────────────────────────────────────

def peut_voir_ia_supreme():
    return is_admin() or is_premium()

def peut_voir_consensus():
    return is_admin() or is_premium()

def peut_voir_value_bet_detail():
    return is_admin() or is_premium()

# ─────────────────────────────────────────────
# MODE INVITÉ — 3 jours
# ─────────────────────────────────────────────

def get_jours_restants_invite():
    user = get_user()
    if not user or not is_anonyme():
        return -1
    date_inscription = user.get("date_inscription", "")
    if not date_inscription:
        return DUREE_MODE_INVITE_JOURS
    try:
        date_debut     = datetime.fromisoformat(date_inscription)
        date_expiration = date_debut + timedelta(days=DUREE_MODE_INVITE_JOURS)
        delta          = date_expiration - datetime.now()
        if delta.total_seconds() <= 0:
            return 0
        return max(0, delta.days + (1 if delta.seconds > 0 else 0))
    except:
        return DUREE_MODE_INVITE_JOURS

def get_temps_restant_invite_str():
    user = get_user()
    if not user or not is_anonyme():
        return ""
    date_inscription = user.get("date_inscription", "")
    if not date_inscription:
        return f"{DUREE_MODE_INVITE_JOURS}j 0h"
    try:
        date_debut     = datetime.fromisoformat(date_inscription)
        date_expiration = date_debut + timedelta(days=DUREE_MODE_INVITE_JOURS)
        delta          = date_expiration - datetime.now()
        if delta.total_seconds() <= 0:
            return "Expiré"
        return f"{delta.days}j {delta.seconds // 3600}h"
    except:
        return f"{DUREE_MODE_INVITE_JOURS}j 0h"

def mode_invite_expire():
    return is_anonyme() and get_jours_restants_invite() == 0

def afficher_popup_inscription():
    st.markdown("""
    <div style='background:linear-gradient(135deg,rgba(45,158,86,0.2),rgba(45,158,86,0.05));
        border:2px solid rgba(45,158,86,0.5);border-radius:16px;
        padding:2rem;text-align:center;margin:2rem 0;'>
        <div style='font-size:3rem;margin-bottom:1rem;'>🎾</div>
        <h2 style='color:#4ade80;margin-bottom:1rem;'>Ton mode invité a expiré !</h2>
        <p style='color:rgba(255,255,255,0.8);font-size:1.1rem;margin-bottom:1.5rem;'>
            Tu as profité de <strong>3 jours gratuits</strong> sans inscription.<br>
            Crée ton compte maintenant pour continuer !
        </p>
        <div style='background:rgba(45,158,86,0.15);border-radius:10px;padding:1rem;margin-bottom:1.5rem;'>
            <p style='color:#4ade80;font-weight:600;margin:0;'>
                🎁 Bonus inscription : <strong>5 prédictions gratuites</strong> offertes !
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COMPTEUR DE PRÉDICTIONS
# ─────────────────────────────────────────────

def get_predictions_restantes():
    if not MODE_PAYANT:
        return -1
    if is_admin() or is_premium():
        return -1

    user = get_user()
    if not user:
        return 0

    aujourd_hui = date.today().isoformat()
    derniere    = user.get("date_derniere_prediction", "")
    compteur    = user.get("predictions_aujourd_hui", 0)

    if derniere != aujourd_hui:
        compteur = 0

    if is_anonyme():
        limite = LIMITE_PREDICTIONS_ANONYME
    else:
        date_inscription = str(user.get("date_inscription", ""))[:10]
        limite = BONUS_INSCRIPTION if date_inscription == aujourd_hui else LIMITE_PREDICTIONS_GRATUITES

    return max(0, limite - compteur)

def get_limite_du_jour():
    if not MODE_PAYANT or is_admin() or is_premium():
        return -1
    user = get_user()
    if not user:
        return LIMITE_PREDICTIONS_GRATUITES
    if is_anonyme():
        return LIMITE_PREDICTIONS_ANONYME
    date_inscription = str(user.get("date_inscription", ""))[:10]
    return BONUS_INSCRIPTION if date_inscription == date.today().isoformat() else LIMITE_PREDICTIONS_GRATUITES

# ─────────────────────────────────────────────
# AUTHENTIFICATION
# ─────────────────────────────────────────────

def connexion_email(email, mot_de_passe):
    if not FIREBASE_API_KEY:
        return {"success": False, "erreur": "Clé Firebase manquante"}
    url     = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": mot_de_passe, "returnSecureToken": True}
    try:
        r    = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if "idToken" in data:
            return {"success": True, "token": data["idToken"],
                    "uid": data["localId"], "email": data["email"]}
        msg = data.get("error", {}).get("message", "Erreur inconnue")
        messages_fr = {
            "EMAIL_NOT_FOUND":           "Aucun compte avec cet email.",
            "INVALID_PASSWORD":          "Mot de passe incorrect.",
            "USER_DISABLED":             "Ce compte a été désactivé.",
            "INVALID_LOGIN_CREDENTIALS": "Email ou mot de passe incorrect.",
        }
        return {"success": False, "erreur": messages_fr.get(msg, msg)}
    except Exception as e:
        return {"success": False, "erreur": f"Erreur réseau : {e}"}


def inscription_email(email, mot_de_passe, nom):
    url     = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": mot_de_passe, "returnSecureToken": True}
    try:
        r    = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if "idToken" in data:
            creer_profil_utilisateur(data["localId"], email, nom)
            return {"success": True, "token": data["idToken"],
                    "uid": data["localId"], "email": email}
        msg = data.get("error", {}).get("message", "Erreur inconnue")
        messages_fr = {
            "EMAIL_EXISTS":   "Un compte existe déjà avec cet email.",
            "INVALID_EMAIL":  "Format d'email invalide.",
            "WEAK_PASSWORD : Password should be at least 6 characters":
                              "Le mot de passe doit contenir au moins 6 caractères.",
        }
        return {"success": False, "erreur": messages_fr.get(msg, msg)}
    except Exception as e:
        return {"success": False, "erreur": f"Erreur réseau : {e}"}


def connexion_anonyme():
    """
    Connexion anonyme avec anti-reset compteur via cookie.
    Si un UID anonyme existe déjà → on le réutilise.
    """
    # Anti-triche : réutiliser le même UID anonyme via cookie
    try:
        from modules.session_persistante import get_cookie_manager
        cm          = get_cookie_manager()
        cookie_anon = cm.get("tennis_ia_anon_uid")
        if cookie_anon:
            profil = charger_profil_utilisateur(cookie_anon, "anonyme@tennis-ia.app")
            if profil:
                return {"success": True, "token": "anon_restored",
                        "uid": cookie_anon, "email": None}
    except:
        pass

    url     = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"returnSecureToken": True}
    try:
        r    = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if "idToken" in data:
            # Sauvegarder l'UID anonyme dans un cookie
            try:
                from modules.session_persistante import get_cookie_manager
                cm     = get_cookie_manager()
                expiry = datetime.now() + timedelta(days=DUREE_MODE_INVITE_JOURS + 1)
                cm.set("tennis_ia_anon_uid", data["localId"], expires_at=expiry)
            except:
                pass
            return {"success": True, "token": data["idToken"],
                    "uid": data["localId"], "email": None}
        return {"success": False, "erreur": "Impossible de se connecter anonymement."}
    except Exception as e:
        return {"success": False, "erreur": f"Erreur réseau : {e}"}


def deconnexion():
    st.session_state.user     = None
    st.session_state.token    = None
    st.session_state.connecte = False
    st.session_state.pop("onboarding_complete", None)
    # Ne PAS effacer le cookie anonyme (anti-triche)
    try:
        from modules.session_persistante import effacer_session_locale
        effacer_session_locale()
    except:
        pass
    st.rerun()

# ─────────────────────────────────────────────
# GESTION PROFILS FIRESTORE
# ─────────────────────────────────────────────

def creer_profil_utilisateur(uid, email, nom="Utilisateur"):
    est_admin = email == ADMIN_EMAIL
    profil = {
        "uid":                     uid,
        "email":                   email,
        "nom":                     ADMIN_NAME if est_admin else nom,
        "role":                    "admin" if est_admin else "user",
        "plan":                    "premium" if est_admin else "gratuit",
        "date_inscription":        datetime.now().isoformat(),
        "predictions_aujourd_hui": 0,
        "date_derniere_prediction": None,
        "actif":                   True,
    }
    try:
        db = get_db()
        if db:
            db.collection("users").document(uid).set(profil)
    except:
        pass
    return profil


def charger_profil_utilisateur(uid, email):
    """
    Charge le profil depuis Firestore avec cache session de 5 minutes.
    Retourne toujours un profil valide même si Firebase est indisponible.
    """
    cache_key = f"profil_cache_{uid}"
    if st.session_state.get(cache_key):
        return st.session_state[cache_key]

    profil_defaut = {
        "uid":                     uid,
        "email":                   email,
        "nom":                     ADMIN_NAME if email == ADMIN_EMAIL else "Utilisateur",
        "role":                    "admin" if email == ADMIN_EMAIL else "user",
        "plan":                    "premium" if email == ADMIN_EMAIL else "gratuit",
        "predictions_aujourd_hui": 0,
        "date_inscription":        datetime.now().isoformat(),
        "actif":                   True,
    }

    # Essayer de charger depuis Firestore avec cache 5 min
    data = firebase_lire_avec_cache("users", uid, duree_cache_sec=300)
    if data:
        st.session_state[cache_key] = data
        return data

    # Créer le profil si inexistant
    try:
        db = get_db()
        if db:
            doc = db.collection("users").document(uid).get()
            if doc.exists:
                profil = doc.to_dict()
                st.session_state[cache_key] = profil
                return profil
            else:
                profil = creer_profil_utilisateur(uid, email)
                st.session_state[cache_key] = profil
                return profil
    except:
        pass

    st.session_state[cache_key] = profil_defaut
    return profil_defaut


def connecter_utilisateur(result, nom="Utilisateur"):
    if result["success"]:
        uid   = result["uid"]
        email = result.get("email", "")
        profil = charger_profil_utilisateur(uid, email or "anonyme@tennis-ia.app")
        if profil:
            if not profil.get("actif", True) and email != ADMIN_EMAIL:
                return "bloque"
            st.session_state.user     = profil
            st.session_state.token    = result["token"]
            st.session_state.connecte = True
            try:
                from modules.session_persistante import sauvegarder_session
                sauvegarder_session(uid, email or "", result["token"])
            except:
                pass
            return True
    return False

# ─────────────────────────────────────────────
# VÉRIFICATION DES LIMITES
# ─────────────────────────────────────────────

def peut_faire_prediction():
    if not MODE_PAYANT:
        return True, ""
    if is_admin() or is_premium():
        return True, ""
    if mode_invite_expire():
        return False, "Ton mode invité de 3 jours a expiré. Crée un compte pour continuer !"
    user = get_user()
    if not user:
        return False, "Vous devez être connecté."
    restantes = get_predictions_restantes()
    if restantes <= 0:
        limite = get_limite_du_jour()
        return False, f"Limite atteinte ({limite} prédictions/jour). Passe en Premium !"
    return True, ""


def incrementer_compteur_predictions():
    if not MODE_PAYANT:
        return
    user = get_user()
    if not user or is_admin() or is_premium():
        return
    try:
        aujourd_hui = date.today().isoformat()
        # Mise à jour locale immédiate
        st.session_state.user["predictions_aujourd_hui"] = user.get("predictions_aujourd_hui", 0) + 1
        st.session_state.user["date_derniere_prediction"] = aujourd_hui
        # Invalider le cache profil
        uid       = user.get("uid")
        cache_key = f"profil_cache_{uid}"
        st.session_state[cache_key] = st.session_state.user
        # Puis Firebase (silencieux si erreur)
        db = get_db()
        if db:
            db.collection("users").document(uid).update({
                "predictions_aujourd_hui":  firestore.Increment(1),
                "date_derniere_prediction": aujourd_hui,
            })
    except:
        pass

# ─────────────────────────────────────────────
# CADENAS PREMIUM
# ─────────────────────────────────────────────

def afficher_cadenas(message="Cette fonctionnalité est réservée aux membres Premium.",
                     bouton_premium=True):
    st.markdown(f"""
    <div style='background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.4);
        border-radius:12px;padding:1.2rem;text-align:center;margin:0.5rem 0;'>
        <span style='font-size:2rem;'>🔒</span>
        <p style='color:rgba(255,255,255,0.8);margin:0.5rem 0 0 0;font-size:0.95rem;'>
            {message}
        </p>
    </div>
    """, unsafe_allow_html=True)
    if bouton_premium:
        st.markdown(
            "<p style='text-align:center;color:#f59e0b;font-size:0.85rem;'>"
            "⭐ Passe en Premium pour débloquer → onglet Premium</p>",
            unsafe_allow_html=True
        )


def afficher_prediction_floutee(res):
    st.markdown("""
    <div style='background:rgba(45,158,86,0.1);border:1px solid rgba(45,158,86,0.3);
        border-radius:12px;padding:1.5rem;text-align:center;margin:1rem 0;position:relative;'>
        <div style='filter:blur(8px);pointer-events:none;'>
            <h3 style='color:#4ade80;'>🏆 Vainqueur : ████████</h3>
            <p style='color:rgba(255,255,255,0.7);'>
                Probabilité : ██.█% · Score : █-█ █-█ · Sets : █
            </p>
        </div>
        <div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
            background:rgba(0,0,0,0.8);border-radius:12px;padding:1rem 2rem;'>
            <span style='font-size:2rem;'>🔒</span>
            <p style='color:#f59e0b;font-weight:600;margin:0.5rem 0 0 0;'>
                Limite atteinte — Passe en Premium !
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def afficher_message_apres_limite():
    st.markdown("""
    <div style='background:linear-gradient(135deg,rgba(245,158,11,0.15),rgba(245,158,11,0.05));
        border:1px solid rgba(245,158,11,0.4);border-radius:12px;padding:1.5rem;margin:1rem 0;'>
        <h3 style='color:#f59e0b;text-align:center;'>Tu as utilisé toutes tes prédictions du jour !</h3>
        <p style='color:rgba(255,255,255,0.8);text-align:center;margin-bottom:1rem;'>
            Voici ce que tu rates en restant en gratuit :
        </p>
        <div style='display:flex;flex-wrap:wrap;gap:0.5rem;justify-content:center;'>
            <span style='background:rgba(45,158,86,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.85rem;'>♾️ Prédictions illimitées</span>
            <span style='background:rgba(45,158,86,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.85rem;'>👑 IA Suprême</span>
            <span style='background:rgba(45,158,86,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.85rem;'>📊 Historique complet</span>
            <span style='background:rgba(45,158,86,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.85rem;'>💰 Value Bets détaillés</span>
        </div>
        <p style='text-align:center;margin-top:1rem;'>
            <strong style='color:#4ade80;'>⭐ À partir de 500 FCFA/semaine</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PANEL ADMIN
# ─────────────────────────────────────────────

def afficher_panel_admin():
    if not is_admin():
        return
    try:
        from modules.admin import afficher_panel_admin_complet
        afficher_panel_admin_complet()
    except Exception:
        st.error("Module admin non disponible")

# ─────────────────────────────────────────────
# INTERFACE DE CONNEXION
# ─────────────────────────────────────────────

def afficher_interface_connexion():
    init_session()

    if is_connecte():
        return True

    st.markdown("""
        <div style='text-align:center;padding:2rem 0 1rem 0;'>
            <h1 style='font-size:3rem;background:linear-gradient(135deg,#00c853,#00e676);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
                🎾 Tennis IA
            </h1>
            <p style='color:#888;font-size:1.1rem;'>
                Prédictions tennis par intelligence artificielle
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📧 Email", "📱 Téléphone", "👤 Anonyme", "ℹ️ À propos", "🔑 Mot de passe oublié"
    ])

    # ── Onglet Email ──
    with tab1:
        mode = st.radio(
            "Mode", ["Se connecter", "Créer un compte"],
            horizontal=True, label_visibility="collapsed"
        )

        if mode == "Se connecter":
            with st.form("form_connexion"):
                email  = st.text_input("Email", placeholder="votre@email.com")
                mdp    = st.text_input("Mot de passe", type="password", placeholder="••••••••")
                submit = st.form_submit_button("🔐 Se connecter", use_container_width=True)
                if submit:
                    if not email or not mdp:
                        st.error("Veuillez remplir tous les champs.")
                    else:
                        with st.spinner("Connexion en cours..."):
                            result = connexion_email(email, mdp)
                            statut = connecter_utilisateur(result)
                            if statut is True:
                                st.success(f"Bienvenue {st.session_state.user.get('nom', '')} ! 🎾")
                                st.rerun()
                            elif statut == "bloque":
                                st.error("🚫 Votre compte a été suspendu.")
                            else:
                                st.error(result.get("erreur", "Erreur de connexion."))

        else:
            with st.form("form_inscription"):
                nom    = st.text_input("Votre nom", placeholder="Ex: Jean Dupont")
                email  = st.text_input("Email", placeholder="votre@email.com")
                mdp    = st.text_input("Mot de passe (min. 6 caractères)", type="password")
                mdp2   = st.text_input("Confirmer le mot de passe", type="password")
                submit = st.form_submit_button("✅ Créer mon compte", use_container_width=True)
                if submit:
                    if not nom or not email or not mdp:
                        st.error("Veuillez remplir tous les champs.")
                    elif mdp != mdp2:
                        st.error("Les mots de passe ne correspondent pas.")
                    elif len(mdp) < 6:
                        st.error("Le mot de passe doit contenir au moins 6 caractères.")
                    else:
                        with st.spinner("Création du compte..."):
                            result = inscription_email(email, mdp, nom)
                            if connecter_utilisateur(result, nom):
                                st.success(f"Compte créé ! Bienvenue {nom} 🎾")
                                st.rerun()
                            else:
                                st.error(result.get("erreur", "Erreur lors de la création."))

    # ── Onglet Téléphone ──
    with tab2:
        st.info("📱 La connexion par téléphone est uniquement disponible dans l'APK Android.")
        st.markdown("**Étapes dans l'APK :**\n1. Entrez votre numéro (+225XXXXXXXX)\n2. Recevez un SMS\n3. Entrez le code reçu")

    # ── Onglet Anonyme ──
    with tab3:
        st.markdown("""
            <div style='text-align:center;padding:1rem;'>
                <p>Accédez à l'app sans créer de compte.<br>
                <small style='color:#888;'>
                    Vous avez <strong>3 jours d'essai gratuit</strong> · <strong>2 prédictions/jour</strong><br>
                    Fonctionnalités Premium non incluses.
                </small></p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("👤 Essayer 3 jours gratuitement", use_container_width=True):
            with st.spinner("Connexion anonyme..."):
                result = connexion_anonyme()
                if connecter_utilisateur(result, "Visiteur"):
                    st.rerun()
                else:
                    st.error("Impossible de se connecter anonymement.")

    # ── Onglet À propos ──
    with tab4:
        st.markdown("""
            **Tennis IA** est une application de prédictions tennis basée sur l'intelligence artificielle.

            - 🤖 **Modèles IA** : XGBoost entraîné sur 755 000+ matchs
            - 🎯 **Précision** : ~70% vainqueur, ~70% sets
            - 👥 **Joueurs** : 27 225 joueurs référencés
            - 📱 **Développé par** : Fulgence N'da
        """)

    # ── Onglet Mot de passe oublié ──
    # CORRECTION : st.form avec st.form_submit_button → corrige "Missing Submit Button"
    with tab5:
        afficher_reset_password()

    return False

# ─────────────────────────────────────────────
# BARRE UTILISATEUR
# ─────────────────────────────────────────────

def afficher_barre_utilisateur():
    if not is_connecte():
        return

    user  = get_user()
    nom   = user.get("nom", "Utilisateur")
    plan  = user.get("plan", "gratuit")

    with st.sidebar:
        st.markdown("---")

        if is_admin():
            st.markdown(f"**🛡️ {nom}**")
            st.markdown("*Administrateur*")
        elif plan == "premium":
            st.markdown(f"**⭐ {nom}**")
            st.markdown("*Compte Premium*")
        elif is_anonyme():
            temps = get_temps_restant_invite_str()
            st.markdown("**👤 Visiteur**")
            if temps == "Expiré":
                st.error("⏰ Mode invité expiré")
            else:
                st.warning(f"⏰ Mode invité : encore **{temps}**")
            restantes = get_predictions_restantes()
            limite    = get_limite_du_jour()
            utilisees = limite - restantes
            st.caption(f"🎯 Prédictions : {utilisees}/{limite}")
        else:
            st.markdown(f"**👤 {nom}**")
            if MODE_PAYANT:
                st.markdown("*Compte Gratuit*")
                restantes = get_predictions_restantes()
                limite    = get_limite_du_jour()
                utilisees = limite - restantes
                st.caption(f"🎯 Prédictions : {utilisees}/{limite} utilisées")
                if limite > 0:
                    pct     = min(1.0, utilisees / limite)
                    couleur = "#2d9e56" if pct < 0.5 else "#f59e0b" if pct < 1.0 else "#e74c3c"
                    st.markdown(f"""
                    <div style='background:rgba(255,255,255,0.1);border-radius:5px;height:6px;margin:4px 0;'>
                        <div style='background:{couleur};border-radius:5px;height:6px;width:{pct*100}%;'></div>
                    </div>
                    """, unsafe_allow_html=True)

        if st.button("🚪 Se déconnecter", use_container_width=True):
            deconnexion()

        st.markdown("---")

# ─────────────────────────────────────────────
# MOT DE PASSE OUBLIÉ
# CORRECTION : utilisation de st.form pour éviter "Missing Submit Button"
# ─────────────────────────────────────────────

def afficher_reset_password():
    st.markdown("## 🔑 Récupération d'accès")

    # Le radio DOIT être hors du form (Streamlit l'exige)
    choix = st.radio(
        "Choisissez une méthode :",
        ["📧 Email", "📱 Téléphone (OTP)"],
        key="reset_method_radio"
    )

    if choix == "📧 Email":
        # ✅ CORRECTION : st.form avec st.form_submit_button
        with st.form("form_reset_password"):
            email  = st.text_input("Entrez votre email", placeholder="votre@email.com")
            submit = st.form_submit_button(
                "📧 Envoyer le lien de réinitialisation",
                use_container_width=True
            )
            if submit:
                if not email:
                    st.error("Veuillez entrer un email valide.")
                else:
                    try:
                        url     = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
                        payload = {"requestType": "PASSWORD_RESET", "email": email}
                        r       = requests.post(url, json=payload, timeout=10)
                        data    = r.json()
                        if r.status_code == 200:
                            st.success("📧 Email envoyé ! Vérifiez votre boîte mail.")
                        else:
                            msg = data.get("error", {}).get("message", "Erreur inconnue")
                            st.error(f"❌ {msg}")
                    except Exception as e:
                        st.error(f"Erreur : {e}")
    else:
        st.info("📱 Connectez-vous via OTP depuis l'écran principal (APK Android).")
