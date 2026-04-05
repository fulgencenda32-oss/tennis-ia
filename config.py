"""
╔══════════════════════════════════════════════════════════════════╗
║                    TENNIS IA — CONFIGURATION                      ║
║                    Auteur : Fulgence N'da                         ║
║                                                                   ║
║  Ce fichier centralise tous les paramètres du projet.            ║
║  Modifie ici pour ajuster le comportement global.                ║
╚══════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime

# ══════════════════════════════════════════════════════════════════
# PARAMÈTRES DE TÉLÉCHARGEMENT
# ══════════════════════════════════════════════════════════════════

# Années à télécharger (2010 à 2026 inclus)
ANNEES = list(range(2010, 2027))

# URL de base Sackmann
BASE_SACKMANN = "https://raw.githubusercontent.com/JeffSackmann"

# Sources de données (5 catégories de simples)
SOURCES_MATCHS = {
    "atp_main": {
        "nom": "ATP Tour Principal",
        "circuit": "ATP",
        "url_pattern": BASE_SACKMANN + "/tennis_atp/master/atp_matches_{annee}.csv",
    },
    "atp_chall": {
        "nom": "ATP Challengers & Qualifs",
        "circuit": "Challenger",
        "url_pattern": BASE_SACKMANN + "/tennis_atp/master/atp_matches_qual_chall_{annee}.csv",
    },
    "atp_futures": {
        "nom": "ITF Hommes (Futures)",
        "circuit": "ITF_M",
        "url_pattern": BASE_SACKMANN + "/tennis_atp/master/atp_matches_futures_{annee}.csv",
    },
    "wta_main": {
        "nom": "WTA Tour Principal",
        "circuit": "WTA",
        "url_pattern": BASE_SACKMANN + "/tennis_wta/master/wta_matches_{annee}.csv",
    },
    "wta_itf": {
        "nom": "ITF Femmes & Qualifs WTA",
        "circuit": "ITF_W",
        "url_pattern": BASE_SACKMANN + "/tennis_wta/master/wta_matches_qual_itf_{annee}.csv",
    },
}

# Sources joueurs et classements
SOURCES_AUTRES = {
    "atp_joueurs": BASE_SACKMANN + "/tennis_atp/master/atp_players.csv",
    "wta_joueurs": BASE_SACKMANN + "/tennis_wta/master/wta_players.csv",
    "atp_ranking": BASE_SACKMANN + "/tennis_atp/master/atp_rankings_current.csv",
    "wta_ranking": BASE_SACKMANN + "/tennis_wta/master/wta_rankings_current.csv",
}

# Timeout pour les requêtes HTTP (secondes)
TIMEOUT_HTTP = 30

# ══════════════════════════════════════════════════════════════════
# PARAMÈTRES ELO (PONDÉRATION TEMPORELLE)
# ══════════════════════════════════════════════════════════════════

# K variable selon l'année du match (plus récent = plus d'impact)
K_PAR_ANNEE = {
    2010: 24, 2011: 24, 2012: 24, 2013: 24, 2014: 24, 2015: 24,
    2016: 28, 2017: 28, 2018: 28, 2019: 28,
    2020: 32, 2021: 32, 2022: 32,
    2023: 38, 2024: 38,
    2025: 44, 2026: 44,
}

# Fenêtre de recence (années) : facteur de décroissance exponentielle
# Les matchs dans cette fenêtre gardent ~100% de leur poids
# Les matchs plus anciens perdent progressivement de l'importance
FENETRE_RECENCE = 2

# ELO de départ pour les nouveaux joueurs
ELO_INITIAL = 1500.0

# ══════════════════════════════════════════════════════════════════
# DOSSIERS ET FICHIERS
# ══════════════════════════════════════════════════════════════════

DATA_DIR = "data"

# Sous-dossiers
RAW_DIR = f"{DATA_DIR}/raw"
RAW_MATCHS_DIR = f"{RAW_DIR}/matchs"
RAW_JOUEURS_DIR = f"{RAW_DIR}/joueurs"
RAW_CLASSEMENTS_DIR = f"{RAW_DIR}/classements"
CLEANED_DIR = f"{DATA_DIR}/cleaned"
STATS_DIR = f"{DATA_DIR}/stats"
MODELS_DIR = f"{DATA_DIR}/models"
BACKUP_DIR = f"{DATA_DIR}/backups"

# Fichiers de sortie
FICHIER_MATCHS_BRUTS = f"{RAW_DIR}/matchs_bruts_complet.csv"
FICHIER_MATCHS_CLEAN = f"{CLEANED_DIR}/matchs_clean.csv"
FICHIER_JOUEURS = f"{CLEANED_DIR}/joueurs.csv"
FICHIER_CLASSEMENTS = f"{CLEANED_DIR}/classements.json"
FICHIER_ELO = f"{STATS_DIR}/elo_complet.pkl"
FICHIER_STATS = f"{STATS_DIR}/stats_joueurs.pkl"
FICHIER_MODELES = f"{MODELS_DIR}/modeles_tennis_v2.pkl"
FICHIER_META_MODELE = f"{MODELS_DIR}/ia_supreme.pkl"

# Checkpoints (pour vérifier que le script précédent a bien tourné)
CHECKPOINT_1 = f"{DATA_DIR}/checkpoint_1_telechargement.json"
CHECKPOINT_2 = f"{DATA_DIR}/checkpoint_2_nettoyage.json"
CHECKPOINT_3 = f"{DATA_DIR}/checkpoint_3_stats.json"
CHECKPOINT_4 = f"{DATA_DIR}/checkpoint_4_entrainement.json"

# Rapports
RAPPORT_DOUBLONS = f"{RAW_DIR}/rapport_doublons.txt"
LOG_FILE = f"{DATA_DIR}/tennis_ia.log"

# ══════════════════════════════════════════════════════════════════
# PARAMÈTRES ML
# ══════════════════════════════════════════════════════════════════

# Nombre minimum de matchs pour qu'un joueur soit utilisé en ML
MIN_MATCHS_JOUEUR = 5

# Features pour les modèles
FEATURES_BASE = [
    'elo_diff', 'elo_diff_surf', 'forme_diff', 'h2h_diff',
    'fatigue_diff', 'streak_diff', 'comeback_diff', 'clutch_diff',
    'bigmatch_diff', 'dominance_diff', 'revanche_diff', 'hist_tournoi_diff',
    'rank_diff', 'age_diff', 'surface_enc', 'circuit_enc', 'genre_enc',
    'best_of', 'round_num', 'cote_diff', 'cote_proba_A', 'cote_proba_B',
]

# Meta-features pour l'IA Suprême
META_FEATURES = [
    'proba_generale', 'proba_clay', 'proba_hard', 'proba_grass',
    'surface_enc', 'proba_specialiste', 'proba_max', 'proba_min',
    'proba_mean', 'proba_std', 'ecart_clay_gen', 'ecart_hard_gen',
    'ecart_grass_gen', 'ecart_specialiste_gen', 'ecart_gen_spec',
    'ecart_max', 'confiance_generale', 'confiance_specialiste',
    'consensus', 'consensus_std', 'moyenne_probas', 'accord_gen_spec',
]

# Encodages
SURFACE_MAP = {'Hard': 0, 'Clay': 1, 'Grass': 2, 'Carpet': 3}
CIRCUIT_MAP = {'ATP': 0, 'WTA': 1, 'Challenger': 2, 'ITF_M': 3, 'ITF_W': 4}

# ══════════════════════════════════════════════════════════════════
# UTILITAIRES PARTAGÉS
# ══════════════════════════════════════════════════════════════════

def simplifier_round(r):
    """Convertit un round en valeur numérique (1-7)"""
    r = str(r).upper().strip()
    mapping = {
        'F': 7, 'SF': 6, 'QF': 5, 'R16': 4,
        'R32': 3, 'R64': 2, 'R128': 1, 'RR': 4, 'BR': 5,
        'Q1': 1, 'Q2': 2, 'Q3': 3,
    }
    return mapping.get(r, 3)

def get_k_pour_annee(annee):
    """Retourne le K à utiliser pour une année donnée"""
    return K_PAR_ANNEE.get(annee, 32)

def calculer_facteur_recence(annee_match, annee_max):
    """
    Calcule le facteur de recence (0 à 1)
    Plus le match est récent, plus le facteur est proche de 1
    """
    ecart = annee_max - annee_match
    if ecart <= 0:
        return 1.0
    return 0.5 ** (ecart / FENETRE_RECENCE)

# ══════════════════════════════════════════════════════════════════
# MÉTADONNÉES
# ══════════════════════════════════════════════════════════════════

VERSION = "2.0"
AUTEUR = "Fulgence N'da"
DATE_CREATION = datetime.now().strftime("%Y-%m-%d")