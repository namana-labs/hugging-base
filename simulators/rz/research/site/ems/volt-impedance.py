"""volt item: where the voltage drop to the worst home comes from, and which lever (kW or kvar) moves each part.

Written after adversarial review (2026-09-26). v2 of the spec quoted "R/X of 120/240 V cables vs primary 1.93 vs 0.46";
that compared a feeder-wide km-weighted SELF-impedance mean (secondary) against a single-path SELF-impedance ratio
(primary). This script replaces it with:

  1. MEASURED sensitivity split (DERIVED from SIM solves): perturb Core kW and Core kvar (own Core, then all 96)
     and split the change in voltage at the worst home into primary / transformer / service-drop segments, tracking
     ONE phase-consistent node chain (source phase node -> transformer primary node -> LV leg -> home leg).
     The ratio (dV per kW) / (dV per kvar) of each segment is the effective R/X that segment presents.
  2. FINITE-change splits along the same node chain: PF-0.88 bug vs unity, volt-var, all-Core capability ceiling,
     own-Core-only ceiling, own Core idle, and the aware controller's kW at the same clock.
  3. R/X on a stated, consistent basis, same scope for both sides: loop impedance Zs-Zm (per conductor) for the
     2-wire 120/240 V triplex (what a 240 V line-to-line Core current sees), positive-sequence Z1 = mean(diag) -
     mean(offdiag) for multi-phase primary, self impedance for 1-phase primary laterals (Kron-reduced, the only
     defined quantity). Scopes: the worst-home path and feeder-wide. Both aggregations are given: ratio of sums
     (sum R*L / sum X*L, the path's series impedance) and km-weighted mean of per-line ratios. The v2 self-impedance
     numbers are reproduced so the correction is auditable.
  4. Transformer X/R from the SMART-DS 3-winding split-phase definitions: 120 V leg-1 (XHL over R_H+R_X1), leg-2
     (XHT over R_H+R_X2) and the 240 V line-to-line star equivalent.

Run: <venv>/bin/python volt-impedance.py <tmp_dir>   (needs <tmp_dir>/volt_v2_states.json from volt-analysis.py;
writes <tmp_dir>/volt_v2_impedance.json; about 1 s of CPU)
"""
import sys, json, math, heapq, time
from collections import defaultdict
from pathlib import Path

GS = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories')
sys.path.insert(0, str(GS))
from sim.feeder import Feeder  # noqa: E402
from opendssdirect import dss  # noqa: E402

TMP = Path(sys.argv[1])
S = json.loads((TMP / 'volt_v2_states.json').read_text())
R = json.loads((GS / 'ui' / 'dist' / 'replays.json').read_text())
T = json.loads((GS / 'ui' / 'dist' / 'topology.json').read_text())
M = json.loads((GS / 'ui' / 'dist' / 'model.json').read_text())
CORE_KVA = 20.0; QMAX = 0.44 * CORE_KVA  # ASSUMPTION, same as volt-analysis.py

t0 = time.time()
f = Feeder()
dss.Loads.Name('bat_' + f.homes[0]['id']); FRESH_PF = dss.Loads.PF()
weak = M['shaping']['weakLine']; dss.Lines.Name(weak); dss.Lines.Length(M['shaping']['modifiedLengthKm'])
SOURCE = 'p1udt17263-p1uhs19_1247x'
home_ids = [h['id'] for h in f.homes]; core_ids = sorted(h['id'] for h in T['homes'] if h['battery']); core_set = set(core_ids)
hmeta = {h['id']: h for h in T['homes']}

# ---------- graph with element names so a path can be turned into its line list ----------
graph = defaultdict(list); lines = {}
for ln in dss.Lines:
    a, b = ln.Bus1().split('.')[0], ln.Bus2().split('.')[0]
    L = ln.Length(); assert ln.Units() in (0, 3)
    n = ln.Phases(); Rm = ln.RMatrix(); Xm = ln.XMatrix()
    diag = [i * n + i for i in range(n)]; off = [i * n + j for i in range(n) for j in range(n) if i != j]
    Rs = sum(Rm[k] for k in diag) / n; Xs = sum(Xm[k] for k in diag) / n
    Rmu = sum(Rm[k] for k in off) / len(off) if off else 0.0; Xmu = sum(Xm[k] for k in off) / len(off) if off else 0.0
    dss.Circuit.SetActiveBus(a); kvb = dss.Bus.kVBase()
    kind = 'primary' if kvb > 1 else 'secondary' if abs(kvb - 0.12) < 1e-3 else 'otherLV'
    name = ln.Name()
    lines[name] = {'kind': kind, 'n': n, 'km': L, 'self': (Rs, Xs), 'seq': (Rs - Rmu, Xs - Xmu) if n >= 2 else (Rs, Xs)}
    w = max(L, 1e-5); graph[a].append((b, w, name)); graph[b].append((a, w, name))
for _ in dss.Transformers:
    bs = [s.split('.')[0] for s in dss.CktElement.BusNames()]
    for x in bs[1:]:
        if x != bs[0]: graph[bs[0]].append((x, 0.0, None)); graph[x].append((bs[0], 0.0, None))
dist = {SOURCE: 0.0}; parent = {}; q = [(0.0, SOURCE)]
while q:
    d, a = heapq.heappop(q)
    if d > dist[a]: continue
    for b, w, nm in graph[a]:
        if d + w < dist.get(b, 1e30): dist[b] = d + w; parent[b] = (a, nm); heapq.heappush(q, (d + w, b))

def path_lines(target):
    out = []; b = target
    while b != SOURCE:
        a, nm = parent[b]
        if nm: out.append(nm)
        b = a
    return out[::-1]

def rx_stats(names, basis):
    rows = [lines[n] for n in names]
    km = sum(r['km'] for r in rows)
    if km == 0: return None
    sR = sum(r[basis][0] * r['km'] for r in rows); sX = sum(r[basis][1] * r['km'] for r in rows)
    wm = sum(r[basis][0] / r[basis][1] * r['km'] for r in rows) / km
    return {'km': round(km, 3), 'lines': len(rows), 'ratioOfSums': round(sR / sX, 3), 'kmWeightedMeanOfRatios': round(wm, 3),
            'ohmsR': round(sR, 4), 'ohmsX': round(sX, 4)}

# ---------- state set-up (same inputs as volt-analysis.py) ----------
def setup(s, variant='unityPf', p_over=None, q_inj=None):
    """variant asBuilt = PF 0.88 Cores (the replay); unityPf = kvar 0; q_inj {core: kvar injected} applied on top of unity."""
    f.load(s['loadFactor']); powers = dict(s['powers']); powers.update(p_over or {}); f.battery(powers)
    for u in core_ids:
        dss.Loads.Name('bat_' + u)
        if variant == 'asBuilt': dss.Loads.PF(FRESH_PF); dss.Loads.kW(powers.get(u, 0))
        else: dss.Loads.kvar(-(q_inj or {}).get(u, 0.0))
    dss.Solution.Solve(); assert dss.Solution.Converged()

def node_v(bus, node):
    dss.Circuit.SetActiveBus(bus); ns = dss.Bus.Nodes(); v = dss.Bus.puVmagAngle()[::2]
    return v[ns.index(node)]

def home_min_leg(h):
    dss.Circuit.SetActiveBus(h); ns = dss.Bus.Nodes(); v = dss.Bus.puVmagAngle()[::2]
    return ns[v.index(min(v))], min(v)

def chain_for(h):
    tf = f.transformers[hmeta[h]['tf']]
    dss.Circuit.SetActiveElement('Transformer.' + tf['id']); bn = dss.CktElement.BusNames()
    prim_bus, prim_node = bn[0].split('.')[0], int(bn[0].split('.')[1])
    leg, _ = home_min_leg(h)
    return {'home': h, 'leg': leg, 'transformer': tf['id'], 'transformerKva': tf['kva'], 'tapBus': prim_bus, 'tapNode': prim_node,
            'lvBus': tf['secondary'], 'sourceNode': prim_node}

def points(c):
    leg, vmin = home_min_leg(c['home'])
    return {'source': node_v(SOURCE, c['sourceNode']), 'tap': node_v(c['tapBus'], c['tapNode']),
            'lv': node_v(c['lvBus'], c['leg']), 'home': node_v(c['home'], c['leg']), 'homeMinOverLegs': vmin, 'lowLeg': leg}

def split(p):
    return {'primary': p['source'] - p['tap'], 'transformer': p['tap'] - p['lv'], 'service': p['lv'] - p['home'], 'homePu': p['home']}

def diff(a, b):  # voltage GAIN at the home from a -> b, per segment (positive = voltage higher in b)
    sa, sb = split(a), split(b)
    return {k: round(sa[k] - sb[k], 5) for k in ('primary', 'transformer', 'service')} | {'total': round(sb['homePu'] - sa['homePu'], 5),
            'homeMinOverLegsGain': round(b['homeMinOverLegs'] - a['homeMinOverLegs'], 5), 'homeMinOverLegsAfter': round(b['homeMinOverLegs'], 5),
            'lowLegAfter': b['lowLeg']}

def r5(d): return {k: round(v, 5) if isinstance(v, float) else v for k, v in d.items()}

states_by_key = {s['key']: s for s in S['states']}
TARGETS = [k for k in ('rebound.naive.3', f"rebound.naive.{S['timeline']['worstUnityReboundNaiveStep']}") if k in states_by_key]
TARGETS = list(dict.fromkeys(TARGETS))
out = {'meta': {'generatedAtUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'status': 'SIM solves; splits, sensitivities and ratios DERIVED',
                'segments': 'primary = source phase node -> transformer primary node; transformer = primary node -> LV bus on the home\'s low leg; service = LV bus -> home, same leg',
                'sign': 'drops are positive pu; gains are positive when the home voltage rises'},
       'states': {}}

for key in TARGETS:
    sv = states_by_key[key]; s = R[sv['scenario']][sv['policy']][sv['step']]
    setup(s, 'unityPf')
    wh = min(home_ids, key=lambda x: home_min_leg(x)[1])
    assert abs(home_min_leg(wh)[1] - sv['unityPf']['counts']['homes']['minPu']) < 2e-5, (key, wh)
    c = chain_for(wh); base = points(c)
    own_core = wh in core_set; own_kw = s['powers'].get(wh, 0.0)
    st = {'clock': sv['clock'], 'worstHomeUnityPf': wh, 'label': hmeta[wh]['label'], 'chain': c, 'ownCore': own_core, 'ownCoreKW': own_kw,
          'unityPfDrop': r5(split(base))}
    # --- 1. small-signal sensitivities, central difference, +/- 1 kW or kvar ---
    sens = {}
    for scope, who in (('ownCore', [wh] if own_core else []), ('fleet96', core_ids)):
        if not who: continue
        res = {}
        for lever in ('kW', 'kvar'):
            pts = []
            for sgn in (+1, -1):
                if lever == 'kW':  # +1 = 1 kW LESS charging (more discharge) per Core
                    setup(s, 'unityPf', p_over={u: s['powers'].get(u, 0.0) - sgn * 1.0 for u in who})
                else:              # +1 = 1 kvar injected per Core
                    setup(s, 'unityPf', q_inj={u: sgn * 1.0 for u in who})
                pts.append(split(points(c)))
            res[lever] = {k: (pts[1][k] - pts[0][k]) / 2 for k in ('primary', 'transformer', 'service')}  # drop reduction per unit
            res[lever]['total'] = (pts[0]['homePu'] - pts[1]['homePu']) / 2
        ratio = {k: round(res['kW'][k] / res['kvar'][k], 2) if abs(res['kvar'][k]) > 1e-9 else None for k in ('primary', 'transformer', 'service', 'total')}
        sens[scope] = {'perKW': {k: round(v, 6) for k, v in res['kW'].items()}, 'perKvar': {k: round(v, 6) for k, v in res['kvar'].items()},
                       'effectiveRoverX': ratio, 'coresPerturbed': len(who)}
    st['sensitivity'] = sens
    # --- 2. finite changes along the same chain ---
    fin = {}
    setup(s, 'asBuilt'); ab = points(c)
    fin['pfBugToUnity'] = {'what': 'PF 0.88 replay (bug) -> unity PF, same kW', **diff(ab, base)}
    vv = dict(zip(S['feeder']['coreIds'], sv['voltVar']['perCoreKvar'])) if 'perCoreKvar' in sv['voltVar'] else None
    if vv is not None:
        setup(s, 'unityPf', q_inj=vv); fin['voltVarCatB'] = {'what': 'unity PF -> IEEE 1547-2018 Cat B default volt-var (steady state from volt-analysis.py)', **diff(base, points(c))}
    setup(s, 'unityPf', q_inj={u: QMAX for u in core_ids}); fin['ceilingAll96'] = {'what': f'unity PF -> all 96 Cores inject {QMAX} kvar (capability bound)', **diff(base, points(c))}
    if own_core:
        setup(s, 'unityPf', q_inj={wh: QMAX}); fin['ceilingOwnCoreOnly'] = {'what': f'unity PF -> only the worst home\'s Core injects {QMAX} kvar', **diff(base, points(c))}
        setup(s, 'unityPf', p_over={wh: 0.0}); fin['ownCoreIdle'] = {'what': f'unity PF -> the worst home\'s Core idle instead of charging {own_kw} kW (others unchanged)', **diff(base, points(c))}
    aw = R[sv['scenario']]['aware'][sv['step']]
    setup(aw, 'unityPf'); fin['awareKW'] = {'what': f"unity PF, naive kW -> aware controller's kW at {sv['clock']} (fleet {round(sum(aw['powers'].values()), 1)} kW vs {round(sum(s['powers'].values()), 1)} kW)", **diff(base, points(c))}
    st['finiteChanges'] = fin
    # --- 3. impedance basis on the same path ---
    pl = path_lines(wh)
    st['pathLines'] = {'primary': [n for n in pl if lines[n]['kind'] == 'primary'], 'secondary': [n for n in pl if lines[n]['kind'] == 'secondary']}
    st['pathIncludesWeakLine'] = any(n.lower() == weak.lower() for n in pl)
    st['impedance'] = {kind: {'loopOrPositiveSequence': rx_stats(names, 'seq'), 'self': rx_stats(names, 'self')}
                       for kind, names in st['pathLines'].items()}
    # --- 4. the home's transformer ---
    dss.Transformers.Name(c['transformer'])
    rw = []
    for w in range(1, dss.Transformers.NumWindings() + 1):
        dss.Transformers.Wdg(w); rw.append(dss.Transformers.R())
    xhl, xht, xlt = dss.Transformers.Xhl(), dss.Transformers.Xht(), dss.Transformers.Xlt()
    tfx = {'windings': len(rw), 'pctR': [round(x, 4) for x in rw], 'XHL': xhl, 'XHT': xht, 'XLT': xlt}
    if len(rw) == 3:
        xh, xl, xt = (xhl + xht - xlt) / 2, (xhl + xlt - xht) / 2, (xht + xlt - xhl) / 2
        r240, x240 = rw[0] + (rw[1] + rw[2]) / 4, xh + (xl + xt) / 4
        tfx.update({'leg1_120V': {'pctR': round(rw[0] + rw[1], 4), 'pctX': xhl, 'XoverR': round(xhl / (rw[0] + rw[1]), 2)},
                    'leg2_120V': {'pctR': round(rw[0] + rw[2], 4), 'pctX': xht, 'XoverR': round(xht / (rw[0] + rw[2]), 2)},
                    'lineToLine_240V': {'pctR': round(r240, 4), 'pctX': round(x240, 4), 'XoverR': round(x240 / r240, 2),
                                        'formula': 'star equivalent XH=(XHL+XHT-XLT)/2, XX1=(XHL+XLT-XHT)/2, XX2=(XHT+XLT-XHL)/2; each 120 V half-winding carries 0.5 pu of its own base for a 240 V load, so Z240 = Z_H + (Z_X1 + Z_X2)/4'}})
    st['transformer'] = tfx
    out['states'][key] = st
    print(key, wh, 'drop', {k: round(v, 4) for k, v in split(base).items()}, flush=True)
    print('   sens', json.dumps(sens)[:600], flush=True)
    for k, v in fin.items(): print('   fin', k, {kk: vv_ for kk, vv_ in v.items() if kk != 'what'}, flush=True)
    print('   tf', tfx, flush=True)
    print('   Z', st['impedance'], 'tf', tfx.get('lineToLine_240V', {}).get('XoverR'), 'weak on path', st['pathIncludesWeakLine'], flush=True)

# ---------- feeder-wide impedance basis ----------
fw = {}
for kind in ('primary', 'secondary'):
    names = [n for n, r in lines.items() if r['kind'] == kind]
    fw[kind] = {'loopOrPositiveSequence': rx_stats(names, 'seq'), 'self': rx_stats(names, 'self'),
                'byPhases': {str(k): {'loopOrPositiveSequence': rx_stats([n for n in names if lines[n]['n'] == k], 'seq'),
                                      'self': rx_stats([n for n in names if lines[n]['n'] == k], 'self')}
                             for k in sorted({lines[n]['n'] for n in names})}}
out['feederWide'] = fw
# fleet transformer X/R (240 V line-to-line star equivalent), kVA-weighted
xr = []
for tf in f.transformers:
    dss.Transformers.Name(tf['id']); nw = dss.Transformers.NumWindings()
    rw = []
    for w in range(1, nw + 1): dss.Transformers.Wdg(w); rw.append(dss.Transformers.R())
    if nw == 3:
        xhl, xht, xlt = dss.Transformers.Xhl(), dss.Transformers.Xht(), dss.Transformers.Xlt()
        xh, xl, xt = (xhl + xht - xlt) / 2, (xhl + xlt - xht) / 2, (xht + xlt - xhl) / 2
        xr.append((tf['kva'], (xh + (xl + xt) / 4) / (rw[0] + (rw[1] + rw[2]) / 4), xhl / (rw[0] + rw[1]), xht / (rw[0] + rw[2])))
out['transformersFleet'] = {'splitPhase3Winding': len(xr), 'other': len(f.transformers) - len(xr),
                            'kvaWeightedXoverR_240V': round(sum(k * a for k, a, _, _ in xr) / sum(k for k, *_ in xr), 2),
                            'range240V': [round(min(a for _, a, _, _ in xr), 2), round(max(a for _, a, _, _ in xr), 2)],
                            'kvaWeightedXoverR_leg1': round(sum(k * b for k, _, b, _ in xr) / sum(k for k, *_ in xr), 2),
                            'kvaWeightedXoverR_leg2': round(sum(k * c for k, _, _, c in xr) / sum(k for k, *_ in xr), 2)}
# reproduce the v2 numbers that the review challenged
sec_all = [n for n, r in lines.items() if r['kind'] == 'secondary']
out['v2Reproduction'] = {
    'what': 'v2 spec said "120/240 V cables R/X 1.93 (km-weighted, 27.8 km), primary 0.46". Reproduced here on the SELF-impedance basis to show the mismatch in scope.',
    'secondaryFeederWideSelfKmWeightedMean': rx_stats(sec_all, 'self')['kmWeightedMeanOfRatios'],
    'primaryFeederWideSelfKmWeightedMean': fw['primary']['self']['kmWeightedMeanOfRatios'],
    'primaryWorstPathSelfRatioOfSums': {k: v['impedance']['primary']['self']['ratioOfSums'] for k, v in out['states'].items()},
}
print('feederWide', json.dumps(fw)); print('tfFleet', out['transformersFleet']); print('v2', out['v2Reproduction'])
out['meta']['runSeconds'] = round(time.time() - t0, 2)
(TMP / 'volt_v2_impedance.json').write_text(json.dumps(out, separators=(',', ':')))
