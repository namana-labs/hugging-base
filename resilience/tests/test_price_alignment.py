"""Pin the ERCOT price alignment rule sim.prices uses (kickoff B1.2).

ERCOT stamps a settlement point price by the END of its interval (hour-ending 1-24, interval 1-4). A simulation step
that starts at local minute t belongs to the first interval ending strictly after t. sim.prices converts each row to
its interval START and price_at() floors to the interval that contains t; the two rules are the same, and these tests
derive the first one independently from the raw CSV columns (date, hour, interval), never from the file's own
interval_start_local column.
"""
import bisect
import csv
import unittest
from collections import Counter
from datetime import datetime, timedelta

from sim import prices

DAY = "2026-08-23"


def raw_rows():
    with prices.CSV.open() as fh:
        return list(csv.DictReader(fh))


def interval_end(r):
    """End of an ERCOT interval, local, from hour-ending and interval: (hour-1)*60 + interval*15 minutes."""
    d = datetime.strptime(r["date"], "%m/%d/%Y")
    return d + timedelta(minutes=(int(r["hour"]) - 1) * 60 + int(r["interval"]) * 15)


class PriceAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = raw_rows()
        by_end = sorted((interval_end(r), float(r["price"])) for r in cls.rows)
        cls.ends = [e for e, _ in by_end]
        cls.prices = [p for _, p in by_end]

    def first_ending_after(self, t):
        i = bisect.bisect_right(self.ends, t)
        if i == len(self.ends):
            raise KeyError(t)
        return self.prices[i]

    def raw(self, hour, interval, date="08/23/2026"):
        (r,) = [r for r in self.rows if r["date"] == date and int(r["hour"]) == hour and int(r["interval"]) == interval]
        return float(r["price"])

    def test_boundaries_on_the_p1_day(self):
        # 19:59 is inside HE20 interval 4 (19:45-20:00); 20:00 starts HE21 interval 1 (20:00-20:15).
        self.assertEqual(prices.price_at(f"{DAY}T19:59"), self.raw(20, 4))
        self.assertEqual(prices.price_at(f"{DAY}T20:00"), self.raw(21, 1))
        self.assertEqual(prices.price_at(f"{DAY}T20:14"), self.raw(21, 1))
        self.assertEqual(prices.price_at(f"{DAY}T20:15"), self.raw(21, 2))
        self.assertNotEqual(self.raw(20, 4), self.raw(21, 1), "the boundary test needs two different prices")

    def test_every_minute_of_the_p1_window_is_interval_ending(self):
        """16:00 on the 23rd to 04:00 on the 24th, every minute: price_at == the first interval ending after t."""
        t0 = datetime.strptime(f"{DAY}T16:00", prices.FMT)
        for k in range(720):
            t = t0 + timedelta(minutes=k)
            self.assertEqual(prices.price_at(t), self.first_ending_after(t), t)

    def test_every_p2_step_start_is_interval_ending(self):
        """P2 steps are 15 min from 1 Aug 00:00: step k takes the interval ending at its own end."""
        t0 = datetime.strptime("2026-08-01T00:00", prices.FMT)
        for k in range(31 * 96):
            t = t0 + timedelta(minutes=15 * k)
            self.assertEqual(prices.price_at(t), self.first_ending_after(t), t)


class DaylightSaving(unittest.TestCase):
    """The file keys prices by local start time. A skipped hour leaves a gap; a repeated hour would collide."""

    @classmethod
    def setUpClass(cls):
        cls.rows = raw_rows()

    def test_no_two_rows_share_a_local_start(self):
        starts = Counter(r["interval_start_local"] for r in self.rows)
        dup = [k for k, n in starts.items() if n > 1]
        self.assertEqual(dup, [], "prices.load() keeps only the last row per start: see resilience/docs/requests.md")

    def test_no_repeated_hour_rows(self):
        """rep = ERCOT's repeated-hour (DST end) flag. DST ends 1 Nov 2026, after this file (to 19 Sep). If the file
        is extended past it, this fails first: the rep=Y hour maps to the same local start as rep=N."""
        self.assertEqual(Counter(r["rep"] for r in self.rows), Counter({"N": len(self.rows)}))

    def test_spring_forward_skips_the_missing_hour(self):
        """8 Mar 2026: ERCOT publishes no hour-ending 3, so 02:00-02:59 local (which did not exist) has no price."""
        hours = sorted({int(r["hour"]) for r in self.rows if r["date"] == "03/08/2026"})
        self.assertNotIn(3, hours)
        self.assertEqual(sum(1 for r in self.rows if r["date"] == "03/08/2026"), 92)
        with self.assertRaises(KeyError):
            prices.price_at("2026-03-08T02:30")
        prices.price_at("2026-03-08T03:00")

    def test_the_p1_day_and_p2_month_have_no_transition(self):
        for day in [f"2026-08-{d:02d}" for d in range(1, 32)] + ["2026-09-01"]:
            self.assertEqual(len(prices.day_prices(day)), 96, day)


if __name__ == "__main__":
    unittest.main()
