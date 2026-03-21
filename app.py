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
    chemin = os.path.join(
        os.path.dirname(__file__), 'data', 'BASE_FEATURES.csv'
    )
    if os.path.exists(chemin):
        return pd.read_csv(chemin, low_memory=False)
    try:
        from huggingface_hub import hf_hub_download
        chemin_hf = hf_hub_download(
            repo_id   = 'fulgence10/tennis-data',
            filename  = 'BASE_FEATURES.csv',
            repo_type = 'dataset'
        )
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
    <p>Intelligence Artificielle de Prédictions Tennis · ATP · WTA · Challengers · ITF · 830 000+ matchs</p>
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
    st.metric("📊 Matchs analysés", "830 906")

if not CSV_DISPO:
    st.warning("⚠️ BASE_FEATURES.csv non disponible – certaines fonctionnalités sont limitées.")

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

    # Onglets de base
    onglets = [
        "📅 Matchs du jour",
        "🎾 Prédiction",
        "👤 Joueurs",
        "🔄 Mise à jour",
        "📚 Historique",
        "📊 Performance IA"
    ]

    # Ajouter onglet Admin si c'est Fulgence N'da
    if is_admin():
        onglets.append("🛡️ Admin")

    tabs = st.tabs(onglets)

    with tabs[0]:
        page_matchs_jour(modeles, df_base)
    with tabs[1]:
        page_prediction(modeles, df_base)
    with tabs[2]:
        page_joueurs(modeles, df_base)
    with tabs[3]:
        page_mise_a_jour(modeles, df_base)
    with tabs[4]:
        page_historique()
    with tabs[5]:
        page_performance()

    # Panel Admin visible uniquement pour vous
    if is_admin() and len(tabs) > 6:
        with tabs[6]:
            afficher_panel_admin()

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
