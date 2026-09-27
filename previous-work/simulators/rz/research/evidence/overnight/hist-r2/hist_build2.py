import sys, time, json
from pathlib import Path
sys.path.insert(0, "/Users/rzalagbada/hb-overnight/hb")
SP = sys.argv[1]
import sim.prices as P
P.CSV = Path(f"{SP}/lz_north_2025_2026.csv"); P.load.cache_clear()
import sim.p1_build as B
from sim.loads import Loads
from sim.feeder import Feeder
_orig = B._pick_silent
def pick(sc, cmds):
    try: return _orig(sc, cmds)
    except AssertionError:
        on = [(c.kw, i) for i, c in cmds.items() if c.kw > B.MIN_GRANT_KW]
        if not on: raise
        print("   (fault fallback: silent battery outside A-D)", flush=True)
        return max(on)[1]
B._pick_silent = pick
feeder = Feeder(); aug = Loads()
res = {}
for day in sys.argv[2:]:
    loads = aug if day.startswith("2026-08") else Loads(npz=f"{SP}/slice_{day}.npz")
    t = time.time()
    try:
        r = B.build(B.Window(day=day), out=f"{SP}/hist/{day}", loads=loads, feeder=feeder, quiet=True)
    except Exception as e:
        print(day, "FAILED", repr(e)); continue
    m = r["meta"]; s = m["summary"]
    res[day] = {"seconds": round(r["seconds"],1), "total": sum(r["sizes"].values()),
        "onset": m["plan"]["onset"], "mode": m["plan"]["mode"], "plan": m["plan"]["discharge"], "thr": m["plan"]["threshold"]["v"],
        "tc": m["tc"]["t"],
        "max": {b: (s[b]["maxLoading"]["v"], s[b]["maxLoading"].get("tf"), s[b]["maxLoading"].get("t")) for b in s},
        "normalEvents": {b: s[b]["normalEvents"]["v"] for b in s},
        "emergencyTfs": {b: s[b]["emergencyTfs"]["v"] for b in s},
        "battCausedN": {b: s[b]["batteryCausedNormal"]["v"] for b in s},
        "homeOnlyOver100": {b: s[b]["homeOnlyOver100"]["v"] for b in s},
        "prot": {b: s[b]["protectionOperated"]["v"] for b in s},
        "dark": {b: s[b]["homesDark"]["v"] for b in s},
        "energy": {b: s[b]["energyValueUSD"]["v"] for b in s},
        "charged": {b: s[b]["chargedPctBy0400"]["v"] for b in s},
        "vmin": {b: s[b]["vMinHome"]["v"] for b in s},
        "head": {b: s[b]["feederHead"]["v"] for b in s},
        "relief": {k: m["relief"].get(k) for k in ("tf","t","text")},
        "reliefKW": m["relief"]["reliefKW"]["v"], "reliefKWh": m["relief"]["reliefKWh"]["v"],
        "capAware": m["money"]["systemCapacityPerMonth"].get("aware",{}).get("fleetKW",{}).get("v"),
        "unrelieved": len(m["unrelieved"])}
    print(day, json.dumps(res[day]), flush=True)
json.dump(res, open(f"{SP}/hist/summary2.json","w"), indent=1)
