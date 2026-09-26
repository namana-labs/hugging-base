"""The OpenDSS referee on one day (no lock; a few seconds): it runs OpenDSS on the P2 schedule, never reads results."""
import unittest

from sim import referee


class RefereeOneDay(unittest.TestCase):
    def test_one_day_baseline_agrees_with_the_surrogate(self):
        lines = []
        doc = referee.run(steps=96, runs=referee.RUNS[:1], write=False, out=lines.append)
        self.assertEqual(doc["runs"], 1)
        self.assertEqual(doc["steps"], 96)
        self.assertEqual(len(doc["schedule_sha256"]), 64)
        self.assertGreaterEqual(len(doc["shortlist"]), 5)
        # the calibrated surrogate is within a few points of OpenDSS on the shortlist (7.2 found p99 0.26 pts)
        self.assertLess(doc["errorPts"]["p99"], 5.0)
        self.assertGreater(doc["tierAgreementPct"], 95.0)
        self.assertTrue(any(s.startswith("referee: 1 runs x 96") for s in lines))


class CapacityCheckOneDay(unittest.TestCase):
    """sim.referee's OpenDSS check of a capacity build (one day, 40 Cores): the fields exist, and the per-phase head
    estimate is within a few points of the OpenDSS head current (a physics check, not a fitted number)."""

    def test_capacity_check_one_day(self):
        from sim import p2_build as pb
        from sim.feeder import Feeder
        c = pb.Ctx()
        doc = referee.capacity_check(Feeder(), c, c.eligible[:40], "aware", steps=96)
        self.assertEqual(doc["n"], 40)
        for k in ("causedNormal", "normalEvents", "causedEmergencyN", "emergencyN", "protectionTfs", "maxPct", "head",
                  "vmin", "curtailPct", "errorAllPts"):
            self.assertIn(k, doc)
        h = doc["head"]
        self.assertGreater(h["maxPct"], 30.0)
        self.assertLess(abs(h["maxPct"] - h["estAtMaxPct"]), 5.0)
        self.assertLess(h["underReadMaxPts"], 5.0)
        self.assertGreater(doc["vmin"]["pu"], 0.9)
        self.assertLess(doc["errorAllPts"]["p99"], 5.0)


if __name__ == "__main__":
    unittest.main()
