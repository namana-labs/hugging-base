// Pure data model for the Chapter 1 dashboard (docs/design-handoff/README.md).
// No DOM here: everything is a function of the replay, the ERCOT series and the
// simulated hour, so `node --test ui/test/` can check it. Numbers come from the
// simulator's frames; nothing here chooses a dispatch.

export const STEPS_PER_HOUR = 12;           // 5-minute market steps
export const STEP_MINUTES = 5;

// Design values that are not tokens (handoff README, Feeder board and Motion).
export const HOME_EMPTY_RGB = [190, 208, 193];   // battery home when empty
export const BRAND_RGB = [30, 77, 43];           // #1e4d2b, battery home when full
export const PULSE = { lub: 0.07, dubOffset: 0.24, dubGain: 0.55, travel: 0.55, minBpm: 40, rangeBpm: 80 };

export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
export const clock = h => { const m = Math.floor(((h % 24) + 24) % 24 * 60 + 1e-6); return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); };

// Lub-dub heartbeat, x in beats.
export function pulse(x) {
  x -= Math.floor(x);
  const a = x > 0.75 ? x - 1 : x;
  return Math.exp(-((a / PULSE.lub) ** 2)) + PULSE.dubGain * Math.exp(-(((a - PULSE.dubOffset) / PULSE.lub) ** 2));
}

// Board field mix: 0 = day, 1 = night. Transitions 05:00→07:30 and 18:30→21:00.
export function night(h) {
  h = ((h % 24) + 24) % 24;
  if (h < 5) return 1;
  if (h < 7.5) return 1 - smoothstep((h - 5) / 2.5);
  if (h < 18.5) return 0;
  if (h < 21) return smoothstep((h - 18.5) / 2.5);
  return 1;
}

// ---- frames -----------------------------------------------------------------

export function stepAt(h, n) {
  const x = clamp(h, 0, 24) * STEPS_PER_HOUR;
  const k = Math.min(n - 1, Math.floor(x));
  return { k, t: k === n - 1 ? 0 : x - k, k2: Math.min(n - 1, k + 1) };
}

export const fleetSoc = f => { const v = Object.values(f.soc); return v.reduce((a, b) => a + b, 0) / v.length; };

// A scalar from a frame, by key or accessor, interpolated between steps.
export function sample(frames, h, get) {
  const g = typeof get === 'string' ? f => f[get] : get;
  const { k, t, k2 } = stepAt(h, frames.length);
  return lerp(g(frames[k]), g(frames[k2]), t);
}

// Tier code per transformer, from the referee's tier string and its sustained list.
// 0 inside limits, 1 over nameplate (counted), 2 above 110 % for the window, 3 above emergency.
export function tierCodes(f) {
  return f.tier.map((s, i) => s === 'emergency' ? 3
    : (s === 'normal_exceeded' && f.sustainedViolations.includes(i)) ? 2
    : s === 'ok' ? 0 : 1);
}

export const homeVoltageColor = v => v < 0.95 ? 'tier2' : v < 0.96 ? 'tier1' : 'healthy';
export const busVoltageColor = v => v > 1.05 ? 'tier3' : v < 0.95 ? 'tier2' : (v < 0.96 || v > 1.04) ? 'tier1' : 'healthy';

export function homeFill(soc, offset, reserve = 0.2) {
  const t = clamp((soc - reserve) / (1 - reserve) + offset, 0, 1);
  return 'rgb(' + HOME_EMPTY_RGB.map((a, i) => Math.round(lerp(a, BRAND_RGB[i], t))).join(',') + ')';
}

// Deterministic per-home colour offset (±0.08) from its index; no Math.random in the demo.
export const homeOffset = i => (((i * 9301 + 49297) % 233280) / 233280 - 0.5) * 0.16;

// ---- layout -----------------------------------------------------------------

// Places the replay's lateral in the 1000×620 board: substation left, trunk along
// y=330, one transformer badge per node spaced by electrical distance, its home
// hung below on a service drop. Works for any node count.
export function layout(topology) {
  const nodes = topology.transformers.map((t, i) => ({ id: t.id, i, x: t.coordinates[0] }));
  const maxX = Math.max(...nodes.map(n => n.x), 0.001);
  // The trunk starts right of the legend overlay and ends left of the inset.
  const X = x => 380 + (x / maxX) * 520, Y = 300;
  const sub = { x: 300, y: Y };
  const txs = nodes.map(n => ({ i: n.i, id: n.id, x: +X(n.x).toFixed(1), y: Y, dn: n.x / maxX }));
  let prev = sub, d = 0;
  const edges = txs.map((t, i) => { const e = { i, x1: prev.x, y1: prev.y, x2: t.x, y2: t.y, w: 4.2, d, dn: t.dn }; d += t.x - prev.x; prev = t; return e; });
  const homes = topology.homes.map((h, i) => {
    const t = txs[h.tf];
    const drop = 60 + 60 * (h.distanceKm - topology.transformers[h.tf].coordinates[0]) / 0.09; // long drop hangs lower
    return { i, id: h.id, tx: h.tf, x: t.x, y: +(t.y + drop).toFixed(1), bat: true, pv: h.pvKW > 0, label: h.label, off: homeOffset(i) };
  });
  const svc = homes.map(h => ({ x1: h.x, y1: txs[h.tx].y, x2: h.x, y2: h.y }));
  return { sub, txs, edges, homes, svc };
}

// ---- ERCOT system series ----------------------------------------------------

// One-minute ERCOT series mapped onto the 24-hour clock; missing minutes are null.
export function ercot(freq) {
  const s = freq.series_1min, n = s.n;
  const at = (arr, i) => (i < n && arr[i] != null) ? arr[i] : null;
  const rows = [];
  for (let i = 0; i < 24 * 60; i++) {
    rows.push({
      h: i / 60,
      freq: at(s.f_mean_hz, i),
      rocof: at(s.rocof10_extreme_hz_per_s, i),
      te: at(s.time_error_s, i),
      prc: at(s.prc_mean_mw, i),
      inert: at(s.inertia_mws, i) == null ? null : s.inertia_mws[i] / 1000,   // MW·s → GW·s
    });
  }
  const c = freq.constants;
  return {
    rows, minutes: n,
    thresholds: { deadband: c.governor_deadband_hz, prcWatch: c.prc_thresholds_mw.watch, prcEea1: c.prc_thresholds_mw.eea1, inertCritical: c.critical_inertia_mws / 1000 },
    label: freq.title,
  };
}

export function ercotAt(e, h) {
  const i = clamp(Math.floor(h * 60), 0, 24 * 60 - 1);
  return e.rows[i];
}

// ---- paths ------------------------------------------------------------------

// SVG path for a series in the 1000×100 plot box; y from lo..hi, nulls break the line.
export function seriesPath(points, lo, hi, x = p => p.h / 24 * 1000) {
  let d = '', pen = false;
  for (const p of points) {
    if (p.v == null) { pen = false; continue; }
    const y = 96 - (clamp(p.v, lo, hi) - lo) / (hi - lo) * 92;
    d += (pen ? 'L' : 'M') + x(p).toFixed(1) + ',' + y.toFixed(2);
    pen = true;
  }
  return d;
}

export const yOf = (v, lo, hi) => 96 - (clamp(v, lo, hi) - lo) / (hi - lo) * 92;

// ---- story ------------------------------------------------------------------

const pct = v => Math.round(v * 100) + '%';

// Timestamped sentences derived from the replay itself: phase changes, the bank,
// the fleet reaching full or the reserve, the referee's flags, and device events.
export function story(replay, policy) {
  const frames = replay.runs[policy];
  if (!frames) return [];
  const p = replay.params || {}, reserve = p.reserve_floor ?? 0.2;
  const split = policy === 'aware' ? 'nearest-first on charge, farthest-first on discharge' : 'split evenly';
  const out = [];
  const add = (f, s, kind = 'story') => out.push({ h: f.minute / 60, t: f.clock, s, kind });
  const f0 = frames[0];
  add(f0, `Night. The fleet holds about ${pct(fleetSoc(f0))}. Every transformer sits inside its nameplate (its rated size).`
    + (f0.phase === 'cheap charge' ? ` Cheap overnight power at $${f0.price}/MWh (ASSUMPTION): batteries top up slowly.` : ''));
  let phase = f0.phase, prevPhase = null, full = false, atReserve = false, cap = f0.capOn, sustained = false, volt = false;
  for (const f of frames) {
    if (f.phase !== phase) {
      prevPhase = phase; phase = f.phase;
      const soc = fleetSoc(f);
      if (phase === 'cheap charge' && soc < 0.99) add(f, (f.hour < 7 || f.hour > 20)
        ? `Cheap overnight power ($${f.price}/MWh, ASSUMPTION). Batteries top up slowly.`
        : `Cheap midday price ($${f.price}/MWh, ASSUMPTION). Batteries keep topping up.`, 'marker');
      if (phase === 'solar soak') add(f, 'Solar passes household load. Batteries soak up the excess.', 'marker');
      if (phase === 'peak discharge') add(f, `LZ_NORTH price rises to $${f.price}/MWh (ASSUMPTION). The fleet discharges, ${split}.`, 'marker');
      if (phase === 'idle') add(f, prevPhase === 'peak discharge' ? 'Load eases. The fleet holds what is left.' : f.hour < 12 ? 'Morning ramp. Load rises as homes wake up; the fleet waits for the price to move.' : 'Solar fades. The fleet waits for the evening price.', 'marker');
    }
    if (!full && fleetSoc(f) >= 0.995) { full = true; add(f, `The fleet is full at ${f.clock}; the rest of the solar goes to the grid.`); }
    if (f.capOn !== cap) { cap = f.capOn; add(f, cap ? `Capacitor bank closes: feeder-head VAr demand passed ${(f.feederKVAr + f.capKVAr).toFixed(1)} kvar.` : 'Capacitor bank opens again as VAr demand falls.'); }
    if (!sustained && f.sustainedViolations.length) { sustained = true; add(f, `${f.sustainedViolations.map(i => 'tf' + (i + 1)).join(', ')} crosses normal rating: above 110% for the full window.`, 'violation'); }
    if (!volt && f.voltageViolations) { volt = true; const i = f.voltageMax.findIndex(v => v > 1.05); add(f, i >= 0 ? `Node ${i + 1} rises above 1.05 pu (voltage as a share of nominal) on export.` : 'A home sags below 0.95 pu (voltage as a share of nominal).', 'violation'); }
    if (!atReserve && phase === 'peak discharge') {
      const units = Object.values(f.soc), low = units.filter(v => v <= reserve + 0.005).length;
      if (low) { atReserve = true; add(f, low === units.length ? `The fleet stops at the ${pct(reserve)} member reserve, never used.`
        : `${low} of ${units.length} units at the ${pct(reserve)} member reserve; the rest carry the base point.`); }
    }
    for (const e of f.events) add(f, e.replace(/^(h\d+) /, (m, u) => `Node ${u.slice(1)} (${u}) `), 'event');
  }
  return out.sort((a, b) => a.h - b.h || (a.kind === 'story' ? -1 : 1));
}

export function storyAt(list, h) {
  let i = 0;
  list.forEach((s, j) => { if (h >= s.h) i = j; });
  return list[i];
}

// Event markers for the transport: phase changes and the first violation.
export const markers = list => list.filter(s => s.kind === 'marker' || s.kind === 'violation' || s.kind === 'event').map(s => ({
  h: s.h, label: s.kind === 'violation' ? 'Normal rating' : s.kind === 'event' ? s.s.split(':')[0] : s.s.split('.')[0].replace(/ \(.*?\)/, ''), violation: s.kind === 'violation',
}));

// ---- fleet ------------------------------------------------------------------

export function fleet(replay, policy, h) {
  const frames = replay.runs[policy], { k } = stepAt(h, frames.length), f = frames[k];
  const p = replay.params || {}, n = frames[0].loading.length;
  const capKW = n * (p.core_power_kw ?? 20), kwh = n * (p.core_usable_kwh ?? 37);
  const power = sample(frames, h, 'fleetKW');
  return { soc: sample(frames, h, fleetSoc), socStep: fleetSoc(f), power, pn: clamp(Math.abs(power) / capKW, 0, 1), dir: power >= 0 ? 1 : -1, capKW, kwh, frame: f, k, n: frames.length };
}
