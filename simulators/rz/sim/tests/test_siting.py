import unittest

import numpy as np

from sim import siting
from sim.caps import transformer_caps
from sim.constants import AWARE_MARGIN, RESERVE_FLOOR
from sim.tiers import normal_events, protection_events


class HandComputedTwoTransformers(unittest.TestCase):
    """month_metrics on a hand-built 2-transformer, 15-minute series (the first deliverable of lane L3)."""

    def setUp(self):
        n = 12
        pct = np.full((n, 2), 80.0)
        # tf0: 105 at k=1 (amber), 115 at k=3..5 (3 intervals > 110: one normal event of 0.75 h), 160 at k=8 (emergency)
        pct[1, 0] = 105
        pct[3:6, 0] = 115
        pct[8, 0] = 160
        # tf1: 112 at k=2 alone (a one-interval run: no event), 205 at k=10 (protection: one interval above 200%)
        pct[2, 1] = 112
        pct[10, 1] = 205
        self.pct = pct
        none = pct.copy()
        none[3:6, 0] = 99.0          # tf0's run exists only because of batteries
        self.none = none
        ck = np.zeros((n, 2))
        ck[3:6, 0] = 20.0            # charging during tf0's run
        self.ck = ck

    def test_counts_by_hand(self):
        M = siting.month_metrics(self.pct, self.none, self.ck, steps=12)
        # hours above 100%: tf0 intervals 1,3,4,5,8 = 5 x 0.25 h; tf1 intervals 2,10 = 0.5 h
        self.assertEqual(M["h100"].tolist(), [1.25, 0.5])
        self.assertEqual(M["h110"].tolist(), [1.0, 0.5])
        self.assertEqual(M["normalEvents"].tolist(), [1, 0])
        self.assertEqual(M["normalH"].tolist(), [0.75, 0.0])
        self.assertEqual(M["emergencyN"].tolist(), [1, 1])
        self.assertEqual(M["protection"].tolist(), [-1, 10])
        self.assertEqual(M["peak"].tolist(), [160.0, 205.0])
        self.assertEqual(M["peakT"].tolist(), [8, 10])
        self.assertEqual(M["causedNormal"].tolist(), [1, 0])
        self.assertEqual(M["causedLagNormal"].tolist(), [1, 0])

    def test_agrees_with_sim_tiers(self):
        M = siting.month_metrics(self.pct, steps=12)
        ev = normal_events(self.pct, 15)
        self.assertEqual(ev, [(0, 3, 6)])
        self.assertEqual(M["normalEvents"].tolist(), [sum(1 for e in ev if e[0] == j) for j in range(2)])
        prot = protection_events(self.pct, 900)
        self.assertEqual(prot, [(10, 1)])

    def test_home_only_event_is_not_battery_caused(self):
        M = siting.month_metrics(self.pct, self.pct.copy(), np.zeros_like(self.pct), steps=12)
        self.assertEqual(M["normalEvents"].tolist(), [1, 0])
        self.assertEqual(M["causedNormal"].tolist(), [0, 0])


class StatelessRule(unittest.TestCase):
    def random_state(self, rng, T=6, m=14):
        kva = rng.choice([10.0, 25.0, 50.0, 75.0], T)
        bg_kw = rng.uniform(-5, 1.1, T) * kva
        bg_kvar = rng.uniform(0, 0.45, T) * np.abs(bg_kw)
        soc = rng.uniform(0.1, 1.0, m)
        soc[rng.random(m) < 0.15] = 1.0
        soc[rng.random(m) < 0.1] = RESERVE_FLOOR
        tf_of = rng.integers(0, T, m)
        pmax = rng.choice([20.0, 11.4], m)
        emax = np.where(pmax == 20.0, 37.0, 22.5)
        rte = np.where(pmax == 20.0, 0.89, 0.88)
        return bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, rte

    def test_vectorised_equals_sequential_walk(self):
        rng = np.random.default_rng(7)
        worst = 0.0
        for i in range(600):
            bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, rte = self.random_state(rng)
            mode = ("charge", "discharge", "idle")[i % 3]
            target = float(rng.choice([1e9, rng.uniform(0, 120)]))
            dt_h = float(rng.choice([1 / 60, 0.25]))
            a = siting.per_tf_rule(bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, target, mode, rte=rte, dt_h=dt_h)
            b = siting.per_tf_rule_reference(bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, target, mode, rte=rte, dt_h=dt_h)
            worst = max(worst, float(np.abs(a - b).max()))
        self.assertLess(worst, 1e-6)

    def test_caps_hold_in_the_controller_view(self):
        rng = np.random.default_rng(11)
        for i in range(400):
            bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, rte = self.random_state(rng)
            mode = ("charge", "discharge")[i % 2]
            kw = siting.per_tf_rule(bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, 1e9, mode, rte=rte)
            per_tf = np.bincount(tf_of, weights=kw, minlength=len(kva))
            H, E, R = transformer_caps(bg_kw, bg_kvar, kva)
            s_after = np.hypot(bg_kw + per_tf, bg_kvar)
            s_before = np.hypot(bg_kw, bg_kvar)
            lim = AWARE_MARGIN * kva
            # never pushes a transformer past alpha kVA; where it was over, never makes it worse
            self.assertTrue(np.all((s_after <= lim + 1e-6) | (s_after <= s_before + 1e-6)))
            if mode == "charge":
                self.assertTrue(np.all(per_tf[H <= 0] <= 1e-9))
            # the reserve holds and nobody charges past full
            dis, chg = siting.limits(soc, pmax, emax, rte, 1 / 60)
            self.assertTrue(np.all(-kw <= dis + 1e-9))
            self.assertTrue(np.all(kw <= chg + 1e-9))
            self.assertTrue(np.all((np.abs(kw) < 1e-12) | (np.abs(kw) >= 0.5 - 1e-12)))

    def test_grant_in_turn_not_equal_split(self):
        # four batteries on one 25 kVA can whose H fits one: the lowest SoC bucket gets it all
        kw = siting.per_tf_rule(np.array([2.0]), np.array([0.0]), np.array([25.0]), np.array([0.5, 0.3, 0.7, 0.31]),
                                20.0, 37.0, np.array([0, 0, 0, 0]), 1e9, "charge")
        H = AWARE_MARGIN * 25 - 2.0
        self.assertAlmostEqual(kw[1], 20.0)
        self.assertAlmostEqual(kw[3], H - 20.0)       # next bucket takes the rest
        self.assertEqual(kw[0], 0.0)
        self.assertEqual(kw[2], 0.0)

    def test_relief_overrides_the_market(self):
        # home load 30 kW on 25 kVA: R = 30 - 23.75 = 6.25 kW; both batteries idle in the market
        kw = siting.per_tf_rule(np.array([30.0]), np.array([0.0]), np.array([25.0]), np.array([0.6, 0.9]),
                                20.0, 37.0, np.array([0, 0]), 0.0, "idle")
        self.assertAlmostEqual(kw[1], -6.25)          # highest SoC relieves first, just enough
        self.assertEqual(kw[0], 0.0)


class ParityWithP1(unittest.TestCase):
    """5.4.3 step 9: allocate(state=None, cover=False) == per_tf_rule on 1,000 random single-step states, to 1e-6."""

    def test_parity(self):
        worst, n, detail = siting.parity(1000)
        if worst is None:
            self.skipTest(detail)
        self.assertEqual(n, 1000)
        self.assertLess(worst, 1e-6, detail)


if __name__ == "__main__":
    unittest.main()
