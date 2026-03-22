# ============================================================
# RÉENTRAÎNEMENT HEBDOMADAIRE — Tennis IA
# Lancez ce script une fois par semaine sur votre PC
# ============================================================
import pandas as pd
import numpy as np
import os, re, pickle, requests
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier, XGBRegressor
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

def simplifier_round(r):
    r = str(r).lower().strip()
    if any(x in r for x in ['final', 'f']): return 5
    if any(x in r for x in ['semi', 'sf']): return 4
    if any(x in r for x in ['quarter', 'qf']): return 3
    if any(x in r for x in ['r16', '16']): return 2
    if any(x in r for x in ['r32', '32']): return 1
    if any(x in r for x in ['r64', '64']): return 0
    if any(x in r for x in ['r128', '128']): return -1
    return 1


# ============================================================
# CONFIGURATION
# ============================================================
DOSSIER        = r"C:\Users\HP\OneDrive\Documents\Tennis_IA"
FICHIER_BASE   = os.path.join(DOSSIER, "data", "BASE_FEATURES.csv")
FICHIER_MODELE = os.path.join(DOSSIER, "data", "modeles_tennis_v2.pkl")
API_KEY        = os.getenv("ALLSPORTS_API_KEY")
BASE_URL       = "https://apiv2.allsportsapi.com/tennis/"
HF_REPO_SPACE  = "Fulgence10/Tennis-IA"
HF_REPO_DATA   = "Fulgence10/tennis-data"

print("=" * 60)
print("🎾 RÉENTRAÎNEMENT HEBDOMADAIRE TENNIS IA")
print("=" * 60)

# ============================================================
# ÉTAPE 1 — SAISIE DE LA DATE
# ============================================================
print("\n📅 Quelle date de début pour récupérer les nouveaux matchs ?")
print("   (Appuyez sur Entrée pour prendre les 7 derniers jours)")
date_input = input("   Date (format YYYY-MM-DD) : ").strip()

if not date_input:
    date_debut = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
else:
    date_debut = date_input

date_fin = datetime.now().strftime('%Y-%m-%d')
print(f"   ✅ Période : {date_debut} → {date_fin}")

# ============================================================
# ÉTAPE 2 — RÉCUPÉRATION NOUVEAUX MATCHS VIA API
# ============================================================
print(f"\n📡 Récupération des matchs via API...")

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
# ÉTAPE 3 — CONVERSION AU FORMAT BASE_FEATURES
# ============================================================
print("\n🔄 Conversion des matchs terminés...")

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
        'winner_age'   : None,
        'loser_age'    : None,
        'winner_ioc'   : None,
        'loser_ioc'    : None,
    })

print(f"   ✅ {len(nouveaux_matchs)} matchs terminés convertis")

# ============================================================
# ÉTAPE 4 — AJOUT À LA BASE
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
# ÉTAPE 5 — CHARGEMENT MODÈLE EXISTANT
# ============================================================
print("\n📦 Chargement modèle existant...")
if not os.path.exists(FICHIER_MODELE):
    print("   Telechargement modele depuis HuggingFace...")
    try:
        from huggingface_hub import hf_hub_download
        import shutil
        chemin = hf_hub_download(
            repo_id="fulgence10/tennis-ia",
            filename="data/modeles_tennis_v2.pkl",
            repo_type="space",
            local_dir=os.path.join(os.path.dirname(FICHIER_MODELE), "tmp_hf")
        )
        shutil.copy(chemin, FICHIER_MODELE)
        print("   OK modele telecharge")
    except Exception as e:
        print(f"   ERREUR telechargement : {e}")
        print("   Copiez manuellement modeles_tennis_v2.pkl dans data/")
        exit(1)
with open(FICHIER_MODELE, 'rb') as f:
    modeles = pickle.load(f)

elo_g       = defaultdict(lambda: 1500.0, modeles['elo_final'])
elo_s       = defaultdict(lambda: defaultdict(lambda: 1500.0))
for surf, d in modeles['elo_final_surf'].items():
    for joueur, val in d.items():
        elo_s[surf][joueur] = val
forme_hist  = defaultdict(list)
for joueur, val in modeles['forme_final'].items():
    forme_hist[joueur] = [1 if val > 0.5 else 0]

print(f"   ✅ Modèle chargé — {len(elo_g):,} joueurs")

# ============================================================
# ÉTAPE 6 — MISE À JOUR INCRÉMENTALE ELO + FORME
# ============================================================
if nb_nouveaux > 0:
    print(f"\n⚡ Mise à jour incrémentale ELO + forme ({nb_nouveaux} matchs)...")

    for _, row in df_new.iterrows():
        w    = str(row['winner_name'])
        l    = str(row['loser_name'])
        surf = str(row.get('surface', 'Hard'))

        # Mise à jour ELO général
        ea = 1 / (1 + 10**((elo_g[l] - elo_g[w]) / 400))
        elo_g[w] += 32 * (1 - ea)
        elo_g[l] += 32 * (0 - (1 - ea))

        # Mise à jour ELO surface
        ea_s = 1 / (1 + 10**((elo_s[surf][l] - elo_s[surf][w]) / 400))
        elo_s[surf][w] += 32 * (1 - ea_s)
        elo_s[surf][l] += 32 * (0 - (1 - ea_s))

        # Mise à jour forme
        forme_hist[w] = (forme_hist[w] + [1])[-10:]
        forme_hist[l] = (forme_hist[l] + [0])[-10:]

    # Mise à jour des dictionnaires finaux
    modeles['elo_final'] = dict(elo_g)
    for surf in ['Hard', 'Clay', 'Grass', 'Carpet']:
        modeles['elo_final_surf'][surf].update(dict(elo_s[surf]))
    modeles['forme_final'] = {
        j: sum(v)/len(v) for j, v in forme_hist.items() if v
    }
    print("   ✅ ELO et forme mis à jour !")

# ============================================================
# ÉTAPE 7 — AFFINAGE RAPIDE DES MODÈLES (nouveaux matchs)
# ============================================================
if nb_nouveaux > 0:
    print(f"\n🤖 Affinage rapide des modèles ({nb_nouveaux} nouveaux matchs)...")

    def simplifier_round(r):
        r = str(r).upper()
        if 'QUARTER' in r or 'QF' in r: return 4
        if 'SEMI'    in r or 'SF' in r: return 5
        if r in ['F','FINAL','THE FINAL']: return 6
        if 'R128' in r: return 1
        if 'R64'  in r: return 2
        return 3

    surface_map = modeles['surface_map']
    circuit_map = modeles['circuit_map']
    FEATURES    = modeles['features']

    def preparer_features(df_matchs):
        rows = []
        for _, row in df_matchs.iterrows():
            w    = str(row['winner_name'])
            l    = str(row['loser_name'])
            surf = str(row.get('surface', 'Hard'))
            rows.append({
                'elo_diff'      : elo_g[w] - elo_g[l],
                'elo_diff_surf' : elo_s[surf][w] - elo_s[surf][l],
                'forme_diff'    : modeles['forme_final'].get(w, 0.5) - modeles['forme_final'].get(l, 0.5),
                'h2h_diff'      : 0.0,
                'fatigue_diff'  : 0.0,
                'rank_diff'     : float(str(row.get('loser_rank', 500) or 500)) - float(str(row.get('winner_rank', 500) or 500)),
                'age_diff'      : 0.0,
                'surface_enc'   : surface_map.get(surf, 4),
                'circuit_enc'   : circuit_map.get(str(row.get('circuit', 'ATP')), 0),
                'genre_enc'     : 1 if str(row.get('genre', 'M')) == 'F' else 0,
                'best_of'       : int(row.get('best_of', 3) or 3),
                'round_num'     : simplifier_round(row.get('round', 'R32')),
                'cote_diff'     : 0.0,
                'cote_proba_A'  : 0.5,
                'cote_proba_B'  : 0.5,
            })
        return pd.DataFrame(rows)[FEATURES].fillna(0).astype('float32')

    # Dataset symétrique nouveaux matchs
    X_new  = preparer_features(df_new)
    X_newB = X_new.copy()
    for col in ['elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff','rank_diff','age_diff','cote_diff']:
        X_newB[col] = -X_new[col]

    X_affinage = pd.concat([X_new, X_newB], ignore_index=True)
    y_affinage = np.array([1]*len(X_new) + [0]*len(X_newB))

    # Affinage modèle vainqueur
    modeles['modele_win'].fit(
        X_affinage, y_affinage,
        xgb_model=modeles['modele_win'].get_booster(),
        verbose=False
    )
    print("   ✅ Modèle vainqueur affiné")

# ============================================================
# ÉTAPE 8 — RÉENTRAÎNEMENT COMPLET (hebdomadaire)
# ============================================================
print("\n🔄 Réentraînement complet sur toute la base...")
print("   ⏳ Cela prend 30-60 minutes, veuillez patienter...")

df['tourney_date'] = pd.to_datetime(df['tourney_date'], errors='coerce')
df = df.sort_values('tourney_date').reset_index(drop=True)

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
df['over_sets']     = (df['nb_sets'] > 2).astype('Int8')

# Recalcul ELO complet
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

df['elo_winner'] = np.array(elo_wg, dtype='float32')
df['elo_loser']  = np.array(elo_lg, dtype='float32')
df['elo_winner_surf'] = np.array(elo_ws, dtype='float32')
df['elo_loser_surf']  = np.array(elo_ls, dtype='float32')
df['elo_diff']        = (df['elo_winner'] - df['elo_loser']).astype('float32')
df['elo_diff_surf']   = (df['elo_winner_surf'] - df['elo_loser_surf']).astype('float32')
print("   ✅ ELO recalculé")

# Forme
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

def safe_float(val, defaut=500.0):
    try:
        f = float(str(val)); return defaut if np.isnan(f) else f
    except: return defaut

def simplifier_round(r):
    r = str(r).upper()
    if 'QUARTER' in r or 'QF' in r: return 4
    if 'SEMI' in r or 'SF' in r: return 5
    if r in ['F','FINAL','THE FINAL']: return 6
    if 'R128' in r: return 1
    if 'R64' in r: return 2
    return 3

surface_map = {'Carpet':0,'Clay':1,'Clay (Indoor)':2,'Grass':3,'Hard':4,'Hard (Indoor)':5,'Unknown':6}
circuit_map = {'ATP':0,'Challenger':1,'Futures':2,'ITF':3,'Juniors':4,'Teams Men':5,'Teams Women':6,'WTA':7}

df['rank_diff']    = (df['loser_rank'].apply(safe_float) - df['winner_rank'].apply(safe_float)).astype('float32')
df['age_diff']     = (df['winner_age'].apply(lambda x: safe_float(x,0)) - df['loser_age'].apply(lambda x: safe_float(x,0))).astype('float32')
df['round_num']    = df['round'].astype(str).apply(simplifier_round)
df['surface_enc']  = df['surface'].map(surface_map).fillna(4).astype(int)
df['circuit_enc']  = df['circuit'].map(circuit_map).fillna(0).astype(int)
df['genre_enc']    = (df['genre'].astype(str) == 'F').astype(int)
df['cote_diff']    = 0.0; df['cote_proba_A'] = 0.5; df['cote_proba_B'] = 0.5
if 'best_of' not in df.columns: df['best_of'] = 3
df['best_of'] = pd.to_numeric(df['best_of'], errors='coerce').fillna(3).astype(int)

FEATURES = ['elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff','rank_diff','age_diff','surface_enc','circuit_enc','genre_enc','best_of','round_num','cote_diff','cote_proba_A','cote_proba_B']

df_clean = df.dropna(subset=['elo_diff','forme_diff']).copy()
df_A = df_clean.copy(); df_A['target'] = 1
df_B = df_clean.copy(); df_B['target'] = 0
for col in ['elo_diff','elo_diff_surf','forme_diff','h2h_diff','fatigue_diff','rank_diff','age_diff','cote_diff']:
    df_B[col] = -df_clean[col].fillna(0).values
df_B['cote_proba_A'] = df_clean['cote_proba_B'].values
df_B['cote_proba_B'] = df_clean['cote_proba_A'].values

df_sym = pd.concat([df_A, df_B], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
X_sym  = df_sym[FEATURES].fillna(0).astype('float32')
y_sym  = df_sym['target'].astype(int)
X_tr, X_te, y_tr, y_te = train_test_split(X_sym, y_sym, test_size=0.2, random_state=42, stratify=y_sym)

print("\n🤖 Réentraînement Modèle 1 — Vainqueur...")
modele_win = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, eval_metric='logloss', random_state=42, n_jobs=-1)
modele_win.fit(X_tr, y_tr, verbose=False)
acc_win = accuracy_score(y_te, modele_win.predict(X_te))
print(f"   ✅ Précision : {acc_win*100:.1f}%")

print("\n🤖 Réentraînement Modèle 2 — Nb Sets...")
df_sets = df_clean[df_clean['nb_sets'].notna()].copy()
df_sets['cote_diff'] = 0.0; df_sets['cote_proba_A'] = 0.5; df_sets['cote_proba_B'] = 0.5
X_s = df_sets[FEATURES].fillna(0).astype('float32')
y_s = df_sets['nb_sets'].astype(int).clip(2,5) - 2
X_tr_s, X_te_s, y_tr_s, y_te_s = train_test_split(X_s, y_s, test_size=0.2, random_state=42)
modele_sets = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, eval_metric='mlogloss', random_state=42, n_jobs=-1)
modele_sets.fit(X_tr_s, y_tr_s, verbose=False)
acc_sets = accuracy_score(y_te_s+2, modele_sets.predict(X_te_s)+2)
print(f"   ✅ Précision : {acc_sets*100:.1f}%")

print("\n🤖 Réentraînement Modèle 3 — Handicap...")
df_h = df_clean[df_clean['handicap_sets'].notna()].copy()
df_h['cote_diff'] = 0.0; df_h['cote_proba_A'] = 0.5; df_h['cote_proba_B'] = 0.5
X_h = df_h[FEATURES].fillna(0).astype('float32')
y_h = df_h['handicap_sets'].astype(int).clip(1,3) - 1
X_tr_h, X_te_h, y_tr_h, y_te_h = train_test_split(X_h, y_h, test_size=0.2, random_state=42)
modele_handi = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, eval_metric='mlogloss', random_state=42, n_jobs=-1)
modele_handi.fit(X_tr_h, y_tr_h, verbose=False)
acc_handi = accuracy_score(y_te_h+1, modele_handi.predict(X_te_h)+1)
print(f"   ✅ Précision : {acc_handi*100:.1f}%")

print("\n🤖 Réentraînement Modèle 4 — Over/Under Sets 2.5...")
df_ou_sets = df_clean[df_clean['over_sets'].notna()].copy()
df_ou_sets['cote_diff'] = 0.0; df_ou_sets['cote_proba_A'] = 0.5; df_ou_sets['cote_proba_B'] = 0.5
X_ou_s = df_ou_sets[FEATURES].fillna(0).astype('float32')
y_ou_s = df_ou_sets['over_sets'].astype(int)
X_tr_ou_s, X_te_ou_s, y_tr_ou_s, y_te_ou_s = train_test_split(X_ou_s, y_ou_s, test_size=0.2, random_state=42, stratify=y_ou_s)
modele_ou_sets = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, eval_metric='logloss', random_state=42, n_jobs=-1)
modele_ou_sets.fit(X_tr_ou_s, y_tr_ou_s, verbose=False)
acc_ou_sets = accuracy_score(y_te_ou_s, modele_ou_sets.predict(X_te_ou_s))
print(f"   ✅ Précision O/U Sets : {acc_ou_sets*100:.1f}%")

print("\n🤖 Réentraînement Modèle 5 — Total Jeux (Over/Under jeux)...")
df_ou_jeux = df_clean[df_clean['total_jeux'].notna() & (df_clean['total_jeux'] > 0)].copy()
df_ou_jeux['cote_diff'] = 0.0; df_ou_jeux['cote_proba_A'] = 0.5; df_ou_jeux['cote_proba_B'] = 0.5
X_ou_j = df_ou_jeux[FEATURES].fillna(0).astype('float32')
y_ou_j = df_ou_jeux['total_jeux'].astype(float)
X_tr_ou_j, X_te_ou_j, y_tr_ou_j, y_te_ou_j = train_test_split(X_ou_j, y_ou_j, test_size=0.2, random_state=42)
modele_ou_jeux = XGBRegressor(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8, random_state=42, n_jobs=-1)
modele_ou_jeux.fit(X_tr_ou_j, y_tr_ou_j, verbose=False)
mae_jeux = abs(y_te_ou_j.values - modele_ou_jeux.predict(X_te_ou_j)).mean()
print(f"   ✅ Erreur moyenne total jeux : ±{mae_jeux:.1f} jeux")

# Dictionnaire scores
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

elo_final      = df_clean.groupby('winner_name')['elo_winner'].last().to_dict()
elo_final_surf = {}
for surf in ['Hard','Clay','Grass','Carpet']:
    mask = df_clean['surface'] == surf
    elo_final_surf[surf] = df_clean[mask].groupby('winner_name')['elo_winner_surf'].last().to_dict()
forme_final = df_clean.groupby('winner_name')['forme_winner'].last().to_dict()

# ============================================================
# ÉTAPE 9 — SAUVEGARDE
# ============================================================
print("\n💾 Sauvegarde...")
modeles_complets = {
    'modele_win': modele_win, 'modele_sets': modele_sets, 'modele_handi': modele_handi,
    'modele_ou_sets': modele_ou_sets, 'modele_ou_jeux': modele_ou_jeux,
    'features': FEATURES, 'simplifier_round': simplifier_round,
    'dico_scores': dico_scores, 'dico_scores_surf': dico_scores_surf,
    'elo_final': elo_final, 'elo_final_surf': elo_final_surf, 'forme_final': forme_final,
    'surface_map': surface_map, 'circuit_map': circuit_map,
    'acc_win': acc_win, 'acc_sets': acc_sets, 'acc_handi': acc_handi,
    'acc_ou_sets': acc_ou_sets, 'mae_ou_jeux': mae_jeux,
    'date_entrainement': datetime.now().strftime('%Y-%m-%d %H:%M'),
}

with open(FICHIER_MODELE, 'wb') as f:
    pickle.dump(modeles_complets, f)
print(f"   ✅ modeles_tennis_v2.pkl sauvegardé")

# ============================================================
# ÉTAPE 10 — UPLOAD SUR HUGGINGFACE
# ============================================================
print("\n🚀 Upload sur HuggingFace...")
try:
    from huggingface_hub import HfApi
    api = HfApi()
    api.upload_file(
        path_or_fileobj=FICHIER_MODELE,
        path_in_repo='data/modeles_tennis_v2.pkl',
        repo_id=HF_REPO_SPACE, repo_type='space',
        commit_message=f'Réentraînement {datetime.now().strftime("%Y-%m-%d")} — Win:{acc_win*100:.1f}%'
    )
    print("   ✅ Modèle uploadé sur HuggingFace Space")
    api.upload_file(
        path_or_fileobj=FICHIER_BASE,
        path_in_repo='BASE_FEATURES.csv',
        repo_id=HF_REPO_DATA, repo_type='dataset',
        commit_message=f'Mise à jour données {datetime.now().strftime("%Y-%m-%d")}'
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
print(f"  Nouveaux matchs ajoutés : {nb_nouveaux}")
print(f"  Total matchs en base    : {len(df_clean):,}")
print(f"  Vainqueur               : {acc_win*100:.1f}%")
print(f"  Nb Sets                 : {acc_sets*100:.1f}%")
print(f"  Handicap                : {acc_handi*100:.1f}%")
print(f"  Over/Under Sets 2.5     : {acc_ou_sets*100:.1f}%")
print(f"  Total Jeux (erreur moy) : ±{mae_jeux:.1f} jeux")
print(f"  Joueurs avec ELO        : {len(elo_final):,}")
print(f"  Date                    : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}")
print(f"\n✅ L'app HuggingFace sera mise à jour dans 2-3 minutes !")
