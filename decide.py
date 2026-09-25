"""Le DÉCIDEUR : Gemini choisit l'allocation crypto du jour.

Contrairement à une stratégie mécanique (momentum pur, rotation systématique), c'est
ici l'IA qui décide vraiment : elle reçoit le momentum de chaque actif (24h/7j/30j)
et peut chercher l'actualité fraîche (grounding Google Search) avant de répartir le
portefeuille entre les actifs de l'univers et le cash.
"""
from __future__ import annotations

import datetime
import json
import re

import config

_SYSTEME = """Tu es un gérant de portefeuille crypto discipliné et prudent. Chaque
semaine, tu répartis un portefeuille virtuel entre un panier de cryptos majeures et le
cash (USD), pour la semaine à venir.

Règles :
- Tu peux allouer de 0 % à 100 % du portefeuille par actif, le reste en cash.
- Reste diversifié : le poids d'un seul actif ne doit jamais dépasser 40 %.
- Sois prudent en cas d'incertitude ou de signal contradictoire : garder du cash est
  une décision valable, pas un aveu d'échec.
- Cherche l'actualité crypto récente pertinente si utile (macro, régulation,
  actualité propre à un projet), mais ne base pas toute la décision dessus — le
  momentum de prix (24h/7j/30j) reste le socle de l'analyse.
- Réponds en français.

Termine IMPÉRATIVEMENT ta réponse par un objet JSON sur une seule ligne, au format :
{"allocations": {"bitcoin": 0.30, "ethereum": 0.20}, "cash": 0.50,
 "regime": "risk_on"|"neutre"|"risk_off",
 "commentaire": "2-4 phrases expliquant la logique du jour"}
Les clés d'« allocations » doivent être des identifiants CoinGecko (ex. "bitcoin",
"ethereum", "solana"...), la somme des poids + cash doit faire environ 1.0."""


def _extraire_json(texte: str) -> dict | None:
    """Le JSON de décision peut être multi-ligne (objet allocations imbriqué) : on
    cherche le dernier bloc équilibré contenant la clé "allocations"."""
    profondeur = 0
    debut = None
    for i, ch in enumerate(texte):
        if ch == "{":
            if profondeur == 0:
                debut = i
            profondeur += 1
        elif ch == "}":
            profondeur -= 1
            if profondeur == 0 and debut is not None:
                bloc = texte[debut:i + 1]
                try:
                    d = json.loads(bloc)
                except json.JSONDecodeError:
                    continue
                if "allocations" in d:
                    return d
    return None


def decider_allocation(marche: dict[str, dict], part_ia: float = 1.0,
                       tendance: dict | None = None) -> dict | None:
    """Renvoie {allocations: {id: poids}, cash, regime, commentaire} ou None si
    l'IA est indisponible. Les poids portent sur la part pilotée par l'IA
    (`part_ia` du portefeuille), pas sur le portefeuille entier."""
    if not config.GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY absente : impossible de décider.")
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("⚠️ Paquet google-genai absent.")
        return None

    lignes = "\n".join(
        f"- {infos['nom']} ({actif_id}) : {infos['prix']:,.4g} $ "
        f"| 24h {infos['var_24h']:+.1f}% | 7j {infos['var_7j']:+.1f}% | 30j {infos['var_30j']:+.1f}%"
        for actif_id, infos in marche.items()
    )
    if tendance:
        txt_tendance = (f"Bitcoin est {'AU-DESSUS' if tendance['haussiere'] else 'SOUS'} sa "
                        f"moyenne mobile 200 jours ({tendance['ecart_pct']:+.1f} %) : tendance "
                        f"de fond {'HAUSSIÈRE' if tendance['haussiere'] else 'BAISSIÈRE'}.")
    else:
        txt_tendance = "Tendance de fond indisponible aujourd'hui."
    if part_ia < 1.0:
        txt_part = (f"Tu pilotes {part_ia:.0%} du portefeuille ; le reste est un socle investi "
                    "à parts égales sur tout l'univers, que tu ne contrôles pas. Tes poids "
                    "portent sur TA part uniquement (100 % = toute ta part). En tendance "
                    "haussière, rester en cash coûte cher : ne le fais que sur un signal net.")
    else:
        txt_part = ("Tendance baissière : tu pilotes 100 % du portefeuille et le cash est "
                    "ta protection principale.")
    prompt = f"""DATE DU JOUR : {datetime.date.today().isoformat()}

TENDANCE DE FOND : {txt_tendance}
TON PÉRIMÈTRE : {txt_part}
Le portefeuille n'est rééquilibré qu'une fois par semaine : raisonne à cet horizon.

UNIVERS ET MOMENTUM DU JOUR :
{lignes}

Décide de l'allocation du portefeuille pour aujourd'hui. Termine par le JSON demandé."""

    cfg = {}
    if config.UTILISER_RECHERCHE:
        cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    else:
        cfg["response_mime_type"] = "application/json"

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        reponse = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=f"{_SYSTEME}\n\n{prompt}",
            config=types.GenerateContentConfig(**cfg),
        )
        data = _extraire_json(reponse.text or "")
        if not data:
            print("⚠️ Réponse IA non exploitable (pas de JSON d'allocations).")
            return None

        allocations = {}
        for actif_id, poids in (data.get("allocations") or {}).items():
            if actif_id not in config.UNIVERS:
                continue  # l'IA a halluciné un identifiant hors univers : on ignore
            try:
                p = max(0.0, min(config.POIDS_MAX_ACTIF, float(poids)))
            except (TypeError, ValueError):
                continue
            if p > 0:
                allocations[actif_id] = p

        total = sum(allocations.values())
        if total > 1.0:  # normalisation défensive si l'IA dépasse 100 %
            allocations = {k: v / total for k, v in allocations.items()}
            total = 1.0

        return {
            "allocations": allocations,
            "cash": round(1.0 - total, 4),
            "regime": str(data.get("regime", "neutre")),
            "commentaire": str(data.get("commentaire", ""))[:600],
        }
    except Exception as e:  # noqa: BLE001 — l'IA ne doit jamais faire planter le passage
        print(f"⚠️ Décision Gemini indisponible : {e}")
        return None
