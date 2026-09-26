"""FixtureLoads has the sim.loads.Loads API (docs/contracts.md); L1's conformance test repeats this on both."""
import json
import unittest

import numpy as np

from sim.feeder import ROOT
from sim.fixtures import FixtureLoads


class FixtureLoadsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = FixtureLoads()

    def test_api_shapes(self):
        L = self.L
        self.assertEqual((L.steps, L.step_minutes, L.t0), (3000, 15, "2026-08-01T00:00"))
        kw, kvar = L.at_step(0)
        self.assertEqual((kw.shape, kvar.shape, kw.dtype), ((2021,), (2021,), np.float64))
        kw2, _ = L.at_minute("2026-08-23", 1330)
        self.assertEqual(kw2.shape, (2021,))
        kw3, _ = L.at_minute("2026-08-23", 1440 + 120)   # minute may exceed 1440
        self.assertEqual(kw3.shape, (2021,))
        P, Q = L.tf_pq(100, 8)
        self.assertEqual((P.shape, Q.shape), ((8, 379), (8, 379)))
        H = L.home_kw(100, 8)
        self.assertEqual(H.shape, (8, 1010))
        self.assertTrue(np.allclose(P.sum(axis=1), H.sum(axis=1)))
        self.assertEqual(L.profile_of(0), "res_kw_36218_pu")
        with self.assertRaises(IndexError):
            L.tf_pq(2999, 2)

    def test_interpolation(self):
        L = self.L
        a, _ = L.at_step(22 * 96 + 88)          # 2026-08-23 22:00
        b, _ = L.at_step(22 * 96 + 89)          # 22:15
        m, _ = L.at_minute("2026-08-23", 22 * 60 + 5)
        self.assertTrue(np.allclose(m, a + (b - a) / 3))

    def test_deterministic(self):
        self.assertTrue(np.array_equal(FixtureLoads().at_step(500)[0], self.L.at_step(500)[0]))

    def test_fixture_files_flagged(self):
        for p in (ROOT / "ui" / "data" / "fixtures").rglob("*.json"):
            self.assertTrue(json.loads(p.read_text()).get("fixture"), p)


if __name__ == "__main__":
    unittest.main()
