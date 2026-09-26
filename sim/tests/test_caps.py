import unittest

import numpy as np

from sim.caps import transformer_caps


class CapsTests(unittest.TestCase):
    def test_formula(self):
        H, E, R = transformer_caps([10.0, 30.0], [3.0, 0.0], [25.0, 25.0], alpha=0.95)
        room0 = np.sqrt((0.95 * 25) ** 2 - 9.0)
        self.assertAlmostEqual(H[0], room0 - 10)
        self.assertAlmostEqual(E[0], room0 + 10)
        self.assertEqual(R[0], 0.0)
        self.assertAlmostEqual(R[1], 30 - 0.95 * 25)
        self.assertAlmostEqual(H[1], 0.95 * 25 - 30)

    def test_reactive_larger_than_rating(self):
        H, E, R = transformer_caps([0.0], [30.0], [25.0])
        self.assertEqual(H[0], 0.0)
        self.assertEqual(E[0], 0.0)

    def test_vectorised_shape(self):
        H, E, R = transformer_caps(np.zeros((4, 379)), np.zeros((4, 379)), np.full(379, 50.0))
        self.assertEqual(H.shape, (4, 379))
        self.assertTrue(np.allclose(H, 47.5))


if __name__ == "__main__":
    unittest.main()
