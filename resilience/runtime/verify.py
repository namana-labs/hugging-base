"""Verify the worker-kill replay (house style of sim.verify_p1: [INVARIANT] lines gate, [EXPECT] lines never do).

    python -m resilience.runtime.verify              # the committed replay and fixture, no rebuild
    python -m resilience.runtime.verify --rebuild    # also rebuilds into a temp dir and byte-compares (about 2 min)

Ends with one line: "VERIFY runtime: PASS (k expectations refuted)" or "VERIFY runtime: FAIL (<invariants>)". Where it
can, it re-derives a claim from the arrays instead of trusting the summary the build wrote.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sim import contracts
from sim.constants import DATA_FILE_CAP_MB

from resilience.constants import LEASE_TTL_S, RUNTIME_CONSTANTS, RUNTIME_TRACKING_PCT
from .build import FIXTURES, LIVE_OUT, OUT, PRODUCER, REL, ROOT

KNOWN_PRODUCER_GAP = (f"envelope: producer '{PRODUCER}' is not sim.<module> or scripts.<name>")


class V:
    def __init__(self):
        self.failed = []
        self.refuted = []

    def inv(self, ok, name, text):
        print(f"[INVARIANT: {'ok' if ok else 'FAIL'}] {text}")
        if not ok:
            self.failed.append(name)

    def exp(self, ok, name, text):
        print(f"[EXPECT] {text}: {'ok' if ok else 'REFUTED'}")
        if not ok:
            self.refuted.append(name)


def v(x):
    return x["v"] if isinstance(x, dict) else x


def contract_errors(doc, rel=REL):
    """sim.contracts' own checks (envelope, labels, shapes, size), less the one known gap: PRODUCER_RE admits only
    sim.* and scripts.*, so 'resilience.runtime' fails it until the lead widens it (resilience/docs/requests.md)."""
    errs = [e for e in contracts.check_envelope(doc) if e != KNOWN_PRODUCER_GAP]
    le, n = contracts.audit_labels(doc)
    errs += le + contracts.check_shapes(rel, doc)
    size = len(contracts.dumps(doc).encode())
    if size > DATA_FILE_CAP_MB * 1024 * 1024:
        errs.append(f"size {size} > {DATA_FILE_CAP_MB} MB")
    return errs, n, size


def check_replay(chk, doc, label):
    s = doc["summary"]
    rt = doc["runtime"]
    n = doc["steps"]
    errs, nlab, size = contract_errors(doc)
    chk.inv(not errs, "contract", f"{label}: sim.contracts envelope, labels, shapes, size ({nlab} labelled numbers, "
            f"{size / 1024:.0f} KB){'' if not errs else ': ' + '; '.join(errs[:4])} "
            f"[producer '{doc['producer']}' needs the PRODUCER_RE request]")
    chk.inv(all(k in doc["constants"] for k in RUNTIME_CONSTANTS), "constants",
            f"{label}: the envelope exports every runtime constant ({len(RUNTIME_CONSTANTS)})")
    shapes = (len(rt["holder"]) == n and all(len(h) == len(rt["partitions"]) for h in rt["holder"])
              and len(rt["partitionTargetKW"]) == n and len(rt["partitionDeliveredKW"]) == n
              and len(rt["baseline"]["deliveredKW"]) == n)
    chk.inv(shapes, "shape", f"{label}: runtime arrays have {n} steps x {len(rt['partitions'])} groups")
    # re-derived from the arrays
    bat = doc["batKW"]
    dsum = max(abs(sum(bat[k]) - doc["deliveredKW"][k]) for k in range(n))
    chk.inv(dsum <= len(bat[0]) // 2, "delivered", f"{label}: deliveredKW = sum of batKW every step (max rounding gap {dsum} tenths)")
    psum = max(abs(sum(rt["partitionDeliveredKW"][k]) - doc["deliveredKW"][k]) for k in range(n))
    chk.inv(psum <= len(rt["partitions"]), "groups", f"{label}: the groups' delivered kW add up to the fleet's (max gap {psum} tenths)")
    low = sum(1 for k in range(n) for i, x in enumerate(doc["soc"][k]) if x < 200 and doc["state"][k][i] != "B")
    chk.inv(low == 0 and v(s["reserveBreaches"]) == 0, "reserve",
            f"{label}: 20% reserve holds at every step (re-derived from soc: {low} battery-steps below 200 per mille)")
    xk = sum(1 for k in range(n) for i, c in enumerate(doc["state"][k]) if c == "X" and doc["batKW"][k][i] != 0)
    chk.inv(xk == 0 and v(s["actedAfterExpiry"]) == 0 and v(s["nonIncreasingAccepted"]) == 0, "expiry",
            f"{label}: no battery acts on an expired command ({xk}); no out-of-order command accepted")
    prot = sum(t.count("5") for t in doc["tier"])
    chk.inv(v(s["batteryCausedNormal"]) == 0 and v(s["batteryCausedEmergency"]) == 0 and prot == 0
            and v(s["protectionOperated"]) == 0, "tiers",
            f"{label}: OpenDSS: no battery-caused normal or emergency event, no protection operated "
            f"(max loading {v(s['maxLoading'])}% at {s['maxLoading']['t']})")
    kill, late = rt["kill"], rt["late"]
    tks = [t for t in rt["takeover"] if t["partition"] in kill["groups"]]
    chk.inv(bool(tks) and v(s["takeoverSeconds"]) <= LEASE_TTL_S
            and (tks[0]["step"] - kill["step"]) * 60 == v(s["takeoverSeconds"]), "takeover",
            f"{label}: the lease moves within one interval: {kill['worker']} killed {kill['t']}, "
            f"{tks[0]['worker'] if tks else '?'} takes {', '.join(kill['groups'])} at {tks[0]['t'] if tks else '?'} "
            f"({v(s['takeoverSeconds'])} s <= {LEASE_TTL_S} s)")
    dead = kill["worker"][1:]
    after = [k for k in range(kill["step"], n) if dead in rt["holder"][k]]
    chk.inv(not after, "dead", f"{label}: the killed worker commands nothing after the kill (holder strings)")
    gap = [k for k in range(kill["step"] + 1, tks[0]["step"]) if "-" not in rt["holder"][k]] if tks else [0]
    chk.inv(not gap, "gap", f"{label}: its group is marked unserved from the step after the kill to the takeover")
    chk.inv(late["commands"] > 0 and late["withPower"] > 0 and late["unexpiredOnArrival"] == late["commands"]
            and late["rejected"]["staleEpoch"] == late["commands"] and v(s["rejectedStaleEpoch"]) >= late["commands"],
            "late", f"{label}: all {late['commands']} late commands ({late['withPower']} carrying power, all unexpired on "
                    f"arrival) are refused for a stale epoch alone")
    chk.inv(v(s["killCostPct"]) is not None and v(s["killCostPct"]) <= RUNTIME_TRACKING_PCT, "tracking",
            f"{label}: from the kill to one interval after the takeover, the kill moves delivered power by at most "
            f"{v(s['killCostMaxKW'])} kW ({v(s['killCostPct'])}% of target) <= RUNTIME_TRACKING_PCT {RUNTIME_TRACKING_PCT}%")
    out = rt["baseline"].get("outcome", {})
    energy = sum(doc["deliveredKW"]) / 10 / 60
    chk.exp(v(s["chargedPctBy0400"]) == out.get("chargedPctBy0400") and abs(v(s["killCostKWh"])) <= 0.01 * energy,
            f"{label}:outcome", f"{label}: the night's outcome is unchanged by the kill: charged "
            f"{v(s['chargedPctBy0400'])}% (no kill {out.get('chargedPctBy0400')}%), energy short "
            f"{v(s['killCostKWh'])} kWh of {energy:.0f}; the runs drift apart by up to {v(s['divergenceMaxKW'])} kW at "
            f"{s['divergenceMaxKW']['t']} (different allocation paths after the takeover)")
    chk.exp(v(s["trackingMaxErrPct"]) is not None and v(s["trackingMaxErrPct"]) <= 15.0, f"{label}:design-tol",
            f"{label}: tracking through the gap inside the design's max(2 MW, 15%): {v(s['trackingMaxErrKW'])} kW, "
            f"{v(s['trackingMaxErrPct'])}% (no-kill run, same minutes: {v(s['baselineMaxErrPct'])}%)")
    chk.exp(v(s["seqOnlyLateAccepted"]) > 0 and v(s["seqOnlyTakeoverRejected"]) > 0, f"{label}:counterfactual",
            f"{label}: why the epoch: seq-only devices would accept {v(s['seqOnlyLateAccepted'])} late commands and "
            f"refuse {v(s['seqOnlyTakeoverRejected'])} of the new holder's")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    chk = V()
    path = OUT / REL
    if not path.exists():
        print(f"VERIFY runtime: SKIP ({path.relative_to(ROOT)} not built: python -m resilience.runtime.build)")
        return 0
    doc = json.loads(path.read_text())
    rt = doc["runtime"]
    print(f"runtime {doc['steps']} steps | groups {', '.join(p['id'] + '=' + '/'.join(p['focus']) for p in rt['partitions'])} "
          f"| workers {', '.join(rt['workers'])} | Tc {rt['tc']['t']} | kill {rt['kill']['t']} ({rt['kill']['worker']})")
    check_replay(chk, doc, "replay")
    # the no-failure run against committed P1 aware (the runtime split should not cost P1's outcome)
    aware_p = ROOT / "ui" / "data" / "p1" / "aware.json"
    if aware_p.exists():
        aware = json.loads(aware_p.read_text())
        base = rt["baseline"]["deliveredKW"]
        if len(aware["deliveredKW"]) == len(base):
            e_a, e_b = sum(aware["deliveredKW"]), sum(base)
            dmax = max(abs(a - b) for a, b in zip(aware["deliveredKW"], base)) / 10
            share = abs(e_b - e_a) / max(abs(e_a), 1) * 100
            chk.exp(share <= 1.0, "vs-aware", f"no-kill runtime vs one-controller P1 aware: delivered energy differs by "
                    f"{share:.2f}% (max {dmax:.1f} kW in one minute)")
    # the fixture
    fx = FIXTURES / REL
    if fx.exists():
        fdoc = json.loads(fx.read_text())
        chk.inv(fdoc.get("fixture") is True and str(fdoc["inputs"]["loads_sha256"]).startswith("fixture:"), "fixture",
                f"fixture {fx.relative_to(ROOT)}: fixture: true, synthetic loads named in inputs")
        check_replay(chk, fdoc, "fixture")
    else:
        chk.inv(False, "fixture", "fixture missing: python -m resilience.runtime.build --fixture")
    # a live recording, when one exists (never committed)
    lp = LIVE_OUT / REL
    if lp.exists():
        ldoc = json.loads(lp.read_text())
        rec = ldoc.get("recorded", {})
        same = ldoc["batKW"] == doc["batKW"] and ldoc["runtime"]["holder"] == rt["holder"]
        chk.exp(same, "live=replay", f"live recording ({rec.get('platform')}, pids {rec.get('pids')}, killed "
                f"{(rec.get('killed') or {}).get('worker')} exit {(rec.get('killed') or {}).get('exitcode')}): "
                f"{rec.get('wallSecondsKillToTakeover')} s wall from kill to takeover; missed heartbeats "
                f"{rec.get('missedHeartbeats')}; arrays equal to the replay")
    # determinism
    if "--rebuild" in argv:
        with tempfile.TemporaryDirectory(prefix="runtime-rebuild-") as tmp:
            r = subprocess.run([sys.executable, "-m", "resilience.runtime.build", "--out", tmp], cwd=ROOT,
                               capture_output=True, text=True)
            same = r.returncode == 0 and (Path(tmp) / REL).read_bytes() == path.read_bytes()
            chk.inv(same, "determinism", f"determinism: rebuild {'byte-identical' if same else 'DIFFERS'}"
                    + ("" if r.returncode == 0 else f" (build exit {r.returncode}: {r.stderr.strip()[-200:]})"))
    else:
        print("determinism: not checked (run --rebuild)")
    if chk.failed:
        print(f"VERIFY runtime: FAIL ({', '.join(chk.failed)})")
        return 1
    print(f"VERIFY runtime: PASS ({len(chk.refuted)} expectations refuted{': ' + ', '.join(chk.refuted) if chk.refuted else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
