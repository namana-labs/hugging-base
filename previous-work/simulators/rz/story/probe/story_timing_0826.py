"""26 Aug probe: the 23 Aug comms-loss picker finds no charging battery on A-D at Tc+15, so use a fallback picker
(the largest charge command on the whole feeder), the same hook sim.chaos uses. Writes nothing."""
import gzip, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from sim.p1_build import Window, Scenario, run_branch, branch_doc, summarize
from sim.history import slice_loads
from sim.loads import Loads
from sim.contracts import dumps
from sim.constants import FAULT_COMMS_AFTER_MIN, FAULT_HOT_AFTER_MIN, FAULT_STALL_AFTER_MIN, MIN_DWELL_MIN, MIN_GRANT_KW
d = "2026-08-26"
sc = Scenario(Window(day=d), loads=Loads(npz=slice_loads(d)))
aw = run_branch(sc, "aware", faults={"dwell": MIN_DWELL_MIN})
g = aw["grants"]
tc = int(np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))[0])
def pick(sc, cmds, k):
    on = [(c.kw, -i, i) for i, c in cmds.items() if c.kw > MIN_GRANT_KW]
    return [max(on)[2]] if on else []
t = time.process_time()
run = run_branch(sc, "aware_faults", faults={"dwell": MIN_DWELL_MIN, "comms": tc + FAULT_COMMS_AFTER_MIN, "pick_silent": pick,
                                             "hot": tc + FAULT_HOT_AFTER_MIN, "stall": tc + FAULT_STALL_AFTER_MIN})
cpu = time.process_time() - t
s = summarize(sc, run)[0]
gz = len(gzip.compress(dumps(branch_doc(sc, run)).encode(), 9, mtime=0))
print(json.dumps({"tc": tc, "cpu": round(cpu, 1), "gzBytes": gz, **{k: s[k]["v"] for k in ("batteryCausedNormal", "batteryCausedEmergency", "batteryCausedAmberMin", "maxLoading", "chargedPctBy0400", "energyValueUSD")}, "events": [e["text"] for e in run["events"]]}))
