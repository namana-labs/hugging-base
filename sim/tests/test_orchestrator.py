"""allocate() and the controller (lane L2): property tests over 2,000 random states, the rotation rule, dwell, cover.
Build prompt 5.4.3 and section 6 ("L2's property tests")."""
import unittest

import numpy as np

from sim.caps import transformer_caps
from sim.constants import AWARE_MARGIN, RESERVE_FLOOR, CORE_RTE, LEGACY_RTE, MIN_GRANT_KW
from sim.devices import Battery, Device
from sim.orchestrator import allocate, AllocState, Controller, handoffs, charge_target

DT = 1 / 60


def random_state(rng, n_tf=12, m=30):
    kva = rng.choice([25.0, 50.0, 75.0], size=n_tf)
    bg_kw = rng.uniform(-0.2, 1.25, size=n_tf) * kva
    bg_kvar = rng.uniform(0.0, 0.45, size=n_tf) * np.abs(bg_kw)
    tf = rng.integers(0, n_tf, size=m)
    soc = rng.uniform(0.0, 1.0, size=m)
    pmax = rng.choice([20.0, 11.4], size=m)
    emax = np.where(pmax == 20.0, 37.0, 22.5)
    mode = str(rng.choice(["charge", "discharge", "idle"]))
    target = float(rng.uniform(0, 1.2) * pmax.sum()) * (1 if mode == "charge" else -1)
    return bg_kw, bg_kvar, kva, tf, soc, pmax, emax, target, mode


class TestAllocateProperties(unittest.TestCase):
    def check(self, rng, state_factory=None):
        bg_kw, bg_kvar, kva, tf, soc, pmax, emax, target, mode = random_state(rng)
        st = state_factory(len(tf)) if state_factory else None
        rte = np.where(pmax == 20.0, CORE_RTE, LEGACY_RTE)
        kw, (H, E, R), _ = allocate(bg_kw, bg_kvar, kva, tf, soc, pmax, emax, target, mode, state=st, cover=False,
                                    rte=rte)
        per_tf = np.bincount(tf, weights=kw, minlength=len(kva))
        net = bg_kw + per_tf
        s_after = np.hypot(net, bg_kvar)
        s_before = np.hypot(bg_kw, bg_kvar)
        lim = AWARE_MARGIN * kva
        for t in range(len(kva)):
            if R[t] <= 1e-9 and s_before[t] <= lim[t] + 1e-9:
                # never pushes a transformer past alpha x kVA in either direction (controller view)
                self.assertLessEqual(s_after[t], lim[t] + 1e-6, (mode, t))
            else:
                self.assertLessEqual(s_after[t], s_before[t] + 1e-6, (mode, t))   # never makes an overload worse
            self.assertGreaterEqual(net[t], -np.sqrt(max(0, lim[t] ** 2 - bg_kvar[t] ** 2)) - 1e-6)
        # the reserve holds, full stops, ratings hold
        for i in range(len(tf)):
            b = Battery(soc=float(soc[i]), cls="core" if pmax[i] == 20.0 else "legacy")
            self.assertAlmostEqual(b.limit(kw[i], DT), kw[i], places=9)
            b.advance(kw[i], DT)
            self.assertGreaterEqual(b.soc, min(soc[i], RESERVE_FLOOR) - 1e-12)
            if soc[i] <= RESERVE_FLOOR:
                self.assertGreaterEqual(kw[i], 0.0)
            self.assertLessEqual(abs(kw[i]), pmax[i] + 1e-9)
            self.assertTrue(kw[i] == 0 or abs(kw[i]) >= MIN_GRANT_KW - 1e-9)
        # sum <= target (relief discharge is outside the charge target)
        if mode == "charge":
            self.assertLessEqual(kw[kw > 0].sum(), target + 1e-6)
        relief = sum(-kw[i] for i in range(len(tf)) if kw[i] < 0 and R[tf[i]] > 0)
        if mode == "discharge":
            self.assertLessEqual(-kw[kw < 0].sum(), max(abs(target), relief) + 1e-6)
        if mode == "idle":
            self.assertTrue(np.all(kw <= 0))

    def test_2000_random_states_stateless(self):
        rng = np.random.default_rng(20260926)
        for _ in range(2000):
            self.check(rng)

    def test_2000_random_states_stateful(self):
        rng = np.random.default_rng(99)
        for _ in range(2000):
            self.check(rng, state_factory=lambda m: AllocState(m))

    def test_grant_in_turn_lowest_bucket_first_no_equal_split(self):
        kva = np.array([25.0])
        # H = 0.95*25 - 4 = 19.75 kW: fits one battery at a time
        kw, (H, _, _), _ = allocate(np.array([4.0]), np.array([0.0]), kva, np.zeros(4, int),
                                    np.array([0.50, 0.30, 0.31, 0.29]), 20.0, 37.0, 80.0, "charge")
        self.assertAlmostEqual(H[0], 19.75)
        # buckets: 0.30 and 0.31 -> 15, 0.29 -> 14 ; lowest bucket first: battery 3 takes all the room
        self.assertAlmostEqual(kw[3], 19.75)
        self.assertEqual(list(kw[:3]), [0.0, 0.0, 0.0])

    def test_relief_overrides_market(self):
        kva = np.array([25.0, 25.0])
        bg = np.array([30.0, 5.0])     # tf 0 above 0.95 x 25 = 23.75
        kw, (_, _, R), _ = allocate(bg, np.zeros(2), kva, np.array([0, 0, 1]), np.array([0.9, 0.8, 0.9]), 20.0, 37.0,
                                    40.0, "charge")
        self.assertAlmostEqual(R[0], 6.25)
        self.assertAlmostEqual(kw[0], -6.25)   # highest SoC relieves first, just enough
        self.assertEqual(kw[1], 0.0)
        self.assertGreater(kw[2], 0)

    def test_discharge_capped_by_export_headroom(self):
        kva = np.array([25.0])
        kw, (_, E, _), _ = allocate(np.array([5.0]), np.array([0.0]), kva, np.zeros(2, int), np.array([0.9, 0.9]),
                                    20.0, 37.0, -40.0, "discharge")
        self.assertAlmostEqual(E[0], 28.75)
        self.assertAlmostEqual(-kw.sum(), 28.75)


def run_rotation(dwell, steps=60, n=4):
    """Four batteries on one 25 kVA transformer whose H fits one at a time; returns the hand-off count."""
    ctl = Controller(np.zeros(n, int), [20.0] * n, [37.0] * n, [CORE_RTE] * n, [f"b{i}" for i in range(n)],
                     dwell_min=dwell)
    devs = [Device(Battery(soc=0.30 + 0.001 * i)) for i in range(n)]
    kva = np.array([25.0])
    hist = np.zeros((steps, n))
    for k in range(steps):
        t = k * 60
        soc = np.array([d.battery.soc for d in devs])
        tgt = 80.0
        kw, _, _, cmds = ctl.tick(k, t, np.ones(n, bool), soc, np.array([4.0]), np.array([0.0]), kva, "charge", tgt)
        for i, c in cmds.items():
            devs[i].receive(c)
        for i, d in enumerate(devs):
            hist[k, i], _ = d.step(t, DT)
    return handoffs(hist)[0], hist


class TestRotationAndDwell(unittest.TestCase):
    def test_dwell_changes_handoff_count(self):
        """The judge's check (build prompt 5.4.3 step 5, section 9): MIN_DWELL_MIN 5 vs 15 gives different counts."""
        h5, hist5 = run_rotation(5)
        h15, _ = run_rotation(15)
        self.assertGreaterEqual(h5, 3)
        self.assertNotEqual(h5, h15)
        self.assertGreater(h5, h15)
        # one at a time: the transformer's H (19.75 kW) is never exceeded
        self.assertLessEqual(hist5.sum(axis=1).max(), 19.75 + 1e-6)

    def test_charge_target(self):
        soc = np.array([0.2, 0.2])
        t = charge_target(soc, [37.0, 37.0], CORE_RTE, 360)
        need = 2 * 0.8 * 37.0 / np.sqrt(CORE_RTE)
        self.assertAlmostEqual(t, need / 6 * 1.2)


class TestStaleAndCover(unittest.TestCase):
    def test_silent_unit_booked_until_expiry_then_covered(self):
        n = 2
        ctl = Controller(np.zeros(n, int), [20.0] * n, [37.0] * n, [CORE_RTE] * n, ["a", "b"], dwell_min=5)
        devs = [Device(Battery(soc=0.30)), Device(Battery(soc=0.40))]
        kva = np.array([25.0])
        heard = np.ones(n, bool)
        states = []
        hist = []
        s = 3
        for k in range(12):
            t = k * 60
            soc = np.array([d.battery.soc for d in devs])
            kw, _, _, cmds = ctl.tick(k, t, heard, soc, np.array([4.0]), np.array([0.0]), kva, "charge", 60.0)
            for i, c in cmds.items():
                if heard[i] or i != 0:
                    devs[i].receive(c)
            row = [d.step(t, DT) for d in devs]
            hist.append([r[0] for r in row])
            states.append((bool(ctl.stale[0]), row[0][1]))
            if k == s:
                heard = np.array([False, True])     # battery 0 goes silent after step s's exchange
        hist = np.array(hist)
        self.assertGreater(hist[s, 0], 0.5)                      # its command was non-zero
        self.assertEqual([st[0] for st in states][s + 1:s + 4], [False, False, True])  # stale at +3
        self.assertEqual(states[s + 4][1], "C")                 # still acting on its last command at +4
        self.assertEqual(states[s + 5][1], "X")                 # expired, idle with backup armed at +5
        self.assertLessEqual(hist[s + 1:s + 5, 1].max(), 0.5)    # headroom never double-booked while booked
        self.assertGreater(hist[s + 5, 1], 0.5)                  # the neighbour covers at expiry (<= 60 s)


if __name__ == "__main__":
    unittest.main()
