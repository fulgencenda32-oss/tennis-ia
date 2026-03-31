# ============================================================
# ÉTAPE 3 — ENTRAÎNEMENT DE L'IA SUPRÊME
# Tennis IA | Fulgence N'da
# Lancez ce script APRÈS etape2_meta_dataset.py
# Durée estimée : 5-10 minutes
# ============================================================
import pandas as pd
import numpy as np
import os, pickle
from datetime import datetime
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================
DOSSIER        = r"C:\Users\HP\OneDrive\Documents\Tennis_IA"
FICHIER_MODELE = os.path.join(DOSSIER, "data", "modeles_tennis_v2.pkl")
FICHIER_META   = os.path.join(DOSSIER, "data", "meta_dataset.csv")
HF_REPO_SPACE  = "fulgence10/IA-tennis"

FEATURES_META = [
    'proba_generale',
    'proba_clay',
    'proba_hard',
    'proba_grass',
    'surface_code',
    'elo_diff',
    'rank_diff',
    'consensus_score',
    'surface_ia_active',
]

print("=" * 60)
print("🎾 IA SUPRÊME — ÉTAPE 3")
print("=" * 60)

# ============================================================
# CHARGEMENT
# ============================================================
print("\n📦 Chargement modèle et dataset méta...")

def simplifier_round(r):
    r = str(r).upper()
    if 'QUARTER' in r or 'QF' in r: return 4
    if 'SEMI'    in r or 'SF' in r: return 5
    if r in ['F','FINAL','THE FINAL']: return 6
    return 3

import __main__
__main__.simplifier_round = simplifier_round

with open(FICHIER_MODELE, 'rb') as f:
    modeles = pickle.load(f)
modeles['simplifier_round'] = simplifier_round

acc_general = modeles.get('acc_win', 0)
acc_surf    = modeles.get('acc_surf', {})
print(f"   IA Générale : {acc_general*100:.1f}%")
for surf, acc in acc_surf.items():
    print(f"   IA {surf:<8} : {acc*100:.1f}%")

df_meta = pd.read_csv(FICHIER_META)
print(f"   Dataset méta : {len(df_meta):,} matchs")

X_meta = df_meta[FEATURES_META].fillna(0.5).astype('float32')
y_meta = df_meta['target'].astype(int)

# ============================================================
# ÉVALUATION CROSS-VALIDATION
# ============================================================
print("\n🔬 Évaluation cross-validation (5 folds)...")

ia_supreme_eval = XGBClassifier(
    n_estimators=200,
    max_depth=3,        # Volontairement peu profond
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric='logloss',
    random_state=42,
    n_jobs=-1
)

scores = cross_val_score(ia_supreme_eval, X_meta, y_meta, cv=5, scoring='accuracy')
acc_supreme_cv = scores.mean()
gain_vs_general = (acc_supreme_cv - acc_general) * 100

print(f"   IA Suprême CV   : {acc_supreme_cv*100:.1f}% ± {scores.std()*100:.1f}%")
print(f"   IA Générale     : {acc_general*100:.1f}%")
print(f"   Gain            : {gain_vs_general:+.1f}%")

if acc_supreme_cv < acc_general - 0.01:
    print("\n⚠️  L'IA Suprême est moins bonne que la générale.")
    print("   Causes possibles :")
    print("   - Dataset méta insuffisant")
    print("   - IA spécialisées pas assez différentes")
    print("   Action : L'IA Générale reste utilisée par défaut")
    deployer = False
else:
    deployer = True
    print(f"\n✅ L'IA Suprême améliore de {gain_vs_general:+.1f}% → DÉPLOYÉE")

# ============================================================
# ENTRAÎNEMENT FINAL SUR TOUT LE DATASET
# ============================================================
print("\n🤖 Entraînement final sur tout le dataset...")

ia_supreme = XGBClassifier(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric='logloss',
    random_state=42,
    n_jobs=-1
)
ia_supreme.fit(X_meta, y_meta, verbose=False)

# Précision finale
X_tr_m, X_te_m, y_tr_m, y_te_m = train_test_split(
    X_meta, y_meta, test_size=0.2, random_state=42, stratify=y_meta
)
ia_supreme_test = XGBClassifier(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    eval_metric='logloss', random_state=42, n_jobs=-1
)
ia_supreme_test.fit(X_tr_m, y_tr_m, verbose=False)
acc_test = accuracy_score(y_te_m, ia_supreme_test.predict(X_te_m))
print(f"   Précision test : {acc_test*100:.1f}%")

# Importance des features
print("\n📊 Importance des features de l'IA Suprême :")
importances = ia_supreme.feature_importances_
for feat, imp in sorted(zip(FEATURES_META, importances), key=lambda x: -x[1]):
    barre = "█" * int(imp * 100)
    print(f"   {feat:<22} : {imp:.3f} {barre}")

# ============================================================
# SAUVEGARDE
# ============================================================
print("\n💾 Sauvegarde...")

modeles['ia_supreme']      = ia_supreme
modeles['features_meta']   = FEATURES_META
modeles['acc_supreme']     = float(acc_supreme_cv)
modeles['supreme_active']  = deployer
modeles['date_supreme']    = datetime.now().strftime('%Y-%m-%d %H:%M')

with open(FICHIER_MODELE, 'wb') as f:
    pickle.dump(modeles, f)

print(f"   ✅ IA Suprême sauvegardée dans modeles_tennis_v2.pkl")

# ============================================================
# UPLOAD SUR HUGGINGFACE
# ============================================================
print("\n🚀 Upload sur HuggingFace...")
try:
    from huggingface_hub import HfApi
    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=FICHIER_MODELE,
        path_in_repo='data/modeles_tennis_v2.pkl',
        repo_id=HF_REPO_SPACE, repo_type='space', token=token,
        commit_message=f'IA Suprême déployée — {acc_supreme_cv*100:.1f}% ({gain_vs_general:+.1f}% vs général)'
    )
    print("   ✅ Modèle uploadé sur HuggingFace Space")
except Exception as e:
    print(f"   ❌ Erreur upload : {e}")

# ============================================================
# RÉSUMÉ FINAL
# ============================================================
print(f"\n{'='*60}")
print("🎉 ÉTAPE 3 TERMINÉE — IA SUPRÊME")
print(f"{'='*60}")
print(f"  IA Générale     : {acc_general*100:.1f}%")
for surf, acc in acc_surf.items():
    print(f"  IA {surf:<8}     : {acc*100:.1f}%")
print(f"  IA Suprême CV   : {acc_supreme_cv*100:.1f}% ({gain_vs_general:+.1f}%)")
print(f"  Statut          : {'✅ ACTIVE' if deployer else '⚠️ INACTIVE (générale utilisée)'}")
print(f"{'='*60}")
print(f"\n✅ Prochaine étape : vérifier l'affichage dans l'app")
print(f"   Le fichier prediction.py détecte automatiquement l'IA Suprême")
print(f"   et affiche l'indicateur de consensus 🟢🟡🔴")
