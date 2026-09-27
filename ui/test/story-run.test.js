// ui/test/story-run.test.js (UI-A): the pure half of Running and Run (ui/story/run.js) and the shell's labelled numbers
// (ui/story/shell.js). Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { SPEEDS, DEFAULT_SPEED, MERGE_GAP, focusLabels, runFiles, attackPath, ranges, kindWord, KIND, buildSeries, fallbackFailures,
  fallbackMoments, covertFailures, covertMoments, detectorModel, momentAt, runCostHTML, tierNames } from '../story/run.js';
import { numHTML, tagHTML, leverSummary, STEPS } from '../story/shell.js';
import { LabelError } from '../lib/format.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPO = path.resolve(UI, '..');
const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

test('run: the six speeds of ruling 5, default 0.25x', () => {
  assert.deepEqual(SPEEDS, [0.1, 0.25, 0.5, 1, 2, 4]);
  assert.equal(DEFAULT_SPEED, 0.25);
  assert.equal(MERGE_GAP, 5);
});

test('run: ranges merge runs of steps when the gap is 5 or less', () => {
  const on = new Set([3, 4, 5, 9, 10, 20]);
  assert.deepEqual(ranges(30, (k) => on.has(k)), [[3, 10], [20, 20]]);
  assert.deepEqual(ranges(30, (k) => on.has(k), 2), [[3, 5], [9, 10], [20, 20]]);
  assert.deepEqual(ranges(10, () => false), []);
  assert.deepEqual(ranges(4, () => true), [[0, 3]]);
});

test('run: the files a scenario reads; covert adds its detector file (catalogue `attack`)', () => {
  const base = { id: '2026-08-23/aware', levers: { failure: 'none' }, meta: 'p1/meta.json', branch: 'p1/aware.json', extras: 'p1/extras/2026-08-23_aware.json.gz' };
  assert.deepEqual(runFiles(base).map((f) => f.path), ['topology.json', 'footprints.json', 'p1/meta.json', 'p1/aware.json', 'p1/extras/2026-08-23_aware.json.gz']);
  assert.equal(attackPath(base), null);
  const cov = { ...base, levers: { failure: 'covert' }, attack: 'p3/covert.json' };
  assert.equal(attackPath(cov), 'p3/covert.json');
  assert.equal(runFiles(cov).at(-1).path, 'p3/covert.json');
  assert.equal(attackPath({ ...cov, attack: undefined, covert: '../../mpalacios/out/p3/covert.json' }), '../../mpalacios/out/p3/covert.json');
  assert.equal(runFiles({ ...base, extras: null }).length, 4);
});

test('run: every failure kind the engine writes has display words', () => {
  for (const k of ['comms_lost', 'hot', 'stall', 'stale', 'normal', 'emergency', 'protection', 'worker_kill', 'covert']) assert.ok(KIND[k], k);
  assert.equal(kindWord('protection'), 'Protection open');
  assert.equal(kindWord('new_kind'), 'new kind');
});

test('run: tier names read the run\'s own thresholds', () => {
  const t = tierNames({ amber: 100, normal: 110, normalMinutes: 30, emergency: 150 });
  assert.equal(t.length, 6);
  assert.match(t[3], /30\+ min/);
  assert.match(t[4], /150%/);
});

test('run: the engine cost line is the catalogue\'s labelled numbers; no bare number passes', () => {
  const sc = { engine: { buildSeconds: { v: 34.8, label: 'DERIVED', cite: 'sim.scenarios' }, solves: { v: 721, label: 'SIM' } } };
  const html = runCostHTML(sc, numHTML);
  assert.match(html, /721<\/span><span class="chip chip-SIM"/);
  assert.match(html, /34\.8 s<\/span><span class="chip chip-DERIVED" title="sim.scenarios"/);
  assert.match(html, /nothing is solved in the browser/);
  assert.match(runCostHTML({}, numHTML), /no measured engine cost/);
  const cov = runCostHTML({ ...sc, producer: 'mpalacios.detect', attackEngine: { buildSeconds: { v: 110, label: 'DERIVED' } } }, numHTML);
  assert.match(cov, /detector replay \(mpalacios\.detect\) took <span class="num">110 s/);
  assert.match(cov, /^The engine already ran this evening: /, 'the feeder run is not the detector run');
  assert.match(runCostHTML({ ...sc, producer: 'mpalacios.runtime' }, numHTML), /^The engine already ran this evening \(mpalacios\.runtime\): /);
  assert.throws(() => runCostHTML({ engine: { solves: 721 } }, numHTML), LabelError);
});

test('shell: numHTML tags every value; SCREENING is its own dashed tag; unknown labels throw', () => {
  assert.equal(numHTML({ v: 197.04, label: 'SIM' }, { unit: '%' }), '<span class="num">197.0%</span><span class="chip chip-SIM">SIM</span>');
  const s = numHTML({ v: 1007, label: 'SIM', cite: 'x' }, { screening: true });
  assert.match(s, /chip-SIM" title="x">SIM/);
  assert.match(s, /chip-SCREENING" title="Screening estimate, not checked by OpenDSS\. x">SCREENING/);
  assert.match(numHTML({ v: 3, label: 'UNVERIFIED' }), /chip-UNVERIFIED/);
  assert.throws(() => numHTML(3), LabelError);
  assert.throws(() => numHTML({ v: 3, label: 'GUESS' }), LabelError);
  assert.throws(() => tagHTML('GUESS'), LabelError);
  assert.deepEqual(STEPS.map((x) => x[1]), ['1 Configure', '2 Run', '3 Results', '4 Learnings']);
});

test('shell: the run pill summary uses the catalogue labels, cut at ": " or " ("', () => {
  const cat = { levers: {
    policy: { options: [{ id: 'aware', label: 'Feeder-aware' }, { id: 'none', label: 'No batteries' }] },
    failure: { options: [{ id: 'worker_kill', label: 'Controller crash: a worker is killed and its lease taken over' }] },
    fleet: { options: [{ id: 96, label: '96 batteries' }] }, cls: { options: [{ id: 'core', label: 'Core (20 kW, 37 kWh)' }] },
    reserve: { options: [{ id: 20, label: '20% reserve' }] }, soc0: { options: [{ id: 90, label: '90% at 16:00' }] },
    growth: { default: 0, options: [{ id: 0, label: "Today's load" }, { id: 20, label: '+20% home load' }] } } };
  const L = { policy: 'aware', failure: 'worker_kill', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 };
  assert.equal(leverSummary(cat, L), 'Feeder-aware · Controller crash · 96 batteries, Core · 20% reserve · 90% at 16:00');
  assert.equal(leverSummary(cat, { ...L, policy: 'none', failure: 'none', growth: 20 }), 'No batteries · +20% home load');
});

// ---- the committed data ----
const meta = readJSON(path.join(UI, 'data', 'p1', 'meta.json'));
const topology = readJSON(path.join(UI, 'data', 'topology.json'));

test('run: series from the committed aware_faults branch: steps, transformers and fleet read from the data', () => {
  const doc = readJSON(path.join(UI, 'data', 'p1', 'aware_faults.json'));
  const S = buildSeries(doc, meta, topology);
  assert.equal(S.n, meta.steps);
  assert.equal(S.tfN, topology.transformers.length);
  assert.equal(S.fleetN, topology.fleet.length);
  assert.equal(S.focus.map((f) => f.name).join(','), 'A,B,C,D,T-240');
  for (let k = 0; k < S.n; k += 97) {
    assert.equal(S.worst[k], Math.max(...doc.loading[k]) / 10);
    assert.ok(S.soc[k] > 0 && S.soc[k] <= 100);
  }
  // extras' worst series wins when it has the run's length
  const x = { worstPct: doc.loading.map(() => 1234), worstTf: doc.loading.map(() => 7) };
  const SX = buildSeries(doc, meta, topology, x);
  assert.equal(SX.worst[5], 123.4);
  assert.equal(SX.wtf[5], 7);
});

test('run: the fallback story and failures (no extras) use the files\' own text; another branch\'s faults stay out', () => {
  const doc = readJSON(path.join(UI, 'data', 'p1', 'aware_faults.json'));
  const S = buildSeries(doc, meta, topology);
  const f = fallbackFailures({ meta, doc, series: S, topology, branch: 'aware_faults' });
  const scripted = (meta.events.aware_faults || []).map((e) => e.kind);
  for (const k of scripted) assert.ok(f.some((x) => x.kind === k), `scripted ${k}`);
  for (const x of f) { assert.ok(x.k0 <= x.k1, JSON.stringify(x)); assert.ok(kindWord(x.kind)); }
  const m = fallbackMoments({ meta, doc, branch: 'aware_faults' });
  for (let i = 1; i < m.length; i++) assert.ok(m[i - 1].k <= m[i].k);
  const aware = readJSON(path.join(UI, 'data', 'p1', 'aware.json'));
  const ma = fallbackMoments({ meta, doc: aware, branch: 'aware' });
  const faultTexts = new Set((meta.events.aware_faults || []).map((e) => e.text));
  assert.ok(!ma.some((x) => faultTexts.has(x.text)), 'the aware branch shows no aware_faults event');
  assert.equal(momentAt(m, -1), null);
  assert.equal(momentAt(m, S.n), m.at(-1));
});

test('run: worker_kill fallback reads the kill from its runtime block', () => {
  const doc = readJSON(path.join(REPO, 'mpalacios', 'out', 'p1', 'worker_kill.json'));
  const S = buildSeries(doc, meta, topology);
  const f = fallbackFailures({ meta, doc, series: S, topology, branch: 'worker_kill' });
  const kill = f.find((x) => x.kind === 'worker_kill');
  assert.equal(kill.k0, doc.runtime.kill.step);
  assert.equal(kill.k1, doc.runtime.takeover[0].step);
  assert.equal(kill.text, doc.runtime.kill.text);
  const m = fallbackMoments({ meta, doc, branch: 'worker_kill' });
  assert.ok(m.some((x) => x.text === doc.runtime.takeover[0].text));
});

test('run: the covert detector card counts flagged and quarantined units from p3/covert.json', () => {
  const cov = readJSON(path.join(REPO, 'mpalacios', 'out', 'p3', 'covert.json'));
  const n = cov.window.steps;
  const d = detectorModel(cov, n);
  assert.equal(d.units.length, cov.attack.shard.length);
  assert.equal(d.flaggedAt(cov.attack.step - 1), 0);
  assert.equal(d.flaggedAt(n - 1), cov.units.filter((u) => u.flaggedStep !== null).length);
  assert.equal(d.flaggedAt(n - 1), cov.summary.detected.v);
  assert.equal(d.quarantinedAt(n - 1), cov.quarantine.log.length);
  const first = Math.min(...cov.units.map((u) => u.flaggedStep).filter((x) => x !== null));
  assert.equal((first - cov.attack.step + 1) * 60, cov.summary.detectionSeconds.v, 'the minute it is flagged counts');
  assert.ok(d.w0 <= cov.attack.step && d.w1 >= Math.max(...cov.quarantine.log.map((q) => q[0])));
  assert.equal(d.x(d.w0 - 1), null);
  assert.equal(d.x(d.w0), '0.0');
  assert.match(d.flagPath, /^M0,42\.0.*H300$/);
  const cf = covertFailures(cov, n);
  assert.equal(cf.length, 1);
  assert.equal(cf[0].k0, cov.attack.step);
  assert.equal(cf[0].text, cov.attack.text);
  assert.equal(covertMoments(cov)[0].text, cov.attack.text);
  assert.deepEqual(covertFailures(null, n), []);
});

test('shell: vsDefault rows follow the catalogue headline order, labelled from the runs\' own summaries', async () => {
  const { vsDefaultRows, vsDefaultText, vsDefaultHTML } = await import('../story/shell.js');
  const sum = (v, label = 'SIM') => ({ v, label, cite: 'c' });
  const cat = {
    headline: ['batteryCausedNormal', 'energyValueUSD', 'maxLoading'],
    scenarios: [
      { id: 'd/naive', title: 'Naive', summary: { batteryCausedNormal: sum(11), energyValueUSD: sum(893.83, 'DERIVED'), maxLoading: sum(201.2) } },
      { id: 'd/naive/fleet=192', title: 'Naive, 192', summary: { batteryCausedNormal: sum(15), energyValueUSD: sum(1789.11, 'DERIVED'), maxLoading: sum(201.3), bare: 3 },
        vsDefault: { energyValueUSD: { v: 1789.11, ref: 893.83, refId: 'd/naive' }, batteryCausedNormal: { v: 15, ref: 11, refId: 'd/naive' }, bare: { v: 3, ref: 1, refId: 'd/naive' } } },
    ],
  };
  const rows = vsDefaultRows(cat, cat.scenarios[1]);
  assert.deepEqual(rows.map((r) => r.key), ['batteryCausedNormal', 'energyValueUSD'], 'headline order; a value without a label is dropped');
  assert.deepEqual(rows[1].now, { v: 1789.11, label: 'DERIVED', cite: 'c' });
  assert.equal(rows[1].refTitle, 'Naive');
  assert.match(vsDefaultText(rows), /fleet gross energy value, not Base's profit \$1,789\.11 \(default run \$893\.83\)/);
  assert.match(vsDefaultHTML(rows, { max: 1 }), /\+1 more/);
  assert.deepEqual(vsDefaultRows(cat, cat.scenarios[0]), []);
  assert.deepEqual(vsDefaultRows(cat, { id: 'x', vsDefault: {} }), []);
});

test('run: the named places come from topology (focus keys, bridge tf), or are left out', () => {
  assert.deepEqual(focusLabels(topology), { streetsLabel: `Street ${topology.focus[0].key}–${topology.focus.at(-1).key}`, bridgeLabel: `T-${topology.bridge[0].tf}` });
  assert.deepEqual(focusLabels({ focus: [{ key: 'Q' }] }), { streetsLabel: 'Street Q', bridgeLabel: null });
  assert.deepEqual(focusLabels({}), { streetsLabel: null, bridgeLabel: null });
});

test("shell: a time-named headline key takes its run's end time, or 'the end of the run'", async () => {
  const { vsDefaultRows } = await import('../story/shell.js');
  const sum = (v) => ({ v, label: 'SIM', cite: 'c' });
  const cat = { headline: ['chargedPctBy0400'], scenarios: [{ id: 'd', summary: { chargedPctBy0400: sum(100) } },
    { id: 'x', summary: { chargedPctBy0400: sum(99.2) }, vsDefault: { chargedPctBy0400: { v: 99.2, ref: 100, refId: 'd' } } }] };
  assert.equal(vsDefaultRows(cat, cat.scenarios[1], { end: '04:00' })[0].words, 'fleet charged by 04:00');
  assert.equal(vsDefaultRows(cat, cat.scenarios[1])[0].words, 'fleet charged by the end of the run');
});
