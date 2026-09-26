// ui/panels/p2.js (L5): P2, "where the next battery goes". A month-long what-if on REAL ERCOT LZ_NORTH prices
// (August 2026) and SMART-DS 2018 loads (SIM). Everything is precomputed by sim.p2_build (L3); this view only looks
// results up and never re-derives tiers (build prompt 5.3, 5.6).
//
//   mount(el, ctx) -> Promise     ctx as docs/contracts.md A.9
//
// Pure helpers are exported for ui/test/p2.test.js (no DOM at import time).
import { chartHTML, modeIndex } from '../lib/charts.js';
import { beatBarHTML } from './more.js';

export const POLICIES = [['aware', 'feeder-aware'], ['naive', 'naive']];
export const CLASSES = [['core', 'Core'], ['legacy', 'Legacy']];
export const RULES = [['d26', 'D-26 onset'], ['cheapest', 'cheapest hours']];
export const GROWTHS = [['0', 'today'], ['20', 'growth']];

// Display rule for the flip headline (ASSUMPTION, shown on screen): the sentence "How you charge decides where the
// next battery goes" appears only when naive and aware share at most this many of their top 10.
export const FLIP_HEADLINE_MAX_OVERLAP = 5;

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

/** A labelled bulk value: bulk arrays carry their label once in the envelope's `series`. */
export function bulk(doc, key, v, cite) {
  const s = doc && doc.series && doc.series[key];
  const label = s && s.label ? s.label : 'SIM';
  return cite ? { v, label, cite } : { v, label };
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

/** The flip verdict from index.flip (labelled numbers). */
export function flipVerdict(flip) {
  const ov = flip && flip.top10Overlap;
  if (!ov || typeof ov.v !== 'number') return { supports: false, headline: null };
  const un = flip.untied && flip.untied.top10Overlap;
  const unOk = !un || typeof un.v !== 'number' || !(flip.untied.n && flip.untied.n.v >= 10) || un.v <= FLIP_HEADLINE_MAX_OVERLAP;
  const supports = ov.v <= FLIP_HEADLINE_MAX_OVERLAP && unOk;
  return { supports, headline: supports ? 'How you charge decides where the next battery goes.' : null };
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

function driverParts(driver) {
  if (!driver || !driver.profile) return null;
  const shared = (driver.sharedWith || []).filter(Boolean);
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
  const month = (index && index.month) || 'the month';
  const parts = [];
  const beforeH = entry.before && entry.before.h100 ? entry.before.h100 : bulk(doc, 'baseline', doc.baseline.h100[tf]);
  const beforePeak = entry.before && entry.before.peakPct ? entry.before.peakPct : bulk(doc, 'baseline', doc.baseline.peak[tf] / 10);
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
  parts.push(`With a ${clsName} at ${homeLabel(topology, entry.home)} under ${pol}: `);
  if (entry.after && entry.after.h100) parts.push({ ...entry.after.h100, unit: ' h', digits: 2 }, ' above nameplate, ');
  if (entry.peakWithPct) parts.push('peak ', { ...entry.peakWithPct, unit: '%', digits: 1 }, ', ');
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

function partText(p, fmt) { return typeof p === 'string' ? p : fmt.fmt(p, { unit: p.unit, digits: p.digits, money: p.money }); }
function partHTML(p, fmt) { return typeof p === 'string' ? esc(p) : fmt.fmtHTML(p, { unit: p.unit, digits: p.digits, money: p.money }); }
export const counterfactualText = (args, fmt) => counterfactualParts(args).map((p) => partText(p, fmt)).join('');
export const counterfactualHTML = (args, fmt) => counterfactualParts(args).map((p) => partHTML(p, fmt)).join('');

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
  out.push(`<div class="p2-legend"><span class="hs-b0 sw"></span>at or below nameplate <span class="hs-b1 sw"></span>over nameplate <span class="hs-b2 sw"></span>over the normal rating <span class="hs-b4 sw"></span>over the emergency rating (bands, not tier events)</div>`);
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

function candidateCard(ctx, st) {
  const { topology, fmt } = ctx;
  const { doc, index, combo, sel, other, otherCombo } = st;
  const e = sel.entry;
  if (!e) {
    if (sel.home < 0) return '<div class="p2-card"><div class="hb-sub">No candidate selected.</div></div>';
    const h = topology.homes[sel.home];
    const peak = bulk(doc, 'baseline', doc.baseline.peak[h.tf] / 10);
    return `<div class="p2-card"><h3>${esc(h.label)} · ${esc(tfName(topology, h.tf))}</h3>
      <div class="hb-sub">${h.battery ? 'This home already has a battery.' : 'Not in this combo\'s top 50.'} Its transformer's month peak without a new battery: ${fmt.fmtHTML(peak, { unit: '%', digits: 1 })}.</div></div>`;
  }
  const t = topology.transformers[e.tf];
  const kva = { v: t.kva, label: 'REAL', cite: 'SMART-DS Transformers.dss' };
  const badge = e.opendss
    ? '<span class="p2-badge ok" title="sim.referee: OpenDSS month run">OpenDSS-checked</span>'
    : '<span class="p2-badge screen" title="surrogate only (sim.surrogate); not yet refereed by OpenDSS">screening</span>';
  const metrics = labelledPairs(e, fmt.isLabelled).filter(([k]) => METRIC_NAMES[k])
    .map(([k, v]) => `<div class="p2-m"><span>${esc(METRIC_NAMES[k][0])}</span><b>${fmt.fmtHTML(v, METRIC_NAMES[k][1])}</b></div>`).join('');
  const odss = e.opendss ? ['before', 'after'].map((w) => {
    const pairs = labelledPairs(e.opendss[w], fmt.isLabelled);
    return pairs.length ? `<div class="p2-m"><span>OpenDSS ${w}</span><b>${pairs.map(([k, v]) => `${esc(k)} ${fmt.fmtHTML(v, { digits: 1 })}`).join(' · ')}</b></div>` : '';
  }).join('') : '';
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
  const toggle = otherCombo
    ? `<a class="p2-toggle" href="${ctx.href({ view: 'p2', combo: otherCombo, home: homeId })}">Managed ${oc.policy === 'naive' ? 'naively' : 'feeder-aware'} instead: ${oRank ? `rank ${esc(oRank)}` : 'not in its top 50'}${oEntry && oEntry.noNewViolation && oEntry.noNewViolation.v === false ? ', adds a violation' : ''}</a>` : '';
  return `<div class="p2-card">
    <div class="p2-card-h"><h3>#${esc(e.rank)} ${esc(homeLabel(topology, e.home))} · ${esc(tfName(topology, e.tf))} · ${fmt.fmtHTML(kva, { unit: ' kVA' })}</h3>${badge}</div>
    <div class="p2-reason">${esc(e.reason || '')}</div>
    <p class="p2-cf">${counterfactualHTML({ entry: e, doc, index, topology, combo }, fmt)}</p>
    ${neighbour}
    <div class="p2-metrics">${metrics}${odss}</div>
    ${also}${tie}
    ${toggle}
    ${strips(e, doc, topology, fmt)}
  </div>`;
}

function rankingTable(ctx, st) {
  const { topology, fmt } = ctx;
  const { doc, sel } = st;
  const rows = (doc.ranking || []).slice(0, 15).map((e) => {
    const id = topology.homes[e.home] ? topology.homes[e.home].id : '';
    const on = sel.entry && sel.entry.rank === e.rank;
    const pw = e.peakWithPct ? fmt.fmtValue(e.peakWithPct, { digits: 1 }) : 'n/a';
    const av = e.stressAvoidedH ? fmt.fmtValue(e.stressAvoidedH, { digits: 2 }) : 'n/a';
    const rv = e.revenueUSD ? fmt.fmtValue(e.revenueUSD, { money: true, digits: 0 }) : 'n/a';
    const viol = e.noNewViolation && e.noNewViolation.v === false ? ' p2-viol' : '';
    return `<tr class="${on ? 'on' : ''}${viol}"><td>${esc(e.rank)}</td><td><a href="${ctx.href({ view: 'p2', combo: st.combo, home: id })}">${esc(homeLabel(topology, e.home))}</a>${e.tieBroken ? '<sup title="place decided by id">id</sup>' : ''}</td>
      <td>${esc(tfName(topology, e.tf))}</td><td class="n">${esc(pw)}</td><td class="n">${esc(av)}</td><td class="n">${esc(rv)}</td><td>${e.opendss ? '<span class="p2-dot ok" title="OpenDSS-checked">●</span>' : '<span class="p2-dot" title="screening">○</span>'}</td></tr>`;
  }).join('');
  const lab = (k, fallback) => {
    const e = (doc.ranking || [])[0];
    return e && e[k] && e[k].label ? fmt.chip(e[k].label, e[k].cite) : fmt.chip(fallback);
  };
  return `<table class="p2-rank"><thead><tr><th>#</th><th>home</th><th>transformer</th><th>peak with, %${lab('peakWithPct', 'SIM')}</th><th>stress avoided, h${lab('stressAvoidedH', 'SIM')}</th><th>August value${lab('revenueUSD', 'DERIVED')}</th><th></th></tr></thead><tbody>${rows}</tbody></table>
    <div class="hb-sub">Rank rule, no weights: adds no new violation; stress hours avoided; peak with the battery, lowest first; value minus curtailment; home id. Rows in red add a violation. ● OpenDSS-checked, ○ screening.</div>`;
}

function greedyBlock(ctx, st) {
  const { topology, fmt } = ctx;
  const g = (st.doc.greedy || []).slice(0, st.n);
  if (!g.length) return '';
  const rows = g.map((x) => `<tr><td>${esc(x.k)}</td><td>${esc(homeLabel(topology, x.home))}</td><td>${esc(tfName(topology, x.tf))}</td>
    <td class="n">${x.feeder && x.feeder.normalTfs ? fmt.fmtValue(x.feeder.normalTfs) : 'n/a'}</td><td class="n">${x.feeder && x.feeder.emergencyTfs ? fmt.fmtValue(x.feeder.emergencyTfs) : 'n/a'}</td><td class="n">${x.feeder && x.feeder.h110 ? fmt.fmtValue(x.feeder.h110, { digits: 1 }) : 'n/a'}</td></tr>`).join('');
  const l0 = g[0].feeder && g[0].feeder.normalTfs ? fmt.chip(g[0].feeder.normalTfs.label, g[0].feeder.normalTfs.cite) : '';
  return `<h2>Greedy build: batteries placed one at a time</h2>
    <table class="p2-rank"><thead><tr><th>k</th><th>home</th><th>transformer</th><th>feeder tfs with a normal-tier event${l0}</th><th>emergency tfs${l0}</th><th>h above normal rating${l0}</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="hb-sub">Place #1, re-run its transformer, re-score, repeat (exact in the screening model).</div>`;
}

function flipBlock(ctx, st) {
  const { fmt, topology } = ctx;
  const f = st.index.flip || {};
  const v = flipVerdict(f);
  const ov = f.top10Overlap, sp = f.spearman, un = f.untied || {};
  const ties = st.index.ties && st.index.ties.byId;
  let body = '';
  if (ov) {
    body += `<div class="p2-flip-big"><span class="hb-big">${fmt.fmtHTML(ov)}</span><span class="hb-sub"> of 10 homes in both top tens (naive vs feeder-aware)</span></div>`;
    body += v.supports ? `<div class="p2-headline">${esc(v.headline)}</div>`
      : `<div class="p2-headline muted">The two rankings overlap by the number above; the flip is ${ov.v >= 10 ? 'not seen' : 'partial'} in this data.</div>`;
    body += `<div class="hb-sub">Spearman ${sp ? fmt.fmtHTML(sp, { digits: 2 }) : 'n/a'}${un.top10Overlap ? ` · untied candidates only: overlap ${fmt.fmtHTML(un.top10Overlap)}, Spearman ${un.spearman ? fmt.fmtHTML(un.spearman, { digits: 2 }) : 'n/a'} over ${un.n ? fmt.fmtHTML(un.n) : 'n/a'} candidates` : ''}${ties ? ` · places decided by id: ${fmt.fmtHTML(ties)} of ${esc(st.index.ties.of)}` : ''}</div>`;
    body += `<div class="hb-sub">Headline rule: shown only when the two top tens share at most ${esc(FLIP_HEADLINE_MAX_OVERLAP)} homes (display rule ${fmt.chip('ASSUMPTION', 'ui/panels/p2.js FLIP_HEADLINE_MAX_OVERLAP')}).</div>`;
  }
  if (st.aware && st.naive) {
    const a1 = (st.aware.ranking || [])[0], n1 = (st.naive.ranking || [])[0];
    const line = (e, from, to, toName) => {
      if (!e) return '';
      const r = rankOf(to, e.home);
      const te = findCandidate(to, topology, topology.homes[e.home] && topology.homes[e.home].id).entry;
      const viol = te && te.noNewViolation && te.noNewViolation.v === false;
      return `<li>${esc(from)} #1 ${esc(homeLabel(topology, e.home))} on ${esc(tfName(topology, e.tf))}: under ${esc(toName)} ${r ? `rank ${esc(r)}` : 'not in the top 50'}${viol ? ', and it adds a violation there (where NOT to put it)' : ''}.</li>`;
    };
    body += `<ul class="p2-fliplist">${line(a1, 'Feeder-aware', st.naive, 'naive dispatch')}${line(n1, 'Naive', st.aware, 'feeder-aware dispatch')}</ul>`;
  }
  return `<section class="p2-flip" data-beat="p2-flip"><h2>The flip: naive vs feeder-aware ranking</h2>${body || '<div class="hb-sub">Not computed yet.</div>'}</section>`;
}

function capacityBlock(ctx, st) {
  const { fmt } = ctx;
  const u = st.index.usefulCapacity;
  if (!u) return '';
  const stop = (x) => (x && x.stop ? ` <span class="hb-sub">(stops: ${esc(x.stop)})</span>` : '');
  let chart = '';
  const pick = (a) => (Array.isArray(a) ? a.map((x) => (typeof x === 'number' ? x : (x && typeof x === 'object'
    ? [x.v, x.curtailPct, x.normalTfs, x.value].find((y) => typeof y === 'number') : null))) : []);
  const cn = pick(u.curve && u.curve.naive), ca = pick(u.curve && u.curve.aware);
  const cl = (st.index.series && st.index.series.usefulCapacity && st.index.series.usefulCapacity.label) || (u.aware && u.aware.label) || 'SIM';
  if (cn.length > 1 || ca.length > 1) {
    chart = chartHTML('line', { series: [{ name: 'naive', values: cn, cls: 's-without' }, { name: 'feeder-aware', values: ca, cls: 's-with' }],
      label: cl, title: 'useful capacity', caption: 'Capacity curve as batteries are added in each policy\'s greedy order (grey naive, accent feeder-aware)' });
  }
  return `<h2 data-beat="p2-capacity">Useful capacity from an empty feeder</h2>
    <div class="p2-cap"><div><span class="hb-sub">naive</span><div class="hb-big">${u.naive ? fmt.fmtHTML(u.naive) : 'n/a'}</div>${stop(u.naive)}</div>
    <div><span class="hb-sub">feeder-aware</span><div class="hb-big">${u.aware ? fmt.fmtHTML(u.aware) : 'n/a'}</div>${stop(u.aware)}</div></div>
    <div class="hb-sub">Batteries added until the first battery-caused normal-tier event (naive) or curtailment above the cap (feeder-aware), or every home is used.</div>${chart}`;
}

function insightBlock(ctx, st) {
  const { fmt } = ctx;
  const ins = st.index.insight;
  if (!ins || !Array.isArray(ins.tfPeakHour)) return '';
  const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  const mt = modeIndex(ins.tfPeakHour), mp = modeIndex(ins.priceMaxHour);
  const nT = ins.tfPeakHour.reduce((s, v) => s + v, 0), nP = (ins.priceMaxHour || []).reduce((s, v) => s + v, 0);
  const txt = mt !== null && mp !== null
    ? `Transformers most often hit their monthly peak at ${hours[mt]}:00 ${fmt.fmtHTML({ v: ins.tfPeakHour[mt], label: 'SIM' })} of ${fmt.fmtHTML({ v: nT, label: 'SIM' })}; the day's highest price most often falls at ${hours[mp]}:00 ${fmt.fmtHTML({ v: ins.priceMaxHour[mp], label: 'REAL' })} of ${fmt.fmtHTML({ v: nP, label: 'REAL' })} days.${mt !== mp ? ' A market-only dispatcher saves its energy for the price peak and leaves the load peak alone.' : ''}`
    : 'Not computed yet.';
  return `<h2 data-beat="insight">When transformers peak vs when prices peak</h2><div class="p2-insight">${txt}</div>
    ${chartHTML('bar', { categories: hours, series: [{ name: 'transformers', values: ins.tfPeakHour, cls: 's-with' }], label: 'SIM', xLabelEvery: 3, height: 90, caption: 'Hour of each transformer\'s monthly peak loading (SMART-DS 2018 shapes)', title: 'transformer peak hour' })}
    ${chartHTML('bar', { categories: hours, series: [{ name: 'days', values: ins.priceMaxHour || [], cls: 's-price' }], label: 'REAL', xLabelEvery: 3, height: 90, caption: 'Hour of each August day\'s maximum LZ_NORTH price', title: 'price max hour' })}`;
}

function fleetBlock(ctx, st) {
  const { fmt } = ctx;
  const t = fleetTotals(st.index.fleetCounterfactual);
  if (!t.none) return '';
  const lab = (st.index.series && st.index.series.fleetCounterfactual && st.index.series.fleetCounterfactual.label) || 'SIM';
  const row = (k, name) => (t[k] ? `<tr><td>${esc(name)}</td><td class="n">${fmt.fmtHTML({ v: t[k].h100, label: lab }, { digits: 1 })}</td><td class="n">${fmt.fmtHTML({ v: t[k].normalTfs, label: lab })}</td><td class="n">${fmt.fmtHTML({ v: t[k].emergencyN, label: lab })}</td></tr>` : '');
  return `<h2>The existing fleet: did our batteries cause it?</h2>
    <table class="p2-rank"><thead><tr><th>existing fleet</th><th>h above nameplate, all tfs</th><th>tfs with a normal-tier event</th><th>emergency intervals</th></tr></thead>
    <tbody>${row('none', 'no batteries')}${row('naive', 'managed naively')}${row('aware', 'feeder-aware')}</tbody></table>`;
}

function marketBlock(ctx, st) {
  const { fmt } = ctx;
  const cl = st.index.cliffs;
  let out = '<h2>Real prices: the month and the cliffs</h2>';
  if (Array.isArray(st.index.price)) {
    const pl = (st.index.series && st.index.series.price && st.index.series.price.label) || 'REAL';
    out += chartHTML('price', { price: st.index.price, label: pl, caption: `ERCOT RTM LZ_NORTH, ${st.index.month}, 15-minute settlement prices`, title: 'august prices', height: 60 });
  }
  if (cl && cl.count) {
    out += `<div class="p2-insight">${fmt.fmtHTML(cl.count)} price cliffs in ${esc(cl.period || '')}; ${fmt.fmtHTML(cl.evening)} in the evening, while home load is still high. Each would synchronize a market-only fleet.</div>`;
    if (Array.isArray(cl.events)) out += chartHTML('cliff', { events: cl.events, period: cl.period, label: cl.count.label || 'DERIVED', caption: `Rule: ${cl.rule || ''}. Accent = evening`, title: 'price cliffs' });
  }
  return out;
}

function refereeBlock(ctx, st) {
  const { fmt } = ctx;
  const r = st.index.referee;
  if (!r) return '';
  if (!r.runs) return `<div class="p2-ref screen">OpenDSS referee: not run yet for this build. Every number here is screening (surrogate).</div>`;
  return `<div class="p2-ref ok">OpenDSS referee: ${esc(r.runs)} month runs · surrogate error p99 ${r.errorPts && r.errorPts.p99 ? fmt.fmtHTML(r.errorPts.p99, { digits: 2, unit: ' pts' }) : 'n/a'} (max ${r.errorPts && r.errorPts.max ? fmt.fmtHTML(r.errorPts.max, { digits: 2, unit: ' pts' }) : 'n/a'}) · tier agreement ${r.tierAgreementPct ? fmt.fmtHTML(r.tierAgreementPct, { digits: 1, unit: '%' }) : 'n/a'}</div>`;
}

function handoffBlock(ctx, st) {
  const { topology, fmt } = ctx;
  const un = st.p1meta && Array.isArray(st.p1meta.unrelieved) ? st.p1meta.unrelieved : [];
  if (!un.length) return '';
  const items = un.map((u) => {
    const best = (st.doc.ranking || []).find((e) => e.tf === u.tf);
    const d = u.driver || {};
    const drv = d.profile ? ` Driver: ${esc(d.label || '')} (SMART-DS profile ${esc(d.profile)}${(d.sharedWith || []).length ? `, the same profile as ${esc(d.sharedWith.join(', '))}` : ''})${d.kwAtPeak ? `, ${fmt.fmtHTML(d.kwAtPeak, { unit: ' kW', digits: 1 })} at the peak` : ''}.` : '';
    const link = best ? ` Best candidate here: <a href="${ctx.href({ view: 'p2', combo: st.combo, home: topology.homes[best.home].id })}">#${esc(best.rank)} ${esc(homeLabel(topology, best.home))}</a>.` : ' No candidate on it in this combo\'s top 50.';
    return `<li><b>${esc(tfName(topology, u.tf))}</b>: ${esc(u.reason || 'unrelieved')}.${drv}${link}</li>`;
  }).join('');
  return `<section class="p2-handoff"><h2>From P1: left unrelieved on ${esc(st.p1meta.day || 'the P1 day')}</h2><ul>${items}</ul></section>`;
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
  for (const u of (st.p1meta && st.p1meta.unrelieved) || []) {
    const t = topology.transformers[u.tf];
    if (t) model.labels.push({ key: 'handoff', text: 'P1: unrelieved', position: t.lonlat, color: ink, handoff: true, tf: u.tf });
  }
  return model;
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
  const n = link.n || 5;
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

  el.classList.add('p2');
  el.innerHTML = `${beat}
    <h1>P2 · where the next battery goes</h1>
    <div class="hb-sub">${esc(index.month)} what-if · prices ${fmt.chip('REAL', 'ERCOT RTM SPP LZ_NORTH 15-min')} · loads SMART-DS 2018, same calendar date ${fmt.chip('SIM')} ${fmt.chip('ASSUMPTION', '2018 weather-year load paired with 2026 prices by calendar date')}</div>
    <div class="p2-controls">
      <div><span>policy</span>${seg(ctx, cur, 'policy', POLICIES)}</div>
      <div><span>battery</span>${seg(ctx, cur, 'cls', CLASSES, clsLabel)}</div>
      <div><span>charge rule</span>${seg(ctx, cur, 'rule', RULES)}</div>
      <div><span>load</span>${seg(ctx, cur, 'growth', GROWTHS, growthLabel)}</div>
      <div><span>batteries to add</span><input type="range" min="1" max="10" step="1" value="${n}" class="p2-n" aria-label="batteries to add"><output class="p2-nout">${esc(n)}</output></div>
    </div>
    ${cur.policy === 'naive' ? `<div class="p2-naive-note">Naive: ERCOT's one number per zone split with no feeder check ${fmt.chip('ASSUMPTION', "Base's real split is not public (build prompt 12 Q5)")}. Never implies Base charges this way today.</div>` : ''}
    ${refereeBlock(ctx, st)}
    ${handoffBlock(ctx, st)}
    ${flipBlock(ctx, st)}
    <h2>The candidate</h2>
    ${candidateCard(ctx, st)}
    <h2>Ranked candidates</h2>
    ${rankingTable(ctx, st)}
    ${greedyBlock(ctx, st)}
    ${capacityBlock(ctx, st)}
    ${insightBlock(ctx, st)}
    ${fleetBlock(ctx, st)}
    ${marketBlock(ctx, st)}
    <div class="hb-note">The next-battery score is not a Base product: Base schedules installs by demand; this adds the grid lens. Screening numbers come from a per-transformer surrogate calibrated against OpenDSS; shortlist cards carry OpenDSS numbers when the referee has run. Growth ${fmt.chip('ASSUMPTION', 'EVs and heat pumps')}, the fleet placement ${fmt.chip('ASSUMPTION', 'seed 17263, the prototype placement')} and the curtailment cap ${fmt.chip('ASSUMPTION')} are named constants.</div>`;

  if (link.beat) {
    const t = el.querySelector(`[data-beat="${String(link.beat).replace(/[^a-z0-9-]/gi, '')}"]`);
    if (t && t.scrollIntoView) t.scrollIntoView({ block: 'start' });
  }
  const range = el.querySelector('.p2-n');
  if (range) {
    range.addEventListener('input', () => { el.querySelector('.p2-nout').textContent = range.value; });
    range.addEventListener('change', () => ctx.go({ view: 'p2', combo, home: link.home, n: +range.value }));
  }
}
