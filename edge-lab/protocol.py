"""Meet: hoeveel nep-winnaars komen door een streng protocol heen?
Train = jaar 1 (1.525 strategieen proberen), Validatie = jaar 2 H1 (alleen de winnaar, 1 test),
Forward = jaar 2 H2 (stand-in voor paper trading: data die niemand heeft gezien)."""
import numpy as np, json
from multiprocessing import Pool
from math import erf, sqrt
import research as R
Phi = lambda x: 0.5*(1+erf(x/sqrt(2)))
A = 24*365

def psr(pnl, sr0=0.0):
    s = pnl.std()
    if s == 0: return 0.0
    srp = pnl.mean()/s                     # Sharpe per periode (uur)
    n = len(pnl)
    return Phi((srp - sr0/np.sqrt(A)) / np.sqrt((1 + srp*srp/2)/n))   # Lo (2002)

def one(args):
    seed, phi = args
    rng = np.random.default_rng(seed); e = rng.normal(0,0.006,R.H)
    r = e.copy()
    if phi:
        for t in range(1,R.H): r[t] = phi*r[t-1]+e[t]
    p = np.exp(np.cumsum(r)); S = R.SPLIT; V = S + (R.H-S)//2
    best = max(R.PAIRS, key=lambda fs: R.backtest(r[:S], p[:S], *fs)[0])
    # volledige reeks draaien zodat MA's opgewarmd zijn, daarna segmenten knippen
    _, pnl = R.backtest(r, p, *best)
    val, fwd = pnl[S:V], pnl[V:]
    return dict(val_psr=psr(val), fwd_psr=psr(fwd), val=float(val.sum()), fwd=float(fwd.sum()))

if __name__ == "__main__":
    out = {}
    for name, phi in [("random", 0.0), ("momentum", 0.03)]:
        with Pool(4) as pool: res = pool.map(one, [(5000+i, phi) for i in range(400)])
        v = np.array([x["val_psr"] for x in res]); f = np.array([x["fwd"] for x in res])
        passed = v > 0.95
        out[name] = dict(markets=400,
            pass_rate=float(passed.mean()),
            fwd_pos_all=float((f>0).mean()),
            fwd_pos_passed=float((f[passed]>0).mean()) if passed.any() else None,
            fwd_eur_passed=float(np.median(10000*(np.exp(f[passed])-1))) if passed.any() else None,
            n_passed=int(passed.sum()),
            n_passed_both=int((passed & (np.array([x["fwd_psr"] for x in res])>0.95)).sum()))
        print(name, out[name], flush=True)
    json.dump(out, open("protocol.json","w"))
