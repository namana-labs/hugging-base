// Shared data for the three story views (levers → watch → result).
// Real P1 runs come from ui/data via hb-views.js. ERCOT-wide signals, bus voltage shape
// and reactive power are scripted here and carry ASSUMPTION / UNVERIFIED tags.
import * as H from './hb-views.js';
export { H };

export const LS_KEY = 'hb-story-levers';
export const DEFAULTS = { controller: 'aware', failures: false, fleetSize: 96, cls: 'core', reserve: 20, soc0: 90 };
export const BRANCH = {
  none: { name: 'No batteries', short: 'no batteries' },
  naive: { name: 'Naive split', short: 'naive' },
  aware: { name: 'Feeder-aware', short: 'feeder-aware' },
  aware_faults: { name: 'Feeder-aware + failures', short: 'aware + failures' },
};
export const TIER_COLOR = H.TIER_COLOR;

export function getLevers() {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(LS_KEY) || '{}') }; } catch (e) { return { ...DEFAULTS }; }
}
export function setLevers(v) { try { localStorage.setItem(LS_KEY, JSON.stringify(v)); } catch (e) { /* ignore */ } }

/** Which committed run the lever settings match, or the nearest one plus the re-run command. */
export function resolve(l) {
  const diffs = [];
  if (l.fleetSize !== DEFAULTS.fleetSize) diffs.push({ flag: '--fleet-size', v: String(l.fleetSize), what: `fleet ${l.fleetSize} homes` });
  if (l.cls !== DEFAULTS.cls) diffs.push({ flag: '--class', v: l.cls, what: `${l.cls === 'legacy' ? 'Legacy' : 'Core'} batteries` });
  if (l.reserve !== DEFAULTS.reserve) diffs.push({ flag: '--reserve', v: (l.reserve / 100).toFixed(2), what: `${l.reserve}% reserve` });
  if (l.soc0 !== DEFAULTS.soc0) diffs.push({ flag: '--soc0', v: (l.soc0 / 100).toFixed(2), what: `${l.soc0}% start` });
  const failures = l.controller !== 'none' && l.failures;
  if (failures && l.controller === 'naive') diffs.push({ flag: '--faults', v: 'naive', what: 'failures on naive' });
  const branch = l.controller === 'none' ? 'none' : l.controller === 'naive' ? 'naive' : failures ? 'aware_faults' : 'aware';
  const cmd = `python -m sim.p1_build --out runs/custom${diffs.map((d) => ` ${d.flag} ${d.v}`).join('')}`;
  return { matches: diffs.length === 0, branch, diffs, cmd, failures };
}

let basePromise = null; const runs = {};
export function loadBase() { if (!basePromise) basePromise = H.loadP1Base(); return basePromise; }
export function loadRun(b) {
  if (!runs[b]) runs[b] = (async () => { const base = await loadBase(); const doc = await H.loadP1Branch(b); return { ...base, doc, branch: b, s: series(base, doc) }; })();
  return runs[b];
}

const FOCUS = ['A', 'B', 'C', 'D', '240'];
function series({ meta }, doc) {
  const n = meta.steps; const soc = [], kw = [], worst = [], wtier = [], wtf = [], vmin = [], counts = []; const focus = {};
  FOCUS.forEach((k) => { if (doc.focus && doc.focus[k]) focus[k] = { tf: doc.focus[k].tf, pct: [] }; });
  for (let k = 0; k < n; k++) {
    const s = doc.soc[k], b = doc.batKW[k]; let ss = 0, bb = 0;
    for (let i = 0; i < s.length; i++) { ss += s[i]; bb += b[i]; }
    soc.push(ss / s.length / 10); kw.push(bb / 10);
    const w = H.worstAt(doc, k); worst.push(w.pct); wtier.push(w.code); wtf.push(w.tf);
    vmin.push(doc.vMin[k] / 1e4); counts.push(H.countsAt(doc, k));
    for (const key in focus) focus[key].pct.push(doc.loading[k][focus[key].tf] / 10);
  }
  return { n, soc, kw, worst, wtier, wtf, vmin, counts, focus, price: meta.price };
}

export const hourOf = (k) => 16 + k / 60;
export const timeOf = (k) => { const m = Math.round(k) + 16 * 60; return `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; };

// ---- SVG paths on a 0..1000 × 0..100 field -------------------------------------------------------------
export const yOf = (v, lo, hi, top = 4, bot = 96) => +(bot - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo) * (bot - top)).toFixed(2);
export function path(arr, lo, hi, top, bot) {
  const n = arr.length; let d = '';
  for (let i = 0; i < n; i++) d += (i ? 'L' : 'M') + (i / (n - 1) * 1000).toFixed(1) + ',' + yOf(arr[i], lo, hi, top, bot);
  return d;
}
export function area(arr, lo, hi, base, top, bot) {
  const y0 = yOf(base == null ? lo : base, lo, hi, top, bot);
  return path(arr, lo, hi, top, bot) + `L1000,${y0}L0,${y0}Z`;
}
export const xPct = (k, n) => `${(k / (n - 1) * 100).toFixed(3)}%`;

// ---- scripted ERCOT-wide signals, evening 16:00 → 04:00 (from Heartbeat v2) --------------------------------
const gs = (x, m, s) => Math.exp(-0.5 * ((x - m) / s) ** 2);
const demand = (h) => { h %= 24; return 0.30 + 0.08 * gs(h, 7.5, 1.3) + 0.62 * gs(h, 18.6, 2.4) + 0.12 * gs(h, 14, 3); };
const solar = (h) => { h %= 24; if (h < 6.8 || h > 19.8) return 0; return Math.pow(Math.max(0, Math.sin(Math.PI * (h - 6.8) / 13)), 1.5); };
const trip = (h) => (h >= 18.333 ? (h - 18.333) * 60 : -1);
export const SYS = {
  freq(h) { const m = trip(h); let f = 60 + 0.008 * Math.sin(h * 7.1 + 1) + 0.006 * Math.sin(h * 23 + 2.1) + 0.004 * Math.sin(h * 61 + 0.7); if (m >= 0 && m < 60) f += -0.125 * Math.exp(-m / 3) * (1 - Math.exp(-m * 5)) - 0.015 * Math.exp(-m / 14) * (1 - Math.exp(-m)); return f; },
  rocof(h) { const m = trip(h); let r = 0.004 * Math.sin(h * 97 + 1) + 0.002 * Math.sin(h * 211 + 3); if (m >= 0 && m < 30) r += -0.085 * Math.exp(-m * 1.2) + 0.01 * Math.exp(-m / 3) * (1 - Math.exp(-m * 2)); return r; },
  te(h) { const m = trip(h); return 1.4 * Math.sin(h / 24 * 6.283 + 1) + 0.5 * Math.sin(h * 0.9 + 1.7) - (m >= 0 ? 0.35 * (1 - Math.exp(-m / 30)) : 0); },
  prc(h) { const m = trip(h); return 7200 + 150 * Math.sin(h * 3.1 + 1) - 3400 * gs(h % 24 < 12 ? h : h, 20.3, 1.4) - (m >= 0 ? 1100 * Math.exp(-m / 26) : 0); },
  inert(h) { const m = trip(h); return 230 + 70 * demand(h) - 90 * solar(h) + 6 * Math.sin(h * 2.3 + 1) - (m >= 0 && m < 600 ? 5 : 0); },
  qdem(h) { return 0.34 * (1.6 + 3.5 * demand(h)); },
  qcap(h) { return SYS.qdem(h) > 1.05 ? 0.6 : 0; },
};
export const SYS_DEF = [
  { key: 'freq', title: 'Frequency', unit: 'Hz', lo: 59.84, hi: 60.04, tag: 'ASSUMPTION', note: 'ERCOT system', digits: 3, refs: [{ v: 60, solid: true }, { v: 60.017, dash: true }, { v: 59.983, dash: true, label: 'deadband ±0.017' }] },
  { key: 'rocof', title: 'RoCoF', unit: 'Hz/s', lo: -0.1, hi: 0.04, tag: 'ASSUMPTION', note: 'Rate of change of frequency', digits: 3, refs: [{ v: 0, solid: true }] },
  { key: 'te', title: 'Time error', unit: 's', lo: -3, hi: 3, tag: 'ASSUMPTION', note: 'Accumulated clock drift', digits: 2, refs: [{ v: 0, solid: true }] },
  { key: 'prc', title: 'PRC', unit: 'MW', lo: 0, hi: 9000, tag: 'UNVERIFIED', note: 'Responsive reserve left', digits: 0, fill: true, refs: [{ v: 3000, color: '#c7962b', label: 'Watch 3,000' }, { v: 2500, color: '#b23a2f', label: 'EEA1 2,500', below: true }] },
  { key: 'inert', title: 'Inertia', unit: 'GW·s', lo: 0, hi: 350, tag: 'UNVERIFIED', note: 'Speed of a frequency fall', digits: 0, refs: [{ v: 100, color: '#b23a2f', label: 'critical ~100' }] },
];
export function sysSeries(n) {
  const out = {}; for (const d of SYS_DEF) { out[d.key] = []; for (let k = 0; k < n; k++) out[d.key].push(SYS[d.key](hourOf(k))); }
  out.qdem = []; out.qcap = []; for (let k = 0; k < n; k++) { out.qdem.push(SYS.qdem(hourOf(k))); out.qcap.push(SYS.qcap(hourOf(k))); }
  return out;
}
export const fmtNum = (v, digits = 0) => (v == null || Number.isNaN(v) ? '—' : Number(v).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }));

// ---- runs: configure → go → the simulator runs in the background ----------------------------------------
// If window.HB_SIM_URL is set, POST the levers there and poll. Otherwise progress is simulated from the
// measured engine speed (engine.json: 4.2 ms per OpenDSS step) and the result is the committed run nearest the settings.
export const RUN_KEY = 'hb-story-run';
export function getRun() { try { return JSON.parse(localStorage.getItem(RUN_KEY) || 'null'); } catch (e) { return null; } }
function saveRun(r) { try { localStorage.setItem(RUN_KEY, JSON.stringify(r)); } catch (e) { /* ignore */ } }
export function sameLevers(a, b) { return !!a && !!b && Object.keys(DEFAULTS).every((k) => a[k] === b[k]); }
let live = null;
export function startRun(levers, onUpdate) {
  const res = resolve(levers); const prev = getRun();
  const rec = { id: (prev && prev.id ? prev.id : 0) + 1, levers: { ...levers }, status: 'running', stage: 'Loading feeder, loads and prices', step: 0, steps: 720,
    startedAt: Date.now(), branch: res.branch, connected: !!(typeof window !== 'undefined' && window.HB_SIM_URL), preview: !res.matches };
  saveRun(rec); onUpdate({ ...rec });
  if (live) clearInterval(live);
  if (rec.connected) {
    fetch(window.HB_SIM_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(levers) })
      .then((r) => r.json()).then((j) => { Object.assign(rec, { status: 'done', stage: 'Done', step: 720, remote: j }); saveRun(rec); onUpdate({ ...rec }); })
      .catch((e) => { Object.assign(rec, { status: 'failed', stage: String(e && e.message || e) }); saveRun(rec); onUpdate({ ...rec }); });
    return rec;
  }
  const t0 = performance.now(), setup = 700, perStep = 4.2, tail = 400;
  live = setInterval(() => {
    const t = performance.now() - t0;
    if (t < setup) rec.stage = 'Loading feeder, loads and prices';
    else if (t < setup + 720 * perStep) { rec.stage = 'OpenDSS power flow'; rec.step = Math.min(720, Math.floor((t - setup) / perStep)); }
    else if (t < setup + 720 * perStep + tail) { rec.stage = 'Writing results'; rec.step = 720; }
    else { rec.status = 'done'; rec.stage = 'Done'; rec.finishedAt = Date.now(); clearInterval(live); live = null; }
    saveRun(rec); onUpdate({ ...rec });
  }, 80);
  return rec;
}

// ---- how many batteries fit on one transformer: screening estimate from the P1 no-battery evening -------------
// Naive: every battery charges at full power from the 22:00 onset until refilled; fits while the transformer stays
// under its normal rating (110%, or 150% if the charge lasts under 30 min). Feeder-aware: charge only into room under
// 95% of nameplate between 22:00 and 04:00; fits while at least 90% of the energy gets back (CURTAIL_CAP 10%).
export const KVA_STEPS = [10, 25, 50, 75, 100, 150, 167];
export function fitModel(noneRun, awareRun, tf, kvaOverride, growth = 0) {
  const t = noneRun.topology.transformers[tf]; const kva0 = t.kva, kva = kvaOverride || kva0;
  const home = noneRun.doc.loading.map((r) => r[tf] / 1000 * kva0 * (1 + growth));
  const onset = 360, end = noneRun.s.n; const socOn = awareRun.s.soc[onset];
  const need = 37 * (1 - socOn / 100), d = Math.ceil(need / 20 * 60);
  let hm = 0; for (let k = onset; k < Math.min(end, onset + d); k++) hm = Math.max(hm, home[k]);
  let E = 0; for (let k = onset; k < end; k++) E += Math.max(0, 0.95 * kva - home[k]) / 60;
  const lim = d >= 30 ? 110 : 150;
  const naivePeak = (n) => (hm + n * 20) / kva * 100;
  const awareBack = (n) => (n === 0 ? 100 : Math.min(100, E / (n * need) * 100));
  const nNaive = Math.max(0, Math.floor((lim / 100 * kva - hm) / 20)), nAware = Math.max(0, Math.floor(E / (need * 0.9)));
  return { kva, kva0, homes: t.homes.length, need, chargeMin: d, lim, homePeakAtOnset: hm, roomKWh: E, naivePeak, awareBack, nNaive, nAware };
}
export function nextKva(kva) { return KVA_STEPS.find((x) => x > kva) || kva; }

// ---- voltage by bus: every service transformer ordered by distance from the substation ------------------------
// Shape is scripted (ASSUMPTION); the floor at each step is OpenDSS minimum home voltage (SIM).
let busCache = null;
export function buses(topology) {
  if (busCache) return busCache;
  const src = topology.meta.source; const cos = Math.cos(src[1] * Math.PI / 180);
  const d = topology.transformers.map((t, i) => ({ i, d: Math.hypot((t.lonlat[0] - src[0]) * cos, t.lonlat[1] - src[1]) }));
  d.sort((a, b) => a.d - b.d); const max = d[d.length - 1].d || 1;
  busCache = d.map((b, j) => { const h = Math.sin((b.i + 1) * 12.9898) * 43758.5453; const jit = h - Math.floor(h); return { tf: b.i, j, dn: b.d / max, f: Math.min(1, Math.pow(b.d / max, 0.85) * (0.82 + 0.18 * jit)) }; });
  return busCache;
}
export const busV = (b, vmin) => 1.03 - (1.03 - vmin) * b.f;
export const vColor = (v) => (v > 1.05 ? '#6e1d17' : v < 0.95 ? '#b23a2f' : (v < 0.96 || v > 1.04) ? '#c7962b' : '#8aa58f');
