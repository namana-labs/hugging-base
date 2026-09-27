// Chapter 1 control room (option 3a), driven by the simulator's replay.
// Layout and motion follow docs/design-handoff/README.md; every value on screen
// comes from data/replays/*.json (the feeder) and data/ems/freq-series.json (ERCOT).
import * as M from './dashboard-model.js';

const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const el = (t, a = {}, ...c) => { const n = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) n.setAttribute(k, v); for (const x of c) n.append(x); return n; };
const tok = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const COLOR = { healthy: 'var(--healthy)', tier1: 'var(--tier-1)', tier2: 'var(--tier-2)', tier3: 'var(--tier-3)' };
const TIER = ['var(--healthy)', 'var(--tier-1)', 'var(--tier-2)', 'var(--tier-3)'];
const DAY_MS = 20000;   // one simulated day at 1× (motion token --day-duration)
const q = new URLSearchParams(location.search);

const S = { replay: null, freq: null, ercot: null, policy: q.get('policy') === 'aware' ? 'aware' : 'naive', layer: q.get('layer') === 'voltage' ? 'voltage' : 'loading',
  h: +(q.get('t') || 0), day: 1, paused: q.has('paused'), speed: 1, phase: 0, lastStep: -1, ghostT: 0, stripe: 0, zoom: 1, last: 0, dirty: true, story: [], marks: [], layout: null, axes: {} };

// ---- loading ----------------------------------------------------------------

async function main() {
  const name = q.get('replay') || 'day';
  const [replay, freq] = await Promise.all([
    fetch(`../data/replays/${name}.json`, { cache: 'no-store' }).then(r => r.json()),
    fetch('../data/ems/freq-series.json', { cache: 'no-store' }).then(r => r.json()),
  ]);
  S.freq = freq; S.ercot = M.ercot(freq);
  setReplay(replay);
  wire();
  fit();
  S.last = performance.now();
  requestAnimationFrame(frame);
}

function setReplay(replay) {
  S.replay = replay;
  if (!replay.runs[S.policy]) S.policy = Object.keys(replay.runs)[0];
  S.layout = M.layout(replay.topology);
  buildBoard(); buildSystemCards(); buildTransport(); buildReactive(); buildVbus(); buildSheet();
  rebuildStory();
  const n = replay.topology.transformers.length, p = replay.params || {};
  $('scenario').textContent = replay.name === 'day' ? `Heat-wave evening · ${n}-node lateral` : `Mechanics test · ${n}-node lateral`;
  $('attrib-topo').textContent = `Topology: ${replay.topology.name} (hand-built, not SMART-DS)`;
  $('fleetSize').textContent = `Fleet size ${(n * (p.core_usable_kwh ?? 37)).toFixed(0)} kWh`;
  const reserve = p.reserve_floor ?? 0.2;
  $('batReserve').style.left = (reserve * 100) + '%';
  $('resLbl').style.left = `calc(${reserve * 100}% - 4px)`; $('resLbl').textContent = `↑ ${Math.round(reserve * 100)}% member reserve, never used`;
  $('lgReserve').textContent = Math.round(reserve * 100) + '%';
  $('reserveLine').setAttribute('y1', (96 - reserve * 88).toFixed(1)); $('reserveLine').setAttribute('y2', (96 - reserve * 88).toFixed(1));
  $('vbusUnit').textContent = `pu, ${n} transformer buses`;
  $('vbusName').textContent = replay.topology.name === 'four-node' ? 'Test lateral · four nodes' : `Test lateral · ${n} nodes`;
  S.h = Math.min(S.h, 23.999); S.lastStep = -1; S.dirty = true;
}

function rebuildStory() { S.story = M.story(S.replay, S.policy); S.marks = M.markers(S.story); buildMarkers(); buildTransport(); buildReactive(); S.lastStep = -1; S.dirty = true; }

// ---- board ------------------------------------------------------------------

function buildBoard() {
  const L = S.layout;
  const g = id => { const n = $(id); n.replaceChildren(); return n; };
  const svc = g('g-svc'), edges = g('g-edges'), homes = g('g-homes'), txs = g('g-txs'), labels = g('g-labels'), sub = g('g-sub');
  for (const s of L.svc) svc.append(el('line', { x1: s.x1, y1: s.y1, x2: s.x2, y2: s.y2, stroke: 'var(--service-drop)', 'stroke-width': 0.8 }));
  S.nE = L.edges.map(e => { const n = el('line', { x1: e.x1, y1: e.y1, x2: e.x2, y2: e.y2, stroke: 'var(--healthy)', 'stroke-width': e.w, 'stroke-linecap': 'round' }); edges.append(n); return [n, e]; });
  S.nH = L.homes.map(h => {
    const wrap = el('g', { transform: `translate(${h.x},${h.y})` });
    const use = el('use', { href: '#ic-house', x: -5.5, y: -5.5, width: 11, height: 11, 'stroke-width': 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
    wrap.append(use); homes.append(wrap);
    labels.append(el('text', { x: h.x, y: h.y + 20, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--muted)' }, `${h.label} · ${h.id}`));
    return [use, h];
  });
  S.nT = L.txs.map(t => {
    const wrap = el('g', { transform: `translate(${t.x},${t.y})` });
    const badge = el('g', { fill: 'var(--healthy)' });
    badge.append(el('rect', { x: -7, y: -7, width: 14, height: 14, rx: 3.5, stroke: 'var(--panel)', 'stroke-width': 1.5 }));
    badge.append(el('use', { href: '#ic-zap', x: -4.5, y: -4.5, width: 9, height: 9, fill: 'none', stroke: 'var(--panel)', 'stroke-width': 2.6, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    wrap.append(badge); txs.append(wrap);
    labels.append(el('text', { x: t.x, y: t.y - 14, 'text-anchor': 'middle', 'font-size': 11, 'font-weight': 700, fill: 'var(--ink)' }, `${t.id} · ${S.replay.topology.transformers[t.i].kva} kVA`));
    return [badge, t.i];
  });
  sub.append(el('rect', { x: L.sub.x - 12, y: L.sub.y - 12, width: 24, height: 24, rx: 5, fill: 'var(--ink)' }));
  sub.append(el('use', { href: '#ic-zap', x: L.sub.x - 8, y: L.sub.y - 8, width: 16, height: 16, fill: 'var(--panel)', stroke: 'var(--panel)', 'stroke-width': 1.5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
  sub.append(el('text', { x: L.sub.x, y: L.sub.y + 34, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 700, fill: 'var(--ink)' }, 'Substation'));
  sub.append(el('text', { x: L.sub.x, y: L.sub.y + 50, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--muted)' }, '12.47 kV · 1.03 pu'));
  // callouts: the far node is the weak point (long service drop), like the handoff's Mesquite Run
  const far = L.txs[L.txs.length - 1], tp = S.replay.topology;
  labels.append(el('text', { x: far.x + 40, y: 200, 'text-anchor': 'end', 'font-size': 15, 'font-weight': 700, fill: 'var(--ink)' }, 'Far end'));
  labels.append(el('text', { x: far.x + 40, y: 218, 'text-anchor': 'end', 'font-size': 12, fill: 'var(--muted)' }, `long service drop · ${(tp.homes[tp.homes.length - 1].distanceKm).toFixed(2)} km from the source`));
  labels.append(el('text', { x: L.sub.x - 12, y: 200, 'font-size': 15, 'font-weight': 700, fill: 'var(--ink)' }, `Test lateral · ${L.txs.length} nodes`));
  labels.append(el('text', { x: L.sub.x - 12, y: 218, 'font-size': 12, fill: 'var(--muted)' }, 'one Core and one rooftop PV per node · ASSUMPTION topology'));
  $('ring').setAttribute('cx', L.sub.x); $('ring').setAttribute('cy', L.sub.y); $('ring').setAttribute('stroke', 'var(--brand)');
  setZoom(1);
}

function setZoom(z) {
  S.zoom = Math.max(1, Math.min(4, z));
  const w = 1000 / S.zoom, h = 620 / S.zoom;
  $('board').setAttribute('viewBox', `${(500 - w / 2).toFixed(1)} ${(310 - h / 2).toFixed(1)} ${w.toFixed(1)} ${h.toFixed(1)}`);
}

// ---- system cards -----------------------------------------------------------

const SYS = [
  { key: 'freq', title: 'Frequency', unit: 'Hz', lo: 59.84, hi: 60.04, fmt: v => v.toFixed(3), tag: 'SOURCED', foot: 'ERCOT system · 25 Sep 2026', refs: e => [{ v: 60, stroke: 'var(--ink)', op: .25 }, { v: 60 + e.thresholds.deadband, dash: '3 3' }, { v: 60 - e.thresholds.deadband, dash: '3 3', label: `deadband ±${e.thresholds.deadband}`, at: 'bottom' }] },
  { key: 'rocof', title: 'RoCoF', unit: 'Hz/s', lo: -0.10, hi: 0.04, fmt: v => v.toFixed(3), tag: 'DERIVED', foot: '10-s extreme, from ERCOT frequency', refs: () => [{ v: 0, stroke: 'var(--ink)', op: .25 }] },
  { key: 'te', title: 'Time error', unit: 's', lo: -3, hi: 3, fmt: v => v.toFixed(2), tag: 'DERIVED', foot: 'integrated from ERCOT frequency', refs: () => [{ v: 0, stroke: 'var(--ink)', op: .25 }] },
  { key: 'prc', title: 'PRC', unit: 'MW', lo: 0, hi: 9000, fmt: v => (Math.round(v / 10) * 10).toLocaleString('en-US'), tag: 'SOURCED', foot: 'thresholds UNVERIFIED', area: true, refs: e => [{ v: e.thresholds.prcWatch, stroke: 'var(--tier-1)', dash: '4 3', label: 'Watch' }, { v: e.thresholds.prcEea1, stroke: 'var(--tier-2)', dash: '4 3' }] },
  { key: 'inert', title: 'Inertia', unit: 'GW·s', lo: 0, hi: 350, fmt: v => String(Math.round(v)), tag: 'SOURCED', foot: 'critical UNVERIFIED', refs: e => [{ v: e.thresholds.inertCritical, stroke: 'var(--tier-2)', dash: '4 3', label: 'critical' }] },
];

function buildSystemCards() {
  const e = S.ercot, root = $('sys'); root.replaceChildren(); S.sysCards = [];
  for (const c of SYS) {
    const vals = e.rows.map(r => r[c.key]).filter(v => v != null);
    const hi = c.key === 'prc' ? Math.max(c.hi, Math.ceil(Math.max(...vals) / 5000) * 5000) : c.hi;
    const card = document.createElement('div'); card.className = 'card';
    card.innerHTML = `<div class="hd"><span class="title">${c.title}</span><span class="unit">${c.unit}</span><span class="now">now <b>—</b></span></div>
      <div class="plot" data-scrub><svg viewBox="0 0 1000 100" preserveAspectRatio="none"><rect x="0" y="0" width="1000" height="100" fill="var(--plot-field)"></rect><g class="refs"></g><defs><clipPath id="clip-${c.key}"><rect class="clip" x="0" y="-10" width="0" height="120"></rect></clipPath></defs><g clip-path="url(#clip-${c.key})"><path class="area" fill="var(--sky-night)"></path><path class="line" fill="none" stroke="var(--ink)" stroke-width="1.3" vector-effect="non-scaling-stroke"></path></g></svg><div class="cursor"></div></div>
      <div class="ft"><span class="tag">${c.tag}</span>${c.foot}</div>`;
    const refs = card.querySelector('.refs');
    for (const r of c.refs(e)) {
      const y = M.yOf(r.v, c.lo, hi).toFixed(2);
      refs.append(el('line', { x1: 0, x2: 1000, y1: y, y2: y, stroke: r.stroke || 'var(--muted)', 'stroke-opacity': r.op ?? (r.dash ? .6 : 1), ...(r.dash ? { 'stroke-dasharray': r.dash } : {}), 'vector-effect': 'non-scaling-stroke' }));
      if (r.label) { const s = document.createElement('span'); s.className = 'lbl'; s.style.cssText = r.at === 'bottom' ? 'right:3px;bottom:2px' : `right:3px;top:calc(${y}% - 13px)`; s.textContent = r.label; card.querySelector('.plot').append(s); }
    }
    const d = M.seriesPath(e.rows.map(r => ({ h: r.h, v: r[c.key] })), c.lo, hi);
    card.querySelector('.line').setAttribute('d', d);
    if (c.area && d) card.querySelector('.area').setAttribute('d', d + `L${(e.minutes / 1440 * 1000).toFixed(1)},96L0,96Z`);
    root.append(card);
    S.sysCards.push({ c, now: card.querySelector('.now b') });
  }
}

// ---- transport, reactive, voltage by bus ----------------------------------------

function framePath(frames, get, lo, hi) { return M.seriesPath(frames.map(f => ({ h: f.minute / 60, v: get(f) })), lo, hi); }

function buildTransport() {
  const frames = S.replay.runs[S.policy];
  const kwMax = Math.max(5, Math.ceil(Math.max(...frames.map(f => Math.max(f.loadKW, f.solarKW))) * 1.1 / 5) * 5);
  S.axes.kw = kwMax;
  const ticks = $('hourTicks'); ticks.replaceChildren();
  for (const h of [0, 3, 6, 9, 12, 15, 18, 21, 24]) ticks.append(el('line', { x1: h / 24 * 1000, x2: h / 24 * 1000, y1: 0, y2: 100, stroke: 'var(--ink)', 'stroke-opacity': .08, 'vector-effect': 'non-scaling-stroke' }));
  const soc = M.seriesPath(frames.map(f => ({ h: f.minute / 60, v: M.fleetSoc(f) * 100 })), 0, 100 / 92 * 88 + 0 ) ;
  // fleet charge on the 0–100 % axis drawn to the same 8–96 box the prototype uses
  const socD = frames.map((f, i) => (i ? 'L' : 'M') + (f.minute / 60 / 24 * 1000).toFixed(1) + ',' + (96 - M.fleetSoc(f) * 88).toFixed(1)).join('');
  $('pSoc').setAttribute('d', socD); $('pSocArea').setAttribute('d', socD + 'L1000,96L0,96Z');
  const ym = kw => (96 - kw / kwMax * 88).toFixed(1);
  $('pLoad').setAttribute('d', frames.map((f, i) => (i ? 'L' : 'M') + (f.minute / 60 / 24 * 1000).toFixed(1) + ',' + ym(f.loadKW)).join(''));
  $('pSolar').setAttribute('d', frames.map((f, i) => (i ? 'L' : 'M') + (f.minute / 60 / 24 * 1000).toFixed(1) + ',' + ym(f.solarKW)).join(''));
  const top = frames.map(f => (f.minute / 60 / 24 * 1000).toFixed(1) + ',' + ym(Math.max(f.solarKW, f.loadKW)));
  const bot = frames.map(f => (f.minute / 60 / 24 * 1000).toFixed(1) + ',' + ym(f.loadKW));
  $('pExcess').setAttribute('d', 'M' + top.join('L') + 'L' + bot.reverse().join('L') + 'Z');
  void soc;
}

function buildMarkers() {
  const root = $('markers'); root.replaceChildren();
  let lastX = -1;
  for (const m of S.marks) {
    const x = m.h / 24 * 100; if (x - lastX < 4.5 && !m.violation) continue; lastX = x;
    const d = document.createElement('div'); d.className = 'mk' + (m.violation ? ' violation' : ''); d.style.left = x + '%';
    d.innerHTML = `<span>${m.label}</span>`; root.append(d);
  }
}

function buildReactive() {
  const frames = S.replay.runs[S.policy];
  const dem = f => f.feederKVAr + f.capKVAr + f.inverterKVAr;   // the feeder's own demand, before support
  const qmax = Math.max(2, Math.ceil(Math.max(...frames.map(f => Math.max(Math.abs(dem(f)), f.capKVAr + Math.max(0, f.inverterKVAr), Math.abs(Math.min(0, f.inverterKVAr))))) * 1.15));
  S.axes.q = qmax;
  // the reserve line only draws where it fits the axis; the legend always shows the value
  S.axes.reserveOffScale = Math.min(...frames.map(f => f.inverterKVArReserve)) > qmax;
  const lo = -qmax, hi = qmax, Y = v => M.yOf(v, lo, hi).toFixed(2), X = f => (f.minute / 60 / 24 * 1000).toFixed(1);
  $('qzero').setAttribute('y1', Y(0)); $('qzero').setAttribute('y2', Y(0));
  $('pQdem').setAttribute('d', framePath(frames, dem, lo, hi));
  $('pQres').setAttribute('d', S.axes.reserveOffScale ? '' : framePath(frames, f => f.inverterKVArReserve, lo, hi));
  const cap = frames.map(f => X(f) + ',' + Y(f.capKVAr)), inj = frames.map(f => X(f) + ',' + Y(f.capKVAr + Math.max(0, f.inverterKVAr))), abs = frames.map(f => X(f) + ',' + Y(Math.min(0, f.inverterKVAr)));
  const zero = frames.map(f => X(f) + ',' + Y(0));
  $('pQcap').setAttribute('d', 'M' + cap.join('L') + 'L' + zero.slice().reverse().join('L') + 'Z');
  $('pQinv').setAttribute('d', 'M' + inj.join('L') + 'L' + cap.slice().reverse().join('L') + 'Z');
  $('pQabs').setAttribute('d', 'M' + abs.join('L') + 'L' + zero.slice().reverse().join('L') + 'Z');
}

function buildVbus() {
  const svg = $('vbus'); svg.replaceChildren();
  const n = S.replay.topology.transformers.length;
  const yTop = M.yOf(1.05, 0.93, 1.07) * 1.5, yBot = M.yOf(0.95, 0.93, 1.07) * 1.5;  // 150-high box
  svg.append(el('rect', { x: 0, y: 28.6, width: 470, height: 92.8, fill: 'var(--band)' }));
  svg.append(el('line', { x1: 0, x2: 470, y1: 28.6, y2: 28.6, stroke: 'var(--tier-2)', 'stroke-dasharray': '4 3', 'vector-effect': 'non-scaling-stroke' }));
  svg.append(el('line', { x1: 0, x2: 470, y1: 121.4, y2: 121.4, stroke: 'var(--tier-2)', 'stroke-dasharray': '4 3', 'vector-effect': 'non-scaling-stroke' }));
  svg.append(el('line', { x1: 0, x2: 470, y1: 75, y2: 75, stroke: 'var(--ink)', 'stroke-opacity': .2, 'vector-effect': 'non-scaling-stroke' }));
  svg.append(el('rect', { x: 60, y: 0, width: 400, height: 150, fill: 'var(--ink)', 'fill-opacity': .04 }));
  S.vb = [];
  for (let i = 0; i < n; i++) {
    const x = 80 + i * (360 / Math.max(1, n - 1));
    const stem = el('line', { x1: x, x2: x, y1: 75, y2: 75, stroke: 'var(--healthy)', 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke' });
    const dot = el('circle', { cx: x, cy: 75, r: 3.6, fill: 'var(--healthy)' });
    svg.append(stem, dot); S.vb.push([stem, dot]);
  }
  void yTop; void yBot;
}

// ---- sources sheet ----------------------------------------------------------

async function buildSheet() {
  const r = S.replay;
  $('provTable').innerHTML = Object.entries(r.provenance || {}).map(([k, v]) => `<tr><td><b>${k}</b></td><td>${v}</td></tr>`).join('') + `<tr><td><b>engine</b></td><td>${r.engine} · generated ${r.generatedAt} in ${r.buildSeconds} s</td></tr>`;
  let schema = null;
  try { const x = await fetch('/api/params', { cache: 'no-store' }); if (x.ok) schema = (await x.json()).schema; } catch { /* static mode */ }
  const labels = Object.fromEntries((schema || []).map(k => [k.name, k]));
  $('paramTable').innerHTML = Object.entries(r.params || {}).map(([k, v]) => { const m = labels[k]; return `<tr><td>${m ? m.label : k}</td><td>${Array.isArray(v) ? v.join(', ') : v === null ? 'default' : v}${m && m.unit ? ' <span class="muted">' + m.unit + '</span>' : ''}</td><td><span class="tag">${m ? m.tag : ''}</span></td></tr>`; }).join('');
  $('rerun').disabled = !schema;
  $('rerunStatus').textContent = schema ? 'Live: the local server can rerun OpenDSS with these parameters.' : 'Static replay. Start `python -m sim.server` to rerun live.';
  const e = S.freq;
  $('ercotNote').textContent = `${e.title}. ${e.status_legend.REAL} shown as SOURCED; RoCoF and time error are ${e.status_legend.DERIVED}. PRC and inertia thresholds stay UNVERIFIED until checked against the ERCOT documents the file cites. The series covers ${Math.floor(S.ercot.minutes / 60)} h ${S.ercot.minutes % 60} min of the day; the rest is a gap, not zero.`;
}

async function rerun() {
  $('rerunStatus').textContent = 'Running…';
  try {
    const r = await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario: S.replay.name === 'day' ? 'day' : 'mechanics', params: S.replay.params }) });
    const d = await r.json(); if (!r.ok || d.error) throw new Error(d.error || r.statusText);
    setReplay(d); $('rerunStatus').textContent = `Reran in ${d.buildSeconds} s · ${d.steps} steps`;
  } catch (err) { $('rerunStatus').textContent = 'Error: ' + err.message; }
}

// ---- wiring -----------------------------------------------------------------

function wire() {
  document.querySelectorAll('[data-policy]').forEach(b => b.onclick = () => { S.policy = b.dataset.policy; document.querySelectorAll('[data-policy]').forEach(x => x.setAttribute('aria-pressed', x === b)); rebuildStory(); });
  document.querySelectorAll('[data-layer]').forEach(b => b.onclick = () => { S.layer = b.dataset.layer; document.querySelectorAll('[data-layer]').forEach(x => x.setAttribute('aria-pressed', x === b)); $('legend-loading').hidden = S.layer !== 'loading'; $('legend-voltage').hidden = S.layer !== 'voltage'; S.dirty = true; });
  document.querySelectorAll('[data-speed]').forEach(b => b.onclick = () => { S.speed = +b.dataset.speed; document.querySelectorAll('[data-speed]').forEach(x => x.setAttribute('aria-pressed', x === b)); });
  $('play').onclick = () => { S.paused = !S.paused; $('play').textContent = S.paused ? '▶' : '❚❚'; };
  $('restart').onclick = () => seek(0);
  document.querySelectorAll('[data-scrub], #scrub').forEach(n => n.addEventListener('click', e => { const r = n.getBoundingClientRect(); seek(M.clamp((e.clientX - r.left) / r.width, 0, 0.999) * 24); }));
  $('zin').onclick = () => setZoom(S.zoom * 1.5); $('zout').onclick = () => setZoom(S.zoom / 1.5); $('zreset').onclick = () => setZoom(1);
  $('sources').onclick = () => $('sheet').setAttribute('open', ''); $('sheetClose').onclick = () => $('sheet').removeAttribute('open');
  $('sheet').addEventListener('click', e => { if (e.target === $('sheet')) $('sheet').removeAttribute('open'); });
  $('rerun').onclick = rerun;
  document.querySelectorAll('[data-policy]').forEach(x => x.setAttribute('aria-pressed', x.dataset.policy === S.policy));
  document.querySelectorAll('[data-layer]').forEach(x => x.setAttribute('aria-pressed', x.dataset.layer === S.layer));
  $('legend-loading').hidden = S.layer !== 'loading'; $('legend-voltage').hidden = S.layer !== 'voltage';
  $('play').textContent = S.paused ? '▶' : '❚❚';
  window.addEventListener('resize', fit);
  window.addEventListener('keydown', e => { if (e.key === ' ') { e.preventDefault(); $('play').click(); } if (e.key === 'ArrowRight') seek(Math.min(23.999, S.h + 0.25)); if (e.key === 'ArrowLeft') seek(Math.max(0, S.h - 0.25)); });
}

function fit() { const s = Math.min(window.innerWidth / 1600, window.innerHeight / 900); $('frame').style.transform = `scale(${s.toFixed(4)})`; }

// Seeking sets the hour directly: tiers and counters are the replay's, judged by the simulator at each step.
function seek(h) { S.h = h; S.lastStep = -1; S.dirty = true; }

// ---- loop -------------------------------------------------------------------

function frame(now) {
  const dt = Math.min(50, now - S.last); S.last = now;
  if (!S.paused) advance(dt / DAY_MS * 24 * S.speed, now);
  paint(now);
  requestAnimationFrame(frame);
}

function advance(dh, now) {
  const fl = M.fleet(S.replay, S.policy, S.h);
  // beats per minute follow normalised fleet power (motion tokens: 40 + 80·|P|)
  S.phase += (M.PULSE.minBpm + M.PULSE.rangeBpm * fl.pn) / 60 * (dh / 24 * DAY_MS / 1000);
  let h1 = S.h + dh;
  if (h1 >= 24) {   // midnight: new day, yesterday's charge curve stays as a fading ghost
    h1 -= 24; S.day++; S.ghostT = now;
    $('pSocG').setAttribute('d', $('pSoc').getAttribute('d')); $('pSocAreaG').setAttribute('d', $('pSocArea').getAttribute('d'));
    S.lastStep = -1;
  }
  S.h = h1;
}

function paint(now) {
  const R = S.replay, frames = R.runs[S.policy], h = S.h, L = S.layout;
  const fl = M.fleet(R, S.policy, h), { pn, dir } = fl, amp = 0.25 + 0.75 * pn, ph = S.phase;
  const volt = S.layer === 'voltage';
  const lag = dn => (dir > 0 ? dn : 1 - dn) * M.PULSE.travel;
  // board field: day ↔ night
  const nmix = M.night(h);
  const day = [239, 236, 227], dusk = [208, 211, 204];   // --board and --board-dusk
  $('field').setAttribute('fill', 'rgb(' + day.map((a, i) => Math.round(M.lerp(a, dusk[i], nmix))).join(',') + ')');
  // heartbeat along the lines
  for (const [n, e] of S.nE) { const p = Math.min(1, M.pulse(ph - lag(e.dn))) * amp; n.setAttribute('stroke-opacity', (0.45 + 0.55 * p).toFixed(2)); n.setAttribute('stroke-width', (e.w * (1 + 0.55 * p)).toFixed(2)); }
  const f = fl.frame, tiers = M.tierCodes(f);
  const txP = L.txs.map(t => Math.min(1, M.pulse(ph - lag(t.dn))));
  for (const [badge, i] of S.nT) { const rr = 5.5 + [0.6 * amp, 1.6, 3.4, 3.8][tiers[i]] * txP[i]; badge.setAttribute('transform', `scale(${(1 + (rr - 5.5) / 9).toFixed(3)})`); badge.setAttribute('fill', volt ? 'var(--neutral-tx)' : TIER[tiers[i]]); }
  if (!volt) for (const [n, hm] of S.nH) { const k = txP[hm.tx] * amp; n.setAttribute('transform', `scale(${(1 + 0.3 * k).toFixed(3)})`); }
  const x = ph - Math.floor(ph);
  $('ring').setAttribute('r', (dir > 0 ? 12 + 34 * x : 46 - 34 * x).toFixed(1));
  $('ring').setAttribute('opacity', x < 0.7 ? (0.6 * amp * (dir > 0 ? 1 - x / 0.7 : x / 0.7)).toFixed(2) : '0');
  // cursors and reveals
  const pct = (h / 24 * 100).toFixed(3) + '%';
  document.querySelectorAll('.cursor').forEach(n => n.style.left = pct);
  document.querySelectorAll('.clip').forEach(n => n.setAttribute('width', (h / 24 * 1000).toFixed(2)));
  $('cursorT').style.left = pct; $('headT').style.left = pct; $('headT').style.top = (96 - fl.soc * 88).toFixed(2) + '%';
  // battery body
  const pp = Math.min(1, M.pulse(ph)) * amp, bw = (fl.soc * 100).toFixed(2) + '%';
  $('batFill').style.width = bw;
  S.stripe = (S.stripe + dir * (0.15 + 1.1 * pn)) % 3700;
  const st = $('batStripe'); st.style.width = bw; st.style.backgroundPosition = S.stripe.toFixed(1) + 'px 0'; st.style.opacity = (0.3 + 0.7 * pn).toFixed(2);
  $('batEdge').style.left = bw; $('batEdge').style.opacity = (0.3 + 0.7 * pp).toFixed(2);
  if (S.ghostT) { const o = 0.9 * (1 - (now - S.ghostT) / 4000); $('ghost').setAttribute('opacity', Math.max(0, o).toFixed(3)); if (o <= 0) S.ghostT = 0; }
  // text and tiers change only on market steps (decision 2 in the README)
  if (fl.k !== S.lastStep || S.dirty) {
    S.lastStep = fl.k; S.dirty = false;
    $('clock').textContent = f.clock; $('stepLabel').textContent = `Step ${fl.k + 1} of ${fl.n}`; $('day').textContent = `Day ${S.day}`;
    $('lgLoad').textContent = f.loadKW.toFixed(1); $('lgSolar').textContent = f.solarKW.toFixed(1);
    const socR = Math.round(fl.socStep * 100); $('lgSoc').textContent = String(socR); $('socPct').textContent = socR + '%';
    const kw = Math.abs(f.fleetKW).toFixed(1);
    $('flow').textContent = Math.abs(f.fleetKW) < 0.5 ? 'Holding' : f.fleetKW > 0 ? `Charging +${kw} kW` : `Discharging −${kw} kW`;
    [0, 1, 2, 3].forEach(k => $('n' + k).textContent = String(tiers.filter(t => t === k).length));
    // voltage by bus
    const vs = f.tfVoltage; $('minv').textContent = Math.min(...vs).toFixed(3);
    S.vb.forEach(([stem, dot], i) => { const y = (140 - (M.clamp(vs[i], 0.93, 1.07) - 0.93) / 0.14 * 130).toFixed(1); stem.setAttribute('y2', y); dot.setAttribute('cy', y); stem.setAttribute('stroke', COLOR[M.busVoltageColor(vs[i])]); dot.setAttribute('fill', COLOR[M.busVoltageColor(vs[i])]); });
    // reactive legend
    $('vQ').textContent = (f.feederKVAr + f.capKVAr + f.inverterKVAr).toFixed(1) + ' kvar'; $('vQres').textContent = f.inverterKVArReserve.toFixed(1) + ' kvar' + (S.axes.reserveOffScale ? ' (off scale)' : '');
    // system cards
    const row = M.ercotAt(S.ercot, h);
    for (const { c, now: n } of S.sysCards) n.textContent = row[c.key] == null ? 'no data' : c.fmt(row[c.key]);
    // story
    const s = M.storyAt(S.story, h); if (s) { $('storyTime').textContent = s.t; $('storyText').textContent = s.s; }
    // homes
    for (const [n, hm] of S.nH) {
      if (volt) { const v = f.voltage[hm.i]; n.setAttribute('fill', COLOR[M.homeVoltageColor(v)]); n.setAttribute('stroke', 'var(--ink)'); n.setAttribute('transform', 'scale(1.1)'); }
      else { n.setAttribute('fill', M.homeFill(f.soc[hm.id], hm.off, R.params?.reserve_floor ?? 0.2)); n.setAttribute('stroke', 'var(--brand)'); }
    }
  }
}

main().catch(err => { document.body.insertAdjacentHTML('afterbegin', `<p style="padding:20px;color:var(--tier-2)">Could not load the replay: ${err.message}</p>`); console.error(err); });
