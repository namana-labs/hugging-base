"""P1 build (lane L2): runs the simulation on a short window (60 steps, 22:00-23:00, OpenDSS every step, all four
branches incl. the three faults) and checks the contract and the invariants. Under 20 s, no lock."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

from sim.constants import RESERVE_FLOOR, TIER_EMERGENCY_PCT, MIN_GRANT_KW, MIN_DWELL_MIN, TAG
from sim.contracts import UI_DATA, validate
from sim.p1_build import Window, build, market, battery_active
from sim.tiers import normal_events
from sim.verify_p1 import check_scale_ladder


class TestMarketPlan(unittest.TestCase):
    def test_full_window_plan(self):
        win = Window()
        modes, plan, onset, _ = market(win)
        self.assertEqual(win.steps, 720)
        self.assertEqual(onset[0], "2026-08-23T22:00")
        self.assertEqual(round(onset[1], 2), 55.42)
        self.assertEqual([(t[11:16], m) for t, m in plan],
                         [("21:00", 15), ("21:15", 15), ("20:00", 15), ("19:45", 15), ("20:15", 13)])
        self.assertEqual(modes.count("discharge"), 73)
        self.assertEqual(modes.count("charge"), 360)       # 22:00 -> 04:00
        self.assertEqual(modes[win.step_of(win.time(0).replace(hour=16, minute=45))], "idle")


class TestShortWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="p1-test-")
        cls.r = build(Window(start="22:00", steps=60), out=cls.tmp.name, quiet=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_contract(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            fails, n, total, lab = validate(root=Path(self.tmp.name))
        self.assertEqual(fails, [], buf.getvalue())
        self.assertEqual(n, 5)

    def test_aware_invariants(self):
        sc = self.r["sc"]
        for b in ("aware", "aware_faults"):
            run = self.r["runs"][b]
            caused, _ = battery_active(sc, run)
            nev = [e for e in normal_events(run["pct"], 1.0) if caused[e[1]:e[2], e[0]].any()]
            self.assertEqual(nev, [], b)
            self.assertFalse(((run["pct"] > TIER_EMERGENCY_PCT) & caused).any(), b)
            self.assertGreaterEqual(run["soc"].min(), RESERVE_FLOOR - 1e-9, b)
            acted = [(k, i) for k, s in enumerate(run["state"]) for i, c in enumerate(s)
                     if c == "X" and abs(run["batkw"][k, i]) > 1e-9]
            self.assertEqual(acted, [], b)
            self.assertEqual(sum(d.accepted_nonincreasing for d in run["devs"]), 0)
        # the admit half: aware charges (not safe by doing nothing)
        self.assertGreater(self.r["runs"]["aware"]["batkw"].sum(), 1000.0)

    def test_naive_overloads_where_aware_does_not(self):
        naive, aware = self.r["runs"]["naive"]["pct"], self.r["runs"]["aware"]["pct"]
        a = self.r["sc"].focus["A"]
        self.assertGreater(naive[:, a].max(), 150.0)       # all at once on a 25 kVA can
        self.assertLessEqual(aware[:, a].max(), 100.0)

    def test_comms_loss_stale_expiry_cover(self):
        meta = self.r["meta"]
        tc = meta["tc"]["step"]
        self.assertEqual(tc, 0)                              # the window starts at the 22:00 onset
        e = {x["kind"]: x for x in meta["events"]["aware_faults"]}["comms_lost"]
        self.assertEqual(e["step"], tc + 15)
        self.assertGreater(e["cmdKW"], MIN_GRANT_KW)
        self.assertEqual(e["staleStep"] - e["step"], 3)
        self.assertEqual(e["expiredStep"] - e["step"], 5)
        self.assertIsNotNone(e["coveredStep"])
        self.assertLessEqual(e["coveredStep"] - e["expiredStep"], 1)

    def test_stall_expires_every_command(self):
        run = self.r["runs"]["aware_faults"]
        s0 = {x["kind"]: x for x in self.r["meta"]["events"]["aware_faults"]}["stall"]["step"]
        live = [i for i, c in enumerate(run["state"][s0 - 1]) if c in "CD"]
        self.assertTrue(live)
        for i in live:
            self.assertIn("X", "".join(run["state"][k][i] for k in range(s0, min(len(run["state"]), s0 + 6))))

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as t2:
            build(Window(start="22:00", steps=60), out=t2, quiet=True)
            for name in ("meta.json", "none.json", "naive.json", "aware.json", "aware_faults.json"):
                self.assertEqual((Path(self.tmp.name) / name).read_bytes(), (Path(t2) / name).read_bytes(), name)

    def test_constants_are_the_values_that_ran(self):
        # default dwell: MIN_DWELL_MIN exported as registered (the committed build)
        for name in ("meta.json", "aware.json", "naive.json"):
            c = json.loads((Path(self.tmp.name) / name).read_text())["constants"]["MIN_DWELL_MIN"]
            self.assertEqual(c, TAG["MIN_DWELL_MIN"], name)

    def test_scale_ladder_in_meta(self):
        meta = self.r["meta"]
        topo = json.loads((UI_DATA / "topology.json").read_text())
        a = {f["key"]: f["tf"] for f in topo["focus"]}["A"]
        ok, txt = check_scale_ladder(meta, topo, a)
        self.assertTrue(ok, txt)
        self.assertEqual(meta["scaleLadder"]["kw"]["v"], 40.0)            # 2 Cores on A x 20 kW
        # the refuse half: a stale or edited ladder fails the invariant
        bad = json.loads(json.dumps(meta))
        bad["scaleLadder"]["rungs"][2]["sharePct"]["v"] = 1.0
        self.assertFalse(check_scale_ladder(bad, topo, a)[0])
        self.assertFalse(check_scale_ladder({k: v for k, v in meta.items() if k != "scaleLadder"}, topo, a)[0])

    def test_quantization(self):
        doc = json.loads((Path(self.tmp.name) / "aware.json").read_text())
        self.assertTrue(all(isinstance(x, int) for x in doc["loading"][0]))
        self.assertEqual(len(doc["tier"][0]), 379)
        self.assertEqual(len(doc["state"][0]), 96)
        self.assertEqual(set(doc["focus"]), {"A", "B", "C", "D", "240"})



class TestDwellOverrideExported(unittest.TestCase):
    """The judge's check (build prompt 9): --dwell N changes the rotation, and the envelope exports N, not the default."""

    def test_override_value_and_cite(self):
        with tempfile.TemporaryDirectory(prefix="p1-dwell-") as t:
            r = build(Window(start="22:00", steps=20), out=t, quiet=True, dwell=15)
            for name in ("meta.json", "none.json", "naive.json", "aware.json", "aware_faults.json"):
                c = json.loads((Path(t) / name).read_text())["constants"]["MIN_DWELL_MIN"]
                self.assertEqual(c["value"], 15, name)
                self.assertEqual(c["label"], "ASSUMPTION", name)
                self.assertTrue(c["cite"].startswith("override: judge check"), c["cite"])
                self.assertIn(f"uses {MIN_DWELL_MIN}", c["cite"])
        self.assertEqual(r["runs"]["aware"]["ctl"].state.dwell, 15)
        self.assertEqual(TAG["MIN_DWELL_MIN"]["value"], MIN_DWELL_MIN)      # the registry is never mutated


if __name__ == "__main__":
    unittest.main()
