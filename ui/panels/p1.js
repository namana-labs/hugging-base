// ui/panels/p1.js (L4): the P1 view, "where to charge". Build prompt 5.5.
//   mount(el, ctx) -> Promise   resolves after the panel's first render and ctx.scene.update(...)
//   ctx = {topology, footprints, link, scene, data, fmt, sceneModel, theme, reportError, href(patch), go(patch)}
// What it shows (1080p first; one big number per beat):
//   - the branch toggle (naive carries its ASSUMPTION framing), the clock, and the big number: the worst service
//     transformer right now (OpenDSS, SIM) with the tier counts;
//   - A-D (+ T-240) headroom gauges: home load (grey) + battery kW (accent; relief hatched) against 100% of nameplate,
//     ticks at 110% / 150% and the fuse rule's 200% (ASSUMPTION), the OpenDSS loading, room to nameplate (DERIVED)
//     and the evening's fuse margin;
//   - the orchestrator ticker, the failure events (aware_faults), the relief beat with its `driver`, the unrelieved
//     transformers handed to P2, the grid checks (voltage, feeder head), the branch summary, money, scale ladder,
//     what the controller sees, and sources;
//   - over the scene: camera presets, a legend (three tiers + protection, battery and home states), credits, and the
//     transport (play, 0.5x-8x, 1 simulated minute per 100 ms at 1x) with the REAL price strip, a tier-count ribbon,
//     data-computed markers and a scrubber.
// Every number on screen is a labelled value (format.js throws on a bare one) or a bulk value shown with its
// series label. Tiers, runs and protection come from the JSON; nothing here re-derives them.

export const BRANCH_NAMES = { none: 'no batteries', naive: 'naive', aware: 'feeder-aware', aware_faults: 'aware + failures' };
export const NAIVE_FRAMING = 'ERCOT dispatches one number per zone and does not check feeders (REAL). The naive branch splits that number with no feeder check, all at once at the onset (ASSUMPTION: Base\'s real split is not public; build prompt 12 Q5). Base may not charge this way today.';
export const SPEEDS = [0.5, 1, 2, 4, 8];
export const MS_PER_STEP = 100;          // 1 simulated minute per 100 ms at 1x (build prompt 5.5)
export const GAUGE_MAX_PCT = 220;        // the gauge's full width
export const MARK_CHARS = 34;            // strip marker labels are cut here (the full text is the tooltip and the list)
export const LABEL_BAND_PX = 40;         // three rows of marker labels above the price line

const FOCUS_KEYS = ['A', 'B', 'C', 'D', '240'];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const L = (v, label, cite, extra) => ({ v, label, ...(cite ? { cite } : {}), ...(extra || {}) });
let nvFmt = null;
/** A labelled number's value (format.js throws on a bare one), for lines that carry one chip for all their numbers. */
const nv = (x, opts) => `<span class="num">${esc(nvFmt.fmtValue(x, opts))}</span>`;

/** Minutes either side of a driver's 15-minute interval in which the hero names it (the interval interpolated to 1 min). */
export const DRIVER_WINDOW_MIN = 15;

/**
 * The `driver` behind transformer `tf` at step `k`, or null: `meta.relief` (A's spike) or a `meta.unrelieved` entry
 * (T-240) whose peak is within DRIVER_WINDOW_MIN of k. Used so the hero names one home's spike, and its shared
 * SMART-DS profile, whenever it shows that spike as the worst service transformer (build prompt 4.2, 5.3).
 */
export function spikeDriverAt(meta, fmt, tf, k) {
  const near = (step) => Number.isInteger(step) && Math.abs(k - step) <= DRIVER_WINDOW_MIN * 60 / (meta.stepSeconds || 60);
  const r = meta.relief;
  if (r && r.tf === tf && r.driver) {
    const step = Number.isInteger(r.step) ? r.step : (r.t ? fmt.timeToStep(meta, r.t) : null);
    if (near(step)) return { kind: 'relief', tf, t: r.t, driver: r.driver };
  }
  for (const u of meta.unrelieved || []) {
    if (u.tf !== tf || !u.driver) continue;
    const t = (u.peak && u.peak.t) || null;
    if (t && near(fmt.timeToStep(meta, t))) return { kind: 'unrelieved', tf, t, driver: u.driver };
  }
  return null;
}

/** One line for the hero: whose spike it is, its SMART-DS profile, and where else the same profile is used. */
export function driverLineHTML(fmt, info, homeLabel) {
  if (!info) return '';
  const d = info.driver;
  const shared = d.sharedWith && d.sharedWith.length ? `; the same profile is used at ${esc(d.sharedWith.map(homeLabel).join(', '))}, so it is not independent evidence` : '';
  const kw = d.kwAtPeak && fmt.isLabelled(d.kwAtPeak) ? ` (${fmt.fmtHTML(d.kwAtPeak, { unit: ' kW', digits: 1 })} at ${esc(info.t || '')})` : '';
  const what = info.kind === 'unrelieved' ? 'home load only, no battery here: ' : '';
  return `<div class="p1-driver p1-hero-driver">${what}one home's 15-minute spike: ${esc(d.label || homeLabel(d.home))}, SMART-DS profile <code>${esc(d.profile || '')}</code>${kw}${shared}.</div>`;
}

/** The label of a bulk series in a branch doc (the envelope's `series`), defaulting to SIM. */
export function seriesLabel(doc, name, dflt = 'SIM') {
  const s = doc && doc.series && doc.series[name];
  return s && s.label ? s.label : dflt;
}

/** The step to open at: the link's t, else 30 minutes after the D-26 onset, else the middle of the window. */
export function initialStep(meta, link, fmt) {
  if (link && link.t) {
    const k = fmt.timeToStep(meta, link.t);
    if (k !== null) return k;
  }
  if (meta.plan && meta.plan.onset) {
    const k = fmt.timeToStep(meta, meta.plan.onset);
    if (k !== null) return Math.min(meta.steps - 1, k + Math.round(30 * 60 / (meta.stepSeconds || 60)));
  }
  return Math.floor(meta.steps / 2);
}

/** The worst service transformer at step k: {pct, tf, code}. */
export function worstAt(doc, k) {
  const row = doc.loading[k];
  let best = -1, tf = 0;
  for (let i = 0; i < row.length; i++) if (row[i] > best) { best = row[i]; tf = i; }
  return { pct: best / 10, tf, code: Number(doc.tier[k][tf]) };
}

/** Transformers per tier code 1..5 at step k (from `counts`, else counted from the tier string). */
export function countsAt(doc, k) {
  if (doc.counts && doc.counts[k]) return doc.counts[k].slice(0, 5);
  const c = [0, 0, 0, 0, 0];
  for (const ch of doc.tier[k]) { const n = Number(ch); if (n >= 1 && n <= 5) c[n - 1] += 1; }
  return c;
}

/** Battery states at step k: {C, D, I, S, X, B} counts. */
export function stateCounts(doc, k) {
  const c = { C: 0, D: 0, I: 0, S: 0, X: 0, B: 0 };
  for (const ch of doc.state[k]) if (ch in c) c[ch] += 1;
  return c;
}

/** The last n ticker lines at or before step k, newest first. */
export function tickerAt(doc, k, n = 6) {
  const out = [];
  const t = doc.ticker || [];
  for (let i = t.length - 1; i >= 0 && out.length < n; i--) if (t[i][0] <= k) out.push(t[i]);
  return out;
}

/** Transformer-level evening stats from the committed arrays (display only; tiers come from the JSON):
 *  max loading and when, and minutes at tier codes 2-4 (above 110%) and 4 (above 150%). */
export function tfEvening(doc, tf, stepSeconds = 60) {
  let max = -1, at = 0, n110 = 0, n150 = 0, open = -1;
  for (let k = 0; k < doc.loading.length; k++) {
    const v = doc.loading[k][tf];
    if (v > max) { max = v; at = k; }
    const c = Number(doc.tier[k][tf]);
    if (c >= 2 && c <= 4) n110 += 1;
    if (c === 4) n150 += 1;
    if (c === 5 && open < 0) open = k;
  }
  const m = stepSeconds / 60;
  return { maxPct: max / 10, maxStep: at, min110: n110 * m, min150: n150 * m, openStep: open };
}

/** The gauge for one focus transformer at step k. Percent-of-nameplate splits use kW / kVA (DERIVED). */
export function gaugeModel(meta, doc, topology, key, k, roomKW) {
  const f = doc.focus && doc.focus[key];
  if (!f) return null;
  const tf = f.tf;
  const t = topology.transformers[tf];
  const kva = t.kva;
  const pct = doc.loading[k][tf] / 10;
  const code = Number(doc.tier[k][tf]);
  const homeKW = f.homeKW[k] / 10, batKW = f.batKW[k] / 10;
  const ev = tfEvening(doc, tf, meta.stepSeconds || 60);
  const batteries = (topology.fleet || []).filter((hi) => topology.homes[hi].tf === tf).length;
  return {
    key, tf, id: t.id, kva, homes: t.homes.length, batteries, pct, code, homeKW, batKW,
    homePct: 100 * homeKW / kva, batPct: 100 * batKW / kva,
    room: roomKW(kva, pct, homeKW + batKW), open: code === 5, ...ev,
  };
}

/** x-position (0..1) of each step's markers: meta.markers, the D-26 onset, and the branch's fault events. */
export function stripMarks(meta, branch, fmt, homeLabel = null) {
  const out = [];
  // a marker that restates a failure event belongs to that event's branch only (never "C runs hot" on aware)
  const evKey = (e) => `${e.t}|${e.text || ''}`;
  const otherEvents = new Set(), ownEvents = new Set();
  for (const [b, list] of Object.entries(meta.events || {})) for (const e of list || []) (b === branch ? ownEvents : otherEvents).add(evKey(e));
  const seenText = new Map();
  for (const m of meta.markers || []) {
    const key = `${m.t}|${m.text}`;
    if (otherEvents.has(key) || ownEvents.has(key)) continue;
    const k = fmt.timeToStep(meta, m.t);
    if (k === null) continue;
    const first = !seenText.has(m.text);
    if (first) seenText.set(m.text, { n: 0 });
    seenText.get(m.text).n += 1;
    out.push({ k, t: m.t, text: m.text, label: m.label || 'SIM', kind: 'marker', repeat: !first, group: seenText.get(m.text) });
  }
  const ev = (meta.events && meta.events[branch]) || [];
  for (const e of ev) out.push({ k: e.step, t: e.t, text: e.text || faultText(e, homeLabel), label: 'SIM', kind: 'fault', group: { n: 1 } });
  out.sort((a, b) => a.k - b.k);
  // label rows: identical texts are labelled once ("x5"); labels that would collide drop to the next row (3 rows)
  const rowEnd = [-1, -1, -1];
  const n = meta.steps || 1;
  for (const m of out) {
    m.count = m.group.n;
    delete m.group;
    m.row = -1;
    if (m.repeat) continue;
    const x = (m.k + 0.5) / n, w = (m.t.length + 1 + Math.min(m.text.length, MARK_CHARS) + (m.count > 1 ? 3 : 0) + 6) * 0.0054;
    for (let r = 0; r < rowEnd.length; r++) if (x > rowEnd[r]) { m.row = r; rowEnd[r] = x + w; break; }
  }
  return out;
}

export function faultText(e, homeLabel) {
  const who = e.home !== undefined && e.home !== null ? (homeLabel ? homeLabel(e.home) : `home ${e.home}`)
    : e.tf !== undefined && e.tf !== null ? `transformer ${e.tf}` : '';
  if (e.kind === 'comms_lost') return `comms lost: ${who}`;
  if (e.kind === 'hot') return `runs hot: ${who}`;
  if (e.kind === 'stall') return 'our controller stalls';
  return `${e.kind}${who ? ': ' + who : ''}`;
}

const NAMES = {
  normalEvents: 'Normal-tier events (>110% for >= 30 min)', emergencyTfs: 'Transformers in emergency (>150%)',
  batteryCausedNormal: 'Battery-caused normal-tier events', batteryCausedEmergency: 'Battery-caused emergency events',
  batteryCausedAmberMin: 'Battery-caused minutes over nameplate', homeOnlyOver100: 'Home-load-only transformers over nameplate',
  protectionOperated: 'Protection operated (fuse rule, ASSUMPTION)', homesDark: 'Homes dark', homesOnBattery: 'Homes lit by their own battery',
  maxLoading: 'Worst service transformer', reserveBreaches: '20% reserve breaches', chargedPctBy0400: 'Fleet charged by 04:00',
  energyValueUSD: 'Energy value (gross, not Base\'s P&L)', costOfAwareness: 'Cost of awareness (naive minus aware)',
  vMinHome: 'Minimum service voltage', homesBelow095: 'Homes below 0.95 pu', feederHead: 'Feeder head (first primary cable)',
  reliefKW: 'Relief', reliefKWh: 'Relief energy', minutesOver100: 'Minutes over nameplate',
};
export function humanKey(k) {
  if (NAMES[k]) return NAMES[k];
  const s = String(k).replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Format options for a labelled value from its key name. */
export function optsFor(key) {
  const k = String(key);
  if (/usd|dollar|\$|value$/i.test(k) && !/pct/i.test(k)) return { money: true, digits: 2 };
  if (/pct|loading|percent|share/i.test(k)) return { unit: '%' };
  if (/kwh/i.test(k)) return { unit: ' kWh', digits: 1 };
  if (/kw$/i.test(k)) return { unit: ' kW', digits: 1 };
  if (/min(utes)?$/i.test(k) || /Min$/.test(k)) return { unit: ' min' };
  return {};
}

const ID_KEYS = new Set(['rank', 'home', 'tf', 'step', 'k', 'n', 'index', 'of', 'runs', 'minute', 'seq', 'batt']);

/** Generic HTML for a labelled tree (money, scale ladder, anything L2 adds): labelled values get their chip,
 *  strings are text, id counters are plain, and a bare number anywhere else throws (format.js), raising data-errors. */
export function labelledTreeHTML(fmt, x, key = '', depth = 0, inherit = '') {
  if (x === null || x === undefined) return '';
  let own = Object.keys(optsFor(key)).length ? key : inherit;   // children inherit the parent's unit (energyValueUSD.naive)
  if (x && typeof x === 'object' && !Array.isArray(x) && typeof x.unit === 'string' && x.unit.includes('$')) own = 'USD';
  if (typeof x === 'string') return `<span class="p1-text">${esc(x)}</span>`;
  if (typeof x === 'boolean') return esc(x ? 'yes' : 'no');
  if (typeof x === 'number') {
    if (ID_KEYS.has(key)) return esc(String(x));
    return fmt.fmtHTML(x);            // throws: a bare headline number is a contract bug
  }
  if (Array.isArray(x)) {
    if (x.every((v) => typeof v === 'string')) return `<span class="p1-text">${esc(x.join(', '))}</span>`;
    if (x.every((v) => isLabelledRecord(fmt, v))) return `<ul class="p1-tree">${x.map((v) => `<li>${recordHTML(fmt, v)}</li>`).join('')}</ul>`;
    return `<ul class="p1-tree">${x.map((v) => `<li>${labelledTreeHTML(fmt, v, key, depth + 1, own)}</li>`).join('')}</ul>`;
  }
  if (isLabelledRecord(fmt, x)) return recordHTML(fmt, x);
  if (fmt.isLabelled ? fmt.isLabelled(x) : ('v' in x && 'label' in x)) {
    const extras = Object.entries(x).filter(([k]) => !['v', 'label', 'cite'].includes(k))
      .map(([k, v]) => `${esc(humanKey(k))} ${labelledTreeHTML(fmt, v, k, depth + 1)}`).join(' · ');
    return `${fmt.fmtHTML(x, optsFor(own))}${extras ? ` <span class="hb-sub">${extras}</span>` : ''}`;
  }
  const rows = Object.entries(x).map(([k, v]) =>
    `<div class="p1-row"><span class="p1-k">${esc(humanKey(k))}</span><span class="p1-v">${labelledTreeHTML(fmt, v, k, depth + 1, own)}</span></div>`);
  return `<div class="p1-tree-obj depth-${depth}">${rows.join('')}</div>`;
}

/** A record with a label but no `v`: {text, label, cite} or {who, for, label, cite}: its strings, then one chip. */
export function isLabelledRecord(fmt, x) {
  return !!x && typeof x === 'object' && !Array.isArray(x) && !('v' in x) && fmt.LABELS.includes(x.label)
    && Object.entries(x).every(([k, v]) => k === 'label' || k === 'cite' || typeof v === 'string');
}
export function recordHTML(fmt, x) {
  const parts = Object.entries(x).filter(([k]) => k !== 'label' && k !== 'cite').map(([, v]) => v);
  return `<span class="p1-text">${esc(parts.join(': '))}</span> ${fmt.chip(x.label, x.cite)}`;
}

/** The money card (build prompt 5.4.6), each line labelled; unknown keys fall through to the generic tree.
 *  Local relief is never priced here, and the system-capacity band is applied only to fleet kW at the price peak. */
export function moneyHTML(fmt, money, branch, branchNames = BRANCH_NAMES, consts = null) {
  if (!money) return '';
  const done = new Set();
  const out = [];
  const row = (k, v) => `<div class="p1-row"><span class="p1-k">${k}</span><span class="p1-v">${v}</span></div>`;
  const usd = (x) => fmt.fmtHTML(x, { money: true, digits: 2 });
  if (money.energyValueUSD && typeof money.energyValueUSD === 'object' && !fmt.isLabelled(money.energyValueUSD)) {
    done.add('energyValueUSD');
    out.push(`<div class="p1-money-h">Energy value this evening <span class="hb-sub">(gross energy value, not Base's P&amp;L)</span></div>`);
    out.push(Object.entries(money.energyValueUSD).map(([b, v]) => row(esc(branchNames[b] || b) + (b === branch ? ' ◂' : ''), usd(v))).join(''));
  }
  if (money.costOfAwareness) {
    done.add('costOfAwareness');
    const c = money.costOfAwareness;
    out.push(row('Cost of awareness (naive minus aware)', usd(c)));
    if (c.v !== null && c.v < 0) out.push('<div class="hb-sub">Negative: feeder-aware earned more; prices keep falling after the onset.</div>');
  }
  const cap = money.systemCapacityPerMonth;
  if (cap && typeof cap === 'object') {
    done.add('systemCapacityPerMonth');
    const c = cap[branch] || cap.aware || Object.values(cap)[0];
    if (c && c.fleetKW && c.low && c.high) {
      const lo = consts && consts.CAPACITY_BENCHMARK_USD_KW_MONTH, hi = consts && consts.CAPACITY_HIGH_USD_KW_MONTH;
      const band = lo && hi
        ? `${usd({ v: lo.value, label: lo.label, cite: lo.cite })} (market benchmark) to ${usd({ v: hi.value, label: hi.label, cite: hi.cite })} (UNVERIFIED) per kW-month`
        : 'the $3.12 benchmark to $8.50 UNVERIFIED per kW-month';
      out.push(`<div class="p1-money-h">System-capacity value <span class="hb-sub">(fleet kW at the price peak × ${band})</span></div>`);
      out.push(row(`Fleet at the price peak (${esc(branchNames[cap[branch] ? branch : 'aware'] || '')})`, fmt.fmtHTML(c.fleetKW, { unit: ' kW', digits: 1 })));
      out.push(row('Per month, low to high', `${usd(c.low)} to ${usd(c.high)}`));
      out.push('<div class="hb-sub">A system-peak value, not a payment for local relief.</div>');
    }
  }
  const r = money.relief;
  if (r && typeof r === 'object' && !fmt.isLabelled(r)) {
    done.add('relief');
    out.push('<div class="p1-money-h">Local relief</div>');
    if (r.kwh) out.push(row('Relief energy on A', fmt.fmtHTML(r.kwh, { unit: ' kWh', digits: 2 })));
    if (r.opportunityUpperUSD) out.push(row('Upper-bound opportunity cost', usd(r.opportunityUpperUSD)));
    if (r.priced) out.push(row('Priced?', fmt.fmtHTML(r.priced)));
  }
  if (money.localRelief) { done.add('localRelief'); out.push(`<div class="p1-note">${labelledTreeHTML(fmt, money.localRelief, 'localRelief')}</div>`); }
  if (Array.isArray(money.whoPays)) {
    done.add('whoPays');
    out.push('<div class="p1-money-h">Who pays today, and for what</div>');
    out.push(labelledTreeHTML(fmt, money.whoPays, 'whoPays'));
  }
  if (money.transformerReplacementUSD) {
    done.add('transformerReplacementUSD');
    const t = money.transformerReplacementUSD;
    out.push(row('Transformer replacement cost', t.v === null ? `not sourced ${fmt.chip(t.label, t.cite)}` : usd(t)));
  }
  const ah = money.avoidedHarm;
  if (ah && typeof ah === 'object') {
    done.add('avoidedHarm');
    const cols = ['normalEvents', 'emergencyTfs', 'protectionOperated'];
    const heads = ['normal-tier events', 'emergency tfs', 'protection'];
    const bs = Object.keys(ah);
    const lab = (bs.length && ah[bs[0]][cols[0]]) ? ah[bs[0]][cols[0]].label : 'SIM';
    out.push(`<div class="p1-money-h">Avoided harm ${fmt.chip(lab, 'OpenDSS tier events')}</div>
      <table class="p1-table"><tr><th></th>${heads.map((h) => `<th>${h}</th>`).join('')}</tr>
      ${bs.map((b) => `<tr${b === branch ? ' class="now"' : ''}><td>${esc(branchNames[b] || b)}</td>${cols.map((c) => `<td>${ah[b][c] ? esc(fmt.fmtValue(ah[b][c])) : ''}</td>`).join('')}</tr>`).join('')}</table>`);
  }
  const rest = Object.fromEntries(Object.entries(money).filter(([k]) => !done.has(k)));
  if (Object.keys(rest).length) out.push(labelledTreeHTML(fmt, rest));
  return out.join('');
}

/** The grid-check line of a branch summary (build prompt 7.3): measured, never asserted. */
export function gridCheckHTML(fmt, s, homeLabel) {
  if (!s) return '';
  const parts = [];
  if (s.vMinHome) {
    const v = s.vMinHome;
    const where = `${v.home !== undefined ? esc(homeLabel(v.home)) : ''}${v.t ? ', ' + esc(v.t) : ''}`;
    const volts = v.volts !== undefined ? fmt.fmtHTML(L(v.volts, v.label, v.cite), { unit: ' V', digits: 1 }) : '';
    const below = s.homesBelow095 ? s.homesBelow095.v : null;
    if (below === 0) {
      parts.push(`<div>Voltage stays in range at unity pf ${fmt.chip('SIM', 'OpenDSS; batteries at unity power factor (ASSUMPTION)')}: lowest home ${fmt.fmtHTML(L(v.v, v.label, v.cite), { digits: 4, unit: ' pu' })} = ${volts} (${where})</div>`);
    } else {
      parts.push(`<div>Lowest service voltage ${fmt.fmtHTML(L(v.v, v.label, v.cite), { digits: 4, unit: ' pu' })} = ${volts} (${where})${s.homesBelow095 ? `; homes below 0.95 pu ${fmt.fmtHTML(s.homesBelow095)}` : ''}</div>`);
    }
  }
  if (s.feederHead) {
    const h = s.feederHead;
    const rating = h.ratingA ? fmt.fmtHTML(h.ratingA, { unit: ' A' }) : '';
    const amps = h.amps !== undefined ? fmt.fmtHTML(L(h.amps, h.label, h.cite), { unit: ' A', digits: 0 }) : '';
    parts.push(`<div>Feeder head max ${fmt.fmtHTML(L(h.v, h.label, h.cite), { unit: '%', digits: 1 })} of ${rating}${amps ? ` (${amps}${h.t ? ' at ' + esc(h.t) : ''})` : ''}</div>`);
  }
  return parts.join('');
}

// ---------------------------------------------------------------------------------------------------------------
export async function mount(el, ctx) {
  const { data, link, fmt, sceneModel, scene, topology } = ctx;
  nvFmt = fmt;
  const meta = await data.loadP1Meta();
  const branches = meta.branches;
  let branch = branches.includes(link.branch) ? link.branch : branches[0];
  const docs = {};
  const loadDoc = async (b) => (docs[b] || (docs[b] = await data.loadP1Branch(b)));
  let doc = await loadDoc(branch);
  let k = initialStep(meta, link, fmt);
  let playing = false, speed = 1, acc = 0, last = 0;
  const stepSec = meta.stepSeconds || 60;
  const homeLabel = (h) => {
    if (typeof h === 'number') return topology.homes[h] ? topology.homes[h].label : `home ${h}`;
    if (h && typeof h === 'object') {
      const lab = h.label || (typeof h.home === 'number' && topology.homes[h.home] ? topology.homes[h.home].label : 'a home');
      return h.tf !== undefined && h.tf !== null ? `${lab} on ${tfName(h.tf)}` : lab;
    }
    return String(h);
  };
  const tfName = (tf) => {
    const f = (topology.focus || []).find((x) => x.tf === tf);
    if (f) return f.key;
    const b = (topology.bridge || []).find((x) => x.tf === tf);
    return b ? `T-${tf}` : `T-${tf}`;
  };
  const priceLabel = seriesLabel(meta, 'price', 'REAL');

  // ---- static panel skeleton ----
  el.classList.add('p1');
  el.innerHTML = `
    <h1>P1 · where to charge</h1>
    <div class="hb-sub" id="p1-when"></div>
    <div class="hb-seg p1-branches" role="tablist">${branches.map((b) => `<a href="${ctx.href({ branch: b, t: fmt.stepToTime(meta, k) })}" data-branch="${b}" aria-current="${b === branch}">${esc(BRANCH_NAMES[b] || b)}${b === 'naive' ? fmt.chip('ASSUMPTION', NAIVE_FRAMING) : ''}</a>`).join('')}</div>
    <div class="p1-framing" id="p1-framing"></div>
    <section class="p1-hero" id="p1-hero"></section>
    <section id="p1-faults-sec" hidden><h2>Pieces fail ${fmt.chip('ASSUMPTION', 'event times and sizes are named constants (build prompt 5.4.4)')}</h2><div id="p1-faults"></div></section>
    <section><h2>Street A–D and T-240 · headroom now</h2><div id="p1-gauges"></div>
      <div class="p1-legend-gauge"><span class="sw sw-home"></span>home load <span class="sw sw-bat"></span>battery charging <span class="sw sw-relief"></span>battery discharging (relief) · ticks: 100% nameplate, 110% normal rating, 150% emergency ${fmt.chip('REAL', 'SMART-DS normhkva / EmergHKVA')}, 200% fuse rule ${fmt.chip('ASSUMPTION', meta.protection && meta.protection.cite)}</div></section>
    <section><h2>Orchestrator ticker ${fmt.chip(seriesLabel(doc, 'ticker', 'SIM'), 'sim.orchestrator.allocate(): deterministic, no model in the loop')}</h2><ol class="p1-ticker" id="p1-ticker"></ol></section>
    <section id="p1-relief-sec" hidden><h2>Peak relief</h2><div id="p1-relief"></div></section>
    <section id="p1-unrel-sec" hidden><h2>Not relieved here → P2</h2><div id="p1-unrel"></div></section>
    <section><h2>Grid checks · this branch</h2><div id="p1-grid" class="p1-grid"></div></section>
    <section><h2>This evening · this branch</h2><div id="p1-summary"></div></section>
    <section id="p1-money-sec" hidden><h2>Money</h2><div id="p1-money"></div></section>
    <section id="p1-ladder-sec" hidden><h2>Scale ladder</h2><div id="p1-ladder"></div></section>
    <section id="p1-pick-sec" hidden><h2>Selected</h2><div id="p1-pick"></div></section>
    <section><h2>What the controller sees</h2><div class="hb-sub">${esc(meta.controllerView ? meta.controllerView.text : '')} ${meta.controllerView ? fmt.chip(meta.controllerView.label, meta.controllerView.cite) : ''}</div></section>
    <section><h2>Sources</h2><div class="hb-sub" id="p1-sources"></div></section>`;
  const $ = (id) => el.querySelector('#' + id);

  // ---- overlays on the scene: camera presets, legend, credits, transport ----
  for (const old of document.querySelectorAll('.p1-overlay')) old.remove();
  const cams = document.createElement('div');
  cams.className = 'p1-overlay p1-cams';
  cams.innerHTML = [['feeder', 'Whole feeder'], ['street', 'Street A–D'], ['t240', 'Northbank T-240']]
    .map(([c, t]) => `<button type="button" data-cam="${c}"${link.cam === c ? ' aria-pressed="true"' : ''}>${t}</button>`).join('');
  const legend = document.createElement('div');
  legend.className = 'p1-overlay p1-legend';
  const TR = sceneModel.TIER_RGB, TN = sceneModel.TIER_NAMES;
  const rgb = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
  legend.innerHTML = `<div class="p1-legend-h">Transformer zone (homes and cans) · OpenDSS ${fmt.chip('SIM')}</div>
    ${TN.map((n, i) => `<div><span class="sw" style="background:${rgb(TR[i])}"></span>${esc(n)}</div>`).join('')}
    <div class="p1-legend-h">Homes</div>
    <div><span class="sw" style="background:${rgb(sceneModel.DARK_HOME)}"></span>dark (protection opened)</div>
    <div><span class="sw" style="background:${rgb(sceneModel.BACKUP_GLOW)}"></span>lit by its own battery</div>
    <div class="p1-legend-h">Batteries (column = state of charge; ring = 20% reserve)</div>
    <div><span class="sw" style="background:var(--accent)"></span>charging <span class="sw" style="background:var(--serious)"></span>discharging <span class="sw" style="background:rgb(140,164,146)"></span>idle <span class="sw" style="background:rgb(150,150,150)"></span>stale / expired (!)</div>
    <div class="p1-legend-h">Cans: glass = 100% of nameplate; fill = loading; ring 110%; red cap 150%. Room = kW to nameplate ${fmt.chip('DERIVED')}</div>`;
  const credits = document.createElement('div');
  credits.className = 'p1-overlay p1-credits';
  const fm = ctx.footprints && ctx.footprints.meta;
  credits.innerHTML = `Buildings © OpenStreetMap contributors, ODbL 1.0${fm && fm.matched ? ` (${fmt.fmtHTML(fm.matched)} of 1,010 homes matched; the rest are 12 m boxes ${fmt.chip('ASSUMPTION')})` : ' (not loaded: every home is a 12 m box ' + fmt.chip('ASSUMPTION') + ')'} · Feeder: NREL SMART-DS 2018 AUS P1U, CC BY 4.0 · Prices: ERCOT RTM LZ_NORTH`;
  const transport = document.createElement('div');
  transport.className = 'p1-overlay p1-transport';
  transport.innerHTML = `
    <button type="button" class="p1-play" id="p1-play" aria-label="play">▶</button>
    <select id="p1-speed" aria-label="speed">${SPEEDS.map((s) => `<option value="${s}"${s === 1 ? ' selected' : ''}>${s}×</option>`).join('')}</select>
    <div class="p1-clock"><div class="p1-time" id="p1-time"></div><div class="p1-price" id="p1-price"></div></div>
    <div class="p1-strip-wrap"><canvas id="p1-strip" class="p1-strip"></canvas><div class="p1-strip-marks" id="p1-marks"></div></div>`;
  document.body.append(cams, legend, credits, transport);
  const strip = transport.querySelector('#p1-strip');

  // ---- rendering ----
  function framingHTML() {
    if (branch === 'naive') {
      const nl = meta.naiveLabel && meta.naiveLabel.text ? meta.naiveLabel : { text: NAIVE_FRAMING, label: 'ASSUMPTION', cite: 'build prompt 3.4, 12 Q5' };
      return `<div class="p1-note">${esc(nl.text)} ${fmt.chip(nl.label || 'ASSUMPTION', nl.cite)}</div>`;
    }
    if (branch === 'none') return '<div class="p1-note">No batteries: what the homes alone do to their transformers.</div>';
    if (branch === 'aware_faults') return '<div class="p1-note">Feeder-aware, while a battery goes silent, a transformer runs hot and our controller stalls.</div>';
    return '<div class="p1-note">Feeder-aware: before sending charge, each transformer\'s headroom is checked and only what fits is sent.</div>';
  }

  function renderStatic() {
    for (const a of el.querySelectorAll('.p1-branches a')) {
      a.setAttribute('aria-current', String(a.dataset.branch === branch));
      a.href = ctx.href({ branch: a.dataset.branch, t: fmt.stepToTime(meta, k) });
    }
    $('p1-framing').innerHTML = framingHTML();
    const s = meta.summary && meta.summary[branch];
    $('p1-grid').innerHTML = gridCheckHTML(fmt, s, homeLabel);
    // summary, the claim scoped to service transformers
    if (s) {
      const keys = ['batteryCausedNormal', 'batteryCausedEmergency', 'normalEvents', 'emergencyTfs', 'batteryCausedAmberMin', 'homeOnlyOver100',
        'protectionOperated', 'homesDark', 'homesOnBattery', 'reserveBreaches', 'chargedPctBy0400', 'energyValueUSD'];
      const ml = s.maxLoading;
      let claim = '';
      if (s.normalEvents && s.emergencyTfs) {
        claim = s.normalEvents.v === 0 && s.emergencyTfs.v === 0
          ? `<div class="p1-claim ok">No service transformer passed its limit this evening (normal rating or emergency) ${fmt.chip(s.normalEvents.label, s.normalEvents.cite)}</div>`
          : `<div class="p1-claim bad">${fmt.fmtHTML(s.normalEvents)} normal-tier events and ${fmt.fmtHTML(s.emergencyTfs)} transformers in emergency this evening</div>`;
      }
      $('p1-summary').innerHTML = claim
        + (ml ? `<div class="p1-row"><span class="p1-k">${NAMES.maxLoading}</span><span class="p1-v">${fmt.fmtHTML(ml, { unit: '%', digits: 1 })} <span class="hb-sub">${ml.tf !== undefined ? esc(tfName(ml.tf)) : ''}${ml.t ? ' at ' + esc(ml.t) : ''}</span></span></div>` : '')
        + keys.filter((kk) => s[kk]).map((kk) => `<div class="p1-row"><span class="p1-k">${esc(humanKey(kk))}</span><span class="p1-v">${fmt.fmtHTML(s[kk], optsFor(kk))}</span></div>`).join('');
    } else {
      $('p1-summary').innerHTML = '<div class="hb-sub">No summary for this branch.</div>';
    }
    // faults
    const ev = (meta.events && meta.events[branch]) || [];
    $('p1-faults-sec').hidden = !ev.length;
    // relief
    const r = meta.relief;
    $('p1-relief-sec').hidden = !r;
    if (r) {
      const d = r.driver;
      const shared = d && d.sharedWith && d.sharedWith.length ? `, also used at ${esc(d.sharedWith.map(homeLabel).join(', '))}` : '';
      const mins = r.minutesOver100;
      const minsHTML = !mins ? '' : fmt.isLabelled(mins) && mins.none !== undefined && mins.aware !== undefined
        ? `none ${nv(L(mins.none, mins.label), { unit: ' min' })} → aware ${nv(L(mins.aware, mins.label), { unit: ' min' })} ${fmt.chip(mins.label, mins.cite)}`
        : fmt.isLabelled(mins) ? fmt.fmtHTML(mins, { unit: ' min' })
        : `none ${mins.none ? fmt.fmtHTML(mins.none, { unit: ' min' }) : 'n/a'} → aware ${mins.aware ? fmt.fmtHTML(mins.aware, { unit: ' min' }) : 'n/a'}`;
      $('p1-relief').innerHTML = `
        <div class="p1-relief-big">${esc(tfName(r.tf))} at ${esc(r.t || '')}: ${r.none ? fmt.fmtHTML(r.none, { unit: '%', digits: 1 }) : 'n/a'} without batteries → ${r.aware ? fmt.fmtHTML(r.aware, { unit: '%', digits: 1 }) : 'n/a'} feeder-aware</div>
        <div class="p1-row"><span class="p1-k">Minutes over nameplate</span><span class="p1-v">${minsHTML}</span></div>
        ${r.reliefKW ? `<div class="p1-row"><span class="p1-k">Batteries discharged</span><span class="p1-v">${fmt.fmtHTML(r.reliefKW, { unit: ' kW', digits: 1 })}${r.reliefKWh ? ' · ' + fmt.fmtHTML(r.reliefKWh, { unit: ' kWh', digits: 1 }) : ''}</span></div>` : ''}
        ${d ? `<div class="p1-driver">Driver: one home's 15-minute spike: ${esc(d.label || homeLabel(d.home))}, SMART-DS profile <code>${esc(d.profile || '')}</code>${d.kwAtPeak ? ' at ' + fmt.fmtHTML(d.kwAtPeak, { unit: ' kW', digits: 1 }) : ''}${shared}. The same shape elsewhere is not independent evidence.</div>` : ''}
        <div class="hb-sub">${esc(r.text || 'Over nameplate for about 15 minutes is amber, not a failure.')}</div>`;
    }
    // unrelieved -> P2
    const un = meta.unrelieved || [];
    $('p1-unrel-sec').hidden = !un.length;
    $('p1-unrel').innerHTML = un.map((u) => {
      const d = u.driver;
      return `<div class="p1-unrel">${esc(tfName(u.tf))}: ${esc(u.reason || '')}${u.peak && fmt.isLabelled(u.peak) ? ` (peak ${fmt.fmtHTML(u.peak, { unit: '%', digits: 1 })}${u.peak.t ? ' at ' + esc(u.peak.t) : ''})` : ''}${d ? `; driver ${esc(d.label || homeLabel(d.home))} (<code>${esc(d.profile || '')}</code>${d.sharedWith && d.sharedWith.length ? ', shared with ' + esc(d.sharedWith.map(homeLabel).join(', ')) : ''})` : ''}. <a href="${ctx.href({ view: 'p2', branch: null, t: null, cam: u.tf === ((topology.bridge || [])[0] || {}).tf ? 't240' : null })}">Where the next battery goes →</a></div>`;
    }).join('');
    // money + ladder (generic labelled trees: every value carries its label)
    $('p1-money-sec').hidden = !meta.money;
    if (meta.money) $('p1-money').innerHTML = moneyHTML(fmt, meta.money, branch, BRANCH_NAMES, meta.constants);
    const ladder = meta.scaleLadder || (meta.money && meta.money.scaleLadder) || null;
    $('p1-ladder-sec').hidden = !ladder || !!(meta.money && meta.money.scaleLadder);
    if (ladder && !(meta.money && meta.money.scaleLadder)) $('p1-ladder').innerHTML = labelledTreeHTML(fmt, ladder);
    $('p1-sources').innerHTML = Object.values(meta.sources || {}).map((s) => `${esc(s.text)} ${fmt.chip(s.label)}`).join('<br>');
    drawStrip();
  }

  function renderGauges() {
    const lab = seriesLabel(doc, 'loading', 'SIM');
    const flab = seriesLabel(doc, 'focus', 'SIM');
    const fuse = { pct: meta.protection ? meta.protection.fusePct : 200, min: meta.protection ? meta.protection.fuseMinutes : 10, cite: meta.protection && meta.protection.cite };
    const html = FOCUS_KEYS.map((key) => {
      const g = gaugeModel(meta, doc, topology, key, k, sceneModel.roomKW);
      if (!g) return '';
      const w = (p) => `${Math.max(0, Math.min(100, 100 * p / GAUGE_MAX_PCT)).toFixed(2)}%`;
      const homeW = Math.max(0, g.homePct);
      const batOn = g.batPct > 0.05 ? g.batPct : 0;
      const relief = g.batPct < -0.05 ? Math.min(homeW, -g.batPct) : 0;
      const tick = (p, cls) => `<span class="g-tick ${cls}" style="left:${w(p)}"></span>`;
      const title = key === '240' ? `T-240 · ${g.kva} kVA · no battery` : `${key} · ${g.kva} kVA · ${g.homes} homes, ${branch === 'none' ? 'batteries off in this branch' : `${g.batteries} batteries`}`;
      const room = g.open ? 'open (protection)' : g.pct > 100
        ? `over nameplate by ${fmt.fmtHTML(L(+((g.pct / 100 - 1) * g.kva).toFixed(1), 'DERIVED', 'OpenDSS loading above 100%, times kVA'), { unit: ' kVA', digits: 1 })}`
        : `room ${fmt.fmtHTML(L(+Math.max(0, g.room).toFixed(1), 'DERIVED', 'kW of charge that still fits under nameplate, from OpenDSS loading and metered kW (unity-pf batteries)'), { unit: ' kW', digits: 1 })}`;
      return `<div class="gauge tier-bg-${g.code}">
        <div class="g-head"><span class="g-key">${esc(title)}</span><span class="g-pct tier-${g.code}">${fmt.fmtHTML(L(+g.pct.toFixed(1), lab, 'OpenDSS loading, % of nameplate'), { unit: '%', digits: 1 })}</span></div>
        <div class="g-bar">
          <span class="g-home" style="width:${w(homeW - relief)}"></span><span class="g-relief" style="width:${w(relief)}"></span><span class="g-bat" style="width:${w(batOn)}"></span>
          <span class="g-load" style="left:${w(g.pct)}"></span>
          ${tick(100, 't100')}${tick(110, 't110')}${tick(150, 't150')}${tick(200, 't200')}
        </div>
        <div class="g-sub">home ${nv(L(+g.homeKW.toFixed(1), flab), { unit: ' kW', digits: 1 })} · batteries ${nv(L(+g.batKW.toFixed(1), flab), { unit: ' kW', digits: 1, signed: true })} ${fmt.chip(flab, 'metered kW at the homes (SIM)')} · ${room}</div>
        <div class="g-fuse">evening max ${nv(L(+g.maxPct.toFixed(1), lab), { unit: '%', digits: 1 })} at ${esc(fmt.stepToTime(meta, g.maxStep))} · ${nv(L(g.min110, lab), { unit: ' min' })} above 110%${g.min150 ? ` · ${nv(L(g.min150, lab), { unit: ' min' })} above 150%` : ''} ${fmt.chip(lab, 'OpenDSS loading; minutes at tier codes 2-4')} · fuse rule opens at ${nv(L(fuse.pct, 'ASSUMPTION'), { unit: '%' })} for ${nv(L(fuse.min, 'ASSUMPTION'), { unit: ' min' })} ${fmt.chip('ASSUMPTION', fuse.cite)}${g.openStep >= 0 ? ` · <b>opened at ${esc(fmt.stepToTime(meta, g.openStep))}</b>` : ''}</div>
      </div>`;
    }).join('');
    $('p1-gauges').innerHTML = html;
  }

  /** Near A's spike, on the feeder-aware branch: the relief at its true size, above the fold (build prompt 4.2, 11). */
  function heroReliefHTML() {
    const r = meta.relief;
    if (!r || branch !== 'aware' || !r.none || !r.aware || !spikeDriverAt(meta, fmt, r.tf, k)) return '';
    const kw = r.reliefKW ? `; its batteries discharged ${fmt.fmtHTML(r.reliefKW, { unit: ' kW', digits: 1 })}` : '';
    return `<div class="p1-counts">relief on ${esc(tfName(r.tf))} at ${esc(r.t || '')}: ${fmt.fmtHTML(r.none, { unit: '%', digits: 1 })} with no batteries → ${fmt.fmtHTML(r.aware, { unit: '%', digits: 1 })} feeder-aware${kw} (over nameplate is amber, not a failure)</div>`;
  }

  function renderDynamic() {
    const time = fmt.stepToTime(meta, k);
    $('p1-when').textContent = `${meta.day} · ${time} · step ${k} of ${meta.steps} · ${BRANCH_NAMES[branch] || branch}`;
    const lab = seriesLabel(doc, 'loading', 'SIM');
    const w = worstAt(doc, k);
    const c = countsAt(doc, k);
    const sc = stateCounts(doc, k);
    $('p1-hero').innerHTML = `
      <h2>Worst service transformer now</h2>
      <div class="hb-big tier-${w.code}">${fmt.fmtHTML(L(+w.pct.toFixed(1), lab, 'OpenDSS loading, % of nameplate'), { unit: '%', digits: 1 })}</div>
      <div class="hb-sub">${esc(tfName(w.tf))} · ${esc(sceneModel.TIER_NAMES[w.code] || '')}</div>
      ${w.code >= 1 ? driverLineHTML(fmt, spikeDriverAt(meta, fmt, w.tf, k), homeLabel) : ''}
      ${heroReliefHTML()}
      <div class="p1-counts">transformers now: over nameplate ${nv(L(c[0] + c[1] + c[2] + c[3], lab))} · above 110% ${nv(L(c[1] + c[2] + c[3], lab))} · emergency ${nv(L(c[3], lab))} · protection open ${nv(L(c[4], lab))} ${fmt.chip(lab, 'tier codes from sim.tiers')}</div>
      ${branch === 'none' ? '<div class="p1-counts">no batteries in this branch</div>' : `<div class="p1-counts">batteries now: charging ${nv(L(sc.C, 'SIM'))} · discharging ${nv(L(sc.D, 'SIM'))} · idle ${nv(L(sc.I, 'SIM'))}${sc.S + sc.X ? ` · stale/expired ${nv(L(sc.S + sc.X, 'SIM'))}` : ''}${sc.B ? ` · islanded ${nv(L(sc.B, 'SIM'))}` : ''} ${fmt.chip('SIM')}</div>`}`;
    renderGauges();
    const tk = tickerAt(doc, k, 6);
    $('p1-ticker').innerHTML = tk.length ? tk.map(([st, text]) => `<li class="${st === k ? 'now' : ''}">${esc(text)}</li>`).join('') : '<li class="hb-sub">nothing sent yet</li>';
    const ev = (meta.events && meta.events[branch]) || [];
    if (ev.length) {
      $('p1-faults').innerHTML = ev.map((e) => {
        const past = e.step <= k;
        let now = '';
        if (e.kind === 'comms_lost' && e.home !== undefined) {
          const j = Number.isInteger(e.batt) ? e.batt : (topology.fleet || []).indexOf(e.home);
          if (j >= 0) now = ` · now: ${esc(sceneModel.STATE_NAMES[doc.state[k][j]] || doc.state[k][j])}`;
        }
        const vals = [];
        if (e.cmdKW !== undefined) vals.push(`command ${fmt.fmtHTML(L(e.cmdKW, 'SIM'), { unit: ' kW', digits: 1, signed: true })}`);
        if (e.deltaKW !== undefined) vals.push(`+${fmt.fmtHTML(L(e.deltaKW, 'ASSUMPTION', 'EV_KW: a Level 2 EV'), { unit: ' kW', digits: 1 })}`);
        if (e.minutes !== undefined) vals.push(fmt.fmtHTML(L(e.minutes, 'ASSUMPTION'), { unit: ' min' }));
        return `<div class="p1-fault ${past ? 'past' : ''}"><b>${esc(e.t)}</b> ${esc(e.text || faultText(e, homeLabel))}${vals.length ? ' · ' + vals.join(' · ') : ''}${past ? now : ''}</div>`;
      }).join('');
    }
    const pv = meta.price[k];
    transport.querySelector('#p1-time').textContent = time;
    transport.querySelector('#p1-price').innerHTML = fmt.fmtHTML(L(pv, priceLabel, 'ERCOT RTM SPP LZ_NORTH, the interval containing this minute'), { money: true, digits: 2, unit: '/MWh' });
    drawCursor();
    const frame = sceneModel.frameFromP1(doc, k);
    scene.update(sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame, view: 'p1', theme: ctx.theme, hideBatteries: branch === 'none' }));
  }

  // ---- price strip: REAL price line, the market plan's discharge intervals, a tier-count ribbon, markers, cursor ----
  let stripBase = null;
  function drawStrip() {
    const r = strip.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    strip.width = Math.max(1, Math.round(r.width * dpr));
    strip.height = Math.max(1, Math.round(r.height * dpr));
    const c = strip.getContext('2d');
    if (!c) return;
    const W = strip.width, H = strip.height, n = meta.steps;
    const css = getComputedStyle(document.body);
    const col = (v, d) => (css.getPropertyValue(v).trim() || d);
    c.clearRect(0, 0, W, H);
    const ribbon = 11 * dpr, top = LABEL_BAND_PX * dpr, ph = H - ribbon - top - 14 * dpr;
    const xs = (i) => (i + 0.5) / n * W;
    // discharge plan (DERIVED)
    c.fillStyle = 'rgba(236,131,90,0.16)';
    for (const [start, mins] of (meta.plan && meta.plan.discharge) || []) {
      const k0 = fmt.timeToStep(meta, start);
      if (k0 === null) continue;
      const k1 = Math.min(n, k0 + Math.round(mins * 60 / stepSec));
      c.fillRect(k0 / n * W, top, (k1 - k0) / n * W, ph);
    }
    // price (REAL)
    const pmax = Math.max(1, ...meta.price), pmin = Math.min(0, ...meta.price);
    c.strokeStyle = col('--ink', '#101613');
    c.lineWidth = 1.5 * dpr;
    c.beginPath();
    meta.price.forEach((p, i) => { const y = top + ph - (p - pmin) / (pmax - pmin) * ph; if (i) c.lineTo(xs(i), y); else c.moveTo(xs(i), y); });
    c.stroke();
    c.fillStyle = col('--muted', '#55625A');
    c.font = `${10 * dpr}px sans-serif`;
    c.textAlign = 'right';
    c.fillText(`max $${pmax.toFixed(0)}/MWh (${priceLabel} price)`, W - 2 * dpr, top + 9 * dpr);
    c.textAlign = 'left';
    // tier ribbon: the worst code present at each step, alpha by how many transformers
    const TR = sceneModel.TIER_RGB;
    for (let i = 0; i < n; i++) {
      const cnt = countsAt(doc, i);
      let worst = 0;
      for (let q = 4; q >= 0; q--) if (cnt[q] > 0) { worst = q + 1; break; }
      if (!worst) continue;
      const tot = cnt.reduce((a, b) => a + b, 0);
      const a = Math.min(1, 0.35 + tot / 12);
      const t = TR[worst];
      c.fillStyle = `rgba(${t[0]},${t[1]},${t[2]},${a})`;
      c.fillRect(i / n * W, H - ribbon, Math.max(1, W / n + 0.5), ribbon);
    }
    // hour ticks
    c.fillStyle = col('--muted', '#55625A');
    for (let i = 0; i < n; i++) {
      const t = fmt.stepToTime(meta, i);
      if (t.endsWith(':00') && (n <= 180 || Number(t.slice(0, 2)) % 2 === 0)) {
        c.fillRect(xs(i), H - ribbon - 3 * dpr, 1 * dpr, 3 * dpr);
        c.fillText(t, xs(i) + 2 * dpr, H - ribbon - 3 * dpr);
      }
    }
    stripBase = c.getImageData(0, 0, W, H);
    // markers as DOM (legible, labelled)
    const marks = stripMarks(meta, branch, fmt, homeLabel);
    $marks.innerHTML = marks.map((m) => {
      const txt = m.text.length > MARK_CHARS ? m.text.slice(0, MARK_CHARS - 1) + '…' : m.text;
      const lab = m.row < 0 ? '' : `<span style="top:${m.row * 13}px">${esc(m.t)} ${esc(txt)}${m.count > 1 ? ` ×${m.count}` : ''}${fmt.chip(m.label)}</span>`;
      return `<button type="button" class="mark mark-${m.kind}" style="left:${(100 * (m.k + 0.5) / n).toFixed(2)}%" data-k="${m.k}" title="${esc(m.t + ' ' + m.text + ' (' + m.label + ')')}">${lab}</button>`;
    }).join('');
    drawCursor();
  }
  const $marks = transport.querySelector('#p1-marks');
  function drawCursor() {
    if (!stripBase) return;
    const c = strip.getContext('2d');
    c.putImageData(stripBase, 0, 0);
    const dpr = window.devicePixelRatio || 1;
    const x = (k + 0.5) / meta.steps * strip.width;
    c.fillStyle = getComputedStyle(document.body).getPropertyValue('--accent').trim() || '#0B6B6F';
    c.fillRect(x - 1 * dpr, 0, 2.5 * dpr, strip.height);
  }

  // ---- interaction ----
  function seek(kk, { url = true } = {}) {
    k = Math.max(0, Math.min(meta.steps - 1, kk | 0));
    renderDynamic();
    for (const a of el.querySelectorAll('.p1-branches a')) a.href = ctx.href({ branch: a.dataset.branch, t: fmt.stepToTime(meta, k) });
    if (url) replaceUrl();
  }
  function replaceUrl() {
    try {
      const q = ctx.data.linkQuery({ ...link, beat: null, branch, t: fmt.stepToTime(meta, k) });
      history.replaceState(null, '', q);
    } catch (e) { /* file:// or sandboxed: the link still works */ }
  }
  function setPlaying(p) {
    playing = p;
    const b = transport.querySelector('#p1-play');
    b.textContent = p ? '❚❚' : '▶';
    b.setAttribute('aria-label', p ? 'pause' : 'play');
    if (p) { last = performance.now(); acc = 0; requestAnimationFrame(tick); } else replaceUrl();
  }
  function tick(now) {
    if (!playing) return;
    acc += (now - last) * speed;
    last = now;
    const adv = Math.floor(acc / MS_PER_STEP);
    if (adv > 0) {
      acc -= adv * MS_PER_STEP;
      if (k + adv >= meta.steps - 1) { seek(meta.steps - 1, { url: false }); setPlaying(false); return; }
      seek(k + adv, { url: false });
    }
    requestAnimationFrame(tick);
  }
  transport.querySelector('#p1-play').addEventListener('click', () => setPlaying(!playing));
  transport.querySelector('#p1-speed').addEventListener('change', (e) => { speed = Number(e.target.value) || 1; });
  const scrubAt = (ev) => {
    const r = strip.getBoundingClientRect();
    seek(Math.floor((ev.clientX - r.left) / r.width * meta.steps));
  };
  let scrubbing = false;
  strip.addEventListener('pointerdown', (ev) => { scrubbing = true; strip.setPointerCapture(ev.pointerId); scrubAt(ev); });
  strip.addEventListener('pointermove', (ev) => { if (scrubbing) scrubAt(ev); });
  strip.addEventListener('pointerup', () => { scrubbing = false; });
  $marks.addEventListener('click', (ev) => { const b = ev.target.closest('.mark'); if (b) seek(Number(b.dataset.k)); });
  cams.addEventListener('click', (ev) => {
    const b = ev.target.closest('button[data-cam]');
    if (!b) return;
    for (const x of cams.querySelectorAll('button')) x.removeAttribute('aria-pressed');
    b.setAttribute('aria-pressed', 'true');
    scene.camera(b.dataset.cam);
  });
  el.querySelector('.p1-branches').addEventListener('click', async (ev) => {
    const a = ev.target.closest('a[data-branch]');
    if (!a) return;
    ev.preventDefault();
    try {
      branch = a.dataset.branch;
      doc = await loadDoc(branch);
      renderStatic();
      renderDynamic();
      replaceUrl();
    } catch (e) { ctx.reportError(e); }
  });
  const onKey = (ev) => {
    if (ev.target && /input|select|textarea/i.test(ev.target.tagName)) return;
    if (ev.key === ' ') { ev.preventDefault(); setPlaying(!playing); }
    else if (ev.key === 'ArrowRight') seek(k + (ev.shiftKey ? 10 : 1));
    else if (ev.key === 'ArrowLeft') seek(k - (ev.shiftKey ? 10 : 1));
  };
  window.addEventListener('keydown', onKey);
  window.addEventListener('resize', () => drawStrip());
  scene.onPick(({ layer, object }) => {
    if (!object) return;
    let html = '';
    if (layer && String(layer).startsWith('can') && object.id !== undefined) {
      const t = topology.transformers[object.i];
      html = `<div><b>${esc(tfName(object.i))}</b> <code>${esc(t.id)}</code> · ${fmt.fmtHTML(L(t.kva, 'REAL', 'SMART-DS'), { unit: ' kVA' })}</div>
        <div>loading now ${fmt.fmtHTML(L(+(doc.loading[k][object.i] / 10).toFixed(1), seriesLabel(doc, 'loading', 'SIM')), { unit: '%', digits: 1 })} · ${esc(sceneModel.TIER_NAMES[Number(doc.tier[k][object.i])] || '')}</div>
        <div class="hb-sub">homes: ${esc(t.homes.map((h) => topology.homes[h].label + (topology.homes[h].battery ? ' (battery)' : '')).join(', '))}</div>`;
    } else if (layer === 'homes' && object.i !== undefined) {
      const h = topology.homes[object.i];
      html = `<div><b>${esc(h.label)}</b> <code>${esc(h.id)}</code> · ${esc(h.district)} (fictional name) · on ${esc(tfName(h.tf))}${h.battery ? ' · has a battery' : ''}</div>`;
    } else if (layer === 'batteries' && object.j !== undefined && object.j >= 0) {
      const h = topology.homes[object.home];
      html = `<div><b>Battery at ${esc(h.label)}</b> on ${esc(tfName(h.tf))}: ${esc(sceneModel.STATE_NAMES[object.state] || object.state)} ${fmt.fmtHTML(L(object.kw, 'SIM'), { unit: ' kW', digits: 1, signed: true })} · state of charge ${fmt.fmtHTML(L(Math.round(object.soc * 100), 'SIM'), { unit: '%' })}</div>`;
    }
    if (html) { $('p1-pick-sec').hidden = false; $('p1-pick').innerHTML = html; }
  });

  renderStatic();
  renderDynamic();
  if (link.cam) scene.camera(link.cam);
}
