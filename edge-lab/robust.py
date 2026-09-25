"""Weerlegging: probeer de conclusies van multi.py/portfolio.py onderuit te halen."""
import io, json, contextlib, numpy as np, pandas as pd
from math import sqrt
with contextlib.redirect_stdout(io.StringIO()):
    import multi as M                       # draait multi.py stil, geeft R, S, prijzen

R, idx = M.R, M.idx
out = {}

def st(r):
    r = r.dropna(); eq = (1 + r).cumprod(); y = len(r) / 12
    return dict(cagr=float(eq.iloc[-1] ** (1 / y) - 1), sharpe=float(r.mean() / r.std() * sqrt(12)),
                dd=float((eq / eq.cummax() - 1).min()))

# 1) parametergevoeligheid trendregel
sens = {}
for asset, price, col in [("S&P", M.spx.SP500.reindex(idx), "spx"), ("Goud", M.gold.Price.reindex(idx), "gold")]:
    for n in [4, 6, 8, 10, 12, 14, 18]:
        sig = M.sma_signal(price, n)
        r = M.with_cost(pd.DataFrame({col: sig, "cash": 1 - sig}), R[[col, "cash"]])
        sens[f"{asset} {n}m"] = dict(ins=st(r[:"1999"]), oos=st(r["2000":]))
out["trend_params"] = sens

# 2) splitdatum: selecteer op data t/m jaar X, test daarna
base = {k: v for k, v in M.S.items() if "itcoin" not in k and "thereum" not in k}
Sdf = pd.DataFrame(base)
splits = {}
for cut in [1979, 1989, 1999, 2009]:
    sel = []
    for k in Sdf:
        s = M.stats(Sdf[k][:str(cut)], R.cash)
        if s and s["dsr"] >= 0.90: sel.append(k)
    A = Sdf.loc[str(cut + 1):, sel].mean(axis=1)
    spx = Sdf.loc[str(cut + 1):, "S&P 500 kopen en houden"]
    splits[cut] = dict(n=len(sel), sel=sel, A=st(A), spx=st(spx))
out["splits"] = splits

# 3) kosten x2 en x5, en 1 maand vertraging (uitvoering een maand later)
P = json.load(open("portfolio.json")); sel = P["selected"]
def rebuild(cost_mult=1, lag=0):
    old = M.COST
    M.COST = old * cost_mult
    S2 = {}
    sig = M.sma_signal(M.spx.SP500.reindex(idx), 10).shift(lag)
    S2["S&P trend (10-maands gem.)"] = M.with_cost(pd.DataFrame({"spx": sig, "cash": 1 - sig}), R[["spx", "cash"]], M.COST)
    S2["60/40 aandelen/obligaties"] = M.with_cost(pd.DataFrame({"spx": .6, "bond": .4}, index=idx), R[["spx", "bond"]], M.COST)
    ex = (20 / M.vix.reindex(idx)).clip(upper=1.5).shift(lag)
    S2["S&P volatiliteitsdoel (VIX)"] = M.with_cost(pd.DataFrame({"spx": ex, "cash": 1 - ex}), R[["spx", "cash"]], M.COST).where(M.vix.reindex(idx).notna())
    cm = M.cape.reindex(idx); wc = (0.5 + 0.5 * (cm < cm.expanding(120).median()).astype(float)).shift(lag)
    S2["S&P waarde-timing (CAPE)"] = M.with_cost(pd.DataFrame({"spx": wc, "cash": 1 - wc}), R[["spx", "cash"]], M.COST)
    w = M.w.shift(lag)
    S2["Dual momentum (aandelen/oblig./goud)"] = M.with_cost(w, R[["spx", "bond", "gold", "cash"]], M.COST)
    S2["S&P 500 kopen en houden"] = R.spx
    M.COST = old
    return pd.DataFrame(S2).loc["2000":][sel].mean(axis=1)
out["stress"] = {"basis": st(rebuild()), "kosten x2": st(rebuild(2)), "kosten x5": st(rebuild(5)),
                 "1 maand vertraging": st(rebuild(lag=1)), "kosten x5 + vertraging": st(rebuild(5, 1))}

# 4) rollende 10-jaarsvensters (vanaf 1965 zodat alle regels opgewarmd zijn; VIX-strategie telt mee zodra beschikbaar)
A_all = Sdf[sel].mean(axis=1)["1965":]
spx_all = Sdf["S&P 500 kopen en houden"]["1965":]
wins_sr = wins_ret = tot = 0; worst_rel = 0
for i in range(0, len(A_all) - 120, 1):
    a, s = A_all.iloc[i:i + 120], spx_all.iloc[i:i + 120]
    tot += 1
    sa, ss = st(a), st(s)
    wins_sr += sa["sharpe"] > ss["sharpe"]; wins_ret += sa["cagr"] > ss["cagr"]
    worst_rel = min(worst_rel, sa["cagr"] - ss["cagr"])
out["rolling10"] = dict(windows=tot, share_better_sharpe=wins_sr / tot, share_better_return=wins_ret / tot, worst_cagr_gap=worst_rel)

# 5) gepaarde block-bootstrap: kans dat Sharpe(A) > Sharpe(S&P) in 2000-2026
rng = np.random.default_rng(11)
a = Sdf.loc["2000":, sel].mean(axis=1).values; s = Sdf.loc["2000":, "S&P 500 kopen en houden"].values
L = len(a); cnt = 0; B = 20000
for _ in range(B):
    ix = np.concatenate([np.arange(k, k + 12) for k in rng.integers(0, L - 12, L // 12 + 1)])[:L]
    aa, ss = a[ix], s[ix]
    cnt += aa.mean() / aa.std() > ss.mean() / ss.std()
out["p_sharpe_better"] = cnt / B

json.dump(out, open("robust.json", "w"), default=float)
f = lambda d: f"CAGR {d['cagr']*100:5.1f}% SR {d['sharpe']:.2f} DD {d['dd']*100:6.1f}%"
print("== Trendregel, verschillende lengtes (IS | OOS)")
for k, v in sens.items(): print(f"  {k:10s} {f(v['ins'])} | {f(v['oos'])}")
print("== Splitdatum")
for k, v in splits.items(): print(f"  t/m {k}: {v['n']} gekozen | portf {f(v['A'])} | S&P {f(v['spx'])}")
print("== Stress"); [print(f"  {k:24s} {f(v)}") for k, v in out["stress"].items()]
print("== Rollend 10 jaar", out["rolling10"])
print("== Kans Sharpe portefeuille > S&P:", out["p_sharpe_better"])
