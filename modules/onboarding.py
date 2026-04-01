# ============================================================
# MODULE ONBOARDING — 3 écrans de bienvenue pour nouveaux utilisateurs
# Tennis IA — Fulgence N'da
# ============================================================

import streamlit as st
from datetime import datetime

def doit_afficher_onboarding():
    """
    Vérifie si l'utilisateur doit voir l'onboarding.
    Retourne True si c'est sa première visite.
    """
    user = st.session_state.get("user", {})
    
    # Si pas connecté, pas d'onboarding
    if not user:
        return False
    
    # Vérifier si l'onboarding a déjà été vu (en session)
    if st.session_state.get("onboarding_complete", False):
        return False
    
    # Vérifier dans le profil utilisateur (Firebase)
    if user.get("onboarding_complete", False):
        st.session_state["onboarding_complete"] = True
        return False
    
    return True


def marquer_onboarding_termine():
    """
    Marque l'onboarding comme terminé dans Firebase et en session.
    """
    st.session_state["onboarding_complete"] = True
    
    user = st.session_state.get("user", {})
    uid = user.get("uid", "")
    
    if uid:
        try:
            from modules.auth import get_db
            db = get_db()
            db.collection("users").document(uid).update({
                "onboarding_complete": True,
                "onboarding_date": datetime.now().isoformat()
            })
        except:
            pass


def afficher_onboarding():
    """
    Affiche les 3 écrans d'onboarding.
    Retourne True si l'onboarding est en cours (bloquer l'app).
    Retourne False si terminé (continuer vers l'app).
    """
    
    if not doit_afficher_onboarding():
        return False
    
    # Initialiser l'étape
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1
    
    step = st.session_state["onboarding_step"]
    
    # ── CSS personnalisé pour l'onboarding ──
    st.markdown("""
    <style>
    .onboarding-container {
        text-align: center;
        padding: 2rem;
        max-width: 600px;
        margin: 0 auto;
    }
    .onboarding-emoji {
        font-size: 5rem;
        margin-bottom: 1rem;
    }
    .onboarding-title {
        font-size: 2rem;
        font-weight: 700;
        color: #4ade80;
        margin-bottom: 1rem;
    }
    .onboarding-text {
        font-size: 1.1rem;
        color: rgba(255,255,255,0.8);
        line-height: 1.6;
        margin-bottom: 2rem;
    }
    .onboarding-feature {
        background: rgba(45,158,86,0.15);
        border: 1px solid rgba(45,158,86,0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        text-align: left;
    }
    .onboarding-dots {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 2rem 0;
    }
    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
    }
    .dot.active {
        background: #4ade80;
        width: 24px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ── Indicateur de progression ──
    dots_html = ""
    for i in range(1, 4):
        if i == step:
            dots_html += '<div class="dot active"></div>'
        else:
            dots_html += '<div class="dot"></div>'
    
    # ══════════════════════════════════════════════════════════
    # ÉCRAN 1 : Bienvenue
    # ══════════════════════════════════════════════════════════
    if step == 1:
        st.markdown(f"""
        <div class="onboarding-container">
            <div class="onboarding-emoji">🎾</div>
            <div class="onboarding-title">Bienvenue sur Tennis IA !</div>
            <div class="onboarding-text">
                L'application d'intelligence artificielle qui prédit les résultats 
                des matchs de tennis avec une précision de <strong>70%+</strong>.
                <br><br>
                Plus de <strong>830 000 matchs</strong> analysés pour t'aider 
                à faire les meilleurs pronostics.
            </div>
            <div class="onboarding-dots">{dots_html}</div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Suivant →", type="primary", use_container_width=True):
                st.session_state["onboarding_step"] = 2
                st.rerun()
    
    # ══════════════════════════════════════════════════════════
    # ÉCRAN 2 : Fonctionnalités
    # ══════════════════════════════════════════════════════════
    elif step == 2:
        st.markdown(f"""
        <div class="onboarding-container">
            <div class="onboarding-emoji">🤖</div>
            <div class="onboarding-title">Comment ça marche ?</div>
            <div class="onboarding-text">
                Tennis IA utilise 4 modèles d'intelligence artificielle 
                pour analyser chaque match :
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="onboarding-feature">
                <strong>📅 Matchs du jour</strong><br>
                <small>Tous les matchs en temps réel avec prédiction en 1 clic</small>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="onboarding-feature">
                <strong>🎯 Prédictions détaillées</strong><br>
                <small>Vainqueur, score exact, nombre de sets, handicap</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="onboarding-feature">
                <strong>💰 Value Bets</strong><br>
                <small>Détection automatique des cotes avantageuses</small>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="onboarding-feature">
                <strong>📊 Historique & Stats</strong><br>
                <small>Suis ta précision et améliore tes pronostics</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="onboarding-dots">{dots_html}</div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("← Retour", use_container_width=True):
                st.session_state["onboarding_step"] = 1
                st.rerun()
        with col3:
            if st.button("Suivant →", type="primary", use_container_width=True):
                st.session_state["onboarding_step"] = 3
                st.rerun()
    
    # ══════════════════════════════════════════════════════════
    # ÉCRAN 3 : Prêt à commencer
    # ══════════════════════════════════════════════════════════
    elif step == 3:
        user = st.session_state.get("user", {})
        nom = user.get("nom", "Champion")
        
        st.markdown(f"""
        <div class="onboarding-container">
            <div class="onboarding-emoji">🚀</div>
            <div class="onboarding-title">Prêt à gagner, {nom} ?</div>
            <div class="onboarding-text">
                Tu as <strong>2 prédictions gratuites par jour</strong>.<br>
                Passe en <strong>Premium</strong> pour un accès illimité !
                <br><br>
                <strong>Astuce :</strong> Commence par l'onglet 📅 Matchs du jour 
                pour voir les matchs en cours et prédire en 1 clic.
            </div>
            <div class="onboarding-dots">{dots_html}</div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("← Retour", use_container_width=True):
                st.session_state["onboarding_step"] = 2
                st.rerun()
        with col3:
            if st.button("🎾 C'est parti !", type="primary", use_container_width=True):
                marquer_onboarding_termine()
                st.rerun()
    
    # Bloquer l'affichage de l'app tant que l'onboarding n'est pas terminé
    return True