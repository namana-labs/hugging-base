"""Money lines (lane L2; build prompt 5.4.6): signs, labels, and local relief never priced."""
import unittest

import numpy as np

from sim.contracts import audit_labels
from sim.money import energy_value_usd, money_block


class TestMoney(unittest.TestCase):
    def test_energy_value_sign(self):
        # 20 kW charging for 60 min at $50/MWh costs $1; discharging earns
        self.assertAlmostEqual(energy_value_usd(np.full((60, 1), 20.0), np.full(60, 50.0), 1 / 60), -1.0)
        self.assertAlmostEqual(energy_value_usd(np.full((60, 1), -20.0), np.full(60, 500.0), 1 / 60), 10.0)

    def test_block_labelled_and_relief_unpriced(self):
        b = money_block({"naive": 10.0, "aware": 12.0}, 1.2, 566.42, 34.47, "21:00", "16:45",
                        {"naive": 1920.0, "aware": 1500.0}, {"naive": {"normalEvents": 3}})
        errs, n = audit_labels({"money": b})
        self.assertEqual(errs, [])
        self.assertEqual(b["costOfAwareness"]["v"], -2.0)
        self.assertIs(b["relief"]["priced"]["v"], False)
        self.assertIsNone(b["transformerReplacementUSD"]["v"])
        # the capacity band prices fleet kW at the price peak only, never the relief
        self.assertAlmostEqual(b["systemCapacityPerMonth"]["naive"]["low"]["v"], 1920.0 * 3.12)
        self.assertNotIn("relief", b["systemCapacityPerMonth"])


if __name__ == "__main__":
    unittest.main()
