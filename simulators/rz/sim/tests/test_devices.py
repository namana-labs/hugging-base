"""Device rules (lane L2): reserve, taper, seq, expiry. Build prompt 5.4.3 step 8."""
import math
import unittest

import numpy as np

from sim.constants import RESERVE_FLOOR, CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW, COMMAND_TTL_S
from sim.devices import Battery, Command, Device, charge_limit, discharge_limit

DT = 1 / 60


class TestBattery(unittest.TestCase):
    def test_reserve_holds_under_any_discharge(self):
        b = Battery(soc=0.25)
        for _ in range(200):
            b.advance(-CORE_POWER_KW, DT)
        self.assertGreaterEqual(b.soc, RESERVE_FLOOR - 1e-12)
        self.assertEqual(b.limit(-20.0, DT), 0.0)

    def test_stops_at_full_taper(self):
        b = Battery(soc=0.999)
        kw = b.advance(20.0, DT)
        self.assertLess(kw, 20.0)          # the taper: only the room left
        self.assertAlmostEqual(b.soc, 1.0, places=9)
        self.assertEqual(b.advance(20.0, DT), 0.0)

    def test_sqrt_rte_each_leg(self):
        b = Battery(soc=0.5)
        b.advance(20.0, 0.5)               # 10 kWh at the meter
        self.assertAlmostEqual(b.soc, 0.5 + 10 * math.sqrt(CORE_RTE) / CORE_USABLE_KWH, places=12)

    def test_market_plan_energy(self):
        """0.90 -> 0.20 at 20 kW: about 73 minutes (build prompt 5.4.2)."""
        b = Battery(soc=0.90)
        mins = 0
        while b.advance(-20.0, DT) < -1e-9:
            mins += 1
        self.assertIn(mins, (73, 74))

    def test_limits_match_battery(self):
        rng = np.random.default_rng(1)
        for _ in range(500):
            soc = float(rng.uniform(0, 1))
            b = Battery(soc=soc)
            self.assertAlmostEqual(b.limit(99.0, DT), charge_limit(soc, CORE_USABLE_KWH, CORE_POWER_KW, CORE_RTE, DT))
            self.assertAlmostEqual(-b.limit(-99.0, DT), discharge_limit(soc, CORE_USABLE_KWH, CORE_POWER_KW, CORE_RTE, DT))


class TestDevice(unittest.TestCase):
    def test_rejects_non_increasing_seq(self):
        d = Device(Battery(soc=0.5))
        self.assertTrue(d.receive(Command.make(5, 0, 10.0)))
        self.assertFalse(d.receive(Command.make(5, 60, -10.0)))   # equal
        self.assertFalse(d.receive(Command.make(3, 60, -10.0)))   # lower (a late duplicate)
        self.assertEqual(d.rejected, 2)
        self.assertEqual(d.cmd.kw, 10.0)
        self.assertEqual(d.accepted_nonincreasing, 0)

    def test_idles_with_backup_armed_at_expiry(self):
        d = Device(Battery(soc=0.5))
        d.receive(Command.make(1, 0, 10.0))
        for t in range(0, COMMAND_TTL_S, 60):
            kw, s = d.step(t, DT)
            self.assertGreater(kw, 0)
            self.assertEqual(s, "C")
        kw, s = d.step(COMMAND_TTL_S, DT)
        self.assertEqual((kw, s), (0.0, "X"))
        self.assertTrue(d.backup_armed)
        self.assertEqual(d.acted_after_expiry, 0)

    def test_random_command_streams(self):
        """2,000 random deliveries: a device never accepts a non-increasing seq and never acts after expiry."""
        rng = np.random.default_rng(7)
        d = Device(Battery(soc=0.6))
        best = -1
        for step in range(2000):
            t = step * 60
            if rng.random() < 0.7:
                seq = int(rng.integers(0, 3000))
                c = Command.make(seq, t - int(rng.integers(0, 400)), float(rng.uniform(-20, 20)))
                ok = d.receive(c)
                self.assertEqual(ok, seq > best)
                best = max(best, seq) if ok else best
            kw, s = d.step(t, DT)
            if d.cmd is not None and t >= d.cmd.expires_s:
                self.assertEqual(kw, 0.0)
                self.assertEqual(s, "X")
            self.assertGreaterEqual(d.battery.soc, RESERVE_FLOOR - 1e-12)


if __name__ == "__main__":
    unittest.main()
