// ui/story/results.js (UI-B): Screen 3a Results (docs/design-handoff/story-flow/README.md "Screen 3").
// Verdict + four tiles against the other committed runs of the same evening/levers; money, reserve, homes dark;
// voltage by bus at the shared cursor and the bus x time heat map (extras vTfMilli by busOrder); reactive power
// (extras headKVAr, capKVAr; our inverters 0 at unity power factor, ASSUMPTION); failure summaries; ERCOT context
// ONLY for the covert scenario (REAL 25 Sep 2026 frequency, "a different day", beside the 3-17 mHz band).
// Every number comes from a data file with its label. A missing file or field says so; it is never drawn as zero.
// Pure view functions are exported for ui/test/pagesb-results.test.js; mount() is the DOM half.

export const PAGE = 'results';

// The frequency effect of a 1,000-battery hijack: a BAND, never one value, never 3-5 mHz (CLAUDE.md non-negotiable).
// Single named value (docs/design.md §10 rule); not yet in sim/constants.py, so it lives here with its cite.
export const HIJACK_FREQ_BAND_MHZ = Object.freeze({
  lo: 3, hi: 17, label: 'DERIVED',
  cite: 'about 40 MW for 1,000 batteries at ERCOT load damping and governor deadband; docs/research-report.md §frequency (DERIVED, corrected 26 Sep 2026 from 3-5 mHz)',
});

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];
export const isLab = (x) => x != null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
const has = (x) => isLab(x) && x.v != null;

/** A plain provenance tag (for series whose label lives in `series`). `screening` draws the dashed variant. */
export function tagHTML(label, cite, screening = false) {
  const word = screening ? 'SCREENING' : label;
  return `<span class="pb-tag${screening ? ' pb-tag-screen' : ''}"${cite ? ` title="${esc(cite)}"` : ''}>${esc(word)}</span>`;
}
export const missingHTML = (what = 'not exported for this run') => `<span class="pb-missing">${esc(what)}</span>`;

// ---- small numeric helpers (plain text; the tile's tag covers its compare rows, as the 3a reference) ----
export function fmtNum(v, d = 0) {
  if (v == null || !Number.isFinite(+v)) return '—';
  return Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
export function clockOf(k, start = '16:00', stepSeconds = 60) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(start || '16:00') || [0, 16, 0];
  const t = ((+m[1] * 60 + +m[2] + Math.round(k * stepSeconds / 60)) % 1440 + 1440) % 1440;
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
}

/** "p1/days/2026-07-22/aware.json.gz" -> "aware"; "p1/aware_faults.json" -> "aware_faults". */
export function branchKey(p) {
  const b = String(p || '').split('/').pop() || '';
  return b.replace(/\.json(\.gz)?$/, '');
}

const FLEET_KEYS = ['fleet', 'cls', 'reserve', 'soc0', 'growth'];
const POLICY_ORDER = { none: 0, naive: 1, aware: 2 };
const FAIL_ORDER = { none: 0, faults: 1, worker_kill: 2, covert: 3 };

/** The option label for a lever value from the catalogue (never a hard-coded name when the catalogue has one). */
export function leverLabel(catalogue, lever, value) {
  const o = catalogue && catalogue.levers && catalogue.levers[lever];
  const hit = o && (o.options || []).find((x) => String(x.id) === String(value));
  return hit ? hit.label : String(value);
}

/** A short run name: "Feeder-aware + Pieces fail", from the lever labels. */
export function runName(scn, catalogue) {
  const L = (scn && scn.levers) || {};
  const pol = leverLabel(catalogue, 'policy', L.policy);
  return L.failure && L.failure !== 'none' ? `${pol} + ${leverLabel(catalogue, 'failure', L.failure)}` : pol;
}

/** Other committed runs of the same evening and fleet levers (every policy and failure), in a stable order. */
export function siblings(scn, catalogue) {
  const all = (catalogue && catalogue.scenarios) || [];
  const L = scn.levers || {};
  return all.filter((s) => s.id !== scn.id && s.levers && s.levers.evening === L.evening && FLEET_KEYS.every((k) => String(s.levers[k]) === String(L[k])))
    .sort((a, b) => (POLICY_ORDER[a.levers.policy] ?? 9) - (POLICY_ORDER[b.levers.policy] ?? 9)
      || (FAIL_ORDER[a.levers.failure] ?? 9) - (FAIL_ORDER[b.levers.failure] ?? 9));
}

/** The verdict sentence. Every no-violation claim says "because of batteries" (story-contract ruling 6). */
export function verdictOf(sm, levers = {}) {
  if (!sm) return { title: 'This run\'s summary is not exported yet', sub: 'not exported for this run', ok: null };
  const v = (k) => (has(sm[k]) ? sm[k].v : null);
  const sub = 'OpenDSS every minute, 16:00 → 04:00';
  if (levers.policy === 'none') {
    const ml = sm.maxLoading;
    return { title: has(ml) ? `With no batteries, home load alone takes one transformer to ${fmtNum(ml.v, 1)}%` : 'With no batteries, home load alone sets the evening',
      sub, ok: null };
  }
  const bn = v('batteryCausedNormal'), be = v('batteryCausedEmergency'), prot = v('protectionOperated');
  if (bn == null && be == null) return { title: 'Battery-caused events are not exported for this run', sub, ok: null };
  if (!bn && !be && !prot) return { title: 'No service transformer passed its limit because of batteries this evening', sub: `${sub} · normal rating and emergency`, ok: true };
  const parts = [];
  if (bn) parts.push(`${fmtNum(bn)} normal-rating event${bn === 1 ? '' : 's'}`);
  if (be) parts.push(`${fmtNum(be)} transformer${be === 1 ? '' : 's'} in emergency`);
  if (prot) parts.push(`${fmtNum(prot)} fuse${prot === 1 ? '' : 's'} open`);
  return { title: `Batteries caused ${parts.join(' and ')} this evening`, sub, ok: false };
}

export const TILE_DEFS = [
  { key: 'maxLoading', title: 'Worst transformer', opts: { digits: 1, unit: '%' }, where: true },
  { key: 'normalEvents', title: 'Normal-rating events', opts: { digits: 0 } },
  { key: 'vMinHome', title: 'Lowest home voltage', opts: { digits: 3, unit: ' pu' } },
  { key: 'chargedPctBy0400', title: 'Fleet charged by 04:00', opts: { digits: 1, unit: '%' } },
];

/** Tile models: this run's labelled value (or null) and one compare row per other run. */
export function tilesModel(sm, others) {
  return TILE_DEFS.map((d) => {
    const x = sm ? sm[d.key] : null;
    const big = has(x) ? x : null;
    const why = x && isLab(x) && x.v == null ? (x.cite || 'not applicable') : null;
    const where = d.where && big && big.tf != null ? `T-${big.tf}${big.t ? ` at ${big.t}` : ''}` : '';
    const cmp = others.map((o) => {
      const y = o.summary ? o.summary[d.key] : null;
      return { name: o.name, text: has(y) ? `${fmtNum(y.v, d.opts.digits)}${d.opts.unit || ''}` : '—', missing: !has(y) };
    });
    return { ...d, big, why, where, cmp };
  });
}

/** The evening's other labelled facts (money, reserve, homes dark). */
export const EVENING_DEFS = [
  { key: 'energyValueUSD', title: 'Gross energy value, not Base\'s profit', opts: { money: true, digits: 2 } },
  { key: 'reserveBreaches', title: '20% member reserve breaches', opts: { digits: 0 } },
  { key: 'homesDark', title: 'Homes dark', opts: { digits: 0 } },
  { key: 'emergencyTfs', title: 'Transformers in emergency', opts: { digits: 0 } },
];

// ---- voltage ------------------------------------------------------------------------------------------------------
export const V_LO = 0.94, V_HI = 1.06;
export const vY = (v) => +(96 - (Math.max(V_LO, Math.min(V_HI, v)) - V_LO) / (V_HI - V_LO) * 92).toFixed(2);
export function vColor(v) {
  if (v > 1.05) return '#6e1d17';
  if (v < 0.95) return '#b23a2f';
  if (v < 0.96) return '#c7962b';
  return '#8aa58f';
}
/** Stems for one step: x in 0..1000 along busOrder, y in the 0..100 viewBox; isolated buses (0) are flagged. */
export function voltageStems(vRow, busOrder) {
  const n = busOrder.length, out = [];
  for (let j = 0; j < n; j++) {
    const i = busOrder[j], m = vRow[i];
    const x = +(4 + (n > 1 ? j / (n - 1) : 0.5) * 992).toFixed(1);
    if (!m) { out.push({ i, x, iso: true }); continue; }
    const v = m / 1000;
    out.push({ i, x, v, y: vY(v), c: vColor(v) });
  }
  return out;
}
/** The lowest non-isolated bus at one step: {i, v} or null. */
export function lowestBus(vRow) {
  let bi = -1, bv = Infinity;
  for (let i = 0; i < vRow.length; i++) if (vRow[i] > 0 && vRow[i] < bv) { bv = vRow[i]; bi = i; }
  return bi < 0 ? null : { i: bi, v: bv / 1000 };
}
const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
/** Heat-map colour for pu x1000 (0 = isolated). */
export function heatRGB(m) {
  if (!m) return [107, 111, 108];
  const v = m / 1000;
  if (v > 1.05) return [110, 29, 23];
  if (v < 0.95) return [178, 58, 47];
  if (v < 0.96) return [199, 150, 43];
  if (v < 0.975) return mix([199, 150, 43], [138, 165, 143], (v - 0.96) / 0.015);
  const t = Math.max(0, Math.min(1, (1.03 - v) / 0.055));
  return t < 0.5 ? mix([241, 238, 229], [185, 201, 186], t * 2) : mix([185, 201, 186], [110, 140, 116], (t - 0.5) * 2);
}

// ---- time series paths (viewBox 1000 x 100) -----------------------------------------------------------------------
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
/** Reactive power model: kVAr (tenths in the file). null when the fields are not exported. */
export function reactiveModel(ex) {
  if (!ex || !Array.isArray(ex.headKVAr) || !Array.isArray(ex.capKVAr) || !ex.headKVAr.length) return null;
  const head = ex.headKVAr.map((x) => x / 10), cap = ex.capKVAr.map((x) => x / 10);
  let lo = Math.min(0, ...head, ...cap), hi = Math.max(...head, ...cap, 1);
  const pad = (hi - lo) * 0.08; lo = lo < 0 ? lo - pad : 0; hi += pad;
  return { head, cap, lo, hi, headD: pathOf(head, lo, hi), capD: areaOf(cap, lo, hi), zeroY: yOf(0, lo, hi) };
}
export const xPct = (k, n) => `${(n > 1 ? k / (n - 1) * 100 : 0).toFixed(3)}%`;

// ---- failure and covert summaries ----------------------------------------------------------------------------------
/** Rows for the failure card: [{k, x (labelled), opts}] plus plain lines. kind = faults | worker_kill | covert. */
export function failureModel(kind, d = {}) {
  const row = (k, x, opts = {}) => ({ k, x: has(x) ? x : null, opts });
  if (kind === 'faults') {
    const c = d.chaos || null, ev = d.events || [], note = d.summary && d.summary.note;
    return {
      title: 'Pieces fail', sub: 'a silent battery, an EV on one street and a controller stall, scripted on this evening',
      lines: ev.map((e) => `${e.t} · ${e.text}`), note: note && note.text ? note.text : null,
      rows: c ? [
        row(`Seeded runs of this evening with random failures`, c.constants && c.constants.CHAOS_RUNS ? { v: c.constants.CHAOS_RUNS.value, label: c.constants.CHAOS_RUNS.label, cite: c.constants.CHAOS_RUNS.cite } : null),
        row('Runs with a battery-caused violation', c.runsWithBatteryCaused),
        row('Battery-caused normal-rating events, all runs', c.batteryCausedNormal),
        row('20% reserve breaches, all runs', c.reserveBreaches),
        row('Worst charge at 04:00 of the batteries that kept talking', c.minChargedPctResponsive, { digits: 1, unit: '%' }),
      ] : [],
      missing: c ? null : 'p1/chaos.json not loaded',
    };
  }
  if (kind === 'worker_kill') {
    const s = d.summary || {}, rt = d.runtime || {};
    return {
      title: 'Controller crash', sub: rt.kill && rt.kill.text ? `${rt.kill.t} · ${rt.kill.text}` : 'one controller worker is killed mid-evening',
      lines: [...(rt.takeover || []).map((t) => `${t.t} · ${t.text}`), ...(rt.late && rt.late.text ? [`${rt.late.t} · ${rt.late.text}`] : [])],
      note: null,
      rows: [
        row('Takeover after the kill', s.takeoverSeconds, { digits: 0, unit: ' s' }),
        row('Worst fleet tracking error, kill to takeover', s.trackingMaxErrPct, { digits: 1, unit: '%' }),
        row('Same minutes without the kill', s.baselineMaxErrPct, { digits: 1, unit: '%' }),
        row('Energy the kill cost', s.killCostKWh, { digits: 2, unit: ' kWh' }),
        row('Late commands from the dead worker', s.lateCommands),
        row('Refused on a stale epoch', s.rejectedStaleEpoch),
      ],
      missing: s.takeoverSeconds ? null : 'takeover summary not exported',
    };
  }
  if (kind === 'covert') {
    const cv = d.covert || null, s = (cv && cv.summary) || {};
    const flagged = has(s.detected) && has(s.shard) ? { v: `${fmtNum(s.detected.v)} of ${fmtNum(s.shard.v)}`, label: s.detected.label, cite: `${s.detected.cite}; shard ${s.shard.label}: ${s.shard.cite}` } : null;
    return {
      title: 'Hidden attacker', sub: cv && cv.attack ? `${cv.attack.t} · ${cv.attack.text}` : 'a fictional adversary on one lateral',
      lines: [], note: 'Fictional attacker: no real company or person. Found from physics (telemetry vs the home\'s own voltage), not command logs.',
      rows: cv ? [
        row('Compromised units flagged', flagged),
        row('First flag after the channel opens', s.detectionSeconds, { digits: 0, unit: ' s' }),
        row('All flagged after', s.allDetectedSeconds, { digits: 0, unit: ' s' }),
        row('False positives, clean evening', s.falsePositivesClean),
        row('False positives, during the attack', s.falsePositivesAttack),
        row('Quarantined (held at zero)', s.quarantined),
      ] : [],
      missing: cv ? null : 'p3/covert.json not built yet',
    };
  }
  return null;
}

/** ERCOT frequency card model from ui/data/ems/freq-series.json (REAL series; sigma DERIVED). */
export function freqModel(f) {
  if (!f || !f.series_1min || !Array.isArray(f.series_1min.f_mean_hz)) return null;
  const s = f.series_1min.f_mean_hz, lo = 59.96, hi = 60.03;
  const day = /^(\d{4}-\d{2}-\d{2})/.exec(f.series_1min.t0_cdt || '');
  const sig = f.stats && f.stats.frequency ? f.stats.frequency.sigma_mhz : null;
  return {
    day: day ? day[1] : null, lo, hi, d: pathOf(s, lo, hi), y60: yOf(60, lo, hi),
    bandTop: yOf(60 - HIJACK_FREQ_BAND_MHZ.lo / 1000, lo, hi), bandBot: yOf(60 - HIJACK_FREQ_BAND_MHZ.hi / 1000, lo, hi),
    sigma: sig != null ? { v: sig, label: 'DERIVED', cite: 'standard deviation of ERCOT frequency samples that day (ui/data/ems/freq-series.json stats.frequency; REAL samples)' } : null,
    n: s.length,
  };
}

// =================================================================================================================
// DOM
// =================================================================================================================
function numH(ctx, x, opts = {}) {
  if (!has(x)) return missingHTML(x && isLab(x) && x.v == null ? 'n/a' : 'not exported for this run');
  try { return ctx.num(x, opts); } catch (e) { return missingHTML('unlabelled value refused'); }
}

async function tryGet(fn) {
  try { return { doc: await fn(), err: null }; } catch (e) { return { doc: null, err: e }; }
}
const notBuilt = (err, path) => (err && err.status === 404 ? `not built yet: ${path}` : `could not load ${path}`);

export async function mount(root, ctx) {
  const scn = ctx.scenario || {};
  const cat = ctx.catalogue || {};
  const L = scn.levers || {};
  const failure = L.failure || 'none';
  const bk = branchKey(scn.branch);
  root.classList.add('pb-page', 'pb-results');
  root.innerHTML = `<div class="pb-loading">Loading this run's results…</div>`;

  // ---- load: extras, meta (events, fallback summary), failure docs, frequency (covert only) ----
  const [exR, metaR] = await Promise.all([
    scn.extras ? tryGet(() => ctx.getAny(scn.extras)) : Promise.resolve({ doc: null, err: null }),
    scn.meta ? tryGet(() => ctx.getJSON(scn.meta)) : Promise.resolve({ doc: null, err: null }),
  ]);
  const ex = exR.doc, meta = metaR.doc;
  let sm = scn.summary || (meta && meta.summary && meta.summary[bk]) || null;
  let fdata = {}, freq = null, freqErr = null;
  if (failure === 'faults') {
    const c = await tryGet(() => ctx.getJSON('p1/chaos.json'));
    fdata = { chaos: c.doc, events: (meta && meta.events && meta.events[bk]) || [], summary: sm };
  } else if (failure === 'worker_kill') {
    // the branch doc carries runtime (kill, takeover, late batch); its summary fills in when the catalogue's lacks it
    const w = await tryGet(() => ctx.getAny(scn.branch));
    const runtime = w.doc ? w.doc.runtime || null : null;
    if (w.doc && (!sm || !has(sm.takeoverSeconds))) sm = w.doc.summary || sm;
    fdata = { summary: sm, runtime };
  } else if (failure === 'covert') {
    const cpath = scn.covert || 'p3/covert.json';
    const [c, f] = await Promise.all([tryGet(() => ctx.getJSON(cpath)), tryGet(() => ctx.getJSON('ems/freq-series.json'))]);
    fdata = { covert: c.doc, covertErr: c.err ? notBuilt(c.err, cpath) : null };
    freq = f.doc; freqErr = f.err ? notBuilt(f.err, 'ems/freq-series.json') : null;
  }
  const others = siblings(scn, cat).map((s) => ({ id: s.id, name: runName(s, cat), summary: s.summary || null }));

  // ---- derived view state ----
  const n = ex && ex.steps ? ex.steps : (meta && meta.steps) || 720;
  const start = (ex && ex.start) || (meta && meta.start) || '16:00';
  const stepS = (ex && ex.stepSeconds) || (meta && meta.stepSeconds) || 60;
  const hasV = !!(ex && Array.isArray(ex.vTfMilli) && ex.vTfMilli.length && Array.isArray(ex.busOrder));
  const series = (ex && ex.series) || {};
  const sLabel = (k, dflt) => (series[k] && LABELS.includes(series[k].label) ? series[k].label : dflt);
  const rq = reactiveModel(ex);
  const fm = failure !== 'none' ? failureModel(failure, fdata) : null;
  const fq = failure === 'covert' ? freqModel(freq) : null;
  const verdict = verdictOf(sm, L);
  const tiles = tilesModel(sm, others);
  let k0 = Number.isFinite(ctx.k) ? ctx.k : null;
  if (k0 == null && ex && Array.isArray(ex.worstPct)) { let w = 0; ex.worstPct.forEach((v, i) => { if (v > ex.worstPct[w]) w = i; }); k0 = w; }
  let k = Math.max(0, Math.min(n - 1, k0 ?? 0));

  const evening = (cat.levers && cat.levers.evening) ? leverLabel(cat, 'evening', L.evening) : (L.evening || '');
  const fixture = [ex, meta, fdata.chaos, fdata.covert].some((d) => d && d.fixture) || cat.fixture;
  const exMissing = !ex ? (exR.err ? notBuilt(exR.err, scn.extras) : 'not exported for this run') : null;

  // ---- markup ----
  const tileH = tiles.map((t) => `
    <div class="pb-card pb-tile">
      <div class="pb-tile-h"><span class="pb-card-t">${esc(t.title)}</span></div>
      <div class="pb-tile-big">${t.big ? numH(ctx, t.big, t.opts) : missingHTML(t.why ? (L.policy === 'none' && t.key === 'chargedPctBy0400' ? 'no batteries in this run' : 'n/a') : 'not exported for this run')}</div>
      ${t.where ? `<div class="pb-tile-where">${esc(t.where)}</div>` : ''}
      <div class="pb-cmp">${t.cmp.length ? t.cmp.map((c) => `<div class="pb-cmp-row${c.missing ? ' pb-dim' : ''}"><span>${esc(c.name)}</span><span>${esc(c.text)}</span></div>`).join('') : '<div class="pb-cmp-row pb-dim"><span>no other committed run for these levers</span></div>'}</div>
    </div>`).join('');

  const eveningH = EVENING_DEFS.map((d) => {
    const x = sm ? sm[d.key] : null;
    if (d.key === 'energyValueUSD' && L.policy === 'none') return '';
    return `<div class="pb-kv"><span>${esc(d.title)}</span><span>${numH(ctx, x, d.opts)}</span></div>`;
  }).join('');

  const failH = fm ? `
    <div class="pb-card pb-fail">
      <div class="pb-card-h"><span class="pb-card-t">${esc(fm.title)}</span>${failure === 'covert' ? '<span class="pb-sub">Fictional attacker</span>' : ''}</div>
      <div class="pb-sub pb-clip2">${esc(fm.sub)}</div>
      ${fm.lines.length ? `<ul class="pb-lines">${fm.lines.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>` : ''}
      ${fm.rows.map((r) => `<div class="pb-kv"><span>${esc(r.k)}</span><span>${r.x ? numH(ctx, r.x, r.opts) : missingHTML()}</span></div>`).join('')}
      ${fm.missing || fdata.covertErr ? `<div class="pb-kv">${missingHTML(fdata.covertErr || fm.missing)}</div>` : ''}
      ${fm.note ? `<div class="pb-note">${esc(fm.note)}</div>` : ''}
    </div>` : '';

  const freqH = failure === 'covert' ? `
    <div class="pb-card pb-freq">
      <div class="pb-card-h"><span class="pb-card-t">ERCOT frequency</span><span class="pb-sub">${fq && fq.day ? esc(fq.day) : ''} · a different day</span>${fq ? tagHTML('REAL', 'ERCOT dashboards, 1-minute mean of the 10-s samples (ui/data/ems/freq-series.json provenance)') : ''}</div>
      ${fq ? `<div class="pb-plot pb-freq-plot">
        <svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-label="ERCOT frequency, a different day">
          <rect width="1000" height="100" fill="#f6f3ea"/>
          <rect x="930" width="60" y="${fq.bandTop}" height="${(fq.bandBot - fq.bandTop).toFixed(2)}" fill="#e4efe6" stroke="#1e4d2b" stroke-width="1" vector-effect="non-scaling-stroke"/>
          <line x1="0" x2="1000" y1="${fq.y60}" y2="${fq.y60}" stroke="#10231a" stroke-opacity=".25" vector-effect="non-scaling-stroke"/>
          <path d="${fq.d}" fill="none" stroke="#10231a" stroke-width="1" vector-effect="non-scaling-stroke" transform="scale(0.92,1)"/>
        </svg>
        <span class="pb-axis pb-axis-tl">60.03 Hz</span><span class="pb-axis pb-axis-bl">59.96 Hz</span>
      </div>
      <div class="pb-kv"><span>Normal wander that day (σ)</span><span>${numH(ctx, fq.sigma, { digits: 1, unit: ' mHz' })}</span></div>
      <div class="pb-kv"><span>A 1,000-battery hijack moves it by</span><span><span class="num">${HIJACK_FREQ_BAND_MHZ.lo}–${HIJACK_FREQ_BAND_MHZ.hi} mHz</span>${tagHTML(HIJACK_FREQ_BAND_MHZ.label, HIJACK_FREQ_BAND_MHZ.cite)}</span></div>
      <div class="pb-note">Inside normal wander (the green bracket at the right edge, same scale): the grid-wide signal cannot show this attack. The feeder can.</div>`
      : `<div class="pb-kv">${missingHTML(freqErr || 'frequency series not loaded')}</div>`}
    </div>` : '';

  const vLab = sLabel('vTfMilli', 'SIM'), oLab = sLabel('busOrder', 'DERIVED');
  const qLab = sLabel('headKVAr', 'SIM');
  root.innerHTML = `
    ${fixture ? '<div class="pb-fixture">FIXTURE data: contract-shaped stand-ins, not engine output</div>' : ''}
    <div class="pb-row1">
      <div class="pb-card pb-verdict${verdict.ok === false ? ' pb-verdict-bad' : ''}">
        <div class="pb-eyebrow">THIS EVENING · ${esc(String(evening).toUpperCase())} · ${esc(runName(scn, cat).toUpperCase())}</div>
        <div class="pb-verdict-t">${esc(verdict.title)}</div>
        <div class="pb-verdict-s">${sm ? tagHTML('SIM', 'OpenDSS AC power flow, every step (meta.summary)') : ''}<span>${esc(verdict.sub)}</span></div>
      </div>
      ${tileH}
    </div>
    <div class="pb-row2">
      <div class="pb-card pb-vbus">
        <div class="pb-card-h"><span class="pb-card-t">Voltage by bus</span><span class="pb-sub">lowest home per service transformer, pu, at <b data-pb="clock"></b></span><span class="pb-right pb-sub" data-pb="vnow"></span></div>
        <div class="pb-plot" data-pb="vplot">${hasV ? `
          <svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-label="Voltage by bus">
            <rect x="0" y="${vY(1.05)}" width="1000" height="${(vY(0.95) - vY(1.05)).toFixed(2)}" fill="#eef2ea"/>
            <line x1="0" x2="1000" y1="${vY(1.05)}" y2="${vY(1.05)}" stroke="#b23a2f" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>
            <line x1="0" x2="1000" y1="${vY(0.95)}" y2="${vY(0.95)}" stroke="#b23a2f" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>
            <line x1="0" x2="1000" y1="${vY(1)}" y2="${vY(1)}" stroke="#10231a" stroke-opacity=".2" vector-effect="non-scaling-stroke"/>
            <g data-pb="stems"></g>
          </svg>
          <span class="pb-axis pb-red" style="top:calc(${vY(1.05)}% - 14px)">1.05</span><span class="pb-axis pb-red" style="top:calc(${vY(0.95)}% + 1px)">0.95</span><span class="pb-axis" style="top:calc(${vY(1)}% - 14px)">1.00</span>
          <span class="pb-axis pb-axis-bl">← near the substation</span><span class="pb-axis pb-axis-br">far end →</span>` : `<div class="pb-empty">${missingHTML(exMissing || 'voltage by bus not exported for this run')}</div>`}
        </div>
        <div class="pb-foot">${hasV ? `${tagHTML(vLab, 'OpenDSS lowest home voltage per transformer (extras vTfMilli)')}OpenDSS, every transformer · order ${tagHTML(oLab, 'path distance from the substation along the SMART-DS lines (extras busOrder)')} path distance from the substation · band 0.95–1.05` : 'Voltage by bus comes from the engine\'s extras export'}</div>
      </div>
      <div class="pb-card pb-q">
        <div class="pb-card-h"><span class="pb-card-t">Reactive power</span><span class="pb-sub">kVAr at the feeder head</span><span class="pb-right pb-sub" data-pb="qnow"></span></div>
        <div class="pb-plot pb-scrub" data-pb="qplot">${rq ? `
          <svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-label="Reactive power">
            <rect width="1000" height="100" fill="#f6f3ea"/>
            <path d="${rq.capD}" fill="#c9cfc4"/>
            <line x1="0" x2="1000" y1="${rq.zeroY}" y2="${rq.zeroY}" stroke="#1e4d2b" stroke-width="2" vector-effect="non-scaling-stroke"/>
            <path d="${rq.headD}" fill="none" stroke="#10231a" stroke-width="1.5" vector-effect="non-scaling-stroke"/>
          </svg>
          <span class="pb-axis pb-axis-tl">${esc(fmtNum(rq.hi, 0))}</span><span class="pb-axis pb-axis-bl">${esc(fmtNum(rq.lo, 0))}</span>
          <div class="pb-cursor" data-pb="cur"></div>` : `<div class="pb-empty">${missingHTML(exMissing || 'reactive power not exported for this run')}</div>`}
        </div>
        <div class="pb-legend"><span><i class="pb-sw-line"></i>feeder head ${tagHTML(qLab, 'OpenDSS feeder-head Q (extras headKVAr)')}</span><span><i class="pb-sw-area"></i>capacitor bank ${tagHTML(sLabel('capKVAr', 'SIM'), 'OpenDSS capacitor output (extras capKVAr)')}</span><span><i class="pb-sw-brand"></i>our inverters: 0, unity power factor ${tagHTML('ASSUMPTION', 'BATTERY_PF = 1.0: the batteries exchange no reactive power in this run')}</span></div>
      </div>
    </div>
    <div class="pb-row3${fm ? ' pb-has-fail' : ''}${failure === 'covert' ? ' pb-has-freq' : ''}">
      <div class="pb-card pb-heat">
        <div class="pb-card-h"><span class="pb-card-t">Voltage over the evening</span><span class="pb-sub">every transformer (rows, substation at top) × every minute</span>${hasV ? tagHTML(vLab, 'OpenDSS lowest home voltage per transformer (extras vTfMilli)') : ''}</div>
        <div class="pb-plot pb-scrub" data-pb="hplot">${hasV ? `<canvas data-pb="heat" width="${n}" height="${ex.busOrder.length}"></canvas><div class="pb-cursor" data-pb="cur"></div>` : `<div class="pb-empty">${missingHTML(exMissing || 'not exported for this run')}</div>`}</div>
        <div class="pb-legend pb-heat-legend"><span><i style="background:#6e8c74"></i>≥ 1.00</span><span><i style="background:#b9c9ba"></i>0.98</span><span><i style="background:#8aa58f"></i>0.97</span><span><i style="background:#c7962b"></i>0.95–0.96</span><span><i style="background:#b23a2f"></i>&lt; 0.95</span><span><i style="background:#6b6f6c"></i>isolated</span></div>
      </div>
      <div class="pb-card pb-evening">
        <div class="pb-card-h"><span class="pb-card-t">The evening in numbers</span></div>
        ${sm ? eveningH : `<div class="pb-kv">${missingHTML()}</div>`}
        <div class="pb-note">Gross energy value is REAL LZ_NORTH prices × simulated battery kW: not Base's profit.</div>
      </div>
      ${failH}${freqH}
    </div>
    <div class="pb-scrubber pb-scrub" data-pb="scrub">
      <span class="pb-clock" data-pb="clock2"></span>
      <div class="pb-track"><div class="pb-track-bg"></div><div class="pb-knob" data-pb="knob"><i></i></div>
        <div class="pb-ticks">${[0, 120, 240, 360, 480, 600, 719].map((s) => `<span>${clockOf(Math.min(s, n - 1), start, stepS)}</span>`).join('')}</div></div>
      <span class="pb-sub">Drag to read any minute</span>
    </div>`;

  const $ = (sel) => root.querySelector(`[data-pb="${sel}"]`);
  const $$ = (sel) => [...root.querySelectorAll(`[data-pb="${sel}"]`)];

  // ---- heat map (drawn once) ----
  if (hasV) {
    const cv = $('heat'), g = cv.getContext && cv.getContext('2d');
    if (g) {
      const B = ex.busOrder, img = g.createImageData(n, B.length);
      for (let kk = 0; kk < n; kk++) {
        const row = ex.vTfMilli[kk] || [];
        for (let j = 0; j < B.length; j++) { const c = heatRGB(row[B[j]]), o = (j * n + kk) * 4; img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255; }
      }
      g.putImageData(img, 0, 0);
    }
  }

  // ---- cursor-dependent parts ----
  function update(kNew) {
    if (!Number.isFinite(kNew)) return;
    k = Math.max(0, Math.min(n - 1, Math.round(kNew)));
    const clock = clockOf(k, start, stepS);
    for (const el of [$('clock'), $('clock2')]) if (el) el.textContent = clock;
    const left = xPct(k, n);
    for (const el of $$('cur')) el.style.left = left;
    const knob = $('knob'); if (knob) knob.style.left = left;
    if (hasV) {
      const row = ex.vTfMilli[k] || [];
      const st = voltageStems(row, ex.busOrder);
      const y1 = vY(1);
      $('stems').innerHTML = st.map((b) => (b.iso
        ? `<line x1="${b.x}" x2="${b.x}" y1="98" y2="100" stroke="#6b6f6c" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`
        : `<line x1="${b.x}" x2="${b.x}" y1="${y1}" y2="${b.y}" stroke="${b.c}" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`)).join('');
      const lo = lowestBus(row), iso = st.filter((b) => b.iso).length;
      const dist = lo && Array.isArray(ex.busDistKm) ? ex.busDistKm[lo.i] : null;
      $('vnow').innerHTML = lo ? `lowest <b>${fmtNum(lo.v, 3)} pu</b> at T-${lo.i}${dist != null ? ` (${fmtNum(dist, 1)} km out)` : ''}${iso ? ` · ${iso} isolated` : ''} ${tagHTML(vLab, 'extras vTfMilli')}` : 'every bus isolated';
    } else if ($('vnow')) $('vnow').textContent = '';
    if (rq && $('qnow')) $('qnow').innerHTML = `head <b>${fmtNum(rq.head[k], 0)}</b> · capacitor <b>${fmtNum(rq.cap[k], 0)}</b> kVAr ${tagHTML(qLab, 'extras headKVAr / capKVAr')}`;
  }

  // ---- scrubbing: every time-axis element seeks ----
  let drag = null;
  const kFrom = (e, el) => { const r = el.getBoundingClientRect(); return (e.clientX - r.left) / (r.width || 1) * (n - 1); };
  const seek = (kk) => { update(kk); try { ctx.setK && ctx.setK(k); } catch (e) { /* the shell owns the cursor */ } };
  const handlers = [];
  for (const el of root.querySelectorAll('.pb-scrub')) {
    const target = el.querySelector('.pb-track') || el;
    const down = (e) => { drag = target; try { el.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ } seek(kFrom(e, target)); };
    const move = (e) => { if (drag === target) seek(kFrom(e, target)); };
    const up = () => { drag = null; };
    el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    handlers.push([el, down, move, up]);
  }
  const off = typeof ctx.onK === 'function' ? ctx.onK((kk) => { if (kk !== k) update(kk); }) : null;
  update(k);

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
