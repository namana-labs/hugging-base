"""Light probe (< 20 s CPU): 22 Jul, feeder-aware then feeder-aware + F1+F2+F3, then F1 alone. Writes nothing."""
import gzip, json, sys, time, resource
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from sim.p1_build import Window, Scenario, run_branch, branch_doc, summarize
from sim.history import slice_loads
from sim.loads import Loads
from sim.contracts import dumps
from sim.constants import FAULT_COMMS_AFTER_MIN, FAULT_HOT_AFTER_MIN, FAULT_STALL_AFTER_MIN, MIN_DWELL_MIN, MIN_GRANT_KW
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else "2026-07-22"
t = time.time(); c0 = time.process_time()
win = Window(day=d); sc = Scenario(win, loads=Loads(npz=slice_loads(d)))
setup = (time.time() - t, time.process_time() - c0)
out = {"day": d, "setupWallCpu": [round(x, 1) for x in setup]}
def timed(name, branch, faults):
    t = time.time(); c = time.process_time()
    run = run_branch(sc, branch, faults=dict(faults, dwell=MIN_DWELL_MIN))
    w, cp = time.time() - t, time.process_time() - c
    s = summarize(sc, run)[0]; doc = branch_doc(sc, run)
    gz = len(gzip.compress(dumps(doc).encode(), 9, mtime=0))
    out[name] = {"wall": round(w, 1), "cpu": round(cp, 1), "gzBytes": gz,
                 "batteryCausedNormal": s["batteryCausedNormal"]["v"], "batteryCausedEmergency": s["batteryCausedEmergency"]["v"],
                 "batteryCausedAmberMin": s["batteryCausedAmberMin"]["v"], "maxLoading": s["maxLoading"]["v"],
                 "chargedPctBy0400": s["chargedPctBy0400"]["v"], "energyValueUSD": s["energyValueUSD"]["v"],
                 "events": [e["text"] for e in run["events"]]}
    return run
aw = timed("aware", "aware", {})
g = aw["grants"]
ch = np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))
tc = int(ch[0]); out["tc"] = tc
timed("aware_faults", "aware_faults", {"comms": tc + FAULT_COMMS_AFTER_MIN, "hot": tc + FAULT_HOT_AFTER_MIN, "stall": tc + FAULT_STALL_AFTER_MIN})
timed("aware_comms_only", "aware_comms", {"comms": tc + FAULT_COMMS_AFTER_MIN})
out["loadavg"] = [round(x, 1) for x in __import__("os").getloadavg()]
print(json.dumps(out, indent=1))
