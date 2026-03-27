"""
bilan_ia.py — Bilan hebdomadaire automatique de l'IA Tennis
Analyse les erreurs par surface, tournoi, round, circuit
Tennis IA | Fulgence N'da
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────────
# CHARGEMENT DES PRÉDICTIONS DEPUIS FIRESTORE
# ─────────────────────────────────────────────

def _charger_predictions_semaine(db, n_jours: int = 7) -> list[dict]:
    """
    Charge depuis Firestore les prédictions des n derniers jours
    qui ont un résultat réel renseigné.
    Adapte la collection selon ton schéma Firestore.
    """
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
        st.error(f"Erreur chargement Firestore : {e}")
        return []


# ─────────────────────────────────────────────
# CALCUL DU BILAN
# ─────────────────────────────────────────────

def _calculer_bilan(predictions: list[dict]) -> dict:
    """
    Analyse une liste de prédictions et retourne un bilan structuré.

    Chaque prédiction doit avoir :
        - prediction_ia  : ex. "Djokovic"
        - resultat_reel  : ex. "Djokovic" (même format)
        - surface        : "Hard" | "Clay" | "Grass"
        - tournoi        : nom du tournoi
        - round          : ex. "Quarts", "Finale", "1er tour"
        - circuit        : "ATP" | "WTA" | "Challenger" | "ITF"
    """
    if not predictions:
        return {}

    total = len(predictions)
    corrects = sum(
        1 for p in predictions
        if p.get("prediction_ia", "").strip().lower() == p.get("resultat_reel", "").strip().lower()
    )

    # ── Par surface ──
    par_surface = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        s = p.get("surface", "Inconnu")
        par_surface[s]["total"] += 1
        if p.get("prediction_ia", "").strip().lower() == p.get("resultat_reel", "").strip().lower():
            par_surface[s]["corrects"] += 1

    # ── Par tournoi ──
    par_tournoi = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        t = p.get("tournoi", "Inconnu")
        par_tournoi[t]["total"] += 1
        if p.get("prediction_ia", "").strip().lower() == p.get("resultat_reel", "").strip().lower():
            par_tournoi[t]["corrects"] += 1

    # ── Par round ──
    par_round = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        r = p.get("round", "Inconnu")
        par_round[r]["total"] += 1
        if p.get("prediction_ia", "").strip().lower() == p.get("resultat_reel", "").strip().lower():
            par_round[r]["corrects"] += 1

    # ── Par circuit ──
    par_circuit = defaultdict(lambda: {"total": 0, "corrects": 0})
    for p in predictions:
        c = p.get("circuit", "Inconnu")
        par_circuit[c]["total"] += 1
        if p.get("prediction_ia", "").strip().lower() == p.get("resultat_reel", "").strip().lower():
            par_circuit[c]["corrects"] += 1

    # ── Patterns d'échec ──
    erreurs = [
        p for p in predictions
        if p.get("prediction_ia", "").strip().lower() != p.get("resultat_reel", "").strip().lower()
    ]

    return {
        "total": total,
        "corrects": corrects,
        "taux_global": corrects / total if total > 0 else 0,
        "erreurs_count": len(erreurs),
        "par_surface": dict(par_surface),
        "par_tournoi": dict(par_tournoi),
        "par_round": dict(par_round),
        "par_circuit": dict(par_circuit),
        "exemples_erreurs": erreurs[:10],  # 10 exemples max
    }


def _taux(d: dict) -> float:
    if d["total"] == 0:
        return 0.0
    return d["corrects"] / d["total"]


# ─────────────────────────────────────────────
# AFFICHAGE STREAMLIT
# ─────────────────────────────────────────────

def afficher_bilan_hebdomadaire(db, n_jours: int = 7):
    """
    Affiche le bilan complet de l'IA pour les n derniers jours.
    À appeler dans le Panel Admin ou un onglet dédié.
    """
    date_debut = (datetime.now() - timedelta(days=n_jours)).strftime("%d/%m/%Y")
    date_fin = datetime.now().strftime("%d/%m/%Y")

    st.title("📊 Bilan Hebdomadaire de l'IA")
    st.caption(f"Période analysée : {date_debut} → {date_fin}")

    with st.spinner("Chargement des prédictions..."):
        predictions = _charger_predictions_semaine(db, n_jours)

    if not predictions:
        st.warning("Aucune prédiction avec résultat réel trouvée sur cette période.")
        return

    bilan = _calculer_bilan(predictions)

    # ── Métriques globales ──
    st.subheader("🎯 Performance globale")
    col1, col2, col3 = st.columns(3)
    col1.metric("Prédictions analysées", bilan["total"])
    col2.metric("Correctes", bilan["corrects"])
    taux_pct = bilan["taux_global"] * 100
    couleur_delta = "normal" if taux_pct >= 70 else "inverse"
    col3.metric("Taux de réussite", f"{taux_pct:.1f}%")

    st.progress(bilan["taux_global"], text=f"{taux_pct:.1f}% de précision cette semaine")
    st.divider()

    # ── Par surface ──
    st.subheader("🟤 Analyse par surface")
    rows_surface = []
    for surf, d in sorted(bilan["par_surface"].items()):
        t = _taux(d) * 100
        icone = "🟢" if t >= 72 else ("🟡" if t >= 65 else "🔴")
        rows_surface.append({
            "Surface": surf,
            "Matchs": d["total"],
            "Corrects": d["corrects"],
            "Taux (%)": f"{t:.1f}",
            "Statut": icone,
        })
    st.dataframe(pd.DataFrame(rows_surface), use_container_width=True, hide_index=True)
    st.divider()

    # ── Par tournoi (top 10 en erreurs) ──
    st.subheader("🏆 Tournois avec le plus d'erreurs")
    rows_tournoi = []
    for tournoi, d in sorted(bilan["par_tournoi"].items(), key=lambda x: _taux(x[1])):
        t = _taux(d) * 100
        rows_tournoi.append({
            "Tournoi": tournoi,
            "Matchs": d["total"],
            "Erreurs": d["total"] - d["corrects"],
            "Taux (%)": f"{t:.1f}",
        })
    st.dataframe(
        pd.DataFrame(rows_tournoi).head(10),
        use_container_width=True,
        hide_index=True,
    )
    st.divider()

    # ── Par round ──
    st.subheader("🎾 Analyse par round")
    rows_round = []
    for rnd, d in bilan["par_round"].items():
        t = _taux(d) * 100
        rows_round.append({
            "Round": rnd,
            "Matchs": d["total"],
            "Taux (%)": f"{t:.1f}",
        })
    st.dataframe(pd.DataFrame(rows_round), use_container_width=True, hide_index=True)
    st.divider()

    # ── Par circuit ──
    st.subheader("🌍 Analyse par circuit")
    cols = st.columns(len(bilan["par_circuit"]) or 1)
    for i, (circuit, d) in enumerate(bilan["par_circuit"].items()):
        t = _taux(d) * 100
        cols[i].metric(circuit, f"{t:.1f}%", f"{d['total']} matchs")
    st.divider()

    # ── Exemples d'erreurs ──
    st.subheader("❌ Exemples d'erreurs de l'IA")
    if bilan["exemples_erreurs"]:
        rows_err = []
        for p in bilan["exemples_erreurs"]:
            rows_err.append({
                "Date": p.get("date", "?"),
                "Match": f"{p.get('joueur_a','?')} vs {p.get('joueur_b','?')}",
                "Surface": p.get("surface", "?"),
                "IA a prédit": p.get("prediction_ia", "?"),
                "Résultat réel": p.get("resultat_reel", "?"),
                "Tournoi": p.get("tournoi", "?"),
            })
        st.dataframe(pd.DataFrame(rows_err), use_container_width=True, hide_index=True)
    else:
        st.success("Aucune erreur à analyser sur cette période !")

    # ── Export ──
    st.divider()
    st.subheader("📥 Export du bilan")
    if st.button("⬇️ Télécharger le bilan CSV"):
        df_export = pd.DataFrame([{
            "Période": f"{date_debut} → {date_fin}",
            "Total matchs": bilan["total"],
            "Corrects": bilan["corrects"],
            "Taux global (%)": round(taux_pct, 2),
        }])
        st.download_button(
            label="📄 Télécharger",
            data=df_export.to_csv(index=False).encode("utf-8"),
            file_name=f"bilan_ia_{date_fin.replace('/', '-')}.csv",
            mime="text/csv",
        )
