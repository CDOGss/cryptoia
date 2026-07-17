"""Passage quotidien de CryptoIA.

1. Récupère les prix + momentum de l'univers (CoinGecko).
2. Amorce les benchmarks « buy & hold » au tout premier passage.
3. Fait décider Gemini de l'allocation cible du jour (analyse + actu fraîche).
4. Rééquilibre le portefeuille virtuel vers cette cible (avec frais simulés).
5. Écrit le portefeuille, l'historique, le rapport markdown et le graphique.
"""
from __future__ import annotations

import config
import decide
import engine
import market_data
import report


def executer_passage() -> None:
    print("→ Récupération des prix et du momentum (CoinGecko)…")
    marche = market_data.snapshot_marche()

    pf = engine.charger_portefeuille()
    engine.initialiser_benchmarks(pf, marche)

    print("→ Décision d'allocation (Gemini)…")
    decision = decide.decider_allocation(marche)
    ordres = []
    if decision is None:
        print("  ⚠️ Pas de décision IA aujourd'hui — portefeuille inchangé.")
    else:
        pf["derniere_decision"] = decision
        ordres = engine.rééquilibrer(pf, marche, decision)
        print(f"  {len(ordres)} ordre(s) exécuté(s).")

    engine.sauver_portefeuille(pf)

    m = engine.metriques(pf, marche)
    hist = report.ajouter_snapshot(m)
    report.tracer_graphique(hist)
    report.ecrire_rapport(m, decision, ordres)

    print("\n=== Résumé ===")
    print(f"NAV : {m['nav']:,.2f} $ ({m['perf_totale_pct']:+.2f} %)")
    if "buy_hold_btc" in m:
        print(f"Buy & hold BTC : {m['buy_hold_btc']['perf_pct']:+.2f} % "
              f"| écart : {m['alpha_vs_btc_pts']:+.2f} pts")
    print(f"Rapport : {config.FICHIER_RAPPORT.name}")


if __name__ == "__main__":
    executer_passage()
