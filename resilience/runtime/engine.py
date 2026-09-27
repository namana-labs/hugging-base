"""The coordinator's step loop (docs/design.md §5.7): leases, the share split, delivery to epoch-aware devices, and
OpenDSS judging every step.

It mirrors sim.p1_build.run_branch's aware path so the result is comparable with P1: the same Scenario (window, loads,
market plan, fleet, SoC at the window start), the same controller view (last minute's measured transformer load minus
the batteries' reports, 60 s lag), the same fleet target formula, the same device step (expiry, reserve, taper), the
same protection rule on OpenDSS loading. What differs is who commands: RUNTIME_WORKERS workers, each holding leases on
transformer groups, instead of one controller.

One step:
  1. leases: expire the ones whose TTL ran out; give each orphaned group to the live worker (heartbeat at the previous
     step) holding the fewest groups, id breaking ties; the grant bumps the group's epoch;
  2. the view and the fleet target, exactly as P1 aware computes them;
  3. the split (partition.split_target): a group whose worker missed its last heartbeat is booked at its telemetry;
  4. every live worker ticks and returns a batch; at the kill step the doomed worker's batch is held back (the late
     batch) and the worker is killed;
  5. delivery in worker-id order: renewals to the lease table, commands to the devices; the late batch lands right
     after the takeover's commands (LATE_BATCH_RULE);
  6. devices act; OpenDSS solves; protection may open a transformer (ASSUMPTION rule, as P1).

Every device also has a shadow sim.devices.Device fed the same commands without the epoch: it never acts, it only
counts what a seq-only device would have accepted (the counterfactual in the summary).
"""
import math

import numpy as np

from sim.caps import transformer_caps
from sim.constants import (AWARE_MARGIN, FUSE_PCT, FUSE_MINUTES, FUSE_INSTANT_PCT, FUSE_INSTANT_SECONDS, MIN_GRANT_KW,
                           P1_STEP_SECONDS)
from sim.devices import Battery, Device, discharge_limit
from sim.orchestrator import charge_target
from sim.p1_build import DT_H, hhmm, _ticker

from resilience.constants import LEASE_TTL_S, RUNTIME_PARTITIONS, RUNTIME_WORKERS
from .device import REASONS, EpochDevice
from .lease import LeaseTable
from .partition import partitions, split_target
from .worker import WorkerLogic

STEP = P1_STEP_SECONDS
BIG = 10 ** 9


def worker_ids():
    return [f"W{i + 1}" for i in range(RUNTIME_WORKERS)]


def static_of(sc, parts):
    """What a worker needs to build its Controllers (plain lists: it crosses a process boundary in live mode)."""
    return {"tf_of_batt": [int(x) for x in sc.tf_of_batt], "pmax": [float(x) for x in sc.pmax],
            "emax": [float(x) for x in sc.emax], "rte": [float(x) for x in sc.rte], "ids": list(sc.ids),
            "parts": {p["id"]: list(p["batts"]) for p in parts}}


class InProcess:
    """Replay transport: the workers are stepped in this process, in worker-id order, on the simulation clock."""
    kind = "replay"

    def __init__(self, static, wids):
        self.w = {w: WorkerLogic(w, static) for w in wids}
        self.alive = set(wids)

    def grant(self, wid, pid, epoch):
        if wid in self.alive:
            self.w[wid].grant(pid, epoch)

    def tick(self, k, t_s, view, shares, mode):
        return {w: self.w[w].tick(k, t_s, view, shares.get(w, {}), mode) for w in sorted(self.alive)}

    def kill(self, wid):
        self.alive.discard(wid)

    def pace(self, k, on):
        pass

    def now(self):
        return None

    def close(self):
        pass


def run(sc, transport, kill_step=None, doomed_group=None, pace=None, device_factory=None, observer=None):
    """One evening under the runtime. kill_step=None is the no-failure run. Returns P1's run dict (so
    sim.p1_build.summarize and branch_doc apply unchanged) plus a "runtime" dict.

    Two hooks for resilience.detect (both None here by default, and then the run is exactly the runtime's):
      device_factory(i, battery) -> the device for battery i (a compromised one, say);
      observer(k, t_s, kw[m], setpoint[m], v_home[1010]) -> battery indices to quarantine from the next step on.
    A quarantined unit is held at zero, out of the fleet target and the split, and never commanded again."""
    win, f = sc.win, sc.feeder
    n, m, T = win.steps, sc.m, len(sc.kva)
    parts = partitions(sc.tf_of_batt, RUNTIME_PARTITIONS)
    pids = [p["id"] for p in parts]
    wids = worker_ids()
    leases = LeaseTable(pids, LEASE_TTL_S)
    f.restore_all()
    bat = [Battery(soc=float(sc.soc_start[i]), cls=sc.cls[i]) for i in range(m)]
    devs = [device_factory(i, b) if device_factory else EpochDevice(b) for i, b in enumerate(bat)]
    quarantined = np.zeros(m, dtype=bool)
    quarantine_log = []
    shadow = [Device(Battery(soc=0.5)) for _ in range(m)]
    pct = np.zeros((n, T))
    P = np.zeros((n, T))
    head = np.zeros(n)
    vmin_home = np.zeros((n, len(sc.home_tf)))
    batkw = np.zeros((n, m))
    soc = np.zeros((n, m))
    target = np.zeros(n)
    home_tf_kw = np.zeros((n, T))
    grants = np.zeros((n, m))
    part_target = np.zeros((n, len(parts)))
    part_delivered = np.zeros((n, len(parts)))
    states, home_state, ticker, events = [], [], [], []
    holder = []
    isolated_at = {}
    stats = {"issued": 0, "delivered": 0, "rejected": 0, "actedAfterExpiry": 0}
    reasons = {r: 0 for r in REASONS}
    counter = {"seqOnlyLateAccepted": 0, "seqOnlyTakeoverRejected": 0, "takeoverCommands": 0}
    kw0, kvar0 = sc.loads.at_minute(win.day, win.start_min - 1)
    f.set_loads(kw0, kvar0)
    f.set_batteries(np.zeros(m))
    r0 = f.solve()
    P_prev, Q_prev = r0["P"].copy(), r0["Q"].copy()
    applied_prev = np.zeros(m)
    over200 = np.zeros(T, dtype=int)
    over300 = np.zeros(T, dtype=int)
    need_fuse = max(1, math.ceil(FUSE_MINUTES * 60 / STEP))
    need_inst = max(1, math.ceil(FUSE_INSTANT_SECONDS / STEP))
    last_hb = {w: -BIG for w in wids}
    granted_at = {}
    grants_log = []
    takeover_epoch = {}
    for j, pid in enumerate(pids):
        w = wids[j % len(wids)]
        e = leases.grant(pid, w, 0)
        granted_at[pid] = 0
        grants_log.append([0, pid, w, e])
        transport.grant(w, pid, e)
    kill_info, late, late_info = None, None, None
    takeovers = []
    wall = {}
    for k in range(n):
        t_s = k * STEP
        tnow = win.time(k)
        transport.pace(k, bool(pace and pace(k, kill_info, takeovers)))
        kw, kvar = sc.home_loads(k)
        mode = sc.modes[k]
        blocked = np.array([sc.tf_of_batt[i] in f.isolated for i in range(m)])
        heard = ~blocked
        avail = heard & ~quarantined
        # 1. leases
        for pid, old, e_old in leases.expire(t_s):
            alive = [w for w in wids if last_hb[w] >= t_s - STEP]
            if not alive:
                events.append({"step": k, "t": hhmm(tnow), "kind": "orphan", "text": f"lease {pid} expired and no live worker can take it"})
                continue
            w = min(alive, key=lambda x: (len(leases.held_by(x)), x))
            e = leases.grant(pid, w, t_s)
            granted_at[pid] = t_s
            takeover_epoch[pid] = e
            grants_log.append([k, pid, w, e])
            transport.grant(w, pid, e)
            after = t_s - kill_info["step"] * STEP if kill_info else None
            tk = {"step": k, "t": hhmm(tnow), "partition": pid, "from": old, "worker": w, "epoch": e, "afterSeconds": after,
                  "text": f"lease {pid} ran out ({LEASE_TTL_S} s without renewal from {old}); {w} takes it over at epoch {e}"
                          + (f", {after} s after the kill" if after is not None else "")}
            takeovers.append(tk)
            events.append({"step": k, "t": tk["t"], "kind": "takeover", "text": tk["text"]})
            if transport.now() is not None:
                wall.setdefault("takeover", transport.now())
        # 2. the view and the fleet target (sim.p1_build.run_branch, aware)
        rep = np.where(heard, applied_prev, 0.0)
        bg_kw = P_prev - np.bincount(sc.tf_of_batt, weights=rep, minlength=T)
        bg_kvar = Q_prev
        socs = np.array([b.soc for b in bat])
        soc_t = np.where(avail, socs, 1.0)
        if mode == "charge":
            tgt = charge_target(soc_t, sc.emax, sc.rte, win.deadline_step - k)
        elif mode == "discharge":
            tgt = -float(sum(discharge_limit(socs[i], sc.emax[i], sc.pmax[i], sc.rte[i], DT_H) for i in range(m) if avail[i]))
        else:
            tgt = 0.0
        target[k] = tgt
        served = {}
        for pid in pids:
            h = leases.holder(pid)
            served[pid] = h is not None and (last_hb[h] >= t_s - STEP or granted_at.get(pid) == t_s)
        # 3. the split
        shares = split_target(mode, tgt, parts, served, applied_prev, soc_t, socs, sc.pmax, sc.emax, sc.rte,
                              sc.tf_of_batt, bg_kw, bg_kvar, sc.kva, DT_H, win.deadline_step - k, avail)
        for j, p in enumerate(parts):
            part_target[k, j] = shares[p["id"]] if served[p["id"]] else float(sum(applied_prev[i] for i in p["batts"]))
        by_worker = {}
        for pid in pids:
            h = leases.holder(pid)
            if h is not None:
                by_worker.setdefault(h, {})[pid] = shares[pid]
        view = {"heard": heard, "soc": socs, "bg_kw": bg_kw, "bg_kvar": bg_kvar, "kva": sc.kva,
                "blocked": blocked | quarantined}
        # 4. the workers
        batches = transport.tick(k, t_s, view, by_worker, mode)
        if kill_step is not None and k == kill_step:
            doomed = leases.holder(doomed_group)
            late = batches.pop(doomed, None)
            held = leases.held_by(doomed)
            transport.kill(doomed)
            if transport.now() is not None:
                wall["kill"] = transport.now()
            kill_info = {"step": k, "t": hhmm(tnow), "worker": doomed, "groups": held,
                         "text": f"worker {doomed} is killed while it holds {', '.join(held)}; its batteries run on their "
                                 f"last commands until they expire"}
            events.append({"step": k, "t": kill_info["t"], "kind": "kill", "text": kill_info["text"]})
        # 5. delivery
        if k:
            grants[k] = grants[k - 1]

        def deliver(c, is_late):
            stats["issued"] += 1
            if not heard[c.batt]:
                return None
            stats["delivered"] += 1
            reason = devs[c.batt].deliver(c, t_s)
            if reason is not None:
                reasons[reason] += 1
                if reason == "nonIncreasingSeq":
                    stats["rejected"] += 1
            seq_ok = shadow[c.batt].receive(c.seq_only())
            if is_late and seq_ok:
                counter["seqOnlyLateAccepted"] += 1
            if not is_late and takeover_epoch.get(c.partition) == c.epoch:
                counter["takeoverCommands"] += 1
                if not seq_ok:
                    counter["seqOnlyTakeoverRejected"] += 1
            return reason

        dec_all = []
        got = {}
        for w in sorted(batches):
            b = batches[w]
            last_hb[w] = t_s
            for pid, e in b["renew"]:
                leases.renew(pid, w, e, t_s)
                got[pid] = w
            for c in b["cmds"]:
                deliver(c, False)
            for i, g in b["kw"].items():
                grants[k, int(i)] = g
            dec_all += b["dec"]
        if late is not None and late_info is None and any(tk["step"] == k and tk["partition"] in kill_info["groups"]
                                                          for tk in takeovers):
            got_r = {r: 0 for r in REASONS}
            unexpired = 0
            for c in late["cmds"]:
                unexpired += int(t_s < c.expires_s)
                r = deliver(c, True)
                if r is not None:
                    got_r[r] += 1
            e_old = late["cmds"][0].epoch if late["cmds"] else None
            late_info = {"step": k, "t": hhmm(tnow), "worker": kill_info["worker"], "epoch": e_old,
                         "issuedStep": late["step"], "commands": len(late["cmds"]),
                         "withPower": sum(1 for c in late["cmds"] if abs(c.kw) > MIN_GRANT_KW),
                         "unexpiredOnArrival": unexpired, "rejected": got_r,
                         "text": f"{len(late['cmds'])} late commands from {kill_info['worker']} (epoch {e_old}, issued "
                                 f"{hhmm(win.time(late['step']))}) reach the devices: {got_r['staleEpoch']} rejected, stale epoch"}
            events.append({"step": k, "t": late_info["t"], "kind": "late", "text": late_info["text"]})
        holder.append("".join(got[pid][1:] if pid in got else "-" for pid in pids))
        # 6. devices act, OpenDSS judges
        st_chars = ["I"] * m
        for i in range(m):
            if blocked[i]:
                lit = bat[i].island(float(kw[sc.load_home == sc.fleet[i]].sum()), DT_H)
                st_chars[i] = "B" if lit else "I"
                continue
            if quarantined[i]:
                bat[i].advance(0.0, DT_H)
                continue
            v, s = devs[i].step(t_s, DT_H)
            batkw[k, i] = v
            st_chars[i] = s
        caps = transformer_caps(bg_kw, bg_kvar, sc.kva, AWARE_MARGIN)
        _ticker(sc, win, k, dec_all, caps, grants, ticker)
        for j, p in enumerate(parts):
            part_delivered[k, j] = float(sum(batkw[k, i] for i in p["batts"]))
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
        P_prev, Q_prev = r["P"].copy(), r["Q"].copy()
        applied_prev = batkw[k].copy()
        if observer is not None:
            live = [d.cmd is not None and d.cmd.issued_s <= t_s < d.cmd.expires_s for d in devs]
            setpoint = np.array([devs[i].cmd.kw if live[i] and not quarantined[i] else 0.0 for i in range(m)])
            for i in sorted(int(x) for x in observer(k, t_s, batkw[k].copy(), setpoint, r["vmin_home_pu"].copy())):
                if not quarantined[i]:
                    quarantined[i] = True
                    quarantine_log.append([k, i])
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
    return {"branch": "worker_kill" if kill_step is not None else "runtime", "pct": pct, "P": P, "head": head,
            "vmin_home": vmin_home, "batkw": batkw, "soc": soc, "state": states, "home_state": home_state,
            "ticker": ticker, "events": events, "target": target, "home_tf_kw": home_tf_kw, "isolated_at": isolated_at,
            "grants": grants, "stats": stats, "ctl": None, "devs": devs, "silent": None,
            "runtime": {"parts": parts, "wids": wids, "leases": grants_log, "lease_log": leases.log, "kill": kill_info,
                        "takeovers": takeovers, "late": late_info, "holder": holder, "reasons": reasons,
                        "counter": counter, "part_target": part_target, "part_delivered": part_delivered,
                        "wall": wall, "missed": dict(getattr(transport, "missed", {})),
                        "quarantine": quarantine_log}}
