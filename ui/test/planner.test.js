// ui/test/planner.test.js (PLANNER): the capacity planner's upgrade math (ui/lib/planner.js) and its data file
// (ui/data/p2/planner.json). J1-J8 are DESIGN-CAPACITY-PLANNER.md §6.4. Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { mulberry32, monthly, surv, pReplace, annuity, breakEven, breakEvenValue, bindingCap, scenarioCosts, decide,
  paramsFor, verdict, rackStates, tfRow, capsFor, labelOf, growthOf, SETTINGS } from '../lib/planner.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FILE = path.join(UI, 'data', 'p2', 'planner.json');
const planner = JSON.parse(fs.readFileSync(FILE, 'utf8'));
const S = planner.survival.r;
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg ?? ''} ${a} vs ${b} (±${tol})`);
const rel = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol * Math.abs(b), `${msg ?? ''} ${a} vs ${b} (±${tol * 100}%)`);

// The design's T-61 neighbourhood (DESIGN §3.3 / §3.7: M = 49 eligible homes within 200 m, 6 installed), as
// sim.planner.demand_curves(49, 6, q=0, seed=[20260926, 49, 6, 0]) writes it (sim/tests/test_planner.py pins these
// numbers): nine decile curves of the per-home cumulative join probability at months 0, 12, ..., 60. DERIVED.
const T61_Q0 = [[0, 0.0185, 0.0367, 0.0546, 0.0721, 0.0893], [0, 0.023, 0.0455, 0.0675, 0.089, 0.11],
  [0, 0.0262, 0.0517, 0.0766, 0.1007, 0.1243], [0, 0.0292, 0.0575, 0.0851, 0.1118, 0.1377],
  [0, 0.0321, 0.0632, 0.0933, 0.1225, 0.1507], [0, 0.0352, 0.0692, 0.102, 0.1337, 0.1642],
  [0, 0.039, 0.0765, 0.1125, 0.1471, 0.1803], [0, 0.0439, 0.0859, 0.126, 0.1644, 0.2011],
  [0, 0.0517, 0.1007, 0.1472, 0.1913, 0.2331]];
const ZERO = Array.from({ length: 9 }, () => [0, 0, 0, 0, 0, 0]);
const base = (o = {}) => ({ k0: 2, homes: 3, c: 1, cUp: 2, age: 39, survTable: S, C: 10000, Cinc: 1071, L: 6, r: 0.08,
  V: annuity(631, 0.08, 12), pLoss: 0.3, s: 0.5, H: 5, paths: 1000, perMember: 1, life: 12, ...o });

// ---- survival (DESIGN §3.2; P8's JS half) ---------------------------------------------------------------------------
test('survival: P_rep(5 | 20) = 0.124 and P_rep(5 | 40) = 0.575 (±0.002); monotone in age and years', () => {
  near(pReplace(S, 20, 5), 0.124, 0.002, 'P_rep(5|20)');
  near(pReplace(S, 40, 5), 0.575, 0.002, 'P_rep(5|40)');
  near(pReplace(S, 39, 5), 0.5455, 0.001, 'P_rep(5|39), T-61');
  assert.equal(S.length, 61);
  assert.equal(surv(S, 60), 0);
  assert.equal(pReplace(S, 60, 1), 1);
  for (let a = 0; a < 55; a++) assert.ok(pReplace(S, a + 1, 5) >= pReplace(S, a, 5) - 1e-12, `age ${a}`);
  for (let n = 1; n < 20; n++) assert.ok(pReplace(S, 20, n + 1) >= pReplace(S, 20, n), `years ${n}`);
  near(surv(S, 20.5), (S[20] + S[21]) / 2, 1e-12, 'linear between years');
});

test('helpers: mulberry32 is seeded, monthly interpolates the yearly points', () => {
  const a = mulberry32(7), b = mulberry32(7);
  for (let i = 0; i < 5; i++) assert.equal(a(), b());
  const m = monthly([0, 0.12, 0.24, 0.36, 0.48, 0.6]);
  assert.equal(m.length, 61);
  near(m[6], 0.06, 1e-12);
  near(m[60], 0.6, 1e-12);
  near(annuity(631, 0.08, 12), 4755, 1, 'V at $631');
  near(annuity(2040, 0.08, 12), 15374, 1, 'V at $2,040');
});

// ---- J1-J8 (DESIGN §6.4) --------------------------------------------------------------------------------------------
test('J1: no future joins, already over: upgrade = 16,181.5, don\'t = 9,510, wait = upgrade', () => {
  const p = base({ k0: 4, homes: 4, c: 2, cUp: 3, V: 4755 });
  const s = scenarioCosts(p, monthly(ZERO[0]), 1);
  near(s.upgrade, 16181.5, 1e-6);
  near(s.never, 9510, 1e-6);
  near(s.wait, s.upgrade, 1e-6);
  const d = decide(p, ZERO);
  near(d.expected.upgrade, 16181.5, 1e-6);
  assert.equal(verdict(p, d).code, 'dont-upgrade-tell');
  assert.equal(verdict(p, d).twoRows, true);
});

test('J2: fits forever (c >= homes): wait = don\'t = 0, upgrade = C, verdict "no upgrade"', () => {
  const p = base({ k0: 1, homes: 3, c: 3, cUp: 4 });
  const d = decide(p, T61_Q0);
  assert.equal(d.expected.wait, 0);
  assert.equal(d.expected.never, 0);
  assert.equal(d.expected.upgrade, 10000);
  assert.equal(d.pOverP90, 0);
  assert.equal(verdict(p, d).code, 'no-upgrade');
});

test('J3: in every named scenario the smallest regret is 0; leastRegret = argmin of the worst regret', () => {
  for (const o of [{}, { V: annuity(2040, 0.08, 12) }, { k0: 1, c: 2, cUp: 3 }]) {
    const d = decide(base(o), T61_Q0);
    for (const k of ['p10', 'p50', 'p90']) assert.equal(Math.min(...Object.values(d.regretBy[k])), 0, k);
    const worst = Math.min(...Object.values(d.regret));
    assert.equal(d.regret[d.leastRegret], worst);
  }
});

test('J4: break-even members and break-even member value', () => {
  assert.equal(breakEven(10000, 4755), 3);
  assert.equal(breakEven(10000, 15374), 1);
  near(breakEvenValue(10000, 1, 0.08, 12), 1327, 1, 'CRITIQUE must-fix 5: ~$1,327/yr for one member');
  assert.equal(breakEvenValue(10000, 0, 0.08, 12), Infinity);
});

test('J5: determinism; mean joins within 5% of m x F(60) at 1,000 paths', () => {
  const p = base({ k0: 0, homes: 6, c: 10, cUp: 12 });
  assert.deepEqual(decide(p, T61_Q0), decide(p, T61_Q0));
  const F = monthly(T61_Q0[8]);
  const s = scenarioCosts(p, F, 20260926);
  rel(s.meanJoins, 6 * F[60], 0.05, 'mean joins');
});

test('J6: monotone: raising C never lowers "upgrade now"; raising V never lowers "don\'t upgrade"', () => {
  let last = -Infinity;
  for (const C of [4178, 10000, 15000]) { const u = decide(base({ C }), T61_Q0).expected.upgrade; assert.ok(u >= last); last = u; }
  last = -Infinity;
  for (const v of [631, 859, 2040]) { const n = decide(base({ V: annuity(v, 0.08, 12) }), T61_Q0).expected.never; assert.ok(n >= last); last = n; }
});

test('J7: bindingCap follows the §3.4.1 table; portal headroom replaces the paper rule', () => {
  const caps = { naive: 1, aware: 4, paper: 2 };
  assert.equal(bindingCap(caps, 'naive'), 1);
  assert.equal(bindingCap(caps, 'aware-screen'), 2);
  assert.equal(bindingCap(caps, 'aware-credit'), 4);
  assert.equal(bindingCap({ ...caps, utility: 3 }, 'aware-screen'), 3);
  assert.equal(bindingCap({ ...caps, utility: 0 }, 'naive'), 0);
});

test('J8: the T-61 row of §3.7 (naive, $631): expected costs within ±3% of $12,048 and $5,376; don\'t upgrade', () => {
  const p = base();
  const d = decide(p, T61_Q0);
  rel(d.expected.upgrade, 12048, 0.03, 'upgrade now');
  rel(d.expected.never, 5376, 0.03, 'don\'t upgrade');
  assert.equal(d.expected.wait, d.expected.upgrade);           // over today: wait = upgrade (the two-row table)
  assert.equal(verdict(p, d).code, 'dont-upgrade-tell');
  const d2 = decide(base({ V: annuity(2040, 0.08, 12) }), T61_Q0); // §3.7: at $2,040 it flips to upgrade now
  assert.equal(verdict(base(), d2).code === 'upgrade-now' || d2.leastRegret === 'upgrade', true);
  assert.equal(d2.leastRegret, 'upgrade');
});

// ---- planner.json + paramsFor: the T-61 verdicts on the built data ---------------------------------------------------
test('planner.json: envelope, exclusions, perK g0 / g20 / g50 at [376][51], size <= 2.0 MB', () => {
  assert.equal(planner.schema, 'hb.planner.v1');
  assert.ok(fs.statSync(FILE).size <= 2.0 * 1024 * 1024);
  const tfs = planner.tfs.map((r) => r.tf);
  assert.equal(tfs.length, 376);
  for (const x of [123, 144, 366]) assert.ok(!tfs.includes(x), `T-${x} excluded`);
  assert.deepEqual(planner.meta.excluded, [123, 144, 366]);
  assert.deepEqual(planner.meta.tfOrder, tfs);
  for (const g of ['g0', 'g20', 'g50']) {
    const blk = planner.perK[g];
    for (const k of ['naivePeak', 'naiveCaused', 'naiveTier', 'awarePeak', 'awareEff']) {
      assert.equal(blk[k].length, 376, `${g}.${k}`);
      assert.ok(blk[k].every((row) => row.length === 51), `${g}.${k} rows`);
    }
    if (g !== 'g0') { assert.ok(Array.isArray(blk.awareGrid) && blk.awareGrid.length === 19); assert.ok(blk.awareInterp); }
  }
  assert.equal(planner.perK.g0.awareGrid, null);
  for (const r of planner.tfs) for (const k of ['naive', 'aware', 'paper']) assert.ok(['SIM', 'DERIVED'].includes(r.cap[k].label));
});

test('planner.json: OpenDSS wins (cap.*.shown) and the referee block', () => {
  const ref = planner.referee;
  assert.ok(['checked', 'not run'].includes(ref.status));
  for (const r of planner.tfs) {
    for (const k of ['naive', 'aware']) {
      const c = r.cap[k];
      assert.equal(c.shown, c.opendss === 'lower' ? c.v - 1 : c.v, `T-${r.tf} ${k}`);
      if (ref.status !== 'checked') assert.equal(c.opendss, 'not run');
    }
  }
  if (ref.status === 'checked') {
    assert.ok(ref.naiveAtCap.agree.v >= 370, 'naive at cap agrees on almost all');
    assert.equal(ref.naiveAtCapPlus1.agree.v, 376);
    assert.equal(ref.awareAtCap.agree.v, 376);
  }
});

test('paramsFor: the §3.7 T-61 verdicts on the built data (installed 1 + 1 sold = 2 wanted)', () => {
  const run = (knobs) => { const p = paramsFor(planner, 61, 2, knobs); const d = decide(p, p.deciles, planner.decision.seed); return { p, d, v: verdict(p, d) }; };
  const naive = run({ setting: 'naive', value: 0 });
  assert.equal(naive.p.c, 1);
  assert.equal(naive.v.code, 'dont-upgrade-tell');
  assert.equal(naive.v.blockedToday, 1);
  assert.equal(run({ setting: 'naive', value: 2 }).v.code, 'upgrade-now');
  const screen = run({ setting: 'aware-screen', value: 0 });
  assert.equal(screen.p.c, 2);
  assert.equal(screen.p.cUp, 3);
  assert.equal(screen.v.code, 'dont-upgrade');
  assert.equal(run({ setting: 'aware-screen', value: 2 }).v.code, 'wait-and-watch');
  const credit = run({ setting: 'aware-credit', value: 0 });
  assert.equal(credit.p.c, 4);
  assert.equal(credit.v.code, 'no-upgrade');
  assert.equal(credit.v.roomToday, 2);
});

test('paramsFor: shape, knob aliases (growth "g20", dispatch/credit, q30) and errors', () => {
  const p = paramsFor(planner, 61, 2);
  for (const k of ['k0', 'homes', 'c', 'cUp', 'age', 'survTable', 'C', 'Cinc', 'L', 'r', 'V', 'pLoss', 's', 'H', 'paths',
    'perMember', 'life', 'deciles', 'caps', 'row', 'setting', 'v', 'cost', 'value', 'knobs']) assert.ok(k in p, k);
  assert.equal(p.setting, planner.decision.defaults.setting);
  assert.equal(p.C, 10000);
  assert.equal(p.v, 631);
  assert.equal(p.deciles.length, 9);
  assert.equal(p.caps.checked, planner.referee.status === 'checked');
  assert.deepEqual(paramsFor(planner, 61, 2, { growth: 'g20' }).caps, paramsFor(planner, 61, 2, { growth: 20 }).caps);
  assert.equal(paramsFor(planner, 61, 2, { growth: 'g50' }).caps.upAtToday, true);
  assert.equal(paramsFor(planner, 61, 2, { dispatch: 'aware', credit: true }).setting, 'aware-credit');
  assert.equal(paramsFor(planner, 61, 2, { dispatch: 'naive' }).setting, 'naive');
  const row = tfRow(planner, 61);
  assert.equal(paramsFor(planner, 61, 2, { q: 'q30' }).deciles, planner.demand.curves[row.nb.key].q30);
  assert.equal(paramsFor(planner, 61, 2, { cost: 12345 }).cost.label, 'ASSUMPTION');
  assert.throws(() => paramsFor(planner, 123, 1), /not a homes-serving/);
  assert.throws(() => paramsFor(planner, 61, 1, { setting: 'bogus' }), /setting/);
  assert.equal(growthOf('g50'), 50);
  assert.deepEqual(SETTINGS, ['naive', 'aware-screen', 'aware-credit']);
  assert.deepEqual(labelOf(planner, 3), { v: 3, label: 'DERIVED', cite: planner.decision.cite });
});

test('capsFor / rackStates: growth caps come from perK, the rack marks overload, paper, interpolated k', () => {
  const row = tfRow(planner, 61);
  const r = planner.meta.tfOrder.indexOf(61);
  assert.equal(capsFor(planner, row, 50).naive, planner.perK.g50.capNaive[r]);
  assert.equal(capsFor(planner, row, 0).naive, row.cap.naive.shown);
  const naive = rackStates(planner, 61, 5, 'naive');
  assert.deepEqual(naive.map((x) => x.state), ['fits', 'overload', 'overload', 'overload', 'overload']);
  assert.equal(naive[3].hypothetical, false);
  assert.equal(rackStates(planner, 61, 7, 'naive')[6].hypothetical, true);
  const screen = rackStates(planner, 61, 5, 'aware-screen');
  assert.deepEqual(screen.map((x) => x.state), ['fits', 'fits', 'paper', 'paper', 'earnsLess']);
  const g20 = rackStates(planner, 61, 14, 'aware-screen', 20);
  assert.equal(g20[11].approx, false);                                  // j = 12 is on the 19-value grid
  assert.equal(g20[12].approx, true);                                   // j = 13 sits between 12 and 15
  assert.equal(rackStates(planner, 61, 14, 'aware-screen', 0)[12].approx, false);   // g0 is simulated at every k
});

test('decide() is fast enough for the page (< 400 ms per call here; 3-16 ms on the design machine)', () => {
  const p = paramsFor(planner, 61, 2);
  decide(p, p.deciles);
  const t0 = performance.now();
  decide(p, p.deciles);
  assert.ok(performance.now() - t0 < 400);
});
