// ui/panels/p2.js (L5): P2, "where the next battery goes". A month-long what-if on REAL ERCOT LZ_NORTH prices
// (August 2026) and SMART-DS 2018 loads (SIM). Everything is precomputed by sim.p2_build (L3); this view only looks
// results up and never re-derives tiers (build prompt 5.3, 5.6).
//
//   mount(el, ctx) -> Promise     ctx as docs/contracts.md A.9
//
// Pure helpers are exported for ui/test/p2.test.js (no DOM at import time).
import { chartHTML, modeIndex, band } from '../lib/charts.js';
import { svg } from '../lib/icons.js';
import {
  beatBarHTML, sharedNames, flipVerdict, FLIP_HEADLINE_MAX_OVERLAP, isScreening, numHTML, numText, SCREEN_CHIP, unscreenedChips, lazyDetails,
} from './more.js';

// ---- round 2 (UX_SPEC_R2 7.2): a few front cards, everything else in collapsible sections, plain words first ----

/** The one setting the index-level blocks were computed for (flip, bridge, useful capacity; audit R2 M1, M3). */
export const INDEX_SCOPE_TEXT = "Core battery · D-26 onset · today's load";
/** True when index-level blocks (index.flip, index.bridge, usefulCapacity) describe this combo: index.flip.combos
 *  lists the combos they were built from. Elsewhere those blocks carry a scope label and are never read as this
 *  combo's own numbers. */
export function inIndexScope(index, combo) {
  const fc = index && index.flip && Array.isArray(index.flip.combos) ? index.flip.combos : null;
  if (fc) return fc.includes(combo);
  return /-core-d26-g0$/.test(String(combo || ''));
}
function scopeNote(index, combo) {
  if (inIndexScope(index, combo)) return '';
  return `<div class="p2-scope" data-tip="These numbers were computed for one setting only, not for the controls picked above. Switch to Core, D-26 onset, today's load to see them as that combo's own.">${svg('info', { size: 13 })} Computed for ${esc(INDEX_SCOPE_TEXT)} only</div>`;
}

/** Month-peak words for a meter. A month PEAK is not a tier event (tiers need duration: sim/tiers.py), so these are
 *  display bands of the peak (charts.band), worded as peaks. [tier colour index, word, tooltip] */
export const PEAK_WORDS = {
  b0: [0, 'Stays within rating', 'Its highest reading all month is at or under 100% of nameplate.'],
  b1: [1, 'Peaks over nameplate', 'Its highest reading is 100-110% of nameplate: short spells are normal, not a violation.'],
  b2: [2, 'Peaks above its normal rating', 'Its highest reading is above 110%, the normal rating. Held for 30 minutes that becomes a violation.'],
  b4: [4, 'Peaks above its emergency rating', 'Its highest reading is above 150%, the emergency rating (SMART-DS, REAL).'],
  na: [0, 'no reading', 'No month peak in the data.'],
};
export const peakWord = (pct) => PEAK_WORDS[band(pct)] || PEAK_WORDS.na;

/** A collapsible section (base.css .hb-sec). teaser is HTML our code built. data-sec is the id the beat map and the
 *  per-viewer open state use. */
export function secHTML({ id, title, icon = null, teaser = '', body = '', open = false, beat = null }) {
  return `<details class="hb-sec p2-sec" data-sec="${esc(id)}"${beat ? ` data-beat="${esc(beat)}"` : ''}${open ? ' open' : ''}>`
    + `<summary>${icon ? svg(icon, { size: 16 }) : ''}<span class="sec-t">${esc(title)}</span><span class="sec-teaser">${teaser}</span>${svg('chevron', { size: 14, cls: 'sec-chev' })}</summary>`
    + `<div class="hb-sec-body">${body}</div></details>`;
}
/** Which section a P2 beat opens (UX_SPEC_R2 7.2: a beat opens its target section before scrollIntoView). */
export const BEAT_SECTION = { 'p2-flip': 'flip', 'p2-capacity': 'capacity', insight: 'insight', 'p2-controls': null };

// The flip display rule and the screening chip live in more.js (the beat captions use them too); re-exported here
// for the panel's tests.
export { flipVerdict, FLIP_HEADLINE_MAX_OVERLAP, isScreening, SCREEN_CHIP, unscreenedChips };

export const POLICIES = [['aware', 'feeder-aware'], ['naive', 'naive']];
export const CLASSES = [['core', 'Core'], ['legacy', 'Legacy']];
export const RULES = [['d26', 'D-26 onset'], ['cheapest', 'cheapest hours']];
export const GROWTHS = [['0', 'today'], ['20', 'growth']];

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** "aware-core-d26-g0" -> {policy, cls, rule, growth} (growth as a string of digits); null if malformed. */
export function parseCombo(id) {
  const m = /^([a-z]+)-([a-z]+)-([a-z0-9]+)-g(\d+)$/.exec(String(id || ''));
  return m ? { policy: m[1], cls: m[2], rule: m[3], growth: m[4] } : null;
}
export const comboId = (c) => `${c.policy}-${c.cls}-${c.rule}-g${c.growth}`;
export const counterpart = (id) => {
  const c = parseCombo(id);
  return c ? comboId({ ...c, policy: c.policy === 'aware' ? 'naive' : 'aware' }) : null;
};

/** A labelled bulk value: bulk arrays carry their label once in the envelope's `series`. A series computed by the
 *  surrogate (`by: "surrogate"`) is screening: its values carry a "not OpenDSS-checked" cite, so they get the chip. */
export function bulk(doc, key, v, cite) {
  const s = doc && doc.series && doc.series[key];
  const label = s && s.label ? s.label : 'SIM';
  const c = cite || (s && s.by === 'surrogate' ? 'surrogate screen (sim.surrogate, calibrated vs OpenDSS); not OpenDSS-checked' : null);
  return c ? { v, label, cite: c } : { v, label };
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
/** "2026-08" -> "August 2026" (a date, not a measured number). */
export function monthName(ym) {
  const m = /^(\d{4})-(\d{2})$/.exec(String(ym || ''));
  return m && MONTHS[+m[2] - 1] ? `${MONTHS[+m[2] - 1]} ${m[1]}` : 'the month';
}

export function tfName(topology, i) {
  const t = topology.transformers[i];
  if (!t) return `T-${i}`;
  return t.focus ? `${t.focus} (T-${i})` : `T-${i}`;
}
export function homeLabel(topology, i) {
  const h = topology.homes[i];
  return h ? h.label : `home ${i}`;
}
export function homeIndexById(topology, id) {
  if (id == null) return -1;
  return topology.homes.findIndex((h) => h.id === id);
}

/** Find the ranking entry for a home id: the entry itself, or the entry whose alsoOnTf lists it. */
export function findCandidate(doc, topology, homeId) {
  const hi = homeIndexById(topology, homeId);
  if (hi < 0) return { entry: null, via: null, home: -1 };
  for (const e of doc.ranking || []) {
    if (e.home === hi) return { entry: e, via: 'home', home: hi };
  }
  for (const e of doc.ranking || []) {
    if ((e.alsoOnTf || []).includes(hi)) return { entry: e, via: 'alsoOnTf', home: hi };
  }
  return { entry: null, via: null, home: hi };
}

/** Rank of a home (index) in a combo's ranking, counting alsoOnTf siblings; null if not in the top 50. */
export function rankOf(doc, homeIdx) {
  for (const e of (doc && doc.ranking) || []) {
    if (e.home === homeIdx || (e.alsoOnTf || []).includes(homeIdx)) return e.rank;
  }
  return null;
}

/** Totals of the existing-fleet counterfactual (index.fleetCounterfactual): per policy, summed over transformers. */
export function fleetTotals(fc) {
  const out = {};
  for (const k of ['none', 'naive', 'aware']) {
    const x = fc && fc[k];
    if (!x) continue;
    const sum = (a) => (Array.isArray(a) ? a.reduce((s, v) => s + (Number.isFinite(v) ? v : 0), 0) : 0);
    out[k] = {
      h100: Math.round(sum(x.h100) * 100) / 100,
      normalTfs: Array.isArray(x.normalEvents) ? x.normalEvents.filter((v) => v > 0).length : 0,
      normalEvents: sum(x.normalEvents),
      emergencyN: sum(x.emergencyN),
    };
  }
  return out;
}

/** Where a home stands under a policy when it is outside that combo's top 50: the collapsed rank from
 *  index.flip.movers (one entry per transformer) and the with/without month peak from index.bridge, when L3 lists
 *  them. Both are labelled data; null fields when not listed. */
export function standingOutside(index, homeIdx, tf, policy) {
  const f = index && index.flip;
  const mv = f && Array.isArray(f.movers) ? f.movers.find((m) => m.home === homeIdx) : null;
  const rank = mv ? (policy === 'naive' ? mv.rankNaive : mv.rankAware) : null;
  const br = index && Array.isArray(index.bridge) ? index.bridge.find((b) => b.tf === tf) : null;
  const bp = br && br[policy] && br[policy].home === homeIdx ? br[policy] : null;
  return { rank: rank && typeof rank === 'object' && 'label' in rank ? rank : null, bridge: bp };
}

/** True when the OpenDSS referee re-ran this candidate (L3: opendss.after is null when it did not). */
export function checkedByOpenDSS(e) { return !!(e && e.opendss && e.opendss.after && e.screening !== true); }

function driverParts(driver) {
  if (!driver || !driver.profile) return null;
  const shared = sharedNames(driver.sharedWith);
  return { home: driver.label || null, profile: driver.profile, shared, kw: driver.kwAtPeak || null };
}

/**
 * The counterfactual sentence, built only from data (build prompt 5.6 "candidate card").
 * Returns an array of parts: strings (prose, no digits of our own) and labelled numbers {v,label,cite?, unit, digits}.
 * The renderers below turn the labelled parts into "value + chip" (HTML) or "value LABEL" (text).
 */
export function counterfactualParts({ entry, doc, index, topology, combo }) {
  const c = parseCombo(combo) || {};
  const tf = entry.tf;
  const tname = tfName(topology, tf);
  const month = monthName(index && index.month);
  const parts = [];
  const od = checkedByOpenDSS(entry) ? entry.opendss : null;
  const B = od && od.before ? od.before : entry.before;
  const A = od ? od.after : entry.after;
  const beforeH = B && B.h100 ? B.h100 : bulk(doc, 'baseline', doc.baseline.h100[tf]);
  const beforePeak = B && B.peakPct ? B.peakPct : bulk(doc, 'baseline', doc.baseline.peak[tf] / 10);
  const clsName = (CLASSES.find(([k]) => k === c.cls) || [null, c.cls])[1];
  const pol = c.policy === 'naive' ? 'naive dispatch (no feeder check)' : 'feeder-aware dispatch';
  const d = driverParts(entry.driver);
  const stressed = typeof beforeH.v === 'number' && beforeH.v > 0;
  if (stressed) {
    parts.push(`In ${month} transformer ${tname} spent `, { ...beforeH, unit: ' h', digits: 2 }, ' above nameplate without a new battery (peak ', { ...beforePeak, unit: '%', digits: 1 }, ')');
    if (d) {
      parts.push(`, driven by one home's load, ${d.home || 'one home'} (SMART-DS profile ${d.profile}`);
      if (d.shared.length) parts.push(`, the same profile as ${d.shared.join(', ')}: one shape, not independent evidence`);
      parts.push(')');
    }
    parts.push('. ');
  } else {
    parts.push(`In ${month} transformer ${tname} stayed at or below nameplate without a new battery (peak `, { ...beforePeak, unit: '%', digits: 1 }, '). ');
  }
  parts.push(`With a ${clsName} at ${homeLabel(topology, entry.home)} under ${pol}${od ? ' (OpenDSS month run)' : ''}: `);
  if (A && A.h100) parts.push({ ...A.h100, unit: ' h', digits: 2 }, ' above nameplate, ');
  const pk = od && A && A.peakPct ? A.peakPct : entry.peakWithPct;
  if (pk) parts.push('peak ', { ...pk, unit: '%', digits: 1 }, ', ');
  if (entry.revenueUSD) parts.push('August energy value ', { ...entry.revenueUSD, money: true, digits: 0 });
  if (entry.curtailKWh && entry.curtailKWh.v > 0) parts.push(', curtailed ', { ...entry.curtailKWh, unit: ' kWh', digits: 0 });
  parts.push('.');
  if (entry.noNewViolation && entry.noNewViolation.v === false) {
    parts.push(' It adds a new violation');
    if (entry.stressAddedH) parts.push(' (', { ...entry.stressAddedH, unit: ' h', digits: 2 }, ' of added stress)');
    parts.push(': where NOT to put it.');
  } else if (entry.stressAvoidedH && entry.stressAvoidedH.v > 0) {
    parts.push(' It avoids ', { ...entry.stressAvoidedH, unit: ' h', digits: 2 }, ' of stress on its transformer.');
  }
  if (entry.protectionWith && entry.protectionWith.v === true) {
    const dark = (entry.homesDarkWith || []).map((i) => homeLabel(topology, i));
    parts.push(` Protection may operate here (ASSUMPTION rule)${dark.length ? `: ${dark.join(', ')} go dark while battery homes island and stay lit` : ''}.`);
  }
  return parts;
}

function partText(p, fmt) { return typeof p === 'string' ? p : numText(fmt, p, { unit: p.unit, digits: p.digits, money: p.money }); }
function partHTML(p, fmt) { return typeof p === 'string' ? esc(p) : numHTML(fmt, p, { unit: p.unit, digits: p.digits, money: p.money }); }
export const counterfactualText = (args, fmt) => counterfactualParts(args).map((p) => partText(p, fmt)).join('');
export const counterfactualHTML = (args, fmt) => counterfactualParts(args).map((p) => partHTML(p, fmt)).join('');

/** The month peak with the battery as the table shows it: OpenDSS's number when the referee ran this candidate,
 *  otherwise the surrogate screening number (5.6.11: shortlist rows show OpenDSS numbers). */
export function peakWithShown(e) {
  if (checkedByOpenDSS(e) && e.opendss.after && e.opendss.after.peakPct) return e.opendss.after.peakPct;
  return e.peakWithPct || null;
}

/** The OpenDSS month peaks {before, after} of a refereed ranking entry, or null (then only screening numbers exist). */
export function odssPeaks(e) {
  if (!checkedByOpenDSS(e)) return null;
  const b = e.opendss.before && e.opendss.before.peakPct, a = e.opendss.after && e.opendss.after.peakPct;
  return b && a ? { before: b, after: a } : null;
}

/** Labelled metrics of an object as [key, labelled] pairs (skips anything not labelled). */
export function labelledPairs(obj, isLabelled) {
  return Object.entries(obj || {}).filter(([, v]) => isLabelled(v));
}

const METRIC_NAMES = {
  noNewViolation: ['adds no new violation', {}],
  peakWithPct: ['peak with the battery', { unit: '%', digits: 1 }],
  stressAvoidedH: ['stress avoided', { unit: ' h', digits: 2 }],
  stressAddedH: ['stress added', { unit: ' h', digits: 2 }],
  reliefKWh: ['energy shaved above nameplate', { unit: ' kWh', digits: 1 }],
  revenueUSD: ['August energy value', { money: true, digits: 0 }],
  curtailKWh: ['curtailed', { unit: ' kWh', digits: 0 }],
  protectionWith: ['protection operates (ASSUMPTION rule)', {}],
};

/** Candidate metrics computed on the surrogate loading whatever their cite says (5.6.5: kWh shaved above nameplate). */
const SURROGATE_METRICS = new Set(['reliefKWh']);

const OPENDSS_NAMES = {
  peakPct: ['peak', { unit: '%', digits: 1 }],
  h100: ['above nameplate', { unit: ' h', digits: 2 }],
  normalEvents: ['normal-tier events', {}],
  emergencyN: ['emergency intervals', {}],
  protection: ['protection', {}],
};

// ---------------------------------------------------------------------------------------------------------------
function seg(ctx, cur, key, opts, labelFor) {
  return `<div class="hb-seg" role="group" aria-label="${esc(key)}">${opts.map(([k, t]) => {
    const next = comboId({ ...cur, [key]: k });
    return `<a href="${ctx.href({ view: 'p2', combo: next })}"${cur[key] === k ? ' aria-current="true"' : ''}>${labelFor ? labelFor(k, t) : esc(t)}</a>`;
  }).join('')}</div>`;
}

function constLabelled(doc, name) {
  const c = doc && doc.constants && doc.constants[name];
  return c && typeof c.value === 'number' ? { v: c.value, label: c.label, cite: c.cite } : null;
}

function strips(entry, doc, topology, fmt) {
  const s = doc.strips && doc.strips[String(entry.tf)];
  if (!s) return `<div class="hb-sub">No monthly strip for ${esc(tfName(topology, entry.tf))} in this combo (strips cover the top 10 plus A and T-240).</div>`;
  const lab = (doc.series && doc.series.strips && doc.series.strips.label) || 'SIM';
  const out = [];
  out.push(`<div class="p2-strips"><div>${chartHTML('heat', { values: s.without, label: lab, caption: 'Without the battery: hourly max loading, by day and hour', captionTop: true, title: 'without' })}</div>`);
  out.push(`<div>${chartHTML('heat', { values: s.with, label: lab, caption: 'With the battery', captionTop: true, title: 'with' })}</div></div>`);
  const scr = doc.series && doc.series.strips && doc.series.strips.by === 'surrogate' ? ` ${SCREEN_CHIP}` : '';
  out.push(`<div class="p2-legend"><span class="hs-b0 sw"></span>at or below nameplate <span class="hs-b1 sw"></span>over nameplate <span class="hs-b2 sw"></span>over the normal rating <span class="hs-b4 sw"></span>over the emergency rating (bands, not tier events)${scr}</div>`);
  if (s.peakDay && Array.isArray(s.peakDay.without)) {
    const ticks = [0, 24, 48, 72].map((i) => ({ i, text: `${String(i / 4).padStart(2, '0')}:00` }));
    out.push(chartHTML('line', {
      series: [
        { name: 'without', values: s.peakDay.without.map((x) => x / 10), cls: 's-without' },
        { name: 'with', values: (s.peakDay.with || []).map((x) => x / 10), cls: 's-with' },
      ],
      refs: [{ y: 100, text: 'nameplate', cls: 'r-amber' }, { y: 110, text: 'normal', cls: 'r-normal' }, { y: 150, text: 'emergency', cls: 'r-emerg' }],
      xTicks: ticks, unit: '%', label: lab, title: 'peak day',
      caption: `Peak day ${s.peakDay.day || ''}: loading without (grey) and with (accent) the battery, % of nameplate`,
    }));
  }
  void fmt;
  return out.join('');
}

const P = { unit: '%', digits: 1 };

/** The details of a candidate, behind "Why this home" (the counterfactual sentence, the metrics, OpenDSS's month run,
 *  the other policy's standing and the month strips). Every number stays one click away (UX_SPEC_R2 2.5). */
function candidateDetails(ctx, st, e) {
  const { topology, fmt } = ctx;
  const { doc, index, combo, other, otherCombo } = st;
  // Audit R2 L8: the screening peak beside OpenDSS's always carries the screening tag, whatever its cite says.
  const screenTag = (x) => (isScreening(x) ? '' : SCREEN_CHIP);
  const metricHTML = (k, v) => (k === 'peakWithPct' && checkedByOpenDSS(e) && e.opendss.after.peakPct
    ? `${numHTML(fmt, e.opendss.after.peakPct, METRIC_NAMES[k][1])} OpenDSS · ${numHTML(fmt, v, METRIC_NAMES[k][1])}${screenTag(v)}`
    : numHTML(fmt, v, METRIC_NAMES[k][1]) + ((SURROGATE_METRICS.has(k) || (k === 'peakWithPct' && !checkedByOpenDSS(e))) && !isScreening(v) ? SCREEN_CHIP : ''));
  const metrics = labelledPairs(e, fmt.isLabelled).filter(([k]) => METRIC_NAMES[k])
    .map(([k, v]) => `<div class="p2-m"><span>${esc(METRIC_NAMES[k][0])}</span><b>${metricHTML(k, v)}</b></div>`).join('');
  const odss = checkedByOpenDSS(e) ? `<div class="p2-odss"><b>OpenDSS month run</b>${['before', 'after'].map((w) => {
    const pairs = labelledPairs(e.opendss[w], fmt.isLabelled).filter(([k]) => OPENDSS_NAMES[k]);
    return pairs.length ? `<div class="p2-m"><span>${w === 'before' ? 'without' : 'with'} the battery</span><b>${pairs.map(([k, v]) => `${esc(OPENDSS_NAMES[k][0])} ${numHTML(fmt, v, OPENDSS_NAMES[k][1])}`).join(' · ')}</b></div>` : '';
  }).join('')}</div>` : '';
  const also = (e.alsoOnTf || []).length
    ? `<div class="hb-sub">Same transformer, identical in the screening model: ${e.alsoOnTf.map((i) => esc(homeLabel(topology, i))).join(', ')}. The lowest id is shown.</div>` : '';
  const tie = e.tieBroken ? '<div class="hb-sub">Its place among equals was decided by home id (the last rank key).</div>' : '';
  const homeId = topology.homes[e.home] ? topology.homes[e.home].id : null;
  const oRank = other ? rankOf(other, e.home) : null;
  const oEntry = other ? findCandidate(other, topology, homeId).entry : null;
  const oc = parseCombo(otherCombo) || {};
  let neighbour = '';
  if (oEntry && oEntry.protectionWith && oEntry.protectionWith.v === true && !(e.protectionWith && e.protectionWith.v === true)) {
    const dark = (oEntry.homesDarkWith || []).map((i) => homeLabel(topology, i));
    if (dark.length) neighbour = `<div class="p2-neighbour">Under ${oc.policy === 'naive' ? 'naive' : 'feeder-aware'} dispatch, protection may operate here (ASSUMPTION rule) and ${esc(dark.join(', '))} go dark. Under this policy they stay lit: your neighbour's battery, managed this way, kept your lights on (SIM).</div>`;
  }
  let oWhere = oRank ? `rank ${esc(oRank)}` : 'not in its top 50';
  let oViol = !!(oEntry && oEntry.noNewViolation && oEntry.noNewViolation.v === false);
  if (!oRank && otherCombo && inIndexScope(index, combo)) {
    const so = standingOutside(index, e.home, e.tf, oc.policy);
    if (so.rank) oWhere = `rank ${numHTML(fmt, so.rank)} (one entry per transformer)`;
    if (so.bridge && fmt.isLabelled(so.bridge.peakWithPct)) oWhere += `, month peak with it ${numHTML(fmt, so.bridge.peakWithPct, P)}`;
    oViol = oViol || !!(so.bridge && so.bridge.noNewViolation && so.bridge.noNewViolation.v === false);
  }
  const toggle = otherCombo
    ? `<a class="p2-toggle" href="${ctx.href({ view: 'p2', combo: otherCombo, home: homeId })}">Managed ${oc.policy === 'naive' ? 'naively' : 'feeder-aware'} instead: ${oWhere}${oViol ? ', adds a violation (where NOT to put it)' : ''}</a>` : '';
  return `<p class="p2-cf">${counterfactualHTML({ entry: e, doc, index, topology, combo }, fmt)}</p>
    ${neighbour}
    <div class="p2-metrics">${metrics}${odss}</div>
    ${also}${tie}
    ${toggle}
    ${strips(e, doc, topology, fmt)}`;
}

/** One month-peak meter (icons.js meter), its word and caption; the number sits in the tooltip (UX_SPEC_R2 2.5). */
function peakMeter(fmt, x, caption) {
  if (!x || !fmt.isLabelled(x)) return `<div class="p2-mt"><div class="p2-mt-cap">${esc(caption)}</div><div class="p2-mt-w">n/a</div></div>`;
  const [tier, word, tipText] = peakWord(x.v);
  const tip = `<b>${esc(caption)}</b>: month peak ${numHTML(fmt, x, P)}<br>${esc(tipText)}`;
  return `<div class="p2-mt" data-tip-html="${esc(tip)}" tabindex="0">${svg('meter', { size: 46, pct: x.v, tier })}`
    + `<div><div class="p2-mt-cap">${esc(caption)}</div><div class="p2-mt-w tier-${tier}">${esc(word)}</div></div></div>`;
}

/** The front card: "Next battery goes here" (UX_SPEC_R2 7.2): house + battery icon, who and where, then two meters,
 *  without -> with the battery (month peak), each with its word; an OpenDSS pill or the screening tag; "Why this home"
 *  opens the counterfactual sentence and every number. */
function candidateCard(ctx, st) {
  const { topology, fmt } = ctx;
  const { doc, index, combo, sel } = st;
  const e = sel.entry;
  if (!e) {
    if (sel.home < 0) return '<div class="p2-card p2-next"><div class="hb-sub">No candidate selected.</div></div>';
    const h = topology.homes[sel.home];
    const peak = bulk(doc, 'baseline', doc.baseline.peak[h.tf] / 10);
    const pol = (parseCombo(combo) || {}).policy;
    // index.flip.movers and index.bridge were built for one setting: never read them as another combo's (audit R2 M1)
    const so = h.battery || !inIndexScope(index, combo) ? { rank: null, bridge: null } : standingOutside(index, sel.home, h.tf, pol);
    const polName = pol === 'naive' ? 'naive dispatch (no feeder check)' : 'feeder-aware dispatch';
    let more = '';
    if (so.rank) more += `<div class="hb-sub">Rank under ${esc(polName)}: ${numHTML(fmt, so.rank)} (one entry per transformer).</div>`;
    const b = so.bridge;
    let meters = peakMeter(fmt, peak, 'without a new battery');
    if (b && fmt.isLabelled(b.peakWithPct)) {
      meters += `<span class="p2-arrow">${svg('chevron', { size: 18 })}</span>${peakMeter(fmt, b.peakWithPct, 'with a battery here')}`;
      more += `<p class="p2-cf">With a new battery here under ${esc(polName)}: month peak ${b.peakWithoutPct ? numHTML(fmt, b.peakWithoutPct, P) : 'n/a'} without, ${numHTML(fmt, b.peakWithPct, P)} with; hours above nameplate ${b.h100Without ? numHTML(fmt, b.h100Without, { unit: ' h', digits: 2 }) : 'n/a'} without, ${b.h100With ? numHTML(fmt, b.h100With, { unit: ' h', digits: 2 }) : 'n/a'} with.${b.noNewViolation && b.noNewViolation.v === false ? ' It adds a new violation: <b>where NOT to put it</b>.' : ''}</p>`;
      const oc = counterpart(combo);
      if (oc) more += `<a class="p2-toggle" href="${ctx.href({ view: 'p2', combo: oc, home: h.id })}">Managed ${pol === 'naive' ? 'feeder-aware' : 'naively'} instead: open its card</a>`;
    }
    const d = (index && Array.isArray(index.bridge) ? index.bridge.find((x) => x.tf === h.tf) : null);
    const dr = d && d.driver && d.driver.profile ? `<div class="hb-sub">Its transformer's stress is one home's load, ${esc(d.driver.label || '')} (SMART-DS profile ${esc(d.driver.profile)}${sharedNames(d.driver.sharedWith).length ? `, the same profile as ${esc(sharedNames(d.driver.sharedWith).join(', '))}: one shape, not independent evidence` : ''}).</div>` : '';
    const viol = b && b.noNewViolation && b.noNewViolation.v === false;
    return `<div class="p2-card p2-next" data-card-home="${esc(h.id)}">
      <div class="p2-next-h">${svg('house', { size: 18 })}<h3>${esc(h.label)} · on ${esc(tfName(topology, h.tf))}</h3></div>
      <div class="hb-sub">${h.battery ? 'This home already has a battery.' : 'Not in this combo\'s top 50.'}</div>
      <div class="p2-meters">${meters}</div>
      ${viol ? `<div class="p2-warnline">${svg('warn', { size: 16 })} Adds a violation here: where NOT to put it</div>` : ''}
      <details class="p2-why"><summary>Why ${svg('chevron', { size: 13, cls: 'sec-chev' })}</summary><div class="p2-why-body">
        <div class="hb-sub">Its transformer's month peak without a new battery: ${numHTML(fmt, peak, P)}.</div>${more}${dr}</div></details></div>`;
  }
  const t = topology.transformers[e.tf];
  const kva = { v: t.kva, label: 'REAL', cite: 'SMART-DS Transformers.dss' };
  const pill = checkedByOpenDSS(e)
    ? '<span class="p2-badge ok" title="sim.referee: an OpenDSS power flow of the whole month (every 15-minute step of August) with and without this battery">✓ OpenDSS-checked</span>'
    : `<span class="p2-badge screen" title="surrogate only (sim.surrogate); not yet refereed by OpenDSS">screening</span>`;
  const od = odssPeaks(e);
  const before = od ? od.before : bulk(doc, 'baseline', doc.baseline.peak[e.tf] / 10);
  const after = peakWithShown(e);
  const viol = e.noNewViolation && e.noNewViolation.v === false;
  const homeId = topology.homes[e.home] ? topology.homes[e.home].id : null;
  const mount = t.mount === 'pole' ? 'polemount' : 'padmount';
  return `<div class="p2-card p2-next" data-card-home="${esc(homeId || '')}">
    <div class="p2-next-h">${svg('house', { size: 18 })}${svg('battery', { size: 22, state: 'N', level: 0.9 })}<span class="p2-next-t">Next battery goes here</span>${pill}</div>
    <h3 class="p2-next-who">#${esc(e.rank)} ${esc(homeLabel(topology, e.home))} · on ${svg(mount, { size: 16 })} ${esc(tfName(topology, e.tf))} · ${numHTML(fmt, kva, { unit: ' kVA' })}</h3>
    <div class="p2-meters">${peakMeter(fmt, before, 'without the battery')}<span class="p2-arrow">${svg('chevron', { size: 18 })}</span>${peakMeter(fmt, after, 'with the battery')}</div>
    ${viol ? `<div class="p2-warnline">${svg('warn', { size: 16 })} Adds a violation here: where NOT to put it</div>` : ''}
    <details class="p2-why"><summary>Why this home ${svg('chevron', { size: 13, cls: 'sec-chev' })}</summary><div class="p2-why-body">${candidateDetails(ctx, st, e)}</div></details>
  </div>`;
}

function rankingTable(ctx, st) {
  const { topology, fmt } = ctx;
  const { doc, sel } = st;
  const rows = (doc.ranking || []).slice(0, 15).map((e) => {
    const id = topology.homes[e.home] ? topology.homes[e.home].id : '';
    const on = sel.entry && sel.entry.rank === e.rank;
    const pk = peakWithShown(e);
    const pw = pk ? fmt.fmtValue(pk, { digits: 1 }) : 'n/a';
    const av = e.stressAvoidedH ? fmt.fmtValue(e.stressAvoidedH, { digits: 2 }) : 'n/a';
    const rv = e.revenueUSD ? fmt.fmtValue(e.revenueUSD, { money: true, digits: 0 }) : 'n/a';
    const viol = e.noNewViolation && e.noNewViolation.v === false ? ' p2-viol' : '';
    return `<tr class="${on ? 'on' : ''}${viol}"><td>${esc(e.rank)}</td><td><a href="${ctx.href({ view: 'p2', combo: st.combo, home: id })}">${esc(homeLabel(topology, e.home))}</a>${e.tieBroken ? '<sup title="place decided by id">id</sup>' : ''}</td>
      <td>${esc(tfName(topology, e.tf))}</td><td class="n">${esc(pw)}</td><td class="n">${esc(av)}</td><td class="n">${esc(rv)}</td><td>${checkedByOpenDSS(e) ? '<span class="p2-dot ok" title="OpenDSS-checked">●</span>' : '<span class="p2-dot" title="screening">○</span>'}</td></tr>`;
  }).join('');
  const lab = (k, fallback) => {
    const e = (doc.ranking || [])[0];
    // the peak column mixes OpenDSS (●) and screening (○) rows, so its header chip names both; other columns are one kind
    if (k === 'peakWithPct') return fmt.chip(e && e[k] && e[k].label ? e[k].label : fallback, 'month peak with the battery: OpenDSS month run on ● rows, surrogate screening on ○ rows');
    return e && e[k] && e[k].label ? fmt.chip(e[k].label, e[k].cite) + (isScreening(e[k]) ? SCREEN_CHIP : '') : fmt.chip(fallback);
  };
  return `<table class="p2-rank"><thead><tr><th>#</th><th>home</th><th>transformer</th><th>peak with, % (● OpenDSS, ○ screening)${lab('peakWithPct', 'SIM')}</th><th>stress avoided, h${lab('stressAvoidedH', 'SIM')}</th><th>August value${lab('revenueUSD', 'DERIVED')}</th><th></th></tr></thead><tbody>${rows}</tbody></table>
    <div class="hb-sub">Rank rule, no weights: adds no new violation; stress hours avoided; peak with the battery, lowest first; value minus curtailment; home id. Rows in red add a violation. ● OpenDSS-checked, ○ screening.</div>`;
}

function greedyBlock(ctx, st) {
  const { topology, fmt } = ctx;
  const g = (st.doc.greedy || []).slice(0, st.n);
  if (!g.length) return '<div class="hb-sub">No greedy build in this combo.</div>';
  const rows = g.map((x) => `<tr><td>${esc(x.k)}</td><td>${esc(homeLabel(topology, x.home))}</td><td>${esc(tfName(topology, x.tf))}</td>
    <td class="n">${x.feeder && x.feeder.normalTfs ? fmt.fmtValue(x.feeder.normalTfs) : 'n/a'}</td><td class="n">${x.feeder && x.feeder.emergencyTfs ? fmt.fmtValue(x.feeder.emergencyTfs) : 'n/a'}</td><td class="n">${x.feeder && x.feeder.h110 ? fmt.fmtValue(x.feeder.h110, { digits: 1 }) : 'n/a'}</td></tr>`).join('');
  const g0 = g[0].feeder && g[0].feeder.normalTfs;
  const l0 = g0 ? fmt.chip(g0.label, g0.cite) + (isScreening(g0) ? SCREEN_CHIP : '') : '';
  return `<table class="p2-rank"><thead><tr><th>k</th><th>home</th><th>transformer</th><th>feeder tfs with a normal-tier event${l0}</th><th>emergency tfs${l0}</th><th>h above normal rating${l0}</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="hb-sub">Place #1, re-run its transformer, re-score, repeat (exact in the screening model). The slider above picks how many; the scene shows them as new cabinets.</div>`;
}

/** The flip in one line (front): this page's #1 and where the other policy ranks it, from the two combos' OWN
 *  rankings (DERIVED). The index-level movers are read only when this combo is in their scope (audit R2 M3). */
export function flipLineHTML(ctx, st) {
  const { fmt, topology } = ctx;
  const cur = (parseCombo(st.combo) || {}).policy;
  const a1 = st.aware && st.aware.ranking && st.aware.ranking[0];
  const n1 = st.naive && st.naive.ranking && st.naive.ranking[0];
  if (!a1 || !n1) return '';
  if (a1.home === n1.home) return `<div class="p2-flipline same">${svg('check', { size: 16 })} Both policies pick the same first home here: ${esc(homeLabel(topology, a1.home))}.</div>`;
  const pick = cur === 'naive' ? n1 : a1;
  const otherDoc = cur === 'naive' ? st.aware : st.naive;
  const otherPol = cur === 'naive' ? 'aware' : 'naive';
  const otherName = cur === 'naive' ? 'feeder-aware' : 'naive';
  const here = cur === 'naive' ? 'naive' : 'feeder-aware';
  const R = (v, which) => numHTML(fmt, { v, label: 'DERIVED', cite: `rank in the ${which} ranking of this setting (sim.p2_build; ties broken by home id)` });
  const r = rankOf(otherDoc, pick.home);
  let where;
  if (r) where = `${esc(otherName)} rank ${R(r, otherName)}`;
  else {
    const so = inIndexScope(st.index, st.combo) ? standingOutside(st.index, pick.home, pick.tf, otherPol) : { rank: null };
    where = so.rank ? `${esc(otherName)} rank ${numHTML(fmt, so.rank)}` : `outside ${esc(otherName)}'s top fifty`;
  }
  const te = findCandidate(otherDoc, topology, topology.homes[pick.home] && topology.homes[pick.home].id).entry;
  const viol = te && te.noNewViolation && te.noNewViolation.v === false;
  const head = cur === 'naive' ? 'Feeder-aware would pick differently' : 'Naive would pick differently';
  return `<div class="p2-flipline">${svg('turns', { size: 16 })}<span><b>${head}:</b> ${esc(homeLabel(topology, pick.home))} goes from ${where} to ${esc(here)} #${R(pick.rank, here)}${viol ? `, and under ${esc(otherName)} dispatch it adds a violation` : ''}.</span></div>`;
}

function flipBlock(ctx, st) {
  const { fmt, topology } = ctx;
  const f = st.index.flip || {};
  const v = flipVerdict(f);
  const ov = f.top10Overlap, sp = f.spearman, un = f.untied || {};
  const ties = st.index.ties && st.index.ties.byId;
  const scoped = inIndexScope(st.index, st.combo);
  let body = scopeNote(st.index, st.combo);
  if (ov) {
    body += `<div class="p2-flip-big"><span class="hb-big">${numHTML(fmt, ov)}</span><span class="hb-sub"> of 10 in both top tens (naive vs feeder-aware${ov.cite && /collapsed|per transformer/i.test(ov.cite) ? ', one entry per transformer' : ''})</span></div>`;
    body += v.supports ? `<div class="p2-headline">${esc(v.headline)}</div>`
      : `<div class="p2-headline muted">The two rankings overlap by the number above; the flip is ${ov.v >= 10 ? 'not seen' : 'partial'} in this data.</div>`;
    body += `<div class="hb-sub">Spearman ${sp ? numHTML(fmt, sp, { digits: 2 }) : 'n/a'}${un.top10Overlap ? ` · untied candidates only: overlap ${numHTML(fmt, un.top10Overlap)}, Spearman ${un.spearman ? numHTML(fmt, un.spearman, { digits: 2 }) : 'n/a'} over ${un.n != null ? numHTML(fmt, typeof un.n === 'number' ? { v: un.n, label: un.top10Overlap.label || 'DERIVED' } : un.n) : 'n/a'} candidates` : ''}${ties ? ` · places decided by id: ${numHTML(fmt, ties)} of ${esc(st.index.ties.of)}` : ''}</div>`;
    const dr = st.index.drivers;
    if (dr && dr.top10DistinctProfiles) body += `<div class="hb-sub">The feeder-aware top 10 is driven by ${numHTML(fmt, dr.top10DistinctProfiles)} distinct SMART-DS load profiles${Array.isArray(dr.profiles) && dr.profiles.length ? ` (${esc([...new Set(dr.profiles)].join(', '))})` : ''}: shared shapes are one piece of evidence, not several.</div>`;
    const mv = Array.isArray(f.movers) ? f.movers.filter((m) => fmt.isLabelled(m.rankNaive) && fmt.isLabelled(m.rankAware)) : [];
    if (mv.length) {
      body += `<div class="hb-sub"><b>Biggest movers</b> (one entry per transformer): <ul class="p2-fliplist">${mv.slice(0, 5).map((m) => `<li>${esc(m.label || homeLabel(topology, m.home))} on ${esc(tfName(topology, m.tf))}: naive rank ${numHTML(fmt, m.rankNaive)} → feeder-aware rank ${numHTML(fmt, m.rankAware)}</li>`).join('')}</ul></div>`;
    }
    body += `<div class="hb-sub">Headline rule: shown only when the two top tens share at most ${esc(FLIP_HEADLINE_MAX_OVERLAP)} homes (display rule ${fmt.chip('ASSUMPTION', 'ui/panels/p2.js FLIP_HEADLINE_MAX_OVERLAP')}).</div>`;
  }
  if (st.aware && st.naive) {
    const a1 = (st.aware.ranking || [])[0], n1 = (st.naive.ranking || [])[0];
    const line = (e, from, to, toName, toPolicy) => {
      if (!e) return '';
      const r = rankOf(to, e.home);
      const te = findCandidate(to, topology, topology.homes[e.home] && topology.homes[e.home].id).entry;
      let viol = te && te.noNewViolation && te.noNewViolation.v === false;
      let where = r ? `rank ${esc(r)}` : 'not in the top 50';
      if (!r && scoped) {
        const so = standingOutside(st.index, e.home, e.tf, toPolicy);
        if (so.rank) where = `rank ${numHTML(fmt, so.rank)} (one entry per transformer)`;
        if (so.bridge && fmt.isLabelled(so.bridge.peakWithPct)) {
          where += `; month peak ${so.bridge.peakWithoutPct ? numHTML(fmt, so.bridge.peakWithoutPct, P) : 'n/a'} without, ${numHTML(fmt, so.bridge.peakWithPct, P)} with`;
          viol = viol || (so.bridge.noNewViolation && so.bridge.noNewViolation.v === false);
        }
      }
      return `<li>${esc(from)} #1 ${esc(homeLabel(topology, e.home))} on ${esc(tfName(topology, e.tf))}: under ${esc(toName)} ${where}${viol ? ', and it adds a violation there (where NOT to put it)' : ''}.</li>`;
    };
    body += `<div class="hb-sub"><b>This setting's own first choices</b>:</div><ul class="p2-fliplist">${line(a1, 'Feeder-aware', st.naive, 'naive dispatch', 'naive')}${line(n1, 'Naive', st.aware, 'feeder-aware dispatch', 'aware')}</ul>`;
  }
  return `<div class="p2-flip">${body || '<div class="hb-sub">Not computed yet.</div>'}</div>`;
}

/** Audit R2 H1, L15, M3: "how many batteries fit before the grid is harmed?", both policies under the same question,
 *  with OpenDSS's verdict on each build shown (not only in a cite). The screening count 383 is never the naive
 *  headline: OpenDSS refutes it (3 battery-caused events, the cable at 176.5%), and the per-phase cable estimate
 *  passes its rating at 94. Nothing is re-tuned; every number is read from index.usefulCapacity. */
export function capacityParts(u, topology) {
  if (!u) return null;
  const od = u.opendss && u.opendss.naive && u.opendss.aware ? u.opendss : null;
  const eligible = ((topology && topology.homes) || []).filter((h) => h.eligible).length;
  const fh = u.feederHead && u.feederHead.naive;
  const naive = [];
  if (fh && fh.overAt && typeof fh.overAt.v === 'number') naive.push('the feeder cable passes its rating at ', { ...fh.overAt, o: {} }, ' batteries (per-phase estimate)');
  if (u.naive && typeof u.naive.v === 'number') {
    naive.push(naive.length ? ', and ' : '', 'transformers break before the screening count of ', { ...u.naive, o: {}, screen: true });
    if (od) {
      naive.push(': OpenDSS found ', { ...od.naive.causedNormal, o: {} }, ' battery-caused events');
      if (od.naive.headMaxPct) naive.push(' and the cable at ', { ...od.naive.headMaxPct, o: P }, ' there');
    } else naive.push(' (screening only; not OpenDSS-checked)');
  }
  const aware = [];
  if (u.aware && typeof u.aware.v === 'number') {
    aware.push({ ...u.aware, o: {} }, u.aware.v >= eligible && eligible > 0 ? ', every eligible home' : '');
    if (od) {
      aware.push(', OpenDSS-checked: ', { ...od.aware.causedNormal, o: {} }, ' battery-caused events');
      if (od.aware.headMaxPct) aware.push(', cable max ', { ...od.aware.headMaxPct, o: P });
      const vm = od.aware.vMinPu;
      if (vm && typeof vm.v === 'number') {
        aware.push('; the lowest home voltage ', { ...vm, o: { digits: 4, unit: ' pu' } });
        if (typeof vm.volts === 'number') aware.push(' (', { v: vm.volts, label: vm.label, cite: vm.cite, o: { digits: 1, unit: ' V' } }, ')');
        const edge = { v: 0.95, label: 'REAL', cite: 'ANSI C84.1 Range A service voltage lower limit (114 V on a 120 V base)', o: { digits: 2, unit: ' pu' } };
        if (vm.v < edge.v) aware.push(', just under the ANSI Range A edge (', edge, ')');
        else if (vm.v < edge.v + 0.001) aware.push(', at the ANSI Range A edge (', edge, ')');
      }
    } else aware.push(' (screening only; not OpenDSS-checked)');
  }
  return { naive, aware, checked: !!od, naiveOk: false, awareOk: !!(od && od.aware.causedNormal && od.aware.causedNormal.v === 0) };
}

function partsToHTML(parts, fmt) {
  return (parts || []).map((x) => {
    if (typeof x === 'string') return esc(x);
    const { o, screen, ...v } = x;
    return numHTML(fmt, v, o || {}) + (screen && !isScreening(v) ? SCREEN_CHIP : '');
  }).join('');
}

function capacityBlock(ctx, st) {
  const { fmt } = ctx;
  const u = st.index.usefulCapacity;
  if (!u) return '<div class="hb-sub">Not computed yet.</div>';
  const cp = capacityParts(u, ctx.topology);
  const cl = (st.index.series && st.index.series.curve && st.index.series.curve.label) || (u.aware && u.aware.label) || 'SIM';
  // curve rows (L3): [k placed, transformers with a battery-caused normal event, feeder curtailment per mille, feeder h above 110%]
  const rows = (a) => (Array.isArray(a) ? a.filter((r) => Array.isArray(r) && r.length >= 3) : []);
  const cn = rows(u.curve && u.curve.naive), ca = rows(u.curve && u.curve.aware);
  let charts = '';
  if (cn.length > 1) {
    charts += chartHTML('line', { series: [{ name: 'naive', values: cn.map((r) => r[1]), cls: 's-without' }], label: cl, title: 'naive capacity', height: 110, integer: true,
      xTicks: [{ i: 0, text: String(cn[0][0]) }, { i: cn.length - 1, text: String(cn[cn.length - 1][0]) }],
      caption: 'Naive, screening: transformers with a battery-caused normal-tier event, as batteries are added in greedy order' });
  }
  if (ca.length > 1) {
    const capPct = u.cap && typeof u.cap.v === 'number' ? u.cap.v * 100 : null;
    charts += chartHTML('line', { series: [{ name: 'feeder-aware', values: ca.map((r) => r[2] / 10), cls: 's-with' }], label: cl, title: 'aware capacity', height: 110, unit: '%',
      refs: capPct !== null ? [{ y: capPct, text: 'cap', cls: 'r-normal' }] : [],
      xTicks: [{ i: 0, text: String(ca[0][0]) }, { i: ca.length - 1, text: String(ca[ca.length - 1][0]) }],
      caption: 'Feeder-aware, screening: feeder curtailment, % of the energy the new batteries need, as batteries are added' });
  }
  const rule = u.opendss && u.opendss.rule ? `<div class="hb-sub">OpenDSS rule: ${esc(u.opendss.rule)}.</div>` : '';
  return `${scopeNote(st.index, st.combo)}
    <div class="p2-capq">How many batteries fit before the grid is harmed?</div>
    <div class="p2-capline bad">${svg('warn', { size: 18 })}<div><b>Naive:</b> ${partsToHTML(cp.naive, fmt)}.</div></div>
    <div class="p2-capline ${cp.awareOk ? 'ok' : ''}">${svg(cp.awareOk ? 'check' : 'info', { size: 18 })}<div><b>Feeder-aware:</b> ${partsToHTML(cp.aware, fmt)}.</div></div>
    ${rule}
    <div class="hb-sub">Batteries are added from an empty feeder in greedy order. Naive stops at its first battery-caused normal-tier event; feeder-aware stops when curtailment passes the cap${u.cap ? ` of ${numHTML(fmt, { ...u.cap, v: u.cap.v * 100 }, { unit: '%', digits: 0 })}` : ''} or every eligible home is used.</div>${charts}`;
}

function insightBlock(ctx, st) {
  const { fmt } = ctx;
  const ins = st.index.insight;
  if (!ins || !Array.isArray(ins.tfPeakHour)) return '<div class="hb-sub">Not computed yet.</div>';
  const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  const mt = modeIndex(ins.tfPeakHour), mp = modeIndex(ins.priceMaxHour);
  const nT = ins.tfPeakHour.reduce((s, v) => s + v, 0), nP = (ins.priceMaxHour || []).reduce((s, v) => s + v, 0);
  const txt = mt !== null && mp !== null
    ? `Transformers most often hit their monthly peak at ${hours[mt]}:00 ${numHTML(fmt, { v: ins.tfPeakHour[mt], label: 'SIM' })} of ${numHTML(fmt, { v: nT, label: 'SIM' })}; the day's highest price most often falls at ${hours[mp]}:00 ${numHTML(fmt, { v: ins.priceMaxHour[mp], label: 'REAL' })} of ${numHTML(fmt, { v: nP, label: 'REAL' })} days.${mt !== mp ? ' A market-only dispatcher saves its energy for the price peak and leaves the load peak alone.' : ''}`
    : 'Not computed yet.';
  return `<div class="p2-insight">${txt}</div>
    ${chartHTML('bar', { categories: hours, series: [{ name: 'transformers', values: ins.tfPeakHour, cls: 's-with' }], label: 'SIM', xLabelEvery: 3, height: 90, caption: 'Hour of each transformer\'s monthly peak loading (SMART-DS 2018 shapes)', title: 'transformer peak hour' })}
    ${chartHTML('bar', { categories: hours, series: [{ name: 'days', values: ins.priceMaxHour || [], cls: 's-price' }], label: 'REAL', xLabelEvery: 3, height: 90, caption: 'Hour of each August day\'s maximum LZ_NORTH price', title: 'price max hour' })}`;
}

/** The feeder-head (cable) reading for this combo's existing fleet, from index.referee.head (audit R2 M6):
 *  {x, own} when OpenDSS ran this combo's baseline, {x, own: false, from} for the Core D-26 run at the same policy and
 *  load when it did not, else null. */
export function headReading(index, combo) {
  const h = index && index.referee && index.referee.head;
  const c = parseCombo(combo);
  if (!h || !c) return null;
  const own = h[`baseline ${combo}`];
  if (own && own.maxPct && typeof own.maxPct.v === 'number') return { x: own.maxPct, own: true, from: combo };
  const from = `${c.policy}-core-d26-g${c.growth}`;
  const core = h[`baseline ${from}`];
  return core && core.maxPct && typeof core.maxPct.v === 'number' ? { x: core.maxPct, own: false, from } : null;
}
/** "today's load" or "+20% load" (HTML: the growth is an ASSUMPTION constant, so it carries its tag). */
function growthHTML(fmt, doc, index, growth) {
  if (growth === '0') return "today's load";
  const g = constLabelled(doc, 'GROWTH') || constLabelled(index, 'GROWTH');
  return g ? `+${numHTML(fmt, { ...g, v: g.v * 100 }, { unit: '%', digits: 0 })} load` : 'the growth load';
}
function headLineHTML(ctx, st) {
  const { fmt } = ctx;
  const hr = headReading(st.index, st.combo);
  const c = parseCombo(st.combo);
  const gt = growthHTML(fmt, st.doc, st.index, c.growth);
  if (!hr) return '';
  const over = hr.x.v > 100;
  const val = `${numHTML(fmt, hr.x, P)} of its rating`;
  const txt = hr.own ? `${val} at its worst (OpenDSS month run, the batteries already here)` : `not OpenDSS-checked for this combo; the Core D-26 run at this load reads ${val}`;
  return `<div class="p2-cable ${over ? 'over' : ''}" data-tip="The feeder head: the cable leaving the substation, rated 370 A per conductor (SMART-DS, REAL). OpenDSS reads its current every 15 minutes of August.">${svg('cable', { size: 16 })}<span><b>Feeder cable at ${gt}:</b> ${txt}${over ? '. Over its rating' : ''}.</span></div>`;
}

/** The existing fleet, from THIS combo's own headline and its counterpart's (audit R2 M2), with OpenDSS's battery-caused
 *  count where the referee ran that baseline (audit L9). The "no batteries" row comes from the index, which is for
 *  today's load only. */
function fleetBlock(ctx, st) {
  const { fmt } = ctx;
  const c = parseCombo(st.combo);
  const T = st.index.fleetCounterfactualTotals || {};
  const ref = (st.index.referee && st.index.referee.baselineCausedNormal) || {};
  const pill = '<span class="p2-badge ok sm" title="the OpenDSS referee ran this baseline month (sim.referee)">✓ OpenDSS</span>';
  const cell = (x, o = {}) => `<td class="n">${x && fmt.isLabelled(x) ? numHTML(fmt, x, o) : 'n/a'}</td>`;
  const causedCell = (id, x) => {
    const r = ref[id];
    if (r && fmt.isLabelled(r)) {
      const same = x && x.v === r.v;
      return `<td class="n">${numHTML(fmt, r)}${pill}${!same && x && fmt.isLabelled(x) ? ` <span class="hb-sub">(screening ${numHTML(fmt, x)}${isScreening(x) ? '' : SCREEN_CHIP})</span>` : ''}</td>`;
    }
    return `<td class="n">${x && fmt.isLabelled(x) ? numHTML(fmt, x) + (isScreening(x) ? '' : SCREEN_CHIP) : 'n/a'}</td>`;
  };
  const rowOf = (doc, name) => {
    if (!doc || !doc.headline) return '';
    const h = doc.headline;
    return `<tr><td>${esc(name)}</td>${cell(h.h100, { digits: 1 })}${cell(h.normalEvents)}${causedCell(doc.combo || comboId({ ...c, policy: name.startsWith('naive') ? 'naive' : 'aware' }), h.causedNormal)}${cell(h.emergencyN)}</tr>`;
  };
  const none = c.growth === '0' && T.none
    ? `<tr><td>no batteries</td>${cell(T.none.h100, { digits: 1 })}${cell(T.none.normalEvents)}<td class="n">none</td>${cell(T.none.emergencyN)}</tr>`
    : `<tr><td>no batteries</td><td class="n" colspan="4"><span class="hb-sub">not computed at ${growthHTML(fmt, st.doc, st.index, c.growth)}</span></td></tr>`;
  return `<table class="p2-rank"><thead><tr><th>existing fleet</th><th>h above nameplate, all tfs</th><th>normal-tier events</th><th>caused by batteries</th><th>emergency intervals</th></tr></thead>
    <tbody>${none}${rowOf(st.naive, 'naive dispatch')}${rowOf(st.aware, 'feeder-aware')}</tbody></table>
    <div class="hb-sub">This setting's own month (${esc(c.cls === 'legacy' ? 'Legacy' : 'Core')} · ${esc(c.rule === 'd26' ? 'D-26 onset' : 'cheapest hours')} · ${growthHTML(fmt, st.doc, st.index, c.growth)}). "Caused by batteries": a normal-tier event while the transformer's batteries charge or back-feed.</div>
    ${headLineHTML(ctx, st)}`;
}

function marketBlock(ctx, st) {
  const { fmt } = ctx;
  const cl = st.index.cliffs;
  let out = '';
  if (Array.isArray(st.index.price)) {
    const pl = (st.index.series && st.index.series.price && st.index.series.price.label) || 'REAL';
    out += chartHTML('price', { price: st.index.price, label: pl, caption: `ERCOT RTM LZ_NORTH, ${st.index.month}, 15-minute settlement prices`, title: 'august prices', height: 60 });
  }
  if (cl && cl.count) {
    out += `<div class="p2-insight">${numHTML(fmt, cl.count)} price cliffs in ${esc(cl.period || '')}; ${numHTML(fmt, cl.evening)} in the evening, while home load is still high. Each would synchronize a market-only fleet.</div>`;
    if (Array.isArray(cl.events)) out += chartHTML('cliff', { events: cl.events, period: cl.period, label: cl.count.label || 'DERIVED', caption: `Rule: ${cl.rule || ''}. Accent = evening`, title: 'price cliffs' });
  }
  return out || '<div class="hb-sub">Not computed yet.</div>';
}

/** Where the ASSUMPTION protection rule operates in the month (naive): candidate placements (combo protectionCases)
 *  and the existing fleet (index.fleetProtection). Dark homes only where the data lists them. */
function protectionBlock(ctx, st) {
  const { fmt, topology } = ctx;
  const cs = Array.isArray(st.naive && st.naive.protectionCases) ? st.naive.protectionCases : [];
  const fp = st.index.fleetProtection;
  const fl = fp && Array.isArray(fp.naive) && inIndexScope(st.index, st.combo) ? fp.naive : [];
  if (!cs.length && !fl.length) return '';
  const dark = (list) => (list && list.length ? `<b>dark:</b> ${esc(list.map((i) => homeLabel(topology, i)).join(', '))}` : 'no battery-less home behind it (nothing goes dark)');
  const rows = [
    ...cs.map((c) => `<li>New battery at ${esc(c.label || homeLabel(topology, c.home))} on ${esc(tfName(topology, c.tf))}, managed naively: peak ${fmt.isLabelled(c.peakWithPct) ? numHTML(fmt, c.peakWithPct, P) : 'n/a'} (${esc(c.t || '')}); ${dark(c.homesDark)}.</li>`),
    ...fl.map((c) => `<li>Existing fleet managed naively, ${esc(tfName(topology, c.tf))}: peak ${fmt.isLabelled(c.peakPct) ? numHTML(fmt, c.peakPct, P) : 'n/a'} (${esc(c.t || '')}); ${dark(c.homesDark)}${(c.homesOnBattery || []).length ? `; on battery: ${esc(c.homesOnBattery.map((i) => homeLabel(topology, i)).join(', '))}` : ''}.</li>`),
  ];
  return `<div class="p2-protect"><div class="hb-sub">Rule ${fmt.chip('ASSUMPTION', (fp && fp.rule) || 'fuse rule, round-1 world-sim')}: battery-less homes behind an open transformer go dark; battery homes island on their own battery and stay lit. Only the homes the data lists are shown.</div>
    <ul class="p2-fliplist">${rows.join('')}</ul></div>`;
}

function refereeBlock(ctx, st) {
  const { fmt } = ctx;
  const r = st.index.referee;
  if (!r) return '';
  if (!r.runs) return `<div class="p2-ref screen">OpenDSS referee: not run yet for this build. Every number here is screening (surrogate).</div>`;
  return `<div class="p2-ref ok">OpenDSS referee: ${esc(r.runs)} month runs · surrogate error p99 ${r.errorPts && r.errorPts.p99 ? numHTML(fmt, r.errorPts.p99, { digits: 2, unit: ' pts' }) : 'n/a'} (max ${r.errorPts && r.errorPts.max ? numHTML(fmt, r.errorPts.max, { digits: 2, unit: ' pts' }) : 'n/a'}) · tier agreement ${r.tierAgreementPct ? numHTML(fmt, r.tierAgreementPct, { digits: 1, unit: '%' }) : 'n/a'}</div>`;
}

/** Audit R2 M1: the P1 hand-off reads THIS combo's own ranking row on the unrelieved transformer and its own baseline
 *  peak. index.bridge (built for Core/D-26/today only) is read only inside that scope, for a home outside the top 50;
 *  elsewhere the card says "not in this combo's top 50". */
export function handoffRow(st, tf) {
  const e = (st.doc.ranking || []).find((x) => x.tf === tf) || null;
  const basePeak = bulk(st.doc, 'baseline', st.doc.baseline.peak[tf] / 10);
  if (e) {
    const od = odssPeaks(e);
    return { kind: 'ranked', entry: e, rank: e.rank, home: e.home, without: od ? od.before : basePeak, with: peakWithShown(e), odss: !!od,
      screenWithout: od ? null : basePeak, viol: !!(e.noNewViolation && e.noNewViolation.v === false) };
  }
  const pol = (parseCombo(st.combo) || {}).policy;
  const br = inIndexScope(st.index, st.combo) && Array.isArray(st.index.bridge) ? st.index.bridge.find((x) => x.tf === tf) : null;
  const bp = br && br[pol];
  if (bp && bp.peakWithPct) {
    return { kind: 'bridge', rank: bp.rank, home: bp.home, without: bp.peakWithoutPct || basePeak, with: bp.peakWithPct, odss: false,
      viol: !!(bp.noNewViolation && bp.noNewViolation.v === false), h100Without: bp.h100Without, h100With: bp.h100With };
  }
  return { kind: 'absent', without: basePeak };
}

function handoffBlock(ctx, st) {
  const { topology, fmt } = ctx;
  const un = st.p1meta && Array.isArray(st.p1meta.unrelieved) ? st.p1meta.unrelieved : [];
  if (!un.length) return '';
  const items = un.map((u) => {
    const d = u.driver || {};
    const drv = d.profile ? ` Driver: ${esc(d.label || '')} (SMART-DS profile ${esc(d.profile)}${sharedNames(d.sharedWith).length ? `, the same profile as ${esc(sharedNames(d.sharedWith).join(', '))}` : ''})${d.kwAtPeak ? `, ${numHTML(fmt, d.kwAtPeak, { unit: ' kW', digits: 1 })} at the peak` : ''}.` : '';
    const r = handoffRow(st, u.tf);
    let link;
    if (r.kind === 'absent') {
      link = ` Month peak here without a new battery: ${numHTML(fmt, r.without, P)}. No candidate on it in this combo's top 50.`;
    } else {
      const hid = topology.homes[r.home] ? topology.homes[r.home].id : null;
      const peaks = r.odss
        ? `OpenDSS month run: month peak ${numHTML(fmt, r.without, P)} without, ${numHTML(fmt, r.with, P)} with`
        : `month peak ${numHTML(fmt, r.without, P)} without, ${numHTML(fmt, r.with, P)}${isScreening(r.with) ? '' : SCREEN_CHIP} with`;
      link = ` A new battery here (${esc(homeLabel(topology, r.home))}, rank ${esc(r.rank)} under this policy${r.kind === 'bridge' ? ', one entry per transformer' : ''}): ${peaks}${r.viol ? '; it adds a violation (where NOT to put it)' : ''}. <a href="${ctx.href({ view: 'p2', combo: st.combo, home: hid })}">Open its card</a>.`;
    }
    return `<li><b>${esc(tfName(topology, u.tf))}</b>: ${esc(u.reason || 'unrelieved')}.${drv}${link}</li>`;
  }).join('');
  return `<div class="p2-handoff"><div class="hb-sub">Left unrelieved on ${esc(st.p1meta.day || 'the P1 day')} (P1): no battery sits on it.</div><ul>${items}</ul></div>`;
}

/** Build the P2 scene: the shared scene model (L4) with numbered candidate pins and greedy placements as new
 *  columns. L4's buildSceneModel takes `pins` [{home, text}] and `placed` [{home}]; with an older model that ignores
 *  them, the pins and placements are appended to `labels` / `batteries` here (same fields). */
export function p2SceneModel(ctx, st) {
  const { topology, sceneModel } = ctx;
  const pins = (st.doc.ranking || []).slice(0, 10).filter((e) => topology.homes[e.home]).map((e) => ({ home: e.home, text: `#${e.rank}` }));
  const placed = (st.doc.greedy || []).slice(0, st.n).filter((g) => topology.homes[g.home]).map((g) => ({ home: g.home, k: g.k }));
  const model = sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame: sceneModel.frameFromP2(st.doc), view: 'p2', theme: ctx.theme, pins, placed });
  const ink = model.ink || (ctx.theme === 'dark' ? [228, 235, 230] : [16, 22, 19]);
  const accent = model.accent || (ctx.theme === 'dark' ? [92, 196, 190] : [11, 107, 111]);
  model.labels = model.labels || [];
  model.batteries = model.batteries || [];
  if (!model.labels.some((l) => l.pin)) {
    for (const p of pins) model.labels.push({ key: 'pin', text: p.text, position: topology.homes[p.home].lonlat, color: ink, pin: true, home: p.home });
  }
  if (!model.batteries.some((b) => b.placed)) {
    for (const p of placed) {
      const h = topology.homes[p.home];
      model.batteries.push({ j: -1, home: p.home, position: [h.lonlat[0] + 0.00012, h.lonlat[1]], height: 30, soc: 0.9, kw: 0, state: 'N', color: [...accent, 255], placed: true });
    }
  }
  // The P1 -> P2 handoff: merged into the transformer's own label (a separate label at the same spot overlapped it and
  // read "P1▸ T-240 ved" in judge R1 F8). Only when the transformer has no label of its own is a new one added.
  for (const u of (st.p1meta && st.p1meta.unrelieved) || []) {
    const t = topology.transformers[u.tf];
    if (!t) continue;
    const own = model.labels.find((l) => !l.pin && !l.handoff && Array.isArray(l.position)
      && l.position[0] === t.lonlat[0] && l.position[1] === t.lonlat[1]);
    if (own) {
      own.text = `${own.text} · P1: unrelieved`;
      own.short = `${own.short || tfName(topology, u.tf)} · P1: unrelieved`;
      own.handoff = true;
      own.tf = u.tf;
    } else {
      model.labels.push({ key: 'handoff', text: `${tfName(topology, u.tf)} · P1: unrelieved`, short: `${tfName(topology, u.tf)} · P1: unrelieved`,
        position: [t.lonlat[0], t.lonlat[1], 16], color: ink, handoff: true, tf: u.tf });
    }
  }
  return model;
}

const SEC_KEY = 'hb.sec.p2.';
function readOpen(id) { try { const v = globalThis.localStorage && globalThis.localStorage.getItem(SEC_KEY + id); return v === null || v === undefined ? null : v === '1'; } catch (e) { return null; } }
function writeOpen(id, on) { try { if (globalThis.localStorage) globalThis.localStorage.setItem(SEC_KEY + id, on ? '1' : '0'); } catch (e) { /* per-viewer convenience only */ } }

/** The sections below the front cards (UX_SPEC_R2 7.2), in order. Pure: returns [{id, title, icon, teaser, body, beat}]. */
export function p2Sections(ctx, st) {
  const { fmt, topology } = ctx;
  const c = parseCombo(st.combo);
  const u = st.index.usefulCapacity;
  const cp = u ? capacityParts(u, topology) : null;
  const unTf = st.p1meta && Array.isArray(st.p1meta.unrelieved) && st.p1meta.unrelieved[0] ? st.p1meta.unrelieved[0].tf : null;
  const hr = unTf === null ? null : handoffRow(st, unTf);
  const handTeaser = hr ? `${esc(tfName(topology, unTf))}: ${hr.kind === 'absent' ? 'no candidate in the top 50' : `rank ${esc(hr.rank)} here`}` : '';
  const fh = u && u.feederHead && u.feederHead.naive && u.feederHead.naive.overAt;
  const capTeaser = u ? `${fh ? `naive: cable over at ${numHTML(fmt, fh)}` : 'naive'} · aware ${u.aware ? numHTML(fmt, u.aware) : 'n/a'}${cp && cp.awareOk ? ' ✓' : ''}` : '';
  const ins = st.index.insight;
  const mt = ins && Array.isArray(ins.tfPeakHour) ? modeIndex(ins.tfPeakHour) : null, mp = ins ? modeIndex(ins.priceMaxHour) : null;
  // teasers stay words where the number is one click away (UX_SPEC_R2 2.5: fewer tags above the fold)
  const insTeaser = mt !== null && mp !== null ? (mt !== mp ? 'at different hours' : 'at the same hour') : '';
  const hrd = headReading(st.index, st.combo);
  const fleetTeaser = hrd ? `cable ${numHTML(fmt, hrd.x, P)}${hrd.own ? '' : ' (Core D-26)'}` : '';
  const cl = st.index.cliffs;
  const r = st.index.referee;
  const prot = protectionBlock(ctx, st);
  const secs = [
    { id: 'p1', title: 'From P1: still at risk', icon: 'warn', teaser: handTeaser, body: handoffBlock(ctx, st) },
    { id: 'flip', title: 'The flip in numbers', icon: 'turns', teaser: st.index.flip && st.index.flip.top10Overlap ? `${numHTML(fmt, st.index.flip.top10Overlap)} of ten shared${inIndexScope(st.index, st.combo) ? '' : ' (Core D-26)'}` : '', body: flipBlock(ctx, st), beat: 'p2-flip' },
    { id: 'cands', title: 'All candidates', icon: 'list', teaser: 'the top fifteen', body: rankingTable(ctx, st) },
    { id: 'greedy', title: 'Place up to ten batteries', icon: 'cabinet', teaser: 'use the slider above', body: greedyBlock(ctx, st) },
    { id: 'capacity', title: 'How many batteries fit?', icon: 'padmount', teaser: capTeaser, body: capacityBlock(ctx, st), beat: 'p2-capacity' },
    ...(prot ? [{ id: 'protect', title: 'Where lights could go out', icon: 'fuse', teaser: fmt.chip('ASSUMPTION', 'the fuse rule, round-1 world-sim'), body: prot }] : []),
    { id: 'insight', title: 'When transformers peak vs when prices peak', icon: 'clock', teaser: insTeaser, body: insightBlock(ctx, st), beat: 'insight' },
    { id: 'fleet', title: 'The batteries already here', icon: 'battery', teaser: fleetTeaser, body: fleetBlock(ctx, st) },
    { id: 'prices', title: 'Real August prices and cliffs', icon: 'price', teaser: cl && cl.count ? 'ERCOT LZ_NORTH' : '', body: marketBlock(ctx, st) },
    { id: 'check', title: 'How we check', icon: 'check', teaser: r && r.runs ? `OpenDSS: ${esc(r.runs)} month runs` : 'screening only',
      body: `${refereeBlock(ctx, st)}<div class="hb-sub">The next-battery score is not a Base product: Base schedules installs by demand; this adds the grid lens. Screening numbers (≈) come from a per-transformer surrogate calibrated against OpenDSS; cards carry OpenDSS numbers (✓) where the referee has run. Growth ${fmt.chip('ASSUMPTION', 'EVs and heat pumps')}, the fleet placement ${fmt.chip('ASSUMPTION', 'seed 17263, the prototype placement')} and the curtailment cap ${fmt.chip('ASSUMPTION')} are named constants.</div>` },
  ];
  void c;
  return secs;
}

export async function mount(el, ctx) {
  const { data, link, topology } = ctx;
  const index = await data.loadP2Index();
  const ids = (index.combos || []).map((c) => (typeof c === 'string' ? c : c.id));
  const combo = link.combo && ids.includes(link.combo) ? link.combo : index.default;
  const otherCombo = ids.includes(counterpart(combo)) ? counterpart(combo) : null;
  const [doc, other, p1meta] = await Promise.all([
    data.loadP2Combo(combo),
    otherCombo ? data.loadP2Combo(otherCombo) : Promise.resolve(null),
    data.getOptional('p1/meta.json').catch(() => null),        // real P1 only: the handoff never marks the page fixture
  ]);
  const cur = parseCombo(combo);
  const aware = cur.policy === 'aware' ? doc : other;
  const naive = cur.policy === 'naive' ? doc : other;
  const n = link.n || 1;   // "the next battery"; ?n= (1-10) steps the greedy sequence
  let sel = findCandidate(doc, topology, link.home);
  if (!sel.entry && sel.home < 0 && doc.ranking && doc.ranking.length) sel = { entry: doc.ranking[0], via: 'home', home: doc.ranking[0].home };
  const st = { index, doc, combo, other, otherCombo, aware, naive, p1meta, sel, n };

  const scene = ctx.scene;
  scene.update(p2SceneModel(ctx, st));
  scene.camera(link.cam || 'feeder');
  scene.onPick((info) => {
    const o = info && info.object;
    if (!o) return;
    const hi = typeof o.home === 'number' ? o.home : (o.id && homeIndexById(topology, o.id) >= 0 ? homeIndexById(topology, o.id) : (typeof o.i === 'number' && info.layer === 'homes' ? o.i : -1));
    if (hi >= 0 && topology.homes[hi] && !topology.homes[hi].battery) ctx.go({ view: 'p2', combo, home: topology.homes[hi].id });
  });

  const fmt = ctx.fmt;
  const clsLabel = (k, t) => {
    const c = constLabelled(doc, k === 'core' ? 'CORE_POWER_KW' : 'LEGACY_POWER_KW');
    return c ? `${esc(t)} ${esc(fmt.fmtValue(c, { unit: ' kW' }))}` : esc(t);
  };
  const growthLabel = (k, t) => {
    const g = constLabelled(doc, 'GROWTH') || constLabelled(index, 'GROWTH');
    return k !== '0' && g ? `+${esc(fmt.fmtValue({ ...g, v: g.v * 100 }, { digits: 0 }))}% ${esc(t)}` : esc(t);
  };
  const beat = link.beat ? await beatBarHTML(ctx).catch((e) => { ctx.reportError(e); return ''; }) : '';

  // Which section opens: the beat's section; "From P1" when ?home= is on the unrelieved transformer; otherwise the
  // viewer's own last state (localStorage, per viewer; the page renders the same without it).
  const beatSec = link.beat ? BEAT_SECTION[link.beat] : null;
  const homeIdx = link.home ? homeIndexById(topology, link.home) : -1;
  const unTfs = new Set(((p1meta && p1meta.unrelieved) || []).map((u) => u.tf));
  const secs = p2Sections(ctx, st).map((s) => {
    let open = readOpen(s.id) === true;
    if (s.id === 'p1' && homeIdx >= 0 && topology.homes[homeIdx] && unTfs.has(topology.homes[homeIdx].tf)) open = true;
    if (beatSec && s.id === beatSec) open = true;
    return { ...s, open };
  });
  const g20 = cur.growth !== '0' ? headLineHTML(ctx, st) : '';

  el.classList.add('p2');
  el.innerHTML = `${beat}
    <h1>Where the next battery goes</h1>
    <div class="hb-sub p2-sub">${esc(monthName(index.month))} what-if · prices ${fmt.chip('REAL', 'ERCOT RTM SPP LZ_NORTH 15-min')} · loads SMART-DS 2018, same calendar date ${fmt.chip('SIM')} ${fmt.chip('ASSUMPTION', '2018 weather-year load paired with 2026 prices by calendar date')}</div>
    <div class="p2-controls">
      <div><span>policy</span>${seg(ctx, cur, 'policy', POLICIES)}</div>
      <div><span>battery</span>${seg(ctx, cur, 'cls', CLASSES, clsLabel)}</div>
      <div><span>charge rule</span>${seg(ctx, cur, 'rule', RULES)}</div>
      <div><span>load</span>${seg(ctx, cur, 'growth', GROWTHS, growthLabel)}</div>
      <div class="p2-nrow"><span>batteries to add</span><input type="range" min="1" max="10" step="1" value="${n}" class="p2-n" aria-label="batteries to add"><output class="p2-nout">${esc(n)}</output></div>
    </div>
    ${cur.policy === 'naive' ? `<div class="p2-naive-note">Naive: ERCOT's one number per zone, split with no feeder check ${fmt.chip('ASSUMPTION', "Base's real split is not public (build prompt 12 Q5). Never implies Base charges this way today.")}</div>` : ''}
    <div class="p2-card-anchor" aria-hidden="true"></div>
    ${candidateCard(ctx, st)}
    ${flipLineHTML(ctx, st)}
    ${g20}
    <div class="p2-secs">${secs.map(secHTML).join('')}</div>`;

  // A beat opens its section, then scrolls it (or, on ?home=, the candidate card) into view below the sticky bar.
  const target = link.beat ? el.querySelector(`[data-beat="${String(link.beat).replace(/[^a-z0-9-]/gi, '')}"]`)
    : (link.home ? el.querySelector('.p2-card-anchor') : null);
  if (target && target.scrollIntoView) {
    if (target.tagName === 'DETAILS') target.open = true;
    const bar = el.querySelector('.beat-bar');
    target.style.scrollMarginTop = `${bar ? bar.offsetHeight + 8 : 0}px`;
    target.scrollIntoView({ block: 'start' });
  }
  if (typeof el.querySelectorAll === 'function') {
    for (const d of el.querySelectorAll('details.p2-sec')) d.addEventListener('toggle', () => writeOpen(d.dataset.sec, d.open));
  }
  // closed sections and "Why this home" keep their bodies out of the live DOM until opened (lazyDetails)
  lazyDetails(el, 'details.p2-sec', '.hb-sec-body');
  lazyDetails(el, 'details.p2-why', '.p2-why-body');
  const range = el.querySelector('.p2-n');
  if (range) {
    range.addEventListener('input', () => { el.querySelector('.p2-nout').textContent = range.value; });
    range.addEventListener('change', () => ctx.go({ view: 'p2', combo, home: link.home, n: +range.value }));
  }
}
