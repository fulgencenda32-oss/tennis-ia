"""
auth.py — Module d'authentification Firebase pour Tennis IA
Auteur : Fulgence N'da
Date : 20 mars 2026

Fonctionnalités :
- Connexion Email / Mot de passe
- Connexion Google
- Connexion Numéro de téléphone (OTP)
- Mode Anonyme
- Compte Admin (fulgencenda32@gmail.com)
- Mode gratuit illimité (structure prête pour le payant)
"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, date
import os
import json
import requests

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ADMIN_EMAIL = "fulgencenda32@gmail.com"
ADMIN_NAME = "Fulgence N'da"

# Mode payant : False = tout le monde accède librement
# Pour activer le payant, mettre True
MODE_PAYANT = True

# Limites en mode gratuit (ignorées si MODE_PAYANT = True)
LIMITE_PREDICTIONS_GRATUITES = 2  # par jour

# Firebase Web API Key (à mettre dans .env)
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
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

# ─────────────────────────────────────────────
# AUTHENTIFICATION VIA FIREBASE REST API
# ─────────────────────────────────────────────

def connexion_email(email, mot_de_passe):
    """Connexion avec email et mot de passe."""
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
    """Charge le profil depuis Firestore, le crée si absent."""
    try:
        db = get_db()
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            return doc.to_dict()
        else:
            return creer_profil_utilisateur(uid, email)
    except Exception as e:
        # Mode hors-ligne : profil minimal local
        return {
            "uid": uid,
            "email": email,
            "nom": ADMIN_NAME if email == ADMIN_EMAIL else "Utilisateur",
            "role": "admin" if email == ADMIN_EMAIL else "user",
            "plan": "premium" if email == ADMIN_EMAIL else "gratuit",
            "predictions_aujourd_hui": 0,
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

    user = get_user()
    if not user:
        return False, "Vous devez être connecté."

    # Réinitialiser le compteur si nouveau jour
    aujourd_hui = date.today().isoformat()
    derniere = user.get("date_derniere_prediction", "")
    compteur = user.get("predictions_aujourd_hui", 0)

    if derniere != aujourd_hui:
        compteur = 0

    if compteur >= LIMITE_PREDICTIONS_GRATUITES:
        return False, f"Limite journalière atteinte ({LIMITE_PREDICTIONS_GRATUITES} prédictions/jour en gratuit). Passez en Premium pour un accès illimité !"

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
# PANEL ADMIN
# ─────────────────────────────────────────────

def afficher_panel_admin():
    """Affiche le panel d'administration (visible uniquement pour l'admin)."""
    if not is_admin():
        return

    st.markdown("---")
    st.markdown("### 🛡️ Panel Administrateur")

    try:
        db = get_db()

        col1, col2, col3 = st.columns(3)

        # Stats globales
        users_ref = db.collection("users").stream()
        utilisateurs = [u.to_dict() for u in users_ref]

        total = len(utilisateurs)
        premium_count = sum(1 for u in utilisateurs if u.get("plan") == "premium")
        gratuit_count = total - premium_count

        with col1:
            st.metric("👥 Utilisateurs total", total)
        with col2:
            st.metric("⭐ Premium", premium_count)
        with col3:
            st.metric("🆓 Gratuit", gratuit_count)

        # Liste des utilisateurs
        st.markdown("#### 📋 Liste des utilisateurs")
        for u in utilisateurs:
            with st.expander(f"{u.get('email', 'Anonyme')} — {u.get('plan', 'gratuit').upper()}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Nom :** {u.get('nom', '-')}")
                    st.write(f"**Rôle :** {u.get('role', 'user')}")
                    st.write(f"**Inscrit le :** {u.get('date_inscription', '-')[:10]}")
                with col_b:
                    if u.get("email") != ADMIN_EMAIL:
                        # Bouton plan
                        plan_actuel = u.get("plan", "gratuit")
                        if plan_actuel != "premium":
                            if st.button("⭐ Passer Premium", key=f"prem_{u.get('uid')}"):
                                db.collection("users").document(u["uid"]).update({"plan": "premium"})
                                st.success("Utilisateur passé en Premium ! Rechargez pour voir le changement.")
                        else:
                            if st.button("💳 Repasser Gratuit", key=f"grat_{u.get('uid')}"):
                                db.collection("users").document(u["uid"]).update({"plan": "gratuit"})
                                st.success("Utilisateur repassé en Gratuit ! Rechargez pour voir le changement.")
                        # Bouton bloquer
                        statut = u.get("actif", True)
                        label = "🚫 Bloquer" if statut else "✅ Débloquer"
                        if st.button(label, key=f"block_{u.get('uid')}"):
                            db.collection("users").document(u["uid"]).update({"actif": not statut})
                            st.success("Statut mis à jour ! Rechargez pour voir le changement.")

        # Parametres globaux
        st.markdown("#### ⚙️ Paramètres")
        mode = st.toggle("Mode Payant activé", value=MODE_PAYANT)
        if mode != MODE_PAYANT:
            st.info("Pour changer le mode payant, modifiez MODE_PAYANT dans modules/auth.py")

        # Mise a jour classements
        st.markdown("---")
        st.markdown("#### 🏆 Mise à jour classements ATP/WTA")
        st.caption("Importez un CSV avec colonnes : rank, player_name")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            csv_atp = st.file_uploader("CSV ATP", type=["csv"], key="upload_atp")
            if csv_atp:
                import pandas as _pd, json as _json, os as _os
                df_atp = _pd.read_csv(csv_atp)
                st.dataframe(df_atp.head(3))
                if st.button("✅ Importer ATP", key="btn_atp"):
                    try:
                        _path = _os.path.join(_os.path.dirname(__file__), '..', 'data', 'classements.json')
                        _data = _json.load(open(_path, encoding='utf-8')) if _os.path.exists(_path) else {"ATP": {}, "WTA": {}}
                        _col_r = [c for c in df_atp.columns if 'rank' in c.lower()][0]
                        _col_n = [c for c in df_atp.columns if 'name' in c.lower() or 'player' in c.lower()][0]
                        for _, row in df_atp.iterrows():
                            _data["ATP"][str(row[_col_n])] = int(row[_col_r])
                        from datetime import datetime as _dt
                        _data["date_maj"] = _dt.now().strftime("%Y-%m-%d")
                        _json.dump(_data, open(_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
                        st.success(f"✅ {len(df_atp)} joueurs ATP importes !")
                    except Exception as ex:
                        st.error(f"❌ Erreur : {ex}")
        with col_c2:
            csv_wta = st.file_uploader("CSV WTA", type=["csv"], key="upload_wta")
            if csv_wta:
                import pandas as _pd, json as _json, os as _os
                df_wta = _pd.read_csv(csv_wta)
                st.dataframe(df_wta.head(3))
                if st.button("✅ Importer WTA", key="btn_wta"):
                    try:
                        _path = _os.path.join(_os.path.dirname(__file__), '..', 'data', 'classements.json')
                        _data = _json.load(open(_path, encoding='utf-8')) if _os.path.exists(_path) else {"ATP": {}, "WTA": {}}
                        _col_r = [c for c in df_wta.columns if 'rank' in c.lower()][0]
                        _col_n = [c for c in df_wta.columns if 'name' in c.lower() or 'player' in c.lower()][0]
                        for _, row in df_wta.iterrows():
                            _data["WTA"][str(row[_col_n])] = int(row[_col_r])
                        from datetime import datetime as _dt
                        _data["date_maj"] = _dt.now().strftime("%Y-%m-%d")
                        _json.dump(_data, open(_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
                        st.success(f"✅ {len(df_wta)} joueurs WTA importes !")
                    except Exception as ex:
                        st.error(f"❌ Erreur : {ex}")

    except Exception as e:
        st.error(f"Erreur panel admin : {e}")

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
                <small style='color:#888;'>Vos données ne seront pas sauvegardées en cloud.</small></p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("👤 Continuer sans compte", use_container_width=True):
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
# BARRE UTILISATEUR (affichée en haut de l'app)
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
        else:
            st.markdown(f"**👤 {nom}**")
            if MODE_PAYANT:
                st.markdown("*Compte Gratuit*")
                st.caption(f"Prédictions aujourd'hui : {user.get('predictions_aujourd_hui', 0)}/{LIMITE_PREDICTIONS_GRATUITES}")

        if st.button("🚪 Se déconnecter", use_container_width=True):
            deconnexion()

        st.markdown("---")





# ==============================
# 🔑 MOT DE PASSE OUBLIÉ
# ==============================

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


