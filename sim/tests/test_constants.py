import unittest

from sim import constants as C


class ConstantsTests(unittest.TestCase):
    def test_every_constant_labelled_and_cited(self):
        self.assertGreater(len(C.TAG), 40)
        for name, c in C.TAG.items():
            self.assertIn(c["label"], C.LABELS, name)
            self.assertTrue(c["cite"], name)

    def test_const_rejects_bad_label_and_redefinition(self):
        with self.assertRaises(ValueError):
            C.const("X_TEST_BAD", 1, "SOURCED", "x")
        with self.assertRaises(ValueError):
            C.const("AWARE_MARGIN", 0.5, "ASSUMPTION", "x")

    def test_export_shape(self):
        e = C.export("AWARE_MARGIN")
        self.assertEqual(e, {"AWARE_MARGIN": {"value": 0.95, "label": "ASSUMPTION",
                                              "cite": "four-home-simulation/four_home_constants.py"}})

    def test_ratings_are_real(self):
        self.assertEqual((C.TIER_AMBER_PCT, C.TIER_NORMAL_PCT, C.TIER_EMERGENCY_PCT), (100.0, 110.0, 150.0))
        self.assertEqual(C.TAG["FUSE_PCT"]["label"], "ASSUMPTION")
        self.assertIsNone(C.TRANSFORMER_REPLACEMENT_USD)


if __name__ == "__main__":
    unittest.main()
