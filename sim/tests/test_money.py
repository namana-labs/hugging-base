"""Money lines (lane L2; build prompt 5.4.6): signs, labels, and local relief never priced. The scale ladder (3.4)."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from sim.constants import HEAD_RATING_KVA
from sim.contracts import audit_labels
from sim.money import energy_value_usd, money_block, ercot_demand, scale_ladder, pct_text, sig, ERCOT_DEMAND_CSV
from sim.verify_p1 import bare_numbers


class TestMoney(unittest.TestCase):
    def test_energy_value_sign(self):
        # 20 kW charging for 60 min at $50/MWh costs $1; discharging earns
        self.assertAlmostEqual(energy_value_usd(np.full((60, 1), 20.0), np.full(60, 50.0), 1 / 60), -1.0)
        self.assertAlmostEqual(energy_value_usd(np.full((60, 1), -20.0), np.full(60, 500.0), 1 / 60), 10.0)

    def test_block_labelled_and_relief_unpriced(self):
        b = money_block({"naive": 10.0, "aware": 12.0}, 1.2, 566.42, 34.47, "21:00", "16:45",
                        {"naive": 1920.0, "aware": 1500.0}, {"naive": {"normalEvents": 3}})
        errs, n = audit_labels({"money": b})
        self.assertEqual(errs, [])
        self.assertEqual(b["costOfAwareness"]["v"], -2.0)
        self.assertIs(b["relief"]["priced"]["v"], False)
        self.assertIsNone(b["transformerReplacementUSD"]["v"])
        # the capacity band prices fleet kW at the price peak only, never the relief
        self.assertAlmostEqual(b["systemCapacityPerMonth"]["naive"]["low"]["v"], 1920.0 * 3.12)
        self.assertNotIn("relief", b["systemCapacityPerMonth"])



class TestScaleLadder(unittest.TestCase):
    ERCOT = {"mw": 80000.0, "t": "16:40", "day": "2026-09-25", "rows": 288, "sha256": "0" * 64, "path": "x.csv"}

    def test_rungs_are_the_same_kw_over_each_base(self):
        sl = scale_ladder(2, 20.0, "A", "tr(x)", 25.0, 8000.0, self.ERCOT)
        self.assertEqual(sl["kw"]["v"], 40.0)
        self.assertEqual([r["scale"] for r in sl["rungs"]], ["can", "feeder", "ercot"])
        r = {x["scale"]: x for x in sl["rungs"]}
        self.assertEqual(r["can"]["sharePct"]["v"], 160.0)
        self.assertEqual(r["feeder"]["sharePct"]["v"], 0.5)
        self.assertEqual(r["ercot"]["sharePct"]["v"], 5e-05)            # 40 kW / 80,000 MW
        self.assertEqual((r["can"]["base"]["unit"], r["feeder"]["base"]["unit"], r["ercot"]["base"]["unit"]),
                         ("kVA", "kVA", "MW"))
        self.assertIn("160%", r["can"]["text"])
        self.assertIn("0.00005%", r["ercot"]["text"])
        # labels: DERIVED shares, REAL can and ERCOT bases, DERIVED head rating; no bare number anywhere
        self.assertEqual({x["sharePct"]["label"] for x in sl["rungs"]}, {"DERIVED"})
        self.assertEqual([x["base"]["label"] for x in sl["rungs"]], ["REAL", "DERIVED", "REAL"])
        self.assertEqual(bare_numbers(sl), [])
        self.assertEqual(audit_labels({"summary": sl})[0], [])

    def test_bare_number_is_caught(self):
        sl = scale_ladder(2, 20.0, "A", "tr(x)", 25.0, 8000.0, self.ERCOT)
        sl["rungs"][0]["sharePct"] = 160.0
        self.assertEqual(bare_numbers(sl), ["scaleLadder.rungs[0].sharePct"])

    def test_significant_figures_and_text(self):
        self.assertEqual(sig(0.50053), 0.501)
        self.assertEqual(sig(4.9012e-05), 4.9e-05)
        self.assertEqual(pct_text(4.9012e-05), "0.000049%")
        self.assertEqual(pct_text(160.0), "160%")
        self.assertEqual(pct_text(0.50053), "0.5%")

    def test_ercot_demand_from_the_real_csv(self):
        e = ercot_demand()
        self.assertEqual(e["day"], "2026-09-25")
        self.assertEqual(e["rows"], 288)                                # 5-min, the next day's 00:00 row left out
        self.assertEqual((e["mw"], e["t"]), (81612.0, "16:40"))
        self.assertEqual(len(e["sha256"]), 64)
        self.assertTrue(ERCOT_DEMAND_CSV.exists())
        sl = scale_ladder(2, 20.0, "A", "tr(x)", 25.0, HEAD_RATING_KVA, e)
        self.assertEqual({x["scale"]: x["sharePct"]["v"] for x in sl["rungs"]},
                         {"can": 160.0, "feeder": 0.501, "ercot": 4.9e-05})

    def test_ercot_demand_first_peak_and_day_only(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "d.csv"
            p.write_text("timestamp,demand_mw,capacity_mw\n"
                         "2026-09-25 00:00:00-0500,100,1\n2026-09-25 00:05:00-0500,300,1\n"
                         "2026-09-25 00:10:00-0500,300,1\n2026-09-26 00:00:00-0500,900,1\n")
            e = ercot_demand(p)
        self.assertEqual((e["mw"], e["t"], e["rows"]), (300.0, "00:05", 3))


if __name__ == "__main__":
    unittest.main()
