// ui/lib/format.js (L0): every number shown carries an honesty label (build prompt 3.4).
// fmt()/fmtHTML() THROW on a bare number or an unknown label; the shell counts the throw in data-errors.
// Quantized JSON (docs/contracts.md): loading = int tenths of a percent, kW = int tenths, SoC = int per mille,
// times = local "HH:MM" plus a step index.

export const LABELS = ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION'];

export class LabelError extends Error {
  constructor(msg) { super(msg); this.name = 'LabelError'; }
}

export function isLabelled(x) {
  return x !== null && typeof x === 'object' && !Array.isArray(x) && 'v' in x && LABELS.includes(x.label);
}

export function assertLabelled(x, what = 'number') {
  if (!isLabelled(x)) {
    throw new LabelError(`unlabelled ${what}: ${JSON.stringify(x)} (want {"v": n, "label": "REAL|SIM|DERIVED|ASSUMPTION"})`);
  }
  return x;
}

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** The value of a labelled number as text. opts: {digits, unit, pct10, kw10, signed} */
export function fmtValue(x, opts = {}) {
  assertLabelled(x, opts.what);
  let v = x.v;
  if (v === null || v === undefined) return 'n/a';
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (typeof v === 'string') return v;
  if (opts.pct10) v = v / 10;
  if (opts.kw10) v = v / 10;
  const d = opts.digits ?? (Number.isInteger(v) ? 0 : 1);
  let s = Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  if (opts.signed && v > 0) s = '+' + s;
  if (opts.money) s = (v < 0 ? '-$' : '$') + s.replace('-', '');
  return s + (opts.unit ?? '');
}

/** Plain text: "197.0% SIM". Throws on a bare number. */
export function fmt(x, opts = {}) {
  return `${fmtValue(x, opts)} ${x.label}`;
}

/** The chip for a label, as HTML. The cite becomes the chip's title. */
export function chip(label, cite) {
  if (!LABELS.includes(label)) throw new LabelError(`unknown label ${label}`);
  return `<span class="chip chip-${label}"${cite ? ` title="${esc(cite)}"` : ''}>${label}</span>`;
}

/** HTML: value + chip. Throws on a bare number. */
export function fmtHTML(x, opts = {}) {
  const val = fmtValue(x, opts);
  return `<span class="num">${esc(val)}</span>${chip(x.label, x.cite)}`;
}

// ---- quantized bulk values (their label comes from the file's `series`) ----
export const pct10 = (n) => `${(n / 10).toFixed(1)}%`;
export const kw10 = (n) => `${(n / 10).toFixed(1)} kW`;
export const socPm = (n) => `${Math.round(n / 10)}%`;

// ---- time helpers: steps <-> local "HH:MM" --------------------------------------------------
export function hhmmToMin(s) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(s || ''));
  if (!m) return null;
  const h = +m[1], mi = +m[2];
  if (h > 23 || mi > 59) return null;
  return h * 60 + mi;
}

export function minToHHMM(min) {
  const m = ((Math.round(min) % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}

/** Step index for "HH:MM" in a window {start:"HH:MM", stepSeconds, steps}; a time before `start`
 *  counts as the next day (the P1 window runs past midnight). Clamped to [0, steps-1]; null if unparsable. */
export function timeToStep(meta, hhmm) {
  const t = hhmmToMin(hhmm), s = hhmmToMin(meta.start);
  if (t === null || s === null) return null;
  const rel = ((t - s) + 1440) % 1440;
  const k = Math.round(rel * 60 / (meta.stepSeconds || 60));
  return Math.max(0, Math.min((meta.steps || 1) - 1, k));
}

export function stepToTime(meta, k) {
  return minToHHMM(hhmmToMin(meta.start) + k * (meta.stepSeconds || 60) / 60);
}

// ---- calendar dates (round 2: &date=, the day chip and the clock). The weekday is COMPUTED, never typed. -------------
const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function parseISODate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
  if (!m) return null;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3] ? d : null;
}
/** "2026-08-23" -> "Sun 23 Aug 2026" (opts.weekday=false drops the weekday, opts.year=false the year); null if invalid. */
export function dateLabel(iso, opts = {}) {
  const d = parseISODate(iso);
  if (!d) return null;
  const parts = [];
  if (opts.weekday !== false) parts.push(DOW[d.getUTCDay()]);
  parts.push(String(d.getUTCDate()), MON[d.getUTCMonth()]);
  if (opts.year !== false) parts.push(String(d.getUTCFullYear()));
  return parts.join(' ');
}
/** "2026-08-23" + 1 -> "2026-08-24" (the clock after midnight shows the next day's date). */
export function addDays(iso, n) {
  const d = parseISODate(iso);
  if (!d) return null;
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
/** The calendar date of step k in a window that starts on meta.day at meta.start (it crosses midnight). */
export function dateAtStep(meta, k) {
  const s = hhmmToMin(meta.start);
  if (s === null || !meta.day) return null;
  return addDays(meta.day, Math.floor((s + k * (meta.stepSeconds || 60) / 60) / 1440));
}
