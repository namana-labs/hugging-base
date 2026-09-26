// ui/panels/p1.js (L4): the P1 view, "where to charge". Build prompt 5.5; round 2: UX_SPEC_R2 section 6.
//   mount(el, ctx) -> Promise   resolves after the panel's first render and ctx.scene.update(...)
//   ctx = {topology, footprints, link, scene, data, fmt, sceneModel, theme, reportError, href(patch), go(patch)}
// Round 2 (RZ: declutter, plain words, icons, hover, slower playback, tell the story visually):
//   - front cards: the day + scenario tabs (pictograms, an outcome badge each; naive keeps its ASSUMPTION tag), NOW (the
//     worst transformer's % stays in front, with a load meter, a plain tier word, who and why), the fleet as one big
//     battery, and street A-D + T-240 as five columns of meters and battery icons (no % on the columns: hover has it);
//   - everything else in collapsible sections (money, how the evening ended, failures, relief, still at risk -> P2,
//     street numbers, voltage and feeder cable, how big is this, controller log, sources), closed by default;
//   - over the scene: the story chain + the timestamped story line (storyCues, pure and node-tested), the intro card on
//     a bare `view=p1`, camera buttons, the icon legend with live tier counts, credits and the transport (0.1x-4x,
//     default 0.25x, step one minute, previous/next moment, hold at story moments, icon markers on the price strip);
//   - hover: 3D objects (scene.onHover), the street columns, strip markers and every tag show a tooltip (tip.js).
// Every number on screen is a labelled value (format.js throws on a bare one) or a bulk value shown with its series
// label. Tiers, runs and protection come from the JSON; nothing here re-derives them. No label is invented in the UI.
import { svg, TIER_WORDS, TIER_TIPS, STATE_WORDS, STATE_RGB, TIER_RGB } from '../lib/icons.js';

export const BRANCH_NAMES = { none: 'no batteries', naive: 'naive', aware: 'feeder-aware', aware_faults: 'aware + failures' };
export const TAB_NAMES = { none: 'No batteries', naive: 'Naive', aware: 'Feeder-aware', aware_faults: '+ Failures' };
export const TAB_ICONS = { none: 'house', naive: 'battery', aware: 'turns', aware_faults: 'warn' };
export const TAB_LINES = {
  none: 'What the homes alone do to their transformers.',
  naive: 'Every battery follows the price at the same moment; nobody checks the street.',
  aware: 'Checks each transformer\'s room before sending charge.',
  aware_faults: 'Feeder-aware, while a battery goes silent, an EV plugs in and our controller stalls.',
};
export const NAIVE_FRAMING = 'ERCOT dispatches one number per zone and does not check feeders (REAL). The naive branch splits that number with no feeder check, all at once at the onset (ASSUMPTION: Base\'s real split is not public; build prompt 12 Q5). Base may not charge this way today.';
export const SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4];
export const DEFAULT_SPEED = 0.25;       // RZ: 0.5x was still too fast to watch (RZ_FEEDBACK_R2)
export const MS_PER_STEP = 100;          // 1 simulated minute per 100 ms at 1x (build prompt 5.5)
export const HOLD_MS = 1500;             // playback holds this long at each story moment, once per play
// Display thresholds for the story cues: they decide WHEN TO SPEAK, never what happened (build prompt 3.5). Named here,
// with the reason, and never tuned to make a beat appear.
export const SELL_SHARE = 0.9;           // "the fleet sells": at least 90% of the batteries sending power out
export const ALL_SHARE = 0.9;            // "every battery charges": at least 90% charging
export const DONE_SOC = 0.99;            // "batteries full": fleet mean state of charge at or above 99%
export const HOLD_STEPS = 20;            // a story line stays up for 20 simulated minutes, or until the next cue
export const SHARE_STEPS = 3;            // cues within 3 steps share one line (the later text wins)
export const SPEED_TIPS = { 0.1: '0.1×: 1 simulated minute per second', 0.25: '0.25×: 2.5 simulated minutes per second', 0.5: '0.5×: 5 simulated minutes per second',
  1: '1×: 10 minutes per second (the evening in 72 s)', 2: '2×: 20 minutes per second', 4: '4×: 40 minutes per second' };
/** A beat opens its section (UX_SPEC_R2 6.2). */
export const BEAT_SECTIONS = { money: 'money', 'peak-relief': 'relief', faults: 'faults' };

const FOCUS_KEYS = ['A', 'B', 'C', 'D', '240'];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const L = (v, label, cite, extra) => ({ v, label, ...(cite ? { cite } : {}), ...(extra || {}) });
/** A labelled number's value (format.js throws on a bare one), for lines that carry one tag for all their numbers. */
const nv = (fmt, x, opts) => `<span class="num">${esc(fmt.fmtValue(x, opts))}</span>`;
const LABEL_WORDS = { REAL: 'measured or published data.', SIM: 'our simulation (OpenDSS power flow + our controller). Not a measurement.', DERIVED: 'arithmetic on REAL or SIM numbers.', ASSUMPTION: 'a value we chose because the real one is not public.' };
const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "Sun 23 Aug 2026" for "2026-08-23" (+ dayOffset days); the weekday is computed, never typed. */
export function dayLabel(iso, dayOffset = 0, withYear = true) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
  if (!m) return String(iso || '');
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3] + dayOffset));
  return `${WEEKDAY[d.getUTCDay()]} ${d.getUTCDate()} ${MONTH[d.getUTCMonth()]}${withYear ? ' ' + d.getUTCFullYear() : ''}`;
}
/** Days after meta.day at step k (the P1 window runs past midnight). */
export function dayOffsetAt(meta, fmt, k) {
  const s = fmt.hhmmToMin(meta.start);
  return Math.floor((s + k * (meta.stepSeconds || 60) / 60) / 1440);
}

/** Minutes either side of a driver's 15-minute interval in which it is named (the interval interpolated to 1 min). */
export const DRIVER_WINDOW_MIN = 15;

/** The `driver` behind transformer `tf` at step `k`, or null: `meta.relief` (A's spike) or a `meta.unrelieved` entry
 *  (T-240) whose peak is within DRIVER_WINDOW_MIN of k (build prompt 4.2, 5.3). */
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

/** When the relief's peak discharge (`meta.relief.reliefKW`) happens: "HH:MM" or null (judge R1 F7). */
export function reliefPeakAt(meta, doc, fmt) {
  const r = meta && meta.relief;
  if (!r || !r.reliefKW || !doc || !doc.focus) return null;
  if (r.reliefKW.t) return r.reliefKW.t;
  const f = Object.values(doc.focus).find((x) => x && x.tf === r.tf);
  const step = Number.isInteger(r.step) ? r.step : (r.t ? fmt.timeToStep(meta, r.t) : null);
  if (!f || step === null) return null;
  const w = Math.round(DRIVER_WINDOW_MIN * 60 / (meta.stepSeconds || 60));
  let best = null;
  for (let i = Math.max(0, step - w); i <= Math.min(f.batKW.length - 1, step + w); i++) if (best === null || f.batKW[i] < f.batKW[best]) best = i;
  if (best === null || Math.abs(-f.batKW[best] / 10 - r.reliefKW.v) > 0.1) return null;
  return fmt.stepToTime(meta, best);
}

/** One line: whose spike it is, its SMART-DS profile, and where else the same profile is used. */
export function driverLineHTML(fmt, info, homeLabel) {
  if (!info) return '';
  const d = info.driver;
  const shared = d.sharedWith && d.sharedWith.length ? `; the same profile is used at ${esc(d.sharedWith.map(homeLabel).join(', '))}, so it is not independent evidence` : '';
  const kw = d.kwAtPeak && fmt.isLabelled(d.kwAtPeak) ? ` (${fmt.fmtHTML(d.kwAtPeak, { unit: ' kW', digits: 1 })} at ${esc(info.t || '')})` : '';
  const what = info.kind === 'unrelieved' ? 'home load only, no battery here: ' : '';
  return `<div class="p1-driver">${what}one home's 15-minute spike: ${esc(d.label || homeLabel(d.home))}, SMART-DS profile <code>${esc(d.profile || '')}</code>${kw}${shared}.</div>`;
}

/** The label of a bulk series in a branch doc (the envelope's `series`), defaulting to SIM. */
export function seriesLabel(doc, name, dflt = 'SIM') {
  const s = doc && doc.series && doc.series[name];
  return s && s.label ? s.label : dflt;
}

/** A bare `view=p1` (no branch, t, beat or date): the first open (UX_SPEC_R2 6.3 intro card). */
export function isBare(link, search) {
  if (link && typeof link.bare === 'boolean') return link.bare && !link.beat;
  const q = new URLSearchParams(search || '');
  return !['branch', 't', 'beat', 'date'].some((k) => q.has(k));
}

/** The step to open at: the link's t; a bare first open at 5 minutes before the D-26 onset; else 30 minutes after it. */
export function initialStep(meta, link, fmt, bare = false) {
  if (link && link.t) {
    const k = fmt.timeToStep(meta, link.t);
    if (k !== null) return k;
  }
  if (meta.plan && meta.plan.onset) {
    const k = fmt.timeToStep(meta, meta.plan.onset);
    if (k !== null) return bare ? Math.max(0, k - Math.round(5 * 60 / (meta.stepSeconds || 60))) : Math.min(meta.steps - 1, k + Math.round(30 * 60 / (meta.stepSeconds || 60)));
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

/** Tier codes present at any step of a branch (the legend hides rows at 0 all evening). */
export function tiersPresent(doc) {
  const s = new Set([0]);
  for (const row of doc.tier) for (const ch of row) s.add(Number(ch));
  return s;
}

/** Battery states at step k: {C, D, I, S, X, B} counts. */
export function stateCounts(doc, k) {
  const c = { C: 0, D: 0, I: 0, S: 0, X: 0, B: 0 };
  for (const ch of doc.state[k]) if (ch in c) c[ch] += 1;
  return c;
}

/** Fleet mean state of charge (0..1) at step k. */
export function meanSoc(doc, k) {
  const r = doc.soc[k];
  let s = 0;
  for (const x of r) s += x;
  return r.length ? s / r.length / 1000 : 0;
}

/** Sum of battery kW at step k over the fleet units on transformer tf. */
export function tfBatKW(doc, topology, tf, k) {
  let s = 0;
  (topology.fleet || []).forEach((hi, j) => { if (topology.homes[hi].tf === tf) s += doc.batKW[k][j] / 10; });
  return s;
}

/** The last n ticker lines at or before step k, newest first. */
export function tickerAt(doc, k, n = 6) {
  const out = [];
  const t = doc.ticker || [];
  for (let i = t.length - 1; i >= 0 && out.length < n; i--) if (t[i][0] <= k) out.push(t[i]);
  return out;
}

/** Transformer-level evening stats from the committed arrays (display only; tiers come from the JSON). */
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

/** The model for one focus transformer at step k (street columns, tooltips, numbers section). */
export function gaugeModel(meta, doc, topology, key, k, roomKW, exportRoomKW = null) {
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
  const pKW = homeKW + batKW;
  const exporting = pKW < 0;
  return {
    key, tf, id: t.id, kva, homes: t.homes.length, batteries, pct, code, homeKW, batKW,
    homePct: 100 * homeKW / kva, batPct: 100 * batKW / kva,
    room: roomKW(kva, pct, pKW), exporting, exportRoom: exporting && exportRoomKW ? exportRoomKW(kva, pct, pKW) : null,
    open: code === 5, ...ev,
  };
}

/** "Who" words for a loading (clarity 4.5): the number sits beside them, so the words only read it aloud. */
export function whoPhrase(pct) {
  if (pct <= 100) return 'within its rating';
  if (pct <= 110) return 'just over its rating';
  if (pct < 150) { const f = pct / 100 - 1; return f < 0.29 ? 'a quarter over its rating' : f < 0.42 ? 'a third over its rating' : 'half over its rating'; }
  if (pct < 190) return 'one and a half times its rating';
  return 'twice its rating';
}

/** The ratio word for the price drop (DERIVED, story rule): under 0.15 "about a tenth", 0.15-0.35 "about a quarter",
 *  0.35-0.65 "about half"; otherwise none. */
export function ratioWord(r) {
  if (!Number.isFinite(r) || r <= 0) return '';
  if (r < 0.15) return 'about a tenth';
  if (r < 0.35) return 'about a quarter';
  if (r < 0.65) return 'about half';
  return '';
}

/** Price level (DERIVED from REAL): cheap below the charge rule's threshold (2x the day's median, meta.plan.threshold),
 *  expensive at or above it. No new constant. */
export function priceLevel(meta, price) {
  const th = meta.plan && meta.plan.threshold;
  if (!th || typeof th.v !== 'number') return null;
  return price < th.v ? 'cheap' : 'expensive';
}

// ---- the story (UX_SPEC_R2 6.3): one canonical cue table, computed from the committed JSON --------------------------
/** The three chain steps per branch: [cue id, icon, words]. Ghosted before the cue, lit after; unlit when scrubbed back. */
export const CHAINS = {
  none: [['spike', 'house', 'One home\'s spike'], ['peak', 'priceUp', 'Price peaks'], ['nothing', 'priceDown', 'Price drops: no batteries, nothing changes']],
  naive: [['drop', 'priceDown', 'Price drops'], ['allcharge', 'bolt', 'Every battery charges at once'], ['overload', 'meter', 'Transformers overload']],
  aware: [['drop', 'priceDown', 'Price drops'], ['check', 'check', 'Room checked first'], ['turns', 'turns', 'Batteries take turns']],
  aware_faults: [['comms_lost', 'silent', 'A battery goes silent'], ['hot', 'hot', 'An EV plugs in'], ['stall', 'stall', 'Our controller stalls']],
};
const CUE_ICON = { spike: 'house', unrelieved: 'arrowRight', sell: 'out', backfeed: 'warn', sellcap: 'check', peak: 'priceUp', drop: 'priceDown',
  allcharge: 'bolt', overload: 'warn', worst: 'warn', clear: 'check', check: 'check', turns: 'turns', charged: 'ok', comms_lost: 'silent',
  hot: 'hot', stall: 'stall', resume: 'play', nothing: 'priceDown' };
const CUE_TONE = { backfeed: 'bad', overload: 'bad', worst: 'bad', allcharge: 'bad', comms_lost: 'bad', hot: 'bad', stall: 'bad',
  sellcap: 'ok', clear: 'info', check: 'ok', turns: 'ok', charged: 'ok', resume: 'ok', peak: 'money' };

/**
 * The story cues of one branch, from the committed JSON (pure; node-tested). Returns [{id, k, t, tone, icon, chain,
 * facts, focusTf}] sorted by k. `facts` are labelled values ({v, label, cite}) or ids. A rule that does not fire emits
 * nothing; there is no default time. Ties at one step keep the order below, so the later (more telling) text wins.
 */
export function storyCues(meta, doc, branch, topology, fmt) {
  const out = [];
  const n = doc.loading.length;
  const fleet = (topology.fleet || []).length;
  const loadLab = seriesLabel(doc, 'loading', 'SIM');
  const stateLab = seriesLabel(doc, 'state', 'SIM');
  const priceLab = seriesLabel(meta, 'price', 'REAL');
  const add = (id, k, facts = {}, focusTf = null) => {
    if (!Number.isInteger(k) || k < 0 || k >= n) return;
    out.push({ id, k, t: fmt.stepToTime(meta, k), tone: CUE_TONE[id] || 'info', icon: CUE_ICON[id] || 'info', chain: null, facts, focusTf });
  };
  const hasBat = branch !== 'none';
  const aware = branch === 'aware' || branch === 'aware_faults';
  const onset = meta.plan && meta.plan.onset ? fmt.timeToStep(meta, meta.plan.onset) : null;
  const ge2 = (k) => { const c = countsAt(doc, k); return c[1] + c[2] + c[3]; };   // codes 2-4: above 110%
  const pctFact = (tf, k) => L(doc.loading[k][tf] / 10, loadLab, 'OpenDSS loading, % of nameplate');
  const priceAt = (k) => L(meta.price[k], priceLab, 'ERCOT RTM SPP LZ_NORTH, the interval containing this minute');

  // spike: one home's 15-minute spike on A (meta.relief), when A goes over its nameplate with no batteries
  const r = meta.relief;
  const mins = r && r.minutesOver100;
  const minsNone = mins && typeof mins === 'object' ? (typeof mins.none === 'number' ? mins.none : (mins.none && mins.none.v)) : null;
  // unrelieved (T-240) first: at the same minute the relief line wins on the aware branches
  if (aware) {
    for (const u of meta.unrelieved || []) {
      if (!u.peak || !u.peak.t) continue;
      add('unrelieved', fmt.timeToStep(meta, u.peak.t), { tf: u.tf, peak: u.peak, driver: u.driver ? u.driver.label : null }, u.tf);
      break;
    }
  }
  if (r && minsNone > 0) {
    const k = Number.isInteger(r.step) ? r.step : fmt.timeToStep(meta, r.t);
    const facts = { tf: r.tf, none: r.none, aware: r.aware, driver: r.driver ? r.driver.label : null,
      minutes: L(minsNone, mins.label || 'SIM', mins.cite), reliefKW: r.reliefKW || null, reliefAt: r.reliefKW && r.reliefKW.t ? r.reliefKW.t : null };
    add('spike', k, facts, r.tf);
  }
  // sell: the market plan's discharge, when at least SELL_SHARE of the fleet sends power out
  let sell = null;
  if (hasBat && fleet) {
    for (let k = 0; k < n; k++) if (stateCounts(doc, k).D >= SELL_SHARE * fleet) { sell = k; break; }
    if (sell !== null) {
      add('sell', sell, { price: priceAt(sell), d: L(stateCounts(doc, sell).D, stateLab, 'batteries sending power out'), fleet }, null);
      const end = onset !== null ? onset : n;
      let bf = null;
      if (branch === 'naive') for (let k = sell; k < end; k++) if (ge2(k) > 0) { bf = k; break; }
      if (bf !== null) {
        const w = worstAt(doc, bf);
        add('backfeed', bf, { d: L(stateCounts(doc, bf).D, stateLab, 'batteries sending power out'), fleet, tf: w.tf, pct: pctFact(w.tf, bf) }, w.tf);
      } else if (aware) {
        let best = null;
        for (let k = sell; k < end; k++) { const w = worstAt(doc, k); if (!best || w.pct > best.pct) best = { ...w, k }; }
        if (best) add('sellcap', sell, { tf: best.tf, at: best.k, pct: pctFact(best.tf, best.k) }, best.tf);
      }
    }
  }
  // peak: the day's highest price in the window
  let pk = 0;
  for (let k = 1; k < Math.min(n, meta.price.length); k++) if (meta.price[k] > meta.price[pk]) pk = k;
  add('peak', pk, { price: priceAt(pk), cash: doc.cash || meta.cash ? cashAt(meta, branch, pk) : null }, null);
  // drop: the D-26 onset (the charge signal)
  if (onset !== null) {
    const op = meta.plan.onsetPrice || priceAt(onset);
    const ratio = meta.price[pk] > 0 ? op.v / meta.price[pk] : null;
    const dropFacts = { price: op, ratio: ratioWord(ratio), peak: priceAt(pk) };
    if (branch === 'none') {
      add('drop', onset, dropFacts, null);
      add('nothing', onset, dropFacts, null);
    } else {
      add('drop', onset, dropFacts, null);
      if (branch === 'naive') {
        let ov = null;
        for (let k = onset; k < n; k++) if (ge2(k) > 0) { ov = k; break; }
        let ac = null;
        for (let k = onset; k < n; k++) if (stateCounts(doc, k).C >= ALL_SHARE * fleet) { ac = k; break; }
        const ovFacts = ov === null ? null : (() => {
          const c = countsAt(doc, ov), w = worstAt(doc, ov);
          return { over: L(c[1] + c[2] + c[3], loadLab, 'transformers above 110% (tier codes 2-4)'), emerg: L(c[3], loadLab, 'transformers above 150% (tier code 4)'), tf: w.tf, pct: pctFact(w.tf, ov) };
        })();
        if (ov !== null) add('overload', ov, ovFacts, ovFacts.tf);
        if (ac !== null) add('allcharge', ac, { c: L(stateCounts(doc, ac).C, stateLab, 'batteries charging'), fleet, overload: ov !== null && Math.abs(ov - ac) <= SHARE_STEPS ? ovFacts : null }, null);
        // worst: the highest loading after the onset, if over nameplate; clear: the first minute after it with none above 110%
        let wk = null, wv = -1, wtf = 0;
        for (let k = onset; k < n; k++) { const w = worstAt(doc, k); if (w.pct > wv) { wv = w.pct; wk = k; wtf = w.tf; } }
        if (wk !== null && wv > 100) {
          const rm = meta.constants && meta.constants.TIER_NORMAL_MIN;
          add('worst', wk, { tf: wtf, pct: pctFact(wtf, wk), ruleMin: rm ? L(rm.value, rm.label, rm.cite) : null }, wtf);
          for (let k = wk + 1; k < n; k++) {
            if (ge2(k) === 0) {
              const s = meta.summary && meta.summary[branch];
              add('clear', k, { normal: s && s.batteryCausedNormal, emerg: s && s.batteryCausedEmergency }, null);
              break;
            }
          }
        }
      } else if (aware) {
        const sc = stateCounts(doc, onset);
        const dd = meta.onsetDeferral && meta.onsetDeferral.deferredKW ? meta.onsetDeferral.deferredKW : null;
        add('check', onset, { c: L(sc.C, stateLab, 'batteries charging'), i: L(sc.I, stateLab, 'batteries waiting'), fleet, deferred: dd }, null);
        for (let k = onset + 1; k < n; k++) {
          const a = doc.state[k - 1], b = doc.state[k];
          let hit = false;
          for (let j = 0; j < b.length; j++) if (a[j] === 'I' && b[j] === 'C') { hit = true; break; }
          if (hit) { add('turns', k, {}, null); break; }
        }
      }
      for (let k = onset; k < n; k++) {
        if (meanSoc(doc, k) >= DONE_SOC) {
          const s = meta.summary && meta.summary[branch];
          add('charged', k, { by0400: s && s.chargedPctBy0400, normal: s && s.batteryCausedNormal, emerg: s && s.batteryCausedEmergency }, null);
          break;
        }
      }
    }
  }
  // failures (aware + failures): the scripted events, their times ASSUMPTION, their outcomes SIM
  if (branch === 'aware_faults') {
    for (const e of (meta.events && meta.events[branch]) || []) {
      if (e.kind === 'comms_lost') add('comms_lost', e.step, { e }, e.tf);
      else if (e.kind === 'hot') add('hot', e.step, { e }, e.tf);
      else if (e.kind === 'stall') {
        add('stall', e.step, { e }, null);
        if (Number.isInteger(e.resumeStep)) add('resume', e.resumeStep, { e }, null);
      }
    }
  }
  // chain membership
  for (const [i, [id]] of (CHAINS[branch] || []).entries()) { const c = out.find((x) => x.id === id); if (c) c.chain = i; }
  const order = (c) => out.indexOf(c);
  return out.slice().sort((a, b) => a.k - b.k || order(a) - order(b));
}

/** Cumulative gross energy value at step k (b: `cash`, int cents), as a labelled value, or null. */
export function cashAt(meta, branch, k) {
  const c = meta.cash && meta.cash[branch];
  if (!Array.isArray(c) || !c.length) return null;
  const s = (meta.series && meta.series.cash) || {};
  return L(c[Math.max(0, Math.min(c.length - 1, k))] / 100, s.label || 'DERIVED', s.cite || 'USD, cumulative, fleet (REAL price x SIM battery kW; gross, not Base\'s profit)');
}

/** The story line's sentence for a cue (HTML; every number labelled through fmt). names: {tf(i), home(h)}. */
export function cueText(c, fmt, names, branch) {
  const f = c.facts || {};
  const H = (x, o) => (x && fmt.isLabelled(x) ? fmt.fmtHTML(x, o) : '');
  const pct = { unit: '%', digits: 1 };
  const usd = { money: true, digits: 2, unit: '/MWh' };
  const naiveTag = fmt.chip('ASSUMPTION', NAIVE_FRAMING);
  const tfn = (i) => esc(names.tf(i));
  switch (c.id) {
    case 'spike':
      if (branch === 'aware' || branch === 'aware_faults') {
        const kw = f.reliefKW ? `${H(f.reliefKW, { unit: ' kW', digits: 1 })}` : '';
        return `${tfn(f.tf)}'s own batteries discharged up to ${kw}: ${tfn(f.tf)} reads ${H(f.aware, pct)} instead of ${H(f.none, pct)} with no batteries.`;
      }
      return `One home's short spike${f.driver ? ` (${esc(f.driver)})` : ''} takes ${tfn(f.tf)} to ${H(f.none, pct)}, over its nameplate for ${H(f.minutes, { unit: ' min' })}. Amber, not a failure${branch === 'naive' ? '; no battery helps in this branch' : ''}.`;
    case 'unrelieved':
      return `${tfn(f.tf)} has no battery: one home's spike takes it to ${H(f.peak, pct)}. Where should the next battery go? See P2.`;
    case 'sell':
      return branch === 'naive'
        ? `Power is expensive (${H(f.price, usd)}): the market plan sells, and all ${H(f.d)} batteries send power out at once (no feeder check ${naiveTag}).`
        : `Power is expensive (${H(f.price, usd)}): the market plan sells, but each transformer only sends back what fits.`;
    case 'backfeed':
      return `All ${H(f.d)} batteries sell at once (no feeder check ${naiveTag}): ${tfn(f.tf)} is overloaded in reverse at ${H(f.pct, pct)}. Back-feed is an overload too.`;
    case 'sellcap':
      return `The market plan sells, but each transformer only sends back what fits: the highest loading while selling is ${H(f.pct, pct)} (${tfn(f.tf)}).`;
    case 'peak':
      return `The price peaks at ${H(f.price, usd)}.${f.cash ? ` Batteries have earned ${H(f.cash, { money: true, digits: 2 })} so far tonight (gross, not Base's profit).` : ''}${branch === 'none' ? ' With no batteries, nothing on the street reacts.' : ''}`;
    case 'drop':
      return `The price falls to ${H(f.price, usd)}${f.ratio ? `, ${esc(f.ratio)} of the peak` : ''}: the charge signal.`;
    case 'nothing':
      return `The price falls to ${H(f.price, usd)}. No batteries, so nothing charges: nothing on the street changes.`;
    case 'allcharge': {
      const ov = f.overload ? ` ${nvH(fmt, f.overload.over)} transformers go over 110% and ${nvH(fmt, f.overload.emerg)} past their emergency rating ${fmt.chip(f.overload.over.label, 'OpenDSS tier codes')}.` : '';
      return `Every battery charges at once: ${H(f.c)} of ${nvH(fmt, L(f.fleet, 'REAL', 'Base fleet on this feeder (data/fleet.json)'))} (the naive rule ${naiveTag}).${ov}`;
    }
    case 'overload':
      return `${nvH(fmt, f.over)} transformers go over 110% at once, ${nvH(fmt, f.emerg)} past their emergency rating ${fmt.chip(f.over.label, 'OpenDSS tier codes')}. ${tfn(f.tf)} reaches ${H(f.pct, pct)}: ${esc(whoPhrase(f.pct.v))}.`;
    case 'worst':
      return `${tfn(f.tf)} peaks at ${H(f.pct, pct)}: ${esc(whoPhrase(f.pct.v))}.${f.ruleMin ? ` Over 110% for ${H(f.ruleMin, { unit: ' minutes' })} counts as a violation.` : ''}`;
    case 'clear':
      return `Every transformer is back under 110%. Tonight's cost: ${H(f.normal)} normal-rating violations and ${H(f.emerg)} emergencies, all caused by batteries.`;
    case 'check':
      return `Room checked first: ${H(f.c)} of ${nvH(fmt, L(f.fleet, 'REAL', 'Base fleet on this feeder (data/fleet.json)'))} batteries may charge now; ${H(f.i)} wait their turn.${f.deferred ? ` Feeder-aware held back ${H(f.deferred, { unit: ' kW', digits: 1 })} at the onset.` : ''}`;
    case 'turns':
      return 'Batteries take turns: when one battery\'s turn ends, the next on the same transformer starts.';
    case 'charged':
      if (branch === 'naive') return `Batteries full: ${H(f.by0400, { unit: '%', digits: 1 })} charged by 04:00.`;
      return `Charged ${H(f.by0400, { unit: '%', digits: 1 })} by 04:00, and ${nvH(fmt, f.normal && f.emerg ? L(f.normal.v + f.emerg.v, f.normal.label, 'battery-caused normal + emergency events') : f.normal)} battery-caused overloads all evening ${fmt.chip((f.normal && f.normal.label) || 'SIM', 'OpenDSS')}.`;
    case 'comms_lost': {
      const e = f.e;
      const by = (e.coveredBy || []).map((h) => names.home(h)).join(' and ');
      return `The battery at ${esc(names.home(e.home))} stops answering while holding a ${H(L(e.cmdKW, 'SIM', 'its last command'), { unit: ' kW', digits: 1, signed: true })} command (timing ${fmt.chip('ASSUMPTION', 'FAULT_COMMS_AFTER_MIN')}).${by && Number.isInteger(e.coveredStep) ? ` From ${H(L(names.time(e.coveredStep), 'SIM', 'coveredStep'))} ${esc(by)} take up its share.` : ''}`;
    }
    case 'hot': {
      const e = f.e;
      return `${esc(names.home(e.home))} plugs in an EV: ${H(L(e.deltaKW, 'ASSUMPTION', 'EV_KW: a Level 2 EV'), { unit: ' kW', digits: 1, signed: true })} for ${H(L(e.minutes, 'ASSUMPTION', 'HOT_MINUTES'), { unit: ' min' })} on ${tfn(e.tf)}. The controller sees less room there and sends less.`;
    }
    case 'stall':
      return `Our controller stalls for ${H(L(f.e.minutes, 'ASSUMPTION', 'STALL_MIN'), { unit: ' min' })}. Every battery's command expires on schedule, so they stop and wait safely.`;
    case 'resume':
      return 'The controller is back; charging resumes where there is room.';
    default:
      return '';
  }
}
const nvH = (fmt, x, o) => (x && fmt.isLabelled(x) ? nv(fmt, x, o) : '');

/** The small value under a lit chain step (empty while ghosted, so a future number is never revealed). */
export function chainValue(c, fmt, names, branch, lit, doneCue) {
  if (!c || !lit) return '';
  const f = c.facts || {};
  switch (c.id) {
    case 'drop': case 'nothing': return f.price ? fmt.fmtHTML(f.price, { money: true, digits: 2, unit: '/MWh' }) : '';
    case 'peak': return f.price ? fmt.fmtHTML(f.price, { money: true, digits: 2, unit: '/MWh' }) : '';
    case 'spike': return f.none ? `${esc(names.tf(f.tf))} ${fmt.fmtHTML(f.none, { unit: '%', digits: 1 })}` : '';
    case 'allcharge': return `${nv(fmt, f.c)}/${nv(fmt, L(f.fleet, 'REAL'))} ${fmt.chip('ASSUMPTION', NAIVE_FRAMING)}`;
    case 'overload': return `${esc(names.tf(f.tf))} ${fmt.fmtHTML(f.pct, { unit: '%', digits: 1 })}`;
    case 'check': return `${nv(fmt, f.c)}/${nv(fmt, L(f.fleet, 'REAL'))} ${fmt.chip(f.c.label, 'batteries charging at the onset')}`;
    case 'turns': return doneCue ? `${nv(fmt, doneCue.facts.normal && doneCue.facts.emerg ? L(doneCue.facts.normal.v + doneCue.facts.emerg.v, doneCue.facts.normal.label) : L(0, 'SIM'))} caused by batteries ${fmt.chip('SIM', 'OpenDSS: battery-caused normal + emergency events, whole evening')}` : '';
    case 'comms_lost': case 'hot': case 'stall': return fmt.fmtHTML(L(c.t, 'ASSUMPTION', 'scripted failure time (named constant)'));
    default: return '';
  }
}

/** The active cue at step k: the latest with k0 <= k < min(next.k, k0 + HOLD_STEPS), or null (silence is allowed). */
export function activeCue(cues, k) {
  let a = null;
  for (const c of cues) if (c.k <= k) a = c;
  if (!a || k >= a.k + HOLD_STEPS) return null;
  return a;
}

/** x-positions and icons of the strip markers: the story cues, the price peak, each contiguous market discharge group,
 *  and the branch's failure events (UX_SPEC_R2 6.4: 18 px icons, no text; hover shows the full text). */
export function stripMarks(meta, branch, fmt, cues = []) {
  const out = [];
  const stepSec = meta.stepSeconds || 60;
  // contiguous discharge groups from the market plan (DERIVED): one icon per group
  const iv = ((meta.plan && meta.plan.discharge) || []).map(([t, m]) => [fmt.timeToStep(meta, t), m * 60 / stepSec]).filter((x) => x[0] !== null).sort((a, b) => a[0] - b[0]);
  const groups = [];
  for (const [k0, len] of iv) {
    const g = groups[groups.length - 1];
    if (g && k0 <= g.k1 + 1) g.k1 = Math.max(g.k1, k0 + len); else groups.push({ k0, k1: k0 + len });
  }
  for (const g of groups) out.push({ k: g.k0, icon: 'out', kind: 'plan', label: 'DERIVED', text: `${fmt.stepToTime(meta, g.k0)}–${fmt.stepToTime(meta, Math.min(meta.steps - 1, g.k1))} batteries sell into the price peak (market plan)` });
  // a marker that restates a failure event belongs to that event's branch only (added below from meta.events)
  const evKeys = new Set();
  for (const list of Object.values(meta.events || {})) for (const e of list || []) evKeys.add(`${e.t}|${e.text || ''}`);
  for (const m of meta.markers || []) {
    const k = fmt.timeToStep(meta, m.t);
    if (k === null || /market discharge/.test(m.text) || evKeys.has(`${m.t}|${m.text}`)) continue;
    const icon = /price peak/.test(m.text) ? 'priceUp' : /onset/.test(m.text) ? 'priceDown' : /spike|peaks at/.test(m.text) ? 'house' : 'info';
    out.push({ k, icon, kind: 'marker', label: m.label || 'SIM', text: `${m.t} ${m.text}` });
  }
  for (const e of (meta.events && meta.events[branch]) || []) {
    out.push({ k: e.step, icon: e.kind === 'comms_lost' ? 'silent' : e.kind === 'hot' ? 'hot' : e.kind === 'stall' ? 'stall' : 'warn', kind: 'fault', label: 'ASSUMPTION', text: `${e.t} ${e.text || e.kind}` });
  }
  for (const c of cues) {
    if (c.chain === null) continue;
    if (out.some((m) => Math.abs(m.k - c.k) <= 4 && m.icon === c.icon)) continue;
    out.push({ k: c.k, icon: c.icon, kind: 'cue', label: 'SIM', text: `${c.t} ${(CHAINS[branch] || [])[c.chain][2]}`, tone: c.tone });
  }
  return out.sort((a, b) => a.k - b.k);
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
  normalEvents: 'Normal-rating violations (>110% for >= 30 min)', emergencyTfs: 'Transformers in emergency (>150%)',
  batteryCausedNormal: 'Caused by batteries: normal-rating violations', batteryCausedEmergency: 'Caused by batteries: emergencies',
  batteryCausedAmberMin: 'Caused by batteries: transformer-minutes over nameplate', homeOnlyOver100: 'Over nameplate on home load alone',
  protectionOperated: 'Fuses opened (fuse rule, ASSUMPTION)', homesDark: 'Homes dark', homesOnBattery: 'Homes powered by their own battery',
  maxLoading: 'Worst transformer', reserveBreaches: '20% reserve breaches', chargedPctBy0400: 'Fleet charged by 04:00',
  energyValueUSD: 'Money earned from the price difference (before costs; not Base\'s profit)', costOfAwareness: 'Cost of awareness (naive minus aware)',
  vMinHome: 'Lowest home voltage', homesBelow095: 'Homes below 0.95 pu', feederHead: 'Feeder cable (first primary)',
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

/** Format options for a percentage: 0 decimals from 10, 1 decimal from 0.1, else 2 significant figures. */
export function pctOpts(v) {
  const a = Math.abs(Number(v));
  if (!Number.isFinite(a) || a === 0) return { unit: '%', digits: 0 };
  if (a >= 10) return { unit: '%', digits: a === Math.round(a) ? 0 : 1 };
  if (a >= 0.1) return { unit: '%', digits: 1 };
  return { unit: '%', digits: Math.min(20, 1 - Math.floor(Math.log10(a))) };
}

const ID_KEYS = new Set(['rank', 'home', 'tf', 'step', 'k', 'n', 'index', 'of', 'runs', 'minute', 'seq', 'batt']);

/** Generic HTML for a labelled tree (money, ladder, anything L2 adds): labelled values get their tag, strings are
 *  text, id counters are plain, and a bare number anywhere else throws (format.js), raising data-errors. */
export function labelledTreeHTML(fmt, x, key = '', depth = 0, inherit = '') {
  if (x === null || x === undefined) return '';
  let own = Object.keys(optsFor(key)).length ? key : inherit;
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
    const o = optsFor(own);
    const small = o.unit === '%' && typeof x.v === 'number' && x.v !== 0 && Math.abs(x.v) < 0.1;
    return `${fmt.fmtHTML(x, small ? pctOpts(x.v) : o)}${extras ? ` <span class="hb-sub">${extras}</span>` : ''}`;
  }
  const rows = Object.entries(x).map(([k, v]) =>
    `<div class="p1-row"><span class="p1-k">${esc(humanKey(k))}</span><span class="p1-v">${labelledTreeHTML(fmt, v, k, depth + 1, own)}</span></div>`);
  return `<div class="p1-tree-obj depth-${depth}">${rows.join('')}</div>`;
}

/** A record with a label but no `v`: {text, label, cite} or {who, for, label, cite}: its strings, then one tag. */
export function isLabelledRecord(fmt, x) {
  return !!x && typeof x === 'object' && !Array.isArray(x) && !('v' in x) && fmt.LABELS.includes(x.label)
    && Object.entries(x).every(([k, v]) => k === 'label' || k === 'cite' || typeof v === 'string');
}
export function recordHTML(fmt, x) {
  const parts = Object.entries(x).filter(([k]) => k !== 'label' && k !== 'cite').map(([, v]) => v);
  return `<span class="p1-text">${esc(parts.join(': '))}</span> ${fmt.chip(x.label, x.cite)}`;
}

/** "Money tonight" (UX_SPEC_R2 6.2): each line labelled. The system-capacity band has LEFT P1 (audit M5; it stays on
 *  More, relabelled as a storage revenue benchmark that includes arbitrage). Local relief is never priced here.
 *  From checkpoint (b): sold / bought / net + per battery from `money.split`, when l2 ships it. */
export function moneyHTML(fmt, money, branch, branchNames = BRANCH_NAMES, consts = null, summary = null) {
  if (!money) return '';
  void consts;
  const done = new Set(['systemCapacityPerMonth', 'scaleLadder']);
  const out = [];
  const row = (k, v) => `<div class="p1-row"><span class="p1-k">${k}</span><span class="p1-v">${v}</span></div>`;
  const usd = (x) => fmt.fmtHTML(x, { money: true, digits: 2 });
  const sp = money.split && money.split[branch];
  if (money.split) done.add('split');
  if (sp && sp.net) {
    out.push(`<div class="p1-money-h">${svg('money', { size: 16 })} Tonight, ${esc(branchNames[branch] || branch)} <span class="hb-sub">(before costs; not Base's profit)</span></div>`);
    if (sp.sold) out.push(row(`${svg('priceUp', { size: 14 })} Sold into the evening peak`, usd(sp.sold)));
    if (sp.bought) out.push(row(`${svg('priceDown', { size: 14 })} Bought back when cheap`, usd(sp.bought)));
    out.push(row('Money earned from the price difference', usd(sp.net)));
    if (sp.perBattery) out.push(row('Per battery', usd(sp.perBattery)));
  }
  if (money.energyValueUSD && typeof money.energyValueUSD === 'object' && !fmt.isLabelled(money.energyValueUSD)) {
    done.add('energyValueUSD');
    out.push(`<div class="p1-money-h">Money earned from the price difference <span class="hb-sub">(before costs; not Base's profit)</span></div>`);
    out.push(Object.entries(money.energyValueUSD).map(([b, v]) => row(esc(branchNames[b] || b) + (b === branch ? ' ◂' : ''), usd(v))).join(''));
  }
  if (money.costOfAwareness) {
    done.add('costOfAwareness');
    const c = money.costOfAwareness;
    if (c.v !== null && c.v < 0) out.push(`<div class="p1-claim ok">${svg('check', { size: 15 })} Feeder-aware earned ${usd({ ...c, v: -c.v })} more than naive tonight: checking the street cost nothing.</div>`);
    out.push(row('Cost of awareness (naive minus aware)', usd(c)));
  }
  // L7: a branch note from l2 (for example the silent battery's lower end charge on aware + failures)
  const note = summary && summary[branch] && (summary[branch].note || summary[branch].energyNote);
  if (note) out.push(`<div class="p1-note">${typeof note === 'string' ? esc(note) : isLabelledRecord(fmt, note) ? recordHTML(fmt, note) : labelledTreeHTML(fmt, note)}</div>`);
  const r = money.relief;
  if (r && typeof r === 'object' && !fmt.isLabelled(r)) {
    done.add('relief');
    out.push('<div class="p1-money-h">Local relief</div>');
    if (r.kwh) out.push(row('Relief energy on A', fmt.fmtHTML(r.kwh, { unit: ' kWh', digits: 2 })));
    if (r.opportunityUpperUSD) out.push(row('Upper-bound opportunity cost', usd(r.opportunityUpperUSD)));
    if (r.priced) out.push(row('Paid for today?', `not paid for today ${fmt.chip(r.priced.label, r.priced.cite)}`));
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
    const heads = ['violations', 'emergencies', 'fuses'];
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

/** Log-scale bar length (0..1) for a share given in percent (display only). */
export const LADDER_LOG_LO = -7;
export const LADDER_LOG_HI = 0.35;
export function ladderFrac(sharePct) {
  const f = Math.max(Number(sharePct) / 100, 10 ** (LADDER_LOG_LO - 1));
  return Math.max(0.01, Math.min(1, (Math.log10(f) - LADDER_LOG_LO) / (LADDER_LOG_HI - LADDER_LOG_LO)));
}
export const LADDER_AXIS = [[1e-7, '0.00001%'], [1e-5, '0.001%'], [1e-3, '0.1%'], [1e-1, '10%'], [1, '100%']];

/** "How big is this?" (build prompt 3.4): the same kW at three scales, each rung its words, its share, a log bar and its
 *  base with the base's label. Every number carries its label. */
export function ladderHTML(fmt, ladder) {
  if (!ladder || !Array.isArray(ladder.rungs)) return '';
  const base = (b) => (b && fmt.isLabelled(b) ? fmt.chip(b.label, `base ${fmt.fmtValue(b, { unit: b.unit ? ` ${b.unit}` : '', digits: Number.isInteger(b.v) ? 0 : 1 })}: ${b.cite || ''}`) : '');
  const rungs = ladder.rungs.map((r) => {
    const s = r.sharePct;
    const val = s ? fmt.fmtHTML(s, pctOpts(s.v)) : '';
    const w = s && typeof s.v === 'number' ? (100 * ladderFrac(s.v)).toFixed(1) : '0';
    return `<div class="p1-rung p1-rung-${esc(r.scale || '')}">
      <div class="p1-rung-top"><span class="p1-rung-name">${esc(r.name || r.scale || '')}</span><span class="p1-rung-val">${val}</span></div>
      <div class="p1-rung-bar" aria-hidden="true"><i style="width:${w}%"></i></div>
      <div class="p1-rung-text">${esc(r.text || '')} ${base(r.base)}</div>
    </div>`;
  }).join('');
  const kw = ladder.kw && fmt.isLabelled(ladder.kw) ? ` ${fmt.chip(ladder.kw.label, ladder.kw.cite)}` : '';
  const head = kw ? String(ladder.text || '').replace(new RegExp(`\\s*\\(${ladder.kw.label}\\)\\s*$`), '') : String(ladder.text || '');
  const axis = LADDER_AXIS.map(([f, t]) => `<span style="left:${(100 * ladderFrac(f * 100)).toFixed(1)}%">${t}</span>`).join('');
  return `<div class="p1-ladder-h">${esc(head)}${kw}</div>${rungs}
    <div class="p1-rung-axis" aria-hidden="true">${axis}</div>
    <div class="hb-sub">Bar length on a log scale (display only).</div>`;
}

/** "Voltage and feeder cable" (build prompt 7.3): measured, never asserted. */
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
    parts.push(`<div>Feeder cable max ${fmt.fmtHTML(L(h.v, h.label, h.cite), { unit: '%', digits: 1 })} of ${rating}${amps ? ` (${amps}${h.t ? ' at ' + esc(h.t) : ''})` : ''}</div>`);
  }
  return parts.join('');
}

/** The cause of a transformer's load now (clarity 4.5 rules, in order). HTML, with an icon. */
export function nowWhy(fmt, meta, doc, topology, tf, k, homeLabel) {
  const code = Number(doc.tier[k][tf]);
  const nBat = (topology.fleet || []).filter((hi) => topology.homes[hi].tf === tf).length;
  const bat = tfBatKW(doc, topology, tf, k);
  const exporting = (doc.reverse || []).some((r) => r[0] === k && r[1] === tf);
  if (code === 5) return `${svg('fuse', { size: 15 })} its fuse opened (fuse rule ${fmt.chip('ASSUMPTION', meta.protection && meta.protection.cite)})`;
  if (nBat && bat > 0.5) return `${svg('bolt', { size: 15 })} its ${nBat === 1 ? 'battery is' : 'batteries are'} charging`;
  if (nBat && exporting) return `${svg('out', { size: 15 })} its batteries are sending power back (back-feed)`;
  if (nBat && bat < -0.5) return `${svg('out', { size: 15 })} its batteries are discharging to help (relief)`;
  if (!nBat) {
    const d = spikeDriverAt(meta, fmt, tf, k);
    return `${svg('house', { size: 15 })} homes only: no battery here${d ? `; one home's short spike (${esc(d.driver.label || homeLabel(d.driver.home))})` : ''}`;
  }
  return `${svg('house', { size: 15 })} its homes' own load; its batteries are ${bat > 0.05 ? 'charging a little' : 'waiting'}`;
}

/** The transformer tooltip (3D objects, street columns): at most five short lines, every number labelled. */
export function tfTipHTML(fmt, meta, doc, topology, sceneModel, tf, k, names) {
  const t = topology.transformers[tf];
  const lab = seriesLabel(doc, 'loading', 'SIM');
  const pct = doc.loading[k][tf] / 10, code = Number(doc.tier[k][tf]);
  const mount = t.mount === 'pole' ? 'pole' : 'pad';
  const mountTag = t.mount ? fmt.chip('DERIVED', 'SMART-DS Lines.dss secondary linecodes; an overhead secondary means a pole (ASSUMPTION)') : fmt.chip('ASSUMPTION', 'mount type not in topology.json yet: drawn as a pad-mount');
  const homes = t.homes.length;
  const bats = (topology.fleet || []).filter((hi) => topology.homes[hi].tf === tf).length;
  const key = Object.entries(doc.focus || {}).find(([, f]) => f.tf === tf);
  const lines = [];
  lines.push(`<div class="tip-h">${svg(mount === 'pole' ? 'polemount' : 'padmount', { size: 16 })} Transformer ${esc(names.tf(tf))} · ${mount === 'pole' ? 'on a pole' : 'pad-mount'} ${mountTag} · ${fmt.fmtHTML(L(t.kva, 'REAL', 'SMART-DS kVA'), { unit: ' kVA' })}</div>`);
  lines.push(`<div>${homes} ${homes === 1 ? 'home' : 'homes'}, ${bats ? `${bats} with a Base battery` : 'no battery'}</div>`);
  lines.push(`<div class="tip-now">${svg('meter', { size: 18, pct, tier: code })} Now <b>${fmt.fmtHTML(L(+pct.toFixed(1), lab, 'OpenDSS loading, % of nameplate'), { unit: '%', digits: 1 })}</b> of its rating: <b>${esc(TIER_WORDS[code] || '')}</b>. ${esc(TIER_TIPS[code] || '')}</div>`);
  if (key) {
    const g = gaugeModel(meta, doc, topology, key[0], k, sceneModel.roomKW, sceneModel.exportRoomKW);
    const flab = seriesLabel(doc, 'focus', 'SIM');
    const room = g.open ? 'fuse open' : g.pct > 100
      ? `over by ${fmt.fmtHTML(L(+((g.pct / 100 - 1) * g.kva).toFixed(1), 'DERIVED', 'OpenDSS loading above 100%, times kVA'), { unit: ' kVA', digits: 1 })}`
      : g.exporting && g.exportRoom !== null
        ? `room to export ${fmt.fmtHTML(L(+Math.max(0, g.exportRoom).toFixed(1), 'DERIVED', 'kW of back-feed that still fits under nameplate while exporting (unity-pf batteries)'), { unit: ' kW', digits: 1 })}`
        : `room ${fmt.fmtHTML(L(+Math.max(0, g.room).toFixed(1), 'DERIVED', 'kW of charge that still fits under nameplate (unity-pf batteries)'), { unit: ' kW', digits: 1 })}`;
    lines.push(`<div>homes ${nv(fmt, L(+g.homeKW.toFixed(1), flab), { unit: ' kW', digits: 1 })} + batteries ${nv(fmt, L(+g.batKW.toFixed(1), flab), { unit: ' kW', digits: 1, signed: true })} ${fmt.chip(flab, 'metered kW at the homes')} · ${room}</div>`);
    lines.push(`<div class="tip-what">This evening: highest ${nv(fmt, L(+g.maxPct.toFixed(1), lab), { unit: '%', digits: 1 })} at ${esc(fmt.stepToTime(meta, g.maxStep))}; ${nv(fmt, L(g.min110, lab), { unit: ' min' })} over 110% ${fmt.chip(lab, 'OpenDSS loading; minutes at tier codes 2-4')}</div>`);
  } else if (bats) {
    const b = tfBatKW(doc, topology, tf, k);
    lines.push(`<div>its batteries ${fmt.fmtHTML(L(+b.toFixed(1), seriesLabel(doc, 'batKW', 'SIM'), 'sum of battery kW on this transformer'), { unit: ' kW', digits: 1, signed: true })}</div>`);
  }
  return lines.join('');
}

/** The battery tooltip (3D cabinet or icon, street battery icons). */
export function batteryTipHTML(fmt, meta, doc, topology, j, k, names, branch) {
  const hi = topology.fleet[j];
  const h = topology.homes[hi];
  const lines = [`<div class="tip-h">${svg('cabinet', { size: 16 })} Base battery at ${esc(h.label)} · on ${esc(names.tf(h.tf))}</div>`];
  if (branch === 'none') {
    lines.push('<div>Switched off in this scenario (no batteries).</div>');
  } else {
    const st = doc.state[k][j], kw = doc.batKW[k][j] / 10, soc = doc.soc[k][j] / 10;
    const lab = seriesLabel(doc, 'batKW', 'SIM');
    const word = STATE_WORDS[st] || st;
    const kwTxt = Math.abs(kw) >= 0.05 ? ` ${fmt.fmtHTML(L(+kw.toFixed(1), lab, 'battery kW (+ charging, - sending out)'), { unit: ' kW', digits: 1, signed: true })}` : '';
    lines.push(`<div class="tip-now">${svg('battery', { size: 20, level: soc / 100, state: st })} <b>${esc(word)}</b>${kwTxt} · ${fmt.fmtHTML(L(Math.round(soc), seriesLabel(doc, 'soc', 'SIM'), 'state of charge'), { unit: '% full' })}</div>`);
    if (st === 'S') lines.push('<div>No signal for 3+ minutes; it stops on its own when its command expires (5 min).</div>');
    if (st === 'X') lines.push('<div>Its command expired: it waits, backup armed.</div>');
    if (st === 'I' && (branch === 'aware' || branch === 'aware_faults') && meta.plan && k >= fmt.timeToStep(meta, meta.plan.onset)) lines.push('<div class="tip-what">Waiting: the controller sends charge only where it fits.</div>');
  }
  lines.push(`<div class="tip-what">It keeps 20% for backup (Base's reserve ${fmt.chip('REAL', 'Base member reserve, 20% (build prompt 4.1)')}).</div>`);
  return lines.join('');
}

/** The home tooltip. */
export function homeTipHTML(fmt, topology, footprints, hi, names, state, battery) {
  const h = topology.homes[hi];
  const fp = footprints && footprints.homes && footprints.homes[h.id];
  const lines = [`<div class="tip-h">${svg('house', { size: 16 })} ${esc(h.label)} · on transformer ${esc(names.tf(h.tf))}</div>`];
  lines.push(`<div>${battery ? 'Has a Base battery.' : 'No battery.'} ${h.district ? `${esc(h.district)} (fictional name)` : ''}</div>`);
  lines.push(`<div class="tip-now">Now: ${state === 'dark' ? `<b>lights out</b>: its transformer's fuse opened ${fmt.chip('ASSUMPTION', 'fuse rule')}` : state === 'battery' ? `<b>running on its own battery</b> ${fmt.chip('SIM')}` : 'lights on'}</div>`);
  lines.push(`<div class="tip-what">${fp ? `Footprint © OpenStreetMap ${fmt.chip('REAL', 'ODbL 1.0')}; roof and height drawn for recognition ${fmt.chip('ASSUMPTION', 'display only')}` : `No OSM footprint: drawn as a 12 m square ${fmt.chip('ASSUMPTION', 'FOOTPRINT_MISSING_M')}`}</div>`);
  return lines.join('');
}

// ---------------------------------------------------------------------------------------------------------------
/** A minimal tooltip for when ui/lib/tip.js is not there (the same behaviour: [data-tip], [data-tip-html], .chip). */
function localTips(doc) {
  let el = doc.querySelector('.hb-tip');
  if (!el) { el = doc.createElement('div'); el.className = 'hb-tip'; el.setAttribute('role', 'tooltip'); el.hidden = true; doc.body.appendChild(el); }
  const show = (html, x, y) => {
    el.innerHTML = html; el.hidden = false;
    const w = el.offsetWidth, h = el.offsetHeight;
    const X = x + 14 + w > window.innerWidth ? x - 14 - w : x + 14, Y = y + 14 + h > window.innerHeight ? y - 14 - h : y + 14;
    el.style.left = `${Math.max(4, X)}px`; el.style.top = `${Math.max(4, Y)}px`;
  };
  const hide = () => { el.hidden = true; };
  const LABEL = { REAL: 'REAL: measured or published data.', SIM: 'SIM: our simulation (OpenDSS + our controller). Not a measurement.', DERIVED: 'DERIVED: arithmetic on REAL or SIM numbers.', ASSUMPTION: 'ASSUMPTION: a value we chose because the real one is not public.' };
  const htmlFor = (t) => {
    if (t.dataset.tipHtml) return t.dataset.tipHtml;
    if (t.dataset.tip) return esc(t.dataset.tip);
    if (t.classList.contains('chip')) {
      const lab = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'].find((x) => t.classList.contains('chip-' + x));
      const cite = t.dataset.cite || t.getAttribute('title') || '';
      if (t.hasAttribute('title')) { t.dataset.cite = cite; t.removeAttribute('title'); }
      return `<b>${esc(LABEL[lab] || lab || '')}</b>${cite ? `<br>${esc(cite)}` : ''}`;
    }
    return '';
  };
  doc.addEventListener('pointerover', (ev) => {
    const t = ev.target.closest && ev.target.closest('[data-tip],[data-tip-html],.chip');
    if (!t) return;
    const html = htmlFor(t);
    if (html) show(html, ev.clientX, ev.clientY);
  });
  doc.addEventListener('pointerout', (ev) => { const t = ev.target.closest && ev.target.closest('[data-tip],[data-tip-html],.chip'); if (t) hide(); });
  doc.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') hide(); });
  return { showTip: show, hideTip: hide };
}
async function loadTips() {
  try {
    const t = await import('../lib/tip.js');
    if (typeof t.mountTips === 'function') t.mountTips(document);
    if (typeof t.showTip === 'function' && typeof t.hideTip === 'function') return { showTip: t.showTip, hideTip: t.hideTip };
  } catch (e) { /* tip.js not there yet: the local one */ }
  return localTips(document);
}
const store = {
  get(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* private window: no memory, same page */ } },
};

export async function mount(el, ctx) {
  const { data, fmt, sceneModel, scene, topology } = ctx;
  const link = ctx.link;
  const search = typeof location !== 'undefined' ? location.search : '';
  const q = new URLSearchParams(search);
  const bare = isBare(link, search);
  const meta = await data.loadP1Meta();
  const branches = meta.branches;
  let branch = bare ? 'naive' : (branches.includes(link.branch) ? link.branch : branches[0]);
  const docs = {};
  const loadDoc = async (b) => (docs[b] || (docs[b] = await data.loadP1Branch(b)));
  let doc = await loadDoc(branch);
  let k = initialStep(meta, link, fmt, bare);
  const linkSpeed = Number(link.speed || q.get('speed'));
  let speed = SPEEDS.includes(linkSpeed) ? linkSpeed : DEFAULT_SPEED;
  let hold = link.hold === false ? false : q.get('hold') !== '0';
  let showCap = link.cap === false ? false : q.get('cap') !== '0';
  let playing = false, acc = 0, last = 0, holdUntil = 0;
  let held = new Set();
  const stepSec = meta.stepSeconds || 60;
  const tips = await loadTips();
  const tfName = (tf) => {
    const f = (topology.focus || []).find((x) => x.tf === tf);
    return f ? f.key : `T-${tf}`;
  };
  const homeLabel = (h) => {
    if (typeof h === 'number') return topology.homes[h] ? topology.homes[h].label : `home ${h}`;
    if (h && typeof h === 'object') {
      const lab = h.label || (typeof h.home === 'number' && topology.homes[h.home] ? topology.homes[h.home].label : 'a home');
      return h.tf !== undefined && h.tf !== null ? `${lab} on ${tfName(h.tf)}` : lab;
    }
    return String(h);
  };
  const names = { tf: tfName, home: homeLabel, time: (s) => fmt.stepToTime(meta, s) };
  const priceLabel = seriesLabel(meta, 'price', 'REAL');
  let cues = storyCues(meta, doc, branch, topology, fmt);
  const beatSec = link.beat ? BEAT_SECTIONS[link.beat] : null;

  // ---- static panel skeleton ----
  el.classList.add('p1');
  const secOpen = (id) => (id === beatSec) || (id === 'faults' && branch === 'aware_faults') || store.get('hb.sec.' + id) === '1';
  const sec = (id, icon, title) => `<details class="hb-sec p1-sec" id="sec-${id}" data-sec="${id}"${secOpen(id) ? ' open' : ''}>
      <summary><span class="sec-ic">${svg(icon, { size: 16 })}</span><span class="sec-t" id="sec-${id}-t">${esc(title)}</span><span class="sec-teaser" id="sec-${id}-teaser"></span></summary>
      <div class="sec-body" id="sec-${id}-body"></div></details>`;
  el.innerHTML = `
    <section class="p1-card p1-daycard">
      <div class="p1-day" id="p1-day"></div>
      <nav class="p1-scn" role="tablist">${branches.map((b) => `<a href="${ctx.href({ branch: b, t: fmt.stepToTime(meta, k) })}" data-branch="${b}" aria-current="${b === branch}" data-tip="${esc(TAB_LINES[b] || '')}">${svg(TAB_ICONS[b] || 'info', { size: 16, level: 0.7, state: 'I' })}<span>${esc(TAB_NAMES[b] || b)}</span>${b === 'naive' ? fmt.chip('ASSUMPTION', NAIVE_FRAMING) : ''}<span class="scn-out" id="scn-out-${b}"></span></a>`).join('')}</nav>
      <p class="p1-scn-sub" id="p1-scn-sub"></p>
    </section>
    <section class="p1-card p1-now" id="p1-now" aria-live="polite"></section>
    <section class="p1-card p1-fleet" id="p1-fleet"></section>
    <section class="p1-card p1-street"><div class="p1-street-h">Street A–D · T-240 <span class="ic-help" tabindex="0" data-tip="Four transformers side by side on one street, and T-240 (no battery). The box is 100% of its rating; sticking out of the top is overload. Grey = the homes' load, teal = batteries charging, violet = sending power back. Hover a column for its numbers.">${svg('info', { size: 14 })}</span></div><div class="street" id="p1-streetcols"></div></section>
    ${sec('money', 'money', 'Money tonight')}
    ${sec('evening', 'check', 'How the evening ended')}
    ${sec('faults', 'warn', 'Failures')}
    ${sec('relief', 'house', 'Batteries helped')}
    ${sec('unrel', 'arrowRight', 'Still at risk → P2')}
    ${sec('street', 'meter', 'Street A–D in numbers')}
    ${sec('grid', 'gauge', 'Voltage and feeder cable')}
    ${sec('scale', 'ruler', 'How big is this?')}
    ${sec('log', 'log', 'Controller log')}
    ${sec('sources', 'book', 'Sources and assumptions')}`;
  const $ = (id) => el.querySelector('#' + id);
  // A closed section holds its HTML aside and renders it only when opened: what is not visible is not in the page (the
  // clutter metric and the reader see the same thing), and a playing clock never rebuilds hidden tables.
  const pendingBody = {};
  const bodyOf = (id) => ({
    set innerHTML(html) {
      const d = $(`sec-${id}`), b = $(`sec-${id}-body`);
      if (d && d.open) { b.innerHTML = html; delete pendingBody[id]; } else { pendingBody[id] = html; if (b.firstChild) b.innerHTML = ''; }
    },
  });
  for (const d of el.querySelectorAll('details.hb-sec')) {
    d.addEventListener('toggle', () => {
      store.set('hb.sec.' + d.dataset.sec, d.open ? '1' : '0');
      if (d.open && pendingBody[d.dataset.sec] !== undefined) { $(`sec-${d.dataset.sec}-body`).innerHTML = pendingBody[d.dataset.sec]; delete pendingBody[d.dataset.sec]; }
    });
  }

  // ---- overlays on the scene: story, camera buttons, legend, credits, transport, intro ----
  for (const old of document.querySelectorAll('.p1-overlay')) old.remove();
  const story = document.createElement('div');
  story.className = 'p1-overlay p1-story';
  story.innerHTML = '<div class="chain" id="p1-chain"></div><div class="story-line" id="p1-line"></div>';
  const cams = document.createElement('div');
  cams.className = 'p1-overlay p1-cams';
  const CAMS = [['street', 'street', 'Street A–D', 'The four transformers side by side on one street'], ['t240', 'target', 'T-240 (no battery)', 'T-240: the transformer with no battery'], ['feeder', 'feeder', 'Whole feeder', 'All 379 transformers of the feeder']];
  cams.innerHTML = CAMS.map(([c, ic, t, tip]) => `<button type="button" data-cam="${c}" data-tip="${esc(tip)}"${(link.cam || (bare ? 'street' : null)) === c ? ' aria-pressed="true"' : ''}>${svg(ic, { size: 15 })}<span>${t}</span></button>`).join('');
  const legend = document.createElement('div');
  legend.className = 'p1-overlay p1-legend';
  const credits = document.createElement('div');
  credits.className = 'p1-overlay p1-credits';
  const fm = ctx.footprints && ctx.footprints.meta;
  credits.innerHTML = `© OpenStreetMap contributors (ODbL) · NREL SMART-DS · ERCOT <span class="ic-help" tabindex="0" data-tip-html="${esc(`Buildings © OpenStreetMap contributors, ODbL 1.0${fm && fm.matched ? ` (${fmt.fmtHTML(fm.matched)} of the feeder's homes matched; the rest are 12 m boxes ${fmt.chip('ASSUMPTION')})` : ''}.<br>Feeder: NREL SMART-DS 2018 AUS P1U, CC BY 4.0.<br>Prices: ERCOT RTM settlement point prices, LZ_NORTH (recorded; not live).`)}">${svg('info', { size: 12 })}</span>`;
  const transport = document.createElement('div');
  transport.className = 'p1-overlay p1-transport';
  transport.innerHTML = `
    <div class="tp-left">
      <div class="tp-row">
        <button type="button" class="tp-b" data-step="-1" data-tip="Back 1 minute (←, Shift = 10 min)">${svg('stepBack', { size: 16 })}</button>
        <button type="button" class="p1-play" id="p1-play" aria-label="play" data-tip="Play / pause (Space)">${svg('play', { size: 20 })}</button>
        <button type="button" class="tp-b" data-step="1" data-tip="Forward 1 minute (→, Shift = 10 min)">${svg('stepFwd', { size: 16 })}</button>
        <button type="button" class="tp-ev" data-cue="-1" data-tip="Previous story moment (,)">⟨ moment</button><button type="button" class="tp-ev" data-cue="1" data-tip="Next story moment (.)">moment ⟩</button>
      </div>
      <div class="tp-row">
        <div class="tp-speed" role="radiogroup" aria-label="speed">${SPEEDS.map((s) => `<button type="button" data-speed="${s}" aria-pressed="${s === speed}" data-tip="${esc(SPEED_TIPS[s])}">${s}×</button>`).join('')}</div>
        <label class="tp-hold" data-tip="Pause for a moment at each story step, then carry on"><input type="checkbox" id="p1-hold"${hold ? ' checked' : ''}> hold</label>
        <button type="button" class="tp-cc" id="p1-cc" aria-pressed="${showCap}" data-tip="Show or hide the story line (for clean takes)">CC</button>
      </div>
    </div>
    <div class="p1-clock"><div class="p1-time" id="p1-time"></div><div class="p1-date" id="p1-date"></div><div class="p1-price" id="p1-price"></div><div class="p1-cash" id="p1-cash" hidden></div></div>
    <div class="p1-strip-wrap"><canvas id="p1-strip" class="p1-strip"></canvas><div class="p1-strip-marks" id="p1-marks"></div><div class="strip-k">price ${fmt.chip(priceLabel, 'ERCOT RTM SPP LZ_NORTH')} · transformer trouble ${fmt.chip('SIM', 'the worst tier code present each minute (OpenDSS)')}</div></div>`;
  document.body.append(story, cams, legend, credits, transport);
  const strip = transport.querySelector('#p1-strip');
  const $marks = transport.querySelector('#p1-marks');
  let intro = null;

  // ---- rendering ----
  const L0 = (b) => seriesLabel(docs[b] || doc, 'loading', 'SIM');
  function renderStatic() {
    for (const a of el.querySelectorAll('.p1-scn a')) {
      const b = a.dataset.branch;
      a.setAttribute('aria-current', String(b === branch));
      a.href = ctx.href({ branch: b, t: fmt.stepToTime(meta, k) });
      const s = meta.summary && meta.summary[b];
      const out = $('scn-out-' + b);
      if (b === 'none' || !s || !s.batteryCausedNormal) { out.innerHTML = ''; continue; }
      const bad = (s.batteryCausedNormal.v || 0) + ((s.batteryCausedEmergency && s.batteryCausedEmergency.v) || 0) + ((s.protectionOperated && s.protectionOperated.v) || 0);
      const tip = bad > 0
        ? `Tonight in this scenario: batteries caused ${fmt.fmtHTML(s.batteryCausedNormal)} normal-rating violations and ${s.batteryCausedEmergency ? fmt.fmtHTML(s.batteryCausedEmergency) : ''} emergencies`
        : `Tonight in this scenario: no overload caused by batteries ${fmt.chip(s.batteryCausedNormal.label, s.batteryCausedNormal.cite)}`;
      out.className = `scn-out ${bad > 0 ? 'bad' : 'good'}`;
      out.dataset.tipHtml = tip;
      out.innerHTML = svg(bad > 0 ? 'warn' : 'check', { size: 14 });
    }
    $('p1-scn-sub').textContent = TAB_LINES[branch] || '';
    $('p1-day').innerHTML = `<span class="p1-daychip" data-tip="A real Texas day: ERCOT prices (REAL); home loads are the same calendar date in the 2018 SMART-DS year (ASSUMPTION).">${svg('calendar', { size: 16 })} ${esc(dayLabel(meta.day))} ${fmt.chip(priceLabel, 'ERCOT RTM SPP LZ_NORTH, recorded; the loads are the same calendar date in 2018 (ASSUMPTION)')}</span>`;
    cues = storyCues(meta, doc, branch, topology, fmt);
    renderSections();
    renderLegend();
    drawStrip();
  }

  function sectionTeasers() {
    const s = meta.summary && meta.summary[branch];
    const set = (id, html) => { const t = $(`sec-${id}-teaser`); if (t) t.innerHTML = html; };
    const hideSec = (id, h) => { const d = $(`sec-${id}`); if (d) d.hidden = h; };
    // money
    const sp = meta.money && meta.money.split && meta.money.split[branch];
    const ev = s && s.energyValueUSD;
    set('money', branch === 'none' ? 'no batteries' : sp && sp.net ? fmt.fmtHTML(sp.net, { money: true, digits: 2 }) : ev ? fmt.fmtHTML(ev, { money: true, digits: 2 }) : '');
    // evening
    if (s && s.batteryCausedNormal) {
      const bad = (s.batteryCausedNormal.v || 0) + ((s.batteryCausedEmergency && s.batteryCausedEmergency.v) || 0);
      set('evening', branch === 'none' ? `${svg('house', { size: 14 })} homes only`
        : bad > 0 ? `<span class="t-bad">${svg('warn', { size: 14 })}</span> ${nv(fmt, s.batteryCausedNormal)} violations · ${nv(fmt, s.batteryCausedEmergency || L(0, 'SIM'))} emergencies ${fmt.chip(s.batteryCausedNormal.label, 'caused by batteries (OpenDSS)')}`
          : `<span class="t-ok">${svg('check', { size: 14 })}</span> none caused by batteries ${fmt.chip(s.batteryCausedNormal.label, s.batteryCausedNormal.cite)}`);
    }
    // faults
    const evs = (meta.events && meta.events[branch]) || [];
    hideSec('faults', !evs.length);
    set('faults', evs.length ? `${evs.length === 3 ? 'three' : evs.length} failures: ${evs.map((e) => (e.kind === 'comms_lost' ? 'silent battery' : e.kind === 'hot' ? 'EV' : e.kind === 'stall' ? 'controller freeze' : e.kind)).join(' · ')}` : '');
    // relief (the feeder-aware branches)
    const r = meta.relief;
    const showRelief = !!r && (branch === 'aware' || branch === 'aware_faults');
    hideSec('relief', !showRelief);
    if (r) {
      $('sec-relief-t').textContent = `Batteries helped at ${r.t || ''}`;
      if (showRelief && r.none && r.aware) set('relief', `${esc(tfName(r.tf))}: ${nv(fmt, r.none, { unit: '%', digits: 1 })} → ${nv(fmt, r.aware, { unit: '%', digits: 1 })} ${fmt.chip(r.aware.label, 'OpenDSS, no batteries vs feeder-aware')}`);
    }
    // unrelieved
    const un = meta.unrelieved || [];
    hideSec('unrel', !un.length);
    if (un.length && un[0].peak) set('unrel', `${esc(tfName(un[0].tf))}: no battery, ${fmt.fmtHTML(un[0].peak, { unit: '%', digits: 1 })}`);
    // grid
    if (s && s.feederHead) {
      const ok = s.homesBelow095 && s.homesBelow095.v === 0;
      set('grid', `${ok ? `<span class="t-ok">${svg('check', { size: 14 })}</span> voltage in range · ` : ''}cable max ${fmt.fmtHTML(L(s.feederHead.v, s.feederHead.label, s.feederHead.cite), { unit: '%', digits: 1 })}`);
    }
    set('scale', 'one home\'s two batteries vs A, the feeder, ERCOT');
    set('log', doc.ticker ? `${nv(fmt, L(doc.ticker.length, seriesLabel(doc, 'ticker', 'SIM')))} commands ${fmt.chip(seriesLabel(doc, 'ticker', 'SIM'), 'sim.orchestrator.allocate(): deterministic, no model in the loop')}` : '');
    set('sources', 'ERCOT · SMART-DS · OSM · OpenDSS · named assumptions');
  }

  function renderSections() {
    sectionTeasers();
    const s = meta.summary && meta.summary[branch];
    // money (a: the existing card minus the system-capacity band; b: split / cash when l2 ships them)
    bodyOf('money').innerHTML = meta.money ? moneyHTML(fmt, meta.money, branch, BRANCH_NAMES, meta.constants, meta.summary) : '<div class="hb-sub">No money data.</div>';
    // evening: the claim (scoped to service transformers) + the branch summary
    if (s) {
      const keys = ['batteryCausedNormal', 'batteryCausedEmergency', 'normalEvents', 'emergencyTfs', 'batteryCausedAmberMin', 'homeOnlyOver100',
        'protectionOperated', 'homesDark', 'homesOnBattery', 'reserveBreaches', 'chargedPctBy0400', 'energyValueUSD'];
      const ml = s.maxLoading;
      let claim = '';
      if (s.normalEvents && s.emergencyTfs) {
        claim = s.normalEvents.v === 0 && s.emergencyTfs.v === 0
          ? `<div class="p1-claim ok">${svg('check', { size: 15 })} No service transformer passed its limit this evening (normal rating or emergency) ${fmt.chip(s.normalEvents.label, s.normalEvents.cite)}</div>`
          : `<div class="p1-claim bad">${svg('warn', { size: 15 })} ${fmt.fmtHTML(s.normalEvents)} normal-rating violations and ${fmt.fmtHTML(s.emergencyTfs)} transformers in emergency this evening</div>`;
      }
      bodyOf('evening').innerHTML = claim
        + (ml ? `<div class="p1-row"><span class="p1-k">${NAMES.maxLoading}</span><span class="p1-v">${fmt.fmtHTML(ml, { unit: '%', digits: 1 })} <span class="hb-sub">${ml.tf !== undefined ? esc(tfName(ml.tf)) : ''}${ml.t ? ' at ' + esc(ml.t) : ''}</span></span></div>` : '')
        + keys.filter((kk) => s[kk]).map((kk) => `<div class="p1-row"><span class="p1-k">${esc(humanKey(kk))}</span><span class="p1-v">${fmt.fmtHTML(s[kk], optsFor(kk))}</span></div>`).join('');
    } else {
      bodyOf('evening').innerHTML = '<div class="hb-sub">No summary for this branch.</div>';
    }
    // relief: one plain sentence, then the numbers
    const r = meta.relief;
    if (r) {
      const d = r.driver;
      const at = reliefPeakAt(meta, docs.aware || doc, fmt);
      const mins = r.minutesOver100;
      const minsHTML = !mins ? '' : fmt.isLabelled(mins) && mins.none !== undefined && mins.aware !== undefined
        ? `no batteries ${nv(fmt, L(mins.none, mins.label), { unit: ' min' })} → feeder-aware ${nv(fmt, L(mins.aware, mins.label), { unit: ' min' })} ${fmt.chip(mins.label, mins.cite)}`
        : fmt.isLabelled(mins) ? fmt.fmtHTML(mins, { unit: ' min' }) : '';
      const shared = d && d.sharedWith && d.sharedWith.length ? `, also used at ${esc(d.sharedWith.map(homeLabel).join(', '))}` : '';
      bodyOf('relief').innerHTML = `
        <div class="p1-relief-big">${esc(tfName(r.tf))}'s own batteries discharged up to ${r.reliefKW ? fmt.fmtHTML(r.reliefKW, { unit: ' kW', digits: 1 }) : ''}${at ? ` (${esc(at)})` : ''}: ${esc(tfName(r.tf))} reads ${r.aware ? fmt.fmtHTML(r.aware, { unit: '%', digits: 1 }) : 'n/a'} instead of ${r.none ? fmt.fmtHTML(r.none, { unit: '%', digits: 1 }) : 'n/a'} with no batteries.</div>
        <div class="p1-row"><span class="p1-k">Minutes over nameplate</span><span class="p1-v">${minsHTML}</span></div>
        ${r.reliefKWh ? `<div class="p1-row"><span class="p1-k">Relief energy</span><span class="p1-v">${fmt.fmtHTML(r.reliefKWh, { unit: ' kWh', digits: 1 })}</span></div>` : ''}
        ${d ? `<div class="p1-driver">Driver: one home's 15-minute spike: ${esc(d.label || homeLabel(d.home))}, SMART-DS profile <code>${esc(d.profile || '')}</code>${d.kwAtPeak ? ' at ' + fmt.fmtHTML(d.kwAtPeak, { unit: ' kW', digits: 1 }) : ''}${shared}. The same shape elsewhere is not independent evidence.</div>` : ''}
        ${r.text ? `<div class="hb-sub">${esc(r.text)}</div>` : ''}`;
    }
    // unrelieved -> P2 (audit L6: the peak is said once)
    bodyOf('unrel').innerHTML = (meta.unrelieved || []).map((u) => {
      const d = u.driver;
      const why = String(u.reason || '').split(':')[0];
      return `<div class="p1-unrel">${esc(tfName(u.tf))}: ${esc(why)}${u.peak && fmt.isLabelled(u.peak) ? `; peak ${fmt.fmtHTML(u.peak, { unit: '%', digits: 1 })}${u.peak.t ? ' at ' + esc(u.peak.t) : ''}` : ''}${d ? `; driver ${esc(d.label || homeLabel(d.home))} (<code>${esc(d.profile || '')}</code>${d.sharedWith && d.sharedWith.length ? ', shared with ' + esc(d.sharedWith.map(homeLabel).join(', ')) : ''})` : ''}. <a href="${ctx.href({ view: 'p2', branch: null, t: null, cam: u.tf === ((topology.bridge || [])[0] || {}).tf ? 't240' : null })}">Where the next battery goes →</a></div>`;
    }).join('');
    bodyOf('grid').innerHTML = gridCheckHTML(fmt, s, homeLabel);
    const ladder = meta.scaleLadder || (meta.money && meta.money.scaleLadder) || null;
    bodyOf('scale').innerHTML = ladder ? ladderHTML(fmt, ladder) : '';
    const cv = meta.controllerView;
    const nl = meta.naiveLabel && meta.naiveLabel.text ? meta.naiveLabel : { text: NAIVE_FRAMING, label: 'ASSUMPTION', cite: 'build prompt 3.4, 12 Q5' };
    bodyOf('sources').innerHTML = `
      <div class="p1-row"><span class="p1-k">What the controller sees</span><span class="p1-v">${esc(cv ? cv.text : '')} ${cv ? fmt.chip(cv.label, cv.cite) : ''}</span></div>
      <div class="p1-note"><b>Naive:</b> ${esc(nl.text)} ${fmt.chip(nl.label || 'ASSUMPTION', nl.cite)}</div>
      <div class="hb-sub">${Object.values(meta.sources || {}).map((x) => `${esc(x.text)} ${fmt.chip(x.label)}`).join('<br>')}</div>
      <div class="hb-sub">Buildings © OpenStreetMap contributors, ODbL 1.0${fm && fm.matched ? ` (${fmt.fmtHTML(fm.matched)} of the feeder's homes matched; the rest are 12 m boxes ${fmt.chip('ASSUMPTION')})` : ''} · Feeder: NREL SMART-DS 2018 AUS P1U, CC BY 4.0 · Prices: ERCOT RTM LZ_NORTH. Objects not to scale; roofs, heights and colours drawn for recognition ${fmt.chip('ASSUMPTION', 'display only')}.</div>`;
  }

  function renderLegend() {
    const present = tiersPresent(doc);
    const collapsed = store.get('hb.legend') === '0';
    legend.classList.toggle('collapsed', collapsed);
    const tierRows = [0, 1, 2, 3, 4, 5].filter((c) => present.has(c));
    legend.innerHTML = `
      <button type="button" class="lg-h" aria-expanded="${!collapsed}">What you see ${svg('chevron', { size: 14 })}</button>
      <div class="lg-body">
        <div class="lg-row"><span data-tip="A home: its real footprint (OpenStreetMap) with a pitched roof drawn for recognition. Its roof turns the colour of its transformer's trouble.">${svg('house', { size: 18 })} home</span><span class="c-bat" data-tip="A Base battery cabinet beside the house. The icon above it: fill = charge; teal bolt = charging, violet arrow = sending power out, grey = waiting, crossed signal = silent.">${svg('cabinet', { size: 18 })}${svg('battery', { size: 20, level: 0.7, state: 'C' })} Base battery (fill = charge)</span></div>
        <div class="lg-row"><span class="c-pad" data-tip="A pad-mount transformer: the green box on the ground (drawn about 2.5x real size). Its colour never changes with load.">${svg('padmount', { size: 18 })} transformer on the ground</span><span class="c-pole" data-tip="A pole-mount transformer: the grey can on a pole. Pad or pole comes from the SMART-DS wiring (DERIVED).">${svg('polemount', { size: 18 })} on a pole</span></div>
        <div class="lg-row" data-tip="The meter above a transformer: the box is 100% of its rating; sticking out of the top = too much. Over 150% the top turns jagged.">${svg('meter', { size: 20, pct: 70, tier: 0 })}${svg('meter', { size: 20, pct: 160, tier: 4 })} its load: the box is its limit; sticking out = too much</div>
        <div class="lg-row lg-tiers" id="lg-tiers">${tierRows.map((c) => `<span class="lg-t" data-tip="${esc(TIER_TIPS[c])}"><i style="background:rgb(${TIER_RGB[c].join(',')})"></i>${esc(TIER_WORDS[c])} <b class="num" data-tier="${c}"></b></span>`).join('')}</div>
        <div class="lg-row lg-tags" data-tip="Every number carries a tag: R = REAL (measured or published), S = SIM (our simulation), D = DERIVED (arithmetic on those), A = ASSUMPTION (a value we chose). Hover any tag for its source.">${fmt.chip('REAL')}${fmt.chip('SIM')}${fmt.chip('DERIVED')}${fmt.chip('ASSUMPTION')} where a number comes from (hover any tag)</div>
        <div class="lg-row lg-foot">Objects not to scale; roofs and heights drawn for recognition ${fmt.chip('ASSUMPTION', 'display only')} · Footprints © OpenStreetMap ${fmt.chip('REAL', 'ODbL 1.0')}</div>
      </div>`;
    legend.querySelector('.lg-h').addEventListener('click', () => {
      const c = !legend.classList.contains('collapsed');
      legend.classList.toggle('collapsed', c);
      legend.querySelector('.lg-h').setAttribute('aria-expanded', String(!c));
      store.set('hb.legend', c ? '0' : '1');
    });
    updateLegendCounts();
  }
  function updateLegendCounts() {
    const c = countsAt(doc, k);
    const n = topology.transformers.length;
    const vals = [n - c.reduce((a, b) => a + b, 0), ...c];
    for (const b of legend.querySelectorAll('[data-tier]')) b.textContent = String(vals[Number(b.dataset.tier)]);
  }

  function renderNow() {
    const lab = seriesLabel(doc, 'loading', 'SIM');
    const w = worstAt(doc, k);
    const c = countsAt(doc, k);
    const over = c[0] + c[1] + c[2] + c[3] + c[4];
    const f = Object.entries(doc.focus || {}).find(([, x]) => x.tf === w.tf);
    const meterOpts = { size: 64, pct: w.pct, tier: w.code };
    if (f) {
      const hk = f[1].homeKW[k] / 10, bk = f[1].batKW[k] / 10;
      Object.assign(meterOpts, { homeKW: hk, batKW: bk, exporting: hk + bk < 0 });
    } else {
      const bk = tfBatKW(doc, topology, w.tf, k);
      if ((doc.reverse || []).some((r) => r[0] === k && r[1] === w.tf)) meterOpts.exporting = true;
      else if (bk > 0.05) Object.assign(meterOpts, { homeKW: Math.max(0, (w.pct / 100) * topology.transformers[w.tf].kva - bk), batKW: bk });
    }
    const pv = meta.price[k];
    const lvl = priceLevel(meta, pv);
    const th = meta.plan && meta.plan.threshold;
    const tipTf = esc(tfTipHTML(fmt, meta, doc, topology, sceneModel, w.tf, k, names));
    $('p1-now').className = `p1-card p1-now t${w.code}`;
    $('p1-now').innerHTML = `
      <div class="now-main">
        <span class="now-meter" tabindex="0" data-tip-html="${tipTf}">${svg('meter', meterOpts)}</span>
        <div class="now-txt">
          <div class="now-k">Worst transformer now</div>
          <div class="now-pct tier-${w.code}" data-tip="The worst of the feeder's ${topology.transformers.length} service transformers right now: OpenDSS loading as % of its nameplate. The box is 100%; above the box is overload.">${fmt.fmtHTML(L(+w.pct.toFixed(1), lab, 'OpenDSS loading, % of nameplate'), { unit: '%', digits: 1 })}</div>
          <span class="pill t${w.code}" data-tip="${esc(TIER_TIPS[w.code] || '')}">${svg(w.code >= 2 ? 'warn' : w.code === 1 ? 'meter' : 'check', { size: 13 })} ${esc(TIER_WORDS[w.code] || '')}</span>
          <div class="now-who">Transformer ${esc(tfName(w.tf))} · ${esc(whoPhrase(w.pct))}</div>
          <div class="now-why">${nowWhy(fmt, meta, doc, topology, w.tf, k, homeLabel)}</div>
        </div>
      </div>
      <div class="now-icons">
        <span class="nowi" data-tip-html="${esc(`ERCOT real-time price, North Texas load zone (LZ_NORTH), this minute: ${fmt.fmtHTML(L(pv, priceLabel, 'ERCOT RTM SPP LZ_NORTH'), { money: true, digits: 2, unit: '/MWh' })}.${th ? ` Cheap: under 2× today's median (${fmt.fmtHTML(th, { money: true, digits: 2 })}), the charge rule's threshold.` : ''}`)}">${svg(lvl === 'expensive' ? 'priceUp' : 'priceDown', { size: 18 })} power is ${esc(lvl || 'n/a')}</span>
        <span class="nowi" data-tip-html="${esc(`${fmt.fmtHTML(L(over, lab, 'transformers at tier codes 1-5'))} transformers over their rating now: ${nv(fmt, L(c[0], lab))} over, ${nv(fmt, L(c[1] + c[2], lab))} overloaded, ${nv(fmt, L(c[3], lab))} emergency, ${nv(fmt, L(c[4], lab))} fuse open`)}">${svg('meter', { size: 18, pct: over ? 130 : 60, tier: over ? Math.min(4, c[3] ? 4 : c[1] + c[2] ? 2 : 1) : 0 })} ${over ? `${nv(fmt, L(over, lab))} over their rating ${fmt.chip(lab, 'OpenDSS tier codes')}` : 'all within their rating'}</span>
      </div>`;
  }

  function renderFleet() {
    const node = $('p1-fleet');
    if (branch === 'none') {
      node.innerHTML = `<div class="fleet-row"><div class="fleet-bat off" aria-hidden="true"><i style="width:0%"></i><span class="fleet-res"></span></div><div class="fleet-say">${svg('house', { size: 16 })} No batteries in this scenario</div></div>`;
      return;
    }
    const sc = stateCounts(doc, k);
    const soc = meanSoc(doc, k);
    const lab = seriesLabel(doc, 'soc', 'SIM');
    const n = (topology.fleet || []).length;
    let sumKW = 0;
    for (const x of doc.batKW[k]) sumKW += x / 10;
    const flow = sc.C >= sc.D && sc.C > 0 ? 'C' : sc.D > 0 ? 'D' : 'I';
    const word = sc.C === n ? 'All charging' : sc.D === n ? 'All sending power out' : flow === 'C' ? 'Charging' : flow === 'D' ? 'Sending power out' : 'Waiting';
    const counts = [['C', 'bolt'], ['D', 'out'], ['I', 'wait'], ['S', 'silent'], ['X', 'silent'], ['B', 'house']].filter(([s]) => sc[s] > 0)
      .map(([s, ic]) => `<span class="fc s-${s}" data-tip="${esc(`${STATE_WORDS[s]}`)}">${svg(ic, { size: 14 })}${nv(fmt, L(sc[s], seriesLabel(doc, 'state', 'SIM')))}</span>`).join('');
    const col = STATE_RGB[flow] || STATE_RGB.I;
    node.innerHTML = `<div class="fleet-row" data-tip-html="${esc(`The ${n} Base batteries on this feeder as one battery: fill = their average charge; the dashed line is the 20% member reserve. Right now they move ${fmt.fmtHTML(L(+sumKW.toFixed(1), seriesLabel(doc, 'batKW', 'SIM'), 'sum of battery kW (+ charging)'), { unit: ' kW', digits: 1, signed: true })} in total.`)}">
      <div class="fleet-bat ${playing ? 'moving' : ''} f-${flow}" aria-hidden="true" style="--fc: rgb(${col.join(',')})"><i style="width:${(100 * soc).toFixed(1)}%"></i><span class="fleet-res"></span><b>${nv(fmt, L(Math.round(100 * soc), lab, 'fleet mean state of charge'), { unit: '%' })}</b></div>
      <div class="fleet-txt"><div class="fleet-say">${esc(word)} ${fmt.chip(lab, 'battery states and charge from the controller (SIM)')}</div><div class="fleet-counts">${counts}</div></div></div>`;
  }

  function faultBadgeAt(j) {
    // the comms-lost battery is silent from `silentFrom` (before the controller marks it stale): a no-signal badge
    for (const e of (meta.events && meta.events[branch]) || []) {
      if (e.kind !== 'comms_lost') continue;
      const jj = Number.isInteger(e.batt) ? e.batt : (topology.fleet || []).indexOf(e.home);
      const from = Number.isInteger(e.silentFrom) ? e.silentFrom : e.step + 1;
      const to = Number.isInteger(e.coveredStep) ? e.coveredStep : (Number.isInteger(e.expiredStep) ? e.expiredStep : from + 5);
      if (jj === j && k >= from && k <= to) return e;
    }
    return null;
  }

  function renderStreet() {
    const cols = FOCUS_KEYS.map((key) => {
      const g = gaugeModel(meta, doc, topology, key, k, sceneModel.roomKW, sceneModel.exportRoomKW);
      if (!g) return '';
      const name = key === '240' ? 'T-240' : key;
      const t = topology.transformers[g.tf];
      const tip = esc(tfTipHTML(fmt, meta, doc, topology, sceneModel, g.tf, k, names));
      const meter = svg('meter', { size: 46, pct: g.pct, tier: g.code, homeKW: g.homeKW, batKW: g.batKW, exporting: g.exporting });
      const stateWord = g.exporting && g.code === 0 ? 'Sending back' : TIER_WORDS[g.code];
      const homes = t.homes.map((hi) => `<span class="hm" data-tip="${esc(topology.homes[hi].label)}">${svg('house', { size: 13 })}</span>`).join('');
      const bats = [];
      (topology.fleet || []).forEach((hi, j) => {
        if (topology.homes[hi].tf !== g.tf) return;
        const tipB = esc(batteryTipHTML(fmt, meta, doc, topology, j, k, names, branch));
        if (branch === 'none') { bats.push(`<span class="bt off" data-tip-html="${tipB}">${svg('battery', { size: 26, level: 0, state: 'I' })}</span>`); return; }
        const st = doc.state[k][j];
        const badge = faultBadgeAt(j) ? `<i class="bt-badge" data-tip="No signal from this battery since ${esc(fmt.stepToTime(meta, faultBadgeAt(j).silentFrom ?? faultBadgeAt(j).step + 1))} (a failure we injected, ASSUMPTION)">${svg('silent', { size: 12 })}</i>` : '';
        bats.push(`<span class="bt s-${st}" data-tip-html="${tipB}">${svg('battery', { size: 26, level: doc.soc[k][j] / 1000, state: st })}${badge}</span>`);
      });
      const batHTML = bats.length ? bats.join('') : `<span class="bt-none" data-tip="No battery on T-240. Where would one help most? See P2 →">none</span>`;
      return `<button type="button" class="col t${g.code}" data-key="${key}" data-tf="${g.tf}" data-tip-html="${tip}">
        <span class="col-k">${esc(name)}</span><span class="col-m">${meter}</span>
        <span class="col-state">${esc(stateWord || '')}</span>
        <span class="col-homes">${homes}</span><span class="col-bats">${batHTML}</span></button>`;
    }).join('');
    $('p1-streetcols').innerHTML = cols;
    // numbers, one click away
    const lab = seriesLabel(doc, 'loading', 'SIM');
    const flab = seriesLabel(doc, 'focus', 'SIM');
    const fuse = { pct: meta.protection ? meta.protection.fusePct : 200, min: meta.protection ? meta.protection.fuseMinutes : 10, cite: meta.protection && meta.protection.cite };
    bodyOf('street').innerHTML = FOCUS_KEYS.map((key) => {
      const g = gaugeModel(meta, doc, topology, key, k, sceneModel.roomKW, sceneModel.exportRoomKW);
      if (!g) return '';
      const room = g.open ? 'fuse open' : g.pct > 100
        ? `over by ${fmt.fmtHTML(L(+((g.pct / 100 - 1) * g.kva).toFixed(1), 'DERIVED', 'OpenDSS loading above 100%, times kVA'), { unit: ' kVA', digits: 1 })}`
        : g.exporting && g.exportRoom !== null
          ? `room to export ${fmt.fmtHTML(L(+Math.max(0, g.exportRoom).toFixed(1), 'DERIVED', 'kW of back-feed that still fits under nameplate while exporting'), { unit: ' kW', digits: 1 })}`
          : `room ${fmt.fmtHTML(L(+Math.max(0, g.room).toFixed(1), 'DERIVED', 'kW of charge that still fits under nameplate'), { unit: ' kW', digits: 1 })}`;
      return `<div class="p1-num-row"><b>${key === '240' ? 'T-240' : key}</b> · ${fmt.fmtHTML(L(g.kva, 'REAL', 'SMART-DS kVA'), { unit: ' kVA' })} · now ${fmt.fmtHTML(L(+g.pct.toFixed(1), lab, 'OpenDSS loading'), { unit: '%', digits: 1 })}
        <div class="hb-sub">homes ${nv(fmt, L(+g.homeKW.toFixed(1), flab), { unit: ' kW', digits: 1 })} · batteries ${nv(fmt, L(+g.batKW.toFixed(1), flab), { unit: ' kW', digits: 1, signed: true })} ${fmt.chip(flab, 'metered kW at the homes')} · ${room}</div>
        <div class="hb-sub">evening max ${nv(fmt, L(+g.maxPct.toFixed(1), lab), { unit: '%', digits: 1 })} at ${esc(fmt.stepToTime(meta, g.maxStep))} · ${nv(fmt, L(g.min110, lab), { unit: ' min' })} above 110%${g.min150 ? ` · ${nv(fmt, L(g.min150, lab), { unit: ' min' })} above 150%` : ''} ${fmt.chip(lab, 'OpenDSS loading; minutes at tier codes 2-4')}${g.openStep >= 0 ? ` · <b>fuse opened at ${esc(fmt.stepToTime(meta, g.openStep))}</b>` : ''}</div></div>`;
    }).join('') + `<div class="hb-sub">Fuse rule: opens above ${nv(fmt, L(fuse.pct, 'ASSUMPTION'), { unit: '%' })} for ${nv(fmt, L(fuse.min, 'ASSUMPTION'), { unit: ' min' })} ${fmt.chip('ASSUMPTION', fuse.cite)}; 110% and 150% are SMART-DS ratings ${fmt.chip('REAL', 'SMART-DS normhkva / EmergHKVA')}.</div>`;
  }

  function renderStory() {
    const chain = CHAINS[branch] || [];
    const done = cues.find((c) => c.id === 'charged');
    story.querySelector('#p1-chain').innerHTML = chain.map(([id, icon, words], i) => {
      const c = cues.find((x) => x.id === id);
      const lit = !!c && k >= c.k;
      let w = words, ic = icon, tone = c ? c.tone : 'info';
      if (id === 'turns' && done && k >= done.k) { w = 'Every transformer stayed within its limit'; ic = 'ok'; tone = 'ok'; }
      const tip = c ? esc(`<b>${esc(c.t)}</b> ${cueText(c, fmt, names, branch)}<br><i>click to jump here</i>`) : '';
      const val = chainValue(c, fmt, names, branch, lit, done && k >= done.k ? done : null);
      return `${i ? `<span class="ch-arrow">${svg('arrowRight', { size: 14 })}</span>` : ''}<button type="button" class="ch-step ${lit ? 'lit' : 'ghost'} tone-${tone}${c ? '' : ' nofire'}" data-k="${c ? c.k : ''}" ${c ? `data-tip-html="${tip}"` : 'data-tip="did not happen on this day"'}>
        <span class="ch-ic">${ic === 'meter' ? svg('meter', { size: 20, pct: lit ? 160 : 80, tier: lit ? 4 : 0 }) : svg(ic, { size: 18 })}</span><span class="ch-w">${esc(w)}</span><span class="ch-v">${val}</span></button>`;
    }).join('');
    const a = activeCue(cues, k);
    const line = story.querySelector('#p1-line');
    line.hidden = !showCap || !a;
    if (a && showCap) line.innerHTML = `<b class="sl-t">${esc(a.t)}</b> <span class="sl-ic tone-${a.tone}">${svg(a.icon, { size: 16 })}</span> <span class="sl-text">${cueText(a, fmt, names, branch)}</span>${a.id === 'clear' && branches.includes('aware') ? ' <button type="button" class="sl-next" id="p1-watch-aware">Now watch the same evening feeder-aware ›</button>' : ''}`;
    story.classList.toggle('no-line', line.hidden);
  }

  function badgesAt() {
    const out = [];
    for (const e of (meta.events && meta.events[branch]) || []) {
      if (e.kind === 'comms_lost') {
        const j = Number.isInteger(e.batt) ? e.batt : (topology.fleet || []).indexOf(e.home);
        if (faultBadgeAt(j)) out.push({ icon: 'g-silent', j });
      } else if (e.kind === 'hot' && k >= e.step && k < e.step + (e.minutes || 0) * 60 / stepSec) out.push({ icon: 'g-hot', tf: e.tf });
    }
    return out;
  }

  function renderDynamic() {
    const time = fmt.stepToTime(meta, k);
    renderNow();
    renderFleet();
    renderStreet();
    renderStory();
    updateLegendCounts();
    const tk = tickerAt(doc, k, 12);
    bodyOf('log').innerHTML = `<ol class="p1-ticker">${tk.length ? tk.map(([st, text]) => `<li class="${st === k ? 'now' : ''}">${esc(text)}</li>`).join('') : '<li class="hb-sub">nothing sent yet</li>'}</ol>`;
    const ev = (meta.events && meta.events[branch]) || [];
    if (ev.length) {
      bodyOf('faults').innerHTML = `<ol class="p1-faults">${ev.map((e) => {
        const past = e.step <= k;
        let now = '';
        if (e.kind === 'comms_lost' && e.home !== undefined) {
          const j = Number.isInteger(e.batt) ? e.batt : (topology.fleet || []).indexOf(e.home);
          if (j >= 0) now = ` · now: ${esc(STATE_WORDS[doc.state[k][j]] || doc.state[k][j])}`;
        }
        const vals = [];
        if (e.cmdKW !== undefined) vals.push(`command ${fmt.fmtHTML(L(e.cmdKW, 'SIM'), { unit: ' kW', digits: 1, signed: true })}`);
        if (e.deltaKW !== undefined) vals.push(`${fmt.fmtHTML(L(e.deltaKW, 'ASSUMPTION', 'EV_KW: a Level 2 EV'), { unit: ' kW', digits: 1, signed: true })}`);
        if (e.minutes !== undefined) vals.push(fmt.fmtHTML(L(e.minutes, 'ASSUMPTION'), { unit: ' min' }));
        const ic = e.kind === 'comms_lost' ? 'silent' : e.kind === 'hot' ? 'hot' : e.kind === 'stall' ? 'stall' : 'warn';
        return `<li class="p1-fault ${past ? 'past' : 'future'}">${svg(ic, { size: 16 })}<b>${esc(e.t)}</b> ${esc(e.text || faultText(e, homeLabel))}${vals.length ? ' · ' + vals.join(' · ') : ''}${past ? now : ''}</li>`;
      }).join('')}</ol><div class="hb-sub">Failure times and sizes are named constants ${fmt.chip('ASSUMPTION', 'build prompt 5.4.4')}; what the controller does about them is simulated ${fmt.chip('SIM')}.</div>`;
    }
    const pv = meta.price[k];
    const lvl = priceLevel(meta, pv);
    transport.querySelector('#p1-time').textContent = time;
    transport.querySelector('#p1-date').textContent = dayLabel(meta.day, dayOffsetAt(meta, fmt, k), false);
    transport.querySelector('#p1-price').innerHTML = `${svg(lvl === 'expensive' ? 'priceUp' : 'priceDown', { size: 15 })} ${fmt.fmtHTML(L(pv, priceLabel, 'ERCOT RTM SPP LZ_NORTH, the interval containing this minute'), { money: true, digits: 2, unit: '/MWh' })} <span class="lvl lvl-${lvl}" data-tip-html="${esc(meta.plan && meta.plan.threshold ? `Cheap: under 2× today's median (${fmt.fmtHTML(meta.plan.threshold, { money: true, digits: 2, unit: '/MWh' })}): the charge rule's threshold.` : '')}">${esc(lvl || '')}</span>`;
    const cash = branch !== 'none' ? cashAt(meta, branch, k) : null;
    const cashEl = transport.querySelector('#p1-cash');
    cashEl.hidden = !cash;
    if (cash) cashEl.innerHTML = `${svg('money', { size: 15 })} ${fmt.fmtHTML(cash, { money: true, digits: 2 })} so far`;
    drawCursor();
    const frame = sceneModel.frameFromP1(doc, k);
    const model = sceneModel.buildSceneModel({ topology, footprints: ctx.footprints, frame, view: 'p1', theme: ctx.theme, hideBatteries: branch === 'none' });
    model.badges = badgesAt().map((b) => (b.j !== undefined ? { ...b, position: model.batteries[b.j] && model.batteries[b.j].position } : { ...b, position: model.tfs[b.tf].meterPos })).filter((b) => b.position);
    scene.update(model);
  }

  // ---- price strip: REAL price line with a light area, the tier ribbon ("transformer trouble"), icon markers, cursor ----
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
    const ribbon = 10 * dpr, top = 24 * dpr, ph = H - ribbon - top - 16 * dpr;
    const xs = (i) => (i + 0.5) / n * W;
    // the market plan's sell windows (DERIVED), violet
    c.fillStyle = 'rgba(123,92,214,0.12)';
    for (const [start, mins] of (meta.plan && meta.plan.discharge) || []) {
      const k0 = fmt.timeToStep(meta, start);
      if (k0 === null) continue;
      const k1 = Math.min(n, k0 + Math.round(mins * 60 / stepSec));
      c.fillRect(k0 / n * W, top, (k1 - k0) / n * W, ph);
    }
    const pmax = Math.max(1, ...meta.price), pmin = Math.min(0, ...meta.price);
    const yv = (p) => top + ph - (p - pmin) / (pmax - pmin) * ph;
    c.beginPath();
    meta.price.forEach((p, i) => { if (i) c.lineTo(xs(i), yv(p)); else c.moveTo(xs(i), yv(p)); });
    c.lineTo(xs(n - 1), top + ph); c.lineTo(xs(0), top + ph); c.closePath();
    c.fillStyle = 'rgba(184,134,11,0.12)';
    c.fill();
    c.strokeStyle = col('--ink', '#101613');
    c.lineWidth = 2.5 * dpr;
    c.beginPath();
    meta.price.forEach((p, i) => { if (i) c.lineTo(xs(i), yv(p)); else c.moveTo(xs(i), yv(p)); });
    c.stroke();
    const TR = TIER_RGB;
    for (let i = 0; i < n; i++) {
      const cnt = countsAt(doc, i);
      let worst = 0;
      for (let qq = 4; qq >= 0; qq--) if (cnt[qq] > 0) { worst = qq + 1; break; }
      if (!worst) continue;
      const tot = cnt.reduce((a, b) => a + b, 0);
      const a = Math.min(1, 0.35 + tot / 12);
      const t = TR[worst];
      c.fillStyle = `rgba(${t[0]},${t[1]},${t[2]},${a})`;
      c.fillRect(i / n * W, H - ribbon, Math.max(1, W / n + 0.5), ribbon);
    }
    c.fillStyle = col('--muted', '#55625A');
    c.font = `${10 * dpr}px sans-serif`;
    for (let i = 0; i < n; i++) {
      const t = fmt.stepToTime(meta, i);
      if (t.endsWith(':00') && (n <= 180 || Number(t.slice(0, 2)) % 2 === 0)) {
        c.fillRect(xs(i), H - ribbon - 3 * dpr, 1 * dpr, 3 * dpr);
        c.fillText(t, xs(i) + 2 * dpr, H - ribbon - 3 * dpr);
      }
    }
    stripBase = c.getImageData(0, 0, W, H);
    const marks = stripMarks(meta, branch, fmt, cues);
    // icons that would overlap sit side by side (19 px apart), never on top of each other
    let lastX = -Infinity;
    for (const m of marks) { const x = Math.max(r.width * (m.k + 0.5) / n, lastX + 19); m.x = x; lastX = x; }
    $marks.innerHTML = marks.map((m) => `<button type="button" class="mark mark-${m.kind}${m.tone ? ' tone-' + m.tone : ''}" style="left:${m.x.toFixed(1)}px" data-k="${m.k}" data-tip-html="${esc(`${esc(m.text)} ${fmt.chip(m.label)} · click to jump here`)}" aria-label="${esc(m.text)}">${svg(m.icon, { size: 18 })}</button>`).join('');
    drawCursor();
  }
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
    for (const a of el.querySelectorAll('.p1-scn a')) a.href = ctx.href({ branch: a.dataset.branch, t: fmt.stepToTime(meta, k) });
    if (url) replaceUrl();
  }
  function replaceUrl() {
    try {
      const qq = ctx.data.linkQuery({ ...link, beat: null, branch, t: fmt.stepToTime(meta, k), speed: speed === DEFAULT_SPEED ? null : speed });
      history.replaceState(null, '', qq);
    } catch (e) { /* file:// or sandboxed: the link still works */ }
  }
  function setPlaying(p) {
    playing = p;
    const b = transport.querySelector('#p1-play');
    b.innerHTML = svg(p ? 'pause' : 'play', { size: 20 });
    b.setAttribute('aria-label', p ? 'pause' : 'play');
    const fb = el.querySelector('.fleet-bat');
    if (fb) fb.classList.toggle('moving', p);
    if (p) { last = performance.now(); acc = 0; held = new Set(); if (k >= meta.steps - 1) seek(0, { url: false }); requestAnimationFrame(tick); } else replaceUrl();
  }
  function tick(now) {
    if (!playing) return;
    if (now < holdUntil) { last = now; requestAnimationFrame(tick); return; }
    acc += (now - last) * speed;
    last = now;
    let adv = Math.floor(acc / MS_PER_STEP);
    if (adv > 0) {
      acc -= adv * MS_PER_STEP;
      // hold at story moments: stop on a chain cue's step once per play, then carry on
      if (hold) {
        const c = cues.find((x) => x.chain !== null && x.k > k && x.k <= k + adv && !held.has(x.id));
        if (c) { adv = c.k - k; held.add(c.id); holdUntil = now + HOLD_MS; acc = 0; }
      }
      if (k + adv >= meta.steps - 1) { seek(meta.steps - 1, { url: false }); setPlaying(false); return; }
      seek(k + adv, { url: false });
    }
    requestAnimationFrame(tick);
  }
  function setSpeed(s) {
    speed = s;
    for (const b of transport.querySelectorAll('.tp-speed button')) b.setAttribute('aria-pressed', String(Number(b.dataset.speed) === s));
  }
  function moment(dir) {
    const ks = [...new Set(cues.map((c) => c.k))].sort((a, b) => a - b);
    const t = dir > 0 ? ks.find((x) => x > k) : [...ks].reverse().find((x) => x < k);
    if (t !== undefined) seek(t);
  }
  transport.querySelector('#p1-play').addEventListener('click', () => { closeIntro(); setPlaying(!playing); });
  for (const b of transport.querySelectorAll('[data-step]')) b.addEventListener('click', (ev) => seek(k + Number(b.dataset.step) * (ev.shiftKey ? 10 : 1)));
  for (const b of transport.querySelectorAll('[data-cue]')) b.addEventListener('click', () => moment(Number(b.dataset.cue)));
  for (const b of transport.querySelectorAll('.tp-speed button')) b.addEventListener('click', () => { setSpeed(Number(b.dataset.speed)); replaceUrl(); });
  transport.querySelector('#p1-hold').addEventListener('change', (ev) => { hold = ev.target.checked; });
  transport.querySelector('#p1-cc').addEventListener('click', (ev) => { showCap = !showCap; ev.currentTarget.setAttribute('aria-pressed', String(showCap)); renderStory(); });
  const scrubAt = (ev) => {
    const r = strip.getBoundingClientRect();
    seek(Math.floor((ev.clientX - r.left) / r.width * meta.steps));
  };
  let scrubbing = false;
  strip.addEventListener('pointerdown', (ev) => { scrubbing = true; strip.setPointerCapture(ev.pointerId); scrubAt(ev); });
  strip.addEventListener('pointermove', (ev) => { if (scrubbing) scrubAt(ev); });
  strip.addEventListener('pointerup', () => { scrubbing = false; });
  $marks.addEventListener('click', (ev) => { const b = ev.target.closest('.mark'); if (b) seek(Number(b.dataset.k)); });
  story.addEventListener('click', (ev) => {
    const s = ev.target.closest('.ch-step');
    if (s && s.dataset.k !== '') { seek(Number(s.dataset.k)); return; }
    if (ev.target.closest('#p1-watch-aware')) switchBranch('aware', true);
  });
  cams.addEventListener('click', (ev) => {
    const b = ev.target.closest('button[data-cam]');
    if (!b) return;
    for (const x of cams.querySelectorAll('button')) x.removeAttribute('aria-pressed');
    b.setAttribute('aria-pressed', 'true');
    scene.camera(b.dataset.cam);
  });
  async function switchBranch(b, play = false) {
    try {
      branch = b;
      doc = await loadDoc(branch);
      if (play) { const d = storyCues(meta, doc, branch, topology, fmt).find((c) => c.id === 'drop'); if (d) k = Math.max(0, d.k - 5); }
      renderStatic();
      renderDynamic();
      replaceUrl();
      if (play) setPlaying(true);
    } catch (e) { ctx.reportError(e); }
  }
  el.querySelector('.p1-scn').addEventListener('click', (ev) => {
    const a = ev.target.closest('a[data-branch]');
    if (!a) return;
    ev.preventDefault();
    switchBranch(a.dataset.branch);
  });
  $('p1-streetcols').addEventListener('click', (ev) => {
    const b = ev.target.closest('.col[data-tf]');
    if (b && scene.flyTo) scene.flyTo(topology.transformers[Number(b.dataset.tf)].lonlat, { zoom: 18.6, pitch: 55 });
  });
  const onKey = (ev) => {
    if (ev.target && /input|select|textarea/i.test(ev.target.tagName)) return;
    if (ev.key === ' ') { ev.preventDefault(); closeIntro(); setPlaying(!playing); } else if (ev.key === 'ArrowRight') seek(k + (ev.shiftKey ? 10 : 1));
    else if (ev.key === 'ArrowLeft') seek(k - (ev.shiftKey ? 10 : 1));
    else if (ev.key === '.') moment(1);
    else if (ev.key === ',') moment(-1);
    else if (ev.key === ']' || ev.key === '[') { const i = SPEEDS.indexOf(speed); setSpeed(SPEEDS[Math.max(0, Math.min(SPEEDS.length - 1, i + (ev.key === ']' ? 1 : -1)))]); }
  };
  window.addEventListener('keydown', onKey);
  window.addEventListener('resize', () => drawStrip());

  // ---- hover on the 3D scene (and the 2D fallback): the same tooltip copy ----
  const sceneEl = document.getElementById('scene');
  const hsFor = () => sceneModel.homeStatesAt(doc.homeState || [], k, topology.homes.length);
  const fleetSet = new Set(topology.fleet || []);
  function tipFor({ layer, object: o }) {
    if (!o) return '';
    if (layer === 'worst-tag') return `<b>${esc(o.label)}</b>: ${esc(LABEL_WORDS[o.label] || '')} The worst transformer's loading, from the OpenDSS power flow.`;
    if (['pads', 'poles', 'cans', 'meters', 'plinths', 'worst'].includes(layer) && Number.isInteger(o.i)) return tfTipHTML(fmt, meta, doc, topology, sceneModel, o.i, k, names);
    if ((layer === 'walls' || layer === 'roofs') && Number.isInteger(o.home ?? o.i)) {
      const hi = o.home ?? o.i;
      return homeTipHTML(fmt, topology, ctx.footprints, hi, names, hsFor()[hi], fleetSet.has(hi) && branch !== 'none');
    }
    if (['cabinets', 'caps', 'battery-icons'].includes(layer) && Number.isInteger(o.j) && o.j >= 0) return batteryTipHTML(fmt, meta, doc, topology, o.j, k, names, branch);
    if (layer === 'badges' && o.icon === 'g-silent') return 'This battery has gone silent: no signal since it took its last command (a failure we injected, ASSUMPTION).';
    if (layer === 'badges' && o.icon === 'g-hot') return 'An EV plugged in on this transformer (a failure we injected, ASSUMPTION).';
    return '';
  }
  if (scene.onHover) {
    scene.onHover((info) => {
      try { window.__hbLastHover = info ? info.layer : null; } catch (e) { /* a test reads what was hovered */ }
      if (!info) { tips.hideTip(); return; }
      const html = tipFor(info);
      if (!html) { tips.hideTip(); return; }
      const r = sceneEl ? sceneEl.getBoundingClientRect() : { left: 0, top: 0 };
      tips.showTip(html, r.left + info.x, r.top + info.y);
    });
  }
  scene.onPick(({ layer, object }) => {
    if (!object || !scene.flyTo) return;
    const i = Number.isInteger(object.i) && ['pads', 'poles', 'cans', 'meters'].includes(layer) ? object.i : null;
    if (i !== null) scene.flyTo(topology.transformers[i].lonlat, { zoom: 18.6, pitch: 55 });
  });

  // ---- first open: the intro card (bare view=p1 only) ----
  function closeIntro() {
    if (!intro) return;
    intro.remove(); intro = null;
    document.body.classList.remove('p1-intro-on');
  }
  if (bare) {
    intro = document.createElement('div');
    intro.className = 'p1-overlay p1-intro';
    const fleetN = (topology.fleet || []).length;
    intro.innerHTML = `<div class="intro-card" role="dialog" aria-label="Start here">
      <h2>${nv(fmt, L(fleetN, 'REAL', 'Base fleet on this feeder (data/fleet.json)'))} home batteries. One cheap-power signal. What happens to this street's transformers?</h2>
      <p>A real Texas evening (ERCOT prices, ${esc(dayLabel(meta.day))}) ${fmt.chip(priceLabel, 'ERCOT RTM SPP LZ_NORTH, recorded')} on a simulated neighbourhood feeder, checked by OpenDSS every minute ${fmt.chip('SIM', 'OpenDSS power flow, one solve per minute')}.</p>
      <div class="intro-b"><button type="button" class="intro-watch">${svg('play', { size: 16 })} Watch it happen</button><button type="button" class="intro-own">Explore on my own</button></div></div>`;
    document.body.append(intro);
    document.body.classList.add('p1-intro-on');
    intro.querySelector('.intro-watch').addEventListener('click', () => { closeIntro(); setSpeed(0.25); hold = true; transport.querySelector('#p1-hold').checked = true; setPlaying(true); });
    intro.querySelector('.intro-own').addEventListener('click', closeIntro);
  }

  renderStatic();
  renderDynamic();
  const cam = link.cam || (bare ? 'street' : null);
  if (cam) scene.camera(cam, { instant: true });
}
