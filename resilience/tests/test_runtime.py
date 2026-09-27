"""The controller runtime (kickoff B2): lease table, epoch-aware devices, the partition rule and share split, and one
end-to-end build of the fixture window (synthetic loads, OpenDSS every step), in replay and in live mode."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from resilience.constants import LEASE_TTL_S, RUNTIME_PARTITIONS
from resilience.runtime.device import EpochCommand, EpochDevice
from resilience.runtime.lease import LeaseTable
from resilience.runtime.partition import partitions, split_target
from sim.devices import Battery, Device


class Leases(unittest.TestCase):
    def test_grant_bumps_the_epoch_and_expires_after_the_ttl(self):
        L = LeaseTable(["G1", "G2"], 300)
        self.assertEqual(L.grant("G1", "W1", 0), 1)
        self.assertEqual(L.grant("G2", "W2", 0), 1)
        self.assertTrue(L.renew("G1", "W1", 1, 240))
        self.assertEqual(L.expire(299), [])
        self.assertEqual(L.expire(300), [("G2", "W2", 1)])        # G2 never renewed
        self.assertEqual(L.holder("G1"), "W1")                     # renewed at 240: good to 540
        self.assertEqual(L.expire(540), [("G1", "W1", 1)])
        self.assertEqual(L.grant("G2", "W1", 300), 2)

    def test_renewal_by_a_stale_holder_is_refused(self):
        L = LeaseTable(["G1"], 300)
        L.grant("G1", "W1", 0)
        L.expire(300)
        L.grant("G1", "W2", 300)
        self.assertFalse(L.renew("G1", "W1", 1, 330))              # the old holder, the old epoch
        self.assertFalse(L.renew("G1", "W2", 1, 330))              # the right worker, a stale epoch
        self.assertTrue(L.renew("G1", "W2", 2, 330))
        with self.assertRaises(ValueError):
            L.grant("G1", "W3", 330)                                # still leased


def cmd(epoch, seq, kw=5.0, issued=0, ttl=300):
    return EpochCommand(epoch, seq, issued, issued + ttl, kw, "W1", "G1", 0)


class Devices(unittest.TestCase):
    def test_order_is_epoch_then_seq(self):
        d = EpochDevice(Battery(soc=0.5))
        self.assertIsNone(d.deliver(cmd(1, 7), 0))
        self.assertEqual(d.deliver(cmd(1, 7), 0), "nonIncreasingSeq")
        self.assertIsNone(d.deliver(cmd(2, 1), 0))                   # a new epoch: seq restarts
        self.assertEqual(d.deliver(cmd(1, 99), 0), "staleEpoch")     # the old holder, however high its seq
        self.assertEqual(d.deliver(cmd(2, 2, issued=0, ttl=60), 60), "expired")
        self.assertEqual(d.by_reason, {"staleEpoch": 1, "nonIncreasingSeq": 1, "expired": 1})
        self.assertEqual(d.accepted_nonincreasing, 0)

    def test_the_device_still_never_acts_on_an_expired_command_or_below_the_reserve(self):
        d = EpochDevice(Battery(soc=0.201))
        d.deliver(cmd(1, 1, kw=-20.0, issued=0, ttl=120), 0)
        kw, st = d.step(0, 1 / 60)
        self.assertLessEqual(-kw, 20.0)
        self.assertGreaterEqual(d.battery.soc, 0.2)
        self.assertEqual(d.step(120, 1 / 60), (0.0, "X"))

    def test_a_seq_only_device_gets_the_takeover_wrong_both_ways(self):
        """sim.devices.Device (no epoch) after a takeover: it refuses the new holder, whose seq restarted, and accepts
        the old holder's late command, whose seq is higher. The epoch fixes both."""
        old_last, late, new_first = cmd(1, 500), cmd(1, 501), cmd(2, 1)
        seq_only = Device(Battery(soc=0.5))
        self.assertTrue(seq_only.receive(old_last.seq_only()))
        self.assertFalse(seq_only.receive(new_first.seq_only()))
        self.assertTrue(seq_only.receive(late.seq_only()))
        ep = EpochDevice(Battery(soc=0.5))
        self.assertIsNone(ep.deliver(old_last, 0))
        self.assertIsNone(ep.deliver(new_first, 0))
        self.assertEqual(ep.deliver(late, 0), "staleEpoch")


class Partitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        topo = json.loads((Path(__file__).resolve().parents[2] / "ui" / "data" / "topology.json").read_text())
        cls.topo = topo
        cls.tf = np.array([topo["homes"][h]["tf"] for h in topo["fleet"]])

    def test_every_battery_in_exactly_one_group_and_no_transformer_split(self):
        parts = partitions(self.tf, RUNTIME_PARTITIONS)
        self.assertEqual(len(parts), RUNTIME_PARTITIONS)
        self.assertEqual(sorted(i for p in parts for i in p["batts"]), list(range(len(self.tf))))
        tfs = [t for p in parts for t in p["tfs"]]
        self.assertEqual(len(tfs), len(set(tfs)))
        sizes = [len(p["batts"]) for p in parts]
        self.assertLessEqual(max(sizes) - min(sizes), 4, sizes)
        a = next(f["tf"] for f in self.topo["focus"] if f["key"] == "A")
        self.assertEqual(sum(a in p["tfs"] for p in parts), 1)

    def test_split_caps_at_headroom_and_hands_the_rest_on(self):
        tf = np.array([0, 0, 1, 1, 2, 2])
        parts = [{"id": "G1", "tfs": [0], "batts": [0, 1]}, {"id": "G2", "tfs": [1], "batts": [2, 3]},
                 {"id": "G3", "tfs": [2], "batts": [4, 5]}]
        kva = np.array([25.0, 100.0, 100.0])
        bg_kw = np.array([20.0, 10.0, 10.0])          # G1's transformer has little room left
        n = len(tf)
        soc = np.full(n, 0.5)
        args = dict(soc_t=soc, soc=soc, pmax=np.full(n, 20.0), emax=np.full(n, 37.0), rte=np.full(n, 0.89),
                    tf_of_batt=tf, bg_kw=bg_kw, bg_kvar=np.zeros(3), kva=kva, dt_h=1 / 60, minutes_left=240,
                    heard=np.ones(n, dtype=bool))
        from sim.orchestrator import charge_target
        T = charge_target(soc, args["emax"], args["rte"], 240)
        served = {"G1": True, "G2": True, "G3": True}
        sh = split_target("charge", T, parts, served, np.zeros(n), **args)
        self.assertLess(sh["G1"], T / 3)                              # capped by A's-style headroom
        self.assertAlmostEqual(sum(sh.values()), T, places=6)             # the fleet target is still met
        self.assertGreater(sh["G2"], T / 3)                           # G2 and G3 take what G1 could not
        booked = np.array([0, 0, 15.0, 15.0, 0, 0])
        sh2 = split_target("charge", T, parts, {"G1": True, "G2": False, "G3": True}, booked, **args)
        self.assertEqual(sh2["G2"], 0.0)                              # unserved: booked at telemetry, no share


class EndToEnd(unittest.TestCase):
    """The fixture window through OpenDSS: replay twice (determinism) and live once (real processes)."""

    @classmethod
    def setUpClass(cls):
        from resilience.runtime.build import build
        cls.tmp = tempfile.TemporaryDirectory(prefix="runtime-test-")
        cls.a = build("fixture", out=Path(cls.tmp.name) / "a", quiet=True)
        cls.doc = cls.a["doc"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_takeover_story(self):
        s, rt = self.doc["summary"], self.doc["runtime"]
        self.assertLessEqual(s["takeoverSeconds"]["v"], LEASE_TTL_S)
        self.assertGreater(rt["late"]["commands"], 0)
        self.assertEqual(rt["late"]["rejected"]["staleEpoch"], rt["late"]["commands"])
        self.assertEqual(rt["late"]["unexpiredOnArrival"], rt["late"]["commands"])
        for k in ("reserveBreaches", "actedAfterExpiry", "nonIncreasingAccepted", "batteryCausedNormal",
                  "batteryCausedEmergency", "protectionOperated"):
            self.assertEqual(s[k]["v"], 0, k)

    def test_the_file_passes_the_contract_checks(self):
        from resilience.runtime.verify import contract_errors
        errs, n, _ = contract_errors(self.doc)
        self.assertEqual(errs, [])
        self.assertTrue(self.doc["fixture"])
        self.assertGreater(n, 20)

    def test_rebuild_is_byte_identical(self):
        from resilience.runtime.build import build, REL
        b = build("fixture", out=Path(self.tmp.name) / "b", quiet=True)
        self.assertEqual(Path(b["path"]).read_bytes(), Path(self.a["path"]).read_bytes())

    def test_live_mode_kills_a_real_process_and_matches_the_replay(self):
        from resilience.runtime.build import build
        c = build("fixture", out=Path(self.tmp.name) / "live", live=True, quiet=True)
        rec = c["doc"]["recorded"]
        self.assertEqual(rec["startMethod"], "spawn")
        self.assertFalse(rec["killed"]["aliveAfter"])
        self.assertIsNotNone(rec["killed"]["exitcode"])
        self.assertEqual(sum(rec["missedHeartbeats"].values()), 0, rec)   # the only missing replies are the dead worker's
        self.assertEqual(c["doc"]["batKW"], self.doc["batKW"])
        self.assertEqual(c["doc"]["runtime"]["holder"], self.doc["runtime"]["holder"])


if __name__ == "__main__":
    unittest.main()
