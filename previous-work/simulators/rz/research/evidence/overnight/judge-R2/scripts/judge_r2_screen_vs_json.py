"""Judge R1: the numbers the P1 screen shows (body innerText) equal the committed JSON at that step."""
import json, re, sys
from pathlib import Path
import numpy as np
scr = Path(sys.argv[1]); sp = Path(sys.argv[2])
J = lambda n: json.loads((sp / n).read_text())
topo = J("ui_data_topology.json"); meta = J("ui_data_p1_meta.json")
focus = {f["key"]: f["tf"] for f in topo["focus"]}; focus["T-240"] = 240
fails = 0
for f in sorted(scr.glob("view_p1_*.txt")):
    txt = f.read_text()
    br = re.search(r"branch=(\w+)", txt).group(1); t = re.search(r"&t=(\d\d:\d\d)", txt).group(1)
    k = (int(t[:2]) * 60 + int(t[3:]) - 16 * 60) % 1440
    d = J(f"ui_data_p1_{br}.json")
    L = np.asarray(d["loading"][k]) / 10
    out = []
    for key, tf in focus.items():
        m = re.search(rf"^{re.escape(key)} · \d+ kVA · [^\n]*\n([\d.,]+)%SIM", txt, re.M)
        shown = float(m.group(1).replace(",", "")) if m else None
        ok = shown is not None and abs(shown - L[tf]) < 0.051
        fails += not ok
        out.append(f"{key} screen {shown} json {L[tf]:.1f} {'ok' if ok else 'MISMATCH'}")
    m = re.search(r"WORST SERVICE TRANSFORMER NOW\n([\d.,]+)%SIM", txt)
    w = float(m.group(1).replace(",", "")) if m else None
    okw = w is not None and abs(w - L.max()) < 0.051; fails += not okw
    m = re.search(r"step (\d+) of 720", txt); step = int(m.group(1)) if m else None
    oks = step == k; fails += not oks
    pr = meta["price"][k]; prv = pr["v"] if isinstance(pr, dict) else pr
    m = re.search(rf"\n{t}\n\$([\d.,]+)/MWh", txt)
    ps = float(m.group(1)) if m else None
    okp = ps is not None and abs(ps - prv) < 0.006; fails += not okp
    tier = d["tier"][k]
    over = sum(c >= "1" and c != "5" for c in tier); a110 = sum(c in "234" for c in tier); em = tier.count("4")
    m = re.search(r"transformers now: over nameplate (\d+) · above 110% (\d+) · emergency (\d+)", txt)
    cnt = tuple(map(int, m.groups())) if m else None
    okc = cnt == (over, a110, em); fails += not okc
    print(f"{f.name}: step {step}=={k} {'ok' if oks else 'MISMATCH'} ; worst screen {w} json {L.max():.1f} {'ok' if okw else 'MISMATCH'} ; price ${ps} json ${prv} {'ok' if okp else 'MISMATCH'} ; counts screen {cnt} json {(over, a110, em)} {'ok' if okc else 'MISMATCH'}\n    " + " ; ".join(out))
print(f"SCREEN==JSON P1: {'PASS' if fails == 0 else f'FAIL ({fails} mismatches)'}")
