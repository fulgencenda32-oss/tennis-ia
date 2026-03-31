# ============================================================
# ÉTAPE 1 — IA SPÉCIALISÉES PAR SURFACE
# Tennis IA | Fulgence N'da
# Lancez ce script APRÈS entrainement_hebdo.py (70.2% confirmé)
# Durée estimée : 30-45 minutes
# ============================================================
import pandas as pd
import numpy as np
import os, re, pickle
from datetime import datetime
from collections import defaultdict
from sklearn.model_selection import train_test_split
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
HF_REPO_SPACE  = "fulgence10/IA-tennis"

FEATURES = [
    'elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff',
    'streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
    'dominance_diff','revanche_diff','hist_tournoi_diff',
    'rank_diff','age_diff','surface_enc','circuit_enc',
    'genre_enc','best_of','round_num','cote_diff','cote_proba_A','cote_proba_B',
]

# Paramètres par surface — régularisation selon volume de données
SURFACES_CONFIG = {
    'Clay' : {'max_depth': 5, 'min_child_weight': 15, 'n_estimators': 350},
    'Hard' : {'max_depth': 6, 'min_child_weight': 10, 'n_estimators': 400},
    'Grass': {'max_depth': 4, 'min_child_weight': 20, 'n_estimators': 250},
}

print("=" * 60)
print("🎾 IA SPÉCIALISÉES PAR SURFACE — ÉTAPE 1")
print("=" * 60)

# ============================================================
# CHARGEMENT MODÈLE EXISTANT
# ============================================================
print("\n📦 Chargement du modèle existant...")

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
acc_general = modeles.get('acc_win', 0)
print(f"   ✅ Modèle général chargé — précision : {acc_general*100:.1f}%")

# ============================================================
# CHARGEMENT ET PRÉPARATION DES DONNÉES
# ============================================================
print("\n📂 Chargement de la base...")
df = pd.read_csv(FICHIER_BASE, low_memory=False)
df = df[df['type'] != 'Doubles'] if 'type' in df.columns else df
df['tourney_date'] = pd.to_datetime(df['tourney_date'], errors='coerce')
df = df.sort_values('tourney_date').reset_index(drop=True)
print(f"   ✅ {len(df):,} matchs simples chargés")

# ── Parsing scores ──
def parser_score(s):
    if not isinstance(s, str): return np.nan, np.nan, np.nan
    s = re.sub(r'RET|W/O|DEF|ABN|Ret\.|\(.*?\)', '', s, flags=re.IGNORECASE).strip()
    sets = re.findall(r'(\d+)-(\d+)', s)
    if not sets: return np.nan, np.nan, np.nan
    nb = len(sets)
    sw = sum(1 for a, b in sets if int(a) > int(b))
    return nb, sw, sw - (nb - sw)

parsed = df['score'].apply(parser_score)
df['nb_sets']       = pd.array([p[0] for p in parsed], dtype='Int8')
df['handicap_sets'] = pd.array([p[2] for p in parsed], dtype='Int8')

# ── ELO ──
print("⚡ Calcul ELO...")
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

# ── Forme ──
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

# ── H2H ──
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

# ── Fatigue ──
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

# ── Features psychologiques ──
print("🧠 Calcul features psychologiques...")
streak_d = defaultdict(int)
comeback_d = defaultdict(list)
clutch_d = defaultdict(list)
bigmatch_d = defaultdict(list)
dominance_d = defaultdict(list)
tournoi_d = defaultdict(lambda: defaultdict(list))
revanche_d = {}

streak_wl, streak_ll = [], []
comeback_wl, comeback_ll = [], []
clutch_wl, clutch_ll = [], []
bigmatch_wl, bigmatch_ll = [], []
dominance_wl, dominance_ll = [], []
tournoi_wl, tournoi_ll = [], []
revanche_wl, revanche_ll = [], []

for _, row in df.iterrows():
    w = str(row['winner_name']); l = str(row['loser_name'])
    rnd = str(row.get('round', 'R32')).upper()
    t_key = str(row.get('tourney_name', ''))[:30].lower()
    nb_s = row.get('nb_sets', np.nan)

    streak_wl.append(float(streak_d[w])); streak_ll.append(float(streak_d[l]))
    streak_d[w] += 1; streak_d[l] = 0

    comeback_wl.append(np.mean(comeback_d[w]) if comeback_d[w] else 0.3)
    comeback_ll.append(np.mean(comeback_d[l]) if comeback_d[l] else 0.3)
    if pd.notna(nb_s) and nb_s >= 3:
        comeback_d[w].append(1.0); comeback_d[l].append(0.0)
    comeback_d[w] = comeback_d[w][-30:]; comeback_d[l] = comeback_d[l][-30:]

    clutch_wl.append(np.mean(clutch_d[w]) if clutch_d[w] else 0.5)
    clutch_ll.append(np.mean(clutch_d[l]) if clutch_d[l] else 0.5)
    if pd.notna(nb_s) and nb_s >= 3:
        clutch_d[w].append(1.0); clutch_d[l].append(0.0)
    clutch_d[w] = clutch_d[w][-30:]; clutch_d[l] = clutch_d[l][-30:]

    is_big = any(x in rnd for x in ['QF','SF','FINAL','QUARTER','SEMI'])
    bigmatch_wl.append(np.mean(bigmatch_d[w]) if bigmatch_d[w] else 0.5)
    bigmatch_ll.append(np.mean(bigmatch_d[l]) if bigmatch_d[l] else 0.5)
    if is_big:
        bigmatch_d[w].append(1.0); bigmatch_d[l].append(0.0)
    bigmatch_d[w] = bigmatch_d[w][-30:]; bigmatch_d[l] = bigmatch_d[l][-30:]

    dominance_wl.append(np.mean(dominance_d[w]) if dominance_d[w] else 0.0)
    dominance_ll.append(np.mean(dominance_d[l]) if dominance_d[l] else 0.0)
    handi = row.get('handicap_sets', np.nan)
    if pd.notna(handi) and abs(handi) >= 2:
        dominance_d[w].append(1.0); dominance_d[l].append(0.0)
    dominance_d[w] = dominance_d[w][-20:]; dominance_d[l] = dominance_d[l][-20:]

    tournoi_wl.append(np.mean(tournoi_d[w][t_key]) if tournoi_d[w][t_key] else 0.5)
    tournoi_ll.append(np.mean(tournoi_d[l][t_key]) if tournoi_d[l][t_key] else 0.5)
    tournoi_d[w][t_key].append(1.0); tournoi_d[l][t_key].append(0.0)
    tournoi_d[w][t_key] = tournoi_d[w][t_key][-10:]
    tournoi_d[l][t_key] = tournoi_d[l][t_key][-10:]

    revanche_wl.append(1 - revanche_d.get((w, l), 0.5))
    revanche_ll.append(1 - revanche_d.get((l, w), 0.5))
    revanche_d[(w, l)] = 1; revanche_d[(l, w)] = 0

df['streak_diff']       = (np.array(streak_wl)   - np.array(streak_ll)).astype('float32')
df['comeback_diff']     = (np.array(comeback_wl)  - np.array(comeback_ll)).astype('float32')
df['clutch_diff']       = (np.array(clutch_wl)    - np.array(clutch_ll)).astype('float32')
df['bigmatch_diff']     = (np.array(bigmatch_wl)  - np.array(bigmatch_ll)).astype('float32')
df['dominance_diff']    = (np.array(dominance_wl) - np.array(dominance_ll)).astype('float32')
df['hist_tournoi_diff'] = (np.array(tournoi_wl)   - np.array(tournoi_ll)).astype('float32')
df['revanche_diff']     = (np.array(revanche_wl)  - np.array(revanche_ll)).astype('float32')

def safe_float(val, defaut=500.0):
    try:
        f = float(str(val)); return defaut if np.isnan(f) else f
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
print(f"   ✅ Variables calculées sur {len(df_clean):,} matchs")

# ============================================================
# ENTRAÎNEMENT DES 3 IA SPÉCIALISÉES
# ============================================================
modeles_surf = {}
resultats_surf = {}

for surface, cfg in SURFACES_CONFIG.items():
    print(f"\n{'='*50}")
    print(f"🎾 IA {surface.upper()}")

    df_surf = df_clean[df_clean['surface'] == surface].copy()
    n = len(df_surf)
    print(f"   Matchs disponibles : {n:,}")

    if n < 5000:
        print(f"   ⚠️ Trop peu de données (<5000) — surface ignorée")
        continue

    # Dataset symétrique par surface
    df_s_A = df_surf.copy(); df_s_A['target'] = 1
    df_s_B = df_surf.copy(); df_s_B['target'] = 0
    cols_inv = ['elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff',
                'streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
                'dominance_diff','revanche_diff','hist_tournoi_diff',
                'rank_diff','age_diff','cote_diff']
    for col in cols_inv:
        if col in df_s_B.columns:
            df_s_B[col] = -df_surf[col].fillna(0).values
    df_s_B['cote_proba_A'] = df_surf['cote_proba_B'].values
    df_s_B['cote_proba_B'] = df_surf['cote_proba_A'].values

    import gc
    X_sA = df_s_A[FEATURES].fillna(0).astype('float32')
    y_sA = pd.Series([1]*len(X_sA), dtype=int)
    X_sB = df_s_B[FEATURES].fillna(0).astype('float32')
    y_sB = pd.Series([0]*len(X_sB), dtype=int)
    del df_s_A, df_s_B; gc.collect()

    X_s = pd.concat([X_sA, X_sB], ignore_index=True)
    y_s = pd.concat([y_sA, y_sB], ignore_index=True)
    del X_sA, X_sB, y_sA, y_sB; gc.collect()

    idx = np.random.default_rng(42).permutation(len(X_s))
    X_s = X_s.iloc[idx].reset_index(drop=True)
    y_s = y_s.iloc[idx].reset_index(drop=True)
    gc.collect()

    X_tr_s, X_te_s, y_tr_s, y_te_s = train_test_split(
        X_s, y_s, test_size=0.2, random_state=42, stratify=y_s
    )
    del X_s, y_s; gc.collect()

    # Entraînement
    modele_surf = XGBClassifier(
        n_estimators     = cfg['n_estimators'],
        max_depth        = cfg['max_depth'],
        min_child_weight = cfg['min_child_weight'],
        learning_rate    = 0.05,
        subsample        = 0.8,
        colsample_bytree = 0.8,
        eval_metric      = 'logloss',
        random_state     = 42,
        n_jobs           = -1
    )
    modele_surf.fit(X_tr_s, y_tr_s, verbose=False)
    acc_surf = accuracy_score(y_te_s, modele_surf.predict(X_te_s))

    gain = (acc_surf - acc_general) * 100
    emoji = "✅" if acc_surf > acc_general else "⚠️"
    print(f"   Précision IA {surface} : {acc_surf*100:.1f}% ({gain:+.1f}% vs général) {emoji}")

    # Validation — ignorer si trop faible
    if acc_surf < 0.60:
        print(f"   ❌ Précision < 60% — modèle non retenu pour cette surface")
        print(f"   ℹ️  L'IA Suprême utilisera l'IA Générale sur {surface}")
    else:
        modeles_surf[surface] = modele_surf
        resultats_surf[surface] = acc_surf
        print(f"   ✅ Modèle {surface} retenu")

# ============================================================
# SAUVEGARDE
# ============================================================
print(f"\n{'='*60}")
print("💾 Sauvegarde dans modeles_tennis_v2.pkl...")

modeles['modeles_surf']  = modeles_surf
modeles['acc_surf']      = resultats_surf
modeles['date_surf']     = datetime.now().strftime('%Y-%m-%d %H:%M')

with open(FICHIER_MODELE, 'wb') as f:
    pickle.dump(modeles, f)

print(f"   ✅ Sauvegardé — surfaces entraînées : {list(modeles_surf.keys())}")

# ============================================================
# UPLOAD SUR HUGGINGFACE
# ============================================================
print("\n🚀 Upload sur HuggingFace...")
try:
    from huggingface_hub import HfApi
    import os as _os
    token = _os.getenv("HF_TOKEN")
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=FICHIER_MODELE,
        path_in_repo='data/modeles_tennis_v2.pkl',
        repo_id=HF_REPO_SPACE, repo_type='space', token=token,
        commit_message=f'IA spécialisées {list(modeles_surf.keys())} — Étape 1/3'
    )
    print("   ✅ Modèle uploadé sur HuggingFace Space")
except Exception as e:
    print(f"   ❌ Erreur upload : {e}")
    print("   ℹ️  Modèle sauvegardé localement — upload manuel nécessaire")

# ============================================================
# RÉSUMÉ
# ============================================================
print(f"\n{'='*60}")
print("🎉 ÉTAPE 1 TERMINÉE — IA SPÉCIALISÉES")
print(f"{'='*60}")
print(f"  IA Générale     : {acc_general*100:.1f}%")
for surf, acc in resultats_surf.items():
    gain = (acc - acc_general) * 100
    print(f"  IA {surf:<8}    : {acc*100:.1f}% ({gain:+.1f}%)")
print(f"{'='*60}")
print(f"\n✅ Prochaine étape : lancer etape2_meta_dataset.py")
