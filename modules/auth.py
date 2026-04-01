"""
auth.py — Module d'authentification Firebase pour Tennis IA
Auteur : Fulgence N'da
Date : 20 mars 2026

Fonctionnalités :
- Connexion Email / Mot de passe
- Connexion Google
- Connexion Numéro de téléphone (OTP)
- Mode Anonyme (3 jours)
- Compte Admin (fulgencenda32@gmail.com)
- Mode gratuit avec limites + cadenas Premium
"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, date, timedelta
import os
import json
import requests

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ADMIN_EMAIL = "fulgencenda32@gmail.com"
ADMIN_NAME = "Fulgence N'da"

# Mode payant : False = tout le monde accède librement
MODE_PAYANT = True

# Limites en mode gratuit
LIMITE_PREDICTIONS_GRATUITES = 2  # par jour
BONUS_INSCRIPTION = 5  # prédictions bonus le jour de l'inscription
DUREE_MODE_INVITE_JOURS = 3  # durée du mode invité sans inscription

# Firebase Web API Key
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "") or "AIzaSyA0rB2KDA4hyiEFoPTctapHDCDV98iOGW4"
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "tennis-ia")

# ─────────────────────────────────────────────
# INITIALISATION FIREBASE
# ─────────────────────────────────────────────

def init_firebase():
    """Initialise Firebase Admin SDK si pas déjà fait."""
    if not firebase_admin._apps:
        try:
            cred_path = "data/firebase_key.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            elif os.getenv('FIREBASE_KEY'):
                import json
                cle_json = json.loads(os.getenv('FIREBASE_KEY'))
                cred = credentials.Certificate(cle_json)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        except Exception as e:
            st.error(f"Erreur Firebase : {e}")
            return False
    return True

def get_db():
    """Retourne le client Firestore."""
    init_firebase()
    return firestore.client()

# ─────────────────────────────────────────────
# GESTION SESSION STREAMLIT
# ─────────────────────────────────────────────

def init_session():
    """Initialise les variables de session."""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "token" not in st.session_state:
        st.session_state.token = None
    if "connecte" not in st.session_state:
        st.session_state.connecte = False

def is_connecte():
    """Vérifie si un utilisateur est connecté."""
    return st.session_state.get("connecte", False)

def get_user():
    """Retourne les données de l'utilisateur connecté."""
    return st.session_state.get("user", None)

def is_admin():
    """Vérifie si l'utilisateur connecté est admin."""
    user = get_user()
    if user:
        return user.get("email") == ADMIN_EMAIL
    return False

def is_premium():
    """Vérifie si l'utilisateur est premium."""
    if is_admin():
        return True
    user = get_user()
    if user:
        return user.get("plan") == "premium"
    return False

def is_anonyme():
    """Vérifie si l'utilisateur est en mode anonyme/invité."""
    user = get_user()
    if not user:
        return True
    email = user.get("email", "")
    return not email or email == "anonyme@tennis-ia.app"

# ─────────────────────────────────────────────
# MODE INVITÉ — Gestion 3 jours
# ─────────────────────────────────────────────

def get_jours_restants_invite():
    """
    Retourne le nombre de jours restants en mode invité.
    Retourne -1 si pas en mode invité.
    Retourne 0 si expiré.
    """
    user = get_user()
    if not user:
        return -1

    if not is_anonyme():
        return -1  # Pas un invité

    date_inscription = user.get("date_inscription", "")
    if not date_inscription:
        return DUREE_MODE_INVITE_JOURS

    try:
        date_debut = datetime.fromisoformat(date_inscription)
        date_expiration = date_debut + timedelta(days=DUREE_MODE_INVITE_JOURS)
        maintenant = datetime.now()

        if maintenant >= date_expiration:
            return 0  # Expiré

        delta = date_expiration - maintenant
        # Retourner les jours + heures restants
        return max(0, delta.days + (1 if delta.seconds > 0 else 0))
    except:
        return DUREE_MODE_INVITE_JOURS

def get_temps_restant_invite_str():
    """Retourne le temps restant formaté pour l'affichage."""
    user = get_user()
    if not user or not is_anonyme():
        return ""

    date_inscription = user.get("date_inscription", "")
    if not date_inscription:
        return f"{DUREE_MODE_INVITE_JOURS}j 0h"

    try:
        date_debut = datetime.fromisoformat(date_inscription)
        date_expiration = date_debut + timedelta(days=DUREE_MODE_INVITE_JOURS)
        delta = date_expiration - datetime.now()

        if delta.total_seconds() <= 0:
            return "Expiré"

        jours = delta.days
        heures = delta.seconds // 3600
        return f"{jours}j {heures}h"
    except:
        return f"{DUREE_MODE_INVITE_JOURS}j 0h"

def mode_invite_expire():
    """Vérifie si le mode invité a expiré."""
    return is_anonyme() and get_jours_restants_invite() == 0

def afficher_popup_inscription():
    """Affiche un pop-up doux pour inviter à s'inscrire."""
    st.markdown("""
    <div style='
        background: linear-gradient(135deg, rgba(45,158,86,0.2), rgba(45,158,86,0.05));
        border: 2px solid rgba(45,158,86,0.5);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
        animation: fadeIn 0.5s ease-out;
    '>
        <div style='font-size: 3rem; margin-bottom: 1rem;'>🎾</div>
        <h2 style='color: #4ade80; margin-bottom: 1rem;'>Ton mode invité a expiré !</h2>
        <p style='color: rgba(255,255,255,0.8); font-size: 1.1rem; margin-bottom: 1.5rem;'>
            Tu as profité de <strong>3 jours gratuits</strong> sans inscription.<br>
            Crée ton compte maintenant pour continuer à utiliser Tennis IA !
        </p>
        <div style='
            background: rgba(45,158,86,0.15);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
        '>
            <p style='color: #4ade80; font-weight: 600; margin: 0;'>
                🎁 Bonus inscription : <strong>5 prédictions gratuites</strong> offertes !
            </p>
        </div>
        <p style='color: rgba(255,255,255,0.6); font-size: 0.9rem;'>
            Inscription gratuite · 30 secondes · Email uniquement
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COMPTEUR DE PRÉDICTIONS
# ─────────────────────────────────────────────

def get_predictions_restantes():
    """
    Retourne le nombre de prédictions restantes aujourd'hui.
    Retourne -1 si illimité (admin/premium).
    """
    if not MODE_PAYANT:
        return -1

    if is_admin() or is_premium():
        return -1  # Illimité

    user = get_user()
    if not user:
        return 0

    aujourd_hui = date.today().isoformat()
    derniere = user.get("date_derniere_prediction", "")
    compteur = user.get("predictions_aujourd_hui", 0)

    # Réinitialiser si nouveau jour
    if derniere != aujourd_hui:
        compteur = 0

    # Bonus inscription (jour de l'inscription)
    date_inscription = str(user.get("date_inscription", ""))[:10]
    limite = LIMITE_PREDICTIONS_GRATUITES
    if date_inscription == aujourd_hui:
        limite = BONUS_INSCRIPTION

    restantes = max(0, limite - compteur)
    return restantes

def get_limite_du_jour():
    """Retourne la limite de prédictions pour aujourd'hui."""
    if not MODE_PAYANT or is_admin() or is_premium():
        return -1

    user = get_user()
    if not user:
        return LIMITE_PREDICTIONS_GRATUITES

    date_inscription = str(user.get("date_inscription", ""))[:10]
    aujourd_hui = date.today().isoformat()

    if date_inscription == aujourd_hui:
        return BONUS_INSCRIPTION

    return LIMITE_PREDICTIONS_GRATUITES

# ─────────────────────────────────────────────
# AUTHENTIFICATION VIA FIREBASE REST API
# ─────────────────────────────────────────────

def connexion_email(email, mot_de_passe):
    """Connexion avec email et mot de passe."""
    if not FIREBASE_API_KEY:
        return {"success": False, "erreur": "Clé Firebase manquante — contactez l'administrateur"}
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": mot_de_passe,
        "returnSecureToken": True
    }
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if "idToken" in data:
            return {"success": True, "token": data["idToken"], "uid": data["localId"], "email": data["email"]}
        else:
            msg = data.get("error", {}).get("message", "Erreur inconnue")
            messages_fr = {
                "EMAIL_NOT_FOUND": "Aucun compte avec cet email.",
                "INVALID_PASSWORD": "Mot de passe incorrect.",
                "USER_DISABLED": "Ce compte a été désactivé.",
                "INVALID_LOGIN_CREDENTIALS": "Email ou mot de passe incorrect.",
            }
            return {"success": False, "erreur": messages_fr.get(msg, msg)}
    except Exception as e:
        return {"success": False, "erreur": f"Erreur réseau : {e}"}

def inscription_email(email, mot_de_passe, nom):
    """Inscription avec email et mot de passe."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": mot_de_passe,
        "returnSecureToken": True
    }
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if "idToken" in data:
            # Créer le profil dans Firestore
            creer_profil_utilisateur(data["localId"], email, nom)
            return {"success": True, "token": data["idToken"], "uid": data["localId"], "email": email}
        else:
            msg = data.get("error", {}).get("message", "Erreur inconnue")
            messages_fr = {
                "EMAIL_EXISTS": "Un compte existe déjà avec cet email.",
                "WEAK_PASSWORD : Password should be at least 6 characters": "Le mot de passe doit contenir au moins 6 caractères.",
                "INVALID_EMAIL": "Format d'email invalide.",
            }
            return {"success": False, "erreur": messages_fr.get(msg, msg)}
    except Exception as e:
        return {"success": False, "erreur": f"Erreur réseau : {e}"}

def connexion_anonyme():
    """Connexion anonyme."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"returnSecureToken": True}
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if "idToken" in data:
            return {"success": True, "token": data["idToken"], "uid": data["localId"], "email": None}
        else:
            return {"success": False, "erreur": "Impossible de se connecter anonymement."}
    except Exception as e:
        return {"success": False, "erreur": f"Erreur réseau : {e}"}

def deconnexion():
    """Déconnecte l'utilisateur."""
    st.session_state.user = None
    st.session_state.token = None
    st.session_state.connecte = False
    st.session_state.pop("onboarding_complete", None)
    st.rerun()

# ─────────────────────────────────────────────
# GESTION PROFILS FIRESTORE
# ─────────────────────────────────────────────

def creer_profil_utilisateur(uid, email, nom="Utilisateur"):
    """Crée le profil d'un nouvel utilisateur dans Firestore."""
    try:
        db = get_db()
        est_admin = email == ADMIN_EMAIL
        profil = {
            "uid": uid,
            "email": email,
            "nom": ADMIN_NAME if est_admin else nom,
            "role": "admin" if est_admin else "user",
            "plan": "premium" if est_admin else "gratuit",
            "date_inscription": datetime.now().isoformat(),
            "predictions_aujourd_hui": 0,
            "date_derniere_prediction": None,
            "actif": True,
        }
        db.collection("users").document(uid).set(profil)
        return profil
    except Exception as e:
        st.warning(f"Profil non sauvegardé en cloud : {e}")
        return None

def charger_profil_utilisateur(uid, email):
    """Charge le profil depuis Firestore, le crée si absent. Cache en session pour éviter 429."""
    cache_key = f"profil_cache_{uid}"
    if st.session_state.get(cache_key):
        return st.session_state[cache_key]
    try:
        db = get_db()
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            profil = doc.to_dict()
        else:
            profil = creer_profil_utilisateur(uid, email)
        st.session_state[cache_key] = profil
        return profil
    except Exception as e:
        # Mode hors-ligne : profil minimal local
        return {
            "uid": uid,
            "email": email,
            "nom": ADMIN_NAME if email == ADMIN_EMAIL else "Utilisateur",
            "role": "admin" if email == ADMIN_EMAIL else "user",
            "plan": "premium" if email == ADMIN_EMAIL else "gratuit",
            "predictions_aujourd_hui": 0,
            "date_inscription": datetime.now().isoformat(),
            "actif": True,
        }

def connecter_utilisateur(result, nom="Utilisateur"):
    """Finalise la connexion et charge le profil."""
    if result["success"]:
        uid = result["uid"]
        email = result.get("email", "")
        profil = charger_profil_utilisateur(uid, email or "anonyme@tennis-ia.app")
        if profil:
            if not profil.get("actif", True) and email != ADMIN_EMAIL:
                return "bloque"
            st.session_state.user = profil
            st.session_state.token = result["token"]
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
    """
    Vérifie si l'utilisateur peut faire une prédiction.
    Retourne (True/False, message).
    """
    if not MODE_PAYANT:
        return True, ""

    if is_admin() or is_premium():
        return True, ""

    # Mode invité expiré
    if mode_invite_expire():
        return False, "Ton mode invité de 3 jours a expiré. Crée un compte pour continuer !"

    user = get_user()
    if not user:
        return False, "Vous devez être connecté."

    restantes = get_predictions_restantes()
    if restantes <= 0:
        limite = get_limite_du_jour()
        return False, f"Limite atteinte ({limite} prédictions/jour en gratuit). Passe en Premium pour un accès illimité !"

    return True, ""

def incrementer_compteur_predictions():
    """Incrémente le compteur de prédictions de l'utilisateur."""
    if not MODE_PAYANT:
        return

    user = get_user()
    if not user or is_admin() or is_premium():
        return

    try:
        aujourd_hui = date.today().isoformat()
        db = get_db()
        uid = user.get("uid")
        db.collection("users").document(uid).update({
            "predictions_aujourd_hui": firestore.Increment(1),
            "date_derniere_prediction": aujourd_hui
        })
        # Mise à jour locale
        st.session_state.user["predictions_aujourd_hui"] = user.get("predictions_aujourd_hui", 0) + 1
        st.session_state.user["date_derniere_prediction"] = aujourd_hui
    except Exception as e:
        pass

# ─────────────────────────────────────────────
# CADENAS PREMIUM — Affichage bloqué avec explication
# ─────────────────────────────────────────────

def afficher_cadenas(message="Cette fonctionnalité est réservée aux membres Premium.", 
                     bouton_premium=True):
    """
    Affiche un cadenas 🔒 avec un message explicatif.
    Ne bloque jamais silencieusement — explique toujours pourquoi et comment débloquer.
    """
    st.markdown(f"""
    <div style='
        background: rgba(245,158,11,0.1);
        border: 1px solid rgba(245,158,11,0.4);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        margin: 0.5rem 0;
    '>
        <span style='font-size: 2rem;'>🔒</span>
        <p style='color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0; font-size: 0.95rem;'>
            {message}
        </p>
    </div>
    """, unsafe_allow_html=True)

    if bouton_premium:
        st.markdown(
            "<p style='text-align:center; color:#f59e0b; font-size:0.85rem;'>"
            "⭐ Passe en Premium pour débloquer → onglet Premium</p>",
            unsafe_allow_html=True
        )

def afficher_prediction_floutee(res):
    """
    Affiche une prédiction floutée quand la limite gratuite est atteinte.
    L'utilisateur voit qu'il y a un résultat mais ne peut pas le lire.
    """
    st.markdown(f"""
    <div style='
        background: rgba(45,158,86,0.1);
        border: 1px solid rgba(45,158,86,0.3);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin: 1rem 0;
        position: relative;
    '>
        <div style='filter: blur(8px); pointer-events: none;'>
            <h3 style='color: #4ade80;'>🏆 Vainqueur : ████████</h3>
            <p style='color: rgba(255,255,255,0.7);'>
                Probabilité : ██.█% · Score : █-█ █-█ · Sets : █
            </p>
        </div>
        <div style='
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.8);
            border-radius: 12px;
            padding: 1rem 2rem;
        '>
            <span style='font-size: 2rem;'>🔒</span>
            <p style='color: #f59e0b; font-weight: 600; margin: 0.5rem 0 0 0;'>
                Limite atteinte — Passe en Premium !
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def afficher_message_apres_limite():
    """
    Affiche un message engageant après que l'utilisateur atteint sa limite.
    """
    st.markdown("""
    <div style='
        background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05));
        border: 1px solid rgba(245,158,11,0.4);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    '>
        <h3 style='color: #f59e0b; text-align: center;'>
            Tu as utilisé toutes tes prédictions du jour !
        </h3>
        <p style='color: rgba(255,255,255,0.8); text-align: center; margin-bottom: 1rem;'>
            Voici ce que tu rates en restant en gratuit :
        </p>
        <div style='display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center;'>
            <span style='background: rgba(45,158,86,0.2); padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.85rem;'>
                ♾️ Prédictions illimitées
            </span>
            <span style='background: rgba(45,158,86,0.2); padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.85rem;'>
                👑 IA Suprême
            </span>
            <span style='background: rgba(45,158,86,0.2); padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.85rem;'>
                📊 Historique complet
            </span>
            <span style='background: rgba(45,158,86,0.2); padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.85rem;'>
                💰 Value Bets détaillés
            </span>
        </div>
        <p style='text-align: center; margin-top: 1rem;'>
            <strong style='color: #4ade80;'>⭐ À partir de 500 FCFA/semaine</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PANEL ADMIN
# ─────────────────────────────────────────────

def afficher_panel_admin():
    """Affiche le panel d'administration (visible uniquement pour l'admin)."""
    if not is_admin():
        return
    from modules.admin import afficher_panel_admin_complet
    afficher_panel_admin_complet()

# ─────────────────────────────────────────────
# INTERFACE DE CONNEXION
# ─────────────────────────────────────────────

def afficher_interface_connexion():
    """
    Affiche l'interface de connexion complète.
    Retourne True si l'utilisateur est connecté.
    """
    init_session()

    if is_connecte():
        return True

    # En-tête
    st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem 0;'>
            <h1 style='font-size:3rem; background: linear-gradient(135deg, #00c853, #00e676);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                🎾 Tennis IA
            </h1>
            <p style='color:#888; font-size:1.1rem;'>
                Prédictions tennis par intelligence artificielle
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Onglets de connexion
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📧 Email", "📱 Téléphone", "👤 Anonyme", "ℹ️ À propos", "🔑 Mot de passe oublié"])

    with tab1:
        mode = st.radio("Mode", ["Se connecter", "Créer un compte"], horizontal=True, label_visibility="collapsed")

        if mode == "Se connecter":
            with st.form("form_connexion"):
                email = st.text_input("Email", placeholder="votre@email.com")
                mdp = st.text_input("Mot de passe", type="password", placeholder="••••••••")
                submit = st.form_submit_button("🔐 Se connecter", use_container_width=True)

                if submit:
                    if not email or not mdp:
                        st.error("Veuillez remplir tous les champs.")
                    else:
                        with st.spinner("Connexion en cours..."):
                            result = connexion_email(email, mdp)
                            statut = connecter_utilisateur(result)
                            if statut == True:
                                st.success(f"Bienvenue {st.session_state.user.get('nom', '')} ! 🎾")
                                st.rerun()
                            elif statut == "bloque":
                                st.error("🚫 Votre compte a été suspendu. Contactez l'administrateur.")
                            else:
                                st.error(result.get("erreur", "Erreur de connexion."))

        else:  # Créer un compte
            with st.form("form_inscription"):
                nom = st.text_input("Votre nom", placeholder="Ex: Jean Dupont")
                email = st.text_input("Email", placeholder="votre@email.com")
                mdp = st.text_input("Mot de passe (min. 6 caractères)", type="password")
                mdp2 = st.text_input("Confirmer le mot de passe", type="password")
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
                                st.success(f"Compte créé avec succès ! Bienvenue {nom} 🎾")
                                st.rerun()
                            else:
                                st.error(result.get("erreur", "Erreur lors de la création."))

    with tab2:
        st.info("📱 La connexion par téléphone (OTP SMS) est uniquement disponible dans l'APK Android. Sur le web, utilisez l'onglet 📧 Email.")
        st.markdown("**Étapes dans l'APK :**\n1. Entrez votre numéro (+225XXXXXXXX)\n2. Recevez un SMS\n3. Entrez le code reçu")

    with tab3:
        st.markdown("""
            <div style='text-align:center; padding:1rem;'>
                <p>Accédez à l'app sans créer de compte.<br>
                <small style='color:#888;'>Vous avez <strong>3 jours d'essai gratuit</strong>.<br>
                Inscrivez-vous ensuite pour continuer.</small></p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("👤 Essayer 3 jours gratuitement", use_container_width=True):
            with st.spinner("Connexion anonyme..."):
                result = connexion_anonyme()
                if connecter_utilisateur(result, "Visiteur"):
                    st.rerun()
                else:
                    st.error("Impossible de se connecter anonymement.")

    with tab4:
        st.markdown("""
            **Tennis IA** est une application de prédictions tennis basée sur l'intelligence artificielle.

            - 🤖 **Modèles IA** : XGBoost entraîné sur 830 000+ matchs
            - 🎯 **Précision** : ~68% vainqueur, ~71% sets
            - 👥 **Joueurs** : 26 802 joueurs référencés
            - 📱 **Développé par** : Fulgence N'da
        """)

    with tab5:
        afficher_reset_password()

    return False

# ─────────────────────────────────────────────
# BARRE UTILISATEUR
# ─────────────────────────────────────────────

def afficher_barre_utilisateur():
    """Affiche les infos utilisateur et bouton déconnexion dans la sidebar."""
    if not is_connecte():
        return

    user = get_user()
    nom = user.get("nom", "Utilisateur")
    plan = user.get("plan", "gratuit")
    email = user.get("email", "")

    with st.sidebar:
        st.markdown("---")

        # Badge admin ou plan
        if is_admin():
            st.markdown(f"**🛡️ {nom}**")
            st.markdown("*Administrateur*")
        elif plan == "premium":
            st.markdown(f"**⭐ {nom}**")
            st.markdown("*Compte Premium*")
        elif is_anonyme():
            temps = get_temps_restant_invite_str()
            st.markdown(f"**👤 Visiteur**")
            if temps == "Expiré":
                st.error(f"⏰ Mode invité expiré")
            else:
                st.warning(f"⏰ Mode invité : encore **{temps}**")
        else:
            st.markdown(f"**👤 {nom}**")
            if MODE_PAYANT:
                st.markdown("*Compte Gratuit*")
                restantes = get_predictions_restantes()
                limite = get_limite_du_jour()
                utilisees = limite - restantes
                st.caption(f"🎯 Prédictions : {utilisees}/{limite} utilisées")

                # Barre de progression
                if limite > 0:
                    pct = min(1.0, utilisees / limite)
                    couleur = "#2d9e56" if pct < 0.5 else "#f59e0b" if pct < 1.0 else "#e74c3c"
                    st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.1); border-radius: 5px; height: 6px; margin: 4px 0;'>
                        <div style='background: {couleur}; border-radius: 5px; height: 6px; width: {pct*100}%;'></div>
                    </div>
                    """, unsafe_allow_html=True)

        if st.button("🚪 Se déconnecter", use_container_width=True):
            deconnexion()

        st.markdown("---")

# ─────────────────────────────────────────────
# MOT DE PASSE OUBLIÉ
# ─────────────────────────────────────────────

def afficher_reset_password():
    import streamlit as st
    import requests

    st.markdown("## 🔑 Récupération d'accès")

    choix = st.radio(
        "Choisissez une méthode :",
        ["📧 Email", "📱 Téléphone (OTP)"]
    )

    if choix == "📧 Email":
        email = st.text_input("Entrez votre email")

        if st.button("Envoyer le lien de réinitialisation"):
            if not email:
                st.error("Veuillez entrer un email valide")
            else:
                try:
                    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
                    payload = {
                        "requestType": "PASSWORD_RESET",
                        "email": email
                    }

                    response = requests.post(url, json=payload)
                    data = response.json()

                    if response.status_code == 200:
                        st.success("📧 Email de réinitialisation envoyé ! Vérifiez votre boîte mail.")
                    else:
                        msg = data.get("error", {}).get("message", "Erreur inconnue")
                        st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    else:
        st.info("📱 Connectez-vous via OTP depuis l'écran principal")