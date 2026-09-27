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

    def test_p1_days_dispatch(self):
        # no index yet: SKIP. With an index, the delegate must handle --days (never a PASS that did not look at the days).
        import tempfile
        import types
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as t:
            missing = Path(t) / "p1" / "days" / "index.json"
            with mock.patch.object(verify, "DAYS_INDEX", missing), mock.patch.object(verify, "UI_DATA", Path(t)):
                rc, out = self.run_main("p1", "--days")
                self.assertEqual(rc, 0)
                # Windows prints p1\days\index.json; compare with forward slashes on every OS
                self.assertRegex(out.replace("\\", "/"), r"(?m)^VERIFY p1: SKIP \(no .*days/index.json yet\)")
            missing.parent.mkdir(parents=True)
            missing.write_text("{}")
            (Path(t) / "p1" / "meta.json").write_text("{}")
            calls = []
            fake = types.SimpleNamespace(main=lambda argv: calls.append(list(argv)) or 0)
            with mock.patch.object(verify, "DAYS_INDEX", missing), mock.patch.dict(verify.DATA, {"p1": Path(t) / "p1" / "meta.json"}), \
                    mock.patch.object(verify, "UI_DATA", Path(t)), \
                    mock.patch.object(verify.importlib, "import_module", return_value=fake):
                with mock.patch.object(verify.inspect, "getsource", return_value="def main(argv): ..."):
                    rc, out = self.run_main("p1", "--days")
                    self.assertEqual(rc, 1)
                    self.assertRegex(out, r"(?m)^VERIFY p1: FAIL \(sim.verify_p1 does not handle --days")
                with mock.patch.object(verify.inspect, "getsource", return_value="if '--days' in argv: ..."):
                    rc, out = self.run_main("p1", "--days", "--rebuild")
                    self.assertEqual((rc, calls), (0, [["--days", "--rebuild"]]))

    def test_usage(self):
        rc, out = self.run_main()
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
