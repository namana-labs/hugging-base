// ui/app.js (L0): the shell. Routes the deep link, sets the health flags the smoke test reads, shows the
// FIXTURE banner, creates the scene (deck.gl, or the 2D fallback) and mounts the view's panel.
//
// Health flags on <body> (build prompt 5.5):
//   data-status   loading | ready | error
//   data-webgl    ok | fallback            (pending until the scene exists)
//   data-errors   count of errors + unhandled rejections (window.__hbHealth, set up inline in index.html)
//   data-fixture  1 if any fixture file loaded (the FIXTURE banner shows), else 0
//   data-offsite  count of resources loaded from another origin (must be 0: no network at view time)
//
// Deep links: ?view=p1&branch=none|naive|aware|aware_faults&t=HH:MM&cam=feeder|street|t240
//             ?view=p2&combo=<id>&home=<id>&n=1..10      ?view=more      &beat=<id> (from data/beats.json)
//             &nowebgl=1 forces the 2D fallback; &smoke=dump finalizes deck.gl after the first render (manual only).
import * as data from './lib/data.js';
import * as fmt from './lib/format.js';
import * as sceneModel from './lib/scene-model.js';

const body = document.body;
const health = window.__hbHealth || (window.__hbHealth = { errors: 0, messages: [], onchange: null });
const setFlag = (k, v) => { body.dataset[k] = String(v); };

function showError(msg) {
  let el = document.querySelector('.hb-error');
  if (!el) { el = document.createElement('div'); el.className = 'hb-error'; body.appendChild(el); }
  el.hidden = false;
  el.textContent = msg;
}

export function reportError(err) {
  health.errors += 1;
  health.messages.push(String(err && err.stack ? err.stack : err));
  setFlag('errors', health.errors);
  console.error('[hb]', err);
}
health.onchange = () => setFlag('errors', health.errors);
setFlag('errors', health.errors);

function countOffsite() {
  const here = location.origin;
  let n = 0;
  for (const e of performance.getEntriesByType('resource')) {
    try { if (new URL(e.name).origin !== here) n += 1; } catch (err) { n += 1; }
  }
  setFlag('offsite', n);
  return n;
}
try {
  new PerformanceObserver(() => countOffsite()).observe({ type: 'resource', buffered: true });
} catch (e) { /* older engines: counted again at ready */ }

function theme() {
  const t = document.documentElement.dataset.theme;
  if (t === 'dark' || t === 'light') return t;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function header(link) {
  const tabs = [['p1', 'P1 · where to charge'], ['p2', 'P2 · where the next battery goes'], ['more', 'More']];
  const h = document.createElement('header');
  h.className = 'hb-header';
  h.innerHTML = `<div class="hb-brand">Hugging Base<small>feeder-aware battery fleet</small></div>
    <nav class="hb-tabs">${tabs.map(([v, t]) => `<a href="${data.linkQuery({ view: v })}"${v === link.view ? ' aria-current="page"' : ''}>${t}</a>`).join('')}</nav>
    <div class="hb-standin">NREL SMART-DS 2018 AUS P1U feeder ${fmt.chip('REAL', 'CC BY 4.0')}<br>Oncor-suburb stand-in settled at LZ_NORTH (placeholder) ${fmt.chip('ASSUMPTION', 'CLAUDE.md')}</div>`;
  const banner = document.createElement('div');
  banner.className = 'hb-fixture';
  banner.hidden = true;
  banner.textContent = 'FIXTURE DATA: synthetic stand-ins, not results. Real data has not been built for this view yet.';
  data.onFixture(() => { banner.hidden = false; body.classList.add('has-fixture'); setFlag('fixture', 1); });
  return [h, banner];
}

function withTimeout(p, ms, what) {
  return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`${what} timed out after ${ms} ms`)), ms))]);
}

async function makeScene(el, topology, link) {
  const opts = { topology, theme: theme(), onError: (e) => reportError(e) };
  if (!link.nowebgl) {
    try {
      const m = await import('./lib/scene3d.js');
      const s = m.createScene(el, opts);
      setFlag('webgl', 'ok');
      return s;
    } catch (e) {
      console.warn('[hb] WebGL scene unavailable, using the 2D fallback:', e && e.message);
      el.innerHTML = '';
    }
  }
  const f = await import('./lib/fallback2d.js');
  const s = f.createScene(el, opts);
  setFlag('webgl', 'fallback');
  return s;
}

async function main() {
  setFlag('status', 'loading');
  setFlag('fixture', 0);
  let link = data.parseLink(location.search);
  if (link.beat) link = data.applyBeat(link, await data.loadBeats());
  body.classList.add(`view-${link.view}`);
  const [h, banner] = header(link);
  body.prepend(banner);
  body.prepend(h);
  const sceneEl = document.createElement('div');
  sceneEl.className = 'hb-scene';
  sceneEl.id = 'scene';
  const panelEl = document.createElement('aside');
  panelEl.className = 'hb-panel';
  panelEl.id = 'panel';
  body.append(sceneEl, panelEl);

  const [topology, footprints] = await Promise.all([data.loadTopology(), data.loadFootprints()]);
  const scene = await makeScene(sceneEl, topology, link);
  const panels = { p1: './panels/p1.js', p2: './panels/p2.js', more: './panels/more.js' };
  const panel = await import(panels[link.view]);
  const ctx = {
    topology, footprints, link, scene, data, fmt, sceneModel, theme: theme(), reportError,
    href: (patch) => data.linkQuery({ ...link, beat: null, ...patch }),
    go: (patch) => { location.search = data.linkQuery({ ...link, beat: null, ...patch }); },
  };
  await panel.mount(panelEl, ctx);
  await withTimeout(scene.whenRendered(), 20000, 'first scene render');
  countOffsite();
  if (link.smoke === 'dump') scene.dispose();
  setFlag('status', 'ready');
}

main().catch((e) => {
  reportError(e);
  showError(`Could not start: ${e && e.message ? e.message : e}`);
  countOffsite();
  setFlag('status', 'error');
});
