// ui/lib/scene-model.js (L4, 3D + P1 view). PURE: maps (topology, footprints, frame, view, theme) to plain
// per-layer arrays. No DOM, no deck.gl, node-tested (ui/test/scene-model.test.js). scene3d.js feeds the arrays to
// deck.gl 9.4.0; fallback2d.js draws the same arrays top-down on a canvas. Build prompt 5.5; UX_SPEC_R2 6.1.
//
// Round 2 (RZ: "houses more realistic; transformers must look like transformers; batteries instantly distinguishable"):
//   walls      extruded real OSM footprints, 3.3 m or 6.0 m (display, ASSUMPTION), neutral wall palette
//   roofs      a hip roof over the exact footprint (hipRoof: ridge on the minimum-area box's long axis), triangles with
//              baked Lambert shading; tinted by the transformer's tier ONLY when that tier is >= 1 (roofColor)
//   tfs        379 transformers, each `mount` 'pad' | 'pole' (topology field, DERIVED from SMART-DS secondary linecodes;
//              'pad' when absent): pads = plinth + green box, poles = pole + crossarm + grey can. Colour never changes
//              with load; load shows as the meter icon, the ground halo and the service drops.
//   meters     billboard load meters (icons.js meterId: box = 100% of nameplate, sticking out = over) on A-D, T-240 and
//              any transformer at tier >= 1
//   halos      a ground ring under every transformer at tier >= 1 (radius in metres with a pixel minimum)
//   drops      one service drop per home, pole -> eave (overhead) or pad -> wall (ground); tier colour when tier >= 1
//   cabinets   a white Base battery cabinet with a teal cap beside each fleet home, on the wall nearest its transformer
//              (placement ASSUMPTION, display); `batteries` = the battery icon above it (fill = SoC, colour + glyph = state)
//   pulses     a one-step ring on each battery whose command changed by more than 0.5 kW
//   worst      "worst now {pct}%" above the worst transformer's meter: the only number in the scene (+ its label tag)
//   labels     "A", "B", "C", "D", "T-240" (and P2 pins); `batteries` keeps `placed` entries for P2
// Static geometry (walls, roofs, pads, poles, cabinets, drops, lines) is memoized per (topology, footprints, theme), so
// deck.gl never re-tessellates it; per step only meters, battery icons, halos, drop colours, pulses and worst change.
// The UI never re-derives tiers: codes come from the JSON.
import { batteryId, meterId, TIER_RGB as ICON_TIER_RGB, STATE_RGB as ICON_STATE_RGB, TIER_WORDS as ICON_TIER_WORDS, STATE_WORDS as ICON_STATE_WORDS } from './icons.js';

export const TIER_RGB = ICON_TIER_RGB;       // [0] is sage: green never means "safe" (UX_SPEC_R2 2.1)
export const STATE_RGB = ICON_STATE_RGB;
export const TIER_WORDS = ICON_TIER_WORDS;
export const STATE_WORDS = ICON_STATE_WORDS;
/** Longer tier names (tooltips, tests). The plain word is TIER_WORDS; the exact rule is icons.js TIER_TIPS. */
export const TIER_NAMES = [
  'within its rating (at or under 100% of nameplate)',
  'over nameplate (100-110%; not a violation)',
  'above 110%, clock running (< 30 min)',
  'normal rating exceeded (> 110% for >= 30 min)',
  'emergency (> 150%)',
  'fuse open (fuse rule, ASSUMPTION)',
];
export const STATE_NAMES = STATE_WORDS;
export const ACCENT = [11, 107, 111];
export const ACCENT_DARK = [92, 196, 190];
export const INK = { light: [16, 22, 19], dark: [228, 235, 230] };
export const LINE = { light: [85, 98, 90, 110], dark: [147, 161, 152, 110] };
export const CONTEXT_RGB = { light: [214, 216, 210, 255], dark: [52, 58, 55, 255] };
export const DARK_HOME = [40, 42, 44];                                        // walls of a home without power
export const BACKUP_GLOW = [255, 214, 120];                                   // walls of a home lit by its own battery
// neutral palettes (UX-R2-scene 3.1): red, amber and green belong to the tiers, so no terracotta roofs or green walls
export const WALL_RGB = [[226, 214, 190], [205, 186, 160], [214, 208, 192], [181, 116, 92], [188, 196, 176], [176, 188, 196], [232, 226, 212]];
export const ROOF_RGB = [[74, 76, 80], [104, 88, 74], [96, 104, 114], [120, 112, 102], [86, 80, 76], [132, 126, 118]];
export const PAD_RGB = [62, 98, 68];          // pad-mount green (RZ asked for it); never changes with load
export const PLINTH_RGB = [184, 184, 178];
export const POLE_RGB = [118, 98, 78];
export const CAN_RGB = [168, 176, 180];
export const CABINET_RGB = [240, 242, 238];
export const CAP_RGB = [11, 107, 111];
const DARK_FACTOR = 0.72;                     // dark theme: every neutral palette x 0.72

// display scales (metres; not data)
export const WALL_H_ONE = 3.3;
export const WALL_H_TWO = 6.0;
export const TWO_STOREY_SHARE = 3;            // hash32(id) % 10 >= 7: 30% two-storey (display, ASSUMPTION)
export const ROOF_RISE_MAX_M = 3.2;
export const ROOF_PITCH = 0.42;               // rise = min(3.2, 0.42 x W/2)
export const MISSING_SQUARE_M = 12;           // FOOTPRINT_MISSING_M (ASSUMPTION): a home with no OSM footprint
export const PAD_M = [3.6, 3.0, 2.4];         // pad box L x W x H, about 2.5x real size ("not to scale")
export const PLINTH_M = [4.0, 3.4, 0.25];
export const POLE_H_M = 10.5;
export const CAN_Z_M = 6.8;
export const METER_Z = { pad: 3.2, pole: 11 };
export const CABINET_M = [2.2, 1.1, 2.4];
export const HALO_M = 7;
export const PULSE_KW = 0.5;                  // a command change this big rings the battery for one step
export const RESERVE_FRACTION = 0.20;         // the member reserve (REAL, Base's 20%)
const M_PER_DEG = 6371008.8 * Math.PI / 180;
const SUN = (() => { const v = [-0.45, -0.55, 0.7]; const n = Math.hypot(...v); return v.map((x) => x / n); })();

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

/** A home's wall height: one storey (3.3 m) or two (6.0 m), fixed per id (display, ASSUMPTION). */
export function wallHeight(id) {
  return hash32(String(id)) % 10 >= 10 - TWO_STOREY_SHARE ? WALL_H_TWO : WALL_H_ONE;
}
export const homeHeight = wallHeight;

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
/** [lon, lat] -> metres east/north of origin o. */
export const toM = (p, o) => [(p[0] - o[0]) * M_PER_DEG * Math.cos(o[1] * Math.PI / 180), (p[1] - o[1]) * M_PER_DEG];
/** metres east/north of o -> [lon, lat, z]. */
export const toLL = (m, o, z = 0) => [o[0] + m[0] / (M_PER_DEG * Math.cos(o[1] * Math.PI / 180)), o[1] + m[1] / M_PER_DEG, z];

/** Convex hull (Andrew's monotone chain) of [x, y] points. */
export function hull(pts) {
  const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const x of p) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], x) <= 0) lo.pop(); lo.push(x); }
  for (const x of p.reverse()) { while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], x) <= 0) up.pop(); up.push(x); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}

/** Minimum-area oriented box of [x, y] points (hull + rotating calipers): {c:[x,y], u:[ux,uy] long axis, L, W}, L >= W. */
export function obb(pts) {
  const h = hull(pts);
  let best = null;
  for (let i = 0; i < h.length; i++) {
    const a = h[i], b = h[(i + 1) % h.length], ang = Math.atan2(b[1] - a[1], b[0] - a[0]), c = Math.cos(ang), s = Math.sin(ang);
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const p of h) { const x = p[0] * c + p[1] * s, y = -p[0] * s + p[1] * c; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    const ar = (x1 - x0) * (y1 - y0);
    if (!best || ar < best.ar) best = { ar, c, s, x0, x1, y0, y1 };
  }
  const { c, s, x0, x1, y0, y1 } = best;
  let u = [c, s], L = x1 - x0, W = y1 - y0;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, C = [cx * c - cy * s, cx * s + cy * c];
  if (W > L) { u = [-s, c]; [L, W] = [W, L]; }
  return { c: C, u, L, W };
}

function unitNormal(a, b, c) {
  const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  let n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
  const l = Math.hypot(...n) || 1;
  n = n.map((x) => x / l);
  return n[2] < 0 ? n.map((x) => -x) : n;
}
/** Lambert factor for a face normal (baked, so the 2D fallback is identical and deck lighting never matters). */
export const lambert = (n) => 0.62 + 0.5 * Math.max(0, n[0] * SUN[0] + n[1] * SUN[1] + n[2] * SUN[2]);
const shadeRGB = (col, f) => [Math.min(255, col[0] * f) | 0, Math.min(255, col[1] * f) | 0, Math.min(255, col[2] * f) | 0, 255];

const cross3 = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
const signedArea = (P) => { let a = 0; for (let i = 0; i < P.length; i++) { const p = P[i], q = P[(i + 1) % P.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; };
const triAreaXY = (t) => Math.abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[2][0] - t[0][0]) * (t[1][1] - t[0][1])) / 2;

/** Ear-clipping triangulation of a simple CCW polygon (local metres): [[i, j, k]] index triples. */
export function earClip(P) {
  const idx = P.map((_, i) => i);
  const tris = [];
  const inTri = (p, a, b, c) => cross3(a, b, p) > 1e-9 && cross3(b, c, p) > 1e-9 && cross3(c, a, p) > 1e-9;
  let guard = 0;
  while (idx.length > 3 && guard++ < 4 * P.length * P.length) {
    let clipped = false;
    for (let a = 0; a < idx.length; a++) {
      const i0 = idx[(a + idx.length - 1) % idx.length], i1 = idx[a], i2 = idx[(a + 1) % idx.length];
      if (cross3(P[i0], P[i1], P[i2]) <= 1e-9) continue;
      if (idx.some((j) => j !== i0 && j !== i1 && j !== i2 && inTri(P[j], P[i0], P[i1], P[i2]))) continue;
      tris.push([i0, i1, i2]);
      idx.splice(a, 1);
      clipped = true;
      break;
    }
    if (!clipped) {   // only degenerate (collinear) corners left: drop the flattest one
      let best = 0, bv = Infinity;
      for (let a = 0; a < idx.length; a++) { const v = Math.abs(cross3(P[idx[(a + idx.length - 1) % idx.length]], P[idx[a]], P[idx[(a + 1) % idx.length]])); if (v < bv) { bv = v; best = a; } }
      idx.splice(best, 1);
    }
  }
  if (idx.length === 3) tris.push(idx.slice());
  return tris;
}

/** Hertel-Mehlhorn: merge ear-clip triangles across shared edges while the union stays convex. CCW index lists. */
export function convexPieces(P) {
  let pieces = earClip(P).map((t) => t.slice());
  const convex = (Q) => Q.every((_, i) => cross3(P[Q[i]], P[Q[(i + 1) % Q.length]], P[Q[(i + 2) % Q.length]]) >= -1e-6);
  const merge = (A, B) => {
    for (let i = 0; i < A.length; i++) {
      const u = A[i], v = A[(i + 1) % A.length], j = B.indexOf(v);
      if (j >= 0 && B[(j + 1) % B.length] === u) {
        const out = [];
        for (let t = 0; t < A.length; t++) out.push(A[(i + 1 + t) % A.length]);
        for (let t = 2; t < B.length; t++) out.push(B[(j + t) % B.length]);
        return out;
      }
    }
    return null;
  };
  let changed = true;
  while (changed) {
    changed = false;
    outer: for (let a = 0; a < pieces.length; a++) {
      for (let b = a + 1; b < pieces.length; b++) {
        const m = merge(pieces[a], pieces[b]);
        if (m && convex(m)) { pieces[a] = m; pieces.splice(b, 1); changed = true; break outer; }
      }
    }
  }
  return pieces;
}

/** Hip faces over one CCW ring (local metres): the ridge on the minimum-area box's long axis, every eave vertex joined to
 *  its clamped projection on the ridge. Returns {faces, rise, box, folded} (folded: the faces over-cover the ring). */
function hipFaces(P, wallH) {
  const box = obb(P);
  const h = Math.max(0, (box.L - box.W) / 2), rise = Math.min(ROOF_RISE_MAX_M, ROOF_PITCH * box.W / 2);
  const R = P.map((p) => {
    const t = clamp((p[0] - box.c[0]) * box.u[0] + (p[1] - box.c[1]) * box.u[1], -h, h);
    return [box.c[0] + box.u[0] * t, box.c[1] + box.u[1] * t];
  });
  const faces = [];
  let cover = 0;
  for (let i = 0; i < P.length; i++) {
    const j = (i + 1) % P.length;
    const a = [P[i][0], P[i][1], wallH], b = [P[j][0], P[j][1], wallH], rj = [R[j][0], R[j][1], wallH + rise], ri = [R[i][0], R[i][1], wallH + rise];
    for (const t of [[a, b, rj], [a, rj, ri]]) {
      const ar = triAreaXY(t);
      if (ar < 5e-4) continue;   // degenerate in plan: skip
      cover += ar;
      faces.push({ m: t, n: unitNormal(...t) });
    }
  }
  const area = Math.abs(signedArea(P));
  return { faces, rise, box, folded: cover > area * 1.001 + 0.01 };
}

/** A pyramid over a convex ring (never folds): every edge joined to the centroid at wallH + rise. */
function pyramidFaces(P, wallH) {
  const box = obb(P), rise = Math.min(ROOF_RISE_MAX_M, ROOF_PITCH * box.W / 2);
  const c = P.reduce((s, p) => [s[0] + p[0] / P.length, s[1] + p[1] / P.length], [0, 0]);
  const top = [c[0], c[1], wallH + rise];
  const faces = [];
  for (let i = 0; i < P.length; i++) {
    const j = (i + 1) % P.length, t = [[P[i][0], P[i][1], wallH], [P[j][0], P[j][1], wallH], top];
    if (triAreaXY(t) >= 5e-4) faces.push({ m: t, n: unitNormal(...t) });
  }
  return faces;
}

/**
 * Hip roof over a footprint ring ([lon, lat] points), in local metres about the ring's centroid (UX-R2-scene 3.1):
 *   ridge = c +- u * max(0, (L - W) / 2) of the minimum-area box, at wallH + min(3.2, 0.42 * W / 2); every eave vertex
 *   joins its clamped projection on the ridge; edge (pi, pj) -> triangles (pi, pj, rj), (pi, rj, ri).
 * On a concave footprint that single ridge can fold (triangles over-cover the ring, so they z-fight or overhang); there
 * the footprint is split into convex pieces (ear clipping + Hertel-Mehlhorn) and each piece gets its own hip (a pyramid
 * if even that folds), so the roof covers the exact footprint with no overlap. Returns {faces:[{m:[[x,y,z] x3], n}],
 * rise, box, o, P, pieces}.
 */
export function hipRoof(ring, wallH) {
  const o = ring.reduce((s, p) => [s[0] + p[0] / ring.length, s[1] + p[1] / ring.length], [0, 0]);
  let P = ring.map((p) => toM(p, o));
  if (P.length > 3 && Math.hypot(P[0][0] - P[P.length - 1][0], P[0][1] - P[P.length - 1][1]) < 0.01) P.pop();
  // drop repeated and flat corners (OSM rings carry some), then orient counter-clockwise
  P = P.filter((p, i) => Math.hypot(p[0] - P[(i + 1) % P.length][0], p[1] - P[(i + 1) % P.length][1]) > 0.05);
  for (let changed = true; changed && P.length > 3;) {
    changed = false;
    for (let i = 0; i < P.length && P.length > 3; i++) {
      const a = P[(i + P.length - 1) % P.length], b = P[i], c = P[(i + 1) % P.length];
      if (Math.abs(cross3(a, b, c)) < 0.02 * Math.hypot(c[0] - a[0], c[1] - a[1])) { P.splice(i, 1); changed = true; break; }
    }
  }
  if (signedArea(P) < 0) P.reverse();
  const whole = hipFaces(P, wallH);
  if (!whole.folded) return { faces: whole.faces, rise: whole.rise, box: whole.box, o, P, pieces: 1 };
  const faces = [];
  const pieces = convexPieces(P);
  for (const idx of pieces) {
    const Q = idx.map((i) => P[i]);
    const hf = hipFaces(Q, wallH);
    faces.push(...(hf.folded ? pyramidFaces(Q, wallH) : hf.faces));
  }
  return { faces, rise: whole.rise, box: whole.box, o, P, pieces: pieces.length };
}

/** Area of a ring in local metres (shoelace), for tests. */
export function ringAreaM(P) {
  let a = 0;
  for (let i = 0; i < P.length; i++) { const p = P[i], q = P[(i + 1) % P.length]; a += p[0] * q[1] - q[0] * p[1]; }
  return Math.abs(a) / 2;
}

/** Nearest point of a local-metre ring to point t: {X, u (wall direction), d}. */
function nearestOnRing(P, t) {
  let best = null;
  for (let a = 0; a < P.length; a++) {
    const A = P[a], B = P[(a + 1) % P.length], dx = B[0] - A[0], dy = B[1] - A[1], L2 = dx * dx + dy * dy || 1;
    const s = clamp(((t[0] - A[0]) * dx + (t[1] - A[1]) * dy) / L2, 0, 1), X = [A[0] + dx * s, A[1] + dy * s];
    const d = Math.hypot(X[0] - t[0], X[1] - t[1]);
    if (!best || d < best.d) best = { d, X, u: [dx / Math.sqrt(L2), dy / Math.sqrt(L2)] };
  }
  return best;
}

/** A rectangle (len along u, wid across) centred on cM (local metres about o), as a [lon, lat, z] ring. */
function boxRing(cM, u, len, wid, o, z = 0) {
  const v = [-u[1], u[0]], hl = len / 2, hw = wid / 2;
  return [[1, 1], [-1, 1], [-1, -1], [1, -1]].map(([a, b]) => toLL([cM[0] + u[0] * hl * a + v[0] * hw * b, cM[1] + u[1] * hl * a + v[1] * hw * b], o, z));
}

/** Where a battery cabinet stands (display, ASSUMPTION): on the wall nearest the home's transformer (where the service
 *  entrance and meter usually are), 1.3 m out from the wall and 3 m along it, long side parallel to the wall. */
export function cabinetSpot(ring, tfLonLat) {
  const o = ring.reduce((s, p) => [s[0] + p[0] / ring.length, s[1] + p[1] / ring.length], [0, 0]);
  const P = ring.map((p) => toM(p, o));
  const near = nearestOnRing(P, toM(tfLonLat, o));
  const n = Math.hypot(near.X[0], near.X[1]) || 1;
  const cM = [near.X[0] + near.X[0] / n * 1.3 + near.u[0] * 3, near.X[1] + near.X[1] / n * 1.3 + near.u[1] * 3];
  return { o, cM, u: near.u, entry: near.X, P };
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

/** kW of export (back-feed) room to nameplate (DERIVED; display only): with P < 0, E = sqrt(kVA^2 - Q^2) + P
 *  (the controller's export headroom at alpha = 1, build prompt 5.4.3 step 2). Negative when over nameplate. */
export function exportRoomKW(kva, pct, pKW) {
  const S = (pct / 100) * kva;
  const q2 = Math.max(0, S * S - pKW * pKW);
  return Math.sqrt(Math.max(0, kva * kva - q2)) + pKW;
}

/** The room in the direction power flows now: a transformer whose real power P is negative is back-feeding, so its
 *  headroom is export room (judge R1 F6). Without P: charge. */
export function headroom(kva, pct, pKW = null) {
  if (pKW !== null && pKW !== undefined && Number.isFinite(pKW) && pKW < 0) return { dir: 'export', kw: exportRoomKW(kva, pct, pKW) };
  return { dir: 'charge', kw: roomKW(kva, pct, pKW) };
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
  const lab = doc.series && doc.series.loading && doc.series.loading.label;
  return {
    step: kk,
    loadingPct: doc.loading[kk].map((x) => x / 10),
    tier: Array.from(doc.tier[kk], Number),
    tierKey: doc.tier[kk],
    loadingLabel: lab || 'SIM',
    batKW: doc.batKW[kk].map((x) => x / 10),
    prevBatKW: doc.batKW[prev].map((x) => x / 10),
    soc: doc.soc[kk].map((x) => x / 1000),
    state: doc.state[kk],
    homeStateChanges: doc.homeState || [],
    focus,
  };
}

/** Frame of a p2/<combo>.json: transformer loading = the month peak (pct x10); no battery state. */
export function frameFromP2(doc) {
  const pct = doc.baseline.peak.map((x) => x / 10);
  const tier = pct.map(codeFromPct);
  return { step: 0, loadingPct: pct, tier, tierKey: tier.join(''), loadingLabel: 'SIM', batKW: null, prevBatKW: null, soc: null, state: null, homeStateChanges: [], focus: {}, noWorst: true };
}

/** Camera presets (build prompt 5.5): whole feeder, street A-D (zoom ~18, pitch 55), T-240. */
export function cameraPreset(topology, name) {
  const tfs = topology.transformers;
  if (name === 'street') {
    const pts = (topology.focus || []).map((f) => tfs[f.tf].lonlat);
    const lon = pts.reduce((s, p) => s + p[0], 0) / (pts.length || 1);
    const lat = pts.reduce((s, p) => s + p[1], 0) / (pts.length || 1);
    return { longitude: lon - 0.0006, latitude: lat - 0.00022, zoom: 18, pitch: 55, bearing: -20 };
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

/** The named transformers: {tf -> "A".."D" | "T-240"}. */
export function namedTfs(topology) {
  const m = new Map((topology.focus || []).map((f) => [f.tf, f.key]));
  for (const b of topology.bridge || []) if (!m.has(b.tf)) m.set(b.tf, `T-${b.tf}`);
  return m;
}

/** A transformer's mount: the topology's `mount` field (DERIVED from SMART-DS; l0), else 'pad'. */
export const mountOf = (t) => (t && t.mount === 'pole' ? 'pole' : 'pad');

// ---- static geometry, memoized per (topology, footprints, theme): stable identities let deck.gl skip re-tessellation
const STATIC = new WeakMap();
const dim = (c, theme) => (theme === 'dark' ? c.map((x, i) => (i < 3 ? Math.round(x * DARK_FACTOR) : x)) : c);

export function staticScene(topology, footprints, theme = 'light') {
  let byFp = STATIC.get(topology);
  if (!byFp) { byFp = new Map(); STATIC.set(topology, byFp); }
  const fpKey = footprints || 'none';
  let byTheme = byFp.get(fpKey);
  if (!byTheme) { byTheme = new Map(); byFp.set(fpKey, byTheme); }
  if (byTheme.has(theme)) return byTheme.get(theme);

  const tfs = topology.transformers;
  const fpHomes = (footprints && footprints.homes) || {};
  const fleetIdx = new Map((topology.fleet || []).map((hi, j) => [hi, j]));
  let matched = 0;
  const walls = [], roofs = [], drops = [];
  const spots = new Array((topology.fleet || []).length);
  topology.homes.forEach((h, i) => {
    const fp = fpHomes[h.id];
    const real = !!(fp && fp.length >= 3);
    if (real) matched += 1;
    const polygon = real ? fp : squareRing(h.lonlat);
    const height = wallHeight(h.id);
    walls.push({ i, home: i, id: h.id, tf: h.tf, polygon, height, footprint: real, battery: fleetIdx.has(i), color: dim([...WALL_RGB[hash32(h.id) % WALL_RGB.length], 255], theme) });
    const r = hipRoof(polygon, height);
    const base = dim(ROOF_RGB[hash32(h.id + 'r') % ROOF_RGB.length], theme);
    for (const f of r.faces) {
      const shade = lambert(f.n);
      roofs.push({ home: i, tf: h.tf, poly: f.m.map((m) => toLL(m, r.o, m[2])), shade, base, color: shadeRGB(base, shade) });
    }
    // service drop: transformer -> the footprint point nearest to it (overhead from a pole, on the ground from a pad)
    const t = tfs[h.tf];
    const pole = mountOf(t) === 'pole';
    const P = r.P;
    const near = nearestOnRing(P, toM(t.lonlat, r.o));
    drops.push({ home: i, tf: h.tf, path: [[t.lonlat[0], t.lonlat[1], pole ? 7.2 : 0.4], toLL(near.X, r.o, pole ? height - 0.4 : 0.2)] });
    if (fleetIdx.has(i)) spots[fleetIdx.get(i)] = cabinetSpot(polygon, t.lonlat);
  });
  const cabinets = [], caps = [], iconPos = [];
  spots.forEach((sp, j) => {
    const hi = topology.fleet[j];
    cabinets.push({ j, home: hi, polygon: boxRing(sp.cM, sp.u, CABINET_M[0], CABINET_M[1], sp.o), height: CABINET_M[2] });
    caps.push({ j, home: hi, polygon: boxRing(sp.cM, sp.u, CABINET_M[0] + 0.1, CABINET_M[1] + 0.1, sp.o, CABINET_M[2]), height: 0.3 });
    iconPos.push(toLL(sp.cM, sp.o, CABINET_M[2] + 0.5));
  });

  const names = namedTfs(topology);
  const pads = [], plinths = [], poles = [], cans = [], arms = [];
  const tfList = tfs.map((t, i) => {
    const o = t.lonlat, mount = mountOf(t);
    if (mount === 'pole') {
      poles.push({ i, position: [o[0], o[1], 0] });
      cans.push({ i, position: toLL([1.0, 0], o, CAN_Z_M) });
      arms.push({ i, path: [toLL([-1.6, 0], o, POLE_H_M - 0.4), toLL([1.6, 0], o, POLE_H_M - 0.4)] });
    } else {
      plinths.push({ i, polygon: boxRing([0, 0], [1, 0], PLINTH_M[0], PLINTH_M[1], o), height: PLINTH_M[2] });
      pads.push({ i, polygon: boxRing([0, 0], [1, 0], PAD_M[0], PAD_M[1], o, PLINTH_M[2]), height: PAD_M[2] });
    }
    return { i, id: t.id, kva: t.kva, position: o, mount, key: names.get(i) || null, meterPos: [o[0], o[1], METER_Z[mount]] };
  });
  const ctxColor = CONTEXT_RGB[theme] || CONTEXT_RGB.light;
  const context = ((footprints && footprints.others) || []).filter((r) => r && r.length >= 3).map((polygon) => ({ polygon, height: WALL_H_ONE, color: ctxColor }));
  const lc = LINE[theme] || LINE.light;
  const lines = (topology.edges || []).map((e) => ({ path: [[e[0], e[1]], [e[2], e[3]]], color: lc }));
  const out = {
    walls, roofs, drops, cabinets, caps, iconPos, tfs: tfList, pads, plinths, poles, cans, arms, context, lines, matched,
    colors: { pad: dim(PAD_RGB, theme), plinth: dim(PLINTH_RGB, theme), pole: dim(POLE_RGB, theme), can: dim(CAN_RGB, theme), cabinet: dim(CABINET_RGB, theme), cap: CAP_RGB },
    key: `${topology.homes.length}:${matched}:${context.length}:${theme}:${pads.length}`,
  };
  byTheme.set(theme, out);
  return out;
}

/** A roof triangle's colour for its transformer's tier code: the baked neutral when tier 0, else
 *  0.8 x TIER_RGB[tier] x shade + 0.2 x base, so a stressed street reads as coloured roofs at every zoom. */
export function roofColor(face, code) {
  if (!code) return face.color;
  const t = TIER_RGB[code] || TIER_RGB[0], s = face.shade;
  return [
    Math.min(255, t[0] * s * 0.8 + face.base[0] * 0.2) | 0,
    Math.min(255, t[1] * s * 0.8 + face.base[1] * 0.2) | 0,
    Math.min(255, t[2] * s * 0.8 + face.base[2] * 0.2) | 0, 255];
}

/** A service drop's colour and width (px) for its transformer's tier code. */
export function dropStyle(code, ink = INK.light) {
  if (!code) return { color: [ink[0], ink[1], ink[2], 120], width: 1.2 };
  const t = TIER_RGB[code] || TIER_RGB[0];
  return { color: [t[0], t[1], t[2], 235], width: code >= 2 ? 3.5 : 2.5 };
}

function withAlpha(c, a) { return [c[0], c[1], c[2], a]; }
const NONE = Object.freeze([]);

/** The index of the worst transformer in a loading array. */
export function worstIndex(pct) {
  let w = 0;
  for (let i = 1; i < pct.length; i++) if (pct[i] > pct[w]) w = i;
  return w;
}

/** The scene for one frame. frame = null draws the feeder at rest (no meters, halos or battery state). */
export function buildSceneModel({ topology, footprints = null, frame = null, view = 'p1', theme = 'light', pins = null, placed = null, hideBatteries = false }) {
  const st = staticScene(topology, footprints, theme);
  const tfs = topology.transformers;
  const tier = frame && frame.tier ? frame.tier : tfs.map(() => 0);
  const pct = frame && frame.loadingPct ? frame.loadingPct : tfs.map(() => 0);
  const dimmed = view === 'more';
  const ink = INK[theme] || INK.light;
  const accent = theme === 'dark' ? ACCENT_DARK : ACCENT;
  const hs = frame ? homeStatesAt(frame.homeStateChanges, frame.step, topology.homes.length) : null;

  // walls: neutral, except a home without power (dark) or lit by its own battery (warm)
  const homes = st.walls.map((w) => {
    const state = hs ? hs[w.i] : 'lit';
    const c = state === 'dark' ? DARK_HOME : state === 'battery' ? BACKUP_GLOW : w.color;
    return { i: w.i, id: w.id, tf: w.tf, polygon: w.polygon, height: w.height, state, color: withAlpha(c, dimmed ? 110 : 255) };
  });
  const homeKey = `${view}:${homes.filter((h) => h.state !== 'lit').map((h) => h.i + h.state[0]).join(',')}`;

  // batteries: the cabinet + cap (static geometry) and the icon (per frame)
  const fleet = hideBatteries ? [] : (topology.fleet || []);
  const batteries = [], pulses = [];
  // keep the static arrays' identity when nothing is added (deck.gl then skips re-tessellating the 96 cabinets)
  const extra = (placed || []).length > 0;
  let cabinets = hideBatteries ? NONE : st.cabinets, caps = hideBatteries ? NONE : st.caps;
  if (extra) { cabinets = cabinets.slice(); caps = caps.slice(); }
  fleet.forEach((hi, j) => {
    const position = st.iconPos[j];
    const soc = frame && frame.soc ? clamp(frame.soc[j], 0, 1) : 0;
    const s = frame && frame.state ? frame.state[j] : 'I';
    const kw = frame && frame.batKW ? frame.batKW[j] : 0;
    batteries.push({ j, home: hi, position, polygon: st.cabinets[j].polygon, icon: batteryId(s, soc), soc, kw, state: s });
    if (frame && frame.prevBatKW && Math.abs(kw - frame.prevBatKW[j]) > PULSE_KW) {
      const c = STATE_RGB[s] || STATE_RGB.I;
      pulses.push({ j, position: [position[0], position[1]], color: withAlpha(s === 'C' ? accent : c, 220) });
    }
  });
  for (const p of placed || []) {
    const h = topology.homes[p.home];
    if (!h) continue;
    const sp = cabinetSpot(st.walls[p.home].polygon, tfs[h.tf].lonlat);
    const polygon = boxRing(sp.cM, sp.u, CABINET_M[0], CABINET_M[1], sp.o);
    cabinets.push({ j: -1, home: p.home, polygon, height: CABINET_M[2], placed: true });
    caps.push({ j: -1, home: p.home, polygon: boxRing(sp.cM, sp.u, CABINET_M[0] + 0.1, CABINET_M[1] + 0.1, sp.o, CABINET_M[2]), height: 0.3, placed: true });
    batteries.push({ j: -1, home: p.home, position: toLL(sp.cM, sp.o, CABINET_M[2] + 0.5), polygon, icon: batteryId('N', 0.9), soc: 0.9, kw: 0, state: 'N', placed: true });
  }

  // transformers: meters on the named ones and any at tier >= 1; halos at tier >= 1
  const meters = [], halos = [];
  if (frame) {
    for (const t of st.tfs) {
      const code = tier[t.i] | 0;
      if (code >= 1) halos.push({ i: t.i, position: t.position, code });
      if (t.key || code >= 1) meters.push({ i: t.i, position: t.meterPos, icon: meterId(code, pct[t.i] || 0), code, pct: pct[t.i] || 0, named: !!t.key });
    }
  }
  const tfState = st.tfs.map((t) => ({ ...t, code: tier[t.i] | 0, pct: pct[t.i] || 0 }));

  // the one number in the scene: the worst transformer now, with its label's tag
  const worst = [];
  if (frame && !frame.noWorst) {
    const w = worstIndex(pct);
    const t = st.tfs[w];
    const text = `worst now ${pct[w].toFixed(1)}%`;
    worst.push({ i: w, position: t.meterPos, text, code: tier[w] | 0, pct: pct[w], label: frame.loadingLabel || 'SIM', tag: (frame.loadingLabel || 'SIM')[0], name: t.key || `T-${w}` });
  }

  const labels = [];
  // A-D in topology.focus order, then T-240 (key '240', the contract's focus key for the bridge)
  for (const f of topology.focus || []) { const t = st.tfs[f.tf]; labels.push({ key: f.key, short: f.key, text: f.key, position: t.meterPos, color: ink, tf: f.tf }); }
  for (const b of topology.bridge || []) { const t = st.tfs[b.tf]; labels.push({ key: String(b.tf), short: `T-${b.tf}`, text: `T-${b.tf}`, position: t.meterPos, color: ink, tf: b.tf }); }
  for (const p of pins || []) {
    const h = topology.homes[p.home];
    if (h) labels.push({ key: 'pin', short: String(p.text), text: String(p.text), position: [h.lonlat[0], h.lonlat[1], 16], color: ink, pin: true, home: p.home });
  }

  return {
    view, theme, step: frame ? frame.step : 0, staticKey: st.key, footprintsMatched: st.matched,
    homeGeom: st.walls, walls: st.walls, homes, homeKey, roofs: st.roofs, tier, tierKey: frame ? (frame.tierKey || tier.join('')) : '',
    drops: st.drops, context: st.context, lines: st.lines,
    tfs: tfState, pads: st.pads, plinths: st.plinths, poles: st.poles, cans: st.cans, arms: st.arms, colors: st.colors,
    cabinets, caps, batteries, pulses, meters, halos, worst, labels, badges: [], ink, accent,
  };
}
