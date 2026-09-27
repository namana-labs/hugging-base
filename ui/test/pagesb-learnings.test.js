// ui/test/pagesb-learnings.test.js (UI-B): the pure view functions of ui/story/learnings.js (Screen 4b Learnings).
// Run: node --test ui/test/*.test.js
// Real-data checks read ui/data first, then the dev copies in ui/story/dev-b-fixtures/ (until integration), and skip
// when neither exists. planner.js is ui/lib/planner.js (PLANNER), else the dev copy.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  parseParams, effectiveCap, roomStatus, peakBucket, q1Status, growthLevels, rankingFor, upgradeList, upgradeShortlist,
  verdictWords, VERDICT_WORDS, rankingModel, stripCells, monthName, questions, plannerRows, constOf, tfName, countBy,
} from '../story/learnings.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI = path.resolve(HERE, '..');
const firstFile = (...rels) => rels.map((r) => path.join(UI, r)).find((p) => fs.existsSync(p)) || null;
const readData = (rel) => { const p = firstFile(`data/${rel}`, `story/dev-b-fixtures/${rel}`); return p ? JSON.parse(fs.readFileSync(p, 'utf8')) : null; };
const PLANNER = readData('p2/planner.json');
const LIB_PATH = firstFile('lib/planner.js', 'story/dev-b-fixtures/planner.js');
const lab = (v, label = 'SIM', extra = {}) => ({ v, label, cite: 'c', ...extra });

test('parseParams: q 1-4, tf inside the feeder, n inside 0..kMax; absent stays null', () => {
  assert.deepEqual(parseParams({ q: 3, tf: 61, n: 7 }, 379, 50), { q: 3, tf: 61, n: 7 });
  assert.deepEqual(parseParams({ q: '9', tf: '400', n: '51' }, 379, 50), { q: 1, tf: null, n: null });
  assert.deepEqual(parseParams({ q: null, tf: null, n: null }, 379, 50), { q: 1, tf: null, n: null });
  assert.deepEqual(parseParams({ q: '2', tf: '0', n: '0' }, 379, null), { q: 2, tf: 0, n: 0 });
});

test('OpenDSS wins: the shown cap, its pill, and screening when not refereed', () => {
  const checked = { status: 'checked' };
  const agree = effectiveCap(lab(2, 'SIM', { opendss: 'agree', shown: 2 }), checked);
  assert.equal(agree.v, 2); assert.equal(agree.pill, 'agree');
  const lower = effectiveCap(lab(3, 'SIM', { opendss: 'lower', shown: 2, note: 'OpenDSS found an overload at 3' }), checked);
  assert.equal(lower.v, 2); assert.equal(lower.raw, 3); assert.equal(lower.pill, 'lower'); assert.match(lower.cite, /overload at 3/);
  assert.equal(effectiveCap(lab(2, 'SIM', { opendss: 'agree', shown: 2 }), { status: 'not run' }).pill, 'screening');
  assert.equal(effectiveCap(lab(2, 'SIM', { opendss: 'agree', shown: 2, screening: true }), checked).pill, 'screening');
  assert.equal(effectiveCap(lab(null), checked), null);
});

test('room status and the peak fallback thresholds come from the data', () => {
  assert.deepEqual([roomStatus(4, 1), roomStatus(2, 1), roomStatus(1, 1), roomStatus(0, 1), roomStatus(null, 1)], [0, 1, 2, 3, -1]);
  assert.deepEqual([peakBucket(950, 100, 110), peakBucket(1050, 100, 110), peakBucket(1150, 100, 110)], [0, 2, 3]);
  const C = (value) => ({ value, label: 'REAL', cite: 'c' });
  const p2 = { constants: { TIER_AMBER_PCT: C(100), TIER_NORMAL_PCT: C(110) }, baseline: { peak: [500, 1050, 1200] } };
  const s = q1Status(3, null, p2, p2);
  assert.equal(s.mode, 'peak');
  assert.deepEqual(s.aware, [0, 2, 3]);
  assert.match(s.names[3], /110%/);
  assert.equal(q1Status(3, null, { baseline: { peak: [1] } }, { baseline: { peak: [1] } }), null);   // no thresholds: no map
  const planner = { referee: { status: 'checked' }, tfs: [
    { tf: 0, installed: lab(1, 'ASSUMPTION'), pending: lab(0, 'ASSUMPTION'), cap: { naive: lab(0, 'SIM', { shown: 0, opendss: 'agree' }), aware: lab(3, 'SIM', { shown: 3, opendss: 'agree' }) } },
    { tf: 2, installed: lab(2, 'ASSUMPTION'), pending: lab(0, 'ASSUMPTION'), cap: { naive: lab(2, 'SIM', { shown: 2, opendss: 'agree' }), aware: lab(3, 'SIM', { shown: 3, opendss: 'agree' }) } }] };
  const q = q1Status(3, planner, null, null);
  assert.deepEqual(q.naive, [3, -1, 2]);
  assert.deepEqual(q.aware, [0, -1, 1]);
  assert.deepEqual(countBy(q.aware, [0, 1, -1]), [1, 1, 1]);
});

test('Q4: the rank carries its denominator from the file; ranks are the file\'s', () => {
  const p2a = { flip: { entries: lab(353, 'DERIVED') }, ranking: [
    { rank: 1, label: 'Home 0409', tf: 240, reason: 'relieves 1.25 h above nameplate (SIM, screening); no new violation', stressAvoidedH: lab(1.25), peakWithPct: lab(96.8), revenueUSD: lab(63.91, 'DERIVED') },
    { rank: 2, label: 'Home 0195', tf: 150, reason: 'x', stressAvoidedH: lab(0.5), peakWithPct: lab(97), revenueUSD: lab(63.98, 'DERIVED') }] };
  const topo = { focus: [{ key: 'A', tf: 150 }] };
  const m = rankingModel(p2a, topo, 10);
  assert.equal(m.of.v, 353);
  assert.equal(m.headline, 'The next battery goes to Home 0409 on T-240 (rank 1 of 353): it relieves 1.25 h above nameplate.');
  assert.equal(m.rows[1].tfName, 'Street A');
  assert.deepEqual(m.tfs, [240, 150]);
  assert.equal(rankingModel({ ranking: p2a.ranking }, topo).of, null);
  assert.equal(rankingModel(null, topo).headline, null);
  assert.equal(tfName(topo, 7), 'T-7');
});

test('verdict words for every planner.js code; the horizon comes from the file', () => {
  for (const code of ['no-upgrade', 'wait-and-watch', 'upgrade-now', 'dont-upgrade', 'dont-upgrade-tell']) assert.ok(verdictWords(code, 5).word, code);
  assert.match(verdictWords('no-upgrade', 5).why, /within 5 years/);
  assert.match(verdictWords('no-upgrade', null).why, /within the horizon/);
  assert.equal(verdictWords('bogus', 5), null);
  assert.equal(Object.keys(VERDICT_WORDS).length, 5);
});

test('strip cells span 0..kMax; hypothetical cells come from planner.js rackStates', () => {
  const c = stripCells(2, 5, [false, false, false, false, true, true]);
  assert.equal(c.length, 6);
  assert.deepEqual(c.map((x) => x.fit), [false, true, true, false, false, false]);
  assert.ok(c[0].zero); assert.ok(c[4].hypo && c[5].hypo);
  assert.equal(stripCells(null, 3).some((x) => x.fit), false);
});

test('labels and helpers', () => {
  assert.equal(monthName('2026-08'), 'August 2026');
  assert.equal(monthName('nope'), null);
  assert.equal(questions(50, 10)[1].sub, 'One transformer, 0 to 50 batteries');
  assert.equal(questions(null, null)[3].sub, 'The next homes, ranked');
  assert.deepEqual([...plannerRows({ meta: { tfOrder: [5, 2] } }).entries()], [[5, 0], [2, 1]]);
  assert.deepEqual(constOf('A', { constants: { A: { value: 0.9, label: 'ASSUMPTION', cite: 'x' } } }), { v: 0.9, label: 'ASSUMPTION', cite: 'x' });
  assert.equal(constOf('A', {}), null);
  const g = growthLevels({ meta: { growth: [0, 20, 50] }, perK: { g0: { capAware: [] }, g20: { capAware: [] } } });
  assert.deepEqual(g.map((x) => [x.g, x.ok]), [[0, true], [20, true], [50, false]]);
});

// a two-transformer planner in the planner.json shape, for the ranking port
function tinyPlanner() {
  const F = (last) => Array.from({ length: 9 }, (_, i) => [0, 0, 0, 0, 0, last * (0.5 + i / 8)]);
  const row = (tf, homes, inst, aware, paper, upA, upP, key, age) => ({ tf, homes, installed: lab(inst, 'ASSUMPTION'), pending: lab(0, 'ASSUMPTION'),
    cap: { naive: lab(0, 'SIM', { shown: 0, opendss: 'agree' }), aware: lab(aware, 'SIM', { shown: aware, opendss: 'agree' }), paper: lab(paper, 'DERIVED') },
    up: { kva: lab(50, 'ASSUMPTION'), aware: lab(upA, 'SIM', { screening: true }), paper: lab(upP, 'DERIVED') }, nb: { key }, age: lab(age, 'DERIVED', { pRep5: age / 100 }) });
  return {
    meta: { tfOrder: [10, 11], growth: [0, 20], kMax: 50 },
    tfs: [row(10, 3, 2, 3, 1, 5, 2, 'a', 30), row(11, 4, 1, 4, 2, 6, 3, 'b', 10)],
    perK: { g0: { capAware: [3, 4] }, g20: { capAware: [3, 1], capAwareExact: [1, 0] } },
    money: { memberValueUSDYr: lab(631, 'DERIVED'), upgradeUSD: lab(10000, 'REAL'), coresPerMember: lab(1, 'ASSUMPTION') },
    demand: { curves: { a: { q0: F(0.4) }, b: { q0: F(0.8) } } },
  };
}
test('the ranking port: binding cap min(aware, rule), unlocked, value, payback; growth re-ranks as screening', () => {
  const p = tinyPlanner();
  const r0 = rankingFor(p, 0);
  assert.deepEqual(r0.map((r) => [r.tf, r.why]), [[10, 'blocked'], [11, 'unlocks']]);
  const a = r0[0];
  assert.equal(a.c, 1); assert.equal(a.cUp, 2); assert.equal(a.k0, 2);
  assert.equal(a.blockedToday.v, 1);
  assert.equal(a.unlocked.v, 1);
  assert.equal(a.valueUSDYr.v, 631);
  assert.equal(a.paybackYears.v, 15.8);
  assert.equal(a.screening, false);
  const r20 = rankingFor(p, 20);
  const b = r20.find((r) => r.tf === 11);
  assert.equal(b.c, 1); assert.equal(b.why, 'unlocks'); assert.equal(b.approx, true); assert.equal(b.screening, true);
  assert.deepEqual(rankingFor(p, 50), []);                                            // not exported: nothing invented
  assert.deepEqual(rankingFor(null, 0), []);
  const sl = upgradeShortlist([{ why: 'onboard', tf: 1 }, { why: 'blocked', tf: 2 }, { why: 'little', tf: 3 }, { why: 'onboard', tf: 4 }, { why: 'onboard', tf: 5 }], 8, 2);
  assert.deepEqual(sl.map((x) => x.tf), [2, 3, 1, 4]);
});

test('real planner.json: the port reproduces sim.planner\'s ranking at today\'s load', (t) => {
  if (!PLANNER) { t.skip('no planner.json yet'); return; }
  const mine = rankingFor(PLANNER, 0), theirs = PLANNER.ranking;
  assert.equal(mine.length, theirs.length);
  mine.forEach((m, i) => {
    const x = theirs[i];
    assert.equal(m.tf, x.tf, `row ${i}`); assert.equal(m.why, x.why, `row ${i}`); assert.equal(m.rank, x.rank);
    for (const k of ['blockedToday', 'wanted5y', 'unlocked', 'valueUSDYr', 'paybackYears']) assert.equal(m[k].v, x[k].v, `${x.tf} ${k}`);
    assert.equal(m.unlocked.p10, x.unlocked.p10); assert.equal(m.unlocked.p90, x.unlocked.p90);
  });
  const shown = upgradeList(PLANNER, 0);
  assert.deepEqual(shown.map((r) => r.tf), theirs.map((r) => r.tf));
  assert.ok(shown.every((r) => Number.isInteger(r.k0) && Number.isInteger(r.c)));
  for (const g of growthLevels(PLANNER).filter((x) => x.g && x.ok)) assert.ok(rankingFor(PLANNER, g.g).every((r) => r.screening), `g${g.g}`);
  // planner room/full status covers every homes-serving transformer; the excluded stay -1
  const s = q1Status(379, PLANNER, null, null);
  assert.equal(s.aware.filter((x) => x >= 0).length, PLANNER.tfs.length);
  for (const ex of PLANNER.meta.excluded) assert.equal(s.aware[ex], -1);
});

test('real planner.json + planner.js: every shortlisted row gets a verdict code the page can word', async (t) => {
  if (!PLANNER || !LIB_PATH) { t.skip('planner.json or planner.js not here yet'); return; }
  const lib = await import(pathToFileURL(LIB_PATH).href);
  const H = PLANNER.money.horizonYears.v;
  for (const r of upgradeShortlist(upgradeList(PLANNER, 0)).slice(0, 3)) {
    const p = lib.paramsFor(PLANNER, r.tf, r.k0, { growth: 0, paths: 200 });
    const v = lib.verdict(p, lib.decide(p, p.deciles, PLANNER.decision.seed));
    assert.ok(verdictWords(v.code, H), `${r.tf}: ${v.code}`);
    if (r.why === 'blocked') assert.ok(v.overToday, `${r.tf} is blocked today`);
  }
});

test('real p2 files: Q1 reads naiveOpenDSS (never the 383 screen) and Q4 has a denominator', (t) => {
  const idx = readData('p2/index.json'), p2a = readData('p2/aware-core-d26-g0.json');
  if (!idx || !p2a) { t.skip('p2 files not here'); return; }
  const uc = idx.usefulCapacity;
  assert.ok(uc.naiveOpenDSS && uc.naiveOpenDSS.v != null && uc.naiveOpenDSS.v !== uc.naive.v);
  const m = rankingModel(p2a, { focus: [] });
  assert.ok(m.of && m.of.v >= m.rows.length);
  assert.ok(m.rows.length <= 10);
});

test('no typed-in data values in learnings.js (the lead\'s static-number scan)', () => {
  const src = fs.readFileSync(path.join(UI, 'story/learnings.js'), 'utf8').replace(/^\s*\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '');
  for (const bad of [/\b1,?007\b/, /\b383\b/, /\b379\b/, /\b0\.9\b/, /\b10,?000\b/, /\b631\b/, /(of|for|in) August/,/\b15 minutes\b/, /\b240\b/, /\b50 batteries\b/]) assert.doesNotMatch(src, bad, String(bad));
});
