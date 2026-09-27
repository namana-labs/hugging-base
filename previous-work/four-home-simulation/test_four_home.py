"""Four home model tests. Run from demos/grid-stories: python3 -m unittest sim.test_four_home -v"""
import json
import unittest
from datetime import timedelta

import four_home as M
from four_home_constants import *


class FourHome(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prices, cls.freq, cls.demand, cls.storage = M.load_series()
        cls.start, cls.peak, cls.med, cls.thresh, cls.note = M.onset(cls.prices)
        cls.out = {n: M.run_policy(n, cls.prices, cls.freq, cls.demand, cls.storage, cls.start)
                   for n in M.POLICIES}

    # ---- topology --------------------------------------------------------
    def test_one_battery_per_home_four_homes_two_transformers(self):
        self.assertEqual(len(M.HOMES), 4)
        self.assertEqual(sorted(h for _, _, hs in M.TRANSFORMERS.values() for h in hs), sorted(M.HOMES))
        for s in self.out["naive"]["steps"]:
            self.assertEqual(len(s["homes"]), 4)

    # ---- physics -----------------------------------------------------------
    def test_power_balance_closes_every_step(self):
        """Substation kW = rest of feeder + home loads + batteries + network losses,
        to 10 W on a 6.5 MW feeder. Needs the tightened solver tolerance."""
        for n, p in self.out.items():
            for s in p["steps"]:
                loads = sum(h["load_kw"] + h["batt_kw"] for h in s["homes"].values())
                self.assertAlmostEqual(s["head_kw"], s["bg_kw"] + loads + s["losses_kw"], delta=0.01,
                                       msg=f"{n} step {s['k']}")

    def test_naive_breaks_tier_a_on_the_25_kva_can_only(self):
        st = self.out["naive"]["steps"]
        self.assertEqual(st[0]["xfmr"]["T1"]["tier"], "A")
        self.assertTrue(all(s["xfmr"]["T2"]["tier"] == "ok" for s in st))

    def test_position_matters_t2_never_violates_under_any_policy(self):
        for n, p in self.out.items():
            self.assertTrue(all(s["xfmr"]["T2"]["tier"] == "ok" for s in p["steps"]), n)

    def test_jitter_shifts_energy_and_does_not_reduce_overload(self):
        nv, jt = self.out["naive"]["score"], self.out["jitter"]["score"]
        self.assertAlmostEqual(nv["energy_wall_kwh"], jt["energy_wall_kwh"], delta=0.2)
        self.assertGreaterEqual(jt["violation_minutes"]["A"], nv["violation_minutes"]["A"])

    def test_aware_clears_every_tier_as_refereed_by_opendss(self):
        self.assertEqual(self.out["aware"]["score"]["violation_minutes"], {"N": 0, "E": 0, "A": 0})

    def test_aware_defers_only_behind_the_small_can(self):
        u = self.out["aware"]["score"]["unmet_by_xfmr_kwh"]
        self.assertGreater(u["T1"], 0.0)
        self.assertEqual(u["T2"], 0.0)

    def test_service_voltage_ordering_and_band(self):
        nv, aw = self.out["naive"]["score"], self.out["aware"]["score"]
        self.assertGreater(aw["min_service_v"], nv["min_service_v"])
        for n, p in self.out.items():
            for s in p["steps"]:
                for h in s["homes"].values():
                    self.assertLess(h["v_leg_min"], V_MAX_120 + 1.0, n)

    def test_fleet_frequency_effect_is_below_dashboard_resolution(self):
        """71 kW at 0.075 to 0.12 mHz per MW is microhertz; the feed resolves 1 mHz."""
        for s in self.out["naive"]["steps"]:
            self.assertLess(s["fleet_df_uhz"][1], F_RESOLUTION_MHZ * 1000.0)
            self.assertLessEqual(s["fleet_df_uhz"][0], s["fleet_df_uhz"][1])

    # ---- data alignment ----------------------------------------------------
    def test_price_uses_interval_ending_strictly_after_step_start(self):
        t0 = M.ts(self.prices[self.start]["t"])
        for s in self.out["naive"]["steps"]:
            t = t0 + timedelta(minutes=STEP_MINUTES * s["k"])
            end = M.ts(f"2026-09-25 {s['price_interval_ending']}:00-0500")
            self.assertGreater(end, t)
            self.assertLessEqual(end, t + timedelta(minutes=15))

    def test_real_frequency_joined_for_every_step(self):
        for s in self.out["naive"]["steps"]:
            self.assertTrue(59.9 < s["freq_mean"] < 60.1)
            self.assertLessEqual(s["freq_min"], s["freq_mean"])
            self.assertGreater(s["inertia_gw_s"], 100.0)

    def test_onset_follows_d26_and_reports_when_non_binding(self):
        self.assertLessEqual(self.prices[self.start]["price"], self.thresh)
        if self.thresh >= max(p["price"] for p in self.prices):
            self.assertIn("non binding", self.note)

    # ---- bookkeeping -------------------------------------------------------
    def test_reserve_floor_and_soc_bounds(self):
        for n, p in self.out.items():
            for s in p["steps"]:
                for h, v in s["homes"].items():
                    self.assertGreaterEqual(v["soc"], RESERVE_FLOOR - 1e-9, f"{n} {h}")
                    self.assertLessEqual(v["soc"], 1.0 + 1e-9, f"{n} {h}")

    def test_energy_identity_with_losses_explicit(self):
        for n, p in self.out.items():
            s = p["score"]
            self.assertAlmostEqual(s["energy_stored_kwh"] + s["energy_unmet_kwh"], s["energy_needed_kwh"], delta=0.2, msg=n)
            self.assertAlmostEqual(s["battery_losses_kwh"], s["energy_wall_kwh"] - s["energy_stored_kwh"], delta=0.2, msg=n)

    def test_sign_convention_matches_grid_stories(self):
        first = self.out["naive"]["steps"][0]["homes"]
        self.assertTrue(all(h["batt_kw"] > 0 for h in first.values()))

    def test_deterministic(self):
        again = M.run_policy("naive", self.prices, self.freq, self.demand, self.storage, self.start)
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.out["naive"], sort_keys=True))

    def test_every_constant_tagged(self):
        for name, meta in TAG.items():
            self.assertIn(meta["tag"], ("SOURCED", "DERIVED", "ASSUMPTION", "UNVERIFIED"), name)
            self.assertTrue(meta["cite"], name)


if __name__ == "__main__":
    unittest.main()
