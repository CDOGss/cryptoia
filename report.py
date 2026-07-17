"""Rapport quotidien (markdown) + courbe de performance (PNG)."""
from __future__ import annotations

import datetime
import json

import config


def charger_historique() -> list[dict]:
    if config.FICHIER_HISTORIQUE.exists():
        return json.loads(config.FICHIER_HISTORIQUE.read_text(encoding="utf-8"))
    return []


def ajouter_snapshot(m: dict) -> list[dict]:
    """Un point d'historique par jour (idempotent : un seul par date)."""
    hist = charger_historique()
    hist = [h for h in hist if h["date"] != m["date"]]
    hist.append({
        "date": m["date"],
        "nav": m["nav"],
        "perf_totale_pct": m["perf_totale_pct"],
        "perf_btc_pct": m.get("buy_hold_btc", {}).get("perf_pct"),
        "perf_panier_pct": m.get("buy_hold_panier", {}).get("perf_pct"),
    })
    hist.sort(key=lambda h: h["date"])
    config.FICHIER_HISTORIQUE.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    return hist


def tracer_graphique(hist: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    if not hist:
        return
    dates = [h["date"] for h in hist]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, [h["perf_totale_pct"] for h in hist],
            color="#2563eb", linewidth=2.2, label="CryptoIA (décision Gemini)")
    if any(h.get("perf_btc_pct") is not None for h in hist):
        ax.plot(dates, [h.get("perf_btc_pct") for h in hist],
                color="#f59e0b", linewidth=1.6, linestyle="--", label="Buy & hold BTC")
    if any(h.get("perf_panier_pct") is not None for h in hist):
        ax.plot(dates, [h.get("perf_panier_pct") for h in hist],
                color="#9ca3af", linewidth=1.6, linestyle=":", label="Buy & hold panier")
    ax.axhline(0, color="#6b7280", linewidth=0.8)
    ax.set_title("CryptoIA — performance vs. buy & hold")
    ax.set_ylabel("Performance (%)")
    ax.legend(); ax.grid(alpha=0.3)
    n = max(1, len(dates) // 12)
    ax.set_xticks(dates[::n]); ax.tick_params(axis="x", rotation=45, labelsize=8)
    fig.tight_layout()
    fig.savefig(config.FICHIER_GRAPHIQUE, dpi=110)
    plt.close(fig)


def ecrire_rapport(m: dict, decision: dict | None, ordres: list[dict]) -> None:
    lignes = [f"# 🪙 CryptoIA — rapport du {m['date']}", ""]

    alpha = m.get("alpha_vs_btc_pts")
    verdict = "—"
    if alpha is not None:
        verdict = "✅ l'IA bat BTC en buy & hold" if alpha > 0 else "❌ BTC en buy & hold fait mieux"

    lignes += [
        "## Tableau de bord",
        f"- **NAV** : {m['nav']:,.2f} $ ({m['perf_totale_pct']:+.2f} % depuis le départ)",
        f"- **Cash** : {m['cash']:,.2f} $ | **Frais cumulés** : {m['frais_cumules']:,.2f} $",
    ]
    if "buy_hold_btc" in m:
        lignes.append(
            f"- **Buy & hold BTC** : {m['buy_hold_btc']['perf_pct']:+.2f} % "
            f"| **Buy & hold panier** : {m['buy_hold_panier']['perf_pct']:+.2f} %")
        lignes.append(f"- **Verdict** : {verdict} ({alpha:+.2f} points d'écart)")
    lignes.append("")

    if m["positions"]:
        lignes.append("## Allocation actuelle")
        for actif_id, p in sorted(m["positions"].items(), key=lambda kv: -kv[1]["poids_pct"]):
            lignes.append(f"- {p['nom']} : {p['poids_pct']:.1f} % ({p['valeur_usd']:,.2f} $)")
        cash_pct = 100 * m["cash"] / m["nav"] if m["nav"] else 0
        lignes.append(f"- Cash : {cash_pct:.1f} % ({m['cash']:,.2f} $)")
        lignes.append("")

    if decision:
        lignes += ["## Décision de l'IA aujourd'hui",
                   f"- **Régime perçu** : {decision['regime']}",
                   f"- **Commentaire** : {decision['commentaire']}", ""]

    if ordres:
        lignes.append("## Ordres exécutés (rééquilibrage)")
        for o in ordres:
            nom = config.UNIVERS.get(o["actif"], o["actif"])
            lignes.append(f"- {o['sens'].upper()} {nom} — {o['montant_usd']:,.2f} $ "
                          f"(frais {o['frais_usd']:.2f} $)")
        lignes.append("")
    else:
        lignes.append("*Aucun rééquilibrage aujourd'hui (écarts sous le seuil).*\n")

    lignes += ["---", "*Marche à blanc, aucun argent réel. Rien ici ne constitue un "
               "conseil d'investissement.*"]
    config.FICHIER_RAPPORT.write_text("\n".join(lignes), encoding="utf-8")
