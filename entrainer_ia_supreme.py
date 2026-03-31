# ============================================================
# ENTRAÎNEMENT IA SUPRÊME — Méta-modèle Tennis IA
# Entraîne le méta-modèle XGBoost calibré sur meta_dataset.csv
# À exécuter APRÈS construire_meta_dataset.py
# ============================================================
import pandas as pd
import numpy as np
import os, pickle, gc
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
DOSSIER        = r"C:\Users\HP\OneDrive\Documents\Tennis_IA"
FICHIER_META   = os.path.join(DOSSIER, "data", "meta_dataset.csv")
FICHIER_MODELE = os.path.join(DOSSIER, "data", "modeles_tennis_v2.pkl")

print("=" * 60)
print("👑 ENTRAÎNEMENT IA SUPRÊME — MÉTA-MODÈLE")
print("=" * 60)

# ============================================================
# ÉTAPE 1 — CHARGEMENT META-DATASET
# ============================================================
print("\n📂 Chargement meta_dataset.csv...")
meta_df = pd.read_csv(FICHIER_META)
print(f"   ✅ {len(meta_df):,} lignes chargées")
print(f"   Colonnes : {list(meta_df.columns)}")

# ============================================================
# ÉTAPE 2 — CONSTRUCTION DES FEATURES DU MÉTA-MODÈLE
# ============================================================
print("\n🔧 Construction des meta-features...")

# Features de base : les 4 probas + surface
meta_df['proba_max']   = meta_df[['proba_generale','proba_clay','proba_hard','proba_grass']].max(axis=1)
meta_df['proba_min']   = meta_df[['proba_generale','proba_clay','proba_hard','proba_grass']].min(axis=1)
meta_df['proba_mean']  = meta_df[['proba_generale','proba_clay','proba_hard','proba_grass']].mean(axis=1)
meta_df['proba_std']   = meta_df[['proba_generale','proba_clay','proba_hard','proba_grass']].std(axis=1)

# Écarts entre IA spécialisée pertinente et IA générale
meta_df['ecart_clay_gen']  = meta_df['proba_clay']  - meta_df['proba_generale']
meta_df['ecart_hard_gen']  = meta_df['proba_hard']  - meta_df['proba_generale']
meta_df['ecart_grass_gen'] = meta_df['proba_grass'] - meta_df['proba_generale']

# Confiance : distance à 0.5 (plus c'est loin de 0.5, plus le modèle est sûr)
meta_df['confiance_generale'] = (meta_df['proba_generale'] - 0.5).abs()
meta_df['confiance_clay']     = (meta_df['proba_clay'] - 0.5).abs()
meta_df['confiance_hard']     = (meta_df['proba_hard'] - 0.5).abs()
meta_df['confiance_grass']    = (meta_df['proba_grass'] - 0.5).abs()

# Consensus : combien d'IA sont d'accord (proba > 0.5)
meta_df['vote_generale'] = (meta_df['proba_generale'] > 0.5).astype(int)
meta_df['vote_clay']     = (meta_df['proba_clay'] > 0.5).astype(int)
meta_df['vote_hard']     = (meta_df['proba_hard'] > 0.5).astype(int)
meta_df['vote_grass']    = (meta_df['proba_grass'] > 0.5).astype(int)
meta_df['consensus']     = meta_df[['vote_generale','vote_clay','vote_hard','vote_grass']].sum(axis=1)

# Proba de l'IA spécialisée correspondant à la surface du match
def proba_surface_pertinente(row):
    surf = str(row['surface']).lower()
    if 'clay' in surf:
        return row['proba_clay']
    elif 'grass' in surf:
        return row['proba_grass']
    else:
        return row['proba_hard']

meta_df['proba_specialiste'] = meta_df.apply(proba_surface_pertinente, axis=1)
meta_df['ecart_specialiste_gen'] = meta_df['proba_specialiste'] - meta_df['proba_generale']
meta_df['confiance_specialiste'] = (meta_df['proba_specialiste'] - 0.5).abs()

# Liste finale des META-FEATURES
META_FEATURES = [
    # Probas brutes
    'proba_generale', 'proba_clay', 'proba_hard', 'proba_grass',
    # Surface
    'surface_enc',
    # Statistiques inter-modèles
    'proba_max', 'proba_min', 'proba_mean', 'proba_std',
    # Écarts
    'ecart_clay_gen', 'ecart_hard_gen', 'ecart_grass_gen',
    'ecart_specialiste_gen',
    # Confiance
    'confiance_generale', 'confiance_specialiste',
    # Consensus
    'consensus',
    # Proba spécialisée pertinente
    'proba_specialiste',
]

print(f"   ✅ {len(META_FEATURES)} meta-features créées")
print(f"   {META_FEATURES}")

# ============================================================
# ÉTAPE 3 — PRÉPARATION TRAIN / TEST
# ============================================================
print("\n📊 Préparation train/test...")

X_meta = meta_df[META_FEATURES].fillna(0).astype('float32')
y_meta = meta_df['target'].astype(int)

X_tr, X_te, y_tr, y_te = train_test_split(
    X_meta, y_meta, test_size=0.2, random_state=42, stratify=y_meta
)

print(f"   Train : {len(X_tr):,}")
print(f"   Test  : {len(X_te):,}")

del X_meta, y_meta
gc.collect()

# ============================================================
# ÉTAPE 4 — ENTRAÎNEMENT MÉTA-MODÈLE
# ============================================================
print("\n👑 Entraînement IA Suprême (XGBoost + Calibration)...")

# XGBoost léger (max_depth=3 pour éviter l'overfitting sur les probas)
xgb_meta = XGBClassifier(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric='logloss',
    random_state=42,
    n_jobs=-1
)

# Calibration avec CalibratedClassifierCV (5 folds internes)
print("   🔧 Calibration en cours (CalibratedClassifierCV)...")
meta_model = CalibratedClassifierCV(
    estimator=xgb_meta,
    method='isotonic',
    cv=5
)
meta_model.fit(X_tr, y_tr)
print("   ✅ Méta-modèle entraîné et calibré")

# ============================================================
# ÉTAPE 5 — ÉVALUATION
# ============================================================
print("\n📈 Évaluation...")

# Prédictions IA Suprême
y_pred_supreme = meta_model.predict(X_te)
y_proba_supreme = meta_model.predict_proba(X_te)[:, 1]

# Précision IA Suprême
acc_supreme = accuracy_score(y_te, y_pred_supreme)

# Brier Score (mesure la qualité des probas : plus c'est bas, mieux c'est)
brier_supreme = brier_score_loss(y_te, y_proba_supreme)

# Log Loss
logloss_supreme = log_loss(y_te, y_proba_supreme)

# Comparaison avec l'IA Générale seule (proba_generale comme seul prédicteur)
y_pred_gen = (X_te['proba_generale'] > 0.5).astype(int)
acc_generale = accuracy_score(y_te, y_pred_gen)
brier_generale = brier_score_loss(y_te, X_te['proba_generale'])
logloss_generale = log_loss(y_te, X_te['proba_generale'].clip(0.001, 0.999))

# Comparaison avec la proba spécialisée pertinente
y_pred_spec = (X_te['proba_specialiste'] > 0.5).astype(int)
acc_specialiste = accuracy_score(y_te, y_pred_spec)

# Gain
gain_acc = (acc_supreme - acc_generale) * 100
gain_brier = (brier_generale - brier_supreme) * 100

print(f"\n   {'='*50}")
print(f"   {'Modèle':<25} {'Accuracy':>10} {'Brier':>10} {'LogLoss':>10}")
print(f"   {'='*50}")
print(f"   {'IA Générale seule':<25} {acc_generale*100:>9.1f}% {brier_generale:>10.4f} {logloss_generale:>10.4f}")
print(f"   {'IA Spécialiste seule':<25} {acc_specialiste*100:>9.1f}%")
print(f"   {'👑 IA SUPRÊME':<25} {acc_supreme*100:>9.1f}% {brier_supreme:>10.4f} {logloss_supreme:>10.4f}")
print(f"   {'='*50}")
print(f"   Gain Accuracy  : {gain_acc:+.2f}%")
print(f"   Gain Brier     : {gain_brier:+.4f} (positif = mieux)")

# Analyse par surface
print(f"\n   📊 Détail par surface :")
surfaces_in_test = meta_df.loc[X_te.index, 'surface']
for surf in sorted(surfaces_in_test.unique()):
    mask = surfaces_in_test == surf
    if mask.sum() < 100:
        continue
    acc_s = accuracy_score(y_te[mask], y_pred_supreme[mask])
    acc_g = accuracy_score(y_te[mask], y_pred_gen[mask.values])
    delta = (acc_s - acc_g) * 100
    print(f"      {surf:20s} : Suprême {acc_s*100:.1f}% vs Générale {acc_g*100:.1f}% ({delta:+.1f}%) [{mask.sum():,} matchs]")

# Feature importance du méta-modèle
print(f"\n   🏆 Importance des meta-features (top 10) :")
# Extraire les importances depuis les estimateurs calibrés
try:
    importances = np.zeros(len(META_FEATURES))
    for cal_est in meta_model.calibrated_classifiers_:
        importances += cal_est.estimator.feature_importances_
    importances /= len(meta_model.calibrated_classifiers_)
    importance_df = pd.DataFrame({
        'feature': META_FEATURES,
        'importance': importances
    }).sort_values('importance', ascending=False)
    for _, row in importance_df.head(10).iterrows():
        bar = '█' * int(row['importance'] * 50)
        print(f"      {row['feature']:30s} {row['importance']:.3f} {bar}")
except Exception as e:
    print(f"      ⚠️ Impossible d'extraire les importances : {e}")

# ============================================================
# ÉTAPE 6 — SAUVEGARDE DANS LE PKL
# ============================================================
print("\n💾 Sauvegarde dans modeles_tennis_v2.pkl...")

# Charger le PKL existant
import __main__
def simplifier_round(r):
    r = str(r).upper()
    if 'QUARTER' in r or 'QF' in r: return 4
    if 'SEMI'    in r or 'SF' in r: return 5
    if r in ['F','FINAL','THE FINAL']: return 6
    if 'R128' in r: return 1
    if 'R64'  in r: return 2
    if 'R32'  in r: return 3
    return 3
__main__.simplifier_round = simplifier_round

with open(FICHIER_MODELE, 'rb') as f:
    modeles = pickle.load(f)

# Ajouter le méta-modèle et ses infos
modeles['meta_model']      = meta_model
modeles['meta_features']   = META_FEATURES
modeles['acc_supreme']     = acc_supreme
modeles['brier_supreme']   = brier_supreme
modeles['gain_vs_generale'] = gain_acc

# Sauvegarder
with open(FICHIER_MODELE, 'wb') as f:
    pickle.dump(modeles, f)

print(f"   ✅ modeles_tennis_v2.pkl mis à jour")
print(f"   Clés présentes : {list(modeles.keys())}")

# ============================================================
# ÉTAPE 7 — UPLOAD SUR HUGGINGFACE
# ============================================================
print("\n🚀 Upload sur HuggingFace...")
try:
    from huggingface_hub import HfApi
    from dotenv import load_dotenv
    load_dotenv()
    HF_TOKEN = os.getenv("HF_TOKEN")
    api = HfApi(token=HF_TOKEN)
    api.upload_file(
        path_or_fileobj=FICHIER_MODELE,
        path_in_repo='data/modeles_tennis_v2.pkl',
        repo_id='Fulgence10/Tennis-IA',
        repo_type='space',
        token=HF_TOKEN,
        commit_message=f'IA Supreme ajoutee {datetime.now().strftime("%Y-%m-%d")} Acc:{acc_supreme*100:.1f}% Gain:{gain_acc:+.1f}%'
    )
    print("   ✅ Modèle uploadé sur HuggingFace Space")
except Exception as e:
    print(f"   ❌ Erreur upload : {e}")

# ============================================================
# RÉSUMÉ FINAL
# ============================================================
print(f"\n{'='*60}")
print(f"👑 IA SUPRÊME ENTRAÎNÉE AVEC SUCCÈS")
print(f"{'='*60}")
print(f"  Meta-dataset       : {len(meta_df):,} lignes")
print(f"  Meta-features      : {len(META_FEATURES)}")
print(f"  IA Générale        : {acc_generale*100:.1f}%")
print(f"  IA Spécialiste     : {acc_specialiste*100:.1f}%")
print(f"  👑 IA Suprême      : {acc_supreme*100:.1f}%")
print(f"  Gain vs Générale   : {gain_acc:+.2f}%")
print(f"  Brier Score        : {brier_supreme:.4f}")
print(f"  Calibration        : isotonic (5 folds)")
print(f"  Profondeur max     : 3")
print(f"  Date               : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")
print(f"\n✅ Prêt pour l'Étape 4 : modifier prediction.py")