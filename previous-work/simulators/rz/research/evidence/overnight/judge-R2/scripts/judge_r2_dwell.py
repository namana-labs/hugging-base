"""Judge R1 spot-check: does MIN_DWELL_MIN change the A-D hand-off count (5.4.3 definition)?
Reads aware.json from the committed P1 data (dwell 5) and from rebuilt outputs at other dwell values.
Hand-offs are counted with sim.orchestrator.handoffs, window fixed at 5 min (the definition), threshold 0.5 kW."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path.home() / "hb-overnight/judge-2"))
from sim.orchestrator import handoffs  # noqa: E402

root = Path.home() / "hb-overnight/judge-2"
topo = json.loads((root / "ui/data/topology.json").read_text())
tf_of_home = [h["tf"] for h in topo["homes"]]
tf_of_batt = [tf_of_home[h] for h in topo["fleet"]]
focus = {f["key"]: f["tf"] for f in topo["focus"]}
abcd = [i for i, t in enumerate(tf_of_batt) if t in focus.values()]

def stats(path):
    d = json.loads(Path(path).read_text())
    bk = np.asarray(d["batKW"], dtype=float) / 10
    h, pairs = handoffs(bk[:, abcd], window=5, thr=0.5)
    first = {}
    for k in ("A", "B", "C", "D"):
        cols = [i for i in abcd if tf_of_batt[i] == focus[k]]
        on = np.flatnonzero((bk[:, cols] > 0.5).any(axis=1) & (np.arange(len(bk)) >= 360))
        first[k] = int(on[0]) if len(on) else None
    kwh = {k: round(float(np.clip(np.asarray(d["focus"][k]["batKW"]) / 10, 0, None).sum() / 60), 1) for k in "ABCD"}
    L = np.asarray(d["loading"]) / 10
    tier = np.array([[int(c) for c in s] for s in d["tier"]])
    soc = np.asarray(d["soc"])
    return {"handoffs": h, "firstChargeStep": first, "kwhABCD": kwh, "maxLoading": round(float(L.max()), 1),
            "tierGE3": int((tier >= 3).sum()), "chargedMeanPerMille": float(soc[-1].mean()), "socMin": int(soc.min())}

for label, p in [(a.split("=")[0], a.split("=")[1]) for a in sys.argv[1:]]:
    print(label, json.dumps(stats(p)))
