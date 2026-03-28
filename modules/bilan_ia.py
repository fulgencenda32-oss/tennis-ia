"""
bilan_ia.py — Bilan hebdomadaire automatique de l'IA Tennis
Analyse enrichie : mémoire long terme, profils joueurs,
confiance calibrée, Black Swans, recommandations automatiques
Tennis IA | Fulgence N'da
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

FICHIER_MEMOIRE = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'memoire_ia.json'
)

# ─────────────────────────────────────────────
# MÉMOIRE LONG TERME (4 semaines glissantes)
# ─────────────────────────────────────────────

def _charger_memoire() -> dict:
    """Charge la mémoire cumulative des bilans précédents."""
    if os.path.exists(FICHIER_MEMOIRE):
        try:
            with open(FICHIER_MEMOIRE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"semaines": [], "patterns_recurrents": {}}

def _sauvegarder_memoire(memoire: dict):
    """Sauvegarde la mémoire après chaque bilan."""
    os.makedirs(os.path.dirname(FICHIER_MEMOIRE), exist_ok=True)
    with open(FICHIER_MEMOIRE, 'w', encoding='utf-8') as f:
        json.dump(memoire, f, ensure_ascii=False, indent=2)

def _mettre_a_jour_memoire(bilan: dict, memoire: dict) -> dict:
    """
    Ajoute le bilan courant à la mémoire et détecte
    les patterns récurrents sur 4 semaines glissantes.
    """
    entree = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "taux_global": bilan.get("taux_global", 0),
        "par_surface": {
            s: d["corrects"] / d["total"] if d["total"] > 0 else 0
            for s, d in bilan.get("par_surface", {}).items()
        },
        "nb_erreurs": bilan.get("erreurs_count", 0),
        "nb_black_swans": bilan.get("nb_black_swans", 0),
    }

    # Garder uniquement les 4 dernières semaines
    memoire["semaines"].append(entree)
    memoire["semaines"] = memoire["semaines"][-4:]

    # Détecter patterns récurrents par surface
    patterns = {}
    if len(memoire["semaines"]) >= 2:
        toutes_surfaces = set()
        for s in memoire["semaines"]:
            toutes_surfaces.update(s.get("par_surface", {}).keys())

        for surf in toutes_surfaces:
            taux_surf = [
                s["par_surface"].get(surf, None)
                for s in memoire["semaines"]
            ]
            taux_surf = [t for t in taux_surf if t is not None]
            if len(taux_surf) >= 2:
                moyenne = sum(taux_surf) / len(taux_surf)
                tendance = taux_surf[-1] - taux_surf[0]
                patterns[surf] = {
                    "moyenne": round(moyenne, 3),
                    "tendance": round(tendance, 3),
                    "alerte": moyenne < 0.65,
                    "amelioration": tendance > 0.05,
                }

    memoire["patterns_recurrents"] = patterns
    return memoire

# ─────────────────────────────────────────────
# CHARGEMENT PRÉDICTIONS DEPUIS FIRESTORE
# ─────────────────────────────────────────────

def _charger_predictions_semaine(db, n_jours: int = 7) -> list:
    """Charge les prédictions des n derniers jours avec résultat réel."""
    cutoff = datetime.now() - timedelta(days=n_jours)
    try:
        docs = (
            db.collection("predictions")
            .where("date", ">=", cutoff.strftime("%Y-%m-%d"))
            .where("resultat_reel", "!=", None)
            .stream()
        )
        return [d.to_dict() for d in docs]
    except Exception as e:
        # Fallback sur fichier local
        try:
            fichier = os.path.join(
                os.path.dirname(__file__), '..', 'data', 'historique.json'
            )
            if os.path.exists(fichier):
                with open(fichier, 'r', encoding='utf-8') as f:
                    tous = json.load(f)
                cutoff_str = cutoff.strftime("%Y-%m-%d")
                return [
                    p for p in tous
                    if p.get("resultat_reel")
                    and str(p.get("date", ""))[:10] >= cutoff_str
                ]
        except:
            return []

# ─────────────────────────────────────────────
# CALCUL DU BILAN ENRICHI
# ─────────────────────────────────────────────

def _est_correct(p: dict) -> bool:
    """Vérifie si une prédiction est correcte."""
    pred = p.get("vainqueur", p.get("prediction_ia", "")).strip().lower()
    reel = p.get("resultat_reel", "").strip().lower()
    if not pred or not reel:
        return False
    return pred.split()[-1] == reel.split()[-1] or pred == reel

def _get_rank_categorie(rank) -> str:
    """Catégorise le ranking d'un joueur."""
    try:
        r = int(float(str(rank)))
        if r <= 20:   return "Top 20"
        if r <= 50:   return "Top 21-50"
        if r <= 100:  return "Top 51-100"
        if r <= 200:  return "Top 101-200"
        return "200+"
    except:
        return "Inconnu"

def _calculer_bilan(predictions: list) -> dict:
    """Calcul complet du bilan avec toutes les analyses enrichies."""
    if not predictions:
        return {}

    total = len(predictions)
    corrects_list = [p for p in predictions if _est_correct(p)]
    erreurs_list  = [p for p in predictions if not _est_correct(p)]
    corrects = len(corrects_list)

    # ── Par surface ──
    par_surface = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        s = p.get("surface", "Inconnu")
        par_surface[s]["total"] += 1
        if _est_correct(p):
            par_surface[s]["corrects"] += 1

    # ── Par tournoi ──
    par_tournoi = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        t = p.get("tournoi", p.get("tournament", "Inconnu"))
        par_tournoi[t]["total"] += 1
        if _est_correct(p):
            par_tournoi[t]["corrects"] += 1

    # ── Par round ──
    par_round = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        r = p.get("round", p.get("best_of", "Inconnu"))
        par_round[r]["total"] += 1
        if _est_correct(p):
            par_round[r]["corrects"] += 1

    # ── Par circuit ──
    par_circuit = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        c = p.get("tournoi", "ATP")
        par_circuit[c]["total"] += 1
        if _est_correct(p):
            par_circuit[c]["corrects"] += 1

    # ── Par profil de joueur (ranking) ──
    par_profil = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        rank_a = p.get("rank_a", p.get("winner_rank", 500))
        rank_b = p.get("rank_b", p.get("loser_rank", 500))
        favori_rank = min(
            float(str(rank_a).replace("nan", "500") or 500),
            float(str(rank_b).replace("nan", "500") or 500)
        )
        cat = _get_rank_categorie(favori_rank)
        par_profil[cat]["total"] += 1
        if _est_correct(p):
            par_profil[cat]["corrects"] += 1

    # ── Score de confiance calibré ──
    par_confiance = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        conf = p.get("confiance", {})
        if isinstance(conf, dict):
            niveau = conf.get("niveau", "INCONNUE")
        else:
            niveau = "INCONNUE"
        par_confiance[niveau]["total"] += 1
        if _est_correct(p):
            par_confiance[niveau]["corrects"] += 1

    # ── Black Swans (upsets majeurs) ──
    black_swans = []
    for p in erreurs_list:
        proba_v = float(str(p.get("proba_v", 50)).replace("%", "") or 50)
        if proba_v >= 75:
            black_swans.append({
                "match": f"{p.get('joueur_a','?')} vs {p.get('joueur_b','?')}",
                "surface": p.get("surface", "?"),
                "tournoi": p.get("tournoi", "?"),
                "date": p.get("date", "?"),
                "proba_annoncee": f"{proba_v}%",
                "ia_a_predit": p.get("vainqueur", p.get("prediction_ia", "?")),
                "vrai_vainqueur": p.get("resultat_reel", "?"),
            })

    # ── Duels récurrents mal prédits ──
    duels_erreurs = defaultdict(int)
    duels_total   = defaultdict(int)
    for p in predictions:
        a = p.get("joueur_a", "")
        b = p.get("joueur_b", "")
        if a and b:
            key = tuple(sorted([a.split()[-1], b.split()[-1]]))
            duels_total[key] += 1
            if not _est_correct(p):
                duels_erreurs[key] += 1

    duels_problematiques = [
        {
            "duel": f"{k[0]} vs {k[1]}",
            "erreurs": v,
            "total": duels_total[k],
            "taux_erreur": round(v / duels_total[k] * 100, 1)
        }
        for k, v in duels_erreurs.items()
        if v >= 2 and duels_total[k] >= 2
    ]
    duels_problematiques.sort(key=lambda x: x["taux_erreur"], reverse=True)

    # ── Recommandations automatiques ──
    recommandations = []

    for surf, d in par_surface.items():
        if d["total"] >= 3:
            taux = d["corrects"] / d["total"]
            if taux < 0.60:
                recommandations.append({
                    "priorite": "🔴 HAUTE",
                    "action": f"Renforcer le modèle sur surface {surf}",
                    "detail": f"Taux actuel : {taux*100:.1f}% — objectif : 70%+",
                    "impact": "Réentraîner avec pondération x2 sur erreurs {surf}"
                })
            elif taux < 0.68:
                recommandations.append({
                    "priorite": "🟡 MOYENNE",
                    "action": f"Surveiller surface {surf}",
                    "detail": f"Taux actuel : {taux*100:.1f}% — légèrement sous la moyenne",
                    "impact": "Augmenter le poids des matchs {surf} récents"
                })

    if len(black_swans) >= 3:
        recommandations.append({
            "priorite": "🔴 HAUTE",
            "action": "Trop d'upsets non détectés cette semaine",
            "detail": f"{len(black_swans)} Black Swans manqués",
            "impact": "Baisser le seuil de confiance HAUTE de 75% à 70%"
        })

    for cat, d in par_profil.items():
        if d["total"] >= 3 and d["corrects"] / d["total"] < 0.55:
            recommandations.append({
                "priorite": "🟡 MOYENNE",
                "action": f"Améliorer les prédictions sur joueurs {cat}",
                "detail": f"Taux : {d['corrects']/d['total']*100:.1f}% — insuffisant",
                "impact": "Enrichir la base de données sur ce profil de joueurs"
            })

    conf_haute = par_confiance.get("HAUTE", {"total": 0, "corrects": 0})
    if conf_haute["total"] >= 5:
        taux_haute = conf_haute["corrects"] / conf_haute["total"]
        if taux_haute < 0.75:
            recommandations.append({
                "priorite": "🔴 HAUTE",
                "action": "Score de confiance HAUTE mal calibré",
                "detail": f"Confiance HAUTE réussit seulement {taux_haute*100:.1f}% — devrait être 75%+",
                "impact": "Relever le seuil de déclenchement du score HAUTE"
            })

    # ── Calcul poids pour réentraînement ──
    poids_erreurs = []
    for p in predictions:
        proba = float(str(p.get("proba_v", 50)).replace("%", "") or 50) / 100
        if _est_correct(p):
            poids_erreurs.append({"match": f"{p.get('joueur_a','')} vs {p.get('joueur_b','')}", "poids": 1.0})
        else:
            # Plus l'IA était confiante et s'est trompée, plus le poids est élevé
            poids = 1.0 + (proba - 0.5) * 4
            poids_erreurs.append({
                "match": f"{p.get('joueur_a','')} vs {p.get('joueur_b','')}",
                "poids": round(min(poids, 3.0), 2)
            })

    return {
        "total": total,
        "corrects": corrects,
        "taux_global": corrects / total if total > 0 else 0,
        "erreurs_count": len(erreurs_list),
        "par_surface": dict(par_surface),
        "par_tournoi": dict(par_tournoi),
        "par_round": dict(par_round),
        "par_circuit": dict(par_circuit),
        "par_profil": dict(par_profil),
        "par_confiance": dict(par_confiance),
        "black_swans": black_swans,
        "nb_black_swans": len(black_swans),
        "duels_problematiques": duels_problematiques[:5],
        "recommandations": recommandations,
        "poids_erreurs": poids_erreurs,
        "exemples_erreurs": erreurs_list[:10],
    }


def _taux(d: dict) -> float:
    if d["total"] == 0: return 0.0
    return d["corrects"] / d["total"]


# ─────────────────────────────────────────────
# AFFICHAGE STREAMLIT ENRICHI
# ─────────────────────────────────────────────

def afficher_bilan_hebdomadaire(db, n_jours: int = 7):
    """Affiche le bilan complet enrichi."""
    date_debut = (datetime.now() - timedelta(days=n_jours)).strftime("%d/%m/%Y")
    date_fin   = datetime.now().strftime("%d/%m/%Y")

    st.title("📊 Bilan Hebdomadaire de l'IA")
    st.caption(f"Période : {date_debut} → {date_fin}")

    # Sélecteur de période
    n_jours = st.selectbox(
        "Période d'analyse",
        [7, 14, 30],
        format_func=lambda x: f"{x} derniers jours",
        index=0
    )

    with st.spinner("Analyse en cours..."):
        predictions = _charger_predictions_semaine(db, n_jours)

    if not predictions:
        st.warning("Aucune prédiction avec résultat réel trouvée sur cette période.")
        st.info("💡 Lance une prédiction puis saisis le résultat réel dans l'onglet Historique.")
        return

    bilan   = _calculer_bilan(predictions)
    memoire = _charger_memoire()
    memoire = _mettre_a_jour_memoire(bilan, memoire)
    _sauvegarder_memoire(memoire)

    taux_pct = bilan["taux_global"] * 100

    # ── Score global ──
    st.subheader("🎯 Performance globale")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Matchs analysés", bilan["total"])
    col2.metric("Corrects", bilan["corrects"])
    col3.metric("Erreurs", bilan["erreurs_count"])
    col4.metric("Taux global", f"{taux_pct:.1f}%")

    couleur = "🟢" if taux_pct >= 70 else ("🟡" if taux_pct >= 60 else "🔴")
    st.progress(bilan["taux_global"], text=f"{couleur} {taux_pct:.1f}% de précision")
    st.divider()

    # ── Mémoire long terme ──
    if len(memoire["semaines"]) >= 2:
        st.subheader("📈 Évolution sur 4 semaines")
        df_mem = pd.DataFrame([
            {
                "Semaine": s["date"],
                "Taux global": f"{s['taux_global']*100:.1f}%",
                "Erreurs": s["nb_erreurs"],
                "Black Swans": s["nb_black_swans"],
            }
            for s in memoire["semaines"]
        ])
        st.dataframe(df_mem, use_container_width=True, hide_index=True)

        # Patterns récurrents
        patterns = memoire.get("patterns_recurrents", {})
        alertes = [s for s, p in patterns.items() if p.get("alerte")]
        if alertes:
            st.error(f"⚠️ **Pattern récurrent détecté** — L'IA performe mal sur : {', '.join(alertes)} depuis plusieurs semaines")
        amelios = [s for s, p in patterns.items() if p.get("amelioration")]
        if amelios:
            st.success(f"✅ **Amélioration détectée** sur : {', '.join(amelios)}")
        st.divider()

    # ── Par surface ──
    st.subheader("🟤 Analyse par surface")
    rows_s = []
    for surf, d in sorted(bilan["par_surface"].items()):
        t = _taux(d) * 100
        icone = "🟢" if t >= 72 else ("🟡" if t >= 65 else "🔴")
        # Comparer avec semaine précédente si dispo
        evolution = ""
        if len(memoire["semaines"]) >= 2:
            prev = memoire["semaines"][-2].get("par_surface", {}).get(surf)
            if prev is not None:
                diff = t/100 - prev
                evolution = f"{'↑' if diff > 0 else '↓'} {abs(diff)*100:.1f}%"
        rows_s.append({
            "Surface": surf,
            "Matchs": d["total"],
            "Corrects": d["corrects"],
            "Taux": f"{t:.1f}%",
            "Évolution": evolution,
            "Statut": icone,
        })
    st.dataframe(pd.DataFrame(rows_s), use_container_width=True, hide_index=True)
    st.divider()

    # ── Par profil de joueur ──
    st.subheader("👤 Analyse par profil de joueur")
    rows_p = []
    for cat, d in sorted(bilan["par_profil"].items()):
        t = _taux(d) * 100
        icone = "🟢" if t >= 70 else ("🟡" if t >= 60 else "🔴")
        rows_p.append({
            "Profil (ranking favori)": cat,
            "Matchs": d["total"],
            "Corrects": d["corrects"],
            "Taux": f"{t:.1f}%",
            "Statut": icone,
        })
    if rows_p:
        st.dataframe(pd.DataFrame(rows_p), use_container_width=True, hide_index=True)
    st.divider()

    # ── Score de confiance calibré ──
    st.subheader("🎯 Calibration du score de confiance")
    rows_c = []
    for niveau, d in bilan["par_confiance"].items():
        if d["total"] > 0:
            t = _taux(d) * 100
            objectif = {"HAUTE": 75, "MOYENNE": 62, "FAIBLE": 50}.get(niveau, 60)
            ok = "✅" if t >= objectif else "⚠️"
            rows_c.append({
                "Niveau confiance": niveau,
                "Matchs": d["total"],
                "Taux réel": f"{t:.1f}%",
                "Objectif": f"{objectif}%",
                "Calibré ?": ok,
            })
    if rows_c:
        st.dataframe(pd.DataFrame(rows_c), use_container_width=True, hide_index=True)
        st.caption("💡 Une confiance HAUTE devrait réussir 75%+ des fois pour être fiable.")
    st.divider()

    # ── Black Swans ──
    st.subheader("⚡ Black Swans — Upsets non détectés")
    if bilan["black_swans"]:
        st.warning(f"{len(bilan['black_swans'])} upset(s) majeur(s) non anticipé(s) cette semaine")
        df_bs = pd.DataFrame(bilan["black_swans"])
        st.dataframe(df_bs, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Aucun Black Swan cette semaine — l'IA a bien détecté les upsets !")
    st.divider()

    # ── Duels problématiques ──
    if bilan["duels_problematiques"]:
        st.subheader("🔄 Duels récurrents mal prédits")
        df_d = pd.DataFrame(bilan["duels_problematiques"])
        st.dataframe(df_d, use_container_width=True, hide_index=True)
        st.caption("Ces duels sont historiquement difficiles à prédire pour l'IA.")
        st.divider()

    # ── Recommandations automatiques ──
    st.subheader("💡 Recommandations automatiques")
    if bilan["recommandations"]:
        for rec in bilan["recommandations"]:
            if "HAUTE" in rec["priorite"]:
                st.error(f"**{rec['priorite']}** — {rec['action']}\n\n{rec['detail']}\n\n→ {rec['impact']}")
            elif "MOYENNE" in rec["priorite"]:
                st.warning(f"**{rec['priorite']}** — {rec['action']}\n\n{rec['detail']}\n\n→ {rec['impact']}")
            else:
                st.info(f"**{rec['priorite']}** — {rec['action']}\n\n{rec['detail']}")
    else:
        st.success("✅ Aucune recommandation urgente — l'IA performe bien sur tous les critères !")
    st.divider()

    # ── Tournois difficiles ──
    st.subheader("🏆 Tournois avec le plus d'erreurs")
    rows_t = []
    for tournoi, d in sorted(bilan["par_tournoi"].items(), key=lambda x: _taux(x[1])):
        if d["total"] >= 2:
            t = _taux(d) * 100
            rows_t.append({
                "Tournoi": tournoi,
                "Matchs": d["total"],
                "Erreurs": d["total"] - d["corrects"],
                "Taux": f"{t:.1f}%",
            })
    if rows_t:
        st.dataframe(
            pd.DataFrame(rows_t).head(10),
            use_container_width=True, hide_index=True
        )
    st.divider()

    # ── Par round ──
    st.subheader("🎾 Analyse par round")
    rows_r = []
    for rnd, d in bilan["par_round"].items():
        t = _taux(d) * 100
        rows_r.append({"Round": rnd, "Matchs": d["total"], "Taux": f"{t:.1f}%"})
    if rows_r:
        st.dataframe(pd.DataFrame(rows_r), use_container_width=True, hide_index=True)
    st.divider()

    # ── Exemples d'erreurs ──
    st.subheader("❌ Exemples d'erreurs")
    if bilan["exemples_erreurs"]:
        rows_e = []
        for p in bilan["exemples_erreurs"]:
            proba = p.get("proba_v", "?")
            rows_e.append({
                "Date": str(p.get("date", "?"))[:10],
                "Match": f"{p.get('joueur_a','?')} vs {p.get('joueur_b','?')}",
                "Surface": p.get("surface", "?"),
                "IA a prédit": p.get("vainqueur", p.get("prediction_ia", "?")),
                "Résultat réel": p.get("resultat_reel", "?"),
                "Confiance annoncée": f"{proba}%",
                "Tournoi": p.get("tournoi", "?"),
            })
        st.dataframe(pd.DataFrame(rows_e), use_container_width=True, hide_index=True)
    st.divider()

    # ── Export ──
    st.subheader("📥 Export")
    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
        df_export = pd.DataFrame([{
            "Période": f"{date_debut} → {date_fin}",
            "Total": bilan["total"],
            "Corrects": bilan["corrects"],
            "Taux (%)": round(taux_pct, 2),
            "Black Swans": bilan["nb_black_swans"],
            "Recommandations": len(bilan["recommandations"]),
        }])
        st.download_button(
            label="📄 Bilan CSV",
            data=df_export.to_csv(index=False).encode("utf-8"),
            file_name=f"bilan_ia_{date_fin.replace('/', '-')}.csv",
            mime="text/csv",
        )

    with col_ex2:
        if bilan["poids_erreurs"]:
            df_poids = pd.DataFrame(bilan["poids_erreurs"])
            st.download_button(
                label="⚖️ Poids erreurs (pour réentraînement)",
                data=df_poids.to_csv(index=False).encode("utf-8"),
                file_name=f"poids_erreurs_{date_fin.replace('/', '-')}.csv",
                mime="text/csv",
            )