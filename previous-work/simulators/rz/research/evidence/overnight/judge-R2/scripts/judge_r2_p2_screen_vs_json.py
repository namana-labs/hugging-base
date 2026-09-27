"""Judge R2: the P2 ranking table and referee badge on screen equal the committed JSON."""
import json, re, sys
from pathlib import Path
E = Path(sys.argv[1]); sp = E / "committed"
idx = json.loads((sp / "ui_data_p2_index.json").read_text())
d = json.loads((sp / "ui_data_p2_aware-core-d26-g0.json").read_text())
topo = json.loads((sp / "ui_data_topology.json").read_text())
txt = (E / "screen" / "view_p2_combo_aware_core_d26_g0.txt").read_text()
fails = 0
rows = re.findall(r"^(\d+)\tHome (\d{4})\tT-(\d+)\t([\d.]+)\t([\d.]+)\t\$(\d+)\t([●○])$", txt, re.M)
for r in rows:
    k = int(r[0]); e = d["ranking"][k - 1]
    od = e.get("opendss") or None
    after = (od or {}).get("after") if od else None
    peak = after["peakPct"] if after else e["peakWithPct"]
    pv = peak["v"] if isinstance(peak, dict) else peak
    home_label = topo["homes"][e["home"]]["label"] if isinstance(e["home"], int) else e["home"]
    mark = "●" if after else "○"
    ok = (f"Home {r[1]}" == home_label and int(r[2]) == e["tf"] and abs(float(r[3]) - pv) < 0.051 and r[6] == mark)
    fails += not ok
    print(f"rank {k}: screen Home {r[1]} T-{r[2]} {r[3]} {r[6]} | json {home_label} T-{e['tf']} {pv} {mark} {'ok' if ok else 'MISMATCH'}")
ref = idx["referee"]
m = re.search(r"OpenDSS referee: (\d+) month runs · surrogate error p99 ([\d.]+) ptsSIM \(max ([\d.]+) ptsSIM\) · tier agreement ([\d.]+)%", txt)
got = tuple(float(x) for x in m.groups()) if m else None
want = (ref["runs"], ref["errorPts"]["p99"]["v"], ref["errorPts"]["max"]["v"], ref["tierAgreementPct"]["v"])
okb = got is not None and all(abs(a - b) < 0.006 for a, b in zip(got, want)); fails += not okb
print(f"referee badge screen {got} json {want} {'ok' if okb else 'MISMATCH'}")
print(f"rows compared {len(rows)}")
print(f"SCREEN==JSON P2: {'PASS' if fails == 0 and rows else f'FAIL ({fails} mismatches)'}")
