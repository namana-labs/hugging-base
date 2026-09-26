"""res: co-optimized upward reserve on the SMART-DS feeder (SIM), added after adversarial review.

res-sim.py asks "if the fleet were IDLE at this SoC and were called now". That over-states what a fleet that is
already discharging for energy can add. Here the replay's own energy dispatch is HELD for the whole product
duration, and we ask how much EXTRA upward reserve each Core can add on top of it:

    per Core u, base point p_b (kW at the terminal, + = discharging; the replay's powers use + = charging, so p_b = -powers[u])
    S_u   = max(0, SoC_u - 0.20) x 37 kWh                          (stored energy above the backup floor)
    r_u   = max(0, min(20 - p_b, S_u x sqrt(0.89) / H - p_b))       (power headroom; energy for base point + reserve over H)

For a charging Core (p_b < 0) the same formula counts stopping the charge as upward reserve, which is exact for
net output: the Core discharges (r_u - c) for H hours. Charging energy gained before the call is not credited.

Downward (extra charging, 30 min, Reg-Down-like), same idea with the replay charge c_b (+ = charging) held:
    d_u   = max(0, min(20 - c_b, (1 - SoC_u) x 37 kWh / sqrt(0.89) / H - c_b))

Feeder check (same limits as res-sim.py): transformers <= 99.5% winding kVA, home voltage 0.9505-1.0495 pu, every
OpenDSS Line element <= 99.5% NormAmps. An element already over with the fleet idle, OR already over at the replay's
own dispatch, may not be made worse (+0.05 slack). The replay's dispatch is never cut; only the extra reserve is.
  - allElements: the extra vector r scaled down uniformly (16-step bisection) until every element passes
                 (the waterfall main path in res-sim.py is the same uniform cut; checked below)
  - targeted:    only the extra of Cores behind an element that is over is cut, 5% per iteration

Status: SIM (OpenDSS on SMART-DS with scripted replay inputs). Usage:
  lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 python res-coopt.py OUT.json [scenario/policy/step,...]
"""
import sys, json, math, time, collections
GS = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories'
sys.path.insert(0, GS)
from sim.feeder import Feeder
from sim.constants import CORE_POWER_KW, CORE_USABLE_KWH, CORE_ROUND_TRIP_EFFICIENCY, RESERVE_FLOOR
from opendssdirect import dss

OUT = sys.argv[1]
# optional: comma list of scenario/policy/step (e.g. heatwave/aware/7); default = all 52 replay states
ONLY = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
R = json.load(open(GS + '/ui/dist/replays.json'))
M = json.load(open(GS + '/ui/dist/model.json'))
t0 = time.time()
f = Feeder()
sh = M['shaping']
dss.Lines.Name(sh['weakLine']); dss.Lines.Length(sh['modifiedLengthKm'])   # same 3x weak-line edit as the replays
homes = {h['id']: h for h in f.homes}
IDS = sorted(R['heatwave']['aware'][0]['powers'].keys())
assert len(IDS) == 96
ETA = math.sqrt(CORE_ROUND_TRIP_EFFICIENCY)
DURATIONS = {'0.5': 0.5, '1': 1.0, '4': 4.0}
LMAX, VLO, VHI, TOL = 99.5, 0.9505, 1.0495, 0.05

# line -> batteries downstream (same tree walk as res-sim.py)
adj = collections.defaultdict(list)
for ln in dss.Lines:
    name = 'line.' + ln.Name().lower()
    a, b = ln.Bus1().split('.')[0], ln.Bus2().split('.')[0]
    adj[a].append((b, name)); adj[b].append((a, name))
for t in f.transformers:
    adj[t['primary']].append((t['secondary'], None)); adj[t['secondary']].append((t['primary'], None))
SRC = 'p1udt17263-p1uhs19_1247x'
parent = {SRC: (None, None)}; dq = collections.deque([SRC])
while dq:
    a = dq.popleft()
    for b, el in adj[a]:
        if b not in parent:
            parent[b] = (a, el); dq.append(b)
down = collections.defaultdict(set)
for u in IDS:
    bus = u
    while parent.get(bus, (None, None))[0] is not None:
        up, el = parent[bus]
        if el:
            down[el].add(u)
        bus = up
nsolve = 0


def solve():
    global nsolve
    nsolve += 1
    r = f.solve(True)
    names = dss.PDElements.AllNames(); pct = dss.PDElements.AllPctNorm(False)
    r['lines'] = {n.lower(): p for n, p in zip(names, pct) if n.lower().startswith('line.')}
    return r


def limits(*states):
    """Limit = the margin, or (if already over in any of the given reference states) that value + TOL."""
    lim = {'tf': [LMAX] * len(f.transformers), 'vlo': [VLO] * len(f.homes), 'vhi': [VHI] * len(f.homes),
           'line': {k: LMAX for k in states[0]['lines']}}
    for s in states:
        lim['tf'] = [max(a, x + TOL) for a, x in zip(lim['tf'], s['loading'])]
        lim['vlo'] = [min(a, x - TOL / 100) for a, x in zip(lim['vlo'], s['voltage'])]
        lim['vhi'] = [max(a, x + TOL / 100) for a, x in zip(lim['vhi'], s['voltageMax'])]
        lim['line'] = {k: max(lim['line'][k], p + TOL) for k, p in s['lines'].items()}
    return lim


def violations(r, lim):
    tf = [i for i, x in enumerate(r['loading']) if x > lim['tf'][i]]
    vv = [i for i, (lo, hi) in enumerate(zip(r['voltage'], r['voltageMax'])) if lo < lim['vlo'][i] or hi > lim['vhi'][i]]
    ln = [k for k, p in r['lines'].items() if p > lim['line'][k]]
    return tf, vv, ln


def count_over(r, lim):
    tf, vv, ln = violations(r, lim)
    return {'transformersOver': len(tf), 'voltageViolations': len(vv), 'linesOver': len(ln),
            'maxTransformerPct': r['maxLoading'], 'maxLinePct': round(max(r['lines'].values()), 2),
            'minVoltagePu': r['minVoltage'], 'maxVoltagePu': r['maxVoltage']}


def headroom(socs, powers, hours, direction='up'):
    """Extra kW per Core with the replay base point held for `hours`. up = more discharge, down = more charge."""
    out = {}
    for u in IDS:
        if direction == 'up':
            pb = -powers.get(u, 0.0)                       # + = discharging
            S = max(0.0, socs[u] - RESERVE_FLOOR) * CORE_USABLE_KWH * ETA
        else:
            pb = powers.get(u, 0.0)                        # + = charging
            S = max(0.0, 1.0 - socs[u]) * CORE_USABLE_KWH / ETA
        out[u] = max(0.0, min(CORE_POWER_KW - pb, S / hours - pb))
    return out


def uniform(load, base, extra, lim, sign=-1):
    """sign -1: extra is discharge (upward); +1: extra is charge (downward)."""
    f.load(load)
    f.battery({u: base.get(u, 0.0) + sign * extra[u] for u in IDS}); r = solve()
    total = sum(extra.values())
    if not any(violations(r, lim)):
        return round(total, 1), 1.0
    lo, hi = 0.0, 1.0
    for _ in range(16):
        s = (lo + hi) / 2
        f.battery({u: base.get(u, 0.0) + sign * extra[u] * s for u in IDS}); r = solve()
        if any(violations(r, lim)):
            hi = s
        else:
            lo = s
    return round(total * lo, 1), round(lo, 4)


def targeted(load, base, extra, lim, sign=-1):
    f.load(load)
    x = dict(extra)
    for it in range(800):
        f.battery({u: base.get(u, 0.0) + sign * x[u] for u in IDS}); r = solve()
        tf, vv, ln = violations(r, lim)
        if not (tf or vv or ln):
            return round(sum(x.values()), 1), it
        bad_tf = set(tf) | {f.homes[i]['tf'] for i in vv}
        hit = {u for u in IDS if homes[u]['tf'] in bad_tf}
        for k in ln:
            hit |= down.get(k, set())
        hit = [u for u in hit if x[u] > 1e-6]
        for u in (hit or IDS):
            x[u] *= 0.95 if hit else 0.98
    raise RuntimeError('targeted did not converge')


states = []
check = None
for sc in ['heatwave', 'rebound']:
    for pol in ['naive', 'aware']:
        for s in R[sc][pol]:
            if ONLY and f"{sc}/{pol}/{s['step']}" not in ONLY:
                continue
            socs, load, base = s['soc'], s['loadFactor'], s['powers']
            f.load(load); f.battery({}); idle = solve()
            f.battery(base); rep = solve()
            lim_idle = limits(idle)
            lim = limits(idle, rep)
            st = {'scenario': sc, 'policy': pol, 'step': s['step'], 'clock': f"{s['minute']//60:02d}:{s['minute']%60:02d}",
                  'replayDispatchKW': round(sum(base.values()), 1),
                  'replayDischargeKW': round(sum(-v for v in base.values() if v < 0), 1),
                  'replayChargeKW': round(sum(v for v in base.values() if v > 0), 1),
                  'replayVsIdleLimits': count_over(rep, lim_idle), 'byDuration': {}}
            for key, hrs in DURATIONS.items():
                ex = headroom(socs, base, hrs)
                u_kw, scale = uniform(load, base, ex, lim)
                row = {'headroomKW': round(sum(ex.values()), 1), 'allElementsKW': u_kw, 'scale': scale}
                if key in ('1', '4'):
                    row['targetedKW'], row['targetedIterations'] = targeted(load, base, ex, lim)
                st['byDuration'][key] = row
            exd = headroom(socs, base, 0.5, 'down')
            d_kw, d_scale = uniform(load, base, exd, lim, +1)
            d_tg, d_it = targeted(load, base, exd, lim, +1)
            st['down05'] = {'headroomKW': round(sum(exd.values()), 1), 'allElementsKW': d_kw, 'scale': d_scale,
                            'targetedKW': d_tg, 'targetedIterations': d_it}
            states.append(st)
            b = st['byDuration']
            print(sc, pol, s['step'], st['clock'], 'dispatch', st['replayDispatchKW'],
                  '| 0.5h', b['0.5']['headroomKW'], b['0.5']['allElementsKW'],
                  '| 1h', b['1']['headroomKW'], b['1']['allElementsKW'], b['1']['targetedKW'],
                  '| 4h', b['4']['headroomKW'], b['4']['allElementsKW'], b['4']['targetedKW'],
                  '| down 0.5h', st['down05']['headroomKW'], d_kw, d_tg,
                  '| replay over', st['replayVsIdleLimits']['transformersOver'], st['replayVsIdleLimits']['linesOver'],
                  st['replayVsIdleLimits']['voltageViolations'], flush=True)
            if (sc, pol, s['step']) == ('heatwave', 'aware', 7):
                # reproduction check: with base = {} the uniform search must match res-sim.py's idle main path
                zero = {u: 0.0 for u in IDS}
                check = {k: uniform(load, zero, headroom(socs, zero, h), limits(idle))[0] for k, h in DURATIONS.items()}

json.dump({'states': states, 'meta': {
    'engine': dss.Basic.Version().split('\n')[0], 'solves': nsolve, 'seconds': round(time.time() - t0, 1),
    'weakLine': sh['weakLine'], 'eta': ETA,
    'formula': 'r_u = max(0, min(20 - p_b, max(0, SoC - 0.20) x 37 x sqrt(0.89) / H - p_b)); p_b = replay base point, + = discharging',
    'formulaDown': 'd_u = max(0, min(20 - c_b, (1 - SoC) x 37 / sqrt(0.89) / 0.5 h - c_b)); c_b = replay base point, + = charging',
    'limits': 'transformers 99.5% kVA, voltage 0.9505-1.0495 pu, every Line <= 99.5% NormAmps; if already over at idle OR at the replay dispatch: that value + 0.05',
    'idleReproductionCheck': {'state': 'heatwave/aware/7', 'uniformKW': check,
                              'compareTo': 'res-sim.py byDuration[k].prototypeAllElementsKW (idle framing, two-stage uniform cut)'}}},
          open(OUT, 'w'))
print('check (base = idle)', check)
print('done', nsolve, 'solves', round(time.time() - t0, 1), 's')
