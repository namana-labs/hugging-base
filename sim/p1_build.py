"""P1, where to charge: the time-stepped balancing simulation (lane L2; build prompt 5.4).

2026-08-23 16:00 -> 04:00 on the 24th, 720 steps of 60 s, OpenDSS solving every step of every branch:
  none          no batteries: what AC alone does
  naive         ERCOT's one number per zone split with no feeder check (ASSUMPTION: Base's real split is not public,
                §12 Q5): every battery discharges at full power in the market plan's minutes and charges at full power,
                all at once, from the D-26 onset until full
  aware         sim.orchestrator.Controller + allocate() (relief, E-capped discharge, charge in turn, dwell, cover)
  aware_faults  aware plus the three failures of 5.4.4 at Tc+15 (comms loss), Tc+35 (C runs hot), Tc+55 (stall)

    python -m sim.p1_build                 # the full build: writes ui/data/p1/{meta,none,naive,aware,aware_faults}.json
    python -m sim.p1_build --quick         # 60 steps, 22:00-23:00, to ~/hb-overnight/tmp/p1-quick (under 20 s, no lock)
    python -m sim.p1_build --out DIR       # write somewhere else (verify --rebuild uses this)
    python -m sim.p1_build --dwell N --out DIR   # MIN_DWELL_MIN override (the judge's check); the envelope exports N

Scenario levers (sprint story contract; sim.scenarios builds the variants): Scenario(..., soc0, reserve, growth) and a
fleet doc passed to Feeder(fleet=...) (size and class). Every lever defaults to the committed value, so the committed
build is byte-identical. A reserve below RESERVE_FLOOR (the 20% member reserve) is refused: it is a hard constraint.

Heavy (about 3,000 OpenDSS solves): run through scripts/build_all.sh p1 (takes the shared lock).
Prices REAL (ERCOT LZ_NORTH), loads SIM (SMART-DS 2018, same calendar date, 15 -> 1 min linear: DERIVED), battery
power factor 1.0 (ASSUMPTION), controller view = total transformer load with a 60 s lag (ASSUMPTION, §12 Q4).
"""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from .constants import (export, P1_DAY, P1_START, P1_STEPS, P1_STEP_SECONDS, P1_CHARGE_DEADLINE, SOC0,
                        RESERVE_FLOOR, CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE, FOCUS_TFS, BRIDGE_TF,
                        FAULT_COMMS_AFTER_MIN, FAULT_HOT_AFTER_MIN, FAULT_STALL_AFTER_MIN, EV_KW, HOT_MINUTES, STALL_MIN,
                        MIN_GRANT_KW, MIN_DWELL_MIN, TIER_AMBER_PCT, TIER_NORMAL_PCT, TIER_EMERGENCY_PCT, FUSE_PCT,
                        FUSE_MINUTES, FUSE_INSTANT_PCT, FUSE_INSTANT_SECONDS, CONTROLLER_VIEW, HEAD_RATING_A,
                        HEAD_RATING_KVA, TAG)
from .contracts import envelope, inputs_sha, labelled, write_json
from .devices import Battery, Device, CLASSES, discharge_limit
from .feeder import Feeder, ROOT
from .money import (energy_value_usd, money_block, ercot_demand, scale_ladder, ERCOT_DEMAND_REL, split_block, cash_cents,
                    head_kva_per_phase, SPLIT_CITE)
from .orchestrator import Controller, allocate, charge_target
from .devices import Command
from .constants import COMMAND_TTL_S, COMMS_STALE_S
from .prices import price_at, onset_d26, discharge_plan
from .tiers import tier_codes, tier_strings, normal_events, protection_events
from .history import story_for             # the day chip's story line (tag + why), formatted from the meta

OUT = ROOT / "ui" / "data" / "p1"
QUICK_OUT = Path.home() / "hb-overnight" / "tmp" / "p1-quick"
TIMING = ROOT / "data" / "cache" / "p1_build_timing.json"
BRANCHES = ("none", "naive", "aware", "aware_faults")
# lane L0's round-2 constants, exported by the meta once they exist in sim.constants (RZ adopt-now #2; audit L2)
LEAD_CONSTS = tuple(n for n in ("BASE_HOUSTON_CHARGE_BLOCK_MW", "HEAD_RATING_KVA_PER_PHASE") if n in TAG)
FMT = "%Y-%m-%dT%H:%M"
DT_H = P1_STEP_SECONDS / 3600.0
LOADS_TEXT = "NREL SMART-DS 2018 AUS P1U, same calendar date; 15->1 min linear (DERIVED)"
NAIVE_TEXT = ("ERCOT dispatches one number per zone and does not check feeders (REAL). The naive branch splits that "
              "number with no feeder check, all at once at the onset (ASSUMPTION: Base's real split is not public; §12 Q5).")


def hhmm(dt):
    return dt.strftime("%H:%M")


def i10(x):
    return np.rint(np.asarray(x, dtype=float) * 10).astype(int).tolist()


def constants_block(names, dwell=MIN_DWELL_MIN, overrides=None):
    """The envelope's `constants`: the values that ran. A --dwell override replaces MIN_DWELL_MIN's value and cite, so
    a judge-check build never exports the default it did not use (build prompt 5.3). `overrides` ({NAME: {value, label,
    cite}}, a scenario lever's values: Scenario.overrides()) replaces or adds entries the same way."""
    c = export(*names)
    if "MIN_DWELL_MIN" in c and dwell != MIN_DWELL_MIN:
        c["MIN_DWELL_MIN"] = {"value": dwell, "label": "ASSUMPTION",
                              "cite": f"override: judge check (--dwell {dwell}); the committed build uses {MIN_DWELL_MIN} "
                                      f"({TAG['MIN_DWELL_MIN']['cite']})"}
    for k, v in (overrides or {}).items():
        c[k] = v
    return c


class Window:
    """The P1 clock: step k <-> local minute start + k (minutes after P1_DAY midnight; may pass 1440)."""

    def __init__(self, day=P1_DAY, start=P1_START, steps=P1_STEPS):
        self.day = day
        self.t0 = datetime.strptime(f"{day}T{start}", FMT)
        self.steps = int(steps)
        self.start_min = self.t0.hour * 60 + self.t0.minute
        dl = datetime.strptime(f"{day}T{P1_CHARGE_DEADLINE}", FMT)
        if dl <= self.t0:
            dl += timedelta(days=1)
        self.deadline = dl
        self.deadline_step = int((dl - self.t0).total_seconds() // 60)

    def time(self, k):
        return self.t0 + timedelta(minutes=int(k))

    def ts(self, k):
        return self.time(k).strftime(FMT)

    def step_of(self, dt):
        return int((dt - self.t0).total_seconds() // 60)


def market(win, soc0=SOC0, reserve=RESERVE_FLOOR, emax=CORE_USABLE_KWH, pmax=CORE_POWER_KW, rte=CORE_RTE):
    """(modes[n], plan, onset) from sim.prices: the market plan is the same for every branch with batteries (DERIVED).
    One battery's usable energy above the reserve sizes the plan: soc0, reserve and the class (emax, pmax, rte) are
    the scenario's (defaults: the committed Core at SOC0 over RESERVE_FLOOR)."""
    onset, onset_p, peak_ts, threshold, rule_mode = onset_d26(win.day)
    usable = (soc0 - reserve) * emax * math.sqrt(rte)
    plan = discharge_plan(win.day, onset, usable, pmax)
    modes = ["idle"] * win.steps
    full_plan_modes = {}
    for ts, minutes in plan:
        t = datetime.strptime(ts, FMT)
        for j in range(minutes):
            full_plan_modes[t + timedelta(minutes=j)] = "discharge"
    onset_dt = datetime.strptime(onset, FMT)
    for k in range(win.steps):
        t = win.time(k)
        if t in full_plan_modes:
            modes[k] = "discharge"
        elif onset_dt <= t < win.deadline:
            modes[k] = "charge"
    return modes, plan, (onset, onset_p, peak_ts, threshold, rule_mode), full_plan_modes


def check_levers(soc0, reserve, growth):
    """Refuse a lever outside its physical range. The 20% member reserve is a hard constraint (CLAUDE.md): never below
    RESERVE_FLOOR, in any scenario."""
    if reserve < RESERVE_FLOOR - 1e-12:
        raise ValueError(f"reserve {reserve:.0%} is below the {RESERVE_FLOOR:.0%} member reserve (a hard constraint)")
    if not reserve < 1.0:
        raise ValueError(f"reserve {reserve} must be below 1")
    if not reserve <= soc0 <= 1.0:
        raise ValueError(f"start charge {soc0} must lie between the reserve {reserve} and 1")
    if not growth > -1.0:
        raise ValueError(f"home-load growth {growth} must be above -100%")


class Scenario:
    """Everything shared by the branches: feeder, loads, fleet, prices, the plan.

    Levers (defaults = the committed build): soc0 (state of charge at 16:00), reserve (the member reserve, never below
    RESERVE_FLOOR), growth (uniform multiplier 1 + growth on every home's kW and kvar, the warm-up minute included:
    sim.siting's growth_factor definition). The fleet (size, class, placement) is the feeder's: Feeder(fleet=doc)."""

    def __init__(self, win, loads=None, feeder=None, soc0=SOC0, reserve=RESERVE_FLOOR, growth=0.0):
        from .loads import Loads
        check_levers(soc0, reserve, growth)
        self.soc0 = soc0
        self.reserve = reserve
        self.growth = growth
        self.const_extra = {}            # more envelope constants for a scenario (sim.scenarios: the fleet levers)
        self.win = win
        self.loads = loads if loads is not None else Loads()
        self.feeder = feeder if feeder is not None else Feeder()
        f = self.feeder
        self.kva = f.kva
        self.fleet = f.fleet                         # home indices, fleet order
        self.tf_of_batt = f.tf_of_batt
        self.m = len(self.fleet)
        self.ids = [f.homes[j]["id"] for j in self.fleet]
        self.cls = [b.get("cls", "core") for b in f.fleet_doc["batteries"]]
        self.pmax = np.array([CLASSES[c]["pmax"] for c in self.cls])
        self.emax = np.array([CLASSES[c]["emax"] for c in self.cls])
        self.rte = np.array([CLASSES[c]["rte"] for c in self.cls])
        self.load_tf = f.load_tf
        self.load_home = f.load_home
        self.home_tf = np.array([h["tf"] for h in f.homes], dtype=np.int64)
        self.labels = [f"Home {i + 1:04d}" for i in range(len(f.homes))]
        self.focus = {k: f.tf_index[v] for k, v in FOCUS_TFS.items()}
        self.focus["240"] = f.tf_index[BRIDGE_TF]
        self.focus_of_tf = {v: k for k, v in self.focus.items()}
        # the market plan is sized on one battery of the fleet's class (the Core by default; the Legacy lever uses
        # the Legacy's power and energy). A mixed fleet has no single plan battery: refused.
        kinds = sorted(set(self.cls))
        if len(kinds) != 1:
            raise ValueError(f"the market plan needs one battery class, the fleet has {kinds}")
        spec = CLASSES[kinds[0]]
        self.modes, self.plan, self.onset, self.plan_minutes = market(win, soc0, reserve, spec["emax"], spec["pmax"],
                                                                      spec["rte"])
        self.price = np.array([price_at(win.time(k)) for k in range(win.steps)])
        # SoC at the window start: SOC0 at 16:00, or (quick windows) SOC0 run through the plan minutes before start
        soc = np.full(self.m, soc0)
        pre = [t for t in sorted(self.plan_minutes) if t < win.t0 and t >= datetime.strptime(f"{win.day}T16:00", FMT)]
        for _ in pre:
            for i in range(self.m):
                b = Battery(soc=float(soc[i]), cls=self.cls[i], reserve=reserve)
                b.advance(-self.pmax[i], DT_H)
                soc[i] = b.soc
        self.soc_start = soc
        self._loads_cache = [None] * win.steps

    def loads_at(self, minute):
        """Home kW and kvar (Loads.dss order) at local minute `minute` of the day, with the growth lever applied."""
        kw, kvar = self.loads.at_minute(self.win.day, minute)
        if self.growth:
            kw, kvar = kw * (1 + self.growth), kvar * (1 + self.growth)
        return kw, kvar

    def home_loads(self, k):
        if self._loads_cache[k] is None:
            self._loads_cache[k] = self.loads_at(self.win.start_min + k)
        kw, kvar = self._loads_cache[k]
        return kw.copy(), kvar.copy()

    def controller(self, dwell_min):
        """The aware controller: sim.orchestrator.Controller, or (reserve lever above the floor) ReserveController."""
        args = (self.tf_of_batt, self.pmax, self.emax, self.rte, self.ids)
        if self.reserve == RESERVE_FLOOR:
            return Controller(*args, dwell_min=dwell_min)
        return ReserveController(*args, dwell_min=dwell_min, reserve=self.reserve)

    def overrides(self):
        """Envelope constants for the levers that differ from the committed build ({} by default)."""
        o = {}
        if self.soc0 != SOC0:
            o["SOC0"] = {"value": self.soc0, "label": "ASSUMPTION",
                         "cite": f"scenario lever (start charge); the committed build uses {SOC0} ({TAG['SOC0']['cite']})"}
        if self.reserve != RESERVE_FLOOR:
            o["RESERVE_FLOOR"] = {"value": self.reserve, "label": "ASSUMPTION",
                                  "cite": f"scenario lever (member reserve), never below the {RESERVE_FLOOR:.0%} floor "
                                          f"({TAG['RESERVE_FLOOR']['cite']})"}
        if self.growth:
            o["LOAD_GROWTH"] = {"value": self.growth, "label": "ASSUMPTION",
                                "cite": "scenario lever: every home's kW and kvar x (1 + growth), the warm-up minute "
                                        "included (sim.siting growth_factor's definition)"}
        o.update(self.const_extra)
        return o


class ReserveController(Controller):
    """sim.orchestrator.Controller with a member reserve above RESERVE_FLOOR (the reserve lever). Controller.tick()
    calls allocate() without `reserve`, so this is its tick with `reserve=self.reserve` passed through; the protocol
    is unchanged. Used only when the reserve differs from the floor (the committed build uses Controller itself).
    REQUEST (lead): give Controller a `reserve` argument and delete this class."""

    def __init__(self, *args, reserve=RESERVE_FLOOR, **kw):
        super().__init__(*args, **kw)
        self.reserve = reserve

    def tick(self, k, t_s, heard, soc_now, bg_kw, bg_kvar, kva, mode, target_kw, blocked=None):
        from .orchestrator import BIG
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
        st.blocked = st.blocked | (~heard & exp)
        st.release = {}
        for i in range(self.m):
            if exp[i] and st.grant[i] != 0.0:
                if prev_held[i] and st.grant[i] > 0:
                    t = int(self.tf[i])
                    st.release[t] = st.release.get(t, 0.0) + float(st.grant[i])
                st.grant[i] = 0.0
                st.grant_step[i] = -BIG
        kw, caps, dec = allocate(bg_kw, bg_kvar, kva, self.tf, self.soc_view, self.pmax, self.emax, target_kw, mode,
                                 state=st, alpha=self.alpha, cover=self.cover, rte=self.rte, ids=self.ids,
                                 reserve=self.reserve)
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


def run_branch(sc, branch, faults=None):
    """Run one branch through OpenDSS. Returns a dict of numpy arrays and event lists."""
    win, f = sc.win, sc.feeder
    n, m, T = win.steps, sc.m, len(sc.kva)
    f.restore_all()
    bat = [Battery(soc=float(sc.soc_start[i]), cls=sc.cls[i], reserve=sc.reserve) for i in range(m)]
    devs = [Device(b) for b in bat]
    ctl = None
    if branch.startswith("aware"):
        ctl = sc.controller(faults.get("dwell", MIN_DWELL_MIN) if faults else MIN_DWELL_MIN)
    faults = faults or {}
    pct = np.zeros((n, T))
    P = np.zeros((n, T))
    head = np.zeros(n)
    vmin_home = np.zeros((n, len(sc.home_tf)))
    batkw = np.zeros((n, m))
    soc = np.zeros((n, m))
    target = np.zeros(n)
    home_tf_kw = np.zeros((n, T))
    head_kw = np.zeros(n)          # sprint readouts (extras): feeder-head P/Q, capacitor kvar, served home load
    head_kvar = np.zeros(n)
    cap_kvar = np.zeros(n)
    load_kw = np.zeros(n)
    states = []
    home_state = []
    ticker = []
    events = []
    isolated_at = {}
    grants = np.zeros((n, m))
    # warm-up: the measurement the controller reads at step 0 (the minute before the window, batteries idle)
    kw0, kvar0 = sc.loads_at(win.start_min - 1)
    f.set_loads(kw0, kvar0)
    f.set_batteries(np.zeros(m))
    r0 = f.solve()
    P_prev, Q_prev = r0["P"].copy(), r0["Q"].copy()
    applied_prev = np.zeros(m)
    over200 = np.zeros(T, dtype=int)
    need_fuse = max(1, math.ceil(FUSE_MINUTES * 60 / P1_STEP_SECONDS))
    need_inst = max(1, math.ceil(FUSE_INSTANT_SECONDS / P1_STEP_SECONDS))
    over300 = np.zeros(T, dtype=int)
    # Faults (5.4.4). The defaults are aware_faults' three events; sim.chaos (P3, 5.7) passes the optional keys:
    #   pick_silent(sc, cmds, k) -> [batt]  who goes silent at the first controller tick at or after `comms`
    #                                       (default: 5.4.4's rule, one battery)
    #   hot_tf, hot_minutes                 which transformer runs hot (default C) and for how long (HOT_MINUTES)
    #   stall_min                           how long the controller stalls (default STALL_MIN)
    silent = None
    silent_from = None
    comms_at = faults.get("comms")
    picker = faults.get("pick_silent")
    hot_at = faults.get("hot")
    hot_minutes = int(faults.get("hot_minutes", HOT_MINUTES))
    stall_at = faults.get("stall")
    stall_min = int(faults.get("stall_min", STALL_MIN))
    hot_home = None
    if hot_at is not None:
        c_tf = sc.focus["C"] if faults.get("hot_tf") is None else int(faults["hot_tf"])
        who = "C" if faults.get("hot_tf") is None else sc.focus_of_tf.get(c_tf, f"tf {c_tf}")
        hot_home = int(min(sc.feeder.transformers[c_tf]["homes"]))
        hot_loads = np.flatnonzero(sc.load_home == hot_home)
        events.append({"step": hot_at, "t": hhmm(win.time(hot_at)), "kind": "hot", "tf": c_tf, "home": hot_home,
                       "deltaKW": EV_KW, "minutes": hot_minutes,
                       "text": f"{who} runs hot: {sc.labels[hot_home]} plugs in a Level 2 EV, +{EV_KW} kW for {hot_minutes} min (ASSUMPTION)"})
    stall_steps = set(range(stall_at, stall_at + stall_min)) if stall_at is not None else set()
    if stall_at is not None:
        ttl = TAG['COMMAND_TTL_S']['value']
        events.append({"step": stall_at, "t": hhmm(win.time(stall_at)), "kind": "stall", "minutes": stall_min,
                       "resumeStep": stall_at + stall_min,
                       "text": f"our controller stalls for {stall_min} min "
                               + (f"(longer than the {ttl} s command TTL)" if stall_min * 60 > ttl
                                  else f"(within the {ttl} s command TTL: live commands run on)")})
    last_cmd_kw = np.zeros(m)
    if branch == "naive":
        prev_mode = None
        for k in range(n):
            md = sc.modes[k]
            if md != prev_mode and md != "idle":
                what = (f"all {m} batteries discharge at full power (market plan; no feeder check, ASSUMPTION)" if md == "discharge"
                        else f"D-26 onset ${sc.price[k]:.2f}: all {m} batteries charge at full power at once (no feeder check, ASSUMPTION)")
                ticker.append([k, f"{hhmm(win.time(k))} {what}"])
            prev_mode = md
    stats = {"issued": 0, "delivered": 0, "rejected": 0, "actedAfterExpiry": 0}
    prev_state = ["I"] * m
    for k in range(n):
        t_s = k * P1_STEP_SECONDS
        tnow = win.time(k)
        kw, kvar = sc.home_loads(k)
        if hot_at is not None and hot_at <= k < hot_at + hot_minutes:
            kw[hot_loads] += EV_KW / len(hot_loads)
        mode = sc.modes[k]
        blocked = np.array([sc.tf_of_batt[i] in f.isolated for i in range(m)])
        cmd_kw = np.zeros(m)
        st_chars = ["I"] * m
        if branch == "none":
            pass
        elif branch == "naive":
            for i in range(m):
                if blocked[i]:
                    continue
                cmd_kw[i] = sc.pmax[i] if mode == "charge" else (-sc.pmax[i] if mode == "discharge" else 0.0)
            target[k] = float(sum(bat[i].limit(cmd_kw[i], DT_H) for i in range(m)))
        else:
            heard = ~blocked.copy()
            if silent is not None and k >= silent_from:
                heard[silent] = False
            stalled = k in stall_steps
            if not stalled:
                # the controller's view: last minute's measured transformer load minus its batteries' last reports
                rep = np.where(heard, applied_prev, 0.0)
                for i in np.flatnonzero(~heard):
                    c = ctl.last_cmd[i]
                    if c is not None and (t_s - P1_STEP_SECONDS) < c.expires_s:
                        rep[i] = c.kw
                bg_kw = P_prev - np.bincount(sc.tf_of_batt, weights=rep, minlength=T)
                bg_kvar = Q_prev
                socs = np.array([b.soc for b in bat])
                known = np.where(heard, socs, ctl.soc_view)
                if mode == "charge":
                    live = ~(ctl.stale | blocked) & (heard | ~np.array([ctl.expired(i, t_s) for i in range(m)]))
                    tgt = charge_target(np.where(live, known, 1.0), sc.emax, sc.rte, win.deadline_step - k)
                elif mode == "discharge":
                    tgt = -float(sum(discharge_limit(socs[i], sc.emax[i], sc.pmax[i], sc.rte[i], DT_H, sc.reserve)
                                     for i in range(m) if heard[i]))
                else:
                    tgt = 0.0
                kw_alloc, caps, dec, cmds = ctl.tick(k, t_s, heard, socs, bg_kw, bg_kvar, sc.kva, mode, tgt,
                                                     blocked=blocked)
                target[k] = tgt
                grants[k] = kw_alloc
                for i, c in cmds.items():
                    stats["issued"] += 1
                    if heard[i]:
                        stats["delivered"] += 1
                        if not devs[i].receive(c):
                            stats["rejected"] += 1
                        last_cmd_kw[i] = c.kw
                _ticker(sc, win, k, dec, caps, grants, ticker)
                if comms_at is not None and k >= comms_at and silent is None and picker is None:
                    silent = _pick_silent(sc, cmds)
                    silent_from = k + 1
                    c = cmds[silent]
                    if not c.kw > MIN_GRANT_KW:
                        raise AssertionError(f"comms-loss battery {silent} has a zero command at step {k}")
                    h = int(sc.fleet[silent])
                    ev = {"step": k, "t": hhmm(tnow), "kind": "comms_lost", "home": h, "batt": int(silent),
                          "tf": int(sc.tf_of_batt[silent]), "cmdKW": round(c.kw, 2), "silentFrom": k + 1,
                          "expiresStep": int(c.expires_s // P1_STEP_SECONDS),
                          "text": f"{sc.labels[h]} (behind {sc.focus_of_tf.get(int(sc.tf_of_batt[silent]), 'tf')}) goes silent after its {hhmm(tnow)} command (+{c.kw:.1f} kW)"}
                    events.append(ev)
                elif comms_at is not None and k >= comms_at and silent is None:
                    silent = np.asarray(sorted(int(i) for i in picker(sc, cmds, k)), dtype=np.int64)
                    silent_from = k + 1
                    events.append({"step": k, "t": hhmm(tnow), "kind": "comms_lost", "batts": silent.tolist(),
                                   "homes": [int(sc.fleet[i]) for i in silent], "silentFrom": k + 1,
                                   "cmdKW": [round(cmds[int(i)].kw, 2) for i in silent],
                                   "expiresStep": [int(cmds[int(i)].expires_s // P1_STEP_SECONDS) for i in silent],
                                   "text": f"{len(silent)} batteries go silent after their {hhmm(tnow)} commands"})
            else:
                target[k] = 0.0
        # devices act
        for i in range(m):
            if branch == "none":
                st_chars[i] = "I"
                continue
            if blocked[i]:
                lit = bat[i].island(float(kw[sc.load_home == sc.fleet[i]].sum()), DT_H)
                batkw[k, i] = 0.0
                st_chars[i] = "B" if lit else "I"
                continue
            if branch == "naive":
                batkw[k, i] = bat[i].advance(cmd_kw[i], DT_H)
                v = batkw[k, i]
                st_chars[i] = "C" if v > 1e-9 else ("D" if v < -1e-9 else "I")
            else:
                if devs[i].cmd is not None and t_s >= devs[i].cmd.expires_s:
                    pass
                v, s = devs[i].step(t_s, DT_H)
                batkw[k, i] = v
                if s != "X" and ctl.stale[i]:
                    s = "S"
                st_chars[i] = s
        soc[k] = [b.soc for b in bat]
        states.append("".join(st_chars))
        home_tf_kw[k] = np.bincount(sc.load_tf, weights=kw, minlength=T)
        f.set_loads(kw, kvar)
        f.set_batteries(batkw[k])
        r = f.solve()
        pct[k] = r["pct"]
        P[k] = r["P"]
        head[k] = r["head_amps"]
        vmin_home[k] = r["vmin_home_pu"]
        head_kw[k], head_kvar[k], cap_kvar[k] = r["head_kw"], r["head_kvar"], r["cap_kvar"]
        load_kw[k] = float(kw[~np.isin(sc.load_tf, list(f.isolated))].sum()) if f.isolated else float(kw.sum())
        P_prev, Q_prev = r["P"].copy(), r["Q"].copy()
        applied_prev = batkw[k].copy()
        # protection (4.5, ASSUMPTION): judged on OpenDSS loading; the transformer opens for the rest of the window
        over200 = np.where(pct[k] > FUSE_PCT, over200 + 1, 0)
        over300 = np.where(pct[k] > FUSE_INSTANT_PCT, over300 + 1, 0)
        for t in np.flatnonzero((over200 >= need_fuse) | (over300 >= need_inst)):
            t = int(t)
            if t in f.isolated:
                continue
            f.isolate_tf(t)
            isolated_at[t] = k
            if k + 1 < n:
                for h in sc.feeder.transformers[t]["homes"]:
                    home_state.append([k + 1, int(h), "battery" if int(h) in set(sc.fleet.tolist()) else "dark"])
            ticker.append([k, f"{hhmm(tnow)} protection may operate on {sc.focus_of_tf.get(t, 'tf ' + str(t))} "
                              f"({pct[k, t]:.0f}% of nameplate; ASSUMPTION rule: {FUSE_PCT:.0f}% for {FUSE_MINUTES} min)"])
        prev_state = st_chars
    return {"branch": branch, "pct": pct, "P": P, "head": head, "vmin_home": vmin_home, "batkw": batkw, "soc": soc,
            "state": states, "home_state": home_state, "ticker": ticker, "events": events, "target": target,
            "home_tf_kw": home_tf_kw, "isolated_at": isolated_at, "grants": grants, "stats": stats,
            "ctl": ctl, "devs": devs, "silent": silent,
            "head_kw": head_kw, "head_kvar": head_kvar, "cap_kvar": cap_kvar, "load_kw": load_kw}


def _pick_silent(sc, cmds):
    """The battery behind A with the largest charge command; if none on A is charging, the first charging battery on
    B, C, then D (build prompt 5.4.4)."""
    for key in "ABCD":
        tf = sc.focus[key]
        on = [(c.kw, -i, i) for i, c in cmds.items() if sc.tf_of_batt[i] == tf and c.kw > MIN_GRANT_KW]
        if on:
            if key == "A":
                return max(on)[2]
            return min(i for _, _, i in on)
    raise AssertionError("no battery on A-D is charging at the comms-loss step")


def _ticker(sc, win, k, dec, caps, grants, out):
    """Ticker lines for A-D batteries when their command changes (from allocate's decisions)."""
    H = caps[0]
    prev = grants[k - 1] if k else np.zeros(sc.m)
    now = grants[k]
    t = hhmm(win.time(k))
    seen = set()
    for i, kind, kw, room in dec:
        tf = int(sc.tf_of_batt[i])
        key = sc.focus_of_tf.get(tf)
        if key is None or key == "240" or i in seen:
            continue
        seen.add(i)
        lab = sc.labels[int(sc.fleet[i])]
        changed = abs(now[i] - prev[i]) >= MIN_GRANT_KW
        if kind in ("grant", "cover") and changed and prev[i] <= MIN_GRANT_KW:
            why = f"lowest charge on {key} goes first" if kind == "grant" else f"covers for the silent battery on {key}"
            out.append([k, f"{t} {key}: {lab} starts charging, +{kw:.1f} kW of {room:.1f} kW room ({why})"])
        elif kind == "cut":
            # the controller cuts the newest grant among the batteries it still hears (a silent unit is not booked)
            out.append([k, f"{t} {key}: room shrank to {max(H[tf], 0):.1f} kW → {lab} cut to {kw:.1f} kW (newest live grant first)"])
        elif kind == "relief" and prev[i] > -MIN_GRANT_KW:
            out.append([k, f"{t} {key} above {TAG['AWARE_MARGIN']['value']:.0%} of nameplate → {lab} sends {abs(kw):.1f} kW out "
                           f"(relief overrides the market)"])
    for i in range(sc.m):
        tf = int(sc.tf_of_batt[i])
        key = sc.focus_of_tf.get(tf)
        if key is None or key == "240" or i in seen:
            continue
        if prev[i] > MIN_GRANT_KW and now[i] <= MIN_GRANT_KW:
            out.append([k, f"{t} {key}: {sc.labels[int(sc.fleet[i])]} stops charging (taking turns)"])


# ------------------------------------------------------------------------------------------------------------------
def battery_active(sc, run):
    """[n, 379] bool: the transformer's batteries are charging (> 0.5 kW) or back-feeding (discharging while the
    transformer's net P is negative), at that step or within the previous 2 steps (build prompt 7.3)."""
    per_tf = np.stack([np.bincount(sc.tf_of_batt, weights=run["batkw"][k], minlength=len(sc.kva))
                       for k in range(len(run["batkw"]))])
    act = (per_tf > MIN_GRANT_KW) | ((per_tf < -MIN_GRANT_KW) & (run["P"] < 0))
    out = act.copy()
    out[1:] |= act[:-1]
    out[2:] |= act[:-2]
    return out, per_tf


def summarize(sc, run, loads_driver=None):
    win = sc.win
    pct = run["pct"]
    n = len(pct)
    caused, per_tf = battery_active(sc, run)
    nev = normal_events(pct, 1.0)
    caused_n = [e for e in nev if caused[e[1]:e[2], e[0]].any()]
    emerg = pct > TIER_EMERGENCY_PCT
    prot = protection_events(pct, P1_STEP_SECONDS)
    fleet_set = set(sc.fleet.tolist())
    dark = sorted({h for _, h, s in run["home_state"] if s == "dark"})
    onbat = sorted({h for _, h, s in run["home_state"] if s == "battery"})
    mx = np.unravel_index(int(np.argmax(pct)), pct.shape)
    iso = np.zeros(pct.shape[1], dtype=bool)
    v = run["vmin_home"].copy()
    v[v <= 0] = np.nan           # isolated homes read 0.0: not a voltage
    kv, hv = np.unravel_index(int(np.nanargmin(v)), v.shape)
    below095 = int((np.nanmin(v, axis=0) < 0.95).sum())
    kh = int(np.argmax(run["head"]))
    ko = next((k for k in range(n) if sc.modes[k] == "charge"), None)
    if ko is not None:
        kh2 = ko + int(np.argmax(run["head"][ko:]))
    socs = run["soc"]
    islanded = np.array([[c == "B" for c in s] for s in run["state"]])
    # HIST-R2 3.5 (l2's decision): a battery behind an open transformer carries its home down to empty. That is the
    # member backup in use during an outage, not a reserve breach; it is counted apart (reserveUsedInOutage).
    outage = np.zeros(socs.shape, dtype=bool)
    for t_iso, k_iso in run["isolated_at"].items():
        outage[k_iso + 1:, sc.tf_of_batt == t_iso] = True
    below = socs < sc.reserve - 1e-9
    rpct = f"{sc.reserve:.0%}"
    breaches = int((below & ~islanded & ~outage).sum())
    used_in_outage = int((below & outage).sum())
    has_batt = run["branch"] != "none"
    dl = min(win.deadline_step, n) - 1
    value = energy_value_usd(run["batkw"], sc.price, DT_H) + 0.0   # + 0.0: no "-0.0" in the JSON
    s = {
        "normalEvents": labelled(len(nev), "SIM", "OpenDSS: runs above 110% lasting >= 30 min"),
        "emergencyTfs": labelled(int(emerg.any(axis=0).sum()), "SIM", "OpenDSS: transformers above 150% at any step"),
        "batteryCausedNormal": labelled(len(caused_n), "SIM", "normal-tier events while the transformer's batteries charge or back-feed (at the step or the 2 before)"),
        "batteryCausedEmergency": labelled(int((emerg & caused).any(axis=0).sum()), "SIM", "transformers above 150% while their batteries charge or back-feed"),
        "batteryCausedAmberMin": labelled(int(((pct > TIER_AMBER_PCT) & caused).sum()), "SIM", "transformer-minutes above 100% while their batteries charge or back-feed"),
        "homeOnlyOver100": labelled(int(((pct > TIER_AMBER_PCT) & ~caused).any(axis=0).sum()), "SIM", "transformers above 100% on home load alone"),
        "protectionOperated": labelled(len(prot), "SIM", f"ASSUMPTION rule: fuse opens above {FUSE_PCT:.0f}% for {FUSE_MINUTES} min or {FUSE_INSTANT_PCT:.0f}% for {FUSE_INSTANT_SECONDS} s"),
        "homesDark": labelled(len(dark), "SIM", "battery-less homes behind an open transformer"),
        "homesOnBattery": labelled(len(onbat), "SIM", "battery homes islanded on their own battery (lit)"),
        "maxLoading": labelled(round(float(pct.max()), 1), "SIM", "OpenDSS", tf=int(mx[1]), t=hhmm(win.time(mx[0]))),
        "reserveBreaches": labelled(breaches if has_batt else 0, "SIM", f"battery-steps below the {rpct} reserve outside an outage "
                                    "(a battery carrying its home behind an open transformer is the backup in use: reserveUsedInOutage)"),
        "reserveUsedInOutage": labelled(used_in_outage if has_batt else 0, "SIM",
                                        f"battery-steps below the {rpct} reserve while carrying its home behind an open transformer "
                                        "(the member backup in use during an outage, not a breach; ASSUMPTION fuse rule)"),
        "chargedPctBy0400": labelled(round(float(socs[dl].mean() * 100), 1) if has_batt else None, "SIM",
                                     f"fleet state of charge at {hhmm(win.time(dl + 1))}" if has_batt else "no batteries in this branch"),
        "energyValueUSD": labelled(round(value, 2) + 0.0, "DERIVED", "sum of -P x price x dt (gross energy value, not Base's P&L)"),
        "vMinHome": labelled(round(float(v[kv, hv]), 4), "SIM", "OpenDSS minimum home voltage (pu, 120 V base)",
                             volts=round(float(v[kv, hv]) * 120, 1), home=int(hv), t=hhmm(win.time(kv))),
        "homesBelow095": labelled(below095, "SIM", "homes below 0.95 pu at any step"),
        "feederHead": labelled(round(float(run["head"][kh]) / HEAD_RATING_A * 100, 1), "SIM",
                               "OpenDSS current in the head cable as % of its rating", amps=round(float(run["head"][kh]), 1),
                               t=hhmm(win.time(kh)),
                               ratingA=labelled(HEAD_RATING_A, "REAL", "SMART-DS NormAmps of linecode 3P_UG_AL_350kcmil_3 "
                                                                       "(data/smartds/LineCodes.dss); site/ems/flow-spec.md"),
                               **({"afterOnset": labelled(round(float(run["head"][kh2]) / HEAD_RATING_A * 100, 1), "SIM",
                                                          "head-cable maximum from the D-26 onset on", amps=round(float(run["head"][kh2]), 1),
                                                          t=hhmm(win.time(kh2)))} if ko is not None else {})),
        "fuseMargin": _fuse_margin(win, pct),
        "commands": labelled(run["stats"]["issued"], "SIM", "commands issued by the controller (seq + expiry)"),
        "seqRejected": labelled(run["stats"]["rejected"], "SIM", "deliveries a device refused for a non-increasing seq"),
        "nonIncreasingAccepted": labelled(sum(d.accepted_nonincreasing for d in run["devs"]), "SIM", "must be 0"),
        "actedAfterExpiry": labelled(_acted_after_expiry(run), "SIM", "battery-steps with non-zero kW in state X (must be 0)"),
    }
    return s, {"caused": caused, "per_tf": per_tf, "normal": nev, "caused_normal": caused_n, "prot": prot}


def _fuse_margin(win, pct):
    """The worst transformer against the ASSUMPTION fuse rule: its peak, and its longest run above FUSE_PCT."""
    t = int(np.argmax(pct.max(axis=0)))
    col = pct[:, t] > FUSE_PCT
    run = best = 0
    for x in col:
        run = run + 1 if x else 0
        best = max(best, run)
    k = int(np.argmax(pct[:, t]))
    return labelled(round(float(pct[k, t]), 1), "SIM",
                    f"peak loading vs the ASSUMPTION fuse rule ({FUSE_PCT:.0f}% for {FUSE_MINUTES} min, or {FUSE_INSTANT_PCT:.0f}% at once)",
                    tf=t, t=hhmm(win.time(k)), minutesAbove200=labelled(best, "SIM", "longest run above 200% (minutes)"),
                    fuseMinutes=labelled(FUSE_MINUTES, "ASSUMPTION", TAG["FUSE_MINUTES"]["cite"]))


def _acted_after_expiry(run):
    return int(sum(1 for k, s in enumerate(run["state"]) for i, c in enumerate(s)
                   if c == "X" and abs(run["batkw"][k, i]) > 1e-9))


def branch_doc(sc, run, fixture=False, dwell=MIN_DWELL_MIN, inputs=None):
    win = sc.win
    T = len(sc.kva)
    codes = tier_codes(run["pct"], P1_STEP_SECONDS / 60)
    caused, per_tf = battery_active(sc, run)
    focus = {}
    for key, tf in sc.focus.items():
        focus[key] = {"tf": tf, "homeKW": i10(run["home_tf_kw"][:, tf]), "batKW": i10(per_tf[:, tf])}
    v = run["vmin_home"].copy()
    v[v <= 0] = np.nan
    vmin = np.nanmin(v, axis=1)
    counts = [[int((codes[k] == c).sum()) for c in (1, 2, 3, 4, 5)] for k in range(len(codes))]
    reverse = [[int(k), int(t)] for k, t in zip(*np.nonzero(run["P"] < 0))]
    doc = envelope(f"p1.{run['branch']}", "sim.p1_build", inputs=inputs or inputs_sha(),
                   constants=constants_block(("AWARE_MARGIN", "CORE_POWER_KW", "CORE_USABLE_KWH", "CORE_RTE",
                                              "RESERVE_FLOOR", "SOC0", "BATTERY_PF", "MIN_DWELL_MIN", "COMMAND_TTL_S",
                                              "COMMS_STALE_S"), dwell, sc.overrides()),
                   sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                            "load": {"label": "SIM", "text": LOADS_TEXT},
                            "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow, every step"}},
                   series={"loading": {"label": "SIM", "unit": "pct x10", "by": "OpenDSS"},
                           "tier": {"label": "SIM", "unit": "code 0-5", "by": "sim.tiers from OpenDSS loading"},
                           "batKW": {"label": "SIM", "unit": "kW x10"}, "soc": {"label": "SIM", "unit": "per mille"},
                           "focus": {"label": "SIM", "unit": "kW x10", "by": "home load (SMART-DS, interpolated) and battery kW per transformer"},
                           "targetKW": {"label": "SIM", "unit": "kW x10"}, "deliveredKW": {"label": "SIM", "unit": "kW x10"},
                           "vMin": {"label": "SIM", "unit": "pu x1e4", "by": "OpenDSS"},
                           "counts": {"label": "SIM", "unit": "transformers at tier codes 1-5"},
                           "reverse": {"label": "SIM", "unit": "[step, tf] where the transformer's net P < 0 (back-feed)", "by": "OpenDSS"}},
                   fixture=fixture)
    doc.update({
        "branch": run["branch"], "steps": win.steps,
        "loading": np.rint(run["pct"] * 10).astype(int).tolist(),
        "focus": focus,
        "tier": tier_strings(codes),
        "batKW": i10(run["batkw"]),
        "soc": np.rint(run["soc"] * 1000).astype(int).tolist(),
        "state": run["state"],
        "homeState": run["home_state"],
        "targetKW": i10(run["target"]),
        "deliveredKW": i10(run["batkw"].sum(axis=1)),
        "vMin": [int(round(x * 1e4)) for x in vmin],
        "counts": counts,
        "reverse": reverse,
        "ticker": run["ticker"] + [[e["step"], f"{e['t']} {e['text']}"] for e in run["events"]],
    })
    doc["ticker"].sort(key=lambda x: x[0])
    return doc


def build(win, out=OUT, loads=None, feeder=None, quiet=False, dwell=MIN_DWELL_MIN, branches=BRANCHES, story=story_for,
          inputs=None, write_branch=None, scenario_kw=None):
    """Run the branches and write meta.json + one file per branch into `out`.

    branches: BRANCHES (23 Aug, the default) or ("none", "naive", "aware") for a history day (HIST-R2 D2: the failure
              script is tuned to 23 Aug and aware_faults is 23 Aug only);
    story:    a function(meta) -> {tag, why{text, label, cite?}} (default sim.history.story_for), or None;
    inputs:   the envelope's inputs block (a history day names the loads slice it read); default inputs_sha();
    write_branch: function(path_without_suffix, doc) -> (name, bytes) for the branch files (a history day writes gzip);
              default write_json to <branch>.json;
    scenario_kw: the Scenario levers ({soc0, reserve, growth}); default the committed values."""
    branches = tuple(b for b in BRANCHES if b in branches)
    if branches[:3] != ("none", "naive", "aware"):
        raise ValueError(f"branches must include none, naive and aware: {branches}")
    t0 = time.time()
    sc = Scenario(win, loads=loads, feeder=feeder, **(scenario_kw or {}))
    runs = {}
    solves = 0
    for b in ("none", "naive", "aware"):
        runs[b] = run_branch(sc, b, faults={"dwell": dwell})
        solves += win.steps + 1
        if not quiet:
            print(f"  {b}: max {runs[b]['pct'].max():.1f}% ({time.time() - t0:.1f} s)", flush=True)
    g = runs["aware"]["grants"]
    charging = np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))
    tc = int(charging[0]) if len(charging) else None
    faults = {"dwell": dwell}
    if "aware_faults" in branches:
        if tc is not None:
            for key, off in (("comms", FAULT_COMMS_AFTER_MIN), ("hot", FAULT_HOT_AFTER_MIN), ("stall", FAULT_STALL_AFTER_MIN)):
                if tc + off < win.steps:
                    faults[key] = tc + off
        runs["aware_faults"] = run_branch(sc, "aware_faults", faults=faults)
        solves += win.steps + 1
    secs = time.time() - t0
    if not quiet and "aware_faults" in runs:
        print(f"  aware_faults ({secs:.1f} s)", flush=True)
    meta, docs = assemble(sc, runs, tc, faults, solves, dwell=dwell, inputs=inputs)
    if story is not None:
        meta["story"] = story(meta)
    out = Path(out)
    sizes = {}
    sizes["meta.json"] = write_json(out / "meta.json", meta)
    for b, d in docs.items():
        if write_branch is None:
            sizes[f"{b}.json"] = write_json(out / f"{b}.json", d)
        else:
            name, size = write_branch(out / b, d)
            sizes[name] = size
    return {"sc": sc, "runs": runs, "meta": meta, "docs": docs, "sizes": sizes, "seconds": secs, "solves": solves,
            "tc": tc}


def relief_text(minutes_over, none_max, driver):
    """relief.text, derived from the day (HIST-R2 3.1, audit L12): never a fixed 23 Aug sentence."""
    if minutes_over == 0:
        return f"A stays under its nameplate all evening (max {none_max:.1f}%)"
    return f"over nameplate for {minutes_over} minutes (amber; not a failure): {driver['label']}'s load"


def onset_deferral(sc, runs):
    """Adopt #3: at the D-26 onset step, the fleet kW naive and aware charge (SIM) and what aware defers (DERIVED).
    kW are the branch files' deliveredKW (0.1 kW), so the page and this block agree."""
    ko = next((k for k in range(sc.win.steps) if sc.modes[k] == "charge"), None)
    if ko is None or "naive" not in runs or "aware" not in runs:
        return None
    nk = round(float(np.rint(runs["naive"]["batkw"][ko].sum() * 10)) / 10, 1)
    ak = round(float(np.rint(runs["aware"]["batkw"][ko].sum() * 10)) / 10, 1)
    t = hhmm(sc.win.time(ko))
    return {"step": ko, "t": t,
            "naiveKW": labelled(nk, "SIM", f"fleet charge kW at the {t} onset, naive (every battery at full power at once)"),
            "awareKW": labelled(ak, "SIM", f"fleet charge kW at the {t} onset, feeder-aware (only what fits each transformer)"),
            "deferredKW": labelled(round(nk - ak, 1), "DERIVED", f"naive - aware fleet charge kW at the {t} onset: charge the "
                                                                 f"feeder check moved later in the night")}


def faults_note(sc, runs, values):
    """Audit L7: aware + failures earns a little more than aware only because the silent battery stopped charging.
    The note states the silent battery's end SoC and the kWh the fleet did not charge (SIM), and the $ delta (DERIVED)."""
    af, aw = runs["aware_faults"], runs["aware"]
    i = af["silent"]
    if i is None or np.ndim(i) != 0:
        return None
    dl = min(sc.win.deadline_step, sc.win.steps) - 1
    soc = float(af["soc"][dl, int(i)] * 100)
    kwh = float((np.clip(aw["batkw"], 0, None).sum() - np.clip(af["batkw"], 0, None).sum()) * DT_H)
    d = values["aware_faults"] - values["aware"]
    lab = sc.labels[int(sc.fleet[int(i)])]
    return {"text": (f"{'+' if d >= 0 else '-'}${abs(d):.2f} against feeder-aware is not a gain: the silent battery ({lab}) "
                     f"ends at {soc:.1f}% charge, so the fleet charged {kwh:.1f} kWh less and bought less power back"),
            "label": "DERIVED",
            "silentEndSocPct": labelled(round(soc, 1), "SIM", f"{lab}'s state of charge at {hhmm(sc.win.time(dl + 1))}"),
            "chargedKWhLess": labelled(round(kwh, 1), "SIM", "fleet charge energy, aware - aware + failures"),
            "valueDeltaUSD": labelled(round(d, 2) + 0.0, "DERIVED", "energy value, aware + failures - aware")}


def assemble(sc, runs, tc, faults, solves, dwell=MIN_DWELL_MIN, inputs=None):
    win = sc.win
    inputs = inputs or inputs_sha()
    summaries = {}
    extra = {}
    for b, run in runs.items():
        summaries[b], extra[b] = summarize(sc, run)
    docs = {b: branch_doc(sc, run, dwell=dwell, inputs=inputs) for b, run in runs.items()}
    onset, onset_p, peak_ts, threshold, rule_mode = sc.onset
    a = sc.focus["A"]
    # relief (16:45 on A): measured, not assumed
    none_a = runs["none"]["pct"][:, a]
    kp = int(np.argmax(none_a))
    aware = runs["aware"]
    per_tf_aware = extra["aware"]["per_tf"]
    relief_steps = [k for k in range(win.steps) if sc.modes[k] == "idle" and per_tf_aware[k, a] < -MIN_GRANT_KW]
    relief_kw = float(-per_tf_aware[relief_steps, a].min()) if relief_steps else 0.0
    relief_kwh = float(-per_tf_aware[relief_steps, a].sum() * DT_H) if relief_steps else 0.0
    # when the largest relief minute is, and what A's batteries give at the peak minute itself (judge R1 F7: the
    # peak relief and the 16:45 value differ by a minute; captions word it from these, not from one number)
    kr = relief_steps[int(np.argmin(per_tf_aware[relief_steps, a]))] if relief_steps else None
    relief_when = ({"t": hhmm(win.time(kr)), "step": int(kr)} if kr is not None else {})
    relief_at_peak = labelled(round(float(max(0.0, -per_tf_aware[kp, a])), 2), "SIM",
                              "A's batteries' discharge at the peak minute (relief.t)")
    loads = sc.loads
    k15 = loads.step_of(win.day, win.start_min + kp)
    driver = loads.driver(a, k15)
    relief = {
        "tf": a, "t": hhmm(win.time(kp)), "step": kp,
        "none": labelled(round(float(none_a[kp]), 1), "SIM", "OpenDSS, no batteries"),
        "aware": labelled(round(float(aware["pct"][kp, a]), 1), "SIM", "OpenDSS, feeder-aware"),
        "minutesOver100": labelled(int((none_a > TIER_AMBER_PCT).sum()), "SIM", "minutes A spends above nameplate, none vs aware",
                                   none=int((none_a > TIER_AMBER_PCT).sum()), aware=int((aware["pct"][:, a] > TIER_AMBER_PCT).sum())),
        "reliefKW": labelled(round(relief_kw, 2), "SIM", "A's batteries discharging outside the market plan (relief): the largest minute",
                             **relief_when, atPeak=relief_at_peak),
        "reliefKWh": labelled(round(relief_kwh, 3), "SIM", "energy of that relief"),
        "driver": driver,
        "text": relief_text(int((none_a > TIER_AMBER_PCT).sum()), float(none_a[kp]), driver),
    }
    minutes_over = int((none_a > TIER_AMBER_PCT).sum())
    # unrelieved: over 100% in aware on home load only, no battery on the transformer
    fleet_tfs = set(sc.tf_of_batt.tolist())
    unrelieved = []
    ap = aware["pct"]
    for t in np.flatnonzero((ap > TIER_AMBER_PCT).any(axis=0)):
        t = int(t)
        if t in fleet_tfs:
            continue
        kk = int(np.argmax(ap[:, t]))
        unrelieved.append({"tf": t, "reason": f"home load only, no battery: peak {ap[kk, t]:.1f}% at {hhmm(win.time(kk))} (SIM)",
                           "peak": labelled(round(float(ap[kk, t]), 1), "SIM", "OpenDSS", t=hhmm(win.time(kk))),
                           "driver": loads.driver(t, loads.step_of(win.day, win.start_min + kk))})
    # money
    kpk = int(np.argmax(sc.price))
    klo = kp
    fleet_at_peak = {b: float(-runs[b]["batkw"][kpk].sum()) for b in runs if b != "none"}
    harm = {b: {"normalEvents": len(extra[b]["normal"]), "emergencyTfs": int((runs[b]["pct"] > TIER_EMERGENCY_PCT).any(axis=0).sum()),
                "protectionOperated": len(extra[b]["prot"])} for b in runs}
    values = {b: summaries[b]["energyValueUSD"]["v"] for b in runs}
    money = money_block(values, relief_kwh, float(sc.price[kpk]),
                        float(sc.price[klo]), hhmm(win.time(kpk)), hhmm(win.time(klo)), fleet_at_peak, harm)
    batt_runs = [b for b in runs if b != "none"]
    money["split"] = split_block({b: runs[b]["batkw"] for b in batt_runs}, sc.price, DT_H, values, sc.m)
    cash = {b: cash_cents(runs[b]["batkw"], sc.price, DT_H) for b in batt_runs}
    for b in batt_runs:
        if cash[b][-1] != int(round(values[b] * 100)):
            raise AssertionError(f"cash {b}: {cash[b][-1]} cents != energy value {values[b]:.2f}")
    if "aware_faults" in runs:
        note = faults_note(sc, runs, values)
        if note is not None:
            summaries["aware_faults"]["note"] = note
    # events of aware_faults, with their measured outcomes (a history day has no aware_faults: events {})
    ev = []
    af = runs.get("aware_faults")
    for e in sorted(af["events"] if af else [], key=lambda x: x["step"]):
        e = dict(e)
        if e["kind"] == "comms_lost":
            i = e["batt"]
            col = [s[i] for s in af["state"]]
            e["staleStep"] = next((k for k in range(e["step"] + 1, win.steps) if col[k] == "S"), None)
            e["expiredStep"] = next((k for k in range(e["step"] + 1, win.steps) if col[k] == "X"), None)
            tf = e["tf"]
            others = [j for j in range(sc.m) if sc.tf_of_batt[j] == tf and j != i]
            cov = None
            if e["expiredStep"] is not None:
                for k in range(e["expiredStep"], min(win.steps, e["expiredStep"] + 2)):
                    if any(af["batkw"][k, j] > af["batkw"][k - 1, j] + MIN_GRANT_KW for j in others) or \
                            af["grants"][k, others].sum() > af["grants"][k - 1, others].sum() + MIN_GRANT_KW:
                        cov = k
                        break
            e["coveredStep"] = cov
            e["coveredBy"] = [int(sc.fleet[j]) for j in others]
        ev.append(e)
    # HIST-R2 3.2: the A marker is derived, and only when A actually went over its nameplate that evening
    markers = ([{"t": hhmm(win.time(kp)), "text": f"A peaks at {none_a[kp]:.1f}% with no batteries: over nameplate for "
                                                  f"{minutes_over} minutes ({driver['label']}'s load)", "label": "SIM"}]
               if minutes_over > 0 else [])
    for ts, mins in sorted(sc.plan):
        markers.append({"t": ts[11:16], "text": f"market discharge, {mins} min (perfect-foresight plan)", "label": "DERIVED"})
    markers.append({"t": hhmm(win.time(kpk)), "text": f"price peak ${sc.price[kpk]:.2f}/MWh", "label": "REAL"})
    markers.append({"t": onset[11:16], "text": f"D-26 onset ${onset_p:.2f}/MWh ({rule_mode})", "label": "DERIVED"})
    for e in ev:
        markers.append({"t": e["t"], "text": e["text"], "label": "ASSUMPTION"})
    markers = [x for x in markers if win.t0 <= datetime.strptime(f"{win.day}T{x['t']}", FMT) + (timedelta(days=1) if x["t"] < hhmm(win.t0) else timedelta()) <= win.time(win.steps - 1)]
    part = [[a_[11:16], mm] for a_, mm in sc.plan if mm < 15]
    ercot = ercot_demand()
    on_a = np.flatnonzero(sc.tf_of_batt == a)
    pmax_a = sorted(set(float(x) for x in sc.pmax[on_a]))
    if len(pmax_a) != 1:
        raise AssertionError(f"the scale ladder needs one battery class on A, found {pmax_a}")
    ladder = scale_ladder(len(on_a), pmax_a[0], "A", sc.feeder.transformers[a]["id"], float(sc.kva[a]),
                          head_kva_per_phase(), ercot)
    meta = envelope("p1.meta", "sim.p1_build", inputs=inputs,
                    constants=constants_block(("TIER_AMBER_PCT", "TIER_NORMAL_PCT", "TIER_NORMAL_MIN", "TIER_EMERGENCY_PCT",
                                     "FUSE_PCT", "FUSE_MINUTES", "FUSE_INSTANT_PCT", "FUSE_INSTANT_SECONDS",
                                     "CONTROLLER_VIEW", "AWARE_MARGIN", "SOC0", "RESERVE_FLOOR", "CORE_POWER_KW",
                                     "CORE_USABLE_KWH", "CORE_RTE", "BATTERY_PF", "CHARGE_URGENCY", "MIN_DWELL_MIN",
                                     "SOC_BUCKET", "MIN_GRANT_KW", "FLIP_MIN", "COMMAND_TTL_S", "COMMS_STALE_S",
                                     "FAULT_COMMS_AFTER_MIN", "FAULT_HOT_AFTER_MIN", "FAULT_STALL_AFTER_MIN", "EV_KW",
                                     "HOT_MINUTES", "STALL_MIN", "P1_DAY", "P1_START", "P1_STEPS", "LOAD_PAIRING",
                                     "PROFILE_INDEX_RULE", "CAPACITY_BENCHMARK_USD_KW_MONTH", "CAPACITY_HIGH_USD_KW_MONTH",
                                     "TRANSFORMER_REPLACEMENT_USD", "HEAD_RATING_A", "HEAD_RATING_KVA",
                                     "SCALE_LADDER_ERCOT") + LEAD_CONSTS, dwell, sc.overrides()),
                    sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                             "load": {"label": "SIM", "text": LOADS_TEXT},
                             "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow, every step of every branch"},
                             "naive": {"label": "ASSUMPTION", "text": NAIVE_TEXT},
                             "ercotDemand": {"label": "REAL", "text": f"ERCOT system demand, 5 min, {ercot['day']} "
                                                                      f"({ERCOT_DEMAND_REL}; the scale ladder's ERCOT rung)"}},
                    series={"price": {"label": "REAL", "unit": "$/MWh"},
                            "cash": {"label": "DERIVED", "unit": "USD cents, cumulative, fleet", "by": "REAL LZ_NORTH x SIM battery kW",
                                     "cite": f"cumulative sum of -P x price x dt at the end of each step; {SPLIT_CITE}"}})
    meta.update({
        "day": win.day, "start": hhmm(win.t0), "stepSeconds": P1_STEP_SECONDS, "steps": win.steps,
        "tiers": {"amber": 100, "normal": 110, "normalMinutes": 30, "emergency": 150, "label": "REAL"},
        "protection": {"fusePct": 200, "fuseMinutes": 10, "instantPct": 300, "instantSeconds": 60, "label": "ASSUMPTION",
                       "cite": TAG["FUSE_PCT"]["cite"]},
        "price": [float(x) for x in sc.price],
        "plan": {"discharge": [[a_[11:16], mm] for a_, mm in sc.plan], "partial": part, "onset": onset[11:16],
                 "onsetPrice": labelled(onset_p, "REAL", "ERCOT RTM SPP LZ_NORTH"), "rule": "D-26", "mode": rule_mode,
                 "threshold": labelled(round(threshold, 2), "DERIVED", "2 x the day's median price"),
                 "label": "DERIVED"},
        "branches": list(runs),
        "naiveLabel": {"text": NAIVE_TEXT, "label": "ASSUMPTION", "cite": "build prompt 3.4; §12 Q5"},
        "tc": {"step": tc, "t": hhmm(win.time(tc)) if tc is not None else None,
               "text": "first minute aware grants non-zero charge"},
        "events": {"aware_faults": ev} if af is not None else {},
        "markers": markers,
        "summary": summaries,
        "controllerView": {"text": CONTROLLER_VIEW, "label": "ASSUMPTION", "cite": TAG["CONTROLLER_VIEW"]["cite"]},
        "relief": relief,
        "money": money,
        "cash": cash,
        "onsetDeferral": onset_deferral(sc, runs),
        "unrelieved": unrelieved,
        "scaleLadder": ladder,
        "engine": {"solves": labelled(solves, "SIM", "OpenDSS solves in this build (incl. one warm-up per branch)"),
                   "msPerSolve": labelled(None, "SIM", "timings live in ui/data/engine.json (not deterministic)")},
    })
    return meta, docs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="60 steps from 22:00, to ~/hb-overnight/tmp/p1-quick")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dwell", type=int, default=MIN_DWELL_MIN, help="MIN_DWELL_MIN override (the judge's check)")
    a = ap.parse_args(argv)
    if a.quick:
        win = Window(start="22:00", steps=60)
        out = Path(a.out) if a.out else QUICK_OUT
    else:
        win = Window()
        out = Path(a.out) if a.out else OUT
    if a.dwell != MIN_DWELL_MIN and out == OUT:
        raise SystemExit("--dwell changes the committed data; pass --out")
    print(f"P1 build {win.day} {hhmm(win.t0)} + {win.steps} x {P1_STEP_SECONDS} s -> {out}", flush=True)
    r = build(win, out=out, dwell=a.dwell)
    tot = sum(r["sizes"].values())
    for name, size in r["sizes"].items():
        print(f"  wrote {name} {size / 1024:.0f} KB")
    print(f"P1 build: {r['solves']} OpenDSS solves in {r['seconds']:.1f} s ({r['seconds'] / r['solves'] * 1000:.1f} ms/step incl. controller); "
          f"Tc {r['meta']['tc']['t']} ; {tot / 1048576:.2f} MB")
    if not a.quick and a.out is None:
        TIMING.parent.mkdir(parents=True, exist_ok=True)
        TIMING.write_text(json.dumps({"seconds": round(r["seconds"], 1), "solves": r["solves"],
                                      "loadavg": ([round(x, 1) for x in os.getloadavg()] if hasattr(os, "getloadavg")
                                                  else None)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
