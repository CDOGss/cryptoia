# 🪙 CryptoIA — l'IA contre le buy & hold

Expérience de **marche à blanc** (aucun argent réel) : chaque jour, une IA (Gemini)
analyse un panier de cryptos majeures et **décide** comment répartir un portefeuille
virtuel entre ces actifs et le cash. Le tout tourne automatiquement sur GitHub
Actions et publie un dashboard sur GitHub Pages.

## L'idée

Contrairement à une stratégie mécanique (momentum pur, rotation systématique),
c'est ici **l'IA qui décide vraiment** : elle reçoit le momentum de chaque actif
(24h / 7 jours / 30 jours), peut chercher l'actualité crypto fraîche (grounding
Google Search), et choisit une allocation — ou de rester en cash si rien ne la
convainc.

- **Le décideur, c'est l'IA.** Gemini analyse et alloue, chaque jour.
- **Le benchmark, c'est le marché.** Deux références « buy & hold » jamais
  retouchées : 100 % Bitcoin, et un panier équipondéré sur tout l'univers.
- **Le feedback est objectif et continu.** Le marché crypto est ouvert 24/7, les
  prix sont publics : on sait chaque jour qui a fait mieux.

**Différence avec les paris (Unibet, marchés de prédiction…)** : le trading crypto
spot est un **marché financier classique**, légal et accessible en France via des
plateformes régulées (Binance, Coinbase, Kraken — enregistrées PSAN auprès de
l'AMF). Si l'expérience s'avère concluante, elle est transposable avec de l'argent
réel — contrairement à un marché de prédiction type Polymarket, interdit en ligne
en France par l'ANJ.

## La stratégie

1. **Données** — chaque jour, récupération du prix et du momentum (24h/7j/30j) de
   10 cryptos majeures (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOT, DOGE) via
   l'API publique CoinGecko.
2. **Décision** — Gemini reçoit ce momentum et décide une allocation cible
   (poids par actif + cash), avec deux garde-fous : poids max 40 % par actif,
   diversification encouragée en cas d'incertitude.
3. **Rééquilibrage** — le portefeuille virtuel est ajusté vers cette cible, avec
   des frais simulés (0,10 % par ordre, comparable à une plateforme régulée), et
   un seuil pour éviter de repayer des frais sur des écarts négligeables.
4. **Comparaison** — chaque jour, on mesure la performance du portefeuille IA
   contre les deux benchmarks buy & hold.

- **Capital virtuel : 1 000 $.**
- **Benchmarks** : 100 % Bitcoin (buy & hold) et panier équipondéré (buy & hold).

## Architecture

```
main.py         Passage quotidien : données → décision IA → rééquilibrage → rapport
market_data.py  Accès API CoinGecko : prix + momentum 24h/7j/30j
decide.py       Le DÉCIDEUR : Gemini choisit l'allocation (+ Google Search)
engine.py       Portefeuille virtuel, rééquilibrage, frais, benchmarks, métriques
config.py       Paramètres (univers, frais, garde-fous, modèle)
report.py       Rapport markdown quotidien + courbe PNG
web/index.html  Dashboard autonome (lit portfolio.json / history.json)
portfolio.json  État : cash, positions, benchmarks, dernière décision IA
history.json    Un snapshot par jour (NAV, perf IA vs BTC vs panier)
```

## Installation

1. **Dépôt GitHub** (public pour GitHub Pages gratuit), pousser ce code.
2. **Secret API** : *Settings → Secrets and variables → Actions* → créer
   `GEMINI_API_KEY` (clé [Google AI Studio](https://aistudio.google.com/apikey)).
3. **GitHub Pages** : *Settings → Pages* → source **GitHub Actions**.
4. Premier lancement : onglet *Actions* → workflow **Bot CryptoIA** → *Run workflow*.
   Le dashboard sera à l'adresse `…github.io/<dépôt>/`.

### En local

```bash
pip install -r requirements.txt
cp .env.example .env          # puis renseigner GEMINI_API_KEY
export GEMINI_API_KEY=...      # PowerShell : $env:GEMINI_API_KEY="..."

python main.py                # un passage (décide et rééquilibre)

# Prévisualiser le dashboard
python -m http.server 8000    # puis http://localhost:8000/web/
```

## Garde-fous

- **Idempotence de rééquilibrage** : un écart sous 3 points de pourcentage n'est
  pas retouché (évite de payer des frais pour rien).
- **IA robuste** : toute erreur Gemini est non bloquante — le portefeuille reste
  simplement inchangé ce jour-là.
- **Diversification forcée** : poids plafonné à 40 % par actif, quelle que soit la
  décision de l'IA.
- **Univers hallucination-proof** : tout identifiant renvoyé par l'IA hors de
  l'univers configuré est silencieusement ignoré.

---

*Projet pédagogique de suivi en marche à blanc. Rien ici ne constitue un conseil
d'investissement. Les cryptomonnaies sont des actifs très volatils.*
