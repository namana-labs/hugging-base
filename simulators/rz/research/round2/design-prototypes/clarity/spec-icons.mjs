// ui/lib/icons.js (L0): the shared inline-SVG icon set, the transformer "tank", battery icons and the plain state words. PURE.
const SVG = (inner, cls = '', size = 16) => `<svg class="ic ${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
export const PATHS = {
  house: '<path d="M3.5 11 12 4l8.5 7"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5.5h4V20"/>',
  battery: '<rect x="7" y="5" width="10" height="16" rx="2"/><path d="M10 2.8h4"/><path d="M13 8.5 10.5 13h3l-2.5 4.5"/>',
  tf: '<rect x="4" y="7" width="16" height="12" rx="1.5"/><path d="M4 9.5h16"/><path d="M2.5 21.5h19"/><circle cx="10.3" cy="14.2" r="2.5"/><circle cx="13.7" cy="14.2" r="2.5"/>',
  pole: '<path d="M8 2v20"/><path d="M3.5 5h9"/><rect x="10.5" y="8" width="7" height="9" rx="3"/><path d="M10.5 12.5H8"/>',
  price: '<path d="M20.6 13.3 13.3 20.6a1.5 1.5 0 0 1-2.1 0L3.5 12.9V3.5h9.4l7.7 7.7a1.5 1.5 0 0 1 0 2.1z"/><circle cx="8" cy="8" r="1.4"/>',
  priceUp: '<path d="M3.5 12.9V3.5h9.4l3 3"/><circle cx="8" cy="8" r="1.4"/><path d="M18 21v-8M14.8 16.2 18 13l3.2 3.2"/>',
  priceDown: '<path d="M3.5 12.9V3.5h9.4l3 3"/><circle cx="8" cy="8" r="1.4"/><path d="M18 13v8M14.8 17.8 18 21l3.2-3.2"/>',
  money: '<ellipse cx="12" cy="6" rx="7" ry="2.6"/><path d="M5 6v4.5c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6"/><path d="M5 10.5V15c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6v-4.5"/><path d="M5 15v3.5c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V15"/>',
  warning: '<path d="M10.3 4.2 2.6 17.6a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4.5"/><path d="M12 17.3h.01"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.7 2.7 5.5-5.5"/>',
  tripped: '<path d="M12 3.5V11"/><path d="M7 6.4a7.5 7.5 0 1 0 10 0"/>',
  bolt: '<path d="M13 2.5 5.5 13.5H11l-1 8 7.5-11H12z" fill="currentColor" stroke="none"/>',
  out: '<path d="M6 18 18 6"/><path d="M9 6h9v9"/>',
  silent: '<path d="M5.5 12.5a9.5 9.5 0 0 1 13 0"/><path d="M8.8 15.8a4.8 4.8 0 0 1 6.4 0"/><path d="M12 19.3h.01"/><path d="m3 3 18 18"/>',
  plug: '<path d="M9 2.5v5M15 2.5v5"/><path d="M6 7.5h12V11a6 6 0 0 1-12 0z"/><path d="M12 17v4.5"/>',
  controller: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
  freeze: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7M14 8.5v7"/>',
  turns: '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 3.5V8h4.5"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 20.5V16h-4.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  play: '<path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none"/>',
  pause: '<path d="M7.5 5h3v14h-3zM13.5 5h3v14h-3z" fill="currentColor" stroke="none"/>',
  stepBack: '<path d="M6 5v14"/><path d="M18 5.5v13L9 12z" fill="currentColor"/>',
  stepFwd: '<path d="M18 5v14"/><path d="M6 5.5v13L15 12z" fill="currentColor"/>',
  feeder: '<circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 12h10M6.7 10.9 17.3 6M6.7 13.1l10.6 4.9"/>',
  street: '<path d="M2.5 12 7 8l4.5 4"/><path d="M4 11v7h6v-7"/><path d="M12.5 12 17 8l4.5 4"/><path d="M14 11v7h6v-7"/><path d="M2 21h20"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.8h.01"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  numbers: '<path d="M4.5 8.5 6.5 7v10M4.5 17h4"/><path d="M10.5 9a2 2 0 1 1 3.4 1.4L10.5 17h4"/><path d="M16.5 7.5H20l-2 3.5a2.6 2.6 0 1 1-2 4.6"/>',
  gauge: '<path d="M4.5 17a8 8 0 1 1 15 0"/><path d="m12 13.5 4-4.5"/><path d="M12 13.5h.01"/>',
  ruler: '<rect x="2.5" y="8" width="19" height="8" rx="1.5"/><path d="M6.5 8v3M10.5 8v4.5M14.5 8v3M18.5 8v4.5"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
  book: '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H19v15H5.5A1.5 1.5 0 0 0 4 19.5z"/><path d="M4 19.5A1.5 1.5 0 0 0 5.5 21H19"/>',
  arrow: '<path d="M4 12h15M13 6l6 6-6 6"/>',
};
export const icon = (name, { size = 16, cls = '' } = {}) => SVG(PATHS[name] || '', `ic-${name} ${cls}`, size);

/** Plain words for tier codes 0..5 (display only; the codes come from the JSON). TIER_TIPS carry the exact rule. */
export const TIER_WORDS = ['OK', 'Over', 'Overloaded', 'Overloaded 30+ min', 'Emergency', 'Lights out'];
export const TIER_GLYPH = ['check', 'warning', 'warning', 'warning', 'warning', 'tripped'];
export const TIER_TIPS = [
  'Within its rating: at or under 100% of nameplate.',
  'Over nameplate (100–110%). Short spells are normal for transformers; not a violation.',
  'Above 110%, its normal rating. If it lasts 30 minutes it becomes a violation; the clock is running.',
  'Above 110% for 30 minutes or more: a normal-rating violation (it ages the transformer).',
  'Above 150%: past its emergency rating. Real transformers survive this only briefly.',
  'Its fuse opened under our rule (above 200% for 10 min, or 300% for 60 s; ASSUMPTION). Homes without a battery go dark; homes with one run on it.',
];
export const STATE_WORDS = { C: 'charging', D: 'sending power out', I: 'waiting', S: 'silent (no signal)', X: 'stopped safely', B: 'powering its own home', N: 'new (P2)' };

/** A battery icon: fill = state of charge (0..1), colour = state (C D I S X B N). 20 x 26 viewBox: body left, state badge top right. */
export function batteryIcon(soc, state = 'I', { w = 16, h = 21 } = {}) {
  const s = Math.max(0, Math.min(1, Number(soc) || 0));
  const top = (5.2 + 17.3 * (1 - s)).toFixed(2), fh = (17.3 * s).toFixed(2);
  const badge = { C: '<path class="bb" d="M17.2 1.2 14.4 5.4h2.2l-.8 3.6 3-4.5H16.5z"/>',
                  D: '<path class="bb bb-s" d="M14.6 8.2 19.4 3.4M16 3.2h3.6v3.6"/>',
                  S: '<circle class="bb" cx="17" cy="4.5" r="3.4"/><path class="bb-w" d="M17 2.8v2.2M17 6.4h.01"/>',
                  X: '<circle class="bb" cx="17" cy="4.5" r="3.4"/><path class="bb-w" d="M15.6 4.5h2.8"/>' }[state] || '';
  return `<svg class="ic-bat s-${state}" width="${w}" height="${h}" viewBox="0 0 20 26" aria-hidden="true">`
    + '<rect class="bat-nub" x="4.5" y="1" width="5" height="2.4" rx="1"/><rect class="bat-body" x="1" y="3.2" width="12" height="21.3" rx="2.4"/>'
    + `<rect class="bat-fill" x="3" y="${top}" width="8" height="${fh}" rx="1"/><path class="bat-res" d="M2.4 19h9.2"/>${badge}</svg>`;
}

/** The transformer "tank" (display scale only; the % is OpenDSS's): the box is 0-100% of nameplate; the column above it is
 *  100-200% (compressed); homes fill grey, charging batteries teal; relief = hatched ghost of what it would be without the
 *  batteries; back-feed = orange with an out-arrow. fuse = {run, of} minutes above the fuse %, drawn as a ring. */
export function tankSVG({ pct, homeKW = null, batKW = null, code = 0, exporting = false, without = null, fuse = null, w = 46, h = 75 }) {
  const P = Math.max(0, Number(pct) || 0);
  const box = (p) => 32 * Math.min(100, Math.max(0, p)) / 100;          // inner box: y 55 -> 23
  const col = (p) => 28 * Math.min(100, Math.max(0, p - 100)) / 100;    // overflow column: y 20 -> -8 is 100 -> 200%
  const hk = Math.max(0, homeKW ?? 0), bk = batKW ?? 0;
  const batShare = !exporting && bk > 0 && hk + bk > 0 ? bk / (hk + bk) : 0;
  const r = [];
  const f = box(P), fb = f * batShare;
  r.push(`<rect class="${exporting ? 'tk-exp' : 'tk-home'}" x="9" y="${(55 - f).toFixed(2)}" width="30" height="${(f - fb).toFixed(2)}"/>`);
  if (fb > 0) r.push(`<rect class="tk-bat" x="9" y="${(55 - f).toFixed(2)}" width="30" height="${fb.toFixed(2)}"/>`);
  if (without !== null && without > P) {
    const g0 = box(P), g1 = box(without);
    if (g1 > g0) r.push(`<rect class="tk-relief" x="9" y="${(55 - g1).toFixed(2)}" width="30" height="${(g1 - g0).toFixed(2)}"/>`);
    if (without > 100) r.push(`<rect class="tk-relief" x="14" y="${(20 - col(without)).toFixed(2)}" width="20" height="${(col(without) - col(Math.max(P, 100))).toFixed(2)}"/>`);
  }
  const o = col(P);
  if (o > 0) r.push(`<rect class="tk-over" x="14" y="${(20 - o).toFixed(2)}" width="20" height="${o.toFixed(2)}"/>`);
  if (P > 200) r.push('<path class="tk-over" d="M13 -9 24 -14 35 -9z"/>');
  if (exporting) r.push('<path class="tk-arrow" d="M18 44 30 32M23 32h7v7"/>');
  if (fuse && fuse.run > 0) {
    const c = 2 * Math.PI * 5, d = (c * Math.min(1, fuse.run / fuse.of)).toFixed(2);
    r.push(`<circle class="tk-fuse-bg" cx="42" cy="6" r="5"/><circle class="tk-fuse" cx="42" cy="6" r="5" stroke-dasharray="${d} ${c.toFixed(2)}" transform="rotate(-90 42 6)"/>`);
  }
  return `<svg class="tank t${code}${exporting ? ' exporting' : ''}" width="${w}" height="${h}" viewBox="0 -15 48 78" aria-hidden="true">`
    + '<rect class="tk-pad" x="3" y="58.5" width="42" height="4" rx="1"/><rect class="tk-col" x="14" y="-8" width="20" height="28"/>'
    + '<path class="tk-tick" d="M11 17.2h26"/><path class="tk-tick tk-t150" d="M11 6h26"/>'
    + '<rect class="tk-box" x="6" y="20" width="36" height="38.5" rx="3"/>' + r.join('')
    + '<g class="tk-coil"><circle cx="21" cy="40" r="5"/><circle cx="27" cy="40" r="5"/></g></svg>';
}
/** A 10 x 13 mini tank for the trouble row. */
export const tankMini = (code) => `<svg class="tank-mini t${code}" width="10" height="13" viewBox="0 0 10 13" aria-hidden="true"><rect x="1" y="3" width="8" height="8.5" rx="1.2"/><path d="M0 12.5h10"/></svg>`;
