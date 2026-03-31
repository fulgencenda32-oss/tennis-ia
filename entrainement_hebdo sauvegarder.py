# ============================================================
# RÉENTRAÎNEMENT HEBDOMADAIRE — Tennis IA
# Version COMPLÈTE avec toutes les variables psychologiques
# Lancez ce script une fois par semaine sur votre PC
# ============================================================
import pandas as pd
import numpy as np
import os, re, pickle, requests
from datetime import datetime, timedelta
from collections import defaultdict, Counter
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
FICHIER_MEMOIRE = os.path.join(DOSSIER, "data", "memoire_ia.json")
API_KEY        = os.getenv("ALLSPORTS_API_KEY")
BASE_URL       = "https://apiv2.allsportsapi.com/tennis/"
HF_REPO_SPACE  = "Fulgence10/Tennis-IA"
HF_REPO_DATA   = "Fulgence10/tennis-data"

print("=" * 60)
print("🎾 RÉENTRAÎNEMENT HEBDOMADAIRE TENNIS IA")
print("=" * 60)

# Calcul de la période (7 derniers jours)
date_fin   = datetime.now().strftime('%Y-%m-%d')
date_debut = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
print(f"\n📡 Récupération matchs du {date_debut} au {date_fin}...")

# ============================================================
# ÉTAPE 1 — RÉCUPÉRATION NOUVEAUX MATCHS VIA API
# ============================================================
def get_matchs_api(date_debut, date_fin):
    try:
        r = requests.get(BASE_URL, params={
            "met"    : "Fixtures",
            "APIkey" : API_KEY,
            "from"   : date_debut,
            "to"     : date_fin,
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") == 1:
                return data.get("result", [])
    except Exception as e:
        print(f"   ❌ Erreur API : {e}")
    return []

matchs_raw = get_matchs_api(date_debut, date_fin)
print(f"   ✅ {len(matchs_raw)} matchs récupérés")

# ============================================================
# ÉTAPE 2 — CONVERSION AU FORMAT BASE_FEATURES
# ============================================================
print("\n🔄 Conversion des matchs...")

nouveaux_matchs = []
for m in matchs_raw:
    statut = str(m.get('event_status', '')).lower()
    if statut not in ['finished', 'fin', 'ft', 'retired', 'walk over']:
        continue
    score_raw = str(m.get('event_final_result', '') or '')
    joueur_a  = str(m.get('event_first_player',  '') or '')
    joueur_b  = str(m.get('event_second_player', '') or '')
    if not joueur_a or not joueur_b or not score_raw:
        continue
    sets = re.findall(r'(\d+)\s*-\s*(\d+)', score_raw)
    if not sets:
        continue
    sets_a = sum(1 for a, b in sets if int(a) > int(b))
    sets_b = len(sets) - sets_a
    winner = joueur_a if sets_a > sets_b else joueur_b
    loser  = joueur_b if sets_a > sets_b else joueur_a
    circuit = str(m.get('country_name', 'ATP') or 'ATP')
    genre   = 'F' if 'WTA' in circuit.upper() else 'M'
    nouveaux_matchs.append({
        'tourney_date' : str(m.get('event_date', date_fin)),
        'tourney_name' : str(m.get('league_name', '') or ''),
        'surface'      : 'Hard',
        'circuit'      : circuit,
        'genre'        : genre,
        'round'        : str(m.get('league_round', 'R32') or 'R32'),
        'best_of'      : 3,
        'winner_name'  : winner,
        'loser_name'   : loser,
        'score'        : score_raw,
        'winner_rank'  : m.get('first_player_rank' if sets_a > sets_b else 'second_player_rank', None),
        'loser_rank'   : m.get('second_player_rank' if sets_a > sets_b else 'first_player_rank', None),
        'winner_age'   : None, 'loser_age' : None,
        'winner_ioc'   : None, 'loser_ioc' : None,
    })

print(f"   ✅ {len(nouveaux_matchs)} matchs terminés convertis")

# ============================================================
# ÉTAPE 3 — AJOUT À LA BASE
# ============================================================
print("\n📂 Chargement base existante...")
df = pd.read_csv(FICHIER_BASE, low_memory=False)
nb_avant = len(df)
print(f"   ✅ {nb_avant:,} matchs existants")

nb_nouveaux = 0
if nouveaux_matchs:
    df_new = pd.DataFrame(nouveaux_matchs)
    df_new['tourney_date'] = pd.to_datetime(df_new['tourney_date'], errors='coerce')
    df['tourney_date']     = pd.to_datetime(df['tourney_date'], errors='coerce')
    cles_existantes = set(zip(
        df['winner_name'].astype(str),
        df['loser_name'].astype(str),
        df['tourney_date'].astype(str)
    ))
    df_new = df_new[~df_new.apply(
        lambda r: (str(r['winner_name']), str(r['loser_name']),
                   str(r['tourney_date'])[:10]) in cles_existantes, axis=1
    )]
    nb_nouveaux = len(df_new)
    if nb_nouveaux > 0:
        df = pd.concat([df, df_new], ignore_index=True)
        df = df.sort_values('tourney_date').reset_index(drop=True)
        df.to_csv(FICHIER_BASE, index=False)
        print(f"   ✅ {nb_nouveaux} nouveaux matchs ajoutés → {len(df):,} total")
    else:
        print("   ℹ️ Aucun nouveau match (déjà présents)")
else:
    print("   ℹ️ Aucun nouveau match récupéré")

# ============================================================
# ÉTAPE 4 — RÉENTRAÎNEMENT COMPLET
# ============================================================
print("\n🔄 Préparation des données...")

df['tourney_date'] = pd.to_datetime(df['tourney_date'], errors='coerce')
df = df.sort_values('tourney_date').reset_index(drop=True)

# Parsing scores
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
print("⚡ Calcul ELO...")
elo_g2 = defaultdict(lambda: 1500.0)
elo_s2 = defaultdict(lambda: defaultdict(lambda: 1500.0))
elo_wg, elo_lg, elo_ws, elo_ls = [], [], [], []

for _, row in df.iterrows():
    w = str(row['winner_name']); l = str(row['loser_name']); surf = str(row['surface'])
    elo_wg.append(elo_g2[w]); elo_lg.append(elo_g2[l])
    elo_ws.append(elo_s2[surf][w]); elo_ls.append(elo_s2[surf][l])
    ea = 1 / (1 + 10**((elo_g2[l] - elo_g2[w]) / 400))
    elo_g2[w] += 32*(1-ea); elo_g2[l] += 32*(0-(1-ea))
    ea_s = 1 / (1 + 10**((elo_s2[surf][l] - elo_s2[surf][w]) / 400))
    elo_s2[surf][w] += 32*(1-ea_s); elo_s2[surf][l] += 32*(0-(1-ea_s))

df['elo_winner']      = np.array(elo_wg, dtype='float32')
df['elo_loser']       = np.array(elo_lg, dtype='float32')
df['elo_winner_surf'] = np.array(elo_ws, dtype='float32')
df['elo_loser_surf']  = np.array(elo_ls, dtype='float32')
df['elo_diff']        = (df['elo_winner'] - df['elo_loser']).astype('float32')
df['elo_diff_surf']   = (df['elo_winner_surf'] - df['elo_loser_surf']).astype('float32')
print("   ✅ ELO recalculé")

# Forme
print("📈 Calcul forme...")
hist2 = defaultdict(list)
fw_l, fl_l = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    hw = hist2[w][-10:]; hl = hist2[l][-10:]
    fw_l.append(sum(hw)/len(hw) if hw else 0.5)
    fl_l.append(sum(hl)/len(hl) if hl else 0.5)
    hist2[w].append(1); hist2[l].append(0)

df['forme_winner'] = np.array(fw_l, dtype='float32')
df['forme_loser']  = np.array(fl_l, dtype='float32')
df['forme_diff']   = (df['forme_winner'] - df['forme_loser']).astype('float32')
print("   ✅ Forme recalculée")

# H2H
print("🤝 Calcul H2H...")
h2h2 = defaultdict(lambda: [0, 0])
hw_l2, hl_l2 = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    key = tuple(sorted([w, l])); tot = h2h2[key][1]
    if tot > 0:
        wins_w = h2h2[key][0] if key[0]==w else tot - h2h2[key][0]
        hw_l2.append(wins_w/tot); hl_l2.append(1-wins_w/tot)
    else:
        hw_l2.append(0.5); hl_l2.append(0.5)
    h2h2[key][1] += 1
    if key[0] == w: h2h2[key][0] += 1

df['h2h_winner'] = np.array(hw_l2, dtype='float32')
df['h2h_loser']  = np.array(hl_l2, dtype='float32')
df['h2h_diff']   = (df['h2h_winner'] - df['h2h_loser']).astype('float32')
print("   ✅ H2H recalculé")

# Fatigue
print("😴 Calcul fatigue...")
mj2 = defaultdict(list)
fw3, fl3 = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name']); d = row['tourney_date']
    if pd.notna(d):
        fw3.append(sum(1 for dd in mj2[w] if (d-dd).days <= 7))
        fl3.append(sum(1 for dd in mj2[l] if (d-dd).days <= 7))
        mj2[w] = (mj2[w]+[d])[-30:]; mj2[l] = (mj2[l]+[d])[-30:]
    else:
        fw3.append(0); fl3.append(0)

df['fatigue_winner'] = np.array(fw3, dtype='float32')
df['fatigue_loser']  = np.array(fl3, dtype='float32')
df['fatigue_diff']   = (df['fatigue_winner'] - df['fatigue_loser']).astype('float32')
print("   ✅ Fatigue recalculée")

# Hot Streak
print("🔥 Calcul hot streak...")
streak_joueur = defaultdict(int)
streak_w_list, streak_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    streak_w_list.append(streak_joueur[w])
    streak_l_list.append(streak_joueur[l])
    streak_joueur[w] += 1
    streak_joueur[l]  = 0
df['streak_winner'] = np.array(streak_w_list, dtype='float32')
df['streak_loser']  = np.array(streak_l_list, dtype='float32')
df['streak_diff']   = (df['streak_winner'] - df['streak_loser']).astype('float32')
streak_final = dict(streak_joueur)

# Comeback ratio
print("💪 Calcul comeback ratio...")
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
        premier_set_w = sets[0][0] > sets[0][1]
        if not premier_set_w:
            comeback_w[w][1] += 1
            comeback_w[w][0] += 1
        if sets[0][0] > sets[0][1]:
            comeback_l[l][1] += 1
comeback_final = {}
for j in set(list(comeback_w.keys()) + list(comeback_l.keys())):
    wins = comeback_w[j][0]
    opp  = comeback_w[j][1] + comeback_l[j][1]
    comeback_final[j] = round(wins / opp, 3) if opp > 0 else 0.3

comeback_w_list, comeback_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    comeback_w_list.append(comeback_final.get(w, 0.3))
    comeback_l_list.append(comeback_final.get(l, 0.3))
df['comeback_winner'] = np.array(comeback_w_list, dtype='float32')
df['comeback_loser']  = np.array(comeback_l_list, dtype='float32')
df['comeback_diff']   = (df['comeback_winner'] - df['comeback_loser']).astype('float32')

# Clutch score
print("🎯 Calcul clutch score...")
clutch_w = defaultdict(lambda: [0, 0])
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    nb = row.get('nb_sets', 2)
    try: nb = int(nb)
    except: nb = 2
    if nb >= 3:
        clutch_w[w][0] += 1; clutch_w[w][1] += 1
        clutch_w[l][1] += 1
clutch_final = {j: round(v[0]/v[1], 3) if v[1] > 0 else 0.5 for j, v in clutch_w.items()}

clutch_w_list, clutch_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    clutch_w_list.append(clutch_final.get(w, 0.5))
    clutch_l_list.append(clutch_final.get(l, 0.5))
df['clutch_winner'] = np.array(clutch_w_list, dtype='float32')
df['clutch_loser']  = np.array(clutch_l_list, dtype='float32')
df['clutch_diff']   = (df['clutch_winner'] - df['clutch_loser']).astype('float32')

# Big match player
print("🏆 Calcul big match...")
bigmatch_w = defaultdict(lambda: [0, 0])
bigmatch_l = defaultdict(lambda: [0, 0])
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    rnd = str(row.get('round', '')).upper()
    if 'FINAL' in rnd or rnd == 'F':
        bigmatch_w[w][0] += 1; bigmatch_w[w][1] += 1
        bigmatch_l[l][1] += 1
bigmatch_final = {}
for j in set(list(bigmatch_w.keys()) + list(bigmatch_l.keys())):
    total = bigmatch_w[j][1] + bigmatch_l[j][1]
    wins  = bigmatch_w[j][0]
    bigmatch_final[j] = round(wins / total, 3) if total > 0 else 0.5

bigmatch_w_list, bigmatch_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    bigmatch_w_list.append(bigmatch_final.get(w, 0.5))
    bigmatch_l_list.append(bigmatch_final.get(l, 0.5))
df['bigmatch_winner'] = np.array(bigmatch_w_list, dtype='float32')
df['bigmatch_loser']  = np.array(bigmatch_l_list, dtype='float32')
df['bigmatch_diff']   = (df['bigmatch_winner'] - df['bigmatch_loser']).astype('float32')

# Dominance score
print("💥 Calcul dominance...")
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

# Revanche factor
print("🔄 Calcul revanche factor...")
last_result = {}
revanche_w_list, revanche_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    revanche_w_list.append(1 - last_result.get((w, l), 0.5))
    revanche_l_list.append(1 - last_result.get((l, w), 0.5))
    last_result[(w, l)] = 1
    last_result[(l, w)] = 0
df['revanche_winner'] = np.array(revanche_w_list, dtype='float32')
df['revanche_loser']  = np.array(revanche_l_list, dtype='float32')
df['revanche_diff']   = (df['revanche_winner'] - df['revanche_loser']).astype('float32')

# Historique tournoi
print("📅 Calcul historique tournoi...")
tournoi_hist = defaultdict(lambda: defaultdict(lambda: [0, 0]))
hist_w_list, hist_l_list = [], []
for _, row in df.iterrows():
    w, l = str(row['winner_name']), str(row['loser_name'])
    t = str(row.get('tourney_name', '')).lower()[:30]
    hist_w_list.append(tournoi_hist[w][t][0] / tournoi_hist[w][t][1] if tournoi_hist[w][t][1] > 0 else 0.5)
    hist_l_list.append(tournoi_hist[l][t][0] / tournoi_hist[l][t][1] if tournoi_hist[l][t][1] > 0 else 0.5)
    tournoi_hist[w][t][0] += 1; tournoi_hist[w][t][1] += 1
    tournoi_hist[l][t][1] += 1
tournoi_hist_final = {j: {t: round(v[0]/v[1], 3) for t, v in td.items() if v[1] > 0} for j, td in tournoi_hist.items()}
df['hist_tournoi_winner'] = np.array(hist_w_list, dtype='float32')
df['hist_tournoi_loser']  = np.array(hist_l_list, dtype='float32')
df['hist_tournoi_diff']   = (df['hist_tournoi_winner'] - df['hist_tournoi_loser']).astype('float32')

# IOC nationalité
if 'winner_ioc' in df.columns:
    ioc_final = df[df['winner_ioc'].notna()].groupby('winner_name')['winner_ioc'].last().to_dict()
else:
    ioc_final = {}

print(f"   ✅ Toutes les variables calculées !")

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

df['rank_diff']    = (df['loser_rank'].apply(safe_float) - df['winner_rank'].apply(safe_float)).astype('float32')
df['age_diff']     = (df['winner_age'].apply(lambda x: safe_float(x,0)) - df['loser_age'].apply(lambda x: safe_float(x,0))).astype('float32')
df['round_num']    = df['round'].astype(str).apply(simplifier_round)
df['surface_enc']  = df['surface'].map(surface_map).fillna(4).astype(int)
df['circuit_enc']  = df['circuit'].map(circuit_map).fillna(0).astype(int) if 'circuit' in df.columns else 0
df['genre_enc']    = (df['genre'].astype(str) == 'F').astype(int) if 'genre' in df.columns else 0
df['cote_diff']    = 0.0; df['cote_proba_A'] = 0.5; df['cote_proba_B'] = 0.5
if 'best_of' not in df.columns: df['best_of'] = 3
df['best_of'] = pd.to_numeric(df['best_of'], errors='coerce').fillna(3).astype(int)

# FEATURES COMPLÈTES (22 variables)
FEATURES = [
    'elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff',
    'streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
    'dominance_diff','revanche_diff','hist_tournoi_diff',
    'rank_diff','age_diff','surface_enc','circuit_enc','genre_enc',
    'best_of','round_num','cote_diff','cote_proba_A','cote_proba_B'
]

# Dataset symétrique avec gestion mémoire
print("\n🔀 Dataset symétrique...")
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

import gc
X_A = df_A[FEATURES].fillna(0).astype('float32')
y_A = pd.Series([1]*len(X_A), dtype=int)
X_B = df_B[FEATURES].fillna(0).astype('float32')
y_B = pd.Series([0]*len(X_B), dtype=int)
del df_A, df_B
gc.collect()

X_sym = pd.concat([X_A, X_B], ignore_index=True)
y_sym = pd.concat([y_A, y_B], ignore_index=True)
del X_A, X_B, y_A, y_B
gc.collect()

idx = np.random.default_rng(42).permutation(len(X_sym))
X_sym = X_sym.iloc[idx].reset_index(drop=True)
y_sym = y_sym.iloc[idx].reset_index(drop=True)
gc.collect()

X_tr, X_te, y_tr, y_te = train_test_split(X_sym, y_sym, test_size=0.2, random_state=42, stratify=y_sym)
del X_sym, y_sym
gc.collect()

# ============================================================
# ÉTAPE 5 — PONDÉRATION DEPUIS MÉMOIRE IA (si disponible)
# ============================================================
import json as _json
sample_weights_train = np.ones(len(X_tr), dtype='float32')
sample_weights_info  = "uniforme"

try:
    if os.path.exists(FICHIER_MEMOIRE):
        with open(FICHIER_MEMOIRE, 'r', encoding='utf-8') as f:
            memoire_ia = _json.load(f)
        patterns = memoire_ia.get("patterns_recurrents", {})
        poids_surface = {}
        for surf, p in patterns.items():
            if p.get("alerte"):
                poids_surface[surf] = 2.0
                print(f"   ⚠️ Surface {surf} : poids x2")
            elif p.get("amelioration"):
                poids_surface[surf] = 0.8
        if poids_surface:
            surface_map_inv = {v: k for k, v in surface_map.items()}
            for idx_row in range(len(X_tr)):
                surf_enc = int(X_tr.iloc[idx_row]['surface_enc'])
                surf_nom = surface_map_inv.get(surf_enc, 'Hard')
                sample_weights_train[idx_row] *= poids_surface.get(surf_nom, 1.0)
            sample_weights_info = f"pondéré ({len(poids_surface)} surfaces)"
except Exception as e:
    print(f"   ⚠️ Mémoire IA ignorée : {e}")

print(f"   Mode pondération : {sample_weights_info}")

# ============================================================
# ÉTAPE 6 — ENTRAÎNEMENT AVEC VALIDATION
# ============================================================
acc_ancien = 0
if os.path.exists(FICHIER_MODELE):
    try:
        import __main__
        __main__.simplifier_round = simplifier_round
        with open(FICHIER_MODELE, 'rb') as f:
            modeles_ancien = pickle.load(f)
        acc_ancien = modeles_ancien.get('acc_win', 0)
        print(f"\n📌 Modèle actuel : {acc_ancien*100:.1f}%")
    except:
        pass

# Modèle Vainqueur avec validation
print("\n🤖 Entraînement Modèle 1 — Vainqueur...")
candidat_win = XGBClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    eval_metric='logloss', random_state=42, n_jobs=-1
)
candidat_win.fit(X_tr, y_tr, sample_weight=sample_weights_train, verbose=False)
acc_win_candidat = accuracy_score(y_te, candidat_win.predict(X_te))

SEUIL = 0.001
if acc_ancien <= 0 or acc_win_candidat >= acc_ancien - SEUIL:
    modele_win = candidat_win
    acc_win    = acc_win_candidat
    gain = (acc_win_candidat - acc_ancien) * 100
    print(f"   ✅ Précision : {acc_win*100:.1f}% ({gain:+.2f}% vs ancien) → DÉPLOYÉ")
else:
    modele_win = modeles_ancien['modele_win']
    acc_win    = acc_ancien
    print(f"   ⚠️ Candidat moins bon → ANCIEN CONSERVÉ ({acc_win*100:.1f}%)")

# Modèle Sets
print("\n🤖 Entraînement Modèle 2 — Nb Sets...")
df_sets = df_clean[df_clean['nb_sets'].notna()].copy()
df_sets['cote_diff'] = 0.0; df_sets['cote_proba_A'] = 0.5; df_sets['cote_proba_B'] = 0.5
for col in ['streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
            'dominance_diff','revanche_diff','hist_tournoi_diff']:
    if col not in df_sets.columns: df_sets[col] = 0.0
X_s = df_sets[FEATURES].fillna(0).astype('float32')
y_s = df_sets['nb_sets'].astype(int).clip(2,5) - 2
X_tr_s, X_te_s, y_tr_s, y_te_s = train_test_split(X_s, y_s, test_size=0.2, random_state=42)
modele_sets = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                             eval_metric='mlogloss', random_state=42, n_jobs=-1)
modele_sets.fit(X_tr_s, y_tr_s, verbose=False)
acc_sets = accuracy_score(y_te_s+2, modele_sets.predict(X_te_s)+2)
print(f"   ✅ Précision : {acc_sets*100:.1f}%")

# Modèle Handicap
print("\n🤖 Entraînement Modèle 3 — Handicap...")
df_h = df_clean[df_clean['handicap_sets'].notna()].copy()
df_h['cote_diff'] = 0.0; df_h['cote_proba_A'] = 0.5; df_h['cote_proba_B'] = 0.5
for col in ['streak_diff','comeback_diff','clutch_diff','bigmatch_diff',
            'dominance_diff','revanche_diff','hist_tournoi_diff']:
    if col not in df_h.columns: df_h[col] = 0.0
X_h = df_h[FEATURES].fillna(0).astype('float32')
y_h = df_h['handicap_sets'].astype(int).clip(1,3) - 1
X_tr_h, X_te_h, y_tr_h, y_te_h = train_test_split(X_h, y_h, test_size=0.2, random_state=42)
modele_handi = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                              eval_metric='mlogloss', random_state=42, n_jobs=-1)
modele_handi.fit(X_tr_h, y_tr_h, verbose=False)
acc_handi = accuracy_score(y_te_h+1, modele_handi.predict(X_te_h)+1)
print(f"   ✅ Précision : {acc_handi*100:.1f}%")

# Dictionnaire scores
print("\n📚 Dictionnaire scores...")
def parser_score_str(score_str):
    if not isinstance(score_str, str): return ''
    score_str = re.sub(r'RET|W/O|DEF|ABN|Ret\.|\(.*?\)', '', score_str, flags=re.IGNORECASE).strip()
    sets = re.findall(r'(\d+)-(\d+)', score_str)
    return ' '.join([f"{a}-{b}" for a,b in sets]) if sets else ''

df_clean['score_propre'] = df_clean['score'].apply(parser_score_str)
dico_scores = {}
for (nb, handi), grp in df_clean.groupby(['nb_sets','handicap_sets']):
    if pd.isna(nb) or pd.isna(handi): continue
    scores = grp['score_propre'].dropna(); scores = scores[scores != '']
    if len(scores) > 0:
        dico_scores[(int(nb), int(handi))] = [s for s,_ in Counter(scores).most_common(3)]

dico_scores_surf = {}
for (nb, handi, surf), grp in df_clean.groupby(['nb_sets','handicap_sets','surface']):
    if pd.isna(nb) or pd.isna(handi): continue
    scores = grp['score_propre'].dropna(); scores = scores[scores != '']
    if len(scores) > 0:
        top = Counter(scores).most_common(1)
        dico_scores_surf[(int(nb), int(handi), str(surf))] = top[0][0]

# ELO finaux
elo_final      = df_clean.groupby('winner_name')['elo_winner'].last().to_dict()
elo_final_surf = {}
for surf in ['Hard','Clay','Grass','Carpet']:
    mask = df_clean['surface'] == surf
    elo_final_surf[surf] = df_clean[mask].groupby('winner_name')['elo_winner_surf'].last().to_dict()
forme_final = df_clean.groupby('winner_name')['forme_winner'].last().to_dict()
print(f"   ✅ {len(ioc_final):,} nationalités chargées")

# ============================================================
# ÉTAPE 7 — SAUVEGARDE
# ============================================================
print("\n💾 Sauvegarde...")
modeles_complets = {
    'modele_win'   : modele_win,
    'modele_sets'  : modele_sets,
    'modele_handi' : modele_handi,
    'features'     : FEATURES,
    'simplifier_round' : simplifier_round,
    'dico_scores'      : dico_scores,
    'dico_scores_surf' : dico_scores_surf,
    'elo_final'        : elo_final,
    'elo_final_surf'   : elo_final_surf,
    'forme_final'      : forme_final,
    'streak_final'     : streak_final,
    'ioc_final'        : ioc_final,
    'comeback_final'   : comeback_final,
    'clutch_final'     : clutch_final,
    'bigmatch_final'   : bigmatch_final,
    'dominance_final'  : dominance_final,
    'tournoi_hist_final': tournoi_hist_final,
    'surface_map'      : surface_map,
    'circuit_map'      : circuit_map,
    'acc_win'          : acc_win,
    'acc_sets'         : acc_sets,
    'acc_handi'        : acc_handi,
    'mode_entrainement': sample_weights_info,
    'date_entrainement': datetime.now().strftime('%Y-%m-%d %H:%M'),
}

with open(FICHIER_MODELE, 'wb') as f:
    pickle.dump(modeles_complets, f)
print(f"   ✅ modeles_tennis_v2.pkl sauvegardé")

# ============================================================
# ÉTAPE 8 — UPLOAD SUR HUGGINGFACE
# ============================================================
print("\n🚀 Upload sur HuggingFace...")
try:
    from huggingface_hub import HfApi
    HF_TOKEN = os.getenv("HF_TOKEN")
    api = HfApi(token=HF_TOKEN)
    api.upload_file(
        path_or_fileobj=FICHIER_MODELE,
        path_in_repo='data/modeles_tennis_v2.pkl',
        repo_id=HF_REPO_SPACE, repo_type='space', token=HF_TOKEN,
        commit_message=f'Reentrainement {datetime.now().strftime("%Y-%m-%d")} Win:{acc_win*100:.1f}% {sample_weights_info}'
    )
    print("   ✅ Modèle uploadé sur HuggingFace Space")
    api.upload_file(
        path_or_fileobj=FICHIER_BASE,
        path_in_repo='BASE_FEATURES.csv',
        repo_id=HF_REPO_DATA, repo_type='dataset', token=HF_TOKEN,
        commit_message=f'Mise a jour donnees {datetime.now().strftime("%Y-%m-%d")}'
    )
    print("   ✅ CSV mis à jour sur HuggingFace Dataset")
except Exception as e:
    print(f"   ❌ Erreur upload : {e}")

# ============================================================
# RÉSUMÉ FINAL
# ============================================================
print(f"\n{'='*60}")
print(f"🎉 RÉENTRAÎNEMENT TERMINÉ")
print(f"{'='*60}")
print(f"  Matchs utilisés    : {len(df_clean):,}")
print(f"  Nouveaux ajoutés   : {nb_nouveaux}")
print(f"  Vainqueur          : {acc_win*100:.1f}%")
print(f"  Nb Sets            : {acc_sets*100:.1f}%")
print(f"  Handicap           : {acc_handi*100:.1f}%")
print(f"  Joueurs avec ELO   : {len(elo_final):,}")
print(f"  Variables          : {len(FEATURES)} features")
print(f"  Mode               : {sample_weights_info}")
print(f"  Date               : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")
print(f"\n✅ L'app HuggingFace utilisera le nouveau modèle dans 2-3 minutes !")
