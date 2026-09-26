# Re-solve committed prototype frames at the prototype's default pf (0.88) and at unity pf.
# A fresh circuit per solve: once kvar is written, OpenDSS keeps kvar fixed on later kW writes.
import json
from pathlib import Path
from opendssdirect import dss
from sim.feeder import Feeder
C = Path.home()/'hb-overnight/tmp/review-connor-proto/committed'
rep = json.loads((C/'replays.json').read_text()); topo = json.loads((C/'topology.json').read_text())
sh = topo['shaping']
def solve(fr, unity):
    f = Feeder(); dss.Lines.Name(sh['weakLine']); dss.Lines.Length(sh['modifiedLengthKm'])
    f.load(fr['loadFactor']); f.battery(fr['powers'])
    if unity:
        for u in fr['powers']:
            dss.Loads.Name('bat_'+u); dss.Loads.kvar(0)
    return f.solve(False)
rows = [('rebound','naive',s) for s in (5,7)]
for scen, key, step in rows:
    fr = rep[scen][key][step]; a = solve(fr, False); b = solve(fr, True)
    print(f"{scen:8s} {key:6s} step {step:2d}: committed {fr['maxLoading']:7.2f}% ovl {fr['overloaded']:3d} minV {fr['minVoltage']:.5f} vViol {fr['voltageViolations']:2d} | 0.88pf {a['maxLoading']:7.2f}% {a['overloaded']:3d} {a['minVoltage']:.5f} {a['voltageViolations']:2d} | unity {b['maxLoading']:7.2f}% {b['overloaded']:3d} {b['minVoltage']:.5f} {b['voltageViolations']:2d}")
