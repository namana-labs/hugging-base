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
//             &date=YYYY-MM-DD (a real ERCOT evening; default 2026-08-23) &speed=0.1|0.25|0.5|1|2|4 &hold=0 &cap=0
//             ?view=p2&combo=<id>&home=<id>&n=1..10      ?view=more      &beat=<id> (from data/beats.json)
//             &nowebgl=1 forces the 2D fallback; &smoke=dump finalizes deck.gl after the first render (manual only).
// Dates: a P1 date that p1/days/index.json does not list, or that the P1 panel cannot load yet (it exports
// `supportsDates = true` once it reads data.loadP1MetaFor(ctx.link.date)), shows a notice and the 23 Aug evening.
// aware_faults on a history day opens aware with a notice (failures are scripted for 23 Aug only). Notices are not errors.
import * as data from './lib/data.js';
import * as fmt from './lib/format.js';
import * as sceneModel from './lib/scene-model.js';
import { mountTips } from './lib/tip.js';

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

const STANDIN_CITE = "CLAUDE.md; 'Oncor suburb' is a framing label: the synthetic feeder is drawn on NW-Austin coordinates that fall in Pedernales Electric Cooperative territory (PUCT service-area layers, 2023, marked 'UNOFFICIAL', information purposes only)";
// data-truth fix list #1: NREL's SMART-DS is a real published dataset of a synthetic feeder ("realistic but not real")
const FEEDER_CITE = "NREL SMART-DS 2018 AUS P1U, CC BY 4.0: NREL's published files, byte-identical to OEDI. NREL calls SMART-DS 'realistic but not real' (https://www.nlr.gov/grid/smart-ds.html): a synthetic, statistically realistic Austin feeder, not a utility circuit";

/** A visible notice under the header (not an error: data-errors is untouched). body data-notice counts them. */
function showNotice(msg) {
  let el = document.querySelector('.hb-notice');
  if (!el) {
    el = document.createElement('div');
    el.className = 'hb-notice';
    el.setAttribute('role', 'status');
    el.innerHTML = '<span class="hb-notice-t"></span><button type="button" aria-label="Dismiss">×</button>';
    el.querySelector('button').addEventListener('click', () => { el.hidden = true; });
    body.appendChild(el);
  }
  const t = el.querySelector('.hb-notice-t');
  t.textContent = t.textContent ? `${t.textContent} ${msg}` : msg;
  el.hidden = false;
  setFlag('notice', (Number(body.dataset.notice) || 0) + 1);
}

/** Resolve &date= (and aware_faults on a history day) before the panel mounts. Returns the link the panel sees. */
async function routeDate(link, panel) {
  if (link.view !== 'p1' || link.date === data.DEFAULT_DATE) return link;
  const day = await data.resolveP1Date(link.date);
  const label = fmt.dateLabel(link.date) || link.date;
  if (!day.simulated) { showNotice(day.notice); return { ...link, date: data.DEFAULT_DATE }; }
  if (panel.supportsDates !== true) {
    showNotice(`${label} is simulated, but this P1 view reads 23 Aug only so far; showing ${fmt.dateLabel(data.DEFAULT_DATE)}.`);
    return { ...link, date: data.DEFAULT_DATE };
  }
  if (link.branch === 'aware_faults' && !day.faults) {
    showNotice(`Failures are scripted for ${fmt.dateLabel(data.DEFAULT_DATE)} only; showing feeder-aware on ${label}.`);
    return { ...link, branch: 'aware' };
  }
  return link;
}


/** Where "Back to the story" goes: the story URL the reader came from (from=..., kept in sessionStorage so it survives
 *  the explorer's own tab links, which rebuild the query), else the story's first page. */
function storyBack() {
  const names = { configure: 'Configure', running: 'Run', run: 'Run', results: 'Results', learnings: 'Learnings' };
  let from = new URLSearchParams(location.search).get('from');
  try {
    if (from != null) sessionStorage.setItem('hb.storyFrom', from);
    else from = sessionStorage.getItem('hb.storyFrom');
  } catch { /* storage blocked: the Back link still opens the story */ }
  if (!from || !/^[\w=&%./,:+~-]*$/.test(from)) from = '';
  const page = new URLSearchParams(from).get('page');
  return { href: `index.html${from ? `?${from}` : ''}`, label: names[page] || 'the story' };
}

function header(link) {
  const tabs = [['p1', 'P1 · where to charge'], ['p2', 'P2 · where the next battery goes'], ['more', 'More']];
  const h = document.createElement('header');
  h.className = 'hb-header';
  const back = storyBack();
  h.innerHTML = `<div class="hb-row"><a class="hb-back" title="Back to the four-page story, where you left it">← Back to ${back.label}</a><div class="hb-brand"><img class="hb-mark" src="assets/batter-up-mark-256.png" alt="" width="24" height="30">Batter Up<small>Engine explorer</small></div>
    <nav class="hb-tabs">${tabs.map(([v, t]) => `<a href="${data.linkQuery({ view: v })}"${v === link.view ? ' aria-current="page"' : ''}>${t}</a>`).join('')}</nav>
    <div class="hb-standin">NREL SMART-DS 2018 AUS P1U: REAL dataset · synthetic feeder ${fmt.chip('REAL', FEEDER_CITE)}<br>Oncor-suburb stand-in settled at LZ_NORTH (placeholder) ${fmt.chip('ASSUMPTION', STANDIN_CITE)}</div></div>
    <div class="hb-explain">The full-control view of the same engine the story plays: every branch, every transformer and every labelled number on one screen. The four-page story (Configure → Run → Results → Learnings) is the guided tour of these same results.</div>`;
  h.querySelector('.hb-back').href = back.href;
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
  mountTips(document);
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
  link = await routeDate(link, panel);
  const ctx = {
    topology, footprints, link, scene, data, fmt, sceneModel, theme: theme(), reportError, showNotice,
    href: (patch) => data.linkQuery({ ...link, beat: null, ...patch }),
    go: (patch) => { location.search = data.linkQuery({ ...link, beat: null, ...patch }); },
  };
  await panel.mount(panelEl, ctx);
  // P1 beats get the caption bar from L5's more.js (P2 and More render their own). Namespace import + typeof guard:
  // a no-op until more.js exports mountBeatBar; a failure counts in data-errors instead of blanking the page.
  if (link.beat && link.view === 'p1') {
    try {
      const more = await import('./panels/more.js');
      if (typeof more.mountBeatBar === 'function') await more.mountBeatBar(ctx, panelEl);
    } catch (e) { reportError(e); }
  }
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
