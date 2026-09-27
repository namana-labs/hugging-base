"""res (Reserves and their deployability): fleet reserve on the SMART-DS feeder.

For every replay state (heatwave/rebound x naive/aware x 13 steps) we ask:
if the 96-Core fleet were called for reserve right now, how many kW could it
deliver (a) on paper, (b) through the feeder without violations (OpenDSS), and
(c) for the duration the ERCOT product needs (energy above the 20% floor)?

Element limits checked: distribution transformers (% of winding kVA, as the prototype does),
home voltage band, and every OpenDSS Line element (primary, secondary, pad switches, fuses,
feeder head) against its NormAmps. The prototype controller checks only the first two.

Status of outputs: SIM (OpenDSS on SMART-DS with scripted inputs) and DERIVED.
Inputs: replays.json (SIM), sim.constants (ASSUMPTIONs marked there).
Usage: python res-sim.py OUT.json
"""
import sys, json, math, time, collections
GS = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories'
sys.path.insert(0, GS)
from sim.feeder import Feeder
from sim.splitter import allocate
from sim.constants import CORE_POWER_KW, CORE_USABLE_KWH, CORE_ROUND_TRIP_EFFICIENCY, RESERVE_FLOOR
from opendssdirect import dss

OUT = sys.argv[1]
# optional: comma list of scenario/policy/step to run (e.g. heatwave/aware/7); default = all 52 states
ONLY = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
R = json.load(open(GS + '/ui/dist/replays.json'))
M = json.load(open(GS + '/ui/dist/model.json'))

t0 = time.time()
f = Feeder()
# Reproduce the replay feeder exactly: build_replays.py lengthens one primary line 3x.
sh = M['shaping']
dss.Lines.Name(sh['weakLine']); dss.Lines.Length(sh['modifiedLengthKm'])
homes = {h['id']: h for h in f.homes}
for i, h in enumerate(f.homes):
    h['index'] = i
cedar = set(sh['denseHomes'])
IDS = sorted(R['heatwave']['aware'][0]['powers'].keys())
assert len(IDS) == 96
ETA = math.sqrt(CORE_ROUND_TRIP_EFFICIENCY)  # one-way efficiency, same as sim/devices.py
NAMEPLATE = CORE_POWER_KW * len(IDS)
DURATIONS = {'0.5': 0.5, '1': 1.0, '4': 4.0}  # h: Reg/RRS 30 min, ECRS 1 h (NPRR1282), Non-Spin 4 h
LMAX, VLO, VHI = 99.5, 0.9505, 1.0495     # prototype controller margins (sim/splitter.py); reused for lines
TOL = 0.05                                 # % / pu*100 slack when an element is already over at idle

# ---- line table + which batteries sit downstream of each line --------------------------------
LINE_NAMES = [n for n in dss.PDElements.AllNames() if n.lower().startswith('line.')]
line_info = {}
adj = collections.defaultdict(list)
for ln in dss.Lines:
    name = 'Line.' + ln.Name()
    a, b = ln.Bus1().split('.')[0], ln.Bus2().split('.')[0]
    dss.Circuit.SetActiveBus(a)
    line_info[name.lower()] = {'id': name, 'normAmps': ln.NormAmps(), 'kVBase': round(dss.Bus.kVBase(), 4), 'linecode': ln.LineCode()}
    adj[a].append((b, name.lower())); adj[b].append((a, name.lower()))
for t in f.transformers:
    adj[t['primary']].append((t['secondary'], None)); adj[t['secondary']].append((t['primary'], None))
SRC = f.source and 'p1udt17263-p1uhs19_1247x'
parent = {SRC: (None, None)}; dq = collections.deque([SRC])
while dq:
    a = dq.popleft()
    for b, el in adj[a]:
        if b not in parent:
            parent[b] = (a, el); dq.append(b)
down = collections.defaultdict(set)     # line name (lower) -> battery ids downstream
for u in IDS:
    bus = u
    while parent.get(bus, (None, None))[0] is not None:
        up, el = parent[bus]
        if el:
            down[el].add(u)
        bus = up
HEAD = max(down, key=lambda k: len(down[k]))  # the element every battery sits behind
nsolve = 0


def solve():
    global nsolve
    nsolve += 1
    r = f.solve(True)
    names = dss.PDElements.AllNames(); pct = dss.PDElements.AllPctNorm(False)
    r['lines'] = {n.lower(): p for n, p in zip(names, pct) if n.lower().startswith('line.')}
    return r


def limits_from(idle):
    """Batteries may not push any element past its limit, or make an already-over element worse."""
    return {'tf': [max(LMAX, x + TOL) for x in idle['loading']],
            'vlo': [min(VLO, x - TOL / 100) for x in idle['voltage']],
            'vhi': [max(VHI, x + TOL / 100) for x in idle['voltageMax']],
            'line': {k: max(LMAX, p + TOL) for k, p in idle['lines'].items()}}


def violations(r, lim):
    tf = [i for i, x in enumerate(r['loading']) if x > lim['tf'][i]]
    vv = [i for i, (lo, hi) in enumerate(zip(r['voltage'], r['voltageMax'])) if lo < lim['vlo'][i] or hi > lim['vhi'][i]]
    ln = [k for k, p in r['lines'].items() if p > lim['line'][k]]
    return tf, vv, ln


def summary(r, lim):
    tf, vv, ln = violations(r, lim)
    return {'transformersOver': len(tf), 'voltageViolations': len(vv), 'linesOver': len(ln),
            'maxTransformerPct': r['maxLoading'], 'maxLinePct': round(max(r['lines'].values()), 2),
            'minVoltagePu': r['minVoltage'], 'maxVoltagePu': r['maxVoltage']}


class Capped:
    """Stands in for sim.devices.Battery inside the prototype allocate(): clamps to a kW cap."""
    def __init__(self, up, down_):
        self.up, self.down = up, down_

    def limit(self, p):
        return max(-self.up, min(self.down, p))


def caps_for(socs, direction, hours):
    out = {}
    for u in IDS:
        s = socs[u]
        if hours is None:
            e = CORE_POWER_KW
        elif direction == 'up':
            e = max(0.0, s - RESERVE_FLOOR) * CORE_USABLE_KWH * ETA / hours
        else:
            e = max(0.0, 1.0 - s) * CORE_USABLE_KWH / ETA / hours
        out[u] = min(CORE_POWER_KW, e)
    return out


def paper(load, caps, sign, lim):
    f.load(load); f.battery({u: sign * caps[u] for u in IDS}); r = solve()
    tf, vv, ln = violations(r, lim)
    return {'kW': round(sum(caps.values()), 1), **summary(r, lim)}, (tf, vv, ln, r)


def prototype(load, caps, sign, lim):
    """(1) the team's aware controller (sim/splitter.py) as built: transformer + voltage only.
       (2) the same allocation scaled down uniformly until every element incl. lines passes."""
    f.load(load); f.battery({}); base = f.solve(True)
    devices = {u: (Capped(caps[u], 0) if sign < 0 else Capped(0, caps[u])) for u in IDS}
    power, r0 = allocate(f, devices, sign * sum(caps.values()), 'aware', base)
    f.battery(power); r = solve()
    built = {'kW': round(abs(sum(power.values())), 1), **summary(r, lim)}
    if not any(violations(r, lim)):
        return built, {'kW': built['kW'], **summary(r, lim)}, power
    lo, hi = 0.0, 1.0
    for _ in range(14):
        s = (lo + hi) / 2
        f.battery({k: v * s for k, v in power.items()}); rr = solve()
        if any(violations(rr, lim)):
            hi = s
        else:
            lo = s
    p2 = {k: v * lo for k, v in power.items()}
    f.battery(p2); rr = solve()
    return built, {'kW': round(abs(sum(p2.values())), 1), 'scale': round(lo, 4), **summary(rr, lim)}, p2


def targeted(load, caps, sign, lim):
    """Heuristic written for this panel (not the prototype controller): cut only the Cores behind an
    element that is over its limit (their transformer, or any line they sit downstream of), 5% per
    iteration; a voltage violation cuts the Cores on that home's transformer; if a violation has no
    Core behind it, 2% on everyone."""
    f.load(load)
    p = {u: sign * caps[u] for u in IDS}
    for it in range(800):
        f.battery(p); r = solve()
        tf, vv, ln = violations(r, lim)
        if not (tf or vv or ln):
            break
        bad_tf = set(tf) | {f.homes[i]['tf'] for i in vv}
        hit = {u for u in IDS if homes[u]['tf'] in bad_tf}
        for k in ln:
            hit |= down.get(k, set())
        hit = [u for u in hit if abs(p[u]) > 1e-6]
        if hit:
            for u in hit:
                p[u] *= 0.95
        else:
            for u in IDS:
                p[u] *= 0.98
    else:
        raise RuntimeError('targeted curtailment did not converge')
    return {'kW': round(abs(sum(p.values())), 1), 'iterations': it, **summary(r, lim)}, p


def element_list(tf, vv, ln, r):
    out = []
    for i in tf:
        t = f.transformers[i]
        out.append({'kind': 'transformer', 'id': t['id'], 'ratingKVA': t['kva'], 'pct': round(r['loading'][i], 1),
                    'cores': sum(1 for u in IDS if homes[u]['tf'] == i)})
    for k in ln:
        li = line_info[k]
        kind = 'feeder head' if k == HEAD else ('switch/fuse' if ('padswitch' in k or 'fuse' in k) else ('primary line' if li['kVBase'] > 1 else 'secondary line'))
        out.append({'kind': kind, 'id': li['id'], 'normAmps': li['normAmps'], 'pct': round(r['lines'][k], 1), 'cores': len(down.get(k, ()))})
    for i in vv:
        out.append({'kind': 'voltage', 'id': f.homes[i]['id'], 'minPu': r['voltage'][i], 'maxPu': r['voltageMax'][i],
                    'cores': sum(1 for u in IDS if homes[u]['tf'] == f.homes[i]['tf'])})
    return sorted(out, key=lambda x: -x.get('pct', 0))


def stranded_by_tf(caps, power):
    rows = {}
    for u in IDS:
        t = homes[u]['tf']
        row = rows.setdefault(t, {'transformer': f.transformers[t]['id'], 'kva': f.transformers[t]['kva'],
                                  'cores': 0, 'cedarCores': 0, 'offeredKW': 0.0, 'deliverableKW': 0.0})
        row['cores'] += 1; row['cedarCores'] += u in cedar
        row['offeredKW'] += caps[u]; row['deliverableKW'] += abs(power.get(u, 0))
    out = []
    for row in rows.values():
        row['strandedKW'] = round(row['offeredKW'] - row['deliverableKW'], 1)
        row['offeredKW'] = round(row['offeredKW'], 1); row['deliverableKW'] = round(row['deliverableKW'], 1)
        if row['strandedKW'] > 0.05:
            out.append(row)
    return sorted(out, key=lambda x: -x['strandedKW'])


states = []; detail = {}
DEFAULTS = {('heatwave', 'aware', 7), ('rebound', 'aware', 3)}
for sc in ['heatwave', 'rebound']:
    for pol in ['naive', 'aware']:
        for s in R[sc][pol]:
            if ONLY and f"{sc}/{pol}/{s['step']}" not in ONLY:
                continue
            socs = s['soc']; load = s['loadFactor']; vals = list(socs.values())
            f.load(load); f.battery({}); idle = solve(); lim = limits_from(idle)
            st = {'scenario': sc, 'policy': pol, 'step': s['step'], 'minute': s['minute'],
                  'clock': f"{s['minute']//60:02d}:{s['minute']%60:02d}", 'loadFactor': load,
                  'socMean': round(sum(vals)/len(vals), 4), 'socMin': round(min(vals), 4), 'socMax': round(max(vals), 4),
                  'replayDispatchKW': round(sum(s['powers'].values()), 1),  # + charging, - discharging
                  'replayTargetKW': s['targetKW'], 'replayDeliveredKW': s['deliveredKW'],
                  'idle': {'maxTransformerPct': idle['maxLoading'], 'maxLinePct': round(max(idle['lines'].values()), 2),
                           'headPct': round(idle['lines'][HEAD], 2), 'minVoltagePu': idle['minVoltage'], 'maxVoltagePu': idle['maxVoltage']}}
            for direction, sign in [('up', -1), ('down', +1)]:
                d = {'nameplateKW': NAMEPLATE}
                full = caps_for(socs, direction, None)
                d['paper'], pv = paper(load, full, sign, lim)
                d['prototypeAsBuilt'], d['prototypeAllElements'], pp = prototype(load, full, sign, lim)
                d['targeted'], tp = targeted(load, full, sign, lim)
                d['byDuration'] = {}
                # downward (extra charging) only needs the 30-min Reg-Down duration; 1 h / 4 h are upward products
                for key, hrs in (DURATIONS.items() if direction == 'up' else [('0.5', 0.5)]):
                    c = caps_for(socs, direction, hrs)
                    b, a, _ = prototype(load, c, sign, lim)
                    tg, _ = targeted(load, c, sign, lim)
                    d['byDuration'][key] = {'energyCapKW': round(sum(c.values()), 1), 'prototypeAsBuiltKW': b['kW'],
                                            'prototypeAsBuiltLinesOver': b['linesOver'],
                                            'prototypeAllElementsKW': a['kW'], 'targetedKW': tg['kW']}
                st[direction] = d
                if (sc, pol, s['step']) in DEFAULTS:
                    detail[f"{sc}/{pol}/{s['step']}/{direction}"] = {
                        'paperOverLimit': element_list(*pv),
                        'prototypeStrandedByTransformer': stranded_by_tf(full, pp)[:12],
                        'targetedStrandedByTransformer': stranded_by_tf(full, tp)[:12]}
            states.append(st)
            u, dn = st['up'], st['down']
            print(sc, pol, s['step'], st['clock'], 'soc', st['socMean'],
                  '| UP paper', u['paper']['transformersOver'], u['paper']['linesOver'], u['paper']['voltageViolations'],
                  'proto', u['prototypeAsBuilt']['kW'], '(lines over', u['prototypeAsBuilt']['linesOver'], ') all', u['prototypeAllElements']['kW'],
                  'tgt', u['targeted']['kW'], 'ECRS', u['byDuration']['1']['prototypeAllElementsKW'], u['byDuration']['1']['targetedKW'],
                  'NSRS', u['byDuration']['4']['prototypeAllElementsKW'],
                  '| DOWN proto', dn['prototypeAsBuilt']['kW'], '(lines', dn['prototypeAsBuilt']['linesOver'], ') all', dn['prototypeAllElements']['kW'],
                  'tgt', dn['targeted']['kW'], flush=True)

json.dump({'states': states, 'binding': detail, 'meta': {
    'engine': dss.Basic.Version().split('\n')[0], 'solves': nsolve, 'seconds': round(time.time()-t0, 1),
    'weakLine': sh['weakLine'], 'homes': len(f.homes), 'transformers': len(f.transformers), 'lines': len(LINE_NAMES),
    'head': line_info[HEAD], 'headCoresDownstream': len(down[HEAD]),
    'fleet': len(IDS), 'cedarCores': len(cedar & set(IDS)), 'eta': ETA,
    'margins': {'maxTransformerPct': LMAX, 'maxLinePctOfNormAmps': LMAX, 'minVoltagePu': VLO, 'maxVoltagePu': VHI,
                'alreadyOverAtIdle': f'limit = idle value + {TOL} (batteries may not make it worse)'}}}, open(OUT, 'w'))
print('done', nsolve, 'solves', round(time.time()-t0, 1), 's')
