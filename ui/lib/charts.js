// ui/lib/charts.js (L5): small, dependency-free SVG charts for the P2 view, the More tab and the P1 panel.
//
// Two layers:
//   *SVG(opts) -> string   PURE (no DOM): node-tested in ui/test/charts.test.js.
//   priceStrip(el, opts), heatStrip(el, opts), lineChart(el, opts), barChart(el, opts), cliffStrip(el, opts)
//                          write the SVG plus its caption into `el` and return `el` (null when el is null).
//
// Honesty (build prompt 3.4): every chart carries exactly one label chip for its values (REAL|SIM|DERIVED|ASSUMPTION),
// passed as opts.label; a chart without a valid label THROWS (like format.js on a bare number). Axis ticks and
// reference lines are read against that label. Colours come from CSS classes in ui/css/p2.css (Atlas tokens), so
// light and dark themes both work.

export const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];

export class ChartLabelError extends Error {
  constructor(msg) { super(msg); this.name = 'ChartLabelError'; }
}

export function requireLabel(label, what = 'chart') {
  if (!LABELS.includes(label)) throw new ChartLabelError(`${what}: needs a label REAL|SIM|DERIVED|ASSUMPTION, got ${JSON.stringify(label)}`);
  return label;
}

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const r1 = (x) => Math.round(x * 10) / 10;
const finite = (a) => a.filter((x) => typeof x === 'number' && Number.isFinite(x));

/** Loading band of a value in percent (display only; tiers themselves come from sim/tiers.py). */
export function band(pct) {
  if (!(typeof pct === 'number' && Number.isFinite(pct))) return 'na';
  if (pct > 150) return 'b4';
  if (pct > 110) return 'b2';
  if (pct > 100) return 'b1';
  return 'b0';
}

function frame(w, h, body, cls, title) {
  return `<svg class="hb-chart ${cls}" viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="none" role="img" aria-label="${esc(title || cls)}" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
}

function chipHTML(label, cite) {
  requireLabel(label);
  return `<span class="chip chip-${label}"${cite ? ` title="${esc(cite)}"` : ''}>${label}</span>`;
}

/** Caption line under/over a chart: text + the chart's label chip. */
export function captionHTML(text, label, cite) {
  return `<div class="hb-chart-cap">${esc(text)}${chipHTML(label, cite)}</div>`;
}

// ---------------------------------------------------------------------------------------------------------------
// Heat strip: days x hours grid (31 x 24 for a month of hourly max loading). values in pct TENTHS (the contract's
// quantization) unless opts.tenths === false. Cells coloured by loading band; <= 100% shaded by level.
export function heatStripSVG({ values, days = 31, hours = 24, label, tenths = true, title = 'heat strip', cell = 9, gap = 1 }) {
  requireLabel(label, 'heatStrip');
  if (!Array.isArray(values)) throw new TypeError('heatStrip: values[] required');
  const w = hours * cell, h = days * cell;
  let body = '';
  for (let d = 0; d < days; d++) {
    for (let k = 0; k < hours; k++) {
      const raw = values[d * hours + k];
      const pct = typeof raw === 'number' ? (tenths ? raw / 10 : raw) : NaN;
      const b = band(pct);
      const op = b === 'b0' ? Math.max(0.08, Math.min(0.85, pct / 100 * 0.85)).toFixed(2) : '1';
      body += `<rect class="hs-${b}" x="${k * cell}" y="${d * cell}" width="${cell - gap}" height="${cell - gap}" fill-opacity="${op}"><title>day ${d + 1} ${String(k).padStart(2, '0')}:00 ${Number.isFinite(pct) ? r1(pct) + '%' : 'n/a'}</title></rect>`;
    }
  }
  return frame(w, h, body, 'hb-heat', title);
}

// ---------------------------------------------------------------------------------------------------------------
// Line chart: series [{name, values[], cls}] on a shared x index; refs [{y, text, cls}] horizontal lines;
// xTicks [{i, text}]. Missing values break the line.
export function lineChartSVG({ series, label, refs = [], xTicks = [], yMin = null, yMax = null, width = 400, height = 150, title = 'line chart', unit = '' }) {
  requireLabel(label, 'lineChart');
  if (!Array.isArray(series) || !series.length) throw new TypeError('lineChart: series[] required');
  const n = Math.max(...series.map((s) => s.values.length));
  const all = finite(series.flatMap((s) => s.values)).concat(refs.map((r) => r.y));
  let lo = yMin ?? Math.min(0, ...all), hi = yMax ?? Math.max(...all, lo + 1);
  if (hi <= lo) hi = lo + 1;
  const padL = 34, padR = 6, padT = 8, padB = 18;
  const X = (i) => padL + (n <= 1 ? 0 : (i / (n - 1)) * (width - padL - padR));
  const Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (height - padT - padB);
  let body = `<rect class="lc-bg" x="${padL}" y="${padT}" width="${width - padL - padR}" height="${height - padT - padB}"/>`;
  for (const t of [lo, (lo + hi) / 2, hi]) {
    body += `<text class="lc-tick" x="${padL - 4}" y="${r1(Y(t) + 3)}" text-anchor="end">${esc(Math.round(t))}${esc(unit)}</text>`;
  }
  for (const r of refs) {
    if (r.y < lo || r.y > hi) continue;
    body += `<line class="lc-ref ${esc(r.cls || '')}" x1="${padL}" x2="${width - padR}" y1="${r1(Y(r.y))}" y2="${r1(Y(r.y))}"/>`;
    if (r.text) body += `<text class="lc-reftext ${esc(r.cls || '')}" x="${width - padR - 2}" y="${r1(Y(r.y) - 2)}" text-anchor="end">${esc(r.text)}</text>`;
  }
  for (const t of xTicks) body += `<text class="lc-tick" x="${r1(X(t.i))}" y="${height - 4}" text-anchor="middle">${esc(t.text)}</text>`;
  for (const s of series) {
    let d = '', pen = false;
    s.values.forEach((v, i) => {
      if (typeof v !== 'number' || !Number.isFinite(v)) { pen = false; return; }
      d += `${pen ? 'L' : 'M'}${r1(X(i))},${r1(Y(v))}`;
      pen = true;
    });
    body += `<path class="lc-line ${esc(s.cls || '')}" d="${d}"><title>${esc(s.name || '')}</title></path>`;
  }
  return frame(width, height, body, 'hb-line', title);
}

// ---------------------------------------------------------------------------------------------------------------
// Bar chart: categories[] x series [{name, values[], cls}] (grouped bars). xLabelEvery thins category labels.
export function barChartSVG({ categories, series, label, width = 400, height = 130, title = 'bar chart', xLabelEvery = 1, yMax = null }) {
  requireLabel(label, 'barChart');
  if (!Array.isArray(categories) || !Array.isArray(series) || !series.length) throw new TypeError('barChart: categories[] and series[] required');
  const hi = yMax ?? Math.max(1, ...finite(series.flatMap((s) => s.values)));
  const padL = 26, padR = 4, padT = 6, padB = 16;
  const cw = (width - padL - padR) / Math.max(1, categories.length);
  const bw = Math.max(1, (cw - 2) / series.length);
  const Y = (v) => padT + (1 - v / hi) * (height - padT - padB);
  let body = `<line class="bc-axis" x1="${padL}" x2="${width - padR}" y1="${height - padB}" y2="${height - padB}"/>`;
  body += `<text class="lc-tick" x="${padL - 3}" y="${padT + 7}" text-anchor="end">${esc(Math.round(hi))}</text>`;
  body += `<text class="lc-tick" x="${padL - 3}" y="${height - padB}" text-anchor="end">0</text>`;
  categories.forEach((c, i) => {
    series.forEach((s, j) => {
      const v = s.values[i];
      if (typeof v !== 'number' || !Number.isFinite(v) || v <= 0) return;
      const y = Y(v);
      body += `<rect class="bc-bar ${esc(s.cls || '')}" x="${r1(padL + i * cw + 1 + j * bw)}" y="${r1(y)}" width="${r1(bw)}" height="${r1(height - padB - y)}"><title>${esc(s.name || '')} ${esc(c)}: ${esc(v)}</title></rect>`;
    });
    if (i % xLabelEvery === 0) body += `<text class="lc-tick" x="${r1(padL + (i + 0.5) * cw)}" y="${height - 4}" text-anchor="middle">${esc(c)}</text>`;
  });
  return frame(width, height, body, 'hb-bar', title);
}

// ---------------------------------------------------------------------------------------------------------------
// Price strip: price[] ($/MWh) as a filled area; markers [{i, text}] as vertical ticks; highlight [{i0, i1, cls}].
export function priceStripSVG({ price, label = 'REAL', markers = [], highlight = [], width = 400, height = 70, title = 'price strip' }) {
  requireLabel(label, 'priceStrip');
  if (!Array.isArray(price) || !price.length) throw new TypeError('priceStrip: price[] required');
  const vals = finite(price);
  const lo = Math.min(0, ...vals), hi = Math.max(1, ...vals);
  const padT = 4, padB = 4;
  const X = (i) => (price.length <= 1 ? 0 : (i / (price.length - 1)) * width);
  const Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (height - padT - padB);
  let body = '';
  for (const h of highlight) body += `<rect class="ps-hl ${esc(h.cls || '')}" x="${r1(X(h.i0))}" y="0" width="${r1(Math.max(1, X(h.i1) - X(h.i0)))}" height="${height}"/>`;
  let d = `M0,${r1(Y(0))}`;
  price.forEach((v, i) => { d += `L${r1(X(i))},${r1(Y(Number.isFinite(v) ? v : 0))}`; });
  d += `L${width},${r1(Y(0))}Z`;
  body += `<path class="ps-area" d="${d}"/>`;
  for (const m of markers) {
    body += `<line class="ps-mark" x1="${r1(X(m.i))}" x2="${r1(X(m.i))}" y1="0" y2="${height}"><title>${esc(m.text || '')}</title></line>`;
  }
  body += `<text class="lc-tick" x="2" y="11">max ${esc(Math.round(hi))} $/MWh</text>`;
  return frame(width, height, body, 'hb-price', title);
}

// ---------------------------------------------------------------------------------------------------------------
// Cliff strip: price-cliff events on a time axis. events [{t:"YYYY-MM-DDTHH:MM", prev, next, drop, evening}],
// period "YYYY-MM-DD..YYYY-MM-DD". Tick height = the fractional drop; evening events use the accent class.
export function parseISOmin(t) {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(String(t || ''));
  if (!m) return null;
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)) / 60000;
}

export function cliffStripSVG({ events, period, label = 'DERIVED', width = 400, height = 56, title = 'price cliffs' }) {
  requireLabel(label, 'cliffStrip');
  if (!Array.isArray(events)) throw new TypeError('cliffStrip: events[] required');
  const [a, b] = String(period || '').split('..');
  let t0 = parseISOmin(a), t1 = parseISOmin(b);
  const ts = events.map((e) => parseISOmin(e.t)).filter((x) => x !== null);
  if (t0 === null) t0 = Math.min(...ts);
  if (t1 === null) t1 = Math.max(...ts);
  if (!(t1 > t0)) t1 = t0 + 1;
  const padT = 4, padB = 14;
  const X = (m) => ((m - t0) / (t1 - t0)) * (width - 2) + 1;
  let body = `<line class="bc-axis" x1="0" x2="${width}" y1="${height - padB}" y2="${height - padB}"/>`;
  // month ticks
  const d0 = new Date(t0 * 60000), d1 = new Date(t1 * 60000);
  for (let y = d0.getUTCFullYear(), mo = d0.getUTCMonth(); Date.UTC(y, mo, 1) <= d1.getTime(); mo === 11 ? (y++, mo = 0) : mo++) {
    const m = Date.UTC(y, mo, 1) / 60000;
    if (m < t0) continue;
    body += `<text class="lc-tick" x="${r1(X(m))}" y="${height - 3}">${['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'][mo]}</text>`;
  }
  for (const e of events) {
    const m = parseISOmin(e.t);
    if (m === null) continue;
    const frac = typeof e.drop === 'number' ? Math.max(0.15, Math.min(1, e.drop)) : 0.5;
    const y = padT + (1 - frac) * (height - padT - padB);
    body += `<line class="cs-tick ${e.evening ? 'cs-evening' : ''}" x1="${r1(X(m))}" x2="${r1(X(m))}" y1="${r1(y)}" y2="${height - padB}"><title>${esc(e.t)}: $${esc(e.prev)} to $${esc(e.next)}${e.evening ? ' (evening)' : ''}</title></line>`;
  }
  return frame(width, height, body, 'hb-cliffs', title);
}

// ---------------------------------------------------------------------------------------------------------------
// DOM wrappers (keep L0's export names). Each writes the SVG and a caption with the label chip.
function mount(el, draw, opts) {
  if (!el) return null;
  const svg = draw(opts);
  const cap = opts.caption ? captionHTML(opts.caption, opts.label, opts.cite) : '';
  el.innerHTML = (opts.captionTop ? cap : '') + svg + (opts.captionTop ? '' : cap);
  return el;
}
export const priceStrip = (el, opts) => mount(el, priceStripSVG, opts);
export const heatStrip = (el, opts) => mount(el, heatStripSVG, opts);
export const lineChart = (el, opts) => mount(el, lineChartSVG, opts);
export const barChart = (el, opts) => mount(el, barChartSVG, opts);
export const cliffStrip = (el, opts) => mount(el, cliffStripSVG, opts);

/** HTML string (SVG + caption) for panels that build markup as strings. kind: price|heat|line|bar|cliff */
export function chartHTML(kind, opts) {
  const f = { price: priceStripSVG, heat: heatStripSVG, line: lineChartSVG, bar: barChartSVG, cliff: cliffStripSVG }[kind];
  if (!f) throw new TypeError(`chartHTML: unknown kind ${kind}`);
  const svg = f(opts);
  const cap = opts.caption ? captionHTML(opts.caption, opts.label, opts.cite) : '';
  return `<figure class="hb-fig">${opts.captionTop ? cap : ''}${svg}${opts.captionTop ? '' : cap}</figure>`;
}

/** The mode (argmax, first on ties) of a histogram like insight.tfPeakHour[24]; null when all zero. */
export function modeIndex(hist) {
  if (!Array.isArray(hist) || !hist.length) return null;
  let best = -1, bi = null;
  hist.forEach((v, i) => { if (typeof v === 'number' && v > best && v > 0) { best = v; bi = i; } });
  return bi;
}
