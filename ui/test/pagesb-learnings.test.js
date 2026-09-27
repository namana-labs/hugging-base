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
  parseParams, effectiveCap, roomStatus, peakBucket, q1Status, growthLevels, rankingOf, upgradeList, upgradeShortlist, growthStory, q3Rows,
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
    { rank: 1, label: 'Home 0409', tf: 240, reason: 'relieves 1.25 h above nameplate (SIM, screening); no new violation', stressAvoidedH: lab(1.25), peakWithPct: lab(96.8), revenueUSD: lab(63.91, 'DERIVED'), noNewViolation: lab(true, 'SIM') },
    { rank: 2, label: 'Home 0195', tf: 150, reason: 'x', stressAvoidedH: lab(0.5), peakWithPct: lab(97), revenueUSD: lab(63.98, 'DERIVED'), noNewViolation: lab(true, 'SIM') }] };
  const topo = { focus: [{ key: 'A', tf: 150 }] };
  const m = rankingModel(p2a, topo, 10);
  assert.equal(m.of.v, 353);
  assert.deepEqual(m.lead, { home: 'Home 0409', tf: 240, tfName: 'T-240', rank: 1, stress: p2a.ranking[0].stressAvoidedH });   // fields, no sentence parsing
  assert.equal(m.noNew.all, true); assert.equal(m.noNew.label, 'SIM');
  p2a.ranking[1].noNewViolation = lab(false, 'SIM');
  assert.deepEqual([rankingModel(p2a, topo).noNew.all, rankingModel(p2a, topo).noNew.n], [false, 1]);
  delete p2a.ranking[1].noNewViolation;
  assert.equal(rankingModel(p2a, topo).noNew, null);                               // not every row says: no claim
  assert.equal(m.rows[1].tfName, 'Street A');
  assert.deepEqual(m.tfs, [240, 150]);
  assert.equal(rankingModel({ ranking: p2a.ranking }, topo).of, null);
  assert.equal(rankingModel(null, topo).lead, null);
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
  assert.doesNotMatch(questions(50, 10).map((x) => x.sub).join(' '), /[0-9]/);                       // no unlabelled numbers in the rail

  assert.deepEqual([...plannerRows({ meta: { tfOrder: [5, 2] } }).entries()], [[5, 0], [2, 1]]);
  assert.deepEqual(constOf('A', { constants: { A: { value: 0.9, label: 'ASSUMPTION', cite: 'x' } } }), { v: 0.9, label: 'ASSUMPTION', cite: 'x' });
  assert.equal(constOf('A', {}), null);
});

// a two-row planner in the planner.json shape: the page only READS rankingByGrowth (no ranking logic in the browser)
function tinyPlanner() {
  const row = (tf, inst, paper) => ({ tf, homes: 3, installed: lab(inst, 'ASSUMPTION'), pending: lab(0, 'ASSUMPTION'), cap: { paper: lab(paper, 'DERIVED') } });
  const rk = (rank, tf, why, fit, extra = {}) => ({ rank, tf, why, unlocked: lab(1, 'DERIVED', { p10: 1, p90: 1 }), controlsFit: lab(fit), ...extra });
  const g0 = [rk(1, 10, 'blocked', 2), rk(2, 11, 'onboard', 4)];
  return {
    meta: { tfOrder: [10, 11], growth: [0, 20, 50] },
    tfs: [row(10, 2, 1), row(11, 1, 2)],
    ranking: g0,
    rankingByGrowth: { g0, g20: [rk(1, 10, 'blocked', 2, { approx: false }), rk(2, 11, 'onboard', 5, { approx: true })] },
  };
}
test('Q3 reads rankingByGrowth as written; growth levels exist only when the file carries them', () => {
  const p = tinyPlanner();
  assert.deepEqual(growthLevels(p).map((x) => [x.g, x.ok]), [[0, true], [20, true], [50, false]]);
  assert.equal(rankingOf(p, 50), null);
  assert.deepEqual(upgradeList(p, 50), []);                                           // not exported: nothing invented
  assert.equal(rankingOf({ ranking: p.ranking }, 0), p.ranking);                     // older file: g0 falls back to ranking
  assert.equal(rankingOf({ ranking: p.ranking }, 20), null);
  const l0 = upgradeList(p, 0);
  assert.deepEqual(l0.map((r) => [r.tf, r.k0, r.paper.v, r.fitFrom]), [[10, 2, 1, null], [11, 1, 2, null]]);
  const l20 = upgradeList(p, 20);
  assert.deepEqual(l20.map((r) => [r.tf, r.rank, r.approx, r.fitFrom]), [[10, 1, false, null], [11, 2, true, 4]]);
  assert.equal(l20[1].controlsFit.v, 5);
});

test('growthStory states what the file shows: order held, unlocked held, which rows moved and which way', () => {
  const p = tinyPlanner();
  const s = growthStory(p, 20);
  assert.equal(s.n, 2); assert.equal(s.sameOrder, true); assert.equal(s.sameUnlocked, true);
  assert.deepEqual(s.changed, [{ tf: 11, from: 4, to: 5 }]);
  assert.equal(s.up, 1); assert.equal(s.down, 0); assert.equal(s.approx, 1);
  p.rankingByGrowth.g20 = [p.rankingByGrowth.g20[1], p.rankingByGrowth.g20[0]];
  assert.equal(growthStory(p, 20).sameOrder, false);
  assert.equal(growthStory(p, 50), null);
});

test('Q3 rows: the shortlist, plus every row that moved at +g%, in rank order', () => {
  const sl = upgradeShortlist([{ why: 'onboard', tf: 1 }, { why: 'blocked', tf: 2 }, { why: 'little', tf: 3 }, { why: 'onboard', tf: 4 }, { why: 'onboard', tf: 5 }], 8, 2);
  assert.deepEqual(sl.map((x) => x.tf), [2, 3, 1, 4]);
  const all = [{ rank: 1, tf: 1, why: 'blocked' }, { rank: 2, tf: 2, why: 'onboard' }, { rank: 3, tf: 3, why: 'onboard' }, { rank: 4, tf: 4, why: 'onboard', fitFrom: 1 }];
  assert.deepEqual(q3Rows(all).map((x) => x.tf), [1, 2, 3, 4]);
  assert.deepEqual(upgradeShortlist(all, 8, 2).map((x) => x.tf), [1, 2, 3]);
});

test('real planner.json: rankingByGrowth.g0 is the ranking; the page\'s rows carry the transformer facts', (t) => {
  if (!PLANNER) { t.skip('no planner.json yet'); return; }
  if (!PLANNER.rankingByGrowth) { t.skip('planner.json predates rankingByGrowth'); return; }
  assert.deepEqual(PLANNER.rankingByGrowth.g0, PLANNER.ranking);
  for (const g of growthLevels(PLANNER)) {
    assert.ok(g.ok, `g${g.g} exported`);
    const l = upgradeList(PLANNER, g.g);
    assert.ok(l.length > 0);
    assert.ok(l.every((r) => Number.isInteger(r.k0) && r.paper && Number.isInteger(r.paper.v)), `g${g.g}`);
    if (g.g) {
      const s = growthStory(PLANNER, g.g);
      assert.equal(s.changed.length, l.filter((r) => r.fitFrom != null).length);
      assert.equal(s.up + s.down, s.changed.length);
    }
  }
  const s1 = q1Status(379, PLANNER, null, null);
  assert.equal(s1.aware.filter((x) => x >= 0).length, PLANNER.tfs.length);
  for (const ex of PLANNER.meta.excluded) assert.equal(s1.aware[ex], -1);
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
