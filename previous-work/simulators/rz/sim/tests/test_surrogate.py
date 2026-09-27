"""Lane L1: sim.surrogate. The OpenDSS test runs the simulation on three frames (a short window)."""
import unittest

import numpy as np

from sim import surrogate
from sim.loads import Loads

A_ID = 'tr(r:p1udt9411-p1udt9411lv)'


class TestPrior(unittest.TestCase):
    def test_centre_tap_prior_for_a(self):
        L = Loads()
        i = L.tf_ids.index(A_ID)
        c = surrogate.physics_prior(L.tf_ids)
        # 25 kVA: %r = 0.266272 / 0.532544 / 0.532544 ; XHL 2.4, XHT 1.6, XLT 2.4 ; %noloadloss 0.472
        self.assertAlmostEqual(c['kva'][i], 25.0)
        self.assertAlmostEqual(c['a'][i], (0.266272 + 2 * 0.532544 / 4) / 100 / 25)
        self.assertAlmostEqual(c['b'][i], (0.8 + (1.6 + 0.8) / 4) / 100 / 25)
        self.assertAlmostEqual(c['p0'][i], 0.472 / 100 * 25)
        self.assertEqual(c['q0'][i], 0.0)

    def test_three_phase_prior(self):
        L = Loads()
        params = surrogate.transformer_params()
        c = surrogate.physics_prior(L.tf_ids)
        three = [i for i, t in enumerate(L.tf_ids) if params[t]['windings'] == 2]
        self.assertTrue(three)
        i = three[0]
        t = params[L.tf_ids[i]]
        self.assertAlmostEqual(c['a'][i], (t['r'][0] + t['r'][1]) / 100 / t['kva'])
        self.assertAlmostEqual(c['b'][i], t['xhl'] / 100 / t['kva'])

    def test_loading_shapes_and_losses_add(self):
        L = Loads()
        P, Q = L.tf_pq(2170, 12)
        b = np.zeros_like(P)
        b[:, L.tf_ids.index(A_ID)] = 40.0
        s = surrogate.loading(P, Q, b)
        self.assertEqual(s.shape, (12, 379))
        self.assertTrue(np.all(s >= surrogate.loading_lossless(P, Q, b) - 1e-9))
        # the [379] form works too
        self.assertEqual(surrogate.loading(P[0], Q[0], b[0]).shape, (379,))


class TestAgainstOpenDSS(unittest.TestCase):
    """Three frames on 23 Aug (none at 16:45, all 96 at +20 kW at 22:00, all at -20 kW at 20:00)."""

    def test_losses_bring_the_surrogate_closer_to_opendss(self):
        from sim.calibrate import batt_per_tf, get_feeder, solve_frame
        L = Loads()
        f, _ = get_feeder()
        nf = len(f.fleet)
        worst, worst0 = 0.0, 0.0
        for minute, kw in ((16 * 60 + 45, 0.0), (22 * 60, 20.0), (20 * 60, -20.0)):
            k = L.step_of('2026-08-23', minute)
            kw96 = np.full(nf, kw)
            r = solve_frame(f, L, k, kw96)
            P, Q = L.tf_pq(k, 1)
            b = batt_per_tf(L, f, kw96)
            worst = max(worst, np.abs(surrogate.loading(P[0], Q[0], b) - r['pct']).max())
            worst0 = max(worst0, np.abs(surrogate.loading_lossless(P[0], Q[0], b) - r['pct']).max())
        self.assertLess(worst, worst0)


if __name__ == '__main__':
    unittest.main()
