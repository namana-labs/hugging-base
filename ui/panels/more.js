// ui/panels/more.js (L5): the "More" tab and the demo's beat captions.
//
//   mount(el, ctx) -> Promise            the More view: the 5-minute beat list, money, performance, the untouched
//                                         prototype and four-home, and (P3) the chaos sweep and ERCOT console when built
//   beatBarHTML(ctx) -> Promise<string>  the caption bar for ?beat=<id> (P2 and More render it; P1 via mountBeatBar)
//   mountBeatBar(ctx) -> Promise         inserts the caption bar at the top of the panel (for the shell / P1)
//
// Captions in ui/data/beats.json are TEMPLATES: prose plus {{fact}} placeholders. Every number in a caption comes
// from a fact below, read from the committed JSON, and renders with its honesty label (format.js). A caption with a
// bare digit fails ui/test/p2.test.js. A fact whose data is not built yet renders "(not built yet)", never a guess.
//   {{name}}                a fact from FACTS
//   {{chip:LABEL}}          a label chip for a prose claim; {{chip:LABEL:cite text}} adds the cite as its title
//   [[ ... ]]               an OPTIONAL clause (round 2): dropped whole when any fact inside it is not built, so a
//                           caption that names round-2 data (money.split, onsetDeferral, the history days) reads
//                           cleanly before that data lands, and in full after. Never a guess, never a half sentence.
// Each beat also has a `headline` (round 2): one sentence, placeholders only, no bare digits. The P1 beat bar shows the
// headline with the full caption one click away (UX_SPEC_R2 7.2); P2 and More show both.

import { chartHTML } from '../lib/charts.js';
import { svg } from '../lib/icons.js';
import { calendarStripHTML } from '../lib/days.js';

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];
const isL = (x) => x !== null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
const L = (v, label, cite, o) => (v === null || v === undefined ? null : { v, label, ...(cite ? { cite } : {}), ...(o ? { o } : {}) });
const withO = (x, o) => (isL(x) ? { ...x, o } : null);
const get = (obj, path) => path.split('.').reduce((a, k) => (a == null ? a : a[k]), obj);

// Surrogate-only numbers carry a "screening" chip (build prompt 5.6.11, 3.4). L3 ends the cite of every number the
// OpenDSS referee did not check with "not OpenDSS-checked"; a bulk series with `by: "surrogate"` is the same thing.
export const SCREEN_CITE = /not OpenDSS-checked/i;
export function isScreening(x) { return !!(isL(x) && typeof x.cite === 'string' && SCREEN_CITE.test(x.cite)); }
export const SCREEN_CHIP = '<span class="p2-badge screen sm" title="surrogate screening number (sim.surrogate); not refereed by OpenDSS">screening</span>';
/** fmtHTML, plus the screening chip on a surrogate-only value. */
export function numHTML(fmt, x, opts = {}) { return fmt.fmtHTML(x, opts) + (isScreening(x) ? SCREEN_CHIP : ''); }
/** fmt (text), plus "screening" on a surrogate-only value. */
export function numText(fmt, x, opts = {}) { return fmt.fmt(x, opts) + (isScreening(x) ? ' screening' : ''); }
/** Chips in rendered HTML whose cite says "not OpenDSS-checked" but that are not followed by the screening chip
 *  (ui/test/p2.test.js gates on this returning []). */
export function unscreenedChips(html) {
  const out = [];
  const re = /<span class="chip chip-[A-Z]+" title="([^"]*)">[A-Z]+<\/span>/g;
  for (const m of String(html).matchAll(re)) {
    if (!SCREEN_CITE.test(m[1])) continue;
    const next = String(html).slice(m.index + m[0].length, m.index + m[0].length + 40);
    if (!next.startsWith('<span class="p2-badge screen')) out.push(String(html).slice(Math.max(0, m.index - 80), m.index + m[0].length));
  }
  return out;
}

export const DEFAULT_AWARE = 'aware-core-d26-g0';
export const DEFAULT_NAIVE = 'naive-core-d26-g0';

function tfName(topology, i) {
  const t = topology && topology.transformers[i];
  if (!t) return i == null ? null : `T-${i}`;
  return t.focus ? `${t.focus} (T-${i})` : `T-${i}`;
}
function homeLabel(topology, i) { const h = topology && topology.homes[i]; return h ? h.label : null; }
function constOf(doc, name, o) {
  const c = doc && doc.constants && doc.constants[name];
  return c && c.value !== null && c.value !== undefined ? { v: c.value, label: c.label, cite: c.cite, o } : null;
}
function rankOf(doc, hi) {
  for (const e of (doc && doc.ranking) || []) if (e.home === hi || (e.alsoOnTf || []).includes(hi)) return e;
  return null;
}
function hhmm(min) { const m = ((min % 1440) + 1440) % 1440; return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; }
function stepTime(meta, k) {
  const [h, m] = String(meta.start || '16:00').split(':').map(Number);
  return hhmm(h * 60 + m + Math.round(k * (meta.stepSeconds || 60) / 60));
}
function modeHour(hist) {
  let best = 0, bi = null;
  (hist || []).forEach((v, i) => { if (v > best) { best = v; bi = i; } });
  return bi;
}
function relief(S) { return S.p1meta && S.p1meta.relief; }
/** driver.sharedWith: strings ("Home 0409") in fixtures, {home, label, tf} objects in real data. */
export function sharedNames(list) {
  return (list || []).map((x) => (typeof x === 'string' ? x : x && x.label ? `${x.label}${x.tf != null ? ` on T-${x.tf}` : ''}` : null)).filter(Boolean);
}
function minutesOver100(S, which) {
  const m = relief(S) && relief(S).minutesOver100;
  if (!m) return null;
  if (isL(m)) {
    if (which === 'none') return withO(m, { unit: ' min' });
    return typeof m[which] === 'number' ? { v: m[which], label: m.label, cite: m.cite, o: { unit: ' min' } } : null;
  }
  return withO(m[which], { unit: ' min' });
}
/** Max loading on A-D while the transformer actually exports: net P (homes + batteries, focus.homeKW + focus.batKW)
 *  below zero, from a p1 branch file. Audit R2 M4: testing batKW < 0 alone counted 16:39 on A, when A's batteries
 *  gave 1.7 kW of relief but A still imported 23.0 kW (so that 97.9% was not back-feed). Exported for the tests. */
export function backfeed(doc, topology) {
  if (!doc || !doc.focus || !doc.loading) return null;
  let best = null;
  for (const key of ['A', 'B', 'C', 'D']) {
    const f = doc.focus[key];
    if (!f || !Array.isArray(f.batKW) || !Array.isArray(f.homeKW)) continue;
    f.batKW.forEach((b, k) => {
      if (!(b < 0) || !(Number(f.homeKW[k]) + Number(b) < 0)) return;
      const pct = doc.loading[k] && doc.loading[k][f.tf];
      if (typeof pct === 'number' && (!best || pct > best.pct)) best = { pct, key, tf: f.tf, k };
    });
  }
  if (!best) return null;
  const lab = (doc.series && doc.series.loading && doc.series.loading.label) || 'SIM';
  return { ...best, v: best.pct / 10, label: lab, name: tfName(topology, best.tf) };
}
// Display rule for the flip headline (ASSUMPTION, shown on screen): the sentence "How you charge decides where the
// next battery goes" appears only when naive and aware share at most this many of their top 10 (and, when at least
// 10 untied candidates exist, the untied top 10 too). p2.js re-exports both.
export const FLIP_HEADLINE_MAX_OVERLAP = 5;

/** The flip verdict from index.flip (labelled numbers). */
export function flipVerdict(flip) {
  const ov = flip && flip.top10Overlap;
  if (!ov || typeof ov.v !== 'number') return { supports: false, headline: null };
  const un = flip.untied && flip.untied.top10Overlap;
  const nU = flip.untied ? (typeof flip.untied.n === 'number' ? flip.untied.n : flip.untied.n && flip.untied.n.v) : null;
  const unOk = !un || typeof un.v !== 'number' || !(nU >= 10) || un.v <= FLIP_HEADLINE_MAX_OVERLAP;
  const supports = ov.v <= FLIP_HEADLINE_MAX_OVERLAP && unOk;
  return { supports, headline: supports ? 'How you charge decides where the next battery goes.' : null };
}

/** Indices j into fleet[96] (and so into a branch's batKW[step][96]) of the batteries behind transformer tf. */
export function fleetOn(topology, tf) {
  const out = [];
  ((topology && topology.fleet) || []).forEach((h, j) => {
    const hi = typeof h === 'number' ? h : h && h.home;
    if (topology.homes[hi] && topology.homes[hi].tf === tf) out.push(j);
  });
  return out;
}
const minGrantKW = (meta) => { const c = meta && meta.constants && meta.constants.MIN_GRANT_KW; return c && typeof c.value === 'number' ? c.value : 0.5; };

/**
 * What the "transformer runs hot" fault actually did, measured in the aware_faults branch (build prompt 5.4.4).
 * The caption says this instead of asserting a throttle: on 23 Aug the hot transformer's batteries may not be charging
 * when the extra load arrives, and then there is nothing to shift (sim.verify p1 prints the same three kW values).
 *   before/at/after: kW on the transformer's batteries the minute before the load arrives, at it, and the minute after
 *   state: 'idle' (not charging before: nothing to shift) | 'throttled' (cut by more than MIN_GRANT_KW the next minute)
 *          | 'kept' (kept charging)
 *   maxPct/maxPctStep: the transformer's highest OpenDSS loading over the event window; maxKW/firstChargeStep: its
 *   batteries' highest charge in the window and the first minute they charge in it (null if they never do)
 * Null when the event, the branch file or the topology is missing.
 */
export function hotOutcome(meta, doc, topology) {
  const e = ((meta && meta.events && meta.events.aware_faults) || []).find((x) => x.kind === 'hot');
  if (!e || !doc || !Array.isArray(doc.batKW) || !Array.isArray(doc.loading) || !topology || typeof e.step !== 'number') return null;
  const js = fleetOn(topology, e.tf);
  const n = Math.min(doc.batKW.length, doc.loading.length);
  if (e.step < 1 || e.step >= n) return null;
  const kwAt = (k) => js.reduce((s, j) => s + (Number(doc.batKW[k][j]) || 0), 0) / 10;
  const g = minGrantKW(meta);
  const s0 = e.step;
  const before = kwAt(s0 - 1), at = kwAt(s0), after = kwAt(Math.min(n - 1, s0 + 1));
  const end = Math.min(n, s0 + (typeof e.minutes === 'number' ? Math.round(e.minutes * 60 / (meta.stepSeconds || 60)) : 60));
  let maxPct = -Infinity, maxPctStep = s0, maxKW = 0, firstChargeStep = null;
  for (let k = s0; k < end; k++) {
    const p = Number(doc.loading[k][e.tf]) / 10;
    if (p > maxPct) { maxPct = p; maxPctStep = k; }
    const kw = kwAt(k);
    if (kw > maxKW) maxKW = kw;
    if (kw > g && firstChargeStep === null) firstChargeStep = k;
  }
  const state = before <= g ? 'idle' : (after < before - g ? 'throttled' : 'kept');
  return { tf: e.tf, home: e.home, step: s0, minutes: e.minutes, batteries: js.length, before, at, after, state, maxPct, maxPctStep, maxKW, firstChargeStep, minGrant: g };
}

/** The first minute (from Tc) each focus transformer A-D gets charge in a branch, in time order: the measured order
 *  the charge reaches the street (the rotation EXPECT in 7.3 is refuted on this data, so the beat states the order). */
export function chargeOrder(meta, doc, topology) {
  if (!meta || !doc || !Array.isArray(doc.batKW) || !topology) return null;
  const k0 = meta.tc && typeof meta.tc.step === 'number' ? meta.tc.step : 0;
  const g = minGrantKW(meta);
  const out = [];
  for (const f of topology.focus || []) {
    const js = fleetOn(topology, f.tf);
    for (let k = k0; k < doc.batKW.length; k++) {
      if (js.reduce((s, j) => s + (Number(doc.batKW[k][j]) || 0), 0) / 10 > g) { out.push({ key: f.key, tf: f.tf, step: k }); break; }
    }
  }
  return out.sort((a, b) => a.step - b.step || String(a.key).localeCompare(String(b.key)));
}

/**
 * A's relief discharge at its largest, measured in the feeder-aware branch (the series the gauge draws): the run of
 * steps around meta.relief.step in which A's batteries discharge, its largest discharge and the minute it happens.
 * meta.relief.reliefKW is that peak but carries no time, and it is not the kW at the relief step (judge R1 F7:
 * -6.2 kW at 16:45, -6.9 kW at 16:46). Null when A's batteries are not discharging at the relief step.
 */
export function reliefPeak(meta, doc, topology) {
  const r = meta && meta.relief;
  if (!r || typeof r.step !== 'number' || !doc || !doc.focus || !topology) return null;
  const fk = (topology.focus || []).find((f) => f.tf === r.tf);
  const kw = fk && doc.focus[fk.key] && doc.focus[fk.key].batKW;
  if (!Array.isArray(kw) || !(kw[r.step] < 0)) return null;
  let a = r.step, b = r.step;
  while (a > 0 && kw[a - 1] < 0) a -= 1;
  while (b < kw.length - 1 && kw[b + 1] < 0) b += 1;
  let k = a;
  for (let i = a; i <= b; i++) if (kw[i] < kw[k]) k = i;
  return { key: fk.key, tf: r.tf, step: k, kw: -kw[k] / 10, from: a, to: b, label: (doc.series && doc.series.batKW && doc.series.batKW.label) || 'SIM' };
}

/** Digits for a share-of-scale percent: whole above 10%, one place above 1%, two significant figures below 1% (the
 *  ERCOT rung is 0.000049%; a fixed 1 digit printed 0.0%, judge R1 F2). */
export function shareDigits(v) {
  if (!(v > 0) || v >= 10) return 0;
  if (v >= 1) return 1;
  return Math.max(1, 1 - Math.floor(Math.log10(v)));
}

function scanEngine(eng, re) {
  let hit = null;
  const walk = (o, path) => {
    if (!o || typeof o !== 'object' || hit) return;
    for (const [k, v] of Object.entries(o)) {
      const p = path ? `${path}.${k}` : k;
      if (isL(v) && typeof v.v === 'number' && re.test(p)) { hit = { ...v, path: p }; return; }
      if (v && typeof v === 'object' && !Array.isArray(v)) walk(v, p);
    }
  };
  walk(eng, '');
  return hit;
}

/**
 * FACTS: name -> [sources, fn(S) -> null | string | labelled (with optional .o format opts) | parts[], optionalSources?].
 * A fact runs only when every source in `sources` loaded; `optionalSources` are loaded too but may be null.
 * Sources: topology, p1meta, p1:<branch>, p2index, p2:<combo>, engine. A null result renders "(not built yet)".
 */
export const FACTS = {
  streetTfs: [['topology'], (S) => L((S.topology.focus || []).length, 'REAL', 'SMART-DS topology: A-D by transformer id')],
  streetHomes: [['topology'], (S) => L((S.topology.focus || []).reduce((s, f) => s + S.topology.transformers[f.tf].homes.length, 0), 'REAL', 'SMART-DS topology')],
  fleetSize: [['topology'], (S) => L((S.topology.fleet || []).length, 'ASSUMPTION', "the prototype's 96-Core placement, seed 17263")],
  reliefT: [['p1meta'], (S) => (relief(S) ? L(relief(S).t, 'SIM', 'OpenDSS peak interval on A, no batteries') : null)],
  reliefNone: [['p1meta'], (S) => withO(relief(S) && relief(S).none, { unit: '%', digits: 1 })],
  reliefAware: [['p1meta'], (S) => withO(relief(S) && relief(S).aware, { unit: '%', digits: 1 })],
  reliefMinutesNone: [['p1meta'], (S) => minutesOver100(S, 'none')],
  reliefMinutesAware: [['p1meta'], (S) => minutesOver100(S, 'aware')],
  reliefKW: [['p1meta'], (S) => withO(relief(S) && relief(S).reliefKW, { unit: ' kW', digits: 1 })],
  reliefKWh: [['p1meta'], (S) => withO(relief(S) && relief(S).reliefKWh, { unit: ' kWh', digits: 1 })],
  // The scale ladder (build prompt 3.4, DERIVED): meta.scaleLadder's kW and its rungs, each share with its base.
  scaleLadderKW: [['p1meta'], (S) => withO(get(S, 'p1meta.scaleLadder.kw'), { unit: ' kW', digits: 0 })],
  scaleLadder: [['p1meta'], (S) => {
    const rungs = get(S, 'p1meta.scaleLadder.rungs');
    if (!Array.isArray(rungs)) return null;
    const parts = [];
    for (const r of rungs) {
      if (!r || !isL(r.sharePct) || !isL(r.base)) continue;
      if (parts.length) parts.push('; ');
      const head = String(r.name || r.scale || '').split(':')[0].trim();
      parts.push({ ...r.sharePct, o: { unit: '%', digits: shareDigits(r.sharePct.v) } }, ` of ${head} (`,
        { v: r.base.v, label: r.base.label, cite: r.base.cite, o: { unit: r.base.unit ? ` ${r.base.unit}` : '', digits: Number.isInteger(r.base.v) ? 0 : 1 } },
        r.base.at ? ` on ${String(r.base.at).slice(0, 10)}` : '', ')');
    }
    return parts.length ? parts : null;
  }],
  // "up to X kW (HH:MM)": the largest relief discharge and its minute, from the aware branch (reliefPeak)
  reliefKWPeak: [['p1meta', 'p1:aware', 'topology'], (S) => {
    const p = reliefPeak(S.p1meta, S['p1:aware'], S.topology);
    if (!p) return null;
    return [L(Math.round(p.kw * 10) / 10, p.label, `largest discharge of ${p.key}'s batteries in the relief event (feeder-aware branch, focus.${p.key}.batKW)`, { unit: ' kW', digits: 1 }),
      ' (', L(stepTime(S.p1meta, p.step), 'SIM', 'the minute of that largest discharge'), ')'];
  }],
  reliefDriverHome: [['p1meta'], (S) => get(S, 'p1meta.relief.driver.label') || null],
  reliefDriverProfile: [['p1meta'], (S) => get(S, 'p1meta.relief.driver.profile') || null],
  reliefDriverShared: [['p1meta'], (S) => {
    const d = get(S, 'p1meta.relief.driver');
    if (!d) return null;
    const names = sharedNames(d.sharedWith);
    return names.length ? names.join(', ') : 'no other home on this feeder';
  }],
  unrelievedTf: [['p1meta', 'topology'], (S) => {
    const u = S.p1meta && S.p1meta.unrelieved;
    return Array.isArray(u) && u.length ? u.map((x) => tfName(S.topology, x.tf)).join(', ') : null;
  }],
  dischargeSlots: [['p1meta'], (S) => {
    const p = S.p1meta && S.p1meta.plan;
    if (!p || !Array.isArray(p.discharge)) return null;
    const partial = new Set((p.partial || []).map((x) => x[0]));
    const full = p.discharge.filter((x) => !partial.has(x[0])).map((x) => x[0]).sort();
    const part = (p.partial || []).map((x) => `${x[1]} min of ${x[0]}`);
    return L([...full, ...part].join(', '), 'DERIVED', 'sim.prices.discharge_plan: highest-priced intervals the usable energy covers, perfect foresight (ASSUMPTION)');
  }],
  onsetT: [['p1meta'], (S) => (S.p1meta && S.p1meta.plan ? L(S.p1meta.plan.onset, 'DERIVED', 'D-26 onset: first interval after the evening peak at or below 2 x the day median') : null)],
  onsetPrice: [['p1meta'], (S) => withO(get(S, 'p1meta.plan.onsetPrice'), { money: true, digits: 2 })],
  eveningPeakPrice: [['p1meta'], (S) => {
    const m = S.p1meta;
    if (!m || !Array.isArray(m.price)) return null;
    let bi = -1;
    m.price.forEach((v, i) => { if (stepTime(m, i) >= '17:00' && (bi < 0 || v > m.price[bi])) bi = i; });
    return bi < 0 ? null : L(m.price[bi], 'REAL', 'ERCOT RTM SPP LZ_NORTH', { money: true, digits: 2 });
  }],
  eveningPeakT: [['p1meta'], (S) => {
    const m = S.p1meta;
    if (!m || !Array.isArray(m.price)) return null;
    let bi = -1;
    m.price.forEach((v, i) => { if (stepTime(m, i) >= '17:00' && (bi < 0 || v > m.price[bi])) bi = i; });
    return bi < 0 ? null : L(stepTime(m, bi - (bi % 15)), 'REAL', 'interval start of the evening price peak');
  }],
  naiveMax: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.maxLoading'), { unit: '%', digits: 1 })],
  naiveMaxTf: [['p1meta', 'topology'], (S) => { const x = get(S, 'p1meta.summary.naive.maxLoading'); return x ? tfName(S.topology, x.tf) : null; }],
  naiveMaxT: [['p1meta'], (S) => { const x = get(S, 'p1meta.summary.naive.maxLoading'); return x && x.t ? L(x.t, x.label, x.cite) : null; }],
  naiveNormalEvents: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.normalEvents'))],
  naiveEmergencyTfs: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.emergencyTfs'))],
  naiveProtection: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.protectionOperated'))],
  naiveHomesDark: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.homesDark'))],
  fusePct: [['p1meta'], (S) => { const p = get(S, 'p1meta.protection'); return p ? L(p.fusePct, p.label || 'ASSUMPTION', p.cite, { unit: '%' }) : null; }],
  fuseMinutes: [['p1meta'], (S) => { const p = get(S, 'p1meta.protection'); return p ? L(p.fuseMinutes, p.label || 'ASSUMPTION', p.cite, { unit: ' min' }) : null; }],
  awareBatteryNormal: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.aware.batteryCausedNormal'))],
  awareBatteryEmergency: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.aware.batteryCausedEmergency'))],
  awareCharged: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.aware.chargedPctBy0400'), { unit: '%', digits: 1 })],
  awareVerdict: [['p1meta'], (S) => {
    const n = get(S, 'p1meta.summary.aware.batteryCausedNormal'), e = get(S, 'p1meta.summary.aware.batteryCausedEmergency');
    if (!isL(n) || !isL(e)) return null;
    return n.v === 0 && e.v === 0 ? 'No service transformer passes its limit because of battery charging.'
      : 'Battery-caused tier events remain in this run: see the gauges.';
  }],
  naiveVmin: [['p1meta'], (S) => {
    const x = get(S, 'p1meta.summary.naive.vMinHome');
    if (!isL(x)) return null;
    return typeof x.volts === 'number'
      ? [{ ...x, o: { digits: 4, unit: ' pu' } }, ' = ', { v: x.volts, label: x.label, cite: x.cite, o: { digits: 1, unit: ' V' } }]
      : [{ ...x, o: { digits: 4, unit: ' pu' } }];
  }],
  naiveHead: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.feederHead'), { unit: '%', digits: 1 })],
  naiveHeadOnset: [['p1meta'], (S) => {
    const x = get(S, 'p1meta.summary.naive.feederHead.afterOnset');
    return isL(x) ? [{ ...x, o: { unit: '%', digits: 1 } }, ' of its rating', x.t ? ` at ${x.t}` : ''] : null;
  }],
  naiveVoltVerdict: [['p1meta'], (S) => {
    const x = get(S, 'p1meta.summary.naive.homesBelow095');
    if (!isL(x)) return null;
    return x.v === 0 ? ['voltage stays in range at unity pf (', { ...x, o: {} }, ' homes below 0.95 pu)'] : [{ ...x, o: {} }, ' homes fall below 0.95 pu'];
  }],
  naiveBackfeedMax: [['p1:naive', 'topology'], (S) => { const b = backfeed(S['p1:naive'], S.topology); return b ? [{ v: b.v, label: b.label, o: { unit: '%', digits: 1 } }, ` on ${b.name} at ${stepTime(S['p1:naive'], b.k)}`] : null; }],
  awareBackfeedMax: [['p1:aware', 'topology'], (S) => { const b = backfeed(S['p1:aware'], S.topology); return b ? [{ v: b.v, label: b.label, cite: 'OpenDSS loading while the transformer exports (net P < 0: homes + batteries), feeder-aware', o: { unit: '%', digits: 1 } }, ` on ${b.name} at ${stepTime(S['p1:aware'], b.k)}`] : 'no street transformer exports'; }],
  faultCommsT: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost'); return e ? L(e.t, 'SIM') : null; }],
  faultCommsHome: [['p1meta', 'topology'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost'); return e ? homeLabel(S.topology, e.home) : null; }],
  faultCommsKW: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost'); return e && typeof e.cmdKW === 'number' ? L(e.cmdKW, 'SIM', 'its last charge command', { unit: ' kW', digits: 1, signed: true }) : null; }],
  faultHotT: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'hot'); return e ? L(e.t, 'SIM') : null; }],
  faultStallT: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'stall'); return e ? L(e.t, 'SIM') : null; }],
  faultHotTf: [['p1meta', 'topology'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'hot'); return e ? `transformer ${tfName(S.topology, e.tf)}` : null; }],
  faultHotMinutes: [['p1meta'], (S) => {
    const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'hot');
    return constOf(S.p1meta, 'HOT_MINUTES', { unit: ' min' }) || (e && typeof e.minutes === 'number' ? L(e.minutes, 'ASSUMPTION', 'hot-transformer event length', { unit: ' min' }) : null);
  }],
  // What the hot-transformer fault did, measured (hotOutcome). Never asserts a shift the data did not show.
  faultHotOutcome: [['p1meta', 'p1:aware_faults', 'topology'], (S) => {
    const h = hotOutcome(S.p1meta, S['p1:aware_faults'], S.topology);
    if (!h) return null;
    const d = S['p1:aware_faults'];
    const kl = (d.series && d.series.batKW && d.series.batKW.label) || 'SIM';
    const pl = (d.series && d.series.loading && d.series.loading.label) || 'SIM';
    const kw = (v, cite) => L(Math.round(v * 10) / 10, kl, cite, { unit: ' kW', digits: 1, signed: true });
    const peak = L(Math.round(h.maxPct * 10) / 10, pl, `OpenDSS, highest loading on T-${h.tf} during the event (aware_faults)`, { unit: '%', digits: 1 });
    const parts = [];
    if (h.state === 'idle') {
      parts.push('Its batteries were not charging when the load arrived (', kw(h.before, 'battery kW on that transformer the minute before'), '), so there was no charge to shift.');
    } else if (h.state === 'throttled') {
      parts.push('Its batteries were throttled from ', kw(h.before, 'battery kW the minute before'), ' to ', kw(h.after, 'battery kW the minute after'), ' within a minute.');
    } else {
      parts.push('Its batteries kept charging (', kw(h.before, 'battery kW the minute before'), ', then ', kw(h.after, 'battery kW the minute after'), ').');
    }
    parts.push(' During the event it peaked at ', peak, ' of nameplate');
    if (h.firstChargeStep !== null && h.state === 'idle') parts.push(', with its batteries charging from ', L(stepTime(S.p1meta, h.firstChargeStep), 'SIM', 'first minute they charge during the event'), ' at up to ', kw(h.maxKW, 'highest battery charge on that transformer during the event'));
    else if (h.firstChargeStep === null) parts.push('; its batteries stayed idle throughout');
    parts.push('.');
    return parts;
  }],
  faultCover: [['p1meta', 'topology'], (S) => {
    const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost');
    if (!e) return null;
    if (typeof e.coveredStep !== 'number' || !Array.isArray(e.coveredBy) || !e.coveredBy.length) return 'no neighbour picked up its headroom';
    const who = e.coveredBy.map((i) => homeLabel(S.topology, i)).filter(Boolean).join(' and ');
    const s = typeof e.expiredStep === 'number' ? (e.coveredStep - e.expiredStep) * (S.p1meta.stepSeconds || 60) : null;
    return [`${who} on the same transformer pick up its headroom`, s === null ? '' : ' ', s === null ? '' : L(s, 'SIM', 'seconds from expiry to the re-grant (5.4.3 cover)', { unit: ' s' }), s === null ? '' : ' after expiry'];
  }],
  chargeOrder: [['p1meta', 'p1:aware', 'topology'], (S) => {
    const o = chargeOrder(S.p1meta, S['p1:aware'], S.topology);
    if (!o || !o.length) return null;
    return L(o.map((x) => `${x.key} ${stepTime(S.p1meta, x.step)}`).join(', '), 'SIM', 'first minute each focus transformer\'s batteries charge (feeder-aware, 23 Aug)');
  }],
  staleS: [['p1meta'], (S) => constOf(S.p1meta, 'COMMS_STALE_S', { unit: ' s' })],
  ttlS: [['p1meta'], (S) => constOf(S.p1meta, 'COMMAND_TTL_S', { unit: ' s' })],
  evKW: [['p1meta'], (S) => constOf(S.p1meta, 'EV_KW', { unit: ' kW', digits: 1 })],
  stallMin: [['p1meta'], (S) => {
    const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'stall');
    return e && typeof e.minutes === 'number' ? L(e.minutes, 'ASSUMPTION', 'STALL_MIN', { unit: ' min' }) : constOf(S.p1meta, 'STALL_MIN', { unit: ' min' });
  }],
  faultsBatteryNormal: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.aware_faults.batteryCausedNormal'))],
  faultsBatteryEmergency: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.aware_faults.batteryCausedEmergency'))],
  energyNaive: [['p1meta'], (S) => withO(get(S, 'p1meta.money.energyValueUSD.naive') || get(S, 'p1meta.summary.naive.energyValueUSD'), { money: true, digits: 0 })],
  energyAware: [['p1meta'], (S) => withO(get(S, 'p1meta.money.energyValueUSD.aware') || get(S, 'p1meta.summary.aware.energyValueUSD'), { money: true, digits: 0 })],
  costOfAwareness: [['p1meta'], (S) => withO(get(S, 'p1meta.money.costOfAwareness'), { money: true, digits: 0 })],
  fleetKWPeakAware: [['p1meta'], (S) => withO(get(S, 'p1meta.money.systemCapacityPerMonth.aware.fleetKW'), { unit: ' kW', digits: 0 })],
  capMonthAwareLow: [['p1meta'], (S) => withO(get(S, 'p1meta.money.systemCapacityPerMonth.aware.low'), { money: true, digits: 0 })],
  capMonthAwareHigh: [['p1meta'], (S) => withO(get(S, 'p1meta.money.systemCapacityPerMonth.aware.high'), { money: true, digits: 0 })],
  reliefOpportunity: [['p1meta'], (S) => withO(get(S, 'p1meta.money.relief.opportunityUpperUSD'), { money: true, digits: 2 })],
  capacityLow: [['topology'], (S) => constOf(S.p1meta, 'CAPACITY_BENCHMARK_USD_KW_MONTH', { money: true, digits: 2 }) || L(3.12, 'REAL', "Modo Apr 2026 ERCOT storage market benchmark (third party); docs/headroom/research_notes/grid_physics_orchestration_and_attacks.md:229", { money: true, digits: 2 }), ['p1meta']],
  capacityHigh: [['topology'], (S) => constOf(S.p1meta, 'CAPACITY_HIGH_USD_KW_MONTH', { money: true, digits: 2 }) || L(8.5, 'DERIVED', 'implied from an UNVERIFIED Austin Energy figure; docs/research-report.md:246, docs/design.md:160-161', { money: true, digits: 2 }), ['p1meta']],
  controllerView: [['p1meta'], (S) => { const c = get(S, 'p1meta.controllerView'); return c && c.text ? L(c.text, c.label || 'ASSUMPTION', c.cite) : null; }],
  msPerSolve: [['topology'], (S) => {
    const m = get(S, 'p1meta.engine.msPerSolve');
    const x = isL(m) && typeof m.v === 'number' ? m : scanEngine(S.engine, /solve/i);
    return x ? { ...x, o: { unit: ' ms', digits: 1 } } : null;
  }, ['p1meta', 'engine']],
  allocateLargest: [['topology'], (S) => {
    const a = S.engine && S.engine.allocate;
    if (a && typeof a === 'object') {
      const sizes = Object.keys(a).filter((k) => /^\d+$/.test(k) && isL(a[k]) && typeof a[k].v === 'number').map(Number).sort((x, y) => x - y);
      if (sizes.length) {
        const big = sizes[sizes.length - 1], x = a[String(big)];
        return [{ ...x, v: Math.round(x.v / 100) / 10, cite: `${x.cite || 'sim.bench'}; shown here in ms`, o: { unit: ' ms', digits: 1 } }, ' per call for ', L(big, 'ASSUMPTION', 'synthetic scale test fleet (sim.bench)'), ' batteries'];
      }
    }
    const h = scanEngine(S.engine, /100k|100000|1e5/i) || scanEngine(S.engine, /alloc/i);
    return h ? { ...h, o: { unit: ' µs', digits: 0 } } : null;
  }, ['engine']],
  candidates: [['p2index'], (S) => { const t = get(S, 'p2index.ties'); return t && typeof t.of === 'number' ? L(t.of, 'DERIVED', 'eligible homes without a battery') : null; }],
  refereeRuns: [['p2index'], (S) => { const r = get(S, 'p2index.referee'); return r && typeof r.runs === 'number' ? L(r.runs, 'SIM', 'sim.referee OpenDSS month runs') : null; }],
  refereeP99: [['p2index'], (S) => {
    if (get(S, 'p2index.referee.runs') === 0) return 'not measured (the referee has not run)';
    const x = withO(get(S, 'p2index.referee.errorPts.p99'), { unit: ' pts', digits: 2 });
    return x && typeof x.v === 'number' ? ['p99 ', x] : null;
  }],
  awareTop1: [['p2:' + DEFAULT_AWARE, 'topology'], (S) => { const e = get(S, `p2:${DEFAULT_AWARE}.ranking.0`); return e ? homeLabel(S.topology, e.home) : null; }],
  awareTop1Tf: [['p2:' + DEFAULT_AWARE, 'topology'], (S) => { const e = get(S, `p2:${DEFAULT_AWARE}.ranking.0`); return e ? tfName(S.topology, e.tf) : null; }],
  awareTop1UnderNaive: [['p2:' + DEFAULT_AWARE, 'p2:' + DEFAULT_NAIVE], (S) => {
    const a = get(S, `p2:${DEFAULT_AWARE}.ranking.0`), nd = S[`p2:${DEFAULT_NAIVE}`];
    if (!a || !nd) return null;
    const e = rankOf(nd, a.home);
    if (e) {
      const viol = e.noNewViolation && e.noNewViolation.v === false;
      return [`naive rank `, L(e.rank, 'SIM', 'naive ranking'), viol ? ', and it adds a violation there (where NOT to put it)' : ''];
    }
    // outside the naive top 50: the collapsed rank (flip.movers) and the naive with/without peak (index.bridge)
    const mv = (get(S, 'p2index.flip.movers') || []).find((m) => m.home === a.home);
    const br = (get(S, 'p2index.bridge') || []).find((b) => b.tf === a.tf);
    const bn = br && br.naive && br.naive.home === a.home ? br.naive : null;
    const parts = [];
    parts.push(mv && isL(mv.rankNaive) ? 'naive rank ' : 'outside the naive top fifty');
    if (mv && isL(mv.rankNaive)) parts.push({ ...mv.rankNaive, o: {} }, isL(mv.rankAware) ? ' (feeder-aware rank ' : '', isL(mv.rankAware) ? { ...mv.rankAware, o: {} } : '', isL(mv.rankAware) ? ')' : '');
    if (bn && isL(bn.peakWithoutPct) && isL(bn.peakWithPct)) parts.push('; managed naively, a battery there takes its month peak from ', { ...bn.peakWithoutPct, o: { unit: '%', digits: 1 } }, ' to ', { ...bn.peakWithPct, o: { unit: '%', digits: 1 } });
    if (bn && bn.noNewViolation && bn.noNewViolation.v === false) parts.push(' and adds a violation (where NOT to put it)');
    return parts;
  }, ['p2index']],
  // the naive standing of feeder-aware's first choice, short (the p2-flip headline)
  awareTop1NaiveRank: [['p2:' + DEFAULT_AWARE, 'p2:' + DEFAULT_NAIVE], (S) => {
    const a = get(S, `p2:${DEFAULT_AWARE}.ranking.0`), nd = S[`p2:${DEFAULT_NAIVE}`];
    if (!a || !nd) return null;
    const e = rankOf(nd, a.home);
    if (e) return ['rank ', L(e.rank, 'SIM', 'naive ranking (sim.p2_build)')];
    const mv = (get(S, 'p2index.flip.movers') || []).find((m) => m.home === a.home);
    return mv && isL(mv.rankNaive) ? ['rank ', { ...mv.rankNaive, o: {} }] : 'outside the top fifty';
  }, ['p2index']],
  flipHeadline: [['p2index'], (S) => {
    const f = get(S, 'p2index.flip');
    if (!f || !isL(f.top10Overlap)) return null;
    const v = flipVerdict(f);
    return v.supports ? v.headline : 'The flip is partial in this data (the headline needs at most five shared homes in both top tens).';
  }],
  flipUntied: [['p2index'], (S) => {
    const u = get(S, 'p2index.flip.untied');
    if (!u || !isL(u.top10Overlap)) return null;
    const n = typeof u.n === 'number' ? L(u.n, u.top10Overlap.label, 'candidates no id tie-break placed') : (isL(u.n) ? u.n : null);
    return [{ ...u.top10Overlap, o: {} }, ' of ten', isL(u.spearman) ? ' (Spearman ' : '', isL(u.spearman) ? { ...u.spearman, o: { digits: 2 } } : '', n ? ', over ' : '', n ? { ...n, o: {} } : '', n ? ' candidates' : '', isL(u.spearman) ? ')' : ''];
  }],
  flipOverlap: [['p2index'], (S) => withO(get(S, 'p2index.flip.top10Overlap'))],
  flipSpearman: [['p2index'], (S) => withO(get(S, 'p2index.flip.spearman'), { digits: 2 })],
  capNaive: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.naive'))],
  capAware: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.aware'))],
  capAwareStop: [['p2index', 'topology'], (S) => {
    const a = get(S, 'p2index.usefulCapacity.aware');
    if (!isL(a)) return null;
    const eligible = (S.topology.homes || []).filter((h) => h.eligible).length;
    return a.v >= eligible ? 'every eligible home, without curtailment passing the cap' : 'before curtailment passes the cap';
  }],
  // Where the ASSUMPTION protection rule operates in P2 (naive): candidate placements and the existing fleet. Dark
  // homes are counted from the data; with none, the caption says so instead of animating dark homes.
  protectionWhere: [['p2:' + DEFAULT_NAIVE, 'topology'], (S) => {
    const d = S[`p2:${DEFAULT_NAIVE}`];
    const cases = Array.isArray(d.protectionCases) ? d.protectionCases : null;
    const fleet = get(S, 'p2index.fleetProtection.naive');
    if (!cases && !Array.isArray(fleet)) return null;
    const cs = cases || [], fl = Array.isArray(fleet) ? fleet : [];
    const dark = new Set([...cs.flatMap((c) => c.homesDark || []), ...fl.flatMap((c) => c.homesDark || [])]);
    const parts = [L(cs.length, 'SIM', 'naive candidate placements where the ASSUMPTION rule operates (one 15-min interval above 200%)'), ' naive candidate placement' + (cs.length === 1 ? '' : 's')];
    if (cs.length) parts.push(' (' + cs.map((c) => `${c.label || homeLabel(S.topology, c.home)} on ${tfName(S.topology, c.tf)}`).join(', ') + ')');
    if (Array.isArray(fleet)) {
      parts.push(' and ', L(fl.length, 'SIM', 'transformers where the rule operates with the existing fleet managed naively'), ' transformer' + (fl.length === 1 ? '' : 's') + ' with the existing fleet managed naively');
      if (fl.length) parts.push(' (' + fl.map((c) => tfName(S.topology, c.tf)).join(', ') + ')');
    }
    parts.push('. Battery-less homes that would go dark: ');
    if (dark.size === 0) parts.push(L(0, 'SIM', 'battery-less homes behind those transformers'), ': every home behind them has a battery and islands');
    else parts.push(L(dark.size, 'SIM', 'battery-less homes behind those transformers'), ` (${[...dark].map((i) => homeLabel(S.topology, i)).join(', ')})`);
    return parts;
  }, ['p2index']],
  insightTfHour: [['p2index'], (S) => { const h = modeHour(get(S, 'p2index.insight.tfPeakHour')); return h === null ? null : L(`${String(h).padStart(2, '0')}:00`, 'SIM', 'mode of the hour of each transformer\'s monthly peak'); }],
  insightPriceHour: [['p2index'], (S) => { const h = modeHour(get(S, 'p2index.insight.priceMaxHour')); return h === null ? null : L(`${String(h).padStart(2, '0')}:00`, 'REAL', 'mode of the hour of each August day\'s max LZ_NORTH price'); }],
  insightVerdict: [['p2index'], (S) => {
    const t = modeHour(get(S, 'p2index.insight.tfPeakHour')), p = modeHour(get(S, 'p2index.insight.priceMaxHour'));
    if (t === null || p === null) return null;
    return t !== p ? 'The two peaks fall at different hours: a market-only dispatcher saves its energy for the price peak and does nothing for the load peak.'
      : 'In this data the two peaks share an hour.';
  }],
  cliffCount: [['p2index'], (S) => withO(get(S, 'p2index.cliffs.count'))],
  cliffEvening: [['p2index'], (S) => withO(get(S, 'p2index.cliffs.evening'))],

  // ---- round 2 -------------------------------------------------------------------------------------------------
  // Adopt #2: Base's real Houston charge block. The meta constant when l2 exports it (docs/contracts.md A.5r); until
  // then the same constant as sim/constants.py (ui/test/p2.test.js pins the two equal), with its source.
  houstonBlock: [['topology'], (S) => {
    const c = constOf(S.p1meta, 'BASE_HOUSTON_CHARGE_BLOCK_MW', { unit: ' MW', digits: 1 });
    return [c || { ...HOUSTON_BLOCK_MW, o: { unit: ' MW', digits: 1 } }, ' within fifteen minutes on ', L(HOUSTON_BLOCK_DATE, 'REAL', HOUSTON_BLOCK_MW.cite)];
  }, ['p1meta']],
  // Adopt #3: what feeder-aware held back at the price-collapse onset (meta.onsetDeferral, l2)
  onsetDeferredKW: [['p1meta'], (S) => withO(get(S, 'p1meta.onsetDeferral.deferredKW'), { unit: ' kW', digits: 0 })],
  onsetNaiveKW: [['p1meta'], (S) => withO(get(S, 'p1meta.onsetDeferral.naiveKW'), { unit: ' kW', digits: 0 })],
  onsetAwareKW: [['p1meta'], (S) => withO(get(S, 'p1meta.onsetDeferral.awareKW'), { unit: ' kW', digits: 0 })],
  // Money tonight, split (meta.money.split, l2): sold at the peak, bought back after the fall, per battery
  soldAware: [['p1meta'], (S) => withO(get(S, 'p1meta.money.split.aware.sold'), { money: true, digits: 0 })],
  boughtAware: [['p1meta'], (S) => withO(get(S, 'p1meta.money.split.aware.bought'), { money: true, digits: 0 })],
  perBatteryAware: [['p1meta'], (S) => withO(get(S, 'p1meta.money.split.aware.perBattery'), { money: true, digits: 2 })],
  awareMoreTonight: [['p1days'], (S) => {
    const d = daysOf(S).find((r) => r.date === (S.p1days.default || DEFAULT_DAY));
    return d ? withO(d.awareMoreUSD, { money: true, digits: 2 }) : null;
  }],
  // The real ERCOT evenings (p1/days/index.json, l2): how the money and the harm vary day to day
  daysCount: [['p1days'], (S) => { const n = daysOf(S).length; return n ? L(n, 'DERIVED', 'real ERCOT evenings simulated on this feeder (p1/days/index.json)') : null; }],
  daysAwareMoreEvery: [['p1days'], (S) => {
    const ds = daysOf(S).filter((r) => isL(r.awareMoreUSD));
    if (!ds.length) return null;
    const more = ds.filter((r) => r.awareMoreUSD.v > 0).length;
    return more === ds.length ? 'on every one of them' : ['on ', L(more, 'DERIVED', 'evenings where feeder-aware earned more than naive'), ' of them'];
  }],
  daysAwareSafe: [['p1days'], (S) => {
    const ds = daysOf(S).filter((r) => isL(r.awareBatteryCaused));
    if (!ds.length) return null;
    const bad = ds.filter((r) => r.awareBatteryCaused.v > 0).length;
    return bad === 0 ? ['with ', L(0, 'SIM', 'battery-caused overloads, feeder-aware, summed over the simulated evenings (OpenDSS)'), ' battery-caused overloads']
      : ['with battery-caused overloads on ', L(bad, 'SIM', 'evenings with a battery-caused overload, feeder-aware'), ' evenings'];
  }],
  daysNaiveBroke: [['p1days'], (S) => {
    const ds = daysOf(S).filter((r) => isL(r.naiveEvents));
    return ds.length ? L(ds.filter((r) => r.naiveEvents.v > 0).length, 'SIM', 'evenings where naive caused a normal-tier event (OpenDSS)') : null;
  }],
  daysBest: [['p1days'], (S) => dayExtreme(S, 1)],
  daysWorst: [['p1days'], (S) => dayExtreme(S, -1)],
  perCoreYear: [['p1cal'], (S) => withO(get(S, 'p1cal.headline.perBattery2026ytd'), { money: true, digits: 0 })],
  top10Share: [['p1cal'], (S) => withO(get(S, 'p1cal.headline.top10Share2026'), { unit: '%', digits: 0 })],
  losingNights: [['p1cal'], (S) => withO(get(S, 'p1cal.headline.losingNights2026'))],
  // Audit R2 H1: the useful-capacity figures OpenDSS measured on each build (index.usefulCapacity.opendss)
  capNaiveCableAt: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.feederHead.naive.overAt'))],
  capNaiveScreen: [['p2index'], (S) => {
    const x = get(S, 'p2index.usefulCapacity.naive');
    return isL(x) ? { ...x, cite: 'screening count (sim.surrogate) of batteries before the first battery-caused event; the count itself is not OpenDSS-checked as safe: OpenDSS refutes it', o: {} } : null;
  }],
  capNaiveOdssCaused: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.opendss.naive.causedNormal'))],
  capNaiveOdssHead: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.opendss.naive.headMaxPct'), { unit: '%', digits: 1 })],
  capAwareOdssCaused: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.opendss.aware.causedNormal'))],
  capAwareOdssHead: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.opendss.aware.headMaxPct'), { unit: '%', digits: 1 })],
  capAwareVmin: [['p2index'], (S) => {
    const x = get(S, 'p2index.usefulCapacity.opendss.aware.vMinPu');
    if (!isL(x)) return null;
    return typeof x.volts === 'number' ? [{ ...x, o: { digits: 4, unit: ' pu' } }, ' (', { v: x.volts, label: x.label, cite: x.cite, o: { digits: 1, unit: ' V' } }, ')'] : [{ ...x, o: { digits: 4, unit: ' pu' } }];
  }],
  // Audit R2 L3: per solve and per step are different numbers (engine.json)
  msPerStep: [['topology'], (S) => { const x = scanEngine(S.engine, /msPerStep|perStep/i); return x ? { ...x, o: { unit: ' ms', digits: 1 } } : null; }, ['engine']],
};

/** Base's Houston charge block (adopt #2, REAL): the same constant as sim/constants.py BASE_HOUSTON_CHARGE_BLOCK_MW
 *  (l0), used until l2 exports it in p1/meta.json constants. ui/test/p2.test.js pins the value to the Python file. */
export const HOUSTON_BLOCK_MW = { v: -45.8, label: 'REAL',
  cite: "Base blog 'Aggregated DERs and the capacity crunch' (Jul 2026): Base's Houston charge block reached -45.8 MW within 15 minutes on 22 Jul 2026 (docs/research-report.md:207-212, 297; sim/constants.py BASE_HOUSTON_CHARGE_BLOCK_MW)" };
export const HOUSTON_BLOCK_DATE = '22 Jul 2026';
const DEFAULT_DAY = '2026-08-23';
function daysOf(S) { return (S.p1days && Array.isArray(S.p1days.days)) ? S.p1days.days : []; }
/** The best (dir 1) or worst (dir -1) simulated evening by feeder-aware money per battery: date, tag, $ per battery. */
function dayExtreme(S, dir) {
  const ds = daysOf(S).filter((r) => r.perBattery && isL(r.perBattery.aware));
  if (ds.length < 2) return null;
  const r = ds.reduce((a, b) => ((b.perBattery.aware.v - a.perBattery.aware.v) * dir > 0 ? b : a));
  return [L(dateText(r.date), 'REAL', 'a real ERCOT evening (LZ_NORTH prices)'), r.tag ? ` (${String(r.tag)})` : '', ', ', { ...r.perBattery.aware, o: { money: true, digits: 2 } }, ' a battery'];
}
const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/** "Sun 23 Aug 2026" from an ISO date; the weekday is computed, never typed. */
export function dateText(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
  if (!m) return String(iso || '');
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return `${WD[d.getUTCDay()]} ${+m[3]} ${MO[+m[2] - 1]} ${m[1]}`;
}

const PLACEHOLDER = /\{\{\s*([^}]+?)\s*\}\}/g;

/** Placeholders in a template: [{raw, name, chip?, cite?}] */
export function placeholders(tpl) {
  const out = [];
  for (const m of String(tpl || '').matchAll(PLACEHOLDER)) {
    const [kind, ...rest] = m[1].split(':');
    if (kind === 'chip') out.push({ raw: m[0], chip: rest[0], cite: rest.slice(1).join(':') || null });
    else out.push({ raw: m[0], name: m[1] });
  }
  return out;
}
/** The template with every placeholder (and optional-clause bracket) removed: what the "no bare digits" test reads. */
export const stripPlaceholders = (tpl) => String(tpl || '').replace(PLACEHOLDER, '').replace(/\[\[|\]\]/g, '');

const OPTIONAL = /\[\[([\s\S]*?)\]\]/g;
/** The optional clauses of a template: [{raw, inner}]. */
export function optionalClauses(tpl) { return [...String(tpl || '').matchAll(OPTIONAL)].map((m) => ({ raw: m[0], inner: m[1] })); }
/** The template with its optional clauses removed: its placeholders must always resolve. */
export const requiredPart = (tpl) => String(tpl || '').replace(OPTIONAL, '');
/** Keep an optional clause (without its brackets) when every fact inside it resolves; drop it whole otherwise. */
export function applyOptional(tpl, S) {
  return String(tpl || '').replace(OPTIONAL, (raw, inner) => (placeholders(inner).every((p) => !p.name || evalFact(p.name, S)) ? inner : ''))
    .replace(/ {2,}/g, ' ').replace(/ ([.,;:])/g, '$1');
}

/** Sources a set of templates needs. */
export function sourcesFor(templates) {
  const need = new Set();
  for (const t of templates) for (const p of placeholders(t)) if (p.name && FACTS[p.name]) for (const s of [...FACTS[p.name][0], ...(FACTS[p.name][2] || [])]) need.add(s);
  return [...need];
}

function sourcePath(key) {
  if (key === 'p1meta') return 'p1/meta.json';
  if (key === 'p2index') return 'p2/index.json';
  if (key === 'engine') return 'engine.json';
  if (key === 'p1days') return 'p1/days/index.json';
  if (key === 'p1cal') return 'p1/days/calendar.json';
  if (key.startsWith('p1:')) return `p1/${key.slice(3)}.json`;
  if (key.startsWith('p2:')) return `p2/${key.slice(3)}.json`;
  return null;
}

/** Load sources: real files only; fixtures only when the page is already a FIXTURE page (its banner shows). */
export async function loadSources(ctx, keys) {
  const S = { topology: ctx.topology };
  await Promise.all(keys.filter((k) => k !== 'topology').map(async (k) => {
    const path = sourcePath(k);
    if (!path) return;
    let d = null;
    try { d = await ctx.data.getOptional(path); } catch (e) { d = null; }
    if (!d && !['engine', 'p1days', 'p1cal'].includes(k) && ctx.data.isFixture && ctx.data.isFixture()) {
      try { d = await ctx.data.getOptional('fixtures/' + path); } catch (e) { d = null; }
    }
    S[k] = d;
  }));
  return S;
}

/** Evaluate a fact; returns parts[] (strings and labelled values) or null. Never throws. */
export function evalFact(name, S) {
  const f = FACTS[name];
  if (!f) return null;
  if (f[0].some((s) => S[s] == null)) return null;
  let r;
  try { r = f[1](S); } catch (e) { return null; }
  if (r === null || r === undefined || r === '') return null;
  return Array.isArray(r) ? r.filter((x) => x !== null && x !== '') : [r];
}

function renderPart(p, fmt, html) {
  if (typeof p === 'string') return html ? esc(p) : p;
  if (isL(p)) return html ? numHTML(fmt, p, p.o || {}) : numText(fmt, p, p.o || {});
  return html ? esc(String(p)) : String(p);
}

/** Resolve a caption template. html=true for the page; false gives "value LABEL" text (tests, docs). */
export function resolveCaption(tpl, S, fmt, { html = true } = {}) {
  return applyOptional(tpl, S).replace(PLACEHOLDER, (raw, inner) => {
    const [kind, ...rest] = inner.trim().split(':');
    if (kind === 'chip') {
      const label = rest[0], cite = rest.slice(1).join(':') || undefined;
      return html ? fmt.chip(label, cite) : `[${label}]`;
    }
    const parts = evalFact(inner.trim(), S);
    if (!parts) return html ? '<span class="beat-na">(not built yet)</span>' : '(not built yet)';
    return parts.map((p) => renderPart(p, fmt, html)).join('');
  });
}

function beatsList(beats) { return Array.isArray(beats) ? beats : ((beats && beats.beats) || []); }
export function beatHref(b) { return `?${b.link}&beat=${encodeURIComponent(b.id)}`; }

/** The caption bar for the current ?beat=<id>, with prev / next. compact (the P1 bar, UX_SPEC_R2 7.2): the title,
 *  prev / next and the beat's one-sentence headline, with the full caption under "Read the full caption". P2 and More
 *  show the headline and the full caption. */
export async function beatBarHTML(ctx, { compact = false } = {}) {
  const beats = beatsList(await ctx.data.loadBeats());
  const i = beats.findIndex((b) => b.id === ctx.link.beat);
  if (i < 0) return '';
  const b = beats[i];
  const S = await loadSources(ctx, sourcesFor([b.caption, b.headline || '']));
  const next = beats[i + 1], prev = beats[i - 1];
  const head = b.headline ? `<div class="beat-headline">${resolveCaption(b.headline, S, ctx.fmt)}</div>` : '';
  const cap = resolveCaption(b.caption, S, ctx.fmt);
  const body = compact && head
    ? `${head}<details class="beat-more"><summary>Read the full caption</summary><div class="beat-cap">${cap}</div></details>`
    : `${head}<div class="beat-cap">${cap}</div>`;
  return `<div class="beat-bar${compact ? ' compact' : ''}" data-beat-id="${esc(b.id)}">
    <div class="beat-h"><span class="beat-t">${esc(b.t0)}–${esc(b.t1)}</span> <b>${esc(b.title)}</b>${b.label ? ctx.fmt.chip(b.label) : ''}
      <span class="beat-nav">${prev ? `<a href="${beatHref(prev)}" title="${esc(prev.title)}">‹ prev</a>` : ''}${next ? `<a href="${beatHref(next)}" title="${esc(next.title)}">next beat ›</a>` : ''}</span></div>
    ${body}</div>`;
}

/** Closed <details> keep their body out of the live DOM until opened (Chrome lays out a closed body, so hidden tags
 *  and numbers counted as "above the fold" and were reachable by screen readers). The HTML string a panel builds still
 *  holds every body (node tests read it); in the browser the body is moved aside and put back on the first open.
 *  bodySel names the body element inside each details (its first match). */
export function lazyDetails(root, detailsSel, bodySel) {
  if (!root || typeof root.querySelectorAll !== 'function') return 0;
  let n = 0;
  for (const d of root.querySelectorAll(detailsSel)) {
    if (d.open || d.dataset.lazy) continue;
    const body = d.querySelector(bodySel);
    if (!body || !body.innerHTML) continue;
    const html = body.innerHTML;
    body.innerHTML = '';
    d.dataset.lazy = '1';
    d.addEventListener('toggle', () => { if (d.open && !body.innerHTML) body.innerHTML = html; });
    n += 1;
  }
  return n;
}

/** For the shell or the P1 panel: put the compact caption bar at the top of the panel when ?beat= is set. */
export async function mountBeatBar(ctx, panelEl) {
  if (!ctx.link.beat) return;
  const el = panelEl || (typeof document !== 'undefined' && document.getElementById('panel'));
  if (!el || el.querySelector('.beat-bar')) return;
  const html = await beatBarHTML(ctx, { compact: ctx.link.view === 'p1' });
  if (html) {
    el.insertAdjacentHTML('afterbegin', html);
    lazyDetails(el, '.beat-bar details.beat-more', '.beat-cap');
  }
}

// ---------------------------------------------------------------------------------------------------------------
// The payers (5.4.6): who pays today, and for what. REAL, sourced; never a price for local relief.
export const PAYERS = [
  { who: 'CoServ', mw: 100, what: 'peak shaving and arbitrage', dispatchPct: 80, cite: 'docs/research-report.md:215-224' },
  { who: 'GVEC', mw: 50, what: 'ERCOT summer four-coincident-peak and arbitrage', cite: 'docs/research-report.md:215-224' },
  { who: 'Austin Energy', mw: 40, what: 'system peak demand and wholesale prices (it dispatches)', cite: 'docs/research-report.md:215-224' },
  { who: 'El Paso Electric', mw: 10, what: 'local capacity constraints: the only local-constraint programme found, and it is outside ERCOT', cite: 'docs/research-report.md:59, 215-224' },
];

/** A labelled money value as HTML, or the "not built yet" marker. */
function moneyHTML(fmt, x, digits = 0) { return isL(x) ? fmt.fmtHTML(x, { money: true, digits }) : '<span class="beat-na">(not built yet)</span>'; }

/** Tonight's money (the P1 evening): sold at the peak, bought back after the fall, net, per branch (meta.money.split,
 *  l2; before it lands, the energy value alone). Audit R2 M5: no monthly benchmark sits beside these per-evening $. */
function moneyCard(ctx, S) {
  const { fmt } = ctx;
  const m = S.p1meta && S.p1meta.money;
  const split = m && m.split;
  const day = S.p1meta && S.p1meta.day ? dateText(S.p1meta.day) : 'the P1 evening';
  const rows = [];
  const maxSold = split ? Math.max(1, ...['naive', 'aware'].map((k) => (split[k] && isL(split[k].sold) ? split[k].sold.v : 0))) : 1;
  for (const k of ['naive', 'aware', 'aware_faults']) {
    const net = m && m.energyValueUSD && m.energyValueUSD[k];
    if (!isL(net)) continue;
    const sp = split && split[k];
    const name = k === 'naive' ? 'naive' : k === 'aware' ? 'feeder-aware' : 'feeder-aware + failures';
    let bars = '';
    if (sp && isL(sp.sold) && isL(sp.bought)) {
      const w = (x) => Math.max(1, Math.round((x / maxSold) * 100));
      bars = `<div class="money-bars" data-tip-html="${esc(`<b>${name}</b><br>sold at the peak ${fmt.fmtHTML(sp.sold, { money: true, digits: 2 })}<br>bought back after the fall ${fmt.fmtHTML(sp.bought, { money: true, digits: 2 })}<br>net ${fmt.fmtHTML(sp.net || net, { money: true, digits: 2 })}${isL(sp.perBattery) ? `, ${fmt.fmtHTML(sp.perBattery, { money: true, digits: 2 })} a battery` : ''}`)}" tabindex="0">`
        + `<span class="mb sold" style="width:${w(sp.sold.v)}%"></span><span class="mb bought" style="width:${w(sp.bought.v)}%"></span></div>`;
    }
    rows.push(`<div class="money-row"><span class="money-name">${esc(name)}</span>${bars}<b class="money-net">${fmt.fmtHTML(net, { money: true, digits: 0 })}</b></div>`);
  }
  const more = evalFact('awareMoreTonight', S);
  const cost = m && isL(m.costOfAwareness) ? m.costOfAwareness : null;
  const safe = m && S.p1meta.summary && S.p1meta.summary.aware && isL(S.p1meta.summary.aware.batteryCausedNormal) ? S.p1meta.summary.aware.batteryCausedNormal : null;
  const moreLine = more ? `<div class="money-more">${svg('turns', { size: 15 })}<span>Feeder-aware earned ${more.map((x) => renderPart(x, fmt, true)).join('')} more than naive tonight${safe ? `, with ${fmt.fmtHTML(safe)} battery-caused overloads` : ''}.</span></div>`
    : cost ? `<div class="money-more"><span>Cost of awareness (naive − feeder-aware; negative means feeder-aware earned more): ${fmt.fmtHTML(cost, { money: true, digits: 2 })}</span></div>` : '';
  const r = m && m.relief;
  const relief = r && isL(r.opportunityUpperUSD)
    ? `<p class="hb-sub">A's local relief on this evening (one home's spike) would have earned at most ${fmt.fmtHTML(r.opportunityUpperUSD, { money: true, digits: 2 })} at the price peak: it is <b>not paid for today</b> ${fmt.chip('ASSUMPTION', 'no sourced price for local transformer relief anywhere in our material (build prompt 5.4.6)')}.</p>` : '';
  const note = m && m.systemCapacityPerMonth && m.systemCapacityPerMonth.note ? '' : '';
  return `<div class="hb-card more-money" data-beat="money"><h3>${svg('money', { size: 18 })} Money tonight, ${esc(day)}</h3>
    <div class="hb-sub">Batteries earn by <span class="k-sold">selling</span> in the evening's priciest intervals and <span class="k-bought">buying back</span> after the price falls. Gross energy value, not Base's profit.</div>
    <div class="money-rows">${rows.join('') || '<span class="beat-na">P1 money not built yet</span>'}</div>
    ${moreLine}${relief}${note}</div>`;
}

/** The real ERCOT evenings (p1/days/index.json + calendar.json, l2): how Base earns at the evening peak day to day,
 *  and what each dispatch does to the street that night (RZ ask 3). Every value from the index, labelled. */
function daysCard(ctx, S) {
  const { fmt } = ctx;
  const idx = S.p1days;
  const days = idx && Array.isArray(idx.days) ? idx.days : [];
  if (!days.length) return `<div class="hb-card more-days"><h3>${svg('calendar', { size: 18 })} Real Texas evenings</h3><p class="hb-sub"><span class="beat-na">The history days are not built yet</span> (<code>p1/days/index.json</code>, sim.history).</p></div>`;
  const spk = idx.series && idx.series.sparkline && LABELS.includes(idx.series.sparkline.label) ? idx.series.sparkline.label : null;
  const maxPB = Math.max(0.01, ...days.map((d) => (d.perBattery && isL(d.perBattery.aware) ? Math.abs(d.perBattery.aware.v) : 0)));
  const rows = [...days].sort((a, b) => String(a.date).localeCompare(String(b.date))).map((d) => {
    const pb = d.perBattery && d.perBattery.aware, pn = d.perBattery && d.perBattery.naive;
    const w = isL(pb) ? Math.max(2, Math.round(Math.abs(pb.v) / maxPB * 100)) : 0;
    const nm = d.naiveMax;
    const nmTip = isL(nm) ? `<b>Naive, the worst transformer</b><br>${fmt.fmtHTML(nm, { unit: '%', digits: 1 })}${nm.tf != null ? ` on ${esc(typeof nm.tf === 'number' ? `T-${nm.tf}` : nm.tf)}` : ''}${nm.t ? ` at ${esc(nm.t)}` : ''}${isL(d.naiveEvents) ? `<br>${fmt.fmtHTML(d.naiveEvents)} battery-caused normal-tier events` : ''}` : '';
    const ab = d.awareBatteryCaused;
    const peakTip = isL(d.peak) ? `<b>ERCOT LZ_NORTH, 16:00 to 04:00</b><br>evening peak ${fmt.fmtHTML(d.peak, { digits: 2, unit: ' $/MWh' })}${d.peak.t ? ` at ${esc(d.peak.t)}` : ''}` : '';
    const href = ctx.href({ view: 'p1', date: d.date, branch: 'aware', t: d.peak && d.peak.t ? d.peak.t : null, combo: null, home: null, n: null });
    return `<a class="day-row" href="${href}" data-date="${esc(d.date)}">
      <span class="day-d"><b>${esc(dateText(d.date))}</b>${fmt.chip('REAL', 'a real ERCOT evening: LZ_NORTH prices for this date; the load is the 2018 SMART-DS weather year on the same calendar date (ASSUMPTION)')}<span class="day-tag">${esc(d.tag || '')}</span></span>
      <span class="day-spark"${peakTip ? ` data-tip-html="${esc(peakTip)}"` : ''}>${sparkSVG(d.sparkline)}${spk ? fmt.chip(spk, 'ERCOT RTM SPP LZ_NORTH, 15-min, 16:00 to 04:00') : ''}</span>
      <span class="day-money${isL(pb) && pb.v < 0 ? ' lose' : ''}" data-tip-html="${esc(`<b>Money per battery tonight</b> (gross, not Base's profit)<br>feeder-aware ${moneyHTML(fmt, pb, 2)}<br>naive ${moneyHTML(fmt, pn, 2)}${isL(d.awareMoreUSD) ? `<br>feeder-aware earned ${fmt.fmtHTML(d.awareMoreUSD, { money: true, digits: 2 })} more (fleet)` : ''}`)}"><span class="day-bar" style="width:${w}%"></span><b>${moneyHTML(fmt, pb, 2)}</b></span>
      <span class="day-naive" data-tip-html="${esc(nmTip)}">${isL(nm) ? svg('meter', { size: 22, pct: nm.v, tier: nm.tier ?? 4 }) : ''}</span>
      <span class="day-aware" data-tip="Feeder-aware: battery-caused overloads that evening (OpenDSS)">${isL(ab) ? `${svg(ab.v === 0 ? 'check' : 'warn', { size: 16 })}${fmt.fmtHTML(ab)}` : ''}</span></a>`;
  }).join('');
  const f = (name) => { const p = evalFact(name, S); return p ? p.map((x) => renderPart(x, fmt, true)).join('') : null; };
  const best = f('daysBest'), worst = f('daysWorst'), every = f('daysAwareMoreEvery'), safe = f('daysAwareSafe'), broke = f('daysNaiveBroke'), n = f('daysCount');
  const lines = [];
  if (best && worst) lines.push(`${svg('money', { size: 15 })}<span>The money is lumpy: ${best} on the best evening, ${worst} on the worst.</span>`);
  if (every && safe) lines.push(`${svg('check', { size: 15 })}<span>Feeder-aware earned more than naive ${every}, ${safe}.</span>`);
  if (broke && n) lines.push(`${svg('warn', { size: 15 })}<span>Naive caused a transformer overload on ${broke} of ${n} evenings, even on a night that lost money.</span>`);
  const cal = S.p1cal ? calendarStripHTML(S.p1cal, ctx.link.date || DEFAULT_DAY) : '';
  return `<div class="hb-card more-days" data-beat="days"><h3>${svg('calendar', { size: 18 })} Real Texas evenings: where the money is, and what it costs the street</h3>
    <div class="day-head"><span></span><span>price, 16:00 to 04:00</span><span>per battery, feeder-aware</span><span>naive</span><span>aware</span></div>
    <div class="day-rows">${rows}</div>
    ${lines.length ? `<div class="day-lines">${lines.map((l) => `<div>${l}</div>`).join('')}</div>` : ''}
    <p class="hb-sub">Why it matters for Base: the money comes from the evening price spike and the fall after it, and that fall is when a whole fleet charging at once overloads this street's transformers. The lines above compare the two ways of charging on each real evening; where feeder-aware shows no battery-caused overload, Base keeps the money and gains a claim it can take to the wires company. Click an evening to replay it.</p>
    ${cal}</div>`;
}

/** 48 prices -> a small sparkline (REAL; the tag sits beside it). Pure string. */
function sparkSVG(values, w = 88, h = 18) {
  const v = (values || []).filter((x) => typeof x === 'number' && Number.isFinite(x));
  if (v.length < 2) return '';
  const lo = Math.min(0, ...v), hi = Math.max(...v), span = hi - lo || 1;
  const pts = v.map((x, i) => `${(i * (w - 2) / (v.length - 1) + 1).toFixed(1)},${(h - 1 - (x - lo) * (h - 2) / span).toFixed(1)}`).join(' ');
  return `<svg class="day-sparksvg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>`;
}

/** Who pays today, and a monthly yardstick (audit R2 M5): the $3.12 figure is a grid-scale storage REVENUE benchmark
 *  (Modo, Apr 2026) that already includes arbitrage, not a capacity payment (ERCOT pays none). It sits in its own card,
 *  never beside a per-evening dollar. */
function payersCard(ctx, S) {
  const { fmt } = ctx;
  const m = S.p1meta && S.p1meta.money;
  const sc = m && m.systemCapacityPerMonth && m.systemCapacityPerMonth.aware;
  const f = (name) => { const p = evalFact(name, S); return p ? p.map((x) => renderPart(x, fmt, true)).join('') : '<span class="beat-na">(not built yet)</span>'; };
  const band = sc && isL(sc.fleetKW) && isL(sc.low) && isL(sc.high)
    ? `<p class="hb-sub"><b>A monthly yardstick, not tonight's money.</b> Feeder-aware, the fleet delivers ${fmt.fmtHTML(sc.fleetKW, { unit: ' kW', digits: 0 })} at the price peak. Priced at a grid-scale storage revenue benchmark (Modo, Apr 2026, which already includes arbitrage) of ${f('capacityLow')} to an implied ${f('capacityHigh')} per kW-month, that is ${fmt.fmtHTML(sc.low, { money: true, digits: 0 })} to ${fmt.fmtHTML(sc.high, { money: true, digits: 0 })} a month. It overlaps the energy value above, so never add the two. ERCOT pays no capacity; this is not a capacity payment.</p>` : '';
  return `<div class="hb-card more-payers-card"><h3>${svg('house', { size: 18 })} Who pays today, and for what ${fmt.chip('REAL', 'docs/research-report.md:59, 215-224')}</h3>
    <ul class="more-payers">${PAYERS.map((p) => `<li>${esc(p.who)} (${fmt.fmtHTML({ v: p.mw, label: 'REAL', cite: p.cite }, { unit: ' MW' })}${p.dispatchPct ? `, ${fmt.fmtHTML({ v: p.dispatchPct, label: 'REAL', cite: p.cite }, { unit: '% dispatch' })}` : ''}): ${esc(p.what)}</li>`).join('')}
      <li>Base's own "distribution grid support" offering: no public price ${fmt.chip('REAL', 'docs/headroom/research_notes/base_power_product_and_system.md:388')}</li></ul>
    <p class="hb-sub"><b>Local transformer relief and upgrade deferral</b> have no sourced price anywhere in our material: an opportunity for Base and the wires company, not revenue ${fmt.chip('ASSUMPTION', 'build prompt 5.4.6')}.</p>
    ${band}</div>`;
}

/** The unit of an engine.json number, read from its key and cite (judge R1 F9: the unit was only in the chip's title).
 *  allocate.<n>: "microseconds per stateless allocate() call" -> "µs per call"; ms*, *Seconds; counts and the load
 *  average have none. Returns {name, unit}: the row name says what the number is. */
export function engineUnit(path, v) {
  const cite = String((v && v.cite) || '');
  const keys = path.split(' · ');
  const last = keys[keys.length - 1];
  if (/^microseconds per\b/i.test(cite)) {
    const n = /^\d+$/.test(last) ? Number(last).toLocaleString('en-US') : null;
    return { name: `${keys[0]}()${n ? `, ${n} batteries` : ''}`, unit: ' µs per call' };
  }
  if (/^ms/i.test(last) || /\bms per\b/i.test(cite)) return { name: path, unit: ' ms' };
  if (/seconds$/i.test(last) || /\bwall time\b|\bseconds\b/i.test(cite)) return { name: path, unit: ' s' };
  return { name: path, unit: '' };
}

/** The machine the timings were measured on (audit R2 L4): engine.json sources.machine (l2, round 2) or the old
 *  loadAvg row, as a caption, never as a result row. */
export function machineNote(eng) {
  const m = eng && eng.sources && eng.sources.machine;
  if (m && m.text) return String(m.text);
  const la = eng && eng.loadAvg;
  return isL(la) && typeof la.v === 'number' ? `timings measured on a shared machine (1-minute load average ${la.v} while measuring); not a benchmark` : null;
}

function engineCard(ctx, S) {
  const { fmt } = ctx;
  const rows = [];
  const walk = (o, path) => {
    for (const [k, v] of Object.entries(o || {})) {
      const p = path ? `${path} · ${k}` : k;
      if (/^loadAvg$/i.test(k)) continue;           // the machine's load is a caption, not a result (audit R2 L4)
      if (isL(v) && typeof v.v === 'number') {
        const u = engineUnit(p, v);
        rows.push(`<tr><td>${esc(u.name)}</td><td class="n">${fmt.fmtHTML(v, { digits: v.v < 10 ? 2 : v.v < 100 ? 1 : 0, unit: u.unit })}</td></tr>`);
      } else if (v && typeof v === 'object' && !Array.isArray(v) && !['constants', 'sources', 'series', 'inputs'].includes(k)) walk(v, p);
    }
  };
  if (S.engine) walk(S.engine, '');
  const solve = evalFact('msPerSolve', S);
  const mn = machineNote(S.engine);
  return `<div class="hb-card" data-beat="plug-in"><h3>Performance, as measured</h3>
    ${rows.length ? `<table class="p2-rank">${rows.slice(0, 12).join('')}</table>` : `<p class="hb-sub">${solve ? `One OpenDSS solve: ${solve.map((x) => renderPart(x, fmt, true)).join('')}.` : '<span class="beat-na">engine.json not built yet</span>'}</p>`}
    <p class="hb-sub">${mn ? `${esc(mn.charAt(0).toUpperCase() + mn.slice(1))}. ` : ''}A solve is one OpenDSS power flow; a step also sets every load and battery and reads the result. All static: the browser replays committed JSON; no server, no network at view time.</p></div>`;
}

function plugInCard(ctx, S) {
  const cv = evalFact('controllerView', S);
  return `<div class="hb-card" data-beat="plug-in"><h3>How Base plugs it in tomorrow</h3>
    <ol class="more-steps">
      <li><b>Where the next battery goes:</b> <code>data/out/siting-2026-08.csv</code> sits beside the install queue. Base still schedules installs by demand; the file adds the grid lens.</li>
      <li><b>Where to charge:</b> <code>allocate()</code> sits behind the zone base point and splits it by transformer headroom, deterministically, with no model in the loop.</li>
      <li><b>What it needs to see:</b> ${cv ? cv.map((x) => renderPart(x, ctx.fmt, true)).join('') : 'total transformer load'}, which needs a utility meter-to-transformer map. On street A–D every home is a member, so member meters are enough there.</li>
      <li><b>Devices:</b> commands carry a sequence number and an expiry; a silent unit goes stale, then idles with backup armed.</li>
    </ol><p class="hb-sub">See <code>docs/how-base-plugs-in.md</code>.</p></div>`;
}

const STORIES = [
  ['Heat wave', 'Prototype story: a scripted heat wave on the same feeder.'],
  ['Rebound', 'Prototype story: the price rebound, even split vs feeder-aware. Its voltage sag is an artefact of the power-factor setting below.'],
  ['Covert channel + quarantine', 'Prototype story: a fictional adversary signals through battery setpoints; the detector quarantines it. SIM, fictional. The detector uses a privileged voltage baseline and is keyed to a fixed square wave, so a channel carrying real bits would mostly pass it.'],
  ['Siting board', "Prototype's next-battery board (its own score; see P2 for tonight's month what-if)."],
];
/** Adopt #5 (TEAMMATES_REVIEW, RZ's list): honest caveats on the teammate cards, in OUR copy only; their folders are
 *  untouched. Numbers are facts about their code, read and re-run by our review, each with its source. */
const PROTO_CAVEAT = (fmt) => `Caveats from our review: its battery loads run at ${fmt.fmtHTML({ v: 0.88, label: 'REAL', cite: "read from the prototype's battery() (it writes kW only, so OpenDSS applies pf 0.88); overnight/REVIEW-connor-proto.md W1" }, { digits: 2 })} power factor, so its voltage sag and trade-off figures are artefacts (at unity power factor the naive rebound shows no voltage violation); its detector has a privileged voltage baseline and is keyed to a fixed ${fmt.fmtHTML({ v: 350, label: 'REAL', cite: 'build_replays.py:69, the fixed alternating attack wave; overnight/REVIEW-connor-proto.md W3' }, { unit: ' W', digits: 0 })} alternating wave. Connor's newer simulator (simulators/connor) fixes the power factor.`;
const FOURHOME_CAVEAT = (fmt) => `Caveat from our review: its frequency figure uses the retired ${fmt.fmtHTML({ v: '3–5 mHz', label: 'DERIVED', cite: 'four_home_constants.py:73-74 F_SENS 0.075/0.12 mHz/MW x a 40 MW swing; the team corrected it to 3-17 mHz on 26 Sep (docs/research-report.md:308-318)' })} band for a thousand-battery swing, and its naive branch is not labelled an assumption.`;

async function chaosCard(ctx) {
  const doc = await ctx.data.getOptional('p1/chaos.json').catch(() => null);
  if (!doc) return '';
  const { fmt } = ctx;
  const runs = doc.runs || [];
  const counts = Array.isArray(runs) ? runs.map((r) => (r && (isL(r.batteryCaused) ? r.batteryCaused.v : typeof r.batteryCaused === 'number' ? r.batteryCaused : 0)) || 0) : [];
  const head = Object.entries(doc).filter(([, v]) => isL(v)).map(([k, v]) => `<div>${esc(k)}: ${fmt.fmtHTML(v)}</div>`).join('');
  return `<div class="hb-card"><h3>Chaos sweep</h3><div class="hb-sub">The P1 evening, seeded failures; battery-caused violations only.</div>${head}${counts.length ? `<div class="hb-sub">Runs: ${fmt.fmtHTML({ v: counts.length, label: 'SIM' })}; with any battery-caused violation: ${fmt.fmtHTML({ v: counts.filter((c) => c > 0).length, label: 'SIM' })}</div>` : ''}</div>`;
}

// ---------------------------------------------------------------------------------------------------------------
// P3: the ERCOT console (build prompt 5.7.3). Four REAL system cards for one recorded day, computed at view time from a
// byte-for-byte snapshot of site/ems (ui/data/ems/index.json lists the sha256s). site/ems/SYNTHESIS.md picks the
// panels: frequency, PRC reserves, net load and its ramp, SCED congestion. Each number carries the status the EMS
// bundle gives its field (real5.fields; UNVERIFIED maps to ASSUMPTION with "unverified" in the cite).
const RESEARCH_FREQ_CITE = 'docs/research-report.md:308-318: 0.075-0.12 mHz per MW from two recorded events (NERC Odessa 2021; ERCOT NP12-261-M, 2026-08-07), applied to the 411 MW full swing; includes the dip, so it reads above the settling shift';
const EMS_LABEL = (st) => (/^REAL/.test(String(st || '')) ? 'REAL' : /^DERIVED/.test(String(st || '')) ? 'DERIVED' : /^SIM/.test(String(st || '')) ? 'SIM' : 'ASSUMPTION');

/** argmin/argmax over a numeric array (nulls skipped): {i, v} or null. */
function extreme(a, dir) {
  let bi = -1;
  (a || []).forEach((v, i) => { if (typeof v === 'number' && Number.isFinite(v) && (bi < 0 || (dir > 0 ? v > a[bi] : v < a[bi]))) bi = i; });
  return bi < 0 ? null : { i: bi, v: a[bi] };
}

/**
 * The console cards as data (pure; ui/test/p2.test.js reads it): [{key, title, label, stats: [{name, x, o}], chart, text}].
 * synth = synth-console.json, freq = freq-series.json (constants and 10-s stats), manifest = ems/index.json.
 * Null when the snapshot is missing.
 */
export function emsModel(synth, freq, manifest) {
  const r = synth && synth.real5;
  if (!r || !Array.isArray(r.t)) return null;
  const F = r.fields || {};
  const lab = (k) => EMS_LABEL(F[k] && F[k].status);
  const cite = (k, extra) => `site/ems synth-console.json real5.${k} (${(F[k] && F[k].from) || 'EMS bundle'})${extra ? `; ${extra}` : ''}`;
  const at = (k, e, o, extra) => (e ? [{ v: e.v, label: lab(k), cite: cite(k, extra), o }, { v: r.t[e.i], label: lab(k), cite: `5-min bin start, ${r.tz || 'CDT'}` }] : null);
  const ticks = r.t.map((t, i) => (/^(00|06|12|18):00$/.test(t) ? { i, text: t } : null)).filter(Boolean);
  const C = (freq && freq.constants) || {};
  const fsrc = 'site/ems freq-series.json constants (ERCOT Nodal Operating Guide; see its sources)';
  const sc = synth.scale || {};
  const scLab = EMS_LABEL(sc.status);
  const cards = [];

  // 1. Frequency
  const fs = freq && freq.stats && freq.stats.frequency;
  const fLo = extreme(r.fMinHz, -1), fHi = extreme(r.fMaxHz, 1);
  const f = { key: 'frequency', title: 'Frequency', label: lab('fMinHz'), stats: [] };
  if (fs && typeof fs.min_hz === 'number') {
    f.stats.push({ name: 'lowest ten-second sample', parts: [{ v: fs.min_hz, label: 'REAL', cite: 'freq-series.json stats.frequency.min_hz, 8,289 ten-second samples', o: { unit: ' Hz', digits: 3 } }, ' at ', { v: fs.min_time_cdt, label: 'REAL', cite: 'CDT' }] });
    f.stats.push({ name: 'highest ten-second sample', parts: [{ v: fs.max_hz, label: 'REAL', cite: 'freq-series.json stats.frequency.max_hz', o: { unit: ' Hz', digits: 3 } }, ' at ', { v: fs.max_time_cdt, label: 'REAL', cite: 'CDT' }] });
    if (typeof fs.sigma_mhz === 'number') f.stats.push({ name: 'day\'s wander (σ)', parts: [{ v: fs.sigma_mhz, label: 'DERIVED', cite: 'freq-series.json stats.frequency.sigma_mhz', o: { unit: ' mHz', digits: 1 } }] });
    if (typeof fs.clock_minutes_avg_below_59_91 === 'number') f.stats.push({ name: 'clock minutes below the EEA frequency trigger', parts: [{ v: fs.clock_minutes_avg_below_59_91, label: 'DERIVED', cite: 'freq-series.json stats.frequency.clock_minutes_avg_below_59_91' }] });
  } else if (fLo && fHi) {
    f.stats.push({ name: 'lowest (five-minute bins)', parts: at('fMinHz', fLo, { unit: ' Hz', digits: 3 }) }, { name: 'highest', parts: at('fMaxHz', fHi, { unit: ' Hz', digits: 3 }) });
  }
  const f0 = typeof C.f0_hz === 'number' ? C.f0_hz : null, db = typeof C.governor_deadband_hz === 'number' ? C.governor_deadband_hz : null;
  // y range from the data (and the deadband when known), so the band is visible around nominal
  const fyLo = Math.min(...[fLo && fLo.v, f0 !== null && db !== null ? f0 - db : null].filter((x) => typeof x === 'number'));
  const fyHi = Math.max(...[fHi && fHi.v, f0 !== null && db !== null ? f0 + db : null].filter((x) => typeof x === 'number'));
  f.chart = { series: [{ name: 'min', values: r.fMinHz, cls: 's-without' }, { name: 'max', values: r.fMaxHz, cls: 's-with' }], label: lab('fMinHz'),
    ...(Number.isFinite(fyLo) && Number.isFinite(fyHi) ? { yMin: fyLo - (fyHi - fyLo) * 0.1, yMax: fyHi + (fyHi - fyLo) * 0.1 } : {}),
    refs: f0 !== null && db !== null ? [{ y: f0 + db, text: 'deadband', cls: 'r-amber' }, { y: f0 - db, text: '', cls: 'r-amber' }] : [], xTicks: ticks, height: 90,
    caption: `Frequency, min and max per 5-min bin, ${r.day}${db !== null ? '; the governor deadband dashed' : ''}`, title: 'ercot frequency' };
  if (Array.isArray(sc.fleetNameplate_mHz) && sc.inputs && sc.inputs.fleetNameplateMW) {
    const [lo, mid, hi] = sc.fleetNameplate_mHz;
    // Audit R2 L11: this is a SETTLING shift (ERCOT's measured beta), not the nadir. The research report's event-rate
    // band (0.075-0.12 mHz per MW, docs/research-report.md:308-318) reads higher; both are shown, neither is a nadir.
    const full = Array.isArray(sc.fleetFullSwing411MW_mHz) ? sc.fleetFullSwing411MW_mHz : null;
    f.thread = ['Swinging Base\'s whole fleet (', { v: sc.inputs.fleetNameplateMW.value, label: 'REAL', cite: `Base-published; ${sc.inputs.fleetNameplateMW.source || ''}`, o: { unit: ' MW', digits: 1 } },
      ') one way would shift where frequency settles by about ', { v: lo, label: scLab, cite: sc.formula || 'synth scale', o: { digits: 1 } }, ' to ', { v: hi, label: scLab, cite: sc.formula || 'synth scale', o: { unit: ' mHz', digits: 1 } },
      ' (median ', { v: mid, label: scLab, cite: sc.formula || 'synth scale', o: { unit: ' mHz', digits: 1 } }, '). That is the settling shift from ERCOT\'s measured response, not the lowest point (nadir) of a fast swing, which dips further',
      ...(full ? ['; the full charge-to-discharge swing doubles the MW (', { v: full[0], label: scLab, cite: `${sc.formula || 'synth scale'}; 2 x the fleet nameplate`, o: { digits: 0 } }, ' to ', { v: full[2], label: scLab, cite: `${sc.formula || 'synth scale'}; 2 x the fleet nameplate`, o: { unit: ' mHz', digits: 0 } }, ')'] : []),
      '. Event-based rates from Odessa and a 2026 ERCOT event read higher, about ', { v: 30, label: 'DERIVED', cite: RESEARCH_FREQ_CITE, o: { digits: 0 } }, ' to ', { v: 50, label: 'DERIVED', cite: RESEARCH_FREQ_CITE, o: { unit: ' mHz', digits: 0 } },
      ' for that full swing. Either way it sits near the day\'s normal wander: context, not a frequency actor.'];
  }
  cards.push(f);

  // 2. PRC reserves
  const pLo = extreme(r.prcMinMW, -1);
  const T = C.prc_thresholds_mw || {};
  const p = { key: 'prc', title: 'Physical responsive capability (reserves)', label: lab('prcMinMW'), stats: [] };
  // The lowest PRC sample and its own time (audit R2 L10: the 5-min bin start 07:40 is not when it happened, 07:44:52 is)
  const ps = freq && freq.stats && freq.stats.prc;
  if (ps && typeof ps.min_mw === 'number' && ps.min_time_cdt) {
    p.stats.push({ name: 'lowest PRC sample', parts: [{ v: ps.min_mw, label: 'REAL', cite: `freq-series.json stats.prc.min_mw (ERCOT daily PRC dashboard, ${(freq.stats.data_quality && freq.stats.data_quality.daily_prc && freq.stats.data_quality.daily_prc.points) || 'every'} samples)`, o: { unit: ' MW', digits: 0 } }, ' at ', { v: ps.min_time_cdt, label: 'REAL', cite: 'the sample time, CDT (stats.prc.min_time_cdt)' }] });
  } else if (pLo) p.stats.push({ name: 'lowest PRC (5-min bin start)', parts: at('prcMinMW', pLo, { unit: ' MW', digits: 0 }) });
  if (typeof T.watch === 'number') p.stats.push({ name: 'watch trigger', parts: [{ v: T.watch, label: 'REAL', cite: fsrc, o: { unit: ' MW', digits: 0 } }] });
  if (pLo && typeof T.watch === 'number') p.verdict = pLo.v >= T.watch ? 'PRC stayed above the watch trigger all day.' : 'PRC fell below the watch trigger.';
  p.chart = { series: [{ name: 'PRC min', values: r.prcMinMW, cls: 's-with' }], label: lab('prcMinMW'), yMin: 0,
    refs: ['watch', 'eea1'].filter((k) => typeof T[k] === 'number').map((k) => ({ y: T[k], text: k === 'watch' ? 'watch' : 'EEA1', cls: 'r-normal' })),
    xTicks: ticks, height: 90, unit: '', caption: `PRC, lowest per 5-min bin (MW), ${r.day}`, title: 'ercot prc' };
  cards.push(p);

  // 3. Net load and its ramp
  const nHi = extreme(r.netLoadMW, 1);
  const rAbs = (r.ramp15MWperMin || []).map((v) => (typeof v === 'number' ? Math.abs(v) : null));
  const rHi = extreme(rAbs, 1);
  const n = { key: 'netload', title: 'Net load and its ramp', label: lab('netLoadMW'), stats: [] };
  if (nHi) n.stats.push({ name: 'net-load peak (demand − wind − solar)', parts: at('netLoadMW', nHi, { unit: ' MW', digits: 0 }) });
  if (rHi) n.stats.push({ name: 'steepest quarter-hour ramp', parts: at('ramp15MWperMin', { i: rHi.i, v: r.ramp15MWperMin[rHi.i] }, { unit: ' MW/min', digits: 1, signed: true }) });
  n.chart = { series: [{ name: 'net load', values: r.netLoadMW, cls: 's-with' }, ...(Array.isArray(r.demandMW) ? [{ name: 'demand', values: r.demandMW, cls: 's-without' }] : [])],
    label: lab('netLoadMW'), xTicks: ticks, height: 90,
    ...(extreme(r.netLoadMW, -1) ? { yMin: extreme(r.netLoadMW, -1).v * 0.9 } : {}), caption: `Net load (accent) and demand (grey), MW, ${r.day}`, title: 'ercot net load' };
  if (typeof sc.fleetShareOfNetLoadPeakPct === 'number') {
    n.thread = ['Base\'s whole fleet is ', { v: sc.fleetShareOfNetLoadPeakPct, label: scLab, cite: 'synth scale.fleetShareOfNetLoadPeakPct', o: { unit: '%', digits: 2 } }, ' of the net-load peak',
      ...(typeof sc.fleetSecondsOfSteepestRamp15 === 'number' ? [' and covers ', { v: sc.fleetSecondsOfSteepestRamp15, label: scLab, cite: 'synth scale.fleetSecondsOfSteepestRamp15', o: { unit: ' s', digits: 0 } }, ' of the steepest ramp'] : []), '.'];
  }
  cards.push(n);

  // 4. Congestion (SCED) and the zone price
  const bHi = extreme(r.scedBinding, 1);
  const viol = (r.scedViolated || []).filter((v) => typeof v === 'number' && v > 0).length;
  const lzHi = extreme(r.lzNorthUSD, 1);
  const g = { key: 'congestion', title: 'Congestion: binding transmission constraints', label: lab('scedBinding'), stats: [] };
  if (bHi) g.stats.push({ name: 'most binding constraints in one bin', parts: at('scedBinding', bHi, { digits: 0 }) });
  if (Array.isArray(r.scedViolated)) g.stats.push({ name: 'five-minute bins with a violated constraint', parts: [{ v: viol, label: lab('scedViolated'), cite: cite('scedViolated') }] });
  if (lzHi) g.stats.push({ name: 'highest LZ_NORTH real-time price', parts: at('lzNorthUSD', lzHi, { money: true, digits: 2 }) });
  g.chart = { series: [{ name: 'binding', values: r.scedBinding, cls: 's-with' }], label: lab('scedBinding'), yMin: 0, xTicks: ticks, height: 90,
    caption: `SCED binding constraints per 5-min bin, ${r.day}`, title: 'ercot sced' };
  g.thread = ['These are transmission constraints. ERCOT dispatches one number per load zone and checks no feeder or service transformer: that gap is what P1 and P2 fill.'];
  cards.push(g);

  const ends = r.coverageEnds || {};
  const snap = manifest && Array.isArray(manifest.files) ? manifest.files.map((x) => `${x.name} sha256 ${String(x.sha256 || '').slice(0, 12)}…`).join(', ') : null;
  return { day: r.day, tz: r.tz, cards,
    caveat: `Recorded ${r.day}, not live; the data ends at ${Object.entries(ends).map(([k, v]) => `${k} ${v}`).join(', ')}. A different day from P1 (the 23 Aug replay).`,
    source: `site/ems (snapshot: ${snap || 'no manifest'})` };
}

function partsHTML(parts, fmt) {
  return (parts || []).map((x) => (typeof x === 'string' ? esc(x) : isL(x) ? numHTML(fmt, x, x.o || {}) : esc(String(x)))).join('');
}

async function emsCards(ctx) {
  const [manifest, synth, freq] = await Promise.all(['ems/index.json', 'ems/synth-console.json', 'ems/freq-series.json']
    .map((p) => ctx.data.getOptional(p).catch(() => null)));
  const m = emsModel(synth, freq, manifest);
  if (!m) return '';
  const { fmt } = ctx;
  const cards = m.cards.map((c) => `<div class="hb-card ems" data-ems="${esc(c.key)}"><h3>${esc(c.title)} ${fmt.chip(c.label)}</h3>
    ${c.stats.filter((s) => s.parts).map((s) => `<div class="ems-stat"><span>${esc(s.name)}</span><b>${partsHTML(s.parts, fmt)}</b></div>`).join('')}
    ${c.verdict ? `<div class="hb-sub">${esc(c.verdict)} ${fmt.chip('DERIVED', 'lowest PRC vs the watch trigger')}</div>` : ''}
    ${c.chart ? chartHTML('line', c.chart) : ''}
    ${c.thread ? `<div class="hb-sub ems-thread">${partsHTML(c.thread, fmt)}</div>` : ''}</div>`).join('');
  return `<h2 class="more-h" data-beat="ercot">ERCOT console: the system day, ${esc(m.day)} ${fmt.chip('REAL', 'ERCOT public dashboards and MIS reports, recorded by the EMS workflow (site/ems)')}</h2>
    <div class="hb-sub more-sub">${esc(m.caveat)} Source: <code>${esc(m.source)}</code>; panels picked by <code>site/ems/SYNTHESIS.md</code>.</div>
    <div class="hb-cards ems-cards">${cards}</div>`;
}

export async function mount(el, ctx) {
  const { sceneModel, scene, topology, fmt } = ctx;
  scene.update(sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame: null, view: 'more', theme: ctx.theme }));
  const beats = beatsList(await ctx.data.loadBeats());
  const S = await loadSources(ctx, [...new Set([...sourcesFor(beats.flatMap((b) => [b.caption, b.headline || ''])), 'p1meta', 'engine', 'p1days', 'p1cal'])]);
  const beatBar = ctx.link.beat ? await beatBarHTML(ctx) : '';
  const beatRows = beats.map((b) => `<li class="beat-item${b.id === ctx.link.beat ? ' on' : ''}">
      <div class="beat-h"><span class="beat-t">${esc(b.t0)}–${esc(b.t1)}</span> <a href="${beatHref(b)}"><b>${esc(b.title)}</b></a>${b.label ? fmt.chip(b.label) : ''}</div>
      ${b.headline ? `<div class="beat-headline">${resolveCaption(b.headline, S, fmt)}</div>` : ''}
      <details class="beat-more"${b.id === ctx.link.beat ? ' open' : ''}><summary>Caption</summary><div class="beat-cap">${resolveCaption(b.caption, S, fmt)}</div></details></li>`).join('');
  el.innerHTML = `<div class="more-wrap">
    ${beatBar}
    <div class="hb-cards more-top">
      <div class="hb-card more-beats"><h3>The five-minute video, beat by beat</h3>
        <div class="hb-sub">Each beat is one deep link; every number in a caption is read from the committed data, with its label. A beat whose data is not built says so.</div>
        <ol class="beat-list">${beatRows || '<li><span class="beat-na">beats.json not built yet</span></li>'}</ol></div>
      <div class="more-col">${moneyCard(ctx, S)}${payersCard(ctx, S)}</div>
      ${daysCard(ctx, S)}
    </div>
    <div class="hb-cards more-mid">${plugInCard(ctx, S)}${engineCard(ctx, S)}</div>
    <h2 class="more-h">Everything that already worked, unchanged</h2>
    <div class="hb-cards">
      ${STORIES.map(([t, d]) => `<div class="hb-card"><h3><a href="../demos/grid-stories/ui/dist/">${esc(t)}</a></h3><div class="hb-sub">${esc(d)} Pick it in the prototype's story menu. Connor's prototype, unchanged; its prices and loads are scripted.</div></div>`).join('')}
      <div class="hb-card more-caveat"><h3>${svg('info', { size: 16 })} Before you quote the prototype</h3><div class="hb-sub">${PROTO_CAVEAT(fmt)}</div></div>
      <div class="hb-card"><h3><a href="../four-home-simulation/four-home.html">Four-home simulation</a></h3><div class="hb-sub">Michael's four-home model on real prices, unchanged. ${FOURHOME_CAVEAT(fmt)}</div></div>
      ${await chaosCard(ctx)}
    </div>
    ${await emsCards(ctx)}</div>`;
  lazyDetails(el, 'details.beat-more', '.beat-cap');
  // the money calendar's simulated evenings open on P1 (the same link as the evening rows)
  if (typeof el.querySelectorAll === 'function') {
    for (const b of el.querySelectorAll('.more-days .hb-cal-cell.sim[data-date]')) {
      b.addEventListener('click', () => ctx.go({ view: 'p1', date: b.dataset.date, branch: 'aware', t: null, combo: null, home: null, n: null }));
    }
  }
  if (ctx.link.beat) {
    const t = el.querySelector(`[data-beat="${typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(ctx.link.beat) : ctx.link.beat}"]`);
    const bar = el.querySelector('.beat-bar');
    if (t && t.scrollIntoView) { t.style.scrollMarginTop = `${bar ? bar.offsetHeight + 8 : 0}px`; t.scrollIntoView({ block: 'start' }); }
  }
}
