"""Power balance of the root feeder, every step (kickoff B1.1; ported from four-home-simulation/test_four_home.py
test_power_balance_closes_every_step).

Substation kW must equal the solved kW of every load element (homes and batteries) plus the losses, to
POWER_BALANCE_TOL_W, at every step. The solves are the committed P1 aware evening's: sim.loads load and the battery
kW in ui/data/p1/aware.json. The tightened solver tolerance closes it; the tolerance sim.feeder ships with does not,
and that test is marked as an expected failure until the lead sets SOLVER_TOLERANCE in sim/feeder.py (request 2 in
mpalacios/docs/requests.md). When that lands, it "unexpectedly succeeds": delete the decorator.
"""
import json
import unittest

import numpy as np

from mpalacios.constants import POWER_BALANCE_TOL_W, SOLVER_TOLERANCE
from mpalacios.physics.balance import ROOT, solve_window

WINDOWS = ((0, 30), (360, 30))      # 16:00-16:29 (home load only) and 22:00-22:29 (the fleet charging)


class PowerBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sim.loads import Loads
        cls.loads = Loads()
        doc = json.loads((ROOT / "ui" / "data" / "p1" / "aware.json").read_text())
        cls.batkw = np.asarray(doc["batKW"], dtype=float) / 10.0
        meta = json.loads((ROOT / "ui" / "data" / "p1" / "meta.json").read_text())
        h, m = (int(x) for x in meta["start"].split(":"))
        cls.day, cls.start = meta["day"], h * 60 + m

    def residuals(self, tol):
        from sim.feeder import Feeder
        feeder = Feeder()                           # a fresh circuit: sim.feeder's own settings, then `tol`
        out = []
        for k0, n in WINDOWS:
            res, _, _, used = solve_window(feeder, self.loads, self.day, self.start + k0, self.batkw[k0:k0 + n],
                                           {}, n, tol)
            out.append(np.abs(res))
        return np.concatenate(out), used

    def test_tightened_tolerance_closes_every_step(self):
        res, used = self.residuals(SOLVER_TOLERANCE)
        self.assertEqual(used, SOLVER_TOLERANCE)
        self.assertLessEqual(float(res.max()), POWER_BALANCE_TOL_W,
                             f"residual {res.max():.3f} W at tolerance {used:g}")

    @unittest.expectedFailure
    def test_tolerance_as_shipped_closes_every_step(self):
        res, used = self.residuals(None)
        self.assertLessEqual(float(res.max()), POWER_BALANCE_TOL_W,
                             f"residual {res.max():.3f} W at the shipped tolerance {used:g}")


if __name__ == "__main__":
    unittest.main()
