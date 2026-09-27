// ui/story/learnings.js (UI-B): Screen 4b Learnings (docs/design-handoff/story-flow/README.md "Screen 4").
// Left rail, four questions (?q=1-4, &tf=<index>, &n=<0-50>):
//   Q1 compare charging: p2/index.json usefulCapacity.aware vs usefulCapacity.naiveOpenDSS (NOT the 383 screen);
//      map coloured by the planner's room/full status per transformer (fallback: P2 baseline.peak by tier thresholds)
//   Q2 one transformer 0-50: p2/planner.json caps (naive / utility rule / feeder-aware) with the OpenDSS pill, perK at n
//   Q3 RZ's upgrade priority list: members unlocked, simulated age, cited cost, verdict from ui/lib/planner.js decide();
//      home-load growth toggle reads planner perK.g0 / g20 / g50
//   Q4 where a battery helps most: top 10 of p2/aware-core-d26-g0.json ranking
// Q2-Q4 are feeder-aware only. A missing file or field says "not built yet" / "not exported"; never a zero.
// No language model produces a rank or verdict here: every rank and verdict is this deterministic code or planner.js.

export const PAGE = 'learnings';
export const DEFAULTS = Object.freeze({ q: 1, tf: 240, n: 2 });
const PLANNER_LIB = '../lib/planner.js';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];
export const isLab = (x) => x != null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
const has = (x) => isLab(x) && x.v != null;
export function tagHTML(label, cite, screening = false) {
  return `<span class="pb-tag${screening ? ' pb-tag-screen' : ''}"${cite ? ` title="${esc(cite)}"` : ''}>${esc(screening ? 'SCREENING' : label)}</span>`;
}
export const missingHTML = (what = 'not exported') => `<span class="pb-missing">${esc(what)}</span>`;
export function fmtNum(v, d = 0) {
  if (v == null || !Number.isFinite(+v)) return '—';
  return Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}

export const QUESTIONS = [
  { q: 1, title: 'Compare charging algorithms', sub: 'A/B: same feeder, naive vs feeder-aware' },
  { q: 2, title: 'How many more can we deploy?', sub: 'One transformer, 0 to 50 batteries' },
  { q: 3, title: 'Which transformers should we upgrade?', sub: 'The tightest as home load grows' },
  { q: 4, title: 'Where does a battery help most?', sub: 'The next 10 homes, ranked' },
];

/** Parse ?q, tf, n with the page defaults. Unknown values fall back. */
export function parseParams(p = {}, nTf = 379) {
  const int = (x) => (x === '' || x == null ? NaN : Number(x));
  const q = int(p.q), tf = int(p.tf), n = int(p.n);
  return {
    q: Number.isInteger(q) && q >= 1 && q <= 4 ? q : DEFAULTS.q,
    tf: Number.isInteger(tf) && tf >= 0 && tf < nTf ? tf : null,
    n: Number.isInteger(n) && n >= 0 && n <= 50 ? n : DEFAULTS.n,
  };
}

// ---- map geometry (the reference's projection: local metres around topology.meta.source) --------------------------
export function project(topo) {
  const src = topo.meta && topo.meta.source ? topo.meta.source : topo.transformers[0].lonlat;
  const cos = Math.cos(src[1] * Math.PI / 180), SC = 100000;
  const P = (ll) => [(ll[0] - src[0]) * cos * SC, -(ll[1] - src[1]) * SC];
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, d = '';
  for (const e of topo.edges || []) {
    const a = P([e[0], e[1]]), b = P([e[2], e[3]]);
    d += `M${a[0].toFixed(0)},${a[1].toFixed(0)}L${b[0].toFixed(0)},${b[1].toFixed(0)}`;
    for (const q of [a, b]) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); }
  }
  const pts = topo.transformers.map((t) => P(t.lonlat).map((v) => +v.toFixed(0)));
  for (const q of pts) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); }
  const span = Math.max(x1 - x0, y1 - y0) || 1, pad = span * 0.04;
  return {
    vb: `${(x0 - pad).toFixed(0)} ${(y0 - pad).toFixed(0)} ${(x1 - x0 + 2 * pad).toFixed(0)} ${(y1 - y0 + 2 * pad).toFixed(0)}`,
    edges: d, pts, ew: +(span / 700).toFixed(1), r: +(span / 120).toFixed(1), rr: +(span / 55).toFixed(1), sw: +(span / 900).toFixed(1), sw2: +(span / 350).toFixed(1),
  };
}

/** "Street A" for the four focus transformers, "T-240" otherwise (the app's T-<index> convention). */
export function tfName(topo, tf) {
  const f = topo && (topo.focus || []).find((x) => x.tf === tf);
  return f ? `Street ${f.key}` : `T-${tf}`;
}

// ---- planner helpers ------------------------------------------------------------------------------------------------
/** Row index of a topology tf in planner.tfs (perK arrays follow tfs order). */
export function plannerRows(planner) {
  const m = new Map();
  (planner && planner.tfs || []).forEach((t, i) => m.set(t.tf, i));
  return m;
}
/** OpenDSS wins (DESIGN §3.1.7): "lower" means OpenDSS found an overload at the surrogate cap, so show cap - 1. */
export function effectiveCap(cap, referee) {
  if (!has(cap)) return null;
  const checked = referee && referee.status === 'checked';
  if (checked && cap.opendss === 'lower') return { v: Math.max(0, cap.v - 1), label: cap.label, cite: `${cap.cite || ''}; OpenDSS found an overload at ${cap.v}`, pill: 'lower', raw: cap.v };
  return { v: cap.v, label: cap.label, cite: cap.cite, pill: checked && cap.opendss === 'agree' ? 'agree' : 'screening', raw: cap.v };
}
/** Room status from a cap and the batteries installed today: 0 room (2+ spare), 1 nearly full, 2 at capacity, 3 over. */
export function roomStatus(cap, installed) {
  if (cap == null || installed == null) return -1;
  const spare = cap - installed;
  return spare < 0 ? 3 : spare === 0 ? 2 : spare === 1 ? 1 : 0;
}
/** P2 baseline peak (pct x10) -> the design's four buckets: room <85, tight 85-100, full 100-110, over >110. */
export const peakBucket = (p10) => { const p = p10 / 10; return p > 110 ? 3 : p >= 100 ? 2 : p >= 85 ? 1 : 0; };
export const STATUS_COL = ['#8aa58f', '#d9d4c3', '#c7962b', '#b23a2f'];
export const EXCL_COL = '#b9b4a6';
export const ROOM_NAMES = ['has room (2+ more)', 'nearly full (1 more)', 'at capacity', 'over capacity today'];
export const PEAK_NAMES = ['room (under 85%)', 'tight (85–100%)', 'full (over nameplate)', 'over normal rating'];

/** Per-transformer status arrays [379] for naive and aware (-1 = excluded / not in the planner). */
export function q1Status(topo, planner, p2n, p2a) {
  const NT = topo.transformers.length;
  if (planner && Array.isArray(planner.tfs) && planner.tfs.length) {
    const naive = new Array(NT).fill(-1), aware = new Array(NT).fill(-1);
    for (const t of planner.tfs) {
      const inst = has(t.installed) ? t.installed.v : null;
      const cn = effectiveCap(t.cap && t.cap.naive, planner.referee), ca = effectiveCap(t.cap && t.cap.aware, planner.referee);
      naive[t.tf] = roomStatus(cn ? cn.v : null, inst); aware[t.tf] = roomStatus(ca ? ca.v : null, inst);
    }
    return { mode: 'planner', naive, aware, names: ROOM_NAMES };
  }
  if (p2n && p2a && p2n.baseline && p2a.baseline) {
    return { mode: 'peak', naive: p2n.baseline.peak.map(peakBucket), aware: p2a.baseline.peak.map(peakBucket), names: PEAK_NAMES };
  }
  return null;
}
export const countBy = (arr, vals) => vals.map((v) => arr.filter((x) => x === v).length);

/** Largest k (0..50) with every Core still earning >= earnMin of an unconstrained one: awareEff is effective Cores x100. */
export function capFromEff(effRow, earnMin = 0.9) {
  if (!Array.isArray(effRow)) return null;
  let c = 0;
  for (let k = 1; k < effRow.length; k++) { if (effRow[k] >= earnMin * k * 100 - 1e-9) c = k; else break; }
  return c;
}
/** Largest k with no battery-caused normal event for every j <= k (naiveCaused per k). */
export function capFromCaused(causedRow) {
  if (!Array.isArray(causedRow)) return null;
  let c = 0;
  for (let k = 1; k < causedRow.length; k++) { if (!causedRow[k]) c = k; else break; }
  return c;
}
/** Growth levels the planner exported: [{id, pct, ok}] (g0 always from tfs caps when perK.g0 is absent). */
export function growthLevels(planner) {
  const pk = (planner && planner.perK) || {};
  return [['g0', 0], ['g20', 20], ['g50', 50]].map(([id, pct]) => ({ id, pct, ok: id === 'g0' ? true : !!pk[id] }));
}

/** Monthly interpolation of the decile curves' 5-year point: F(60) per decile (q0 = referral off). */
export function fiveYearShares(planner, key, q = 'q0') {
  const c = planner && planner.demand && planner.demand.curves && planner.demand.curves[key];
  const rows = c && c[q];
  if (!Array.isArray(rows) || !rows.length) return null;
  return rows.map((r) => r[r.length - 1]);
}

/**
 * RZ's upgrade priority list (DATA-SCOPE layer 3), feeder-aware with the utility rule unchanged (DESIGN §3.4.1).
 * Pure: no money arithmetic beyond the stated DERIVED ratios; the verdict comes later from planner.js decide().
 * Returns every transformer at capacity now, or likely to outgrow its cap within the horizon (p90), sorted by the
 * members an upgrade unlocks (p50, then p90), then age (older first: likely replaced anyway).
 */
export function upgradeRows(planner, g = 'g0', earnMin = 0.9) {
  if (!planner || !Array.isArray(planner.tfs)) return [];
  const pk = planner.perK && planner.perK[g];
  const rows = [];
  planner.tfs.forEach((t, row) => {
    const inst = has(t.installed) ? t.installed.v : 0, pend = has(t.pending) ? t.pending.v : 0;
    const paper = t.cap && has(t.cap.paper) ? t.cap.paper.v : null;
    let aware = t.cap && has(t.cap.aware) ? effectiveCap(t.cap.aware, planner.referee).v : null;
    if (g !== 'g0') aware = pk && pk.awareEff ? capFromEff(pk.awareEff[row], earnMin) : null;
    if (aware == null || paper == null) return;
    const c = Math.min(aware, paper);
    const upA = t.up && has(t.up.aware) ? t.up.aware.v : null, upP = t.up && has(t.up.paper) ? t.up.paper.v : null;
    const cUp = upA != null && upP != null ? Math.min(upA, upP) : null;
    const now = inst + pend, homes = t.homes ?? 0, m = Math.max(0, homes - Math.min(now, homes));
    const key = t.nb && t.nb.key ? t.nb.key : `${homes}-${inst}`;
    const F = fiveYearShares(planner, key, 'q0');
    const addsAt = (i) => (F ? Math.round(m * F[i]) : null);
    const adds = F ? { p10: addsAt(0), p50: addsAt(Math.floor(F.length / 2)), p90: addsAt(F.length - 1) } : null;
    const want = (a) => now + (a ?? 0);
    const unl = (a) => (cUp == null ? null : Math.max(0, Math.min(want(a), cUp) - Math.min(want(a), c)));
    const unlocked = adds ? { p10: unl(adds.p10), p50: unl(adds.p50), p90: unl(adds.p90) } : { p10: unl(0), p50: unl(0), p90: unl(0) };
    const overNow = now > c, atCap = now >= c, mayOutgrow = adds ? want(adds.p90) > c : false;
    const onBoard = m === 0 && atCap;
    if (!(atCap || mayOutgrow)) return;
    rows.push({ tf: t.tf, row, kva: t.kva, upKva: t.up && t.up.kva, homes, now, c, cUp, aware, paper, adds, unlocked, overNow, atCap, mayOutgrow, onBoard, age: t.age });
  });
  rows.sort((a, b) => (a.onBoard - b.onBoard) || ((b.unlocked.p50 ?? -1) - (a.unlocked.p50 ?? -1)) || ((b.unlocked.p90 ?? -1) - (a.unlocked.p90 ?? -1))
    || ((b.age && b.age.v) || 0) - ((a.age && a.age.v) || 0) || a.tf - b.tf);
  return rows;
}
/** The upgrade list the page shows: the top `n` that unlock something, then up to `nb` "fully on board" rows. */
export function upgradeShortlist(rows, n = 8, nb = 2) {
  const worth = rows.filter((r) => !r.onBoard).slice(0, n);
  return [...worth, ...rows.filter((r) => r.onBoard).slice(0, nb)];
}

export const ACTION_WORDS = { upgrade: 'Upgrade now', wait: 'Wait and watch', never: 'Don\'t upgrade' };
/** Plain verdict words from a decide() result (DESIGN §3.4.4). */
export function verdictWords(d, r) {
  if (!d) return null;
  if (r && !r.overNow && d.pOver != null && d.pOver < 0.05) return { word: 'No upgrade', why: 'unlikely to fill up in 5 years' };
  const w = ACTION_WORDS[d.leastRegret] || d.leastRegret;
  const why = d.leastExpected && d.leastExpected !== d.leastRegret ? `least regret; expected cost favours ${String(ACTION_WORDS[d.leastExpected] || d.leastExpected).toLowerCase()}` : 'least regret and lowest expected cost';
  return { word: w, why };
}

/** Q4 headline and rows from a P2 combo's ranking (top 10). */
export function rankingModel(p2a, topo, n = 10) {
  const rank = (p2a && Array.isArray(p2a.ranking) ? p2a.ranking : []).slice(0, n);
  const r0 = rank[0];
  const why = r0 ? String(r0.reason || '').split(';')[0].replace(/\s*\((SIM|DERIVED|REAL|ASSUMPTION)[^)]*\)/g, '').trim() : '';
  return {
    headline: r0 ? `The next battery goes to ${r0.label} on ${tfName(topo, r0.tf)}: it ${why}.` : null,
    rows: rank.map((r) => ({ rank: r.rank, home: r.label, tf: r.tf, tfName: tfName(topo, r.tf), stress: r.stressAvoidedH, peak: r.peakWithPct, value: r.revenueUSD, screening: r.screening })),
    tfs: [...new Set(rank.map((r) => r.tf))],
  };
}

/** 51 fit cells for a 0..50 strip: filled up to `limit`, faded beyond `2 x homes` (hypothetical). */
export function stripCells(limit, homes) {
  return Array.from({ length: 51 }, (_, i) => ({ fit: limit != null && i <= limit && i > 0, zero: i === 0, hypo: homes != null && i > 2 * homes }));
}

// =================================================================================================================
// DOM
// =================================================================================================================
async function tryGet(fn) { try { return { doc: await fn(), err: null }; } catch (e) { return { doc: null, err: e }; } }
const notBuilt = (err, path) => (err && err.status === 404 ? `not built yet: ${path}` : err && /404|not found/i.test(String(err.message)) ? `not built yet: ${path}` : `could not load ${path}`);

async function loadPlannerLib(ctx) {
  try { return await import(PLANNER_LIB); } catch (e) { /* not built yet */ }
  if (ctx && ctx.devPlannerLib) { try { return await import(ctx.devPlannerLib); } catch (e) { /* ignore */ } }
  return null;
}

export async function mount(root, ctx) {
  root.classList.add('pb-page', 'pb-learn');
  root.innerHTML = '<div class="pb-loading">Loading the learnings…</div>';
  const [topoR, idxR, plR, p2aR, p2nR, lib] = await Promise.all([
    tryGet(() => ctx.getJSON('topology.json')), tryGet(() => ctx.getJSON('p2/index.json')), tryGet(() => ctx.getJSON('p2/planner.json')),
    tryGet(() => ctx.getJSON('p2/aware-core-d26-g0.json')), tryGet(() => ctx.getJSON('p2/naive-core-d26-g0.json')), loadPlannerLib(ctx),
  ]);
  const topo = topoR.doc;
  if (!topo) { root.innerHTML = `<div class="pb-loading">${missingHTML(notBuilt(topoR.err, 'topology.json'))}</div>`; return { dispose() { root.innerHTML = ''; } }; }
  const idx = idxR.doc, planner = plR.doc, p2a = p2aR.doc, p2n = p2nR.doc;
  const NT = topo.transformers.length;
  const geo = project(topo);
  const rows = plannerRows(planner);
  const pp = parseParams(ctx.params || {}, NT);
  const st = {
    q: pp.q, n: pp.n, view: 'diff', g: 'g0',
    sel: pp.tf ?? (planner && planner.meta && Number.isInteger(planner.meta.defaultTf) ? planner.meta.defaultTf : DEFAULTS.tf),
  };
  const s1 = q1Status(topo, planner, p2n, p2a);
  const fixture = [idx, planner, p2a].some((d) => d && d.fixture);
  const earnMin = planner && planner.constants && planner.constants.PLAN_AWARE_EARN_MIN ? planner.constants.PLAN_AWARE_EARN_MIN.value : 0.9;
  const decideCache = new Map();

  root.innerHTML = `
    ${fixture ? '<div class="pb-fixture">FIXTURE data: contract-shaped stand-ins, not engine output</div>' : ''}
    <div class="pb-learn-grid">
      <nav class="pb-rail" aria-label="Key takeaways">
        <div class="pb-eyebrow pb-rail-h">KEY TAKEAWAYS</div>
        ${QUESTIONS.map((x) => `<button type="button" class="pb-q-btn" data-q="${x.q}"><span class="pb-q-dot">${x.q}</span><span class="pb-q-txt"><span class="pb-q-title">${esc(x.title)}</span><span class="pb-q-sub">${esc(x.sub)}</span></span></button>`).join('')}
      </nav>
      <section class="pb-mapcol">
        <div class="pb-maphead"><div data-pb="toggle"></div><span class="pb-sub pb-right" data-pb="caption"></span></div>
        <div class="pb-map">
          <svg viewBox="${geo.vb}" preserveAspectRatio="xMidYMid meet" data-pb="svg" aria-label="The feeder's 379 service transformers">
            <path d="${geo.edges}" fill="none" stroke="#c3c9bf" stroke-width="${geo.ew}" stroke-linecap="round"/>
            <g data-pb="dots">${geo.pts.map((p, i) => `<circle data-tf="${i}" cx="${p[0]}" cy="${p[1]}" r="${geo.r}" fill="#d9d4c3" stroke="#fffdf8" stroke-width="${geo.sw}"><title>${esc(tfName(topo, i))}</title></circle>`).join('')}</g>
            <circle data-pb="ring" r="${geo.rr}" fill="none" stroke="#10231a" stroke-width="${geo.sw2}" cx="-99999" cy="-99999"/>
          </svg>
          <div class="pb-maplegend" data-pb="legend"></div>
          <div class="pb-mapsrc" data-pb="src"></div>
        </div>
      </section>
      <aside class="pb-aside" data-pb="aside"></aside>
    </div>`;
  const $ = (s) => root.querySelector(`[data-pb="${s}"]`);
  const dots = [...root.querySelectorAll('[data-pb="dots"] circle')];

  const writeURL = () => {
    try {
      if (typeof ctx.link !== 'function') return;
      const p = {};
      if (st.q !== DEFAULTS.q) p.q = st.q;
      if (st.sel !== ((planner && planner.meta && planner.meta.defaultTf) ?? DEFAULTS.tf)) p.tf = st.sel;
      if (st.n !== DEFAULTS.n) p.n = st.n;
      const href = ctx.link({ page: 'learnings', q: p.q, tf: p.tf, n: p.n });
      if (href && typeof history !== 'undefined') history.replaceState(history.state, '', href);
    } catch (e) { /* the URL is a convenience */ }
  };
  const num = (x, opts) => { if (!has(x)) return missingHTML(); try { return ctx.num(x, opts); } catch (e) { return missingHTML('unlabelled value refused'); } };

  // ---------------- map painting ----------------
  function paint(colours, legend, caption, src, ringOn = true) {
    dots.forEach((d, i) => d.setAttribute('fill', colours[i] || EXCL_COL));
    $('legend').innerHTML = legend.map((l) => `<span><i style="background:${l.c}"></i>${esc(l.name)}<b>${l.n != null ? fmtNum(l.n) : ''}</b></span>`).join('');
    $('caption').textContent = caption;
    $('src').innerHTML = src;
    const ring = $('ring'), p = geo.pts[st.sel];
    ring.setAttribute('cx', ringOn && p ? p[0] : -99999); ring.setAttribute('cy', ringOn && p ? p[1] : -99999);
  }
  const statusColours = (arr) => arr.map((s) => (s < 0 ? EXCL_COL : STATUS_COL[s]));
  const statusLegend = (arr, names) => {
    const c = countBy(arr, [0, 1, 2, 3, -1]);
    const L = names.map((name, i) => ({ name, c: STATUS_COL[i], n: c[i] }));
    if (c[4]) L.push({ name: 'not homes (excluded)', c: EXCL_COL, n: c[4] });
    return L;
  };
  const srcQ1 = () => (s1 && s1.mode === 'planner'
    ? `${tagHTML(planner.tfs[0].cap.aware.label, 'p2/planner.json tfs[].cap vs tfs[].installed')}Room = the most that fit (planner, from an empty feeder) minus our batteries there today ${tagHTML('ASSUMPTION', 'the prototype 96-Core placement (data/fleet.json)')}`
    : s1 ? `${tagHTML('SIM', 'P2 baseline.peak (sim.surrogate, calibrated vs OpenDSS)')}Month peak with our 96 batteries · planner not built yet, so coloured by loading` : missingHTML('not built yet: p2/planner.json and the P2 combos'));

  function paintMap() {
    if (st.q === 1 || st.q === 2) {
      if (!s1) { paint(new Array(NT).fill(EXCL_COL), [], 'Transformer status', srcQ1()); return; }
      const view = st.q === 2 ? 'aware' : st.view;
      if (view === 'diff') {
        const cls = s1.naive.map((nv, i) => { const av = s1.aware[i]; if (nv < 0 || av < 0) return 'x'; return nv >= 2 && av < 2 ? 'g' : av >= 2 ? 'f' : 'o'; });
        const DC = { g: '#1e4d2b', f: '#c7962b', o: '#d9d4c3', x: EXCL_COL };
        const cnt = (k) => cls.filter((x) => x === k).length;
        paint(cls.map((c) => DC[c]), [
          { name: 'full under naive, room with feeder-aware', c: DC.g, n: cnt('g') }, { name: 'full under both', c: DC.f, n: cnt('f') },
          { name: 'room under both', c: DC.o, n: cnt('o') }, ...(cnt('x') ? [{ name: 'not homes (excluded)', c: EXCL_COL, n: cnt('x') }] : []),
        ], 'What feeder-aware adds: full under naive, room under feeder-aware', srcQ1(), st.q === 2);
      } else {
        const arr = s1[view];
        paint(statusColours(arr), statusLegend(arr, s1.names), view === 'aware' ? 'B · Feeder-aware: which transformers have room' : 'A · Naive split: which transformers have room', srcQ1(), st.q === 2);
      }
      if (st.q === 2) $('caption').textContent = 'Feeder-aware · room per transformer · click one to pick it';
      return;
    }
    if (st.q === 3) {
      const list = upgradeRows(planner, st.g, earnMin);
      const byTf = new Map(list.map((r) => [r.tf, r]));
      const col = topo.transformers.map((_, i) => { const r = byTf.get(i); if (!rows.has(i)) return EXCL_COL; if (!r) return STATUS_COL[0]; return r.overNow ? STATUS_COL[3] : r.atCap ? STATUS_COL[2] : STATUS_COL[1]; });
      const c = (k) => col.filter((x) => x === k).length;
      paint(planner ? col : new Array(NT).fill(EXCL_COL), planner ? [
        { name: 'room for 5 years', c: STATUS_COL[0], n: c(STATUS_COL[0]) }, { name: 'may outgrow in 5 years (p90)', c: STATUS_COL[1], n: c(STATUS_COL[1]) },
        { name: 'at capacity now', c: STATUS_COL[2], n: c(STATUS_COL[2]) }, { name: 'over capacity now', c: STATUS_COL[3], n: c(STATUS_COL[3]) },
        { name: 'not homes (excluded)', c: EXCL_COL, n: c(EXCL_COL) },
      ] : [], `Feeder-aware, utility rule unchanged · ${growthLevels(planner).find((x) => x.id === st.g).pct ? `home load +${growthLevels(planner).find((x) => x.id === st.g).pct}%` : 'today\'s load'}`,
      planner ? `${tagHTML('DERIVED', planner.decision && planner.decision.cite)}Capacity binds at min(feeder-aware, utility rule); demand from the planner's decile curves` : missingHTML('not built yet: p2/planner.json'));
      return;
    }
    const rm = rankingModel(p2a, topo);
    const top = new Set(rm.tfs);
    paint(topo.transformers.map((_, i) => (top.has(i) ? '#1e4d2b' : '#d9d4c3')), [
      { name: 'a top-10 next-battery home', c: '#1e4d2b', n: top.size }, { name: 'other transformers', c: '#d9d4c3', n: NT - top.size },
    ], 'Feeder-aware · where the next 10 batteries go', p2a ? `${tagHTML('SIM', 'sim.p2_build ranking (surrogate, calibrated vs OpenDSS)')}sim.p2_build ranking · August 2026 · feeder-aware` : missingHTML(notBuilt(p2aR.err, 'p2/aware-core-d26-g0.json')));
  }

  // ---------------- aside panels ----------------
  function q1HTML() {
    const uc = idx && idx.usefulCapacity;
    const A = uc && uc.aware, N = uc && uc.naiveOpenDSS;
    if (!uc) return `<div class="pb-eyebrow">WHICH TRANSFORMERS HAVE ROOM</div>${missingHTML(notBuilt(idxR.err, 'p2/index.json'))}`;
    const fullN = s1 ? s1.naive.filter((x) => x >= 2).length : null, fullA = s1 ? s1.aware.filter((x) => x >= 2).length : null;
    const fail = N && N.failAt != null ? N.failAt : null;
    const cols = N && N.checkCols ? N.checkCols : [];
    const failRow = N && Array.isArray(N.checks) ? N.checks.find((r) => r[0] === fail) : null;
    const colOf = (name) => (failRow ? failRow[cols.indexOf(name)] : null);
    const headAt = colOf('headMaxPct');
    const causedAt = colOf('causedNormal');
    const whyFail = failRow ? (causedAt ? `${fmtNum(causedAt)} battery-caused transformer event${causedAt === 1 ? '' : 's'}` : headAt != null && headAt > 100 ? `the feeder-head cable at ${fmtNum(headAt, 1)}% of its rating` : 'a violation') : null;
    return `
      <div class="pb-eyebrow">WHICH TRANSFORMERS HAVE ROOM</div>
      <div class="pb-headline">The same feeder holds ${has(A) ? fmtNum(A.v) : '—'} batteries with feeder-aware charging, and ${has(N) ? fmtNum(N.v) : '—'} with a naive split.</div>
      <div class="pb-two">
        <div class="pb-capt"><span class="pb-capt-t">A · Naive split</span><span class="pb-capt-big">${has(N) ? num(N, { digits: 0 }) : missingHTML('naiveOpenDSS not exported')}</span><span class="pb-sub">useful capacity, OpenDSS-judged${fullN != null ? ` · ${fmtNum(fullN)} transformers full or over today` : ''}</span></div>
        <div class="pb-capt pb-capt-ours"><span class="pb-capt-t">B · Feeder-aware</span><span class="pb-capt-big">${has(A) ? num(A, { digits: 0 }) : missingHTML()}</span><span class="pb-sub">useful capacity, OpenDSS-checked${fullA != null ? ` · ${fmtNum(fullA)} transformers full or over today` : ''}</span></div>
      </div>
      <div class="pb-body">Useful capacity is how many batteries fit, placed one at a time from an empty feeder in the same order, before the next one causes a problem.</div>
      <div class="pb-body"><b>Naive</b> is our assumption of one number, no feeder check: every battery charges at once when the price drops. OpenDSS stepped it one battery at a time: ${has(N) ? fmtNum(N.v) : '—'} hold for the whole of August${fail != null ? `; battery ${fmtNum(fail)} brings ${esc(whyFail || 'a violation')}` : ''}.</div>
      <div class="pb-body"><b>Feeder-aware</b> charges each transformer only into the room it has, so it places a battery at every eligible home with no transformer event because of batteries (OpenDSS, every 15 minutes of August)${uc.cap && has(uc.cap) ? `; it would stop if the feeder had to give up more than ${num({ ...uc.cap, v: uc.cap.v * 100 }, { digits: 0, unit: '%' })} of its charge` : ''}.</div>
      <div class="pb-foot">${esc(uc.scopeText || '')} · sim.p2_build usefulCapacity · aware ${has(A) ? tagHTML(A.label, A.cite) : ''} naive ${has(N) ? tagHTML(N.label, N.cite) : ''}</div>`;
  }

  function q2HTML() {
    const eyebrow = `<div class="pb-row-b"><span class="pb-eyebrow">HOW MANY FIT ON ONE TRANSFORMER</span></div>`;
    if (!planner) return `${eyebrow}${missingHTML(notBuilt(plR.err, 'p2/planner.json'))}<div class="pb-body">The per-transformer 0–50 curves come from the capacity planner (PLANNER).</div>`;
    const row = rows.get(st.sel), t = row != null ? planner.tfs[row] : null;
    const opts = [...(topo.focus || []).map((f) => f.tf), ...(topo.bridge || []).map((b) => b.tf), planner.meta && planner.meta.demoTf].filter((x) => Number.isInteger(x));
    if (!opts.includes(st.sel)) opts.push(st.sel);
    const sel = `<select class="pb-select" data-pb="loc">${[...new Set(opts)].map((v) => `<option value="${v}"${v === st.sel ? ' selected' : ''}>${esc(tfName(topo, v))}</option>`).join('')}</select>`;
    if (!t) return `${eyebrow}${sel}<div class="pb-body">${esc(tfName(topo, st.sel))} serves no homes (a commercial 3-phase unit), so the planner leaves it out.</div>`;
    const n = st.n, cn = effectiveCap(t.cap.naive, planner.referee), ca = effectiveCap(t.cap.aware, planner.referee), cp = has(t.cap.paper) ? t.cap.paper : null;
    const pk = planner.perK && planner.perK.g0;
    const at = (name) => (pk && Array.isArray(pk[name]) && pk[name][row] ? pk[name][row][n] : null);
    const nPeak = at('naivePeak'), nTier = at('naiveTier'), aPeak = at('awarePeak'), aEff = at('awareEff');
    const perKLab = planner.series && planner.series.perK && LABELS.includes(planner.series.perK.label) ? planner.series.perK.label : 'SIM';
    const TIER = ['within its rating', 'over nameplate', 'above 110%, clock running', 'overloaded 30+ min', 'emergency (over 150%)', 'fuse open'];
    const pill = (c) => (!c ? '' : c.pill === 'agree' ? '<span class="pb-pill">✓ OpenDSS</span>' : c.pill === 'lower' ? `<span class="pb-pill pb-pill-warn" title="${esc(c.cite)}">OpenDSS: overload at ${fmtNum(c.raw)}</span>` : tagHTML('SIM', 'not OpenDSS-checked', true));
    const strip = (c) => `<div class="pb-strip">${stripCells(c ? c.v : null, t.homes).map((x) => `<i class="${x.fit ? 'f' : x.zero ? 'z' : 'n'}${x.hypo ? ' h' : ''}"></i>`).join('')}<b style="left:${((n + 0.5) / 51 * 100).toFixed(2)}%"></b></div>`;
    const limitRow = (name, verb, c, extra) => `
      <div class="pb-limit">
        <div class="pb-limit-h"><span class="pb-limit-n">${esc(name)}</span>${pill(c)}<span class="pb-right">${verb} <b class="pb-limit-v">${c ? num(c, { digits: 0 }) : missingHTML()}</b></span></div>
        ${strip(c)}${extra ? `<div class="pb-sub">${extra}</div>` : ''}
      </div>`;
    const age = t.age && has(t.age) ? `about ${fmtNum(t.age.v)} years old (${t.age.source === 'utility' ? 'utility' : 'simulated'}) ${tagHTML(t.age.label, `${t.age.cite || ''}${t.age.p10 != null ? `; could be ${t.age.p10}–${t.age.p90} years` : ''}`)}` : '';
    const fitsA = ca && n <= ca.v, fitsN = cn && n <= cn.v, fitsP = cp && n <= cp.v;
    let answer;
    if (n === 0) answer = 'Slide to add batteries to this transformer.';
    else if (fitsA) answer = `${n} batter${n === 1 ? 'y fits' : 'ies fit'} here with feeder-aware charging${!fitsN && cn ? `; a naive split tops out at ${fmtNum(cn.v)}` : ''}${!fitsP && cp ? `, and the utility's nameplate rule allows only ${fmtNum(cp.v)} today` : ''}.`;
    else answer = `${n} is too many even for feeder-aware: past ${ca ? fmtNum(ca.v) : '—'}, each extra battery earns less than ${fmtNum(earnMin * 100)}% of an unconstrained one. Feeder-aware never overloads the transformer; it charges less instead, so this limit is about money, not safety.`;
    const hypo = n > 2 * t.homes ? ` More than 2 per home is hypothetical here (${fmtNum(t.homes)} home${t.homes === 1 ? '' : 's'}).` : '';
    return `
      ${eyebrow}
      ${sel}
      <div class="pb-sub">${num(t.kva, { digits: 0, unit: ' kVA' })} · ${fmtNum(t.homes)} home${t.homes === 1 ? '' : 's'} · ${num(t.installed, { digits: 0 })} of our batteries today · ${esc(t.mount || '')}</div>
      ${age ? `<div class="pb-sub">${age}</div>` : ''}
      <div class="pb-slider"><input type="range" min="0" max="50" step="1" value="${n}" data-pb="n" aria-label="Batteries on this transformer"><span class="pb-slider-v">${n}</span></div>
      ${limitRow('Naive', 'fits', cn, nPeak != null ? `at ${n}: month peak ${fmtNum(nPeak / 10, 0)}%, ${TIER[nTier] || ''} ${tagHTML(perKLab, 'planner perK.g0.naivePeak (surrogate)', true)}` : missingHTML('per-k peaks not exported'))}
      ${limitRow('Utility rule', 'allows', cp, `nameplate vs kVA: it does not look at when batteries charge ${cp ? tagHTML(cp.label, cp.cite) : ''}`)}
      ${limitRow('Feeder-aware', 'fits', ca, aPeak != null ? `at ${n}: month peak ${fmtNum(aPeak / 10, 0)}%, earning like ${fmtNum(aEff / 100, 1)} full batteries ${tagHTML(perKLab, 'planner perK.g0.awarePeak / awareEff (surrogate)', true)}` : missingHTML('per-k peaks not exported'))}
      <div class="pb-body">${esc(answer)}${esc(hypo)}</div>
      <div class="pb-foot">Naive: our assumption of one number, no feeder check. Feeder-aware fits = the most that still earn at least ${fmtNum(earnMin * 100)}% each. ${esc(planner.meta && planner.meta.scope || '')}</div>`;
  }

  function q3HTML() {
    const eyebrow = `<div class="pb-row-b"><span class="pb-eyebrow">WHICH ARE WORTH UPGRADING</span>${tagHTML('DERIVED', planner && planner.decision && planner.decision.cite)}</div>`;
    if (!planner) return `${eyebrow}${missingHTML(notBuilt(plR.err, 'p2/planner.json'))}<div class="pb-body">The upgrade list comes from the capacity planner (PLANNER): RZ's three-layer scope.</div>`;
    const levels = growthLevels(planner), lev = levels.find((x) => x.id === st.g);
    const all = upgradeRows(planner, st.g, earnMin), list = upgradeShortlist(all);
    const money = planner.money || {};
    const C = money.PLAN_UPGRADE_USD, V = money.PLAN_MEMBER_VALUE_USD_YR;
    const over = all.filter((r) => r.overNow).length, atCap = all.filter((r) => r.atCap).length;
    const seg = levels.map((l) => `<button type="button" class="pb-seg-b${l.id === st.g ? ' on' : ''}" data-g="${l.id}"${l.ok ? '' : ' disabled title="not exported by the planner"'}>${l.pct ? `+${l.pct}%` : 'Today\'s load'}${l.ok ? '' : ' · not exported'}</button>`).join('');
    const lines = list.map((r) => {
      const name = tfName(topo, r.tf);
      const u = r.unlocked, a = r.adds;
      const unl = u && u.p50 != null ? `${fmtNum(u.p50)}${u.p10 !== u.p90 ? ` (${fmtNum(u.p10)}–${fmtNum(u.p90)})` : ''}` : '—';
      const worth = has(V) && u && u.p50 ? { v: u.p50 * V.v, label: 'DERIVED', cite: `${u.p50} members × ${V.cite || 'PLAN_MEMBER_VALUE_USD_YR'}` } : null;
      const payback = worth && has(C) && worth.v > 0 ? { v: C.v / worth.v, label: 'DERIVED', cite: 'upgrade cost ÷ yearly energy value unlocked (undiscounted)' } : null;
      const key = `${st.g}:${r.tf}`, dv = decideCache.get(key);
      const vw = r.onBoard ? { word: 'Not worth it', why: 'neighbourhood already fully on board' } : dv === undefined ? { word: lib ? 'computing…' : 'verdict not built yet', why: lib ? '' : 'ui/lib/planner.js (PLANNER)' } : dv && dv.err ? { word: 'no verdict', why: dv.err } : verdictWords(dv, r);
      return `
        <div class="pb-up${r.tf === st.sel ? ' on' : ''}${r.onBoard ? ' pb-dim' : ''}" data-tf="${r.tf}">
          <div class="pb-up-h"><b>${esc(name)}</b><span class="pb-sub">${has(r.kva) ? `${fmtNum(r.kva.v)}` : '—'}${has(r.upKva) ? ` → ${fmtNum(r.upKva.v)}` : ''} kVA · ${fmtNum(r.homes)} home${r.homes === 1 ? '' : 's'} · ${fmtNum(r.now)} wanted now, fits ${fmtNum(r.c)}</span><span class="pb-right pb-verdict-w${vw && /Upgrade/.test(vw.word) ? ' pb-go' : ''}">${esc(vw ? vw.word : '')}</span></div>
          <div class="pb-up-b">${r.onBoard ? 'every home here is already a member: an upgrade unlocks no one' : `unlocks <b>${unl}</b> member${u && u.p50 === 1 ? '' : 's'} in 5 years${worth ? `, worth ${num(worth, { money: true, digits: 0 })}/yr` : ''}${payback ? ` · pays back in ${num(payback, { digits: 1, unit: ' yr' })}` : ''}`}${r.age && has(r.age) ? ` · age ${num(r.age, { digits: 0, unit: ' y' })} ${r.age.source === 'utility' ? '' : '(simulated)'}` : ''}</div>
          ${vw && vw.why ? `<div class="pb-sub">${esc(vw.why)}</div>` : ''}
        </div>`;
    }).join('');
    return `
      ${eyebrow}
      <div class="pb-headline pb-h20">${lev.pct ? `At +${lev.pct}% home load` : 'At today\'s load'}, ${fmtNum(atCap)} transformer${atCap === 1 ? ' is' : 's are'} at capacity for batteries wanted now${over ? ` and ${fmtNum(over)} already over` : ''}, feeder-aware with the utility rule unchanged.</div>
      <div class="pb-growth"><span class="pb-sub">Home load growth (EVs, heat pumps)</span>${tagHTML('ASSUMPTION', 'planner perK.g0 / g20 / g50: the same sweep with home load scaled')}<div class="pb-seg">${seg}</div></div>
      <div class="pb-uplist">${lines || `<div class="pb-body">No transformer is at capacity at this load.</div>`}</div>
      <div class="pb-foot">Upgrade cost ${has(C) ? num(C, { money: true, digits: 0 }) : missingHTML()} per transformer · member value ${has(V) ? num(V, { money: true, digits: 0 }) : missingHTML()}/yr is energy value, not Base's profit · unlocked = members over today's cap that one size up serves (p50, p10–p90) · verdict = least worst regret over slow, typical and fast growth (planner.js decide)${st.g !== 'g0' ? ' · one size up is at today\'s load (screening)' : ''}</div>`;
  }

  function q4HTML() {
    const eyebrow = `<div class="pb-row-b"><span class="pb-eyebrow">WHERE A BATTERY HELPS MOST</span>${tagHTML('SIM', 'sim.p2_build ranking (surrogate, calibrated vs OpenDSS)')}</div>`;
    if (!p2a) return `${eyebrow}${missingHTML(notBuilt(p2aR.err, 'p2/aware-core-d26-g0.json'))}`;
    const rm = rankingModel(p2a, topo);
    if (!rm.rows.length) return `${eyebrow}${missingHTML('no ranking exported for this combo')}`;
    return `
      ${eyebrow}
      <div class="pb-headline pb-h20">${esc(rm.headline)}</div>
      <div class="pb-sub">Ranked by the transformer stress it removes, then energy value, for August with feeder-aware charging. Each pick adds no new violation because of batteries.</div>
      <div class="pb-ranklist">${rm.rows.map((r) => `
        <div class="pb-rank${r.tf === st.sel ? ' on' : ''}" data-tf="${r.tf}">
          <span class="pb-rank-n">${r.rank}</span>
          <span class="pb-rank-h"><b>${esc(r.home)}</b> <span class="pb-sub">on ${esc(r.tfName)}</span></span>
          <span class="pb-rank-v">${has(r.value) ? num(r.value, { money: true, digits: 2 }) : missingHTML()}</span>
          <span></span>
          <span class="pb-sub">removes ${has(r.stress) ? num(r.stress, { digits: 2, unit: ' h' }) : '—'} over nameplate · month peak ${has(r.peak) ? num(r.peak, { digits: 1, unit: '%' }) : '—'} with it</span>
          <span class="pb-sub">energy value</span>
        </div>`).join('')}</div>
      <div class="pb-foot">sim.p2_build ranking, aware-core-d26-g0 · stress hours SIM (surrogate, calibrated to OpenDSS) · energy value DERIVED from REAL prices, not Base's profit</div>`;
  }

  // ---------------- render + events ----------------
  function renderToggle() {
    const el = $('toggle');
    if (st.q === 1) {
      el.innerHTML = `<div class="pb-seg pb-seg-ink">${[['naive', 'A · Naive split'], ['aware', 'B · Feeder-aware'], ['diff', 'What B adds']].map(([v, t]) => `<button type="button" class="pb-seg-b${st.view === v ? ' on' : ''}" data-view="${v}">${t}</button>`).join('')}</div>`;
    } else el.innerHTML = '<span class="pb-chip-ours">Feeder-aware</span>';
  }
  function renderAside() {
    const html = st.q === 1 ? q1HTML() : st.q === 2 ? q2HTML() : st.q === 3 ? q3HTML() : q4HTML();
    $('aside').innerHTML = html;
    if (st.q === 3) scheduleDecide();
  }
  function renderRail() {
    for (const b of root.querySelectorAll('.pb-q-btn')) b.classList.toggle('on', Number(b.dataset.q) === st.q);
  }
  function render() { renderRail(); renderToggle(); paintMap(); renderAside(); writeURL(); }

  // verdicts: decide() for the shortlist only (3-16 ms each), after the first paint
  let decideTimer = null;
  function scheduleDecide() {
    if (!lib || typeof lib.decide !== 'function' || !planner) return;
    clearTimeout(decideTimer);
    decideTimer = setTimeout(() => {
      const list = upgradeShortlist(upgradeRows(planner, st.g, earnMin)).filter((r) => !r.onBoard);
      let changed = false;
      for (const r of list) {
        const key = `${st.g}:${r.tf}`;
        if (decideCache.has(key)) continue;
        try {
          const knobs = { setting: 'aware-screen', dispatch: 'aware', credit: false, referral: false, q: 'q0', growth: st.g, cost: 1, value: 0 };
          const pr = typeof lib.paramsFor === 'function' ? lib.paramsFor(planner, r.tf, r.now, knobs) : null;
          if (!pr) throw new Error('paramsFor not built yet');
          const p = { ...(pr.p || pr) };
          if (st.g !== 'g0') p.c = r.c;                      // growth: the cap from perK.<g> (one size up stays at today's load)
          const tfRow = planner.tfs[r.row];
          const dec = pr.deciles || p.deciles || (planner.demand && planner.demand.curves && planner.demand.curves[tfRow.nb && tfRow.nb.key] && planner.demand.curves[tfRow.nb.key].q0);
          if (!dec) throw new Error('demand curves not exported');
          decideCache.set(key, lib.decide(p, dec, planner.decision && planner.decision.seed));
        } catch (e) { decideCache.set(key, { err: String(e && e.message || e) }); }
        changed = true;
      }
      if (changed && st.q === 3) $('aside').innerHTML = q3HTML();
    }, 0);
  }

  const pick = (tf) => { if (!Number.isInteger(tf) || tf < 0 || tf >= NT) return; st.sel = tf; if (st.q === 1) st.q = 2; render(); };
  const onClick = (e) => {
    const qb = e.target.closest('.pb-q-btn'); if (qb) { st.q = Number(qb.dataset.q); render(); return; }
    const vb = e.target.closest('[data-view]'); if (vb) { st.view = vb.dataset.view; renderToggle(); paintMap(); return; }
    const gb = e.target.closest('[data-g]'); if (gb && !gb.disabled) { st.g = gb.dataset.g; paintMap(); renderAside(); return; }
    const dot = e.target.closest('circle[data-tf]'); if (dot) { pick(Number(dot.dataset.tf)); return; }
    const row = e.target.closest('.pb-up[data-tf], .pb-rank[data-tf]'); if (row) { st.sel = Number(row.dataset.tf); paintMap(); renderAside(); writeURL(); }
  };
  const onInput = (e) => {
    if (e.target.matches('[data-pb="n"]')) {
      st.n = Math.max(0, Math.min(50, Number(e.target.value) || 0));
      const aside = $('aside'), sc = aside.scrollTop;
      aside.innerHTML = q2HTML(); aside.scrollTop = sc;
      const s = aside.querySelector('[data-pb="n"]'); if (s) s.focus();
      writeURL();
    }
  };
  const onChange = (e) => { if (e.target.matches('[data-pb="loc"]')) { st.sel = Number(e.target.value); paintMap(); renderAside(); writeURL(); } };
  root.addEventListener('click', onClick);
  root.addEventListener('input', onInput);
  root.addEventListener('change', onChange);
  render();

  return {
    dispose() {
      clearTimeout(decideTimer);
      root.removeEventListener('click', onClick); root.removeEventListener('input', onInput); root.removeEventListener('change', onChange);
      root.innerHTML = ''; root.classList.remove('pb-page', 'pb-learn');
    },
  };
}
