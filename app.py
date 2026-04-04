# ============================================================
# TENNIS IA – Application principale
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURATION PAGE
# ============================================================
st.set_page_config(
    page_title            = "🎾 Tennis IA",
    page_icon             = "🎾",
    layout                = "wide",
    initial_sidebar_state = "collapsed"
)

# ============================================================
# CSS PERSONNALISÉ – Vert gazon moderne
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0a1628 100%);
    color: #ffffff;
}

.main-header {
    background: linear-gradient(90deg, #1a6b3a 0%, #2d9e56 50%, #1a6b3a 100%);
    padding: 20px 30px;
    border-radius: 16px;
    margin-bottom: 24px;
    text-align: center;
    box-shadow: 0 8px 32px rgba(45,158,86,0.3);
    animation: slideDown 0.6s ease-out;
}
@keyframes slideDown {
    from { opacity: 0; transform: translateY(-20px); }
    to   { opacity: 1; transform: translateY(0); }
}
.main-header h1 { color:#ffffff; font-size:2.5rem; font-weight:700; margin:0; }
.main-header p  { color:rgba(255,255,255,0.85); font-size:1rem; margin:6px 0 0 0; }

.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px; padding: 6px; gap: 4px;
    border: 1px solid rgba(45,158,86,0.2);
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: rgba(255,255,255,0.6);
    border-radius: 8px; padding: 10px 20px;
    font-weight: 500; transition: all 0.3s ease; border: none;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(45,158,86,0.2); color: #ffffff;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#1a6b3a,#2d9e56) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(45,158,86,0.4);
}

[data-testid="metric-container"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(45,158,86,0.3);
    border-radius: 12px; padding: 16px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(45,158,86,0.2);
}
[data-testid="metric-container"] label {
    color: rgba(255,255,255,0.6) !important;
    font-size: 0.85rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #4ade80 !important;
    font-weight: 700 !important;
    font-size: 1.4rem !important;
}

.stButton > button {
    background: linear-gradient(135deg,#1a6b3a,#2d9e56);
    color: white; border: none; border-radius: 10px;
    padding: 12px 24px; font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(45,158,86,0.3);
}
.stButton > button:hover {
    background: linear-gradient(135deg,#2d9e56,#3dbf6e);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(45,158,86,0.5);
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background: rgba(15, 40, 30, 0.95) !important;
    border: 1px solid rgba(45,158,86,0.5) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    caret-color: #4ade80 !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #2d9e56 !important;
    box-shadow: 0 0 0 2px rgba(45,158,86,0.3) !important;
}
input::placeholder, textarea::placeholder {
    color: rgba(255,255,255,0.35) !important;
}

.stSelectbox > div > div,
[data-baseweb="select"] > div {
    background: rgba(15, 40, 30, 0.95) !important;
    border: 1px solid rgba(45,158,86,0.5) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
}
[data-baseweb="select"] span {
    color: #ffffff !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"] {
    background: #0d2137 !important;
    border: 1px solid rgba(45,158,86,0.3) !important;
    border-radius: 10px !important;
}
[role="option"] {
    background: #0d2137 !important;
    color: #ffffff !important;
}
[role="option"]:hover,
[aria-selected="true"] {
    background: rgba(45,158,86,0.25) !important;
    color: #4ade80 !important;
}

[data-testid="stDateInput"] input {
    background: rgba(15,40,30,0.95) !important;
    color: #ffffff !important;
    border: 1px solid rgba(45,158,86,0.5) !important;
}

[data-testid="stCheckbox"] label {
    color: #ffffff !important;
}

.stSuccess {
    background: rgba(45,158,86,0.15) !important;
    border: 1px solid rgba(45,158,86,0.4) !important;
    border-radius: 10px !important;
    color: #4ade80 !important;
}
.stError {
    background: rgba(239,68,68,0.15) !important;
    border: 1px solid rgba(239,68,68,0.4) !important;
    border-radius: 10px !important;
}
.stInfo {
    background: rgba(59,130,246,0.15) !important;
    border: 1px solid rgba(59,130,246,0.4) !important;
    border-radius: 10px !important;
}
.stWarning {
    background: rgba(245,158,11,0.15) !important;
    border: 1px solid rgba(245,158,11,0.4) !important;
    border-radius: 10px !important;
}

.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(45,158,86,0.2);
}

hr { border-color: rgba(45,158,86,0.2) !important; }
label { color: rgba(255,255,255,0.8) !important; font-weight:500 !important; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
::-webkit-scrollbar-thumb { background: #2d9e56; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# AUTHENTIFICATION FIREBASE
# ============================================================
from modules.auth import afficher_interface_connexion, afficher_barre_utilisateur, is_connecte, is_admin, afficher_panel_admin

from modules.session_persistante import restaurer_session, effacer_session_locale

# Tenter de restaurer la session depuis localStorage
restaurer_session()

# Afficher l'interface de connexion — si non connecté, on s'arrête ici
if not afficher_interface_connexion():
    st.stop()

# Afficher la barre utilisateur dans la sidebar
afficher_barre_utilisateur()

# ============================================================
# ONBOARDING — 3 écrans pour nouveaux utilisateurs
# ============================================================
from modules.onboarding import afficher_onboarding

if afficher_onboarding():
    st.stop()

    # ============================================================
# VÉRIFICATION MODE INVITÉ (3 jours)
# ============================================================
from modules.auth import is_anonyme, mode_invite_expire, afficher_popup_inscription

if mode_invite_expire():
    afficher_popup_inscription()
    st.stop()

# ============================================================
# REDÉFINITION simplifier_round
# ============================================================
def simplifier_round(r):
    r = str(r).upper()
    if 'QUARTER' in r or 'QF' in r: return 4
    if 'SEMI'    in r or 'SF' in r: return 5
    if r in ['F','FINAL','THE FINAL']: return 6
    if 'R128' in r: return 1
    if 'R64'  in r: return 2
    if 'R32'  in r: return 3
    if 'R16'  in r: return 3
    if 'RR'   in r: return 3
    return 3

# ============================================================
# CHARGEMENT DES MODÈLES
# ============================================================
@st.cache_resource
def charger_modeles():
    chemin = os.path.join(
        os.path.dirname(__file__), 'data', 'models', 'modeles_tennis_v2.pkl'
    )
    if not os.path.exists(chemin):
        # Fallback ancien emplacement
        chemin = os.path.join(
            os.path.dirname(__file__), 'data', 'modeles_tennis_v2.pkl'
        )
    if not os.path.exists(chemin):
        try:
            from huggingface_hub import hf_hub_download
            chemin = hf_hub_download(
                repo_id   = 'fulgence10/tennis-data',
                filename  = 'modeles_tennis_v2.pkl',
                repo_type = 'dataset'
            )
        except Exception as e:
            st.error(f"❌ Impossible de télécharger les modèles : {e}")
            st.stop()
    with open(chemin, 'rb') as f:
        modeles = pickle.load(f)
    modeles['simplifier_round'] = simplifier_round
    return modeles

@st.cache_data
def charger_base():
    # Seules 4 colonnes sont utilisées par l'app pour les prédictions
    # winner_name/loser_name : filtrage matchs
    # winner_rank/loser_rank : récupération classement
    COLS = ['winner_name', 'loser_name', 'winner_rank', 'loser_rank']

    # Nouveau fichier nettoyé (priorité)
    chemin = os.path.join(
        os.path.dirname(__file__), 'data', 'cleaned', 'matchs_clean.csv'
    )
    if os.path.exists(chemin):
        try:
            return pd.read_csv(chemin, usecols=COLS, low_memory=False)
        except Exception:
            return pd.read_csv(chemin, low_memory=False)

    # Fallback ancien fichier local
    chemin_old = os.path.join(
        os.path.dirname(__file__), 'data', 'BASE_FEATURES.csv'
    )
    if os.path.exists(chemin_old):
        try:
            return pd.read_csv(chemin_old, usecols=COLS, low_memory=False)
        except Exception:
            return pd.read_csv(chemin_old, low_memory=False)

    # Fallback HuggingFace — nouveau fichier
    try:
        from huggingface_hub import hf_hub_download
        chemin_hf = hf_hub_download(
            repo_id   = 'fulgence10/tennis-data',
            filename  = 'matchs_clean.csv',
            repo_type = 'dataset'
        )
        try:
            return pd.read_csv(chemin_hf, usecols=COLS, low_memory=False)
        except Exception:
            return pd.read_csv(chemin_hf, low_memory=False)
    except Exception:
        pass

    # Fallback HuggingFace — ancien fichier
    try:
        from huggingface_hub import hf_hub_download
        chemin_hf = hf_hub_download(
            repo_id   = 'fulgence10/tennis-data',
            filename  = 'BASE_FEATURES.csv',
            repo_type = 'dataset'
        )
        try:
            return pd.read_csv(chemin_hf, usecols=COLS, low_memory=False)
        except Exception:
            return pd.read_csv(chemin_hf, low_memory=False)
    except Exception as e:
        return None

# ============================================================
# CHARGEMENT DONNÉES
# ============================================================
with st.spinner("⏳ Chargement de Tennis IA..."):
    try:
        modeles = charger_modeles()
        df_base = charger_base()
        CHARGE  = True
        CSV_DISPO = df_base is not None
    except Exception as e:
        st.error(f"❌ Erreur : {e}")
        st.stop()

# ============================================================
# HEADER PRINCIPAL
# ============================================================
st.markdown("""
<div class="main-header">
    <h1>🎾 Tennis IA</h1>
    <p>Intelligence Artificielle de Prédictions Tennis · ATP · WTA · Challengers · ITF · 755 917 matchs</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("🏆 Joueurs", f"{modeles.get('nb_joueurs', 26802):,}")
with col2:
    st.metric("🏆 Vainqueur", f"{modeles.get('acc_win',0)*100:.1f}%")
with col3:
    st.metric("🔢 Nb Sets", f"{modeles.get('acc_sets',0)*100:.1f}%")
with col4:
    st.metric("⚖️ Handicap", f"{modeles.get('acc_handi',0)*100:.1f}%")
with col5:
    st.metric("📊 Matchs analysés", "755 917")

if not CSV_DISPO:
    st.warning("⚠️ Base de données non disponible – certaines fonctionnalités sont limitées.")


# ============================================================
# BROADCAST MESSAGE (Admin -> Utilisateurs)
# ============================================================
try:
    from modules.auth import get_db as _get_db
    _db = _get_db()
    _doc = _db.collection("broadcast").document("message_actif").get()
    if _doc.exists:
        _msg = _doc.to_dict()
        if _msg.get("actif", False):
            _texte = _msg.get("texte", "")
            _type  = _msg.get("type", "info")
            _cible = _msg.get("cible", "Tous")
            _user  = st.session_state.get("user", {})
            _plan  = _user.get("plan", "gratuit")
            _show  = (
                _cible == "Tous" or
                (_cible == "Gratuit uniquement" and _plan == "gratuit") or
                (_cible == "Premium uniquement" and _plan == "premium")
            )
            if _show and _texte:
                if _type == "success":   st.success(_texte)
                elif _type == "warning": st.warning(_texte)
                elif _type == "error":   st.error(_texte)
                else:                    st.info(_texte)
except Exception:
    pass

st.markdown("---")

# ============================================================
# ONGLETS NAVIGATION
# ============================================================
if CHARGE:
    from modules.prediction     import page_prediction
    from modules.joueurs        import page_joueurs
    from modules.historique     import page_historique
    from modules.mise_a_jour    import page_mise_a_jour
    from modules.performance    import page_performance
    from modules.matchs_du_jour import page_matchs_jour
    from modules.paiement       import page_paiement
    from modules.suggestions    import page_suggestions

    # ============================================================
    # ONGLETS — différenciés selon le rôle
    # Admin    : voit tous les onglets (+ Mise à jour + Performance IA)
    # Utilisateur : voit uniquement les onglets publics
    # ============================================================
    if is_admin():
        onglets = [
            "📅 Matchs du jour",   # 0
            "🎾 Prédiction",        # 1
            "👤 Joueurs",           # 2
            "🔄 Mise à jour",       # 3  — admin uniquement
            "📚 Historique",        # 4
            "📊 Performance IA",    # 5  — admin uniquement
            "💡 Suggestions",       # 6
            "🛡️ Admin",             # 7
            "⭐ Premium",           # 8
        ]
    else:
        onglets = [
            "📅 Matchs du jour",   # 0
            "🎾 Prédiction",        # 1
            "👤 Joueurs",           # 2
            "📚 Historique",        # 3
            "💡 Suggestions",       # 4
            "⭐ Premium",           # 5
        ]

    tabs = st.tabs(onglets)

    # ── Onglets communs aux deux rôles ──────────────────────────
    with tabs[0]:
        try:
            page_matchs_jour(modeles, df_base)
        except Exception as e:
            from modules.logs import log_erreur
            log_erreur(e, contexte="page_matchs_jour", onglet="Matchs du jour",
                       uid=st.session_state.get("user",{}).get("uid",""),
                       email=st.session_state.get("user",{}).get("email",""))
            st.error("❌ Une erreur est survenue dans Matchs du jour.")

    with tabs[1]:
        try:
            page_prediction(modeles, df_base)
        except Exception as e:
            from modules.logs import log_erreur
            log_erreur(e, contexte="page_prediction", onglet="Prédiction",
                       uid=st.session_state.get("user",{}).get("uid",""),
                       email=st.session_state.get("user",{}).get("email",""))
            st.error("❌ Une erreur est survenue dans Prédiction.")

    with tabs[2]:
        try:
            page_joueurs(modeles, df_base)
        except Exception as e:
            from modules.logs import log_erreur
            log_erreur(e, contexte="page_joueurs", onglet="Joueurs",
                       uid=st.session_state.get("user",{}).get("uid",""),
                       email=st.session_state.get("user",{}).get("email",""))
            st.error("❌ Une erreur est survenue dans Joueurs.")

    if is_admin():
        # ── Onglets réservés à l'admin ──────────────────────────
        with tabs[3]:
            try:
                page_mise_a_jour(modeles, df_base)
            except Exception as e:
                from modules.logs import log_erreur
                log_erreur(e, contexte="page_mise_a_jour", onglet="Mise à jour",
                           uid=st.session_state.get("user",{}).get("uid",""),
                           email=st.session_state.get("user",{}).get("email",""))
                st.error("❌ Une erreur est survenue dans Mise à jour.")

        with tabs[4]:
            try:
                page_historique()
            except Exception as e:
                from modules.logs import log_erreur
                log_erreur(e, contexte="page_historique", onglet="Historique",
                           uid=st.session_state.get("user",{}).get("uid",""),
                           email=st.session_state.get("user",{}).get("email",""))
                st.error("❌ Une erreur est survenue dans Historique.")

        with tabs[5]:
            try:
                page_performance()
            except Exception as e:
                from modules.logs import log_erreur
                log_erreur(e, contexte="page_performance", onglet="Performance IA",
                           uid=st.session_state.get("user",{}).get("uid",""),
                           email=st.session_state.get("user",{}).get("email",""))
                st.error("❌ Une erreur est survenue dans Performance IA.")

        with tabs[6]:
            try:
                page_suggestions()
            except Exception as e:
                from modules.logs import log_erreur
                log_erreur(e, contexte="page_suggestions", onglet="Suggestions",
                           uid=st.session_state.get("user",{}).get("uid",""),
                           email=st.session_state.get("user",{}).get("email",""))
                st.error("❌ Une erreur est survenue dans Suggestions.")

        with tabs[7]:
            afficher_panel_admin()

        with tabs[8]:
            page_paiement()

    else:
        # ── Suite onglets utilisateur (index décalé sans Mise à jour / Perf) ──
        with tabs[3]:
            try:
                page_historique()
            except Exception as e:
                from modules.logs import log_erreur
                log_erreur(e, contexte="page_historique", onglet="Historique",
                           uid=st.session_state.get("user",{}).get("uid",""),
                           email=st.session_state.get("user",{}).get("email",""))
                st.error("❌ Une erreur est survenue dans Historique.")

        with tabs[4]:
            try:
                page_suggestions()
            except Exception as e:
                from modules.logs import log_erreur
                log_erreur(e, contexte="page_suggestions", onglet="Suggestions",
                           uid=st.session_state.get("user",{}).get("uid",""),
                           email=st.session_state.get("user",{}).get("email",""))
                st.error("❌ Une erreur est survenue dans Suggestions.")

        with tabs[5]:
            page_paiement()

    # Restaurer onglet actif via JavaScript
    import streamlit.components.v1 as _components
    _components.html("""
    <script>
    function activerOnglet() {
        var idx = parseInt(sessionStorage.getItem("tennis_ia_tab") || "0");
        var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
        if (tabs && tabs[idx]) { tabs[idx].click(); }
    }
    var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
    tabs.forEach(function(tab, i) {
        tab.addEventListener("click", function() {
            sessionStorage.setItem("tennis_ia_tab", i);
        });
    });
    setTimeout(activerOnglet, 300);
    </script>
    """, height=0)

else:
    st.error("❌ Impossible de charger l'application.")
