"""res: combined ECRS + Non-Spin offer from ONE store of energy (SIM + DERIVED), added after the second adversarial review.

"ECRS-backed" (1 h) and "Non-Spin-backed" (4 h) in res-sim.py / res-coopt.py are ALTERNATIVE uses of the same stored
energy: each is computed as if the fleet offered only that product. This script asks what the fleet can hold AT ONCE.

Per Core u (P = 20 kW, e_u = max(0, SoC_u - 0.20) x 37 kWh x sqrt(0.89) = energy above the backup floor, kWh;
p_u = base point held, + = discharging: 0 in the idle framing, the replay's own dispatch in the co-optimized framing):

  mode A, ECRS only (base held 1 h):       0 <= x <= min(P - p, e - p),  y = 0
  mode B, holds Non-Spin (base held 4 h):  x, y >= 0,  x + y <= min(P - p, e - p),  x + 4y <= e - 4p

  (x = ECRS kW for 1 h, y = Non-Spin kW for 4 h; both deployed at once is the worst case, so the feeder must carry
   p + x + y at every Core; "x + y <= e - p" is the 1-hour SoC check, "x + 4y <= e - 4p" the 4-hour one.)
  In the idle framing (p = 0) mode A lies inside mode B, so every Core's set is convex.
  mode A alone reproduces res-coopt.py's 1 h figure and mode B with x = 0 its 4 h figure.

Fleet frontier (before the feeder): maximise X + mu*Y over the union of each Core's mode vertices, for every mu
at which some Core changes its choice (a Lagrangian sweep; gives every vertex of the fleet's upper-right hull exactly).
Edges whose moving Cores all stay inside one convex mode set are interpolated exactly (each mover moves the same
fraction t); edges with a Core jumping between modes are reported only at their end vertices (never interpolated).

Feeder check (same limits and search as res-coopt.py): the extra discharge x_u + y_u on top of p_u is
  - uniform: scaled by one factor (16-step bisection) until every transformer, home voltage and Line element passes;
    both products shrink by the same factor (the prototype's uniform-cut method)
  - targeted: only Cores behind an element that is over are cut, 5% per iteration, both products together
Limits: transformers 99.5% kVA, voltage 0.9505-1.0495 pu, every Line <= 99.5% NormAmps; an element already over with
the fleet idle (or, co-optimized, at the replay's own dispatch) may not get worse (+0.05).

DERIVED fleet-level relaxation (the reviewer's form): x*1h + y*4h <= E = sum_u e_u and x + y <= feeder-deliverable.
It ignores which Core holds the energy and where it sits on the feeder, so it is an outer bound on the SIM line.

Status: frontier before the feeder = DERIVED (per-Core arithmetic on replay SoC); after the feeder = SIM.
Also writes energyAboveFloorKWh (DERIVED) for all 52 replay states, for the either/or check in fleet.states.
Usage:
  nice -n 10 python res-combo.py OUT.json [scenario/policy/step,...]
  (default: the two upward waterfall states heatwave/aware/7 and rebound/aware/3; 168 solves, about 2 s of CPU, so no heavy
   lock is needed; wrap it in  lockf -k /private/tmp/claude-501/heavy-local.lock  if you pass many states)
"""
import sys, json, math, time, collections
GS = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories'
sys.path.insert(0, GS)
from sim.feeder import Feeder
from sim.constants import CORE_POWER_KW, CORE_USABLE_KWH, CORE_ROUND_TRIP_EFFICIENCY, RESERVE_FLOOR
from opendssdirect import dss

OUT = sys.argv[1]
ONLY = sys.argv[2].split(',') if len(sys.argv) > 2 else ['heatwave/aware/7', 'rebound/aware/3']
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
P = CORE_POWER_KW
LMAX, VLO, VHI, TOL = 99.5, 0.9505, 1.0495, 0.05
# extra ECRS targets (kW) to report exactly where an edge allows it: the reviewer's worked example
EXTRA_X = {('heatwave', 'aware', 7, 'idle'): [1000.0]}

# line -> batteries downstream (same tree walk as res-sim.py / res-coopt.py)
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


def energy(soc):
    return max(0.0, soc - RESERVE_FLOOR) * CORE_USABLE_KWH * ETA


def core_modes(e, p):
    """Vertices of mode A (ECRS only) and mode B (holds Non-Spin) for one Core; B = [] if infeasible."""
    c = min(P - p, e - p)            # power headroom and 1-hour energy
    f4 = e - 4 * p                   # 4-hour energy with the base point held
    A = [(0.0, 0.0), (max(0.0, c), 0.0)]
    B = []
    if c >= 0 and f4 >= 0:
        B = {(0.0, 0.0), (min(c, f4), 0.0), (0.0, min(c, f4 / 4))}
        if f4 / 4 < c < f4:
            yy = (f4 - c) / 3
            B.add((c - yy, yy))
        B = sorted(B)
    return A, B, c, f4


def in_B(v, c, f4):
    return c >= 0 and f4 >= 0 and v[0] >= -1e-9 and v[1] >= -1e-9 and v[0] + v[1] <= c + 1e-9 and v[0] + 4 * v[1] <= f4 + 1e-9


def frontier(cores):
    """cores: {u: (A, B, c, f4)}. Returns hull vertices as list of allocations {u: (x, y)}, max-X end first."""
    mus = set()
    for A, B, c, f4 in cores.values():
        V = A + B
        for v in V:
            for w in V:
                if w[1] > v[1] + 1e-12:
                    m = (v[0] - w[0]) / (w[1] - v[1])
                    if m > 0:
                        mus.add(round(m, 9))
    mus = sorted(mus)
    probes = [1e-7] + [(a + b) / 2 for a, b in zip(mus, mus[1:])] + ([mus[-1] * 2 + 1] if mus else []) + [1e7]

    def best(mu):
        out = {}
        for u, (A, B, c, f4) in cores.items():
            out[u] = max(A + B, key=lambda v: (v[0] + mu * v[1], v[1] if mu > 1 else v[0]))
        return out
    verts = []
    for mu in probes:
        a = best(mu)
        if not verts or any(abs(a[u][0] - verts[-1][u][0]) > 1e-9 or abs(a[u][1] - verts[-1][u][1]) > 1e-9 for u in IDS):
            verts.append(a)
    return verts


def tot(a):
    return sum(v[0] for v in a.values()), sum(v[1] for v in a.values())


def edge_convex(a, b, cores):
    for u in IDS:
        if a[u] != b[u]:
            A, B, c, f4 = cores[u]
            both_B = in_B(a[u], c, f4) and in_B(b[u], c, f4)
            both_A = a[u][1] == 0 and b[u][1] == 0
            if not (both_B or both_A):
                return False
    return True


def lerp(a, b, t):
    return {u: (a[u][0] + t * (b[u][0] - a[u][0]), a[u][1] + t * (b[u][1] - a[u][1])) for u in IDS}


def samples(verts, cores, extra_x, n=10):
    """Hull vertices, plus exact interpolation on convex edges so X is sampled about every Xmax/n, plus extra X targets."""
    xmax = tot(verts[0])[0]
    out = [(verts[0], 'vertex')]
    for a, b in zip(verts, verts[1:]):
        (xa, _), (xb, _) = tot(a), tot(b)
        if edge_convex(a, b, cores) and xmax > 0:
            k = int(math.floor((xa - xb) / (xmax / n) - 1e-9))
            for i in range(1, k + 1):
                out.append((lerp(a, b, i / (k + 1)), 'edge'))
            for xt in extra_x:
                if xb < xt < xa:
                    out.append((lerp(a, b, (xa - xt) / (xa - xb)), 'example'))
        out.append((b, 'vertex'))
    out.sort(key=lambda s: -tot(s[0])[0])
    return out


def feeder_uniform(load, base, alloc, lim):
    f.load(load)
    ext = {u: alloc[u][0] + alloc[u][1] for u in IDS}
    f.battery({u: base.get(u, 0.0) - ext[u] for u in IDS})
    if not any(violations(solve(), lim)):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(16):
        s = (lo + hi) / 2
        f.battery({u: base.get(u, 0.0) - ext[u] * s for u in IDS})
        if any(violations(solve(), lim)):
            hi = s
        else:
            lo = s
    return lo


def what_binds(load, base, alloc, lim, scale):
    """Solve 1 percentage point above the uniform pass scale and report which limits fail (so the text can name the binding kind)."""
    f.load(load)
    ps = min(1.0, scale + 0.01)
    f.battery({u: base.get(u, 0.0) - (alloc[u][0] + alloc[u][1]) * ps for u in IDS}); r = solve()
    tf, vv, ln = violations(r, lim)
    return {'probeScale': round(ps, 4), 'transformersOver': len(tf), 'voltageViolations': len(vv), 'linesOver': len(ln),
            'maxVoltagePu': round(r['maxVoltage'], 5), 'maxTransformerPct': r['maxLoading'], 'maxLinePct': round(max(r['lines'].values()), 2)}


def feeder_targeted(load, base, alloc, lim):
    f.load(load)
    k = {u: 1.0 for u in IDS}
    ext = {u: alloc[u][0] + alloc[u][1] for u in IDS}
    for it in range(800):
        f.battery({u: base.get(u, 0.0) - ext[u] * k[u] for u in IDS}); r = solve()
        tf, vv, ln = violations(r, lim)
        if not (tf or vv or ln):
            return k, it
        bad_tf = set(tf) | {f.homes[i]['tf'] for i in vv}
        hit = {u for u in IDS if homes[u]['tf'] in bad_tf}
        for el in ln:
            hit |= down.get(el, set())
        hit = [u for u in hit if ext[u] * k[u] > 1e-6]
        for u in (hit or IDS):
            k[u] *= 0.95 if hit else 0.98
    raise RuntimeError('targeted did not converge')


out_states = []
for key in ONLY:
    sc, pol, step = key.split('/'); step = int(step)
    s = next(x for x in R[sc][pol] if x['step'] == step)
    socs, load, base = s['soc'], s['loadFactor'], s['powers']
    f.load(load); f.battery({}); idle = solve()
    f.battery(base); rep = solve()
    E = sum(energy(socs[u]) for u in IDS)
    st = {'scenario': sc, 'policy': pol, 'step': step, 'clock': f"{s['minute']//60:02d}:{s['minute']%60:02d}",
          'replayDispatchKW': round(sum(base.values()), 1), 'energyAboveFloorKWh': round(E, 2), 'framings': {}}
    for framing in ('idle', 'coopt'):
        pb = {u: (0.0 if framing == 'idle' else -base.get(u, 0.0)) for u in IDS}   # + = discharging
        fb = {} if framing == 'idle' else base
        lim = limits(idle) if framing == 'idle' else limits(idle, rep)
        cores = {u: core_modes(energy(socs[u]), pb[u]) for u in IDS}
        verts = frontier(cores)
        smp = samples(verts, cores, EXTRA_X.get((sc, pol, step, framing), []))
        pts, binds = [], []
        for alloc, kind in smp:
            X, Y = tot(alloc)
            s_u = feeder_uniform(load, fb, alloc, lim)
            if s_u < 1.0:
                binds.append({'point': len(pts), **what_binds(load, fb, alloc, lim, s_u)})
            kt, it = feeder_targeted(load, fb, alloc, lim)
            Xt = sum(alloc[u][0] * kt[u] for u in IDS); Yt = sum(alloc[u][1] * kt[u] for u in IDS)
            pts.append([round(X, 1), round(Y, 1), round(X * s_u, 1), round(Y * s_u, 1), round(s_u, 4), round(Xt, 1), round(Yt, 1), kind])
            print(sc, pol, step, framing, kind, 'pre', round(X, 1), round(Y, 1), '| uniform', round(X * s_u, 1), round(Y * s_u, 1),
                  'scale', round(s_u, 4), '| targeted', round(Xt, 1), round(Yt, 1), it, flush=True)
        nB = sum(1 for u in IDS if cores[u][1])
        st['framings'][framing] = {
            'basePointKW': round(sum(pb.values()), 1),
            'coresThatCanHoldNonSpin': nB,
            'hullVertices': len(verts),
            'fields': ['ecrsKW', 'nonSpinKW', 'ecrsUniformKW', 'nonSpinUniformKW', 'uniformScale', 'ecrsTargetedKW', 'nonSpinTargetedKW', 'kind'],
            'points': pts,
            'binding': binds}   # for every point the uniform cut scaled: which limits fail 1 percentage point above the pass scale
    out_states.append(st)

allE = {f"{sc}/{pol}/{x['step']}": round(sum(energy(x['soc'][u]) for u in IDS), 1)
        for sc in ('heatwave', 'rebound') for pol in ('naive', 'aware') for x in R[sc][pol]}
json.dump({'states': out_states, 'energyAboveFloorKWh': allE, 'meta': {
    'engine': dss.Basic.Version().split('\n')[0], 'solves': nsolve, 'seconds': round(time.time() - t0, 1), 'eta': ETA,
    'modes': 'mode A (ECRS only, base held 1 h): 0 <= x <= min(20 - p, e - p), y = 0; mode B (holds Non-Spin, base held 4 h): x + y <= min(20 - p, e - p), x + 4y <= e - 4p; '
             'e = max(0, SoC - 0.20) x 37 kWh x sqrt(0.89); p = 0 (idle) or the replay base point (co-optimized, + = discharging)',
    'frontier': 'Lagrangian sweep over mu (maximise X + mu*Y over each Core\'s mode vertices); convex edges interpolated exactly, mode-jump edges only at end vertices',
    'feeder': 'extra discharge x + y per Core on top of p; uniform = one scale factor, 16-step bisection; targeted = only Cores behind an element that is over, 5%/iteration; '
              'transformers 99.5% kVA, voltage 0.9505-1.0495 pu, every Line <= 99.5% NormAmps; already over at idle (or at the replay dispatch, co-optimized): that value + 0.05'}},
          open(OUT, 'w'))
print('done', nsolve, 'solves', round(time.time() - t0, 1), 's')
