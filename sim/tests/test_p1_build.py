"""P1 build (lane L2): runs the simulation on a short window (60 steps, 22:00-23:00, OpenDSS every step, all four
branches incl. the three faults) and checks the contract and the invariants. Under 20 s, no lock."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

from sim.constants import RESERVE_FLOOR, TIER_EMERGENCY_PCT, MIN_GRANT_KW
from sim.contracts import validate
from sim.p1_build import Window, build, market, battery_active
from sim.tiers import normal_events


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

    def test_quantization(self):
        doc = json.loads((Path(self.tmp.name) / "aware.json").read_text())
        self.assertTrue(all(isinstance(x, int) for x in doc["loading"][0]))
        self.assertEqual(len(doc["tier"][0]), 379)
        self.assertEqual(len(doc["state"][0]), 96)
        self.assertEqual(set(doc["focus"]), {"A", "B", "C", "D", "240"})


if __name__ == "__main__":
    unittest.main()
