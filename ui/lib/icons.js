// ui/lib/icons.js: ONE icon set, three renderers (UX_SPEC_R2 2.3). Added by l0 (a stub in scripts/lanes.json), then owned
// by l4-scene-p1; l5 imports it. Lifted from $OVN/proto-r2-scene/icons.js with the round-2 colours (2.1) and grafts.
//   svg(name, opts)                        -> inline SVG string for the DOM (currentColor, 24x24 grid)
//   drawIcon(ctx, name, x, y, size, opts)  -> the same paths on a 2D canvas (fallback2d.js and the atlas)
//   buildAtlas()                           -> {canvas, mapping} for a deck.gl IconLayer (drawn at start-up; no data: URLs)
// PURE: strings and canvas drawing only. Nothing touches the DOM at import, so node tests can import it.
// Procedural icons: battery (fill = state of charge, colour + glyph = state) and meter (the one "load" picture:
// the box is 0-100% of nameplate, the lid is the limit, load above 100% rises out of the box at the same scale).
// Colour means one thing each (2.1): tiers for transformers only, state colours for batteries only.
// "Green never means safe": tier 0 is sage, not bright green.

export const TIER_RGB = [[138, 165, 143], [250, 178, 25], [236, 131, 90], [224, 96, 58], [208, 59, 59], [107, 111, 108]];
// C charging (teal, "ours") · D sending power out (violet, never a tier colour) · I waiting · S silent · X stopped safely
// · B powering its own home · N new (P2 placement)
export const STATE_RGB = { C: [11, 107, 111], D: [123, 92, 214], I: [125, 139, 153], S: [143, 143, 143], X: [143, 143, 143],
  B: [214, 154, 0], N: [11, 107, 111] };
export const HOME_RGB = [140, 148, 143];   // the homes' share of a transformer's load (panel meter split)

// 24x24 stroke paths (round caps and joins, stroke 1.8). "f:" prefix = a filled path.
export const PATHS = {
  house: ['M3 11.5L12 4l9 7.5', 'M5.5 10v10h13V10', 'M10.5 20v-5h3v5'],
  padmount: ['M4 8.5h16v10.5H4z', 'M2.5 19.5h19', 'M4 11h16', 'M9.5 15.2a1.9 1.9 0 1 0 0.01 0', 'M14.5 15.2a1.9 1.9 0 1 0 0.01 0'],
  polemount: ['M10 2.5v19', 'M5 5.5h10', 'M5 5.5v1.5M15 5.5v1.5', 'M11 9h4.5a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H11z', 'M7.5 21.5h5'],
  cabinet: ['M7 3.5h10a1 1 0 0 1 1 1v15.5H6V4.5a1 1 0 0 1 1-1z', 'M4.5 20h15', 'M9 7h6', 'f:M9.5 10h5v7h-5z'],
  bolt: ['f:M13 2.5L5.5 13.5h5.5l-1 8 7.5-11h-5.5z'],
  out: ['M4 12h13', 'M12.5 7l5 5-5 5'],
  wait: ['M7 3.5h10M7 20.5h10', 'M8 3.5c0 5 8 5 8 8.5s-8 3.5-8 8.5', 'M16 3.5c0 5-8 5-8 8.5s8 3.5 8 8.5'],
  silent: ['M4 9.5a11.5 11.5 0 0 1 16 0', 'M7 13a7 7 0 0 1 10 0', 'M10 16.5a3 3 0 0 1 4 0', 'M3.5 3.5l17 17'],
  warn: ['M12 3.5l9.5 16.5h-19z', 'M12 9.8v4.6', 'M12 17.2v.3'],
  fuse: ['M2.5 14h5.5', 'M16 14h5.5', 'M8.4 13.6l6.2-5.2', 'f:M8 14a1.6 1.6 0 1 0 0.01 0', 'f:M16 14a1.6 1.6 0 1 0 0.01 0'],
  hot: ['M12 21c-3.9 0-6-2.6-6-5.9 0-3.5 2.9-5 2.9-9.1 2.1 1 5.1 3.5 5.1 6.2 1-1 1.4-2 1.4-3.1 2 1.8 2.6 4 2.6 6 0 3.3-2.1 5.9-6 5.9z'],
  stall: ['M12 3.5a8.5 8.5 0 1 0 0.01 0', 'M10 9v6M14 9v6'],
  price: ['M3 12.2V4.5A1.5 1.5 0 0 1 4.5 3h7.7l8.8 8.8-9.2 9.2z', 'f:M7.6 7.6a1.3 1.3 0 1 0 0.01 0'],
  priceDown: ['M3 12.2V4.5A1.5 1.5 0 0 1 4.5 3h7.7l8.8 8.8-9.2 9.2z', 'f:M7.6 7.6a1.3 1.3 0 1 0 0.01 0', 'M13.5 9.5v6.5M11 13.8l2.5 2.5 2.5-2.5'],
  priceUp: ['M3 12.2V4.5A1.5 1.5 0 0 1 4.5 3h7.7l8.8 8.8-9.2 9.2z', 'f:M7.6 7.6a1.3 1.3 0 1 0 0.01 0', 'M13.5 16V9.5M11 11.7l2.5-2.5 2.5 2.5'],
  money: ['M2.5 6.5h19v11h-19z', 'M12 9.4a2.6 2.6 0 1 0 0.01 0', 'M5.5 9.5v5M18.5 9.5v5'],
  ok: ['M12 3.5a8.5 8.5 0 1 0 0.01 0', 'M8 12.3l2.7 2.7L16.2 9.5'],
  // grafts from UX-R2-story section 5 (the story chain) and UX-R2-clarity 4.4 (transport, sections, day picker)
  check: ['M12 3.5a8.5 8.5 0 1 0 0.01 0', 'M8 12.3l2.7 2.7L16.2 9.5'],
  turns: ['M20 11a8 8 0 0 0-14.3-4.9L4 8', 'M4 3.5V8h4.5', 'M4 13a8 8 0 0 0 14.3 4.9L20 16', 'M20 20.5V16h-4.5'],
  calendar: ['M5.5 5h13a2 2 0 0 1 2 2v11.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z', 'M3.5 10h17', 'M8 3v4M16 3v4'],
  info: ['M12 3a9 9 0 1 0 0.01 0', 'M12 11v5.5', 'M12 7.8v.01'],
  chevron: ['M9 6l6 6-6 6'],
  play: ['f:M7 4.5v15l12-7.5z'],
  pause: ['f:M7.5 5h3v14h-3z', 'f:M13.5 5h3v14h-3z'],   // transport; the story's "controller stalls" glyph is `stall`
  stepBack: ['M6 5v14', 'f:M18 5.5v13L9 12z'],
  stepFwd: ['M18 5v14', 'f:M6 5.5v13L15 12z'],
  clock: ['M12 3a9 9 0 1 0 0.01 0', 'M12 7v5l3.5 2'],
  list: ['M9 6h11M9 12h11M9 18h11', 'M4.5 6v.01M4.5 12v.01M4.5 18v.01'],
  cable: ['M2.5 16c3 0 3-8 6-8s3 8 6 8 3-8 6-8', 'M2.5 20h19'],
};
// Story names (UX-R2-story section 5) that map onto the prototype's glyphs.
export const ALIASES = { nosignal: 'silent', ev: 'hot', coin: 'money', warning: 'warn', tripped: 'fuse', tf: 'padmount', pole: 'polemount' };
export const pathsFor = (name) => PATHS[name] || PATHS[ALIASES[name]] || null;

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
const clamp01 = (x) => Math.max(0, Math.min(1, Number(x) || 0));

/** Inline SVG for the DOM. opts: {size=18, title, cls}; battery takes {level, state}; meter takes {pct, tier} plus the
 *  panel-only {homeKW, batKW} (split fill: grey homes, teal batteries) and {exporting} (violet fill + out-arrow). */
export function svg(name, opts = {}) {
  const size = opts.size || 18;
  const t = opts.title ? `<title>${esc(opts.title)}</title>` : '';
  if (name === 'battery') return batterySVG(opts.level ?? 0, opts.state || 'I', size, t, opts.cls);
  if (name === 'meter') return meterSVG(opts, size, t);
  const body = (pathsFor(name) || []).map((d) => (d.startsWith('f:') ? `<path d="${d.slice(2)}" fill="currentColor" stroke="none"/>` : `<path d="${d}"/>`)).join('');
  return `<svg class="ic ic-${name} ${opts.cls || ''}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="${t ? 'false' : 'true'}" role="img">${t}${body}</svg>`;
}

// Battery: horizontal, body 2..19.5 x 7..17, nub 20..22; fill = level (0..1) in the state colour, in deciles when the
// caller rounds (batteryId); dashed tick at the 20% member reserve (x 6.3 = 3.3 + 0.2 x 15);
// glyph: bolt (charging), arrow out (sending power out), none (waiting), no-signal (silent / stopped), house (islanded).
export const GLYPH = { C: 'bolt', D: 'out', I: null, S: 'silent', X: 'silent', B: 'house', N: null };
function batterySVG(level, state, size, t, cls) {
  const c = STATE_RGB[state] || STATE_RGB.I, w = clamp01(level) * 15;
  const g = GLYPH[state];
  const glyph = g ? `<g transform="translate(5.6 6.2) scale(0.5)" stroke-width="${g === 'bolt' ? 1.6 : 3}" ${g === 'bolt' ? 'fill="currentColor" stroke="#fff"' : 'stroke="currentColor"'}>${PATHS[g].map((d) => `<path d="${d.replace('f:', '')}"/>`).join('')}</g>` : '';
  return `<svg class="ic ic-battery s-${state} ${cls || ''}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="${t ? 'false' : 'true'}" role="img">${t}`
    + `<rect x="2" y="7" width="17.5" height="10" rx="2" fill="${rgb([255, 255, 255], 0.9)}"/><rect x="3.3" y="8.3" width="${w.toFixed(2)}" height="7.4" rx="1" fill="${rgb(c)}" stroke="none"/>`
    + `<path d="M6.3 8.3v7.4" stroke-width="0.8" stroke-dasharray="1 1"/><path d="M21.2 10.3v3.4" stroke-width="2.4"/>${glyph}</svg>`;
}

// Meter: one scale all the way up. The box (y 12..22) is 100% of nameplate; the lid (y 12) is the limit; load above
// 100% keeps rising ABOVE the lid at the same scale (y 2 = 200%), so it reads "too tall for its box". Over 150%
// (emergency) the overflow gets a jagged top. Tier 5 (fuse open) is an empty box with a fuse badge.
// The tier colour comes from the JSON's tier code, never re-derived from the %.
export function meterGeom(pct) {
  const p = Math.max(0, Math.min(200, Number(pct) || 0));
  return { inTop: 22 - Math.min(100, p) / 10, overTop: 12 - Math.max(0, p - 100) / 10, over: p > 100.05, burst: p > 150 };
}
function meterSVG(opts, size, t) {
  const pct = opts.pct ?? 0, tier = opts.tier ?? 0;
  const c = TIER_RGB[tier] || TIER_RGB[0], g = meterGeom(pct);
  const inH = 22 - g.inTop, overH = 12 - g.overTop;
  const cls = `ic ic-meter t${tier | 0}${opts.exporting ? ' exporting' : ''} ${opts.cls || ''}`;
  const head = `<svg class="${cls}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="${t ? 'false' : 'true'}" role="img">${t}`
    + `<rect x="6" y="12" width="12" height="10" rx="1.2" fill="${rgb([255, 255, 255], 0.92)}"/>`;
  const lid = '<path d="M4.5 12h15" stroke-width="2.2"/></svg>';
  if (tier === 5) {
    return head + `<g transform="translate(7 12.4) scale(0.42)" stroke-width="3">${PATHS.fuse.map((d) => (d.startsWith('f:') ? `<path d="${d.slice(2)}" fill="currentColor" stroke="none"/>` : `<path d="${d}"/>`)).join('')}</g>` + lid;
  }
  const parts = [];
  if (inH > 0.3) {
    const y0 = g.inTop + 0.1, h = inH - 1.1;
    if (opts.exporting) {
      parts.push(`<rect x="7.2" y="${y0.toFixed(2)}" width="9.6" height="${h.toFixed(2)}" fill="${rgb(STATE_RGB.D)}" stroke="none"/>`);
    } else if (opts.homeKW != null && opts.batKW != null && Number(opts.batKW) > 0) {
      const hk = Math.max(0, Number(opts.homeKW) || 0), bk = Math.max(0, Number(opts.batKW) || 0);
      const share = hk + bk > 0 ? bk / (hk + bk) : 0, bh = h * share;
      parts.push(`<rect x="7.2" y="${(y0 + bh).toFixed(2)}" width="9.6" height="${(h - bh).toFixed(2)}" fill="${rgb(HOME_RGB)}" stroke="none"/>`);
      if (bh > 0.05) parts.push(`<rect class="m-bat" x="7.2" y="${y0.toFixed(2)}" width="9.6" height="${bh.toFixed(2)}" fill="${rgb(STATE_RGB.C)}" stroke="none"/>`);
    } else {
      parts.push(`<rect x="7.2" y="${y0.toFixed(2)}" width="9.6" height="${h.toFixed(2)}" fill="${rgb(c)}" stroke="none"/>`);
    }
  }
  if (g.over && overH > 0.2) {
    const top = g.burst ? `M7.2 12V${g.overTop.toFixed(2)}l1.6 -1.4 1.6 1.4 1.6 -1.4 1.6 1.4 1.6 -1.4 1.6 1.4V12` : `M7.2 12V${g.overTop.toFixed(2)}h9.6V12`;
    parts.push(`<path d="${top}" fill="${rgb(c)}" stroke-width="1.1"/>`);
  }
  if (opts.exporting) parts.push('<path d="M9 19.5l5.5-5.5M11 14h3.5v3.5" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>');
  return head + parts.join('') + lid;
}

/** Draw a named icon on a 2D canvas at (x, y) (top-left) and `size` px. Same geometry as svg(). */
export function drawIcon(ctx, name, x, y, size, opts = {}) {
  const s = size / 24;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const col = opts.color || [16, 22, 19];
  ctx.strokeStyle = rgb(col); ctx.fillStyle = rgb(col);
  if (name === 'battery') drawBattery(ctx, opts.level ?? 0, opts.state || 'I', col);
  else if (name === 'meter') drawMeter(ctx, opts.pct ?? 0, opts.tier ?? 0, col);
  else {
    if (opts.bg) { ctx.fillStyle = rgb(opts.bg, 0.92); ctx.beginPath(); ctx.arc(12, 12, 12, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = rgb(col); }
    ctx.lineWidth = 1.8;
    for (const d of pathsFor(name) || []) { const p = new Path2D(d.replace('f:', '')); if (d.startsWith('f:')) ctx.fill(p); else ctx.stroke(p); }
  }
  ctx.restore();
}
function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x, y, w, h, r); else ctx.rect(x, y, w, h); }
function drawBattery(ctx, level, state, ink) {
  const c = STATE_RGB[state] || STATE_RGB.I;
  ctx.lineWidth = 1.6;
  rrect(ctx, 2, 7, 17.5, 10, 2); ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.fill(); ctx.stroke();
  const w = clamp01(level) * 15;
  if (w > 0) { rrect(ctx, 3.3, 8.3, w, 7.4, 1); ctx.fillStyle = rgb(c); ctx.fill(); }
  ctx.lineWidth = 0.8; ctx.setLineDash([1, 1]); ctx.beginPath(); ctx.moveTo(6.3, 8.3); ctx.lineTo(6.3, 15.7); ctx.stroke(); ctx.setLineDash([]);
  ctx.lineWidth = 2.4; ctx.beginPath(); ctx.moveTo(21.2, 10.3); ctx.lineTo(21.2, 13.7); ctx.stroke();
  const g = GLYPH[state];
  if (g) {
    ctx.save(); ctx.translate(5.6, 6.2); ctx.scale(0.5, 0.5); ctx.fillStyle = rgb(ink);
    for (const d of PATHS[g]) {
      const p = new Path2D(d.replace('f:', ''));
      if (d.startsWith('f:')) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.4; ctx.stroke(p); ctx.fill(p); }
      else { ctx.strokeStyle = '#fff'; ctx.lineWidth = 6; ctx.stroke(p); ctx.strokeStyle = rgb(ink); ctx.lineWidth = 3; ctx.stroke(p); }
    }
    ctx.restore();
  }
}
function drawMeter(ctx, pct, tier, ink) {
  const c = TIER_RGB[tier] || TIER_RGB[0], g = meterGeom(pct);
  ctx.lineWidth = 1.6; ctx.strokeStyle = rgb(ink);
  rrect(ctx, 6, 12, 12, 10, 1.2); ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.fill(); ctx.stroke();
  if (tier === 5) {
    ctx.save(); ctx.translate(7, 12.4); ctx.scale(0.42, 0.42); ctx.lineWidth = 3; ctx.fillStyle = rgb(ink);
    for (const d of PATHS.fuse) { const p = new Path2D(d.replace('f:', '')); if (d.startsWith('f:')) ctx.fill(p); else ctx.stroke(p); }
    ctx.restore();
  } else {
    const inH = 22 - g.inTop;
    ctx.fillStyle = rgb(c);
    if (inH > 0.3) ctx.fillRect(7.2, g.inTop + 0.1, 9.6, inH - 1.1);
    if (g.over && 12 - g.overTop > 0.2) {
      ctx.beginPath(); ctx.moveTo(7.2, 12); ctx.lineTo(7.2, g.overTop);
      if (g.burst) { for (let i = 1; i <= 6; i++) ctx.lineTo(7.2 + i * 1.6, g.overTop + (i % 2 ? -1.4 : 0)); } else ctx.lineTo(16.8, g.overTop);
      ctx.lineTo(16.8, 12); ctx.closePath(); ctx.fill(); ctx.lineWidth = 1.1; ctx.stroke();
    }
  }
  ctx.lineWidth = 2.2; ctx.beginPath(); ctx.moveTo(4.5, 12); ctx.lineTo(19.5, 12); ctx.stroke();
}

/** Icon ids for the atlas. Battery: `bat-<state>-<decile>`; meter: `m-<tier>-<pct5>` (pct in 5% steps, 0..200);
 *  glyph badges: `g-<name>` on a round paper background. */
export const BATTERY_STATES = 'CDISXBN';
export const batteryId = (state, soc) => `bat-${BATTERY_STATES.includes(state) && state ? state : 'I'}-${Math.round(clamp01(soc) * 10)}`;
export const meterId = (tier, pct) => `m-${Math.max(0, Math.min(5, tier | 0))}-${Math.max(0, Math.min(200, Math.round((Number(pct) || 0) / 5) * 5))}`;
export const ATLAS_GLYPHS = ['warn', 'fuse', 'hot', 'silent', 'stall', 'bolt', 'priceDown', 'priceUp', 'house', 'padmount', 'polemount', 'cabinet', 'ok', 'check', 'turns', 'money'];
/** Every atlas id with its drawing recipe (pure; buildAtlas draws them). */
export function atlasIds() {
  const ids = [];
  for (const st of BATTERY_STATES) for (let d = 0; d <= 10; d++) ids.push(['battery', `bat-${st}-${d}`, { state: st, level: d / 10 }]);
  for (let tier = 0; tier <= 5; tier++) for (let p = 0; p <= 200; p += 5) ids.push(['meter', `m-${tier}-${p}`, { tier, pct: p }]);
  for (const g of ATLAS_GLYPHS) ids.push([g, `g-${g}`, { bg: [247, 249, 245] }]);
  return ids;
}
export function buildAtlas(cell = 64, ink = [16, 22, 19], doc = globalThis.document) {
  const ids = atlasIds();
  const cols = Math.floor(2048 / cell), rows = Math.ceil(ids.length / cols);
  const canvas = doc.createElement('canvas');
  canvas.width = cols * cell; canvas.height = rows * cell;
  const ctx = canvas.getContext('2d');
  const mapping = {};
  ids.forEach(([name, id, o], i) => {
    const x = (i % cols) * cell, y = Math.floor(i / cols) * cell;
    const col = name === 'warn' ? [208, 59, 59] : ink;
    drawIcon(ctx, name, x, y, cell, { ...o, color: col });
    mapping[id] = { x, y, width: cell, height: cell, anchorY: cell, mask: false };
  });
  return { canvas, mapping };
}

// ---- words (2.4): plain first; the exact rule sits in the tooltip. Tier codes come from the JSON, never re-derived ----
export const TIER_WORDS = ['Within rating', 'Over', 'Overloaded', 'Overloaded 30+ min', 'Emergency', 'Fuse open'];
export const TIER_GLYPH = ['check', 'warn', 'warn', 'warn', 'warn', 'fuse'];
export const TIER_TIPS = [
  'At or under 100% of nameplate.',
  '100–110% of nameplate. Short spells are normal; not a violation.',
  'Above 110%, its normal rating. If it lasts 30 minutes it becomes a violation; the clock is running.',
  'Above 110% for 30 minutes or more: a normal-rating violation (the team rule).',
  'Above 150%, its emergency rating (SMART-DS ratings, REAL).',
  'Our fuse rule opened it (above 200% for 10 min, or 300% for 60 s; ASSUMPTION). Homes without a battery go dark.',
];
export const STATE_WORDS = { C: 'charging', D: 'sending power out', I: 'waiting', S: 'silent (no signal)', X: 'stopped safely',
  B: 'powering its own home', N: 'new (P2)' };

// ---- the legend container (6.4): collapsible to a pill; rows are icon + words; l4 fills the live tier counts ----------
/** Object rows every scene legend starts with (house, battery, pad-mount, pole-mount, the meter). */
export const LEGEND_OBJECTS = [
  { icon: 'house', text: 'home', tip: 'A home on this feeder (footprint from OpenStreetMap, REAL).' },
  { icon: 'battery', opts: { state: 'C', level: 0.6 }, text: 'battery (fill = charge)', tip: 'A Base battery cabinet beside the home. Fill = state of charge; the dashed tick is the 20% member reserve.' },
  { icon: 'padmount', text: 'transformer on the ground', tip: 'Pad-mount transformer (green box). Its colour never changes with load.' },
  { icon: 'polemount', text: 'transformer on a pole', tip: 'Pole-mount transformer (grey can).' },
  { icon: 'meter', opts: { pct: 130, tier: 2 }, text: 'the box is its limit; sticking out = too much', tip: 'Load meter: the box is 100% of nameplate; anything above the lid is load over the rating.' },
];
export const TAG_LEGEND = 'R S D A: where a number comes from (hover any tag)';
/** A legend: <details class="hb-legend ..."> with a pill summary. rows: [{icon, opts?, text, tip?, html?}], extraHTML is
 *  trusted HTML built by our code (the tier counts); foot is plain text, footHTML trusted HTML (with fmt.chip tags). Pure. */
export function legendHTML({ title = 'Legend', rows = LEGEND_OBJECTS, extraHTML = '', foot = '', footHTML = '', open = true, cls = '' } = {}) {
  const row = (r) => `<div class="hb-legend-row"${r.tip ? ` data-tip="${esc(r.tip)}" tabindex="0"` : ''}>`
    + `<span class="hb-legend-ic">${svg(r.icon, { size: 18, ...(r.opts || {}) })}</span><span>${r.html ?? esc(r.text)}</span></div>`;
  return `<details class="hb-legend ${cls}"${open ? ' open' : ''}><summary>${svg('info', { size: 14 })}<span>${esc(title)}</span></summary>`
    + `<div class="hb-legend-body">${rows.map(row).join('')}${extraHTML}`
    + `<div class="hb-legend-tags">${esc(TAG_LEGEND)}</div>${foot || footHTML ? `<div class="hb-legend-foot">${footHTML || esc(foot)}</div>` : ''}</div></details>`;
}
