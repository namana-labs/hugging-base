"""verify_p2 on the committed data (skipped before ui/data/p2/index.json exists): every [INVARIANT] line passes."""
import contextlib
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class VerifyP2(unittest.TestCase):
    @unittest.skipUnless((ROOT / "ui" / "data" / "p2" / "index.json").exists(), "no ui/data/p2 yet")
    def test_committed_data_passes(self):
        from sim import verify_p2
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = verify_p2.main([])
        out = buf.getvalue()
        self.assertEqual(rc, 0, out[-2000:])
        self.assertIn("VERIFY p2: PASS", out)
        self.assertIn("determinism: not checked (run --full)", out)
        self.assertNotIn("[INVARIANT: FAIL]", out)


if __name__ == "__main__":
    unittest.main()
