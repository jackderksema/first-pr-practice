"""Onderzoek 1: overfitting op schaal. Onderzoek 2: funding-arb Monte Carlo sweep.
Alle markten zijn synthetisch; parameters zijn aannames, geen live data."""
import json, time
import numpy as np
from multiprocessing import Pool

H = 2 * 365 * 24          # 2 jaar uurdata
SPLIT = H // 2
FEE = 0.0005
PAIRS = [(f, s) for f in range(2, 60, 2) for s in range(f + 5, 400, 7)]


def ma(p, w):
    c = np.cumsum(np.insert(p, 0, 0.0))
    out = np.empty_like(p)
    out[w - 1:] = (c[w:] - c[:-w]) / w
    out[:w - 1] = np.nan
    return out


def backtest(r, p, fast, slow):
    mf, ms = ma(p, fast), ma(p, slow)
    pos = np.where(mf > ms, 1.0, -1.0)
    pos[:slow] = 0
    pos = np.roll(pos, 1); pos[0] = 0
    trades = np.abs(np.diff(pos, prepend=0))
    pnl = pos * r - trades * FEE
    return pnl.sum(), pnl


def one_market(args):
    seed, phi = args
    rng = np.random.default_rng(seed)
    e = rng.normal(0, 0.006, H)
    r = np.empty(H); r[0] = e[0]
    if phi == 0:
        r = e
    else:
        for t in range(1, H):
            r[t] = phi * r[t - 1] + e[t]
    p = np.exp(np.cumsum(r))
    best = (-1e9, None)
    ins_all, oos_all = [], []
    for f, s in PAIRS:
        a, pnl = backtest(r[:SPLIT], p[:SPLIT], f, s)
        b, _ = backtest(r[SPLIT:], p[SPLIT:], f, s)
        ins_all.append(a); oos_all.append(b)
        if a > best[0]:
            sr = pnl.mean() / pnl.std() * np.sqrt(24 * 365) if pnl.std() > 0 else 0
            best = (a, (f, s, b, sr))
    a, (f, s, b, sr) = best
    return dict(ins=a, oos=b, sr_ins=sr, med_oos=float(np.median(oos_all)))


def overfit_study(n_markets, phi):
    with Pool(4) as pool:
        res = pool.map(one_market, [(1000 + i, phi) for i in range(n_markets)])
    ins = np.array([x["ins"] for x in res]); oos = np.array([x["oos"] for x in res])
    to_eur = lambda lr: 10000 * (np.exp(lr) - 1)
    return dict(
        phi=phi, markets=n_markets, strategies_per_market=len(PAIRS),
        backtests=n_markets * len(PAIRS) * 2,
        best_ins_eur_median=float(np.median(to_eur(ins))),
        best_oos_eur_median=float(np.median(to_eur(oos))),
        best_oos_positive_share=float((oos > 0).mean()),
        best_sr_ins_median=float(np.median([x["sr_ins"] for x in res])),
        oos_eur_all=[round(float(v)) for v in to_eur(oos)],
        ins_eur_all=[round(float(v)) for v in to_eur(ins)],
    )


# ---------- Funding-arb Monte Carlo ----------
def funding_paths(rng, n_paths, hours):
    """Uurlijkse funding (fractie per uur). Twee regimes: 'bull' (positief, hoog)
    en 'bear' (licht negatief). AR(1) rond regimegemiddelde. Aannames, geen fit."""
    mu = {0: 0.08 / 8760, 1: -0.04 / 8760}           # 8%/jr resp. -4%/jr
    sig = 0.000005   # stationaire sd ~0,002%/u
    phi = 0.97
    p_switch = 1 / (24 * 60)                          # gem. regime ~60 dagen
    reg = rng.integers(0, 2, n_paths)
    f = np.array([mu[x] for x in reg])
    out = np.empty((hours, n_paths))
    for t in range(hours):
        sw = rng.random(n_paths) < p_switch
        reg = np.where(sw, 1 - reg, reg)
        m = np.where(reg == 0, mu[0], mu[1])
        f = m + phi * (f - m) + rng.normal(0, sig, n_paths)
        out[t] = f
    return out


def funding_arb(fund, lev, thresh_apr, rng, capital=10000, rt_cost=0.0015,
                venue_fail_yr=0.03, venue_loss=1.0, gap_yr=0.05):
    hours, n = fund.shape
    notional = capital * lev / (lev + 1)              # spot + perp-marge
    thresh = thresh_apr / 8760
    # signaal: 24u-gemiddelde funding boven drempel -> in positie
    k = np.ones(168) / 168                          # 7-daags gemiddelde
    pnl = np.zeros(n)
    for j in range(n):
        c = np.cumsum(np.insert(fund[:, j], 0, 0.0))
        sm = np.full(hours, np.nan); sm[167:] = (c[168:] - c[:-168]) / 168  # alleen verleden
        on = np.zeros(hours, bool); state = False
        for t in range(168, hours, 8):              # elke 8 uur beslissen, met hysterese
            if not state and sm[t] > thresh: state = True
            elif state and sm[t] < 0: state = False
            on[t:t + 8] = state
        on = np.roll(on, 1); on[0] = False
        switches = np.abs(np.diff(on.astype(int), prepend=0)).sum()
        pnl[j] = notional * (fund[:, j] * on).sum() - switches / 2 * notional * rt_cost
    yrs = hours / 8760
    # staartrisico's
    fail = rng.random(n) < venue_fail_yr * yrs
    pnl -= fail * (capital / (lev + 1)) * venue_loss   # perp-kant op beurs verloren
    # hedge breekt (ADL, liquidatie bij spike, depeg): verlies op notional
    gap = rng.random(n) < min(1.0, gap_yr * yrs * lev / 2)
    pnl -= gap * notional * rng.uniform(0.05, 0.25, n)
    return pnl


def funding_sweep():
    rng = np.random.default_rng(42)
    fund = funding_paths(rng, 3000, 8760)
    grid = []
    for lev in [1, 2, 3, 5]:
        for th in [0.0, 0.05, 0.10, 0.20]:
            pnl = funding_arb(fund, lev, th, rng)
            grid.append(dict(lev=lev, thresh=th,
                             median=float(np.median(pnl)), mean=float(pnl.mean()),
                             p05=float(np.percentile(pnl, 5)), p95=float(np.percentile(pnl, 95)),
                             loss_share=float((pnl < 0).mean())))
    return grid


if __name__ == "__main__":
    t0 = time.time()
    out = {}
    prev = json.load(open("research.json"))
    out["overfit_random"] = prev["overfit_random"]; out["overfit_edge"] = prev["overfit_edge"]
    out["funding"] = funding_sweep()
    out["runtime_s"] = round(time.time() - t0)
    json.dump(out, open("research.json", "w"))
    for k in ("overfit_random", "overfit_edge"):
        d = {kk: v for kk, v in out[k].items() if not kk.endswith("_all")}
        print(k, d)
    for g in out["funding"]:
        print(g)
    print("runtime", out["runtime_s"])
