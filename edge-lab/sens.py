import json, numpy as np, research as R
rng = np.random.default_rng(7)
rows = []
for bull in [0.05, 0.10, 0.15, 0.25]:
    for tail in [0.0, 1.0]:
        def fp(rng, n, h, bull=bull):
            mu = {0: bull/8760, 1: -0.04/8760}; sig=0.000005; phi=0.97; ps=1/(24*60)
            reg = rng.integers(0,2,n); f = np.where(reg==0, mu[0], mu[1]); out=np.empty((h,n))
            for t in range(h):
                reg = np.where(rng.random(n)<ps, 1-reg, reg); m=np.where(reg==0,mu[0],mu[1])
                f = m + phi*(f-m) + rng.normal(0,sig,n); out[t]=f
            return out
        fund = fp(rng, 1500, 8760)
        pnl = R.funding_arb(fund, 2, 0.05, rng, venue_fail_yr=0.03*tail, gap_yr=0.05*tail)
        rows.append(dict(bull=bull, tails=bool(tail), median=float(np.median(pnl)), mean=float(pnl.mean()),
                         p05=float(np.percentile(pnl,5)), loss_share=float((pnl<0).mean())))
        print(rows[-1], flush=True)
d = json.load(open("research.json")); d["sensitivity"] = rows; json.dump(d, open("research.json","w"))
