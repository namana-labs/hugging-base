"""Judge R1: every P2 ranking entry whose transformer is stressed without the battery (baseline h100 > 0) carries a driver."""
import json, subprocess
idx = json.loads(subprocess.check_output(["git", "show", "HEAD:ui/data/p2/index.json"]))
tot = miss = 0
for c in idx["combos"]:
    cid = c if isinstance(c, str) else c.get("id")
    d = json.loads(subprocess.check_output(["git", "show", f"HEAD:ui/data/p2/{cid}.json"]))
    h100 = d["baseline"]["h100"]
    h = h100 if isinstance(h100, list) else h100.get("v")
    st = [e for e in d["ranking"] if (h[e["tf"]] if not isinstance(h[e["tf"]], dict) else h[e["tf"]]["v"]) > 0]
    m = [e["home"] for e in st if not e.get("driver")]
    tot += len(st); miss += len(m)
    print(f"{cid:28s} ranking {len(d['ranking'])} ; on stressed tfs {len(st)} ; missing driver {len(m)} {m[:5]}")
print(f"TOTAL stressed entries {tot} ; missing driver {miss}")
