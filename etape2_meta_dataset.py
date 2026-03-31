# ============================================================
# ÉTAPE 2 — GÉNÉRATION DU DATASET MÉTA (Out-of-Fold)
# Tennis IA | Fulgence N'da
# Lancez ce script APRÈS etape1_ia_specialisees.py
# Durée estimée : 60-90 minutes
# ============================================================
import pandas as pd
import numpy as np
import os, re, pickle
from datetime import datetime
from collections import defaultdict
from sklearn.model_selection import StratifiedKFold
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
FICHIER_BASE   = os.path.join(DOSSIER, "data", "BASE_FEATURES.csv")
FICHIER_MODELE = os.path.join(DOSSIER, "data", "modeles_tennis_v2.pkl")
FICHIER_META   = os.path.join(DOSSIER, "data", "meta_dataset.csv")

FEATURES = [
    'elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff',
    'streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
    'dominance_diff','revanche_diff','hist_tournoi_diff',
    'rank_diff','age_diff','surface_enc','circuit_enc',
    'genre_enc','best_of','round_num','cote_diff','cote_proba_A','cote_proba_B',
]

print("=" * 60)
print("🎾 DATASET MÉTA OUT-OF-FOLD — ÉTAPE 2")
print("=" * 60)
print("\n⚠️  Cette méthode évite le data leakage :")
print("   On prédit uniquement sur des matchs NON vus à l'entraînement")

# ============================================================
# CHARGEMENT
# ============================================================
print("\n📦 Chargement modèle et données...")

def simplifier_round(r):
    r = str(r).upper()
    if 'QUARTER' in r or 'QF' in r: return 4
    if 'SEMI'    in r or 'SF' in r: return 5
    if r in ['F','FINAL','THE FINAL']: return 6
    if 'R128' in r: return 1
    if 'R64'  in r: return 2
    if 'R32'  in r: return 3
    return 3

import __main__
__main__.simplifier_round = simplifier_round

with open(FICHIER_MODELE, 'rb') as f:
    modeles = pickle.load(f)
modeles['simplifier_round'] = simplifier_round

modeles_surf = modeles.get('modeles_surf', {})
print(f"   IA spécialisées disponibles : {list(modeles_surf.keys())}")

df = pd.read_csv(FICHIER_BASE, low_memory=False)
df = df[df['type'] != 'Doubles'] if 'type' in df.columns else df
df['tourney_date'] = pd.to_datetime(df['tourney_date'], errors='coerce')
df = df.sort_values('tourney_date').reset_index(drop=True)
print(f"   ✅ {len(df):,} matchs chargés")

# ── Recalcul des features (identique à étape 1) ──
print("\n🔧 Calcul des features...")

def parser_score(s):
    if not isinstance(s, str): return np.nan, np.nan, np.nan
    s = re.sub(r'RET|W/O|DEF|ABN|Ret\.|\(.*?\)', '', s, flags=re.IGNORECASE).strip()
    sets = re.findall(r'(\d+)-(\d+)', s)
    if not sets: return np.nan, np.nan, np.nan
    nb = len(sets); sw = sum(1 for a, b in sets if int(a) > int(b))
    return nb, sw, sw - (nb - sw)

parsed = df['score'].apply(parser_score)
df['nb_sets']       = pd.array([p[0] for p in parsed], dtype='Int8')
df['handicap_sets'] = pd.array([p[2] for p in parsed], dtype='Int8')

# ELO
elo_g = defaultdict(lambda: 1500.0)
elo_s = defaultdict(lambda: defaultdict(lambda: 1500.0))
elo_wg, elo_lg, elo_ws, elo_ls = [], [], [], []
for _, row in df.iterrows():
    w = str(row['winner_name']); l = str(row['loser_name']); surf = str(row['surface'])
    elo_wg.append(elo_g[w]); elo_lg.append(elo_g[l])
    elo_ws.append(elo_s[surf][w]); elo_ls.append(elo_s[surf][l])
    ea = 1/(1+10**((elo_g[l]-elo_g[w])/400))
    elo_g[w] += 32*(1-ea); elo_g[l] += 32*(0-(1-ea))
    ea_s = 1/(1+10**((elo_s[surf][l]-elo_s[surf][w])/400))
    elo_s[surf][w] += 32*(1-ea_s); elo_s[surf][l] += 32*(0-(1-ea_s))
df['elo_winner'] = np.array(elo_wg, dtype='float32')
df['elo_loser']  = np.array(elo_lg, dtype='float32')
df['elo_winner_surf'] = np.array(elo_ws, dtype='float32')
df['elo_loser_surf']  = np.array(elo_ls, dtype='float32')
df['elo_diff']      = (df['elo_winner'] - df['elo_loser']).astype('float32')
df['elo_diff_surf'] = (df['elo_winner_surf'] - df['elo_loser_surf']).astype('float32')

# Forme
hist = defaultdict(list)
fw_l, fl_l = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    hw = hist[w][-10:]; hl = hist[l][-10:]
    fw_l.append(sum(hw)/len(hw) if hw else 0.5)
    fl_l.append(sum(hl)/len(hl) if hl else 0.5)
    hist[w].append(1); hist[l].append(0)
df['forme_winner'] = np.array(fw_l, dtype='float32')
df['forme_loser']  = np.array(fl_l, dtype='float32')
df['forme_diff']   = (df['forme_winner'] - df['forme_loser']).astype('float32')

# H2H
h2h = defaultdict(lambda: [0, 0])
hw_l2, hl_l2 = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    key = tuple(sorted([w, l])); tot = h2h[key][1]
    if tot > 0:
        wins_w = h2h[key][0] if key[0]==w else tot - h2h[key][0]
        hw_l2.append(wins_w/tot); hl_l2.append(1-wins_w/tot)
    else:
        hw_l2.append(0.5); hl_l2.append(0.5)
    h2h[key][1] += 1
    if key[0] == w: h2h[key][0] += 1
df['h2h_winner'] = np.array(hw_l2, dtype='float32')
df['h2h_loser']  = np.array(hl_l2, dtype='float32')
df['h2h_diff']   = (df['h2h_winner'] - df['h2h_loser']).astype('float32')

# Fatigue
mj = defaultdict(list)
fw3, fl3 = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name']); d = row['tourney_date']
    if pd.notna(d):
        fw3.append(sum(1 for dd in mj[w] if (d-dd).days <= 7))
        fl3.append(sum(1 for dd in mj[l] if (d-dd).days <= 7))
        mj[w] = (mj[w]+[d])[-30:]; mj[l] = (mj[l]+[d])[-30:]
    else:
        fw3.append(0); fl3.append(0)
df['fatigue_winner'] = np.array(fw3, dtype='float32')
df['fatigue_loser']  = np.array(fl3, dtype='float32')
df['fatigue_diff']   = (df['fatigue_winner'] - df['fatigue_loser']).astype('float32')

# Features psychologiques (simplifiées pour ce script)
for col in ['streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
            'dominance_diff','revanche_diff','hist_tournoi_diff']:
    if col not in df.columns: df[col] = 0.0

def safe_float(val, defaut=500.0):
    try: f = float(str(val)); return defaut if np.isnan(f) else f
    except: return defaut

surface_map = {'Carpet':0,'Clay':1,'Clay (Indoor)':2,'Grass':3,'Hard':4,'Hard (Indoor)':5,'Unknown':6}
circuit_map = {'ATP':0,'Challenger':1,'Futures':2,'ITF':3,'Juniors':4,'Teams Men':5,'Teams Women':6,'WTA':7}

df['rank_diff']   = (df['loser_rank'].apply(safe_float) - df['winner_rank'].apply(safe_float)).astype('float32')
df['age_diff']    = (df['winner_age'].apply(lambda x: safe_float(x,0)) - df['loser_age'].apply(lambda x: safe_float(x,0))).astype('float32')
df['round_num']   = df['round'].astype(str).apply(simplifier_round)
df['surface_enc'] = df['surface'].map(surface_map).fillna(4).astype(int)
df['circuit_enc'] = df['circuit'].map(circuit_map).fillna(0).astype(int) if 'circuit' in df.columns else 0
df['genre_enc']   = (df['genre'].astype(str) == 'F').astype(int) if 'genre' in df.columns else 0
df['cote_diff'] = 0.0; df['cote_proba_A'] = 0.5; df['cote_proba_B'] = 0.5
if 'best_of' not in df.columns: df['best_of'] = 3
df['best_of'] = pd.to_numeric(df['best_of'], errors='coerce').fillna(3).astype(int)

df_clean = df.dropna(subset=['elo_diff','forme_diff']).copy()
print(f"   ✅ Features calculées sur {len(df_clean):,} matchs")

# ============================================================
# GÉNÉRATION OUT-OF-FOLD
# ============================================================
print("\n🔄 Génération out-of-fold (5 folds)...")
print("   ⏳ Cela prend 60-90 minutes — chaque fold réentraîne 4 modèles")

X = df_clean[FEATURES].fillna(0).astype('float32').values
y = np.ones(len(df_clean), dtype=int)  # 1 = winner_name gagne

surfaces = df_clean['surface'].values

# Matrice méta : [proba_gen, proba_clay, proba_hard, proba_grass]
meta = np.full((len(df_clean), 4), 0.5, dtype='float32')

kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for fold, (train_idx, val_idx) in enumerate(kf.split(X, y)):
    print(f"\n  Fold {fold+1}/5 — {len(val_idx):,} matchs en validation...")

    X_tr, X_val = X[train_idx], X[val_idx]
    y_tr = y[train_idx]
    surfs_tr  = surfaces[train_idx]
    surfs_val = surfaces[val_idx]

    # ── IA Générale sur ce fold ──
    ia_gen = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric='logloss', random_state=42, n_jobs=-1
    )
    # Dataset symétrique pour ce fold
    X_tr_sym = np.vstack([X_tr, X_tr.copy()])
    y_tr_sym  = np.array([1]*len(X_tr) + [0]*len(X_tr))
    ia_gen.fit(X_tr_sym, y_tr_sym, verbose=False)
    meta[val_idx, 0] = ia_gen.predict_proba(X_val)[:, 1]
    print(f"    IA Générale — fold {fold+1} entraîné")

    # ── IA Spécialisées sur ce fold ──
    for i, surface in enumerate(['Clay', 'Hard', 'Grass'], start=1):
        mask_tr  = surfs_tr == surface
        mask_val = surfs_val == surface

        n_tr = mask_tr.sum()
        n_val = mask_val.sum()

        if n_tr < 1000 or n_val == 0:
            # Pas assez → on utilise l'IA générale
            if n_val > 0:
                meta[val_idx[mask_val], i] = meta[val_idx[mask_val], 0]
            print(f"    IA {surface} — fold {fold+1} : trop peu ({n_tr}) → général utilisé")
            continue

        X_surf_tr = X_tr[mask_tr]
        X_surf_sym = np.vstack([X_surf_tr, X_surf_tr.copy()])
        y_surf_sym  = np.array([1]*len(X_surf_tr) + [0]*len(X_surf_tr))

        ia_surf = XGBClassifier(
            n_estimators=250, max_depth=4, min_child_weight=15,
            learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
            eval_metric='logloss', random_state=42, n_jobs=-1
        )
        ia_surf.fit(X_surf_sym, y_surf_sym, verbose=False)

        # Prédire sur TOUS les matchs de validation (pas seulement la surface)
        meta[val_idx, i] = ia_surf.predict_proba(X_val)[:, 1]
        print(f"    IA {surface} — fold {fold+1} : {n_tr:,} matchs entraînés, {n_val:,} validés")

# ============================================================
# CONSTRUCTION DU DATASET MÉTA
# ============================================================
print("\n📊 Construction du dataset méta...")

surface_code_map = {'Clay': 1, 'Hard': 2, 'Grass': 3, 'Carpet': 4}

df_meta = pd.DataFrame({
    # Probas des 4 IA (features principales)
    'proba_generale' : meta[:, 0],
    'proba_clay'     : meta[:, 1],
    'proba_hard'     : meta[:, 2],
    'proba_grass'    : meta[:, 3],

    # Contexte du match
    'surface_code'   : df_clean['surface'].map(surface_code_map).fillna(0).values,
    'elo_diff'       : df_clean['elo_diff'].values,
    'rank_diff'      : df_clean['rank_diff'].values,

    # Méta-features dérivées
    'consensus_score': meta.max(axis=1) - meta.min(axis=1),
    'surface_ia_active': df_clean['surface'].isin(modeles_surf.keys()).astype(int).values,

    # Cible
    'target': y
})

df_meta.to_csv(FICHIER_META, index=False)

# Statistiques
print(f"\n{'='*60}")
print(f"✅ DATASET MÉTA GÉNÉRÉ")
print(f"{'='*60}")
print(f"  Fichier : {FICHIER_META}")
print(f"  Lignes  : {len(df_meta):,}")
print(f"  Features: {len(df_meta.columns)-1}")
print(f"\n  Statistiques des probas :")
for col in ['proba_generale','proba_clay','proba_hard','proba_grass']:
    print(f"  {col:<20} : moy={df_meta[col].mean():.3f} std={df_meta[col].std():.3f}")
print(f"\n  Consensus moyen : {df_meta['consensus_score'].mean():.3f}")
print(f"  Matchs avec IA active : {df_meta['surface_ia_active'].sum():,}")
print(f"{'='*60}")
print(f"\n✅ Prochaine étape : lancer etape3_ia_supreme.py")
