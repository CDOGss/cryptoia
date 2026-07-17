"""Cœur de la marche à blanc : portefeuille virtuel, rééquilibrage vers l'allocation
décidée par l'IA, valorisation quotidienne et calcul des métriques (P&L, ROI, vs
benchmarks « buy & hold »).
"""
from __future__ import annotations

import datetime
import json

import config


# --- État du portefeuille -----------------------------------------------------

def charger_portefeuille() -> dict:
    if config.FICHIER_PORTEFEUILLE.exists():
        return json.loads(config.FICHIER_PORTEFEUILLE.read_text(encoding="utf-8"))
    return {
        "capital_initial": config.CAPITAL_INITIAL,
        "cash": config.CAPITAL_INITIAL,
        "positions": {},        # {actif_id: {"parts": float}}
        "frais_cumules": 0.0,
        "benchmarks": {},       # {actif_id: {"parts_initiales": float}} — buy & hold, jamais retouché
        "derniere_decision": None,
    }


def sauver_portefeuille(pf: dict) -> None:
    config.FICHIER_PORTEFEUILLE.write_text(
        json.dumps(pf, ensure_ascii=False, indent=2), encoding="utf-8")


# --- Valorisation ---------------------------------------------------------------

def valeur_positions(pf: dict, marche: dict[str, dict]) -> float:
    return sum(pos["parts"] * marche[actif_id]["prix"]
               for actif_id, pos in pf["positions"].items() if actif_id in marche)


def nav(pf: dict, marche: dict[str, dict]) -> float:
    return pf["cash"] + valeur_positions(pf, marche)


def initialiser_benchmarks(pf: dict, marche: dict[str, dict]) -> None:
    """Amorce, au tout premier passage, un panier « buy & hold » équipondéré sur
    tout l'univers, et un « buy & hold BTC seul » — jamais retouchés ensuite."""
    if pf["benchmarks"]:
        return
    part_btc = config.CAPITAL_INITIAL / marche[config.ACTIF_BENCHMARK]["prix"]
    pf["benchmarks"]["buy_hold_btc"] = {"parts": {config.ACTIF_BENCHMARK: part_btc}}

    montant_par_actif = config.CAPITAL_INITIAL / len(config.UNIVERS)
    parts_panier = {actif_id: montant_par_actif / marche[actif_id]["prix"]
                     for actif_id in config.UNIVERS}
    pf["benchmarks"]["buy_hold_panier"] = {"parts": parts_panier}


def valeur_benchmark(pf: dict, marche: dict[str, dict], nom: str) -> float:
    parts = pf["benchmarks"][nom]["parts"]
    return sum(p * marche[actif_id]["prix"] for actif_id, p in parts.items()
               if actif_id in marche)


# --- Rééquilibrage vers la cible décidée par l'IA -------------------------------

def rééquilibrer(pf: dict, marche: dict[str, dict], decision: dict) -> list[dict]:
    """Ajuste les positions vers l'allocation cible. Renvoie la liste des ordres
    exécutés (pour le rapport). Applique des frais simulés sur chaque ordre."""
    valeur_totale = nav(pf, marche)
    cibles_usd = {actif_id: poids * valeur_totale
                  for actif_id, poids in decision["allocations"].items()}

    ordres = []
    for actif_id in set(pf["positions"]) | set(cibles_usd):
        prix = marche.get(actif_id, {}).get("prix")
        if prix is None:
            continue
        valeur_actuelle = pf["positions"].get(actif_id, {}).get("parts", 0.0) * prix
        valeur_cible = cibles_usd.get(actif_id, 0.0)
        ecart_pts = abs(valeur_cible - valeur_actuelle) / valeur_totale if valeur_totale else 0
        if ecart_pts < config.SEUIL_REEQUILIBRAGE_PTS:
            continue
        delta_usd = valeur_cible - valeur_actuelle
        if abs(delta_usd) < config.SEUIL_ORDRE_USD:
            continue

        frais = abs(delta_usd) * config.FRAIS_PCT / 100
        sens = "achat" if delta_usd > 0 else "vente"

        if sens == "achat":
            montant_net = delta_usd - frais  # les frais réduisent ce qu'on achète réellement
            if montant_net <= 0:
                continue
            parts_delta = montant_net / prix
            pf["cash"] -= delta_usd  # on paie le montant brut, frais inclus dans le coût
        else:
            montant_brut = -delta_usd
            parts_delta = -(montant_brut / prix)
            pf["cash"] += montant_brut - frais

        pf["positions"].setdefault(actif_id, {"parts": 0.0})
        pf["positions"][actif_id]["parts"] += parts_delta
        if abs(pf["positions"][actif_id]["parts"]) < 1e-12:
            del pf["positions"][actif_id]
        pf["frais_cumules"] = round(pf["frais_cumules"] + frais, 4)

        ordres.append({
            "actif": actif_id, "sens": sens, "montant_usd": round(abs(delta_usd), 2),
            "frais_usd": round(frais, 4),
        })
    return ordres


# --- Métriques ----------------------------------------------------------------

def metriques(pf: dict, marche: dict[str, dict]) -> dict:
    valeur = nav(pf, marche)
    perf = (valeur / pf["capital_initial"] - 1) * 100

    m = {
        "date": datetime.date.today().isoformat(),
        "nav": round(valeur, 2),
        "cash": round(pf["cash"], 2),
        "perf_totale_pct": round(perf, 2),
        "frais_cumules": round(pf["frais_cumules"], 2),
        "positions": {
            actif_id: {
                "nom": config.UNIVERS.get(actif_id, actif_id),
                "poids_pct": round(100 * pos["parts"] * marche[actif_id]["prix"] / valeur, 1)
                if valeur and actif_id in marche else 0.0,
                "valeur_usd": round(pos["parts"] * marche[actif_id]["prix"], 2)
                if actif_id in marche else 0.0,
            }
            for actif_id, pos in pf["positions"].items()
        },
    }
    for nom_bench in pf.get("benchmarks", {}):
        v_bench = valeur_benchmark(pf, marche, nom_bench)
        m[nom_bench] = {
            "valeur": round(v_bench, 2),
            "perf_pct": round((v_bench / pf["capital_initial"] - 1) * 100, 2),
        }
    if "buy_hold_btc" in m:
        m["alpha_vs_btc_pts"] = round(m["perf_totale_pct"] - m["buy_hold_btc"]["perf_pct"], 2)
    return m
