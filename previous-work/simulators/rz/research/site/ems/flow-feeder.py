"""flow item: every line / switch / transformer on the SMART-DS feeder vs its thermal limit.

SIM: prototype OpenDSS snapshot solves of NREL SMART-DS p1uhs19_1247--p1udt17263 with the
prototype's scripted load factor and battery powers (hugging-base/demos/grid-stories).
Writes a raw per-element JSON to the scratchpad; flow-build.py compacts it for the site (rev 2 adds the size-consistent rating basis there; no solve changes).
"""
import sys, json, math, time
sys.path.insert(0, '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories')
from sim.feeder import Feeder
from opendssdirect import dss

DIST = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories/ui/dist/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/flow_raw.json'
t0 = time.time()
replays = json.load(open(DIST + 'replays.json'))
topo = json.load(open(DIST + 'topology.json'))
shaping = topo['shaping']

f = Feeder()
# Reproduce build_replays.py shaping: one primary segment lengthened 3x electrically.
dss.Lines.Name(shaping['weakLine'])
assert abs(dss.Lines.Length() - shaping['originalLengthKm']) < 1e-9, dss.Lines.Length()
dss.Lines.Length(shaping['modifiedLengthKm'])

HEAD = 'l(r:p1udt17263-p1uhs19_1247)'

# Static element table
coords = {}
for line in open('/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories/data/smartds/Buscoords.dss'):
    p = line.split()
    if len(p) == 3:
        coords[p[0]] = [float(p[1]), float(p[2])]

lines = []
for ln in dss.Lines:
    name = ln.Name()
    b1 = ln.Bus1().split('.')[0]; b2 = ln.Bus2().split('.')[0]
    dss.Circuit.SetActiveBus(b1); kvb = dss.Bus.kVBase()
    code = ln.LineCode()
    if name == HEAD:
        typ = 'head'
    elif name.startswith('padswitch') or name.startswith('fuse') or code.startswith('padswitch') or code.startswith('fuse'):
        typ = 'switch_fuse'
    elif kvb > 1:
        typ = 'primary_line'
    else:
        typ = 'secondary_line'
    c1 = coords.get(b1); c2 = coords.get(b2)
    mid = [round((c1[0] + c2[0]) / 2, 6), round((c1[1] + c2[1]) / 2, 6)] if c1 and c2 else (c1 or c2)
    lines.append({'id': name, 'type': typ, 'kind': 'line', 'linecode': code, 'phases': ln.Phases(),
                  'normAmps': ln.NormAmps(), 'emergAmps': ln.EmergAmps(), 'lengthKm': ln.Length(),
                  'kVBaseLN': round(kvb, 4), 'bus1': b1, 'bus2': b2, 'xy': mid})

# Orientation: which end of each line is nearer the substation (BFS hops over lines + transformers).
import collections
adj = collections.defaultdict(list)
for el in lines:
    adj[el['bus1']].append(el['bus2']); adj[el['bus2']].append(el['bus1'])
for tf in f.transformers:
    adj[tf['primary']].append(tf['secondary']); adj[tf['secondary']].append(tf['primary'])
SRC = 'p1udt17263-p1uhs19_1247x'
hop = {SRC: 0}; dq = collections.deque([SRC])
while dq:
    a = dq.popleft()
    for b in adj[a]:
        if b not in hop:
            hop[b] = hop[a] + 1; dq.append(b)
for el in lines:
    el['down'] = 1 if hop.get(el['bus1'], 1e9) <= hop.get(el['bus2'], 1e9) else -1

tfs = []
for i, tf in enumerate(f.transformers):
    dss.Circuit.SetActiveElement('Transformer.' + tf['id'])
    dss.Transformers.Name(tf['id']); dss.Transformers.Wdg(1)
    tfs.append({'id': tf['id'], 'type': 'transformer', 'kind': 'transformer', 'kva': tf['kva'],
                'phases': dss.CktElement.NumPhases(), 'xy': tf['coordinates'], 'idx': i})


def solve_case(load_factor, powers):
    f.load(load_factor); f.battery(powers)
    res = f.solve(detail=True)
    L = []
    for el in lines:
        dss.Circuit.SetActiveElement('Line.' + el['id'])
        cm = dss.CktElement.CurrentsMagAng()[::2]
        nc = dss.CktElement.NumConductors()
        amps = max(cm[:2 * nc]) if cm else 0.0
        p = dss.CktElement.Powers()
        pkw = sum(p[:2 * nc][::2]); qkvar = sum(p[:2 * nc][1::2])
        L.append({'amps': round(amps, 2), 'pct': round(amps / el['normAmps'] * 100, 2), 'kW': round(pkw, 2), 'kvar': round(qkvar, 2),
                  'kWdown': round(pkw * el['down'], 2)})
    T = []
    for i, tf in enumerate(tfs):
        dss.Circuit.SetActiveElement('Transformer.' + tf['id'])
        nc = dss.CktElement.NumConductors()
        v = dss.CktElement.Powers()[:2 * nc]
        p = sum(v[::2]); q = sum(v[1::2])
        kva = math.hypot(p, q)
        T.append({'kVA': round(kva, 2), 'pct': round(kva / tf['kva'] * 100, 2), 'kW': round(p, 2)})
    # head
    dss.Circuit.SetActiveElement('Line.' + HEAD)
    nc = dss.CktElement.NumConductors()
    pw = dss.CktElement.Powers()[:2 * nc]
    headP = sum(pw[::2]); headQ = sum(pw[1::2])
    dss.Circuit.SetActiveBus(lines[[x['id'] for x in lines].index(HEAD)]['bus1'])
    headV = dss.Bus.puVmagAngle()[::2]
    return {'lines': L, 'tfs': T, 'summary': res, 'head': {'kW': round(headP, 1), 'kvar': round(headQ, 1), 'kVA': round(math.hypot(headP, headQ), 1), 'vpu': [round(x, 5) for x in headV]}}


cases = [
    ('rebound_s3_naive', 'rebound', 'naive', 3),
    ('rebound_s3_aware', 'rebound', 'aware', 3),
    ('heatwave_s12_naive', 'heatwave', 'naive', 12),
    ('heatwave_s12_aware', 'heatwave', 'aware', 12),
]
out = {'engine': dss.Basic.Version(), 'shaping': shaping, 'lines': lines, 'transformers': tfs, 'cases': {}}
for cid, sc, pol, st in cases:
    step = replays[sc][pol][st]
    r = solve_case(step['loadFactor'], step['powers'])
    # reproduction check vs the published replay
    dl = max(abs(a - b) for a, b in zip(r['summary']['loading'], step['loading']))
    dv = max(abs(a - b) for a, b in zip(r['summary']['voltage'], step['voltage']))
    r['meta'] = {'scenario': sc, 'policy': pol, 'step': st, 'minute': step['minute'],
                 'clock': '%02d:%02d' % divmod(step['minute'], 60), 'loadFactor': step['loadFactor'],
                 'batteryKW': round(sum(step['powers'].values()), 1), 'nBatteries': len(step['powers']),
                 'charging': sum(1 for v in step['powers'].values() if v > 0.01),
                 'discharging': sum(1 for v in step['powers'].values() if v < -0.01),
                 'reproMaxAbsDiffTransformerPct': round(dl, 4), 'reproMaxAbsDiffVoltagePU': round(dv, 6),
                 'replayMaxLoading': step['maxLoading'], 'replayFeederMW': step['feederMW']}
    out['cases'][cid] = r
    print(cid, r['meta'], 'head', r['head'], flush=True)

# Reference: same rebound step-3 load with every battery idle (counterfactual, SIM)
step = replays['rebound']['naive'][3]
r = solve_case(step['loadFactor'], {})
r['meta'] = {'scenario': 'rebound', 'policy': 'idle', 'step': 3, 'minute': step['minute'], 'clock': '%02d:%02d' % divmod(step['minute'], 60),
             'loadFactor': step['loadFactor'], 'batteryKW': 0.0, 'nBatteries': len(step['powers']), 'charging': 0, 'discharging': 0}
out['cases']['rebound_s3_idle'] = r
print('rebound_s3_idle head', r['head'], flush=True)

# Without shaping (sanity: how much does the prototype's weak-line edit matter?)
dss.Lines.Name(shaping['weakLine']); dss.Lines.Length(shaping['originalLengthKm'])
step = replays['rebound']['naive'][3]
r = solve_case(step['loadFactor'], step['powers'])
out['noShapingCheck'] = {'case': 'rebound_s3_naive', 'maxLinePct': max(x['pct'] for x in r['lines']),
                         'maxTfPct': max(x['pct'] for x in r['tfs']), 'head': r['head'], 'minV': r['summary']['minVoltage']}
dss.Lines.Name(shaping['weakLine']); dss.Lines.Length(shaping['modifiedLengthKm'])
print('noShaping', out['noShapingCheck'])
out['runSeconds'] = round(time.time() - t0, 1)
out['generatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
json.dump(out, open(OUT, 'w'))
print('done', out['runSeconds'], 's')
