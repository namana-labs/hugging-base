"""DATA-TRUTH auditor 2: independent OpenDSS re-solve of three committed P1 frames.
Uses ONLY sim.feeder.create() (the repo's circuit loader). Everything else is written here:
home loads straight from the raw SMART-DS CSVs (my own 2018 index + 15->1 min interpolation),
battery kW from the committed branch JSON, and my own readout of transformer loading and home voltage."""
import json, re, sys, math
from pathlib import Path
import numpy as np
REPO = Path(sys.argv[1]); CACHE = Path.home() / "hb-overnight/cache/smartds"
sys.path.insert(0, str(REPO))
from sim.feeder import create
from opendssdirect import dss

homes, tfs, _, _, load_names = create()                 # the repo's loader (SMART-DS dss files + weak-line shaping)
# my own Loads.dss parse: name -> (kW, kvar, yearly shape)
spec = {}
for line in (REPO / "data/smartds/Loads.dss").read_text().splitlines():
    if not line.lower().startswith("new load."): continue
    name = re.search(r"(?i)new load\.(\S+)", line).group(1).lower()
    kw = float(re.search(r"(?i)\bkw=([\d.eE+-]+)", line).group(1))
    kvar = float(re.search(r"(?i)\bkvar=([\d.eE+-]+)", line).group(1))
    shape = re.search(r"(?i)yearly=(\S+)", line).group(1)
    spec[name] = (kw, kvar, shape)
_csv = {}
def shape(name):
    if name not in _csv: _csv[name] = np.loadtxt(CACHE / f"{name}.csv")
    return _csv[name]
def mult(name, day, hh, mm):
    # 2018 index of the interval starting at 2018-<same month-day> hh:mm, knot = interval start (repo's stated convention)
    doy = (np.datetime64(f"2018-{day}") - np.datetime64("2018-01-01")).astype(int)
    m = doy * 1440 + hh * 60 + mm
    k, r = divmod(m, 15)
    s = shape(name)
    return s[k] if r == 0 else (1 - r / 15) * s[k] + (r / 15) * s[k + 1]
fleet = json.loads((REPO / "data/fleet.json").read_text())["batteries"]
tfid = [t["id"] for t in tfs]; kva = np.array([t["kva"] for t in tfs])
home_ids = [h["id"] for h in homes]
elig = {h["id"] for h in homes if h["eligible"]}

def solve_frame(branch, hhmm, day="08-23"):
    doc = json.loads((REPO / f"ui/data/p1/{branch}.json").read_text())
    hh, mm = map(int, hhmm.split(":")); k = (hh * 60 + mm) - 16 * 60
    for L in dss.Loads:
        pass
    i = dss.Loads.First()
    while i:
        n = dss.Loads.Name().lower()
        if n in spec:
            kw0, kvar0, sh = spec[n]
            dss.Loads.kW(kw0 * mult(sh, day, hh, mm)); dss.Loads.kvar(kvar0 * mult(sh.replace("_kw_", "_kvar_"), day, hh, mm))
        elif n.startswith("bat_"):
            dss.Loads.kW(0.0); dss.Loads.kvar(0.0)
        i = dss.Loads.Next()
    for j, b in enumerate(fleet):
        dss.Loads.Name(f"bat_{b['id']}"); dss.Loads.kW(doc["batKW"][k][j] / 10.0); dss.Loads.kvar(0.0)
    dss.Solution.Solve(); assert dss.Solution.Converged()
    pct = np.zeros(len(tfs))
    for t, name in enumerate(tfid):
        dss.Circuit.SetActiveElement("Transformer." + name)
        p = dss.CktElement.Powers(); n = 2 * dss.CktElement.NumConductors()
        pct[t] = math.hypot(sum(p[0:n:2]), sum(p[1:n:2])) / kva[t] * 100
    vmin = 9.0; vwho = None
    for hid in home_ids:
        dss.Circuit.SetActiveBus(hid)
        v = min(dss.Bus.puVmagAngle()[0::2])
        if v < vmin: vmin, vwho = v, hid
    com = np.array(doc["loading"][k]) / 10.0
    top = int(np.argmax(pct))
    return {"branch": branch, "t": hhmm, "k": k,
            "mine_worst": (round(float(pct.max()), 1), top), "committed_worst": (float(com.max()), int(np.argmax(com))),
            "mine_over110": int((pct > 110).sum()), "committed_over110": int((com > 110).sum()),
            "mine_over100": int((pct > 100).sum()), "committed_over100": int((com > 100).sum()),
            "mine_over150": int((pct > 150).sum()), "committed_over150": int((com > 150).sum()),
            "mine_vmin": round(vmin, 4), "mine_vmin_home": vwho, "committed_vmin": doc["vMin"][k] / 1e4,
            "max_abs_diff_pts_all_379": round(float(np.abs(pct - com).max()), 2),
            "fleet_kw": round(sum(doc["batKW"][k]) / 10, 1)}

for br, t in [("naive", "22:30"), ("aware", "22:30"), ("aware_faults", "22:16"), ("none", "16:45")]:
    print(json.dumps(solve_frame(br, t)))
