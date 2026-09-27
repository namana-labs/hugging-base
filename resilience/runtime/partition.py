"""Transformer groups (PARTITION_RULE) and the coordinator's split of the fleet target across them (SHARE_RULE).

The split is the coordinator's only dispatch decision and it is deterministic arithmetic. Inside a group, the worker
runs sim.orchestrator's Controller and allocate() unchanged.
"""
import numpy as np

from sim.caps import transformer_caps
from sim.constants import AWARE_MARGIN
from sim.devices import charge_limit, discharge_limit
from sim.orchestrator import charge_target


def partitions(tf_of_batt, n):
    """[{id, tfs, batts}]: the fleet's transformers in index order, cut into n contiguous groups of about equal battery
    count. A transformer is never split, so every battery on one transformer has one worker."""
    tf = np.asarray(tf_of_batt, dtype=np.int64)
    tfs = sorted({int(t) for t in tf})
    count = {t: int((tf == t).sum()) for t in tfs}
    total = sum(count.values())
    groups = [[] for _ in range(n)]
    cum = 0
    for t in tfs:
        g = min(n - 1, int((cum + count[t] / 2) * n // total))
        groups[g].append(t)
        cum += count[t]
    if any(not g for g in groups):
        raise ValueError(f"PARTITION_RULE left an empty group: {[len(g) for g in groups]}")
    out = []
    for p, g in enumerate(groups):
        members = set(g)
        out.append({"id": f"G{p + 1}", "tfs": g, "batts": [i for i in range(len(tf)) if int(tf[i]) in members]})
    return out


def split_target(mode, target_kw, parts, served, telemetry_kw, soc_t, soc, pmax, emax, rte, tf_of_batt,
                 bg_kw, bg_kvar, kva, dt_h, minutes_left, heard, alpha=AWARE_MARGIN):
    """{partition id: kW share}.

    served[pid]  the group's worker heartbeated at the previous step (or was granted the lease this step);
    soc_t        the SoC the fleet target was computed from (P1: 1.0 for a unit the controller cannot count on);
    heard        the units that can act this step (not islanded, not quarantined): only those add headroom or discharge;
    telemetry_kw the kW each battery reported last step. An unserved group keeps acting on its last commands, so it is
                 booked at its telemetry, and the served groups cover the rest.

    charge:    each served group gets min(its own batteries' charge target, its headroom), where headroom sums, per
               transformer, min(H, the batteries' charge limits); what is left goes to groups with room left, in
               proportion to that room.
    discharge: each served group gets its own heard batteries' discharge limits (the P1 target is every heard unit at
               its limit), so no redistribution.
    """
    shares = {p["id"]: 0.0 for p in parts}
    if mode == "idle":
        return shares
    tf = np.asarray(tf_of_batt, dtype=np.int64)
    booked = {p["id"]: float(sum(telemetry_kw[i] for i in p["batts"])) for p in parts if not served[p["id"]]}
    if mode == "discharge":
        for p in parts:
            if served[p["id"]]:
                shares[p["id"]] = -float(sum(discharge_limit(soc[i], emax[i], pmax[i], rte[i], dt_h)
                                             for i in p["batts"] if heard[i]))
        return shares
    H, _, _ = transformer_caps(bg_kw, bg_kvar, kva, alpha)
    # a unit that cannot act (islanded, or held at zero by a quarantine) adds nothing to its group's headroom
    lc = np.array([charge_limit(soc[i], emax[i], pmax[i], rte[i], dt_h) if heard[i] else 0.0 for i in range(len(tf))])
    need, cap = {}, {}
    for p in parts:
        b = np.asarray(p["batts"], dtype=np.int64)
        need[p["id"]] = charge_target(soc_t[b], emax[b], rte[b], minutes_left)
        per_tf = np.bincount(tf[b], weights=lc[b], minlength=len(H))
        cap[p["id"]] = float(sum(min(max(float(H[t]), 0.0), float(per_tf[t])) for t in p["tfs"]))
    live = [p["id"] for p in parts if served[p["id"]]]
    for pid in live:
        shares[pid] = min(need[pid], cap[pid])
    left = max(0.0, float(target_kw)) - sum(shares[pid] for pid in live) - sum(booked.values())
    spare = {pid: cap[pid] - shares[pid] for pid in live}
    room = sum(spare.values())
    if left > 0 and room > 0:
        f = min(1.0, left / room)
        for pid in live:
            shares[pid] += spare[pid] * f
    return shares
