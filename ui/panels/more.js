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

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];
const isL = (x) => x !== null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
const L = (v, label, cite, o) => (v === null || v === undefined ? null : { v, label, ...(cite ? { cite } : {}), ...(o ? { o } : {}) });
const withO = (x, o) => (isL(x) ? { ...x, o } : null);
const get = (obj, path) => path.split('.').reduce((a, k) => (a == null ? a : a[k]), obj);

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
/** Max loading on A-D while their own batteries export (batKW < 0), from a p1 branch file. */
function backfeed(doc, topology) {
  if (!doc || !doc.focus || !doc.loading) return null;
  let best = null;
  for (const key of ['A', 'B', 'C', 'D']) {
    const f = doc.focus[key];
    if (!f || !Array.isArray(f.batKW)) continue;
    f.batKW.forEach((b, k) => {
      if (b >= 0) return;
      const pct = doc.loading[k] && doc.loading[k][f.tf];
      if (typeof pct === 'number' && (!best || pct > best.pct)) best = { pct, key, tf: f.tf, k };
    });
  }
  if (!best) return null;
  const lab = (doc.series && doc.series.loading && doc.series.loading.label) || 'SIM';
  return { ...best, v: best.pct / 10, label: lab, name: tfName(topology, best.tf) };
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
    return [{ ...x, o: { digits: 4, unit: ' pu' } }, typeof x.volts === 'number' ? ` (${x.volts.toFixed(1)} V)` : ''];
  }],
  naiveHead: [['p1meta'], (S) => withO(get(S, 'p1meta.summary.naive.feederHead'), { unit: '%', digits: 1 })],
  naiveBackfeedMax: [['p1:naive', 'topology'], (S) => { const b = backfeed(S['p1:naive'], S.topology); return b ? [{ v: b.v, label: b.label, o: { unit: '%', digits: 1 } }, ` on ${b.name} at ${stepTime(S['p1:naive'], b.k)}`] : null; }],
  awareBackfeedMax: [['p1:aware', 'topology'], (S) => { const b = backfeed(S['p1:aware'], S.topology); return b ? [{ v: b.v, label: b.label, o: { unit: '%', digits: 1 } }, ` on ${b.name}`] : 'no export above its cap'; }],
  faultCommsT: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost'); return e ? L(e.t, 'SIM') : null; }],
  faultCommsHome: [['p1meta', 'topology'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost'); return e ? homeLabel(S.topology, e.home) : null; }],
  faultCommsKW: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'comms_lost'); return e && typeof e.cmdKW === 'number' ? L(e.cmdKW, 'SIM', 'its last charge command', { unit: ' kW', digits: 1, signed: true }) : null; }],
  faultHotT: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'hot'); return e ? L(e.t, 'SIM') : null; }],
  faultStallT: [['p1meta'], (S) => { const e = (get(S, 'p1meta.events.aware_faults') || []).find((x) => x.kind === 'stall'); return e ? L(e.t, 'SIM') : null; }],
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
  capacityLow: [['topology'], (S) => constOf(S.p1meta, 'CAPACITY_BENCHMARK_USD_KW_MONTH', { money: true, digits: 2 }) || L(3.12, 'REAL', "Modo Apr 2026 ERCOT storage market benchmark (third party); docs/headroom/research_notes/grid_physics_orchestration_and_attacks.md:229", { money: true, digits: 2 }), ['p1meta']],
  capacityHigh: [['topology'], (S) => constOf(S.p1meta, 'CAPACITY_HIGH_USD_KW_MONTH', { money: true, digits: 2 }) || L(8.5, 'DERIVED', 'implied from an UNVERIFIED Austin Energy figure; docs/research-report.md:246, docs/design.md:160-161', { money: true, digits: 2 }), ['p1meta']],
  controllerView: [['p1meta'], (S) => { const c = get(S, 'p1meta.controllerView'); return c && c.text ? L(c.text, c.label || 'ASSUMPTION', c.cite) : null; }],
  msPerSolve: [['topology'], (S) => {
    const m = get(S, 'p1meta.engine.msPerSolve');
    const x = isL(m) && typeof m.v === 'number' ? m : scanEngine(S.engine, /solve/i);
    return x ? { ...x, o: { unit: ' ms', digits: 1 } } : null;
  }, ['p1meta', 'engine']],
  allocateLargest: [['topology'], (S) => { const h = scanEngine(S.engine, /100k|100000|1e5/i) || scanEngine(S.engine, /alloc/i); return h ? { ...h, o: { unit: ' µs', digits: 0 } } : null; }, ['engine']],
  candidates: [['p2index'], (S) => { const t = get(S, 'p2index.ties'); return t && typeof t.of === 'number' ? L(t.of, 'DERIVED', 'eligible homes without a battery') : null; }],
  refereeRuns: [['p2index'], (S) => { const r = get(S, 'p2index.referee'); return r && typeof r.runs === 'number' ? L(r.runs, 'SIM', 'sim.referee OpenDSS month runs') : null; }],
  refereeP99: [['p2index'], (S) => { const x = withO(get(S, 'p2index.referee.errorPts.p99'), { unit: ' pts', digits: 2 }); return x ? ['p99 ', x] : null; }],
  awareTop1: [['p2:' + DEFAULT_AWARE, 'topology'], (S) => { const e = get(S, `p2:${DEFAULT_AWARE}.ranking.0`); return e ? homeLabel(S.topology, e.home) : null; }],
  awareTop1Tf: [['p2:' + DEFAULT_AWARE, 'topology'], (S) => { const e = get(S, `p2:${DEFAULT_AWARE}.ranking.0`); return e ? tfName(S.topology, e.tf) : null; }],
  awareTop1UnderNaive: [['p2:' + DEFAULT_AWARE, 'p2:' + DEFAULT_NAIVE], (S) => {
    const a = get(S, `p2:${DEFAULT_AWARE}.ranking.0`), nd = S[`p2:${DEFAULT_NAIVE}`];
    if (!a || !nd) return null;
    const e = rankOf(nd, a.home);
    if (!e) return 'not in the naive top fifty';
    const viol = e.noNewViolation && e.noNewViolation.v === false;
    return [`naive rank `, L(e.rank, 'SIM', 'naive ranking'), viol ? ', and it adds a violation there (where not to put it)' : ''];
  }],
  flipHeadline: [['p2index'], (S) => {
    const f = get(S, 'p2index.flip.top10Overlap');
    if (!isL(f)) return null;
    return f.v <= 5 ? 'How you charge decides where the next battery goes.' : 'The rankings mostly agree in this data.';
  }],
  flipOverlap: [['p2index'], (S) => withO(get(S, 'p2index.flip.top10Overlap'))],
  flipSpearman: [['p2index'], (S) => withO(get(S, 'p2index.flip.spearman'), { digits: 2 })],
  capNaive: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.naive'))],
  capAware: [['p2index'], (S) => withO(get(S, 'p2index.usefulCapacity.aware'))],
  protectionCases: [['p2:' + DEFAULT_NAIVE], (S) => {
    const d = S[`p2:${DEFAULT_NAIVE}`];
    if (!d || !Array.isArray(d.ranking)) return null;
    return L(d.ranking.filter((e) => e.protectionWith && e.protectionWith.v === true).length, 'SIM', 'naive top-50 candidates where the ASSUMPTION fuse rule operates');
  }],
  insightTfHour: [['p2index'], (S) => { const h = modeHour(get(S, 'p2index.insight.tfPeakHour')); return h === null ? null : L(`${String(h).padStart(2, '0')}:00`, 'SIM', 'mode of the hour of each transformer\'s monthly peak'); }],
  insightPriceHour: [['p2index'], (S) => { const h = modeHour(get(S, 'p2index.insight.priceMaxHour')); return h === null ? null : L(`${String(h).padStart(2, '0')}:00`, 'REAL', 'mode of the hour of each August day\'s max LZ_NORTH price'); }],
  cliffCount: [['p2index'], (S) => withO(get(S, 'p2index.cliffs.count'))],
  cliffEvening: [['p2index'], (S) => withO(get(S, 'p2index.cliffs.evening'))],
};

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
/** The template with every placeholder removed: what the "no bare digits" test reads. */
export const stripPlaceholders = (tpl) => String(tpl || '').replace(PLACEHOLDER, '');

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
    if (!d && k !== 'engine' && ctx.data.isFixture && ctx.data.isFixture()) {
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
  if (isL(p)) return html ? fmt.fmtHTML(p, p.o || {}) : fmt.fmt(p, p.o || {});
  return html ? esc(String(p)) : String(p);
}

/** Resolve a caption template. html=true for the page; false gives "value LABEL" text (tests, docs). */
export function resolveCaption(tpl, S, fmt, { html = true } = {}) {
  return String(tpl || '').replace(PLACEHOLDER, (raw, inner) => {
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

/** The caption bar for the current ?beat=<id>, with a "next beat" stepper. */
export async function beatBarHTML(ctx) {
  const beats = beatsList(await ctx.data.loadBeats());
  const i = beats.findIndex((b) => b.id === ctx.link.beat);
  if (i < 0) return '';
  const b = beats[i];
  const S = await loadSources(ctx, sourcesFor([b.caption]));
  const next = beats[i + 1], prev = beats[i - 1];
  return `<div class="beat-bar" data-beat-id="${esc(b.id)}">
    <div class="beat-h"><span class="beat-t">${esc(b.t0)}–${esc(b.t1)}</span> <b>${esc(b.title)}</b>${b.label ? ctx.fmt.chip(b.label) : ''}
      <span class="beat-nav">${prev ? `<a href="${beatHref(prev)}" title="${esc(prev.title)}">‹ prev</a>` : ''}${next ? `<a href="${beatHref(next)}" title="${esc(next.title)}">next beat ›</a>` : ''}</span></div>
    <div class="beat-cap">${resolveCaption(b.caption, S, ctx.fmt)}</div></div>`;
}

/** For the shell or the P1 panel: put the caption bar at the top of the panel when ?beat= is set. */
export async function mountBeatBar(ctx, panelEl) {
  if (!ctx.link.beat) return;
  const el = panelEl || (typeof document !== 'undefined' && document.getElementById('panel'));
  if (!el || el.querySelector('.beat-bar')) return;
  const html = await beatBarHTML(ctx);
  if (html) el.insertAdjacentHTML('afterbegin', html);
}

// ---------------------------------------------------------------------------------------------------------------
// The payers (5.4.6): who pays today, and for what. REAL, sourced; never a price for local relief.
export const PAYERS = [
  { who: 'CoServ', mw: 100, what: 'peak shaving and arbitrage', dispatchPct: 80, cite: 'docs/research-report.md:215-224' },
  { who: 'GVEC', mw: 50, what: 'ERCOT summer four-coincident-peak and arbitrage', cite: 'docs/research-report.md:215-224' },
  { who: 'Austin Energy', mw: 40, what: 'system peak demand and wholesale prices (it dispatches)', cite: 'docs/research-report.md:215-224' },
  { who: 'El Paso Electric', mw: 10, what: 'local capacity constraints: the only local-constraint programme found, and it is outside ERCOT', cite: 'docs/research-report.md:59, 215-224' },
];

function moneyCard(ctx, S) {
  const { fmt } = ctx;
  const m = S.p1meta && S.p1meta.money;
  const f = (name) => { const p = evalFact(name, S); return p ? p.map((x) => renderPart(x, fmt, true)).join('') : '<span class="beat-na">(not built yet)</span>'; };
  const lines = [];
  if (m && m.energyValueUSD) {
    for (const k of ['naive', 'aware', 'aware_faults']) if (isL(m.energyValueUSD[k])) lines.push(`<tr><td>energy value, ${esc(k.replace('_', ' + '))}</td><td class="n">${fmt.fmtHTML(m.energyValueUSD[k], { money: true, digits: 0 })}</td></tr>`);
  }
  if (m && isL(m.costOfAwareness)) lines.push(`<tr><td>cost of awareness (naive − aware; may be negative)</td><td class="n">${fmt.fmtHTML(m.costOfAwareness, { money: true, digits: 0 })}</td></tr>`);
  for (const [k, v] of Object.entries(m || {})) {
    if (k === 'energyValueUSD' || k === 'costOfAwareness' || !isL(v) || typeof v.v !== 'number') continue;
    lines.push(`<tr><td>${esc(k)}</td><td class="n">${fmt.fmtHTML(v, { digits: 2 })}</td></tr>`);
  }
  return `<div class="hb-card more-money" data-beat="money"><h3>Money, labelled</h3>
    <table class="p2-rank">${lines.join('') || `<tr><td colspan="2"><span class="beat-na">P1 money not built yet</span></td></tr>`}</table>
    <p class="hb-sub">System-capacity value of fleet kW <b>at the system or price peak</b>: ${f('capacityLow')} (Modo's ERCOT storage market benchmark) to ${f('capacityHigh')} per kW-month (implied from an unverified Austin Energy figure). Never applied to local relief.</p>
    <p class="hb-sub"><b>Who pays today, and for what</b> ${fmt.chip('REAL', 'docs/research-report.md:59, 215-224')}</p>
    <ul class="more-payers">${PAYERS.map((p) => `<li>${esc(p.who)} (${fmt.fmtHTML({ v: p.mw, label: 'REAL', cite: p.cite }, { unit: ' MW' })}${p.dispatchPct ? `, ${fmt.fmtHTML({ v: p.dispatchPct, label: 'REAL', cite: p.cite }, { unit: '% dispatch' })}` : ''}): ${esc(p.what)}</li>`).join('')}
      <li>Base's own "distribution grid support" offering: no public price ${fmt.chip('REAL', 'docs/headroom/research_notes/base_power_product_and_system.md:388')}</li></ul>
    <p class="hb-sub"><b>Local transformer relief and upgrade deferral</b> have no sourced price anywhere in our material: an opportunity for Base and the wires company, not revenue ${fmt.chip('ASSUMPTION', 'build prompt 5.4.6')}.</p></div>`;
}

function engineCard(ctx, S) {
  const { fmt } = ctx;
  const rows = [];
  const walk = (o, path) => {
    for (const [k, v] of Object.entries(o || {})) {
      const p = path ? `${path} · ${k}` : k;
      if (isL(v) && typeof v.v === 'number') rows.push(`<tr><td>${esc(p)}</td><td class="n">${fmt.fmtHTML(v, { digits: v.v < 10 ? 2 : 0 })}</td></tr>`);
      else if (v && typeof v === 'object' && !Array.isArray(v) && !['constants', 'sources', 'series', 'inputs'].includes(k)) walk(v, p);
    }
  };
  if (S.engine) walk(S.engine, '');
  const solve = evalFact('msPerSolve', S);
  return `<div class="hb-card" data-beat="plug-in"><h3>Performance</h3>
    ${rows.length ? `<table class="p2-rank">${rows.slice(0, 12).join('')}</table>` : `<p class="hb-sub">${solve ? `One OpenDSS step: ${solve.map((x) => renderPart(x, fmt, true)).join('')}.` : '<span class="beat-na">engine.json not built yet</span>'}</p>`}
    <p class="hb-sub">All static: the browser replays committed JSON; no server, no network at view time.</p></div>`;
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
  ['Rebound', 'Prototype story: the price rebound, even split vs feeder-aware.'],
  ['Covert channel + quarantine', 'Prototype story: a fictional adversary signals through battery setpoints; the detector quarantines it. SIM, fictional.'],
  ['Siting board', "Prototype's next-battery board (its own score; see P2 for tonight's month what-if)."],
];

async function chaosCard(ctx) {
  const doc = await ctx.data.getOptional('p1/chaos.json').catch(() => null);
  if (!doc) return '';
  const { fmt } = ctx;
  const runs = doc.runs || [];
  const counts = Array.isArray(runs) ? runs.map((r) => (r && (isL(r.batteryCaused) ? r.batteryCaused.v : typeof r.batteryCaused === 'number' ? r.batteryCaused : 0)) || 0) : [];
  const head = Object.entries(doc).filter(([, v]) => isL(v)).map(([k, v]) => `<div>${esc(k)}: ${fmt.fmtHTML(v)}</div>`).join('');
  return `<div class="hb-card"><h3>Chaos sweep</h3><div class="hb-sub">The P1 evening, seeded failures; battery-caused violations only.</div>${head}${counts.length ? `<div class="hb-sub">Runs: ${fmt.fmtHTML({ v: counts.length, label: 'SIM' })}; with any battery-caused violation: ${fmt.fmtHTML({ v: counts.filter((c) => c > 0).length, label: 'SIM' })}</div>` : ''}</div>`;
}

async function emsCards(ctx) {
  const idx = await ctx.data.getOptional('ems/index.json').catch(() => null);
  if (!idx || !Array.isArray(idx.cards)) return '';
  const { fmt } = ctx;
  return idx.cards.map((c) => `<div class="hb-card ems"><h3>${esc(c.title)}</h3>
    ${(c.stats || []).map((s) => (isL(s) ? `<div class="ems-stat"><span>${esc(s.name || '')}</span><b>${fmt.fmtHTML(s, s.o || {})}</b></div>` : '')).join('')}
    <div class="hb-sub">${esc(c.text || '')}</div><div class="hb-sub">Source: <code>${esc(c.source || '')}</code></div></div>`).join('');
}

export async function mount(el, ctx) {
  const { sceneModel, scene, topology, fmt } = ctx;
  scene.update(sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame: null, view: 'more', theme: ctx.theme }));
  const beats = beatsList(await ctx.data.loadBeats());
  const S = await loadSources(ctx, [...new Set([...sourcesFor(beats.map((b) => b.caption)), 'p1meta', 'engine'])]);
  const beatBar = ctx.link.beat ? await beatBarHTML(ctx) : '';
  const beatRows = beats.map((b) => `<li class="beat-item${b.id === ctx.link.beat ? ' on' : ''}">
      <div class="beat-h"><span class="beat-t">${esc(b.t0)}–${esc(b.t1)}</span> <a href="${beatHref(b)}"><b>${esc(b.title)}</b></a>${b.label ? fmt.chip(b.label) : ''}</div>
      <div class="beat-cap">${resolveCaption(b.caption, S, fmt)}</div></li>`).join('');
  el.innerHTML = `<div class="more-wrap">
    ${beatBar}
    <div class="hb-cards more-top">
      <div class="hb-card more-beats"><h3>The five-minute video, beat by beat</h3>
        <div class="hb-sub">Each beat is one deep link; every number in a caption is read from the committed data, with its label. A beat whose data is not built says so.</div>
        <ol class="beat-list">${beatRows || '<li><span class="beat-na">beats.json not built yet</span></li>'}</ol></div>
      ${moneyCard(ctx, S)}
      ${plugInCard(ctx, S)}
      ${engineCard(ctx, S)}
    </div>
    <h2 class="more-h">Everything that already worked, unchanged</h2>
    <div class="hb-cards">
      ${STORIES.map(([t, d]) => `<div class="hb-card"><h3><a href="../demos/grid-stories/ui/dist/">${esc(t)}</a></h3><div class="hb-sub">${esc(d)} Pick it in the prototype's story menu. Connor's prototype, unchanged; its prices and loads are scripted.</div></div>`).join('')}
      <div class="hb-card"><h3><a href="../four-home-simulation/four-home.html">Four-home simulation</a></h3><div class="hb-sub">Michael's four-home model on real prices, unchanged.</div></div>
      ${await chaosCard(ctx)}
      ${await emsCards(ctx)}
    </div></div>`;
  if (ctx.link.beat) {
    const t = el.querySelector(`[data-beat="${typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(ctx.link.beat) : ctx.link.beat}"]`);
    if (t && t.scrollIntoView) t.scrollIntoView({ block: 'start' });
  }
}
