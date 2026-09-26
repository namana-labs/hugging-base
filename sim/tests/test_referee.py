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


if __name__ == "__main__":
    unittest.main()
