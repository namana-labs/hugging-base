// ui/story/learnings.js (UI-B): Screen 4b Learnings (docs/design-handoff/story-flow/README.md "Screen 4").
// Left rail, four questions (?q=1-4, &tf=<index>, &n=<0..kMax>):
//   Q1 compare charging: p2/index.json usefulCapacity.aware vs usefulCapacity.naiveOpenDSS (NOT the 383 screen);
//      map coloured by the planner's room/full status per transformer (cap.*.shown vs installed); fallback when the
//      planner is missing: P2 baseline.peak bucketed by the TIER_AMBER_PCT / TIER_NORMAL_PCT constants
//   Q2 one transformer 0..kMax: p2/planner.json caps (naive / utility rule / feeder-aware, OpenDSS wins: cap.*.shown)
//      with the OpenDSS pill; perK.g0 per-k peaks at n
//   Q3 RZ's upgrade priority list: planner.json rankingByGrowth.g0 / g20 / g50 as sim.planner wrote it (no ranking logic
//      in the browser), verdicts from ui/lib/planner.js paramsFor() + decide() + verdict()
//   Q4 where a battery helps most: top of p2/aware-core-d26-g0.json ranking
// Q2-Q4 are feeder-aware only. A missing file or field says "not built yet" / "not exported"; never a zero, never a
// typed-in value. No language model produces a rank or verdict here: sim.planner, sim.p2_build and planner.js do.

import { TIER_RGB, TIER_WORDS } from '../lib/icons.js';

export const PAGE = 'learnings';
const PLANNER_LIB = '../lib/planner.js';
const TOP_N = 10;                                   // rows shown for Q4 (a display choice; ranks come from the file)
const UPGRADE_SHOWN = 8, ONBOARD_SHOWN = 2;         // Q3 rows shown (display choice)

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];
export const isLab = (x) => x != null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
const has = (x) => isLab(x) && x.v != null;
const fin = (x) => typeof x === 'number' && Number.isFinite(x);
export function tagHTML(label, cite, screening = false) {
  const one = (l, c) => `<span class="chip chip-${esc(l)}"${c ? ` title="${esc(c)}"` : ''}>${esc(l)}</span>`;
  return one(label, cite) + (screening ? one('SCREENING', `Screening estimate, not checked by OpenDSS.${cite ? ` ${cite}` : ''}`) : '');
}
export const missingHTML = (what = 'not exported') => `<span class="pb-missing">${esc(what)}</span>`;
export function fmtNum(v, d = 0) {
  if (v == null || !Number.isFinite(+v)) return '—';
  return Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
/** A named constant {value, label, cite} from the first doc that carries it, as a labelled value; else null. */
export function constOf(name, ...docs) {
  for (const d of docs) {
    const c = d && d.constants && d.constants[name];
    if (c && typeof c === 'object' && 'value' in c && LABELS.includes(c.label) && c.value != null) return { v: c.value, label: c.label, cite: c.cite };
  }
  return null;
}
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
/** "2026-08" -> "August 2026"; null when unparseable. */
export function monthName(ym) {
  const m = /^(\d{4})-(\d{2})/.exec(String(ym || ''));
  return m && +m[2] >= 1 && +m[2] <= 12 ? `${MONTHS[+m[2] - 1]} ${m[1]}` : null;
}

export function questions(kMax, nTop) {
  return [
    { q: 1, title: 'Compare charging algorithms', sub: 'A/B: same feeder, naive vs feeder-aware' },
    { q: 2, title: 'How many more can we deploy?', sub: 'One transformer, one battery at a time' },
    { q: 3, title: 'Which transformers should we upgrade?', sub: 'The tightest as home load grows' },
    { q: 4, title: 'Where does a battery help most?', sub: 'The next homes, ranked' },
  ];
}

/** Parse ?q, tf, n (numbers or strings; null = absent). tf/n are null when absent or out of range. */
export function parseParams(p = {}, nTf = 0, kMax = null) {
  const int = (x) => (x === '' || x == null ? NaN : Number(x));
  const q = int(p.q), tf = int(p.tf), n = int(p.n);
  return {
    q: Number.isInteger(q) && q >= 1 && q <= 4 ? q : 1,
    tf: Number.isInteger(tf) && tf >= 0 && tf < nTf ? tf : null,
    n: Number.isInteger(n) && n >= 0 && (kMax == null || n <= kMax) ? n : null,
  };
}

// ---- map geometry (local metres around topology.meta.source) ------------------------------------------------------
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

// ---- planner helpers (planner.json hb.planner.v1) -------------------------------------------------------------------
/** tf -> row index of planner.tfs / perK (both follow meta.tfOrder). */
export function plannerRows(planner) {
  const m = new Map();
  const order = planner && planner.meta && Array.isArray(planner.meta.tfOrder) ? planner.meta.tfOrder : (planner && planner.tfs || []).map((t) => t.tf);
  order.forEach((tf, i) => m.set(tf, i));
  return m;
}
/** The cap to show: OpenDSS wins (cap.shown, DESIGN §3.1.7). pill: 'agree' | 'lower' (OpenDSS stricter) | 'screening'. */
export function effectiveCap(cap, referee) {
  if (!has(cap)) return null;
  const checked = !!(referee && referee.status === 'checked') && !cap.screening;
  const v = fin(cap.shown) ? cap.shown : cap.v;
  const pill = checked && cap.opendss === 'agree' ? 'agree' : checked && cap.opendss === 'lower' ? 'lower' : 'screening';
  const cite = `${cap.cite || ''}${pill === 'lower' ? `; OpenDSS found an overload at ${cap.v}, so ${v} is shown${cap.note ? ` (${cap.note})` : ''}` : ''}`;
  return { v, label: cap.label, cite, pill, raw: cap.v };
}
/** Room status from a cap and the batteries there today: 0 has room (2+), 1 room for one more, 2 at capacity, 3 over. */
export function roomStatus(cap, installed) {
  if (cap == null || installed == null) return -1;
  const spare = cap - installed;
  return spare < 0 ? 3 : spare === 0 ? 2 : spare === 1 ? 1 : 0;
}
const hex = (c) => `#${c.slice(0, 3).map((x) => x.toString(16).padStart(2, '0')).join('')}`;
// room (tier-0 sage), one more (neutral, not a tier), at capacity (tier 1), over (tier 4): ui/lib/icons.js TIER_RGB
export const STATUS_COL = [hex(TIER_RGB[0]), '#d9d4c3', hex(TIER_RGB[1]), hex(TIER_RGB[4])];
export const EXCL_COL = '#b9b4a6';
export const ROOM_NAMES = ['has room', 'room for one more', 'at capacity', 'over capacity today'];
/** P2 baseline peak (pct x10) -> 0 under nameplate, 2 over nameplate, 3 over the normal rating (thresholds from the
 *  file's TIER_AMBER_PCT / TIER_NORMAL_PCT). */
export const peakBucket = (p10, amber, normal) => { const p = p10 / 10; return p > normal ? 3 : p > amber ? 2 : 0; };

/** Per-transformer status arrays [nTf] for naive and aware (-1 = excluded / not in the planner). */
export function q1Status(nTf, planner, p2n, p2a) {
  if (planner && Array.isArray(planner.tfs) && planner.tfs.length) {
    const naive = new Array(nTf).fill(-1), aware = new Array(nTf).fill(-1);
    for (const t of planner.tfs) {
      const inst = has(t.installed) ? t.installed.v + (has(t.pending) ? t.pending.v : 0) : null;
      const cn = effectiveCap(t.cap && t.cap.naive, planner.referee), ca = effectiveCap(t.cap && t.cap.aware, planner.referee);
      if (t.tf >= 0 && t.tf < nTf) { naive[t.tf] = roomStatus(cn ? cn.v : null, inst); aware[t.tf] = roomStatus(ca ? ca.v : null, inst); }
    }
    return { mode: 'planner', naive, aware, names: ROOM_NAMES };
  }
  const amber = constOf('TIER_AMBER_PCT', p2a, p2n), normal = constOf('TIER_NORMAL_PCT', p2a, p2n);
  if (p2n && p2a && p2n.baseline && p2a.baseline && amber && normal) {
    const b = (arr) => arr.map((x) => peakBucket(x, amber.v, normal.v));
    return { mode: 'peak', naive: b(p2n.baseline.peak), aware: b(p2a.baseline.peak), amber, normal,
      names: [`under ${fmtNum(amber.v)}% of nameplate`, '', `over nameplate (${fmtNum(amber.v)}–${fmtNum(normal.v)}%)`, `over the normal rating (${fmtNum(normal.v)}%)`] };
  }
  return null;
}
export const countBy = (arr, vals) => vals.map((v) => arr.filter((x) => x === v).length);

/** Growth levels for Q3: [{g (pct), id 'g<pct>', ok}]; ok = planner.json carries that level's upgrade list. */
export function growthLevels(planner) {
  const lv = planner && planner.meta && Array.isArray(planner.meta.growth) ? planner.meta.growth : [];
  return lv.map((g) => ({ g, id: `g${g}`, ok: Array.isArray(rankingOf(planner, g)) }));
}
/** RZ's upgrade priority list at a growth level, as sim.planner wrote it: rankingByGrowth.g<g> (g0 == ranking).
 *  No ranking logic runs in the browser. null when the file does not carry that level. */
export function rankingOf(planner, growth = 0) {
  if (!planner) return null;
  const byG = planner.rankingByGrowth && planner.rankingByGrowth[`g${growth}`];
  if (Array.isArray(byG)) return byG;
  return growth === 0 && Array.isArray(planner.ranking) ? planner.ranking : null;
}
/** The list to show at a growth level: the file's rows, plus the transformer's own facts for the page's words
 *  (installed + pending = planner.js's "Cores wanted here now", the utility rule's count) and, at +g%, how the
 *  feeder-aware-control count moved against today's load (fitFrom). */
export function upgradeList(planner, growth = 0) {
  const src = rankingOf(planner, growth);
  if (!src) return [];
  const byTf = new Map((planner.tfs || []).map((t) => [t.tf, t]));
  const today = new Map((rankingOf(planner, 0) || []).map((x) => [x.tf, x]));
  return src.map((x) => {
    const r = byTf.get(x.tf);
    const k0 = r ? (has(r.installed) ? r.installed.v : 0) + (has(r.pending) ? r.pending.v : 0) : null;
    const t0 = today.get(x.tf);
    const fitFrom = growth && t0 && has(t0.controlsFit) && has(x.controlsFit) && t0.controlsFit.v !== x.controlsFit.v ? t0.controlsFit.v : null;
    return { ...x, k0, paper: r && r.cap && has(r.cap.paper) ? r.cap.paper : null, fitFrom };
  });
}
/** What home-load growth does to the list, read from the file: does the order hold (same transformers, same order,
 *  same members unlocked), and which rows' feeder-aware-control count moved, up or down. */
export function growthStory(planner, growth) {
  const a = rankingOf(planner, 0), b = rankingOf(planner, growth);
  if (!a || !b) return null;
  const sameOrder = a.length === b.length && a.every((x, i) => x.tf === b[i].tf);
  const sameUnlocked = sameOrder && a.every((x, i) => has(x.unlocked) && has(b[i].unlocked) && x.unlocked.v === b[i].unlocked.v);
  const changed = upgradeList(planner, growth).filter((x) => x.fitFrom != null).map((x) => ({ tf: x.tf, from: x.fitFrom, to: x.controlsFit.v }));
  return { n: b.length, sameOrder, sameUnlocked, changed, up: changed.filter((c) => c.to > c.from).length, down: changed.filter((c) => c.to < c.from).length,
    approx: b.filter((x) => x.approx).length };
}
/** The rows the page shows: the first `n` that unlock something, then up to `nb` "already on board" rows. */
export function upgradeShortlist(rows, n = UPGRADE_SHOWN, nb = ONBOARD_SHOWN) {
  return [...rows.filter((r) => r.why !== 'onboard').slice(0, n), ...rows.filter((r) => r.why === 'onboard').slice(0, nb)];
}
/** Q3's rows: the shortlist, plus (at +g%) every row whose feeder-aware-control count moved, in the file's rank order. */
export function q3Rows(all) {
  const short = upgradeShortlist(all);
  const moved = all.filter((r) => r.fitFrom != null && !short.includes(r));
  return [...short, ...moved].sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
}
/** planner.js verdict() codes -> the page's words (DESIGN §3.4.4). */
export const VERDICT_WORDS = {
  'no-upgrade': 'No upgrade needed', 'wait-and-watch': 'Wait and watch', 'upgrade-now': 'Upgrade now',
  'dont-upgrade': 'Don\'t upgrade', 'dont-upgrade-tell': 'Don\'t upgrade: tell the member before install day',
};
export function verdictWords(code, horizon) {
  const w = VERDICT_WORDS[code];
  if (!w) return null;
  const why = {
    'no-upgrade': `fits today and unlikely to outgrow its cap within ${horizon != null ? `${fmtNum(horizon)} years` : 'the horizon'}, even with fast growth`,
    'wait-and-watch': 'fits today; least regret is to upgrade when the next battery is sold',
    'upgrade-now': 'least regret over slow, typical and fast growth is to upgrade now',
    'dont-upgrade': 'least regret is never to upgrade',
    'dont-upgrade-tell': 'over the cap today and upgrading costs more than the members it unlocks',
  }[code];
  return { word: w, why };
}

/** Q4 headline and rows from a P2 combo's ranking (top n). */
export function rankingModel(p2a, topo, n = TOP_N) {
  const rank = (p2a && Array.isArray(p2a.ranking) ? p2a.ranking : []).slice(0, n);
  const r0 = rank[0];
  const of = p2a && p2a.flip && has(p2a.flip.entries) ? p2a.flip.entries : null;     // collapsed: one entry per transformer
  const nn = rank.map((r) => r.noNewViolation).filter(isLab);
  return {
    of,
    lead: r0 ? { home: r0.label, tf: r0.tf, tfName: tfName(topo, r0.tf), rank: r0.rank, stress: has(r0.stressAvoidedH) ? r0.stressAvoidedH : null } : null,
    // "no new violation because of batteries" only when every shown pick's own field says so (surrogate: screening)
    noNew: rank.length && nn.length === rank.length ? { all: nn.every((x) => x.v === true), n: nn.filter((x) => x.v === true).length, of: rank.length, label: nn[0].label, cite: nn[0].cite } : null,
    rows: rank.map((r) => ({ rank: r.rank, home: r.label, tf: r.tf, tfName: tfName(topo, r.tf), stress: r.stressAvoidedH, peak: r.peakWithPct, value: r.revenueUSD, screening: r.screening })),
    tfs: [...new Set(rank.map((r) => r.tf))],
  };
}

/** Fit cells 0..kMax for one limit: fit up to `limit`; `hypo` marks cells planner.js rackStates() calls hypothetical. */
export function stripCells(limit, kMax, hypo = []) {
  return Array.from({ length: kMax + 1 }, (_, i) => ({ fit: limit != null && i <= limit && i > 0, zero: i === 0, hypo: !!hypo[i] }));
}

// =================================================================================================================
// DOM
// =================================================================================================================
async function tryGet(fn) { try { return { doc: await fn(), err: null }; } catch (e) { return { doc: null, err: e }; } }
const notBuilt = (err, path) => (err && err.status === 404 ? `not built yet: ${path}` : `could not load ${path}`);

async function loadPlannerLib(ctx) {
  try { return await import(PLANNER_LIB); } catch (e) { return null; }
}

export async function mount(root, ctx) {
  root.classList.add('pb-page', 'pb-learn');
  root.innerHTML = '<div class="pb-loading">Loading the learnings…</div>';
  const [topoR, idxR, plR, p2aR, p2nR, lib] = await Promise.all([
    tryGet(() => ctx.getJSON('topology.json')), tryGet(() => ctx.getJSON('p2/index.json')), tryGet(() => ctx.getJSON('p2/planner.json')),
    tryGet(() => ctx.getJSON('p2/aware-core-d26-g0.json')), tryGet(() => ctx.getJSON('p2/naive-core-d26-g0.json')), loadPlannerLib(ctx),
  ]);
  const topo = topoR.doc;
  if (!topo) { root.innerHTML = `<div class="pb-loading">${missingHTML(notBuilt(topoR.err, 'topology.json'))}</div>`; return { dispose() { root.innerHTML = ''; root.classList.remove('pb-page', 'pb-learn'); } }; }
  const idx = idxR.doc, planner = plR.doc, p2a = p2aR.doc, p2n = p2nR.doc;
  const NT = topo.transformers.length;
  const geo = project(topo);
  const rows = plannerRows(planner);
  const kMax = planner && planner.meta && Number.isInteger(planner.meta.kMax) ? planner.meta.kMax : null;
  const pp = parseParams(ctx.params || {}, NT, kMax);
  const defaultTf = planner && planner.meta && Number.isInteger(planner.meta.defaultTf) ? planner.meta.defaultTf : null;
  const earn = constOf('PLAN_AWARE_EARN_MIN', planner);
  const horizon = planner && planner.money && has(planner.money.horizonYears) ? planner.money.horizonYears.v : null;
  const month = monthName(idx && idx.month);
  const s1 = q1Status(NT, planner, p2n, p2a);
  const nTop = p2a && Array.isArray(p2a.ranking) ? Math.min(TOP_N, p2a.ranking.length) : null;
  const QS = questions(kMax, nTop);
  const st = { q: pp.q, view: 'diff', g: 0, sel: pp.tf ?? defaultTf, n: pp.n, nSet: pp.n != null };
  const decideCache = new Map();
  const capsOf = (tf) => {
    const row = rows.get(tf), t = row != null && planner ? planner.tfs[row] : null;
    if (!t) return null;
    return { t, row, cn: effectiveCap(t.cap.naive, planner.referee), ca: effectiveCap(t.cap.aware, planner.referee), cp: has(t.cap.paper) ? t.cap.paper : null };
  };
  const nFor = () => { if (st.nSet && st.n != null) return st.n; const c = st.sel != null ? capsOf(st.sel) : null; return c && c.ca ? c.ca.v : 0; };

  root.innerHTML = `
    <div class="pb-learn-grid">
      <nav class="pb-rail" aria-label="Key takeaways">
        <div class="pb-eyebrow pb-rail-h">KEY TAKEAWAYS</div>
        ${QS.map((x) => `<button type="button" class="pb-q-btn" data-q="${x.q}"><span class="pb-q-dot">${x.q}</span><span class="pb-q-txt"><span class="pb-q-title">${esc(x.title)}</span><span class="pb-q-sub">${esc(x.sub)}</span></span></button>`).join('')}
      </nav>
      <section class="pb-mapcol">
        <div class="pb-maphead"><div data-pb="toggle"></div><span class="pb-sub pb-right" data-pb="caption"></span></div>
        <div class="pb-map">
          <svg viewBox="${geo.vb}" preserveAspectRatio="xMidYMid meet" data-pb="svg" aria-label="The feeder's ${NT} service transformers">
            <path d="${geo.edges}" fill="none" stroke="#c3c9bf" stroke-width="${geo.ew}" stroke-linecap="round"/>
            <g data-pb="dots">${geo.pts.map((p, i) => `<circle data-tf="${i}" cx="${p[0]}" cy="${p[1]}" r="${geo.r}" fill="#d9d4c3" stroke="#fffdf8" stroke-width="${geo.sw}"><title>${esc(tfName(topo, i))}</title></circle>`).join('')}</g>
            <circle data-pb="ring" r="${geo.rr}" fill="none" stroke="#10231a" stroke-width="${geo.sw2}" cx="-99999" cy="-99999"/>
          </svg>
          <div class="pb-maplegend" data-pb="legend"></div>
        </div>
        <div class="pb-mapsrc" data-pb="src"></div>
      </section>
      <aside class="pb-aside" data-pb="aside"></aside>
    </div>`;
  const $ = (s) => root.querySelector(`[data-pb="${s}"]`);
  const dots = [...root.querySelectorAll('[data-pb="dots"] circle')];

  const writeURL = () => {
    try {
      if (typeof ctx.link !== 'function') return;
      const href = ctx.link({ page: 'learnings', q: st.q !== 1 ? st.q : null, tf: st.sel != null && st.sel !== defaultTf ? st.sel : null, n: st.nSet ? st.n : null });
      if (href && typeof history !== 'undefined') history.replaceState(history.state, '', href);
    } catch (e) { console.error('[learnings] link', e); }
  };
  const num = (x, opts) => { if (!has(x)) return missingHTML(); try { return ctx.num(x, opts); } catch (e) { console.error('[learnings] unlabelled value refused', x, e); return missingHTML('unlabelled value refused'); } };

  // ---------------- map painting ----------------
  function paint(colours, legend, caption, src, ringOn = true, countCite = null) {
    dots.forEach((d, i) => d.setAttribute('fill', colours[i] || EXCL_COL));
    // the counts are this page's tally of a file's rows: one DERIVED tag heads them, its cite names the file and field
    $('legend').innerHTML = (legend.length && countCite ? `<span class="pb-leg-h">transformers${tagHTML('DERIVED', countCite)}</span>` : '')
      + legend.map((l) => `<span><i style="background:${l.c}"></i>${l.html || esc(l.name)}<b>${l.n != null ? fmtNum(l.n) : ''}</b></span>`).join('');
    $('caption').innerHTML = caption;                  // callers pass HTML (plain words, or words with a tag)
    $('src').innerHTML = src;
    const ring = $('ring'), p = st.sel != null ? geo.pts[st.sel] : null;
    ring.setAttribute('cx', ringOn && p ? p[0] : -99999); ring.setAttribute('cy', ringOn && p ? p[1] : -99999);
  }
  const statusColours = (arr) => arr.map((s) => (s < 0 ? EXCL_COL : STATUS_COL[s]));
  const statusLegend = (arr, names) => {
    const c = countBy(arr, [0, 1, 2, 3, -1]);
    const L = names.map((name, i) => ({ name, c: STATUS_COL[i], n: c[i] })).filter((x, i) => x.name && (c[i] || s1.mode === 'planner'));
    if (c[4]) L.push({ name: 'not homes (excluded)', c: EXCL_COL, n: c[4] });
    return L;
  };
  const srcQ1 = () => (s1 && s1.mode === 'planner'
    ? `${tagHTML('SIM', 'p2/planner.json tfs[].cap.*.shown (surrogate sweep; OpenDSS wins where it is stricter) vs tfs[].installed')}Room = the most that fit (planner, from an empty feeder) minus our batteries there today ${tagHTML('ASSUMPTION', planner.sources && planner.sources.fleet ? planner.sources.fleet.text : 'the prototype placement')}`
    : s1 ? `${tagHTML('SIM', 'P2 baseline.peak (sim.surrogate, calibrated vs OpenDSS)')}Month peak with our batteries · planner not built yet, so coloured by loading ${tagHTML(s1.amber.label, s1.amber.cite)}` : missingHTML('not built yet: p2/planner.json and the P2 combos'));

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
        ], 'What feeder-aware adds: full under naive, room under feeder-aware', srcQ1(), st.q === 2,
        s1.mode === 'planner' ? 'count of p2/planner.json tfs by room status under cap.naive.shown and cap.aware.shown vs installed + pending; topology transformers not in tfs are excluded'
          : 'count of transformers by p2/naive- and aware-core-d26-g0.json baseline.peak against TIER_AMBER_PCT / TIER_NORMAL_PCT');
      } else {
        const arr = s1[view];
        paint(statusColours(arr), statusLegend(arr, s1.names), view === 'aware' ? 'B · Feeder-aware: which transformers have room' : 'A · Naive split: which transformers have room', srcQ1(), st.q === 2,
          s1.mode === 'planner' ? `count of p2/planner.json tfs by room status: cap.${view}.shown minus installed + pending; topology transformers not in tfs are excluded`
            : `count of transformers by p2/${view}-core-d26-g0.json baseline.peak against TIER_AMBER_PCT / TIER_NORMAL_PCT`);
      }
      if (st.q === 2) $('caption').textContent = 'Feeder-aware · room per transformer · click one to pick it';
      return;
    }
    if (st.q === 3) {
      const list = upgradeList(planner, st.g);
      const byTf = new Map(list.map((r) => [r.tf, r]));
      const col = topo.transformers.map((_, i) => { const r = byTf.get(i); if (!rows.has(i)) return EXCL_COL; if (!r) return STATUS_COL[0]; return r.why === 'blocked' ? STATUS_COL[3] : r.why === 'onboard' ? STATUS_COL[2] : STATUS_COL[1]; });
      const c = (k) => col.filter((x) => x === k).length;
      const Hh = horizon != null ? num(planner.money.horizonYears, { digits: 0, unit: ' years' }) : 'the horizon';
      const gc = constOf('PLAN_GROWTH_PCTS', planner);
      paint(planner ? col : new Array(NT).fill(EXCL_COL), planner ? [
        { name: 'room for the horizon', html: `room for ${Hh}`, c: STATUS_COL[0], n: c(STATUS_COL[0]) }, { name: 'may outgrow', html: `may outgrow within ${Hh} (fast growth)`, c: STATUS_COL[1], n: c(STATUS_COL[1]) },
        { name: 'full, every home already a member', c: STATUS_COL[2], n: c(STATUS_COL[2]) }, { name: 'a battery blocked today', c: STATUS_COL[3], n: c(STATUS_COL[3]) },
        { name: 'not homes (excluded)', c: EXCL_COL, n: c(EXCL_COL) },
      ] : [], `Feeder-aware, utility rule unchanged · ${st.g ? `home load +${st.g}%${gc ? tagHTML(gc.label, gc.cite) : ''}` : 'today\'s load'}`,
      planner ? `${tagHTML('DERIVED', planner.decision && planner.decision.cite)}Capacity binds at min(feeder-aware, utility rule); demand from the planner's decile curves` : missingHTML(notBuilt(plR.err, 'p2/planner.json')),
      true, `count of p2/planner.json rankingByGrowth.g${st.g} rows by why (blocked / onboard / the rest); tfs not listed there: room; topology transformers not in tfs are excluded`);
      return;
    }
    const rm = rankingModel(p2a, topo);
    const top = new Set(rm.tfs);
    paint(topo.transformers.map((_, i) => (top.has(i) ? '#1e4d2b' : '#d9d4c3')), [
      { name: 'a top-ranked next-battery home', c: '#1e4d2b', n: top.size }, { name: 'other transformers', c: '#d9d4c3', n: NT - top.size },
    ], 'Feeder-aware · where the next batteries go', p2a ? `${tagHTML('SIM', 'sim.p2_build ranking (surrogate, calibrated vs OpenDSS)')}sim.p2_build ranking${month ? ` · ${esc(month)}` : ''} · feeder-aware` : missingHTML(notBuilt(p2aR.err, 'p2/aware-core-d26-g0.json')),
    true, 'count of transformers in p2/aware-core-d26-g0.json ranking (the rows shown) and of the rest of topology.json transformers');
  }

  // ---------------- aside panels ----------------
  function q1HTML() {
    const uc = idx && idx.usefulCapacity;
    const A = uc && uc.aware, N = uc && uc.naiveOpenDSS;
    if (!uc) return `<div class="pb-eyebrow">WHICH TRANSFORMERS HAVE ROOM</div>${missingHTML(notBuilt(idxR.err, 'p2/index.json'))}`;
    const fullN = s1 && s1.mode === 'planner' ? s1.naive.filter((x) => x >= 2).length : null, fullA = s1 && s1.mode === 'planner' ? s1.aware.filter((x) => x >= 2).length : null;
    const fail = N && N.failAt != null ? N.failAt : null;
    const cols = N && N.checkCols ? N.checkCols : [];
    const failRow = N && Array.isArray(N.checks) ? N.checks.find((r) => r[0] === fail) : null;
    const colOf = (name) => (failRow && cols.includes(name) ? failRow[cols.indexOf(name)] : null);
    const headAt = colOf('headMaxPct'), causedAt = colOf('causedNormal'), headOver = colOf('headStepsOver100'), holds = colOf('holds');
    // the file says which check failed (holds, causedNormal, headStepsOver100); the browser applies no threshold
    const whyFail = failRow && holds === false ? (causedAt ? `${fmtNum(causedAt)} battery-caused transformer event${causedAt === 1 ? '' : 's'}` : headOver ? `the feeder-head cable over its rating (peak ${fmtNum(headAt, 1)}%)` : 'a violation') : null;
    const nTag = has(N) ? tagHTML(N.label, N.cite) : '', aTag = has(A) ? tagHTML(A.label, A.cite) : '';
    const eligible = topo.meta && topo.meta.counts && Number.isInteger(topo.meta.counts.eligible) ? topo.meta.counts.eligible : null;
    const capTag = (k) => { const t0 = planner && planner.tfs && planner.tfs.find((t) => t.cap && isLab(t.cap[k])); return t0 ? tagHTML(t0.cap[k].label, `count of transformers whose planner cap (cap.${k}.shown) is at or below the batteries there today`) : ''; };
    const every = idx.stepMinutes != null ? `every ${fmtNum(idx.stepMinutes)} minutes` : 'every step';
    const of = month ? ` of ${month}` : '';
    return `
      <div class="pb-eyebrow">WHICH TRANSFORMERS HAVE ROOM</div>
      <div class="pb-headline">The same feeder holds ${has(A) ? num(A, { digits: 0 }) : '—'} batteries with feeder-aware charging, and ${has(N) ? num(N, { digits: 0 }) : '—'} with a naive split.</div>
      <div class="pb-two">
        <div class="pb-capt"><span class="pb-capt-t">A · Naive split</span><span class="pb-capt-big">${has(N) ? num(N, { digits: 0 }) : missingHTML('naiveOpenDSS not exported')}</span><span class="pb-sub">useful capacity, OpenDSS-judged${fullN != null ? ` · ${fmtNum(fullN)}${capTag('naive')} transformers full or over today` : ''}</span></div>
        <div class="pb-capt pb-capt-ours"><span class="pb-capt-t">B · Feeder-aware</span><span class="pb-capt-big">${has(A) ? num(A, { digits: 0 }) : missingHTML()}</span><span class="pb-sub">useful capacity, OpenDSS-checked${fullA != null ? ` · ${fmtNum(fullA)}${capTag('aware')} transformers full or over today` : ''}</span></div>
      </div>
      <div class="pb-body">Useful capacity is how many batteries fit, placed one at a time from an empty feeder in the same order, before the next one causes a problem.</div>
      <div class="pb-body"><b>Naive</b> is our assumption of one number, no feeder check: every battery charges at once when the price drops. OpenDSS stepped it one battery at a time: ${has(N) ? num(N, { digits: 0 }) : '—'} hold for the whole month${of}${fail != null ? `; battery ${fmtNum(fail)} brings ${esc(whyFail || 'a violation')}${nTag}` : ''}.</div>
      <div class="pb-body"><b>Feeder-aware</b> charges each transformer only into the room it has, so it places ${has(A) && eligible != null && A.v === eligible ? `a battery at every one of the ${num(A, { digits: 0 })} eligible homes` : `${has(A) ? num(A, { digits: 0 }) : '—'} batteries`} with no transformer event because of batteries (OpenDSS, ${esc(every)}${esc(of)})${uc.cap && has(uc.cap) ? `; it would stop if the feeder had to give up more than ${num({ ...uc.cap, v: uc.cap.v * 100 }, { digits: 0, unit: '%' })} of its charge` : ''}.</div>
      <div class="pb-foot">${esc(uc.scopeText || '')} · sim.p2_build usefulCapacity · aware ${has(A) ? tagHTML(A.label, A.cite) : ''} naive ${has(N) ? tagHTML(N.label, N.cite) : ''}</div>`;
  }

  const TIER = TIER_WORDS.map((w) => w.toLowerCase());
  function q2HTML() {
    const eyebrow = '<div class="pb-row-b"><span class="pb-eyebrow">HOW MANY FIT ON ONE TRANSFORMER</span></div>';
    if (!planner || kMax == null) return `${eyebrow}${missingHTML(notBuilt(plR.err, 'p2/planner.json'))}<div class="pb-body">The per-transformer curves come from the capacity planner (sim.planner).</div>`;
    const opts = [...(topo.focus || []).map((f) => f.tf), ...(topo.bridge || []).map((b) => b.tf), planner.meta.demoTf, defaultTf].filter((x) => Number.isInteger(x));
    if (st.sel != null && !opts.includes(st.sel)) opts.push(st.sel);
    const sel = `<select class="pb-select" data-pb="loc">${st.sel == null ? '<option value="" selected>Pick a transformer</option>' : ''}${[...new Set(opts)].map((v) => `<option value="${v}"${v === st.sel ? ' selected' : ''}>${esc(tfName(topo, v))}</option>`).join('')}</select>`;
    if (st.sel == null) return `${eyebrow}${sel}<div class="pb-body">Pick a transformer on the map.</div>`;
    const cs = capsOf(st.sel);
    if (!cs) {
      const behind = (topo.homes || []).filter((h) => h.tf === st.sel);
      const why = behind.length && behind.every((h) => h.use === 'commercial') ? ' serves only small businesses (topology: use commercial), so' : '';
      return `${eyebrow}${sel}<div class="pb-body">${esc(tfName(topo, st.sel))}${why} the planner leaves it out.</div>`;
    }
    const { t, row, cn, ca, cp } = cs;
    const n = Math.min(kMax, nFor());
    const pk = planner.perK && planner.perK.g0;
    const at = (name) => (pk && Array.isArray(pk[name]) && Array.isArray(pk[name][row]) ? pk[name][row][n] : null);
    const nPeak = at('naivePeak'), nTier = at('naiveTier'), aPeak = at('awarePeak'), aEff = at('awareEff');
    const sl = (k) => (planner.series && planner.series[k] && LABELS.includes(planner.series[k].label) ? planner.series[k].label : 'SIM');
    let hypo = [];
    try { if (lib && typeof lib.rackStates === 'function') hypo = [false, ...lib.rackStates(planner, st.sel, kMax, 'aware-screen', 0).map((x) => x.hypothetical)]; } catch (e) { console.error('[learnings] rackStates', e); }
    const firstHypo = hypo.indexOf(true);
    const pill = (c) => (!c || !c.pill ? '' : c.pill === 'agree' ? `<span class="pb-pill" title="${esc(c.cite)}">✓ OpenDSS</span>` : c.pill === 'lower' ? `<span class="pb-pill pb-pill-warn" title="${esc(c.cite)}">OpenDSS: overload at ${fmtNum(c.raw)}</span>` : tagHTML('SCREENING', 'not OpenDSS-checked'));
    const strip = (c) => `<div class="pb-strip" style="--cells:${kMax + 1}">${stripCells(c ? c.v : null, kMax, hypo).map((x) => `<i class="${x.fit ? 'f' : x.zero ? 'z' : 'n'}${x.hypo ? ' h' : ''}"></i>`).join('')}<b style="left:${((n + 0.5) / (kMax + 1) * 100).toFixed(2)}%"></b></div>`;
    const limitRow = (name, verb, c, extra) => `
      <div class="pb-limit">
        <div class="pb-limit-h"><span class="pb-limit-n">${esc(name)}</span>${pill(c)}<span class="pb-right">${verb} <b class="pb-limit-v">${c ? num(c, { digits: 0 }) : missingHTML()}</b></span></div>
        ${strip(c)}${extra ? `<div class="pb-sub">${extra}</div>` : ''}
      </div>`;
    const age = has(t.age) ? `about ${fmtNum(t.age.v)} years old (${t.age.source === 'utility' ? 'utility' : 'simulated'}) ${tagHTML(t.age.label, `${t.age.cite || ''}${t.age.p10 != null ? `; could be ${t.age.p10}–${t.age.p90} years` : ''}`)}` : '';
    const fitsA = ca && n <= ca.v, fitsN = cn && n <= cn.v, fitsP = cp && n <= cp.v;
    const earnTxt = earn ? `${fmtNum(earn.v * 100)}%` : null;
    let answer;
    if (n === 0) answer = 'Slide to add batteries to this transformer.';
    else if (fitsA) answer = `${n} batter${n === 1 ? 'y fits' : 'ies fit'} here with feeder-aware charging${!fitsN && cn ? `; a naive split tops out at ${fmtNum(cn.v)}` : ''}${!fitsP && cp ? `, and the utility's nameplate rule allows only ${fmtNum(cp.v)} today` : ''}.`;
    else answer = `${n} is too many even for feeder-aware: past ${ca ? fmtNum(ca.v) : '—'}, each extra battery earns less${earnTxt ? ` than ${earnTxt} of an unconstrained one` : ''}. Feeder-aware never overloads the transformer because of batteries; it charges less instead, so this limit is about money, not safety.`;
    const perHome = constOf('PLAN_HYPOTHETICAL_PER_HOME', planner);
    const hypoTxt = perHome && firstHypo > 0 && n >= firstHypo ? ` From ${fmtNum(firstHypo)} on, more than ${num(perHome, { digits: 0 })} per home: hypothetical (faded).` : '';
    return `
      ${eyebrow}
      ${sel}
      <div class="pb-sub">${num(t.kva, { digits: 0, unit: ' kVA' })} · ${fmtNum(t.homes)} home${t.homes === 1 ? '' : 's'} · ${num(t.installed, { digits: 0 })} of our batteries today · ${esc(t.mount || '')}</div>
      ${age ? `<div class="pb-sub">${age}</div>` : ''}
      <div class="pb-slider"><input type="range" min="0" max="${kMax}" step="1" value="${n}" data-pb="n" aria-label="Batteries on this transformer"><span class="pb-slider-v">${n}</span></div>
      ${limitRow('Naive', 'fits', cn, nPeak != null ? `at ${n}: month peak ${fmtNum(nPeak / 10, 0)}% of nameplate, ${esc(TIER[nTier] || '')} ${tagHTML(sl('naivePeak'), planner.series && planner.series.naivePeak && planner.series.naivePeak.text, true)}` : missingHTML('per-k peaks not exported'))}
      ${limitRow('Utility rule', 'allows', cp, `nameplate vs kVA: it does not look at when batteries charge ${cp ? tagHTML(cp.label, cp.cite) : ''}`)}
      ${limitRow('Feeder-aware', 'fits', ca, aPeak != null ? `at ${n}: month peak ${fmtNum(aPeak / 10, 0)}% of nameplate, earning like ${fmtNum(aEff / 100, 1)} full batteries ${tagHTML(sl('awarePeak'), planner.series && planner.series.awareEff && planner.series.awareEff.text, true)}` : missingHTML('per-k peaks not exported'))}
      <div class="pb-body">${esc(answer)}${hypoTxt}</div>
      <div class="pb-foot">${esc(planner.meta.naiveWords || 'Naive: our assumption of one number, no feeder check')}. ${esc(planner.meta.awareWords || '')}${earn ? ` ${tagHTML(earn.label, earn.cite)}` : ''} ${esc(planner.meta.scope || '')}</div>`;
  }

  function q3HTML() {
    const eyebrow = `<div class="pb-row-b"><span class="pb-eyebrow">WHICH ARE WORTH UPGRADING</span>${planner && planner.decision ? tagHTML(planner.decision.label, planner.decision.cite) : ''}</div>`;
    if (!planner) return `${eyebrow}${missingHTML(notBuilt(plR.err, 'p2/planner.json'))}<div class="pb-body">The upgrade list comes from the capacity planner (sim.planner): RZ's three-layer scope.</div>`;
    const levels = growthLevels(planner);
    const all = upgradeList(planner, st.g);
    const list = q3Rows(all);
    const money = planner.money || {};
    const blocked = all.filter((r) => r.why === 'blocked').length;
    const N = all.length;
    const ruleBinds = N > 0 && all.every((r) => r.paper && has(r.controlsFit) && r.paper.v <= r.controlsFit.v);
    const story = st.g ? growthStory(planner, st.g) : null;
    const seg = levels.map((l) => `<button type="button" class="pb-seg-b${l.g === st.g ? ' on' : ''}" data-g="${l.g}"${l.ok ? '' : ' disabled title="not exported by the planner"'}>${l.g ? `+${l.g}%` : 'Today\'s load'}${l.ok ? '' : ' · not exported'}</button>`).join('');
    const H = horizon != null ? num(planner.money.horizonYears, { digits: 0, unit: " years" }) : "the horizon";   // HTML: the value with its tag
    const interp = st.g && planner.perK && planner.perK[`g${st.g}`] ? planner.perK[`g${st.g}`].awareInterp || null : null;
    const gSeries = planner.series && planner.series.rankingByGrowth ? planner.series.rankingByGrowth.text : null;
    const upCite = planner.meta && planner.meta.cites && planner.meta.cites.up;
    const lines = list.map((r) => {
      const t = planner.tfs[rows.get(r.tf)] || {};
      const u = r.unlocked;
      const unl = has(u) ? `${fmtNum(u.v, u.v % 1 ? 1 : 0)}${u.p10 !== u.p90 ? ` (${fmtNum(u.p10, u.p10 % 1 ? 1 : 0)}–${fmtNum(u.p90, u.p90 % 1 ? 1 : 0)})` : ''}` : '—';
      const dv = decideCache.get(`${st.g}:${r.tf}`);
      const vw = dv === undefined ? { word: lib ? 'computing…' : 'verdict not built yet', why: lib ? '' : 'ui/lib/planner.js (PLANNER)' } : dv.err ? { word: 'no verdict', why: dv.err } : verdictWords(dv.code, horizon) || { word: dv.code, why: '' };
      const ageTxt = r.age && has(r.age) ? ` · age ${num(r.age, { digits: 0, unit: ' y' })}${t.age && t.age.source !== 'utility' ? ' (simulated)' : ''}` : '';
      const fit = has(r.controlsFit) ? `${r.approx ? '≈' : ''}${num(r.controlsFit, { digits: 0, screening: !!st.g })}${r.approx ? ` <span class="pb-sub" title="${esc(interp || 'interpolated between awareGrid points')}">interpolated</span>` : ''}` : missingHTML();
      const movedTxt = r.fitFrom != null ? ` <b class="pb-moved">${fmtNum(r.fitFrom)} at today's load</b>` : '';
      return `
        <div class="pb-up${r.tf === st.sel ? ' on' : ''}${r.why === 'onboard' ? ' pb-dim' : ''}${r.fitFrom != null ? ' pb-up-moved' : ''}" data-tf="${r.tf}">
          <div class="pb-up-h"><span class="pb-rank-n">${r.rank != null ? `${r.rank}<small> of ${fmtNum(N)}</small>` : ''}</span><b>${esc(tfName(topo, r.tf))}</b><span class="pb-sub">${has(t.kva) ? num(t.kva, { digits: 0, unit: ' kVA' }) : '—'}${t.up && has(t.up.kva) ? ` → ${num(t.up.kva, { digits: 0, unit: ' kVA' })}` : ''} · ${fmtNum(t.homes)} home${t.homes === 1 ? '' : 's'}</span></div>
          <div class="pb-up-v"><span class="pb-verdict-w${vw && /^Upgrade/.test(vw.word) ? ' pb-go' : ''}">${esc(vw ? vw.word : '')}</span>${vw && vw.why ? ` <span class="pb-sub">${esc(vw.why)}</span>${dv && dv.code === 'no-upgrade' && has(planner.money.horizonYears) ? tagHTML(planner.money.horizonYears.label, planner.money.horizonYears.cite) : ''}` : ''}</div>
          <div class="pb-up-b">${has(r.blockedToday) ? `${num(r.blockedToday, { digits: 0 })} blocked today · ` : ''}${has(r.wanted5y) ? `${num(r.wanted5y)} wanted within ${H} · ` : ''}the utility rule allows ${r.paper ? num(r.paper, { digits: 0 }) : missingHTML()} · feeder-aware control would fit ${fit}${movedTxt}</div>
          <div class="pb-up-b">${r.why === 'onboard' ? 'every home here is already a member: an upgrade unlocks no one' : `unlocks <b>${unl}</b> member${has(u) && u.v === 1 ? '' : 's'} ${has(u) ? tagHTML(u.label, `${u.cite}; one size up: ${upCite || 'screening'}`, true) : ''} within ${H}${r.valueUSDYr && has(r.valueUSDYr) && r.valueUSDYr.v ? `, worth ${num(r.valueUSDYr, { money: true, digits: 0 })}/yr` : ''}${has(r.paybackYears) ? ` · pays back in ${num(r.paybackYears, { digits: 1, unit: ' yr' })}` : ''}`}${ageTxt}</div>
        </div>`;
    }).join('');
    let head, note = '';
    const cnt = (x, what) => `${fmtNum(x)}${tagHTML('DERIVED', `count of p2/planner.json ${what}`)}`;
    if (!st.g) head = `At today's load, ${cnt(blocked, 'rankingByGrowth.g0 rows with why = blocked')} of ${cnt(N, 'rankingByGrowth.g0 rows')} listed transformers block a battery wanted now${ruleBinds ? '; the utility\'s nameplate rule is the binding limit on every one' : ''}.`;
    else if (!story) head = `At +${st.g}% home load: not exported by the planner.`;
    else {
      head = story.sameOrder && story.sameUnlocked
        ? `At +${st.g}% home load the upgrade order holds: the same ${cnt(story.n, `rankingByGrowth.g${st.g} rows`)} transformers, in the same order, unlocking the same members.`
        : `At +${st.g}% home load the upgrade list changes: ${cnt(story.n, `rankingByGrowth.g${st.g} rows`)} transformers${story.sameOrder ? ', same order' : ''}.`;
      const ch = story.changed.length;
      const dir = [story.up ? `${fmtNum(story.up)} fit more` : '', story.down ? `${fmtNum(story.down)} fit fewer` : ''].filter(Boolean).join(', ');
      note = `${ruleBinds ? 'The utility rule still binds. ' : ''}${ch ? `Only what feeder-aware control would fit moves, on ${cnt(ch, `rankingByGrowth.g${st.g} rows whose controlsFit differs from g0`)} row${ch === 1 ? '' : 's'} (${dir}), marked below.` : 'What feeder-aware control would fit does not move on any row.'}${story.approx ? ` ${fmtNum(story.approx)} feeder-aware count${story.approx === 1 ? ' is' : 's are'} interpolated between grid points.` : ''} Feeder-aware counts at +${st.g}% are the surrogate screen ${tagHTML('SCREENING', gSeries || 'not OpenDSS-checked')}`;
    }
    return `
      ${eyebrow}
      <div class="pb-headline pb-h20">${head}</div>
      ${note ? `<div class="pb-note">${note}</div>` : ''}
      <div class="pb-growth"><span class="pb-sub">Home load growth (EVs, heat pumps)</span>${tagHTML('ASSUMPTION', constOf('PLAN_GROWTH_PCTS', planner) ? constOf('PLAN_GROWTH_PCTS', planner).cite : 'planner growth levels')}<div class="pb-seg">${seg}</div></div>
      <div class="pb-uplist">${lines || '<div class="pb-body">No transformer is at capacity at this load.</div>'}</div>
      <div class="pb-foot">sim.planner rankingByGrowth · upgrade cost ${has(money.upgradeUSD) ? num(money.upgradeUSD, { money: true, digits: 0 }) : missingHTML()} per transformer · member value ${has(money.memberValueUSDYr) ? num(money.memberValueUSDYr, { money: true, digits: 0 }) : missingHTML()}/yr per battery is gross energy value, not Base's profit, and assumes perfect price foresight · unlocked = members over today's cap that one size up serves (typical growth; slow–fast) · feeder-aware control would fit = the cap if the utility counted our control (UNVERIFIED in Texas) · verdict = least worst regret over slow, typical and fast growth (planner.js decide)</div>`;
  }

  function q4HTML() {
    const eyebrow = `<div class="pb-row-b"><span class="pb-eyebrow">WHERE A BATTERY HELPS MOST</span>${tagHTML('SIM', 'sim.p2_build ranking (surrogate, calibrated vs OpenDSS)')}</div>`;
    if (!p2a) return `${eyebrow}${missingHTML(notBuilt(p2aR.err, 'p2/aware-core-d26-g0.json'))}`;
    const rm = rankingModel(p2a, topo);
    if (!rm.rows.length) return `${eyebrow}${missingHTML('no ranking exported for this combo')}`;
    return `
      ${eyebrow}
      <div class="pb-headline pb-h20">${rm.lead ? `The next battery goes to ${esc(rm.lead.home)} on ${esc(rm.lead.tfName)} (rank ${fmtNum(rm.lead.rank)}${rm.of ? ` of ${num(rm.of, { digits: 0 })}` : ''})${rm.lead.stress ? `: it removes ${num(rm.lead.stress, { digits: 2, unit: ' h', screening: true })} above nameplate` : ''}.` : ''}</div>
      <div class="pb-sub">Ranked by the transformer stress it removes, then energy value${month ? `, for ${esc(month)}` : ''} with feeder-aware charging${rm.of ? `, among ${num(rm.of, { digits: 0 })} transformers with a candidate home (one entry each)` : ''}.${rm.noNew ? (rm.noNew.all ? ` Each pick adds no new violation because of batteries ${tagHTML(rm.noNew.label, rm.noNew.cite, true)}` : ` ${fmtNum(rm.noNew.n)} of ${fmtNum(rm.noNew.of)} picks add no new violation because of batteries ${tagHTML(rm.noNew.label, rm.noNew.cite, true)}`) : ''}</div>
      <div class="pb-ranklist">${rm.rows.map((r) => `
        <div class="pb-rank${r.tf === st.sel ? ' on' : ''}" data-tf="${r.tf}">
          <span class="pb-rank-n">${r.rank}${rm.of ? `<small> of ${fmtNum(rm.of.v)}</small>` : ''}</span>
          <span class="pb-rank-h"><b>${esc(r.home)}</b> <span class="pb-sub">on ${esc(r.tfName)}</span></span>
          <span class="pb-rank-v">${has(r.value) ? num(r.value, { money: true, digits: 2 }) : missingHTML()}</span>
          <span></span>
          <span class="pb-sub">removes ${has(r.stress) ? num(r.stress, { digits: 2, unit: ' h', screening: true }) : '—'} over nameplate · month peak ${has(r.peak) ? num(r.peak, { digits: 1, unit: '%', screening: true }) : '—'} with it</span>
          <span class="pb-sub">energy value*</span>
        </div>`).join('')}</div>
      <div class="pb-foot">sim.p2_build ranking, ${esc(p2a.combo || 'aware-core-d26-g0')} · stress hours and peaks: surrogate screen, calibrated to OpenDSS, not OpenDSS-checked · *energy value per battery: REAL prices, assumes perfect price foresight; gross energy value, not Base's profit</div>`;
  }

  // ---------------- render + events ----------------
  function renderToggle() {
    const el = $('toggle');
    if (st.q === 1) el.innerHTML = `<div class="pb-seg pb-seg-ink">${[['naive', 'A · Naive split'], ['aware', 'B · Feeder-aware'], ['diff', 'What B adds']].map(([v, t]) => `<button type="button" class="pb-seg-b${st.view === v ? ' on' : ''}" data-view="${v}">${t}</button>`).join('')}</div>`;
    else el.innerHTML = '<span class="pb-chip-ours">Feeder-aware</span>';
  }
  function renderAside() {
    $('aside').innerHTML = st.q === 1 ? q1HTML() : st.q === 2 ? q2HTML() : st.q === 3 ? q3HTML() : q4HTML();
    if (st.q === 3) scheduleDecide();
  }
  function renderRail() { for (const b of root.querySelectorAll('.pb-q-btn')) b.classList.toggle('on', Number(b.dataset.q) === st.q); }
  function render() { renderRail(); renderToggle(); paintMap(); renderAside(); writeURL(); }

  // verdicts: planner.js paramsFor() + decide() + verdict() for the rows shown, after the first paint
  let decideTimer = null;
  function scheduleDecide() {
    if (!lib || typeof lib.decide !== 'function' || typeof lib.paramsFor !== 'function' || typeof lib.verdict !== 'function' || !planner) return;
    clearTimeout(decideTimer);
    // one decide() per tick (60-90 ms each on a loaded machine, docs/contracts-planner.md §3): the page stays live
    const step = () => {
      const g = st.g;
      const r = q3Rows(upgradeList(planner, g)).find((x) => !decideCache.has(`${g}:${x.tf}`));
      if (!r) return;
      const key = `${g}:${r.tf}`;
      try {
        const p = lib.paramsFor(planner, r.tf, r.k0 ?? 0, { growth: g });
        const d = lib.decide(p, p.deciles, planner.decision && planner.decision.seed);
        decideCache.set(key, { ...lib.verdict(p, d), d });
      } catch (e) { decideCache.set(key, { err: String((e && e.message) || e) }); }
      if (st.q === 3 && st.g === g) { const a = $('aside'), sc = a.scrollTop; a.innerHTML = q3HTML(); a.scrollTop = sc; }
      decideTimer = setTimeout(step, 0);
    };
    decideTimer = setTimeout(step, 0);
  }

  const pick = (tf) => { if (!Number.isInteger(tf) || tf < 0 || tf >= NT) return; st.sel = tf; if (!st.nSet) st.n = null; if (st.q === 1) st.q = 2; render(); };
  const onClick = (e) => {
    const qb = e.target.closest('.pb-q-btn'); if (qb) { st.q = Number(qb.dataset.q); render(); return; }
    const vb = e.target.closest('[data-view]'); if (vb) { st.view = vb.dataset.view; renderToggle(); paintMap(); return; }
    const gb = e.target.closest('[data-g]'); if (gb && !gb.disabled) { st.g = Number(gb.dataset.g); paintMap(); renderAside(); return; }
    const dot = e.target.closest('circle[data-tf]'); if (dot) { pick(Number(dot.dataset.tf)); return; }
    const row = e.target.closest('.pb-up[data-tf], .pb-rank[data-tf]'); if (row) { st.sel = Number(row.dataset.tf); paintMap(); renderAside(); writeURL(); }
  };
  const onInput = (e) => {
    if (e.target.matches('[data-pb="n"]')) {
      st.n = Math.max(0, Math.min(kMax ?? 0, Number(e.target.value) || 0)); st.nSet = true;
      const aside = $('aside'), sc = aside.scrollTop;
      aside.innerHTML = q2HTML(); aside.scrollTop = sc;
      const s = aside.querySelector('[data-pb="n"]'); if (s) s.focus();
      writeURL();
    }
  };
  const onChange = (e) => { if (e.target.matches('[data-pb="loc"]') && e.target.value !== '') { st.sel = Number(e.target.value); if (!st.nSet) st.n = null; paintMap(); renderAside(); writeURL(); } };
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
