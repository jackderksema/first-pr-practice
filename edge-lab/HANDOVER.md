# Overdracht Edge Lab → hub / 0103

Plak dit bestand in een sessie op de Mac mini (of laat de hub `git pull` doen op branch
`claude/market-movement-capital-pbojiq` van `jackderksema/first-pr-practice`). Alles wat nodig is
staat in deze map; niets hoeft opnieuw uitgelegd te worden.

## Opdracht voor de volgende sessie

1. Lees deze map: `README.md`, de scripts en de `*.json`-resultaten.
2. Bekijk hoe de hub/0103-code in elkaar zit en zet dit onderzoek daarin volgens die conventies
   (mappen, taken voor de voormannen, logging).
3. Probeer de conclusies te **weerleggen** voordat je ze verbetert. Zie "Open aanvallen" hieronder.
4. Voeg data toe die hier niet bereikbaar was: live beurs-API's (Hyperliquid, Binance, Bybit, OKX),
   Europese ETF-koersen in euro's, dagelijkse S&P-data, echte T-bill-rente.
5. Verander geen vastgelegde strategieregel om een test te laten slagen. Nieuwe regels tellen mee als
   extra pogingen (N omhoog in de DSR).
6. Geen echt geld, geen orders. Alleen onderzoek en paper trading.

## Wie is de gebruiker en wat is het doel

- Jack. Heeft eerder geld verdiend met pool-arbitrage, kleine coins en DeFi.
- Doel: met €10.000 starten, gespreid over markten (aandelen, goud, crypto, maakt niet uit).
- Beslissingen moeten op feiten en metingen rusten, niet op gevoel. Alles moet kritisch getoetst worden.
- Grens die in dit gesprek is getrokken: geen rug pulls, pump-and-dumps, ponzi's of misleidende
  promotie. Wel legale strategieën.

## Wat is vastgesteld

### Synthetische tests (`research.py`, `protocol.py`, `sens.py`)
- Blind zoeken naar een strategie in een toevalsmarkt: beste van 1.525 → backtest +€13.059, daarna
  −€2.409 (mediaan, 200 markten). 35,5% bleef positief.
- Testprotocol (keuze op train, 1 validatietest, 1 forward-test, beide PSR > 95%): 0 van 800
  nep-winnaars kwamen erdoor. Kosten: een echte Sharpe van 2 haalt één poort van ½ jaar maar 42%.
- Funding-arbitrage (model, geen echte data): verwacht −€103 tot +€590 per jaar op 10k bij 5–25%
  funding, inclusief staartrisico. Uitkomst hangt vooral af van funding-niveau en beursrisico.

### Echte data 1954–2026 (`multi.py`, `portfolio.py`)
15 vooraf vastgelegde strategieën. Portefeuille gekozen met alleen data t/m 1999 (in-sample DSR ≥ 90%,
gelijk gewogen): S&P kopen en houden, 60/40, S&P trend 10m, dual momentum, S&P vol-doel (VIX),
CAPE-timing.

| 2000–2026 | Portefeuille | S&P 500 |
|---|---|---|
| Rendement/jr (USD) | 9,2% | 8,4% |
| Grootste daling | −24% | −49% |
| €10k → | €102.865 | €83.628 |
| In euro's: rendement / daling | 8,6% / −33% | 7,8% / −60% |

### Weerlegging (`robust.py`)
- **Trendlengte**: S&P-trend werkt met 4 t/m 18 maanden (OOS Sharpe 0,91–1,17); goud-trend ook
  (0,85–0,95). Geen toevalstreffer van precies "10".
- **Splitdatum**: bij keuze t/m 1979 of t/m 2009 had de S&P 500 zelf **meer rendement** (12,3% vs 10,5%;
  14,4% vs 10,5%). Het voordeel van de portefeuille is **lager risico**, niet hoger rendement.
- **Kosten ×5**: 8,5%/jr, Sharpe 1,03. **1 maand vertraging**: 7,9%/jr, Sharpe 0,93. Beide samen: 7,2%.
- **Rollende 10-jaarsvensters (620)**: betere Sharpe dan S&P in 100%, hoger rendement in 60%,
  slechtste achterstand −4,1%/jr.
- **Gepaarde bootstrap**: kans dat Sharpe portefeuille > S&P in 2000–2026 ≈ 100%.

## Open aanvallen (nog niet gedaan)

- Shiller-S&P is een maandgemiddelde, geen slotkoers → mogelijk flatteuze trendsignalen. Herhaal met
  dagelijkse slotkoersen.
- Obligatierendement is benaderd uit de rente (duratie 8), cash als 10j-rente −1,5%.
- Olie is spotprijs (niet verhandelbaar). Crypto-data loopt tot mei 2026.
- Belasting (box 3), ETF-kosten (TER), spreads in euro's niet meegenomen.
- Goud en Bitcoin werden vóór 2000 (crypto: 2019) niet gekozen; ze toevoegen is kennis achteraf.
- Resultaten van de onafhankelijke code-review staan in `REVIEW.md` (als aanwezig).

## Pagina

Interactief dossier: https://claude.ai/artifact/AXvQcmYK3dt8ag4UjJoqWM (privé, eigenaar Jack).
Bron: `edge-lab.src.html` + `pagedata.json` (vervang `__DATA__`).

## Data opnieuw ophalen

```bash
mkdir -p data && cd data && B=https://raw.githubusercontent.com
curl -sSo spx.csv  $B/datasets/s-and-p-500/main/data/data.csv
curl -sSo gold.csv $B/datasets/gold-prices/main/data/monthly.csv
curl -sSo y10.csv  $B/datasets/bond-yields-us-10y/main/data/monthly.csv
curl -sSo brent.csv $B/datasets/oil-prices/main/data/brent-daily.csv
curl -sSo vix.csv  $B/datasets/finance-vix/main/data/vix-daily.csv
curl -sSo fx.csv   $B/datasets/exchange-rates/main/data/daily.csv
for c in btc eth sol; do curl -sSo $c.csv $B/coinmetrics/data/master/csv/$c.csv; done
cd .. && pip install numpy pandas && python3 multi.py && python3 portfolio.py && python3 robust.py
```
