import re, time, json
import numpy as np
from sim import p2_build as pb, referee
from sim.feeder import Feeder
ctx = pb.Ctx()
txt = open("data/smartds/Transformers.dss").read()
ph = {}
for line in txt.splitlines():
    m = re.match(r"New Transformer\.(\S+) phases=(\d)", line)
    if not m: continue
    b = re.search(r"wdg=1 conn=\w+ bus=\S+?((?:\.\d)+)?\s", line)
    phases = [int(x) for x in (b.group(1) or ".1.2.3").strip(".").split(".")] if b else [1,2,3]
    ph[m.group(1)] = phases if m.group(2) == "1" else [1, 2, 3]
tfph = [ph[i] for i in ctx.tf_ids]
from collections import Counter
print(Counter(tuple(p) for p in tfph))
W = np.zeros((ctx.n_tf, 3))
for i, p in enumerate(tfph):
    for q in p: W[i, q - 1] += 1.0 / len(p)
f = Feeder()
steps = 96 * 3
for pol, homes in (("aware", ctx.eligible), ("naive", ctx.eligible[:383]), ("none", [])):
    if homes:
        world, sim = pb.capacity_sim(ctx, homes, pol if pol != "none" else "aware")
        kwh = referee.world_schedule(ctx, world, sim, steps)
        colkw = sim["col_kw"][:steps]; spct = sim["pct"][:steps]
    else:
        kwh = np.zeros((steps, 1010)); colkw = np.zeros((steps, ctx.n_tf)); spct = None
    sol = referee.solve_month(f, ctx, 0, kwh, steps)
    dss = sol["head"] / 370 * 100
    P = ctx.P[:steps] + colkw; Q = ctx.Q[:steps]
    est3 = np.hypot(P.sum(1), Q.sum(1)) / 7991.5 * 100
    Pp = P @ W; Qp = Q @ W
    estp = (np.hypot(Pp, Qp) / 7.2 / 370 * 100).max(1)
    d3 = dss - est3; dp = dss - estp
    k = int(np.argmax(dss))
    print(pol, "dss max", round(dss.max(),1), "| balanced est at k", round(est3[k],1), "diff max", round(d3.max(),2), "min", round(d3.min(),2),
          "| per-phase est at k", round(estp[k],1), "diff max", round(dp.max(),2), "min", round(dp.min(),2), "p99 |d|", round(np.percentile(np.abs(dp),99),2))
    np.save(f"/Users/rzalagbada/hb-overnight/tmp/l3_probe_{pol}.npy", np.c_[dss, est3, estp, (np.hypot(Pp,Qp)/7.2/370*100)])
