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

    def test_head_rating_per_phase_is_one_conductor(self):
        # audit L2: 370 A x 12.47 kV / sqrt(3) = 2,663.8 kVA, a third of the balanced three-phase rating
        self.assertEqual(C.HEAD_RATING_KVA_PER_PHASE, 2663.8)
        self.assertEqual(C.TAG["HEAD_RATING_KVA_PER_PHASE"]["label"], "DERIVED")
        self.assertAlmostEqual(C.HEAD_RATING_KVA_PER_PHASE, C.HEAD_RATING_KVA / 3, delta=0.1)
        self.assertAlmostEqual(40 / C.HEAD_RATING_KVA_PER_PHASE * 100, 1.5, delta=0.01)   # 40 kW is 1.5% of one conductor

    def test_houston_charge_block_is_real_and_cited(self):
        self.assertEqual(C.BASE_HOUSTON_CHARGE_BLOCK_MW, -45.8)
        t = C.TAG["BASE_HOUSTON_CHARGE_BLOCK_MW"]
        self.assertEqual(t["label"], "REAL")
        self.assertIn("within 15 minutes", t["cite"])
        self.assertIn("aggregated-ders-and-the-capacity-crunch", t["cite"])
        self.assertNotIn("15.9", t["cite"])   # the disputed "-15.9 -> -45.8" pairing is not stated (NOTES.md)

    def test_stand_in_cite_names_pedernales(self):
        cite = C.TAG["STAND_IN"]["cite"]
        self.assertIn("Pedernales Electric Cooperative", cite)
        self.assertNotIn("Austin Energy territory", cite)
        self.assertEqual(C.STAND_IN, "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)")


if __name__ == "__main__":
    unittest.main()
