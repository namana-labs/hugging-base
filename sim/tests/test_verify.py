import io
import unittest
from contextlib import redirect_stdout

from sim import verify


class VerifyTests(unittest.TestCase):
    def run_main(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = verify.main(list(argv))
        return rc, buf.getvalue()

    def test_labels_pass_on_committed_data(self):
        rc, out = self.run_main("labels")
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"(?m)^VERIFY labels: PASS")

    def test_p1_p2_verdict_line(self):
        for part in ("p1", "p2"):
            rc, out = self.run_main(part)
            self.assertRegex(out, rf"(?m)^VERIFY {part}: (PASS|SKIP|FAIL)")

    def test_usage(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
