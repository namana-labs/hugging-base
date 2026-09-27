// ui/story/run.js (UI-A): step 1b Running and step 2 Run (story-flow spec v2, screens 1b and 2b).
//
//   mountRunning(root, ctx)  1b: loads the scenario's files one by one and shows each (waiting, loading, loaded in
//                            N ms, failed) with the engine's MEASURED cost of that run from the catalogue
//                            (scenario.engine.buildSeconds / solves). No fake progress. When the files are in, it opens
//                            Run (replaceState, so Back returns to Configure) and asks Run to play from the start.
//   mount(root, ctx)         2b: the 3D scene (ui/lib/scene3d.js, 2D fallback) over five lanes on one shared axis
//                            (worst transformer, streets A-D + T-240, price REAL with the market-discharge blocks,
//                            fleet charge with the reserve line at the run's own RESERVE_FLOOR, fleet power) and an
//                            aside (worst-now hero, fleet battery, Right now with failures, the transformer bar, the
//                            battery grid). `covert` adds a Detector card and "Fictional attacker"; `worker_kill` shows
//                            the kill, the takeover and the lease strip from its `runtime` block.
// Story line: extras.moments (the engine's rule log). Failures: extras.failures. Without extras (not built yet) they
// fall back to meta.markers / meta.events / the runtime blocks and the counts series; no text is invented here.
// Transformer count, steps, start time, fleet size, tiers and the reserve are all read from the data.
import { TIER_RGB, STATE_RGB, buildSceneModel, frameFromP1 } from '../lib/scene-model.js';
import { stepToTime, timeToStep } from '../lib/format.js';
import { tagHTML, vsDefaultRows, vsDefaultHTML, vsDefaultText } from './shell.js';

export const SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4];
export const DEFAULT_SPEED = 0.25;         // 0.25x = 2.5 simulated minutes per second (story contract ruling 5)
export const MS_PER_STEP = 100;            // 1x = one step (a simulated minute) per 100 ms, as ui/panels/p1.js
export const MERGE_GAP = 5;                // network-limit intervals merge when the gap is 5 steps or less (contract)
export const LANE_WORST = [40, 210];       // display ranges of the lanes (story-flow spec 2b), not data
export const LANE_FOCUS = [0, 210];
export const AUTOPLAY_KEY = 'hb-story-autoplay';
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rgb = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const fmtN = (v, d = 0) => Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

// ------------------------------------------------------------------------------------------------ pure helpers
/** The covert scenario's detector file (catalogue `attack`; `covert` in the dev catalogue), or null. */
export function attackPath(scenario) {
  if (!scenario || !scenario.levers || scenario.levers.failure !== 'covert') return null;
  return scenario.attack || scenario.covert || 'p3/covert.json';
}

/** The files a scenario's Run page reads (paths under ui/data). */
export function runFiles(scenario) {
  const out = [
    { path: 'topology.json', what: 'the feeder: homes, transformers, lines', optional: false },
    { path: 'footprints.json', what: 'building footprints (OSM)', optional: true },
    { path: scenario.meta, what: 'the evening: prices, plan, tiers, constants', optional: false },
    { path: scenario.branch, what: 'the run: loading, tiers, batteries, every minute', optional: false },
  ];
  if (scenario.extras) out.push({ path: scenario.extras, what: 'the rule log, failures, feeder readouts', optional: true });
  if (attackPath(scenario)) out.push({ path: attackPath(scenario), what: 'the detector run (fictional attacker)', optional: false });
  return out;
}

export function tfName(topology, tf) {
  const f = (topology.focus || []).find((x) => x.tf === tf);
  if (f) return `Street ${f.key}`;
  return `T-${tf}`;
}

/** Tier names from the run's own thresholds (meta.tiers). */
export function tierNames(tiers = {}) {
  return ['within nameplate', `over nameplate (${tiers.amber ?? 100}%)`, `above ${tiers.normal ?? 110}%, counting`,
    `normal rating exceeded (${tiers.normalMinutes ?? 30}+ min)`, `emergency (above ${tiers.emergency ?? 150}%)`, 'protection open'];
}

/** Per-step series for the lanes and cards. Worst transformer from extras (worstPct/worstTf, tenths) or from loading. */
export function buildSeries(doc, meta, topology, extras = null) {
  const n = doc.loading.length;
  const worst = new Float64Array(n), wtf = new Int32Array(n), soc = new Float64Array(n), kw = new Float64Array(n);
  // extras' worst series when exported for this run (never a series its `absent` list names)
  const absent = new Set((extras && Array.isArray(extras.absent) && extras.absent) || []);
  const useX = extras && !absent.has('worstPct') && !absent.has('worstTf') && Array.isArray(extras.worstPct) && extras.worstPct.length === n
    && Array.isArray(extras.worstTf) && extras.worstTf.length === n;
  for (let k = 0; k < n; k++) {
    if (useX) { worst[k] = extras.worstPct[k] / 10; wtf[k] = extras.worstTf[k]; } else {
      const row = doc.loading[k];
      let w = 0;
      for (let i = 1; i < row.length; i++) if (row[i] > row[w]) w = i;
      worst[k] = row[w] / 10; wtf[k] = w;
    }
    const s = doc.soc[k] || [];
    let a = 0;
    for (const x of s) a += x;
    soc[k] = s.length ? a / s.length / 10 : 0;
    let p = 0;
    for (const x of doc.batKW[k] || []) p += x;
    kw[k] = p / 10;
  }
  const focus = [...(topology.focus || []).map((f) => ({ key: f.key, name: f.key, tf: f.tf })),
    ...(topology.bridge || []).map((b) => ({ key: String(b.tf), name: `T-${b.tf}`, tf: b.tf }))]
    .map((f) => ({ ...f, pct: Float64Array.from(doc.loading, (row) => row[f.tf] / 10) }));
  const price = Array.isArray(meta.price) && meta.price.length >= n ? meta.price.slice(0, n) : null;
  return { n, worst, wtf, soc, kw, focus, price, counts: doc.counts, fleetN: (doc.soc[0] || []).length, tfN: (doc.loading[0] || []).length };
}

/** [[a, b], ...] runs of steps where fn(k) holds, merged when the gap is `gap` steps or less. */
export function ranges(n, fn, gap = MERGE_GAP) {
  const r = [];
  let st = -1, last = -1e9;
  for (let k = 0; k < n; k++) {
    if (!fn(k)) continue;
    if (st < 0) st = k;
    else if (k - last > gap) { r.push([st, last]); st = k; }
    last = k;
  }
  if (st >= 0) r.push([st, last]);
  return r;
}

/** Display words for the failure kinds of extras.failures (engine codes) and of the fallback list. */
export const KIND = { comms_lost: 'Battery silent', hot: 'Load spike', stall: 'Controller stalled', stale: 'Batteries stale',
  normal: 'Normal rating exceeded', emergency: 'Emergency rating', protection: 'Protection open', worker_kill: 'Worker killed',
  takeover: 'Lease taken over', late: 'Late commands refused', covert: 'Hidden carrier' };
export const kindWord = (kind) => KIND[kind] || String(kind || '').replace(/_/g, ' ');
/** Failures without extras: meta.events of this branch, the runtime block (worker_kill), the covert attack, the
 *  network-limit intervals of the counts series (codes 3/4/5) and stale/expired batteries (state S/X). */
export function fallbackFailures({ meta, doc, series, topology, branch, covert = null }) {
  const n = series.n, out = [];
  const home = (h) => (topology.homes[h] ? topology.homes[h].label : `Home ${h}`);
  for (const e of (meta.events && meta.events[branch]) || []) {
    const k1 = e.kind === 'comms_lost' ? (e.coveredStep ?? e.expiredStep ?? e.step) : e.kind === 'stall' ? (e.resumeStep ?? e.step) : e.kind === 'hot' && e.minutes ? e.step + e.minutes : e.step;
    const where = e.kind === 'comms_lost' ? home(e.home) : e.tf !== undefined ? tfName(topology, e.tf) : e.kind === 'stall' ? 'our controller' : '';
    out.push({ kind: e.kind, where, k0: e.step, k1: Math.min(n - 1, k1), text: e.text || '', label: 'ASSUMPTION' });
  }
  const rt = doc.runtime;
  if (rt) {
    const tk = (rt.takeover || [])[0];
    if (rt.kill) out.push({ kind: 'worker_kill', where: `${rt.kill.worker} · ${(rt.kill.groups || []).join(', ')}`, k0: rt.kill.step, k1: tk ? tk.step : rt.kill.step, text: rt.kill.text || '', label: 'SIM' });
  }
  out.push(...covertFailures(covert, n));
  const c = series.counts;
  for (const [a, b] of ranges(n, (k) => c[k][4] > 0)) out.push({ kind: 'protection', where: tfName(topology, series.wtf[a]), k0: a, k1: b, text: 'The fuse rule opens a transformer; homes without a battery behind it go dark.', label: 'SIM' });
  for (const [a, b] of ranges(n, (k) => c[k][3] > 0)) out.push({ kind: 'emergency', where: tfName(topology, series.wtf[a]), k0: a, k1: b, text: `A transformer is above ${meta.tiers ? meta.tiers.emergency : 150}% of nameplate.`, label: 'SIM' });
  for (const [a, b] of ranges(n, (k) => c[k][2] > 0)) out.push({ kind: 'normal', where: tfName(topology, series.wtf[a]), k0: a, k1: b, text: `Above ${meta.tiers ? meta.tiers.normal : 110}% for ${meta.tiers ? meta.tiers.normalMinutes : 30} minutes or more.`, label: 'SIM' });
  if (series.fleetN) for (const [a, b] of ranges(n, (k) => /[SX]/.test(doc.state[k] || ''), 2)) out.push({ kind: 'stale', where: 'fleet', k0: a, k1: b, text: 'A battery stopped reporting, or its last command expired.', label: 'SIM' });
  out.sort((x, y) => x.k0 - y.k0 || x.k1 - y.k1);
  return out;
}

/** The covert attack as a failure interval: the channel opens at attack.step and runs until the last quarantine. */
export function covertFailures(covert, n) {
  if (!covert || !covert.attack) return [];
  const q = (covert.quarantine && covert.quarantine.log) || [];
  const end = q.length ? Math.max(...q.map((x) => x[0])) : n - 1;
  return [{ kind: 'covert', where: `${(covert.attack.shard || []).length} batteries (fictional attacker)`, k0: covert.attack.step, k1: Math.min(n - 1, end), text: covert.attack.text || '', label: 'ASSUMPTION' }];
}
export const DET_WORDS = { off: 'channel not open yet', on: 'carrying the hidden signal, not flagged yet', flag: 'flagged by the detector', held: 'quarantined: held at zero' };
/** The Detector card's model from p3/covert.json: the shard's units, flagged and quarantined counts per step, and two
 *  step paths over the attack window (a 300 x 44 box). Counts come from units[].flaggedStep and quarantine.log. */
export function detectorModel(covert, n) {
  const a = covert.attack || {};
  const byBatt = new Map((covert.units || []).map((u) => [u.batt, u]));
  const units = (a.shard || []).map((b) => {
    const u = byBatt.get(b) || {};
    return { batt: b, home: u.home ?? null, flaggedStep: u.flaggedStep ?? null, quarantinedStep: u.quarantinedStep ?? null };
  });
  const qlog = ((covert.quarantine && covert.quarantine.log) || []).map((q) => q[0]);
  const flagSteps = units.map((u) => u.flaggedStep).filter((x) => x !== null);
  const last = Math.max(a.step ?? 0, ...flagSteps, ...qlog);
  const w0 = Math.max(0, (a.step ?? 0) - 10), w1 = Math.min(n - 1, last + 20);
  const flaggedAt = (k) => flagSteps.filter((s) => s <= k).length;
  const quarantinedAt = (k) => qlog.filter((s) => s <= k).length;
  const tot = Math.max(1, units.length);
  const X = (k) => ((k - w0) / Math.max(1, w1 - w0) * 300);
  const Y = (c) => (42 - c / tot * 40);
  const path = (fn) => {
    let d = `M0,${Y(fn(w0)).toFixed(1)}`, prev = fn(w0);
    for (let k = w0 + 1; k <= w1; k++) { const c = fn(k); if (c !== prev) { d += `H${X(k).toFixed(1)}V${Y(c).toFixed(1)}`; prev = c; } }
    return `${d}H300`;
  };
  const series = covert.series && covert.series.units;
  return { units, w0, w1, flaggedAt, quarantinedAt, flagPath: path(flaggedAt), heldPath: path(quarantinedAt),
    x: (k) => (k < w0 || k > w1 ? null : X(k).toFixed(1)), label: (series && series.label) || 'SIM' };
}
/** The covert attack in the story line: its own text at attack.step. */
export function covertMoments(covert) {
  if (!covert || !covert.attack) return [];
  return [{ k: covert.attack.step, t: covert.attack.t, text: covert.attack.text, label: 'ASSUMPTION', rule: 'covert channel opens' }];
}

/** Story moments without extras: meta.markers (their own text; another branch's fault markers dropped), this branch's
 *  events, the runtime lines (worker_kill) and the covert attack. */
export function fallbackMoments({ meta, doc, branch, covert = null }) {
  const out = [];
  const other = new Set();
  for (const [b, list] of Object.entries(meta.events || {})) if (b !== branch) for (const e of list) other.add(e.text);
  const mine = new Set(((meta.events && meta.events[branch]) || []).map((e) => e.text));
  for (const m of meta.markers || []) {
    if (other.has(m.text) && !mine.has(m.text)) continue;
    const k = timeToStep(meta, m.t);
    if (k !== null) out.push({ k, t: m.t, text: m.text, label: m.label, rule: 'marker' });
  }
  for (const e of (meta.events && meta.events[branch]) || []) if (!out.some((m) => m.text === e.text)) out.push({ k: e.step, t: e.t, text: e.text, label: 'ASSUMPTION', rule: `fault · ${e.kind}` });
  const rt = doc.runtime;
  if (rt) {
    if (rt.kill) out.push({ k: rt.kill.step, t: rt.kill.t, text: rt.kill.text, label: 'SIM', rule: 'worker killed' });
    for (const t of rt.takeover || []) out.push({ k: t.step, t: t.t, text: t.text, label: 'SIM', rule: 'takeover' });
    if (rt.late) out.push({ k: rt.late.step, t: rt.late.t, text: rt.late.text, label: 'SIM', rule: 'late batch' });
  }
  out.push(...covertMoments(covert));
  out.sort((a, b) => a.k - b.k);
  return out;
}

/** The last item with k <= now, or null. */
export function momentAt(list, k) { let cur = null; for (const m of list) if (m.k <= k) cur = m; else break; return cur; }

/** SVG path of a series on the 1000 x 100 lane box. */
export function lanePath(vals, lo, hi) {
  const n = vals.length, d = [];
  for (let k = 0; k < n; k++) {
    const x = (k / Math.max(1, n - 1) * 1000).toFixed(1);
    const y = clamp(100 - (vals[k] - lo) / (hi - lo) * 100, -2, 102).toFixed(1);
    d.push(`${k ? 'L' : 'M'}${x},${y}`);
  }
  return d.join('');
}
export function laneArea(vals, lo, hi, base = lo) {
  const n = vals.length;
  const yb = clamp(100 - (base - lo) / (hi - lo) * 100, -2, 102).toFixed(1);
  return `M0,${yb}${lanePath(vals, lo, hi).replace(/^M/, 'L')}L1000,${yb}Z`;
}
const yOf = (v, lo, hi) => clamp(100 - (v - lo) / (hi - lo) * 100, -2, 102).toFixed(2);

/** The engine's measured cost of a run, from the catalogue (scenario.engine, and attackEngine for covert). */
export function runCostHTML(sc, num) {
  const e = sc.engine || {}, a = sc.attackEngine || null;
  // `producer` made the run itself (worker_kill: mpalacios.runtime), or, with an attackEngine, only the attack replay
  const by = sc.producer && !a ? ` (${esc(sc.producer)})` : '';
  const aby = sc.producer && a ? ` (${esc(sc.producer)})` : '';
  const parts = [e.solves ? `${num(e.solves)} OpenDSS power flows` : '', e.buildSeconds ? `built in ${num(e.buildSeconds, { unit: ' s' })}` : ''].filter(Boolean);
  let html = parts.length ? `The engine already ran this evening${by}: ${parts.join(', ')}.`
    : 'The catalogue has no measured engine cost for this run.';
  if (a && a.buildSeconds) html += ` The detector replay${aby} took ${num(a.buildSeconds, { unit: ' s' })} to build.`;
  return `${html} This page replays that output; nothing is solved in the browser.`;
}

// ------------------------------------------------------------------------------------------------ 1b Running
export async function mountRunning(root, ctx) {
  const sc = ctx.scenario;
  const files = runFiles(sc);
  let disposed = false, timer = 0;
  const e = sc.engine || {};
  root.innerHTML = `<div class="rn"><div class="rn-spin" aria-hidden="true"></div>
    <div class="rn-head"><div class="rn-title">Loading the engine's run</div><div class="rn-stage">Fetching ${files.length} files for ${esc(sc.title || sc.id)}</div></div>
    <div class="rn-files">${files.map((f, i) => `<div class="rn-file" data-i="${i}"><i class="st"></i><span class="p" title="${esc(f.what)}">${esc(f.path)}</span><span class="w">waiting</span></div>`).join('')}</div>
    <div class="rn-cost"></div></div>`;
  const $ = (s) => root.querySelector(s);
  $('.rn-cost').innerHTML = runCostHTML(sc, ctx.num);
  const setRow = (i, cls, text) => { const r = root.querySelector(`.rn-file[data-i="${i}"]`); if (!r) return; r.className = `rn-file ${cls}`; r.querySelector('.w').textContent = text; };
  const started = performance.now();
  const results = await Promise.all(files.map(async (f, i) => {
    const t0 = performance.now();
    setRow(i, 'loading', 'loading');
    try {
      const doc = await ctx.getAny(f.path);
      if (!disposed) setRow(i, 'ok', `loaded in ${fmtN(performance.now() - t0)} ms`);
      return { ok: true, doc };
    } catch (err) {
      if (!disposed) setRow(i, f.optional ? 'ok' : 'bad', f.optional ? 'not built (optional)' : `failed: ${err && err.message ? err.message : err}`);
      return { ok: false, optional: f.optional, err };
    }
  }));
  if (disposed) return { dispose() {} };
  const failed = results.findIndex((r) => !r.ok && !r.optional);
  const rn = $('.rn');
  if (failed >= 0) {
    rn.classList.add('failed');
    $('.rn-title').textContent = 'The run didn’t open';
    $('.rn-stage').textContent = `${files[failed].path}: ${results[failed].err && results[failed].err.message ? results[failed].err.message : 'failed'}`;
    rn.insertAdjacentHTML('beforeend', `<a class="st-btn-ghost rn-back" href="${esc(ctx.link({ page: 'configure' }))}">← Back to Configure</a>`);
    rn.querySelector('.rn-back').addEventListener('click', (ev) => { ev.preventDefault(); ctx.nav('configure', {}); });
    return { dispose() { disposed = true; } };
  }
  const meta = results[2].doc;
  rn.classList.add('done');
  $('.rn-title').textContent = 'Done';
  $('.rn-stage').textContent = `Opening the run: ${meta.start} → ${stepToTime(meta, meta.steps)}, ${fmtN(meta.steps)} steps, files in ${fmtN(performance.now() - started)} ms`;
  try { sessionStorage.setItem(AUTOPLAY_KEY, sc.id); } catch (err) { /* private mode: Run opens paused */ }
  timer = setTimeout(() => { if (!disposed) ctx.nav('run', { s: sc.id, k: null }, { replace: true }); }, 500);
  return { dispose() { disposed = true; clearTimeout(timer); } };
}

// ------------------------------------------------------------------------------------------------ 2b Run
async function makeScene(el, topology, nowebgl, onError) {
  const opts = { topology, theme: 'light', onError };
  if (!nowebgl) {
    try {
      const m = await import('../lib/scene3d.js');
      const s = m.createScene(el, opts);
      document.body.dataset.webgl = 'ok';
      return s;
    } catch (e) {
      console.warn('[hb story] WebGL scene unavailable, using the 2D fallback:', e && e.message);
      el.innerHTML = '';
    }
  }
  const f = await import('../lib/fallback2d.js');
  const s = f.createScene(el, opts);
  document.body.dataset.webgl = 'fallback';
  return s;
}
const n0 = (doc) => (doc.loading || []).length;
const LABEL_OK = (l) => ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION', 'UNVERIFIED', 'SCREENING'].includes(l);
const withTimeout = (p, ms, what) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`${what} timed out after ${ms} ms`)), ms))]);

const STATE_CSS = { C: '#1e4d2b', D: '#c7962b', I: '#e3dfd3', S: '#8f8b7f', X: '#8f8b7f', B: '#8fcf9f' };

export async function mount(root, ctx) {
  const sc = ctx.scenario;
  const lev = sc.levers || {};
  const covertOn = lev.failure === 'covert';
  let runtimeOn = false;
  root.innerHTML = '<div class="rv"><div class="rv-loading">Loading the run…</div></div>';
  const [topology, footprints, meta, doc, extras, covert] = await Promise.all([
    ctx.getJSON('topology.json'), ctx.getJSON('footprints.json').catch(() => null), ctx.getAny(sc.meta), ctx.getAny(sc.branch),
    sc.extras ? ctx.getAny(sc.extras).catch(() => null) : Promise.resolve(null),
    covertOn ? ctx.getAny(attackPath(sc)) : Promise.resolve(null),
  ]);
  const branch = doc.branch || (lev.failure === 'faults' ? 'aware_faults' : lev.policy);
  const rt = doc.runtime && Array.isArray(doc.runtime.holder) && Array.isArray(doc.runtime.partitions) ? doc.runtime : null;
  runtimeOn = !!rt;
  const rtLab = (key) => (doc.series && doc.series[key] && doc.series[key].label) || 'SIM';
  const noFleet = lev.policy === 'none';
  const S = buildSeries(doc, meta, topology, extras);
  const n = S.n;
  const tiers = meta.tiers || {};
  const TN = tierNames(tiers);
  const reserveC = meta.constants && meta.constants.RESERVE_FLOOR;
  const reservePct = reserveC ? reserveC.value * 100 : null;
  const summary = (meta.summary && meta.summary[branch]) || sc.summary || {};
  // a variant run may place its batteries on other homes (meta.fleet / doc.fleet: home indices)
  const fleetHomes = (Array.isArray(meta.fleet) && meta.fleet) || (Array.isArray(doc.fleet) && doc.fleet) || null;
  let topoRun = topology;
  let hideBatteries = noFleet;
  if (fleetHomes && fleetHomes.length === S.fleetN) topoRun = { ...topology, fleet: fleetHomes };
  else if (S.fleetN !== (topology.fleet || []).length) hideBatteries = true;
  // the engine's rule log and failure list (extras); the covert attack lives in its own file (p3/covert.json), so its
  // line and interval are added here from that file's own text and steps
  const moments = extras && Array.isArray(extras.moments)
    ? [...extras.moments, ...covertMoments(covert)].sort((a, b) => a.k - b.k) : fallbackMoments({ meta, doc, branch, covert });
  const failures = extras && Array.isArray(extras.failures)
    ? [...extras.failures, ...covertFailures(covert, n0(doc))].sort((a, b) => a.k0 - b.k0 || a.k1 - b.k1)
    : fallbackFailures({ meta, doc, series: S, topology, branch, covert });
  const worstMax = Math.max(...S.worst);
  const priceMax = S.price ? Math.max(...S.price) : 0;
  const priceHi = Math.max(600, Math.ceil(priceMax / 100) * 100);
  const kwMax = Math.max(...Array.from(S.kw, Math.abs));
  const kwHi = Math.max(2000, Math.ceil(kwMax / 1000) * 1000);
  const uid = Math.random().toString(36).slice(2, 8);
  const vsRows = vsDefaultRows(ctx.catalogue || {}, sc);
  // data-truth audit #5: the fleet sits where it stresses these streets on purpose (topology meta.shaping; a variant's
  // own placement rule is the catalogue's FLEET_PLACEMENT)
  const shaping = topology.meta && topology.meta.shaping;
  const placeC = ctx.catalogue && ctx.catalogue.constants && ctx.catalogue.constants.FLEET_PLACEMENT;
  const placementNote = noFleet || !shaping ? '' : `<span class="note">fleet placed to stress these streets${tagHTML(shaping.label || 'ASSUMPTION',
    [shaping.description, fleetHomes && placeC ? `This run: ${placeC.value}` : ''].filter(Boolean).join(' '))}</span>`;
  const loadLab = (doc.series && doc.series.loading && doc.series.loading.label) || 'SIM';
  const socLab = (doc.series && doc.series.soc && doc.series.soc.label) || 'SIM';
  const priceLab = (meta.series && meta.series.price && meta.series.price.label) || 'REAL';
  const bands = ((meta.plan && meta.plan.discharge) || []).map(([t, mins]) => {
    const k0 = timeToStep(meta, t);
    return k0 === null ? '' : `<rect x="${(k0 / (n - 1) * 1000).toFixed(1)}" y="0" width="${(mins / (n - 1) * 1000).toFixed(1)}" height="100" fill="#e9dfbb"></rect>`;
  }).join('');
  const hrs = [];
  for (let k = 0; k < n; k += Math.round(120 * 60 / (meta.stepSeconds || 60))) hrs.push(stepToTime(meta, k));
  hrs.push(stepToTime(meta, n));
  const clipRect = `<clipPath id="rvc-${uid}"><rect class="rv-clip" x="0" y="-10" width="0" height="120"></rect></clipPath>`;
  const lane = (inner, refs = '') => `<div class="rv-plot"><svg viewBox="0 0 1000 100" preserveAspectRatio="none"><rect width="1000" height="100" fill="#f6f3ea"></rect>${refs}<defs>${clipRect.replace(`rvc-${uid}`, `rvc-${uid}-${inner.id}`)}</defs><g clip-path="url(#rvc-${uid}-${inner.id})">${inner.html}</g></svg></div>`;
  const dash = (v, lo, hi, col, da = '4 3') => `<line x1="0" x2="1000" y1="${yOf(v, lo, hi)}" y2="${yOf(v, lo, hi)}" stroke="${col}" stroke-dasharray="${da}" vector-effect="non-scaling-stroke"></line>`;
  const kwPos = Array.from(S.kw, (v) => Math.max(0, v)), kwNeg = Array.from(S.kw, (v) => Math.min(0, v));
  const legend = [[TIER_RGB[0], 'within nameplate'], [TIER_RGB[1], `over nameplate (${tiers.amber ?? ''}%)`], [TIER_RGB[3], `above ${tiers.normal ?? ''}%`],
    [TIER_RGB[4], `emergency (${tiers.emergency ?? ''}%)`], [TIER_RGB[5], 'protection open'], ...(hideBatteries ? [] : [[STATE_RGB.C, 'battery charging']])];

  root.innerHTML = `<div class="rv">
    <div class="rv-left">
      <div class="rv-scene"><div class="rv-scene-el"></div><div class="rv-loading">Loading the feeder…</div>
        <div class="rv-over"><div class="rv-story" hidden><b></b><span></span></div><div class="rv-banner" hidden><span class="bang">!</span><span class="t"></span></div>
          ${covertOn ? `<div class="rv-fict" title="${esc((covert.sources && covert.sources.adversary && covert.sources.adversary.text) || '')}">Fictional attacker</div>` : ''}</div>
        <div class="rv-cams" role="radiogroup" aria-label="Camera">${[['feeder', 'Whole feeder'], ['street', 'Street A–D'], ['t240', 'T-240']].map(([id, t]) => `<button type="button" data-cam="${id}" class="${id === 'feeder' ? 'on' : ''}">${t}</button>`).join('')}</div>
        <div class="rv-legend">${legend.map(([c, t]) => `<span><i style="background:${rgb(c)}"></i>${esc(t)}</span>`).join('')}${tagHTML(loadLab, 'OpenDSS loading, as % of nameplate kVA as shipped; tiers from the engine (never re-derived here)')}</div>
      </div>
      <div class="rv-lanes">
        <div class="rv-trans"><button type="button" class="rv-play" aria-label="Play">▶</button><span class="st-clock">${stepToTime(meta, 0)}</span>
          <button type="button" class="st-btn-ghost rv-replay" title="Replay from ${esc(meta.start)}">↺ Replay</button>
          <span class="rv-stepno">Step 1 of ${fmtN(n)}</span>
          ${vsRows.length ? `<span class="rv-vs" title="${esc(`Versus ${vsRows[0].refTitle}: ${vsDefaultText(vsRows)}`)}"><b>vs the default run</b>${vsDefaultHTML(vsRows, { max: 2 })}</span>` : ''}
          <div class="rv-speed" role="radiogroup" aria-label="Speed">${SPEEDS.map((s) => `<button type="button" data-speed="${s}">${s}×</button>`).join('')}</div></div>
        <div class="rv-grid">
          <div class="rv-lab"><span class="n">Worst transformer</span><span class="v" data-v="worst"></span></div>
          ${lane({ id: 'w', html: `<path d="${lanePath(S.worst, ...LANE_WORST)}" fill="none" stroke="#10231a" stroke-width="1.4" vector-effect="non-scaling-stroke"></path>` },
            (tiers.normal ? dash(tiers.normal, ...LANE_WORST, '#c7962b') : '') + (tiers.emergency ? dash(tiers.emergency, ...LANE_WORST, '#b23a2f') : ''))}
          <div class="rv-lab"><span class="n">Street A–D, T-240</span><span class="v" data-v="focus"></span>${placementNote}</div>
          ${lane({ id: 'f', html: S.focus.map((f) => `<path d="${lanePath(f.pct, ...LANE_FOCUS)}" fill="none" stroke="#10231a" stroke-opacity="${f.key.length > 1 ? 0.9 : 0.55}" stroke-width="1.1" ${f.key.length > 1 ? 'stroke-dasharray="4 3"' : ''} vector-effect="non-scaling-stroke"></path>`).join('') },
            tiers.amber ? dash(tiers.amber, ...LANE_FOCUS, '#c7962b') : '')}
          <div class="rv-lab"><span class="n">Price $/MWh</span><span class="v" data-v="price"></span></div>
          ${lane({ id: 'p', html: S.price ? `<path d="${lanePath(S.price, 0, priceHi)}" fill="none" stroke="#10231a" stroke-width="1.4" vector-effect="non-scaling-stroke"></path>` : '' }, bands)}
          <div class="rv-lab"><span class="n">Fleet charge %</span><span class="v" data-v="soc"></span></div>
          ${lane({ id: 's', html: noFleet ? '' : `<path d="${laneArea(S.soc, 0, 100)}" fill="#1e4d2b" fill-opacity=".14"></path><path d="${lanePath(S.soc, 0, 100)}" fill="none" stroke="#1e4d2b" stroke-width="2.2" vector-effect="non-scaling-stroke"></path>` },
            reservePct !== null ? dash(reservePct, 0, 100, '#1e4d2b', '2 3') : '')}
          <div class="rv-lab"><span class="n">Fleet power MW</span><span class="v" data-v="kw"></span></div>
          ${lane({ id: 'k', html: noFleet ? '' : `<path d="${laneArea(kwPos, -kwHi, kwHi, 0)}" fill="#1e4d2b" fill-opacity=".5"></path><path d="${laneArea(kwNeg, -kwHi, kwHi, 0)}" fill="#10231a" fill-opacity=".22"></path>` },
            `<line x1="0" x2="1000" y1="50" y2="50" stroke="#10231a" stroke-opacity=".25" vector-effect="non-scaling-stroke"></line>`)}
          <div></div><div class="rv-axis">${hrs.map((h) => `<span>${h}</span>`).join('')}</div>
          <div class="rv-scrub" role="slider" aria-label="Scrub the evening" aria-valuemin="0" aria-valuemax="${n - 1}" tabindex="0">
            ${failures.map((f, i) => `<div class="rv-band" data-f="${i}" style="left:${(f.k0 / (n - 1) * 100).toFixed(3)}%;width:${Math.max(0.25, (f.k1 - f.k0 + 1) / (n - 1) * 100).toFixed(3)}%"></div>`).join('')}
            <div class="rv-cursor"></div></div>
        </div>
      </div>
    </div>
    <aside class="rv-aside">
      <div class="rv-card rv-hero"><div class="h"><span class="st-eyebrow">WORST TRANSFORMER NOW</span>${tagHTML(loadLab, 'OpenDSS loading as % of nameplate kVA as shipped')}</div>
        <div class="big" data-v="hero"></div><div class="who"><i></i><b></b><span class="tn"></span></div><div class="cnt"></div></div>
      ${covertOn ? '<div class="rv-card rv-det"></div>' : ''}
      ${runtimeOn ? '<div class="rv-card rv-ctl"></div>' : ''}
      <div class="rv-card rv-bat"><div class="h"><span class="t">Fleet charge</span><span class="m">${noFleet ? 'no batteries in this run' : `${fmtN(S.fleetN)} batteries`}</span><span class="flow"></span></div>
        <div class="rv-cell"><div class="rv-body"><div class="rv-track"><div class="rv-fill"></div><div class="rv-stripes"></div>${reservePct !== null ? `<div class="rv-reserve" style="left:${reservePct}%"></div>` : ''}<span class="rv-pct"></span></div></div><div class="rv-term"></div></div>
        <div class="rv-resnote">${reservePct !== null ? `<span style="left:calc(${reservePct}% - 4px)">↑ ${fmtN(reservePct)}% member reserve${summary.reserveBreaches ? (summary.reserveBreaches.v === 0 ? ', never used' : `, crossed ${fmtN(summary.reserveBreaches.v)} battery-minutes`) : ''} ${tagHTML(reserveC.label, reserveC.cite)}</span>` : ''}</div></div>
      <div class="rv-card rv-now"></div>
    </aside></div>`;
  const $ = (s) => root.querySelector(s);
  const clips = [...root.querySelectorAll('.rv-clip')];
  const cursor = $('.rv-cursor');
  const bandEls = [...root.querySelectorAll('.rv-band')];

  // ---- state
  let k = clamp(ctx.k || 0, 0, n - 1);
  let speed = SPEEDS.includes(ctx.params.speed) ? ctx.params.speed : DEFAULT_SPEED;
  let playing = false, raf = 0, last = 0, acc = 0, disposed = false, scene = null, drawn = -1, sceneK = -1;
  let autoplay = false;
  try { if (sessionStorage.getItem(AUTOPLAY_KEY) === sc.id) { autoplay = true; sessionStorage.removeItem(AUTOPLAY_KEY); } } catch (e) { /* ignore */ }
  if (autoplay) k = 0;

  function setSpeed(s) {
    speed = s;
    for (const b of root.querySelectorAll('.rv-speed button')) b.classList.toggle('on', Number(b.dataset.speed) === s);
    history.replaceState(history.state, '', ctx.link({ speed: s === DEFAULT_SPEED ? null : s, k: k || null }));
  }
  const span = (f) => `${stepToTime(meta, f.k0)}–${stepToTime(meta, f.k1)}`;

  function drawNow() {
    const c = S.counts[k] || [0, 0, 0, 0, 0];
    const tot = S.tfN;
    const within = tot - (c[0] + c[1] + c[2] + c[3] + c[4]);
    const nowF = failures.filter((f) => f.k0 <= k && k <= f.k1);
    const st = noFleet ? '' : (doc.state[k] || '');
    const cnt = { C: 0, D: 0, I: 0, F: 0 };
    const cells = Array.from(st).map((ch) => {
      const bad = ch === 'S' || ch === 'X';
      if (bad) cnt.F += 1; else if (ch in cnt) cnt[ch] += 1;
      return `<i class="${bad ? 'bad' : ''}" style="background:${STATE_CSS[ch] || '#e3dfd3'}"></i>`;
    }).join('');
    const tierRows = [['over nameplate', c[0], TIER_RGB[1], false], [`above ${tiers.normal ?? ''}%`, c[1] + c[2], TIER_RGB[3], c[2] > 0],
      ['emergency', c[3], TIER_RGB[4], c[3] > 0], ['open', c[4], TIER_RGB[5], c[4] > 0]];
    const bar = [[within, TIER_RGB[0]], ...tierRows.map((r) => [r[1], r[2]])].filter((r) => r[0] > 0)
      .map(([v, col]) => `<div style="width:${(v / tot * 100).toFixed(2)}%;background:${rgb(col)}"></div>`).join('');
    const el = $('.rv-now');
    el.classList.toggle('failing', nowF.length > 0);
    el.innerHTML = `<div class="h"><span class="st-eyebrow">RIGHT NOW · ${stepToTime(meta, k)}</span>${tagHTML('SIM', 'the engine\'s run at this minute')}</div>
      ${nowF.length ? `<div class="rv-failing"><div class="e">FAILING NOW · ${nowF.length}</div>${nowF.map((f) => `<button type="button" class="rv-fnow" data-seek="${f.k0}"><span class="a"><b>${esc(kindWord(f.kind))}${f.where ? ` · ${esc(f.where)}` : ''}</b><span>${span(f)}</span></span><span class="b">${esc(f.text)}${LABEL_OK(f.label) ? tagHTML(f.label, f.label === 'ASSUMPTION' ? 'a scripted failure: what fails and when are assumptions' : 'from this run') : ''}</span></button>`).join('')}</div>`
        : '<div class="rv-ok"><i></i>No failures right now</div>'}
      <div class="rv-sec"><div class="r"><b>${fmtN(tot)} transformers</b><span>${fmtN(within)} within nameplate</span></div><div class="rv-tbar">${bar}</div>
        <div class="rv-tiers">${tierRows.map(([nm, v, col, bad]) => `<span class="${bad ? 'bad' : v ? '' : 'zero'}"><i style="background:${rgb(col)}"></i>${esc(nm)} ${fmtN(v)}</span>`).join('')}</div></div>
      ${noFleet ? '' : `<div class="rv-sec"><div class="r"><b>${fmtN(S.fleetN)} batteries</b><span>charging ${cnt.C} · discharging ${cnt.D} · idle ${cnt.I}${cnt.F ? ` · failing ${cnt.F}` : ''}</span></div><div class="rv-cells">${cells}</div></div>`}
      <div class="rv-all"><div class="e">FAILURES THIS EVENING<span>${failures.length}</span></div>${failures.length ? failures.map((f) => {
        const act = f.k0 <= k && k <= f.k1, past = f.k1 < k;
        return `<button type="button" class="rv-frow${act ? ' act' : past ? ' past' : ''}" data-seek="${f.k0}" title="${esc(f.text)}"><i></i><span class="s">${span(f)}</span><span class="w">${esc(kindWord(f.kind))}${f.where ? ` · ${esc(f.where)}` : ''}</span></button>`;
      }).join('') : '<div class="rv-ok">None in this run.</div>'}</div>`;
    const banner = $('.rv-banner');
    banner.hidden = nowF.length === 0;
    banner.querySelector('.t').textContent = nowF.map((f) => `${kindWord(f.kind)}${f.where ? ` · ${f.where}` : ''}`).join('  ·  ');
    for (const b of bandEls) { const f = failures[Number(b.dataset.f)]; b.style.opacity = f.k1 < k || (f.k0 <= k && k <= f.k1) ? '1' : '.45'; }
  }

  const det = covertOn ? detectorModel(covert, n) : null;
  function drawDetector() {
    if (!det) return;
    const a = covert.attack || {}, sm = covert.summary || {};
    const flagged = det.flaggedAt(k), quarantined = det.quarantinedAt(k);
    const cells = det.units.map((u) => {
      const st = k < a.step ? 'off' : u.quarantinedStep !== null && u.quarantinedStep <= k ? 'held' : u.flaggedStep !== null && u.flaggedStep <= k ? 'flag' : 'on';
      return `<i class="${st}" title="${esc(`battery ${u.batt} (home ${u.home}) · ${DET_WORDS[st]}${u.flaggedStep !== null ? ` · flagged ${stepToTime(meta, u.flaggedStep)}` : ''}`)}"></i>`;
    }).join('');
    const cx = det.x(k);
    $('.rv-det').innerHTML = `<div class="h"><span class="e">DETECTOR · FICTIONAL ATTACKER</span>${tagHTML(det.label, (covert.sources && covert.sources.detector && covert.sources.detector.text) || 'detector run')}</div>
      <div class="rv-det-top"><div class="big">${k < a.step ? '—' : `${fmtN(flagged)} of ${fmtN(det.units.length)}`}</div>
        <div class="l">${k < a.step ? `The channel opens at ${esc(a.t)}` : `compromised batteries flagged<br>${fmtN(quarantined)} quarantined (held at zero)`}</div></div>
      <svg class="rv-det-plot" viewBox="0 0 300 44" preserveAspectRatio="none" aria-label="Batteries flagged and quarantined, ${esc(stepToTime(meta, det.w0))} to ${esc(stepToTime(meta, det.w1))}">
        <rect width="300" height="44" fill="#f6f3ea"></rect>
        <path d="${det.flagPath}" fill="none" stroke="#b23a2f" stroke-width="1.6" vector-effect="non-scaling-stroke"></path>
        <path d="${det.heldPath}" fill="none" stroke="#10231a" stroke-width="1.2" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"></path>
        ${cx !== null ? `<line x1="${cx}" x2="${cx}" y1="0" y2="44" stroke="#1e4d2b" stroke-width="2" vector-effect="non-scaling-stroke"></line>` : ''}</svg>
      <div class="rv-det-ax"><span>${esc(stepToTime(meta, det.w0))}</span><span><i class="flag"></i>flagged <i class="held"></i>quarantined</span><span>${esc(stepToTime(meta, det.w1))}</span></div>
      <div class="rv-cells">${cells}</div>
      <div class="l">${sm.detectionSeconds ? `First flag ${ctx.num(sm.detectionSeconds, { unit: ' s' })} after the channel opens` : ''}${sm.falsePositivesClean ? ` · false flags on the clean fleet ${ctx.num(sm.falsePositivesClean)}` : ''}</div>`;
  }

  // worker_kill: the controller's workers and leases from the run's own runtime block (mpalacios.runtime replay)
  function drawController() {
    if (!rt) return;
    const h = rt.holder[k] || '';
    const kill = rt.kill || null, tk = (rt.takeover || [])[0] || null, late = rt.late || null;
    const killed = kill && k >= kill.step ? kill.worker : null;
    const tgt = (rt.partitionTargetKW || [])[k] || [], got = (rt.partitionDeliveredKW || [])[k] || [];
    const rows = rt.partitions.map((p, i) => {
      const ch = h[i] || '-';
      const w = ch === '-' ? null : `W${ch}`;
      const took = tk && k >= tk.step && tk.partition === p.id;
      const state = !w ? `no worker: its ${fmtN((p.batts || []).length)} batteries run on their last commands` : took ? `${w}, took over (epoch ${tk.epoch})` : w;
      return `<div class="rv-ctl-row${w ? '' : ' gap'}"><b>${esc(p.id)}</b><span class="w">${esc(state)}</span>
        <span class="kw">${tgt[i] !== undefined ? `${fmtN(got[i] / 10, 0)} of ${fmtN(tgt[i] / 10, 0)} kW` : ''}</span></div>`;
    }).join('');
    const ev = (e, text) => (e ? `<div class="rv-ctl-ev${k >= e.step ? ' on' : ''}"><span class="s">${esc(e.t)}</span><span>${esc(text)}</span></div>` : '');
    $('.rv-ctl').innerHTML = `<div class="h"><span class="e">CONTROLLER · ${fmtN((rt.workers || []).length)} WORKERS</span>${tagHTML(rtLab('holder'), (doc.series && doc.series.holder && doc.series.holder.unit) || 'runtime.holder')}</div>
      <div class="rv-ctl-ws">${(rt.workers || []).map((w) => `<span class="${w === killed ? 'dead' : ''}">${esc(w)}${w === killed ? ' · killed' : ''}</span>`).join('')}</div>
      <div class="rv-ctl-rows">${rows}</div>
      <div class="rv-ctl-sub">delivered of target kW per group ${tagHTML(rtLab('partitionDeliveredKW'), (doc.series && doc.series.partitionDeliveredKW && doc.series.partitionDeliveredKW.by) || '')}</div>
      ${ev(kill, kill ? kill.text : '')}${ev(tk, tk ? tk.text : '')}${ev(late, late ? late.text : '')}`;
  }

  function draw() {
    if (drawn === k) return;
    drawn = k;
    const x = (k / (n - 1) * 1000).toFixed(1);
    for (const r of clips) r.setAttribute('width', x);
    cursor.style.left = `${(k / (n - 1) * 100).toFixed(3)}%`;
    $('.st-clock').textContent = stepToTime(meta, k);
    $('.rv-stepno').textContent = `Step ${fmtN(k + 1)} of ${fmtN(n)}`;
    $('.rv-scrub').setAttribute('aria-valuenow', String(k));
    const code = doc.tier[k] ? Number(doc.tier[k][S.wtf[k]]) : 0;
    const c = S.counts[k] || [0, 0, 0, 0, 0];
    root.querySelector('[data-v="worst"]').innerHTML = `<b>${fmtN(S.worst[k], 1)}%</b> · ${esc(tfName(topology, S.wtf[k]))} ${tagHTML(loadLab)}`;
    const top = S.focus.reduce((m, f) => (f.pct[k] > m.pct[k] ? f : m), S.focus[0]);
    root.querySelector('[data-v="focus"]').innerHTML = top ? `top <b>${esc(top.name)} ${fmtN(top.pct[k], 0)}%</b> ${tagHTML(loadLab)}` : '';
    root.querySelector('[data-v="price"]').innerHTML = S.price ? `<b>$${fmtN(S.price[k], 2)}</b> ${tagHTML(priceLab, meta.sources && meta.sources.price ? meta.sources.price.text : '')}` : 'no price series';
    root.querySelector('[data-v="soc"]').innerHTML = noFleet ? 'no batteries' : `<b>${fmtN(S.soc[k], 0)}%</b> ${tagHTML(socLab)}${reservePct !== null ? ` · ${fmtN(reservePct)}% reserve` : ''}`;
    root.querySelector('[data-v="kw"]').innerHTML = noFleet ? 'no batteries' : `<b>${S.kw[k] >= 0 ? '+' : '−'}${fmtN(Math.abs(S.kw[k]) / 1000, 2)}</b> ${tagHTML('SIM')} · ±${fmtN(kwHi / 1000)} MW`;
    // hero
    $('[data-v="hero"]').textContent = `${fmtN(S.worst[k], 1)}%`;
    $('.rv-hero .who i').style.background = rgb(TIER_RGB[code] || TIER_RGB[0]);
    $('.rv-hero .who b').textContent = tfName(topology, S.wtf[k]);
    $('.rv-hero .who .tn').textContent = TN[code] || '';
    $('.rv-hero .cnt').textContent = `Over nameplate ${fmtN(c[0] + c[1] + c[2] + c[3])} · above ${tiers.normal ?? ''}% ${fmtN(c[1] + c[2] + c[3])} · emergency ${fmtN(c[3])} · open ${fmtN(c[4])}`;
    // battery
    const socNow = noFleet ? 0 : clamp(S.soc[k], 0, 100);
    for (const s of [$('.rv-fill'), $('.rv-stripes')]) s.style.width = `${socNow.toFixed(1)}%`;
    const pctEl = $('.rv-pct');
    pctEl.textContent = noFleet ? '' : `${fmtN(socNow, 0)}%`;
    pctEl.classList.toggle('dark', socNow < 18);
    const kwNow = S.kw[k];
    $('.rv-bat .flow').textContent = noFleet ? '' : Math.abs(kwNow) < 5 ? 'Holding' : kwNow > 0 ? `Charging +${fmtN(kwNow / 1000, 2)} MW` : `Discharging −${fmtN(-kwNow / 1000, 2)} MW`;
    // story line
    const m = momentAt(moments, k);
    const story = $('.rv-story');
    story.hidden = !m;
    if (m) { story.querySelector('b').textContent = m.t || stepToTime(meta, m.k); story.querySelector('span').innerHTML = `${esc(m.text)} ${m.label ? tagHTML(m.label, m.rule ? `rule: ${m.rule}` : '') : ''}`; }
    drawNow();
    drawDetector();
    drawController();
    if (scene && sceneK !== k) {
      sceneK = k;
      scene.update(buildSceneModel({ topology: topoRun, footprints, frame: frameFromP1(doc, k), view: 'p1', theme: 'light', hideBatteries }));
    }
  }

  function seek(nk, { user = true } = {}) {
    k = clamp(Math.round(nk), 0, n - 1);
    if (user) ctx.setK(k);
    requestDraw();
  }
  let pend = 0;
  function requestDraw() { if (!pend) pend = requestAnimationFrame(() => { pend = 0; if (!disposed) draw(); }); }

  function tick(now) {
    if (!playing || disposed) return;
    acc += (now - last) * speed / MS_PER_STEP;
    last = now;
    if (acc >= 1) {
      const st = Math.floor(acc);
      acc -= st;
      if (k + st >= n - 1) { seek(n - 1); setPlaying(false); return; }
      seek(k + st);
    }
    raf = requestAnimationFrame(tick);
  }
  function setPlaying(p) {
    playing = p;
    $('.rv-play').textContent = p ? '❚❚' : '▶';
    $('.rv-play').setAttribute('aria-label', p ? 'Pause' : 'Play');
    cancelAnimationFrame(raf);
    if (p) { if (k >= n - 1) seek(0); last = performance.now(); acc = 0; raf = requestAnimationFrame(tick); }
  }

  // ---- events
  $('.rv-play').addEventListener('click', () => setPlaying(!playing));
  $('.rv-replay').addEventListener('click', () => { seek(0); setPlaying(true); });
  for (const b of root.querySelectorAll('.rv-speed button')) b.addEventListener('click', () => setSpeed(Number(b.dataset.speed)));
  const scrub = $('.rv-scrub');
  const kFrom = (ev) => { const r = scrub.getBoundingClientRect(); return (ev.clientX - r.left) / r.width * (n - 1); };
  let drag = false;
  scrub.addEventListener('pointerdown', (ev) => { drag = true; try { scrub.setPointerCapture(ev.pointerId); } catch (e) { /* ignore */ } seek(kFrom(ev)); });
  scrub.addEventListener('pointermove', (ev) => { if (drag) seek(kFrom(ev)); });
  scrub.addEventListener('pointerup', () => { drag = false; });
  scrub.addEventListener('keydown', (ev) => {
    if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') { ev.preventDefault(); seek(k + (ev.key === 'ArrowRight' ? 1 : -1) * (ev.shiftKey ? 15 : 1)); }
  });
  root.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-seek]');
    if (b) seek(Number(b.dataset.seek));
    const c = ev.target.closest('[data-cam]');
    if (c && scene) {
      for (const x of root.querySelectorAll('[data-cam]')) x.classList.toggle('on', x === c);
      scene.camera(c.dataset.cam);
    }
  });
  const onKey = (ev) => {
    if (ev.target && /input|textarea|select/i.test(ev.target.tagName)) return;
    if (ev.key === ' ' && !(ev.target && ev.target.closest && ev.target.closest('button'))) { ev.preventDefault(); setPlaying(!playing); }
  };
  document.addEventListener('keydown', onKey);

  setSpeed(speed);
  draw();
  // the scene: deck.gl (or the 2D fallback); its first render gates "ready"
  try {
    scene = await makeScene($('.rv-scene-el'), topoRun, ctx.params.nowebgl, (e) => console.error('[hb scene]', e));
    scene.camera('feeder', { instant: true });
    sceneK = -1;
    drawn = -1;
    draw();
    // a slow first frame (a loaded machine, a background tab) is not an error: the page is usable, the scene fills in
    await withTimeout(scene.whenRendered(), 20000, 'first scene render').catch((e) => console.warn('[hb story]', e.message));
  } finally {
    const l = root.querySelector('.rv-scene .rv-loading');
    if (l) l.remove();
  }
  if (autoplay && !disposed) setPlaying(true);

  return {
    setK(nk) { seek(nk, { user: false }); },
    dispose() {
      disposed = true;
      playing = false;
      cancelAnimationFrame(raf);
      cancelAnimationFrame(pend);
      document.removeEventListener('keydown', onKey);
      try { if (scene) scene.dispose(); } catch (e) { /* already gone */ }
      root.innerHTML = '';
    },
  };
}
