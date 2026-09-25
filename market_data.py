"""Accès à l'API CoinGecko (publique, gratuite, sans authentification)."""
from __future__ import annotations

import requests

import config

_TIMEOUT = 30


def snapshot_marche() -> dict[str, dict]:
    """Renvoie, pour chaque actif de l'univers : prix courant (USD) et variations
    24h/7j/30j — ce qui sert à la fois de base au raisonnement de l'IA et au calcul
    du P&L quotidien."""
    ids = ",".join(config.UNIVERS)
    r = requests.get(
        f"{config.COINGECKO_API}/coins/markets",
        params={
            "vs_currency": "usd",
            "ids": ids,
            "price_change_percentage": "24h,7d,30d",
        },
        timeout=_TIMEOUT,
        headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    data = {}
    for c in r.json():
        data[c["id"]] = {
            "nom": config.UNIVERS.get(c["id"], c["id"]),
            "prix": float(c["current_price"]),
            "var_24h": c.get("price_change_percentage_24h_in_currency"),
            "var_7j": c.get("price_change_percentage_7d_in_currency"),
            "var_30j": c.get("price_change_percentage_30d_in_currency"),
        }
    manquants = set(config.UNIVERS) - set(data)
    if manquants:
        raise RuntimeError(f"Actifs absents de la réponse CoinGecko : {manquants}")
    return data


def tendance_btc(prix_actuel: float) -> dict | None:
    """Filtre de tendance : BTC au-dessus (haussier) ou sous (baissier) sa moyenne
    mobile 200 jours. None si l'historique est indisponible."""
    try:
        r = requests.get(
            f"{config.COINGECKO_API}/coins/{config.ACTIF_BENCHMARK}/market_chart",
            params={"vs_currency": "usd", "days": config.JOURS_MOYENNE_TENDANCE,
                    "interval": "daily"},
            timeout=_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        closes = [p[1] for p in r.json()["prices"]][-config.JOURS_MOYENNE_TENDANCE:]
    except Exception as e:  # noqa: BLE001 — pas de filtre plutôt qu'un plantage
        print(f"⚠️ Historique BTC indisponible : {e}")
        return None
    if len(closes) < config.JOURS_MOYENNE_TENDANCE * 0.9:
        return None
    mm = sum(closes) / len(closes)
    return {"haussiere": prix_actuel >= mm, "mm200": round(mm, 2),
            "ecart_pct": round(100 * (prix_actuel / mm - 1), 2)}
