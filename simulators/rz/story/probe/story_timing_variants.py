"""Light probe (< 20 s CPU): one evening; feeder-aware (for Tc), then EV alone, stall alone (feeder-aware) and naive + EV."""
import gzip, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from sim.p1_build import Window, Scenario, run_branch, branch_doc, summarize
from sim.history import slice_loads
from sim.loads import Loads
from sim.contracts import dumps
from sim.constants import FAULT_HOT_AFTER_MIN, FAULT_STALL_AFTER_MIN, MIN_DWELL_MIN, MIN_GRANT_KW
d = sys.argv[1]
sc = Scenario(Window(day=d), loads=Loads(npz=slice_loads(d)))
aw = run_branch(sc, "aware", faults={"dwell": MIN_DWELL_MIN})
tc = int(np.flatnonzero((aw["grants"] > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))[0])
out = {"day": d, "tc": tc}
for name, br, f in [("aware_hot", "aware_hot", {"hot": tc + FAULT_HOT_AFTER_MIN}), ("aware_stall", "aware_stall", {"stall": tc + FAULT_STALL_AFTER_MIN}),
                    ("naive_hot", "naive", {"hot": tc + FAULT_HOT_AFTER_MIN})]:
    t = time.process_time(); run = run_branch(sc, br, faults=dict(f, dwell=MIN_DWELL_MIN)); cpu = time.process_time() - t
    s = summarize(sc, run)[0]; gz = len(gzip.compress(dumps(branch_doc(sc, run)).encode(), 9, mtime=0))
    out[name] = {"cpu": round(cpu, 1), "gzBytes": gz, **{k: s[k]["v"] for k in ("normalEvents", "batteryCausedNormal", "batteryCausedEmergency", "batteryCausedAmberMin", "protectionOperated", "maxLoading", "chargedPctBy0400", "energyValueUSD")},
                 "maxTf": s["maxLoading"].get("tf"), "maxT": s["maxLoading"].get("t"), "events": [e["text"] for e in run["events"]]}
print(json.dumps(out))
