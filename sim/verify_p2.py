"""VERIFY p2 (build prompt 7.4; lane L3): reads the committed ui/data/p2/*, data/out/siting-2026-08.csv and
data/out/referee-2026-08.json, and prints 7.4's lines.

    python -m sim.verify p2              # committed JSON only; "determinism: not checked (run --full)"
    python -m sim.verify p2 --rebuild    # heavy (the caller holds the lock): rebuild p2 + referee, byte-compare

[INVARIANT] lines gate; [EXPECT] lines print `ok <measured>` or `REFUTED: <measured>` and never gate (3.5);
[report] lines only print. Ends "VERIFY p2: PASS (k expectations refuted, see the [EXPECT] lines above)" or "VERIFY p2: FAIL (...)".
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
        print("rebuild: sim.referee (16 combos + useful capacity + 6 + 2 OpenDSS months + re-merge) ...")
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
    print(f"fleet head estimate (DERIVED, per phase, % of 370 A): none {v(t['none']['headPct'])} / naive {v(t['naive']['headPct'])} / "
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

    # per-combo blocks (audit R2 M1-M3): each combo's own bridge, fleet table and flip, consistent with its own data --
    t240 = next(i for i, t in enumerate(topo["transformers"]) if t["id"] == idx["bridge"][0]["id"]) if idx.get("bridge") else None
    bad = []
    m1 = []
    for cid, d in combos.items():
        pol, cls, rule, gg = cid.split("-")
        cn, ca = f"naive-{cls}-{rule}-{gg}", f"aware-{cls}-{rule}-{gg}"
        b, fct, fl = d.get("bridge"), d.get("fleetCounterfactualTotals"), d.get("flip")
        if not (b and fct and fl):
            bad.append(f"{cid}: missing bridge/fleetCounterfactualTotals/flip")
            continue
        e = b.get(pol)
        if b["tf"] != t240 or e is None:
            bad.append(f"{cid}: bridge tf {b['tf']} / entry {e is not None}")
            continue
        if abs(v(e["peakWithoutPct"]) - d["baseline"]["peak"][t240] / 10) > 0.051:
            bad.append(f"{cid}: bridge peak without {v(e['peakWithoutPct'])} vs baseline {d['baseline']['peak'][t240] / 10}")
        if e["rank"] <= len(d["ranking"]):
            r = d["ranking"][e["rank"] - 1]
            if r["tf"] != t240 or v(r["peakWithPct"]) != v(e["peakWithPct"]) or r["home"] != e["home"]:
                bad.append(f"{cid}: bridge rank {e['rank']} disagrees with ranking row")
        elif any(r["tf"] == t240 for r in d["ranking"]):
            bad.append(f"{cid}: bridge rank {e['rank']} but T-240 is in the top {len(d['ranking'])}")
        for p_, sib in (("naive", cn), ("aware", ca)):
            hl = combos[sib]["headline"]
            if any(v(fct[p_][k]) != v(hl[k]) for k in ("h100", "normalEvents", "emergencyN", "causedNormal")):
                bad.append(f"{cid}: fleet row {p_} != {sib} headline")
        if fl["combos"] != [cn, ca]:
            bad.append(f"{cid}: flip combos {fl['combos']}")
        m1.append(f"{cid} rank {e['rank']} {v(e['peakWithoutPct'])}->{v(e['peakWithPct'])}")
    dft = combos[idx["default"]]
    for k in ("none", "naive", "aware"):
        if dft.get("fleetCounterfactualTotals", {}).get(k) != idx["fleetCounterfactualTotals"][k]:
            bad.append(f"index.fleetCounterfactualTotals.{k} != {idx['default']}'s")
    if {kk: vv for kk, vv in idx["flip"].items() if kk != "scopeText"} != dft.get("flip"):
        bad.append("index.flip != the default combo's own flip")
    for x in bad[:8]:
        print("    -", x)
    chk.inv(not bad, "per-combo blocks", f"per-combo blocks: {len(combos)} combos carry their own bridge (T-240), fleet table and "
            f"flip, each consistent with its own ranking, baseline and sibling headline; index blocks = {idx['default']}'s "
            f"({len(bad)} problems)")
    print("bridge T-240 per combo (rank, month peak without -> with, screening): " + " ; ".join(m1) + "   [report]")

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
          f"transformer caps only: {v(uc['awareTransformerOnly'])} ; per-phase feeder-head estimate (DERIVED; OpenDSS check below): "
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
    ok = r.get("runs") == 6 and v(r.get("steps")) == idx["steps"] and fresh and all(x == 5 for x in carded.values())
    chk.inv(ok, "referee", f"referee: {r.get('runs')} runs x {v(r.get('steps', 0))} | shortlist {carded['aware-core-d26-g0']}/5 "
            f"(naive {carded['naive-core-d26-g0']}/5) carry OpenDSS numbers | schedules {'match' if fresh else 'STALE or missing'}")
    if r.get("runs"):
        p99, mx = v(r["errorPts"]["p99"]), v(r["errorPts"]["max"])
        chk.exp(p99 is not None and p99 <= 5, f"         error max {mx} pts ; p99 {p99} pts ; tier agreement "
                f"{v(r['tierAgreementPct'])}% (all 379 tfs: max {v(r['errorAllPts']['max'])}, p99 {v(r['errorAllPts']['p99'])}) ; "
                f"OpenDSS battery-caused normal, baseline: " +
                ", ".join(f"{k} {v(x)}" for k, x in r.get("baselineCausedNormal", {}).items()), "p99 <= 5")

    # the feeder head and the useful-capacity builds, in OpenDSS ------------------------------------------------------
    heads = r.get("head") or {}
    if heads:
        print("referee head: OpenDSS max phase vs P2's per-phase estimate (DERIVED): " + " ; ".join(
            f"{run.split()[0]} {run.split()[1].split('-')[0]}{'-g20' if run.endswith('g20') else ''} {v(h['maxPct'])}% "
            f"(est {v(h['estMaxPct'])}%, est - OpenDSS {-v(h['underReadMaxPts']):+.2f} to {v(h['overReadMaxPts']):+.2f} pts; balanced total {v(h['balancedMaxPct'])}%)"
            for run, h in heads.items()) + "   [report]")
    fl = r.get("fleet") or {}
    want = {"none-g0", "none-g20"} | {c for c in combos if c.split("-")[1] == "core"}
    chk.inv(set(fl) == want and fresh, "fleet months", f"existing-fleet OpenDSS months: {len(fl)}/{len(want)} "
            f"(home load only g0 and g20 + every Core baseline) | schedules {'match' if fresh else 'STALE or missing'}")
    if fl:
        def fline(k):
            e = fl[k]
            return (f"{k} {v(e['h100'])} h, {v(e['normalEvents'])} events"
                    + (f" ({v(e['causedNormal'])} battery-caused)" if "causedNormal" in e else "")
                    + f", head {v(e['headMaxPct'])}%")
        print("fleet months (OpenDSS): " + " ; ".join(fline(k) for k in sorted(fl)) + "   [report]")
        tn = idx["fleetCounterfactualTotals"]["none"]
        ok_none = v(fl["none-g0"]["normalEvents"]) == v(tn["normalEvents"]) and abs(v(fl["none-g0"]["h100"]) - v(tn["h100"])) <= 0.5
        chk.exp(ok_none, f"no-battery row, OpenDSS vs screen: {v(fl['none-g0']['h100'])} h / {v(fl['none-g0']['normalEvents'])} events "
                f"vs {v(tn['h100'])} / {v(tn['normalEvents'])}", "same event count, h within 0.5")
        aw0 = {k: v(e["causedNormal"]) for k, e in fl.items() if k.startswith("aware")}
        chk.exp(all(x == 0 for x in aw0.values()), f"OpenDSS: aware existing fleet battery-caused normal events, every Core "
                f"baseline: {aw0}", "all 0")
        print(f"feeder head at +20% load (OpenDSS, % of 370 A): home load only {v(fl['none-g20']['headMaxPct'])}, "
              f"aware fleet {v(fl['aware-core-d26-g20']['headMaxPct'])}, naive fleet {v(fl['naive-core-d26-g20']['headMaxPct'])} ; "
              f"today's load: {v(fl['none-g0']['headMaxPct'])} / {v(fl['aware-core-d26-g0']['headMaxPct'])} / "
              f"{v(fl['naive-core-d26-g0']['headMaxPct'])}   [report]")
    cap = ref.get("capacity") or {}
    ucd = uc.get("opendss") or {}
    n3 = v(uc.get("naiveHead"))
    fresh_cap = (cap.get("sha256") is not None and cap.get("sha256") == idx.get("referee_capacity_sha256")
                 and all(p in ucd for p in ("naive", "aware", "naiveHead")) and ucd["naive"]["n"] == n1
                 and ucd["aware"]["n"] == n2 and ucd["naiveHead"]["n"] == n3 and "naiveOpenDSS" in uc)
    chk.inv(fresh_cap, "capacity-check", f"useful capacity OpenDSS check: naive {ucd.get('naive', {}).get('n')} / aware "
            f"{ucd.get('aware', {}).get('n')} / naive under aware's question {ucd.get('naiveHead', {}).get('n')} Cores from an "
            f"empty feeder, one OpenDSS month each | builds {'match' if fresh_cap else 'STALE or missing'}")
    if fresh_cap:
        def line(pol):
            c = ucd[pol]
            return (f"battery-caused normal {v(c['causedNormal'])} (all {v(c['normalEvents'])}), battery-caused emergency "
                    f"intervals {v(c['causedEmergencyN'])}, protection {v(c['protectionTfs'])} tfs, max tf {v(c['maxPct'])}%; "
                    f"head max {v(c['headMaxPct'])}% of 370 A at {c['headMaxPct']['t']} ({c['headMaxPct']['stepsOver100']} steps > 100%; "
                    f"per-phase estimate max {v(c['headEstMaxPct'])}%, OpenDSS - estimate <= {v(c['headUnderReadPts']):+.2f} pts; balanced total "
                    f"{v(c['headBalancedMaxPct'])}%); min home voltage {v(c['vMinPu'])} pu = {c['vMinPu']['volts']} V "
                    f"({c['vMinPu']['home']}, {c['vMinPu']['t']}), homes < 0.95 pu {v(c['homesBelow095'])}; surrogate err "
                    f"max {v(c['errorAllPts']['max'])} p99 {v(c['errorAllPts']['p99'])} pts")
        a = ucd["aware"]
        chk.exp(v(a["causedNormal"]) == 0 and v(a["causedEmergencyN"]) == 0 and v(a["headMaxPct"]) <= 100.0,
                f"         aware {n2}: " + line("aware"), "0 battery-caused normal and emergency ; head <= 100%")
        nv = ucd["naive"]
        chk.exp(v(nv["causedNormal"]) == 0, f"         naive {n1}: " + line("naive"),
                "0 battery-caused normal (the screen's stop rule); head reported")
        nh = ucd["naiveHead"]
        chk.exp(v(nh["causedNormal"]) == 0 and v(nh["causedEmergencyN"]) == 0 and nh["headMaxPct"]["stepsOver100"] == 0,
                f"         naive under aware's question {n3} (stop: {uc['naiveHead']['stop']}): " + line("naiveHead"),
                "0 battery-caused normal and emergency ; head never > 100%")
        so = uc["naiveOpenDSS"]
        print(f"         naive, OpenDSS-judged: holds up to {v(so)}, harm at {so['failAt']} "
              f"({'exact' if so['exact'] else 'bounds only'}; {len(so['checks'])} OpenDSS months: "
              + ", ".join(f"n={r[0]} caused {r[1]} head {r[3]}% ({r[4]} steps>100) {'holds' if r[6] else 'HARM'}" for r in so["checks"])
              + ")   [report]")

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
    print(f"VERIFY p2: PASS ({len(chk.refuted)} expectations refuted, see the [EXPECT] lines above)")
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
