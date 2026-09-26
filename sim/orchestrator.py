"""The feeder-aware orchestrator (lane L2): `allocate()`, its state, and the controller around it.

Deterministic numpy + Python, no model in the loop, and OpenDSS is never an oracle inside it: the controller's caps are
its own view (build prompt 3.4, 5.4.3). OpenDSS judges afterwards (sim.p1_build).

    allocate(bg_kw[379], bg_kvar[379], kva[379], tf_of_batt[m], soc[m], pmax[m], emax[m],
             fleet_target_kw, mode, state=None, alpha=AWARE_MARGIN, cover=True,
             *, rte=CORE_RTE, dt_h=1/60, reserve=RESERVE_FLOOR, ids=None, explain=True) -> (kw[m], caps, decisions)

`mode` is "charge", "discharge" or "idle"; `fleet_target_kw` is signed (+ charge, - discharge) and only its magnitude
in the mode's direction is used. `caps` = (H, E, R) from sim.caps.transformer_caps. `decisions` = [(batt, kind, kw,
room)] with kind in relief | discharge | grant | dwell | cut | cover | held (empty when explain=False).

THE STATELESS CORE (state=None, cover=False), the rule sim.siting.per_tf_rule must equal to 1e-6 (build prompt 5.4.3
step 9; docs/contracts.md "Parity"). No dwell, no bucket memory, no flip limit, no cover, no stale units:
  0. (H, E, R) = transformer_caps(bg_kw, bg_kvar, kva, alpha).
     Per battery: lc = min(pmax, (1 - soc) * emax / (sqrt(rte) * dt_h))          charge limit (taper: never past full)
                  ld = min(pmax, max(0, soc - reserve) * emax * sqrt(rte) / dt_h) discharge limit (reserve always)
  1. Relief (every mode; relief overrides the market): for each transformer with R > 0, in index order, its batteries
     in (-floor(soc / SOC_BUCKET + 1e-9), id) order (highest 2%-SoC bucket first) discharge d = min(ld, R left);
     a d below MIN_GRANT_KW (0.5) becomes 0.
  2. mode "discharge": target T = |fleet_target_kw|, total starts at the relief already given. Batteries in the same
     (-bucket, id) order: g = min(ld - relief_i, E[tf] - exported[tf], T - total); g < 0.5 -> 0; kw -= g.
  3. mode "charge": target T = max(0, fleet_target_kw). Batteries not discharging for relief, sorted by
     (floor(soc / SOC_BUCKET + 1e-9), id) ascending; walk once: g = min(lc, H[tf] - granted[tf], T - total), floored at
     0; g < 0.5 -> 0. No equal split: the lowest 2%-SoC bucket is granted first, id breaks ties.
  `id` = `ids[i]` when given, else the battery index i.

THE STATEFUL RULE (P1, state = AllocState): the core plus
  - held units (the controller cannot command them this step: late telemetry) keep their last command booked,
    unchanged, on their transformer and in the total, until it expires;
  - dwell: a charge grant is held unchanged for MIN_DWELL_MIN (5) steps and booked before the walk (capped at the
    battery's charge limit: stop at full), unless its transformer's H shrinks below what is booked on it: then the
    newest grants there are cut first. At dwell expiry the battery re-enters the sort;
  - cover (cover=True): kW released by an expired held booking goes first to batteries on the same transformer in
    sort order, then back to the walk;
  - flip limit: at most one charge <-> discharge flip per FLIP_MIN (5) steps; a battery the limit holds gets 0;
  - blocked units (islanded behind an open transformer) get 0.
"""
import math

import numpy as np

from .caps import transformer_caps
from .constants import (AWARE_MARGIN, CORE_RTE, RESERVE_FLOOR, SOC_BUCKET, MIN_GRANT_KW, MIN_DWELL_MIN, FLIP_MIN,
                        COMMAND_TTL_S, COMMS_STALE_S, CHARGE_URGENCY)
from .devices import Command

BIG = 10 ** 9
EPS = 1e-9


def bucket(soc):
    return math.floor(soc / SOC_BUCKET + 1e-9)


class AllocState:
    """What allocate() remembers between steps (P1). `step` is set by the caller before each call."""

    def __init__(self, m, dwell_min=MIN_DWELL_MIN, flip_min=FLIP_MIN):
        self.m = m
        self.step = 0
        self.dwell = int(dwell_min)
        self.flip = int(flip_min)
        self.grant = np.zeros(m)                 # the last kW issued to each battery (signed)
        self.grant_step = np.full(m, -BIG)       # step the current charge grant was booked
        self.last_dir = np.zeros(m, dtype=int)   # last non-idle direction issued: +1 charge, -1 discharge
        self.last_flip = np.full(m, -BIG)        # step of the last charge <-> discharge flip
        self.held = np.zeros(m, dtype=bool)      # cannot be commanded this step; last command stays booked
        self.blocked = np.zeros(m, dtype=bool)   # islanded / unavailable: 0
        self.release = {}                        # tf -> kW released this step by an expired held booking

    def can_go(self, i, direction):
        """Flip limit: may battery i be commanded in `direction` (+1/-1) at this step?"""
        last = self.last_dir[i]
        if last == 0 or last == direction:
            return True
        return self.step - self.last_flip[i] >= self.flip

    def commit(self, kw):
        """Record the kW issued this step (directions, flips, grant ages). A grant booked by dwell keeps its age;
        any other positive grant is a new booking from this step."""
        k = self.step
        booked = getattr(self, "_booked", set())
        for i in range(self.m):
            if self.held[i]:
                continue
            g = float(kw[i])
            d = 1 if g > EPS else (-1 if g < -EPS else 0)
            if d != 0 and self.last_dir[i] != 0 and d != self.last_dir[i]:
                self.last_flip[i] = k
            if d != 0:
                self.last_dir[i] = d
            if d > 0:
                if i not in booked:
                    self.grant_step[i] = k
            else:
                self.grant_step[i] = -BIG
            self.grant[i] = g
        self.release = {}
        self._booked = set()


def _limits(soc, pmax, emax, rte, dt_h, reserve):
    eta = np.sqrt(rte)
    lc = np.minimum(pmax, np.maximum(0.0, 1.0 - soc) * emax / (eta * dt_h))
    ld = np.minimum(pmax, np.maximum(0.0, soc - reserve) * emax * eta / dt_h)
    return np.maximum(lc, 0.0), np.maximum(ld, 0.0)


def allocate(bg_kw, bg_kvar, kva, tf_of_batt, soc, pmax, emax, fleet_target_kw, mode, state=None,
             alpha=AWARE_MARGIN, cover=True, *, rte=CORE_RTE, dt_h=1 / 60, reserve=RESERVE_FLOOR, ids=None,
             explain=True):
    tf = np.asarray(tf_of_batt, dtype=np.int64)
    soc = np.asarray(soc, dtype=float)
    m = len(tf)
    pmax = np.broadcast_to(np.asarray(pmax, dtype=float), (m,))
    emax = np.broadcast_to(np.asarray(emax, dtype=float), (m,))
    rte_a = np.broadcast_to(np.asarray(rte, dtype=float), (m,))
    H, E, R = transformer_caps(bg_kw, bg_kvar, kva, alpha)
    lc, ld = _limits(soc, pmax, emax, rte_a, dt_h, reserve)
    key_id = list(range(m)) if ids is None else list(ids)
    kw = np.zeros(m)
    granted = np.zeros(len(H))    # charge kW booked per transformer (controller view)
    exported = np.zeros(len(H))   # discharge kW per transformer (positive magnitude)
    total_c = 0.0
    total_d = 0.0
    dec = [] if explain else None
    st = state
    held = st.held if st is not None else np.zeros(m, dtype=bool)
    blocked = st.blocked if st is not None else np.zeros(m, dtype=bool)
    free = ~held & ~blocked

    # held units: their last command stays booked, unchanged
    if st is not None:
        for i in np.flatnonzero(held):
            g = float(st.grant[i])
            kw[i] = g
            if g > 0:
                granted[tf[i]] += g
                total_c += g
            elif g < 0:
                exported[tf[i]] += -g
                total_d += -g
            if explain and abs(g) > EPS:
                dec.append((int(i), "held", g, None))

    # 1. relief overrides the market
    relief = np.zeros(m, dtype=bool)
    relief_tfs = np.flatnonzero(R > EPS)
    if len(relief_tfs):
        by_tf = {}
        for i in range(m):
            if free[i] and R[tf[i]] > EPS:
                by_tf.setdefault(int(tf[i]), []).append(i)
        for t in relief_tfs:
            need = float(R[t]) - exported[t]
            for i in sorted(by_tf.get(int(t), []), key=lambda j: (-bucket(soc[j]), key_id[j])):
                if need <= EPS:
                    break
                if st is not None and not st.can_go(i, -1):
                    continue
                d = min(ld[i], need)
                if d < MIN_GRANT_KW:
                    continue
                kw[i] = -d
                relief[i] = True
                exported[t] += d
                total_d += d
                need -= d
                if explain:
                    dec.append((int(i), "relief", -d, float(R[t])))

    if mode == "discharge":
        T = abs(float(fleet_target_kw))
        order = sorted((i for i in range(m) if free[i]), key=lambda j: (-bucket(soc[j]), key_id[j]))
        for i in order:
            if st is not None and not st.can_go(i, -1):
                continue
            already = -kw[i] if relief[i] else 0.0
            g = min(ld[i] - already, E[tf[i]] - exported[tf[i]], T - total_d)
            if g < MIN_GRANT_KW:
                continue
            kw[i] -= g
            exported[tf[i]] += g
            total_d += g
            if explain:
                dec.append((int(i), "discharge", -g, float(E[tf[i]] - exported[tf[i]] + g)))
    elif mode == "charge":
        T = max(0.0, float(fleet_target_kw))
        cand = [i for i in range(m) if free[i] and not relief[i] and lc[i] >= MIN_GRANT_KW
                and (st is None or st.can_go(i, +1))]
        key = {i: (bucket(soc[i]), key_id[i]) for i in cand}
        booked = []
        if st is not None:
            k = st.step
            for i in cand:
                if st.grant[i] > MIN_GRANT_KW - EPS and k - st.grant_step[i] < st.dwell:
                    g = min(float(st.grant[i]), lc[i])
                    if g >= MIN_GRANT_KW:
                        booked.append(i)
                        kw[i] = g
                        granted[tf[i]] += g
                        total_c += g
            # H shrank below what is booked: cut the newest grants there first
            for t in sorted({int(tf[i]) for i in booked}):
                over = granted[t] - max(H[t], 0.0)
                if over <= EPS:
                    continue
                mine = sorted((i for i in booked if tf[i] == t), key=lambda j: (-st.grant_step[j], key_id[j]))
                for i in mine:
                    if over <= EPS:
                        break
                    cut = min(kw[i], over)
                    new = kw[i] - cut
                    if new < MIN_GRANT_KW:
                        cut = kw[i]
                        new = 0.0
                    kw[i] = new
                    granted[t] -= cut
                    total_c -= cut
                    over -= cut
                    if explain:
                        dec.append((int(i), "cut", new, float(H[t])))
            for i in booked:
                if explain and kw[i] > EPS:
                    dec.append((int(i), "dwell", float(kw[i]), None))
            st._booked = {i for i in booked if kw[i] > EPS}
        taken = set(booked)
        rest = sorted((i for i in cand if i not in taken), key=lambda j: key[j])
        # cover: released kW goes first to batteries on the same transformer, in sort order
        if cover and st is not None and st.release:
            for t in sorted(st.release):
                budget = float(st.release[t])
                for i in (j for j in rest if tf[j] == t):
                    if budget <= EPS:
                        break
                    g = min(lc[i], H[t] - granted[t], T - total_c, budget)
                    if g < MIN_GRANT_KW:
                        continue
                    kw[i] = g
                    granted[t] += g
                    total_c += g
                    budget -= g
                    taken.add(i)
                    if explain:
                        dec.append((int(i), "cover", g, float(H[t] - granted[t] + g)))
            rest = [i for i in rest if i not in taken]
        for i in rest:
            if T - total_c < MIN_GRANT_KW:
                break
            t = tf[i]
            g = min(lc[i], H[t] - granted[t], T - total_c)
            if g < MIN_GRANT_KW:
                continue
            kw[i] = g
            granted[t] += g
            total_c += g
            if explain:
                dec.append((int(i), "grant", g, float(H[t] - granted[t] + g)))
    return kw, (H, E, R), (dec if explain else [])


def charge_target(soc, emax, rte, minutes_left, urgency=CHARGE_URGENCY):
    """Fleet charge target, kW at the meter: energy needed / time left to the deadline x CHARGE_URGENCY."""
    if minutes_left <= 0:
        return 0.0
    need = float(np.sum(np.maximum(0.0, 1.0 - np.asarray(soc)) * np.asarray(emax) / np.sqrt(rte)))
    return need / (minutes_left / 60.0) * urgency


class Controller:
    """The aware controller around allocate(): telemetry, stale units, bookings kept until expiry, command issue.

    One call to `tick()` per step, when the controller runs (not during a stall). Protocol (ASSUMPTION, §12 Q4):
      - telemetry reaches the controller at the start of a step (SoC, kW applied last step);
      - a unit whose telemetry did not arrive this step is `held`: it gets no new command and its last command stays
        booked until that command's expiry (issued + COMMAND_TTL_S), so headroom is never double-booked;
      - a unit silent for COMMS_STALE_S is marked stale (S);
      - when a held unit's booking expires, its kW is released for cover (same transformer first);
      - every commanded unit gets a fresh command each step (seq + 1, expires = issued + COMMAND_TTL_S).
    """

    def __init__(self, tf_of_batt, pmax, emax, rte, ids, dwell_min=MIN_DWELL_MIN, alpha=AWARE_MARGIN, cover=True):
        self.tf = np.asarray(tf_of_batt, dtype=np.int64)
        self.m = len(self.tf)
        self.pmax = np.asarray(pmax, dtype=float)
        self.emax = np.asarray(emax, dtype=float)
        self.rte = np.asarray(rte, dtype=float)
        self.ids = list(ids)
        self.alpha = alpha
        self.cover = cover
        self.state = AllocState(self.m, dwell_min=dwell_min)
        self.seq = 0
        self.last_cmd = [None] * self.m      # last command issued (the controller's record)
        self.last_seen = np.full(self.m, -BIG, dtype=np.int64)
        self.soc_view = np.zeros(self.m)
        self.stale = np.zeros(self.m, dtype=bool)
        self.issued = 0

    def expired(self, i, t_s):
        c = self.last_cmd[i]
        return c is None or t_s >= c.expires_s

    def tick(self, k, t_s, heard, soc_now, bg_kw, bg_kvar, kva, mode, target_kw, blocked=None):
        """heard[m]: telemetry arrived this step. Returns (kw[m] booked view, commands {i: Command}, decisions)."""
        st = self.state
        st.step = k
        heard = np.asarray(heard, dtype=bool)
        self.last_seen = np.where(heard, t_s, self.last_seen)
        self.soc_view = np.where(heard, soc_now, self.soc_view)
        self.stale = (t_s - self.last_seen) >= COMMS_STALE_S
        prev_held = st.held.copy()
        exp = np.array([self.expired(i, t_s) for i in range(self.m)])
        st.held = ~heard & ~exp
        st.blocked = np.asarray(blocked, dtype=bool) if blocked is not None else np.zeros(self.m, dtype=bool)
        st.blocked = st.blocked | (~heard & exp)   # silent and expired: out of the walk
        st.release = {}
        for i in range(self.m):
            if exp[i] and st.grant[i] != 0.0:
                if prev_held[i] and st.grant[i] > 0:
                    t = int(self.tf[i])
                    st.release[t] = st.release.get(t, 0.0) + float(st.grant[i])
                st.grant[i] = 0.0
                st.grant_step[i] = -BIG
        kw, caps, dec = allocate(bg_kw, bg_kvar, kva, self.tf, self.soc_view, self.pmax, self.emax, target_kw, mode,
                                 state=st, alpha=self.alpha, cover=self.cover, rte=self.rte, ids=self.ids)
        st.commit(kw)
        cmds = {}
        for i in range(self.m):
            if st.held[i] or st.blocked[i]:
                continue
            self.seq += 1
            c = Command.make(self.seq, t_s, float(kw[i]), COMMAND_TTL_S)
            self.last_cmd[i] = c
            cmds[i] = c
            self.issued += 1
        return kw, caps, dec, cmds


def handoffs(kw, window=MIN_DWELL_MIN, thr=MIN_GRANT_KW):
    """Hand-offs among the columns of kw[n, m] (build prompt 5.4.3): one battery's grant falls from > thr to <= thr
    while ANOTHER battery's grant rises from <= thr to > thr within the same `window` minutes (|dt| < window).
    Falls and rises are matched one to one, in time order. Returns (count, [(fall_step, a, rise_step, b)])."""
    kw = np.asarray(kw, dtype=float)
    on = kw > thr
    falls = [(k, a) for k in range(1, len(kw)) for a in np.flatnonzero(on[k - 1] & ~on[k])]
    rises = [(k, b) for k in range(1, len(kw)) for b in np.flatnonzero(~on[k - 1] & on[k])]
    used = set()
    out = []
    for f, a in falls:
        for j, (r, b) in enumerate(rises):
            if j in used or b == a or abs(r - f) >= window:
                continue
            used.add(j)
            out.append((int(f), int(a), int(r), int(b)))
            break
    return len(out), out
