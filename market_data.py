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
