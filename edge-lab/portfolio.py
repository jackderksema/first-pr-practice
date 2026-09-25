import json, numpy as np, pandas as pd
from math import sqrt
from statistics import NormalDist
S = pd.read_pickle("strategies.pkl"); M = json.load(open("multi.json"))
rows = M["rows"]
# 1) Selectie ALLEEN op in-sample (t/m 1999): DSR >= 90% en niet-crypto
sel = [k for k, v in rows.items() if v["ins"] and v["ins"]["dsr"] >= 0.90 and "itcoin" not in k and "thereum" not in k]
print("IS-geselecteerd:", sel)
oos = S.loc["2000-01":"2026-05"]
A = oos[sel].mean(axis=1)                      # gelijk gewogen, maandelijks herbalanceren
cash = pd.Series(np.nan)
def st(r, c=None):
    r = r.dropna(); yrs = len(r)/12
    eq = (1+r).cumprod()
    return dict(cagr=(eq.iloc[-1])**(1/yrs)-1, vol=r.std()*sqrt(12), sharpe=r.mean()/r.std()*sqrt(12),
                maxdd=float((eq/eq.cummax()-1).min()), end10k=float(10000*eq.iloc[-1]), yrs=yrs)
res = {"selected": sel, "A_oos": st(A), "spx_oos": st(oos["S&P 500 kopen en houden"])}
# 2) met 10% bitcoin-trend vanaf 2020
B = A.copy(); b = oos["Bitcoin trend (200 dagen)"]
m = b.notna(); B[m] = 0.9*A[m] + 0.1*b[m]
res["A_2020"] = st(A["2020-01":]); res["B_2020"] = st(B["2020-01":])
# 3) in euro (onafgedekt): r_eur = (1+r_usd)*(fx_t/fx_{t-1}) - 1, fx = EUR per USD
fx = pd.read_csv("data/fx.csv", parse_dates=["Date"]); fx = fx[fx.Country=="Euro"].set_index("Date")["Exchange rate"].resample("ME").last()
fxr = (fx/fx.shift(1)).reindex(A.index)
res["A_oos_eur"] = st((1+A)*fxr-1); res["spx_oos_eur"] = st((1+oos["S&P 500 kopen en houden"])*fxr-1)
# 4) correlaties 2000-2026 (traditioneel) en 2020-2026 incl crypto
res["corr_trad"] = oos[[c for c in S.columns if "itcoin" not in c and "thereum" not in c]].corr().round(2).to_dict()
res["corr_2020"] = S.loc["2020-01":"2026-05"].corr().round(2).to_dict()
# 5) block bootstrap 10 jaar, €10k
rng = np.random.default_rng(3)
def boot(r, years=10, n=20000, block=12):
    r = r.dropna().values; L = len(r); out = np.empty(n)
    for i in range(n):
        seq = []
        while len(seq) < years*12:
            s = rng.integers(0, L-block); seq.extend(r[s:s+block])
        out[i] = 10000*np.prod(1+np.array(seq[:years*12]))
    q = np.percentile(out, [5, 25, 50, 75, 95])
    return dict(p5=q[0], p25=q[1], p50=q[2], p75=q[3], p95=q[4], p_loss=float((out<10000).mean()))
res["boot_A"] = boot(A); res["boot_spx"] = boot(oos["S&P 500 kopen en houden"])
res["boot_btc"] = boot(oos["Bitcoin kopen en houden"]["2020-01":])
res["eq_A"] = [round(float(x),0) for x in (10000*(1+A).cumprod()).values]
res["eq_spx"] = [round(float(x),0) for x in (10000*(1+oos["S&P 500 kopen en houden"]).cumprod()).values]
res["eq_dates"] = [d.strftime("%Y-%m") for d in A.index]
json.dump(res, open("portfolio.json","w"), default=float)
for k in ["A_oos","spx_oos","A_oos_eur","spx_oos_eur","A_2020","B_2020","boot_A","boot_spx","boot_btc"]:
    print(k, {kk: round(v,3) if isinstance(v,float) else v for kk,v in res[k].items()})
c = pd.DataFrame(res["corr_trad"]); print(c.round(2).to_string())
