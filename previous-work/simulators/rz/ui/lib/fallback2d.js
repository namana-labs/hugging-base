// ui/lib/fallback2d.js (L4): the same scene model drawn top-down on a 2D canvas, used when deck.gl or WebGL2 fails,
// or ?nowebgl=1 is set. Same Scene API as scene3d.js; scene.kind = 'fallback'. Web Mercator at the preset's zoom
// (pitch and bearing are ignored). Drag to pan, wheel to zoom; the camera presets rescue a bad view.
// Draws what the 3D scene draws, seen from above (UX_SPEC_R2 6.1): hip roofs (baked triangles, tinted at tier >= 1),
// pad-mount boxes and poles, white battery cabinets, tier halos, service drops, and the atlas icons (meters, batteries)
// via drawImage, plus "A".."D", "T-240" and "worst now N%". Hover hit-tests icons, transformers, cabinets and homes and
// reports {x, y, layer, object} with the 3D layer ids, so the panel's tooltip copy is shared.
import { cameraPreset, roofColor, dropStyle, TIER_RGB } from './scene-model.js';
import { buildAtlas } from './icons.js';

const TILE = 256;
const NEAR = 16.2;
function mercX(lon, z) { return (lon + 180) / 360 * TILE * Math.pow(2, z); }
function mercY(lat, z) {
  const s = Math.sin(lat * Math.PI / 180);
  return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * TILE * Math.pow(2, z);
}
function inPoly(pt, P) {
  let c = false;
  for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
    if (((P[i][1] > pt[1]) !== (P[j][1] > pt[1])) && (pt[0] < (P[j][0] - P[i][0]) * (pt[1] - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0])) c = !c;
  }
  return c;
}

export function createScene(el, opts = {}) {
  const topology = opts.topology;
  const canvas = document.createElement('canvas');
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.display = 'block';
  el.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('2D canvas unavailable');
  let atlas = null;
  try { atlas = buildAtlas(64); } catch (e) { atlas = null; }
  let model = null;
  let pick = null, hover = null;
  let hits = [];            // screen-space hit targets of the last draw, topmost last
  // no pitch in 2D: undo the preset's pitch offset and fit the whole feeder
  const flat = (preset) => {
    const v = { ...cameraPreset(topology, preset) };
    if (preset === 'feeder') { v.latitude += 0.0012; v.zoom -= 0.35; } else v.latitude += 0.00022;
    return v;
  };
  let view = flat('feeder');

  function projector() {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width, h = canvas.height;
    const z = view.zoom, cx = mercX(view.longitude, z), cy = mercY(view.latitude, z);
    return (p) => [w / 2 + (mercX(p[0], z) - cx) * dpr, h / 2 + (mercY(p[1], z) - cy) * dpr];
  }
  const rgba = (c) => `rgba(${c[0]},${c[1]},${c[2]},${(c[3] ?? 255) / 255})`;
  function poly(P, ring) {
    ctx.beginPath();
    ring.forEach((pt, i) => { const q = P(pt); if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
    ctx.closePath();
  }

  function draw() {
    const r = el.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(r.width * dpr));
    canvas.height = Math.max(1, Math.round(r.height * dpr));
    const bg = getComputedStyle(document.body).getPropertyValue('--bg').trim() || '#E9EDE7';
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    hits = [];
    if (!model) return;
    const m = model;
    const P = projector();
    const near = view.zoom >= NEAR;
    const pxPerM = Math.pow(2, view.zoom) * TILE / (40075016.7 * Math.cos(view.latitude * Math.PI / 180)) * dpr;
    for (const c of m.context) { ctx.fillStyle = rgba(c.color); poly(P, c.polygon); ctx.fill(); }
    ctx.lineWidth = 1 * dpr;
    for (const l of m.lines) {
      const a = P(l.path[0]), b = P(l.path[1]);
      ctx.strokeStyle = rgba(l.color);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    const trgb = (c, a) => [...(TIER_RGB[c] || TIER_RGB[0]), a];
    for (const h of m.halos) {
      const a = P(h.position);
      const rad = Math.max(6 * dpr, 7 * pxPerM);
      ctx.fillStyle = rgba(trgb(h.code, 80)); ctx.strokeStyle = rgba(trgb(h.code, 230)); ctx.lineWidth = 2 * dpr;
      ctx.beginPath(); ctx.arc(a[0], a[1], rad, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    if (near) {
      for (const d of m.drops) {
        const s = dropStyle(m.tier[d.tf] | 0, m.ink);
        const a = P(d.path[0]), b = P(d.path[1]);
        ctx.strokeStyle = rgba(s.color); ctx.lineWidth = s.width * dpr;
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      }
    }
    // walls under the roofs (their state colour shows as the outline), then the roof triangles
    ctx.lineWidth = 0.8 * dpr;
    for (const h of m.homes) { if (h.state !== 'lit') { ctx.fillStyle = rgba(h.color); poly(P, h.polygon); ctx.fill(); } }
    for (const f of m.roofs) {
      const rc = roofColor(f, m.tier[f.tf] | 0);
      ctx.fillStyle = rgba(rc); poly(P, f.poly); ctx.fill();
      ctx.strokeStyle = rgba(rc); ctx.lineWidth = 0.6 * dpr; ctx.stroke();
    }
    for (const h of m.homes) {
      if (h.state !== 'lit') { ctx.strokeStyle = rgba(h.color); ctx.lineWidth = 2.5 * dpr; poly(P, h.polygon); ctx.stroke(); }
    }
    for (const p of m.plinths) { ctx.fillStyle = rgba(m.colors.plinth); poly(P, p.polygon); ctx.fill(); }
    for (const p of m.pads) { ctx.fillStyle = rgba(m.colors.pad); poly(P, p.polygon); ctx.fill(); hits.push({ layer: 'pads', object: p, ring: p.polygon.map(P) }); }
    for (const p of m.poles) {
      const a = P(p.position);
      ctx.fillStyle = rgba(m.colors.pole); ctx.beginPath(); ctx.arc(a[0], a[1], Math.max(2.5 * dpr, 0.5 * pxPerM), 0, 7); ctx.fill();
      hits.push({ layer: 'poles', object: p, at: a, r: 8 * dpr });
    }
    for (const a0 of m.arms) { const a = P(a0.path[0]), b = P(a0.path[1]); ctx.strokeStyle = rgba(m.colors.pole); ctx.lineWidth = Math.max(1, 0.3 * pxPerM); ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    for (const c of m.cans) {
      const a = P(c.position);
      ctx.fillStyle = rgba(m.colors.can); ctx.beginPath(); ctx.arc(a[0], a[1], Math.max(3 * dpr, 1.0 * pxPerM), 0, 7); ctx.fill();
      hits.push({ layer: 'cans', object: c, at: a, r: 9 * dpr });
    }
    for (const c of m.cabinets) {
      ctx.fillStyle = rgba(c.placed ? [...m.colors.cabinet.slice(0, 3), 150] : m.colors.cabinet); poly(P, c.polygon); ctx.fill();
      ctx.strokeStyle = rgba(m.colors.cap); ctx.lineWidth = 1.5 * dpr; ctx.stroke();
      hits.push({ layer: 'cabinets', object: c, ring: c.polygon.map(P) });
    }
    ctx.lineWidth = 2 * dpr;
    for (const s of m.pulses) {
      const p = P(s.position);
      ctx.strokeStyle = rgba(s.color);
      ctx.beginPath(); ctx.arc(p[0], p[1], Math.max(5 * dpr, 5.5 * pxPerM), 0, Math.PI * 2); ctx.stroke();
    }
    const icon = (id, pos, size) => {
      const a = P(pos);
      const mp = atlas && atlas.mapping[id];
      if (mp) ctx.drawImage(atlas.canvas, mp.x, mp.y, mp.width, mp.height, a[0] - size * dpr / 2, a[1] - size * dpr, size * dpr, size * dpr);
      return [a[0], a[1] - size * dpr / 2];
    };
    const mSize = near ? 44 : 30, bSize = near ? 34 : 22;
    for (const mt of m.meters) { const c = icon(mt.icon, mt.position, mSize); hits.push({ layer: 'meters', object: mt, at: c, r: mSize * dpr / 2 }); }
    for (const b of m.batteries) { const c = icon(b.icon, b.position, bSize); hits.push({ layer: 'battery-icons', object: b, at: c, r: bSize * dpr / 2 }); }
    for (const b of m.badges || []) {
      const a = P(b.position), sz = near ? 26 : 20, mp = atlas && atlas.mapping[b.icon];
      if (mp) ctx.drawImage(atlas.canvas, mp.x, mp.y, mp.width, mp.height, a[0] + (near ? 16 : 11) * dpr - sz * dpr / 2, a[1] - ((near ? 34 : 24) + sz) * dpr, sz * dpr, sz * dpr);
    }
    const font = `800 ${14 * dpr}px Inter, "Helvetica Neue", Helvetica, Arial, sans-serif`;
    ctx.font = font;
    for (const t of m.labels) {
      const p = P(t.position);
      const w = ctx.measureText(t.text).width;
      const x = p[0] + (t.pin ? 6 : mSize / 2 + 4) * dpr, y = p[1] - (t.pin ? 8 : mSize * 0.6) * dpr;
      ctx.fillStyle = m.theme === 'dark' ? 'rgba(17,24,21,0.88)' : 'rgba(247,249,245,0.92)';
      ctx.fillRect(x - 4 * dpr, y - 13 * dpr, w + 8 * dpr, 18 * dpr);
      ctx.fillStyle = rgba(t.color);
      ctx.fillText(t.text, x, y);
    }
    for (const l of m.worst) {
      const a = P(l.position);
      const w = ctx.measureText(l.text).width;
      const y = a[1] - (mSize + 24) * dpr;
      ctx.fillStyle = rgba(trgb(l.code, 245));
      ctx.fillRect(a[0] - w / 2 - 6 * dpr, y - 15 * dpr, w + 12 * dpr, 21 * dpr);
      ctx.fillStyle = '#fff';
      ctx.fillText(l.text, a[0] - w / 2, y);
      // the label tag, right of the callout
      const tx = a[0] + w / 2 + 12 * dpr;
      ctx.fillStyle = 'rgba(247,249,245,0.96)'; ctx.strokeStyle = 'rgb(207,202,189)'; ctx.lineWidth = 1 * dpr;
      ctx.fillRect(tx, y - 13 * dpr, 16 * dpr, 17 * dpr); ctx.strokeRect(tx, y - 13 * dpr, 16 * dpr, 17 * dpr);
      ctx.fillStyle = 'rgb(85,98,90)'; ctx.font = `700 ${11 * dpr}px Inter, Helvetica, Arial, sans-serif`;
      ctx.fillText(l.tag, tx + 4 * dpr, y);
      ctx.font = font;
    }
    // homes last in the hit list's search order (below everything else)
    hits.unshift(...m.homes.map((h) => ({ layer: 'walls', object: h, ringLL: h.polygon })));
  }

  /** The topmost object under a canvas point (device pixels), or null. */
  function hitAt(x, y) {
    const P = projector();
    for (let i = hits.length - 1; i >= 0; i--) {
      const h = hits[i];
      if (h.at && Math.hypot(h.at[0] - x, h.at[1] - y) <= h.r) return h;
      if (h.ring && inPoly([x, y], h.ring)) return h;
    }
    // homes: test in screen space only near the point (cheap bbox reject first)
    for (let i = hits.length - 1; i >= 0; i--) {
      const h = hits[i];
      if (!h.ringLL) continue;
      const ring = h.ringLL.map(P);
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const q of ring) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]); }
      if (x < x0 || x > x1 || y < y0 || y > y1) continue;
      if (inPoly([x, y], ring)) return h;
    }
    return null;
  }

  const onResize = () => draw();
  window.addEventListener('resize', onResize);
  let drag = null;
  canvas.addEventListener('mousedown', (ev) => { drag = { x: ev.clientX, y: ev.clientY, lon: view.longitude, lat: view.latitude, moved: false }; });
  window.addEventListener('mouseup', () => { setTimeout(() => { drag = null; }, 0); });
  canvas.addEventListener('mousemove', (ev) => {
    if (!drag) {
      if (!hover) return;
      const dpr = window.devicePixelRatio || 1;
      const h = hitAt(ev.offsetX * dpr, ev.offsetY * dpr);
      canvas.style.cursor = h ? 'pointer' : 'grab';
      hover(h ? { x: ev.offsetX, y: ev.offsetY, layer: h.layer, object: h.object } : null);
      return;
    }
    const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    const z = view.zoom;
    const cx = mercX(drag.lon, z) - dx, cy = mercY(drag.lat, z) - dy;
    const n = Math.PI - 2 * Math.PI * cy / (TILE * Math.pow(2, z));
    view = { ...view, longitude: cx / (TILE * Math.pow(2, z)) * 360 - 180, latitude: 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))) };
    draw();
  });
  canvas.addEventListener('mouseleave', () => { if (hover) hover(null); });
  canvas.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    view = { ...view, zoom: Math.max(12, Math.min(20, view.zoom - Math.sign(ev.deltaY) * 0.25)) };
    draw();
  }, { passive: false });
  canvas.addEventListener('click', (ev) => {
    if (!pick || !model || (drag && drag.moved)) return;
    const dpr = window.devicePixelRatio || 1;
    const h = hitAt(ev.offsetX * dpr, ev.offsetY * dpr);
    if (h) pick({ layer: h.layer, object: h.object, index: -1 });
  });

  return {
    kind: 'fallback',
    update(m) { model = m; draw(); },
    camera(preset) { view = flat(preset); draw(); },
    flyTo(lonlat, o = {}) { view = { ...view, longitude: lonlat[0], latitude: lonlat[1], zoom: o.zoom || 18.3 }; draw(); },
    onPick(cb) { pick = cb; },
    onHover(cb) { hover = cb; },
    dispose() { window.removeEventListener('resize', onResize); canvas.remove(); },
    whenRendered() { return new Promise((res) => requestAnimationFrame(() => { draw(); res(); })); },
  };
}
