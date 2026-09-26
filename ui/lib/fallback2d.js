// ui/lib/fallback2d.js -- OWNED BY L4. This is L0's STUB: the same scene model drawn top-down on a 2D canvas,
// used when deck.gl or WebGL2 fails, or ?nowebgl=1 is set. Same Scene API as scene3d.js; scene.kind = 'fallback'.
import { cameraPreset } from './scene-model.js';

export function createScene(el, opts = {}) {
  const topology = opts.topology;
  const canvas = document.createElement('canvas');
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  el.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  let model = null;
  let pick = null;
  let view = cameraPreset(topology, 'feeder');

  function project() {
    const w = canvas.width, h = canvas.height;
    const scale = Math.pow(2, view.zoom) * 256 / 360;               // px per degree of longitude
    const k = Math.cos(view.latitude * Math.PI / 180);
    return (p) => [w / 2 + (p[0] - view.longitude) * scale * (window.devicePixelRatio || 1) / 1,
      h / 2 - (p[1] - view.latitude) * scale / k * (window.devicePixelRatio || 1)];
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
    const P = project();
    const rgba = (c) => `rgba(${c[0]},${c[1]},${c[2]},${(c[3] ?? 255) / 255})`;
    ctx.lineWidth = 1.2 * dpr;
    for (const l of model.lines) {
      const a = P(l.path[0]), b = P(l.path[1]);
      ctx.strokeStyle = rgba(l.color);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    const s = 3.2 * dpr;
    for (const hm of model.homes) {
      const p = P(hm.position);
      ctx.fillStyle = rgba(hm.color);
      ctx.fillRect(p[0] - s, p[1] - s, 2 * s, 2 * s);
    }
    for (const b of model.batteries) {
      const p = P(b.position);
      ctx.fillStyle = rgba(b.color);
      ctx.fillRect(p[0] + s, p[1] - b.height * dpr * 0.4, 2 * dpr, b.height * dpr * 0.4);
    }
    for (const c of model.cans) {
      const p = P(c.position);
      ctx.fillStyle = rgba(c.color);
      ctx.beginPath(); ctx.arc(p[0], p[1], Math.max(2.5, c.radius / 4) * dpr, 0, Math.PI * 2); ctx.fill();
    }
    ctx.font = `700 ${14 * dpr}px sans-serif`;
    for (const t of model.labels) {
      const p = P(t.position);
      ctx.fillStyle = rgba(t.color);
      ctx.fillText(t.text, p[0] + 6 * dpr, p[1] - 6 * dpr);
    }
  }

  const onResize = () => draw();
  window.addEventListener('resize', onResize);
  canvas.addEventListener('click', (ev) => {
    if (!pick || !model) return;
    const P = project();
    const dpr = window.devicePixelRatio || 1;
    const x = ev.offsetX * dpr, y = ev.offsetY * dpr;
    let best = null, bd = 1e9;
    model.cans.forEach((c, i) => { const p = P(c.position); const d = Math.hypot(p[0] - x, p[1] - y); if (d < bd) { bd = d; best = { layer: 'cans', object: c, index: i }; } });
    if (best && bd < 20 * dpr) pick(best);
  });

  return {
    kind: 'fallback',
    update(m) { model = m; draw(); },
    camera(preset) { view = cameraPreset(topology, preset); draw(); },
    onPick(cb) { pick = cb; },
    dispose() { window.removeEventListener('resize', onResize); canvas.remove(); },
    whenRendered() { return new Promise((res) => requestAnimationFrame(() => { draw(); res(); })); },
  };
}
