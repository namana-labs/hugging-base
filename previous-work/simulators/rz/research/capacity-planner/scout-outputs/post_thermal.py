"""Post-process tf_capacity_sweep_g{0,20}.json: thermal capacities under naive dispatch (DERIVED from SIM).
  capNaiveTopOil120: largest k with max top-oil <= 120 C (C57.91 top-oil operating limit cited by Dong et al. 2019)
  capNaiveFEQA1:     largest k whose August equivalent ageing factor FEQA <= 1 (ages no faster than design-normal
                     in the hottest month; IEEE C57.91, 180,000 h)
Thermal constants are ASSUMPTIONs (see tf_capacity_sweep.TH)."""
import json, numpy as np
out = {}
for g in (0, 20):
    d = json.load(open(f"tf_capacity_sweep_g{g}.json"))
    K = d["K_NAIVE"]; to = np.array(d["naive"]["topOilMax"]); fe = np.array(d["naive"]["feqa"])
    res = {}
    for size in (25.0, 50.0, 75.0):
        idx = [t["i"] for t in d["tf"] if t["kva"] == size]
        c1 = [max([k for k in K if to[K.index(k)][i] <= 120.0] or [0]) for i in idx]
        c2 = [max([k for k in K if fe[K.index(k)][i] <= 1.0] or [0]) for i in idx]
        f = lambda v: {"p10": float(np.percentile(v, 10)), "p50": float(np.median(v)), "p90": float(np.percentile(v, 90))}
        res[f"{int(size)}kVA"] = {"capNaiveTopOil120": f(c1), "capNaiveFEQA1": f(c2)}
    out[f"g{g}"] = res
json.dump(out, open("post_thermal_out.json", "w"), indent=1)
print(json.dumps(out, indent=1))
