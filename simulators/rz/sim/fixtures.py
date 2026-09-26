"""Fixtures: synthetic, deterministic stand-ins so the UI and P1/P2 lanes build before real data lands.

`FixtureLoads` has EXACTLY the `sim.loads.Loads` API (docs/contracts.md, Python APIs), with synthetic
diurnal shapes instead of SMART-DS profiles. Nothing here is real load data: every file written by
`python -m sim.fixtures` carries `"fixture": true` in its envelope and the UI shows a FIXTURE banner.

    python -m sim.fixtures        # write ui/data/fixtures/p1/* and ui/data/fixtures/p2/* (under 20 s, no lock)

Prices in the fixtures are the REAL LZ_NORTH prices (they exist from the start); loads, loadings,
rankings and every summary number are synthetic (labelled SIM with cite "fixture").
"""
import math
import sys
import zlib
from datetime import datetime, timedelta

import numpy as np

from .caps import transformer_caps
from .constants import (export, CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE, RESERVE_FLOOR, SOC_BUCKET,
                        MIN_GRANT_KW, FOCUS_TFS, BRIDGE_TF, TIER_AMBER_PCT, CONTROLLER_VIEW, CHARGE_URGENCY)
from .contracts import envelope, inputs_sha, labelled, write_json
from .feeder import ROOT
from .prices import price_at, onset_d26, discharge_plan, find_cliffs
from .tiers import tier_codes, tier_strings, protection_events, normal_events
from .topology import load_table

OUT = ROOT / "ui" / "data" / "fixtures"
FIX = "fixture: synthetic, not a result"
LOADS_TAG = "fixture:sim.fixtures.FixtureLoads(v1)"


class FixtureLoads:
    """Synthetic loads with the sim.loads.Loads API. 3,000 steps of 15 min from 2026-08-01T00:00."""
    steps = 3000
    step_minutes = 15
    t0 = "2026-08-01T00:00"

    def __init__(self, npz=None, table=None):
        self.table = table if table is not None else load_table()
        t = self.table
        names = sorted(set(t["profiles"]))
        self._pidx = np.array([names.index(p) for p in t["profiles"]], dtype=np.int64)
        k = np.arange(self.steps)
        hour = (k % 96) / 4.0
        day = k // 96
        shapes = np.zeros((len(names), self.steps))
        for i, name in enumerate(names):
            rng = np.random.default_rng(zlib.crc32(name.encode()))
            peak_h = 16.75 + rng.uniform(-1.5, 1.5)
            amp = rng.uniform(0.30, 0.55)
            base = rng.uniform(0.15, 0.28)
            phase = rng.uniform(0, 2 * math.pi)
            s = base + amp * np.exp(-((hour - peak_h) / 2.6) ** 2) + 0.10 * np.exp(-((hour - 7.5) / 1.5) ** 2)
            s *= 1 + 0.12 * np.sin(2 * math.pi * day / 7 + phase)
            shapes[i] = np.clip(s, 0.02, 1.0)
        self._shape = shapes
        self._names = names
        n_home = len(t["home_ids"])
        n_tf = len(t["kva"])
        self._to_home = np.zeros((len(t["load_names"]), n_home))
        self._to_home[np.arange(len(t["load_names"])), t["load_home"]] = 1.0
        self._to_tf = np.zeros((len(t["load_names"]), n_tf))
        self._to_tf[np.arange(len(t["load_names"])), t["home_tf"][t["load_home"]]] = 1.0

    def _v(self, k0, n):
        if k0 < 0 or k0 + n > self.steps:
            raise IndexError(f"steps {k0}..{k0 + n} outside 0..{self.steps}")
        return self._shape[self._pidx, k0:k0 + n]            # [2021, n]

    def at_step(self, k):
        v = self._v(int(k), 1)[:, 0]
        return self.table["nameplate_kw"] * v, self.table["nameplate_kvar"] * v

    def at_minute(self, day, minute):
        """15 -> 1 min linear (DERIVED). `minute` counts from local midnight of `day`; it may exceed 1440."""
        d = (datetime.strptime(day, "%Y-%m-%d") - datetime.strptime(self.t0[:10], "%Y-%m-%d")).days
        s = (d * 1440 + minute) / self.step_minutes
        k0 = int(math.floor(s))
        f = s - k0
        k1 = min(k0 + 1, self.steps - 1)
        a_kw, a_kvar = self.at_step(k0)
        b_kw, b_kvar = self.at_step(k1)
        return a_kw + (b_kw - a_kw) * f, a_kvar + (b_kvar - a_kvar) * f

    def tf_pq(self, step0, n):
        v = self._v(step0, n).T                               # [n, 2021]
        return (v * self.table["nameplate_kw"]) @ self._to_tf, (v * self.table["nameplate_kvar"]) @ self._to_tf

    def home_kw(self, step0, n):
        return (self._v(step0, n).T * self.table["nameplate_kw"]) @ self._to_home

    def profile_of(self, load_index):
        return self.table["profiles"][int(load_index)]


# ---------------------------------------------------------------------------------------------
def _hhmm(dt):
    return dt.strftime("%H:%M")


def _i10(x):
    return np.rint(np.asarray(x, dtype=float) * 10).astype(int).tolist()


def _sim(v, **kw):
    return labelled(v, "SIM", FIX, **kw)


def _p1(loads, t):
    day = "2026-08-23"
    start = datetime.strptime(f"{day}T21:30", "%Y-%m-%dT%H:%M")
    n = 120
    onset, onset_p, _, _, _ = onset_d26(day)
    usable = (0.90 - RESERVE_FLOOR) * CORE_USABLE_KWH * CORE_RTE ** 0.5
    plan = discharge_plan(day, onset, usable, CORE_POWER_KW)
    kva = t["kva"]
    tfb = t["tf_of_batt"]
    nb = len(tfb)
    tf_index = {x: i for i, x in enumerate(t["tf_ids"])}
    focus = {k: tf_index[v] for k, v in FOCUS_TFS.items()}
    focus["240"] = tf_index[BRIDGE_TF]
    mins = [(start + timedelta(minutes=k)) for k in range(n)]
    bg_p = np.zeros((n, len(kva)))
    bg_q = np.zeros((n, len(kva)))
    home_tf = t["home_tf"]
    to_tf = np.zeros((len(t["home_ids"]), len(kva)))
    to_tf[np.arange(len(home_tf)), home_tf] = 1
    for k, m in enumerate(mins):
        kw, kvar = loads.at_minute(day, m.hour * 60 + m.minute)
        bg_p[k] = np.bincount(home_tf[t["load_home"]], weights=kw, minlength=len(kva))
        bg_q[k] = np.bincount(home_tf[t["load_home"]], weights=kvar, minlength=len(kva))
    onset_k = int((datetime.strptime(onset, "%Y-%m-%dT%H:%M") - start).total_seconds() // 60)
    rng = np.random.default_rng(17263)
    soc0 = np.clip(0.22 + rng.uniform(0, 0.06, nb), 0.2, 1.0)
    eta = CORE_RTE ** 0.5
    out = {}
    for branch in ("none", "naive", "aware", "aware_faults"):
        soc = soc0.copy()
        bat = np.zeros((n, nb))
        socs = np.zeros((n, nb))
        state = []
        ticker = []
        silent = int(np.argmax(tfb == focus["A"]))
        for k in range(n):
            st = ["I"] * nb
            p = np.zeros(nb)
            if branch != "none" and k >= onset_k:
                room_kwh = (1 - soc) * CORE_USABLE_KWH / eta
                want = np.minimum(CORE_POWER_KW, room_kwh * 60)
                if branch == "naive":
                    p = want
                else:
                    H, _, _ = transformer_caps(bg_p[k], bg_q[k], kva)
                    left = max(1.0, n - k)
                    target = min(want.sum(), room_kwh.sum() * 60 / left * CHARGE_URGENCY * 6)
                    used = np.zeros(len(kva))
                    total = 0.0
                    order = sorted(range(nb), key=lambda j: (math.floor(soc[j] / SOC_BUCKET), j))
                    for j in order:
                        if branch == "aware_faults" and j == silent and onset_k + 15 <= k < onset_k + 25:
                            continue
                        g = min(want[j], H[tfb[j]] - used[tfb[j]], target - total)
                        g = g if g >= MIN_GRANT_KW else 0.0
                        p[j] = g
                        used[tfb[j]] += g
                        total += g
                if branch == "aware_faults" and onset_k + 15 <= k < onset_k + 25:
                    st[silent] = "S" if k < onset_k + 18 else "X"
            for j in range(nb):
                if st[j] == "I":
                    st[j] = "C" if p[j] > 0.5 else ("D" if p[j] < -0.5 else "I")
            soc = np.minimum(1.0, soc + p * eta / 60 / CORE_USABLE_KWH)
            bat[k] = p
            socs[k] = soc
            state.append("".join(st))
            if branch.startswith("aware") and k > 0:
                for key in "ABCD":
                    js = np.nonzero(tfb == focus[key])[0]
                    for j in js:
                        if bat[k, j] > 0.5 and bat[k - 1, j] <= 0.5:
                            label = f"Home {int(t['fleet'][j]) + 1:04d}"
                            ticker.append([k, f"{_hhmm(mins[k])} {key} room -> {label} +{bat[k, j]:.1f} kW (fixture)"])
        bat_tf = bat @ np.eye(len(kva))[tfb]
        pct = np.hypot(bg_p + bat_tf, bg_q) / kva * 100
        codes = tier_codes(pct, 1.0)
        prot = protection_events(pct, 60)
        home_state = []
        for k, tf in prot:
            for h in np.nonzero(home_tf == tf)[0]:
                home_state.append([k, int(h), "battery" if int(h) in set(t["fleet"].tolist()) else "dark"])
        counts = [[int((codes[k] == c).sum()) for c in (1, 2, 3, 4, 5)] for k in range(n)]
        mx = np.unravel_index(int(np.argmax(pct)), pct.shape)
        batt_on = np.abs(bat_tf) > 0.5
        caused_n = [e for e in normal_events(pct, 1.0) if batt_on[e[1]:e[2], e[0]].any()]
        summary = {
            "normalEvents": _sim(len(normal_events(pct, 1.0))),
            "emergencyTfs": _sim(int((pct > 150).any(axis=0).sum())),
            "batteryCausedNormal": _sim(len(caused_n)),
            "batteryCausedEmergency": _sim(int(((pct > 150) & batt_on).any(axis=0).sum())),
            "batteryCausedAmberMin": _sim(int(((pct > TIER_AMBER_PCT) & batt_on).sum())),
            "homeOnlyOver100": _sim(int(((pct > TIER_AMBER_PCT) & ~batt_on).any(axis=0).sum())),
            "protectionOperated": _sim(len(prot)),
            "homesDark": _sim(sum(1 for x in home_state if x[2] == "dark")),
            "homesOnBattery": _sim(sum(1 for x in home_state if x[2] == "battery")),
            "maxLoading": _sim(round(float(pct.max()), 1), tf=int(mx[1]), t=_hhmm(mins[mx[0]])),
            "reserveBreaches": _sim(int((socs < RESERVE_FLOOR - 1e-9).sum())),
            "chargedPctBy0400": _sim(round(float((socs[-1] >= 0.95).mean() * 100), 1)),
            "energyValueUSD": labelled(round(float(-(bat.sum(axis=1) * np.array([price_at(m) for m in mins])).sum() / 60 / 1000), 2), "DERIVED", FIX),
            "vMinHome": _sim(0.9712, volts=116.5, home=int(t["fleet"][0]), t=_hhmm(mins[onset_k])),
            "homesBelow095": _sim(0),
            "feederHead": _sim(round(80 + float(bat.sum(axis=1).max()) / 80, 1), amps=300.0, t=_hhmm(mins[onset_k]),
                               ratingA=labelled(370, "DERIVED", "site/ems/flow-spec.md (SMART-DS NormAmps)")),
        }
        focus_doc = {}
        for key, tf in focus.items():
            focus_doc[key] = {"tf": tf, "homeKW": _i10(bg_p[:, tf]), "batKW": _i10(bat_tf[:, tf])}
        doc = envelope(f"p1.{branch}", "sim.fixtures", inputs=inputs_sha(loads_override=LOADS_TAG),
                       constants=export("AWARE_MARGIN", "CORE_POWER_KW", "CORE_USABLE_KWH", "CORE_RTE", "RESERVE_FLOOR"),
                       sources={"load": {"label": "SIM", "text": "FIXTURE: synthetic diurnal shapes (sim.fixtures.FixtureLoads), not SMART-DS"},
                                "referee": {"label": "SIM", "text": "FIXTURE: lossless surrogate, not OpenDSS"}},
                       series={"loading": {"label": "SIM", "unit": "pct x10", "by": "fixture surrogate"},
                               "batKW": {"label": "SIM", "unit": "kW x10"}, "soc": {"label": "SIM", "unit": "per mille"}},
                       fixture=True)
        doc.update({"branch": branch, "steps": n, "loading": np.rint(pct * 10).astype(int).tolist(),
                    "focus": focus_doc, "tier": tier_strings(codes), "batKW": _i10(bat),
                    "soc": np.rint(socs * 1000).astype(int).tolist(), "state": state, "homeState": home_state,
                    "targetKW": _i10(bat.sum(axis=1)), "deliveredKW": _i10(bat.sum(axis=1)),
                    "vMin": [9712] * n, "counts": counts, "ticker": ticker})
        out[branch] = (doc, summary)
    price = [price_at(m) for m in mins]
    part = [p for p in plan if p[1] < 15]
    meta = envelope("p1.meta", "sim.fixtures", inputs=inputs_sha(loads_override=LOADS_TAG),
                    constants=export("TIER_AMBER_PCT", "TIER_NORMAL_PCT", "TIER_NORMAL_MIN", "TIER_EMERGENCY_PCT",
                                     "FUSE_PCT", "FUSE_MINUTES", "FUSE_INSTANT_PCT", "FUSE_INSTANT_SECONDS",
                                     "CONTROLLER_VIEW", "AWARE_MARGIN", "SOC0"),
                    sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                             "load": {"label": "SIM", "text": "FIXTURE: synthetic diurnal shapes, not SMART-DS"},
                             "referee": {"label": "SIM", "text": "FIXTURE: lossless surrogate, not OpenDSS"}},
                    series={"price": {"label": "REAL", "unit": "$/MWh"}}, fixture=True)
    meta.update({
        "day": day, "start": _hhmm(start), "stepSeconds": 60, "steps": n,
        "tiers": {"amber": 100, "normal": 110, "normalMinutes": 30, "emergency": 150, "label": "REAL"},
        "protection": {"fusePct": 200, "fuseMinutes": 10, "instantPct": 300, "instantSeconds": 60, "label": "ASSUMPTION",
                       "cite": "docs/headroom/design/round1/world-sim.md 'Protection'"},
        "price": price,
        "plan": {"discharge": [[a[11:16], m] for a, m in plan], "partial": [[a[11:16], m] for a, m in part],
                 "onset": onset[11:16], "onsetPrice": labelled(onset_p, "REAL", "ERCOT RTM SPP LZ_NORTH"), "rule": "D-26",
                 "label": "DERIVED"},
        "branches": list(out),
        "events": {"aware_faults": [{"step": onset_k + 15, "t": _hhmm(mins[onset_k + 15]), "kind": "comms_lost",
                                     "home": int(t["fleet"][int(np.argmax(tfb == focus["A"]))]), "cmdKW": 0}]},
        "markers": [{"t": onset[11:16], "text": f"D-26 onset ${onset_p:.2f}", "label": "DERIVED"}],
        "summary": {b: s for b, (_, s) in out.items()},
        "controllerView": {"text": CONTROLLER_VIEW, "label": "ASSUMPTION", "cite": "needs a utility meter-to-transformer map; §12 Q4"},
        "relief": {"tf": focus["A"], "t": "16:45", "none": _sim(0.0), "aware": _sim(0.0), "minutesOver100": _sim(0),
                   "reliefKW": _sim(0.0), "reliefKWh": _sim(0.0),
                   "driver": {"home": 211, "label": "Home 0212", "profile": "res_kw_38274_pu", "kwAtPeak": _sim(0.0),
                              "sharedWith": ["Home 0409"]}},
        "money": {"energyValueUSD": {b: s["energyValueUSD"] for b, (_, s) in out.items()},
                  "costOfAwareness": labelled(0.0, "DERIVED", FIX)},
        "unrelieved": [{"tf": focus["240"], "reason": "home load only, no battery (fixture)",
                        "driver": {"home": 408, "label": "Home 0409", "profile": "res_kw_38274_pu", "kwAtPeak": _sim(0.0), "sharedWith": ["Home 0212"]}}],
        "engine": {"solves": _sim(0), "msPerSolve": _sim(0.0)},
    })
    return meta, {b: d for b, (d, _) in out.items()}


def _p2(loads, t):
    steps = 2976
    P, Q = loads.tf_pq(0, loads.steps)
    kva = t["kva"]
    pct = np.hypot(P, Q) / kva * 100
    month = pct[:steps]
    t0 = datetime(2026, 8, 1)
    price = [price_at(t0 + timedelta(minutes=15 * k)) for k in range(steps)]
    h100 = (month > 100).sum(axis=0) * 0.25
    peak = month.max(axis=0)
    peak_t = month.argmax(axis=0)
    fleet_set = set(t["fleet"].tolist())
    home_tf = t["home_tf"]
    cands = [h for h in range(len(home_tf)) if h not in fleet_set and t["nameplate_kw"][t["load_home"] == h].sum() > 0]
    tf_index = {x: i for i, x in enumerate(t["tf_ids"])}
    combos = [f"{p}-{c}-{r}-g{g}" for p in ("naive", "aware") for c in ("core", "legacy") for r in ("d26", "cheapest") for g in (0, 20)]
    cliffs = find_cliffs()
    files = {}
    rankings = {}
    for combo in combos:
        pol, cls, rule, g = combo.split("-")
        kw = CORE_POWER_KW if cls == "core" else 11.4
        grow = 1.2 if g == "g20" else 1.0
        rows = []
        seen_tf = set()
        for h in cands:
            tf = int(home_tf[h])
            if tf in seen_tf:
                continue
            seen_tf.add(tf)
            base_peak = float(peak[tf]) * grow
            with_peak = base_peak + (kw / kva[tf] * 100 if pol == "naive" else -min(kw, max(0.0, (base_peak - 95) * kva[tf] / 100)) / kva[tf] * 100)
            avoided = float(h100[tf]) if pol == "aware" else 0.0
            added = 0.0 if pol == "aware" or with_peak <= 110 else 2.0
            rows.append((added > 0, -avoided, with_peak, h, tf, avoided, added, base_peak))
        rows.sort()
        ranking = []
        for r, (_, _, with_peak, h, tf, avoided, added, base_peak) in enumerate(rows[:50], 1):
            also = [int(x) for x in np.nonzero(home_tf == tf)[0] if int(x) != h and int(x) in cands]
            ranking.append({"rank": r, "home": int(h), "tf": tf, "reason": f"fixture: peak with battery {with_peak:.0f}%",
                            "alsoOnTf": also, "tieBroken": False,
                            "noNewViolation": _sim(added == 0), "peakWithPct": _sim(round(with_peak, 1)),
                            "stressAvoidedH": _sim(round(avoided, 2)), "stressAddedH": _sim(added),
                            "reliefKWh": _sim(0.0), "revenueUSD": labelled(0.0, "DERIVED", FIX), "curtailKWh": _sim(0.0),
                            "protectionWith": _sim(False), "homesDarkWith": [],
                            "before": {"peakPct": _sim(round(base_peak, 1)), "h100": _sim(round(float(h100[tf]), 2))},
                            "after": {"peakPct": _sim(round(with_peak, 1)), "h100": _sim(round(max(0.0, float(h100[tf]) - avoided), 2))},
                            "opendss": None, "screening": True})
        rankings[combo] = [x["home"] for x in ranking]
        strips = {}
        for tf in [x["tf"] for x in ranking[:10]] + [tf_index[FOCUS_TFS["A"]], tf_index[BRIDGE_TF]]:
            hourly = month[: 744 * 4, tf].reshape(744, 4).max(axis=1) * grow
            d = int(peak_t[tf]) // 96
            day = month[d * 96:(d + 1) * 96, tf] * grow
            shift = kw / kva[tf] * 100 if pol == "naive" else -5.0
            strips[str(tf)] = {"without": _i10(hourly), "with": _i10(np.maximum(0, hourly + shift)),
                               "peakDay": {"day": (t0 + timedelta(days=d)).strftime("%Y-%m-%d"),
                                           "without": _i10(day), "with": _i10(np.maximum(0, day + shift))}}
        doc = envelope(f"p2.{combo}", "sim.fixtures", inputs=inputs_sha(loads_override=LOADS_TAG),
                       constants=export("AWARE_MARGIN", "CORE_POWER_KW", "LEGACY_POWER_KW", "GROWTH", "CURTAIL_CAP"),
                       sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                                "load": {"label": "SIM", "text": "FIXTURE: synthetic diurnal shapes, not SMART-DS"}},
                       series={"baseline": {"label": "SIM", "unit": "pct x10 / hours", "by": "fixture surrogate"},
                               "strips": {"label": "SIM", "unit": "pct x10, hourly max"}}, fixture=True)
        doc.update({"combo": combo,
                    "baseline": {"peak": _i10(peak * grow), "peakT": peak_t.tolist(), "h100": np.round(h100, 2).tolist(),
                                 "normalEvents": [0] * len(kva), "emergencyN": [0] * len(kva), "protection": [0] * len(kva)},
                    "ranking": ranking,
                    "greedy": [{"k": i + 1, "home": x["home"], "tf": x["tf"],
                                "feeder": {"normalTfs": _sim(0), "emergencyTfs": _sim(0), "h110": _sim(0.0)}} for i, x in enumerate(ranking[:10])],
                    "strips": strips})
        files[combo] = doc
    top_n, top_a = rankings["naive-core-d26-g0"][:10], rankings["aware-core-d26-g0"][:10]
    tf_peak_hour = np.bincount((peak_t % 96) // 4, minlength=24).tolist()
    daily_max_hour = [0] * 24
    for d in range(31):
        k = int(np.argmax(price[d * 96:(d + 1) * 96]))
        daily_max_hour[k // 4] += 1
    index = envelope("p2.index", "sim.fixtures", inputs=inputs_sha(loads_override=LOADS_TAG),
                     constants=export("AWARE_MARGIN", "CURTAIL_CAP", "GROWTH", "CLIFF_MIN_PRICE", "CLIFF_DROP_FRAC"),
                     sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                              "load": {"label": "SIM", "text": "FIXTURE: synthetic diurnal shapes, not SMART-DS"}},
                     series={"price": {"label": "REAL", "unit": "$/MWh"},
                             "fleetCounterfactual": {"label": "SIM", "unit": "hours / counts"},
                             "insight": {"label": "SIM", "unit": "count per hour (tfPeakHour SIM; priceMaxHour REAL)"}},
                     fixture=True)
    zeros = [0] * len(kva)
    index.update({
        "month": "2026-08", "stepMinutes": 15, "steps": steps,
        "controls": {"policy": ["naive", "aware"], "cls": ["core", "legacy"], "rule": ["d26", "cheapest"], "growth": [0, 20]},
        "combos": combos, "default": "aware-core-d26-g0", "price": price,
        "cliffs": {"count": labelled(len(cliffs), "DERIVED", "sim.prices.find_cliffs, 2026-01-01..2026-09-19"),
                   "evening": labelled(sum(c["evening"] for c in cliffs), "DERIVED", "later interval 20:00-23:59"),
                   "rule": "prev >= $60 and next <= 0.5 x prev, consecutive 15-min starts", "period": "2026-01-01..2026-09-19",
                   "events": cliffs},
        "fleetCounterfactual": {k: {"h100": np.round(h100, 2).tolist(), "normalEvents": zeros, "emergencyN": zeros}
                                for k in ("none", "naive", "aware")},
        "flip": {"top10Overlap": _sim(len(set(top_n) & set(top_a))), "spearman": _sim(0.0),
                 "untied": {"top10Overlap": _sim(0), "spearman": _sim(0.0), "n": _sim(0)},
                 "combos": ["naive-core-d26-g0", "aware-core-d26-g0"]},
        "ties": {"byId": labelled(0, "SIM", FIX), "of": 911},
        "drivers": {"top10DistinctProfiles": _sim(0), "profiles": []},
        "insight": {"tfPeakHour": tf_peak_hour, "priceMaxHour": daily_max_hour},
        "usefulCapacity": {"naive": _sim(0, stop="fixture"), "aware": _sim(0, stop="fixture"), "curve": {"naive": [], "aware": []}},
        "referee": {"runs": 0, "errorPts": {"max": _sim(0.0), "p99": _sim(0.0)}, "tierAgreementPct": _sim(0.0)},
        "bridge": [{"tf": tf_index[BRIDGE_TF], "id": BRIDGE_TF}],
        "engine": {"screenSecondsPerCombo": _sim(0.0)},
    })
    return index, files


def write_all():
    t = load_table()
    loads = FixtureLoads(table=t)
    meta, branches = _p1(loads, t)
    sizes = [write_json(OUT / "p1" / "meta.json", meta)]
    for b, doc in branches.items():
        sizes.append(write_json(OUT / "p1" / f"{b}.json", doc))
    index, combos = _p2(loads, t)
    sizes.append(write_json(OUT / "p2" / "index.json", index))
    for c, doc in combos.items():
        sizes.append(write_json(OUT / "p2" / f"{c}.json", doc))
    return len(sizes), sum(sizes)


if __name__ == "__main__":
    n, total = write_all()
    print(f"fixtures: {n} files, {total / 1048576:.2f} MB -> {OUT.relative_to(ROOT)}")
    sys.exit(0)
