"""volt item v3: voltage at every bus + reactive power on the SMART-DS feeder, prototype replay states.

v3 (after adversarial review, 2026-09-26): adds a timeline sweep of every replay step (8 series x 13 steps) in the
as-built and unity-PF variants, and adds the worst unity-PF rebound step as a detailed state. Unity PF is the
page's default variant; as-built is the labelled "current replay (bug: Core PF 0.88)" view.

Variants per replay state (all SIM: OpenDSS on NREL SMART-DS p1uhs19_1247--p1udt17263, scripted inputs):
  asBuilt        exactly what replays.json shows. Core loads carry OpenDSS's default PF 0.88 because feeder.py sets
                 kW only (Loads.kW resets the spec to kW+PF); verified: fresh bat_ load reports PF 0.88.
  unityPf        same kW, Core kvar forced to 0 (the README's stated intent: unity-power-factor Cores).
  voltVar        unityPf + IEEE 1547-2018 Category B default volt-var on each Core (steady state, fixed-point iteration).
  ceiling        unityPf + every Core at the curve's saturated 44% of assumed 20 kVA (8.8 kvar) in the helpful
                 direction (inject when the state's problem is low voltage, absorb when high). A capability bound,
                 not default 1547 behaviour.
Run: <venv>/bin/python volt-analysis.py <tmp_dir> && <venv>/bin/python volt-build.py <tmp_dir>   (about 1 s of CPU; writes volt_v2_*.json to <tmp_dir>)
"""
import sys, json, math, time, heapq, hashlib
from collections import defaultdict
from pathlib import Path

GS = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories')
sys.path.insert(0, str(GS))
from sim.feeder import Feeder  # noqa: E402
from opendssdirect import dss  # noqa: E402

OUT = Path(sys.argv[1])
REPLAYS = GS / 'ui' / 'dist' / 'replays.json'
TOPO = GS / 'ui' / 'dist' / 'topology.json'
MODEL = GS / 'ui' / 'dist' / 'model.json'
R = json.loads(REPLAYS.read_text()); T = json.loads(TOPO.read_text()); M = json.loads(MODEL.read_text())
VMIN, VMAX, BIN_KM = 0.95, 1.05, 0.1
VV = [(0.92, 0.44), (0.98, 0.0), (1.02, 0.0), (1.08, -0.44)]  # IEEE 1547-2018 Cat B default (V pu, Q/S rated; + = inject)
CORE_KVA = 20.0  # ASSUMPTION: nameplate apparent power = Base's published 20 kW; P held unchanged when Q is added

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]

t0 = time.time()
f = Feeder()
dss.Loads.Name('bat_' + f.homes[0]['id'])
fresh_pf = dss.Loads.PF()
weak = M['shaping']['weakLine']; dss.Lines.Name(weak)
assert abs(dss.Lines.Length() - M['shaping']['originalLengthKm']) < 1e-9
dss.Lines.Length(M['shaping']['modifiedLengthKm'])  # reproduce build_replays.py shaping exactly

source = 'p1udt17263-p1uhs19_1247x'
coords = {}
for line in (GS / 'data' / 'smartds' / 'Buscoords.dss').read_text().splitlines():
    p = line.split()
    if len(p) == 3: coords[p[0]] = [round(float(p[1]), 6), round(float(p[2]), 6)]

graph = defaultdict(list); total_len = 0.0
for ln in dss.Lines:
    a, b = ln.Bus1().split('.')[0], ln.Bus2().split('.')[0]
    L = max(ln.Length(), 1e-5); total_len += ln.Length()
    assert ln.Units() in (0, 3)  # 3 = km, 0 = none; numeric lengths are km in every case (file total checked)
    graph[a].append((b, L)); graph[b].append((a, L))
for tx in dss.Transformers:
    buses = [s.split('.')[0] for s in dss.CktElement.BusNames()]
    for x in buses[1:]:
        if x != buses[0]: graph[buses[0]].append((x, 0.0)); graph[x].append((buses[0], 0.0))
dist = {source: 0.0}; parent = {}; q = [(0.0, source)]
while q:
    d, a = heapq.heappop(q)
    if d > dist[a]: continue
    for b, w in graph[a]:
        if d + w < dist.get(b, 1e30): dist[b] = d + w; parent[b] = a; heapq.heappush(q, (d + w, b))

all_buses = list(dss.Circuit.AllBusNames())
kvbase = {}
for b in all_buses:
    dss.Circuit.SetActiveBus(b); kvbase[b] = dss.Bus.kVBase()
kinds = {b: ('primary' if kvbase[b] > 1 else 'secondary' if abs(kvbase[b] - 0.12) < 1e-3 else 'otherLV') for b in all_buses}
home_ids = [h['id'] for h in f.homes]; hi = {h['id']: h for h in T['homes']}
core_ids = sorted(h['id'] for h in T['homes'] if h['battery']); core_set = set(core_ids)
assert [h['id'] for h in T['homes']] == home_ids
assert [x['id'] for x in T['transformers']] == [x['id'] for x in f.transformers]
assert all(b in dist for b in all_buses)

def bus_voltages():
    per = defaultdict(list)
    for n, v in zip(dss.Circuit.AllNodeNames(), dss.Circuit.AllBusMagPu()): per[n.split('.')[0]].append(v)
    return {b: (min(v), max(v)) for b, v in per.items()}

def vll_pu(bus):
    dss.Circuit.SetActiveBus(bus); nodes = dss.Bus.Nodes(); v = dss.Bus.Voltages()
    c = {n: complex(v[2 * i], v[2 * i + 1]) for i, n in enumerate(nodes)}
    return abs(c[1] - c[2]) / 240.0

def element_terms(it):
    out = []
    for _ in it:
        pw = dss.CktElement.Powers(); nc = dss.CktElement.NumConductors(); nt = dss.CktElement.NumTerminals()
        out.append((dss.CktElement.Name(), [(sum(pw[2 * nc * t:2 * nc * (t + 1)][::2]), sum(pw[2 * nc * t:2 * nc * (t + 1)][1::2])) for t in range(nt)]))
    return out

def budget():
    tot = dss.Circuit.TotalPower(); P, Q = -tot[0], -tot[1]
    loads = element_terms(dss.Loads)
    isb = lambda n: n.lower().startswith('load.bat_')
    Plh = sum(t[0][0] for n, t in loads if not isb(n)); Qlh = sum(t[0][1] for n, t in loads if not isb(n))
    Plb = sum(t[0][0] for n, t in loads if isb(n)); Qlb = sum(t[0][1] for n, t in loads if isb(n))
    lines = element_terms(dss.Lines); txs = element_terms(dss.Transformers); caps = element_terms(dss.Capacitors)
    Pll = sum(sum(x[0] for x in t) for n, t in lines); Qll = sum(sum(x[1] for x in t) for n, t in lines)
    Ptl = sum(sum(x[0] for x in t) for n, t in txs); Qtl = sum(sum(x[1] for x in t) for n, t in txs)
    Qc = sum(t[0][1] for n, t in caps)
    return {'sourceKW': round(P, 1), 'sourceKvar': round(Q, 1), 'pf': round(P / math.hypot(P, Q), 4),
            'homeLoadKW': round(Plh, 1), 'homeLoadKvar': round(Qlh, 1), 'coreKW': round(Plb, 1), 'coreKvar': round(Qlb, 1),
            'lineLossKW': round(Pll, 1), 'lineNetKvar': round(Qll, 1), 'transformerLossKW': round(Ptl, 1), 'transformerKvar': round(Qtl, 1),
            'capacitorKvar': round(Qc, 1),
            'closureKW': round(P - (Plh + Plb + Pll + Ptl), 3), 'closureKvar': round(Q - (Qlh + Qlb + Qll + Qtl + Qc), 3)}

def cap_state(bv):
    out = []
    for _ in dss.Capacitors:
        bus = dss.CktElement.BusNames()[0].split('.')[0]; pw = dss.CktElement.Powers()
        out.append({'id': dss.Capacitors.Name(), 'state': list(dss.Capacitors.States()), 'deliveredKvar': round(-sum(pw[1::2]), 1),
                    'busPu': [round(bv[bus][0], 4), round(bv[bus][1], 4)]})
    ctl = []
    for _ in dss.CapControls:
        el = dss.CapControls.MonitoredObj(); term = dss.CapControls.MonitoredTerm(); pt = dss.CapControls.PTRatio()
        dss.Circuit.SetActiveElement(el); vm = dss.CktElement.VoltagesMagAng()[0::2]; nc = dss.CktElement.NumConductors()
        ctl.append({'id': dss.CapControls.Name(), 'monitoredV120': [round(v / pt, 2) for v in vm[(term - 1) * nc:term * nc][:3]]})
    return out, ctl

def cap_static():
    caps = []
    for _ in dss.Capacitors:
        bus = dss.CktElement.BusNames()[0].split('.')[0]
        caps.append({'id': dss.Capacitors.Name(), 'bus': bus, 'coordinates': coords.get(bus), 'distanceKm': round(dist[bus], 3),
                     'ratedKvar': dss.Capacitors.kvar(), 'kV': dss.Capacitors.kV(), 'phases': dss.CktElement.NumPhases(),
                     'conn': 'delta' if dss.Capacitors.IsDelta() else 'wye'})
    ctls = []
    for _ in dss.CapControls:
        pt = dss.CapControls.PTRatio()
        ctls.append({'id': dss.CapControls.Name(), 'capacitor': dss.CapControls.Capacitor(), 'type': 'voltage',
                     'monitored': dss.CapControls.MonitoredObj(), 'terminal': dss.CapControls.MonitoredTerm(), 'ptRatio': round(pt, 4),
                     'onBelowV120': dss.CapControls.Vmin(), 'offAboveV120': dss.CapControls.Vmax(),
                     'onBelowPu': round(dss.CapControls.Vmin() * pt / 7200, 4), 'offAbovePu': round(dss.CapControls.Vmax() * pt / 7200, 4),
                     'delayS': dss.CapControls.Delay()})
    return caps, ctls

def tx_rows():
    rows = []
    for tx in f.transformers:
        dss.Circuit.SetActiveElement('Transformer.' + tx['id'])
        pw = dss.CktElement.Powers(); nc = dss.CktElement.NumConductors()
        p1 = sum(pw[:2 * nc][::2]); q1 = sum(pw[:2 * nc][1::2])
        rows.append((p1, q1, sum(pw[1::2]), math.hypot(p1, q1) / tx['kva'] * 100))
    return rows

def profile(bv):
    bins = {}
    for b, (lo, hi_) in bv.items():
        kk = 'primary' if kinds[b] == 'primary' else 'secondary'
        i = int(dist[b] / BIN_KM); e = bins.setdefault((kk, i), [9, 0, 0])
        e[0] = min(e[0], lo); e[1] = max(e[1], hi_); e[2] += 1
    mx = max(i for _, i in bins)
    return {kk: [[round(i * BIN_KM + BIN_KM / 2, 2), round(bins[(kk, i)][0], 4), round(bins[(kk, i)][1], 4), bins[(kk, i)][2]]
                 for i in range(mx + 1) if (kk, i) in bins] for kk in ('primary', 'secondary')}

def path_to(target):
    p = [target]
    while p[-1] != source: p.append(parent[p[-1]])
    return p[::-1]

def trace(target, bv):
    rows = [[round(dist[b], 3), round(bv[b][0], 4), round(bv[b][1], 4), kinds[b][0].upper()] for b in path_to(target)]
    comp = [rows[0]]
    for r in rows[1:]:
        l = comp[-1]
        if r[3] != l[3] or abs(r[1] - l[1]) >= 0.0005 or abs(r[0] - l[0]) >= 0.05: comp.append(r)
    if comp[-1] is not rows[-1]: comp.append(rows[-1])
    return comp

def drop_split(target, bv):
    p = path_to(target)
    lp = max(i for i, b in enumerate(p) if kinds[b] == 'primary'); lv = p[lp + 1]
    v = lambda b: bv[b][0]
    return {'sourcePu': round(v(source), 4), 'primaryTapPu': round(v(p[lp]), 4), 'transformerLvPu': round(v(lv), 4), 'homePu': round(v(target), 4),
            'dropPrimaryPu': round(v(source) - v(p[lp]), 4), 'dropTransformerPu': round(v(p[lp]) - v(lv), 4), 'dropSecondaryPu': round(v(lv) - v(target), 4),
            'primaryTapBus': p[lp], 'transformerLvBus': lv}

def counts(bv):
    c = {}
    for k in ('primary', 'secondary', 'otherLV'):
        bs = [b for b in bv if kinds[b] == k]
        c[k] = {'n': len(bs), 'below': sum(bv[b][0] < VMIN for b in bs), 'above': sum(bv[b][1] > VMAX for b in bs),
                'minPu': round(min(bv[b][0] for b in bs), 5), 'maxPu': round(max(bv[b][1] for b in bs), 5)}
    for k, bs in (('homes', home_ids), ('coreHomes', core_ids)):
        c[k] = {'n': len(bs), 'below': sum(bv[b][0] < VMIN for b in bs), 'above': sum(bv[b][1] > VMAX for b in bs),
                'minPu': round(min(bv[b][0] for b in bs), 5), 'maxPu': round(max(bv[b][1] for b in bs), 5)}
    c['allBuses'] = {'n': len(bv), 'below': sum(v[0] < VMIN for v in bv.values()), 'above': sum(v[1] > VMAX for v in bv.values())}
    return c

def set_core_kvar(qinj):  # qinj: kvar INJECTED per core (generator convention); load convention = negative
    for u in core_ids: dss.Loads.Name('bat_' + u); dss.Loads.kvar(-qinj.get(u, 0.0))

def vv_curve(v):
    if v <= VV[0][0]: return VV[0][1]
    if v >= VV[-1][0]: return VV[-1][1]
    for (va, qa), (vb, qb) in zip(VV, VV[1:]):
        if va <= v <= vb: return qa + (qb - qa) * (v - va) / (vb - va)

def full_detail(s, res, bv, with_trace=True):
    txr = tx_rows(); b = budget(); caps, ctl = cap_state(bv)
    wh = min(home_ids, key=lambda x: bv[x][0]); hh = max(home_ids, key=lambda x: bv[x][1])
    def card(x):
        h = hi[x]; ti = h['tf']
        return {'bus': x, 'label': h['label'], 'district': h['district'], 'core': x in core_set, 'coreKW': s['powers'].get(x, 0),
                'minPu': round(bv[x][0], 5), 'maxPu': round(bv[x][1], 5), 'vllPu': round(vll_pu(x), 5), 'distanceKm': round(dist[x], 3),
                'transformer': f.transformers[ti]['id'], 'transformerIndex': ti, 'transformerKva': f.transformers[ti]['kva'],
                'transformerLoadingPct': round(txr[ti][3], 1), 'transformerKW': round(txr[ti][0], 1), 'transformerKvar': round(txr[ti][1], 1),
                'coordinates': coords.get(x)}
    pfs = sorted(abs(p) / math.hypot(p, qq) for p, qq, *_ in txr if math.hypot(p, qq) > 0.5)
    top = sorted(range(len(txr)), key=lambda i: -txr[i][1])[:5]
    out = {'head': {'kW': b['sourceKW'], 'kvar': b['sourceKvar'], 'pf': b['pf']}, 'reactiveBudget': b, 'counts': counts(bv),
           'profile': profile(bv), 'worstHome': card(wh), 'highestHome': card(hh),
           'dropSplitToWorstHome': drop_split(wh, bv),
           'traceToWorstHome': trace(wh, bv) if with_trace else None,
           'traceToHighestHome': trace(hh, bv) if with_trace else None,
           'outOfLimitBuses': sorted([[x, kinds[x][0].upper(), round(bv[x][0], 4), round(bv[x][1], 4), round(dist[x], 3)] for x in bv if bv[x][0] < VMIN or bv[x][1] > VMAX], key=lambda r: r[2]),
           'capacitor': caps, 'capControlMonitoredV120': ctl,
           'transformers': {'sumPrimaryKW': round(sum(r[0] for r in txr), 1), 'sumPrimaryKvar': round(sum(r[1] for r in txr), 1),
                            'sumVarLosses': round(sum(r[2] for r in txr), 1), 'maxLoadingPct': round(max(r[3] for r in txr), 2),
                            'overloaded': sum(r[3] > 100.0001 for r in txr), 'medianPf': round(pfs[len(pfs) // 2], 4),
                            'pfHistogram': {'<0.90': sum(x < 0.90 for x in pfs), '0.90-0.95': sum(0.90 <= x < 0.95 for x in pfs),
                                            '0.95-0.98': sum(0.95 <= x < 0.98 for x in pfs), '>=0.98': sum(x >= 0.98 for x in pfs)},
                            'topByKvar': [[i, round(txr[i][0], 1), round(txr[i][1], 1), round(txr[i][3], 1)] for i in top],
                            'kvar': [round(r[1], 1) for r in txr]}}
    return out

def solve_variant(s, variant):
    f.load(s['loadFactor']); f.battery(s['powers'])
    info = {}
    if variant == 'asBuilt':
        # build_replays.py only ever set kW, so Core loads kept OpenDSS's default PF (0.88). Restore that explicitly
        # because other variants in this script write kvar (which changes the load's spec type and PF).
        for u in core_ids:
            dss.Loads.Name('bat_' + u); dss.Loads.PF(fresh_pf); dss.Loads.kW(s['powers'].get(u, 0))
    elif variant == 'unityPf':
        set_core_kvar({})
    elif variant == 'voltVar':
        qv = {u: 0.0 for u in core_ids}; set_core_kvar(qv); f.solve(detail=False); delta = None; it = 0
        for it in range(1, 81):
            tgt = {u: vv_curve(vll_pu(u)) * CORE_KVA for u in core_ids}
            new = {u: qv[u] + 0.5 * (tgt[u] - qv[u]) for u in core_ids}
            delta = max(abs(new[u] - qv[u]) for u in core_ids); qv = new; set_core_kvar(qv); f.solve(detail=False)
            if delta < 0.005: break
        info = {'iterations': it, 'converged': delta < 0.005, 'finalStepKvar': round(delta, 4), 'perCoreKvar': qv}
    elif variant.startswith('ceiling'):
        sign = 1 if variant == 'ceilingInject' else -1
        qv = {u: sign * 0.44 * CORE_KVA for u in core_ids}; set_core_kvar(qv); info = {'perCoreKvar': qv}
    res = f.solve(detail=True); bv = bus_voltages()
    return res, bv, info

caps_static, capctl_static = cap_static()

# ---- v3 (review repair): timeline sweep over EVERY replay step, as-built (PF 0.88 bug) and unity PF ----
# Answers "does any bus leave 0.95-1.05 at unity PF in ANY replay state?" and finds the worst unity-PF moment.
TL_COLS = ['step', 'clock', 'minHomePu', 'worstHome', 'maxHomePu', 'busesBelow', 'busesAbove', 'minPrimaryPu', 'headKW', 'headKvar', 'overloadedTx']
def quick(s, res, bv):
    wh = min(home_ids, key=lambda x: bv[x][0])
    tot = dss.Circuit.TotalPower()
    return [s['step_i'], f"{s['minute'] // 60:02d}:{s['minute'] % 60:02d}", round(bv[wh][0], 5), wh, round(max(bv[x][1] for x in home_ids), 5),
            sum(v[0] < VMIN for v in bv.values()), sum(v[1] > VMAX for v in bv.values()),
            round(min(v[0] for b, v in bv.items() if kinds[b] == 'primary'), 5), round(-tot[0], 1), round(-tot[1], 1), res['overloaded']]
timeline = {}; tl_repro = 0.0
for sc, pols in R.items():
    if not isinstance(pols, dict): continue
    for pol, steps in pols.items():
        if not isinstance(steps, list): continue
        rows = {'asBuilt': [], 'unityPf': []}
        for i, s0 in enumerate(steps):
            s = dict(s0, step_i=i)
            res, bv, _ = solve_variant(s, 'asBuilt')
            d = max(abs(a - b) for a, b in zip(res['voltage'], s['voltage'])); tl_repro = max(tl_repro, d)
            assert d <= 2e-5, (sc, pol, i, d)
            rows['asBuilt'].append(quick(s, res, bv))
            res, bv, _ = solve_variant(s, 'unityPf')
            rows['unityPf'].append(quick(s, res, bv))
        timeline[f'{sc}.{pol}'] = rows
set_core_kvar({})
tl_all_unity = [r for v in timeline.values() for r in v['unityPf']]
tl_all_ab = [r for v in timeline.values() for r in v['asBuilt']]
worst_unity_step = min(timeline['rebound.naive']['unityPf'], key=lambda r: r[2])[0]
print('timeline: states', len(tl_all_ab), 'max |home V - replay| as-built', tl_repro,
      '| unity buses outside (any state):', sum(r[5] + r[6] for r in tl_all_unity), 'min home', min(r[2] for r in tl_all_unity),
      '| as-built states with a bus outside:', sum((r[5] + r[6]) > 0 for r in tl_all_ab), 'min home', min(r[2] for r in tl_all_ab),
      '| worst unity rebound.naive step', worst_unity_step, flush=True)

STATES = [('rebound', 'naive', 0), ('rebound', 'aware', 0), ('rebound', 'naive', 3), ('rebound', 'aware', 3)]
if worst_unity_step != 3:
    STATES += [('rebound', 'naive', worst_unity_step), ('rebound', 'aware', worst_unity_step)]
STATES += [('heatwave', 'naive', 12), ('heatwave', 'aware', 12)]
states = []; full = {}
for sc, pol, st in STATES:
    s = R[sc][pol][st]; key = f'{sc}.{pol}.{st}'
    entry = {'key': key, 'scenario': sc, 'policy': pol, 'step': st, 'clock': f"{s['minute'] // 60:02d}:{s['minute'] % 60:02d}",
             'loadFactor': s['loadFactor'], 'coreKWTotal': round(sum(s['powers'].values()), 1),
             'coresCharging': sum(v > 0 for v in s['powers'].values()), 'coresDischarging': sum(v < 0 for v in s['powers'].values())}
    res, bv, _ = solve_variant(s, 'asBuilt')
    rep = {'minVoltage': [res['minVoltage'], s['minVoltage']], 'maxVoltage': [res['maxVoltage'], s['maxVoltage']],
           'maxLoading': [res['maxLoading'], s['maxLoading']], 'feederMW': [res['feederMW'], s['feederMW']],
           'voltageViolations': [res['voltageViolations'], s['voltageViolations']], 'overloaded': [res['overloaded'], s['overloaded']],
           'maxAbsHomeVoltageDiffPu': round(max(abs(a - b) for a, b in zip(res['voltage'], s['voltage'])), 6)}
    assert rep['maxAbsHomeVoltageDiffPu'] <= 2e-5, rep
    entry['reproduction'] = rep
    entry['asBuilt'] = full_detail(s, res, bv)
    full[key] = {'asBuilt': bv}
    res, bv, _ = solve_variant(s, 'unityPf')
    entry['unityPf'] = full_detail(s, res, bv)
    full[key]['unityPf'] = bv
    base_u = entry['unityPf']
    wh_ab = entry['asBuilt']['worstHome']['bus']; hh_ab = entry['asBuilt']['highestHome']['bus']
    idx = {b: i for i, b in enumerate(home_ids)}
    for variant in ('voltVar', 'ceilingInject' if sc == 'rebound' else 'ceilingAbsorb'):
        res, bv, info = solve_variant(s, variant)
        b = budget(); txr = tx_rows(); pc = info['perCoreKvar']
        v = {'head': {'kW': b['sourceKW'], 'kvar': b['sourceKvar'], 'pf': b['pf']}, 'counts': counts(bv), 'profile': profile(bv),
             'fleetInjectKvar': round(sum(pc.values()), 1), 'coresInjecting': sum(x > 0.05 for x in pc.values()),
             'coresAbsorbing': sum(x < -0.05 for x in pc.values()), 'maxCoreInjectKvar': round(max(pc.values()), 2),
             'maxCoreAbsorbKvar': round(-min(pc.values()), 2),
             'maxTransformerLoadingPct': round(max(r[3] for r in txr), 2), 'overloadedTransformers': sum(r[3] > 100.0001 for r in txr),
             'worstHomeAsBuiltPu': round(bv[wh_ab][0], 5), 'highestHomeAsBuiltPu': round(bv[hh_ab][1], 5),
             'worstHomeCoreKvar': round(pc.get(wh_ab, 0), 2) if wh_ab in core_set else None}
        for k in ('iterations', 'converged', 'finalStepKvar'):
            if k in info: v[k] = info[k]
        if variant == 'voltVar':
            v['perCoreKvar'] = [round(pc[u], 2) for u in core_ids]
        v['deltaVsUnityPf'] = {'minHomePu': round(v['counts']['homes']['minPu'] - base_u['counts']['homes']['minPu'], 5),
                               'maxHomePu': round(v['counts']['homes']['maxPu'] - base_u['counts']['homes']['maxPu'], 5),
                               'headKvar': round(b['sourceKvar'] - base_u['head']['kvar'], 1)}
        entry['ceiling' if variant.startswith('ceiling') else 'voltVar'] = v
        if variant.startswith('ceiling'): entry['ceiling']['direction'] = 'inject' if variant == 'ceilingInject' else 'absorb'
    set_core_kvar({})
    states.append(entry)
    ab, u, vv, ce = entry['asBuilt'], entry['unityPf'], entry['voltVar'], entry['ceiling']
    print(f"{key:20s} asBuilt min {ab['counts']['homes']['minPu']:.4f} max {ab['counts']['homes']['maxPu']:.4f} out {ab['counts']['allBuses']} ovl {ab['transformers']['overloaded']} Q {ab['head']['kvar']} coreQ {ab['reactiveBudget']['coreKvar']} | "
          f"unity min {u['counts']['homes']['minPu']:.4f} max {u['counts']['homes']['maxPu']:.4f} out {u['counts']['allBuses']} ovl {u['transformers']['overloaded']} Q {u['head']['kvar']} | "
          f"VV min {vv['counts']['homes']['minPu']:.4f} max {vv['counts']['homes']['maxPu']:.4f} fleetQ {vv['fleetInjectKvar']} it {vv['iterations']} | "
          f"ceil({ce['direction']}) min {ce['counts']['homes']['minPu']:.4f} max {ce['counts']['homes']['maxPu']:.4f} ovl {ce['overloadedTransformers']} Q {ce['head']['kvar']}", flush=True)

meta = {'engine': dss.Basic.Version().split(';')[0].strip(), 'opendssdirect': '0.9.4', 'generatedAtUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'runSeconds': round(time.time() - t0, 2), 'inputsSha256_16': {'replays.json': sha(REPLAYS), 'topology.json': sha(TOPO), 'model.json': sha(MODEL)},
        'freshCoreLoadPf': fresh_pf, 'totalLineKm': round(total_len, 3)}
feeder = {'id': 'p1uhs19_1247--p1udt17263', 'busCounts': {k: sum(1 for b in all_buses if kinds[b] == k) for k in ('primary', 'secondary', 'otherLV')},
          'buses': len(all_buses), 'homes': len(home_ids), 'cores': len(core_ids), 'transformers': len(f.transformers),
          'maxDistanceKm': round(max(dist.values()), 3), 'sourceBus': source, 'sourcePu': 1.03, 'regulators': 0,
          'capacitors': caps_static, 'capControls': capctl_static, 'coreIds': core_ids,
          'weakLine': {'id': weak, 'originalKm': M['shaping']['originalLengthKm'], 'modelledKm': M['shaping']['modifiedLengthKm']}}
meta['timelineMaxAbsHomeVoltageDiffPu'] = round(tl_repro, 6)
tl_out = {'columns': TL_COLS, 'series': timeline, 'worstUnityReboundNaiveStep': worst_unity_step}
(OUT / 'volt_v2_states.json').write_text(json.dumps({'meta': meta, 'feeder': feeder, 'states': states, 'timeline': tl_out}, separators=(',', ':')))
# full per-bus file (audit / map layer), bus order = OpenDSS AllBusNames
fb = {'buses': all_buses, 'kind': [kinds[b][0].upper() for b in all_buses], 'distanceKm': [round(dist[b], 4) for b in all_buses],
      'coordinates': [coords.get(b) for b in all_buses], 'kVBaseLN': [round(kvbase[b], 4) for b in all_buses],
      'states': {k: {var: {'minPu': [round(bvv[b][0], 4) for b in all_buses], 'maxPu': [round(bvv[b][1], 4) for b in all_buses]} for var, bvv in d.items()} for k, d in full.items()}}
(OUT / 'volt_v2_buses.json').write_text(json.dumps(fb, separators=(',', ':')))
print('meta', meta, feeder['busCounts'], feeder['maxDistanceKm'])
