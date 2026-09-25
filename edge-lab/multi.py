"""Multi-markt onderzoek op echte historische data.
Alle regels liggen VOORAF vast (uit literatuur), er wordt niet geoptimaliseerd.
In-sample = tot en met 1999 (crypto: t/m 2019). Out-of-sample = daarna.
Alles maandelijks, in USD."""
import json, numpy as np, pandas as pd
from math import erf, sqrt, e
D = "data/"
Phi = lambda x: 0.5 * (1 + erf(x / sqrt(2)))
COST = 0.001            # 0,1% per omzet (traditioneel)
COST_C = 0.002          # 0,2% per omzet (crypto)


def month_end(s):
    return s.resample("ME").last()

# ---------- data ----------
spx = pd.read_csv(D + "spx.csv", parse_dates=["Date"]).set_index("Date")
spx.index = spx.index + pd.offsets.MonthEnd(0)
dy = (spx.Dividend / spx.SP500).replace(0, np.nan).ffill()     # dividendrendement, na 2023 doorgetrokken
spx_tr = (spx.SP500.pct_change() + dy.shift(1) / 12)
cape = spx.PE10.replace(0, np.nan)

gold = pd.read_csv(D + "gold.csv")
gold.index = pd.to_datetime(gold.Date) + pd.offsets.MonthEnd(0)
gold_r = gold.Price.pct_change()

y = pd.read_csv(D + "y10.csv", parse_dates=["Date"]).set_index("Date").Rate / 100
y.index = y.index + pd.offsets.MonthEnd(0)
bond_r = y.shift(1) / 12 - 8.0 * (y - y.shift(1))                # duratie ~8
cash_r = (y.shift(1) - 0.015).clip(lower=0) / 12                   # proxy T-bill: 10j − 1,5%

brent = month_end(pd.read_csv(D + "brent.csv", parse_dates=["Date"]).set_index("Date").Price)
vix = month_end(pd.read_csv(D + "vix.csv", parse_dates=["DATE"]).set_index("DATE").CLOSE)

def crypto(c):
    d = pd.read_csv(D + f"{c}.csv", parse_dates=["time"], low_memory=False).set_index("time")
    p = d["PriceUSD"] if "PriceUSD" in d else d["ReferenceRateUSD"]
    if "ReferenceRateUSD" in d: p = p.fillna(d["ReferenceRateUSD"])
    return p.dropna()
btc_d, eth_d = crypto("btc"), crypto("eth")

fx = pd.read_csv(D + "fx.csv", parse_dates=["Date"])
eurusd = month_end(fx[fx.Country == "Euro"].set_index("Date")["Exchange rate"])  # EUR per USD

idx = pd.date_range("1954-01-31", "2026-08-31", freq="ME")
R = pd.DataFrame(index=idx)
R["spx"], R["bond"], R["gold"], R["cash"] = spx_tr, bond_r, gold_r, cash_r
R["cash"] = R["cash"].ffill()

# ---------- strategieën (vaste regels) ----------
def with_cost(w, rets, cost=COST):
    """w: gewichten (DataFrame) bepaald op einde maand t-1, rets: rendementen maand t."""
    w = w.shift(1)
    turn = w.diff().abs().sum(axis=1).fillna(0)
    return (w * rets).sum(axis=1, min_count=1) - turn * cost

def sma_signal(price, n):
    return (price > price.rolling(n).mean()).astype(float)

S = {}
px_spx = (1 + R.spx.fillna(0)).cumprod()
px_gold = (1 + R.gold.fillna(0)).cumprod()
px_bond = (1 + R.bond.fillna(0)).cumprod()

S["S&P 500 kopen en houden"] = R.spx
S["Staatsobligaties 10j"] = R.bond
S["Goud kopen en houden"] = R.gold
S["60/40 aandelen/obligaties"] = with_cost(pd.DataFrame({"spx": .6, "bond": .4}, index=idx), R[["spx", "bond"]])
S["Permanent portfolio (4×25%)"] = with_cost(pd.DataFrame({"spx": .25, "bond": .25, "gold": .25, "cash": .25}, index=idx), R[["spx", "bond", "gold", "cash"]])

sig = sma_signal(spx.SP500.reindex(idx), 10)
S["S&P trend (10-maands gem.)"] = with_cost(pd.DataFrame({"spx": sig, "cash": 1 - sig}), R[["spx", "cash"]])
sig = sma_signal(gold.Price.reindex(idx), 10)
S["Goud trend (10-maands gem.)"] = with_cost(pd.DataFrame({"gold": sig, "cash": 1 - sig}), R[["gold", "cash"]])

# dual momentum: beste 12m-rendement van spx/bond/gold, als dat boven cash ligt
mom = pd.DataFrame({k: (1 + R[k]).rolling(12).apply(np.prod, raw=True) - 1 for k in ["spx", "bond", "gold", "cash"]})
_m = mom[["spx", "bond", "gold"]]
best = _m.dropna(how="all").idxmax(axis=1).reindex(idx)
w = pd.DataFrame(0.0, index=idx, columns=["spx", "bond", "gold", "cash"])
for t in idx:
    b = best.get(t)
    if isinstance(b, str) and mom.loc[t, b] > mom.loc[t, "cash"]: w.loc[t, b] = 1
    elif isinstance(b, str): w.loc[t, "cash"] = 1
S["Dual momentum (aandelen/oblig./goud)"] = with_cost(w, R[["spx", "bond", "gold", "cash"]])

vol = R[["spx", "bond", "gold"]].rolling(12).std()
iv = (1 / vol).div((1 / vol).sum(axis=1), axis=0)
S["Risicopariteit (aandelen/oblig./goud)"] = with_cost(iv, R[["spx", "bond", "gold"]])

ex = (20 / vix.reindex(idx)).clip(upper=1.5)                        # doel: VIX 20 = 100%
S["S&P volatiliteitsdoel (VIX)"] = with_cost(pd.DataFrame({"spx": ex, "cash": 1 - ex}), R[["spx", "cash"]])

cape_m = cape.reindex(idx)
cheap = (cape_m < cape_m.expanding(120).median()).astype(float)
wc = 0.5 + 0.5 * cheap
S["S&P waarde-timing (CAPE)"] = with_cost(pd.DataFrame({"spx": wc, "cash": 1 - wc}), R[["spx", "cash"]])

R["oil"] = brent.pct_change().reindex(idx)
sig = sma_signal(brent.reindex(idx), 10)
S["Olie trend (10-maands gem., spot)"] = with_cost(pd.DataFrame({"oil": sig, "cash": 1 - sig}), R[["oil", "cash"]])

# crypto: dagelijks signaal (200 dagen), maandelijks rendement
def crypto_trend(p):
    sig_d = (p > p.rolling(200).mean()).astype(float)
    sig_m = sig_d.resample("ME").last().reindex(idx)
    r = p.resample("ME").last().pct_change().reindex(idx)
    return r, sig_m
R["btc"], sb = crypto_trend(btc_d)
R["eth"], se = crypto_trend(eth_d)
S["Bitcoin kopen en houden"] = R.btc
S["Bitcoin trend (200 dagen)"] = with_cost(pd.DataFrame({"btc": sb, "cash": 1 - sb}), R[["btc", "cash"]], COST_C)
S["Ethereum trend (200 dagen)"] = with_cost(pd.DataFrame({"eth": se, "cash": 1 - se}), R[["eth", "cash"]], COST_C)

# strategie bestaat pas als de onderliggende markt bestaat
for k, u in [("Olie trend (10-maands gem., spot)", "oil"), ("Bitcoin trend (200 dagen)", "btc"), ("Ethereum trend (200 dagen)", "eth"), ("S&P volatiliteitsdoel (VIX)", "spx")]:
    base = R[u] if u != "spx" else vix.reindex(idx)
    S[k] = S[k].where(base.notna())
N_TESTED = len(S)
g = 0.5772156649


def normInv(p):
    from statistics import NormalDist
    return NormalDist().inv_cdf(p)


def stats(r, cash):
    r = r.dropna(); c = cash.reindex(r.index).fillna(0)
    if len(r) < 24: return None
    ex = r - c
    yrs = len(r) / 12
    cagr = (1 + r).prod() ** (1 / yrs) - 1
    vol = r.std() * sqrt(12)
    sr = ex.mean() / ex.std() * sqrt(12)
    eq = (1 + r).cumprod(); dd = (eq / eq.cummax() - 1).min()
    emax = (1 / sqrt(yrs)) * ((1 - g) * normInv(1 - 1 / N_TESTED) + g * normInv(1 - 1 / (N_TESTED * e)))
    return dict(start=str(r.index[0].date())[:7], end=str(r.index[-1].date())[:7], yrs=round(yrs, 1),
                cagr=cagr, vol=vol, sharpe=sr, maxdd=dd,
                psr0=Phi(sr * sqrt(yrs)), dsr=Phi((sr - emax) * sqrt(yrs)))


def split(name, r):
    crypto_ = any(k in name for k in ["itcoin", "thereum"])
    cut = "2019-12-31" if crypto_ else "1999-12-31"
    return stats(r[:cut], R.cash), stats(r[cut:].iloc[1:], R.cash), stats(r, R.cash)

rows = {}
for k, r in S.items():
    ins, oos, full = split(k, r)
    rows[k] = dict(ins=ins, oos=oos, full=full)

# correlaties (maandrendement, overlappende periode 2015-2026 voor alles)
C = pd.DataFrame({k: v for k, v in S.items()}).loc["2015-09":"2026-05"].corr()

out = dict(n_tested=N_TESTED, rows=rows, corr=C.round(2).to_dict(),
           eurusd_2000=float(eurusd.loc["2000-01"].iloc[0]) if len(eurusd.loc["2000-01"]) else None,
           eurusd_now=float(eurusd.dropna().iloc[-1]))
pd.DataFrame(S).to_pickle("strategies.pkl")
json.dump(out, open("multi.json", "w"), default=float)

fmt = lambda d: "—" if d is None else f"{d['start']}–{d['end']} CAGR {d['cagr']*100:5.1f}% vol {d['vol']*100:5.1f}% SR {d['sharpe']:5.2f} DD {d['maxdd']*100:6.1f}% DSR {d['dsr']*100:4.0f}%"
for k, v in rows.items():
    print(f"{k:40s}\n   IS : {fmt(v['ins'])}\n   OOS: {fmt(v['oos'])}")
print("N getest:", N_TESTED)
