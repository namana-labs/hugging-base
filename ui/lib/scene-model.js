// ui/lib/scene-model.js -- OWNED BY L4 (3D + P1 view). This is L0's STUB: plain columns, enough for the shell.
// PURE: maps (topology, footprints, frame, view) to plain per-layer arrays; no DOM, no deck.gl. Node-testable.
// L4 replaces the body and keeps these exports (docs/contracts.md "Scene API"):
//   buildSceneModel({topology, footprints, frame, view, theme}) -> {homes[], batteries[], cans[], lines[], labels[]}
//   cameraPreset(topology, name)  -> {longitude, latitude, zoom, pitch, bearing}     name: feeder | street | t240
//   TIER_RGB[code] -> [r,g,b]      codes 0-5 as in p1/<branch>.json `tier`
//   frameFromP1(branchDoc, k)      -> frame at step k;  frameFromP2(comboDoc) -> frame of month peaks

export const TIER_RGB = [
  [12, 163, 12],    // 0 ok        --good
  [250, 178, 25],   // 1 amber     --warn
  [236, 131, 90],   // 2 >110% counting --serious
  [236, 131, 90],   // 3 normal violation
  [208, 59, 59],    // 4 emergency --crit
  [107, 111, 108],  // 5 protection open
];
export const ACCENT = [11, 107, 111];
export const INK = { light: [16, 22, 19], dark: [228, 235, 230] };
export const LINE = { light: [85, 98, 90, 150], dark: [147, 161, 152, 150] };

/** A tier code from a loading (percent) when no precomputed tier string exists (display only). */
export function codeFromPct(p) {
  if (p > 150) return 4;
  if (p > 110) return 2;
  if (p > 100) return 1;
  return 0;
}

/** Frame at step k of a p1/<branch>.json. loading is int tenths of a percent. */
export function frameFromP1(doc, k) {
  const kk = Math.max(0, Math.min(doc.loading.length - 1, k | 0));
  return {
    loadingPct: doc.loading[kk].map((x) => x / 10),
    tier: Array.from(doc.tier[kk], Number),
    batKW: doc.batKW[kk].map((x) => x / 10),
    soc: doc.soc[kk].map((x) => x / 1000),
    state: doc.state[kk],
    step: kk,
  };
}

/** Frame of a p2/<combo>.json: transformer fill = the month peak (int tenths). */
export function frameFromP2(doc) {
  const pct = doc.baseline.peak.map((x) => x / 10);
  return { loadingPct: pct, tier: pct.map(codeFromPct), batKW: null, soc: null, state: null, step: 0 };
}

export function cameraPreset(topology, name) {
  const tfs = topology.transformers;
  const byKey = (k) => (topology.focus || []).find((f) => f.key === k);
  if (name === 'street') {
    const pts = (topology.focus || []).map((f) => tfs[f.tf].lonlat);
    const lon = pts.reduce((s, p) => s + p[0], 0) / (pts.length || 1);
    const lat = pts.reduce((s, p) => s + p[1], 0) / (pts.length || 1);
    return { longitude: lon, latitude: lat, zoom: 17.6, pitch: 55, bearing: -20 };
  }
  if (name === 't240') {
    const b = (topology.bridge || [])[0];
    const p = b ? tfs[b.tf].lonlat : tfs[0].lonlat;
    return { longitude: p[0], latitude: p[1], zoom: 17.8, pitch: 50, bearing: 15 };
  }
  let lo = [180, 90], hi = [-180, -90];
  for (const h of topology.homes) {
    lo = [Math.min(lo[0], h.lonlat[0]), Math.min(lo[1], h.lonlat[1])];
    hi = [Math.max(hi[0], h.lonlat[0]), Math.max(hi[1], h.lonlat[1])];
  }
  void byKey;
  return { longitude: (lo[0] + hi[0]) / 2, latitude: (lo[1] + hi[1]) / 2, zoom: 14.6, pitch: 40, bearing: -15 };
}

/** The stub model: homes as short columns tinted by their transformer's tier, cans as columns whose height is loading. */
export function buildSceneModel({ topology, footprints = null, frame = null, view = 'p1', theme = 'light' }) {
  void footprints;
  const tfs = topology.transformers;
  const tier = frame && frame.tier ? frame.tier : tfs.map(() => 0);
  const pct = frame && frame.loadingPct ? frame.loadingPct : tfs.map(() => 0);
  const dim = view === 'more';
  const homes = topology.homes.map((h, i) => {
    const c = TIER_RGB[tier[h.tf]] || TIER_RGB[0];
    return { i, id: h.id, position: h.lonlat, height: h.battery ? 9 : 6, color: dim ? [...c, 110] : [...c, 235], tf: h.tf };
  });
  const batteries = (topology.fleet || []).map((hi, j) => {
    const h = topology.homes[hi];
    const soc = frame && frame.soc ? frame.soc[j] : 0.5;
    const s = frame && frame.state ? frame.state[j] : 'I';
    const col = s === 'C' ? ACCENT : s === 'D' ? TIER_RGB[2] : s === 'S' || s === 'X' ? [150, 150, 150] : [140, 160, 145];
    return { j, position: [h.lonlat[0] + 0.00012, h.lonlat[1]], height: 4 + 26 * soc, color: [...col, 255] };
  });
  const cans = tfs.map((t, i) => {
    const c = TIER_RGB[tier[i]] || TIER_RGB[0];
    return { i, id: t.id, position: t.lonlat, radius: 2.4 * Math.sqrt(t.kva), height: Math.max(2, 1.2 * pct[i]), color: [...c, 255], focus: t.focus };
  });
  const lc = LINE[theme] || LINE.light;
  const lines = (topology.edges || []).map((e) => ({ path: [[e[0], e[1]], [e[2], e[3]]], color: lc }));
  const labels = tfs.filter((t) => t.focus).map((t) => ({ text: t.focus, position: t.lonlat, color: INK[theme] || INK.light }));
  for (const b of topology.bridge || []) labels.push({ text: 'T-240', position: tfs[b.tf].lonlat, color: INK[theme] || INK.light });
  return { homes, batteries, cans, lines, labels };
}
