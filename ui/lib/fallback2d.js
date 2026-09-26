// ui/lib/fallback2d.js (L4): the same scene model drawn top-down on a 2D canvas, used when deck.gl or WebGL2 fails,
// or ?nowebgl=1 is set. Same Scene API as scene3d.js; scene.kind = 'fallback'. Web Mercator at the preset's zoom
// (pitch and bearing are ignored). Drag to pan, wheel to zoom; the camera presets rescue a bad view.
// Encoding: homes = real footprints tinted by their transformer's tier; cans = a disc (tier colour) with a bar whose
// full height is 100% of nameplate, a tick at 110% and a red tick at 150%; batteries = a small bar (fill = SoC, a
// line at the 20% reserve); A-D and T-240 labelled.
import { cameraPreset, RESERVE_FRACTION } from './scene-model.js';

const TILE = 256;
function mercX(lon, z) { return (lon + 180) / 360 * TILE * Math.pow(2, z); }
function mercY(lat, z) {
  const s = Math.sin(lat * Math.PI / 180);
  return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * TILE * Math.pow(2, z);
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
  let model = null;
  let pick = null;
  let view = { ...cameraPreset(topology, 'feeder') };
  view.zoom -= 0.35;   // no pitch in 2D: pull back a little so the whole feeder fits

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
    if (!model) return;
    const P = projector();
    const pxPerM = Math.pow(2, view.zoom) * TILE / (40075016.7 * Math.cos(view.latitude * Math.PI / 180)) * dpr;
    for (const c of model.context) { ctx.fillStyle = rgba(c.color); poly(P, c.polygon); ctx.fill(); }
    ctx.lineWidth = 1.1 * dpr;
    for (const l of model.lines) {
      const a = P(l.path[0]), b = P(l.path[1]);
      ctx.strokeStyle = rgba(l.color);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    const ink = model.ink;
    ctx.strokeStyle = rgba([ink[0], ink[1], ink[2], 70]);
    ctx.lineWidth = 0.6 * dpr;
    for (const h of model.homes) { ctx.fillStyle = rgba(h.color); poly(P, h.polygon); ctx.fill(); if (pxPerM > 0.6) ctx.stroke(); }
    // cans: a disc plus a loading bar (full bar = 100% of nameplate)
    const barH = Math.max(10, 26 * pxPerM) , barW = Math.max(2.5, 2.2 * pxPerM);
    for (const c of model.cans) {
      const p = P(c.position);
      const rad = Math.max(2.2 * dpr, c.radius * pxPerM);
      ctx.fillStyle = rgba(c.color);
      ctx.beginPath(); ctx.arc(p[0], p[1], rad, 0, Math.PI * 2); ctx.fill();
      if (c.focus || c.code > 0 || pxPerM > 0.8) {
        const x = p[0] + rad + 2 * dpr, y0 = p[1] + rad;
        ctx.fillStyle = rgba([ink[0], ink[1], ink[2], 40]);
        ctx.fillRect(x, y0 - barH, barW, barH);
        ctx.fillStyle = rgba(c.color);
        const hh = Math.min(barH * 2.2, barH * c.pct / 100);
        ctx.fillRect(x, y0 - hh, barW, hh);
        ctx.fillStyle = rgba([ink[0], ink[1], ink[2], 200]);
        ctx.fillRect(x - 1 * dpr, y0 - barH * 1.1, barW + 2 * dpr, 1 * dpr);
        ctx.fillStyle = 'rgba(208,59,59,0.9)';
        ctx.fillRect(x - 1 * dpr, y0 - barH * 1.5, barW + 2 * dpr, 1.2 * dpr);
      }
    }
    // batteries: ghost bar (full), fill = SoC, reserve line
    const bH = Math.max(8, 12 * pxPerM), bW = Math.max(2, 2.4 * pxPerM);
    for (const b of model.batteries) {
      const p = P(b.position);
      ctx.fillStyle = rgba([ink[0], ink[1], ink[2], 45]);
      ctx.fillRect(p[0], p[1] - bH, bW, bH);
      ctx.fillStyle = rgba(b.color);
      ctx.fillRect(p[0], p[1] - bH * b.soc, bW, bH * b.soc);
      ctx.fillStyle = rgba([ink[0], ink[1], ink[2], 200]);
      ctx.fillRect(p[0] - 1 * dpr, p[1] - bH * RESERVE_FRACTION, bW + 2 * dpr, 1 * dpr);
    }
    ctx.lineWidth = 2 * dpr;
    for (const s of model.pulses) {
      const p = P(s.position);
      ctx.strokeStyle = rgba(s.color);
      ctx.beginPath(); ctx.arc(p[0], p[1], Math.max(5 * dpr, 5.5 * pxPerM), 0, Math.PI * 2); ctx.stroke();
    }
    ctx.font = `800 ${13 * dpr}px sans-serif`;
    for (const a of model.alerts) {
      const p = P(a.position);
      ctx.fillStyle = 'rgba(110,114,111,0.92)';
      ctx.fillRect(p[0] - 5 * dpr, p[1] - bH - 16 * dpr, 12 * dpr, 15 * dpr);
      ctx.fillStyle = '#fff';
      ctx.fillText(a.text, p[0] - 1 * dpr, p[1] - bH - 4 * dpr);
    }
    ctx.font = `700 ${13 * dpr}px Inter, "Helvetica Neue", Helvetica, Arial, sans-serif`;
    for (const t of model.labels) {
      const p = P(t.position);
      const w = ctx.measureText(t.text).width;
      const x = p[0] + 8 * dpr, y = p[1] - 14 * dpr;
      ctx.fillStyle = model.theme === 'dark' ? 'rgba(17,24,21,0.88)' : 'rgba(247,249,245,0.92)';
      ctx.fillRect(x - 4 * dpr, y - 13 * dpr, w + 8 * dpr, 18 * dpr);
      ctx.fillStyle = rgba(t.color);
      ctx.fillText(t.text, x, y);
    }
  }

  const onResize = () => draw();
  window.addEventListener('resize', onResize);
  let drag = null;
  canvas.addEventListener('mousedown', (ev) => { drag = { x: ev.clientX, y: ev.clientY, lon: view.longitude, lat: view.latitude, moved: false }; });
  window.addEventListener('mouseup', () => { setTimeout(() => { drag = null; }, 0); });
  canvas.addEventListener('mousemove', (ev) => {
    if (!drag) return;
    const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    const z = view.zoom;
    const cx = mercX(drag.lon, z) - dx, cy = mercY(drag.lat, z) - dy;
    const n = Math.PI - 2 * Math.PI * cy / (TILE * Math.pow(2, z));
    view = { ...view, longitude: cx / (TILE * Math.pow(2, z)) * 360 - 180, latitude: 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))) };
    draw();
  });
  canvas.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    view = { ...view, zoom: Math.max(12, Math.min(20, view.zoom - Math.sign(ev.deltaY) * 0.25)) };
    draw();
  }, { passive: false });
  canvas.addEventListener('click', (ev) => {
    if (!pick || !model || (drag && drag.moved)) return;
    const P = projector();
    const dpr = window.devicePixelRatio || 1;
    const x = ev.offsetX * dpr, y = ev.offsetY * dpr;
    let best = null, bd = 1e9;
    model.cans.forEach((c, i) => { const p = P(c.position); const d = Math.hypot(p[0] - x, p[1] - y); if (d < bd) { bd = d; best = { layer: 'cans', object: c, index: i }; } });
    if (best && bd < 20 * dpr) pick(best);
  });

  return {
    kind: 'fallback',
    update(m) { model = m; draw(); },
    camera(preset) { view = { ...cameraPreset(topology, preset) }; if (preset === 'feeder') view.zoom -= 0.35; draw(); },
    onPick(cb) { pick = cb; },
    dispose() { window.removeEventListener('resize', onResize); canvas.remove(); },
    whenRendered() { return new Promise((res) => requestAnimationFrame(() => { draw(); res(); })); },
  };
}
