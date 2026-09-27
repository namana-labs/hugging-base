// ui/story/results.js (UI-B): Screen 3a Results (docs/design-handoff/story-flow/README.md "Screen 3").
// Verdict + four tiles against the other committed runs of the same evening/levers; money, reserve, homes dark;
// voltage by bus at the shared cursor and the bus x time heat map (extras vTfMilli by busOrder, band from the named
// constants V_ANSI_LO / V_ANSI_HI); reactive power (extras headKVAr, capKVAr; our inverters 0 at unity power factor,
// ASSUMPTION); failure summaries; ERCOT context ONLY for the covert scenario (REAL 25 Sep 2026 frequency, "a different
// day", beside the HIJACK_MHZ_LO-HI band from the catalogue constants).
// Every number a viewer sees comes from a data file with its label. A missing file or field says so ("not exported
// for this run" / "not built yet"); it is never drawn as zero and never replaced by a typed-in value.
// Pure view functions are exported for ui/test/pagesb-results.test.js; mount() is the DOM half.

import { TIER_RGB } from '../lib/icons.js';

export const PAGE = 'results';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];
export const isLab = (x) => x != null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
const has = (x) => isLab(x) && x.v != null;
const fin = (x) => typeof x === 'number' && Number.isFinite(x);

/** A provenance tag, the same markup as UI-A's shell.js tagHTML (class chip chip-<LABEL>); `screening` adds the
 *  dashed SCREENING tag (not OpenDSS-checked). */
export function tagHTML(label, cite, screening = false) {
  const one = (l, c) => `<span class="chip chip-${esc(l)}"${c ? ` title="${esc(c)}"` : ''}>${esc(l)}</span>`;
  return one(label, cite) + (screening ? one('SCREENING', `Screening estimate, not checked by OpenDSS.${cite ? ` ${cite}` : ''}`) : '');
}
export const missingHTML = (what = 'not exported for this run') => `<span class="pb-missing">${esc(what)}</span>`;

export function fmtNum(v, d = 0) {
  if (v == null || !Number.isFinite(+v)) return '—';
  return Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
/** Decimal places of a constant as written (0.95 -> 2), so a band reads the way its source states it. */
export const decimalsOf = (v) => { const m = /\.(\d+)$/.exec(String(v)); return m ? m[1].length : 0; };

// ---- time ------------------------------------------------------------------------------------------------------
/** The run's clock from extras (first) or meta: {n, start, stepS}. null when any of the three is missing. */
export function timeOf(ex, meta) {
  const pick = (k) => (ex && ex[k] != null ? ex[k] : meta && meta[k] != null ? meta[k] : null);
  const n = pick('steps'), start = pick('start'), stepS = pick('stepSeconds');
  if (!(Number.isInteger(n) && n > 0) || !/^\d{1,2}:\d{2}$/.test(String(start || '')) || !(fin(stepS) && stepS > 0)) return null;
  return { n, start, stepS };
}
/** "HH:MM" of step k (k may equal n: the end of the run). null without a clock. */
export function clockOf(k, tm) {
  if (!tm) return null;
  const [h, m] = tm.start.split(':').map(Number);
  const t = ((h * 60 + m + Math.round(k * tm.stepS / 60)) % 1440 + 1440) % 1440;
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
}
/** Scrubber ticks from the clock alone: whole-hour multiples chosen so at most `maxTicks` fit, plus the run's end.
 *  x is the fraction along the track (the cursor's k / (n - 1) convention). */
export function timeTicks(tm, maxTicks = 7) {
  if (!tm) return [];
  const [h, m] = tm.start.split(':').map(Number);
  const m0 = h * 60 + m, stepMin = tm.stepS / 60, total = tm.n * stepMin;
  const every = [30, 60, 120, 180, 240, 360].find((e) => total / e <= maxTicks - 1) || total;
  const out = [];
  for (let k = 0; k < tm.n; k++) {
    const t = m0 + k * stepMin;
    if (Math.abs(t / every - Math.round(t / every)) < 1e-9) out.push({ k, x: tm.n > 1 ? k / (tm.n - 1) : 0, t: clockOf(k, tm) });
  }
  const last = out[out.length - 1];
  if (!last || (tm.n - last.k) * stepMin >= every / 2) out.push({ k: tm.n, x: 1, t: clockOf(tm.n, tm), end: true });
  return out;
}

// ---- catalogue helpers ------------------------------------------------------------------------------------------
/** "p1/days/2026-07-22/aware.json.gz" -> "aware"; "p1/aware_faults.json" -> "aware_faults". */
export function branchKey(p) {
  const b = String(p || '').split('/').pop() || '';
  return b.replace(/\.json(\.gz)?$/, '');
}
const FLEET_KEYS = ['fleet', 'cls', 'reserve', 'soc0', 'growth'];
const POLICY_ORDER = { none: 0, naive: 1, aware: 2 };
const FAIL_ORDER = { none: 0, faults: 1, worker_kill: 2, covert: 3 };

/** The option label for a lever value from the catalogue (the catalogue's own words). */
export function leverLabel(catalogue, lever, value) {
  const o = catalogue && catalogue.levers && catalogue.levers[lever];
  const hit = o && (o.options || []).find((x) => String(x.id) === String(value));
  return hit ? hit.label : String(value);
}
/** The catalogue label up to its colon: "Naive: our assumption of one number, ..." -> "Naive". */
export const shortLabel = (s) => String(s).split(':')[0].trim();
/** A short run name for compare rows: "Feeder-aware + Pieces fail", from the catalogue's lever labels. */
export function runName(scn, catalogue, short = true) {
  const L = (scn && scn.levers) || {};
  const f = short ? shortLabel : (x) => x;
  const pol = f(leverLabel(catalogue, 'policy', L.policy));
  return L.failure && L.failure !== 'none' ? `${pol} + ${f(leverLabel(catalogue, 'failure', L.failure))}` : pol;
}
/** Other committed runs of the same evening and fleet levers (every policy and failure), stable order. A scenario
 *  that replays another run (`plays`, the covert card on the aware branch) is not listed twice. */
export function siblings(scn, catalogue) {
  const all = (catalogue && catalogue.scenarios) || [];
  const L = (scn && scn.levers) || {};
  return all.filter((s) => s.id !== scn.id && s.id !== scn.plays && !s.plays && s.levers && s.levers.evening === L.evening && FLEET_KEYS.every((k) => String(s.levers[k]) === String(L[k])))
    .sort((a, b) => (POLICY_ORDER[a.levers.policy] ?? 9) - (POLICY_ORDER[b.levers.policy] ?? 9)
      || (FAIL_ORDER[a.levers.failure] ?? 9) - (FAIL_ORDER[b.levers.failure] ?? 9));
}
/** A named constant {value, label, cite} from the first doc that carries it, as a labelled value; else null. */
export function constOf(name, ...docs) {
  for (const d of docs) {
    const c = d && d.constants && d.constants[name];
    if (c && typeof c === 'object' && 'value' in c && LABELS.includes(c.label) && c.value != null) return { v: c.value, label: c.label, cite: c.cite };
  }
  return null;
}
/** The service-voltage band (V_ANSI_LO / V_ANSI_HI): extras first, then the catalogue. null when either is absent. */
export function bandOf(ex, cat) {
  const lo = constOf('V_ANSI_LO', ex, cat), hi = constOf('V_ANSI_HI', ex, cat);
  return lo && hi && fin(lo.v) && fin(hi.v) && hi.v > lo.v ? { lo, hi } : null;
}
/** The frequency effect of a battery hijack, from the catalogue constants: a BAND, never one value. */
export function hijackOf(cat) {
  const lo = constOf('HIJACK_MHZ_LO', cat), hi = constOf('HIJACK_MHZ_HI', cat), mw = constOf('HIJACK_MW', cat), units = constOf('HIJACK_UNITS', cat);
  return lo && hi && fin(lo.v) && fin(hi.v) && hi.v > lo.v ? { lo, hi, mw, units } : null;
}

/** The verdict sentence. Every no-violation claim says "because of batteries" (story-contract ruling 6). */
export function verdictOf(sm, levers = {}, tm = null) {
  const sub = tm ? `OpenDSS every ${fmtNum(tm.stepS / 60)} min, ${clockOf(0, tm)} → ${clockOf(tm.n, tm)}` : 'OpenDSS every step';
  if (!sm) return { title: 'This run\'s summary is not exported yet', sub: 'not exported for this run', ok: null };
  const v = (k) => (has(sm[k]) ? sm[k].v : null);
  if (levers.policy === 'none') {
    const ml = sm.maxLoading;
    return { title: has(ml) ? `With no batteries, home load alone takes one transformer to ${fmtNum(ml.v, 1)}%` : 'With no batteries, home load alone sets the evening', sub, ok: null };
  }
  const bn = v('batteryCausedNormal'), be = v('batteryCausedEmergency'), prot = v('protectionOperated');
  if (bn == null && be == null) return { title: 'Battery-caused events are not exported for this run', sub, ok: null };
  if (!bn && !be && !prot) return { title: 'No service transformer passed its limit because of batteries this evening', sub: `${sub} · normal rating and emergency`, ok: true };
  const parts = [];
  if (bn) parts.push(`${fmtNum(bn)} normal-rating event${bn === 1 ? '' : 's'}`);
  if (be) parts.push(`${fmtNum(be)} transformer${be === 1 ? '' : 's'} in emergency`);
  if (prot) parts.push(`${fmtNum(prot)} fuse${prot === 1 ? '' : 's'} open`);
  return { title: `Batteries caused ${parts.join(' and ')} this evening`, sub: prot ? `${sub} · fuse openings use an ASSUMPTION rule (screening)` : sub, ok: false, screening: !!prot };
}

export function tileDefs(tm) {
  return [
    { key: 'maxLoading', title: 'Worst transformer', opts: { digits: 1, unit: '%' }, where: true },
    { key: 'normalEvents', title: 'Normal-rating events', opts: { digits: 0 } },
    { key: 'vMinHome', title: 'Lowest home voltage', opts: { digits: 3, unit: ' pu' } },
    { key: 'chargedPctBy0400', title: tm ? `Fleet charged by ${clockOf(tm.n, tm)}` : 'Fleet charged at the end of the run', opts: { digits: 1, unit: '%' } },
  ];
}
/** Digits for a pu voltage: one more when 3 would round it onto the band's lower edge (0.9498 must not read 0.950). */
export const vDigits = (v, band) => (band && fin(v) && v < band.lo.v && +v.toFixed(3) >= band.lo.v ? 4 : 3);
/** Tile models: this run's labelled value (or null) and one compare row per other run. The lowest-voltage tile says
 *  when one home dips under the band's floor, and that voltage is not part of the capacity harm test (TRUTH #4). */
export function tilesModel(sm, others, tm = null, band = null) {
  return tileDefs(tm).map((d) => {
    const x = sm ? sm[d.key] : null;
    const big = has(x) ? x : null;
    const na = !!(x && isLab(x) && x.v == null);
    const volt = d.key === 'vMinHome';
    const opts = volt && big ? { ...d.opts, digits: vDigits(big.v, band) } : d.opts;
    let where = d.where && big && big.tf != null ? `T-${big.tf}${big.t ? ` at ${big.t}` : ''}` : '';
    if (volt && big) {
      where = band && big.v < band.lo.v
        ? `one home dips just under ${fmtNum(band.lo.v, decimalsOf(band.lo.v))} pu${big.t ? ` at ${big.t}` : ''}; voltage is not part of the capacity harm test`
        : big.t ? `at ${big.t}` : '';
    }
    const cmp = others.map((o) => {
      const y = o.summary ? o.summary[d.key] : null;
      const dg = volt && has(y) ? vDigits(y.v, band) : d.opts.digits;
      return { name: o.name, text: has(y) ? `${fmtNum(y.v, dg)}${d.opts.unit || ''}` : '—', missing: !has(y), label: has(y) ? y.label : null, cite: has(y) ? y.cite : null };
    });
    const labs = [...new Set(cmp.filter((c) => c.label).map((c) => c.label))];
    const cmpLabel = labs.length === 1 ? { label: labs[0], cite: cmp.find((c) => c.label).cite } : null;   // one tag when all share it
    return { ...d, opts, big, na, where, cmp, cmpLabel };
  });
}
/** The evening's other labelled facts (money, reserve, homes dark). The reserve is this scenario's lever value. */
export function eveningDefs(levers = {}) {
  return [
    { key: 'energyValueUSD', title: 'Fleet gross energy value, not Base\'s profit', opts: { money: true, digits: 2 }, skip: levers.policy === 'none' },
    { key: 'reserveBreaches', title: levers.reserve != null ? `Breaches of the ${levers.reserve}% member reserve` : 'Member reserve breaches', opts: { digits: 0 }, skip: levers.policy === 'none' },
    { key: 'homesDark', title: 'Homes dark', opts: { digits: 0, screening: true } },
    { key: 'emergencyTfs', title: 'Transformers in emergency', opts: { digits: 0 } },
  ];
}

// ---- voltage ----------------------------------------------------------------------------------------------------
/** Lowest and highest non-isolated value over the whole run (pu x1000). */
export function vExtent(rows) {
  let lo = Infinity, hi = -Infinity;
  for (const r of rows || []) for (const m of r) if (m > 0) { if (m < lo) lo = m; if (m > hi) hi = m; }
  return lo <= hi ? { lo: lo / 1000, hi: hi / 1000 } : null;
}
/** The plot's pu range: the band with a tenth of its width either side (widened to the data), else the data. */
export function vScale(band, ext) {
  let lo = null, hi = null;
  if (band) { const w = band.hi.v - band.lo.v; lo = band.lo.v - w / 10; hi = band.hi.v + w / 10; }
  if (ext) { lo = lo == null ? ext.lo : Math.min(lo, ext.lo); hi = hi == null ? ext.hi : Math.max(hi, ext.hi); }
  if (lo == null) return null;
  if (hi - lo < 1e-6) { lo -= 0.005; hi += 0.005; }
  const pad = band ? 0 : (hi - lo) * 0.08;
  return { lo: lo - pad, hi: hi + pad };
}
export const vY = (v, sc) => +(96 - (Math.max(sc.lo, Math.min(sc.hi, v)) - sc.lo) / (sc.hi - sc.lo) * 92).toFixed(2);
const rgb = (c) => `rgb(${c.slice(0, 3).join(',')})`;
// ui/lib/icons.js TIER_RGB: [0] sage (within rating), [3] overloaded 30+ min, [4] emergency, [5] no power (grey)
export const V_COL = Object.freeze({ over: rgb(TIER_RGB[3]), under: rgb(TIER_RGB[4]), ok: rgb(TIER_RGB[0]), iso: rgb(TIER_RGB[5]) });
/** 'over' above the band, 'under' below it, 'ok' inside (or when no band is exported). */
export function vClass(v, band) {
  if (!band) return 'ok';
  return v > band.hi.v ? 'over' : v < band.lo.v ? 'under' : 'ok';
}
/** Stems for one step: x in 0..1000 along busOrder, y in the 0..100 viewBox; isolated buses (0) are flagged. */
export function voltageStems(vRow, busOrder, sc, band) {
  const n = busOrder.length, out = [];
  for (let j = 0; j < n; j++) {
    const i = busOrder[j], m = vRow[i];
    const x = +(4 + (n > 1 ? j / (n - 1) : 0.5) * 992).toFixed(1);
    if (!m) { out.push({ i, x, iso: true }); continue; }
    const v = m / 1000, c = vClass(v, band);
    out.push({ i, x, v, y: vY(v, sc), cls: c, c: V_COL[c] });
  }
  return out;
}
/** The lowest non-isolated bus at one step: {i, v} or null. */
export function lowestBus(vRow) {
  let bi = -1, bv = Infinity;
  for (let i = 0; i < vRow.length; i++) if (vRow[i] > 0 && vRow[i] < bv) { bv = vRow[i]; bi = i; }
  return bi < 0 ? null : { i: bi, v: bv / 1000 };
}
/** busDistKm is indexed by position in busOrder (A.12): the distance of transformer `tf`, or null. */
export function distKmOf(ex, tf) {
  if (!ex || !Array.isArray(ex.busOrder) || !Array.isArray(ex.busDistKm)) return null;
  const j = ex.busOrder.indexOf(tf);
  return j < 0 || ex.busDistKm[j] == null ? null : ex.busDistKm[j];
}
const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
const RAMP = [[241, 238, 229], mix([241, 238, 229], TIER_RGB[0], 0.6), TIER_RGB[0].slice(0, 3)];   // high -> low inside the band: cream -> tier-0 sage
const ramp = (t) => (t < 0.5 ? mix(RAMP[0], RAMP[1], t * 2) : mix(RAMP[1], RAMP[2], (t - 0.5) * 2));
/** Heat-map colour for pu x1000 (0 = isolated): red below the band, dark red above, a sage ramp inside it (or over
 *  the plot range when no band is exported). */
export function heatRGB(m, band, sc) {
  if (!m) return TIER_RGB[5].slice(0, 3);
  const v = m / 1000;
  if (band) {
    if (v > band.hi.v) return TIER_RGB[3].slice(0, 3);
    if (v < band.lo.v) return TIER_RGB[4].slice(0, 3);
    return ramp(Math.max(0, Math.min(1, (band.hi.v - v) / (band.hi.v - band.lo.v))));
  }
  return ramp(Math.max(0, Math.min(1, (sc.hi - v) / (sc.hi - sc.lo || 1))));
}
/** Legend rows for the heat map, numbers only from the band constants. */
export function heatLegend(band) {
  const r = (c) => `rgb(${c.join(',')})`;
  const iso = { css: r(TIER_RGB[5].slice(0, 3)), text: 'isolated' };
  if (!band) return [{ css: `linear-gradient(90deg, ${r(RAMP[0])}, ${r(RAMP[2])})`, text: 'higher → lower, this run\'s range' }, iso];
  const d = Math.max(decimalsOf(band.lo.v), decimalsOf(band.hi.v));
  const lo = fmtNum(band.lo.v, d), hi = fmtNum(band.hi.v, d);
  return [
    { css: `linear-gradient(90deg, ${r(RAMP[0])}, ${r(RAMP[2])})`, text: `${hi} → ${lo} pu` },
    { css: r(TIER_RGB[4].slice(0, 3)), text: `below ${lo}` }, { css: r(TIER_RGB[3].slice(0, 3)), text: `above ${hi}` }, iso,
  ];
}

// ---- time series paths (viewBox 1000 x 100) ------------------------------------------------------------------------
export const yOf = (v, lo, hi) => +(96 - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo || 1) * 92).toFixed(2);
export function pathOf(vals, lo, hi) {
  const n = vals.length; if (!n) return '';
  let d = '';
  for (let k = 0; k < n; k++) d += `${k ? 'L' : 'M'}${(n > 1 ? k / (n - 1) * 1000 : 0).toFixed(1)},${yOf(vals[k], lo, hi)}`;
  return d;
}
export function areaOf(vals, lo, hi) {
  const n = vals.length; if (!n) return '';
  const y0 = yOf(Math.max(lo, 0), lo, hi);
  return `M0,${y0}${pathOf(vals, lo, hi).replace(/^M/, 'L')}L1000,${y0}Z`;
}
/** Reactive power model: kvar (the file stores tenths, A.12). null when the fields are not exported. */
export function reactiveModel(ex) {
  if (!ex || !Array.isArray(ex.headKVAr) || !Array.isArray(ex.capKVAr) || !ex.headKVAr.length) return null;
  const head = ex.headKVAr.map((x) => x / 10), cap = ex.capKVAr.map((x) => x / 10);
  let lo = Math.min(0, ...head, ...cap), hi = Math.max(...head, ...cap);
  if (hi <= lo) hi = lo + 1;
  const pad = (hi - lo) * 0.08; lo = lo < 0 ? lo - pad : 0; hi += pad;
  return { head, cap, lo, hi, headD: pathOf(head, lo, hi), capD: areaOf(cap, lo, hi), zeroY: yOf(0, lo, hi) };
}
export const xPct = (k, n) => `${(n > 1 ? k / (n - 1) * 100 : 0).toFixed(3)}%`;

// ---- failure and covert summaries ----------------------------------------------------------------------------------
/** The failure card: {title, sub {text, label?, cite?}, lines [{text, label?, cite?}], rows [{k, x (labelled or null), opts}],
 *  note {text, label?}, missing}. A line keeps the label its file gives it; a file without one gets no tag. */
export function failureModel(kind, d = {}) {
  const row = (k, x, opts = {}) => ({ k, x: has(x) ? x : null, opts });
  if (kind === 'faults') {
    const c = d.chaos || null, note = d.summary && d.summary.note;
    const fails = Array.isArray(d.failures) ? d.failures : null;
    const lines = fails ? fails.map((f) => ({ text: `${f.t || ''}${f.t ? ' · ' : ''}${f.text}`, label: LABELS.includes(f.label) ? f.label : null, cite: 'extras failures (sim.scenarios rule log)' }))
      : (d.events || []).map((e) => ({ text: `${e.t} · ${e.text}`, label: null }));
    const runs = constOf('CHAOS_RUNS', c);
    return {
      title: 'Pieces fail', sub: { text: 'a silent battery, an EV on one street and a controller stall, scripted on this evening' },
      lines, note: note && note.text ? { text: note.text, label: LABELS.includes(note.label) ? note.label : null } : null,
      rows: c ? [
        row('Seeded runs of this evening with random failures', runs),
        row('Runs with a battery-caused violation', c.runsWithBatteryCaused),
        row('Battery-caused normal-rating events, all runs', c.batteryCausedNormal),
        row('Reserve breaches, all runs', c.reserveBreaches),
        row('Worst charge at the end of the batteries that kept talking', c.minChargedPctResponsive, { digits: 1, unit: '%' }),
      ] : [],
      missing: c ? null : 'p1/chaos.json not loaded',
    };
  }
  if (kind === 'worker_kill') {
    const s = d.summary || {}, rt = d.runtime || {};
    // the extras rule log carries labels (kill ASSUMPTION, takeover and late batch SIM); the branch runtime is the fallback
    const mom = (d.moments || []).filter((m) => ['fault', 'takeover', 'lateCommands'].includes(m.rule));
    const ml = (m) => ({ text: `${m.t} · ${m.text}`, label: LABELS.includes(m.label) ? m.label : null, cite: 'extras moments (sim.scenarios rule log)' });
    const kill = mom.find((m) => m.rule === 'fault');
    return {
      title: 'Controller crash',
      sub: kill ? ml(kill) : rt.kill && rt.kill.text ? { text: `${rt.kill.t} · ${rt.kill.text}` } : { text: 'one controller worker is killed mid-evening' },
      lines: kill ? mom.filter((m) => m !== kill).map(ml)
        : [...(rt.takeover || []).map((t) => ({ text: `${t.t} · ${t.text}` })), ...(rt.late && rt.late.text ? [{ text: `${rt.late.t} · ${rt.late.text}` }] : [])],
      note: null,
      rows: [
        row('Takeover after the kill', s.takeoverSeconds, { digits: 0, unit: ' s' }),
        row('Worst fleet tracking error, kill to takeover', s.trackingMaxErrPct, { digits: 1, unit: '%' }),
        row('Same minutes without the kill', s.baselineMaxErrPct, { digits: 1, unit: '%' }),
        row('Largest power the kill moved', s.killCostMaxKW, { digits: 1, unit: ' kW' }),
        row('Energy without the kill minus with it', s.killCostKWh, { digits: 2, unit: ' kWh' }),
        row('Late commands from the dead worker', s.lateCommands),
        row('Refused on a stale epoch', s.rejectedStaleEpoch),
      ],
      missing: has(s.takeoverSeconds) ? null : 'takeover summary not exported',
    };
  }
  if (kind === 'covert') {
    const cv = d.covert || null, s = (cv && cv.summary) || d.attackSummary || null;
    const S = s || {};
    const flagged = has(S.detected) && has(S.shard) ? { v: `${fmtNum(S.detected.v)} of ${fmtNum(S.shard.v)}`, label: S.detected.label, cite: `${S.detected.cite}; shard ${S.shard.label}: ${S.shard.cite}` } : null;
    const adv = cv && cv.sources && cv.sources.adversary && LABELS.includes(cv.sources.adversary.label) ? cv.sources.adversary : null;
    const det = cv && cv.sources && cv.sources.detector && LABELS.includes(cv.sources.detector.label) ? cv.sources.detector : null;
    return {
      title: 'Hidden attacker',
      sub: cv && cv.attack ? { text: `${cv.attack.t} · ${cv.attack.text}`, label: adv ? adv.label : null, cite: adv ? adv.text : null } : { text: 'a fictional adversary inside the fleet' },
      lines: [], note: { text: 'Fictional attacker: no real company or person. Found from physics (telemetry vs the home\'s own voltage), not command logs.', label: det ? det.label : null, cite: det ? det.text : null },
      rows: s ? [
        row('Compromised units flagged', flagged),
        row('First flag after the channel opens', S.detectionSeconds, { digits: 0, unit: ' s' }),
        row('All flagged after', S.allDetectedSeconds, { digits: 0, unit: ' s' }),
        row('False positives, clean evening', S.falsePositivesClean),
        row('False positives, during the attack', S.falsePositivesAttack),
        row('Quarantined (held at zero)', S.quarantined),
      ] : [],
      missing: s ? null : 'not built yet: the attack summary',
    };
  }
  return null;
}

/** ERCOT frequency card model from ui/data/ems/freq-series.json (REAL samples; sigma DERIVED) and the hijack band.
 *  The plot's range is the day's own minimum and maximum; the band hangs from the nominal f0 when the file has it. */
export function freqModel(f, hij) {
  const s = f && f.series_1min && Array.isArray(f.series_1min.f_mean_hz) ? f.series_1min.f_mean_hz.filter(fin) : null;
  if (!s || !s.length) return null;
  const dmin = Math.min(...s), dmax = Math.max(...s);
  const f0c = f.constants && f.constants.f0_hz;
  const f0 = f0c == null ? null : fin(f0c) ? f0c : fin(f0c.value) ? f0c.value : null;
  let lo = dmin, hi = dmax;
  if (f0 != null && hij) lo = Math.min(lo, f0 - hij.hi.v / 1000);
  const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
  const day = /^(\d{4}-\d{2}-\d{2})/.exec(f.series_1min.t0_cdt || '');
  const sig = f.stats && f.stats.frequency ? f.stats.frequency.sigma_mhz : null;
  // the samples' label: every provenance entry's status, when they agree; sigma is "our arithmetic on REAL" in the
  // file's own status legend
  const st = [...new Set(Object.values(f.provenance || {}).map((p) => p && p.status).filter((x) => LABELS.includes(x)))];
  const sampleLabel = st.length === 1 ? st[0] : null;
  const legend = f.status_legend || {};
  return {
    day: day ? day[1] : null, lo, hi, dmin, dmax, d: pathOf(s, lo, hi), f0, y0: f0 != null ? yOf(f0, lo, hi) : null,
    bandTop: f0 != null && hij ? yOf(f0 - hij.lo.v / 1000, lo, hi) : null, bandBot: f0 != null && hij ? yOf(f0 - hij.hi.v / 1000, lo, hi) : null,
    sampleLabel,
    sigma: fin(sig) && legend.DERIVED ? { v: sig, label: 'DERIVED', cite: `standard deviation of that day's ERCOT frequency samples (freq-series.json stats.frequency.sigma_mhz); DERIVED = ${legend.DERIVED} (the file's status legend)` } : null,
    n: s.length,
  };
}

// =================================================================================================================
// DOM
// =================================================================================================================
function numH(ctx, x, opts = {}) {
  if (!has(x)) return missingHTML(x && isLab(x) && x.v == null ? 'n/a' : 'not exported for this run');
  try { return ctx.num(x, opts); } catch (e) { console.error('[results] unlabelled value refused', x, e); return missingHTML('unlabelled value refused'); }
}
async function tryGet(fn) {
  try { return { doc: await fn(), err: null }; } catch (e) { return { doc: null, err: e }; }
}
const notBuilt = (err, path) => (err && err.status === 404 ? `not built yet: ${path}` : `could not load ${path}`);
const NONE = Promise.resolve({ doc: null, err: null });

export async function mount(root, ctx) {
  const scn = ctx.scenario || {};
  const cat = ctx.catalogue || {};
  const L = scn.levers || {};
  const failure = L.failure || 'none';
  const bk = branchKey(scn.branch);
  root.classList.add('pb-page', 'pb-results');
  root.innerHTML = '<div class="pb-loading">Loading this run\'s results…</div>';

  // ---- load: extras, meta (events, clock, fallback summary), failure docs, frequency (covert only) ----
  const [exR, metaR] = await Promise.all([
    scn.extras ? tryGet(() => ctx.getAny(scn.extras)) : NONE,
    scn.meta ? tryGet(() => ctx.getAny(scn.meta)) : NONE,
  ]);
  const ex = exR.doc, meta = metaR.doc;
  let sm = scn.summary || (meta && meta.summary && meta.summary[bk]) || null;
  if (failure === 'covert' && scn.attackSummary && sm) {
    const a = scn.attackSummary;
    sm = { ...sm, ...Object.fromEntries(Object.keys(sm).filter((k) => isLab(a[k])).map((k) => [k, a[k]])) };
  }
  let fdata = {}, freq = null, freqErr = null;
  if (failure === 'faults') {
    const c = await tryGet(() => ctx.getJSON('p1/chaos.json'));
    fdata = { chaos: c.doc, failures: ex && Array.isArray(ex.failures) ? ex.failures.map((f) => ({ ...f, t: f.t || null })) : null,
      events: (meta && meta.events && meta.events[bk]) || [], summary: sm };
  } else if (failure === 'worker_kill') {
    // the branch doc carries runtime (kill, takeover, late batch); its summary fills in when the catalogue's lacks it
    const w = scn.branch ? await tryGet(() => ctx.getAny(scn.branch)) : { doc: null };
    const runtime = w.doc ? w.doc.runtime || null : null;
    if (w.doc && (!sm || !has(sm.takeoverSeconds))) sm = w.doc.summary || sm;
    fdata = { summary: sm, runtime, moments: ex && Array.isArray(ex.moments) ? ex.moments : null };
  } else if (failure === 'covert') {
    const cpath = scn.attack || null;
    const [c, f] = await Promise.all([cpath ? tryGet(() => ctx.getJSON(cpath)) : NONE, tryGet(() => ctx.getJSON('ems/freq-series.json'))]);
    fdata = { covert: c.doc, attackSummary: scn.attackSummary || null, covertErr: !cpath ? 'the catalogue names no attack file' : c.err ? notBuilt(c.err, cpath) : null };
    freq = f.doc; freqErr = f.err ? notBuilt(f.err, 'ems/freq-series.json') : null;
  }
  const others = siblings(scn, cat).map((s) => ({ id: s.id, name: runName(s, cat), summary: s.summary || null }));

  // ---- derived view state ----
  const tm = timeOf(ex, meta);
  const n = tm ? tm.n : 0;
  if (fdata.failures) for (const f of fdata.failures) f.t = f.t || clockOf(f.k0, tm);
  const hasV = !!(tm && ex && Array.isArray(ex.vTfMilli) && ex.vTfMilli.length === n && Array.isArray(ex.busOrder) && ex.busOrder.length);
  const band = bandOf(ex, cat);
  const vsc = hasV ? vScale(band, vExtent(ex.vTfMilli)) : null;
  const series = (ex && ex.series) || {};
  const sLabel = (k) => (series[k] && LABELS.includes(series[k].label) ? series[k].label : null);
  const sTag = (k, cite) => { const l = sLabel(k); return l ? tagHTML(l, cite) : ''; };
  const pf = constOf('BATTERY_PF', meta);
  const rq = tm && ex && Array.isArray(ex.headKVAr) && ex.headKVAr.length === n ? reactiveModel(ex) : null;
  const fm = failure !== 'none' ? failureModel(failure, fdata) : null;
  const hij = hijackOf(cat);
  const fq = failure === 'covert' ? freqModel(freq, hij) : null;
  const verdict = verdictOf(sm, L, tm);
  const tiles = tilesModel(sm, others, tm, band);
  let k = 0;
  const fromLink = ctx.params && ctx.params.k != null;
  if (fromLink || !(ex && Array.isArray(ex.worstPct) && ex.worstPct.length)) k = Number.isFinite(ctx.k) ? ctx.k : 0;
  else { let w = 0; ex.worstPct.forEach((v, i) => { if (v > ex.worstPct[w]) w = i; }); k = w; }
  k = n ? Math.max(0, Math.min(n - 1, Math.round(k))) : 0;

  const evening = leverLabel(cat, 'evening', L.evening);
  const absent = (k) => !!(ex && Array.isArray(ex.absent) && ex.absent.includes(k));
  const exMissing = !ex ? (exR.err ? notBuilt(exR.err, scn.extras) : 'not exported for this run') : !tm ? 'this run\'s clock (steps, start, stepSeconds) is not exported' : null;
  const vTag = sTag('vTfMilli', 'OpenDSS lowest home voltage per transformer (extras vTfMilli)');
  // the verdict's tag is the label of the fields it is built from
  const vk = sm && [sm.batteryCausedNormal, sm.batteryCausedEmergency, sm.maxLoading].find(isLab);
  const bandTag = band ? tagHTML(band.lo.label, `${band.lo.cite}; ${band.hi.cite}`) : '';
  const bd = band ? Math.max(decimalsOf(band.lo.v), decimalsOf(band.hi.v)) : 0;
  const bandTxt = band ? `band ${fmtNum(band.lo.v, bd)}–${fmtNum(band.hi.v, bd)} pu` : '';
  const ticks = timeTicks(tm);
  const moments = ex && Array.isArray(ex.moments) && tm ? ex.moments.filter((m) => Number.isInteger(m.k) && m.k >= 0 && m.k < n) : [];

  // ---- markup ----
  const tileH = tiles.map((t) => `
    <div class="pb-card pb-tile">
      <div class="pb-tile-h"><span class="pb-card-t">${esc(t.title)}</span></div>
      <div class="pb-tile-big">${t.big ? numH(ctx, t.big, t.opts) : missingHTML(t.na ? (L.policy === 'none' && t.key === 'chargedPctBy0400' ? 'no batteries in this run' : 'n/a') : 'not exported for this run')}</div>
      ${t.where ? `<div class="pb-tile-where">${esc(t.where)}</div>` : ''}
      <div class="pb-cmp">${t.cmp.length ? `${t.cmpLabel ? `<div class="pb-cmp-row pb-cmp-h"><span>other runs, same evening</span>${tagHTML(t.cmpLabel.label, t.cmpLabel.cite)}</div>` : ''}${t.cmp.map((c) => `<div class="pb-cmp-row${c.missing ? ' pb-dim' : ''}"><span>${esc(c.name)}</span><span>${esc(c.text)}${!t.cmpLabel && c.label ? tagHTML(c.label, c.cite) : ''}</span></div>`).join('')}` : '<div class="pb-cmp-row pb-dim"><span>no other committed run for these levers</span></div>'}</div>
    </div>`).join('');

  // the reserve in the row title is this scenario's lever value: tagged with the catalogue's own reason for it
  const rOpt = cat.levers && cat.levers.reserve && (cat.levers.reserve.options || []).find((o) => String(o.id) === String(L.reserve));
  const rWhy = rOpt && rOpt.why && LABELS.includes(rOpt.why.label) ? { label: rOpt.why.label, cite: `${rOpt.why.text}; ${rOpt.why.cite || ''}` } : constOf('STORY_RESERVES_PCT', cat);
  const eveningH = eveningDefs(L).filter((d) => !d.skip).map((d) => `<div class="pb-kv"><span>${esc(d.title)}${d.key === 'reserveBreaches' && L.reserve != null && rWhy ? tagHTML(rWhy.label, rWhy.cite) : ''}</span><span>${numH(ctx, sm ? sm[d.key] : null, d.opts)}</span></div>`).join('');
  const naiveNote = L.policy === 'naive' || others.some((o) => /^Naive/.test(o.name)) ? `<div class="pb-note">${esc(leverLabel(cat, 'policy', 'naive'))}.</div>` : '';

  const failH = fm ? `
    <div class="pb-card pb-fail">
      <div class="pb-card-h"><span class="pb-card-t">${esc(fm.title)}</span>${failure === 'covert' ? '<span class="pb-sub">Fictional attacker</span>' : ''}</div>
      <div class="pb-sub pb-clip2">${esc(fm.sub.text)}${fm.sub.label ? tagHTML(fm.sub.label, fm.sub.cite) : ''}</div>
      ${fm.lines.length ? `<ul class="pb-lines">${fm.lines.map((l) => `<li>${esc(l.text)}${l.label ? tagHTML(l.label, l.cite) : ''}</li>`).join('')}</ul>` : ''}
      ${fm.rows.map((r) => `<div class="pb-kv"><span>${esc(r.k)}</span><span>${r.x ? numH(ctx, r.x, r.opts) : missingHTML()}</span></div>`).join('')}
      ${fm.missing || fdata.covertErr ? `<div class="pb-kv">${missingHTML(fdata.covertErr || fm.missing)}</div>` : ''}
      ${fm.note ? `<div class="pb-note">${esc(fm.note.text)}${fm.note.label ? tagHTML(fm.note.label, fm.note.cite) : ''}</div>` : ''}
    </div>` : '';

  const hijH = hij ? `<span class="num">${fmtNum(hij.lo.v)}–${fmtNum(hij.hi.v)} mHz</span>${tagHTML(hij.lo.label, `${hij.lo.cite}; ${hij.hi.cite}`)}` : missingHTML('band not exported');
  const freqH = failure === 'covert' ? `
    <div class="pb-card pb-freq">
      <div class="pb-card-h"><span class="pb-card-t">ERCOT frequency</span><span class="pb-sub">${fq && fq.day ? esc(fq.day) : ''} · a different day</span>${fq && fq.sampleLabel ? tagHTML(fq.sampleLabel, 'ERCOT dashboards, 1-minute mean of the 10-s samples (freq-series.json provenance, every source\'s status)') : ''}</div>
      ${fq ? `<div class="pb-plot pb-freq-plot">
        <svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-label="ERCOT frequency, a different day">
          <rect width="1000" height="100" fill="#f6f3ea"/>
          ${fq.bandTop != null ? `<rect x="930" width="60" y="${fq.bandTop}" height="${Math.max(0.5, fq.bandBot - fq.bandTop).toFixed(2)}" fill="#e4efe6" stroke="#1e4d2b" stroke-width="1" vector-effect="non-scaling-stroke"/>` : ''}
          ${fq.y0 != null ? `<line x1="0" x2="1000" y1="${fq.y0}" y2="${fq.y0}" stroke="#10231a" stroke-opacity=".25" vector-effect="non-scaling-stroke"/>` : ''}
          <path d="${fq.d}" fill="none" stroke="#10231a" stroke-width="1" vector-effect="non-scaling-stroke" transform="scale(0.92,1)"/>
        </svg>
        <span class="pb-axis pb-axis-tl">${esc(fmtNum(fq.dmax, 3))} Hz</span><span class="pb-axis pb-axis-bl">${esc(fmtNum(fq.dmin, 3))} Hz</span>
      </div>
      <div class="pb-kv"><span>Normal wander that day (σ)</span><span>${numH(ctx, fq.sigma, { digits: 1, unit: ' mHz' })}</span></div>
      ${hij && hij.mw ? `<div class="pb-kv"><span>A hijack${hij.units ? ` of ${numH(ctx, hij.units, { digits: 0 })} batteries` : ''} swings</span><span>${numH(ctx, hij.mw, { digits: 0, unit: ' MW' })}</span></div>` : ''}
      <div class="pb-kv"><span>which moves frequency by</span><span>${hijH}</span></div>
      <div class="pb-note">Same scale: the bracket at the right edge is the hijack band beside a whole day of normal wander. The feeder sees the attack; grid-wide frequency cannot single it out.</div>`
      : `<div class="pb-kv">${missingHTML(freqErr || 'frequency series not loaded')}</div><div class="pb-kv"><span>A hijack${hij && hij.units ? ` of ${numH(ctx, hij.units, { digits: 0 })} batteries` : ''} moves frequency by</span><span>${hijH}</span></div>`}
    </div>` : '';

  root.innerHTML = `
    <div class="pb-row1">
      <div class="pb-card pb-verdict${verdict.ok === false ? ' pb-verdict-bad' : ''}">
        <div class="pb-eyebrow">THIS EVENING · ${esc(String(evening).toUpperCase())} · ${esc(runName(scn, cat).toUpperCase())}</div>
        <div class="pb-verdict-t">${esc(verdict.title)}</div>
        <div class="pb-verdict-s">${vk ? tagHTML(vk.label, vk.cite, !!verdict.screening) : ''}<span>${esc(verdict.sub)}</span></div>
      </div>
      ${tileH}
    </div>
    <div class="pb-row2">
      <div class="pb-card pb-vbus">
        <div class="pb-card-h"><span class="pb-card-t">Voltage by bus</span><span class="pb-sub">lowest home per service transformer, pu, at <b data-pb="clock"></b></span><span class="pb-right pb-sub" data-pb="vnow"></span></div>
        <div class="pb-plot" data-pb="vplot">${hasV ? `
          <svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-label="Voltage by bus">
            ${band ? `<rect x="0" y="${vY(band.hi.v, vsc)}" width="1000" height="${(vY(band.lo.v, vsc) - vY(band.hi.v, vsc)).toFixed(2)}" fill="#eef2ea"/>
            <line x1="0" x2="1000" y1="${vY(band.hi.v, vsc)}" y2="${vY(band.hi.v, vsc)}" stroke="#b23a2f" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>
            <line x1="0" x2="1000" y1="${vY(band.lo.v, vsc)}" y2="${vY(band.lo.v, vsc)}" stroke="#b23a2f" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>` : ''}
            <g data-pb="stems"></g>
          </svg>
          ${band ? `<span class="pb-axis pb-red" style="top:calc(${vY(band.hi.v, vsc)}% - 14px)">${fmtNum(band.hi.v, bd)}</span><span class="pb-axis pb-red" style="top:calc(${vY(band.lo.v, vsc)}% + 1px)">${fmtNum(band.lo.v, bd)}</span>`
    : `<span class="pb-axis pb-axis-tl">${fmtNum(vsc.hi, 3)}</span><span class="pb-axis" style="top:calc(96% - 14px)">${fmtNum(vsc.lo, 3)}</span>`}
` : `<div class="pb-empty">${missingHTML(exMissing || (absent('vTfMilli') ? 'not exported for this run: this replay records no voltage per transformer' : 'voltage by bus not exported for this run'))}</div>`}
        </div>
        ${hasV ? '<div class="pb-xaxis"><span>← near the substation</span><span>far end →</span></div>' : ''}
        <div class="pb-foot">${hasV ? `${vTag}OpenDSS, every transformer · order ${sTag('busOrder', 'path distance from the substation along the SMART-DS lines (extras busOrder)')} path distance from the substation · ${band ? `${bandTxt} ${bandTag}` : missingHTML('band not exported for this run')}` : 'Voltage by bus comes from the engine\'s extras export'}</div>
      </div>
      <div class="pb-card pb-q">
        <div class="pb-card-h"><span class="pb-card-t">Reactive power</span><span class="pb-sub">kvar at the feeder head</span><span class="pb-right pb-sub" data-pb="qnow"></span></div>
        <div class="pb-plot pb-scrub" data-pb="qplot">${rq ? `
          <svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-label="Reactive power">
            <rect width="1000" height="100" fill="#f6f3ea"/>
            <path d="${rq.capD}" fill="#c9cfc4"/>
            <line x1="0" x2="1000" y1="${rq.zeroY}" y2="${rq.zeroY}" stroke="#1e4d2b" stroke-width="2" vector-effect="non-scaling-stroke"/>
            <path d="${rq.headD}" fill="none" stroke="#10231a" stroke-width="1.5" vector-effect="non-scaling-stroke"/>
          </svg>
          <span class="pb-axis pb-axis-tl">${esc(fmtNum(rq.hi, 0))}</span><span class="pb-axis pb-axis-bl">${esc(fmtNum(rq.lo, 0))}</span>
          <div class="pb-cursor" data-pb="cur"></div>` : `<div class="pb-empty">${missingHTML(exMissing || (absent('headKVAr') ? 'not exported for this run: this replay records no feeder-head reactive power' : 'reactive power not exported for this run'))}</div>`}
        </div>
        ${rq ? `<div class="pb-legend"><span><i class="pb-sw-line"></i>feeder head ${sTag('headKVAr', 'OpenDSS feeder-head Q (extras headKVAr)')}</span><span><i class="pb-sw-area"></i>capacitor bank ${sTag('capKVAr', 'OpenDSS capacitor output (extras capKVAr)')}</span>${pf ? `<span><i class="pb-sw-brand"></i>our inverters: power factor ${numH(ctx, pf, { digits: 0 })}, no reactive power</span>` : ''}</div>` : ''}
      </div>
    </div>
    <div class="pb-row3${fm ? ' pb-has-fail' : ''}${failure === 'covert' ? ' pb-has-freq' : ''}">
      <div class="pb-card pb-heat">
        <div class="pb-card-h"><span class="pb-card-t">Voltage over the evening</span><span class="pb-sub">every transformer (rows, substation at top) × every step</span>${hasV ? vTag : ''}</div>
        <div class="pb-plot pb-scrub" data-pb="hplot">${hasV ? `<canvas data-pb="heat" width="${n}" height="${ex.busOrder.length}"></canvas><div class="pb-cursor" data-pb="cur"></div>` : `<div class="pb-empty">${missingHTML(exMissing || (absent('vTfMilli') ? 'not exported for this run: this replay records no voltage per transformer' : 'not exported for this run'))}</div>`}</div>
        <div class="pb-legend pb-heat-legend">${hasV ? heatLegend(band).map((l) => `<span><i style="background:${l.css}"></i>${esc(l.text)}</span>`).join('') + (band ? bandTag : missingHTML('band not exported for this run')) : ''}</div>
      </div>
      <div class="pb-card pb-evening">
        <div class="pb-card-h"><span class="pb-card-t">The evening in numbers</span></div>
        ${sm ? eveningH : `<div class="pb-kv">${missingHTML()}</div>`}
        <div class="pb-note">Fleet gross energy value is REAL LZ_NORTH prices × simulated battery kW: not Base's profit.</div>
        ${naiveNote}
      </div>
      ${failH}${freqH}
    </div>
    <div class="pb-scrubber${tm ? ' pb-scrub' : ''}" data-pb="scrub">
      <span class="pb-clock" data-pb="clock2">${tm ? '' : missingHTML('clock not exported')}</span>
      <div class="pb-track"><div class="pb-track-bg"></div>
        ${moments.map((m) => `<i class="pb-mom" style="left:${xPct(m.k, n)}" title="${esc(`${m.t || clockOf(m.k, tm)} · ${m.text}${m.label ? ` (${m.label})` : ''}`)}"></i>`).join('')}
        ${tm ? '<div class="pb-knob" data-pb="knob"><i></i></div>' : ''}
        <div class="pb-ticks">${ticks.map((t) => `<span style="left:${(t.x * 100).toFixed(3)}%">${esc(t.t)}</span>`).join('')}</div></div>
      <span class="pb-sub">${tm ? 'Drag to read any minute' : ''}</span>
    </div>`;

  const $ = (sel) => root.querySelector(`[data-pb="${sel}"]`);
  const $$ = (sel) => [...root.querySelectorAll(`[data-pb="${sel}"]`)];

  // ---- heat map (drawn once) ----
  if (hasV) {
    const cv = $('heat'), g = cv && cv.getContext && cv.getContext('2d');
    if (g) {
      const B = ex.busOrder, img = g.createImageData(n, B.length);
      for (let kk = 0; kk < n; kk++) {
        const row = ex.vTfMilli[kk] || [];
        for (let j = 0; j < B.length; j++) { const c = heatRGB(row[B[j]], band, vsc), o = (j * n + kk) * 4; img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255; }
      }
      g.putImageData(img, 0, 0);
    }
  }

  // ---- cursor-dependent parts ----
  function update(kNew) {
    if (!tm || !Number.isFinite(kNew)) return;
    k = Math.max(0, Math.min(n - 1, Math.round(kNew)));
    const clock = clockOf(k, tm);
    for (const el of [$('clock'), $('clock2')]) if (el) el.textContent = clock;
    const left = xPct(k, n);
    for (const el of $$('cur')) el.style.left = left;
    const knob = $('knob'); if (knob) knob.style.left = left;
    if (hasV) {
      const row = ex.vTfMilli[k] || [];
      const st = voltageStems(row, ex.busOrder, vsc, band);
      const base = band ? vY((band.lo.v + band.hi.v) / 2, vsc) : 98;
      $('stems').innerHTML = st.map((b) => (b.iso
        ? `<line x1="${b.x}" x2="${b.x}" y1="98" y2="100" stroke="${V_COL.iso}" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`
        : `<line x1="${b.x}" x2="${b.x}" y1="${base}" y2="${b.y}" stroke="${b.c}" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`)).join('');
      const lo = lowestBus(row), iso = st.filter((b) => b.iso).length;
      const dist = lo ? distKmOf(ex, lo.i) : null;
      $('vnow').innerHTML = lo ? `lowest <b>${fmtNum(lo.v, 3)} pu</b> at T-${lo.i}${dist != null ? `, ${fmtNum(dist, 1)} km out ${sTag('busDistKm', 'extras busDistKm: along the SMART-DS lines')}` : ''}${iso ? ` · ${iso} isolated` : ''} ${vTag}` : 'every bus isolated';
    } else if ($('vnow')) $('vnow').textContent = '';
    if (rq && $('qnow')) $('qnow').innerHTML = `head <b>${fmtNum(rq.head[k], 0)}</b> · capacitor <b>${fmtNum(rq.cap[k], 0)}</b> kvar ${sTag('headKVAr', 'extras headKVAr / capKVAr')}`;
  }

  // ---- scrubbing: every time-axis element seeks ----
  let drag = null;
  const kFrom = (e, el) => { const r = el.getBoundingClientRect(); return (e.clientX - r.left) / (r.width || 1) * (n - 1); };
  const seek = (kk) => { update(kk); try { if (ctx.setK) ctx.setK(k); } catch (e) { console.error('[results] setK', e); } };
  const handlers = [];
  if (tm) {
    for (const el of root.querySelectorAll('.pb-scrub')) {
      const target = el.querySelector('.pb-track') || el;
      const down = (e) => { drag = target; try { el.setPointerCapture(e.pointerId); } catch (x) { /* synthetic events */ } seek(kFrom(e, target)); };
      const move = (e) => { if (drag === target) seek(kFrom(e, target)); };
      const up = () => { drag = null; };
      el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
      handlers.push([el, down, move, up]);
    }
  }
  const off = typeof ctx.onK === 'function' ? ctx.onK((kk) => { if (kk !== k) update(kk); }) : null;
  update(k);
  // opened without &k=: the page starts at the worst minute and moves the shared cursor there
  if (tm && !fromLink && k !== ctx.k && typeof ctx.setK === 'function') { try { ctx.setK(k); } catch (e) { console.error('[results] setK', e); } }

  return {
    setK(kk) { if (kk !== k) update(kk); },
    dispose() {
      if (typeof off === 'function') off();
      for (const [el, d, m, u] of handlers) { el.removeEventListener('pointerdown', d); el.removeEventListener('pointermove', m); el.removeEventListener('pointerup', u); el.removeEventListener('pointercancel', u); }
      root.innerHTML = '';
      root.classList.remove('pb-page', 'pb-results');
    },
  };
}
