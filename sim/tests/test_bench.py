"""engine.json labels (lane L2; audit L4): timings measured on a shared machine are DERIVED, not SIM, and the load
average lives in the cites, not as a number of its own. relabel() keeps every value."""
import json
import unittest

from sim.bench import OUT, relabel
from sim.contracts import audit_labels, check_envelope


class TestEngineLabels(unittest.TestCase):
    def test_committed_engine_json(self):
        if not OUT.exists():
            self.skipTest("ui/data/engine.json not built")
        doc = json.loads(OUT.read_text())
        self.assertNotIn("loadAvg", doc)
        for grp in ("opendss", "p1", "allocate"):
            for k, x in doc[grp].items():
                self.assertEqual(x["label"], "DERIVED", f"{grp}.{k}")
                self.assertIn("measured on a shared machine", x["cite"], f"{grp}.{k}")
        self.assertEqual(doc["sources"]["machine"]["label"], "DERIVED")
        self.assertEqual(check_envelope(doc) + audit_labels(doc)[0], [])

    def test_relabel_keeps_values_and_is_idempotent(self):
        old = {"schema": "hb.engine.v1", "producer": "sim.bench", "inputs": {}, "constants": {}, "sources": {}, "series": {},
               "opendss": {"msPerSolve": {"v": 2.13, "label": "SIM", "cite": "median ms per OpenDSS solve"}},
               "p1": {"buildSeconds": {"v": 12.7, "label": "SIM", "cite": "last full build"}},
               "allocate": {"96": {"v": 66.6, "label": "SIM", "cite": "us per call"}},
               "loadAvg": {"v": 13.1, "label": "SIM", "cite": "1-minute load average"}}
        a = relabel(json.loads(json.dumps(old)))
        b = relabel(json.loads(json.dumps(a)))
        self.assertEqual(a, b)
        self.assertEqual(a["opendss"]["msPerSolve"]["v"], 2.13)
        self.assertEqual(a["allocate"]["96"]["v"], 66.6)
        self.assertIn("load average 13.1", a["p1"]["buildSeconds"]["cite"])
        self.assertTrue(a["opendss"]["msPerSolve"]["cite"].startswith("median ms per OpenDSS solve; measured"))


if __name__ == "__main__":
    unittest.main()
