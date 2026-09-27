// ui/test/pagesb-results.test.js (UI-B): the pure view functions of ui/story/results.js (Screen 3a Results).
// Run: node --test ui/test/*.test.js
// Real-data checks read ui/data first, then the dev copies in ui/story/dev-b-fixtures/ (until integration), and skip
// when neither exists.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

import {
  timeOf, clockOf, timeTicks, bandOf, hijackOf, constOf, vDigits, tilesModel, verdictOf, siblings, shortLabel, runName,
  distKmOf, voltageStems, vClass, vScale, vExtent, heatRGB, heatLegend, failureModel, freqModel, reactiveModel, branchKey,
  tagHTML, eveningDefs, decimalsOf,
} from '../story/results.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI = path.resolve(HERE, '..');
function readData(rel) {
  for (const base of [path.join(UI, 'data'), path.join(UI, 'story/dev-b-fixtures')]) {
    const p = path.join(base, rel);
    if (fs.existsSync(p)) { const b = fs.readFileSync(p); return JSON.parse(rel.endsWith('.gz') ? zlib.gunzipSync(b).toString('utf8') : b.toString('utf8')); }
  }
  return null;
}
const C = (value, label = 'REAL', cite = 'test cite') => ({ value, label, cite });
const BAND_DOC = { constants: { V_ANSI_LO: C(0.95), V_ANSI_HI: C(1.05) } };
const band = bandOf(BAND_DOC, null);
const TM = { n: 720, start: '16:00', stepS: 60 };

test('timeOf needs steps, start and stepSeconds; extras first, then meta; never a default', () => {
  assert.equal(timeOf(null, null), null);
  assert.equal(timeOf({ steps: 720 }, null), null);
  assert.equal(timeOf({ steps: 720, start: '16:00' }, null), null);
  assert.deepEqual(timeOf({ steps: 720, start: '16:00', stepSeconds: 60 }, null), TM);
  assert.deepEqual(timeOf({}, { steps: 96, start: '00:00', stepSeconds: 900 }), { n: 96, start: '00:00', stepS: 900 });
  assert.deepEqual(timeOf({ steps: 10 }, { start: '18:30', stepSeconds: 60 }), { n: 10, start: '18:30', stepS: 60 });
});

test('clockOf wraps midnight and names the end of the run', () => {
  assert.equal(clockOf(0, TM), '16:00');
  assert.equal(clockOf(479, TM), '23:59');
  assert.equal(clockOf(480, TM), '00:00');
  assert.equal(clockOf(720, TM), '04:00');
  assert.equal(clockOf(5, null), null);
});

test('timeTicks come from the clock alone: whole hours, the end of the run last', () => {
  const t = timeTicks(TM);
  assert.deepEqual(t.map((x) => x.t), ['16:00', '18:00', '20:00', '22:00', '00:00', '02:00', '04:00']);
  assert.equal(t[0].x, 0);
  assert.equal(t[t.length - 1].x, 1);
  assert.ok(t[t.length - 1].end);
  const q = timeTicks({ n: 96, start: '00:00', stepS: 900 });              // a day of 15-min steps
  assert.equal(q[0].t, '00:00');
  assert.equal(q[q.length - 1].t, '00:00');
  assert.ok(q.length <= 8);
  assert.deepEqual(timeTicks(null), []);
});

test('the voltage band and the hijack band come from named constants, never a literal', () => {
  assert.equal(band.lo.v, 0.95); assert.equal(band.hi.v, 1.05); assert.equal(band.lo.label, 'REAL');
  assert.equal(bandOf({ constants: {} }, null), null);
  assert.equal(bandOf({ constants: { V_ANSI_LO: C(0.95) } }, null), null);            // half a band is no band
  assert.equal(bandOf(null, BAND_DOC).hi.v, 1.05);                                   // catalogue fallback
  assert.equal(bandOf({ constants: { V_ANSI_LO: C(1.05), V_ANSI_HI: C(0.95) } }, null), null);
  assert.equal(constOf('X', { constants: { X: { value: 1, label: 'BOGUS' } } }), null);
  const cat = { constants: { HIJACK_MHZ_LO: C(3, 'DERIVED'), HIJACK_MHZ_HI: C(17, 'DERIVED'), HIJACK_MW: C(40, 'DERIVED') } };
  const h = hijackOf(cat);
  assert.equal(h.lo.v, 3); assert.equal(h.hi.v, 17); assert.equal(h.mw.v, 40);
  assert.equal(hijackOf({ constants: { HIJACK_MHZ_LO: C(3, 'DERIVED') } }), null);   // a single value is refused
  assert.equal(hijackOf({}), null);
  assert.equal(decimalsOf(0.95), 2); assert.equal(decimalsOf(17), 0);
});

test('a voltage just under the floor never rounds onto it, and the tile says so', () => {
  assert.equal(vDigits(0.9498, band), 4);
  assert.equal(vDigits(0.9771, band), 3);
  assert.equal(vDigits(0.9498, null), 3);
  const sm = { vMinHome: { v: 0.9498, label: 'SIM', cite: 'OpenDSS', t: '22:10' }, maxLoading: { v: 119.5, label: 'SIM', tf: 240, t: '16:45' } };
  const others = [{ name: 'Naive', summary: { vMinHome: { v: 0.9498, label: 'SIM' }, maxLoading: { v: 201.2, label: 'SIM' } } }, { name: 'X', summary: null }];
  const tiles = tilesModel(sm, others, TM, band);
  const v = tiles.find((t) => t.key === 'vMinHome');
  assert.equal(v.opts.digits, 4);
  assert.match(v.where, /one home dips just under 0\.95 pu/);
  assert.match(v.where, /not part of the capacity harm test/);
  assert.equal(v.cmp[0].text, '0.9498 pu');
  assert.equal(v.cmp[1].text, '—'); assert.ok(v.cmp[1].missing);
  const w = tiles.find((t) => t.key === 'maxLoading');
  assert.equal(w.where, 'T-240 at 16:45');
  assert.equal(w.cmp[0].text, '201.2%');
  assert.equal(tiles.find((t) => t.key === 'chargedPctBy0400').title, 'Fleet charged by 04:00');
  assert.equal(tileTitle(tilesModel(sm, [], null, band)), 'Fleet charged at the end of the run');
  assert.equal(tilesModel(null, [], TM, band).every((t) => t.big === null), true);
});
const tileTitle = (tiles) => tiles.find((t) => t.key === 'chargedPctBy0400').title;

test('every no-violation verdict says "because of batteries"; protection counts are screening', () => {
  const ok = verdictOf({ batteryCausedNormal: { v: 0, label: 'SIM' }, batteryCausedEmergency: { v: 0, label: 'SIM' }, protectionOperated: { v: 0, label: 'SIM' } }, { policy: 'aware' }, TM);
  assert.equal(ok.ok, true);
  assert.match(ok.title, /because of batteries/);
  assert.match(ok.sub, /every 1 min, 16:00 → 04:00/);
  const bad = verdictOf({ batteryCausedNormal: { v: 11, label: 'SIM' }, batteryCausedEmergency: { v: 3, label: 'SIM' }, protectionOperated: { v: 1, label: 'SIM' } }, { policy: 'naive' }, TM);
  assert.equal(bad.ok, false);
  assert.match(bad.title, /11 normal-rating events and 3 transformers in emergency and 1 fuse open/);
  assert.equal(bad.screening, true);
  assert.match(bad.sub, /screening/);
  assert.match(verdictOf({ maxLoading: { v: 122.1, label: 'SIM' } }, { policy: 'none' }, TM).title, /home load alone .* 122\.1%/);
  assert.equal(verdictOf(null, {}, TM).ok, null);
  assert.equal(verdictOf({}, { policy: 'aware' }, null).sub, 'OpenDSS every step');
});

test('evening facts: fleet money wording, reserve from the scenario lever, homes dark screening', () => {
  const d = eveningDefs({ policy: 'aware', reserve: 30 });
  assert.match(d[0].title, /^Fleet gross energy value, not Base's profit$/);
  assert.equal(d[1].title, 'Breaches of the 30% member reserve');
  assert.equal(d.find((x) => x.key === 'homesDark').opts.screening, true);
  assert.equal(eveningDefs({ policy: 'none' })[0].skip, true);
  assert.equal(eveningDefs({})[1].title, 'Member reserve breaches');
});

const CAT = {
  levers: { policy: { options: [{ id: 'none', label: 'No batteries' }, { id: 'naive', label: 'Naive: our assumption of one number, no feeder check' }, { id: 'aware', label: 'Feeder-aware' }] },
    failure: { options: [{ id: 'faults', label: 'Pieces fail: silent battery, EV spike, controller stall' }, { id: 'covert', label: 'Hidden attacker (fictional): a covert channel' }] } },
  scenarios: [
    { id: 'e/aware', levers: { evening: 'e', policy: 'aware', failure: 'none', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
    { id: 'e/naive', levers: { evening: 'e', policy: 'naive', failure: 'none', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
    { id: 'e/none', levers: { evening: 'e', policy: 'none', failure: 'none', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
    { id: 'e/aware/faults', levers: { evening: 'e', policy: 'aware', failure: 'faults', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
    { id: 'e/aware/covert', plays: 'e/aware', levers: { evening: 'e', policy: 'aware', failure: 'covert', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
    { id: 'e/aware/fleet=192', levers: { evening: 'e', policy: 'aware', failure: 'none', fleet: 192, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
    { id: 'f/aware', levers: { evening: 'f', policy: 'aware', failure: 'none', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 } },
  ],
};

test('siblings: same evening and fleet levers, every policy and failure, replays not listed twice', () => {
  const ids = siblings(CAT.scenarios[0], CAT).map((s) => s.id);
  assert.deepEqual(ids, ['e/none', 'e/naive', 'e/aware/faults']);
  assert.deepEqual(siblings(CAT.scenarios[4], CAT).map((s) => s.id), ['e/none', 'e/naive', 'e/aware', 'e/aware/faults']);
  assert.deepEqual(siblings(CAT.scenarios[5], CAT).map((s) => s.id), []);
  assert.equal(shortLabel('Naive: our assumption of one number, no feeder check'), 'Naive');
  assert.equal(runName(CAT.scenarios[3], CAT), 'Feeder-aware + Pieces fail');
  assert.equal(runName(CAT.scenarios[1], CAT, false), 'Naive: our assumption of one number, no feeder check');
  assert.equal(branchKey('p1/days/2026-07-22/aware.json.gz'), 'aware');
  assert.equal(branchKey('p1/aware_faults.json'), 'aware_faults');
});

test('busDistKm is indexed by position in busOrder (A.12), not by transformer', () => {
  const ex = { busOrder: [2, 0, 1], busDistKm: [0.1, 0.5, 2.25] };
  assert.equal(distKmOf(ex, 2), 0.1);
  assert.equal(distKmOf(ex, 0), 0.5);
  assert.equal(distKmOf(ex, 1), 2.25);
  assert.equal(distKmOf(ex, 7), null);
  assert.equal(distKmOf({ busOrder: [0] }, 0), null);
});

test('voltage stems: ordered by busOrder, classed against the band, isolated flagged', () => {
  const row = [1040, 0, 944, 1060];
  const sc = vScale(band, vExtent([row]));
  assert.ok(sc.lo <= 0.94 && sc.hi >= 1.06);
  const st = voltageStems(row, [3, 1, 0, 2], sc, band);
  assert.deepEqual(st.map((s) => s.i), [3, 1, 0, 2]);
  assert.equal(st[0].cls, 'over'); assert.ok(st[1].iso); assert.equal(st[2].cls, 'ok'); assert.equal(st[3].cls, 'under');
  assert.ok(st[0].x < st[2].x && st[2].x < st[3].x);
  assert.equal(vClass(0.9, null), 'ok');                                              // no band: no red claim
  const sc2 = vScale(null, { lo: 0.97, hi: 1.03 });
  assert.ok(sc2.lo < 0.97 && sc2.hi > 1.03);
  assert.equal(vScale(null, null), null);
});

test('heat map colours and legend take their numbers from the band only', () => {
  assert.deepEqual(heatRGB(0, band, null), [107, 111, 108]);
  assert.deepEqual(heatRGB(940, band, null), [178, 58, 47]);
  assert.deepEqual(heatRGB(1060, band, null), [110, 29, 23]);
  const hi = heatRGB(1050, band, null), lo = heatRGB(950, band, null);
  assert.ok(hi[0] > lo[0]);                                                            // lighter near the top
  const L = heatLegend(band).map((x) => x.text);
  assert.deepEqual(L, ['1.05 → 0.95 pu', 'below 0.95', 'above 1.05', 'isolated']);
  const band3 = bandOf({ constants: { V_ANSI_LO: C(0.917), V_ANSI_HI: C(1.058) } }, null);
  assert.deepEqual(heatLegend(band3).map((x) => x.text).slice(0, 3), ['1.058 → 0.917 pu', 'below 0.917', 'above 1.058']);
  assert.equal(heatLegend(null).some((x) => /\d/.test(x.text)), false);
});

test('reactive power: the file stores tenths; missing fields give null', () => {
  const m = reactiveModel({ headKVAr: [1000, 2000], capKVAr: [3000, 3000] });
  assert.deepEqual(m.head, [100, 200]); assert.deepEqual(m.cap, [300, 300]);
  assert.equal(m.lo, 0); assert.ok(m.hi > 300);
  assert.equal(reactiveModel({ headKVAr: [1] }), null);
  assert.equal(reactiveModel(null), null);
});

test('failure cards read their summaries; nothing is invented when a file is missing', () => {
  const lab = (v, label = 'SIM') => ({ v, label, cite: 'c' });
  const f = failureModel('faults', { chaos: { constants: { CHAOS_RUNS: C(50, 'ASSUMPTION') }, runsWithBatteryCaused: lab(0), batteryCausedNormal: lab(0), reserveBreaches: lab(0), minChargedPctResponsive: lab(99.6) },
    failures: [{ t: '22:16', text: 'Home 0222 goes silent' }] });
  assert.equal(f.rows[0].x.v, 50);
  assert.equal(f.rows[0].x.label, 'ASSUMPTION');
  assert.deepEqual(f.lines, ['22:16 · Home 0222 goes silent']);
  assert.equal(failureModel('faults', {}).missing, 'p1/chaos.json not loaded');
  const w = failureModel('worker_kill', { summary: { takeoverSeconds: lab(240), killCostMaxKW: lab(0.6), lateCommands: lab(31) }, runtime: { kill: { t: '22:20', text: 'worker W2 is killed' }, takeover: [{ t: '22:24', text: 'W1 takes over' }] } });
  assert.equal(w.rows.find((r) => r.k.startsWith('Takeover')).x.v, 240);
  assert.equal(w.rows.find((r) => r.k.startsWith('Refused')).x, null);
  assert.equal(w.sub, '22:20 · worker W2 is killed');
  assert.equal(failureModel('worker_kill', {}).missing, 'takeover summary not exported');
  const cv = failureModel('covert', { attackSummary: { detected: lab(24), shard: lab(24, 'ASSUMPTION'), detectionSeconds: lab(180) } });
  assert.equal(cv.rows[0].x.v, '24 of 24');
  assert.match(cv.note, /Fictional attacker/);
  assert.equal(failureModel('covert', {}).rows.length, 0);
  assert.ok(failureModel('covert', {}).missing);
  assert.equal(failureModel('none', {}), null);
});

test('frequency card: the day\'s own range; the hijack band hangs from f0 only when both exist', () => {
  const f = { series_1min: { t0_cdt: '2026-09-25 00:00 CDT', f_mean_hz: [60.01, 59.99, 60.0] }, constants: { f0_hz: 60 }, stats: { frequency: { sigma_mhz: 13.51 } } };
  const h = hijackOf({ constants: { HIJACK_MHZ_LO: C(3, 'DERIVED'), HIJACK_MHZ_HI: C(17, 'DERIVED') } });
  const m = freqModel(f, h);
  assert.equal(m.day, '2026-09-25');
  assert.equal(m.dmin, 59.99); assert.equal(m.dmax, 60.01);
  assert.ok(m.bandTop < m.bandBot);                                                   // 3 mHz sits above 17 mHz down
  assert.equal(m.sigma.v, 13.51); assert.equal(m.sigma.label, 'DERIVED');
  assert.equal(freqModel(f, null).bandTop, null);
  assert.equal(freqModel({ series_1min: {} }, h), null);
});

test('tags use the shell markup; SCREENING is added, never substituted', () => {
  assert.equal(tagHTML('SIM', 'x'), '<span class="chip chip-SIM" title="x">SIM</span>');
  assert.match(tagHTML('SIM', null, true), /chip-SIM.*chip-SCREENING/);
});

test('real files (ui/data or the dev copies): every catalogue scenario builds its models', (t) => {
  const cat = readData('story/index.json');
  if (!cat) { t.skip('no story/index.json yet'); return; }
  const b = bandOf(null, cat);
  assert.ok(b, 'the catalogue exports V_ANSI_LO / V_ANSI_HI');
  assert.ok(hijackOf(cat), 'the catalogue exports the hijack band');
  for (const s of cat.scenarios) {
    const tiles = tilesModel(s.summary, siblings(s, cat).map((o) => ({ name: runName(o, cat), summary: o.summary })), TM, b);
    for (const t of tiles) for (const c of t.cmp) assert.doesNotMatch(c.text, /NaN|undefined/, `${s.id} ${t.key}`);
    const v = verdictOf(s.summary, s.levers, TM);
    if (v.ok) assert.match(v.title, /because of batteries/, s.id);
  }
  const ex = readData(cat.scenarios.find((s) => s.id === cat.default).extras);
  if (ex) {
    const tm = timeOf(ex, null);
    assert.ok(tm);
    assert.equal(ex.vTfMilli.length, tm.n);
    assert.equal(new Set(ex.busOrder).size, ex.busOrder.length);
    assert.ok(bandOf(ex, null), 'the extras carry the band');
    assert.ok(distKmOf(ex, ex.busOrder[0]) <= distKmOf(ex, ex.busOrder[ex.busOrder.length - 1]));
  }
});

test('no typed-in data values in results.js (the lead\'s static-number scan)', () => {
  const src = fs.readFileSync(path.join(UI, 'story/results.js'), 'utf8').replace(/^\s*\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '');
  for (const bad of [/\b0\.95\b/, /\b1\.05\b/, /\b720\b/, /'16:00'/, /'04:00'/, /3[–-]17/, /3[–-]5 mHz/, /\b1,000\b/, /\b379\b/]) assert.doesNotMatch(src, bad, String(bad));
});
