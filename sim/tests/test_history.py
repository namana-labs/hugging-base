"""History days (lane L2; HIST-R2 4): the calendar rule, the load slices, a 60-step three-branch day with gzip branch
files, the derived story and relief text, the money split and cash, and the index row. Runs the simulation on a short
window (OpenDSS every step); under 20 s, no lock."""
import gzip
import json
import math
import re
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from sim.constants import SOC0, RESERVE_FLOOR, CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW, P1_DAY
from sim.contracts import audit_labels, check_envelope, check_shapes
from sim.history import (AUG_NPZ, CACHE, DAYS, HIST_BRANCHES, SLICES, build_calendar, build_day, index_row, month_max,
                         slice_loads, story_for, day_row)
from sim.prices import load as load_prices, onset_d26, discharge_plan, price_at


def gz(p):
    return json.loads(gzip.decompress(Path(p).read_bytes()))


class TestCalendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = build_calendar({P1_DAY: ""})
        d0 = datetime.strptime(cls.cal["from"], "%Y-%m-%d")
        cls.dates = [(d0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(cls.cal["n"])]

    def independent(self, ds):
        """The calendar rule written again, minute by minute: sell the plan, buy it back from the onset."""
        usable = (SOC0 - RESERVE_FLOOR) * CORE_USABLE_KWH * math.sqrt(CORE_RTE)
        onset = onset_d26(ds)[0]
        sold = 0.0
        for ts, m in discharge_plan(ds, onset, usable, CORE_POWER_KW):
            for j in range(m):
                sold += price_at(datetime.strptime(ts, "%Y-%m-%dT%H:%M") + timedelta(minutes=j)) * CORE_POWER_KW / 60 / 1000
        left, t, bought = usable / CORE_RTE, datetime.strptime(onset, "%Y-%m-%dT%H:%M"), 0.0
        while left > 1e-9:
            e = min(left, CORE_POWER_KW / 60)
            bought += price_at(t) * e / 1000
            left -= e
            t += timedelta(minutes=1)
        return sold, bought

    def test_rule_matches_an_independent_count(self):
        for ds in [r["date"] for r in DAYS]:
            k = self.dates.index(ds)
            sold, bought = self.independent(ds)
            self.assertEqual(self.cal["sold"][k], int(round(sold * 100)), ds)
            self.assertEqual(self.cal["bought"][k], int(round(bought * 100)), ds)
            self.assertEqual(self.cal["net"][k], int(round((sold - bought) * 100)), ds)

    def test_columns_gaps_and_headline(self):
        c = self.cal
        for key in ("net", "sold", "bought", "peak", "negMin"):
            self.assertEqual(len(c[key]), c["n"], key)
        self.assertEqual(len(c["mode"]), c["n"])
        self.assertEqual(len(c["peakT"].split()), c["n"])
        _, starts = load_prices()
        self.assertEqual(c["to"], (datetime.strptime(starts[-1][:10], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"))
        # DST spring-forward: no 02:00 interval, so no evening (HIST-R2 3.4); a gap is null, never a guess
        gaps = {g["day"] for g in c["gaps"]}
        self.assertIn("2026-03-08", gaps)
        for i, ds in enumerate(self.dates):
            self.assertEqual(c["net"][i] is None, ds in gaps, ds)
            self.assertEqual(c["mode"][i] == "-", ds in gaps, ds)
        y26 = [x for x, ds in zip(c["net"], self.dates) if x is not None and ds[:4] == "2026"]
        self.assertAlmostEqual(c["headline"]["perBattery2026ytd"]["v"], sum(y26) / 100, places=9)
        self.assertEqual(c["headline"]["losingNights2026"]["v"], sum(1 for x in y26 if x < 0))
        self.assertEqual(c["sim"], {P1_DAY: ""})
        self.assertEqual(audit_labels(c)[0], [])
        self.assertEqual(check_envelope(c), [])

    def test_peak_is_the_d26_peak_price(self):
        k = self.dates.index(P1_DAY)
        _, _, peak, _, _ = onset_d26(P1_DAY)
        self.assertEqual(self.cal["peak"][k], int(round(price_at(peak) * 100)))
        self.assertEqual(self.cal["peakT"].split()[k], peak[11:16].replace(":", ""))


class TestTagsAreTrue(unittest.TestCase):
    """The drawer's editorial tags must hold on the data they describe (no digits; the claim checked where it can be)."""

    def test_tags_have_no_digits(self):
        for r in DAYS:
            self.assertIsNone(re.search(r"\d", r["tag"]), r["tag"])

    def test_priciest_august_evening_is_26_aug(self):
        mx, when = month_max("2026-08-26")
        self.assertEqual(when[:10], "2026-08-26")
        self.assertEqual(day_row("2026-08-26")["why"], "month_max")

    def test_quiet_night_is_non_binding(self):
        # "A quiet night": the evening peak never reaches 2 x the day's median, so D-26 is non-binding
        self.assertEqual(onset_d26("2026-08-14")[4], "non-binding")


class TestSlices(unittest.TestCase):
    def test_august_reads_the_committed_slice(self):
        self.assertEqual(slice_loads("2026-08-26"), AUG_NPZ)

    @unittest.skipUnless(CACHE.is_dir(), "no SMART-DS cache (python3 scripts/fetch_profiles.py --fetch-only)")
    def test_slice_is_byte_identical_and_loads_reads_it(self):
        from sim.loads import Loads
        with tempfile.TemporaryDirectory() as t:
            p = slice_loads("2026-07-22", out_dir=t, force=True)
            committed = SLICES / "2026-07-22.npz"
            if committed.exists():
                self.assertEqual(p.read_bytes(), committed.read_bytes())
            z = np.load(p)
            self.assertEqual(str(z["t0"]), "2026-07-22T00:00")
            self.assertEqual(str(z["source_t0"]), "2018-07-22T00:00")
            aug = np.load(AUG_NPZ)
            self.assertEqual(z["kw"].shape, (aug["kw"].shape[0], 120))
            L = Loads(npz=p)
            kw, kvar = L.at_minute("2026-07-22", 16 * 60)
            self.assertEqual(kw.shape, (2021,))
            self.assertTrue(np.all(np.isfinite(kw)) and kw.sum() > 0)
            with self.assertRaises(IndexError):
                L.at_minute("2026-07-24", 0)                        # outside the 30 h slice


class TestQuickDay(unittest.TestCase):
    """A 60-step history evening (23:00-00:00, across the 23:15 onset): three branches, gzip branch files, no aware_faults anywhere."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="hist-test-")
        cls.r = build_day("2026-08-26", cls.tmp.name, steps=60, start="23:00")
        cls.dir = Path(cls.tmp.name) / "days" / "2026-08-26"
        cls.meta = json.loads((cls.dir / "meta.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_files_and_contract(self):
        names = sorted(p.name for p in self.dir.iterdir())
        self.assertEqual(names, sorted(["meta.json"] + [f"{b}.json.gz" for b in HIST_BRANCHES]))
        m = self.meta
        self.assertEqual(check_envelope(m) + check_shapes("p1/meta.json", m) + audit_labels(m)[0], [])
        for b in HIST_BRANCHES:
            raw = (self.dir / f"{b}.json.gz").read_bytes()
            self.assertEqual(raw[:2], b"\x1f\x8b")
            self.assertEqual(raw[4:8], b"\x00\x00\x00\x00")              # gzip mtime 0: deterministic bytes
            doc = gz(self.dir / f"{b}.json.gz")
            self.assertEqual(check_envelope(doc) + check_shapes(f"p1/{b}.json", doc) + audit_labels(doc)[0], [], b)
            self.assertEqual(len(doc["loading"]), 60)

    def test_three_branches_no_faults(self):
        m = self.meta
        self.assertEqual(m["branches"], list(HIST_BRANCHES))
        self.assertEqual(m["events"], {})
        for block in (m["summary"], m["money"]["energyValueUSD"], m["money"]["systemCapacityPerMonth"],
                      m["money"]["avoidedHarm"], m["money"]["split"], m["cash"]):
            self.assertNotIn("aware_faults", block)
        self.assertEqual(m["day"], "2026-08-26")

    def test_money_split_and_cash(self):
        m = self.meta
        for b in ("naive", "aware"):
            sp = m["money"]["split"][b]
            ev = m["money"]["energyValueUSD"][b]["v"]
            self.assertEqual(sp["net"]["v"], ev)
            self.assertLessEqual(abs(sp["sold"]["v"] - sp["bought"]["v"] - ev), 0.0101)
            self.assertEqual(len(m["cash"][b]), 60)
            self.assertEqual(m["cash"][b][-1], int(round(ev * 100)))
            self.assertTrue(all(isinstance(x, int) for x in m["cash"][b]))
        self.assertEqual(m["series"]["cash"]["label"], "DERIVED")
        self.assertNotIn("none", m["cash"])

    def test_story_and_relief_text_are_derived(self):
        m = self.meta
        self.assertEqual(m["story"]["tag"], "August's priciest evening")
        self.assertIn(m["story"]["why"]["label"], ("REAL", "SIM", "DERIVED", "ASSUMPTION"))
        mo = m["relief"]["minutesOver100"]["none"]
        self.assertNotIn("about 15", m["relief"]["text"])
        self.assertEqual("under its nameplate" in m["relief"]["text"], mo == 0)
        self.assertEqual(any(x["text"].startswith("A peaks") for x in m["markers"]), mo > 0)

    def test_onset_deferral_and_aware_admit_half(self):
        m = self.meta
        od = m["onsetDeferral"]
        runs = self.r["runs"]
        k = od["step"]
        self.assertEqual(od["t"], m["plan"]["onset"])
        self.assertAlmostEqual(od["deferredKW"]["v"], od["naiveKW"]["v"] - od["awareKW"]["v"], places=6)
        self.assertGreater(od["deferredKW"]["v"], 0.0)                 # the feeder check holds charge back at the onset
        self.assertGreater(runs["aware"]["batkw"][k].sum(), 0.0)       # ... and still charges (not safe by doing nothing)
        self.assertEqual(m["summary"]["aware"]["batteryCausedNormal"]["v"], 0)

    def test_index_row(self):
        naive = gz(self.dir / "naive.json.gz")
        row = index_row(self.meta, day_row("2026-08-26"), naive)
        nm = self.meta["summary"]["naive"]["maxLoading"]
        self.assertIn(row["naiveMax"]["tier"], range(6))
        self.assertEqual(row["naiveMax"]["tier"] >= 4, nm["v"] > 150.0)       # the tier at the worst step, from tier[]
        self.assertEqual(row["dir"], "days/2026-08-26")
        self.assertEqual(row["dow"], "Wed")
        self.assertEqual(len(row["sparkline"]), 4)                     # 60 steps = four 15-min intervals
        self.assertEqual(row["perBattery"]["aware"]["v"], self.meta["money"]["split"]["aware"]["perBattery"]["v"])
        self.assertEqual(audit_labels({"summary": row})[0], [])

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as t2:
            build_day("2026-08-26", t2, steps=60, start="23:00")
            for p in sorted(self.dir.iterdir()):
                self.assertEqual(p.read_bytes(), (Path(t2) / "days" / "2026-08-26" / p.name).read_bytes(), p.name)

    def test_story_for_the_default_day(self):
        s = story_for({"day": P1_DAY, "start": "16:00", "steps": 720, "price": [price_at(
            datetime(2026, 8, 23, 16) + timedelta(minutes=k)) for k in range(720)],
            "plan": {"onset": "22:00", "onsetPrice": {"v": price_at("2026-08-23T22:00")}}})
        self.assertEqual(s["tag"], "The evening we know best")
        self.assertIn("21:00", s["why"]["text"])
        self.assertEqual(s["why"]["label"], "REAL")


if __name__ == "__main__":
    unittest.main()
