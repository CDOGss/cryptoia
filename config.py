"""Paramètres du bot CryptoIA — allocation crypto quotidienne en marche à blanc.

Principe : chaque jour, Gemini analyse un panier de cryptos majeures (momentum sur
24h/7j/30j + actualité fraîche) et DÉCIDE une allocation cible (quels actifs détenir,
en quelle proportion, ou rester en cash). C'est l'IA qui décide — pas une règle
mécanique. Le portefeuille virtuel est rééquilibré chaque jour vers cette cible.

Benchmarks : « buy & hold BTC » (la référence que tout trader crypto connaît) et un
panier équipondéré buy & hold (même univers, jamais retouché).

Marché légal en France (trading spot sur plateforme régulée AMF/PSAN — Binance,
Coinbase, Kraken…) : si l'expérience convainc, elle est transposable avec de l'argent
réel, contrairement aux marchés de prédiction.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Chemins -----------------------------------------------------------------
RACINE = Path(__file__).resolve().parent
FICHIER_PORTEFEUILLE = RACINE / "portfolio.json"
FICHIER_HISTORIQUE = RACINE / "history.json"
FICHIER_RAPPORT = RACINE / "daily_report.md"
FICHIER_GRAPHIQUE = RACINE / "performance_chart.png"

# --- Source de données : API CoinGecko (publique, gratuite, sans clé) --------
COINGECKO_API = "https://api.coingecko.com/api/v3"

# --- Univers : cryptos majeures, liquides (id CoinGecko : nom d'affichage) ----
UNIVERS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
    "binancecoin": "BNB",
    "ripple": "XRP",
    "cardano": "Cardano (ADA)",
    "avalanche-2": "Avalanche (AVAX)",
    "chainlink": "Chainlink (LINK)",
    "polkadot": "Polkadot (DOT)",
    "dogecoin": "Dogecoin (DOGE)",
}
ACTIF_BENCHMARK = "bitcoin"  # référence « buy & hold BTC »

# --- IA : Gemini (le DÉCIDEUR — il choisit l'allocation) -----------------------
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip() or None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Grounding Google Search : Gemini peut chercher l'actu crypto fraîche avant de
# décider. C'est l'avantage structurel de l'IA sur un momentum purement mécanique.
UTILISER_RECHERCHE = os.getenv("UTILISER_RECHERCHE", "1") == "1"

# --- Règles du portefeuille (marche à blanc) -----------------------------------
CAPITAL_INITIAL = 1000.0  # USD virtuels
# Frais simulés par ordre (achat ou vente), en % du montant traité — comparable à
# une plateforme régulée classique (Binance/Coinbase spot, hors promo).
FRAIS_PCT = float(os.getenv("FRAIS_PCT", "0.10"))
# Poids maximum autorisé sur un seul actif (garde-fou anti-concentration).
POIDS_MAX_ACTIF = float(os.getenv("POIDS_MAX_ACTIF", "0.40"))
# En-dessous de ce montant, un ajustement de position n'est pas exécuté (évite les
# micro-ordres qui ne font que payer des frais pour rien).
SEUIL_ORDRE_USD = 5.0
# --- Garde-fous anti-rotation (sept. 2026) ------------------------------------
# Bilan juil.→sept. : +25 % contre +47 % pour le panier buy & hold. Deux causes :
# un rééquilibrage quotidien (≈ 18× le capital échangé en 2 mois) et 25–30 % de
# cash gardé en plein marché haussier. D'où les règles ci-dessous.

# Socle : part du portefeuille investie en panier équipondéré (comme le benchmark),
# que l'IA ne peut pas toucher tant que la tendance de fond est haussière. L'IA ne
# pilote que le reste (le « satellite »), cash compris.
POIDS_SOCLE = float(os.getenv("POIDS_SOCLE", "0.70"))
# Filtre de tendance : BTC sous sa moyenne mobile 200 jours = marché baissier. Le
# socle est alors libéré et l'IA gère 100 % du portefeuille (cash autorisé).
JOURS_MOYENNE_TENDANCE = 200
# Rééquilibrage hebdomadaire : au plus un tous les 7 jours (un cron GitHub sauté
# est rattrapé au passage suivant), sauf changement de tendance (immédiat).
JOURS_ENTRE_REEQUILIBRAGES = 7
# On ne rééquilibre que si l'écart total à la cible dépasse ce seuil (somme des
# écarts absolus / 2 = part du portefeuille à échanger).
SEUIL_REEQUILIBRAGE_PTS = 0.10  # 10 points de pourcentage
# Écart minimal par actif pour passer un ordre, une fois le rééquilibrage décidé.
SEUIL_ORDRE_PTS = 0.01
