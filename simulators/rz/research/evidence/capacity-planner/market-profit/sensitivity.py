"""Sensitivity of the RT perfect-foresight bound (2025, LZ_NORTH, deg $12/MWh) to the member reserve floor and RTE.
DERIVED: REAL prices x ASSUMED battery."""
import json, numpy as np
import profit_bounds as pb
rt = pb.load_rt(pb.RT25); p = np.array([r[3] for r in rt])
res = {}
for floor_frac in (0.0, 0.2, 0.5):
    for rte in (0.85, 0.89):
        pb.FLOOR = floor_frac * pb.E; pb.EC = pb.Ed = rte ** 0.5; pb.S0 = (pb.FLOOR + pb.E) / 2
        r = pb.lp_arbitrage(p, 0.25, deg=12)
        res[f"floor{int(floor_frac*100)}_rte{int(rte*100)}"] = {"net_usd": round(r["net"], 2), "energy_usd": round(r["energy"], 2),
                                                               "cycles_equiv_37kwh": round(r["dis_kwh"] / pb.E, 1)}
        print(floor_frac, rte, res[f"floor{int(floor_frac*100)}_rte{int(rte*100)}"])
json.dump(res, open("sensitivity_out.json", "w"), indent=1)
