// icons.js (R2 scene design prototype; target file ui/lib/icons.js, lane l4-scene-p1). ONE icon set, three renderers:
//   svg(name, opts)            -> inline SVG string for the DOM panel (currentColor, 24x24 grid)
//   drawIcon(ctx, name, x, y, size, opts)  -> the same paths on a 2D canvas (fallback2d.js and the atlas)
//   buildAtlas()               -> {canvas, mapping}  deck.gl IconLayer atlas (no network: drawn at start-up)
// Procedural icons: battery(level 0..1, state), meter(pct, tier), both drawn identically in SVG and canvas.
export const TIER_RGB = [[12, 163, 12], [250, 178, 25], [236, 131, 90], [224, 96, 58], [208, 59, 59], [107, 111, 108]];
export const STATE_RGB = { C: [11, 107, 111], D: [236, 131, 90], I: [140, 164, 146], S: [150, 150, 150], X: [150, 150, 150], B: [255, 196, 92] };

// 24x24 stroke paths (round caps/joins, stroke 1.8). "f:" prefix = filled path.
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
};

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

/** Inline SVG for the DOM. opts: {size=18, title, cls} ; battery/meter take {level,state} / {pct,tier}. */
export function svg(name, opts = {}) {
  const size = opts.size || 18;
  const t = opts.title ? `<title>${esc(opts.title)}</title>` : '';
  if (name === 'battery') return batterySVG(opts.level ?? 0, opts.state || 'I', size, t, opts.cls);
  if (name === 'meter') return meterSVG(opts.pct ?? 0, opts.tier ?? 0, size, t, opts.cls);
  const body = (PATHS[name] || []).map((d) => (d.startsWith('f:') ? `<path d="${d.slice(2)}" fill="currentColor" stroke="none"/>` : `<path d="${d}"/>`)).join('');
  return `<svg class="ic ic-${name} ${opts.cls || ''}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="${t ? 'false' : 'true'}" role="img">${t}${body}</svg>`;
}

// Battery: horizontal, body 2..19 x 7..17, nub 20..22; fill = level (0..1) in the state colour; reserve tick at 20%;
// glyph: bolt (charging), arrow (discharging), hourglass (idle), silent (stale/expired), house (islanded).
const GLYPH = { C: 'bolt', D: 'out', I: null, S: 'silent', X: 'silent', B: 'house' };
function batterySVG(level, state, size, t, cls) {
  const c = STATE_RGB[state] || STATE_RGB.I, w = Math.max(0, Math.min(1, level)) * 15;
  const g = GLYPH[state];
  const glyph = g ? `<g transform="translate(5.6 6.2) scale(0.5)" stroke-width="${g === 'bolt' ? 1.6 : 3}" ${g === 'bolt' ? 'fill="currentColor" stroke="#fff"' : 'stroke="currentColor"'}>${PATHS[g].map((d) => `<path d="${d.replace('f:', '')}"/>`).join('')}</g>` : '';
  return `<svg class="ic ic-battery ${cls || ''}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${t}
    <rect x="2" y="7" width="17.5" height="10" rx="2" fill="${rgb([255, 255, 255], 0.9)}"/><rect x="3.3" y="8.3" width="${w.toFixed(2)}" height="7.4" rx="1" fill="${rgb(c)}" stroke="none"/>
    <path d="M6.3 8.3v7.4" stroke-width="0.8" stroke-dasharray="1 1"/><path d="M21.2 10.3v3.4" stroke-width="2.4"/>${glyph}</svg>`;
}
// Meter: one scale all the way up. The box (y 12..22) is 100% of nameplate; the lid (y 12) is the limit; load above
// 100% keeps rising ABOVE the lid at the same scale (y 2 = 200%), outlined, so it reads "too tall for its box".
// Over 150% (emergency) the overflow gets a jagged top. Tier colour from the JSON's tier code, never re-derived.
export function meterGeom(pct) {
  const p = Math.max(0, Math.min(200, pct));
  return { inTop: 22 - Math.min(100, p) / 10, overTop: 12 - Math.max(0, p - 100) / 10, over: p > 100.05, burst: p > 150 };
}
function meterSVG(pct, tier, size, t, cls) {
  const c = TIER_RGB[tier] || TIER_RGB[0], g = meterGeom(pct);
  const inH = 22 - g.inTop, overH = 12 - g.overTop;
  const top = g.burst ? `M7.2 12V${g.overTop.toFixed(2)}l1.6 -1.4 1.6 1.4 1.6 -1.4 1.6 1.4 1.6 -1.4 1.6 1.4V12` : `M7.2 12V${g.overTop.toFixed(2)}h9.6V12`;
  return `<svg class="ic ic-meter ${cls || ''}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round">${t}
    <rect x="6" y="12" width="12" height="10" rx="1.2" fill="${rgb([255, 255, 255], 0.92)}"/>
    ${inH > 0.3 ? `<rect x="7.2" y="${(g.inTop + 0.1).toFixed(2)}" width="9.6" height="${(inH - 1.1).toFixed(2)}" fill="${rgb(c)}" stroke="none"/>` : ''}
    ${g.over && overH > 0.2 ? `<path d="${top}" fill="${rgb(c)}" stroke-width="1.1"/>` : ''}
    <path d="M4.5 12h15" stroke-width="2.2"/></svg>`;
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
    for (const d of PATHS[name] || []) { const p = new Path2D(d.replace('f:', '')); if (d.startsWith('f:')) ctx.fill(p); else ctx.stroke(p); }
  }
  ctx.restore();
}
function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect ? ctx.roundRect(x, y, w, h, r) : ctx.rect(x, y, w, h); }
function drawBattery(ctx, level, state, ink) {
  const c = STATE_RGB[state] || STATE_RGB.I;
  ctx.lineWidth = 1.6;
  rrect(ctx, 2, 7, 17.5, 10, 2); ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.fill(); ctx.stroke();
  const w = Math.max(0, Math.min(1, level)) * 15;
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
  const inH = 22 - g.inTop;
  ctx.fillStyle = rgb(c);
  if (inH > 0.3) ctx.fillRect(7.2, g.inTop + 0.1, 9.6, inH - 1.1);
  if (g.over && 12 - g.overTop > 0.2) {
    ctx.beginPath(); ctx.moveTo(7.2, 12); ctx.lineTo(7.2, g.overTop);
    if (g.burst) { for (let i = 1; i <= 6; i++) ctx.lineTo(7.2 + i * 1.6, g.overTop + (i % 2 ? -1.4 : 0)); } else ctx.lineTo(16.8, g.overTop);
    ctx.lineTo(16.8, 12); ctx.closePath(); ctx.fill(); ctx.lineWidth = 1.1; ctx.stroke();
  }
  ctx.lineWidth = 2.2; ctx.beginPath(); ctx.moveTo(4.5, 12); ctx.lineTo(19.5, 12); ctx.stroke();
}

/** Icon ids for the atlas. Battery: `bat-<state>-<decile>`; meter: `m-<tier>-<pct5>` (pct in 5% steps, 0..200);
 *  glyph badges: `g-<name>` on a round paper background. */
export const batteryId = (state, soc) => `bat-${'CDISXB'.includes(state) ? state : 'I'}-${Math.round(Math.max(0, Math.min(1, soc)) * 10)}`;
export const meterId = (tier, pct) => `m-${tier | 0}-${Math.max(0, Math.min(200, Math.round(pct / 5) * 5))}`;
export function buildAtlas(cell = 64, ink = [16, 22, 19]) {
  const ids = [];
  for (const st of 'CDISXB') for (let d = 0; d <= 10; d++) ids.push(['battery', `bat-${st}-${d}`, { state: st, level: d / 10 }]);
  for (let tier = 0; tier <= 5; tier++) for (let p = 0; p <= 200; p += 5) ids.push(['meter', `m-${tier}-${p}`, { tier, pct: p }]);
  for (const g of ['warn', 'fuse', 'hot', 'silent', 'stall', 'bolt', 'priceDown', 'priceUp', 'house', 'padmount', 'polemount', 'cabinet', 'ok']) ids.push([g, `g-${g}`, { bg: [247, 249, 245] }]);
  const cols = Math.floor(2048 / cell), rows = Math.ceil(ids.length / cols);
  const canvas = document.createElement('canvas');
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
