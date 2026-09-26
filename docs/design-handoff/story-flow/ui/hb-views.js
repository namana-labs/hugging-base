// Hugging Base view models for the design components (P1, P2, captions). Business logic lifted from
// hugging-base/ui/panels/p1.js, p2.js and more.js; styling lives in the .dc.html templates.
// Every number leaves here as a part {isNum:true, n, label, cite}; prose as {isText:true, t}.
import * as fmt from './lib/format.js';
import * as SM from './lib/scene-model.js';
import { evalFact, sourcesFor, flipVerdict, FLIP_HEADLINE_MAX_OVERLAP, isScreening, sharedNames } from './panels/more.js';
import { chartHTML, modeIndex } from './lib/charts.js';

export { fmt, SM, chartHTML };
const BASE = new URL('data/', import.meta.url);
const cache = new Map();
export function getJSON(path) {
  if (!cache.has(path)) cache.set(path, fetch(new URL(path, BASE)).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`); return r.json(); }));
  return cache.get(path);
}
export const getOptional = (p) => getJSON(p).catch(() => null);

// ---- parts -------------------------------------------------------------------------------------------------------
export const T = (t) => ({ isText: true, t: String(t) });
export const N = (x, o = {}) => (fmt.isLabelled(x) ? { isNum: true, n: fmt.fmtValue(x, o), label: x.label, cite: x.cite || '', screening: isScreening(x) } : T('n/a'));
export const C = (label, cite) => ({ isNum: true, n: '', label, cite: cite || '' });
export const L = (v, label, cite) => ({ v, label, ...(cite ? { cite } : {}) });
/** Build parts from a mixed list: strings -> text, labelled -> number (o from x.o or 2nd tuple item), arrays [x, opts]. */
export function P(...items) {
  const out = [];
  for (const it of items.flat ? items : items) {
    if (it === null || it === undefined || it === '' || it === false) continue;
    if (typeof it === 'string') out.push(T(it));
    else if (it.isText || it.isNum) out.push(it);
    else if (Array.isArray(it)) out.push(N(it[0], it[1] || {}));
    else if (fmt.isLabelled(it)) out.push(N(it, it.o || {}));
    else out.push(T(String(it)));
  }
  return out;
}

export const TIER_COLOR = ['#0ca30c', '#fab219', '#ec835a', '#ec835a', '#d03b3b', '#6b6f6c'];
export const BRANCH_NAMES = { none: 'no batteries', naive: 'naive', aware: 'feeder-aware', aware_faults: 'aware + failures' };
export const GAUGE_MAX_PCT = 220;
const FOCUS_KEYS = ['A', 'B', 'C', 'D', '240'];
const DRIVER_WINDOW_MIN = 15;

// ---- P1 ----------------------------------------------------------------------------------------------------------
export async function loadP1Base() {
  const [meta, topology, footprints] = await Promise.all([getJSON('p1/meta.json'), getJSON('topology.json'), getOptional('footprints.json')]);
  return { meta, topology, footprints };
}
export const loadP1Branch = (b) => getJSON(`p1/${b}.json`);

export function worstAt(doc, k) {
  const row = doc.loading[k]; let best = -1, tf = 0;
  for (let i = 0; i < row.length; i++) if (row[i] > best) { best = row[i]; tf = i; }
  return { pct: best / 10, tf, code: Number(doc.tier[k][tf]) };
}
export function countsAt(doc, k) {
  if (doc.counts && doc.counts[k]) return doc.counts[k].slice(0, 5);
  const c = [0, 0, 0, 0, 0];
  for (const ch of doc.tier[k]) { const n = Number(ch); if (n >= 1 && n <= 5) c[n - 1] += 1; }
  return c;
}
function stateCounts(doc, k) { const c = { C: 0, D: 0, I: 0, S: 0, X: 0, B: 0 }; for (const ch of doc.state[k]) if (ch in c) c[ch] += 1; return c; }
function tfEvening(doc, tf, stepSeconds = 60) {
  let max = -1, at = 0, n110 = 0, n150 = 0, open = -1;
  for (let k = 0; k < doc.loading.length; k++) {
    const v = doc.loading[k][tf]; if (v > max) { max = v; at = k; }
    const c = Number(doc.tier[k][tf]);
    if (c >= 2 && c <= 4) n110 += 1; if (c === 4) n150 += 1; if (c === 5 && open < 0) open = k;
  }
  const m = stepSeconds / 60;
  return { maxPct: max / 10, maxStep: at, min110: n110 * m, min150: n150 * m, openStep: open };
}
function spikeDriverAt(meta, tf, k) {
  const near = (step) => Number.isInteger(step) && Math.abs(k - step) <= DRIVER_WINDOW_MIN * 60 / (meta.stepSeconds || 60);
  const r = meta.relief;
  if (r && r.tf === tf && r.driver && near(Number.isInteger(r.step) ? r.step : fmt.timeToStep(meta, r.t))) return { kind: 'relief', t: r.t, driver: r.driver };
  for (const u of meta.unrelieved || []) if (u.tf === tf && u.driver && u.peak && u.peak.t && near(fmt.timeToStep(meta, u.peak.t))) return { kind: 'unrelieved', t: u.peak.t, driver: u.driver };
  return null;
}
function reliefPeakAt(meta, doc) {
  const r = meta.relief; if (!r || !r.reliefKW || !doc.focus) return null;
  const f = Object.values(doc.focus).find((x) => x && x.tf === r.tf); const step = r.step;
  if (!f || step == null) return null;
  const w = Math.round(DRIVER_WINDOW_MIN * 60 / (meta.stepSeconds || 60)); let best = null;
  for (let i = Math.max(0, step - w); i <= Math.min(f.batKW.length - 1, step + w); i++) if (best === null || f.batKW[i] < f.batKW[best]) best = i;
  if (best === null || Math.abs(-f.batKW[best] / 10 - r.reliefKW.v) > 0.1) return null;
  return fmt.stepToTime(meta, best);
}
function faultText(e, homeLabel) {
  const who = e.home != null ? homeLabel(e.home) : e.tf != null ? `transformer ${e.tf}` : '';
  if (e.kind === 'comms_lost') return `comms lost: ${who}`; if (e.kind === 'hot') return `runs hot: ${who}`; if (e.kind === 'stall') return 'our controller stalls';
  return `${e.kind}${who ? ': ' + who : ''}`;
}
export function stripMarks(meta, branch, homeLabel) {
  const out = []; const evKey = (e) => `${e.t}|${e.text || ''}`; const evs = new Set();
  for (const list of Object.values(meta.events || {})) for (const e of list || []) evs.add(evKey(e));
  const seen = new Map();
  for (const m of meta.markers || []) {
    if (evs.has(`${m.t}|${m.text}`)) continue;
    const k = fmt.timeToStep(meta, m.t); if (k === null) continue;
    const first = !seen.has(m.text); if (first) seen.set(m.text, { n: 0 }); seen.get(m.text).n += 1;
    out.push({ k, t: m.t, text: m.text, label: m.label || 'SIM', kind: 'marker', repeat: !first, group: seen.get(m.text) });
  }
  for (const e of (meta.events && meta.events[branch]) || []) out.push({ k: e.step, t: e.t, text: e.text || faultText(e, homeLabel), label: 'SIM', kind: 'fault', group: { n: 1 } });
  out.sort((a, b) => a.k - b.k);
  const rowEnd = [-1, -1, -1]; const n = meta.steps || 1;
  for (const m of out) {
    m.count = m.group.n; delete m.group; m.row = -1; if (m.repeat) continue;
    const x = (m.k + 0.5) / n, w = (m.t.length + 1 + Math.min(m.text.length, 34) + (m.count > 1 ? 3 : 0) + 6) * 0.0054;
    for (let r = 0; r < 3; r++) if (x > rowEnd[r]) { m.row = r; rowEnd[r] = x + w; break; }
  }
  return out.map((m) => ({
    k: m.k, left: `${(100 * (m.k + 0.5) / n).toFixed(2)}%`, top: `${Math.max(0, m.row) * 13}px`, hasLabel: m.row >= 0,
    text: `${m.t} ${m.text.length > 34 ? m.text.slice(0, 33) + '…' : m.text}${m.count > 1 ? ` ×${m.count}` : ''}`,
    title: `${m.t} ${m.text} (${m.label})`, label: m.label, isFault: m.kind === 'fault', isMarker: m.kind !== 'fault',
  }));
}

export function p1View({ meta, topology, doc, branch, k }) {
  const lab = (doc.series && doc.series.loading && doc.series.loading.label) || 'SIM';
  const flab = (doc.series && doc.series.focus && doc.series.focus.label) || 'SIM';
  const homeLabel = (h) => (typeof h === 'number' ? (topology.homes[h] ? topology.homes[h].label : `home ${h}`) : String(h));
  const tfName = (tf) => { const f = (topology.focus || []).find((x) => x.tf === tf); return f ? f.key : `T-${tf}`; };
  const time = fmt.stepToTime(meta, k);
  const w = worstAt(doc, k), c = countsAt(doc, k), sc = stateCounts(doc, k);
  const pctL = (v) => L(+v.toFixed(1), lab, 'OpenDSS loading, % of nameplate');

  // hero
  let driver = null;
  if (w.code >= 1) {
    const info = spikeDriverAt(meta, w.tf, k);
    if (info) {
      const d = info.driver; const shared = sharedNames(d.sharedWith);
      driver = P(info.kind === 'unrelieved' ? 'home load only, no battery here: ' : '', `one home's 15-minute spike: ${d.label || homeLabel(d.home)}, SMART-DS profile ${d.profile}`,
        d.kwAtPeak ? ' (' : '', d.kwAtPeak ? [d.kwAtPeak, { unit: ' kW', digits: 1 }] : null, d.kwAtPeak ? ` at ${info.t})` : '',
        shared.length ? `; the same profile is used at ${shared.join(', ')}, so it is not independent evidence` : '', '.');
    }
  }
  let heroRelief = null;
  const r = meta.relief;
  if (r && branch === 'aware' && r.none && r.aware && spikeDriverAt(meta, r.tf, k)) {
    const at = reliefPeakAt(meta, doc);
    heroRelief = P(`relief on ${tfName(r.tf)} at ${r.t}: `, [r.none, { unit: '%', digits: 1 }], ' with no batteries → ', [r.aware, { unit: '%', digits: 1 }], ' feeder-aware',
      r.reliefKW ? '; its batteries discharged up to ' : '', r.reliefKW ? [r.reliefKW, { unit: ' kW', digits: 1 }] : null, r.reliefKW && at ? ` (${at})` : '', ' (over nameplate is amber, not a failure)');
  }
  const cnt = (v) => N(L(v, lab));
  const hero = {
    pct: fmt.fmtValue(pctL(w.pct), { unit: '%', digits: 1 }), chip: { label: lab, cite: 'OpenDSS loading, % of nameplate' }, color: TIER_COLOR[w.code] || '#101613',
    sub: `${tfName(w.tf)} · ${SM.TIER_NAMES[w.code] || ''}`, driver, hasDriver: !!driver, relief: heroRelief, hasRelief: !!heroRelief,
    counts: [T('transformers now: over nameplate '), cnt(c[0] + c[1] + c[2] + c[3]), T(' · above 110% '), cnt(c[1] + c[2] + c[3]), T(' · emergency '), cnt(c[3]), T(' · protection open '), cnt(c[4])],
    batteries: branch === 'none' ? [T('no batteries in this branch')] : P('batteries now: charging ', [L(sc.C, 'SIM')], ' · discharging ', [L(sc.D, 'SIM')], ' · idle ', [L(sc.I, 'SIM')],
      sc.S + sc.X ? ' · stale/expired ' : '', sc.S + sc.X ? [L(sc.S + sc.X, 'SIM')] : null, sc.B ? ' · islanded ' : '', sc.B ? [L(sc.B, 'SIM')] : null),
  };

  // gauges
  const fuse = meta.protection || { fusePct: 200, fuseMinutes: 10 };
  const ww = (p) => `${Math.max(0, Math.min(100, 100 * p / GAUGE_MAX_PCT)).toFixed(2)}%`;
  const gauges = FOCUS_KEYS.map((key) => {
    const f = doc.focus && doc.focus[key]; if (!f) return null;
    const t = topology.transformers[f.tf]; const kva = t.kva;
    const pct = doc.loading[k][f.tf] / 10, code = Number(doc.tier[k][f.tf]);
    const homeKW = f.homeKW[k] / 10, batKW = f.batKW[k] / 10, pKW = homeKW + batKW;
    const ev = tfEvening(doc, f.tf, meta.stepSeconds || 60);
    const batteries = (topology.fleet || []).filter((hi) => topology.homes[hi].tf === f.tf).length;
    const homePct = Math.max(0, 100 * homeKW / kva), batPct = 100 * batKW / kva;
    const batOn = batPct > 0.05 ? batPct : 0, relief = batPct < -0.05 ? Math.min(homePct, -batPct) : 0;
    const room = code === 5 ? [T('open (protection)')] : pct > 100
      ? P('over nameplate by ', [L(+((pct / 100 - 1) * kva).toFixed(1), 'DERIVED', 'OpenDSS loading above 100%, times kVA'), { unit: ' kVA', digits: 1 }])
      : pKW < 0 ? P('room to export ', [L(+Math.max(0, SM.exportRoomKW(kva, pct, pKW)).toFixed(1), 'DERIVED', 'kW of back-feed that still fits under nameplate'), { unit: ' kW', digits: 1 }])
        : P('room ', [L(+Math.max(0, SM.roomKW(kva, pct, pKW)).toFixed(1), 'DERIVED', 'kW of charge that still fits under nameplate'), { unit: ' kW', digits: 1 }]);
    return {
      key, title: key === '240' ? `T-240 · ${kva} kVA · no battery` : `${key} · ${kva} kVA · ${t.homes.length} homes, ${branch === 'none' ? 'batteries off in this branch' : `${batteries} batteries`}`,
      pct: fmt.fmtValue(pctL(pct), { unit: '%', digits: 1 }), label: lab, color: TIER_COLOR[code],
      homeW: ww(homePct - relief), reliefW: ww(relief), batW: ww(batOn), loadLeft: ww(pct),
      sub: [...P('home ', [L(+homeKW.toFixed(1), flab), { unit: ' kW', digits: 1 }], ' · batteries ', [L(+batKW.toFixed(1), flab), { unit: ' kW', digits: 1, signed: true }], ' · '), ...room],
      fuse: P('evening max ', [L(+ev.maxPct.toFixed(1), lab), { unit: '%', digits: 1 }], ` at ${fmt.stepToTime(meta, ev.maxStep)} · `, [L(ev.min110, lab), { unit: ' min' }], ' above 110%',
        ev.min150 ? ' · ' : '', ev.min150 ? [L(ev.min150, lab), { unit: ' min' }] : null, ev.min150 ? ' above 150%' : '',
        ' · fuse rule opens at ', [L(fuse.fusePct, 'ASSUMPTION', fuse.cite), { unit: '%' }], ' for ', [L(fuse.fuseMinutes, 'ASSUMPTION', fuse.cite), { unit: ' min' }],
        ev.openStep >= 0 ? ` · opened at ${fmt.stepToTime(meta, ev.openStep)}` : ''),
    };
  }).filter(Boolean);

  // ticker
  const tk = []; const tl = doc.ticker || [];
  for (let i = tl.length - 1; i >= 0 && tk.length < 6; i--) if (tl[i][0] <= k) tk.push({ text: tl[i][1], now: tk.length === 0 || tl[i][0] === k });
  tk.forEach((x) => { x.color = x.now ? '#101613' : '#55625A'; x.bar = x.now ? '#0B6B6F' : '#CAD3CA'; });

  // faults
  const evs = ((meta.events && meta.events[branch]) || []).map((e) => ({ t: e.t, text: e.text || faultText(e, homeLabel), color: e.step <= k ? '#101613' : '#55625A' }));

  // relief section
  let relief = null;
  if (r) {
    const d = r.driver; const mins = r.minutesOver100;
    relief = {
      big: P(`${tfName(r.tf)} at ${r.t}: `, [r.none, { unit: '%', digits: 1 }], ' without batteries → ', [r.aware, { unit: '%', digits: 1 }], ' feeder-aware'),
      minutes: mins ? P('none ', [L(mins.none, mins.label), { unit: ' min' }], ' → aware ', [L(mins.aware, mins.label, mins.cite), { unit: ' min' }]) : [T('n/a')],
      kw: r.reliefKW ? P([r.reliefKW, { unit: ' kW', digits: 1 }], r.reliefKWh ? ' · ' : '', r.reliefKWh ? [r.reliefKWh, { unit: ' kWh', digits: 1 }] : null) : [T('n/a')],
      driver: d ? `Driver: one home's 15-minute spike: ${d.label}, SMART-DS profile ${d.profile}${sharedNames(d.sharedWith).length ? `, also used at ${sharedNames(d.sharedWith).join(', ')}` : ''}. The same shape elsewhere is not independent evidence.` : '',
      note: r.text || '',
    };
  }
  const unrelieved = (meta.unrelieved || []).map((u) => ({ tf: tfName(u.tf), reason: u.reason || '', driver: u.driver ? `driver ${u.driver.label} (${u.driver.profile})` : '', cam: u.tf === ((topology.bridge || [])[0] || {}).tf ? 't240' : 'feeder' }));

  // grid checks + summary
  const s = meta.summary && meta.summary[branch];
  const grid = [];
  if (s && s.vMinHome) {
    const v = s.vMinHome; const where = `${v.home != null ? homeLabel(v.home) : ''}${v.t ? ', ' + v.t : ''}`;
    const below = s.homesBelow095 ? s.homesBelow095.v : null;
    grid.push(P(below === 0 ? 'Voltage stays in range at unity pf: lowest home ' : 'Lowest service voltage ', [L(v.v, v.label, v.cite), { digits: 4, unit: ' pu' }],
      v.volts != null ? ' = ' : '', v.volts != null ? [L(v.volts, v.label, v.cite), { unit: ' V', digits: 1 }] : null, ` (${where})`,
      below ? '; homes below 0.95 pu ' : '', below ? [s.homesBelow095] : null));
  }
  if (s && s.feederHead) {
    const h = s.feederHead;
    grid.push(P('Feeder head max ', [L(h.v, h.label, h.cite), { unit: '%', digits: 1 }], h.ratingA ? ' of ' : '', h.ratingA ? [h.ratingA, { unit: ' A' }] : null,
      h.amps != null ? ' (' : '', h.amps != null ? [L(h.amps, h.label, h.cite), { unit: ' A', digits: 0 }] : null, h.amps != null ? `${h.t ? ' at ' + h.t : ''})` : ''));
  }
  const NAMES = { batteryCausedNormal: 'Battery-caused normal-tier events', batteryCausedEmergency: 'Battery-caused emergency events', normalEvents: 'Normal-tier events (>110% for >= 30 min)',
    emergencyTfs: 'Transformers in emergency (>150%)', batteryCausedAmberMin: 'Battery-caused minutes over nameplate', homeOnlyOver100: 'Home-load-only transformers over nameplate',
    protectionOperated: 'Protection operated (fuse rule, ASSUMPTION)', homesDark: 'Homes dark', homesOnBattery: 'Homes lit by their own battery', reserveBreaches: '20% reserve breaches',
    chargedPctBy0400: 'Fleet charged by 04:00', energyValueUSD: "Energy value (gross, not Base's P&L)" };
  const optsFor = (kk) => (/USD/.test(kk) ? { money: true, digits: 2 } : /Pct/.test(kk) ? { unit: '%' } : /Min$/.test(kk) ? { unit: ' min' } : {});
  let summary = { hasClaim: false, rows: [] };
  if (s) {
    const ok = s.normalEvents && s.emergencyTfs && s.normalEvents.v === 0 && s.emergencyTfs.v === 0;
    summary = {
      hasClaim: !!(s.normalEvents && s.emergencyTfs), ok, bad: !ok, claimBg: ok ? 'rgba(12,163,12,.14)' : 'rgba(208,59,59,.14)',
      claim: ok ? P('No service transformer passed its limit this evening (normal rating or emergency) ', C(s.normalEvents.label, s.normalEvents.cite))
        : P([s.normalEvents], ' normal-tier events and ', [s.emergencyTfs], ' transformers in emergency this evening'),
      rows: [
        ...(s.maxLoading ? [{ k: 'Worst service transformer', v: P([s.maxLoading, { unit: '%', digits: 1 }], ` ${tfName(s.maxLoading.tf)}${s.maxLoading.t ? ' at ' + s.maxLoading.t : ''}`) }] : []),
        ...Object.keys(NAMES).filter((kk) => s[kk]).map((kk) => ({ k: NAMES[kk], v: P([s[kk], optsFor(kk)]) })),
      ],
    };
  }
  const nl = meta.naiveLabel || {};
  const framing = branch === 'naive' ? P(nl.text || '', ' ', C(nl.label || 'ASSUMPTION', nl.cite))
    : branch === 'none' ? [T('No batteries: what the homes alone do to their transformers.')]
      : branch === 'aware_faults' ? [T('Feeder-aware, while a battery goes silent, a transformer runs hot and our controller stalls.')]
        : [T("Feeder-aware: before sending charge, each transformer's headroom is checked and only what fits is sent.")];
  const priceLabel = (meta.series && meta.series.price && meta.series.price.label) || 'REAL';
  return {
    time, when: `${meta.day} · ${time} · step ${k} of ${meta.steps} · ${BRANCH_NAMES[branch] || branch}`,
    framing, hero, gauges, ticker: tk.length ? tk : [{ text: 'nothing sent yet', color: '#55625A', bar: '#CAD3CA' }],
    faults: evs, hasFaults: evs.length > 0, relief, hasRelief: !!relief, unrelieved, hasUnrelieved: unrelieved.length > 0,
    grid, summary,
    controller: meta.controllerView ? P(meta.controllerView.text, ' ', C(meta.controllerView.label, meta.controllerView.cite)) : [],
    sources: Object.values(meta.sources || {}).map((x) => P(x.text, ' ', C(x.label))),
    price: P([L(meta.price[k], priceLabel, 'ERCOT RTM SPP LZ_NORTH, the interval containing this minute'), { money: true, digits: 2, unit: '/MWh' }]),
    naiveChip: { label: 'ASSUMPTION', cite: nl.text || '' },
  };
}

/** The P1 price strip: REAL price, discharge plan, tier ribbon, hour ticks, cursor. Base image cached per key. */
export function drawP1Strip(canvas, { meta, doc, k, key }) {
  const r = canvas.getBoundingClientRect(); const dpr = window.devicePixelRatio || 1;
  const W = Math.max(1, Math.round(r.width * dpr)), H = Math.max(1, Math.round(r.height * dpr));
  const c = canvas.getContext('2d'); if (!c) return;
  const ck = `${key}|${W}x${H}`;
  if (canvas._hbKey !== ck) {
    canvas.width = W; canvas.height = H; const n = meta.steps;
    c.clearRect(0, 0, W, H);
    const ribbon = 11 * dpr, top = 40 * dpr, ph = H - ribbon - top - 14 * dpr; const xs = (i) => (i + 0.5) / n * W;
    c.fillStyle = 'rgba(236,131,90,0.16)';
    for (const [start, mins] of (meta.plan && meta.plan.discharge) || []) {
      const k0 = fmt.timeToStep(meta, start); if (k0 === null) continue;
      const k1 = Math.min(n, k0 + Math.round(mins * 60 / (meta.stepSeconds || 60))); c.fillRect(k0 / n * W, top, (k1 - k0) / n * W, ph);
    }
    const pmax = Math.max(1, ...meta.price), pmin = Math.min(0, ...meta.price);
    c.strokeStyle = '#101613'; c.lineWidth = 1.5 * dpr; c.beginPath();
    meta.price.forEach((p, i) => { const y = top + ph - (p - pmin) / (pmax - pmin) * ph; if (i) c.lineTo(xs(i), y); else c.moveTo(xs(i), y); });
    c.stroke();
    c.fillStyle = '#55625A'; c.font = `${10 * dpr}px Inter, sans-serif`; c.textAlign = 'right';
    c.fillText(`max $${pmax.toFixed(0)}/MWh (REAL price)`, W - 2 * dpr, top + 9 * dpr); c.textAlign = 'left';
    for (let i = 0; i < n; i++) {
      const cnt = countsAt(doc, i); let worst = 0;
      for (let q = 4; q >= 0; q--) if (cnt[q] > 0) { worst = q + 1; break; }
      if (!worst) continue;
      const tot = cnt.reduce((a, b) => a + b, 0); const t = SM.TIER_RGB[worst];
      c.fillStyle = `rgba(${t[0]},${t[1]},${t[2]},${Math.min(1, 0.35 + tot / 12)})`; c.fillRect(i / n * W, H - ribbon, Math.max(1, W / n + 0.5), ribbon);
    }
    c.fillStyle = '#55625A';
    for (let i = 0; i < n; i++) {
      const t = fmt.stepToTime(meta, i);
      if (t.endsWith(':00') && (n <= 180 || Number(t.slice(0, 2)) % 2 === 0)) { c.fillRect(xs(i), H - ribbon - 3 * dpr, dpr, 3 * dpr); c.fillText(t, xs(i) + 2 * dpr, H - ribbon - 3 * dpr); }
    }
    canvas._hbBase = c.getImageData(0, 0, W, H); canvas._hbKey = ck;
  }
  c.putImageData(canvas._hbBase, 0, 0);
  const x = (k + 0.5) / meta.steps * W; c.fillStyle = '#0B6B6F'; c.fillRect(x - dpr, 0, 2.5 * dpr, H);
}

// ---- captions (beats.json templates, facts from more.js) ----------------------------------------------------------
export async function captionParts(beatId, topology, { nav = false } = {}) {
  const beats = await getOptional('beats.json'); const list = Array.isArray(beats) ? beats : ((beats && beats.beats) || []);
  const i = list.findIndex((b) => b.id === beatId); if (i < 0) return null;
  const b = list[i]; const S = { topology };
  const pathOf = (key) => (key === 'p1meta' ? 'p1/meta.json' : key === 'p2index' ? 'p2/index.json' : key === 'engine' ? 'engine.json'
    : key.startsWith('p1:') ? `p1/${key.slice(3)}.json` : key.startsWith('p2:') ? `p2/${key.slice(3)}.json` : null);
  await Promise.all(sourcesFor([b.caption]).filter((s) => s !== 'topology').map(async (s) => { S[s] = pathOf(s) ? await getOptional(pathOf(s)) : null; }));
  const parts = []; const re = /\{\{\s*([^}]+?)\s*\}\}/g; let last = 0, m;
  while ((m = re.exec(b.caption))) {
    if (m.index > last) parts.push(T(b.caption.slice(last, m.index)));
    const [kind, ...rest] = m[1].split(':');
    if (kind === 'chip') parts.push(C(rest[0], rest.slice(1).join(':')));
    else {
      const fp = evalFact(m[1].trim(), S);
      if (!fp) parts.push(T('(not built yet)'));
      else for (const p of fp) parts.push(typeof p === 'string' ? T(p) : fmt.isLabelled(p) ? N(p, p.o || {}) : T(String(p)));
    }
    last = m.index + m[0].length;
  }
  if (last < b.caption.length) parts.push(T(b.caption.slice(last)));
  return { time: `${b.t0}–${b.t1}`, title: b.title, label: b.label || 'SIM', parts, prev: nav && list[i - 1] ? list[i - 1].title : '', next: nav && list[i + 1] ? list[i + 1].title : '' };
}

// ---- P2 ----------------------------------------------------------------------------------------------------------
export const POLICIES = [['aware', 'feeder-aware'], ['naive', 'naive']];
export const CLASSES = [['core', 'Core'], ['legacy', 'Legacy']];
export const RULES = [['d26', 'D-26 onset'], ['cheapest', 'cheapest hours']];
export const GROWTHS = [['0', 'today'], ['20', 'growth']];
export function parseCombo(id) { const m = /^([a-z]+)-([a-z]+)-([a-z0-9]+)-g(\d+)$/.exec(String(id || '')); return m ? { policy: m[1], cls: m[2], rule: m[3], growth: m[4] } : null; }
export const comboId = (c) => `${c.policy}-${c.cls}-${c.rule}-g${c.growth}`;
export const counterpart = (id) => { const c = parseCombo(id); return c ? comboId({ ...c, policy: c.policy === 'aware' ? 'naive' : 'aware' }) : null; };
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const monthName = (ym) => { const m = /^(\d{4})-(\d{2})$/.exec(String(ym || '')); return m ? `${MONTHS[+m[2] - 1]} ${m[1]}` : 'the month'; };
const tfNameP2 = (topology, i) => { const t = topology.transformers[i]; return !t ? `T-${i}` : t.focus ? `${t.focus} (T-${i})` : `T-${i}`; };
const homeLabelP2 = (topology, i) => (topology.homes[i] ? topology.homes[i].label : `home ${i}`);
const checked = (e) => !!(e && e.opendss && e.opendss.after && e.screening !== true);
function bulk(doc, key, v) {
  const s = doc.series && doc.series[key]; const label = s && s.label ? s.label : 'SIM';
  return s && s.by === 'surrogate' ? { v, label, cite: 'surrogate screen (sim.surrogate, calibrated vs OpenDSS); not OpenDSS-checked' } : { v, label };
}
function rankOf(doc, hi) { for (const e of (doc && doc.ranking) || []) if (e.home === hi || (e.alsoOnTf || []).includes(hi)) return e.rank; return null; }
function standingOutside(index, hi, tf, policy) {
  const mv = index.flip && Array.isArray(index.flip.movers) ? index.flip.movers.find((m) => m.home === hi) : null;
  const rank = mv ? (policy === 'naive' ? mv.rankNaive : mv.rankAware) : null;
  const br = Array.isArray(index.bridge) ? index.bridge.find((b) => b.tf === tf) : null;
  return { rank: fmt.isLabelled(rank) ? rank : null, bridge: br && br[policy] && br[policy].home === hi ? br[policy] : null };
}

export async function loadP2(combo) {
  const [index, topology, footprints, p1meta] = await Promise.all([getJSON('p2/index.json'), getJSON('topology.json'), getOptional('footprints.json'), getOptional('p1/meta.json')]);
  const ids = (index.combos || []).map((c) => (typeof c === 'string' ? c : c.id));
  const id = combo && ids.includes(combo) ? combo : index.default;
  const oc = ids.includes(counterpart(id)) ? counterpart(id) : null;
  const [doc, other] = await Promise.all([getJSON(`p2/${id}.json`), oc ? getJSON(`p2/${oc}.json`) : null]);
  return { index, topology, footprints, p1meta, combo: id, otherCombo: oc, doc, other };
}

function counterfactual({ entry, doc, index, topology, combo }) {
  const c = parseCombo(combo) || {}; const tname = tfNameP2(topology, entry.tf); const month = monthName(index.month);
  const od = checked(entry) ? entry.opendss : null; const B = od && od.before ? od.before : entry.before; const A = od ? od.after : entry.after;
  const beforeH = B && B.h100 ? B.h100 : bulk(doc, 'baseline', doc.baseline.h100[entry.tf]);
  const beforePeak = B && B.peakPct ? B.peakPct : bulk(doc, 'baseline', doc.baseline.peak[entry.tf] / 10);
  const cls = (CLASSES.find(([k]) => k === c.cls) || [0, c.cls])[1];
  const pol = c.policy === 'naive' ? 'naive dispatch (no feeder check)' : 'feeder-aware dispatch';
  const d = entry.driver && entry.driver.profile ? entry.driver : null; const shared = d ? sharedNames(d.sharedWith) : [];
  const out = [];
  if (typeof beforeH.v === 'number' && beforeH.v > 0) {
    out.push(`In ${month} transformer ${tname} spent `, [beforeH, { unit: ' h', digits: 2 }], ' above nameplate without a new battery (peak ', [beforePeak, { unit: '%', digits: 1 }], ')');
    if (d) out.push(`, driven by one home's load, ${d.label || 'one home'} (SMART-DS profile ${d.profile}${shared.length ? `, the same profile as ${shared.join(', ')}: one shape, not independent evidence` : ''})`);
    out.push('. ');
  } else out.push(`In ${month} transformer ${tname} stayed at or below nameplate without a new battery (peak `, [beforePeak, { unit: '%', digits: 1 }], '). ');
  out.push(`With a ${cls} at ${homeLabelP2(topology, entry.home)} under ${pol}${od ? ' (OpenDSS month run)' : ''}: `);
  if (A && A.h100) out.push([A.h100, { unit: ' h', digits: 2 }], ' above nameplate, ');
  const pk = od && A && A.peakPct ? A.peakPct : entry.peakWithPct; if (pk) out.push('peak ', [pk, { unit: '%', digits: 1 }], ', ');
  if (entry.revenueUSD) out.push('August energy value ', [entry.revenueUSD, { money: true, digits: 0 }]);
  if (entry.curtailKWh && entry.curtailKWh.v > 0) out.push(', curtailed ', [entry.curtailKWh, { unit: ' kWh', digits: 0 }]);
  out.push('.');
  if (entry.noNewViolation && entry.noNewViolation.v === false) out.push(' It adds a new violation: where NOT to put it.');
  else if (entry.stressAvoidedH && entry.stressAvoidedH.v > 0) out.push(' It avoids ', [entry.stressAvoidedH, { unit: ' h', digits: 2 }], ' of stress on its transformer.');
  if (entry.protectionWith && entry.protectionWith.v === true) out.push(' Protection may operate here (ASSUMPTION rule).');
  return P(...out);
}

const METRICS = { noNewViolation: ['adds no new violation', {}], peakWithPct: ['peak with the battery', { unit: '%', digits: 1 }], stressAvoidedH: ['stress avoided', { unit: ' h', digits: 2 }],
  stressAddedH: ['stress added', { unit: ' h', digits: 2 }], reliefKWh: ['energy shaved above nameplate', { unit: ' kWh', digits: 1 }], revenueUSD: ['August energy value', { money: true, digits: 0 }],
  curtailKWh: ['curtailed', { unit: ' kWh', digits: 0 }], protectionWith: ['protection operates (ASSUMPTION rule)', {}] };

export function p2View(st, homeId, n) {
  const { index, topology, doc, other, combo, otherCombo, p1meta } = st;
  const cur = parseCombo(combo);
  const seg = (key, opts, labelFor) => opts.map(([k, t]) => ({ id: comboId({ ...cur, [key]: k }), text: labelFor ? labelFor(k, t) : t, on: cur[key] === k }));
  const cst = (d, name) => { const c = d && d.constants && d.constants[name]; return c && typeof c.value === 'number' ? { v: c.value, label: c.label, cite: c.cite } : null; };
  const controls = [
    { name: 'policy', opts: seg('policy', POLICIES) },
    { name: 'battery', opts: seg('cls', CLASSES, (k, t) => { const c = cst(doc, k === 'core' ? 'CORE_POWER_KW' : 'LEGACY_POWER_KW'); return c ? `${t} ${fmt.fmtValue(c, { unit: ' kW' })}` : t; }) },
    { name: 'charge rule', opts: seg('rule', RULES) },
    { name: 'load', opts: seg('growth', GROWTHS, (k, t) => { const g = cst(doc, 'GROWTH') || cst(index, 'GROWTH'); return k !== '0' && g ? `+${fmt.fmtValue({ ...g, v: g.v * 100 }, { digits: 0 })}% ${t}` : t; }) },
  ];
  const aware = cur.policy === 'aware' ? doc : other, naive = cur.policy === 'naive' ? doc : other;

  // selection
  const hi = homeId ? topology.homes.findIndex((h) => h.id === homeId) : -1;
  let entry = null;
  if (hi >= 0) entry = (doc.ranking || []).find((e) => e.home === hi || (e.alsoOnTf || []).includes(hi)) || null;
  else entry = (doc.ranking || [])[0] || null;
  const selHome = entry ? entry.home : hi;

  // referee
  const ref = index.referee;
  const referee = !ref ? null : !ref.runs ? { ok: false, parts: [T('OpenDSS referee: not run yet for this build. Every number here is screening (surrogate).')] }
    : { ok: true, parts: P(`OpenDSS referee: ${ref.runs} month runs · surrogate error p99 `, ref.errorPts && ref.errorPts.p99 ? [ref.errorPts.p99, { digits: 2, unit: ' pts' }] : 'n/a',
      ' (max ', ref.errorPts && ref.errorPts.max ? [ref.errorPts.max, { digits: 2, unit: ' pts' }] : 'n/a', ') · tier agreement ', ref.tierAgreementPct ? [ref.tierAgreementPct, { digits: 1, unit: '%' }] : 'n/a') };

  // handoff from P1
  const handoff = ((p1meta && p1meta.unrelieved) || []).map((u) => {
    const br = (index.bridge || []).find((x) => x.tf === u.tf); const bp = br && br[cur.policy]; const Pp = { unit: '%', digits: 1 };
    return { tf: tfNameP2(topology, u.tf), homeId: bp && topology.homes[bp.home] ? topology.homes[bp.home].id : null,
      parts: P(`${u.reason || 'unrelieved'}.`, bp && fmt.isLabelled(bp.peakWithPct) ? ` A new battery here (${bp.label || homeLabelP2(topology, bp.home)}, rank ${bp.rank} under this policy): month peak ` : '',
        bp && bp.peakWithoutPct ? [bp.peakWithoutPct, Pp] : null, bp && fmt.isLabelled(bp.peakWithPct) ? ' without, ' : '', bp && fmt.isLabelled(bp.peakWithPct) ? [bp.peakWithPct, Pp] : null, bp && fmt.isLabelled(bp.peakWithPct) ? ' with.' : '') };
  });

  // flip
  const f = index.flip || {}; const v = flipVerdict(f); const ov = f.top10Overlap, sp = f.spearman, un = f.untied || {};
  const movers = (Array.isArray(f.movers) ? f.movers : []).filter((m) => fmt.isLabelled(m.rankNaive) && fmt.isLabelled(m.rankAware)).slice(0, 5)
    .map((m) => P(`${m.label || homeLabelP2(topology, m.home)} on ${tfNameP2(topology, m.tf)}: naive rank `, [m.rankNaive], ' → feeder-aware rank ', [m.rankAware]));
  const flip = ov ? {
    overlap: N(ov), supports: v.supports, headline: v.supports ? v.headline : `The two rankings overlap by the number above; the flip is ${ov.v >= 10 ? 'not seen' : 'partial'} in this data.`,
    stats: P('Spearman ', sp ? [sp, { digits: 2 }] : 'n/a', un.top10Overlap ? ' · untied candidates only: overlap ' : '', un.top10Overlap ? [un.top10Overlap] : null,
      un.spearman ? ', Spearman ' : '', un.spearman ? [un.spearman, { digits: 2 }] : null),
    movers, rule: P(`Headline rule: shown only when the two top tens share at most ${FLIP_HEADLINE_MAX_OVERLAP} homes (display rule `, C('ASSUMPTION', 'FLIP_HEADLINE_MAX_OVERLAP'), ').'),
  } : null;

  // candidate card
  let card = null;
  if (entry) {
    const t = topology.transformers[entry.tf];
    const metrics = Object.keys(METRICS).filter((k) => fmt.isLabelled(entry[k])).map((k) => ({ name: METRICS[k][0], parts: [N(entry[k], METRICS[k][1])] }));
    const oRank = other ? rankOf(other, entry.home) : null; const oc = parseCombo(otherCombo) || {};
    let oWhere = oRank ? [T(`rank ${oRank}`)] : [T('not in its top 50')];
    if (!oRank && otherCombo) { const so = standingOutside(index, entry.home, entry.tf, oc.policy); if (so.rank) oWhere = P('rank ', [so.rank], ' (one entry per transformer)'); }
    const odss = checked(entry) ? ['before', 'after'].map((w) => ({ name: w === 'before' ? 'without the battery' : 'with the battery',
      parts: P(entry.opendss[w].peakPct ? 'peak ' : '', entry.opendss[w].peakPct ? [entry.opendss[w].peakPct, { unit: '%', digits: 1 }] : null, entry.opendss[w].h100 ? ' · above nameplate ' : '', entry.opendss[w].h100 ? [entry.opendss[w].h100, { unit: ' h', digits: 2 }] : null) })) : [];
    card = {
      title: `#${entry.rank} ${homeLabelP2(topology, entry.home)} · ${tfNameP2(topology, entry.tf)} · ${t.kva} kVA`, checked: checked(entry), screening: !checked(entry),
      reason: entry.reason || '', cf: counterfactual({ entry, doc, index, topology, combo }), metrics, odss, hasOdss: odss.length > 0,
      also: (entry.alsoOnTf || []).length ? `Same transformer, identical in the screening model: ${entry.alsoOnTf.map((i) => homeLabelP2(topology, i)).join(', ')}. The lowest id is shown.` : '',
      toggle: otherCombo ? [T(`Managed ${oc.policy === 'naive' ? 'naively' : 'feeder-aware'} instead: `), ...oWhere] : [], otherCombo, homeId: topology.homes[entry.home] ? topology.homes[entry.home].id : null,
      strips: doc.strips && doc.strips[String(entry.tf)] ? doc.strips[String(entry.tf)] : null,
    };
  } else if (hi >= 0) {
    const h = topology.homes[hi];
    card = { title: `${h.label} · ${tfNameP2(topology, h.tf)}`, reason: h.battery ? 'This home already has a battery.' : "Not in this combo's top 50.", cf: P("Its transformer's month peak without a new battery: ", [bulk(doc, 'baseline', doc.baseline.peak[h.tf] / 10), { unit: '%', digits: 1 }], '.'), metrics: [], odss: [], toggle: [], strips: null };
  }

  // ranking + greedy
  const e0 = (doc.ranking || [])[0] || {};
  const rankCols = [{ label: '#' }, { label: 'home' }, { label: 'transformer' }, { label: 'peak with, %', chip: C(e0.peakWithPct ? e0.peakWithPct.label : 'SIM', 'OpenDSS on ● rows, screening on ○ rows'), num: true },
    { label: 'stress avoided, h', chip: C(e0.stressAvoidedH ? e0.stressAvoidedH.label : 'SIM', e0.stressAvoidedH && e0.stressAvoidedH.cite), num: true },
    { label: 'August value', chip: C(e0.revenueUSD ? e0.revenueUSD.label : 'DERIVED', e0.revenueUSD && e0.revenueUSD.cite), num: true }, { label: '' }];
  const rankRows = (doc.ranking || []).slice(0, 15).map((e) => {
    const pk = checked(e) && e.opendss.after.peakPct ? e.opendss.after.peakPct : e.peakWithPct;
    return { homeId: topology.homes[e.home] ? topology.homes[e.home].id : '', on: entry && entry.rank === e.rank, viol: !!(e.noNewViolation && e.noNewViolation.v === false),
      cells: [String(e.rank), homeLabelP2(topology, e.home), tfNameP2(topology, e.tf), pk ? fmt.fmtValue(pk, { digits: 1 }) : 'n/a',
        e.stressAvoidedH ? fmt.fmtValue(e.stressAvoidedH, { digits: 2 }) : 'n/a', e.revenueUSD ? fmt.fmtValue(e.revenueUSD, { money: true, digits: 0 }) : 'n/a', checked(e) ? '●' : '○'] };
  });
  const g = (doc.greedy || []).slice(0, n); const g0 = g[0] && g[0].feeder && g[0].feeder.normalTfs;
  const greedyCols = [{ label: 'k' }, { label: 'home' }, { label: 'transformer' }, { label: 'tfs with a normal-tier event', chip: g0 ? C(g0.label, g0.cite) : null, num: true },
    { label: 'emergency tfs', chip: g0 ? C(g0.label, g0.cite) : null, num: true }, { label: 'h above normal rating', chip: g0 ? C(g0.label, g0.cite) : null, num: true }];
  const greedyRows = g.map((x) => ({ homeId: topology.homes[x.home] ? topology.homes[x.home].id : '', cells: [String(x.k), homeLabelP2(topology, x.home), tfNameP2(topology, x.tf),
    x.feeder && x.feeder.normalTfs ? fmt.fmtValue(x.feeder.normalTfs) : 'n/a', x.feeder && x.feeder.emergencyTfs ? fmt.fmtValue(x.feeder.emergencyTfs) : 'n/a', x.feeder && x.feeder.h110 ? fmt.fmtValue(x.feeder.h110, { digits: 1 }) : 'n/a'] }));

  // capacity + insight
  const u = index.usefulCapacity;
  const capacity = u ? { naive: u.naive ? N(u.naive) : T('n/a'), aware: u.aware ? N(u.aware) : T('n/a'), naiveStop: u.naive && u.naive.stop ? `stops: ${u.naive.stop}` : '', awareStop: u.aware && u.aware.stop ? `stops: ${u.aware.stop}` : '' } : null;
  const ins = index.insight; let insight = null;
  if (ins && Array.isArray(ins.tfPeakHour)) {
    const hh = (i) => `${String(i).padStart(2, '0')}:00`; const mt = modeIndex(ins.tfPeakHour), mp = modeIndex(ins.priceMaxHour);
    const nT = ins.tfPeakHour.reduce((s, x) => s + x, 0), nP = (ins.priceMaxHour || []).reduce((s, x) => s + x, 0);
    insight = mt !== null && mp !== null ? P(`Transformers most often hit their monthly peak at ${hh(mt)} `, [L(ins.tfPeakHour[mt], 'SIM')], ' of ', [L(nT, 'SIM')], `; the day's highest price most often falls at ${hh(mp)} `, [L(ins.priceMaxHour[mp], 'REAL')], ' of ', [L(nP, 'REAL')], ' days.', mt !== mp ? ' A market-only dispatcher saves its energy for the price peak and leaves the load peak alone.' : '') : [T('Not computed yet.')];
  }
  return {
    subtitle: P(`${monthName(index.month)} what-if · prices `, C('REAL', 'ERCOT RTM SPP LZ_NORTH 15-min'), ' · loads SMART-DS 2018, same calendar date ', C('SIM'), ' ', C('ASSUMPTION', '2018 weather-year load paired with 2026 prices by calendar date')),
    controls, isNaive: cur.policy === 'naive', referee, hasReferee: !!referee, handoff, hasHandoff: handoff.length > 0, p1day: (p1meta && p1meta.day) || 'the P1 day',
    flip, hasFlip: !!flip, card, hasCard: !!card, rankCols, rankRows, greedyCols, greedyRows, hasGreedy: greedyRows.length > 0, capacity, hasCapacity: !!capacity, insight, hasInsight: !!insight,
    selHome, entry, aware, naive, n,
  };
}

export function p2Charts(st, view) {
  const out = {}; const { doc, index } = st; const s = view.card && view.card.strips;
  const lab = (doc.series && doc.series.strips && doc.series.strips.label) || 'SIM';
  if (s) {
    out.heatWithout = chartHTML('heat', { values: s.without, label: lab, caption: 'Without the battery: hourly max loading, by day and hour', captionTop: true, title: 'without' });
    out.heatWith = chartHTML('heat', { values: s.with, label: lab, caption: 'With the battery', captionTop: true, title: 'with' });
    if (s.peakDay && Array.isArray(s.peakDay.without)) out.peakDay = chartHTML('line', {
      series: [{ name: 'without', values: s.peakDay.without.map((x) => x / 10), cls: 's-without' }, { name: 'with', values: (s.peakDay.with || []).map((x) => x / 10), cls: 's-with' }],
      refs: [{ y: 100, text: 'nameplate', cls: 'r-amber' }, { y: 110, text: 'normal', cls: 'r-normal' }, { y: 150, text: 'emergency', cls: 'r-emerg' }],
      xTicks: [0, 24, 48, 72].map((i) => ({ i, text: `${String(i / 4).padStart(2, '0')}:00` })), unit: '%', label: lab, title: 'peak day',
      caption: `Peak day ${s.peakDay.day || ''}: loading without (grey) and with (accent) the battery, % of nameplate` });
  }
  const ins = index.insight;
  if (ins && Array.isArray(ins.tfPeakHour)) {
    const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
    out.tfHour = chartHTML('bar', { categories: hours, series: [{ name: 'transformers', values: ins.tfPeakHour, cls: 's-with' }], label: 'SIM', xLabelEvery: 3, height: 90, caption: "Hour of each transformer's monthly peak loading (SMART-DS 2018 shapes)", title: 'transformer peak hour' });
    out.priceHour = chartHTML('bar', { categories: hours, series: [{ name: 'days', values: ins.priceMaxHour || [], cls: 's-price' }], label: 'REAL', xLabelEvery: 3, height: 90, caption: "Hour of each August day's maximum LZ_NORTH price", title: 'price max hour' });
  }
  if (Array.isArray(index.price)) out.price = chartHTML('price', { price: index.price, label: 'REAL', caption: `ERCOT RTM LZ_NORTH, ${index.month}, 15-minute settlement prices`, title: 'august prices', height: 60 });
  return out;
}

export function p2SceneModel(st, view) {
  const { topology, doc } = st;
  const pins = (doc.ranking || []).slice(0, 10).filter((e) => topology.homes[e.home]).map((e) => ({ home: e.home, text: `#${e.rank}` }));
  const placed = (doc.greedy || []).slice(0, view.n).filter((x) => topology.homes[x.home]).map((x) => ({ home: x.home, k: x.k }));
  const model = SM.buildSceneModel({ topology, footprints: st.footprints, frame: SM.frameFromP2(doc), view: 'p2', theme: 'light', pins, placed });
  model.labels = model.labels || []; model.batteries = model.batteries || [];
  if (!model.labels.some((l) => l.pin)) for (const p of pins) model.labels.push({ key: 'pin', text: p.text, position: topology.homes[p.home].lonlat, color: [16, 22, 19], pin: true, home: p.home });
  if (!model.batteries.some((b) => b.placed)) for (const p of placed) { const h = topology.homes[p.home]; model.batteries.push({ j: -1, home: p.home, position: [h.lonlat[0] + 0.00012, h.lonlat[1]], height: 30, soc: 0.9, kw: 0, state: 'N', color: [11, 107, 111, 255], placed: true }); }
  return model;
}

/** Create the deck.gl scene, falling back to the 2D canvas when WebGL2 is missing. */
export async function createScene(el, topology, onError) {
  try { const m = await import('./lib/scene3d.js'); return m.createScene(el, { topology, theme: 'light', onError }); }
  catch (e) { el.innerHTML = ''; const f = await import('./lib/fallback2d.js'); return f.createScene(el, { topology, theme: 'light', onError }); }
}
