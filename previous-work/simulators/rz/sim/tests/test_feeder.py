"""Runs OpenDSS (under a second). The unity-pf fix, the promoted readout and isolation."""
import unittest

import numpy as np

from sim.constants import FOCUS_TFS, BRIDGE_TF
from sim.feeder import Feeder, N_LOADS, N_HOMES


class FeederTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = Feeder()

    def test_sizes_and_focus(self):
        f = self.f
        self.assertEqual((len(f.load_names), len(f.homes), len(f.transformers), len(f.edges)), (2021, 1010, 379, 2531))
        self.assertEqual(len(f.fleet), 96)
        self.assertEqual(sum(h["eligible"] for h in f.homes), 1007)
        a = f.tf_index[FOCUS_TFS["A"]]
        self.assertEqual(a, 150)
        self.assertEqual(sorted(f.homes[j]["id"] for j in f.transformers[a]["homes"]), ["p1ulv11991", "p1ulv52469"])
        self.assertEqual(f.tf_index[BRIDGE_TF], 240)
        self.assertEqual(f.profiles[[i for i, n in enumerate(f.load_names) if "p1ulv11991" in n][0]], "res_kw_38274_pu")

    def test_unity_pf_battery(self):
        """20 kW of battery on A with homes at 0 reads about 80% (the prototype's 0.88 pf read 92.7%)."""
        f = self.f
        f.restore_all()
        f.set_loads(np.zeros(N_LOADS), np.zeros(N_LOADS))
        kw = np.zeros(N_HOMES)
        a = f.tf_index[FOCUS_TFS["A"]]
        kw[f.transformers[a]["homes"][0]] = 20.0
        f.set_home_batteries(kw)
        r = f.solve()
        self.assertLess(abs(r["pct"][a] - 80.0), 3.0, r["pct"][a])
        self.assertLess(abs(r["Q"][a]), 1.0)

    def test_solve_readout(self):
        f = self.f
        f.restore_all()
        f.set_loads(f.nameplate_kw * 0.5, f.nameplate_kvar * 0.5)
        f.set_batteries(np.zeros(96))
        r = f.solve()
        self.assertEqual(r["pct"].shape, (379,))
        self.assertEqual(r["vmin_home_pu"].shape, (1010,))
        self.assertTrue(0.9 < r["vmin_home_pu"].min() < 1.06)
        self.assertGreater(r["head_amps"], 50)

    def test_isolation(self):
        f = self.f
        a = f.tf_index[FOCUS_TFS["A"]]
        f.set_loads(f.nameplate_kw * 0.5, f.nameplate_kvar * 0.5)
        f.isolate_tf(a)
        f.set_batteries(np.full(96, 20.0))
        r = f.solve()
        self.assertLess(r["pct"][a], 0.01)
        self.assertEqual([r["vmin_home_pu"][j] for j in f.transformers[a]["homes"]], [0.0, 0.0])
        f.restore_all()
        f.set_loads(f.nameplate_kw * 0.5, f.nameplate_kvar * 0.5)
        f.set_batteries(np.zeros(96))
        self.assertGreater(f.solve()["pct"][a], 10)


if __name__ == "__main__":
    unittest.main()
