#!/usr/bin/env node
// ui/story/dev-b-fixtures/make-fixtures.mjs (UI-B, DEV ONLY; delete this folder at integration).
// Writes contract-shaped FIXTURES (every file carries "fixture": true) so results.js / learnings.js can be built before
// ENGINE (story/index.json, p1/extras/*) and PLANNER (p2/planner.json) land. Derived from committed files where possible:
//   story/index.json      summaries copied from ui/data/p1/meta.json, p1/days/<date>/meta.json, mpalacios/out/p1/worker_kill.json
//   p1/extras/*.json.gz   worstPct/worstTf from the real branch loading; busOrder/busDistKm from topology edges (graph distance);
//                         vTfMilli, headKW, headKVAr, capKVAr, feederLoadKW are SYNTHETIC shapes (fixture only)
//   p2/planner.json       caps/peaks from simulators/rz/.../scout-outputs (sweep g0/g20, ages csv, OpenDSS check);
//                         demand curves are SYNTHETIC; perK.g50 is deliberately absent (tests the "not exported" path)
// Run: node ui/story/dev-b-fixtures/make-fixtures.mjs
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const DATA = path.join(ROOT, 'ui/data');
const SCOUT = path.join(ROOT, 'simulators/rz/research/capacity-planner/scout-outputs');
const rd = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const out = (rel, obj, gz = false) => {
  const p = path.join(HERE, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const s = JSON.stringify(obj);
  fs.writeFileSync(p, gz ? zlib.gzipSync(Buffer.from(s)) : s);
  console.log('wrote', rel, (gz ? zlib.gzipSync(Buffer.from(s)).length : s.length) >> 10, 'KB');
};
const L = (v, label, cite) => (cite ? { v, label, cite } : { v, label });
const FIX = 'FIXTURE (ui/story/dev-b-fixtures/make-fixtures.mjs): not engine output';

const topo = rd(path.join(DATA, 'topology.json'));
const meta = rd(path.join(DATA, 'p1/meta.json'));
const engine = rd(path.join(DATA, 'engine.json'));
const NT = topo.transformers.length;

// ---------------- bus order: graph distance along the topology edges from the source ----------------
function busDistances() {
  const key = (lon, lat) => `${lon.toFixed(6)},${lat.toFixed(6)}`;
  const idx = new Map(), xy = [], adj = [];
  const node = (lon, lat) => { const k = key(lon, lat); if (!idx.has(k)) { idx.set(k, xy.length); xy.push([lon, lat]); adj.push([]); } return idx.get(k); };
  const cos = Math.cos(topo.meta.source[1] * Math.PI / 180);
  const km = (a, b) => Math.hypot((a[0] - b[0]) * cos * 111.32, (a[1] - b[1]) * 110.57);
  for (const e of topo.edges) { const a = node(e[0], e[1]), b = node(e[2], e[3]); const d = km(xy[a], xy[b]); adj[a].push([b, d]); adj[b].push([a, d]); }
  const nearest = (p) => { let bi = 0, bd = Infinity; for (let i = 0; i < xy.length; i++) { const d = km(p, xy[i]); if (d < bd) { bd = d; bi = i; } } return [bi, bd]; };
  const [src] = nearest(topo.meta.source);
  const dist = new Array(xy.length).fill(Infinity); dist[src] = 0;
  const done = new Uint8Array(xy.length);
  for (;;) { // O(n^2) Dijkstra, fine for ~2.5k nodes
    let u = -1, best = Infinity;
    for (let i = 0; i < xy.length; i++) if (!done[i] && dist[i] < best) { best = dist[i]; u = i; }
    if (u < 0) break; done[u] = 1;
    for (const [v, w] of adj[u]) if (dist[u] + w < dist[v]) dist[v] = dist[u] + w;
  }
  return topo.transformers.map((t) => { const [n, d] = nearest(t.lonlat); return Number.isFinite(dist[n]) ? dist[n] + d : km(t.lonlat, topo.meta.source); });
}
const distKm = busDistances();
const busOrder = [...distKm.keys()].sort((a, b) => distKm[a] - distKm[b] || a - b);
const maxD = Math.max(...distKm);

// ---------------- extras (hb.p1extras.v1) from a real branch doc ----------------
function extrasFrom(doc, events = []) {
  const steps = doc.steps;
  const worstPct = [], worstTf = [], vTfMilli = [], headKW = [], headKVAr = [], capKVAr = [], feederLoadKW = [];
  for (let k = 0; k < steps; k++) {
    const row = doc.loading[k];
    let w = 0; for (let i = 1; i < NT; i++) if (row[i] > row[w]) w = i;
    worstPct.push(row[w]); worstTf.push(w);
    const vmin = doc.vMin[k] / 1e4;
    const bat = (doc.batKW[k] || []).reduce((s, x) => s + x, 0) / 10;
    let kw = 0; for (let i = 0; i < NT; i++) kw += row[i] / 1000 * topo.transformers[i].kva * 0.97;
    const cap = k >= 180 && k < 540 ? 600 : 300;                          // SYNTHETIC capacitor schedule
    headKW.push(Math.round(kw * 10)); feederLoadKW.push(Math.round((kw - bat) * 10));
    capKVAr.push(cap * 10); headKVAr.push(Math.round((kw * 0.33 - cap) * 10));
    vTfMilli.push(topo.transformers.map((t, i) => {
      const s = Math.pow(distKm[i] / maxD, 0.8) * (0.55 + 0.45 * Math.min(1.5, row[i] / 1000));
      return Math.round(1000 * (1.0 - (1.0 - vmin) * Math.min(1, s)));
    }));
  }
  const moments = [];
  const firstOver = doc.counts.findIndex((c) => c[0] + c[1] + c[2] + c[3] + c[4] > 0);
  if (firstOver >= 0) moments.push({ k: firstOver, t: stepT(firstOver), rule: 'first_over_100', text: `${stepT(firstOver)} · T-${worstTf[firstOver]} goes over nameplate`, label: 'SIM' });
  const failures = events.map((e) => ({ kind: e.kind, where: e.tf != null ? `T-${e.tf}` : 'controller', k0: e.step, k1: e.step + (e.minutes || 5), text: e.text, label: 'SIM' }));
  moments.push({ k: steps - 1, t: stepT(steps - 1), rule: 'end', text: 'end of run', label: 'SIM' });
  return {
    schema: 'hb.p1extras.v1', producer: 'sim.scenarios', fixture: true, inputs: doc.inputs || {}, constants: {}, sources: { note: { label: 'SIM', text: FIX } },
    series: {
      vTfMilli: { label: 'SIM', unit: 'pu x1000, lowest home per transformer; 0 = isolated', by: 'FIXTURE shape (not OpenDSS)' },
      busOrder: { label: 'DERIVED', unit: 'transformer index' }, busDistKm: { label: 'DERIVED', unit: 'km' },
      headKW: { label: 'SIM', unit: 'kW x10' }, headKVAr: { label: 'SIM', unit: 'kVAr x10' }, capKVAr: { label: 'SIM', unit: 'kVAr x10' },
      feederLoadKW: { label: 'SIM', unit: 'kW x10' }, worstPct: { label: 'SIM', unit: 'pct x10' }, worstTf: { label: 'SIM', unit: 'index' },
    },
    steps, start: '16:00', stepSeconds: 60, vTfMilli, busOrder, busDistKm: distKm.map((d) => +d.toFixed(3)),
    headKW, headKVAr, capKVAr, feederLoadKW, worstPct, worstTf, moments, failures,
  };
}
function stepT(k) { const m = (16 * 60 + k) % 1440; return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; }

// ---------------- catalogue (hb.story.v1) ----------------
const eng = { buildSeconds: engine.p1.buildSeconds, solves: meta.engine.solves };
const wk = rd(path.join(ROOT, 'mpalacios/out/p1/worker_kill.json'));
const lev = (o) => ({ evening: '2026-08-23', policy: 'aware', failure: 'none', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0, ...o });
const base = (b) => ({ none: 'p1/none.json', naive: 'p1/naive.json', aware: 'p1/aware.json' }[b]);
const sc = [];
for (const b of ['none', 'naive', 'aware']) {
  sc.push({ id: `2026-08-23/${b}`, title: { none: 'No batteries', naive: 'Naive split', aware: 'Feeder-aware' }[b], ...(b === 'aware' ? { preset: 'demo' } : {}),
    levers: lev({ policy: b }), meta: 'p1/meta.json', branch: base(b), extras: `p1/extras/2026-08-23_${b}.json.gz`,
    compare: { none: 'p1/none.json', naive: 'p1/naive.json', aware: 'p1/aware.json' }, gz: false, summary: meta.summary[b], engine: eng });
}
sc.push({ id: '2026-08-23/aware/faults', title: 'Pieces fail', preset: 'faults', levers: lev({ failure: 'faults' }), meta: 'p1/meta.json', branch: 'p1/aware_faults.json',
  extras: 'p1/extras/2026-08-23_aware_faults.json.gz', compare: { none: 'p1/none.json', naive: 'p1/naive.json', aware: 'p1/aware.json' }, gz: false, summary: meta.summary.aware_faults, engine: eng });
sc.push({ id: '2026-08-23/aware/worker_kill', title: 'Controller crash', preset: 'crash', levers: lev({ failure: 'worker_kill' }), meta: 'p1/meta.json', branch: 'p1/worker_kill.json',
  extras: 'p1/extras/2026-08-23_aware_worker_kill.json.gz', compare: { none: 'p1/none.json', naive: 'p1/naive.json', aware: 'p1/aware.json' }, gz: false, summary: wk.summary, engine: eng });
sc.push({ id: '2026-08-23/aware/covert', title: 'Hidden attacker', preset: 'covert', levers: lev({ failure: 'covert' }), meta: 'p1/meta.json', branch: 'p1/aware.json',
  extras: 'p1/extras/2026-08-23_aware_covert.json.gz', covert: 'p3/covert.json', compare: { none: 'p1/none.json', naive: 'p1/naive.json', aware: 'p1/aware.json' }, gz: false, summary: meta.summary.aware, engine: eng });
const jul = rd(path.join(DATA, 'p1/days/2026-07-22/meta.json'));
for (const b of ['none', 'naive', 'aware']) {
  // NO extras file is written for 22 Jul: the page must say "not exported for this run"
  sc.push({ id: `2026-07-22/${b}`, title: `22 Jul · ${b}`, ...(b === 'aware' ? { preset: 'record' } : {}), levers: lev({ evening: '2026-07-22', policy: b }),
    meta: 'p1/days/2026-07-22/meta.json', branch: `p1/days/2026-07-22/${b}.json.gz`, extras: `p1/extras/2026-07-22_${b}.json.gz`,
    compare: { none: 'p1/days/2026-07-22/none.json.gz', naive: 'p1/days/2026-07-22/naive.json.gz', aware: 'p1/days/2026-07-22/aware.json.gz' }, gz: true, summary: jul.summary[b], engine: eng });
}
const opt = (id, label, extra = {}) => ({ id, label, ...extra });
out('story/index.json', {
  schema: 'hb.story.v1', producer: 'sim.scenarios', fixture: true, inputs: meta.inputs, constants: {}, sources: { note: { label: 'SIM', text: FIX } }, series: {},
  default: '2026-08-23/aware',
  levers: {
    evening: { label: 'Evening', default: '2026-08-23', options: [opt('2026-08-23', 'Sun 23 Aug 2026'), opt('2026-07-22', 'Wed 22 Jul 2026'), opt('2026-08-14', 'Fri 14 Aug 2026'), opt('2026-08-26', 'Wed 26 Aug 2026')] },
    policy: { label: 'Charging', default: 'aware', options: [opt('none', 'No batteries'), opt('naive', 'Naive split'), opt('aware', 'Feeder-aware')] },
    failure: { label: 'Failures', default: 'none', options: [opt('none', 'None'), opt('faults', 'Pieces fail'), opt('worker_kill', 'Controller crash'), opt('covert', 'Hidden attacker')] },
    fleet: { label: 'Fleet size', default: 96, options: [48, 96, 144, 192].map((n) => opt(n, `${n}`)) },
    cls: { label: 'Battery class', default: 'core', options: [opt('core', 'Core'), opt('legacy', 'Legacy')] },
    reserve: { label: 'Member reserve', default: 20, options: [20, 30, 40, 50].map((n) => opt(n, `${n}%`)) },
    soc0: { label: 'Starting charge', default: 90, options: [60, 75, 90, 100].map((n) => opt(n, `${n}%`)) },
    growth: { label: 'Home-load growth', default: 0, options: [0, 20, 50].map((n) => opt(n, `+${n}%`)) },
  },
  scenarios: sc,
  unavailable: [{ levers: { evening: '2026-08-14', failure: 'faults' }, reason: 'Failures are scripted for 23 Aug only' }],
});

// extras for the 23 Aug branches (22 Jul deliberately has none)
for (const [id, file, ev] of [['2026-08-23_none', 'p1/none.json'], ['2026-08-23_naive', 'p1/naive.json'], ['2026-08-23_aware', 'p1/aware.json'],
  ['2026-08-23_aware_faults', 'p1/aware_faults.json', meta.events.aware_faults], ['2026-08-23_aware_covert', 'p1/aware.json']]) {
  out(`p1/extras/${id}.json.gz`, extrasFrom(rd(path.join(DATA, file)), ev || []), true);
}
out('p1/extras/2026-08-23_aware_worker_kill.json.gz', extrasFrom(wk, [{ kind: 'worker_kill', step: wk.runtime.kill.step, minutes: 4, text: wk.runtime.kill.text }]), true);

// ---------------- planner (hb.planner.v1, DESIGN-CAPACITY-PLANNER §2.3) ----------------
const EXCL = [123, 144, 366];
const g0 = rd(path.join(SCOUT, 'tf_capacity_sweep_g0.json'));
const g20 = rd(path.join(SCOUT, 'tf_capacity_sweep_g20.json'));
const chk = rd(path.join(SCOUT, 'tf_capacity_opendss_check.json'));
const ages = fs.readFileSync(path.join(SCOUT, 'tf_simulated_ages.csv'), 'utf8').trim().split(/\r?\n/).slice(1).map((l) => l.split(','));
const ageOf = new Map(ages.map((a) => [+a[0], { draw: +a[2], p10: +a[3], p50: +a[4], p90: +a[5] }]));
const installedOn = new Array(NT).fill(0); for (const h of topo.fleet) installedOn[topo.homes[h].tf] += 1;
const homesOn = topo.transformers.map((t) => t.homes.filter((h) => topo.homes[h].eligible !== false).length);
const NEXT = { 25: 50, 50: 75, 75: 100, 100: 150 };
const med = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0; };
const bySize = (kva, f) => med(g0.tf.filter((t) => t.kva === kva && !EXCL.includes(t.i)).map(f));
const UNIT = { 25: 3853, 50: 4178, 75: 5249, 100: 6057 };
const keep = g0.tf.filter((t) => !EXCL.includes(t.i));
const interp = (obj, key, k) => { // aware sweep is on 19 k-values: linear between them (FIXTURE)
  const ks = Object.keys(obj).map(Number).sort((a, b) => a - b);
  if (obj[k]) return obj[k][key];
  const hi = ks.find((x) => x > k), lo = [...ks].reverse().find((x) => x < k);
  const f = (k - lo) / (hi - lo); return obj[lo][key] + (obj[hi][key] - obj[lo][key]) * f;
};
const perK = (sw) => {
  const one = sw.oneNaiveCoreRevenueUSD;
  const r = { naivePeak: [], naiveCaused: [], naiveTier: [], awarePeak: [], awareEff: [] };
  for (const t of keep) {
    const i = t.i, np = [], nc = [], nt = [], ap = [], ae = [];
    for (let k = 0; k <= 50; k++) {
      const pk = sw.naive.peak[k][i], cn = sw.naive.causedNormal[k][i];
      np.push(Math.round(pk * 10)); nc.push(cn);
      nt.push(sw.naive.protection[k][i] ? 5 : sw.naive.emergencyN[k][i] ? 4 : cn ? 3 : pk > 110 ? 2 : pk > 100 ? 1 : 0);
      ap.push(Math.round(interp(sw.aware[String(i)], 'peak', k) * 10));
      ae.push(Math.round(interp(sw.aware[String(i)], 'revenueUSD', k) / one * 100));
    }
    r.naivePeak.push(np); r.naiveCaused.push(nc); r.naiveTier.push(nt); r.awarePeak.push(ap); r.awareEff.push(ae);
  }
  return r;
};
const survival = Array.from({ length: 61 }, (_, a) => (a >= 60 ? 0 : +(Math.exp(-Math.pow(a / 39.07, 4.6141)) * Math.pow(0.995, a) * Math.pow(0.995, Math.max(0, a - 15))).toFixed(5)));
// SYNTHETIC demand curves: nine deciles of a per-home cumulative join probability at 0,12,...,60 months
const curves = {}, adds = {};
const lam = [0.004, 0.008, 0.012, 0.017, 0.023, 0.03, 0.04, 0.055, 0.08];
const curve = (mult) => lam.map((l) => [0, 12, 24, 36, 48, 60].map((m) => +(1 - Math.exp(-l * mult * m / 12)).toFixed(4)));
const tfs = keep.map((t) => {
  const i = t.i, a = ageOf.get(i) || { draw: 20, p10: 5, p50: 16, p90: 36 }, homes = homesOn[i], inst = installedOn[i], up = NEXT[t.kva];
  const key = `${homes}-${inst}`;
  if (!curves[key]) {
    curves[key] = { q0: curve(1), q30: curve(3) };
    const m = Math.max(0, homes - inst);
    adds[key] = { q0: { p10: 0, p50: Math.round(m * 0.1), p90: Math.round(m * 0.3), label: 'DERIVED' }, q30: { p10: 0, p50: Math.round(m * 0.3), p90: Math.round(m * 0.6), label: 'DERIVED' } };
  }
  const naiveOk = !chk.summary.naive_at_cap.disagree.includes(i);
  return {
    tf: i, id: t.id, kva: L(t.kva, 'REAL', 'SMART-DS Transformers.dss'), mount: topo.transformers[i].mount || 'pad', phases: L(1, 'REAL', 'SMART-DS'),
    homes, installed: L(inst, 'ASSUMPTION', 'the prototype 96-Core placement (data/fleet.json)'), pending: L(0, 'ASSUMPTION', 'no sales pipeline in the sim'),
    age: { v: a.draw, label: 'DERIVED', cite: 'ACS year built x DOE retirement function, one seeded draw (simulated)', source: 'simulated', p10: a.p10, p50: a.p50, p90: a.p90 },
    cap: {
      naive: { v: t.capNaive, label: 'SIM', cite: 'surrogate sweep, largest k with no battery-caused normal event (fixture from the scout sweep)', opendss: naiveOk ? 'agree' : 'lower', firstEmergency: t.firstEmergencyNaive, firstProtection: t.firstProtectionNaive },
      aware: { v: t.capAware90, label: 'SIM', cite: 'largest k where each Core earns >= 90% of an unconstrained Core (fixture from the scout sweep)', opendss: 'agree', k95: t.awareK95 },
      paper: { v: Math.floor(t.kva / 20), label: 'DERIVED', cite: 'floor(kVA / 20 kW), nameplate100 (PUCT 54233 items 85, 92)', profile: 'nameplate100' },
      heat: { wear: L(null, 'SIM', 'not in fixture'), topOil: L(null, 'SIM', 'not in fixture') },
    },
    up: {
      kva: L(up, 'ASSUMPTION', 'next standard size'),
      naive: { v: bySize(up, (x) => x.capNaive) || t.capNaive + 1, label: 'SIM', cite: 'size median (fixture)', screening: true },
      aware: { v: bySize(up, (x) => x.capAware90) || t.capAware90 + 2, label: 'SIM', cite: 'size median (fixture)', screening: true },
      paper: L(Math.floor(up / 20), 'DERIVED', 'floor(kVA / 20 kW)'),
      incrementUSD: L((UNIT[up] || UNIT[100]) - (UNIT[t.kva] || UNIT[75]), 'DERIVED', 'NREL cost DB v2 unit costs (2017)'),
    },
    nb: { key, homes, installed: inst, tfs: [i] },
  };
});
out('p2/planner.json', {
  schema: 'hb.planner.v1', producer: 'sim.planner', fixture: true, inputs: meta.inputs,
  constants: { PLAN_AWARE_EARN_MIN: { value: 0.9, label: 'ASSUMPTION', cite: 'DATA-ASSETS-DEMAND.md §5.2' } },
  sources: { note: { label: 'SIM', text: FIX } },
  series: { perK: { label: 'SIM', unit: 'peaks pct x10; tier codes 0-5; awareEff effective Cores x100', by: 'surrogate (scout sweep, fixture)' }, survival: { label: 'DERIVED' }, demand: { label: 'DERIVED' } },
  meta: { month: '2026-08', rule: 'd26', cls: 'core', fromEmptyFeeder: true, kMax: 50, radiusM: L(200, 'ASSUMPTION', 'PLAN_RADIUS_M'), sizes: [25, 50, 75, 100],
    scope: 'Core battery · D-26 onset · August 2026 prices × SMART-DS 2018 August load · empty feeder', excluded: EXCL, demoTf: 61, defaultTf: 240 },
  tfs,
  perK: { g0: perK(g0), g20: perK(g20) },
  survival: { years: Array.from({ length: 61 }, (_, i) => i), r: survival },
  demand: { deciles: [10, 20, 30, 40, 50, 60, 70, 80, 90], months: [0, 12, 24, 36, 48, 60], curves, adds },
  money: {
    PLAN_UPGRADE_USD: L(10000, 'REAL', "Base told the PUCT a residential post-install transformer upgrade can cost about $10,000 (PUCT 54224 item 49)"),
    PLAN_LEAD_MONTHS: L(6, 'ASSUMPTION', 'PLAN_LEAD_MONTHS'), PLAN_DISCOUNT: L(0.08, 'ASSUMPTION', 'PLAN_DISCOUNT'),
    PLAN_MEMBER_VALUE_USD_YR: L(631, 'DERIVED', "one Core, 2025 LZ_NORTH day-ahead energy value; not Base's profit"),
    PLAN_CONTRACT_YEARS: L(12, 'REAL', 'Base Core Battery Services Agreement'), PLAN_P_LOSS: L(0.3, 'ASSUMPTION', 'PLAN_P_LOSS'),
    PLAN_S_INCREMENT: L(0.5, 'ASSUMPTION', 'PLAN_S_INCREMENT'), PLAN_HORIZON_YEARS: L(5, 'ASSUMPTION', 'PLAN_HORIZON_YEARS'),
    upgradePresets: [L(4178, 'REAL', 'NREL cost DB v2, 2017'), L(10000, 'REAL', 'PUCT 54224 item 49'), L(15000, 'ASSUMPTION', 'PLAN_UPGRADE_USD preset')],
    valuePresets: [L(631, 'DERIVED', 'DATA-MARKET-PROFIT.md §4'), L(2040, 'DERIVED', 'City of Austin RCA 26-1526')],
  },
  screens: { profiles: [{ id: 'nameplate100', share: 1.0, label: 'REAL', cite: 'PUCT 54233 items 85, 92' }, { id: 'ae90', share: 0.9, label: 'REAL', cite: 'AE DG guide rev 14 p. 13' }], default: 'nameplate100' },
  decision: { label: 'DERIVED', cite: 'DESIGN-CAPACITY-PLANNER §3.4; ui/lib/planner.js', paths: L(1000, 'ASSUMPTION'), seed: 20260926 },
  referee: { status: 'checked', runs: chk.runs, secondsPerRun: L(12.8, 'SIM', 'scout OpenDSS check'),
    naiveAtCap: { agree: chk.summary.naive_at_cap.agreeTfs, of: chk.summary.naive_at_cap.transformers, lower: [54, 95] },
    naiveAtCapPlus1: { agree: chk.summary.naive_at_cap_plus1.agreeTfs, of: chk.summary.naive_at_cap_plus1.transformers },
    awareAtCap: { agree: 376, of: 376 }, sha256: 'fixture' },
});
