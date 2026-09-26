import unittest

import numpy as np

from sim.tiers import tier_codes, protection_events, normal_events, tier_strings


class TierTests(unittest.TestCase):
    def test_codes_one_minute(self):
        # tf0: 105% (amber); tf1: 115% for 40 min (counting then violation); tf2: 160% once
        n = 45
        pct = np.zeros((n, 3))
        pct[:, 0] = 105
        pct[0:40, 1] = 115
        pct[10, 2] = 160
        c = tier_codes(pct, 1.0)
        self.assertTrue((c[:, 0] == 1).all())
        self.assertTrue((c[0:29, 1] == 2).all())
        self.assertTrue((c[29:40, 1] == 3).all())   # the 30th minute above 110% is a violation
        self.assertTrue((c[40:, 1] == 0).all())
        self.assertEqual(c[10, 2], 4)
        self.assertEqual(normal_events(pct, 1.0), [(1, 0, 40)])

    def test_run_resets(self):
        pct = np.array([[115.0]] * 20 + [[100.0]] + [[115.0]] * 20)
        self.assertEqual(normal_events(pct, 1.0), [])
        self.assertEqual(int(tier_codes(pct, 1.0).max()), 2)

    def test_fifteen_minute_steps(self):
        pct = np.array([[115.0], [115.0], [90.0]])
        c = tier_codes(pct, 15)
        self.assertEqual(c[:, 0].tolist(), [2, 3, 0])
        self.assertEqual(normal_events(pct, 15), [(0, 0, 2)])

    def test_protection_rule(self):
        # 197% for 90 minutes never operates (the fuse margin, 4.5)
        self.assertEqual(protection_events(np.full((90, 1), 197.0), 60), [])
        # 201% for 9 minutes does not; for 10 it does, at the 10th minute
        self.assertEqual(protection_events(np.full((9, 1), 201.0), 60), [])
        self.assertEqual(protection_events(np.full((12, 1), 201.0), 60), [(9, 0)])
        # 301% for one 60 s step operates at once
        pct = np.zeros((5, 2))
        pct[3, 1] = 301
        self.assertEqual(protection_events(pct, 60), [(3, 1)])
        # 15-min steps: one interval above 200% operates
        self.assertEqual(protection_events(np.array([[150.0], [205.0]]), 900), [(1, 0)])
        c = tier_codes(np.full((12, 1), 201.0), 1.0)
        self.assertTrue((c[9:, 0] == 5).all())

    def test_strings(self):
        self.assertEqual(tier_strings(np.array([[0, 1, 5], [4, 3, 2]], dtype=np.int8)), ["015", "432"])


if __name__ == "__main__":
    unittest.main()
