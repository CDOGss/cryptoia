"""Passage quotidien de CryptoIA.

1. Récupère les prix + momentum de l'univers (CoinGecko).
2. Amorce les benchmarks « buy & hold » au tout premier passage.
3. Filtre de tendance : BTC vs sa moyenne 200 jours.
4. Une fois par semaine (ou si la tendance change) : Gemini décide l'allocation de
   sa part (30 % en tendance haussière, 100 % en baissière), le reste est un socle
   équipondéré ; rééquilibrage si l'écart total à la cible dépasse 10 points.
5. Écrit le portefeuille, l'historique, le rapport markdown et le graphique.
"""
from __future__ import annotations

import datetime

import config
import decide
import engine
import market_data
import report


REGLES = "socle-v1"  # version des règles de gestion (sept. 2026)


def executer_passage() -> None:
    print("→ Récupération des prix et du momentum (CoinGecko)…")
    marche = market_data.snapshot_marche()

    pf = engine.charger_portefeuille()
    engine.initialiser_benchmarks(pf, marche)
    aujourd_hui = datetime.date.today()

    # Filtre de tendance (BTC vs moyenne 200 j). Indisponible → dernière connue.
    tendance = market_data.tendance_btc(marche[config.ACTIF_BENCHMARK]["prix"])
    precedente = pf.get("tendance_haussiere")
    haussiere = tendance["haussiere"] if tendance else (precedente is not False)
    poids_socle = config.POIDS_SOCLE if haussiere else 0.0
    changement = precedente is not None and precedente != haussiere
    pf["tendance_haussiere"] = haussiere
    pf["tendance"] = tendance
    print(f"  Tendance {'haussière' if haussiere else 'BAISSIÈRE'} "
          f"→ socle {poids_socle:.0%}, IA {1 - poids_socle:.0%}")

    dernier = pf.get("dernier_reequilibrage")
    jours = (aujourd_hui - datetime.date.fromisoformat(dernier)).days if dernier else 999
    nouvelles_regles = pf.get("regles") != REGLES
    a_faire = jours >= config.JOURS_ENTRE_REEQUILIBRAGES or changement or nouvelles_regles

    decision, ordres = None, []
    contexte = [f"**Tendance de fond** : {'haussière' if haussiere else 'baissière'}"
                + (f" (BTC {tendance['ecart_pct']:+.1f} % vs moyenne 200 j)" if tendance else "")
                + f" — socle {poids_socle:.0%} / IA {1 - poids_socle:.0%}"]
    if not a_faire:
        prochain = datetime.date.fromisoformat(dernier) + datetime.timedelta(
            days=config.JOURS_ENTRE_REEQUILIBRAGES)
        print(f"  Pas de rééquilibrage aujourd'hui (prochain le {prochain}).")
        contexte.append(f"**Prochain rééquilibrage** : {prochain} (hebdomadaire)")
    else:
        print("→ Décision d'allocation (Gemini)…")
        decision = decide.decider_allocation(marche, 1 - poids_socle, tendance)
        if decision is None:
            print("  ⚠️ Pas de décision IA : la part IA reprend la dernière décision connue.")
        else:
            pf["derniere_decision"] = decision
        cible = engine.cible_finale(decision or pf.get("derniere_decision"), poids_socle)
        ecart = engine.ecart_total(pf, marche, cible)
        if ecart >= config.SEUIL_REEQUILIBRAGE_PTS:
            ordres = engine.rééquilibrer(pf, marche, cible)
            print(f"  Écart {ecart:.0%} → {len(ordres)} ordre(s) exécuté(s).")
        else:
            print(f"  Écart {ecart:.0%} sous le seuil de "
                  f"{config.SEUIL_REEQUILIBRAGE_PTS:.0%} : aucun ordre.")
        contexte.append(f"**Écart à la cible** : {ecart:.0%} (seuil "
                        f"{config.SEUIL_REEQUILIBRAGE_PTS:.0%})")
        pf["dernier_reequilibrage"] = aujourd_hui.isoformat()
        pf["regles"] = REGLES

    engine.sauver_portefeuille(pf)

    m = engine.metriques(pf, marche)
    hist = report.ajouter_snapshot(m)
    report.tracer_graphique(hist)
    report.ecrire_rapport(m, decision, ordres, contexte)

    print("\n=== Résumé ===")
    print(f"NAV : {m['nav']:,.2f} $ ({m['perf_totale_pct']:+.2f} %)")
    if "buy_hold_btc" in m:
        print(f"Buy & hold BTC : {m['buy_hold_btc']['perf_pct']:+.2f} % "
              f"| écart : {m['alpha_vs_btc_pts']:+.2f} pts")
    print(f"Rapport : {config.FICHIER_RAPPORT.name}")


if __name__ == "__main__":
    executer_passage()
