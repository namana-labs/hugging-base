"""Lane L1: sim.loads (the 5.3 Loads API), the committed August slice, and the 5.3 conformance check."""
import importlib.util
import unittest

import numpy as np

from sim.loads import ROOT, Loads, api_conformance

A_ID = 'tr(r:p1udt9411-p1udt9411lv)'
T240_ID = 'tr(r:p1udt15649-p1udt15649lv)'


def _fetch_module():
    spec = importlib.util.spec_from_file_location('fetch_profiles', ROOT / 'scripts' / 'fetch_profiles.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = Loads()

    def test_conformance_loads(self):
        self.assertEqual(api_conformance(self.L), [])

    def test_conformance_fixture_loads(self):
        try:
            from sim.fixtures import FixtureLoads  # lane L0
        except ImportError:
            self.skipTest('sim.fixtures (lane L0) not merged into this branch yet')
        self.assertEqual(api_conformance(FixtureLoads()), [])

    def test_slice_counts_and_order(self):
        L = self.L
        self.assertEqual((L.steps, L.step_minutes, L.t0), (3000, 15, '2026-08-01T00:00'))
        self.assertEqual((L.n_loads, L.n_homes, L.n_tf), (2021, 1010, 379))
        self.assertTrue(L.kw_ok.all())
        fp = _fetch_module()
        rows = fp.parse_loads(fp.default_dss())
        self.assertEqual([r[0] for r in rows], L.load_names)       # Loads.dss order
        self.assertEqual(len(fp.shape_names(rows)[0]), 254)

    def test_a_spike_matches_the_raw_profile(self):
        # 4.2: res_kw_38274_pu runs 0.222 -> 0.528 -> 0.964 -> 0.614 -> 0.165 around 16:45 on 23 Aug.
        L = self.L
        j = L.kw_names.index('res_kw_38274_pu')
        k = L.step_of('2026-08-23', 16 * 60 + 45)
        self.assertEqual(L.time_of(k), '2026-08-23T16:45')
        np.testing.assert_allclose(L._kw_shape[j, k - 2:k + 3], [0.222, 0.528, 0.964, 0.614, 0.165], atol=6e-4)

    def test_kw_and_kvar_convention(self):
        # kW = Loads.dss kW x kW shape (mult); kvar = Loads.dss kvar x kvar shape (qmult): SMART-DS LoadShapes.dss.
        L = self.L
        i = L.load_names.index('load_p1ulv11991_1')
        k = 1234
        kw, kvar = L.at_step(k)
        self.assertAlmostEqual(kw[i], L.load_kw[i] * L._kw_shape[L.load_shape[i], k])
        self.assertAlmostEqual(kvar[i], L.load_kvar[i] * L._kvar_shape[L.load_shape[i], k])
        self.assertEqual(L.profile_of(i), 'res_kw_38274_pu')

    def test_minute_interpolation_is_linear_between_interval_starts(self):
        L = self.L
        k = L.step_of('2026-08-23', 16 * 60 + 45)
        a, _ = L.at_step(k)
        b, _ = L.at_step(k + 1)
        m, _ = L.at_minute('2026-08-23', 16 * 60 + 52)
        np.testing.assert_allclose(m, a + (b - a) * 7 / 15)

    def test_minutes_past_midnight_and_the_31_aug_night(self):
        L = self.L
        np.testing.assert_allclose(L.at_minute('2026-08-23', 1440 + 61)[0], L.at_minute('2026-08-24', 61)[0])
        L.at_minute('2026-08-31', 1440 + 6 * 60 - 15)                  # 1 Sep 05:45, the last step
        with self.assertRaises(IndexError):
            L.at_minute('2026-08-31', 1440 + 6 * 60 + 15)
        with self.assertRaises(IndexError):
            L.tf_pq(2990, 11)

    def test_aggregates_are_sums_of_the_loads(self):
        L = self.L
        k = 2179
        kw, kvar = L.at_step(k)
        P, Q = L.tf_pq(k, 1)
        self.assertAlmostEqual(P.sum(), kw.sum(), places=6)
        self.assertAlmostEqual(Q.sum(), kvar.sum(), places=6)
        self.assertAlmostEqual(L.home_kw(k, 1).sum(), kw.sum(), places=6)
        iA = L.tf_ids.index(A_ID)
        self.assertAlmostEqual(P[0, iA], kw[L.load_tf == iA].sum(), places=9)

    def test_driver_names_the_shared_profile(self):
        L = self.L
        iA, i240 = L.tf_ids.index(A_ID), L.tf_ids.index(T240_ID)
        k = L.step_of('2026-08-23', 16 * 60 + 45)
        d = L.driver(iA, k)
        self.assertEqual((d['label'], d['profile']), ('Home 0212', 'res_kw_38274_pu'))
        self.assertEqual(d['kwAtPeak']['label'], 'SIM')
        self.assertIn(('Home 0409', i240), [(s['label'], s['tf']) for s in d['sharedWith']])
        self.assertEqual(L.driver(i240, k)['profile'], 'res_kw_38274_pu')


if __name__ == '__main__':
    unittest.main()
