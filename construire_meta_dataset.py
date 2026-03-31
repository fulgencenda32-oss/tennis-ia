# ============================================================
# CONSTRUCTION DU META-DATASET — Tennis IA Suprême
# Génère meta_dataset.csv avec probas out-of-fold (5 folds)
# À exécuter UNE FOIS (ou quand la base change significativement)
# ============================================================
import pandas as pd
import numpy as np
import os, re, pickle, gc
from datetime import datetime
from collections import defaultdict
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
DOSSIER        = r"C:\Users\HP\OneDrive\Documents\Tennis_IA"
FICHIER_BASE   = os.path.join(DOSSIER, "data", "BASE_FEATURES.csv")
FICHIER_META   = os.path.join(DOSSIER, "data", "meta_dataset.csv")
N_FOLDS        = 5

print("=" * 60)
print("🧠 CONSTRUCTION META-DATASET — IA SUPRÊME")
print("=" * 60)

# ============================================================
# ÉTAPE 1 — CHARGEMENT ET CALCUL DES FEATURES
# (Reproduction exacte de entrainement_hebdo.py)
# ============================================================
print("\n📂 Chargement base...")
df = pd.read_csv(FICHIER_BASE, low_memory=False)
df['tourney_date'] = pd.to_datetime(df['tourney_date'], errors='coerce')
df = df.sort_values('tourney_date').reset_index(drop=True)
print(f"   ✅ {len(df):,} matchs chargés")

# Parsing scores
print("\n🔄 Calcul des features...")
def parser_score(s):
    if not isinstance(s, str): return np.nan, np.nan, np.nan, np.nan
    s = re.sub(r'RET|W/O|DEF|ABN|Ret\.|\(.*?\)', '', s, flags=re.IGNORECASE).strip()
    sets = re.findall(r'(\d+)-(\d+)', s)
    if not sets: return np.nan, np.nan, np.nan, np.nan
    nb = len(sets)
    sw = sum(1 for a, b in sets if int(a) > int(b))
    total_jeux = sum(int(a) + int(b) for a, b in sets)
    return nb, sw, sw - (nb - sw), total_jeux

parsed = df['score'].apply(parser_score)
df['nb_sets']       = pd.array([p[0] for p in parsed], dtype='Int8')
df['sets_winner']   = pd.array([p[1] for p in parsed], dtype='Int8')
df['handicap_sets'] = pd.array([p[2] for p in parsed], dtype='Int8')
df['total_jeux']    = pd.array([p[3] for p in parsed], dtype='Int16')

# ELO
print("   ⚡ ELO...")
elo_g = defaultdict(lambda: 1500.0)
elo_s = defaultdict(lambda: defaultdict(lambda: 1500.0))
elo_wg, elo_lg, elo_ws, elo_ls = [], [], [], []
for _, row in df.iterrows():
    w = str(row['winner_name']); l = str(row['loser_name']); surf = str(row['surface'])
    elo_wg.append(elo_g[w]); elo_lg.append(elo_g[l])
    elo_ws.append(elo_s[surf][w]); elo_ls.append(elo_s[surf][l])
    ea = 1 / (1 + 10**((elo_g[l] - elo_g[w]) / 400))
    elo_g[w] += 32*(1-ea); elo_g[l] += 32*(0-(1-ea))
    ea_s = 1 / (1 + 10**((elo_s[surf][l] - elo_s[surf][w]) / 400))
    elo_s[surf][w] += 32*(1-ea_s); elo_s[surf][l] += 32*(0-(1-ea_s))
df['elo_winner']      = np.array(elo_wg, dtype='float32')
df['elo_loser']       = np.array(elo_lg, dtype='float32')
df['elo_winner_surf'] = np.array(elo_ws, dtype='float32')
df['elo_loser_surf']  = np.array(elo_ls, dtype='float32')
df['elo_diff']        = (df['elo_winner'] - df['elo_loser']).astype('float32')
df['elo_diff_surf']   = (df['elo_winner_surf'] - df['elo_loser_surf']).astype('float32')

# Forme
print("   📈 Forme...")
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
print("   🤝 H2H...")
h2h = defaultdict(lambda: [0, 0])
hw_l, hl_l = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    key = tuple(sorted([w, l])); tot = h2h[key][1]
    if tot > 0:
        wins_w = h2h[key][0] if key[0]==w else tot - h2h[key][0]
        hw_l.append(wins_w/tot); hl_l.append(1-wins_w/tot)
    else:
        hw_l.append(0.5); hl_l.append(0.5)
    h2h[key][1] += 1
    if key[0] == w: h2h[key][0] += 1
df['h2h_winner'] = np.array(hw_l, dtype='float32')
df['h2h_loser']  = np.array(hl_l, dtype='float32')
df['h2h_diff']   = (df['h2h_winner'] - df['h2h_loser']).astype('float32')

# Fatigue
print("   😴 Fatigue...")
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

# Streak
print("   🔥 Streak...")
streak_joueur = defaultdict(int)
streak_w_list, streak_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    streak_w_list.append(streak_joueur[w])
    streak_l_list.append(streak_joueur[l])
    streak_joueur[w] += 1; streak_joueur[l] = 0
df['streak_winner'] = np.array(streak_w_list, dtype='float32')
df['streak_loser']  = np.array(streak_l_list, dtype='float32')
df['streak_diff']   = (df['streak_winner'] - df['streak_loser']).astype('float32')

# Comeback
print("   💪 Comeback...")
def parser_sets_scores(s):
    if not isinstance(s, str): return []
    sets = re.findall(r'(\d+)-(\d+)', s)
    return [(int(a), int(b)) for a, b in sets]

comeback_w = defaultdict(lambda: [0, 0])
comeback_l = defaultdict(lambda: [0, 0])
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    sets = parser_sets_scores(str(row.get('score', '')))
    if len(sets) >= 2:
        if not (sets[0][0] > sets[0][1]):
            comeback_w[w][1] += 1; comeback_w[w][0] += 1
        if sets[0][0] > sets[0][1]:
            comeback_l[l][1] += 1
comeback_final = {}
for j in set(list(comeback_w.keys()) + list(comeback_l.keys())):
    wins = comeback_w[j][0]; opp = comeback_w[j][1] + comeback_l[j][1]
    comeback_final[j] = round(wins / opp, 3) if opp > 0 else 0.3
comeback_w_list, comeback_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    comeback_w_list.append(comeback_final.get(w, 0.3))
    comeback_l_list.append(comeback_final.get(l, 0.3))
df['comeback_winner'] = np.array(comeback_w_list, dtype='float32')
df['comeback_loser']  = np.array(comeback_l_list, dtype='float32')
df['comeback_diff']   = (df['comeback_winner'] - df['comeback_loser']).astype('float32')

# Clutch
print("   🎯 Clutch...")
clutch_w = defaultdict(lambda: [0, 0])
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    nb = row.get('nb_sets', 2)
    try: nb = int(nb)
    except: nb = 2
    if nb >= 3:
        clutch_w[w][0] += 1; clutch_w[w][1] += 1; clutch_w[l][1] += 1
clutch_final = {j: round(v[0]/v[1], 3) if v[1] > 0 else 0.5 for j, v in clutch_w.items()}
clutch_w_list, clutch_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    clutch_w_list.append(clutch_final.get(w, 0.5))
    clutch_l_list.append(clutch_final.get(l, 0.5))
df['clutch_winner'] = np.array(clutch_w_list, dtype='float32')
df['clutch_loser']  = np.array(clutch_l_list, dtype='float32')
df['clutch_diff']   = (df['clutch_winner'] - df['clutch_loser']).astype('float32')

# Big match
print("   🏆 Big match...")
bigmatch_w = defaultdict(lambda: [0, 0])
bigmatch_l = defaultdict(lambda: [0, 0])
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    rnd = str(row.get('round', '')).upper()
    if 'FINAL' in rnd or rnd == 'F':
        bigmatch_w[w][0] += 1; bigmatch_w[w][1] += 1; bigmatch_l[l][1] += 1
bigmatch_final = {}
for j in set(list(bigmatch_w.keys()) + list(bigmatch_l.keys())):
    total = bigmatch_w[j][1] + bigmatch_l[j][1]; wins = bigmatch_w[j][0]
    bigmatch_final[j] = round(wins / total, 3) if total > 0 else 0.5
bigmatch_w_list, bigmatch_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    bigmatch_w_list.append(bigmatch_final.get(w, 0.5))
    bigmatch_l_list.append(bigmatch_final.get(l, 0.5))
df['bigmatch_winner'] = np.array(bigmatch_w_list, dtype='float32')
df['bigmatch_loser']  = np.array(bigmatch_l_list, dtype='float32')
df['bigmatch_diff']   = (df['bigmatch_winner'] - df['bigmatch_loser']).astype('float32')

# Dominance
print("   💥 Dominance...")
dominance_w = defaultdict(lambda: [0, 0])
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    sets = parser_sets_scores(str(row.get('score', '')))
    dominance_w[w][1] += 1
    for a, b in sets:
        if a == 6 and b == 0: dominance_w[w][0] += 1
dominance_final = {j: round(v[0]/v[1], 3) if v[1] > 0 else 0.0 for j, v in dominance_w.items()}
dom_w_list, dom_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    dom_w_list.append(dominance_final.get(w, 0.0))
    dom_l_list.append(dominance_final.get(l, 0.0))
df['dominance_winner'] = np.array(dom_w_list, dtype='float32')
df['dominance_loser']  = np.array(dom_l_list, dtype='float32')
df['dominance_diff']   = (df['dominance_winner'] - df['dominance_loser']).astype('float32')

# Revanche
print("   🔄 Revanche...")
last_result = {}
revanche_w_list, revanche_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    revanche_w_list.append(1 - last_result.get((w, l), 0.5))
    revanche_l_list.append(1 - last_result.get((l, w), 0.5))
    last_result[(w, l)] = 1; last_result[(l, w)] = 0
df['revanche_winner'] = np.array(revanche_w_list, dtype='float32')
df['revanche_loser']  = np.array(revanche_l_list, dtype='float32')
df['revanche_diff']   = (df['revanche_winner'] - df['revanche_loser']).astype('float32')

# Historique tournoi
print("   📅 Historique tournoi...")
tournoi_hist = defaultdict(lambda: defaultdict(lambda: [0, 0]))
hist_w_list, hist_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    t = str(row.get('tourney_name', '')).lower()[:30]
    hist_w_list.append(tournoi_hist[w][t][0] / tournoi_hist[w][t][1] if tournoi_hist[w][t][1] > 0 else 0.5)
    hist_l_list.append(tournoi_hist[l][t][0] / tournoi_hist[l][t][1] if tournoi_hist[l][t][1] > 0 else 0.5)
    tournoi_hist[w][t][0] += 1; tournoi_hist[w][t][1] += 1; tournoi_hist[l][t][1] += 1
df['hist_tournoi_winner'] = np.array(hist_w_list, dtype='float32')
df['hist_tournoi_loser']  = np.array(hist_l_list, dtype='float32')
df['hist_tournoi_diff']   = (df['hist_tournoi_winner'] - df['hist_tournoi_loser']).astype('float32')

# Encodage
def safe_float(val, defaut=500.0):
    try:
        f = float(str(val)); return defaut if np.isnan(f) else f
    except: return defaut

def simplifier_round(r):
    r = str(r).upper()
    if 'QUARTER' in r or 'QF' in r: return 4
    if 'SEMI'    in r or 'SF' in r: return 5
    if r in ['F','FINAL','THE FINAL']: return 6
    if 'R128' in r: return 1
    if 'R64'  in r: return 2
    if 'R32'  in r: return 3
    return 3

surface_map = {'Carpet':0,'Clay':1,'Clay (Indoor)':2,'Grass':3,'Hard':4,'Hard (Indoor)':5,'Unknown':6}
circuit_map = {'ATP':0,'Challenger':1,'Futures':2,'ITF':3,'Juniors':4,'Teams Men':5,'Teams Women':6,'WTA':7}

df['rank_diff']   = (df['loser_rank'].apply(safe_float) - df['winner_rank'].apply(safe_float)).astype('float32')
df['age_diff']    = (df['winner_age'].apply(lambda x: safe_float(x,0)) - df['loser_age'].apply(lambda x: safe_float(x,0))).astype('float32')
df['round_num']   = df['round'].astype(str).apply(simplifier_round)
df['surface_enc'] = df['surface'].map(surface_map).fillna(4).astype(int)
df['circuit_enc'] = df['circuit'].map(circuit_map).fillna(0).astype(int) if 'circuit' in df.columns else 0
df['genre_enc']   = (df['genre'].astype(str) == 'F').astype(int) if 'genre' in df.columns else 0
df['cote_diff']   = 0.0; df['cote_proba_A'] = 0.5; df['cote_proba_B'] = 0.5
if 'best_of' not in df.columns: df['best_of'] = 3
df['best_of'] = pd.to_numeric(df['best_of'], errors='coerce').fillna(3).astype(int)

print("   ✅ Toutes les features calculées !")

# ============================================================
# ÉTAPE 2 — DATASET SYMÉTRIQUE
# ============================================================
FEATURES = [
    'elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff',
    'streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
    'dominance_diff','revanche_diff','hist_tournoi_diff',
    'rank_diff','age_diff','surface_enc','circuit_enc','genre_enc',
    'best_of','round_num','cote_diff','cote_proba_A','cote_proba_B'
]

print("\n🔀 Construction dataset symétrique...")
df_clean = df.dropna(subset=['elo_diff','forme_diff']).copy()

df_A = df_clean.copy(); df_A['target'] = 1
df_B = df_clean.copy(); df_B['target'] = 0
cols_inv = ['elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff',
            'streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
            'dominance_diff','revanche_diff','hist_tournoi_diff',
            'rank_diff','age_diff','cote_diff']
for col in cols_inv:
    df_B[col] = -df_clean[col].fillna(0).values
df_B['cote_proba_A'] = df_clean['cote_proba_B'].values
df_B['cote_proba_B'] = df_clean['cote_proba_A'].values

X_A = df_A[FEATURES].fillna(0).astype('float32')
y_A = pd.Series([1]*len(X_A), dtype=int)
surf_A = df_A['surface'].values

X_B = df_B[FEATURES].fillna(0).astype('float32')
y_B = pd.Series([0]*len(X_B), dtype=int)
surf_B = df_B['surface'].values

del df_A, df_B
gc.collect()

X_sym = pd.concat([X_A, X_B], ignore_index=True)
y_sym = pd.concat([y_A, y_B], ignore_index=True)
surf_sym = np.concatenate([surf_A, surf_B])

del X_A, X_B, y_A, y_B, surf_A, surf_B
gc.collect()

# Mélange déterministe
idx = np.random.default_rng(42).permutation(len(X_sym))
X_sym = X_sym.iloc[idx].reset_index(drop=True)
y_sym = y_sym.iloc[idx].reset_index(drop=True)
surf_sym = surf_sym[idx]
gc.collect()

print(f"   ✅ {len(X_sym):,} lignes (symétrique)")

# ============================================================
# ÉTAPE 3 — CROSS-VALIDATION OUT-OF-FOLD (5 folds)
# ============================================================
print(f"\n🔄 Cross-validation {N_FOLDS} folds...")
print("   ⚠️ Cela peut prendre plusieurs minutes...\n")

SURFACES_SPECIALISEES = {
    'Clay':  ['Clay', 'Clay (Indoor)'],
    'Hard':  ['Hard', 'Hard (Indoor)'],
    'Grass': ['Grass'],
}

# Colonnes de sortie
proba_generale = np.zeros(len(X_sym), dtype='float32')
proba_clay     = np.zeros(len(X_sym), dtype='float32')
proba_hard     = np.zeros(len(X_sym), dtype='float32')
proba_grass    = np.zeros(len(X_sym), dtype='float32')

skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)

for fold_num, (train_idx, val_idx) in enumerate(skf.split(X_sym, y_sym), 1):
    print(f"   📂 Fold {fold_num}/{N_FOLDS} — {len(train_idx):,} train / {len(val_idx):,} val")

    X_fold_tr = X_sym.iloc[train_idx]
    y_fold_tr = y_sym.iloc[train_idx]
    X_fold_val = X_sym.iloc[val_idx]
    surf_fold_tr = surf_sym[train_idx]
    surf_fold_val = surf_sym[val_idx]

    # --- IA Générale ---
    model_gen = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric='logloss', random_state=42, n_jobs=-1
    )
    model_gen.fit(X_fold_tr, y_fold_tr, verbose=False)
    proba_generale[val_idx] = model_gen.predict_proba(X_fold_val)[:, 1]
    print(f"      ✅ IA Générale OK")

    # --- IA Spécialisées ---
    for surf_nom, surf_variantes in SURFACES_SPECIALISEES.items():
        # Filtrer les données train pour cette surface
        mask_tr_surf = np.isin(surf_fold_tr, surf_variantes)
        nb_train_surf = mask_tr_surf.sum()

        if nb_train_surf < 500:
            # Pas assez de données → utiliser la proba générale comme fallback
            mask_val_surf = np.isin(surf_fold_val, surf_variantes)
            val_idx_surf = val_idx[mask_val_surf]
            if surf_nom == 'Clay':
                proba_clay[val_idx_surf] = proba_generale[val_idx_surf]
            elif surf_nom == 'Hard':
                proba_hard[val_idx_surf] = proba_generale[val_idx_surf]
            elif surf_nom == 'Grass':
                proba_grass[val_idx_surf] = proba_generale[val_idx_surf]
            print(f"      ⚠️ IA {surf_nom} : {nb_train_surf} matchs → fallback Générale")
            continue

        X_surf_tr = X_fold_tr.iloc[np.where(mask_tr_surf)[0]]
        y_surf_tr = y_fold_tr.iloc[np.where(mask_tr_surf)[0]]

        model_surf = XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric='logloss', random_state=42, n_jobs=-1
        )
        model_surf.fit(X_surf_tr, y_surf_tr, verbose=False)

        # Prédire sur TOUS les matchs du fold val (pas seulement cette surface)
        # Car en production, on ne sait pas toujours la surface parfaitement
        probas_surf = model_surf.predict_proba(X_fold_val)[:, 1]

        if surf_nom == 'Clay':
            proba_clay[val_idx] = probas_surf
        elif surf_nom == 'Hard':
            proba_hard[val_idx] = probas_surf
        elif surf_nom == 'Grass':
            proba_grass[val_idx] = probas_surf

        print(f"      ✅ IA {surf_nom} OK ({nb_train_surf:,} matchs)")

    del model_gen, X_fold_tr, y_fold_tr, X_fold_val
    gc.collect()

print(f"\n   ✅ Cross-validation terminée !")

# ============================================================
# ÉTAPE 4 — ASSEMBLAGE ET SAUVEGARDE
# ============================================================
print("\n💾 Assemblage meta_dataset.csv...")

meta_df = pd.DataFrame({
    'proba_generale': proba_generale,
    'proba_clay':     proba_clay,
    'proba_hard':     proba_hard,
    'proba_grass':    proba_grass,
    'surface':        surf_sym,
    'surface_enc':    X_sym['surface_enc'].values,
    'target':         y_sym.values,
})

# Vérification : aucune ligne ne doit avoir toutes les probas à 0
nb_zero = (meta_df[['proba_generale','proba_clay','proba_hard','proba_grass']].sum(axis=1) == 0).sum()
if nb_zero > 0:
    print(f"   ⚠️ {nb_zero} lignes avec probas nulles → supprimées")
    meta_df = meta_df[meta_df[['proba_generale','proba_clay','proba_hard','proba_grass']].sum(axis=1) > 0]

meta_df.to_csv(FICHIER_META, index=False)
print(f"   ✅ {FICHIER_META}")
print(f"   ✅ {len(meta_df):,} lignes sauvegardées")

# ============================================================
# RÉSUMÉ
# ============================================================
print(f"\n{'='*60}")
print(f"🎉 META-DATASET CONSTRUIT AVEC SUCCÈS")
print(f"{'='*60}")
print(f"  Lignes totales     : {len(meta_df):,}")
print(f"  Folds              : {N_FOLDS}")
print(f"  Colonnes           : {list(meta_df.columns)}")
print(f"  Proba Générale     : min={meta_df['proba_generale'].min():.3f}  max={meta_df['proba_generale'].max():.3f}  moy={meta_df['proba_generale'].mean():.3f}")
print(f"  Proba Clay         : min={meta_df['proba_clay'].min():.3f}  max={meta_df['proba_clay'].max():.3f}  moy={meta_df['proba_clay'].mean():.3f}")
print(f"  Proba Hard         : min={meta_df['proba_hard'].min():.3f}  max={meta_df['proba_hard'].max():.3f}  moy={meta_df['proba_hard'].mean():.3f}")
print(f"  Proba Grass        : min={meta_df['proba_grass'].min():.3f}  max={meta_df['proba_grass'].max():.3f}  moy={meta_df['proba_grass'].mean():.3f}")
print(f"  Répartition surface:")
for surf in meta_df['surface'].unique():
    n = (meta_df['surface'] == surf).sum()
    print(f"    {surf:20s} : {n:,} ({n/len(meta_df)*100:.1f}%)")
print(f"  Fichier            : {FICHIER_META}")
print(f"  Date               : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")
print(f"\n✅ Prêt pour l'Étape 3 : entrainer_ia_supreme.py")