"""Power balance on one P1 snapshot (RZ adopt-now #4, TEAMMATES_REVIEW): with the 96 batteries charging, the power
into the feeder head equals every load's kW (homes + batteries) plus the losses, within 100 W. OpenDSS every value;
one solve, under a second, no lock."""
import unittest

import numpy as np
from opendssdirect import dss

from sim.constants import CORE_POWER_KW
from sim.feeder import Feeder, N_LOADS
from sim.loads import Loads


class TestPowerBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = Feeder()
        cls.loads = Loads()
        kw, kvar = cls.loads.at_minute("2026-08-23", 22 * 60)        # the D-26 onset minute of the P1 evening
        cls.set_home_kw = float(kw.sum())
        cls.f.set_loads(kw, kvar)
        cls.bat = np.full(len(cls.f.fleet), CORE_POWER_KW)           # every battery charging at full power
        cls.f.set_batteries(cls.bat)
        cls.r = cls.f.solve()
        home, batt, batt_q = 0.0, 0.0, 0.0
        for name in dss.Loads.AllNames():
            dss.Circuit.SetActiveElement("Load." + name)
            pw = dss.CktElement.Powers()
            p, q = sum(pw[0::2]), sum(pw[1::2])
            if name.lower().startswith("bat_"):
                batt += p
                batt_q += q
            else:
                home += p
        cls.home_kw, cls.batt_kw, cls.batt_kvar = home, batt, batt_q
        cls.losses_kw = dss.Circuit.Losses()[0] / 1000.0

    def test_head_equals_loads_plus_losses(self):
        head = self.r["feeder_kw"]
        balance = head - (self.home_kw + self.batt_kw + self.losses_kw)
        self.assertLess(abs(balance) * 1000.0, 100.0,
                        f"head {head:.3f} kW vs homes {self.home_kw:.3f} + batteries {self.batt_kw:.3f} + losses "
                        f"{self.losses_kw:.3f} kW: off by {balance * 1000:.1f} W")
        self.assertGreater(self.losses_kw, 0.0)

    def test_batteries_draw_what_was_set_at_unity_pf(self):
        self.assertAlmostEqual(self.batt_kw, float(self.bat.sum()), delta=0.1)
        self.assertLess(abs(self.batt_kvar), 0.1)                     # BATTERY_PF 1.0 (the 0.88 pf fix)

    def test_home_loads_are_the_profile_kw(self):
        # constant-PQ loads (model=1): OpenDSS draws what sim.loads set, so the balance is not a tautology of set values
        self.assertAlmostEqual(self.home_kw, self.set_home_kw, delta=0.1)
        self.assertEqual(dss.Loads.Count(), N_LOADS + len(self.f.homes))

    def test_head_current_is_the_reported_head(self):
        self.assertGreater(self.r["head_amps"], 0.0)
        self.assertGreater(self.r["feeder_kw"], self.batt_kw)


if __name__ == "__main__":
    unittest.main()
