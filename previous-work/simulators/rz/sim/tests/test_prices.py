import unittest

from sim.prices import price_at, onset_d26, discharge_plan, find_cliffs, load, day_prices
from sim.constants import CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW, SOC0, RESERVE_FLOOR


class PriceTests(unittest.TestCase):
    def test_hour_ending_clock(self):
        # 08/23 hour 22, interval 1 -> 21:00-21:15 -> $566.42 (build prompt 4.3)
        self.assertEqual(price_at("2026-08-23T21:00"), 566.42)
        self.assertEqual(price_at("2026-08-23T21:14"), 566.42)
        self.assertEqual(price_at("2026-08-23T16:45"), 34.47)
        self.assertEqual(price_at("2026-08-23T22:00"), 55.42)

    def test_coverage(self):
        table, starts = load()
        self.assertEqual(len(table), 25148)
        self.assertEqual(starts[0], "2026-01-01T00:00")
        self.assertEqual(starts[-1], "2026-09-19T23:45")
        self.assertEqual(len(day_prices("2026-08-23")), 96)

    def test_onset_table(self):
        cases = {
            "2026-08-23": ("2026-08-23T22:00", 55.42, "2026-08-23T21:00", 74.43, "binding"),
            "2026-08-22": ("2026-08-23T01:45", 50.54, "2026-08-22T23:15", 57.61, "binding"),
            "2026-08-10": ("2026-08-10T19:45", 29.40, "2026-08-10T19:30", 45.78, "non-binding"),
            "2026-08-14": ("2026-08-14T19:00", 28.56, "2026-08-14T18:45", 43.46, "non-binding"),
            "2026-08-15": ("2026-08-15T20:00", 41.21, "2026-08-15T19:45", 46.73, "non-binding"),
            "2026-08-21": ("2026-08-21T19:00", 47.90, "2026-08-21T18:45", 57.00, "non-binding"),
            "2026-08-28": ("2026-08-28T19:00", 37.13, "2026-08-28T18:45", 65.36, "non-binding"),
        }
        for day, (onset, p, peak, thr, mode) in cases.items():
            got = onset_d26(day)
            self.assertEqual(got[0], onset, day)
            self.assertAlmostEqual(got[1], p, places=2, msg=day)
            self.assertEqual(got[2], peak, day)
            self.assertAlmostEqual(got[3], thr, places=2, msg=day)
            self.assertEqual(got[4], mode, day)

    def test_every_august_day_has_an_onset(self):
        for d in range(1, 32):
            onset, p, peak, thr, mode = onset_d26(f"2026-08-{d:02d}")
            self.assertIn(mode, ("binding", "non-binding", "fallback"))
            self.assertGreater(onset, peak)

    def test_discharge_plan_0823(self):
        usable = (SOC0 - RESERVE_FLOOR) * CORE_USABLE_KWH * CORE_RTE ** 0.5   # about 24.4 kWh at the meter
        self.assertAlmostEqual(usable, 24.43, places=1)
        plan = discharge_plan("2026-08-23", "2026-08-23T22:00", usable, CORE_POWER_KW)
        self.assertEqual(plan, [("2026-08-23T21:00", 15), ("2026-08-23T21:15", 15), ("2026-08-23T20:00", 15),
                                ("2026-08-23T19:45", 15), ("2026-08-23T20:15", 13)])

    def test_cliffs_27_and_13(self):
        c = find_cliffs("2026-01-01T00:00", "2026-09-20T00:00")
        self.assertEqual(len(c), 27)
        self.assertEqual(sum(x["evening"] for x in c), 13)
        for x in c:
            self.assertGreaterEqual(x["prev"], 60)
            self.assertLessEqual(x["next"], 0.5 * x["prev"])


if __name__ == "__main__":
    unittest.main()
