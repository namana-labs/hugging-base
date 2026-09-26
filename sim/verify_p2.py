"""VERIFY p2 (build prompt 7.4; lane L3): reads the committed ui/data/p2/*, data/out/siting-2026-08.csv and
data/out/referee-2026-08.json, and prints 7.4's lines.

    python -m sim.verify p2              # committed JSON only; "determinism: not checked (run --full)"
    python -m sim.verify p2 --rebuild    # heavy (the caller holds the lock): rebuild p2 + referee, byte-compare

[INVARIANT] lines gate; [EXPECT] lines print `ok <measured>` or `REFUTED: <measured>` and never gate (3.5);
[report] lines only print. Ends "VERIFY p2: PASS (k expectations refuted, see NOTES.md)" or "VERIFY p2: FAIL (...)".
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P2 = ROOT / "ui" / "data" / "p2"
CSV_PATH = ROOT / "data" / "out" / "siting-2026-08.csv"
REF_PATH = ROOT / "data" / "out" / "referee-2026-08.json"

# build prompt 4.3's table, measured on the committed CSV (day -> onset ts, price, mode)
ONSET_TABLE = {"2026-08-23": ("2026-08-23T22:00", 55.42, "binding"),
               "2026-08-22": ("2026-08-23T01:45", 50.54, "binding"),
               "2026-08-10": ("2026-08-10T19:45", 29.40, "non-binding"),
               "2026-08-14": ("2026-08-14T19:00", 28.56, "non-binding"),
               "2026-08-15": ("2026-08-15T20:00", 41.21, "non-binding"),
               "2026-08-21": ("2026-08-21T19:00", 47.90, "non-binding"),
               "2026-08-28": ("2026-08-28T19:00", 37.13, "non-binding")}
NON_BINDING = {"2026-08-10", "2026-08-14", "2026-08-15", "2026-08-21", "2026-08-28"}


class V:
    def __init__(self):
        self.fail = []
        self.refuted = []

    def inv(self, ok, name, text):
        print(f"{text}   [INVARIANT{'' if ok else ': FAIL'}]")
        if not ok:
            self.fail.append(name)

    def exp(self, ok, text, what):
        print(f"{text}   [EXPECT: {what}] {'ok' if ok else 'REFUTED'}")
        if not ok:
            self.refuted.append(text.strip())


def load(name):
    return json.loads((P2 / name).read_text())


def v(x):
    return x["v"] if isinstance(x, dict) and "v" in x else x


def main(argv):
    rebuild = "--rebuild" in argv
    chk = V()
    before = None
    if rebuild:
        before = snapshot()
        from . import referee
        print("rebuild: sim.referee (16 combos + useful capacity + 6 OpenDSS months + re-merge) ...")
        referee.run(out=lambda s: None)
    idx = load("index.json")
    combos = {c: load(f"{c}.json") for c in idx["combos"]}
    topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text())
    labels = [h["label"] for h in topo["homes"]]
    fleet_tfs = {topo["homes"][h]["tf"] for h in topo["fleet"]}
    eng = v(idx["engine"]["screenSecondsPerCombo"])
    base = combos[idx["default"]]["baseline"]
    print(f"P2 {idx['month']} | {idx['steps']} x {idx['stepMinutes']} min (+{idx['extraSteps']} steps to 1 Sep 06:00) | "
          f"{len(base['peak'])} tfs | candidates {idx['ties']['of']} | combos {len(idx['combos'])} | "
          f"screen {'%.1f' % eng if eng is not None else 'n/a'} s/combo")

    # onset_d26 ------------------------------------------------------------------------------------------------
    from .prices import onset_d26
    modes = Counter(o["mode"] for o in idx["onsets"])
    nb = [o["day"][5:] for o in idx["onsets"] if o["mode"] == "non-binding"]
    ok = len(idx["onsets"]) == 31
    for o in idx["onsets"]:
        ts, p, _, _, mode = onset_d26(o["day"])
        ok &= (o["onset"] == ts and abs(v(o["price"]) - p) < 1e-9 and o["mode"] == mode)
        if o["day"] in ONSET_TABLE:
            e = ONSET_TABLE[o["day"]]
            ok &= (o["onset"] == e[0] and abs(v(o["price"]) - e[1]) < 0.005 and o["mode"] == e[2])
    ok &= {o["day"] for o in idx["onsets"] if o["mode"] == "non-binding"} == NON_BINDING
    o22 = next(o for o in idx["onsets"] if o["day"] == "2026-08-22")
    chk.inv(ok, "onset_d26", f"onset_d26: {len(idx['onsets'])} days: binding {modes['binding']}, non-binding {modes['non-binding']} "
            f"[{' '.join(nb)}], fallback {modes['fallback']} ; 08-22 -> {o22['onset'][5:10]} {o22['onset'][11:]} ${v(o22['price']):.2f}")

    # cliffs ----------------------------------------------------------------------------------------------------
    from .prices import find_cliffs
    c = find_cliffs()
    cc, ce = v(idx["cliffs"]["count"]), v(idx["cliffs"]["evening"])
    chk.inv(cc == 27 and ce == 13 and cc == len(c) and ce == sum(x["evening"] for x in c), "cliffs",
            f"cliffs: {cc} total, {ce} evening (4.3 rule)")

    # labels ; contract ; csv ---------------------------------------------------------------------------------
    from .contracts import audit_labels, check_envelope, check_shapes
    bad = []
    nlab = 0
    for p in sorted(P2.glob("*.json")):
        doc = json.loads(p.read_text())
        e1, n = audit_labels(doc)
        nlab += n
        bad += [f"{p.name}: {x}" for x in e1 + check_envelope(doc) + check_shapes(f"p2/{p.name}", doc)]
        if doc.get("fixture"):
            bad.append(f"{p.name}: fixture file in ui/data/p2")
    rows = list(csv.reader(CSV_PATH.open())) if CSV_PATH.exists() else []
    hdr = rows[0] if rows else []
    tagged = sum(1 for h in hdr if any(f"[{t}" in h for t in ("REAL", "SIM", "DERIVED", "ASSUMPTION")))
    csv_ok = len(rows) - 1 == idx["ties"]["of"] == 911 and tagged >= 10
    for b in bad[:10]:
        print("    -", b)
    chk.inv(not bad and csv_ok, "labels/contract/csv",
            f"labels ; contract ; csv {CSV_PATH.relative_to(ROOT)} {len(rows) - 1} rows with labelled header "
            f"({len(list(P2.glob('*.json')))} files, {nlab} labelled numbers, {len(bad)} problems, {tagged} labelled columns)")

    # caps parity ------------------------------------------------------------------------------------------------
    from .siting import parity
    worst, n, detail = parity(1000)
    if worst is None:
        print(f"caps parity: PENDING ({detail}; runs once lane L2 merges)   [INVARIANT: not yet checkable]")
    else:
        chk.inv(worst < 1e-6, "caps parity", f"caps parity: allocate(state=None, cover=False) vs siting.per_tf_rule, "
                f"{n} random single-step states, max diff {worst:.1e} < 1e-6")

    # battery-caused normal: aware 0 (every aware combo), naive >= 1 -------------------------------------------
    aw = {k: v(d["headline"]["causedNormal"]) for k, d in combos.items() if k.startswith("aware")}
    chk.inv(all(x == 0 for x in aw.values()), "aware battery-caused",
            f"baseline {idx['default']} battery-caused normal {aw[idx['default']]} (all 8 aware combos: {sorted(set(aw.values()))})")
    nd = combos["naive-core-d26-g0"]["headline"]
    n_nv = v(nd["causedNormal"])
    chk.exp(n_nv >= 1, f"baseline naive-core-d26-g0 battery-caused normal {n_nv} (7.3 lag rule: {v(nd['causedLagNormal'])}; "
            f"emergency intervals {v(nd['emergencyN'])}; protection tfs {v(nd['protectionTfs'])})", ">= 1")
    lag_aw = v(combos[idx["default"]]["headline"]["causedLagNormal"])
    print(f"baseline {idx['default']} normal events attributed by 7.3's lag rule (batteries active within 2 steps): {lag_aw}   [report]")

    # fleet counterfactual, insight -------------------------------------------------------------------------------
    t = idx["fleetCounterfactualTotals"]
    print(f"fleet head estimate (DERIVED, lossless, % of 370 A): none {v(t['none']['headPct'])} / naive {v(t['naive']['headPct'])} / "
          f"aware {v(t['aware']['headPct'])}   [report]")
    print(f"fleet counterfactual (hours >100%, all tfs): none {v(t['none']['h100'])} / naive {v(t['naive']['h100'])} / "
          f"aware {v(t['aware']['h100'])} (SIM) ; normal events {v(t['none']['normalEvents'])} / {v(t['naive']['normalEvents'])} / "
          f"{v(t['aware']['normalEvents'])} ; tfs >100% {v(t['none']['tfsOver100'])} / {v(t['naive']['tfsOver100'])} / "
          f"{v(t['aware']['tfsOver100'])}   [report]")
    tph, pmh = idx["insight"]["tfPeakHour"], idx["insight"]["priceMaxHour"]
    print(f"insight: tf monthly-peak hour (SIM, {sum(tph)} tfs) mode {tph.index(max(tph)):02d} ; daily max-price hour "
          f"(REAL, {sum(pmh)} days) mode {pmh.index(max(pmh)):02d}   [report]")

    # top 5, ties, drivers ------------------------------------------------------------------------------------------
    rk = combos[idx["default"]]["ranking"]
    print(f"top5 {idx['default']}: " + " ".join(f"{e['rank']} {e['label']}@tf{e['tf']} \"{e['reason']}\"" for e in rk[:5]))
    d = idx["drivers"]
    print(f"ties decided by id: {v(idx['ties']['byId'])}/{idx['ties']['of']} ; aware top 10 driven by "
          f"{v(d['top10DistinctProfiles'])} distinct SMART-DS profiles [{', '.join(sorted(set(d['profiles'])))}]   [report]")

    # checks ------------------------------------------------------------------------------------------------------
    hit = [e for e in rk[:5] if e["tf"] not in fleet_tfs and v(e["before"]["h100"]) > 0]
    chk.exp(bool(hit), f"check: a home on a battery-less >100% tf is in the aware top 5: "
            f"{', '.join(e['label'] + '@tf' + str(e['tf']) for e in hit) or 'none'}", "yes")
    nvt = v(nd["newViolationTfs"])
    chk.exp(nvt >= 1, f"check: >= 1 naive candidate creates a new violation (where NOT to put it): {nvt} transformers, "
            f"{v(nd['newViolationHomes'])} candidates", ">= 1")
    pc = combos["naive-core-d26-g0"]["protectionCases"]
    print("check: protection operates in >= 1 naive counterfactual: " +
          (", ".join(f"{x['label']}@tf{x['tf']} {x['t']}, dark homes [{', '.join(labels[h] for h in x['homesDark'])}]" for x in pc[:3])
           + (f" (+{len(pc) - 3} more)" if len(pc) > 3 else "") if pc else "none") + "   [report]")

    # flip ----------------------------------------------------------------------------------------------------------
    f = idx["flip"]
    print(f"flip: top-10 overlap {v(f['top10Overlap'])}/10 ; spearman {v(f['spearman'])} ; untied only "
          f"{v(f['untied']['top10Overlap'])}/10, {v(f['untied']['spearman'])} (n = {f['untied']['n']}) (DERIVED)   [report]")

    # greedy --------------------------------------------------------------------------------------------------------
    g = combos[idx["default"]]["greedy"]
    drops = [x["keyDrops"] for x in g]
    chk.exp(len(drops) == 10 and all(drops), f"greedy: score on the placed tf drops after each placement: "
            f"{sum(drops)}/{len(drops)} ({' '.join(x['label'] + '@tf' + str(x['tf']) for x in g)})", "x10")

    # useful capacity ---------------------------------------------------------------------------------------------
    uc = idx["usefulCapacity"]
    n1, n2 = v(uc["naive"]), v(uc["aware"])
    chk.exp(n2 > n1, f"useful capacity from empty feeder: naive {n1} / aware {n2} (cap {v(uc['cap']):.0%})", "n2 > n1")
    fh = uc["feederHead"]
    print(f"         naive stop: {uc['naive']['stop']} ; aware (feeder-head cap) stop: {uc['aware']['stop']} ; aware with "
          f"transformer caps only: {v(uc['awareTransformerOnly'])} ; feeder-head estimate (DERIVED, lossless, reads low): "
          f"empty feeder {v(fh['aware']['pctEmpty'])}%, without a head cap it passes 100% at placement naive "
          f"{v(fh['naive']['overAt'])} / aware {v(fh['aware']['overAt'])}   [report]")

    # referee -------------------------------------------------------------------------------------------------------
    r = idx["referee"]
    ref = json.loads(REF_PATH.read_text()) if REF_PATH.exists() else {}
    fresh = ref.get("schedule_sha256") == idx.get("referee_schedule_sha256") and ref.get("schedule_sha256") is not None
    carded = {}
    for combo in ("aware-core-d26-g0", "naive-core-d26-g0"):
        top = combos[combo]["ranking"][:5]
        carded[combo] = sum(1 for e in top if e["opendss"] and e["opendss"]["before"] and e["opendss"]["after"] and not e["screening"])
    ok = r.get("runs") == 6 and r.get("steps") == idx["steps"] and fresh and all(x == 5 for x in carded.values())
    chk.inv(ok, "referee", f"referee: {r.get('runs')} runs x {r.get('steps', 0)} | shortlist {carded['aware-core-d26-g0']}/5 "
            f"(naive {carded['naive-core-d26-g0']}/5) carry OpenDSS numbers | schedules {'match' if fresh else 'STALE or missing'}")
    if r.get("runs"):
        p99, mx = v(r["errorPts"]["p99"]), v(r["errorPts"]["max"])
        chk.exp(p99 is not None and p99 <= 5, f"         error max {mx} pts ; p99 {p99} pts ; tier agreement "
                f"{v(r['tierAgreementPct'])}% (all 379 tfs: max {v(r['errorAllPts']['max'])}, p99 {v(r['errorAllPts']['p99'])}) ; "
                f"OpenDSS battery-caused normal, baseline: " +
                ", ".join(f"{k} {v(x)}" for k, x in r.get("baselineCausedNormal", {}).items()), "p99 <= 5")

    # determinism -----------------------------------------------------------------------------------------------------
    if rebuild:
        after = snapshot()
        diff = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        chk.inv(not diff, "determinism", f"determinism: rebuild {'byte-identical' if not diff else 'DIFFERS: ' + ', '.join(diff[:6])} "
                f"({len(after)} files)")
        if diff:
            restore(before)
    else:
        print("determinism: not checked (run --full)")
    if chk.fail:
        print(f"VERIFY p2: FAIL ({', '.join(chk.fail)})")
        return 1
    print(f"VERIFY p2: PASS ({len(chk.refuted)} expectations refuted, see NOTES.md)")
    return 0


def outputs():
    return sorted(P2.glob("*.json")) + [CSV_PATH, REF_PATH]


def snapshot():
    return {str(p.relative_to(ROOT)): p.read_bytes() for p in outputs() if p.exists()}


def restore(snap):
    for rel, b in snap.items():
        (ROOT / rel).write_bytes(b)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
