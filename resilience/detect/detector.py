"""The detector, from telemetry and the homes' own meters only (docs/design.md §5.6, with the M6' fix).

Every minute it sees what a field system sees: each unit's reported kW (true kW plus seeded telemetry noise), the
setpoint it was sent, and the AMI voltage at every home (plus seeded voltage noise). Over the last DETECT_WINDOW_MIN
samples it flags a unit when all three hold:

  1. residual size:      rms(reported - setpoint) > DETECTION_RMS_KW;
  2. residual structure: the residual's lag-1 autocorrelation < -DETECTION_CORRELATION: it oscillates. A legitimate
                         shortfall (the charge taper, the reserve, a rating) is smooth and positively autocorrelated, so
                         it never qualifies however large it is;
  3. voltage corroboration: the home's own measured voltage carries the same carrier, median amplitude at the carrier
                         frequency above VOLTAGE_CARRIER_PU. The power really flowed at that service point: it is not a
                         telemetry glitch. Only "quiet" 4-minute windows count, where no battery on the unit's
                         transformer changed setpoint by more than MIN_GRANT_KW: a legitimate 20 kW grant step moves a
                         home's voltage by up to 0.04 pu, a hundred times the carrier, and the operator knows every
                         setpoint it sent. Fewer than two quiet windows: no verdict this minute.

The M6' fix, and where it departs from the letter of docs/design.md §5.6. The prototype corroborated voltage against
the legitimate-command solve, which a field detector never has; nothing here reads any solve but the one that
happened. §5.6 asks for a peer baseline on the same transformer. On this feeder that baseline is blind to this attack,
measured (resilience/docs/measurements.md): 8 of the 24 compromised homes have no other home on their transformer, the
cohort is clustered so its peers are mostly compromised too, and each home's own legitimate power steps move its
voltage ten times more than the modulation does. So the gate uses the home's own voltage at the carrier frequency, and
the peer comparison (the unit's carrier amplitude over its peers' median, PEER_MIN_HOMES peers) is recorded at the
flag for the record, never gating.
"""
import numpy as np

from sim.constants import MIN_GRANT_KW

from resilience.constants import (DETECT_WINDOW_MIN, DETECTION_CORRELATION, DETECTION_RMS_KW, FIXED_THRESHOLD_KW,
                                 PEER_MIN_HOMES, TELEMETRY_NOISE_KW, VOLTAGE_CARRIER_PU, VOLTAGE_NOISE_PU)

# The carrier template over 4 one-minute samples: a third difference. It is orthogonal to any constant, linear or
# quadratic trend (a home's interpolated load is piecewise linear), and a +-a sign-every-minute carrier projects to a.
CARRIER = np.array([1.0, -3.0, 3.0, -1.0]) / 8.0


def peer_sets(home_of_batt, homes, transformers, need=PEER_MIN_HOMES):
    """For each battery: (peer home indices, rule): 'transformer' when its own transformer has enough other homes,
    else 'widened' (the nearest transformers by distance, whole transformers at a time)."""
    lonlat = np.array([t["lonlat"] for t in transformers], dtype=float)
    out = []
    for h in home_of_batt:
        t = homes[h]["tf"]
        peers = [x for x in transformers[t]["homes"] if x != h]
        rule = "transformer"
        if len(peers) < need:
            rule = "widened"
            d = np.hypot(*(lonlat - lonlat[t]).T)
            for j in np.argsort(d, kind="stable"):
                if int(j) == t:
                    continue
                peers += list(transformers[int(j)]["homes"])
                if len(peers) >= need:
                    break
        out.append((np.array(sorted(peers), dtype=np.int64), rule))
    return out


def lag1(x):
    a, b = x[:-1], x[1:]
    sa, sb = a.std(), b.std()
    if sa <= 0 or sb <= 0:
        return 0.0
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb))


def carrier_amp(z):
    """Median, over 4-sample windows, of the amplitude at the carrier frequency (sign every minute), trends up to
    quadratic removed. z is [samples] or [samples, series]."""
    z = np.asarray(z, dtype=float)
    w = np.lib.stride_tricks.sliding_window_view(z, 4, axis=0)            # [n-3, (series,) 4]
    return np.median(np.abs(np.tensordot(w, CARRIER, axes=([-1], [0]))), axis=0)


def quiet_carrier(v, sp):
    """Median carrier amplitude of one home's voltage v[samples] over its quiet 4-minute windows: those in which no
    battery setpoint in sp[samples, batteries] (the batteries on the home's transformer; may be none) moves by more
    than MIN_GRANT_KW. None with fewer than two quiet windows or a missing reading."""
    v = np.asarray(v, dtype=float)
    if len(v) < 5 or not np.isfinite(v).all():
        return None
    w = np.lib.stride_tricks.sliding_window_view(v, 4)
    sp = np.asarray(sp, dtype=float).reshape(len(v), -1)
    if sp.shape[1]:
        seg = np.lib.stride_tricks.sliding_window_view(sp, 4, axis=0)          # [n-3, batteries, 4]
        quiet = (seg.max(axis=-1) - seg.min(axis=-1)).max(axis=-1) <= MIN_GRANT_KW
    else:
        quiet = np.ones(len(w), dtype=bool)
    if quiet.sum() < 2:
        return None
    return float(np.median(np.abs(w[quiet] @ CARRIER)))


class PeerDetector:
    def __init__(self, home_of_batt, homes, transformers, seed):
        self.home = np.asarray(home_of_batt, dtype=np.int64)
        self.peers = peer_sets(self.home, homes, transformers)
        self.home_tf = np.array([h["tf"] for h in homes])
        tf = self.home_tf[self.home]
        self.batts_on = {int(t): np.flatnonzero(tf == t) for t in set(tf.tolist())}
        self.rng = np.random.default_rng(seed)
        self.r, self.v, self.sp = [], [], []
        self.first = {}                  # battery -> step first flagged
        self.at_flag = {}                # battery -> {rms, ac1, vAmp, peerRatio} when flagged
        self.fixed = {}                  # battery -> step the naive |residual| > FIXED_THRESHOLD_KW rule first fired

    def update(self, k, kw, setpoint, v_home):
        m = len(self.home)
        r = np.asarray(kw) + self.rng.normal(0.0, TELEMETRY_NOISE_KW, m) - np.asarray(setpoint)
        v = np.asarray(v_home, dtype=float) + self.rng.normal(0.0, VOLTAGE_NOISE_PU, len(v_home))
        v[np.asarray(v_home) <= 0] = np.nan            # a home behind an open transformer has no voltage
        self.r.append(r)
        self.v.append(v)
        self.sp.append(np.asarray(setpoint, dtype=float))
        for i in np.flatnonzero(np.abs(r) > FIXED_THRESHOLD_KW):
            self.fixed.setdefault(int(i), k)
        new = []
        if len(self.r) < DETECT_WINDOW_MIN:
            return new
        R = np.array(self.r[-DETECT_WINDOW_MIN:])
        rms = np.sqrt(np.mean(R * R, axis=0))
        cand = [i for i in np.flatnonzero(rms > DETECTION_RMS_KW) if int(i) not in self.first]
        if not cand:
            return new
        V = np.array(self.v[-DETECT_WINDOW_MIN:])
        SP = np.array(self.sp[-DETECT_WINDOW_MIN:])
        for i in cand:
            i = int(i)
            ac1 = lag1(R[:, i])
            if ac1 >= -DETECTION_CORRELATION:
                continue
            amp = self.voltage_amp(i, V, SP)
            if amp is None or amp <= VOLTAGE_CARRIER_PU:
                continue
            pa = [a for a in (self.home_amp(int(h), V, SP) for h in self.peers[i][0]) if a is not None]
            peer = float(np.median(pa)) if pa else None
            self.first[i] = k
            self.at_flag[i] = {"rms": round(float(rms[i]), 4), "ac1": round(ac1, 3), "vAmpPU": round(amp, 7),
                               "peerRatio": None if not peer else round(amp / peer, 2)}
            new.append(i)
        return new

    def home_amp(self, h, V, SP):
        """quiet_carrier() for home h, quiet with respect to the batteries on h's transformer."""
        mates = self.batts_on.get(int(self.home_tf[h]), np.array([], dtype=np.int64))
        return quiet_carrier(V[:, h], SP[:, mates])

    def voltage_amp(self, i, V, SP):
        """Median carrier amplitude of battery i's home voltage over its quiet 4-minute windows, or None."""
        return self.home_amp(int(self.home[i]), V, SP)

    def observe(self, k, t_s, kw, setpoint, v_home):
        """Observer that only watches (the engine's hook): never quarantines."""
        self.update(k, kw, setpoint, v_home)
        return []

    def quarantine(self, k, t_s, kw, setpoint, v_home):
        """Observer that quarantines every unit it flags, from the next step."""
        return self.update(k, kw, setpoint, v_home)
