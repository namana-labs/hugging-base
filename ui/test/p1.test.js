// ui/test/p1.test.js (L4): the P1 panel's pure pieces on the committed P1 data (real when L2 has landed it, else the
// fixtures), plus its honesty rules. Round 2: the story cues (UX_SPEC_R2 6.3, 6.7), the slower transport, plain words,
// tooltips and the money card without the system-capacity band (audit M5). The DOM half is exercised by smoke_ui.sh p1.
// Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import * as fmt from '../lib/format.js';
import * as sceneModel from '../lib/scene-model.js';
import { roomKW, exportRoomKW } from '../lib/scene-model.js';
import {
  worstAt, countsAt, stateCounts, tickerAt, tfEvening, gaugeModel, initialStep, stripMarks, labelledTreeHTML, gridCheckHTML,
  faultText, seriesLabel, optsFor, humanKey, NAIVE_FRAMING, BRANCH_NAMES, SPEEDS, DEFAULT_SPEED, MS_PER_STEP, moneyHTML, isLabelledRecord,
  spikeDriverAt, driverLineHTML, DRIVER_WINDOW_MIN, ladderHTML, pctOpts, ladderFrac, reliefPeakAt, storyCues, cueText, chainValue, activeCue,
  CHAINS, HOLD_STEPS, SELL_SHARE, ALL_SHARE, DONE_SOC, dayLabel, dayOffsetAt, whoPhrase, ratioWord, priceLevel, isBare, meanSoc, tfTipHTML,
  batteryTipHTML, homeTipHTML, nowWhy, tiersPresent, BEAT_SECTIONS, SPEED_TIPS, cashAt, supportsDates, ALL_BRANCHES,
} from '../panels/p1.js';
import zlib from 'node:zlib';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJSON = (rel) => JSON.parse(fs.readFileSync(path.join(UI, 'data', rel), 'utf8'));
const topology = readJSON('topology.json');
const p1Dir = fs.existsSync(path.join(UI, 'data', 'p1', 'meta.json')) ? 'p1' : 'fixtures/p1';
const REAL = p1Dir === 'p1';
const meta = readJSON(`${p1Dir}/meta.json`);
const docs = Object.fromEntries(meta.branches.map((b) => [b, readJSON(`${p1Dir}/${b}.json`)]));
const homeLabel = (h) => (typeof h === 'number' ? topology.homes[h].label : String(h));
const tfName = (tf) => { const f = topology.focus.find((x) => x.tf === tf); return f ? f.key : `T-${tf}`; };
const names = { tf: tfName, home: homeLabel, time: (s) => fmt.stepToTime(meta, s) };
const SRC = fs.readFileSync(path.join(UI, 'panels', 'p1.js'), 'utf8');
/** Digits outside <span class="num"> (labelled values), tags and ids (Home 0212, T-240, SMART-DS profile names) are bare. */
function bareDigits(html) {
  const t = html.replace(/<span class="num">[^<]*<\/span>/g, '').replace(/<[^>]+>/g, ' ')
    .replace(/Home \d{4}/g, '').replace(/T-\d+/g, '').replace(/\bP[12]\b/g, '').replace(/D-26/g, '').replace(/res_kw_\d+_pu/g, '').replace(/&#\d+;/g, '')
    .replace(/\b(110|150)%/g, '').replace(/04:00/g, '');   // the rating thresholds and the 04:00 checkpoint are rule names
  return t.match(/\d/g) || [];
}

test('transport: 0.1x-4x, default 0.25x, 1 simulated minute per 100 ms at 1x (RZ: slower playback)', () => {
  assert.deepEqual(SPEEDS, [0.1, 0.25, 0.5, 1, 2, 4]);
  assert.equal(DEFAULT_SPEED, 0.25);
  assert.equal(MS_PER_STEP, 100);
  assert.equal(meta.stepSeconds, 60);
  for (const s of SPEEDS) assert.ok(SPEED_TIPS[s], `tooltip for ${s}x`);
  assert.match(SPEED_TIPS[0.1], /1 simulated minute per second/);
  assert.deepEqual(BEAT_SECTIONS, { money: 'money', 'peak-relief': 'relief', faults: 'faults' });
});

test('naive carries its ASSUMPTION framing; no "overheat"; the claim is scoped to service transformers', () => {
  assert.match(NAIVE_FRAMING, /one number per zone/);
  assert.match(NAIVE_FRAMING, /ASSUMPTION/);
  assert.match(NAIVE_FRAMING, /not public/);
  for (const b of ['none', 'naive', 'aware', 'aware_faults']) assert.ok(BRANCH_NAMES[b]);
  assert.match(SRC, /b === 'naive' \? fmt\.chip\('ASSUMPTION', NAIVE_FRAMING\)/);
  assert.ok(!/overheat/i.test(SRC), 'never say A "overheats" (build prompt 4.2)');
  assert.match(SRC, /No service transformer passed its limit/);
  // round 1 clutter that left the panel (UX_SPEC_R2 6.2)
  assert.ok(!/step \$\{k\} of/.test(SRC), '"step 390 of 720" is gone');
  assert.ok(!/Northbank/.test(SRC), 'audit L14');
  assert.ok(!/System-capacity value/.test(SRC), 'audit M5: the system-capacity band left P1');
});

test('day label and clock: the weekday is computed, never typed; the date rolls over after midnight', () => {
  assert.equal(dayLabel('2026-08-23'), 'Sun 23 Aug 2026');
  assert.equal(dayLabel('2026-07-22'), 'Wed 22 Jul 2026');
  assert.equal(dayLabel('2026-08-14'), 'Fri 14 Aug 2026');
  assert.equal(dayLabel('2026-08-23', 1, false), 'Mon 24 Aug');
  assert.equal(dayOffsetAt(meta, fmt, 0), 0);
  assert.equal(dayOffsetAt(meta, fmt, fmt.timeToStep(meta, '23:59')), 0);
  assert.equal(dayOffsetAt(meta, fmt, fmt.timeToStep(meta, '00:00')), 1);
});

test('first open: a bare view=p1 opens 5 min before the onset; any link keeps its time', () => {
  assert.equal(isBare({ bare: true }, ''), true);
  assert.equal(isBare({ bare: false }, ''), false);
  assert.equal(isBare({}, '?view=p1'), true);
  assert.equal(isBare({}, '?view=p1&branch=aware'), false);
  assert.equal(isBare({}, '?view=p1&beat=money'), false);
  assert.equal(initialStep(meta, { t: meta.start }, fmt), 0);
  const onset = fmt.timeToStep(meta, meta.plan.onset);
  assert.equal(initialStep(meta, { t: null }, fmt, true), onset - 5);
  assert.equal(initialStep(meta, { t: null }, fmt), Math.min(meta.steps - 1, onset + 30));
  assert.equal(initialStep({ ...meta, plan: null }, {}, fmt), Math.floor(meta.steps / 2));
});

test('story cues on the committed data: naive drop <= allcharge <= overload <= worst < clear; aware checks, takes turns, never overloads', () => {
  const at = (b) => Object.fromEntries(storyCues(meta, docs[b], b, topology, fmt).map((c) => [c.id, c]));
  const n = at('naive');
  for (const id of ['drop', 'allcharge', 'overload', 'worst', 'clear', 'sell', 'backfeed', 'peak', 'charged']) assert.ok(n[id], `naive ${id}`);
  assert.ok(n.drop.k <= n.allcharge.k && n.allcharge.k <= n.overload.k && n.overload.k <= n.worst.k && n.worst.k < n.clear.k);
  assert.equal(n.drop.k, fmt.timeToStep(meta, meta.plan.onset));
  // the rules read the data: allcharge = the first step at or after the onset with >= ALL_SHARE of the fleet charging
  const fleet = topology.fleet.length;
  assert.ok(stateCounts(docs.naive, n.allcharge.k).C >= ALL_SHARE * fleet);
  assert.ok(stateCounts(docs.naive, n.sell.k).D >= SELL_SHARE * fleet);
  for (let k = 0; k < n.sell.k; k++) assert.ok(stateCounts(docs.naive, k).D < SELL_SHARE * fleet);
  assert.equal(n.worst.facts.pct.v, Math.max(...docs.naive.loading.slice(n.drop.k).map((r) => Math.max(...r))) / 10);
  if (REAL) assert.equal(n.worst.facts.pct.v, meta.summary.naive.maxLoading.v);
  assert.ok(meanSoc(docs.naive, n.charged.k) >= DONE_SOC);
  const a = at('aware');
  for (const id of ['drop', 'check', 'turns', 'charged', 'sell', 'sellcap', 'peak']) assert.ok(a[id], `aware ${id}`);
  for (const id of ['overload', 'allcharge', 'backfeed', 'worst', 'clear']) assert.ok(!a[id], `aware has no ${id}`);
  assert.ok(a.turns.k > a.check.k);
  assert.ok(a.sellcap.facts.pct.v <= 100, 'feeder-aware never back-feeds a transformer over its nameplate');
  const none = at('none');
  for (const id of ['sell', 'allcharge', 'check', 'turns', 'charged']) assert.ok(!none[id], `none has no ${id}`);
  assert.ok(none.nothing && none.peak);
  const af = at('aware_faults');
  for (const e of meta.events.aware_faults || []) assert.ok(af[e.kind], `aware_faults ${e.kind}`);
  // chains: three steps per branch, each a cue of that branch when it fires
  for (const b of meta.branches) {
    assert.equal(CHAINS[b].length, 3);
    const cs = storyCues(meta, docs[b], b, topology, fmt);
    for (const c of cs.filter((x) => x.chain !== null)) assert.equal(CHAINS[b][c.chain][0], c.id);
    for (let i = 1; i < cs.length; i++) assert.ok(cs[i].k >= cs[i - 1].k, 'sorted by step');
  }
  // a rule that does not fire emits nothing: a flat-price day with no batteries selling has no `sell`
  const flat = { ...docs.naive, state: docs.naive.state.map((s) => s.replace(/D/g, 'I')) };
  assert.ok(!storyCues(meta, flat, 'naive', topology, fmt).some((c) => c.id === 'sell'));
});

test('story line and chain: every number labelled (no bare digit outside a labelled value); the active cue holds HOLD_STEPS', () => {
  for (const b of meta.branches) {
    const cs = storyCues(meta, docs[b], b, topology, fmt);
    const done = cs.find((c) => c.id === 'charged');
    for (const c of cs) {
      const html = cueText(c, fmt, names, b);
      assert.ok(html.length > 10, `${b} ${c.id} has text`);
      assert.ok(!/NaN|undefined|\[object/.test(html), `${b} ${c.id}: ${html}`);
      assert.deepEqual(bareDigits(html), [], `${b} ${c.id}: bare digits in ${html}`);
      const v = chainValue(c, fmt, names, b, true, done);
      assert.deepEqual(bareDigits(v), [], `${b} ${c.id} chain value: ${v}`);
      assert.equal(chainValue(c, fmt, names, b, false, done), '', 'ghosted steps reveal no number');
    }
  }
  const n = storyCues(meta, docs.naive, 'naive', topology, fmt);
  const ac = n.find((c) => c.id === 'allcharge');
  assert.match(cueText(ac, fmt, names, 'naive'), /Every battery charges at once/);
  assert.match(cueText(ac, fmt, names, 'naive'), /chip-ASSUMPTION/);   // the naive rule is an assumption
  assert.match(cueText(n.find((c) => c.id === 'sell'), fmt, names, 'naive'), /no feeder check/);
  // at the onset the naive line is the all-charge one (its overload shares the line: cues within 3 steps)
  assert.equal(activeCue(n, ac.k).id, REAL ? 'allcharge' : activeCue(n, ac.k).id);
  assert.equal(activeCue(n, ac.k + HOLD_STEPS + 1000), null);
  const first = n[0];
  assert.equal(activeCue(n, first.k - 1), null, 'silence before the first cue');
  if (REAL) {
    // the measured ratio word: $55.42 at the onset is about a tenth of the $566.42 peak
    assert.equal(n.find((c) => c.id === 'drop').facts.ratio, 'about a tenth');
  }
  assert.equal(ratioWord(0.098), 'about a tenth');
  assert.equal(ratioWord(0.25), 'about a quarter');
  assert.equal(ratioWord(0.5), 'about half');
  assert.equal(ratioWord(0.8), '');
});

test('plain words: who phrase, price level (the charge rule threshold, no new constant)', () => {
  assert.equal(whoPhrase(96), 'within its rating');
  assert.equal(whoPhrase(104), 'just over its rating');
  assert.equal(whoPhrase(122), 'a quarter over its rating');
  assert.equal(whoPhrase(133), 'a third over its rating');
  assert.equal(whoPhrase(170), 'one and a half times its rating');
  assert.equal(whoPhrase(201.2), 'twice its rating');
  const th = meta.plan.threshold.v;
  assert.equal(priceLevel(meta, th - 0.01), 'cheap');
  assert.equal(priceLevel(meta, th), 'expensive');
  assert.equal(priceLevel({ plan: null }, 5), null);
});

test('worst transformer, tier counts and battery states at a step come from the JSON', () => {
  for (const [b, doc] of Object.entries(docs)) {
    const k = Math.floor(doc.loading.length / 2);
    const w = worstAt(doc, k);
    assert.equal(w.pct, Math.max(...doc.loading[k]) / 10, b);
    assert.equal(w.code, Number(doc.tier[k][w.tf]));
    const c = countsAt(doc, k);
    const byTier = [0, 0, 0, 0, 0];
    for (const ch of doc.tier[k]) if (+ch >= 1) byTier[+ch - 1] += 1;
    assert.deepEqual(c, byTier);
    const { counts, ...noCounts } = doc;
    void counts;
    assert.deepEqual(countsAt(noCounts, k), byTier);
    assert.equal(Object.values(stateCounts(doc, k)).reduce((a, x) => a + x, 0), 96);
    assert.ok(tiersPresent(doc).has(0));
  }
});

test('ticker: newest first, never ahead of the clock', () => {
  const doc = { ticker: [[1, 'a'], [5, 'b'], [5, 'c'], [9, 'd']] };
  assert.deepEqual(tickerAt(doc, 5, 6).map((x) => x[1]), ['c', 'b', 'a']);
  assert.deepEqual(tickerAt(doc, 100, 2).map((x) => x[1]), ['d', 'c']);
  assert.deepEqual(tickerAt(doc, 0, 6), []);
});

test('evening stats per transformer: max, minutes above 110% (codes 2-4) and 150% (code 4), protection step', () => {
  const doc = { loading: [[500], [1200], [1600], [1700], [0]], tier: ['0', '2', '4', '4', '5'] };
  const e = tfEvening(doc, 0, 60);
  assert.equal(e.maxPct, 170);
  assert.equal(e.maxStep, 3);
  assert.equal(e.min110, 3);
  assert.equal(e.min150, 2);
  assert.equal(e.openStep, 4);
});

test('street columns: A-D and T-240 from `focus`, % of nameplate = kW / kVA, room from OpenDSS loading (DERIVED)', () => {
  const doc = docs.naive;
  const k = doc.loading.length - 1;
  for (const key of ['A', 'B', 'C', 'D', '240']) {
    const g = gaugeModel(meta, doc, topology, key, k, roomKW);
    const f = doc.focus[key];
    assert.equal(g.tf, f.tf);
    assert.equal(g.pct, doc.loading[k][f.tf] / 10);
    assert.ok(Math.abs(g.room - roomKW(g.kva, g.pct, f.homeKW[k] / 10 + f.batKW[k] / 10)) < 1e-9);
  }
  assert.equal(gaugeModel(meta, { ...doc, focus: {} }, topology, 'A', 0, roomKW), null);
  const gA = gaugeModel(meta, doc, topology, 'A', k, roomKW);
  assert.equal(gA.batteries, topology.fleet.filter((hi) => topology.homes[hi].tf === gA.tf).length);
});

test('back-feed: an exporting transformer shows export room, from the data (judge R1 F6)', () => {
  const doc = docs.naive;
  let seen = 0;
  for (let k = 0; k < doc.loading.length; k++) {
    for (const key of ['A', 'B', 'C', 'D']) {
      const f = doc.focus[key];
      const P = f.homeKW[k] / 10 + f.batKW[k] / 10;
      const g = gaugeModel(meta, doc, topology, key, k, roomKW, exportRoomKW);
      assert.equal(g.exporting, P < 0);
      if (P < 0 && g.pct <= 100) {
        seen += 1;
        if (seen === 1) assert.match(tfTipHTML(fmt, meta, doc, topology, sceneModel, f.tf, k, names), /room to export/);
      }
    }
  }
  if (REAL) assert.ok(seen > 0, 'the naive branch back-feeds a focus transformer within nameplate');
  assert.match(SRC, /room to export/);
});

test('tooltips: transformer, battery and home copy, every number labelled, plain words from icons.js', () => {
  const doc = docs.naive;
  const k = fmt.timeToStep(meta, '22:30');
  const A = topology.focus.find((f) => f.key === 'A').tf;
  const t = tfTipHTML(fmt, meta, doc, topology, sceneModel, A, k, names);
  assert.match(t, /Transformer A/);
  assert.match(t, /kVA/);
  assert.match(t, /of its rating/);
  if (REAL) { assert.match(t, />201\.2%</); assert.match(t, /Emergency/); assert.match(t, /over by/); }
  assert.ok(!/NaN|undefined/.test(t));
  const other = topology.transformers.findIndex((x, i) => !x.focus && i !== 240);
  assert.match(tfTipHTML(fmt, meta, doc, topology, sceneModel, other, k, names), new RegExp(`Transformer T-${other}`));
  const bt = batteryTipHTML(fmt, meta, doc, topology, 0, k, names, 'naive');
  assert.match(bt, /Base battery at Home \d{4}/);
  assert.match(bt, /20% for backup/);
  assert.match(bt, /% full/);
  assert.match(batteryTipHTML(fmt, meta, docs.none, topology, 0, k, names, 'none'), /Switched off in this scenario/);
  const ht = homeTipHTML(fmt, topology, null, topology.fleet[0], names, 'lit', true);
  assert.match(ht, /Has a Base battery/);
  assert.match(ht, /12 m square/);
  assert.match(nowWhy(fmt, meta, doc, topology, A, k, homeLabel), /batteries are charging/);
  // T-240 (no battery) at its spike on feeder-aware: homes only, one home's short spike
  const u = meta.unrelieved && meta.unrelieved[0];
  if (u && u.peak) assert.match(nowWhy(fmt, meta, docs.aware, topology, u.tf, fmt.timeToStep(meta, u.peak.t), homeLabel), /homes only: no battery here; one home's short spike/);
  assert.match(SRC, /discharged up to/);
});

test('strip markers: icons only (no text), one per contiguous market discharge group, failures on their branch only', () => {
  const cues = storyCues(meta, docs.aware_faults, 'aware_faults', topology, fmt);
  const marks = stripMarks(meta, 'aware_faults', fmt, cues);
  for (let i = 1; i < marks.length; i++) assert.ok(marks[i].k >= marks[i - 1].k);
  for (const m of marks) { assert.ok(m.icon, 'every marker is an icon'); assert.ok(m.text.length > 0, 'hover text'); }
  const nFaults = ((meta.events || {}).aware_faults || []).length;
  assert.equal(marks.filter((m) => m.kind === 'fault').length, nFaults);
  const aware = stripMarks(meta, 'aware', fmt, storyCues(meta, docs.aware, 'aware', topology, fmt));
  assert.equal(aware.filter((m) => m.kind === 'fault').length, 0);
  assert.ok(!aware.some((m) => /runs hot|goes silent|stalls/.test(m.text)), 'a failure never shows on the branch without it');
  // the plan groups are derived from meta.plan.discharge: contiguous intervals collapse into one icon
  const plan = marks.filter((m) => m.kind === 'plan');
  const iv = meta.plan.discharge.map(([t, mm]) => [fmt.timeToStep(meta, t), mm]).sort((a, b) => a[0] - b[0]);
  let groups = 0, end = -Infinity;
  for (const [k0, mm] of iv) { if (k0 > end + 1) groups += 1; end = Math.max(end, k0 + mm); }
  assert.equal(plan.length, groups);
  assert.ok(!/market discharge/.test(marks.map((m) => m.text).join(' ')), 'individual discharge intervals are not markers');
  assert.equal(faultText({ kind: 'stall' }), 'our controller stalls');
  assert.match(faultText({ kind: 'comms_lost', home: 211 }, homeLabel), /^comms lost: Home 0212$/);
});

test('money card: every line labelled; the system-capacity band has left P1 (audit M5); local relief never priced', () => {
  const html = moneyHTML(fmt, meta.money, 'aware', BRANCH_NAMES, meta.constants, meta.summary);
  assert.ok(html.length > 0);
  assert.ok(!/NaN|undefined|\[object Object\]/.test(html));
  assert.ok(!/System-capacity|system-capacity|per kW-month/.test(html), 'no capacity band on P1');
  const money = {
    energyValueUSD: { naive: { v: 893.83, label: 'DERIVED' }, aware: { v: 916.56, label: 'DERIVED' } },
    costOfAwareness: { v: -22.73, label: 'DERIVED' },
    systemCapacityPerMonth: { aware: { fleetKW: { v: 1888.8, label: 'SIM' }, low: { v: 5893.19, label: 'DERIVED' }, high: { v: 16055.17, label: 'DERIVED' } } },
    relief: { kwh: { v: 1.194, label: 'SIM' }, opportunityUpperUSD: { v: 0.64, label: 'DERIVED' }, priced: { v: false, label: 'ASSUMPTION', cite: 'unpriced' } },
    whoPays: [{ who: 'GVEC (50 MW)', for: 'ERCOT summer 4CP and arbitrage', label: 'REAL', cite: 'x' }],
    transformerReplacementUSD: { v: null, label: 'ASSUMPTION', cite: 'not sourced' },
    avoidedHarm: { naive: { normalEvents: { v: 11, label: 'SIM' }, emergencyTfs: { v: 3, label: 'SIM' }, protectionOperated: { v: 0, label: 'SIM' } } },
    split: { aware: { sold: { v: 1001.11, label: 'DERIVED' }, bought: { v: 84.55, label: 'DERIVED' }, net: { v: 916.56, label: 'DERIVED' }, perBattery: { v: 9.55, label: 'DERIVED' } } },
    extra: { v: 3, label: 'SIM' },
  };
  const h = moneyHTML(fmt, money, 'aware');
  assert.match(h, /\$916\.56/);
  // fix list #12: the money headline says "fleet" and "gross, not Base's profit"
  assert.match(h, /Feeder-aware's fleet earned .*\$22\.73.* more than naive tonight \(gross, not Base's profit\)/s);
  assert.match(h, /The fleet tonight, feeder-aware .*not Base's profit.*perfect foresight/s);
  // with both splits, the reason is the measured sold / bought difference (DERIVED), not an assertion
  const both = { ...money, split: { ...money.split, naive: { sold: { v: 1014.74, label: 'DERIVED' }, bought: { v: 120.91, label: 'DERIVED' }, net: { v: 893.83, label: 'DERIVED' } } } };
  assert.match(moneyHTML(fmt, both, 'aware'), /because prices kept falling after the onset: it sold <span class="num">\$13\.63<\/span><span class="chip chip-DERIVED"[^>]*>DERIVED<\/span> less at the peak but bought back <span class="num">\$36\.36<\/span>/);
  assert.match(h, /Sold into the evening peak.*\$1,001\.11/s);
  assert.match(h, /Bought back when cheap.*\$84\.55/s);
  assert.ok(!/5,893|16,055/.test(h), 'the band never renders on P1');
  assert.match(h, /not paid for today <span class="chip chip-ASSUMPTION"/);
  assert.match(h, /GVEC \(50 MW\): ERCOT summer 4CP and arbitrage<\/span> <span class="chip chip-REAL"/);
  assert.match(h, /not sourced <span class="chip chip-ASSUMPTION"/);
  assert.match(h, /<td>11<\/td><td>3<\/td><td>0<\/td>/);
  assert.match(h, /Extra/);
  // L7: a branch note from l2 shows in the money section
  assert.match(moneyHTML(fmt, money, 'aware', BRANCH_NAMES, null, { aware: { note: { text: 'the silent battery ends lower', label: 'SIM' } } }), /the silent battery ends lower/);
  assert.ok(isLabelledRecord(fmt, { text: 'a', label: 'REAL' }));
  assert.throws(() => moneyHTML(fmt, { mystery: 5 }, 'aware'), fmt.LabelError);
  // the money meter reads `cash` (int cents) only when l2 ships it; the UI never does money arithmetic
  assert.equal(cashAt({}, 'aware', 3), null);
  const c = cashAt({ cash: { aware: [0, 150, -25] }, series: { cash: { label: 'DERIVED', cite: 'x' } } }, 'aware', 1);
  assert.deepEqual([c.v, c.label], [1.5, 'DERIVED']);
  if (meta.cash) for (const b of Object.keys(meta.cash)) assert.equal(cashAt(meta, b, meta.steps - 1).v, meta.summary[b].energyValueUSD.v);
});

test('labelled trees: tags on every value, units inherited, a bare headline number throws', () => {
  const html = labelledTreeHTML(fmt, meta.money);
  assert.ok(!/NaN|undefined/.test(html));
  const t = labelledTreeHTML(fmt, { energyValueUSD: { naive: { v: -12.5, label: 'DERIVED' } }, note: 'unpriced', ids: { rank: 3 } });
  assert.match(t, /-\$12\.50/);
  assert.match(t, /chip-DERIVED/);
  assert.throws(() => labelledTreeHTML(fmt, { reliefKW: 6.1 }), fmt.LabelError);
  assert.deepEqual(optsFor('reliefKWh'), { unit: ' kWh', digits: 1 });
  assert.equal(humanKey('costOfAwareness'), 'Cost of awareness (naive minus aware)');
  assert.equal(seriesLabel({ series: { loading: { label: 'SIM' } } }, 'loading'), 'SIM');
  assert.equal(seriesLabel({}, 'price', 'REAL'), 'REAL');
});

test('voltage and feeder cable: measured, never asserted: "stays in range" only when no home is below 0.95 pu', () => {
  const base = { vMinHome: { v: 0.9538, label: 'SIM', volts: 114.5, home: 211, t: '22:31' },
    feederHead: { v: 84.2, label: 'SIM', amps: 311.5, t: '22:05', ratingA: { v: 370, label: 'REAL', cite: 'SMART-DS NormAmps' } } };
  const ok = gridCheckHTML(fmt, { ...base, homesBelow095: { v: 0, label: 'SIM' } }, homeLabel);
  assert.match(ok, /Voltage stays in range at unity pf/);
  assert.match(ok, /0\.9538 pu/);
  assert.match(ok, /370 A/);
  const sag = gridCheckHTML(fmt, { ...base, vMinHome: { ...base.vMinHome, v: 0.9321 }, homesBelow095: { v: 4, label: 'SIM' } }, homeLabel);
  assert.ok(!/stays in range/.test(sag));
  for (const b of meta.branches) assert.ok(gridCheckHTML(fmt, meta.summary[b], homeLabel).length > 0, b);
});

test('driver: a spike names its home and shared SMART-DS profile, only near the spike', () => {
  assert.equal(DRIVER_WINDOW_MIN, 15);
  const r = meta.relief;
  if (!r || !r.driver) return;
  const k = Number.isInteger(r.step) ? r.step : fmt.timeToStep(meta, r.t);
  const info = spikeDriverAt(meta, fmt, r.tf, k);
  assert.equal(info.kind, 'relief');
  assert.ok(spikeDriverAt(meta, fmt, r.tf, k + 15));
  assert.equal(spikeDriverAt(meta, fmt, r.tf, k + 16), null);
  const html = driverLineHTML(fmt, info, (h) => (typeof h === 'object' ? h.label : homeLabel(h)));
  assert.match(html, new RegExp(r.driver.profile));
  if (r.driver.sharedWith && r.driver.sharedWith.length) assert.match(html, /not independent evidence/);
  assert.equal(driverLineHTML(fmt, null, homeLabel), '');
});

test('relief peak time (judge R1 F7): reliefKW is the peak discharge; its minute comes from the data', () => {
  const r = meta.relief;
  const doc = docs.aware;
  if (!r || !r.reliefKW || !doc) return;
  const t = reliefPeakAt(meta, doc, fmt);
  assert.ok(t);
  const f = Object.values(doc.focus).find((x) => x.tf === r.tf);
  assert.ok(Math.abs(-f.batKW[fmt.timeToStep(meta, t)] / 10 - r.reliefKW.v) <= 0.1, `batKW at ${t} = reliefKW`);
});

test('scale ladder: rungs with their words + base tag, shares below 0.1% to 2 significant figures', () => {
  const f = (v) => fmt.fmtValue({ v, label: 'DERIVED' }, pctOpts(v));
  assert.equal(f(4.9e-05), '0.000049%');
  assert.equal(f(0.501), '0.5%');
  assert.equal(f(160), '160%');
  assert.ok(ladderFrac(4.9e-05) < ladderFrac(0.501) && ladderFrac(0.501) < ladderFrac(160));
  const ladder = meta.scaleLadder || (meta.money && meta.money.scaleLadder);
  if (!ladder) return;
  const html = ladderHTML(fmt, ladder);
  assert.equal((html.match(/class="p1-rung p1-rung-/g) || []).length, ladder.rungs.length);
  assert.ok(!/>0\.0%</.test(html));
});

test('history days (checkpoint b): the panel reads &date=; every simulated evening tells its own story from its own data', () => {
  assert.equal(supportsDates, true);
  assert.deepEqual(ALL_BRANCHES, ['none', 'naive', 'aware', 'aware_faults']);
  // the spike cue (and the relief section) only on an evening where A went over its nameplate with no batteries
  const flat = { ...meta, relief: { ...meta.relief, minutesOver100: { ...(meta.relief || {}).minutesOver100, none: 0 } } };
  assert.ok(!storyCues(flat, docs.none, 'none', topology, fmt).some((c) => c.id === 'spike'));
  const idxPath = path.join(UI, 'data', 'p1', 'days', 'index.json');
  if (!fs.existsSync(idxPath)) return;   // before l2's history build lands: nothing more to check
  const index = JSON.parse(fs.readFileSync(idxPath, 'utf8'));
  for (const row of index.days || []) {
    if (!row.date || row.date === meta.day) continue;
    const dir = path.join(UI, 'data', 'p1', 'days', row.date);
    const m = JSON.parse(fs.readFileSync(path.join(dir, 'meta.json'), 'utf8'));
    assert.equal(m.day, row.date);
    assert.ok(!m.branches.includes('aware_faults'), 'failures are scripted for 23 Aug only');
    const namesD = { tf: tfName, home: homeLabel, time: (st) => fmt.stepToTime(m, st) };
    for (const b of m.branches) {
      const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir, `${b}.json.gz`))).toString('utf8'));
      const cs = storyCues(m, d, b, topology, fmt);
      for (const c of cs) assert.deepEqual(bareDigits(cueText(c, fmt, namesD, b)), [], `${row.date} ${b} ${c.id}`);
      const at = Object.fromEntries(cs.map((c) => [c.id, c]));
      if (b === 'naive' && at.overload) assert.ok(at.drop.k <= at.overload.k);
      if (b === 'aware') for (const id of ['overload', 'allcharge', 'backfeed']) assert.ok(!at[id], `${row.date} aware has no ${id}`);
      if (m.cash && m.cash[b]) assert.equal(cashAt(m, b, m.steps - 1).v, m.summary[b].energyValueUSD.v, `${row.date} ${b}: the money meter ends at the evening's value`);
    }
  }
});
