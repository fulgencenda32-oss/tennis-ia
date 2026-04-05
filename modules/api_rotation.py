"""
api_rotation.py — Rotation intelligente multi-clés AllSports API + cache local
Tennis IA | Fulgence N'da
"""

import os
import time
import json
import requests
import streamlit as st
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ALLSPORTS_ENDPOINT = "https://apiv2.allsportsapi.com/tennis/"
QUOTA_PAR_CLE = 100
SEUIL_ALERTE_ADMIN = 0.20
DUREE_CACHE_HEURES = 24

API_KEYS = [k for k in [
    os.environ.get("ALLSPORTS_API_KEY"),
    os.environ.get("ALLSPORTS_API_KEY_2"),
    os.environ.get("ALLSPORTS_API_KEY_3"),
] if k]


# ─────────────────────────────────────────────
# ÉTAT DE SESSION (quota par clé)
# ─────────────────────────────────────────────

def _init_quota_state():
    if "api_quota" not in st.session_state:
        st.session_state.api_quota = {
            key: {"used": 0, "last_reset": datetime.now().strftime("%Y-%m-%d")}
            for key in API_KEYS
        }

def _reset_quota_si_nouveau_jour():
    today = datetime.now().strftime("%Y-%m-%d")
    for key in API_KEYS:
        entry = st.session_state.api_quota.get(key, {})
        if entry.get("last_reset") != today:
            st.session_state.api_quota[key] = {"used": 0, "last_reset": today}

def _quota_restant(key):
    entry = st.session_state.api_quota.get(key, {"used": 0})
    return QUOTA_PAR_CLE - entry["used"]

def _incrementer_quota(key):
    if key in st.session_state.api_quota:
        st.session_state.api_quota[key]["used"] += 1

def _choisir_cle():
    _reset_quota_si_nouveau_jour()
    meilleure_cle = None
    meilleur_quota = 0
    for key in API_KEYS:
        restant = _quota_restant(key)
        if restant > meilleur_quota:
            meilleur_quota = restant
            meilleure_cle = key
    return meilleure_cle if meilleur_quota > 0 else None

def _quota_global_restant():
    total_max = QUOTA_PAR_CLE * len(API_KEYS)
    total_restant = sum(_quota_restant(k) for k in API_KEYS)
    return total_restant, total_max


# ─────────────────────────────────────────────
# CACHE LOCAL (session_state)
# ─────────────────────────────────────────────

def _cache_key(params: dict) -> str:
    return json.dumps(params, sort_keys=True)

def _lire_cache(params: dict):
    cache = st.session_state.get("api_cache", {})
    key = _cache_key(params)
    entry = cache.get(key)
    if not entry:
        return None
    age_heures = (time.time() - entry["timestamp"]) / 3600
    if age_heures > DUREE_CACHE_HEURES:
        return None
    
    # ✅ NOUVEAU : Vérifier que le cache contient des matchs
    data = entry["data"]
    if isinstance(data, dict):
        result = data.get("result", [])
        if not result or len(result) == 0:
            return None  # Cache vide, on ignore
    
    return data

def _ecrire_cache(params: dict, data):
    # ✅ NOUVEAU : Ne pas cacher si vide
    if isinstance(data, dict):
        result = data.get("result", [])
        if not result or len(result) == 0:
            return  # Ne pas stocker un cache vide
    
    if "api_cache" not in st.session_state:
        st.session_state.api_cache = {}
    st.session_state.api_cache[_cache_key(params)] = {
        "data": data,
        "timestamp": time.time(),
    }


# ─────────────────────────────────────────────
# APPEL API PRINCIPAL
# ─────────────────────────────────────────────

def appel_api(params: dict, utiliser_cache: bool = True) -> dict:
    _init_quota_state()

    # 1. Vérifier le cache
    if utiliser_cache:
        donnees_cache = _lire_cache(params)
        if donnees_cache is not None:
            # ✅ NOUVEAU : Compter les matchs
            nb_matchs = 0
            if isinstance(donnees_cache, dict):
                nb_matchs = len(donnees_cache.get("result", []))
            
            return {
                "data": donnees_cache,
                "source": "cache",
                "cle_utilisee": None,
                "message": f"✅ Cache : {nb_matchs} match(s) trouvé(s) (quota préservé).",
            }

    # 2. Choisir la meilleure clé
    cle = _choisir_cle()
    if cle is None:
        cache_expire = st.session_state.get("api_cache", {}).get(_cache_key(params))
        if cache_expire:
            return {
                "data": cache_expire["data"],
                "source": "cache_expire",
                "cle_utilisee": None,
                "message": "⚠️ Quota épuisé. Cache ancien affiché.",
            }
        return {
            "data": None,
            "source": "erreur",
            "cle_utilisee": None,
            "message": "❌ Quota épuisé et aucun cache disponible.",
        }

    # 3. Effectuer l'appel
    params_complets = {"APIkey": cle, **params}
    index_cle = API_KEYS.index(cle) + 1

    try:
        response = requests.get(ALLSPORTS_ENDPOINT, params=params_complets, timeout=10)
        response.raise_for_status()
        data = response.json()
        _incrementer_quota(cle)
        _ecrire_cache(params, data)

        # ✅ NOUVEAU : Compter les matchs dans la réponse
        nb_matchs = 0
        if isinstance(data, dict) and data.get("success") == 1:
            nb_matchs = len(data.get("result", []))
        
        restant, total = _quota_global_restant()
        message = f"✅ API clé #{index_cle} : {nb_matchs} match(s) ({_quota_restant(cle)} requêtes restantes)."
        
        if restant / total < SEUIL_ALERTE_ADMIN:
            message += f"\n🚨 ALERTE : {restant}/{total} requêtes globales restantes."

        return {
            "data": data,
            "source": "api",
            "cle_utilisee": index_cle,
            "message": message,
        }

    except requests.exceptions.RequestException as e:
        return {
            "data": None,
            "source": "erreur",
            "cle_utilisee": index_cle,
            "message": f"❌ Erreur réseau clé #{index_cle} : {e}",
        }


# ─────────────────────────────────────────────
# WIDGET STREAMLIT — Statut des clés (Admin)
# ─────────────────────────────────────────────

def afficher_statut_api():
    _init_quota_state()
    _reset_quota_si_nouveau_jour()

    st.subheader("🔑 Statut des clés API AllSports")
    restant_total, total_max = _quota_global_restant()
    pct = restant_total / total_max if total_max > 0 else 0

    couleur = "🟢" if pct > 0.5 else ("🟡" if pct > 0.2 else "🔴")
    st.metric(
        label=f"{couleur} Quota global restant",
        value=f"{restant_total} / {total_max} requêtes",
        delta=f"{pct*100:.0f}% disponible",
    )

    for i, key in enumerate(API_KEYS, start=1):
        restant = _quota_restant(key)
        used = st.session_state.api_quota[key]["used"]
        pct_cle = restant / QUOTA_PAR_CLE
        icone = "🟢" if pct_cle > 0.5 else ("🟡" if pct_cle > 0.2 else "🔴")
        st.progress(pct_cle, text=f"{icone} Clé #{i} — {used} utilisées / {restant} restantes")

    taille_cache = len(st.session_state.get("api_cache", {}))
    st.caption(f"📦 Cache local : {taille_cache} entrée(s) stockée(s) en mémoire.")