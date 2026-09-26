"""Judge R1 spot-checks over the committed JSON (git show HEAD), recomputed without sim.verify."""
import json, sys
from pathlib import Path
import numpy as np
sp = Path(sys.argv[1])
J = lambda n: json.loads((sp / n).read_text())
topo = J("ui_data_topology.json"); meta = J("ui_data_p1_meta.json")
print("focus:", [(f["key"], f["tf"], f["id"], topo["transformers"][f["tf"]]["kva"], [topo["homes"][h]["label"] for h in topo["transformers"][f["tf"]]["homes"]]) for f in topo["focus"]])
print("bridge:", topo["bridge"], [topo["homes"][h]["label"] for h in topo["transformers"][240]["homes"]], "batteries on 240:", [topo["homes"][h]["battery"] for h in topo["transformers"][240]["homes"]])
print("plan:", json.dumps({k: meta["plan"][k] for k in meta["plan"] if k != "discharge"}), "discharge:", meta["plan"]["discharge"], "tc:", meta.get("tc"))
print("relief:", json.dumps(meta["relief"])[:900])
print("unrelieved:", json.dumps(meta["unrelieved"])[:600])
tf_of_home = [h["tf"] for h in topo["homes"]]
tf_of_batt = np.array([tf_of_home[h] for h in topo["fleet"]])
for br in ("none", "naive", "aware", "aware_faults"):
    d = J(f"ui_data_p1_{br}.json")
    L = np.asarray(d["loading"]) / 10
    tier = np.array([[int(c) for c in s] for s in d["tier"]])
    bk = np.asarray(d["batKW"]) / 10
    soc = np.asarray(d["soc"])
    tfkw = np.zeros_like(L)
    for i, t in enumerate(tf_of_batt): tfkw[:, t] += bk[:, i]
    # battery-caused (loose): over 100% while that tf's batteries move (|kW|>0.5) at the step or the previous 2
    active = np.abs(tfkw) > 0.5
    act3 = active.copy(); act3[1:] |= active[:-1]; act3[2:] |= active[:-2]
    over100b = int(((L > 100) & act3).sum()); over110b = int(((L > 110) & act3).sum()); over150 = int((L > 150).sum())
    tfs_over100 = sorted(set(np.nonzero(L > 100)[1].tolist()))
    print(f"{br:12s} max {L.max():.1f}% (tf {np.unravel_index(L.argmax(), L.shape)[1]}) ; tier>=3 steps {int((tier>=3).sum())} ; tier==4 {int((tier==4).sum())} ; tier==5 {int((tier==5).sum())} ; "
          f">150% cells {over150} ; >100% with own batteries moving {over100b} ; >110% with own batteries moving {over110b} ; tfs >100% {tfs_over100[:12]} ; "
          f"SoC min {soc.min() if soc.size else None} final mean {soc[-1].mean() if soc.size else 0:.1f} permille")
m = meta["money"]
print("money keys:", list(m.keys()))
print("money.relief:", json.dumps(m.get("relief"))[:600])
print("money.capacity:", json.dumps(m.get("capacity") or m.get("systemCapacity"))[:700])
print("money.localRelief:", json.dumps(m.get("localRelief"))[:400])
print("scaleLadder:", json.dumps(meta.get("scaleLadder"))[:1500])
idx = J("ui_data_p2_index.json")
print("p2 referee:", json.dumps(idx["referee"])[:600])
print("p2 flip:", json.dumps(idx["flip"])[:500])
print("p2 usefulCapacity:", json.dumps({k: idx["usefulCapacity"][k] for k in ("naive", "aware")}))
for c in ("aware-core-d26-g0", "naive-core-d26-g0"):
    d = J(f"ui_data_p2_{c}.json")
    r = d["ranking"]
    stressed = [e for e in r if (e.get("stressAvoidedH") or {}).get("v", 0) > 0 or e.get("driver")]
    nod = [e["home"] for e in r if (e.get("stressAvoidedH") or {}).get("v", 0) > 0 and not e.get("driver")]
    print(c, "top5:", [(e["rank"], topo["homes"][e["home"]]["label"] if isinstance(e["home"], int) else e["home"], e["tf"], (e.get("peakWithPct") or {}).get("v"), bool(e.get("opendss"))) for e in r[:5]],
          "| stressed entries with driver:", sum(1 for e in stressed if e.get("driver")), "/", len(stressed), "| stress-avoided w/o driver:", nod)
