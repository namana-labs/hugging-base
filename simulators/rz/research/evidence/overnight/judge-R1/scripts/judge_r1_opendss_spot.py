"""Judge R1 spot-check: the committed P1 JSON equals an independent OpenDSS solve at chosen steps.
Loads come from sim.loads (the committed npz), batteries from the branch file's batKW (tenths of kW, quantized)."""
import json, sys
from pathlib import Path
import numpy as np
root = Path.home() / "hb-overnight/judge-1"
sys.path.insert(0, str(root))
from sim.feeder import Feeder  # noqa: E402
from sim.loads import Loads  # noqa: E402

spot = Path(sys.argv[1])
topo = json.loads((spot / "ui_data_topology.json").read_text())
focus = {f["key"]: f["tf"] for f in topo["focus"]}
focus["240"] = 240
f = Feeder()
L = Loads()
start_min = 16 * 60
for branch, k in [("none", 45), ("aware", 45), ("naive", 390), ("aware", 390), ("naive", 269), ("aware", 150)]:
    d = json.loads((spot / f"ui_data_p1_{branch}.json").read_text())
    kw, kvar = L.at_minute("2026-08-23", start_min + k)
    f.restore_all()
    f.set_loads(kw, kvar)
    f.set_batteries(np.asarray(d["batKW"][k], dtype=float) / 10)
    r = f.solve()
    pct = np.asarray(r["pct"])
    js = np.asarray(d["loading"][k]) / 10
    diff = np.abs(pct - js)
    t = f"{(start_min + k) // 60 % 24:02d}:{(start_min + k) % 60:02d}"
    print(f"{branch:6s} {t}: " + " ".join(f"{n} dss {pct[i]:.1f} json {js[i]:.1f}" for n, i in focus.items())
          + f" | all 379 tfs max |dss-json| {diff.max():.2f} pts ; head {r['head_amps']:.1f} A")
