"""
api_rotation.py — Rotation intelligente multi-clés AllSports API + fallback Tennis-Data.org
Tennis IA | Fulgence N'da
"""

import os
import time
import json
import requests
import streamlit as st
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

ALLSPORTS_ENDPOINT = "https://apiv2.allsportsapi.com/tennis/"
TENNIS_DATA_ENDPOINT = "http://www.tennis-data.co.uk/live/live.php"
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
    
    # ✅ Vérifier que le cache contient des matchs
    data = entry["data"]
    if isinstance(data, dict):
        result = data.get("result", [])
        if not result or len(result) == 0:
            return None
    
    return data

def _ecrire_cache(params: dict, data):
    # ✅ Ne pas cacher si vide
    if isinstance(data, dict):
        result = data.get("result", [])
        if not result or len(result) == 0:
            return
    
    if "api_cache" not in st.session_state:
        st.session_state.api_cache = {}
    st.session_state.api_cache[_cache_key(params)] = {
        "data": data,
        "timestamp": time.time(),
    }


# ─────────────────────────────────────────────
# ✅ FALLBACK : TENNIS-DATA.ORG
# ─────────────────────────────────────────────

def _fallback_tennis_data(date_debut, date_fin):
    """
    Récupère les matchs depuis Tennis-Data.org et les convertit au format AllSports
    """
    try:
        response = requests.get(TENNIS_DATA_ENDPOINT, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Chercher les tables de matchs
        tables = soup.find_all('table')
        matchs = []
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 5:
                    try:
                        # Extraction basique
                        date_match = cols[0].text.strip()
                        tournoi = cols[1].text.strip() if len(cols) > 1 else "Unknown"
                        joueur_a = cols[2].text.strip() if len(cols) > 2 else ""
                        joueur_b = cols[3].text.strip() if len(cols) > 3 else ""
                        score = cols[4].text.strip() if len(cols) > 4 else ""
                        surface = cols[5].text.strip() if len(cols) > 5 else "Hard"
                        
                        if joueur_a and joueur_b:
                            # Conversion au format AllSports
                            matchs.append({
                                "event_key": hash(f"{joueur_a}{joueur_b}{date_match}"),
                                "event_date": date_debut,
                                "event_time": "TBD",
                                "event_first_player": joueur_a,
                                "first_player_key": 0,
                                "event_second_player": joueur_b,
                                "second_player_key": 0,
                                "league_name": tournoi,
                                "event_ground": surface,
                                "event_final_result": score,
                                "event_status": "Finished" if score else "Not Started",
                                "country_name": "ATP/WTA",
                                "league_round": "Unknown"
                            })
                    except:
                        continue
        
        if matchs:
            return {
                "success": 1,
                "result": matchs
            }
        
        return None
        
    except Exception as e:
        return None


# ─────────────────────────────────────────────
# APPEL API PRINCIPAL (avec fallback)
# ─────────────────────────────────────────────

def appel_api(params: dict, utiliser_cache: bool = True) -> dict:
    _init_quota_state()

    # 1. Vérifier le cache
    if utiliser_cache:
        donnees_cache = _lire_cache(params)
        if donnees_cache is not None:
            nb_matchs = 0
            if isinstance(donnees_cache, dict):
                nb_matchs = len(donnees_cache.get("result", []))
            
            return {
                "data": donnees_cache,
                "source": "cache",
                "cle_utilisee": None,
                "message": f"✅ Cache : {nb_matchs} match(s) (quota préservé).",
            }

    # 2. Choisir la meilleure clé AllSports
    cle = _choisir_cle()
    
    # 3. Si toutes les clés AllSports épuisées → Tennis-Data fallback
    if cle is None:
        # Essayer Tennis-Data.org
        date_debut = params.get("from", datetime.now().strftime("%Y-%m-%d"))
        date_fin = params.get("to", date_debut)
        
        data_fallback = _fallback_tennis_data(date_debut, date_fin)
        
        if data_fallback:
            nb_matchs = len(data_fallback.get("result", []))
            _ecrire_cache(params, data_fallback)
            return {
                "data": data_fallback,
                "source": "tennis_data",
                "cle_utilisee": None,
                "message": f"🔄 Tennis-Data.org : {nb_matchs} match(s) (AllSports épuisé).",
            }
        
        # Si même Tennis-Data échoue → cache expiré
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
            "message": "❌ AllSports épuisé et Tennis-Data inaccessible.",
        }

    # 4. Effectuer l'appel AllSports
    params_complets = {"APIkey": cle, **params}
    index_cle = API_KEYS.index(cle) + 1

    try:
        response = requests.get(ALLSPORTS_ENDPOINT, params=params_complets, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # ✅ Vérifier si la clé est expirée (erreur paiement)
        if data.get("error") == "1":
            msg_erreur = data.get("result", [{}])[0].get("msg", "")
            if "payment" in msg_erreur.lower():
                # Clé expirée → marquer comme épuisée et réessayer
                st.session_state.api_quota[cle]["used"] = QUOTA_PAR_CLE
                return appel_api(params, utiliser_cache=False)  # Retry avec autre clé
        
        _incrementer_quota(cle)
        _ecrire_cache(params, data)

        nb_matchs = 0
        if isinstance(data, dict) and data.get("success") == 1:
            nb_matchs = len(data.get("result", []))
        
        restant, total = _quota_global_restant()
        message = f"✅ AllSports clé #{index_cle} : {nb_matchs} match(s) ({_quota_restant(cle)} requêtes restantes)."
        
        if restant / total < SEUIL_ALERTE_ADMIN:
            message += f"\n🚨 ALERTE : {restant}/{total} requêtes globales restantes."

        return {
            "data": data,
            "source": "api",
            "cle_utilisee": index_cle,
            "message": message,
        }

    except requests.exceptions.RequestException as e:
        # Erreur réseau AllSports → essayer Tennis-Data
        date_debut = params.get("from", datetime.now().strftime("%Y-%m-%d"))
        date_fin = params.get("to", date_debut)
        
        data_fallback = _fallback_tennis_data(date_debut, date_fin)
        
        if data_fallback:
            nb_matchs = len(data_fallback.get("result", []))
            _ecrire_cache(params, data_fallback)
            return {
                "data": data_fallback,
                "source": "tennis_data",
                "cle_utilisee": None,
                "message": f"🔄 Tennis-Data.org : {nb_matchs} match(s) (AllSports erreur).",
            }
        
        return {
            "data": None,
            "source": "erreur",
            "cle_utilisee": index_cle,
            "message": f"❌ Erreur AllSports clé #{index_cle} et Tennis-Data : {e}",
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
    st.caption(f"📦 Cache local : {taille_cache} entrée(s)")
    st.info("🔄 Fallback actif : Tennis-Data.org (si AllSports épuisé)")