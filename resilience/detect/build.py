"""Build the covert-channel replay on the root feeder (deliverable D; milestone M6').

    python -m resilience.detect.build             # the P1 evening, 720 x 60 s: resilience/out/p3/covert.json
    python -m resilience.detect.build --fixture   # 120 steps, synthetic loads: resilience/fixtures/p3/covert.json
    python -m resilience.detect.build --quick     # 60 steps from 22:00, real loads, to ~/hb-overnight/tmp/covert-quick
    python -m resilience.detect.build --out DIR

Three runs of the same evening under the runtime (no worker failure), OpenDSS every step:
  clean       no attack, the detector watching: every flag is a false positive on the clean fleet;
  observe     the fictional adversary's carrier on COVERT_SHARD from Tc + COVERT_AFTER_MIN, the detector watching;
  quarantine  the same attack, each flagged unit held at zero from the next minute and cut from the fleet target.
The detector's noise is seeded identically in the three runs, so the runs differ only by the attack and the response.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from sim.constants import export, COMMAND_TTL_S, MIN_GRANT_KW, P1_STEP_SECONDS
from sim.contracts import envelope, inputs_sha, labelled, write_json
from sim.fixtures import LOADS_TAG
from sim.p1_build import Scenario, hhmm, summarize

from resilience.constants import (CHANNEL_SPAN_MIN, COVERT_AFTER_MIN, COVERT_CONSTANTS, COVERT_SEED, COVERT_SYMBOL_MIN,
                                 MODULATION_KW, VOLTAGE_NOISE_PU)
from resilience.runtime import engine
from resilience.runtime.build import first_charge_step, loads_for, window
from resilience.runtime.device import EpochDevice
from resilience.runtime.partition import partitions

from .attack import Carrier, CompromisedDevice, message_bits
from .detector import PeerDetector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "resilience" / "out"
FIXTURES = ROOT / "resilience" / "fixtures"
QUICK_OUT = Path.home() / "hb-overnight" / "tmp" / "covert-quick"
REL = "p3/covert.json"
PRODUCER = "resilience.detect"
TRACE_BEFORE, TRACE_AFTER = 10, 50
CURVE_MINUTES = list(range(0, 65, 5))


def shard_of(sc):
    dense = set(json.loads((ROOT / "data" / "fleet.json").read_text(encoding="utf-8"))["shaping"]["denseHomes"])
    return [i for i, hid in enumerate(sc.ids) if hid in dense]


def run3(sc, topo, shard):
    parts = partitions(sc.tf_of_batt, len(engine.worker_ids()))
    static = engine.static_of(sc, parts)
    det = lambda: PeerDetector(sc.fleet, topo["homes"], topo["transformers"], [COVERT_SEED, 2])
    d0 = det()
    clean = engine.run(sc, engine.InProcess(static, engine.worker_ids()), observer=d0.observe)
    tc = first_charge_step(sc, clean)
    if tc is None:
        raise SystemExit("no charge grant in this window: no legitimate activity to hide in")
    a = tc + COVERT_AFTER_MIN
    if a + 20 >= sc.win.steps:
        raise SystemExit("window too short for the attack")
    bits = message_bits((sc.win.steps - a) // COVERT_SYMBOL_MIN + 1)
    carrier = Carrier(a * P1_STEP_SECONDS, bits)
    members = set(shard)
    factory = lambda i, b: CompromisedDevice(b, carrier=carrier) if i in members else EpochDevice(b)
    d1 = det()
    observe = engine.run(sc, engine.InProcess(static, engine.worker_ids()), device_factory=factory, observer=d1.observe)
    d2 = det()
    quar = engine.run(sc, engine.InProcess(static, engine.worker_ids()), device_factory=factory, observer=d2.quarantine)
    return {"clean": (clean, d0), "observe": (observe, d1), "quarantine": (quar, d2), "tc": tc, "a": a, "bits": bits,
            "carrier": carrier}


def pct(x, of):
    return round(float(x) / abs(float(of)) * 100, 2) if abs(float(of)) >= MIN_GRANT_KW else None


def assemble(sc, topo, shard, R, fixture=False):
    win = sc.win
    tc, a = R["tc"], R["a"]
    clean, d0 = R["clean"]
    obs, d1 = R["observe"]
    quar, d2 = R["quarantine"]
    members = set(shard)
    m = sc.m
    fp_clean = sorted(d0.first)
    flagged = sorted(d1.first)
    caught = [i for i in flagged if i in members]
    fp_attack = [i for i in flagged if i not in members]
    first = min((d1.first[i] for i in caught), default=None)
    last = max((d1.first[i] for i in caught), default=None) if len(caught) == len(shard) else None
    # the channel: the carrier at every home on the shard's transformers (transmitters and their neighbours), over the
    # attack's first CHANNEL_SPAN_MIN minutes, quiet windows only, with the attack (observe) and without it (clean): a
    # simulation reference that the detector never reads
    homes = sorted({int(h) for i in shard for h in sc.feeder.transformers[int(sc.tf_of_batt[i])]["homes"]})
    e_ch = min(win.steps, a + CHANNEL_SPAN_MIN)

    def channel(d):
        V, SP = np.array(d.v[a:e_ch]), np.array(d.sp[a:e_ch])
        amps = [x for x in (d.home_amp(h, V, SP) for h in homes) if x is not None]
        return float(np.median(amps)) if amps else None
    chan, floor = channel(d1), channel(d0)
    # the hidden offset itself: sum over the shard of (kW - setpoint), exact, while the attack runs unanswered
    off = (obs["batkw"][a:, shard] - np.array(d1.sp[a:])[:, shard]).sum(axis=1)
    jo = int(np.argmax(np.abs(off)))
    # the fleet through the episode: from the channel opening to one command interval after the last unit is flagged
    # (observe) or held (quarantine); after that the runs differ only by their allocation paths (as in the runtime)
    qlog = quar["runtime"]["quarantine"]
    ends = [k for k in (last, max((k for k, _ in qlog), default=None)) if k is not None]
    end = min(win.steps, (max(ends) if ends else win.steps) + COMMAND_TTL_S // P1_STEP_SECONDS + 1)

    def track(run):
        t, d = run["target"][a:end], run["batkw"][a:end].sum(axis=1)
        e = np.abs(t - d)
        j = int(np.argmax(e))
        return e[j], t[j], a + j
    e1, t1, j1 = track(obs)
    e2, t2, j2 = track(quar)
    e0, t0_, j0 = track(clean)
    s_obs, _ = summarize(sc, obs)
    s_q, _ = summarize(sc, quar)
    s_c, _ = summarize(sc, clean)
    det_s = None if first is None else (first - a + 1) * P1_STEP_SECONDS
    summary = {
        "shard": labelled(len(shard), "ASSUMPTION", "COVERT_SHARD: the dense-cohort Cores (fictional adversary)"),
        "falsePositivesClean": labelled(len(fp_clean), "SIM", f"units flagged on the clean fleet, all {win.steps} minutes x {m} units"),
        "detected": labelled(len(caught), "SIM", f"compromised units flagged (of {len(shard)})"),
        "falsePositivesAttack": labelled(len(fp_attack), "SIM", "clean units flagged while the attack runs"),
        "detectionSeconds": labelled(det_s, "SIM", "channel open to the first compromised unit flagged (the minute it is flagged counts)"),
        "allDetectedSeconds": labelled(None if last is None else (last - a + 1) * P1_STEP_SECONDS, "SIM",
                                       "channel open to the last compromised unit flagged"),
        "fixedThresholdClean": labelled(len(d0.fixed), "SIM", "clean-fleet units a naive |residual| > 1 kW rule would flag (FIXED_THRESHOLD_KW)"),
        "fixedThresholdCompromised": labelled(sum(1 for i in shard if i in d1.fixed), "SIM", "compromised units the naive rule catches"),
        "channelVoltagePU": labelled(None if chan is None else round(chan, 7), "SIM",
                                     f"the carrier in the voltage at the {len(homes)} homes on the shard's transformers, attack's "
                                     f"first {CHANNEL_SPAN_MIN} min, quiet windows, median (a simulation reference; the detector never reads it)"),
        "channelFloorPU": labelled(None if floor is None else round(floor, 7), "SIM", "the same homes and minutes without the attack"),
        "channelSNR": labelled(None if chan is None else round(chan / VOLTAGE_NOISE_PU, 1), "DERIVED", "channelVoltagePU / VOLTAGE_NOISE_PU"),
        "channelOverFloor": labelled(None if not (chan and floor) else round(chan / floor, 1), "DERIVED", "channelVoltagePU / channelFloorPU"),
        "aggregateOffsetKW": labelled(round(float(abs(off[jo])), 2), "SIM",
                                      "largest shard-wide hidden offset, sum of (kW - setpoint) over the compromised units, detector only watching",
                                      t=hhmm(win.time(a + jo)), targetPct=labelled(pct(abs(off[jo]), obs["target"][a + jo]), "DERIVED",
                                                                                  "as a share of that minute's fleet target")),
        "trackingMaxErrPctObserve": labelled(pct(e1, t1), "DERIVED", f"largest |fleet target - delivered|, {hhmm(win.time(a))} to "
                                             f"{hhmm(win.time(end - 1))} (the attack to one command interval after the last flag), detector only watching",
                                             kw=round(float(e1), 2), t=hhmm(win.time(j1))),
        "trackingMaxErrPctQuarantine": labelled(pct(e2, t2), "DERIVED", "the same minutes, every flagged unit held at zero and cut from the target",
                                                kw=round(float(e2), 2), t=hhmm(win.time(j2))),
        "trackingMaxErrPctClean": labelled(pct(e0, t0_), "DERIVED", "the same minutes on the clean run",
                                           kw=round(float(e0), 2), t=hhmm(win.time(j0))),
        "quarantined": labelled(len(qlog), "SIM", "units held at zero by the response run"),
        "quarantinedCompromised": labelled(sum(1 for _, i in qlog if i in members), "SIM", "of those, compromised"),
        "reserveBreaches": labelled(max(s_obs["reserveBreaches"]["v"], s_q["reserveBreaches"]["v"], s_c["reserveBreaches"]["v"]),
                                    "SIM", "battery-steps below the 20% reserve, worst of the three runs"),
        "batteryCausedNormal": labelled(max(s_obs["batteryCausedNormal"]["v"], s_q["batteryCausedNormal"]["v"], s_c["batteryCausedNormal"]["v"]),
                                        "SIM", "OpenDSS battery-caused normal-tier events, worst of the three runs"),
        "maxLoading": labelled(max(s_obs["maxLoading"]["v"], s_q["maxLoading"]["v"]), "SIM", "OpenDSS, attack runs"),
    }
    units = []
    for i in range(m):
        h = int(sc.fleet[i])
        p, rule = d1.peers[i]
        u = {"batt": i, "home": h, "tf": int(sc.tf_of_batt[i]), "compromised": i in members, "peers": len(p), "peerRule": rule,
             "flaggedStep": d1.first.get(i), "flaggedClean": d0.first.get(i), "quarantinedStep": d2.first.get(i)}
        if i in d1.at_flag:
            u["atFlag"] = d1.at_flag[i]
        if i in members or i in d1.first or i in d0.first:
            units.append(u)
    k0, k1 = max(0, a - TRACE_BEFORE), min(win.steps, a + TRACE_AFTER)
    peers_clean = [i for i in range(m) if i not in members][:3]
    trace_units = shard[:3] + peers_clean
    per_min = {"steps": [k0, k1], "units": trace_units,
               "residualW": [[int(round(float(d1.r[k][i]) * 1000)) for k in range(k0, k1)] for i in trace_units],
               "vMicroPU": [[None if not np.isfinite(d1.v[k][int(sc.fleet[i])]) else
                             int(round((float(d1.v[k][int(sc.fleet[i])]) - float(d1.v[k0][int(sc.fleet[i])])) * 1e6))
                             for k in range(k0, k1)] for i in trace_units]}
    ttd = [det_s // 60] if det_s is not None else []
    curve = {"minutes": CURVE_MINUTES,
             "bits": [mm // COVERT_SYMBOL_MIN for mm in CURVE_MINUTES],
             "modulatedKWh": [round(len(shard) * MODULATION_KW * mm / 60, 3) for mm in CURVE_MINUTES],
             "detectedAtMin": ttd[0] if ttd else None,
             "text": "harm if the channel runs d minutes before quarantine: bits sent (one per symbol) and energy moved "
                     "by the hidden offset across the shard (DERIVED); detectedAtMin is this run's detector"}
    doc = envelope("p3.covert", PRODUCER,
                   inputs=inputs_sha(loads_override=LOADS_TAG) if fixture else inputs_sha(),
                   constants=export("RESERVE_FLOOR", "COMMAND_TTL_S", *COVERT_CONSTANTS),
                   sources={"load": {"label": "SIM", "text": "fixture: sim.fixtures.FixtureLoads, synthetic, not a result" if fixture
                                     else "NREL SMART-DS 2018 AUS P1U, same calendar date; 15->1 min linear (DERIVED)"},
                            "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow, every step, three runs"},
                            "adversary": {"label": "ASSUMPTION", "text": "a fictional adversary; no real company or person"},
                            "detector": {"label": "SIM", "text": "resilience.detect.detector.PeerDetector: telemetry residual size and oscillation, corroborated by the home's own AMI voltage at the carrier frequency; no privileged solve"}},
                   series={"curve": {"label": "DERIVED", "unit": "minutes, bits, kWh"},
                           "trace": {"label": "SIM", "unit": "residual W (reported - setpoint, with telemetry noise); home AMI voltage minus its first value, 1e-6 pu"},
                           "units": {"label": "SIM", "unit": "per-unit detector record"}},
                   fixture=fixture)
    doc.update({
        "window": {"day": win.day, "start": hhmm(win.t0), "steps": win.steps, "stepSeconds": P1_STEP_SECONDS,
                   "tc": {"step": tc, "t": hhmm(win.time(tc))}},
        "attack": {"step": a, "t": hhmm(win.time(a)), "shard": shard, "homes": [int(sc.fleet[i]) for i in shard],
                   "tfs": sorted({int(sc.tf_of_batt[i]) for i in shard}), "bits": R["bits"][:max(1, (win.steps - a) // COVERT_SYMBOL_MIN)],
                   "text": f"a fictional adversary's {len(shard)} Cores add a hidden +-{MODULATION_KW * 1000:.0f} W carrier from "
                           f"{hhmm(win.time(a))}, one bit per {COVERT_SYMBOL_MIN}-minute symbol"},
        "summary": summary,
        "quarantine": {"log": [[k, i, hhmm(win.time(k))] for k, i in qlog]},
        "units": units,
        "trace": per_min,
        "curve": curve,
    })
    return doc


def build(kind="full", out=None, quiet=False):
    t0 = time.time()
    say = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    sc = Scenario(window(kind), loads=loads_for(kind))
    topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text())
    shard = shard_of(sc)
    R = run3(sc, topo, shard)
    doc = assemble(sc, topo, shard, R, fixture=(kind == "fixture"))
    base = Path(out) if out is not None else (FIXTURES if kind == "fixture" else QUICK_OUT if kind == "quick" else OUT)
    path = base / REL
    size = write_json(path, doc)
    s = doc["summary"]
    say(f"  attack {doc['attack']['t']} on {len(shard)} units: detected {s['detected']['v']}/{len(shard)} in "
        f"{s['detectionSeconds']['v']} s (all in {s['allDetectedSeconds']['v']} s); false positives clean "
        f"{s['falsePositivesClean']['v']}, during attack {s['falsePositivesAttack']['v']}; naive 1 kW rule: "
        f"{s['fixedThresholdCompromised']['v']} caught, {s['fixedThresholdClean']['v']} false; channel "
        f"{s['channelVoltagePU']['v']} pu ({s['channelOverFloor']['v']} x floor, SNR {s['channelSNR']['v']}); offset "
        f"{s['aggregateOffsetKW']['v']} kW ({s['aggregateOffsetKW']['targetPct']['v']}%); tracking {s['trackingMaxErrPctObserve']['v']}% / "
        f"{s['trackingMaxErrPctQuarantine']['v']}%; reserve {s['reserveBreaches']['v']}")
    say(f"  wrote {path} ({size / 1024:.0f} KB) in {time.time() - t0:.1f} s")
    return {"doc": doc, "path": path, "R": R, "sc": sc}


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quick", action="store_true")
    g.add_argument("--fixture", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    kind = "quick" if a.quick else ("fixture" if a.fixture else "full")
    print(f"covert build: {kind}", flush=True)
    build(kind, out=a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
