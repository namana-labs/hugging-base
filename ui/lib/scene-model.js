// ui/lib/scene-model.js (L4, 3D + P1 view). PURE: maps (topology, footprints, frame, view, theme) to plain
// per-layer arrays. No DOM, no deck.gl, node-tested (ui/test/scene-model.test.js). scene3d.js feeds the arrays to
// deck.gl 9.4.0; fallback2d.js draws the same arrays top-down on a canvas. Build prompt 5.5.
//
// Exports (docs/contracts.md "Scene model"; L5 reuses them for the P2 view):
//   buildSceneModel({topology, footprints, frame, view, theme, pins?, placed?}) -> model
//     model.homes[1010]      {i, id, polygon, height, color, state, tf}     tinted by their transformer's tier
//     model.context[]        {polygon, height}                               unmatched OSM buildings (neutral)
//     model.batteries[96]    {j, home, position, height, soc, kw, state, color}      fill height = SoC
//     model.batteryGhosts[96]{j, position, height}                           full capacity (wireframe)
//     model.reserveRings[96] {j, position}                                   20% reserve marker (z = 20% of full)
//     model.cans[379]        {i, id, kva, position, radius, height, pct, code, color, focus, open}
//     model.canGhosts[379]   {i, position, radius, height}                  full height = 100% of nameplate
//     model.canRings[379]    {i, position, radius, pct:110}                 ring at 110% (normal rating)
//     model.canCaps[379]     {i, position, radius, pct:150}                 red cap at 150% (emergency rating)
//     model.lines[2531]      {path, color}                                  stable identity per topology+theme
//     model.labels[]         {text, short, position:[lon,lat,z], color, key} A-D (with room), T-240, pins; short at low zoom
//     model.pulses[]         {position, color}                              batteries whose command changed
//     model.alerts[]         {position, text:'!'}                           stale / expired batteries
//     model.staticKey        string: the home/context geometry is unchanged while this is unchanged
//   cameraPreset(topology, name)  -> {longitude, latitude, zoom, pitch, bearing}   name: feeder | street | t240
//   frameFromP1(branchDoc, k)     -> frame at step k (decodes the quantized contract arrays)
//   frameFromP2(comboDoc)         -> frame of month peaks (transformer fill = the month peak)
//   homeStatesAt(changes, k, n)   -> ['lit'|'battery'|'dark' x n] from p1 `homeState` (changes only)
//   roomKW(kva, pct, pKW)         -> kW of room to nameplate (DERIVED), negative when over
//   TIER_RGB[code], TIER_NAMES[code], STATE_NAMES
// Display scales (not data): CAN_H_M, BAT_H_M etc. The UI never re-derives tiers: codes come from the JSON.

export const TIER_RGB = [
  [12, 163, 12],    // 0 ok                                    --good
  [250, 178, 25],   // 1 over nameplate (>100%, amber)         --warn
  [236, 131, 90],   // 2 above 110%, run < 30 min (counting)   --serious
  [224, 96, 58],    // 3 normal rating exceeded (>=30 min): the headline violation
  [208, 59, 59],    // 4 emergency (>150%)                     --crit
  [107, 111, 108],  // 5 protection open (fuse rule, ASSUMPTION) --open
];
export const TIER_NAMES = [
  'within nameplate',
  'over nameplate (>100%, amber; not a violation)',
  'above 110%, counting (< 30 min)',
  'normal rating exceeded (>110% for >= 30 min)',
  'emergency (>150%)',
  'protection open (fuse rule, ASSUMPTION)',
];
export const STATE_NAMES = { C: 'charging', D: 'discharging', I: 'idle', S: 'stale (silent > 180 s)', X: 'expired: idle, backup armed', B: 'islanded on its own battery' };
export const ACCENT = [11, 107, 111];
export const ACCENT_DARK = [92, 196, 190];
export const INK = { light: [16, 22, 19], dark: [228, 235, 230] };
export const LINE = { light: [85, 98, 90, 140], dark: [147, 161, 152, 130] };
export const HOME_OK = { light: [132, 186, 132], dark: [62, 128, 74] };      // tier 0 homes: a soft green, not a shout
export const CONTEXT_RGB = { light: [196, 201, 193, 235], dark: [44, 52, 48, 235] };
export const DARK_HOME = [26, 28, 27];                                       // a home without power
export const BACKUP_GLOW = [255, 214, 120];                                  // a home lit by its own battery
export const BATTERY_RGB = { C: null /* accent */, D: [236, 131, 90], I: [140, 164, 146], S: [150, 150, 150], X: [150, 150, 150], B: [255, 196, 92] };

// display scales (metres in the 3D scene; not data)
export const CAN_H_M = 22;            // a can's ghost is this tall: 100% of nameplate
export const CAN_R_PER_SQRT_KVA = 0.95;
export const BAT_H_M = 12;            // a battery's ghost: full capacity
export const BAT_R_M = 1.7;
export const HOME_H_MIN_M = 6;
export const HOME_H_MAX_M = 9;
export const MISSING_SQUARE_M = 12;   // FOOTPRINT_MISSING_M (ASSUMPTION): a home with no OSM footprint
export const RESERVE_FRACTION = 0.20; // the member reserve (REAL, Base's 20%)
const M_PER_DEG = 6371008.8 * Math.PI / 180;

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

/** A tier code from a loading (percent) where no precomputed tier exists (P2 month peaks; display only). */
export function codeFromPct(p) {
  if (p > 150) return 4;
  if (p > 110) return 2;
  if (p > 100) return 1;
  return 0;
}

/** Deterministic 32-bit FNV-1a of a string. */
export function hash32(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}

/** A home's display height, 6-9 m, fixed per id. */
export function homeHeight(id) {
  return HOME_H_MIN_M + (hash32(String(id)) % 31) / 30 * (HOME_H_MAX_M - HOME_H_MIN_M);
}

/** A square of side `m` metres centred on [lon, lat], as a ring (not closed). */
export function squareRing(lonlat, m = MISSING_SQUARE_M) {
  const [lon, lat] = lonlat;
  const dy = (m / 2) / M_PER_DEG;
  const dx = (m / 2) / (M_PER_DEG * Math.cos(lat * Math.PI / 180));
  return [[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy], [lon - dx, lat + dy]];
}

/** Offset [lon, lat] by metres east / north. */
export function offsetM(lonlat, east, north) {
  const [lon, lat] = lonlat;
  return [lon + east / (M_PER_DEG * Math.cos(lat * Math.PI / 180)), lat + north / M_PER_DEG];
}

/** Quantized p1 `homeState` changes -> the state of every home at step k ('lit' unless a change says otherwise). */
export function homeStatesAt(changes, k, n) {
  const out = new Array(n).fill('lit');
  for (const c of changes || []) {
    if (c[0] > k) continue;
    if (c[1] >= 0 && c[1] < n) out[c[1]] = c[2];
  }
  return out;
}

/** kW of room to nameplate on a transformer (DERIVED; display only). With the transformer's real power P (kW):
 *  S = pct/100 * kVA, Q^2 = S^2 - P^2, room = sqrt(kVA^2 - Q^2) - P (unity-pf batteries, as the controller's
 *  caps at alpha = 1). Without P: kVA * (1 - pct/100). Negative when over nameplate. */
export function roomKW(kva, pct, pKW = null) {
  const S = (pct / 100) * kva;
  if (pKW === null || pKW === undefined || !Number.isFinite(pKW)) return kva - S;
  const q2 = Math.max(0, S * S - pKW * pKW);
  return Math.sqrt(Math.max(0, kva * kva - q2)) - pKW;
}

/** Frame at step k of a p1/<branch>.json (docs/contracts.md A.6). Decodes loading (pct x10), kW x10, SoC per mille. */
export function frameFromP1(doc, k) {
  const n = doc.loading.length;
  const kk = clamp(k | 0, 0, n - 1);
  const prev = Math.max(0, kk - 1);
  const focus = {};
  for (const [key, f] of Object.entries(doc.focus || {})) {
    focus[key] = { tf: f.tf, homeKW: f.homeKW[kk] / 10, batKW: f.batKW[kk] / 10 };
  }
  return {
    step: kk,
    loadingPct: doc.loading[kk].map((x) => x / 10),
    tier: Array.from(doc.tier[kk], Number),
    batKW: doc.batKW[kk].map((x) => x / 10),
    prevBatKW: doc.batKW[prev].map((x) => x / 10),
    soc: doc.soc[kk].map((x) => x / 1000),
    state: doc.state[kk],
    homeStateChanges: doc.homeState || [],
    focus,
  };
}

/** Frame of a p2/<combo>.json: transformer fill = the month peak (pct x10). */
export function frameFromP2(doc) {
  const pct = doc.baseline.peak.map((x) => x / 10);
  return { step: 0, loadingPct: pct, tier: pct.map(codeFromPct), batKW: null, prevBatKW: null, soc: null, state: null, homeStateChanges: [], focus: {} };
}

/** Camera presets (build prompt 5.5): whole feeder, street A-D (zoom ~18, pitch 55), Northbank T-240. */
export function cameraPreset(topology, name) {
  const tfs = topology.transformers;
  if (name === 'street') {
    const pts = (topology.focus || []).map((f) => tfs[f.tf].lonlat);
    const lon = pts.reduce((s, p) => s + p[0], 0) / (pts.length || 1);
    const lat = pts.reduce((s, p) => s + p[1], 0) / (pts.length || 1);
    return { longitude: lon, latitude: lat - 0.00022, zoom: 18, pitch: 55, bearing: -20 };
  }
  if (name === 't240') {
    const b = (topology.bridge || [])[0];
    const p = b ? tfs[b.tf].lonlat : tfs[0].lonlat;
    return { longitude: p[0], latitude: p[1] - 0.0003, zoom: 18, pitch: 52, bearing: 15 };
  }
  // the neighbourhood, not the long tail to the substation: the 2nd-98th percentile box of the homes
  const lons = topology.homes.map((h) => h.lonlat[0]).sort((a, b) => a - b);
  const lats = topology.homes.map((h) => h.lonlat[1]).sort((a, b) => a - b);
  const q = (a, p) => a[Math.min(a.length - 1, Math.max(0, Math.floor(p * a.length)))];
  return { longitude: (q(lons, 0.02) + q(lons, 0.98)) / 2, latitude: (q(lats, 0.02) + q(lats, 0.98)) / 2 - 0.0016, zoom: 15.0, pitch: 40, bearing: -12 };
}

// ---- static geometry, memoized per (topology, footprints, theme): stable identities let deck.gl skip re-tessellation
const STATIC = new WeakMap();

function ringExtent(ring) {
  let maxLon = -Infinity, sLat = 0;
  for (const p of ring) { if (p[0] > maxLon) maxLon = p[0]; sLat += p[1]; }
  return { maxLon, lat: sLat / ring.length };
}

export function staticScene(topology, footprints, theme = 'light') {
  let byFp = STATIC.get(topology);
  if (!byFp) { byFp = new Map(); STATIC.set(topology, byFp); }
  const fpKey = footprints || 'none';
  let byTheme = byFp.get(fpKey);
  if (!byTheme) { byTheme = new Map(); byFp.set(fpKey, byTheme); }
  if (byTheme.has(theme)) return byTheme.get(theme);

  const fpHomes = (footprints && footprints.homes) || {};
  let matched = 0;
  const homes = topology.homes.map((h, i) => {
    const ring = fpHomes[h.id];
    if (ring && ring.length >= 3) matched += 1;
    const polygon = ring && ring.length >= 3 ? ring : squareRing(h.lonlat);
    return { i, id: h.id, tf: h.tf, polygon, height: homeHeight(h.id), footprint: !!(ring && ring.length >= 3), battery: !!h.battery };
  });
  const ctxColor = CONTEXT_RGB[theme] || CONTEXT_RGB.light;
  const context = ((footprints && footprints.others) || []).filter((r) => r && r.length >= 3)
    .map((polygon, n) => ({ polygon, height: 3.5 + (n % 5) * 0.5, color: ctxColor }));
  const lc = LINE[theme] || LINE.light;
  const lines = (topology.edges || []).map((e) => ({ path: [[e[0], e[1]], [e[2], e[3]]], color: lc }));
  // a battery column stands just east of its home's footprint
  const batteryPos = (topology.fleet || []).map((hi) => {
    const { maxLon, lat } = ringExtent(homes[hi].polygon);
    return offsetM([maxLon, lat], 2.6, 0);
  });
  const canRadius = topology.transformers.map((t) => CAN_R_PER_SQRT_KVA * Math.sqrt(t.kva));
  const out = { homes, context, lines, batteryPos, canRadius, matched, key: `${topology.homes.length}:${matched}:${context.length}:${theme}` };
  byTheme.set(theme, out);
  return out;
}

function withAlpha(c, a) { return [c[0], c[1], c[2], a]; }

/** The scene for one frame. frame = null draws the feeder at rest (every can empty, every home lit). */
export function buildSceneModel({ topology, footprints = null, frame = null, view = 'p1', theme = 'light', pins = null, placed = null }) {
  const st = staticScene(topology, footprints, theme);
  const tfs = topology.transformers;
  const tier = frame && frame.tier ? frame.tier : tfs.map(() => 0);
  const pct = frame && frame.loadingPct ? frame.loadingPct : tfs.map(() => 0);
  const dim = view === 'more';
  const ink = INK[theme] || INK.light;
  const accent = theme === 'dark' ? ACCENT_DARK : ACCENT;
  const homeOk = HOME_OK[theme] || HOME_OK.light;
  const hs = frame ? homeStatesAt(frame.homeStateChanges, frame.step, topology.homes.length) : null;

  const homes = st.homes.map((h) => {
    const code = tier[h.tf] | 0;
    const state = hs ? hs[h.i] : 'lit';
    let c = code === 0 ? homeOk : (TIER_RGB[code] || TIER_RGB[0]);
    if (state === 'dark') c = DARK_HOME;
    else if (state === 'battery') c = BACKUP_GLOW;
    return { i: h.i, id: h.id, tf: h.tf, polygon: h.polygon, height: h.height, state, color: withAlpha(c, dim ? 110 : 245) };
  });

  const fleet = topology.fleet || [];
  const batteries = [], batteryGhosts = [], reserveRings = [], pulses = [], alerts = [];
  fleet.forEach((hi, j) => {
    const position = st.batteryPos[j];
    const soc = frame && frame.soc ? clamp(frame.soc[j], 0, 1) : 0;
    const s = frame && frame.state ? frame.state[j] : 'I';
    const kw = frame && frame.batKW ? frame.batKW[j] : 0;
    const col = s === 'C' ? accent : (BATTERY_RGB[s] || BATTERY_RGB.I);
    batteries.push({ j, home: hi, position, height: Math.max(0.3, BAT_H_M * soc), soc, kw, state: s, color: withAlpha(col, 255) });
    batteryGhosts.push({ j, position, height: BAT_H_M });
    reserveRings.push({ j, position: [position[0], position[1], BAT_H_M * RESERVE_FRACTION] });
    if (frame && frame.prevBatKW && Math.abs(kw - frame.prevBatKW[j]) > 0.5) pulses.push({ j, position, color: withAlpha(col, 200) });
    if (s === 'S' || s === 'X') alerts.push({ j, position: [position[0], position[1], BAT_H_M + 4], text: '!' });
  });
  for (const p of placed || []) {
    const h = topology.homes[p.home];
    if (!h) continue;
    const { maxLon, lat } = ringExtent(st.homes[p.home].polygon);
    const position = offsetM([maxLon, lat], 2.6, 0);
    batteries.push({ j: -1, home: p.home, position, height: BAT_H_M * 0.9, soc: 0.9, kw: 0, state: 'N', color: withAlpha(accent, 255), placed: true });
    batteryGhosts.push({ j: -1, position, height: BAT_H_M });
  }

  const cans = [], canGhosts = [], canRings = [], canCaps = [];
  const bridgeTf = new Set((topology.bridge || []).map((b) => b.tf));
  tfs.forEach((t, i) => {
    const code = tier[i] | 0;
    const radius = st.canRadius[i];
    const p = Math.max(0, pct[i] || 0);
    const open = code === 5;
    const c = TIER_RGB[code] || TIER_RGB[0];
    cans.push({ i, id: t.id, kva: t.kva, position: t.lonlat, radius, pct: p, code, open, focus: t.focus || null,
      height: open ? 0.4 : Math.max(0.4, CAN_H_M * p / 100), color: withAlpha(c, 255) });
    canGhosts.push({ i, position: t.lonlat, radius, height: CAN_H_M });
    // the 110% ring and the 150% cap only where they matter (named cans, or over nameplate now): less clutter
    if (t.focus || bridgeTf.has(i) || p > 100) {
      canRings.push({ i, position: [t.lonlat[0], t.lonlat[1], CAN_H_M * 1.1], radius: radius * 1.18, pct: 110 });
      canCaps.push({ i, position: [t.lonlat[0], t.lonlat[1], CAN_H_M * 1.5], radius: radius * 1.05, pct: 150 });
    }
  });

  const labels = [];
  for (const { key, tf: i } of topology.focus || []) {
    const t = tfs[i];
    const fd = frame && frame.focus ? frame.focus[key] : null;
    const pKW = fd ? fd.homeKW + fd.batKW : null;
    const room = roomKW(t.kva, pct[i] || 0, pKW);
    const p = pct[i] || 0;
    const roomTxt = !frame ? '' : p > 100 ? ` · over by ${((p / 100 - 1) * t.kva).toFixed(1)} kVA` : ` · room ${Math.max(0, room).toFixed(1)} kW`;
    labels.push({ key, short: key, text: `${key} · ${t.kva} kVA${roomTxt}`, position: [t.lonlat[0], t.lonlat[1], CAN_H_M * Math.max(1.55, (pct[i] || 0) / 100) + 6], color: ink, room });
  }
  for (const b of topology.bridge || []) {
    const t = tfs[b.tf];
    labels.push({ key: '240', short: 'T-240', text: `T-240 · ${t.kva} kVA · no battery`, position: [t.lonlat[0], t.lonlat[1], CAN_H_M * Math.max(1.55, (pct[b.tf] || 0) / 100) + 6], color: ink });
  }
  for (const p of pins || []) {
    const h = topology.homes[p.home];
    if (h) labels.push({ key: 'pin', short: String(p.text), text: String(p.text), position: [h.lonlat[0], h.lonlat[1], 16], color: ink, pin: true });
  }

  return {
    view, theme, step: frame ? frame.step : 0, staticKey: st.key, footprintsMatched: st.matched,
    homeGeom: st.homes, homes, context: st.context, batteries, batteryGhosts, reserveRings, pulses, alerts,
    cans, canGhosts, canRings, canCaps, lines: st.lines, labels, ink, accent,
  };
}
