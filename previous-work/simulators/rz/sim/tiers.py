"""Tiers, runs and protection, computed once, in Python, from OpenDSS loading (the UI never re-derives them).

Three tiers (build prompt 3.1; ratings REAL: SMART-DS normhkva = 1.1 x kva, EmergHKVA = 1.5 x kva):
  amber     above 100% (over nameplate): counted, not a violation
  normal    above 110% for >= TIER_NORMAL_MIN (30) consecutive minutes: the headline violation
  emergency above 150% at any step

tier codes (p1/<branch>.json `tier` strings, one character per transformer per step):
  0 ok | 1 amber (>100%) | 2 above 110% and counting (run < 30 min so far) | 3 normal violation
  (the run has lasted >= 30 min, from the step it reaches 30 min on) | 4 emergency (>150%) |
  5 protection open (from the step the fuse opens, for the rest of the window)

Protection (4.5, ASSUMPTION, never tuned): a fuse opens above FUSE_PCT (200%) of nameplate for
FUSE_MINUTES (10) or above FUSE_INSTANT_PCT (300%) for FUSE_INSTANT_SECONDS (60). With 60 s steps
that is 10 consecutive steps above 200% or 1 step above 300%; with 15-min steps one interval above
200% (15 >= 10 min) or above 300% operates it. A run's duration is steps x step length.
"""
import math

import numpy as np

from .constants import (TIER_AMBER_PCT, TIER_NORMAL_PCT, TIER_NORMAL_MIN, TIER_EMERGENCY_PCT,
                        FUSE_PCT, FUSE_MINUTES, FUSE_INSTANT_PCT, FUSE_INSTANT_SECONDS)


def _run_lengths(mask):
    """For a bool array [n, m], the length (in steps) of the current True run ending at each step."""
    mask = np.asarray(mask, dtype=bool)
    out = np.zeros(mask.shape, dtype=np.int64)
    run = np.zeros(mask.shape[1:], dtype=np.int64)
    for k in range(mask.shape[0]):
        run = np.where(mask[k], run + 1, 0)
        out[k] = run
    return out


def protection_events(pct, step_seconds, first_only=True):
    """[(step, tf)] where the 4.5 rule operates, in step order. With first_only (the default) each
    transformer operates at most once (it stays open for the rest of the window)."""
    pct = np.atleast_2d(np.asarray(pct, dtype=float))
    need_fuse = max(1, math.ceil(FUSE_MINUTES * 60 / step_seconds))
    need_inst = max(1, math.ceil(FUSE_INSTANT_SECONDS / step_seconds))
    fuse = _run_lengths(pct > FUSE_PCT) >= need_fuse
    inst = _run_lengths(pct > FUSE_INSTANT_PCT) >= need_inst
    hit = fuse | inst
    events = []
    done = set()
    for k, tf in zip(*np.nonzero(hit)):
        if first_only and tf in done:
            continue
        done.add(int(tf))
        events.append((int(k), int(tf)))
    events.sort()
    return events


def tier_codes(pct, step_minutes):
    """int8[n, m] codes 0-5 (module docstring). `step_minutes` may be fractional (60 s = 1.0)."""
    pct = np.atleast_2d(np.asarray(pct, dtype=float))
    codes = np.zeros(pct.shape, dtype=np.int8)
    codes[pct > TIER_AMBER_PCT] = 1
    above = pct > TIER_NORMAL_PCT
    runs = _run_lengths(above)
    need = max(1, math.ceil(TIER_NORMAL_MIN / step_minutes))
    codes[above] = 2
    codes[above & (runs >= need)] = 3
    codes[pct > TIER_EMERGENCY_PCT] = 4
    for k, tf in protection_events(pct, step_minutes * 60):
        codes[k:, tf] = 5
    return codes


def normal_events(pct, step_minutes):
    """[(tf, start_step, end_step_exclusive)] for every run above 110% lasting >= 30 minutes."""
    pct = np.atleast_2d(np.asarray(pct, dtype=float))
    need = max(1, math.ceil(TIER_NORMAL_MIN / step_minutes))
    out = []
    n = pct.shape[0]
    for tf in range(pct.shape[1]):
        k = 0
        col = pct[:, tf] > TIER_NORMAL_PCT
        while k < n:
            if col[k]:
                j = k
                while j < n and col[j]:
                    j += 1
                if j - k >= need:
                    out.append((tf, k, j))
                k = j
            else:
                k += 1
    return out


def tier_strings(codes):
    """int8[n, m] -> n strings of m digits (the JSON form)."""
    codes = np.asarray(codes, dtype=np.int8)
    return ["".join(map(str, row.tolist())) for row in codes]


def summary_counts(pct, step_minutes):
    """Plain counts for reports: {normalEvents, emergencyTfs, amberTfs, protection}."""
    pct = np.atleast_2d(np.asarray(pct, dtype=float))
    return {"normalEvents": len(normal_events(pct, step_minutes)),
            "emergencyTfs": int((pct > TIER_EMERGENCY_PCT).any(axis=0).sum()),
            "amberTfs": int((pct > TIER_AMBER_PCT).any(axis=0).sum()),
            "protection": protection_events(pct, step_minutes * 60)}
