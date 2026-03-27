"""
entrainement_auto.py — Re-entraînement automatique du modèle IA avec validation
Valide le nouveau modèle avant de le déployer. Push HuggingFace si meilleur.
Tennis IA | Fulgence N'da
"""

import os
import pickle
import subprocess
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

CHEMIN_MODELE_ACTUEL = "models/xgboost_vainqueur.pkl"
CHEMIN_MODELE_CANDIDAT = "models/xgboost_vainqueur_candidat.pkl"
CHEMIN_DONNEES = "data/matchs_historiques.csv"
SEUIL_AMELIORATION = 0.001   # le nouveau modèle doit être au moins 0.1% meilleur
RATIO_VALIDATION = 0.15      # 15% des données pour le jeu de validation
HUGGINGFACE_REPO = "fulgence10/tennis-ia"

FEATURES = [
    "elo_joueur_a", "elo_joueur_b",
    "elo_surface_a", "elo_surface_b",
    "forme_5_a", "forme_5_b",
    "h2h_a", "h2h_b",
    "ranking_a", "ranking_b",
    "surface_encoded",
    "circuit_encoded",
    "round_encoded",
    "best_of",
]
TARGET = "vainqueur"   # 0 = Joueur A gagne, 1 = Joueur B gagne


# ─────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────

def _charger_donnees() -> pd.DataFrame | None:
    if not os.path.exists(CHEMIN_DONNEES):
        st.error(f"❌ Fichier introuvable : {CHEMIN_DONNEES}")
        return None
    try:
        df = pd.read_csv(CHEMIN_DONNEES)
        # Vérification colonnes minimales
        manquantes = [f for f in FEATURES + [TARGET] if f not in df.columns]
        if manquantes:
            st.error(f"❌ Colonnes manquantes dans les données : {manquantes}")
            return None
        df = df.dropna(subset=FEATURES + [TARGET])
        return df
    except Exception as e:
        st.error(f"❌ Erreur chargement données : {e}")
        return None


# ─────────────────────────────────────────────
# CHARGEMENT DU MODÈLE ACTUEL
# ─────────────────────────────────────────────

def _charger_modele_actuel() -> tuple[object | None, float]:
    """Retourne (modèle, précision_baseline). Précision -1 si pas de modèle."""
    if not os.path.exists(CHEMIN_MODELE_ACTUEL):
        return None, -1.0
    try:
        with open(CHEMIN_MODELE_ACTUEL, "rb") as f:
            data = pickle.load(f)
            if isinstance(data, dict):
                return data.get("model"), data.get("accuracy", -1.0)
            return data, -1.0
    except Exception as e:
        st.warning(f"⚠️ Impossible de charger le modèle actuel : {e}")
        return None, -1.0


# ─────────────────────────────────────────────
# ENTRAÎNEMENT DU CANDIDAT
# ─────────────────────────────────────────────

def _entrainer_candidat(df: pd.DataFrame) -> tuple[object, float, float]:
    """
    Entraîne un nouveau modèle XGBoost sur toutes les données.
    Retourne (modèle, précision_train, précision_validation).
    """
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=RATIO_VALIDATION, random_state=42, stratify=y
    )

    modele = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    modele.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    acc_train = accuracy_score(y_train, modele.predict(X_train))
    acc_val = accuracy_score(y_val, modele.predict(X_val))
    return modele, acc_train, acc_val


# ─────────────────────────────────────────────
# SAUVEGARDE + PUSH HUGGINGFACE
# ─────────────────────────────────────────────

def _sauvegarder_modele(modele, accuracy: float, chemin: str):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        pickle.dump({"model": modele, "accuracy": accuracy, "date": datetime.now().isoformat()}, f)

def _push_huggingface(log_zone) -> bool:
    """Push le modèle validé sur HuggingFace Spaces via git."""
    try:
        log_zone.info("📤 Push HuggingFace en cours...")
        commandes = [
            ["git", "add", CHEMIN_MODELE_ACTUEL],
            ["git", "commit", "-m", f"Auto-deploy modèle validé {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            ["git", "push", f"https://huggingface.co/spaces/{HUGGINGFACE_REPO}", "master:main", "--force"],
        ]
        for cmd in commandes:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                log_zone.error(f"❌ Erreur git : {result.stderr}")
                return False
        log_zone.success("✅ Push HuggingFace réussi !")
        return True
    except Exception as e:
        log_zone.error(f"❌ Erreur push : {e}")
        return False


# ─────────────────────────────────────────────
# PIPELINE COMPLET (appelé par le bouton Admin)
# ─────────────────────────────────────────────

def lancer_entrainement_avec_validation(pousser_sur_hf: bool = False):
    """
    Pipeline complet :
      1. Charger les données
      2. Entraîner le candidat
      3. Comparer avec le modèle actuel
      4. Déployer seulement si meilleur
      5. Push HuggingFace (optionnel)
    """
    st.subheader("🔁 Re-entraînement automatique avec validation")
    log = st.empty()
    barre = st.progress(0)

    # Étape 1 : Données
    log.info("📂 Chargement des données...")
    df = _charger_donnees()
    if df is None:
        return
    barre.progress(20)
    st.success(f"✅ {len(df):,} matchs chargés")

    # Étape 2 : Modèle actuel
    log.info("📦 Chargement du modèle actuel...")
    modele_actuel, acc_actuel = _charger_modele_actuel()
    barre.progress(35)

    if modele_actuel:
        st.info(f"📌 Modèle actuel — précision connue : {acc_actuel*100:.2f}%" if acc_actuel > 0
                else "📌 Modèle actuel chargé (précision inconnue)")
    else:
        st.info("ℹ️ Aucun modèle actuel. Le candidat sera déployé directement.")

    # Étape 3 : Entraînement
    log.info("🧠 Entraînement du modèle candidat...")
    with st.spinner("Entraînement XGBoost en cours (peut prendre quelques minutes)..."):
        try:
            candidat, acc_train, acc_val = _entrainer_candidat(df)
        except Exception as e:
            st.error(f"❌ Erreur entraînement : {e}")
            return
    barre.progress(70)

    col1, col2 = st.columns(2)
    col1.metric("Précision candidat (train)", f"{acc_train*100:.2f}%")
    col2.metric("Précision candidat (validation)", f"{acc_val*100:.2f}%")

    # Étape 4 : Validation
    log.info("⚖️ Comparaison avec le modèle actuel...")
    barre.progress(80)

    deployer = False
    if modele_actuel is None or acc_actuel < 0:
        deployer = True
        st.success("✅ Pas de modèle existant → candidat déployé automatiquement.")
    elif acc_val >= acc_actuel + SEUIL_AMELIORATION:
        deployer = True
        gain = (acc_val - acc_actuel) * 100
        st.success(f"✅ Le candidat est meilleur de +{gain:.2f}% → déploiement autorisé.")
    else:
        diff = (acc_actuel - acc_val) * 100
        st.warning(
            f"⚠️ Le candidat n'est pas assez meilleur (écart : {diff:.2f}%). "
            f"L'ancien modèle reste actif. Aucun déploiement."
        )
        _sauvegarder_modele(candidat, acc_val, CHEMIN_MODELE_CANDIDAT)
        st.caption(f"💾 Candidat sauvegardé ici pour revue : `{CHEMIN_MODELE_CANDIDAT}`")

    # Étape 5 : Déploiement
    if deployer:
        _sauvegarder_modele(candidat, acc_val, CHEMIN_MODELE_ACTUEL)
        barre.progress(90)
        st.success(f"💾 Nouveau modèle déployé → `{CHEMIN_MODELE_ACTUEL}`")

        if pousser_sur_hf:
            ok = _push_huggingface(log)
            if not ok:
                st.error("❌ Push HuggingFace échoué. Déploiement local OK mais non synchronisé.")

    barre.progress(100)
    log.empty()
    st.balloons() if deployer else None


# ─────────────────────────────────────────────
# WIDGET ADMIN — Bouton de lancement
# ─────────────────────────────────────────────

def afficher_panneau_entrainement():
    """
    Panneau à intégrer dans le Panel Admin (admin uniquement).
    """
    st.title("⚙️ Re-entraînement IA")
    st.markdown(
        """
        Le pipeline va :
        1. Charger **toutes les données historiques**
        2. Entraîner un **modèle candidat** XGBoost
        3. **Valider** sa performance sur un jeu de test
        4. Déployer **uniquement s'il est meilleur** que l'actuel
        5. *(optionnel)* Pousser sur **HuggingFace Spaces**
        """
    )

    _, modele_actuel, acc_actuel = (None, *_charger_modele_actuel())
    if acc_actuel > 0:
        st.info(f"📌 Modèle actuel en production : précision **{acc_actuel*100:.2f}%**")
    else:
        st.info("📌 Aucun modèle en production actuellement.")

    pousser_hf = st.checkbox("🚀 Pousser sur HuggingFace après déploiement", value=False)

    if st.button("▶️ Lancer le re-entraînement", type="primary"):
        lancer_entrainement_avec_validation(pousser_sur_hf=pousser_hf)
