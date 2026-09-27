import gzip
import json
import tempfile
import unittest
from pathlib import Path

from sim.contracts import (UI_DATA, audit_labels, check_envelope, check_shapes, envelope, labelled, dumps, read_json_any,
                           validate, write_json_gz)


class ContractTests(unittest.TestCase):
    def test_bare_headline_number_fails(self):
        doc = envelope("x", "sim.test", inputs={"prices_sha256": None, "loads_sha256": None, "topology_sha256": None})
        doc["summary"] = {"naive": {"normalEvents": 3}}
        errs, _ = audit_labels(doc)
        self.assertEqual(len(errs), 1)
        doc["summary"] = {"naive": {"normalEvents": labelled(3, "SIM"), "maxLoading": labelled(197.0, "SIM", tf=150, t="22:30")}}
        errs, n = audit_labels(doc)
        self.assertEqual(errs, [])
        self.assertEqual(n, 2)

    def test_scale_ladder_is_a_headline_key(self):
        rung = {"scale": "ercot", "name": "ERCOT", "base": labelled(81612.0, "REAL", unit="MW", at="2026-09-25 16:40 CT"),
                "sharePct": labelled(4.9e-05, "DERIVED"), "text": "40 kW is 0.000049% of ERCOT"}
        doc = {"scaleLadder": {"text": "t", "kw": labelled(40.0, "DERIVED"), "rungs": [rung]}}
        errs, n = audit_labels(doc)
        self.assertEqual(errs, [])
        self.assertEqual(n, 3)
        doc["scaleLadder"]["rungs"][0]["sharePct"] = 4.9e-05
        errs, _ = audit_labels(doc)
        self.assertEqual(len(errs), 1)
        self.assertIn("bare headline number", errs[0])

    def test_bad_label_fails(self):
        with self.assertRaises(ValueError):
            labelled(1, "SOURCED")
        errs, _ = audit_labels({"money": {"x": {"v": 1, "label": "GUESS"}}})
        self.assertTrue(errs)

    def test_ids_and_arrays_allowed(self):
        errs, _ = audit_labels({"ranking": [{"rank": 1, "home": 5, "tf": 7, "peakWithPct": labelled(90.1, "SIM")}],
                                "loading": [[1, 2], [3, 4]]})
        self.assertEqual(errs, [])

    def test_envelope_checks(self):
        self.assertTrue(check_envelope({"schema": "hb.x.v1"}))
        doc = envelope("x", "sim.test", inputs={"prices_sha256": None, "loads_sha256": None, "topology_sha256": None},
                       constants={"A": {"value": 1, "label": "ASSUMPTION", "cite": "c"}})
        self.assertEqual(check_envelope(doc), [])
        doc["constants"]["B"] = {"value": 1, "label": "ASSUMPTION"}
        self.assertTrue(check_envelope(doc))

    def test_producer_sim_or_scripts(self):
        inputs = {"prices_sha256": None, "loads_sha256": None, "topology_sha256": None}
        for ok in ("sim.p1_build", "scripts.fetch_footprints"):
            self.assertEqual(check_envelope(envelope("x", ok, inputs=inputs)), [], ok)
        for bad in ("scripts/fetch_footprints.py", "ui.fetch", "sim.", "Sim.x", "sim.x.y", "handwritten"):
            self.assertTrue(check_envelope(envelope("x", bad, inputs=inputs)), bad)

    def test_deterministic_dump_rejects_nan(self):
        self.assertEqual(dumps({"a": 1, "b": [1.5]}), '{"a":1,"b":[1.5]}')
        with self.assertRaises(ValueError):
            dumps({"a": float("nan")})

    def test_committed_data_passes(self):
        failures, n, total, lab = validate(out=lambda *_: None)
        self.assertEqual(failures, [])
        self.assertGreater(n, 0)



def _history_day(root, date="2026-07-22"):
    """A scratch history day built from the committed 23 Aug files (plumbing only: its numbers are 23 Aug's)."""
    meta = json.loads((UI_DATA / "p1" / "meta.json").read_text())
    meta.update(day=date, branches=["none", "naive", "aware"], events={})
    d = Path(root) / "p1" / "days" / date
    d.mkdir(parents=True)
    (d / "meta.json").write_text(dumps(meta))
    naive = json.loads((UI_DATA / "p1" / "naive.json").read_text())
    write_json_gz(d / "naive.json.gz", naive)
    return d, naive


class HistoryContractTests(unittest.TestCase):
    """l0-c (UX_SPEC_R2 4.3): gzipped history days are decompressed and judged like any other file."""

    def test_write_json_gz_is_deterministic(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t, "a.json.gz"), Path(t, "b.json.gz")
            doc = {"x": [1, 2.5], "y": "z"}
            write_json_gz(a, doc)
            write_json_gz(b, doc)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(a.read_bytes()[:2], b"\x1f\x8b")
            self.assertEqual(a.read_bytes()[4:8], b"\x00\x00\x00\x00", "mtime 0")
            self.assertEqual(read_json_any(a), doc)

    def test_a_history_day_passes_and_counts_bytes_on_disk(self):
        with tempfile.TemporaryDirectory() as t:
            d, _ = _history_day(t)
            lines = []
            failures, n, total, _ = validate(t, out=lines.append)
            self.assertEqual(failures, [], "\n".join(lines))
            self.assertEqual(n, 2)
            self.assertEqual(total, (d / "meta.json").stat().st_size + (d / "naive.json.gz").stat().st_size)
            self.assertLess((d / "naive.json.gz").stat().st_size, (UI_DATA / "p1" / "naive.json").stat().st_size / 3)

    def test_the_admit_half_a_bad_gz_day_fails(self):
        # a bare headline number inside a gz file, a corrupt gz, a faults branch on a history day, an unknown file
        with tempfile.TemporaryDirectory() as t:
            d, naive = _history_day(t)
            naive["summary"] = {"x": {"normalEvents": 3}}
            write_json_gz(d / "naive.json.gz", naive)
            (d / "aware.json.gz").write_bytes(b"\x1f\x8bnot really gzip")
            meta = json.loads((d / "meta.json").read_text())
            meta["branches"].append("aware_faults")
            (d / "meta.json").write_text(dumps(meta))
            (d / "notes.json").write_text(dumps(envelope("x", "sim.test")))
            failures, _, _, _ = validate(t, out=lambda *_: None)
            # Windows returns p1\days\...; compare with forward slashes on every OS
            self.assertEqual(sorted(x.replace("\\", "/") for x in failures), sorted([f"p1/days/2026-07-22/{f}" for f in ("naive.json.gz", "aware.json.gz", "meta.json", "notes.json")]))

    def test_index_and_calendar_shapes(self):
        row = {"date": "2026-08-23", "dow": "Sun", "tag": "The demo evening", "why": {"text": "t", "label": "REAL"}, "dir": "",
               "branches": ["none", "naive", "aware", "aware_faults"], "peak": labelled(566.42, "REAL", t="21:00"),
               "perBattery": {"aware": labelled(9.55, "DERIVED")}, "naiveMax": labelled(201.2, "SIM", tf="A", t="22:30"),
               "awareBatteryCaused": labelled(0, "SIM"), "sparkline": [1.0] * 48}
        idx = dict(envelope("p1-days-index", "sim.history"), series={"sparkline": {"label": "REAL", "unit": "$/MWh"}},
                   days=[row, dict(row, date="2026-07-22", dir="days/2026-07-22", branches=["none", "naive", "aware"])])
        self.assertEqual(check_shapes("p1/days/index.json", idx), [])
        bad = json.loads(json.dumps(idx))
        bad["days"][1].update(tag="Record 91 GW", sparkline=[1.0] * 47)
        self.assertEqual(len(check_shapes("p1/days/index.json", bad)), 2)
        bad = json.loads(json.dumps(idx))
        bad["days"].reverse()
        self.assertTrue(check_shapes("p1/days/index.json", bad), "row 0 must be 23 Aug")
        cal = dict(envelope("p1-days-calendar", "sim.history"), n=2, net=[1, None], sold=[2, None], bought=[1, None], peak=[5, None],
                   negMin=[0, 0], peakT="2100 -", onset="2200 -", mode="b-", sim={"2026-08-23": ""},
                   series={k: {"label": "DERIVED"} for k in ("net", "sold", "bought", "peak", "negMin")})
        self.assertEqual(check_shapes("p1/days/calendar.json", cal), [])
        self.assertTrue(check_shapes("p1/days/calendar.json", dict(cal, mode="bx")))

    def test_the_old_branch_rule_does_not_swallow_history_files(self):
        # before round 2, any p1/*.json but meta/chaos was judged as a branch doc; index/calendar/day metas are not
        self.assertEqual(check_shapes("p1/days/2026-07-22/meta.json.gz"[:-3], {"steps": 1, "price": [1], "branches": ["none"],
                                      "summary": {}, "day": "2026-07-22", "events": {}}), [])


if __name__ == "__main__":
    unittest.main()
