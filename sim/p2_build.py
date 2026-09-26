"""Build P2: the month what-if (build prompt 5.6; lane L3). Everything is precomputed; the UI only looks results up.

    python -m sim.p2_build            # heavy (take the lock: scripts/build_all.sh p2): 16 combos + useful capacity
    python -m sim.p2_build --quick    # < 20 s, no lock, writes nothing: the default combo on 4 days, top 5 printed
    python -m sim.p2_build --bench    # as the full build, and re-measures engine.screenSecondsPerCombo

Writes ui/data/p2/index.json, ui/data/p2/<combo>.json (16) and data/out/siting-2026-08.csv. When
data/out/referee-2026-08.json exists and was computed on the same battery schedules (its `schedule_sha256`), its
OpenDSS numbers are merged in (sim.referee writes that file and then re-merges); otherwise every card says
"screening" and index.referee.runs is 0.

Determinism: no wall clock in the output except engine.screenSecondsPerCombo, which is measured only with --bench and
otherwise carried over from the committed index.json, so a rebuild on the same inputs is byte-identical.
"""
import csv
import hashlib
import io
import json
import math
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np

from . import siting
from .constants import (export, FOCUS_TFS, BRIDGE_TF, CORE_POWER_KW, GROWTH, CURTAIL_CAP, AWARE_MARGIN, HEAD_RATING_KVA)
from .contracts import envelope, inputs_sha, labelled, write_json, dumps
from .prices import find_cliffs
from .siting import (World, simulate, month_metrics, REPORTED, STEPS, STEP_MIN, MONTH_T0, MONTH_DAYS, TOP_N, GREEDY_N,
                     month_prices, day_windows, stamp, growth_factor)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ui" / "data" / "p2"
CSV_OUT = ROOT / "data" / "out" / "siting-2026-08.csv"
REFEREE_JSON = ROOT / "data" / "out" / "referee-2026-08.json"
POLICIES = ("naive", "aware")
CLS = ("core", "legacy")
RULES = ("d26", "cheapest")
GROWTHS = (0, 20)
COMBOS = [f"{p}-{c}-{r}-g{g}" for p in POLICIES for c in CLS for r in RULES for g in GROWTHS]
DEFAULT = "aware-core-d26-g0"
FLIP = ("naive-core-d26-g0", "aware-core-d26-g0")
SCREEN = "surrogate screen (sim.surrogate, calibrated vs OpenDSS); not OpenDSS-checked"
HEAD_CITE = ("feeder-head estimate: lossless sum of every transformer's load vs 370 A x sqrt(3) x 12.47 kV = 7,991.5 kVA "
             "(site/ems/flow-spec.md); reads low (no losses); overAt = first placement above 100% (null: never)")
CONSTS = ("HEAD_CAP", "HEAD_RATING_A", "HEAD_RATING_KVA", "AWARE_MARGIN", "CORE_POWER_KW", "CORE_USABLE_KWH", "CORE_RTE", "LEGACY_POWER_KW", "LEGACY_USABLE_KWH",
          "LEGACY_RTE", "RESERVE_FLOOR", "SOC_BUCKET", "MIN_GRANT_KW", "GROWTH", "CURTAIL_CAP", "P2_SOC0",
          "P2_DISCHARGE_FROM", "P2_CHARGE_END", "P2_CONTROLLER_VIEW", "P2_CAUSED_EPS_PTS", "CURTAIL_VALUE_RULE",
          "TIER_AMBER_PCT", "TIER_NORMAL_PCT", "TIER_NORMAL_MIN", "TIER_EMERGENCY_PCT", "FUSE_PCT", "FUSE_MINUTES",
          "FUSE_INSTANT_PCT", "FUSE_INSTANT_SECONDS", "ONSET_MEDIAN_MULT", "LOAD_PAIRING", "PROFILE_INDEX_RULE",
          "FLEET_SEED", "FLEET_SIZE")
SOURCES = {"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min, August 2026"},
           "load": {"label": "SIM", "text": "NREL SMART-DS 2018 AUS P1U per-load kW and kvar shapes, same calendar date (2018 load / 2026 prices: ASSUMPTION); 1 Sep 2018 loads for the 31 Aug night"},
           "screen": {"label": "SIM", "text": "sim.surrogate: summed home P and Q per transformer + battery P + calibrated losses"},
           "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow on the shortlist runs (sim.referee)"},
           "fleet": {"label": "ASSUMPTION", "text": "the prototype's 96-Core placement (seed 17263), data/fleet.json"}}


# =================================================================================================================
class Ctx:
    """Inputs shared by every combo: loads per transformer, topology maps, surrogate coefficients, candidates."""

    def __init__(self, loads=None):
        from .loads import Loads
        from .surrogate import coefficients
        from .topology import load_table
        self.loads = loads or Loads()
        self.t = load_table()
        topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text())
        self.topo = topo
        self.P, self.Q = self.loads.tf_pq(0, STEPS)
        self.kva = np.asarray(self.t["kva"], dtype=float)
        self.coeffs, self.coeff_meta = coefficients()
        self.home_tf = np.asarray(self.t["home_tf"])
        self.home_ids = list(self.t["home_ids"])
        self.labels = [h["label"] for h in topo["homes"]]
        self.fleet = [int(x) for x in self.t["fleet"]]
        fset = set(self.fleet)
        eligible = [i for i, h in enumerate(topo["homes"]) if h["eligible"]]
        self.eligible = eligible
        self.cands = [i for i in eligible if i not in fset]                  # 911
        self.n_tf = len(self.kva)
        self.cand_on = [[] for _ in range(self.n_tf)]
        self.elig_on = [[] for _ in range(self.n_tf)]
        self.fleet_on = [[] for _ in range(self.n_tf)]
        for h in self.cands:
            self.cand_on[self.home_tf[h]].append(h)
        for h in eligible:
            self.elig_on[self.home_tf[h]].append(h)
        for h in self.fleet:
            self.fleet_on[self.home_tf[h]].append(h)
        self.tf_ids = list(self.t["tf_ids"])
        self.tf_index = {x: i for i, x in enumerate(self.tf_ids)}
        self.A = self.tf_index[FOCUS_TFS["A"]]
        self.T240 = self.tf_index[BRIDGE_TF]
        self.price = month_prices(STEPS)
        self.price_median = float(np.median(self.price[:REPORTED]))
        self._driver = {}

    def driver(self, tf, k):
        key = (int(tf), int(k))
        if key not in self._driver:
            d = self.loads.driver(tf, k)
            d["t"] = stamp(k)
            self._driver[key] = d
        return self._driver[key]


def siting_world(ctx, cls_new, kmax=GREEDY_N, with_fleet=True, pool=None):
    """Columns (tf, k): the existing fleet on tf (if with_fleet) plus the first k homes of pool[tf] (id order),
    k = 0..min(kmax, len(pool[tf])). Returns (World, col_of{(tf,k): col}, newb{(tf,k): battery index of the k-th})."""
    pool = pool if pool is not None else ctx.cand_on
    col_tf, col, home, cls, new = [], [], [], [], []
    col_of, newb = {}, {}
    for tf in range(ctx.n_tf):
        K = min(kmax, len(pool[tf]))
        for k in range(K + 1):
            c = len(col_tf)
            col_tf.append(tf)
            col_of[(tf, k)] = c
            if with_fleet:
                for h in ctx.fleet_on[tf]:
                    col.append(c), home.append(h), cls.append("core"), new.append(False)
            for j, h in enumerate(pool[tf][:k]):
                if j == k - 1:
                    newb[(tf, k)] = len(col)
                col.append(c), home.append(h), cls.append(cls_new), new.append(True)
    return World(col_tf, col, home, cls, new), col_of, newb


def run_world(ctx, world, policy, rule, g, steps=STEPS):
    f = growth_factor(g)
    sim = simulate(world, ctx.P * f, ctx.Q * f, ctx.kva, ctx.coeffs, policy, rule, steps=steps)
    n = min(REPORTED, steps)
    sim["M"] = month_metrics(sim["pct"], sim["pct_none"], sim["col_kw"], steps=n)
    sim["n"] = n
    return sim


# =================================================================================================================
def evaluate(ctx, sim, col_wo, col_w, b):
    """The candidate metrics: world col_w (with the new battery b) against col_wo (without). Plain floats."""
    M = sim["M"]
    n = sim["n"]
    tf = int(ctx_tf(sim, col_wo))
    kva = ctx.kva[tf]
    pw, pwo = sim["pct"][:n, col_w], sim["pct"][:n, col_wo]
    relief = float(((np.maximum(0, pwo - 100) - np.maximum(0, pw - 100)) / 100 * kva * STEP_MIN / 60).sum())
    newv = bool(M["normalEvents"][col_w] > M["normalEvents"][col_wo] or M["emergencyN"][col_w] > M["emergencyN"][col_wo]
                or (M["protection"][col_w] >= 0 and M["protection"][col_wo] < 0))
    h_w, h_wo = float(M["h100"][col_w]), float(M["h100"][col_wo])
    rev = float(sim["revenue"][b])
    cur = float(sim["curtail_kwh"][b])
    cost = cur * ctx.price_median / 1000.0
    e = {"newViolation": newv, "avoided": max(0.0, h_wo - h_w), "added": max(0.0, h_w - h_wo),
         "peakWith": float(M["peak"][col_w]), "peakWithout": float(M["peak"][col_wo]), "relief": relief,
         "revenue": rev, "curtail": cur, "curtailCost": cost, "need": float(sim["need_kwh"][b]),
         "protWith": int(M["protection"][col_w]), "protWithout": int(M["protection"][col_wo]),
         "col_w": col_w, "col_wo": col_wo, "tf": tf}
    e["key"] = (int(newv), -round(e["avoided"], 6), round(e["peakWith"], 6), -round(rev - cost, 6))
    return e


def ctx_tf(sim, col):
    return sim["col_tf"][col]


def metrics_of(M, col, label="SIM", cite=None):
    """before{}/after{} block: labelled numbers of one column."""
    lab = lambda v, **kw: labelled(v, label, cite, **kw)  # noqa: E731
    prot = int(M["protection"][col])
    return {"peakPct": lab(round(float(M["peak"][col]), 1), t=stamp(int(M["peakT"][col]))),
            "h100": lab(round(float(M["h100"][col]), 2)), "h110": lab(round(float(M["h110"][col]), 2)),
            "normalEvents": lab(int(M["normalEvents"][col])), "normalH": lab(round(float(M["normalH"][col]), 2)),
            "emergencyN": lab(int(M["emergencyN"][col])),
            "protection": lab(prot >= 0, t=stamp(prot) if prot >= 0 else None)}


def reason_of(e):
    if e["newViolation"]:
        return (f"adds a violation (SIM): with the battery the month peak is {e['peakWith']:.1f}% "
                f"({e['added']:.2f} h more above nameplate); where NOT to put it")
    if e["avoided"] > 0:
        return (f"relieves {e['avoided']:.2f} h above nameplate (SIM); no new violation; month peak with the battery "
                f"{e['peakWith']:.1f}% (SIM)")
    return f"no stress to relieve; no new violation; month peak with the battery {e['peakWith']:.1f}% (SIM, lowest first)"


def homes_dark(ctx, tf):
    fset = set(ctx.fleet)
    return [h for h in np.flatnonzero(ctx.home_tf == tf).tolist() if h not in fset]


def entry_doc(ctx, sim, e, rank, home, tie_broken, cls_new):
    tf = e["tf"]
    M = sim["M"]
    dark = homes_dark(ctx, tf) if (e["protWith"] >= 0) else []
    d = {"rank": rank, "home": home, "homeId": ctx.home_ids[home], "label": ctx.labels[home], "tf": tf,
         "tfId": ctx.tf_ids[tf], "kva": labelled(ctx.kva[tf], "REAL", "SMART-DS Transformers.dss"),
         "reason": reason_of(e),
         "alsoOnTf": [h for h in ctx.cand_on[tf] if h != home], "tieBroken": bool(tie_broken),
         "noNewViolation": labelled(not e["newViolation"], "SIM", SCREEN),
         "peakWithPct": labelled(round(e["peakWith"], 1), "SIM", SCREEN),
         "stressAvoidedH": labelled(round(e["avoided"], 2), "SIM", SCREEN),
         "stressAddedH": labelled(round(e["added"], 2), "SIM", SCREEN),
         "reliefKWh": labelled(round(e["relief"], 1), "SIM", "kWh above nameplate shaved (negative: added)"),
         "revenueUSD": labelled(round(e["revenue"], 2), "DERIVED", "the new battery's energy value, sum of -P x REAL price x dt, 1 Aug 00:00 -> 1 Sep 06:00"),
         "curtailKWh": labelled(round(e["curtail"], 1), "SIM", "energy not charged by 06:00 (ASSUMPTION: the zone fleet absorbs it)"),
         "curtailCostUSD": labelled(round(e["curtailCost"], 2), "ASSUMPTION", "CURTAIL_VALUE_RULE"),
         "protectionWith": labelled(e["protWith"] >= 0, "SIM", "protection may operate (ASSUMPTION rule: one 15-min interval above 200%)"),
         "homesDarkWith": dark,
         "cls": cls_new,
         "before": metrics_of(M, e["col_wo"], cite=SCREEN), "after": metrics_of(M, e["col_w"], cite=SCREEN),
         "opendss": None, "screening": True}
    if M["h100"][e["col_wo"]] > 0:
        d["driver"] = ctx.driver(tf, int(M["peakT"][e["col_wo"]]))
    return d


# =================================================================================================================
def rank_combo(ctx, sim, col_of, newb):
    """Greedy step 0: one entry per transformer with candidates (the lowest-id candidate; siblings in alsoOnTf),
    sorted by the 5.6 rule. Returns (entries [(key+(home,), e, tf, home)], home_rank{home: rank 1..911},
    tie_home{home: bool}, tie_entry{tf: bool})."""
    rows = []
    for tf in range(ctx.n_tf):
        if not ctx.cand_on[tf] or (tf, 1) not in col_of:
            continue
        e = evaluate(ctx, sim, col_of[(tf, 0)], col_of[(tf, 1)], newb[(tf, 1)])
        home = ctx.cand_on[tf][0]
        rows.append((e["key"] + (home,), e, tf, home))
    rows.sort(key=lambda r: r[0])
    keys = [r[0][:-1] for r in rows]
    from collections import Counter
    kc = Counter(keys)
    tie_entry = {r[2]: kc[r[0][:-1]] > 1 for r in rows}
    home_rank, tie_home = {}, {}
    r = 0
    for _, e, tf, home in rows:
        for h in ctx.cand_on[tf]:
            r += 1
            home_rank[h] = r
            tie_home[h] = tie_entry[tf] or len(ctx.cand_on[tf]) > 1
    return rows, home_rank, tie_home, tie_entry


def feeder_state(M, cols):
    cols = np.asarray(cols)
    return {"normalTfs": int((M["normalEvents"][cols] > 0).sum()), "emergencyTfs": int((M["emergencyN"][cols] > 0).sum()),
            "h110": float(M["h110"][cols].sum()), "h100": float(M["h100"][cols].sum()),
            "causedNormalTfs": int((M["causedNormal"][cols] > 0).sum())}


def head_pct(tot_p, tot_q, n):
    """Feeder-head estimate: max over the reported steps of |sum P + j sum Q| of every transformer's secondary load,
    in % of HEAD_RATING_KVA (370 A x sqrt(3) x 12.47 kV, DERIVED). Lossless: it ignores transformer and line losses and
    the voltage, so it reads LOW; OpenDSS is not run on these worlds."""
    return float(np.max(np.hypot(tot_p[:n], tot_q[:n])) / HEAD_RATING_KVA * 100.0)


def greedy(ctx, sim, col_of, newb, pool, n_steps, stop=None, track_head=False, growth=1.0):
    """Place the best next battery, re-score that transformer, repeat (exact in the surrogate: transformers are
    independent). pool[tf] = the homes that may be added on tf, id order. Returns the placement list and the
    feeder state after each."""
    M = sim["M"]
    k = [0] * ctx.n_tf
    K = [0] * ctx.n_tf
    for (t, kk) in col_of:
        K[t] = max(K[t], kk)
    ctx_P = ctx.P * growth
    ctx_Q = ctx.Q * growth
    cur = [col_of[(tf, 0)] for tf in range(ctx.n_tf)]
    cache = {}

    def ev(tf):
        kk = k[tf]
        if (tf, kk) not in cache:
            cache[(tf, kk)] = evaluate(ctx, sim, col_of[(tf, kk)], col_of[(tf, kk + 1)], newb[(tf, kk + 1)])
        return cache[(tf, kk)]

    import heapq
    heap = []
    for tf in range(ctx.n_tf):
        if K[tf] > 0:
            e = ev(tf)
            heapq.heappush(heap, (e["key"] + (pool[tf][0],), tf))
    out = []
    state0 = feeder_state(M, cur)
    head = None
    if track_head:
        ck = sim["col_kw"]
        tot_p = ctx_P.sum(axis=1) + ck[:, cur].sum(axis=1)
        tot_q = ctx_Q.sum(axis=1)
        state0["headPct"] = head_pct(tot_p, tot_q, sim["n"])
    while heap and len(out) < n_steps:
        key, tf = heapq.heappop(heap)
        e = ev(tf)
        home = pool[tf][k[tf]]
        k[tf] += 1
        old_col = cur[tf]
        cur[tf] = col_of[(tf, k[tf])]
        st = feeder_state(M, cur)
        if track_head:
            tot_p += ck[:, cur[tf]] - ck[:, old_col]
            st["headPct"] = head_pct(tot_p, tot_q, sim["n"])
        nxt = None
        if k[tf] < K[tf]:
            ne = ev(tf)
            nxt = ne["key"]
            heapq.heappush(heap, (ne["key"] + (pool[tf][k[tf]],), tf))
        out.append({"k": len(out) + 1, "home": home, "tf": tf, "e": e, "state": st, "next_key": nxt,
                    "cur": list(cur), "curtail": sum(float(sim["curtail_kwh"][b]) for b in placed_batteries(newb, k)),
                    "need": sum(float(sim["need_kwh"][b]) for b in placed_batteries(newb, k))})
        if stop is not None and stop(out[-1]):
            break
    return out, state0


def placed_batteries(newb, k):
    """Battery indices of every placed new battery in the current worlds (tf, k[tf])."""
    bs = []
    for tf, kk in enumerate(k):
        # the batteries of world (tf, kk) that are new: the j-th new one sits at newb[(tf, kk)] - (kk - j)
        if kk > 0:
            last = newb[(tf, kk)]
            bs.extend(range(last - kk + 1, last + 1))
    return bs


def hourly_max(x, n):
    x = np.asarray(x)[: (n // 4) * 4]
    return x.reshape(-1, 4).max(axis=1)


def i10(x):
    return np.rint(np.asarray(x, dtype=float) * 10).astype(int).tolist()


# =================================================================================================================
def build_combo(ctx, combo, steps=STEPS):
    pol, cls_new, rule, g = combo.split("-")
    world, col_of, newb = siting_world(ctx, cls_new)
    sim = run_world(ctx, world, pol, rule, int(g[1:]), steps)
    sim["col_tf"] = world.col_tf
    M = sim["M"]
    n = sim["n"]
    rows, home_rank, tie_home, tie_entry = rank_combo(ctx, sim, col_of, newb)
    ranking = [entry_doc(ctx, sim, e, i + 1, home, tie_entry[tf], cls_new) for i, (_, e, tf, home) in enumerate(rows[:TOP_N])]
    gl, _ = greedy(ctx, sim, col_of, newb, ctx.cand_on, GREEDY_N)
    greedy_doc = [{"k": x["k"], "home": x["home"], "tf": x["tf"], "label": ctx.labels[x["home"]],
                   "feeder": {"normalTfs": labelled(x["state"]["normalTfs"], "SIM", SCREEN),
                              "emergencyTfs": labelled(x["state"]["emergencyTfs"], "SIM", SCREEN),
                              "h110": labelled(round(x["state"]["h110"], 2), "SIM", SCREEN)},
                   "keyDrops": x["next_key"] is None or x["next_key"] > x["e"]["key"]} for x in gl]
    base_cols = [col_of[(tf, 0)] for tf in range(ctx.n_tf)]
    strips = {}
    strip_tfs = []
    for x in [r[2] for r in rows[:10]] + [ctx.A, ctx.T240]:
        if x not in strip_tfs:
            strip_tfs.append(x)
    for tf in strip_tfs:
        c0 = col_of[(tf, 0)]
        c1 = col_of.get((tf, 1), c0)
        pk = int(M["peakT"][c0])
        d = pk // 96
        strips[str(tf)] = {"without": i10(hourly_max(sim["pct"][:n, c0], n)),
                           "with": i10(hourly_max(sim["pct"][:n, c1], n)),
                           "candidate": ctx.cand_on[tf][0] if ctx.cand_on[tf] else None,
                           "peakDay": {"day": (MONTH_T0 + timedelta(days=d)).strftime("%Y-%m-%d"),
                                       "without": i10(sim["pct"][d * 96:(d + 1) * 96, c0]),
                                       "with": i10(sim["pct"][d * 96:(d + 1) * 96, c1])}}
    baseline = {"peak": i10(M["peak"][base_cols]), "peakT": [int(x) for x in M["peakT"][base_cols]],
                "h100": [round(float(x), 2) for x in M["h100"][base_cols]],
                "normalEvents": [int(x) for x in M["normalEvents"][base_cols]],
                "emergencyN": [int(x) for x in M["emergencyN"][base_cols]],
                "protection": [int(x) for x in M["protection"][base_cols]],
                "causedNormal": [int(x) for x in M["causedNormal"][base_cols]]}
    totals = {"normalEvents": labelled(int(M["normalEvents"][base_cols].sum()), "SIM", SCREEN),
              "causedNormal": labelled(int(M["causedNormal"][base_cols].sum()), "SIM", "normal events during which the fleet raised loading (P2 definition)"),
              "causedLagNormal": labelled(int(M["causedLagNormal"][base_cols].sum()), "SIM", "7.3's rule at 15-min steps: fleet charging or back-feeding at a step of the run or within the 2 steps before it (report only)"),
              "h100": labelled(round(float(M["h100"][base_cols].sum()), 2), "SIM", SCREEN),
              "emergencyN": labelled(int(M["emergencyN"][base_cols].sum()), "SIM", SCREEN),
              "protectionTfs": labelled(int((M["protection"][base_cols] >= 0).sum()), "SIM", "ASSUMPTION rule, 4.5")}
    nv_rows = [r for r in rows if r[1]["newViolation"]]
    totals["newViolationTfs"] = labelled(len(nv_rows), "SIM", "transformers where one more battery adds a normal-tier event, an emergency interval or a protection operation")
    totals["newViolationHomes"] = labelled(sum(len(ctx.cand_on[r[2]]) for r in nv_rows), "SIM", "candidates on those transformers")
    prot_cases = [{"home": r[3], "tf": r[2], "label": ctx.labels[r[3]], "t": stamp(r[1]["protWith"]),
                   "peakWithPct": labelled(round(r[1]["peakWith"], 1), "SIM", SCREEN), "homesDark": homes_dark(ctx, r[2])}
                  for r in rows if r[1]["protWith"] >= 0 and r[1]["protWithout"] < 0]
    totals["protectionWithTfs"] = labelled(len(prot_cases), "SIM", "protection may operate (ASSUMPTION rule) with one more battery")
    doc = envelope(f"p2.{combo}", "sim.p2_build", inputs=inputs_sha(), constants=export(*CONSTS), sources=SOURCES,
                   series={"baseline": {"label": "SIM", "unit": "peak pct x10, peakT step, h100 hours, counts; existing 96-Core fleet under this combo", "by": "surrogate"},
                           "strips": {"label": "SIM", "unit": "pct x10, hourly max (with = + the listed candidate)", "by": "surrogate"}})
    doc.update({"combo": combo, "policy": pol, "cls": cls_new, "rule": rule, "growth": int(g[1:]),
                "baseline": baseline, "headline": totals, "ranking": ranking, "greedy": greedy_doc, "strips": strips,
                "protectionCases": prot_cases})
    extra = {"sim": sim, "col_of": col_of, "newb": newb, "world": world, "rows": rows, "home_rank": home_rank,
             "tie_home": tie_home, "greedy": gl, "base_cols": base_cols}
    return doc, extra


# =================================================================================================================
def spearman(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 2:
        return 0.0
    ra = np.argsort(np.argsort(a, kind="stable"), kind="stable").astype(float)
    rb = np.argsort(np.argsort(b, kind="stable"), kind="stable").astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = math.sqrt(float((ra * ra).sum() * (rb * rb).sum()))
    return float((ra * rb).sum() / den) if den else 0.0


def flip_doc(ctx, xn, xa):
    top_n = [r[3] for r in xn["rows"][:10]]
    top_a = [r[3] for r in xa["rows"][:10]]
    homes = sorted(ctx.cands)
    rn = [xn["home_rank"][h] for h in homes]
    ra = [xa["home_rank"][h] for h in homes]
    untied = [h for h in homes if not xn["tie_home"][h] and not xa["tie_home"][h]]
    un_n = sorted(untied, key=lambda h: xn["home_rank"][h])[:10]
    un_a = sorted(untied, key=lambda h: xa["home_rank"][h])[:10]
    rho = spearman(rn, ra)
    rho_u = spearman([xn["home_rank"][h] for h in untied], [xa["home_rank"][h] for h in untied])
    rank_n = {r[2]: i + 1 for i, r in enumerate(xn["rows"])}
    rank_a = {r[2]: i + 1 for i, r in enumerate(xa["rows"])}
    movers = sorted(rank_n, key=lambda tf: (-(rank_n[tf] - rank_a[tf]), tf))[:5]
    mov = [{"tf": tf, "home": ctx.cand_on[tf][0], "label": ctx.labels[ctx.cand_on[tf][0]],
            "rankNaive": labelled(rank_n[tf], "DERIVED", "collapsed naive ranking"),
            "rankAware": labelled(rank_a[tf], "DERIVED", "collapsed aware ranking")} for tf in movers]
    return {"movers": mov, "entries": labelled(len(rank_n), "DERIVED", "transformers with candidates (collapsed entries)"),
            "top10Overlap": labelled(len(set(top_n) & set(top_a)), "DERIVED", "collapsed rankings (one entry per transformer), naive vs aware"),
            "spearman": labelled(round(rho, 4), "DERIVED", f"all {len(homes)} candidates, ranks with id tie-breaks"),
            "untied": {"top10Overlap": labelled(len(set(un_n) & set(un_a)), "DERIVED", "candidates no id tie-break placed, in either ranking"),
                       "spearman": labelled(round(rho_u, 4), "DERIVED", "untied candidates only"),
                       "n": len(untied)},
            "combos": list(FLIP), "topNaive": top_n, "topAware": top_a}


def useful_capacity(ctx, steps=STEPS):
    """From an EMPTY feeder (no existing fleet), each policy's greedy order over all eligible homes (the 96 fleet homes
    are candidates like any other; homes on one transformer go by id), core-d26-g0, until the stop."""
    out = {}
    for pol in POLICIES:
        world, col_of, newb = siting_world(ctx, "core", kmax=99, with_fleet=False, pool=ctx.elig_on)
        sim = run_world(ctx, world, pol, "d26", 0, steps)
        sim["col_tf"] = world.col_tf
        curve = []

        def stop(x, pol=pol):
            curt = x["curtail"] / x["need"] if x["need"] > 0 else 0.0
            curve.append([x["k"], x["state"]["causedNormalTfs"], int(round(curt * 1000)), round(x["state"]["h110"], 2),
                          int(round(x["state"]["headPct"] * 10))])
            if pol == "naive":
                return x["state"]["causedNormalTfs"] > 0
            return curt > CURTAIL_CAP

        gl, st0 = greedy(ctx, sim, col_of, newb, ctx.elig_on, len(ctx.eligible), stop=stop, track_head=True)
        last = gl[-1] if gl else None
        if last is None:
            n_ok, why = 0, "no candidates"
        elif stop_hit(pol, last):
            n_ok = last["k"] - 1
            why = (f"placement {last['k']} ({ctx.labels[last['home']]} on tf {last['tf']}) makes the first battery-caused normal-tier event"
                   if pol == "naive" else
                   f"placement {last['k']} ({ctx.labels[last['home']]} on tf {last['tf']}) takes feeder curtailment above {CURTAIL_CAP:.0%}")
        else:
            n_ok, why = last["k"], f"all {len(ctx.eligible)} eligible homes used (transformer limits only)"
        head_over = next((x["k"] for x in gl if x["state"]["headPct"] > 100.0), None)
        if head_over is not None:
            why += f"; the feeder-head estimate (DERIVED, lossless) passes 100% at placement {head_over}"
        head_at = gl[n_ok - 1]["state"]["headPct"] if n_ok > 0 else st0["headPct"]
        out[pol] = {"n": n_ok, "stop": why, "curve": curve, "headOverAt": head_over, "headPctAtN": head_at,
                    "headPct0": st0["headPct"], "order": [x["home"] for x in gl]}
    # aware with the feeder head as a fleet-total cap (4.4): transformers are no longer independent, so each point is
    # one coupled month run of the first k placements of aware's greedy order; the stop is curtailment above CURTAIL_CAP
    out["awareHead"] = head_capped_capacity(ctx, out["aware"]["order"], steps)
    return out


def coupled_run(ctx, homes, steps=STEPS):
    """One month, aware + head cap, one column per transformer, Cores on `homes`: (curtail fraction, row, sim)."""
    world = World(list(range(ctx.n_tf)), [int(ctx.home_tf[h]) for h in homes], list(homes), ["core"] * len(homes),
                  [True] * len(homes))
    sim = simulate(world, ctx.P, ctx.Q, ctx.kva, ctx.coeffs, "aware", "d26", steps=steps, head_kva=HEAD_RATING_KVA)
    n = min(REPORTED, steps)
    M = month_metrics(sim["pct"], sim["pct_none"], sim["col_kw"], steps=n)
    need = float(sim["need_kwh"].sum())
    curt = float(sim["curtail_kwh"].sum()) / need if need > 0 else 0.0
    hp = head_pct(ctx.P.sum(axis=1) + sim["col_kw"].sum(axis=1), ctx.Q.sum(axis=1), n)
    row = [len(homes), int((M["causedNormal"] > 0).sum()), int(round(curt * 1000)), round(float(M["h110"].sum()), 2),
           int(round(hp * 10))]
    return curt, row


def head_capped_capacity(ctx, order, steps=STEPS, grid=50):
    pts = {}

    def f(k):
        if k not in pts:
            pts[k] = coupled_run(ctx, order[:k], steps)
        return pts[k][0]

    ks = list(range(grid, len(order), grid)) + [len(order)]
    lo, hi = 0, None
    for k in ks:
        if f(k) > CURTAIL_CAP:
            hi = k
            break
        lo = k
    if hi is None:
        n, why = len(order), f"all {len(order)} eligible homes used with the feeder-head cap"
    else:
        while hi - lo > 1:                     # first k above the cap (curtailment grows with k)
            mid = (lo + hi) // 2
            if f(mid) > CURTAIL_CAP:
                hi = mid
            else:
                lo = mid
        n = lo
        why = (f"placement {hi} ({ctx.labels[order[hi - 1]]}) takes feeder curtailment to {pts[hi][0]:.1%}, above "
               f"{CURTAIL_CAP:.0%}, with the feeder-head cap (HEAD_CAP, ASSUMPTION)")
    curve = [pts[k][1] for k in sorted(pts)]
    return {"n": n, "stop": why, "curve": curve, "evaluated": len(pts)}


def stop_hit(pol, x):
    if pol == "naive":
        return x["state"]["causedNormalTfs"] > 0
    return x["need"] > 0 and x["curtail"] / x["need"] > CURTAIL_CAP


# =================================================================================================================
def schedule_sha(extras):
    """sha256 of the battery schedules the referee judges (both default combos, g0 and g20)."""
    h = hashlib.sha256()
    for combo in sorted(extras):
        h.update(combo.encode())
        h.update(np.ascontiguousarray(extras[combo]["sim"]["kw"]).tobytes())
    return h.hexdigest()


def load_referee(sha):
    if not REFEREE_JSON.exists():
        return None
    doc = json.loads(REFEREE_JSON.read_text())
    return doc if doc.get("schedule_sha256") == sha else None


def apply_referee(index, combos, ref):
    """Merge sim.referee's OpenDSS numbers into index.referee and the shortlist cards (both default combos)."""
    if ref is None:
        index["referee"] = {"runs": 0, "status": "not run on these schedules (run scripts/build_all.sh referee)",
                            "errorPts": {"max": labelled(None, "SIM", "not run"), "p99": labelled(None, "SIM", "not run")},
                            "tierAgreementPct": labelled(None, "SIM", "not run")}
        return
    index["referee"] = {"runs": ref["runs"], "steps": ref["steps"], "status": "OpenDSS-checked shortlist",
                        "errorPts": {"max": labelled(ref["errorPts"]["max"], "SIM", "surrogate - OpenDSS, shortlisted transformers, all runs"),
                                     "p99": labelled(ref["errorPts"]["p99"], "SIM", "surrogate - OpenDSS, shortlisted transformers, all runs")},
                        "errorAllPts": {"max": labelled(ref["errorAllPts"]["max"], "SIM", "all 379 transformers"),
                                        "p99": labelled(ref["errorAllPts"]["p99"], "SIM", "all 379 transformers")},
                        "tierAgreementPct": labelled(ref["tierAgreementPct"], "SIM", "tier code per step and transformer, surrogate vs OpenDSS, shortlist"),
                        "shortlist": ref["shortlist"], "runList": ref["runList"],
                        "baselineCausedNormal": {k: labelled(v, "SIM", "OpenDSS, existing fleet, battery-caused normal-tier events")
                                                 for k, v in ref["baselineCausedNormal"].items()}}
    for combo, cards in ref["cards"].items():
        doc = combos.get(combo)
        if doc is None:
            continue
        for ent in doc["ranking"]:
            c = cards.get(str(ent["home"]))
            if c is None:
                continue
            cite = "OpenDSS (sim.referee): " + c["runs"]

            def relabel(block):
                if block is None:
                    return None
                return {k: labelled(v["v"], "SIM", cite, **{kk: vv for kk, vv in v.items() if kk not in ("v", "label", "cite")})
                        for k, v in block.items()}
            ent["opendss"] = {"before": relabel(c["before"]), "after": relabel(c["after"])}
            ent["screening"] = c["after"] is None


# =================================================================================================================
def build_index(ctx, extras, uc, bench_s):
    xn, xa = extras[FLIP[0]], extras[FLIP[1]]
    price = [round(float(p), 2) for p in ctx.price[:REPORTED]]
    cliffs = find_cliffs()
    # fleet counterfactual at the default settings (core, d26, g0): none / fleet naive / fleet aware
    fc, fct = {}, {}
    for name, x, which in (("none", xa, "pct_none"), ("naive", xn, "pct"), ("aware", xa, "pct")):
        cols = x["base_cols"]
        if which == "pct_none":
            Mx = month_metrics(x["sim"]["pct_none"][:, cols], steps=x["sim"]["n"])
            idx = slice(None)
        else:
            Mx = x["sim"]["M"]
            idx = cols
        fc[name] = {"h100": [round(float(v), 2) for v in Mx["h100"][idx]],
                    "normalEvents": [int(v) for v in Mx["normalEvents"][idx]],
                    "emergencyN": [int(v) for v in Mx["emergencyN"][idx]]}
        fct[name] = {"h100": labelled(round(float(Mx["h100"][idx].sum()), 2), "SIM", SCREEN),
                     "normalEvents": labelled(int(Mx["normalEvents"][idx].sum()), "SIM", SCREEN),
                     "emergencyN": labelled(int(Mx["emergencyN"][idx].sum()), "SIM", SCREEN),
                     "tfsOver100": labelled(int((Mx["h100"][idx] > 0).sum()), "SIM", SCREEN),
                     "causedNormal": labelled(int(Mx["causedNormal"][idx].sum()) if which == "pct" else 0, "SIM", "P2 definition"),
                     "headPct": labelled(round(head_pct(ctx.P.sum(axis=1) + (x["sim"]["col_kw"][:, cols].sum(axis=1) if which == "pct" else 0.0),
                                                        ctx.Q.sum(axis=1), x["sim"]["n"]), 1), "DERIVED", HEAD_CITE)}
        if name == "none":
            none_peakT = Mx["peakT"]
    tf_peak_hour = np.bincount(((np.asarray(none_peakT) % 96) // 4).astype(int), minlength=24).tolist()
    pmh = [0] * 24
    for d in range(MONTH_DAYS):
        pmh[int(np.argmax(ctx.price[d * 96:(d + 1) * 96])) // 4] += 1
    # drivers of the aware top 10
    profs = []
    for _, e, tf, home in xa["rows"][:10]:
        dr = ctx.driver(tf, int(xa["sim"]["M"]["peakT"][e["col_wo"]]))
        p = dr["profile"] if isinstance(dr["profile"], str) else "+".join(dr["profile"])
        profs.append(p)
    ties = sum(1 for h in ctx.cands if xa["tie_home"][h])
    windows = day_windows(STEPS)
    onsets = [{"day": w["day"], "onset": w["onset"], "price": labelled(w["price"], "REAL", "ERCOT RTM SPP LZ_NORTH"),
               "mode": w["mode"], "threshold": labelled(round(w["threshold"], 2), "DERIVED", "2 x the day's median price")}
              for w in windows]
    bridge = []
    for tf in (ctx.T240,):
        item = {"tf": tf, "id": ctx.tf_ids[tf], "candidates": ctx.cand_on[tf]}
        for pol, x in (("naive", xn), ("aware", xa)):
            for r, (_, e, t2, home) in enumerate(x["rows"]):
                if t2 == tf:
                    item[pol] = {"rank": r + 1, "home": home, "label": ctx.labels[home],
                                 "peakWithoutPct": labelled(round(e["peakWithout"], 1), "SIM", SCREEN),
                                 "peakWithPct": labelled(round(e["peakWith"], 1), "SIM", SCREEN),
                                 "h100Without": labelled(round(float(x["sim"]["M"]["h100"][e["col_wo"]]), 2), "SIM", SCREEN),
                                 "h100With": labelled(round(float(x["sim"]["M"]["h100"][e["col_w"]]), 2), "SIM", SCREEN),
                                 "noNewViolation": labelled(not e["newViolation"], "SIM", SCREEN)}
                    break
        c0 = xa["col_of"][(tf, 0)]
        item["driver"] = ctx.driver(tf, int(xa["sim"]["M"]["peakT"][c0]))
        bridge.append(item)
    index = envelope("p2.index", "sim.p2_build", inputs=inputs_sha(), constants=export(*CONSTS), sources=SOURCES,
                     series={"price": {"label": "REAL", "unit": "$/MWh"},
                             "fleetCounterfactual": {"label": "SIM", "unit": "hours / counts per transformer", "by": "surrogate"},
                             "insight": {"label": "SIM", "unit": "count per hour: tfPeakHour SIM (379 tfs, no batteries), priceMaxHour REAL (31 days)"},
                             "curve": {"label": "SIM", "unit": "[k placed, transformers with a battery-caused normal event, feeder curtailment per mille, feeder hours above 110%, feeder-head estimate pct x10 (DERIVED)]"}})
    index.update({
        "month": "2026-08", "stepMinutes": STEP_MIN, "steps": REPORTED, "extraSteps": STEPS - REPORTED,
        "controls": {"policy": list(POLICIES), "cls": list(CLS), "rule": list(RULES), "growth": list(GROWTHS)},
        "combos": list(COMBOS), "default": DEFAULT, "price": price, "onsets": onsets,
        "cliffs": {"count": labelled(len(cliffs), "DERIVED", "sim.prices.find_cliffs, 2026-01-01..2026-09-19"),
                   "evening": labelled(sum(c["evening"] for c in cliffs), "DERIVED", "later interval 20:00-23:59"),
                   "rule": "prev >= $60 and next <= 0.5 x prev, consecutive 15-min starts", "period": "2026-01-01..2026-09-19",
                   "events": cliffs},
        "fleetCounterfactual": fc, "fleetCounterfactualTotals": fct,
        "flip": flip_doc(ctx, xn, xa),
        "ties": {"byId": labelled(ties, "SIM", "candidates whose place only the id decided (siblings on one transformer are identical in the surrogate)"), "of": len(ctx.cands)},
        "drivers": {"top10DistinctProfiles": labelled(len(set(profs)), "SIM", "SMART-DS profiles of the aware top 10 (their transformer's peak home)"),
                    "profiles": profs},
        "insight": {"tfPeakHour": tf_peak_hour, "priceMaxHour": pmh},
        "usefulCapacity": {"naive": labelled(uc["naive"]["n"], "SIM", SCREEN, stop=uc["naive"]["stop"]),
                           "aware": labelled(uc["awareHead"]["n"], "SIM", SCREEN + "; aware with the feeder-head cap (HEAD_CAP)",
                                             stop=uc["awareHead"]["stop"]),
                           "awareTransformerOnly": labelled(uc["aware"]["n"], "SIM", SCREEN + "; transformer caps only, no head cap",
                                                            stop=uc["aware"]["stop"]),
                           "rule": "greedy order from an empty feeder (the 96 fleet homes are candidates like any other; homes on one transformer by id); naive stops at the first battery-caused normal-tier event; aware (feeder-head cap) at feeder curtailment above the cap",
                           "cap": labelled(CURTAIL_CAP, "ASSUMPTION", "CURTAIL_CAP"),
                           "feederHead": {pol: {"overAt": labelled(uc[pol]["headOverAt"], "DERIVED", HEAD_CITE),
                                                "pctAtN": labelled(round(uc[pol]["headPctAtN"], 1), "DERIVED", HEAD_CITE),
                                                "pctEmpty": labelled(round(uc[pol]["headPct0"], 1), "DERIVED", HEAD_CITE)}
                                          for pol in POLICIES},
                           "curve": {"naive": uc["naive"]["curve"], "aware": uc["awareHead"]["curve"],
                                     "awareTransformerOnly": uc["aware"]["curve"]}},
        "bridge": bridge,
        "engine": {"screenSecondsPerCombo": labelled(bench_s, "SIM", "sim.p2_build --bench wall time per combo (one run of 16), this machine")},
    })
    return index


def csv_bytes(ctx, doc, extra):
    """data/out/siting-2026-08.csv: all 911 candidates of the default combo, labelled header."""
    sim = extra["sim"]
    rows = extra["rows"]
    ref_cards = {e["home"]: e for e in doc["ranking"]}
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["rank", "home_id", "home_label", "tf_id", "tf_kva [REAL]", "no_new_violation [SIM]",
                "stress_avoided_h [SIM]", "stress_added_h [SIM]", "peak_without_pct [SIM]", "peak_with_pct [SIM]",
                "relief_kwh [SIM]", "revenue_usd [DERIVED]", "curtail_kwh [SIM]", "curtail_cost_usd [ASSUMPTION]",
                "protection_with [SIM, ASSUMPTION rule]", "tie_broken_by_id", "checked_by", "reason"])
    r = 0
    for _, e, tf, rep in rows:
        for h in ctx.cand_on[tf]:
            r += 1
            card = ref_cards.get(h)
            checked = "OpenDSS" if (card is not None and not card["screening"]) else "screening (surrogate)"
            w.writerow([r, ctx.home_ids[h], ctx.labels[h], ctx.tf_ids[tf], f"{ctx.kva[tf]:g}",
                        "yes" if not e["newViolation"] else "no", f"{e['avoided']:.2f}", f"{e['added']:.2f}",
                        f"{e['peakWithout']:.1f}", f"{e['peakWith']:.1f}", f"{e['relief']:.1f}", f"{e['revenue']:.2f}",
                        f"{e['curtail']:.1f}", f"{e['curtailCost']:.2f}", "yes" if e["protWith"] >= 0 else "no",
                        "yes" if extra["tie_home"][h] else "no", checked, reason_of(e) if h == rep else f"same transformer as {ctx.labels[rep]}"])
    return buf.getvalue().encode()


# =================================================================================================================
def build_all(bench=False, write=True, out=print):
    t0 = time.perf_counter()
    ctx = Ctx()
    combos, extras = {}, {}
    per = []
    for combo in COMBOS:
        t = time.perf_counter()
        doc, extra = build_combo(ctx, combo)
        per.append(time.perf_counter() - t)
        combos[combo] = doc
        if combo in FLIP or combo in ("naive-core-d26-g20", "aware-core-d26-g20"):
            extras[combo] = extra
        out(f"p2 {combo}: {per[-1]:.1f} s; #1 {doc['ranking'][0]['label'] if doc['ranking'] else '-'}")
    uc = useful_capacity(ctx)
    out(f"useful capacity: naive {uc['naive']['n']} / aware {uc['aware']['n']}")
    prev = OUT / "index.json"
    bench_s = None
    if bench:
        bench_s = round(float(np.median(per)), 1)
    elif prev.exists():
        try:
            bench_s = json.loads(prev.read_text())["engine"]["screenSecondsPerCombo"]["v"]
        except (KeyError, ValueError, TypeError):
            bench_s = None
    index = build_index(ctx, extras, uc, bench_s)
    sha = schedule_sha({k: extras[k] for k in referee_combos()})
    index["referee_schedule_sha256"] = sha
    apply_referee(index, combos, load_referee(sha))
    csvb = csv_bytes(ctx, combos[DEFAULT], extras[DEFAULT])
    if write:
        write_outputs(index, combos, csvb)
    out(f"p2 build: {time.perf_counter() - t0:.1f} s")
    return ctx, index, combos, extras, csvb


def referee_combos():
    return ("naive-core-d26-g0", "aware-core-d26-g0", "naive-core-d26-g20", "aware-core-d26-g20")


def write_outputs(index, combos, csvb):
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "index.json", index)
    for c, d in combos.items():
        write_json(OUT / f"{c}.json", d)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSV_OUT.write_bytes(csvb)


def quick(out=print):
    """< 20 s, no lock, writes nothing: the default combo over 4 days (1-4 Aug)."""
    t0 = time.perf_counter()
    ctx = Ctx()
    doc, extra = build_combo(ctx, DEFAULT, steps=4 * 96)
    out(f"p2 --quick {DEFAULT}, 4 days: {len(doc['ranking'])} entries, {time.perf_counter() - t0:.1f} s")
    for e in doc["ranking"][:5]:
        out(f"  {e['rank']} {e['label']}@tf{e['tf']} \"{e['reason']}\"")
    return doc


def main(argv):
    if "--quick" in argv:
        quick()
        return 0
    build_all(bench="--bench" in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
