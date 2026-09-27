"""The covert channel and its detector (kickoff B3): the carrier, the detector's three tests on synthetic series, and
one end-to-end build of the fixture window."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from resilience.constants import COVERT_SYMBOL_MIN, DETECT_WINDOW_MIN, MODULATION_KW
from resilience.detect.attack import Carrier, CompromisedDevice, message_bits
from resilience.detect.detector import PeerDetector, carrier_amp, lag1, peer_sets
from resilience.runtime.device import EpochCommand
from sim.devices import Battery

ROOT = Path(__file__).resolve().parents[2]


class CarrierTests(unittest.TestCase):
    def test_sign_every_minute_and_one_bit_per_symbol(self):
        c = Carrier(600, [1, 0])
        self.assertEqual(c.offset(599), 0.0)
        got = [c.offset(600 + 60 * j) for j in range(2 * COVERT_SYMBOL_MIN)]
        a = MODULATION_KW
        self.assertEqual(got[:COVERT_SYMBOL_MIN], [a, -a, a, -a, a])
        # the 0 bit flips the phase: minute 5 repeats minute 4's sign instead of continuing the carrier
        continued = [a * (-1) ** j for j in range(COVERT_SYMBOL_MIN, 2 * COVERT_SYMBOL_MIN)]
        self.assertEqual(got[COVERT_SYMBOL_MIN:], [-x for x in continued])

    def test_message_is_seeded(self):
        self.assertEqual(message_bits(16), message_bits(16))

    def test_compromised_device_follows_the_command_plus_the_offset_inside_the_limits(self):
        d = CompromisedDevice(Battery(soc=0.5), carrier=Carrier(0, [1]))
        d.deliver(EpochCommand(1, 1, 0, 300, 10.0, "W1", "G1", 0), 0)
        kw, st = d.step(0, 1 / 60)
        self.assertAlmostEqual(kw, 10.0 + MODULATION_KW)
        d2 = CompromisedDevice(Battery(soc=0.2), carrier=Carrier(0, [0]))    # at the reserve: cannot discharge
        d2.deliver(EpochCommand(1, 1, 0, 300, 0.0, "W1", "G1", 0), 0)
        kw, _ = d2.step(0, 1 / 60)
        self.assertGreaterEqual(kw, 0.0)
        self.assertGreaterEqual(d2.battery.soc, 0.2)


class DetectorMath(unittest.TestCase):
    def test_a_smooth_shortfall_never_looks_like_a_carrier(self):
        taper = -np.linspace(0.5, 4.0, DETECT_WINDOW_MIN)          # a charge taper: large and smooth
        self.assertGreater(lag1(taper), 0.9)
        keyed = MODULATION_KW * np.array([(-1) ** j for j in range(DETECT_WINDOW_MIN)])
        self.assertLess(lag1(keyed), -0.9)

    def test_carrier_amplitude(self):
        z = 3e-4 * np.array([(-1) ** j for j in range(DETECT_WINDOW_MIN)]) + np.linspace(0, 0.01, DETECT_WINDOW_MIN)
        self.assertAlmostEqual(float(carrier_amp(z)), 3e-4, delta=0.5e-4)   # the ramp does not leak in
        self.assertLess(float(carrier_amp(np.linspace(0, 0.01, DETECT_WINDOW_MIN))), 1e-12)

    def test_peer_sets_widen_only_when_needed(self):
        topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text(encoding="utf-8"))
        ps = peer_sets(topo["fleet"], topo["homes"], topo["transformers"])
        for h, (peers, rule) in zip(topo["fleet"], ps):
            self.assertNotIn(h, peers)
            self.assertGreaterEqual(len(peers), 5)
            own = len(topo["transformers"][topo["homes"][h]["tf"]]["homes"]) - 1
            self.assertEqual(rule, "transformer" if own >= 5 else "widened")

    def test_the_detector_needs_all_three(self):
        topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text(encoding="utf-8"))
        fleet = topo["fleet"][:2]
        det = PeerDetector(fleet, topo["homes"], topo["transformers"], [1, 2])
        v = np.full(len(topo["homes"]), 1.0)
        for k in range(DETECT_WINDOW_MIN + 2):
            s = (-1) ** k
            kw = np.array([MODULATION_KW * s, MODULATION_KW * s])       # both units oscillate in telemetry
            vk = v.copy()
            vk[fleet[0]] -= 3e-4 * s                                     # only unit 0's own voltage carries it
            det.update(k, kw, np.zeros(2), vk)
        self.assertIn(0, det.first)
        self.assertNotIn(1, det.first)                                   # a telemetry-only oscillation is not enough


class EndToEnd(unittest.TestCase):
    def test_fixture_window(self):
        from resilience.detect.build import build
        with tempfile.TemporaryDirectory(prefix="covert-test-") as tmp:
            s = build("fixture", out=tmp, quiet=True)["doc"]["summary"]
        self.assertEqual(s["falsePositivesClean"]["v"], 0)
        self.assertEqual(s["falsePositivesAttack"]["v"], 0)
        self.assertEqual(s["detected"]["v"], s["shard"]["v"])
        self.assertEqual(s["quarantinedCompromised"]["v"], s["quarantined"]["v"])
        self.assertEqual(s["reserveBreaches"]["v"], 0)
        self.assertEqual(s["fixedThresholdCompromised"]["v"], 0)


if __name__ == "__main__":
    unittest.main()
