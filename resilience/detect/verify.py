"""Verify the covert-channel replay ([INVARIANT] lines gate, [EXPECT] lines never do).

    python -m resilience.detect.verify              # the committed replay and fixture
    python -m resilience.detect.verify --rebuild    # also rebuilds into a temp dir and byte-compares (about 2 min)

Ends with "VERIFY covert: PASS (k expectations refuted)" or "VERIFY covert: FAIL (<invariants>)".
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from resilience.constants import COVERT_CONSTANTS, RUNTIME_TRACKING_PCT
from resilience.runtime.verify import V, contract_errors, v
from .build import FIXTURES, OUT, PRODUCER, REL, ROOT

KNOWN_GAP = f"envelope: producer '{PRODUCER}' is not sim.<module> or scripts.<name>"


def check(chk, doc, label):
    s = doc["summary"]
    from sim import contracts
    errs = [e for e in contracts.check_envelope(doc) if e != KNOWN_GAP]
    le, n = contracts.audit_labels(doc)
    errs += le
    chk.inv(not errs, "contract", f"{label}: sim.contracts envelope and labels ({n} labelled numbers)"
            f"{'' if not errs else ': ' + '; '.join(errs[:4])} [producer '{doc['producer']}' needs the PRODUCER_RE request]")
    chk.inv(all(k in doc["constants"] for k in COVERT_CONSTANTS), "constants", f"{label}: every covert constant exported")
    chk.inv("fictional" in doc["sources"]["adversary"]["text"], "fictional", f"{label}: the adversary is labelled fictional")
    chk.inv(v(s["falsePositivesClean"]) == 0, "fp-clean",
            f"{label}: zero false positives on the clean fleet ({doc['window']['steps']} minutes x 96 units)")
    chk.inv(v(s["falsePositivesAttack"]) == 0, "fp-attack", f"{label}: no clean unit flagged while the attack runs")
    chk.inv(v(s["detected"]) == v(s["shard"]) and v(s["detectionSeconds"]) is not None, "detect",
            f"{label}: every compromised unit flagged ({v(s['detected'])}/{v(s['shard'])}), first in "
            f"{v(s['detectionSeconds'])} s, all in {v(s['allDetectedSeconds'])} s")
    qc = [u for u in doc["units"] if u["quarantinedStep"] is not None]
    chk.inv(all(u["compromised"] for u in qc) and v(s["quarantinedCompromised"]) == v(s["quarantined"]), "quarantine",
            f"{label}: every held unit is compromised ({v(s['quarantined'])} held)")
    chk.inv(v(s["reserveBreaches"]) == 0 and v(s["batteryCausedNormal"]) == 0, "safety",
            f"{label}: 20% reserve and no battery-caused normal-tier event in all three runs")
    chk.inv(v(s["trackingMaxErrPctQuarantine"]) is not None and v(s["trackingMaxErrPctQuarantine"]) <= RUNTIME_TRACKING_PCT,
            "tracking", f"{label}: the fleet re-covers under quarantine: tracking within {v(s['trackingMaxErrPctQuarantine'])}% "
                        f"<= {RUNTIME_TRACKING_PCT}% (watching only: {v(s['trackingMaxErrPctObserve'])}%; clean: "
                        f"{v(s['trackingMaxErrPctClean'])}%)")
    chk.exp(v(s["fixedThresholdCompromised"]) == 0, f"{label}:naive",
            f"{label}: a naive 1 kW threshold misses the channel ({v(s['fixedThresholdCompromised'])} caught, "
            f"{v(s['fixedThresholdClean'])} clean units it would flag)")
    chk.exp(v(s["channelOverFloor"]) is not None and v(s["channelOverFloor"]) > 3 and v(s["channelSNR"]) > 3, f"{label}:channel",
            f"{label}: the channel is physically real: carrier {v(s['channelVoltagePU'])} pu at the shard's transformers' homes, "
            f"{v(s['channelOverFloor'])} x the same homes without the attack ({v(s['channelFloorPU'])} pu) and "
            f"{v(s['channelSNR'])} x the assumed voltage noise")
    agg = s["aggregateOffsetKW"]
    chk.exp(v(agg["targetPct"]) is not None and v(agg["targetPct"]) <= RUNTIME_TRACKING_PCT, f"{label}:inside-tolerance",
            f"{label}: the hidden offset stays inside the fleet's tolerance: at most {v(agg)} kW across the shard, "
            f"{v(agg['targetPct'])}% of the target at {agg['t']}")
    wid = [u for u in doc["units"] if u["compromised"]]
    chk.exp(True, f"{label}:peers", f"{label}: peer rule: {sum(u['peerRule'] == 'widened' for u in wid)} of {len(wid)} "
            f"compromised homes need peers beyond their own transformer; peer ratio at flag (recorded, not gating) "
            f"median {sorted(u['atFlag']['peerRatio'] or 0 for u in wid if 'atFlag' in u)[len(wid) // 2] if wid else None}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    chk = V()
    path = OUT / REL
    if not path.exists():
        print("VERIFY covert: SKIP (not built: python -m resilience.detect.build)")
        return 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    print(f"covert {doc['window']['day']} {doc['window']['start']} + {doc['window']['steps']} min | attack {doc['attack']['t']} "
          f"on {len(doc['attack']['shard'])} units over {len(doc['attack']['tfs'])} transformers")
    check(chk, doc, "replay")
    fx = FIXTURES / REL
    if fx.exists():
        fdoc = json.loads(fx.read_text(encoding="utf-8"))
        chk.inv(fdoc.get("fixture") is True and str(fdoc["inputs"]["loads_sha256"]).startswith("fixture:"), "fixture",
                f"fixture {fx.relative_to(ROOT)}: fixture: true, synthetic loads named in inputs")
        check(chk, fdoc, "fixture")
    else:
        chk.inv(False, "fixture", "fixture missing: python -m resilience.detect.build --fixture")
    if "--rebuild" in argv:
        with tempfile.TemporaryDirectory(prefix="covert-rebuild-") as tmp:
            r = subprocess.run([sys.executable, "-m", "resilience.detect.build", "--out", tmp], cwd=ROOT,
                               capture_output=True, text=True)
            same = r.returncode == 0 and (Path(tmp) / REL).read_bytes() == path.read_bytes()
            chk.inv(same, "determinism", f"determinism: rebuild {'byte-identical' if same else 'DIFFERS'}"
                    + ("" if r.returncode == 0 else f" (build exit {r.returncode}: {r.stderr.strip()[-200:]})"))
    else:
        print("determinism: not checked (run --rebuild)")
    if chk.failed:
        print(f"VERIFY covert: FAIL ({', '.join(chk.failed)})")
        return 1
    print(f"VERIFY covert: PASS ({len(chk.refuted)} expectations refuted{': ' + ', '.join(chk.refuted) if chk.refuted else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
