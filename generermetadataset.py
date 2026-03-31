import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import StratifiedKFold
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier

# Charger les données et modèles
df = pd.read_csv('ton_dataset.csv')
with open('modeles_surf.pkl', 'rb') as f:
    modeles_surf = pickle.load(f)
with open('ia_generale.pkl', 'rb') as f:
    ia_generale = pickle.load(f)

FEATURES_22 = ['feature1', 'feature2', 'feature3']  # À adapter

# Méthode out-of-fold
kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
meta = np.zeros((len(df), 4))

for fold, (train_idx, val_idx) in enumerate(kf.split(df[FEATURES_22], df['winner'])):
    print(f"Fold {fold+1}/5 - {len(val_idx)} matchs")
    
    X_tr, X_val = df[FEATURES_22].iloc[train_idx], df[FEATURES_22].iloc[val_idx]
    y_tr = df['winner'].iloc[train_idx]
    
    # IA Générale
    ia_gen_fold = CalibratedClassifierCV(
        XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                     use_label_encoder=False, eval_metric='logloss'),
        method='isotonic', cv=3
    )
    ia_gen_fold.fit(X_tr, y_tr)
    meta[val_idx, 0] = ia_gen_fold.predict_proba(X_val)[:, 1]
    
    # IA spécialisées
    for i, surface in enumerate(['Clay', 'Hard', 'Grass'], start=1):
        mask_tr = df.iloc[train_idx]['surface'] == surface
        mask_val = df.iloc[val_idx]['surface'] == surface
        
        if mask_tr.sum() < 1000:
            meta[val_idx[mask_val.values], i] = meta[val_idx[mask_val.values], 0]
            continue
            
        ia_surf_fold = CalibratedClassifierCV(
            XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                         use_label_encoder=False, eval_metric='logloss'),
            method='isotonic', cv=3
        )
        ia_surf_fold.fit(X_tr[mask_tr.values], y_tr[mask_tr.values])
        meta[val_idx, i] = ia_surf_fold.predict_proba(X_val)[:, 1]

# Construction du dataset méta
surface_map = {'Clay': 1, 'Hard': 2, 'Grass': 3}
df_meta = pd.DataFrame({
    'proba_generale': meta[:, 0],
    'proba_clay': meta[:, 1],
    'proba_hard': meta[:, 2],
    'proba_grass': meta[:, 3],
    'surface_code': df['surface'].map(surface_map).fillna(0),
    'elo_diff': df['elo_A'] - df['elo_B'],
    'rank_diff': df['rank_A'] - df['rank_B'],
    'consensus_score': meta.max(axis=1) - meta.min(axis=1),
    'surface_ia_active': df['surface'].isin(modeles_surf.keys()).astype(int),
    'winner': df['winner']
})

df_meta.to_csv('meta_dataset.csv', index=False)
print("Fichier meta_dataset.csv généré avec succès")