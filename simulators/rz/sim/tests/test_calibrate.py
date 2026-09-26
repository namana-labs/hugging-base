"""Lane L1: sim.calibrate helpers, and a --quick run of the whole calibration (under 20 s, no lock)."""
import contextlib
import io
import unittest

import numpy as np

from sim import calibrate
from sim.loads import Loads


class TestHelpers(unittest.TestCase):
    def test_longest_run(self):
        m = np.array([[1, 0], [1, 1], [0, 1], [1, 1], [1, 1], [1, 0]], dtype=bool)
        np.testing.assert_array_equal(calibrate.longest_run(m), [3, 4])

    def test_frames_are_deterministic_and_naive_is_all_at_once(self):
        L = Loads()
        a = calibrate.frames(L, 96, 7, 10, spread=False)
        b = calibrate.frames(L, 96, 7, 10, spread=False)
        self.assertEqual([(k, s) for k, s, _ in a], [(k, s) for k, s, _ in b])
        kinds = {k for k, _, _ in a}
        self.assertEqual(kinds, {'none', 'naive charge', 'naive discharge'})
        for kind, _, kw in a:
            want = {'none': 0.0, 'naive charge': 20.0, 'naive discharge': -20.0}[kind]
            self.assertTrue(np.all(kw == want))


class TestQuickRun(unittest.TestCase):
    def test_quick_calibration_prints_every_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            calibrate.main(['--quick'])
        text = out.getvalue()
        for head in ('profiles kW 254/254', 'conformance:', 'unity pf:', 'A   tr(r:p1udt9411', '240 tr(r:p1udt15649',
                     'census', 'surrogate vs OpenDSS', 'step: set 2021 loads', 'CALIBRATE: '):
            self.assertIn(head, text)
        unity = next(line for line in text.splitlines() if line.startswith('unity pf:'))
        self.assertIn('[INVARIANT: 80 +/- 3 ok]', unity)


if __name__ == '__main__':
    unittest.main()
