"""P3 chaos sweep (lane L2; build prompt 5.7 item 2): runs the sweep on the 60-step test window (22:00-23:00, OpenDSS
every step, CHAOS_QUICK_RUNS runs) and checks the plan, the device rules and the verifier (both halves: the real sweep
passes every chaos invariant, doctored copies fail). Under 20 s, no lock."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

from sim.chaos import (CHAOS_QUICK_RUNS, CHAOS_SEED, CHAOS_SILENT, CHAOS_STALL, build, plan_run, silent_picker)
from sim.constants import MIN_GRANT_KW, RESERVE_FLOOR, TIER_EMERGENCY_PCT
from sim.contracts import UI_DATA, validate
from sim.devices import Command
from sim.p1_build import Window, run_branch, battery_active
from sim.tiers import normal_events
from sim.verify_p1 import V, check_chaos


class TestChaosQuick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="chaos-test-")
        cls.r = build(Window(start="22:00", steps=60), CHAOS_QUICK_RUNS, out=cls.tmp.name, quiet=True)
        cls.topo = json.loads((UI_DATA / "topology.json").read_text())
        cls.doc = json.loads((Path(cls.tmp.name) / "chaos.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _verify(self, doc):
        p = Path(self.tmp.name) / "doctored.json"
        p.write_text(json.dumps(doc))
        v = V()
        with redirect_stdout(io.StringIO()):
            check_chaos(v, {"steps": -1}, self.topo, path=p)
        return v

    def test_contract(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            fails, n, total, lab = validate(root=Path(self.tmp.name))
        self.assertEqual(fails, [], buf.getvalue())

    def test_plan_is_seeded_and_in_range(self):
        sc, tc, tend = self.r["sc"], self.r["tc"], self.r["tend"]
        pool = set(int(t) for t in sc.tf_of_batt)
        for r in range(CHAOS_QUICK_RUNS):
            a, b = plan_run(sc, r, tc, tend), plan_run(sc, r, tc, tend)
            self.assertEqual(a, b)
            self.assertTrue(CHAOS_SILENT[0] <= a["silentN"] <= CHAOS_SILENT[1])
            self.assertTrue(CHAOS_STALL[0] <= a["stallMin"] <= CHAOS_STALL[1])
            self.assertIn(a["hotTf"], pool)
            for key in ("silentAt", "hotAt", "stallAt"):
                self.assertTrue(tc <= a[key] <= tend, key)
            self.assertEqual(sorted(a["order"]), list(range(sc.m)))
        self.assertNotEqual(plan_run(sc, 0, tc, tend), plan_run(sc, 0, tc, tend, seed=CHAOS_SEED + 1))

    def test_picker_takes_live_charge_first(self):
        cmds = {i: Command.make(i + 1, 0, kw) for i, kw in enumerate([0.0, 20.0, 0.2, 5.0, 20.0])}
        pick = silent_picker([4, 3, 2, 1, 0], 4)
        self.assertEqual(pick(None, cmds, 0), [4, 3, 1, 2])
        self.assertEqual(silent_picker([0, 1, 2, 3, 4], 10)(None, cmds, 0), [1, 3, 4, 0, 2])

    def test_runs_hold_the_invariants(self):
        """Re-run each planned sweep run and check the battery-caused / device invariants on the raw arrays."""
        sc = self.r["sc"]
        from sim.chaos import faults_of
        for plan in self.r["plans"]:
            run = run_branch(sc, "aware_faults", faults=faults_of(plan))
            caused, _ = battery_active(sc, run)
            self.assertEqual([e for e in normal_events(run["pct"], 1.0) if caused[e[1]:e[2], e[0]].any()], [])
            self.assertFalse(((run["pct"] > TIER_EMERGENCY_PCT) & caused).any())
            self.assertGreaterEqual(run["soc"].min(), RESERVE_FLOOR - 1e-9)
            self.assertEqual(len(run["silent"]), plan["silentN"])
            ev = next(e for e in run["events"] if e["kind"] == "comms_lost")
            for i, es in zip(run["silent"], ev["expiresStep"]):
                if es < len(run["state"]):
                    self.assertTrue(all(run["state"][k][i] in "XB" for k in range(es, len(run["state"]))))
            self.assertTrue(any(kw > MIN_GRANT_KW for kw in ev["cmdKW"]), "a silence holds live charge")
            acted = [(k, i) for k, s in enumerate(run["state"]) for i, c in enumerate(s)
                     if c == "X" and abs(run["batkw"][k, i]) > 1e-9]
            self.assertEqual(acted, [])
            hot = next(e for e in run["events"] if e["kind"] == "hot")
            self.assertEqual(hot["tf"], plan["hotTf"])
            stall = next(e for e in run["events"] if e["kind"] == "stall")
            self.assertEqual(stall["minutes"], plan["stallMin"])
            self.assertIn("TTL", stall["text"])

    def test_summary_equals_runs(self):
        d = self.doc
        self.assertEqual(len(d["runs"]), CHAOS_QUICK_RUNS)
        self.assertEqual(d["constants"]["CHAOS_RUNS"]["value"], CHAOS_QUICK_RUNS)
        self.assertEqual(d["batteryCausedNormal"]["v"], sum(r["batteryCausedNormal"]["v"] for r in d["runs"]))
        self.assertEqual(sum(d["histogram"]["batteryCaused"]["counts"]), CHAOS_QUICK_RUNS)
        self.assertEqual(sum(d["histogram"]["chargedPctResponsive"]["counts"]), CHAOS_QUICK_RUNS)

    def test_verifier_admits_the_real_sweep(self):
        v = self._verify(self.doc)
        self.assertEqual(v.fails, [])

    def test_verifier_refuses_doctored_sweeps(self):
        d = copy.deepcopy(self.doc)
        d["runs"][0]["batteryCausedNormal"]["v"] = 1
        d["runs"][0]["batteryCaused"]["v"] = 1
        d["batteryCausedNormal"]["v"] += 1
        d["runsWithBatteryCaused"]["v"] += 1
        self.assertIn("chaos-battery-caused", self._verify(d).fails)
        d = copy.deepcopy(self.doc)
        d["runs"][1]["reserveBreaches"]["v"] = 2
        self.assertIn("chaos-devices", self._verify(d).fails)
        d = copy.deepcopy(self.doc)
        d["runs"][0]["hot"]["peakPct"] = 88.8
        self.assertIn("chaos-labels", self._verify(d).fails)
        d = copy.deepcopy(self.doc)
        d["runs"][0]["silent"]["n"] = 11
        self.assertIn("chaos-plan", self._verify(d).fails)
        d = copy.deepcopy(self.doc)
        d["runs"][0]["silent"]["idleByExpiry"]["v"] -= 1
        self.assertIn("chaos-expiry", self._verify(d).fails)
        d = copy.deepcopy(self.doc)
        d["batteryCausedEmergency"]["v"] = 3
        self.assertIn("chaos-battery-caused", self._verify(d).fails)


if __name__ == "__main__":
    unittest.main()
