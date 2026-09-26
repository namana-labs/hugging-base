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
const ID_TOKENS = [/Home \d{4}/g, /T-\d+/g, /(res|com)_kw(ar)?_\d+_pu/g, /\b\d{4}-\d{2}(-\d{2})?\b/g];
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
  assert.match(txt, /^In 2026-08 transformer T-240 spent 0\.50 h SIM above nameplate without a new battery \(peak 119\.5% SIM\)/);
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
  assert.equal(m.labels.filter((l) => l.kind === 'candidate').length, Math.min(10, doc.ranking.length));
  assert.equal(m.labels.find((l) => l.kind === 'candidate').text, '#1');
  assert.equal(m.batteries.length, base.batteries.length + 3);
  assert.ok(m.batteries.slice(-3).every((b) => b.greedy));
  assert.equal(m.labels.filter((l) => l.kind === 'handoff').length, 1);
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
