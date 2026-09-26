import unittest

from sim.contracts import audit_labels, check_envelope, envelope, labelled, dumps, validate


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

    def test_deterministic_dump_rejects_nan(self):
        self.assertEqual(dumps({"a": 1, "b": [1.5]}), '{"a":1,"b":[1.5]}')
        with self.assertRaises(ValueError):
            dumps({"a": float("nan")})

    def test_committed_data_passes(self):
        failures, n, total, lab = validate(out=lambda *_: None)
        self.assertEqual(failures, [])
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
