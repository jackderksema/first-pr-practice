# Edge Lab

Onderzoek voor een crypto-tradingplan met €10.000 startkapitaal. Alle markten zijn synthetisch; er is geen live data gebruikt.

| Bestand | Wat het doet |
|---|---|
| `research.py` | Overfitting-studie (2 × 610.000 backtests) en Monte Carlo voor funding-arbitrage |
| `sens.py` | Gevoeligheid van funding-arb voor funding-niveau en staartrisico |
| `protocol.py` | Meet hoeveel nep-winnaars door het testprotocol komen (validatie + forward-poort) |
| `*.json` | Uitkomsten van de runs |
| `edge-lab.src.html` | Bron van de pagina; `__DATA__` wordt vervangen door `pagedata.json` |

Draaien: `pip install numpy`, daarna `python3 sens.py` en `python3 protocol.py`.
`research.py` leest de overfitting-resultaten uit `research.json` en draait alleen de funding-sweep opnieuw.

Belangrijkste uitkomst: van 800 markten zonder bruikbare edge kwamen 0 nep-winnaars door beide poorten.

## Echte data (1954–2026)

| Bestand | Wat het doet |
|---|---|
| `multi.py` | 15 vooraf vastgelegde strategieën op echte koersen (aandelen, obligaties, goud, olie, crypto); test t/m 1999 en daarna |
| `portfolio.py` | Portefeuille die alleen op data t/m 1999 is gekozen, getest op 2000–2026, plus bootstrap over 10 jaar |

Data komt van `raw.githubusercontent.com/datasets/*` en `coinmetrics/data`. Download de CSV's naar `data/` zoals in de scripts staat.
