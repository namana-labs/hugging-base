// ui/test/p2.test.js (L5): the P2 panel's pure pieces, the counterfactual sentence, and beats.json.
// Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import * as fmt from '../lib/format.js';
import { parseLink, VIEWS } from '../lib/data.js';
import {
  parseCombo, comboId, counterpart, findCandidate, rankOf, flipVerdict, fleetTotals, counterfactualParts,
  counterfactualText, counterfactualHTML, tfName, FLIP_HEADLINE_MAX_OVERLAP, bulk, p2SceneModel,
} from '../panels/p2.js';
import { FACTS, placeholders, stripPlaceholders, sourcesFor, evalFact, resolveCaption, beatHref } from '../panels/more.js';
import * as sceneModel from '../lib/scene-model.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJSON = (p) => JSON.parse(fs.readFileSync(path.join(UI, 'data', p), 'utf8'));
const topology = readJSON('topology.json');
const fx = (p) => readJSON('fixtures/' + p);
const index = fx('p2/index.json');
const beatsDoc = readJSON('beats.json');
const beats = beatsDoc.beats;

// Digits allowed in prose only as parts of ids: home labels, transformer names, SMART-DS profile names, the month.
const ID_TOKENS = [/Home \d{4}/g, /T-\d+/g, /(res|com)_kw(ar)?_\d+_pu/g, /\b\d{4}-\d{2}(-\d{2})?\b/g, /[A-Z][a-z]+ \d{4}\b/g];
const stripIds = (s) => ID_TOKENS.reduce((a, re) => a.replace(re, ''), s);

test('p2: combo ids round-trip over the 16 combos, and counterpart flips the policy', () => {
  assert.equal(index.combos.length, 16);
  for (const id of index.combos) {
    const c = parseCombo(id);
    assert.ok(c, id);
    assert.equal(comboId(c), id);
    const o = counterpart(id);
    assert.ok(index.combos.includes(o), o);
    assert.notEqual(parseCombo(o).policy, c.policy);
    assert.equal(counterpart(o), id);
  }
  assert.equal(parseCombo('../../etc'), null);
  assert.ok(index.combos.includes(index.default));
});

test('p2: findCandidate by home id and via alsoOnTf; rankOf', () => {
  const doc = fx('p2/aware-core-d26-g0.json');
  const e = doc.ranking[2];
  const id = topology.homes[e.home].id;
  assert.equal(findCandidate(doc, topology, id).entry.rank, e.rank);
  assert.equal(findCandidate(doc, topology, id).via, 'home');
  const doc2 = JSON.parse(JSON.stringify(doc));
  const ranked = new Set(doc.ranking.flatMap((x) => [x.home, ...(x.alsoOnTf || [])]));
  const sib = topology.homes.findIndex((h, i) => !ranked.has(i) && !h.battery);
  doc2.ranking[2].alsoOnTf = [sib];
  const r = findCandidate(doc2, topology, topology.homes[sib].id);
  assert.equal(r.via, 'alsoOnTf');
  assert.equal(r.entry.rank, e.rank);
  assert.equal(rankOf(doc2, sib), e.rank);
  assert.equal(findCandidate(doc, topology, 'no-such-home').entry, null);
  assert.equal(findCandidate(doc, topology, null).home, -1);
});

test('p2: the flip headline appears only when the measured flip supports it', () => {
  const L = (v) => ({ v, label: 'DERIVED' });
  assert.equal(flipVerdict({ top10Overlap: L(3) }).supports, true);
  assert.equal(flipVerdict({ top10Overlap: L(FLIP_HEADLINE_MAX_OVERLAP) }).supports, true);
  assert.equal(flipVerdict({ top10Overlap: L(FLIP_HEADLINE_MAX_OVERLAP + 1) }).supports, false);
  assert.equal(flipVerdict({ top10Overlap: L(10) }).headline, null);
  // the untied set must agree when it is big enough to judge
  assert.equal(flipVerdict({ top10Overlap: L(2), untied: { top10Overlap: L(9), spearman: L(0.9), n: L(40) } }).supports, false);
  assert.equal(flipVerdict({ top10Overlap: L(2), untied: { top10Overlap: L(9), spearman: L(0.9), n: L(5) } }).supports, true);
  assert.equal(flipVerdict({}).supports, false);
  assert.equal(flipVerdict(index.flip).supports, index.flip.top10Overlap.v <= FLIP_HEADLINE_MAX_OVERLAP);
});

test('p2: fleet counterfactual totals sum per policy', () => {
  const fc = { none: { h100: [0.5, 0, 1.25], normalEvents: [0, 1, 0], emergencyN: [0, 0, 2] }, naive: { h100: [2, 2, 2], normalEvents: [1, 1, 0], emergencyN: [1, 0, 0] } };
  const t = fleetTotals(fc);
  assert.deepEqual(t.none, { h100: 1.75, normalTfs: 1, normalEvents: 1, emergencyN: 2 });
  assert.deepEqual(t.naive, { h100: 6, normalTfs: 2, normalEvents: 2, emergencyN: 1 });
  assert.equal(t.aware, undefined);
  assert.ok(fleetTotals(index.fleetCounterfactual).aware);
});

function stressedEntry(doc) {
  // A hand-built entry in the contract's shape (A.8): transformer 240, Home 0409, the shared res_kw_38274 spike.
  const S = (v) => ({ v, label: 'SIM', cite: 'test' });
  return {
    rank: 1, home: 408, tf: 240, reason: 'relieves a stressed transformer', alsoOnTf: [561], tieBroken: false,
    noNewViolation: S(true), peakWithPct: S(96.4), stressAvoidedH: S(0.5), stressAddedH: S(0), reliefKWh: S(1.2),
    revenueUSD: { v: 41.3, label: 'DERIVED', cite: 'test' }, curtailKWh: S(0), protectionWith: S(false), homesDarkWith: [],
    driver: { home: 408, label: 'Home 0409', profile: 'res_kw_38274_pu', kwAtPeak: S(22.7), sharedWith: ['Home 0212', 'Home 0504'] },
    before: { peakPct: S(119.5), h100: S(0.5) }, after: { peakPct: S(96.4), h100: S(0) }, opendss: null, screening: true,
    _doc: doc,
  };
}

test('p2: the counterfactual sentence is built from data, names the shared driver, and labels every number', () => {
  const doc = fx('p2/aware-core-d26-g0.json');
  const e = stressedEntry(doc);
  const args = { entry: e, doc, index, topology, combo: 'aware-core-d26-g0' };
  const txt = counterfactualText(args, fmt);
  assert.match(txt, /^In August 2026 transformer T-240 spent 0\.50 h SIM above nameplate without a new battery \(peak 119\.5% SIM\)/);
  assert.match(txt, /driven by one home's load, Home 0409 \(SMART-DS profile res_kw_38274_pu, the same profile as Home 0212, Home 0504: one shape, not independent evidence\)/);
  assert.match(txt, /With a Core at Home 0409 under feeder-aware dispatch: 0\.00 h SIM above nameplate, peak 96\.4% SIM, August energy value \$41 DERIVED\./);
  assert.match(txt, /It avoids 0\.50 h SIM of stress/);
  // every labelled part is labelled; prose has no digits of its own
  for (const p of counterfactualParts(args)) {
    if (typeof p === 'string') assert.ok(!/\d/.test(stripIds(p)), `bare digit in prose: ${JSON.stringify(p)}`);
    else assert.ok(fmt.isLabelled(p), `unlabelled part ${JSON.stringify(p)}`);
  }
  const html = counterfactualHTML(args, fmt);
  assert.equal((html.match(/class="chip chip-/g) || []).length, counterfactualParts(args).filter((p) => typeof p !== 'string').length);
});

test('p2: the counterfactual says "where NOT to put it" and names dark homes only when the data says so', () => {
  const doc = fx('p2/naive-core-d26-g0.json');
  const e = stressedEntry(doc);
  e.noNewViolation = { v: false, label: 'SIM' };
  e.stressAddedH = { v: 1.5, label: 'SIM' };
  e.protectionWith = { v: true, label: 'SIM' };
  e.homesDarkWith = [561];
  const txt = counterfactualText({ entry: e, doc, index, topology, combo: 'naive-core-d26-g0' }, fmt);
  assert.match(txt, /under naive dispatch \(no feeder check\)/);
  assert.match(txt, /It adds a new violation \(1\.50 h SIM of added stress\): where NOT to put it\./);
  assert.match(txt, /Protection may operate here \(ASSUMPTION rule\): Home 0562 go dark while battery homes island and stay lit\./);
  // not stressed: no driver claim, no "spent ... above nameplate"
  const calm = stressedEntry(doc);
  calm.before = { peakPct: { v: 61.2, label: 'SIM' }, h100: { v: 0, label: 'SIM' } };
  calm.driver = null;
  const t2 = counterfactualText({ entry: calm, doc, index, topology, combo: 'aware-core-d26-g0' }, fmt);
  assert.match(t2, /stayed at or below nameplate without a new battery \(peak 61\.2% SIM\)/);
  assert.ok(!/SMART-DS profile/.test(t2));
});

test('p2: a bare number in a candidate fails loudly (format.js throws), never renders unlabelled', () => {
  const doc = fx('p2/aware-core-d26-g0.json');
  const e = stressedEntry(doc);
  e.peakWithPct = 96.4;
  assert.throws(() => counterfactualText({ entry: e, doc, index, topology, combo: 'aware-core-d26-g0' }, fmt), fmt.LabelError);
});

test('p2: fixture candidates all render a sentence; bulk values take their series label', () => {
  for (const id of index.combos) {
    const doc = fx(`p2/${id}.json`);
    for (const e of doc.ranking.slice(0, 10)) {
      const t = counterfactualText({ entry: e, doc, index, topology, combo: id }, fmt);
      assert.match(t, new RegExp(`transformer ${tfName(topology, e.tf).replace(/[()]/g, '\\$&')}`));
    }
  }
  assert.deepEqual(bulk({ series: { baseline: { label: 'SIM' } } }, 'baseline', 3), { v: 3, label: 'SIM' });
  assert.deepEqual(bulk({ series: {} }, 'x', 3, 'c'), { v: 3, label: 'SIM', cite: 'c' });
});

test('p2: the scene gets numbered candidate pins and greedy placements as new columns', () => {
  const doc = fx('p2/aware-core-d26-g0.json');
  const ctx = { topology, footprints: null, sceneModel, theme: 'light' };
  const base = sceneModel.buildSceneModel({ topology, frame: sceneModel.frameFromP2(doc), view: 'p2' });
  const m = p2SceneModel(ctx, { doc, n: 3, p1meta: { unrelieved: [{ tf: 240 }] } });
  assert.equal(m.labels.filter((l) => l.pin).length, Math.min(10, doc.ranking.length));
  assert.equal(m.labels.find((l) => l.pin).text, '#1');
  assert.equal(m.batteries.filter((b) => b.placed).length, 3);
  assert.equal(m.batteries.length, base.batteries.length + 3);
  assert.equal(m.labels.filter((l) => l.handoff).length, 1);
});

// ------------------------------------------------------------------------------------------------ beats.json
test('beats.json: envelope, unique ids, the video clock runs 0:00 -> 5:00 with no gaps', () => {
  assert.equal(beatsDoc.schema, 'hb.beats.v1');
  const ids = beats.map((b) => b.id);
  assert.equal(new Set(ids).size, ids.length);
  const sec = (s) => { const [m, x] = s.split(':').map(Number); return m * 60 + x; };
  assert.equal(beats[0].t0, '0:00');
  assert.equal(beats[beats.length - 1].t1, '5:00');
  for (let i = 1; i < beats.length; i++) assert.equal(beats[i].t0, beats[i - 1].t1, `gap before ${beats[i].id}`);
  for (const b of beats) assert.ok(sec(b.t1) > sec(b.t0), b.id);
  for (const b of beats) assert.ok(['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'].includes(b.label), b.id);
});

test('beats.json: no bare digits in any caption or title (numbers come from data, with labels)', () => {
  for (const b of beats) {
    assert.ok(!/\d/.test(stripPlaceholders(b.caption)), `${b.id}: bare digit in caption: ${stripPlaceholders(b.caption).match(/.{0,20}\d.{0,20}/)}`);
    assert.ok(!/\d/.test(b.title), `${b.id}: bare digit in title`);
  }
  // the admit half: the check does catch one
  assert.ok(/\d/.test(stripPlaceholders('A reaches 197% of nameplate {{naiveMax}}')));
  assert.ok(!/\d/.test(stripPlaceholders('A reaches {{naiveMax}} of nameplate')));
});

test('beats.json: every placeholder is a known fact or a chip with a valid label', () => {
  for (const b of beats) {
    for (const p of placeholders(b.caption)) {
      if (p.chip !== undefined) assert.ok(['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'].includes(p.chip), `${b.id}: chip ${p.chip}`);
      else assert.ok(FACTS[p.name], `${b.id}: unknown fact {{${p.name}}}`);
    }
  }
});

test('beats.json: every link is a valid deep link (view, branch, combo) and the naive beats carry the ASSUMPTION chip', () => {
  for (const b of beats) {
    const q = new URLSearchParams(b.link);
    const l = parseLink('?' + b.link);
    assert.ok(VIEWS.includes(q.get('view')) && l.view === q.get('view'), `${b.id}: view`);
    if (q.has('branch')) assert.equal(l.branch, q.get('branch'), `${b.id}: branch`);
    if (q.has('t')) assert.equal(l.t, q.get('t'), `${b.id}: t`);
    if (q.has('combo')) assert.ok(index.combos.includes(q.get('combo')), `${b.id}: combo`);
    assert.equal(beatHref(b), `?${b.link}&beat=${b.id}`);
  }
  const problem = beats.find((b) => b.id === 'problem');
  assert.match(problem.caption, /no feeder check, all at once at the onset \{\{chip:ASSUMPTION:/);
  assert.match(beats.find((b) => b.id === 'money').caption, /not local relief/);
});

test('beats.json: captions resolve against the committed fixtures, with a label on every value', () => {
  const S = {
    topology, p1meta: fx('p1/meta.json'), p2index: index,
    'p1:naive': fx('p1/naive.json'), 'p1:aware': fx('p1/aware.json'), 'p1:aware_faults': fx('p1/aware_faults.json'),
    'p2:aware-core-d26-g0': fx('p2/aware-core-d26-g0.json'), 'p2:naive-core-d26-g0': fx('p2/naive-core-d26-g0.json'),
    engine: null,
  };
  const need = sourcesFor(beats.map((b) => b.caption));
  for (const k of need) assert.ok(k in S, `test is missing source ${k}`);
  const resolvedFacts = new Set();
  for (const b of beats) {
    const txt = resolveCaption(b.caption, S, fmt, { html: false });
    assert.ok(!/\{\{|\}\}/.test(txt), `${b.id}: unresolved placeholder`);
    const html = resolveCaption(b.caption, S, fmt, { html: true });
    assert.ok(!/\{\{/.test(html));
    for (const p of placeholders(b.caption)) if (p.name && evalFact(p.name, S)) resolvedFacts.add(p.name);
  }
  // the core story facts resolve on fixtures (the rest need real-only data: engine.json, fault constants)
  for (const f of ['streetHomes', 'streetTfs', 'fleetSize', 'reliefT', 'reliefNone', 'reliefDriverProfile', 'reliefDriverShared',
    'unrelievedTf', 'dischargeSlots', 'onsetT', 'onsetPrice', 'eveningPeakPrice', 'eveningPeakT', 'naiveMax', 'naiveMaxTf',
    'awareBatteryNormal', 'awareVerdict', 'faultCommsT', 'flipOverlap', 'awareTop1', 'awareTop1UnderNaive', 'capNaive', 'capAware',
    'energyNaive', 'costOfAwareness', 'capacityLow', 'capacityHigh', 'insightTfHour', 'insightPriceHour']) {
    // (naiveBackfeedMax needs the real 16:00 window: the P1 fixture covers 21:30-23:30, after the discharge intervals)
    assert.ok(resolvedFacts.has(f) || !beats.some((b) => b.caption.includes(`{{${f}}}`)), `fact ${f} did not resolve on fixtures`);
  }
  // REAL facts from the real price series: the 23 Aug evening peak and the D-26 onset
  assert.equal(fmt.fmt(evalFact('onsetPrice', S)[0], evalFact('onsetPrice', S)[0].o), '$55.42 REAL');
  assert.equal(evalFact('onsetT', S)[0].v, '22:00');
  const pk = evalFact('eveningPeakPrice', S)[0];
  assert.equal(pk.label, 'REAL');
  // a missing source renders "(not built yet)", never a number
  const t = resolveCaption('A reads {{reliefNone}}.', { topology }, fmt, { html: false });
  assert.equal(t, 'A reads (not built yet).');
});

test('docs/demo-script.md lists every beat with its exact deep link (same ids as beats.json)', () => {
  const doc = fs.readFileSync(path.join(UI, '..', 'docs', 'demo-script.md'), 'utf8');
  for (const b of beats) {
    assert.ok(doc.includes(`(\`${b.id}\`)`), `demo-script.md is missing beat ${b.id}`);
    assert.ok(doc.includes(`\`?${b.link}&beat=${b.id}\``), `demo-script.md has a stale link for ${b.id}`);
    assert.ok(doc.includes(`${b.t0}–${b.t1}`), `demo-script.md has a stale clock for ${b.id}`);
  }
  assert.equal((doc.match(/^\| \d:\d\d–\d:\d\d \|/gm) || []).length, beats.length);
});

test('driver.sharedWith as real objects ({home, label, tf}) reads as names with their transformer', () => {
  const doc = fx('p2/aware-core-d26-g0.json');
  const e = stressedEntry(doc);
  e.driver.sharedWith = [{ home: 211, label: 'Home 0212', tf: 150 }, { home: 503, label: 'Home 0504', tf: 103 }];
  const txt = counterfactualText({ entry: e, doc, index, topology, combo: 'aware-core-d26-g0' }, fmt);
  assert.match(txt, /the same profile as Home 0212 on T-150, Home 0504 on T-103: one shape/);
  assert.ok(!/object Object/.test(txt));
  const meta = JSON.parse(JSON.stringify(fx('p1/meta.json')));
  meta.relief.driver.sharedWith = [{ home: 408, label: 'Home 0409', tf: 240 }];
  assert.equal(resolveCaption('{{reliefDriverShared}}', { topology, p1meta: meta }, fmt, { html: false }), 'Home 0409 on T-240');
  // minutesOver100 with none/aware siblings (the real P1 shape)
  meta.relief.minutesOver100 = { v: 17, label: 'SIM', none: 17, aware: 0 };
  assert.equal(resolveCaption('{{reliefMinutesNone}} -> {{reliefMinutesAware}}', { topology, p1meta: meta }, fmt, { html: false }), '17 min SIM -> 0 min SIM');
});

test('L3 shapes: bare untied.n, OpenDSS numbers replace screening numbers in the sentence when refereed', async () => {
  const L = (v, label = 'DERIVED') => ({ v, label });
  assert.equal(flipVerdict({ top10Overlap: L(2), untied: { top10Overlap: L(9), spearman: L(0.9), n: 40 } }).supports, false);
  assert.equal(flipVerdict({ top10Overlap: L(2), untied: { top10Overlap: L(1), spearman: L(0.1), n: 40 } }).supports, true);
  const { checkedByOpenDSS } = await import('../panels/p2.js');
  const doc = fx('p2/aware-core-d26-g0.json');
  const e = stressedEntry(doc);
  assert.equal(checkedByOpenDSS(e), false);
  e.opendss = { before: null, after: null };
  assert.equal(checkedByOpenDSS(e), false, 'after = null means not refereed');
  const O = (v) => ({ v, label: 'SIM', cite: 'OpenDSS (sim.referee)' });
  e.opendss = { before: { peakPct: O(121.9), h100: O(0.75) }, after: { peakPct: O(97.1), h100: O(0) } };
  e.screening = false;
  assert.equal(checkedByOpenDSS(e), true);
  const txt = counterfactualText({ entry: e, doc, index, topology, combo: 'aware-core-d26-g0' }, fmt);
  assert.match(txt, /spent 0\.75 h SIM above nameplate without a new battery \(peak 121\.9% SIM\)/);
  assert.match(txt, /under feeder-aware dispatch \(OpenDSS month run\): 0\.00 h SIM above nameplate, peak 97\.1% SIM/);
});

// ------------------------------------------------------------------------------------ fix round 0 (judge F6)
// The faults beat once hard-coded "transformer C runs hot ... and charge shifts away" while C's batteries were idle
// (sim.verify p1: "C's batteries +0.0 -> +0.0 -> +0.0 kW ... the throttle is not exercised"). The hot-transformer
// clause is now measured (more.js hotOutcome); these tests fail if a caption asserts a shift the data did not show.
import { hotOutcome, chargeOrder, fleetOn } from '../panels/more.js';

const SHIFT_CLAIM = /shift(s|ed)? (away|to|elsewhere)|charge shifts|throttl|moves? away|re-?balanced/i;
const realJSON = (p) => { try { return readJSON(p); } catch { return null; } };

/** A synthetic aware_faults world: one hot event on transformer C at step 5 (3 minutes), C's batteries given by kw(k). */
function hotWorld(kwOnC) {
  const C = topology.focus.find((f) => f.key === 'C').tf;
  const js = fleetOn(topology, C);
  assert.ok(js.length >= 1, 'C has batteries in the topology');
  const steps = 12;
  const meta = { start: '22:00', stepSeconds: 60, steps, constants: { MIN_GRANT_KW: { value: 0.5, label: 'ASSUMPTION' }, HOT_MINUTES: { value: 3, label: 'ASSUMPTION', cite: 't' } },
    events: { aware_faults: [{ step: 5, t: '22:05', kind: 'hot', tf: C, home: topology.transformers[C].homes[0], deltaKW: 7.2, minutes: 3 }] } };
  const doc = {
    series: { batKW: { label: 'SIM' }, loading: { label: 'SIM' } },
    batKW: Array.from({ length: steps }, (_, k) => Array.from({ length: topology.fleet.length }, (_, j) => (js.includes(j) ? Math.round(kwOnC(k) * 10 / js.length) : 0))),
    loading: Array.from({ length: steps }, (_, k) => Array.from({ length: topology.transformers.length }, (_, t) => (t === C ? 500 + 10 * k : 300))),
  };
  return { meta, doc, C };
}
const faultsBeat = () => beats.find((b) => b.id === 'faults');
const resolveHot = (w) => resolveCaption(faultsBeat().caption, { topology, p1meta: w.meta, 'p1:aware_faults': w.doc }, fmt, { html: false });

test('faults beat (F6): the caption template asserts no shift or throttle of its own; the clause comes from data', () => {
  const b = faultsBeat();
  assert.ok(!SHIFT_CLAIM.test(stripPlaceholders(b.caption)), `static shift claim in the faults caption: ${stripPlaceholders(b.caption)}`);
  assert.ok(b.caption.includes('{{faultHotOutcome}}'), 'the hot-transformer outcome must be the measured fact');
  // the admit half: the old caption is caught
  assert.ok(SHIFT_CLAIM.test(stripPlaceholders('At {{faultHotT}} transformer C runs hot ({{evKW}} of new load) and charge shifts away.')));
});

test('faults beat (F6): idle batteries on the hot transformer -> "no charge to shift", never a shift or throttle', () => {
  const w = hotWorld(() => 0);
  const h = hotOutcome(w.meta, w.doc, topology);
  assert.equal(h.state, 'idle');
  assert.equal(h.firstChargeStep, null);
  const txt = resolveHot(w);
  assert.match(txt, /Its batteries were not charging when the load arrived \(0\.0 kW SIM\), so there was no charge to shift\./);
  assert.match(txt, /its batteries stayed idle throughout/);
  assert.ok(!SHIFT_CLAIM.test(txt.replace('no charge to shift', '')), `idle batteries but the caption claims a shift: ${txt}`);
  // idle at the event, charging later in the window: says when and how much, still no shift claim
  const w2 = hotWorld((k) => (k >= 7 ? 12.6 : 0));
  const t2 = resolveHot(w2);
  assert.match(t2, /no charge to shift\. During the event it peaked at 57\.0% SIM of nameplate, with its batteries charging from 22:07 SIM at up to \+12\.6 kW SIM\./);
  assert.ok(!SHIFT_CLAIM.test(t2.replace('no charge to shift', '')));
});

test('faults beat (F6): a real throttle is reported as measured (before -> after), and "kept charging" is not a throttle', () => {
  const cut = hotWorld((k) => (k < 6 ? 19.6 : 8.0));
  assert.equal(hotOutcome(cut.meta, cut.doc, topology).state, 'throttled');
  assert.match(resolveHot(cut), /Its batteries were throttled from \+19\.6 kW SIM to \+8\.0 kW SIM within a minute\./);
  const kept = hotWorld(() => 10);
  assert.equal(hotOutcome(kept.meta, kept.doc, topology).state, 'kept');
  const tk = resolveHot(kept);
  assert.match(tk, /Its batteries kept charging \(\+10\.0 kW SIM, then \+10\.0 kW SIM\)\./);
  assert.ok(!/throttled/.test(tk));
  // missing branch file -> "(not built yet)", never a guess
  assert.match(resolveCaption('{{faultHotOutcome}}', { topology, p1meta: cut.meta }, fmt, { html: false }), /^\(not built yet\)$/);
});

test('faults beat (F6), REAL data: the clause matches aware_faults focus.C, the path sim.verify p1 prints', { skip: !realJSON('p1/meta.json') && 'no real P1 data' }, () => {
  const meta = realJSON('p1/meta.json'), af = realJSON('p1/aware_faults.json');
  const e = meta.events.aware_faults.find((x) => x.kind === 'hot');
  const key = topology.transformers[e.tf].focus;
  const f = af.focus[key];
  assert.equal(f.tf, e.tf);
  const h = hotOutcome(meta, af, topology);
  // independent path: the branch's focus.<key>.batKW (tenths of kW) at Tc+34..+36, as sim.verify p1 reads it
  assert.deepEqual([h.before, h.at, h.after], [f.batKW[e.step - 1] / 10, f.batKW[e.step] / 10, f.batKW[e.step + 1] / 10]);
  const S = { topology, p1meta: meta, 'p1:aware_faults': af };
  const txt = resolveCaption(faultsBeat().caption, S, fmt, { html: false });
  assert.ok(!/not built yet/.test(txt), txt);
  if (h.state === 'idle') {
    assert.match(txt, /no charge to shift/);
    assert.ok(!SHIFT_CLAIM.test(txt.replace('no charge to shift', '')), `C idle at the event but the caption claims a shift: ${txt}`);
  }
  const peak = Math.max(...af.loading.slice(e.step, e.step + e.minutes).map((r) => r[e.tf])) / 10;
  assert.ok(txt.includes(`peaked at ${peak.toFixed(1)}% SIM`), `peak ${peak} not in: ${txt}`);
});

test('rebound-aware beat: states the measured order charge reaches A-D (the rotation EXPECT is refuted), no "down the street" claim', () => {
  const b = beats.find((x) => x.id === 'rebound-aware');
  assert.ok(!/down the street|A → B → C → D|A-B-C-D|rotat/i.test(stripPlaceholders(b.caption)), stripPlaceholders(b.caption));
  assert.ok(b.caption.includes('{{chargeOrder}}'));
  const meta = realJSON('p1/meta.json'), aw = realJSON('p1/aware.json');
  if (!meta || !aw) return;
  const o = chargeOrder(meta, aw, topology);
  assert.equal(o.length, 4);
  for (const x of o) {
    const kw = aw.focus[x.key].batKW;
    const first = kw.findIndex((v, k) => k >= meta.tc.step && v / 10 > 0.5);
    assert.equal(x.step, first, `first charge on ${x.key}`);
  }
  for (let i = 1; i < o.length; i++) assert.ok(o[i].step >= o[i - 1].step);
});

test('beats.json on the REAL committed data: every placeholder resolves (no "(not built yet)"), every value labelled', { skip: !(realJSON('p1/meta.json') && realJSON('p2/index.json')) && 'real P1/P2 data not built' }, () => {
  const S = {
    topology, p1meta: realJSON('p1/meta.json'), p2index: realJSON('p2/index.json'), engine: realJSON('engine.json'),
    'p1:naive': realJSON('p1/naive.json'), 'p1:aware': realJSON('p1/aware.json'), 'p1:aware_faults': realJSON('p1/aware_faults.json'),
    'p2:aware-core-d26-g0': realJSON('p2/aware-core-d26-g0.json'), 'p2:naive-core-d26-g0': realJSON('p2/naive-core-d26-g0.json'),
  };
  for (const b of beats) {
    for (const p of placeholders(b.caption)) {
      if (!p.name) continue;
      const parts = evalFact(p.name, S);
      assert.ok(parts, `${b.id}: {{${p.name}}} did not resolve on real data`);
      for (const x of parts) if (typeof x !== 'string') assert.ok(fmt.isLabelled(x), `${b.id}: {{${p.name}}} unlabelled ${JSON.stringify(x)}`);
    }
    const txt = resolveCaption(b.caption, S, fmt, { html: false });
    assert.ok(!/not built yet/.test(txt), `${b.id}: ${txt}`);
  }
  // spot values that sim.verify p1/p2 print (the screen equals the JSON)
  const t = (id) => resolveCaption(beats.find((b) => b.id === id).caption, S, fmt, { html: false });
  const m = S.p1meta;
  assert.ok(t('peak-relief').includes(`${m.relief.none.v.toFixed(1)}% SIM`));
  assert.ok(t('rebound-naive').includes(`${m.summary.naive.maxLoading.v.toFixed(1)}% SIM`));
  assert.ok(t('p2-capacity').includes(`${S.p2index.usefulCapacity.naive.v} SIM`));
  // the flip headline follows the measured flip (7/10 on this data: partial), never asserted
  assert.equal(/How you charge decides/.test(t('p2-flip')), flipVerdict(S.p2index.flip).supports);
});

test('ranking table: refereed rows show the OpenDSS peak, screening rows the surrogate (judge R0: no screening mark on OpenDSS-able rows)', async () => {
  const { peakWithShown } = await import('../panels/p2.js');
  const e = stressedEntry(fx('p2/aware-core-d26-g0.json'));
  assert.equal(peakWithShown(e).v, 96.4);
  e.opendss = { before: { peakPct: { v: 121.9, label: 'SIM' } }, after: { peakPct: { v: 97.1, label: 'SIM', cite: 'OpenDSS' } } };
  e.screening = false;
  assert.equal(peakWithShown(e).v, 97.1);
  const real = realJSON('p2/aware-core-d26-g0.json');
  if (real) for (const x of real.ranking.slice(0, 5)) if (x.opendss && x.opendss.after) assert.equal(peakWithShown(x), x.opendss.after.peakPct);
});

test('outside the top 50: the naive standing of feeder-aware #1 comes from flip.movers + index.bridge, labelled', async () => {
  const { standingOutside } = await import('../panels/p2.js');
  const idx = realJSON('p2/index.json');
  if (!idx) return;
  const a1 = realJSON('p2/aware-core-d26-g0.json').ranking[0];
  const so = standingOutside(idx, a1.home, a1.tf, 'naive');
  const mv = (idx.flip.movers || []).find((m) => m.home === a1.home);
  if (mv) assert.deepEqual(so.rank, mv.rankNaive);
  const br = (idx.bridge || []).find((b) => b.tf === a1.tf);
  if (br && br.naive.home === a1.home) {
    assert.equal(so.bridge, br.naive);
    assert.ok(fmt.isLabelled(so.bridge.peakWithPct));
  }
  assert.deepEqual(standingOutside(idx, -5, -5, 'naive'), { rank: null, bridge: null });
});

// ------------------------------------------------------------------------------------ fix round 1 (judge R1)
// F3: surrogate-only numbers carry the "screening" chip (build prompt 5.6.11, 3.4); refereed ones show OpenDSS's.
// These mount the real P2 panel in node (a stub element; the data module reads the committed files) and fail when
// any number whose cite says "not OpenDSS-checked" renders without the chip.
import * as dataMod from '../lib/data.js';
import { unscreenedChips, isScreening, SCREEN_CHIP, numHTML, engineUnit, reliefPeak, shareDigits } from '../panels/more.js';

const DATA_DIR = path.join(UI, 'data') + path.sep;
dataMod._configure({
  base: DATA_DIR,
  fetchFn: async (p) => (fs.existsSync(p)
    ? { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) }
    : { ok: false, status: 404, json: async () => null }),
});

async function mountP2(query) {
  const { mount } = await import('../panels/p2.js');
  const link = parseLink(query);
  const el = { classList: { add() {} }, innerHTML: '', querySelector: () => null };
  const models = [];
  const ctx = {
    topology, footprints: null, link, data: dataMod, fmt, sceneModel, theme: 'light',
    scene: { update: (m) => models.push(m), camera() {}, onPick() {} },
    href: (patch) => dataMod.linkQuery({ ...link, beat: null, ...patch }),
    go() {}, reportError: (e) => { throw e; },
  };
  await mount(el, ctx);
  return { html: el.innerHTML, model: models[models.length - 1] };
}

test('F3: the unscreened-chip check catches a surrogate number rendered without the chip (the admit half)', () => {
  const x = { v: 145.6, label: 'SIM', cite: 'surrogate screen (sim.surrogate, calibrated vs OpenDSS); not OpenDSS-checked' };
  assert.equal(unscreenedChips(fmt.fmtHTML(x, { unit: '%', digits: 1 })).length, 1, 'bare fmtHTML must be caught');
  assert.deepEqual(unscreenedChips(numHTML(fmt, x, { unit: '%', digits: 1 })), []);
  assert.ok(numHTML(fmt, x).includes(SCREEN_CHIP));
  assert.equal(isScreening({ v: 96.9, label: 'SIM', cite: 'OpenDSS (sim.referee): before = baseline month' }), false);
  assert.ok(!numHTML(fmt, { v: 96.9, label: 'SIM', cite: 'OpenDSS (sim.referee)' }).includes('screening'));
});

test('F3: every P2 link renders no "not OpenDSS-checked" number without the screening chip', async () => {
  const ids = index.combos;
  const real = realJSON('p2/index.json');
  const links = [
    ...ids.map((id) => `?view=p2&combo=${id}`),
    '?view=p2&combo=naive-core-d26-g0&home=p1ulv24700',
    '?view=p2&combo=aware-core-d26-g0&n=5',
    ...beats.filter((b) => b.link.startsWith('view=p2')).map((b) => `?${b.link}&beat=${b.id}`),
  ];
  let n = 0;
  for (const q of links) {
    const { html } = await mountP2(q);
    const bad = unscreenedChips(html);
    assert.deepEqual(bad, [], `${q}: screening numbers without the chip:\n${bad.join('\n')}`);
    n += (html.match(/p2-badge screen sm/g) || []).length;
  }
  if (real) assert.ok(n > 0, 'the real data has screening numbers, so some chips must render');
});

test('F3, REAL data: the naive "where NOT to put it" card, the flip #1 line and the handoff card', { skip: !realJSON('p2/index.json') && 'no real P2 data' }, async () => {
  const idx = realJSON('p2/index.json');
  const br = idx.bridge.find((b) => b.tf === 240) || idx.bridge[0];
  const P = { unit: '%', digits: 1 };
  // the naive bridge card (home not in the naive top 50): each surrogate number followed by the chip
  const home = topology.homes[br.naive.home].id;
  const { html: card } = await mountP2(`?view=p2&combo=naive-core-d26-g0&home=${home}`);
  for (const k of ['peakWithoutPct', 'peakWithPct', 'h100Without', 'h100With']) {
    if (!isScreening(br.naive[k])) continue;
    const o = k.startsWith('h100') ? { unit: ' h', digits: 2 } : P;
    assert.ok(card.includes(fmt.fmtHTML(br.naive[k], o) + SCREEN_CHIP), `naive bridge ${k} without the chip`);
  }
  // the default combo: the handoff shows OpenDSS's month peaks where the referee ran the candidate
  const aw = realJSON('p2/aware-core-d26-g0.json');
  const e = aw.ranking.find((x) => x.home === br.aware.home);
  const { html: def } = await mountP2('?view=p2&combo=aware-core-d26-g0');
  const hand = def.slice(def.indexOf('class="p2-handoff"'), def.indexOf('</section>', def.indexOf('class="p2-handoff"')));
  assert.ok(hand.length > 0, 'handoff card rendered');
  if (e && e.opendss && e.opendss.after && e.screening !== true) {
    assert.ok(hand.includes('OpenDSS month run'), hand);
    assert.ok(hand.includes(fmt.fmtHTML(e.opendss.before.peakPct, P)), `handoff lacks OpenDSS before ${e.opendss.before.peakPct.v}`);
    assert.ok(hand.includes(fmt.fmtHTML(e.opendss.after.peakPct, P)), `handoff lacks OpenDSS after ${e.opendss.after.peakPct.v}`);
    // the candidate card's metrics: OpenDSS's peak first, the surrogate beside it as screening
    const met = def.slice(def.indexOf('class="p2-metrics"'));
    assert.ok(met.includes(`${fmt.fmtHTML(e.opendss.after.peakPct, P)} OpenDSS · ${fmt.fmtHTML(e.peakWithPct, P)}${isScreening(e.peakWithPct) ? SCREEN_CHIP : ''}`), 'metrics peak row');
  }
  // the flip card's line for feeder-aware #1 under naive dispatch
  const flip = def.slice(def.indexOf('class="p2-flip"'));
  if (isScreening(br.naive.peakWithPct)) assert.ok(flip.includes(fmt.fmtHTML(br.naive.peakWithPct, P) + SCREEN_CHIP), 'flip #1 line');
});

test('F3: beat captions (P1 and P2 bars, the More list) chip every screening number', { skip: !(realJSON('p1/meta.json') && realJSON('p2/index.json')) && 'real data not built' }, () => {
  const S = {
    topology, p1meta: realJSON('p1/meta.json'), p2index: realJSON('p2/index.json'), engine: realJSON('engine.json'),
    'p1:naive': realJSON('p1/naive.json'), 'p1:aware': realJSON('p1/aware.json'), 'p1:aware_faults': realJSON('p1/aware_faults.json'),
    'p2:aware-core-d26-g0': realJSON('p2/aware-core-d26-g0.json'), 'p2:naive-core-d26-g0': realJSON('p2/naive-core-d26-g0.json'),
  };
  for (const b of beats) assert.deepEqual(unscreenedChips(resolveCaption(b.caption, S, fmt, { html: true })), [], b.id);
});

// F8: the handoff is part of the transformer's own label, never a second label at the same spot.
test('F8: the P1 handoff merges into the T-240 label (no overlapping second label)', () => {
  const doc = fx('p2/aware-core-d26-g0.json');
  const ctx = { topology, footprints: null, sceneModel, theme: 'light' };
  const tf = (topology.bridge && topology.bridge[0] && topology.bridge[0].tf) || 240;
  const m = p2SceneModel(ctx, { doc, n: 1, p1meta: { unrelieved: [{ tf }] } });
  const t = topology.transformers[tf];
  const at = m.labels.filter((l) => !l.pin && l.position[0] === t.lonlat[0] && l.position[1] === t.lonlat[1]);
  assert.equal(at.length, 1, 'one label at the transformer');
  assert.ok(at[0].handoff && /P1: unrelieved/.test(at[0].text) && /P1: unrelieved/.test(at[0].short), JSON.stringify(at[0]));
  assert.ok(/T-240/.test(at[0].text));
});

// F4: the problem beat carries the scale ladder, templated from p1/meta.json scaleLadder.
test('F4: the problem caption templates every scale-ladder rung from the data, with labels', () => {
  const b = beats.find((x) => x.id === 'problem');
  assert.ok(b.caption.includes('{{scaleLadder}}') && b.caption.includes('{{scaleLadderKW}}'));
  const meta = realJSON('p1/meta.json');
  if (!meta || !meta.scaleLadder) return;
  const txt = resolveCaption(b.caption, { topology, p1meta: meta }, fmt, { html: false });
  assert.ok(!/not built yet/.test(txt), txt);
  for (const r of meta.scaleLadder.rungs) {
    const s = fmt.fmt(r.sharePct, { unit: '%', digits: shareDigits(r.sharePct.v) });
    assert.ok(txt.includes(s), `rung ${r.scale}: ${s} missing from ${txt}`);
    assert.ok(!/^0\.0+% /.test(s), `rung ${r.scale} prints as zero: ${s}`);
    assert.ok(txt.includes(`${fmt.fmtValue(r.base, { digits: Number.isInteger(r.base.v) ? 0 : 1 })} ${r.base.unit} ${r.base.label}`), `rung ${r.scale} base`);
  }
  assert.equal(shareDigits(4.9e-5), 6);
  assert.equal(shareDigits(0.501), 2);
  assert.equal(shareDigits(160), 0);
});

// F7: "discharge up to X kW (HH:MM)", both read from the feeder-aware branch the gauge draws.
test('F7: the relief caption gives the largest relief discharge and its minute, as the aware branch measured', () => {
  const b = beats.find((x) => x.id === 'peak-relief');
  assert.ok(b.caption.includes('up to {{reliefKWPeak}}'));
  assert.ok(!/discharge \{\{reliefKW\}\}/.test(b.caption), 'the peak kW without its time must not be read as the kW at the relief step');
  const meta = realJSON('p1/meta.json'), aw = realJSON('p1/aware.json');
  if (!meta || !aw) return;
  const p = reliefPeak(meta, aw, topology);
  assert.ok(p, 'A discharges at the relief step');
  const kw = aw.focus[p.key].batKW;
  for (let k = p.from; k <= p.to; k++) assert.ok(kw[k] >= kw[p.step]);
  if (meta.relief.reliefKW) assert.equal(p.kw.toFixed(1), meta.relief.reliefKW.v.toFixed(1), 'the aware series and meta.relief.reliefKW agree');
  const txt = resolveCaption(b.caption, { topology, p1meta: meta, 'p1:aware': aw }, fmt, { html: false });
  const [h, m] = meta.start.split(':').map(Number);
  const t = h * 60 + m + p.step * meta.stepSeconds / 60;
  const hhmm = `${String(Math.floor(t / 60) % 24).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
  assert.ok(txt.includes(`up to ${p.kw.toFixed(1)} kW SIM (${hhmm} SIM)`), txt);
});

// F9: the performance card prints each number's unit.
test('F9: engine.json rows carry their unit ("µs per call" for allocate)', () => {
  assert.deepEqual(engineUnit('allocate · 96', { v: 66.6, label: 'SIM', cite: 'microseconds per stateless allocate() call, 96 batteries' }), { name: 'allocate(), 96 batteries', unit: ' µs per call' });
  assert.equal(engineUnit('allocate · 100000', { v: 65011.7, label: 'SIM', cite: 'microseconds per stateless allocate() call' }).name, 'allocate(), 100,000 batteries');
  assert.equal(engineUnit('opendss · msPerSolve', { v: 2.1, label: 'SIM', cite: 'median ms per OpenDSS solve' }).unit, ' ms');
  assert.equal(engineUnit('p1 · buildSeconds', { v: 12.7, label: 'SIM', cite: 'last full sim.p1_build' }).unit, ' s');
  assert.equal(engineUnit('p1 · solves', { v: 2884, label: 'SIM', cite: 'OpenDSS solves in that build' }).unit, '');
  const eng = realJSON('engine.json');
  if (eng && eng.allocate) for (const [k, v] of Object.entries(eng.allocate)) if (/^\d+$/.test(k)) assert.equal(engineUnit(`allocate · ${k}`, v).unit, ' µs per call', k);
});
