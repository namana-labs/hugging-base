// ui/test/p1.test.js (L4): the P1 panel's pure pieces on the committed P1 data (real when L2 has landed it, else the
// fixtures), plus its honesty rules. The DOM half is exercised by scripts/smoke_ui.sh p1.
// Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import * as fmt from '../lib/format.js';
import { roomKW } from '../lib/scene-model.js';
import {
  worstAt, countsAt, stateCounts, tickerAt, tfEvening, gaugeModel, initialStep, stripMarks, labelledTreeHTML, gridCheckHTML,
  faultText, seriesLabel, optsFor, humanKey, NAIVE_FRAMING, BRANCH_NAMES, SPEEDS, MS_PER_STEP, moneyHTML, isLabelledRecord,
  spikeDriverAt, driverLineHTML, DRIVER_WINDOW_MIN,
} from '../panels/p1.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJSON = (rel) => JSON.parse(fs.readFileSync(path.join(UI, 'data', rel), 'utf8'));
const topology = readJSON('topology.json');
const p1Dir = fs.existsSync(path.join(UI, 'data', 'p1', 'meta.json')) ? 'p1' : 'fixtures/p1';
const meta = readJSON(`${p1Dir}/meta.json`);
const docs = Object.fromEntries(meta.branches.map((b) => [b, readJSON(`${p1Dir}/${b}.json`)]));
const homeLabel = (h) => (typeof h === 'number' ? topology.homes[h].label : String(h));

test('transport: 1 simulated minute per 100 ms at 1x, 0.5x-8x', () => {
  assert.equal(MS_PER_STEP, 100);
  assert.deepEqual(SPEEDS, [0.5, 1, 2, 4, 8]);
  assert.equal(meta.stepSeconds, 60);
});

test('naive carries its ASSUMPTION framing (build prompt 3.4); branch names cover the four branches', () => {
  assert.match(NAIVE_FRAMING, /one number per zone/);
  assert.match(NAIVE_FRAMING, /ASSUMPTION/);
  assert.match(NAIVE_FRAMING, /not public/);
  for (const b of ['none', 'naive', 'aware', 'aware_faults']) assert.ok(BRANCH_NAMES[b]);
  const src = fs.readFileSync(path.join(UI, 'panels', 'p1.js'), 'utf8');
  assert.match(src, /b === 'naive' \? fmt\.chip\('ASSUMPTION', NAIVE_FRAMING\)/);
  assert.ok(!/overheat/i.test(src), 'never say A "overheats" (build prompt 4.2)');
  assert.match(src, /No service transformer passed its limit/);   // the claim is scoped to service transformers (3.4)
});

test('worst transformer, tier counts and battery states at a step come from the JSON', () => {
  for (const [b, doc] of Object.entries(docs)) {
    const k = Math.floor(doc.loading.length / 2);
    const w = worstAt(doc, k);
    assert.equal(w.pct, Math.max(...doc.loading[k]) / 10, b);
    assert.equal(doc.loading[k][w.tf] / 10, w.pct);
    assert.equal(w.code, Number(doc.tier[k][w.tf]));
    const c = countsAt(doc, k);
    const byTier = [0, 0, 0, 0, 0];
    for (const ch of doc.tier[k]) if (+ch >= 1) byTier[+ch - 1] += 1;
    assert.deepEqual(c, byTier, `${b}: counts[k] matches the tier string`);
    const { counts, ...noCounts } = doc;
    void counts;
    assert.deepEqual(countsAt(noCounts, k), byTier);
    const sc = stateCounts(doc, k);
    assert.equal(Object.values(sc).reduce((a, x) => a + x, 0), 96);
  }
});

test('ticker: newest first, never ahead of the clock', () => {
  const doc = { ticker: [[1, 'a'], [5, 'b'], [5, 'c'], [9, 'd']] };
  assert.deepEqual(tickerAt(doc, 5, 6).map((x) => x[1]), ['c', 'b', 'a']);
  assert.deepEqual(tickerAt(doc, 100, 2).map((x) => x[1]), ['d', 'c']);
  assert.deepEqual(tickerAt(doc, 0, 6), []);
});

test('evening stats per transformer: max, minutes above 110% (codes 2-4) and 150% (code 4), protection step', () => {
  const doc = {
    loading: [[500], [1200], [1600], [1700], [0]],
    tier: ['0', '2', '4', '4', '5'],
  };
  const e = tfEvening(doc, 0, 60);
  assert.equal(e.maxPct, 170);
  assert.equal(e.maxStep, 3);
  assert.equal(e.min110, 3);
  assert.equal(e.min150, 2);
  assert.equal(e.openStep, 4);
  assert.equal(tfEvening(doc, 0, 900).min110, 45);
});

test('gauges: A-D and T-240 from `focus`, % of nameplate = kW / kVA, room from OpenDSS loading (DERIVED)', () => {
  const doc = docs.naive || docs[meta.branches[0]];
  const k = doc.loading.length - 1;
  for (const key of ['A', 'B', 'C', 'D', '240']) {
    const g = gaugeModel(meta, doc, topology, key, k, roomKW);
    assert.ok(g, key);
    const f = doc.focus[key];
    assert.equal(g.tf, f.tf);
    assert.equal(g.pct, doc.loading[k][f.tf] / 10);
    assert.ok(Math.abs(g.homePct - 100 * (f.homeKW[k] / 10) / g.kva) < 1e-9);
    assert.ok(Math.abs(g.batPct - 100 * (f.batKW[k] / 10) / g.kva) < 1e-9);
    assert.ok(Math.abs(g.room - roomKW(g.kva, g.pct, f.homeKW[k] / 10 + f.batKW[k] / 10)) < 1e-9);
    if (key !== '240') assert.equal(topology.transformers[g.tf].focus, key);
  }
  assert.equal(gaugeModel(meta, doc, topology, 240, 0, roomKW) === null, false);
  assert.equal(gaugeModel(meta, { ...doc, focus: {} }, topology, 'A', 0, roomKW), null);
  const gA = gaugeModel(meta, doc, topology, 'A', k, roomKW);
  assert.equal(gA.batteries, topology.fleet.filter((hi) => topology.homes[hi].tf === gA.tf).length);
});

test('opening step: the link time, else 30 min after the D-26 onset, else the middle', () => {
  assert.equal(initialStep(meta, { t: meta.start }, fmt), 0);
  const k = initialStep(meta, { t: null }, fmt);
  assert.equal(k, Math.min(meta.steps - 1, fmt.timeToStep(meta, meta.plan.onset) + 30));
  assert.equal(initialStep({ ...meta, plan: null }, {}, fmt), Math.floor(meta.steps / 2));
});

test('strip markers: meta.markers and the branch\'s fault events, in time order', () => {
  const marks = stripMarks(meta, 'aware_faults', fmt, homeLabel);
  for (let i = 1; i < marks.length; i++) assert.ok(marks[i].k >= marks[i - 1].k);
  const nFaults = ((meta.events || {}).aware_faults || []).length;
  assert.equal(marks.filter((m) => m.kind === 'fault').length, nFaults);
  assert.equal(stripMarks(meta, 'aware', fmt).filter((m) => m.kind === 'fault').length, ((meta.events || {}).aware || []).length);
  for (const m of meta.markers || []) assert.ok(marks.some((x) => x.text === m.text));
  assert.match(faultText({ kind: 'comms_lost', home: 211 }, homeLabel), /^comms lost: Home 0212$/);
  assert.equal(faultText({ kind: 'stall' }), 'our controller stalls');
});

test('labelled trees (money, ladder): chips on every value, units inherited, a bare headline number throws', () => {
  const html = labelledTreeHTML(fmt, meta.money);
  assert.ok(!/NaN|undefined/.test(html));
  if (meta.money.energyValueUSD) assert.match(html, /\$/);
  const n = (html.match(/class="chip chip-/g) || []).length;
  assert.ok(n >= 2, `${n} chips`);
  const t = labelledTreeHTML(fmt, { energyValueUSD: { naive: { v: -12.5, label: 'DERIVED' } }, note: 'unpriced', ids: { rank: 3 } });
  assert.match(t, /-\$12\.50/);
  assert.match(t, /chip-DERIVED/);
  assert.match(t, /unpriced/);
  assert.throws(() => labelledTreeHTML(fmt, { reliefKW: 6.1 }), fmt.LabelError);
  assert.deepEqual(optsFor('reliefKWh'), { unit: ' kWh', digits: 1 });
  assert.equal(humanKey('costOfAwareness'), 'Cost of awareness (naive minus aware)');
  assert.equal(seriesLabel({ series: { loading: { label: 'SIM' } } }, 'loading'), 'SIM');
  assert.equal(seriesLabel({}, 'price', 'REAL'), 'REAL');
});

test('grid checks: measured, never asserted: "stays in range" only when no home is below 0.95 pu; head as % of 370 A', () => {
  const base = { vMinHome: { v: 0.9538, label: 'SIM', volts: 114.5, home: 211, t: '22:31' },
    feederHead: { v: 84.2, label: 'SIM', amps: 311.5, t: '22:05', ratingA: { v: 370, label: 'DERIVED', cite: 'site/ems/flow-spec.md' } } };
  const ok = gridCheckHTML(fmt, { ...base, homesBelow095: { v: 0, label: 'SIM' } }, homeLabel);
  assert.match(ok, /Voltage stays in range at unity pf/);
  assert.match(ok, /0\.9538 pu/);
  assert.match(ok, /114\.5 V/);
  assert.match(ok, /Home 0212, 22:31/);
  assert.match(ok, /84\.2%/);
  assert.match(ok, /370 A/);
  const sag = gridCheckHTML(fmt, { ...base, vMinHome: { ...base.vMinHome, v: 0.9321 }, homesBelow095: { v: 4, label: 'SIM' } }, homeLabel);
  assert.ok(!/stays in range/.test(sag));
  assert.match(sag, /homes below 0\.95 pu/);
  for (const b of meta.branches) assert.ok(gridCheckHTML(fmt, meta.summary[b], homeLabel).length > 0, b);
});

test('money card: every line labelled, local relief never priced, capacity band only on fleet kW at the peak', () => {
  const html = moneyHTML(fmt, meta.money, 'aware');
  assert.ok(html.length > 0);
  assert.ok(!/NaN|undefined|\[object Object\]/.test(html));
  const money = {
    energyValueUSD: { naive: { v: 893.83, label: 'DERIVED' }, aware: { v: 916.56, label: 'DERIVED' } },
    costOfAwareness: { v: -22.73, label: 'DERIVED' },
    systemCapacityPerMonth: { aware: { fleetKW: { v: 1888.8, label: 'SIM' }, low: { v: 5893.19, label: 'DERIVED' }, high: { v: 16055.17, label: 'DERIVED' }, unit: '$/month' } },
    relief: { kwh: { v: 1.194, label: 'SIM' }, opportunityUpperUSD: { v: 0.64, label: 'DERIVED' }, priced: { v: false, label: 'ASSUMPTION' } },
    whoPays: [{ who: 'GVEC (50 MW)', for: 'ERCOT summer 4CP and arbitrage', label: 'REAL', cite: 'x' }],
    localRelief: { text: 'unpriced opportunity', label: 'ASSUMPTION', cite: 'y' },
    transformerReplacementUSD: { v: null, label: 'ASSUMPTION', cite: 'not sourced' },
    avoidedHarm: { naive: { normalEvents: { v: 11, label: 'SIM' }, emergencyTfs: { v: 3, label: 'SIM' }, protectionOperated: { v: 0, label: 'SIM' } } },
    extra: { v: 3, label: 'SIM' },
  };
  const h = moneyHTML(fmt, money, 'aware');
  assert.match(h, /\$916\.56/);
  assert.match(h, /-\$22\.73/);
  assert.match(h, /Negative: feeder-aware earned more/);
  assert.match(h, /\$5,893\.19<\/span>.*to.*\$16,055\.17/s);
  assert.match(h, /not a payment for local relief/);
  assert.match(h, /GVEC \(50 MW\): ERCOT summer 4CP and arbitrage<\/span> <span class="chip chip-REAL"/);
  assert.match(h, /unpriced opportunity/);
  assert.match(h, /not sourced <span class="chip chip-ASSUMPTION"/);
  assert.match(h, /<td>11<\/td><td>3<\/td><td>0<\/td>/);
  assert.match(h, /Extra/);   // unknown keys still render, labelled
  assert.ok(isLabelledRecord(fmt, { text: 'a', label: 'REAL' }));
  assert.ok(!isLabelledRecord(fmt, { v: 1, label: 'REAL' }));
  assert.throws(() => moneyHTML(fmt, { mystery: 5 }, 'aware'), fmt.LabelError);
});

test('hero driver: a spike shown as the worst transformer names its home and shared SMART-DS profile, only near the spike', () => {
  assert.equal(DRIVER_WINDOW_MIN, 15);
  const r = meta.relief;
  if (!r || !r.driver) return;   // fixtures without a relief: nothing to name
  const k = Number.isInteger(r.step) ? r.step : fmt.timeToStep(meta, r.t);
  const info = spikeDriverAt(meta, fmt, r.tf, k);
  assert.equal(info.kind, 'relief');
  assert.equal(info.driver.profile, r.driver.profile);
  // 15 min either side, never further: at the naive rebound the spike is not the cause
  assert.ok(spikeDriverAt(meta, fmt, r.tf, k + 15));
  assert.equal(spikeDriverAt(meta, fmt, r.tf, k + 16), null);
  assert.equal(spikeDriverAt(meta, fmt, r.tf, k - 16), null);
  const html = driverLineHTML(fmt, info, (h) => (typeof h === 'object' ? h.label : homeLabel(h)));
  assert.match(html, new RegExp(r.driver.profile));
  assert.match(html, /15-minute spike/);
  if (r.driver.sharedWith && r.driver.sharedWith.length) assert.match(html, /not independent evidence/);
  assert.match(html, /data-label="SIM"|SIM/);   // the kW at the peak carries its chip
  // an unrelieved transformer (T-240) names its own driver at its peak
  for (const u of meta.unrelieved || []) {
    if (!u.driver || !u.peak || !u.peak.t) continue;
    const ku = fmt.timeToStep(meta, u.peak.t);
    const iu = spikeDriverAt(meta, fmt, u.tf, ku);
    assert.equal(iu.kind, 'unrelieved');
    assert.match(driverLineHTML(fmt, iu, (h) => (typeof h === 'object' ? h.label : homeLabel(h))), /home load only, no battery/);
  }
  // a transformer with no driver entry gets nothing
  assert.equal(spikeDriverAt(meta, fmt, -1, k), null);
  assert.equal(driverLineHTML(fmt, null, homeLabel), '');
});
