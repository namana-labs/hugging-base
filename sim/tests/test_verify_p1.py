"""verify_p1 (lane L2) on the committed ui/data/p1 (skips cleanly before the data exists)."""
import io
import unittest
from contextlib import redirect_stdout

from sim.verify_p1 import P1, main


class TestVerifyP1(unittest.TestCase):
    def test_committed_data_passes_invariants(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main([])
        out = buf.getvalue()
        last = [l for l in out.splitlines() if l.startswith("VERIFY p1:")][-1]
        if not (P1 / "meta.json").exists():
            self.assertTrue(last.startswith("VERIFY p1: SKIP"))
            return
        self.assertEqual(rc, 0, out)
        self.assertTrue(last.startswith("VERIFY p1: PASS"), out)
        self.assertIn("determinism: not checked (run --full)", out)
        for tag in ("plan DERIVED", "labels :", "aware  :", "faults :", "none   :", "naive  :", "relief :", "bridge :",
                    "rotation:", "grid   :", "money  :"):
            self.assertIn(tag, out)


if __name__ == "__main__":
    unittest.main()
