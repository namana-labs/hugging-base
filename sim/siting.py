"""P2, where the next battery goes: the month model on the surrogate (build prompt 5.6; lane L3).

Three layers, all deterministic numpy, no model in the loop:

1. `per_tf_rule()` - the STATELESS 5.4.3 core (no dwell, no bucket memory, no flip limit, no cover), the rule
   `sim.orchestrator.allocate(..., state=None, cover=False)` must agree with to 1e-6 (the parity invariant).
   It shares `sim.caps.transformer_caps` with P1:
     room = sqrt(max(0, (alpha kVA)^2 - bg_kvar^2)); H = room - bg_kw; E = room + bg_kw; R = max(0, bg_kw - room)
   a. relief overrides the market: where R > 0 the transformer's batteries above reserve discharge just enough,
      highest SoC first (id breaks ties);
   b. discharge (mode 'discharge'): the fleet target (its magnitude; the relief already given counts toward it) goes
      highest SoC first, each capped by its transformer's export headroom E (less what relief already exports);
   c. charge (mode 'charge'): batteries below full, sorted by (floor(SoC / SOC_BUCKET + 1e-9), id) ascending, granted
      in turn g = min(pmax, taper(SoC), H - granted on the tf, target - granted in total); there is no equal split;
   d. every grant below MIN_GRANT_KW (0.5 kW) becomes 0; the reserve always holds; a battery stops at full.
   taper(SoC) is the energy-to-full limit over one step, (1 - SoC) E / sqrt(RTE) / dt (four-home's
   Battery.charge_limit_kw); the discharge limit is (SoC - reserve) E sqrt(RTE) / dt (grid side). dt defaults to
   P1's 60 s step.

2. `simulate()` - the month, sequential in time and vectorised across "worlds" (columns). A column is one
   transformer with one set of batteries; transformers are independent in the surrogate, so "one more battery on
   transformer i" for every i is one run. Each battery follows the combo's zone signal every 15 minutes:
     discharge: 5.4.2's rule per day and per battery - the highest-priced intervals between 16:00 and that day's
       D-26 onset that its usable energy covers at full power (perfect foresight, ASSUMPTION; the last one partial,
       floored to whole minutes, exactly as sim.prices.discharge_plan);
     charge: from `onset_d26(day)` (rule 'd26', all at once until full) or in the cheapest intervals of the same
       window that its energy needs (rule 'cheapest', perfect foresight), until 06:00 the next day (P2_CHARGE_END);
       energy not charged by then is curtailment (ASSUMPTION: the rest of Base's zone fleet absorbs it).
   `aware` caps every battery by its own transformer only (the stateless core, cover=False, the fleet target set
   to the zone signal's own total so it never binds); `naive` is uncapped and never relieves.
   The controller sees the interval's summed home P and Q per transformer (P2_CONTROLLER_VIEW, ASSUMPTION).

3. `month_metrics()` / `compare()` - hours above 100%, normal-tier events (>= 2 consecutive intervals above 110%),
   emergency intervals (> 150%), protection (4.5's rule at 15-min steps: one interval above 200% operates it),
   the peak and when, and whether the batteries caused each normal event (P2 definition: during the run the
   batteries RAISED the transformer's loading above what its home load alone gives; at 15-minute steps the P2
   controller sees the interval itself, so 7.3's 2-step lag window is reported separately, never gated).

Sign: positive kW = charging. Loading from `sim.surrogate.loading` (batteries at unity pf, calibrated losses).
"""
import math
from datetime import datetime, timedelta
from functools import lru_cache

import numpy as np

from .caps import transformer_caps
from .constants import (const, AWARE_MARGIN, SOC_BUCKET, MIN_GRANT_KW, RESERVE_FLOOR, CORE_POWER_KW,
                        CORE_USABLE_KWH, CORE_RTE, LEGACY_POWER_KW, LEGACY_USABLE_KWH, LEGACY_RTE, TIER_AMBER_PCT,
                        TIER_NORMAL_PCT, TIER_NORMAL_MIN, TIER_EMERGENCY_PCT, FUSE_PCT, FUSE_MINUTES,
                        FUSE_INSTANT_PCT, FUSE_INSTANT_SECONDS, P1_STEP_SECONDS, GROWTH)
from .prices import onset_d26, price_at

# ---- P2 constants (each one named, labelled and cited) ------------------------------------------------------
P2_SOC0 = const("P2_SOC0", 0.90, "ASSUMPTION",
                "state of charge of every battery at 2026-08-01 00:00, the start of the P2 month (P1's SOC0, build prompt 5.4.1)")
P2_DISCHARGE_FROM = const("P2_DISCHARGE_FROM", "16:00", "ASSUMPTION",
                          "the daily discharge plan searches 16:00 -> D-26 onset (build prompt 5.4.2, applied per day)")
P2_CHARGE_END = const("P2_CHARGE_END", "06:00", "ASSUMPTION",
                      "the nightly charge window ends 06:00; energy not charged by then is curtailment (build prompt 5.6)")
P2_CONTROLLER_VIEW = const("P2_CONTROLLER_VIEW", "the interval's summed home P and Q per transformer, 15-min steps, no lag",
                           "ASSUMPTION", "P2 screening view; P1 uses 60 s lagged total transformer load (CONTROLLER_VIEW, section 12 Q4)")
P2_CAUSED_EPS_PTS = const("P2_CAUSED_EPS_PTS", 0.01, "ASSUMPTION",
                          "a battery 'raises' loading when with-battery loading exceeds home-only loading by more than 0.01 points")
CURTAIL_VALUE_RULE = const("CURTAIL_VALUE_RULE", "curtailed kWh x the August 2026 median LZ_NORTH price", "ASSUMPTION",
                           "rank key 4 'revenue minus curtailment cost' (build prompt 5.6): re-buying the energy elsewhere in the zone")
TOP_N = const("P2_RANKING_TOP", 50, "ASSUMPTION", "p2/<combo>.json keeps the top 50 (build prompt 5.3)")
GREEDY_N = const("P2_GREEDY_N", 10, "ASSUMPTION", "greedy placements per combo (build prompt 5.6 step 7)")

CLASSES = {  # class -> (pmax kW, usable kWh, round-trip efficiency); labels live on the named constants
    "core": (CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE),
    "legacy": (LEGACY_POWER_KW, LEGACY_USABLE_KWH, LEGACY_RTE),
}
STEP_MIN = 15
DT_H = STEP_MIN / 60.0
MONTH_T0 = datetime(2026, 8, 1)
MONTH_DAYS = 31
REPORTED = 2976          # August; the loads carry 24 more steps so the 31 Aug night charges to 06:00
STEPS = 3000


# =================================================================================================================
# 1. the stateless rule
# =================================================================================================================
def _seg_grant(order, col, cap, room):
    """Grant in turn inside each column: walk `order` (a permutation), grant g = clip(room[col] - granted so far on
    that column, 0, cap). `cap` must already be 0 for any battery whose cap is below MIN_GRANT_KW (such a battery can
    never receive a grant >= MIN_GRANT_KW); grants below MIN_GRANT_KW become 0. Exactly the sequential walk."""
    m = len(order)
    out = np.zeros(m)
    if m == 0:
        return out
    o = order[np.argsort(col[order], kind="stable")]          # grouped by column, the walk order kept inside each
    c = cap[o]
    cols = col[o]
    excl = np.cumsum(c) - c
    start = np.ones(m, dtype=bool)
    start[1:] = cols[1:] != cols[:-1]
    first = np.maximum.accumulate(np.where(start, np.arange(m), 0))
    before = excl - excl[first]
    g = np.clip(room[cols] - before, 0.0, c)
    g[g < MIN_GRANT_KW] = 0.0
    out[o] = g
    return out


def _target_clip(order, g, target):
    """The fleet target walked in the same global order: g_i <- clip(target - granted before i, 0, g_i)."""
    if not np.isfinite(target):
        return g
    gs = g[order]
    excl = np.cumsum(gs) - gs
    gs = np.clip(target - excl, 0.0, gs)
    gs[gs < MIN_GRANT_KW] = 0.0
    out = np.zeros_like(g)
    out[order] = gs
    return out


def _floor_grant(x):
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    return np.where(x >= MIN_GRANT_KW, x, 0.0)


def grant(bg_kw, bg_kvar, kva, col, soc, ids, dis_cap, dis_want, chg_want, alpha=AWARE_MARGIN,
          dis_target=math.inf, chg_target=math.inf):
    """The aware grant for one step. dis_cap = what each battery can discharge (reserve and pmax), dis_want /
    chg_want = what the market asks of it (<= its caps). Returns kW per battery (+ charge, - discharge)."""
    H, E, R = transformer_caps(bg_kw, bg_kvar, kva, alpha)
    dis_cap = _floor_grant(dis_cap)
    desc = np.lexsort((ids, -soc))                             # highest SoC first, id breaks ties
    rel = _seg_grant(desc, col, dis_cap, R)
    kw = -rel
    rel_tf = np.bincount(col, weights=rel, minlength=len(E))
    mcap = _floor_grant(np.minimum(dis_want, dis_cap) - rel)
    if mcap.any():
        # the discharge target counts the relief already given (as orchestrator.allocate)
        g = _target_clip(desc, _seg_grant(desc, col, mcap, E - rel_tf), dis_target - rel.sum())
        kw = kw - g
    ccap = _floor_grant(np.where(rel > 0, 0.0, chg_want))
    if ccap.any():
        bucket = np.floor(soc / SOC_BUCKET + 1e-9)
        asc = np.lexsort((ids, bucket))
        g = _target_clip(asc, _seg_grant(asc, col, ccap, H), chg_target)
        kw = kw + g
    return kw


def limits(soc, pmax, emax, rte, dt_h, reserve=RESERVE_FLOOR):
    """(discharge cap, charge cap) in grid-side kW over one step: pmax, the reserve, and full (the taper)."""
    eta = np.sqrt(rte)
    dis = np.minimum(pmax, np.maximum(0.0, soc - reserve) * emax * eta / dt_h)
    chg = np.minimum(pmax, np.maximum(0.0, 1.0 - soc) * emax / eta / dt_h)
    return dis, chg


def per_tf_rule(bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, fleet_target_kw, mode, alpha=AWARE_MARGIN,
                rte=CORE_RTE, dt_h=P1_STEP_SECONDS / 3600.0, reserve=RESERVE_FLOOR, ids=None):
    """The stateless 5.4.3 core (docs/contracts.md Part B). kW per battery [m]; + charge, - discharge.

    bg_kw, bg_kvar, kva [T]: background per transformer (controller view) and nameplate; soc, pmax, emax [m];
    tf_of int [m] indexes the transformer axis; fleet_target_kw: the charge target (mode 'charge') or the discharge
    magnitude (mode 'discharge'; its sign is ignored); mode 'charge' | 'discharge' | 'idle' (relief only).
    ids [m] break ties (default: the battery's position)."""
    soc = np.asarray(soc, dtype=float)
    m = len(soc)
    pmax = np.broadcast_to(np.asarray(pmax, dtype=float), (m,))
    emax = np.broadcast_to(np.asarray(emax, dtype=float), (m,))
    rte = np.broadcast_to(np.asarray(rte, dtype=float), (m,))
    ids = np.arange(m) if ids is None else np.asarray(ids)
    col = np.asarray(tf_of, dtype=np.int64)
    dis_cap, chg_cap = limits(soc, pmax, emax, rte, dt_h, reserve)
    zero = np.zeros(m)
    if mode == "discharge":
        return grant(bg_kw, bg_kvar, kva, col, soc, ids, dis_cap, dis_cap, zero, alpha, dis_target=abs(fleet_target_kw))
    if mode == "charge":
        return grant(bg_kw, bg_kvar, kva, col, soc, ids, dis_cap, zero, chg_cap, alpha, chg_target=fleet_target_kw)
    if mode == "idle":
        return grant(bg_kw, bg_kvar, kva, col, soc, ids, dis_cap, zero, zero, alpha)
    raise ValueError(f"mode {mode!r} not in charge|discharge|idle")


def per_tf_rule_reference(bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, fleet_target_kw, mode, alpha=AWARE_MARGIN,
                          rte=CORE_RTE, dt_h=P1_STEP_SECONDS / 3600.0, reserve=RESERVE_FLOOR):
    """The same rule written as the literal sequential walk of 5.4.3 (for tests; slow)."""
    soc = np.asarray(soc, dtype=float)
    m = len(soc)
    pmax = np.broadcast_to(np.asarray(pmax, dtype=float), (m,))
    emax = np.broadcast_to(np.asarray(emax, dtype=float), (m,))
    rte = np.broadcast_to(np.asarray(rte, dtype=float), (m,))
    H, E, R = transformer_caps(bg_kw, bg_kvar, kva, alpha)
    dis_cap, chg_cap = limits(soc, pmax, emax, rte, dt_h, reserve)
    kw = np.zeros(m)
    desc = sorted(range(m), key=lambda i: (-soc[i], i))
    rel_tf = np.zeros(len(H))
    for i in desc:
        tf = tf_of[i]
        g = min(dis_cap[i], R[tf] - rel_tf[tf])
        g = g if g >= MIN_GRANT_KW else 0.0
        kw[i] -= g
        rel_tf[tf] += g
    if mode == "discharge":
        exp_tf = rel_tf.copy()
        total = float(rel_tf.sum())
        target = abs(fleet_target_kw)
        for i in desc:
            tf = tf_of[i]
            cap = dis_cap[i] + kw[i]            # kw[i] <= 0 is relief already given
            g = max(0.0, min(cap, E[tf] - exp_tf[tf], target - total))
            g = g if g >= MIN_GRANT_KW else 0.0
            kw[i] -= g
            exp_tf[tf] += g
            total += g
    elif mode == "charge":
        got_tf = np.zeros(len(H))
        total = 0.0
        asc = sorted(range(m), key=lambda i: (math.floor(soc[i] / SOC_BUCKET + 1e-9), i))
        for i in asc:
            if kw[i] < 0:
                continue
            tf = tf_of[i]
            g = max(0.0, min(chg_cap[i], H[tf] - got_tf[tf], fleet_target_kw - total))
            g = g if g >= MIN_GRANT_KW else 0.0
            kw[i] += g
            got_tf[tf] += g
            total += g
    return kw


# =================================================================================================================
# 2. the month
# =================================================================================================================
def _ts(k):
    return MONTH_T0 + timedelta(minutes=STEP_MIN * int(k))


def step_of(ts):
    t = ts if isinstance(ts, datetime) else datetime.strptime(ts[:16], "%Y-%m-%dT%H:%M")
    return int((t - MONTH_T0).total_seconds() // (STEP_MIN * 60))


@lru_cache(maxsize=None)
def month_prices(steps=STEPS):
    """REAL LZ_NORTH $/MWh for each 15-min step from 2026-08-01 00:00 (3,000 steps run to 1 Sep 06:00)."""
    return np.array([price_at(_ts(k)) for k in range(steps)])


@lru_cache(maxsize=None)
def day_windows(steps=STEPS):
    """Per day of August: (day, onset step, onset ts, onset price, mode, discharge window [a, b), charge window [b, c)).
    Discharge 16:00 -> onset; charge onset -> 06:00 next day (clipped to the simulated steps)."""
    out = []
    for d in range(MONTH_DAYS):
        day = (MONTH_T0 + timedelta(days=d)).strftime("%Y-%m-%d")
        onset, p, peak, thr, mode = onset_d26(day)
        a = step_of(f"{day}T{P2_DISCHARGE_FROM}")
        b = step_of(onset)
        c = min(steps, step_of((datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d") + "T" + P2_CHARGE_END))
        out.append({"day": day, "onset": onset, "onsetStep": b, "price": p, "peak": peak, "threshold": thr,
                    "mode": mode, "dis": (a, b), "chg": (b, c)})
    return tuple(out)


@lru_cache(maxsize=None)
def signal(rule, steps=STEPS):
    """The zone signal per step, the same for every battery:
    kind[steps] (0 idle, 1 discharge window, 2 charge window), rank[steps] (the step's price rank among the steps
    still left in its window: descending price for discharge, ascending for 'cheapest' charge, earlier first on
    ties, as discharge_plan), window_end[steps], day[steps]."""
    price = month_prices(steps)
    kind = np.zeros(steps, dtype=np.int8)
    rank = np.zeros(steps, dtype=np.int64)
    wend = np.zeros(steps, dtype=np.int64)
    dayi = np.full(steps, -1, dtype=np.int64)
    for d, w in enumerate(day_windows(steps)):
        for (a, b), k, desc in ((w["dis"], 1, True), (w["chg"], 2, False)):
            b = min(b, steps)
            for t in range(a, b):
                rest = np.arange(t, b)
                p = price[rest]
                key = -p if desc else p
                # rank of t among the remaining window: strictly better keys, plus equal keys that come earlier
                rank[t] = int(np.sum(key < key[0]))
                kind[t] = k
                wend[t] = b
                dayi[t] = d
    if rule == "d26":
        rank = np.where(kind == 2, 0, rank)            # d26 charges all at once, until full
    elif rule != "cheapest":
        raise ValueError(f"rule {rule!r} not in d26|cheapest")
    return kind, rank, wend, dayi


def market_want(kind_t, rank_t, soc, pmax, emax, rte, reserve=RESERVE_FLOOR):
    """(discharge want, charge want) of each battery at one step, from its own energy (per-battery plan)."""
    eta = np.sqrt(rte)
    m = len(soc)
    if kind_t == 1:
        # usable energy at the meter, in intervals at full power; the partial interval floored to whole minutes
        n = np.maximum(0.0, soc - reserve) * emax * eta / (pmax * DT_H)
        full = np.floor(n + 1e-9)
        part = np.floor((n - full) * STEP_MIN + 1e-9) / STEP_MIN
        frac = np.where(rank_t < full, 1.0, np.where(rank_t == full, part, 0.0))
        return pmax * frac, np.zeros(m)
    if kind_t == 2:
        need = np.maximum(0.0, 1.0 - soc) * emax / eta / (pmax * DT_H)
        full = np.floor(need + 1e-9)
        frac = np.where(rank_t < full, 1.0, np.where(rank_t == full, need - full, 0.0))
        return np.zeros(m), pmax * frac
    return np.zeros(m), np.zeros(m)


class World:
    """Columns (transformer worlds) and the batteries in them.

    col_tf[W]: the topology transformer index of each column. Batteries: col[m] (column), home[m] (topology home
    index, the id that breaks ties), cls[m] ('core'|'legacy'), new[m] (bool: a candidate, not the existing fleet)."""

    def __init__(self, col_tf, col, home, cls, new):
        self.col_tf = np.asarray(col_tf, dtype=np.int64)
        self.col = np.asarray(col, dtype=np.int64)
        self.home = np.asarray(home, dtype=np.int64)
        self.cls = list(cls)
        self.new = np.asarray(new, dtype=bool)
        spec = np.array([CLASSES[c] for c in self.cls]) if self.cls else np.zeros((0, 3))
        self.pmax, self.emax, self.rte = (spec[:, 0], spec[:, 1], spec[:, 2]) if len(spec) else (np.zeros(0),) * 3

    @property
    def W(self):
        return len(self.col_tf)

    @property
    def m(self):
        return len(self.col)


def simulate(world, P, Q, kva, coeffs, policy, rule, steps=STEPS, soc0=P2_SOC0, alpha=AWARE_MARGIN):
    """Run the month. P, Q [steps, 379] home load per transformer (growth already applied); kva [379]; coeffs the
    surrogate coefficient dict (topology order). Returns a dict of arrays over the columns / batteries:
      kw [steps, m] battery kW (float32), soc_end [m], col_kw [steps, W], pct [steps, W] (with batteries),
      pct_none [steps, W] (home load only), curtail_kwh [m], need_kwh [m] (grid side, summed over charge windows),
      revenue [m] ($, energy value over all simulated steps)."""
    if policy not in ("naive", "aware"):
        raise ValueError(policy)
    kind, rank, wend, dayi = signal(rule, STEPS)
    price = month_prices(STEPS)
    tf = world.col_tf
    Pc = P[:steps][:, tf]
    Qc = Q[:steps][:, tf]
    kva_c = kva[tf]
    m = world.m
    soc = np.full(m, float(soc0))
    kw_out = np.zeros((steps, m), dtype=np.float32)
    col_kw = np.zeros((steps, world.W))
    curtail = np.zeros(m)
    need = np.zeros(m)
    revenue = np.zeros(m)
    eta = np.sqrt(world.rte)
    for t in range(steps):
        kt = int(kind[t])
        if kt == 2 and (t == 0 or kind[t - 1] != 2 or dayi[t - 1] != dayi[t]):
            need += np.maximum(0.0, 1.0 - soc) * world.emax / eta          # charge need at the window start
        dis_cap, chg_cap = limits(soc, world.pmax, world.emax, world.rte, DT_H)
        dw, cw = market_want(kt, rank[t], soc, world.pmax, world.emax, world.rte)
        dw = np.minimum(dw, dis_cap)
        cw = np.minimum(cw, chg_cap)
        if policy == "naive" or m == 0:
            kw = cw - dw
        else:
            kw = grant(Pc[t], Qc[t], kva_c, world.col, soc, world.home, dis_cap, dw, cw, alpha)
        # device bookkeeping (four-home Battery.apply): the reserve always holds, stop at full
        soc = np.where(kw > 0, np.minimum(1.0, soc + kw * eta * DT_H / world.emax),
                       np.maximum(RESERVE_FLOOR, soc + kw * DT_H / (eta * world.emax)))
        kw_out[t] = kw
        if m:
            col_kw[t] = np.bincount(world.col, weights=kw, minlength=world.W)
        revenue -= kw * price[t] * DT_H / 1000.0
        if kt == 2 and (t + 1 >= steps or t + 1 == wend[t]):
            curtail += np.maximum(0.0, 1.0 - soc) * world.emax / eta       # not charged by 06:00
    from . import surrogate
    c = {k: np.asarray(v)[tf] for k, v in coeffs.items()}
    pct = surrogate.loading(Pc, Qc, col_kw, c)
    pct_none = surrogate.loading(Pc, Qc, np.zeros_like(col_kw), c)
    return {"kw": kw_out, "soc_end": soc, "col_kw": col_kw, "pct": pct, "pct_none": pct_none,
            "curtail_kwh": curtail, "need_kwh": need, "revenue": revenue}


# =================================================================================================================
# 3. metrics
# =================================================================================================================
def runs_above(mask):
    """Runs of True down axis 0 of mask [n, W]: arrays (col, start, end_exclusive), sorted by column then start."""
    mask = np.asarray(mask, dtype=bool)
    n, W = mask.shape
    pad = np.zeros((n + 2, W), dtype=np.int8)
    pad[1:-1] = mask
    d = np.diff(pad, axis=0)
    s_t, s_c = np.nonzero(d == 1)
    e_t, e_c = np.nonzero(d == -1)
    so = np.lexsort((s_t, s_c))
    eo = np.lexsort((e_t, e_c))
    return s_c[so], s_t[so], e_t[eo]


def month_metrics(pct, pct_none=None, col_kw=None, steps=REPORTED, step_minutes=STEP_MIN):
    """Per-column month metrics over the first `steps` steps. Returns a dict of [W] arrays:
    peak, peakT, h100, h110, normalEvents, normalH, emergencyN, protection (first step or -1),
    causedNormal (normal events during which the batteries raised the loading), causedLagNormal (7.3's rule: the
    batteries charging or back-feeding at a step of the run or within the 2 steps before it), over100Raised
    (intervals above 100% where the batteries raised the loading)."""
    pct = np.asarray(pct)[:steps]
    n, W = pct.shape
    out = {"peak": pct.max(axis=0), "peakT": pct.argmax(axis=0),
           "h100": (pct > TIER_AMBER_PCT).sum(axis=0) * step_minutes / 60.0,
           "h110": (pct > TIER_NORMAL_PCT).sum(axis=0) * step_minutes / 60.0,
           "emergencyN": (pct > TIER_EMERGENCY_PCT).sum(axis=0)}
    need = max(1, math.ceil(TIER_NORMAL_MIN / step_minutes))
    cols, st, en = runs_above(pct > TIER_NORMAL_PCT)
    keep = (en - st) >= need
    cols, st, en = cols[keep], st[keep], en[keep]
    out["normalEvents"] = np.bincount(cols, minlength=W)
    out["normalH"] = np.bincount(cols, weights=(en - st) * step_minutes / 60.0, minlength=W)
    raised = np.zeros((n, W), dtype=bool)
    lag = np.zeros((n, W), dtype=bool)
    if pct_none is not None:
        raised = pct > np.asarray(pct_none)[:steps] + P2_CAUSED_EPS_PTS
    if col_kw is not None:
        ck = np.asarray(col_kw)[:steps]
        active = ck > MIN_GRANT_KW                                   # charging
        if pct_none is not None:
            active |= (ck < -MIN_GRANT_KW) & (pct > np.asarray(pct_none)[:steps] + P2_CAUSED_EPS_PTS)  # back-feed raises
        lag = active.copy()
        lag[1:] |= active[:-1]
        lag[2:] |= active[:-2]
    cr = np.cumsum(np.vstack([np.zeros((1, W), dtype=np.int64), raised.astype(np.int64)]), axis=0)
    cl = np.cumsum(np.vstack([np.zeros((1, W), dtype=np.int64), lag.astype(np.int64)]), axis=0)
    caused = (cr[en, cols] - cr[st, cols]) > 0
    caused_lag = (cl[en, cols] - cl[st, cols]) > 0
    out["causedNormal"] = np.bincount(cols[caused], minlength=W)
    out["causedLagNormal"] = np.bincount(cols[caused_lag], minlength=W)
    out["over100Raised"] = ((pct > TIER_AMBER_PCT) & raised).sum(axis=0)
    need_fuse = max(1, math.ceil(FUSE_MINUTES / step_minutes))
    need_inst = max(1, math.ceil(FUSE_INSTANT_SECONDS / (step_minutes * 60)))
    prot = np.full(W, -1, dtype=np.int64)
    for thr, k in ((FUSE_PCT, need_fuse), (FUSE_INSTANT_PCT, need_inst)):
        c2, s2, e2 = runs_above(pct > thr)
        ok = (e2 - s2) >= k
        for c, s in zip(c2[ok], s2[ok]):
            hit = s + k - 1
            if prot[c] < 0 or hit < prot[c]:
                prot[c] = hit
    out["protection"] = prot
    return out


def stamp(k):
    """'YYYY-MM-DD HH:MM' of a 15-min step (the interval start, local)."""
    return _ts(k).strftime("%Y-%m-%d %H:%M")


def growth_factor(g):
    return 1.0 + (GROWTH if int(g) else 0.0)


# =================================================================================================================
# 4. parity with P1 (build prompt 5.4.3 step 9)
# =================================================================================================================
def random_states(n=1000, seed=20260826, T=40, m=96):
    """n deterministic single-step states: (bg_kw, bg_kvar, kva, soc, pmax, emax, rte, tf_of, target, mode)."""
    rng = np.random.default_rng(seed)
    for i in range(n):
        kva = rng.choice([10.0, 25.0, 50.0, 75.0, 150.0], T)
        bg_kw = rng.uniform(-0.6, 1.25, T) * kva
        bg_kvar = rng.uniform(0.0, 0.5, T) * np.abs(bg_kw)
        soc = rng.uniform(0.15, 1.0, m)
        soc[rng.random(m) < 0.1] = 1.0
        soc[rng.random(m) < 0.1] = RESERVE_FLOOR
        legacy = rng.random(m) < 0.3
        pmax = np.where(legacy, LEGACY_POWER_KW, CORE_POWER_KW)
        emax = np.where(legacy, LEGACY_USABLE_KWH, CORE_USABLE_KWH)
        rte = np.where(legacy, LEGACY_RTE, CORE_RTE)
        tf_of = rng.integers(0, T, m)
        mode = ("charge", "discharge", "idle")[i % 3]
        target = float(rng.choice([1e6, rng.uniform(0.0, 600.0)]))
        if mode == "discharge" and rng.random() < 0.5:
            target = -target
        yield bg_kw, bg_kvar, kva, soc, pmax, emax, rte, tf_of, target, mode


def parity(n=1000, seed=20260826):
    """max |allocate(state=None, cover=False) - per_tf_rule| over n random single-step states (kW), or None when
    sim.orchestrator (lane L2) is not on this branch. Returns (max_diff or None, n, detail)."""
    try:
        from .orchestrator import allocate  # lane L2
    except ImportError as e:
        return None, 0, f"sim.orchestrator not importable ({e})"
    worst = 0.0
    for bg_kw, bg_kvar, kva, soc, pmax, emax, rte, tf_of, target, mode in random_states(n, seed):
        a, _, _ = allocate(bg_kw, bg_kvar, kva, tf_of, soc, pmax, emax, target, mode, state=None, cover=False,
                           rte=rte, explain=False)
        b = per_tf_rule(bg_kw, bg_kvar, kva, soc, pmax, emax, tf_of, target, mode, rte=rte)
        worst = max(worst, float(np.max(np.abs(np.asarray(a) - b))))
    return worst, n, "orchestrator.allocate(state=None, cover=False) vs siting.per_tf_rule"
