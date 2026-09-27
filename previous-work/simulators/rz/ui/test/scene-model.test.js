// ui/test/scene-model.test.js (L4): the pure scene model on the committed topology, footprints and P1 data.
// Round 2 (UX_SPEC_R2 6.1, 6.7): hip roofs over the exact footprint, pad/pole transformers, battery cabinets + icons,
// meters only where they matter, sage tier 0, and the P2 pins/placed round trip.
// Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildSceneModel, cameraPreset, frameFromP1, frameFromP2, homeStatesAt, roomKW, exportRoomKW, headroom, squareRing, staticScene, codeFromPct,
  TIER_RGB, TIER_NAMES, TIER_WORDS, STATE_RGB, DARK_HOME, BACKUP_GLOW, MISSING_SQUARE_M, wallHeight, WALL_H_ONE, WALL_H_TWO, hipRoof, obb, ringAreaM,
  toM, roofColor, dropStyle, mountOf, namedTfs, cabinetSpot, worstIndex, PULSE_KW, WALL_RGB, ROOF_RGB, PAD_RGB,
} from '../lib/scene-model.js';
import { batteryId, meterId } from '../lib/icons.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJSON = (rel) => JSON.parse(fs.readFileSync(path.join(UI, 'data', rel), 'utf8'));
const topology = readJSON('topology.json');
const footprints = fs.existsSync(path.join(UI, 'data', 'footprints.json')) ? readJSON('footprints.json') : null;
const p1Dir = fs.existsSync(path.join(UI, 'data', 'p1', 'meta.json')) ? 'p1' : 'fixtures/p1';
const meta = readJSON(`${p1Dir}/meta.json`);
const branchDoc = (b) => readJSON(`${p1Dir}/${b}.json`);
const focusTf = (key) => topology.focus.find((f) => f.key === key).tf;
const M_PER_DEG = 6371008.8 * Math.PI / 180;
function ringSizeM(ring) {
  const lat = ring[0][1];
  const xs = ring.map((p) => p[0] * M_PER_DEG * Math.cos(lat * Math.PI / 180));
  const ys = ring.map((p) => p[1] * M_PER_DEG);
  return [Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
}
const triAreaXY = (t) => Math.abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[2][0] - t[0][0]) * (t[1][1] - t[0][1])) / 2;

test('footprints.json: ODbL credit, labelled match counts, one ring per matched home id, inside the feeder bbox', () => {
  assert.ok(footprints, 'ui/data/footprints.json is committed');
  assert.equal(footprints.schema, 'hb.footprints.v1');
  assert.match(footprints.meta.license, /ODbL 1\.0, © OpenStreetMap contributors/);
  assert.equal(footprints.meta.matched.label, 'DERIVED');
  assert.equal(footprints.meta.fallback.label, 'ASSUMPTION');
  const ids = new Set(topology.homes.map((h) => h.id));
  const keys = Object.keys(footprints.homes);
  assert.equal(keys.length, footprints.meta.matched.v);
  assert.equal(keys.length + footprints.meta.fallback.v, topology.homes.length);
  for (const k of keys) assert.ok(ids.has(k), `unknown home id ${k}`);
  for (const r of [...Object.values(footprints.homes), ...footprints.others]) {
    assert.ok(r.length >= 3);
    for (const [lon, lat] of r) assert.ok(lon > -97.81 && lon < -97.78 && lat > 30.40 && lat < 30.44, `${lon},${lat}`);
  }
});

test('homes: walls over the real footprint (else a 12 m square, ASSUMPTION), one or two storeys, neutral colours', () => {
  const m = buildSceneModel({ topology, footprints, frame: null });
  assert.equal(m.homes.length, topology.homes.length);
  assert.equal(m.walls.length, topology.homes.length);
  let real = 0, two = 0;
  for (const w of m.walls) {
    assert.ok(w.polygon.length >= 3);
    assert.ok(w.height === WALL_H_ONE || w.height === WALL_H_TWO, `height ${w.height}`);
    if (w.height === WALL_H_TWO) two += 1;
    assert.equal(w.home, w.i);   // P2's click handler reads `home`
    const fp = footprints && footprints.homes[w.id];
    if (fp) { real += 1; assert.equal(w.polygon, fp); } else {
      const [x, y] = ringSizeM(w.polygon);
      assert.ok(Math.abs(x - MISSING_SQUARE_M) < 0.05 && Math.abs(y - MISSING_SQUARE_M) < 0.05, `${x} x ${y}`);
    }
    assert.ok(WALL_RGB.some((c) => c[0] === w.color[0] && c[1] === w.color[1] && c[2] === w.color[2]), 'wall colour from the neutral palette');
  }
  assert.equal(real, footprints ? footprints.meta.matched.v : 0);
  assert.equal(m.footprintsMatched, real);
  const share = two / m.walls.length;
  assert.ok(share > 0.2 && share < 0.4, `two-storey share ${share}`);
  assert.equal(wallHeight('p1ulv11991'), wallHeight('p1ulv11991'));
  // no roof palette colour is a tier hue (red, amber, orange belong to tiers 1-4; tier 5 is a grey by design)
  for (const r of ROOF_RGB) for (const t of TIER_RGB.slice(1, 5)) assert.ok(Math.hypot(r[0] - t[0], r[1] - t[1], r[2] - t[2]) > 60, `roof ${r} too close to tier ${t}`);
});

test('hip roof: triangles cover the exact footprint (projected area = ring area within 1%), ridge on the long axis', () => {
  // a 20 x 10 m rectangle: a ridge of 10 m at wallH + min(3.2, 0.42 x 5) = wallH + 2.1
  const o = [-97.8, 30.42];
  const rect = [[0, 0], [20, 0], [20, 10], [0, 10]].map(([x, y]) => [o[0] + x / (M_PER_DEG * Math.cos(o[1] * Math.PI / 180)), o[1] + y / M_PER_DEG]);
  const r = hipRoof(rect, 3.3);
  assert.ok(Math.abs(r.box.L - 20) < 1e-3 && Math.abs(r.box.W - 10) < 1e-3, `obb ${r.box.L} x ${r.box.W}`);
  assert.ok(Math.abs(r.rise - 2.1) < 1e-3);
  const area = r.faces.reduce((s, f) => s + triAreaXY(f.m), 0);
  assert.ok(Math.abs(area - 200) < 2, `rect roof area ${area}`);
  const zs = r.faces.flatMap((f) => f.m.map((p) => p[2]));
  assert.ok(Math.abs(Math.min(...zs) - 3.3) < 1e-9 && Math.abs(Math.max(...zs) - 5.4) < 1e-3);
  // the minimum-area box of an axis-aligned rectangle is the rectangle
  const b = obb([[0, 0], [8, 0], [8, 3], [0, 3]]);
  assert.ok(Math.abs(b.L - 8) < 1e-9 && Math.abs(b.W - 3) < 1e-9 && Math.abs(Math.abs(b.u[0]) - 1) < 1e-9);
  // real footprints: every home's roof covers its ring (L-shapes included), within 1%
  let n = 0;
  for (const [id, ring] of Object.entries(footprints ? footprints.homes : {})) {
    if (n++ % 7) continue;   // a seventh of them keeps the test fast; the model builds all of them below
    const rr = hipRoof(ring, 3.3);
    const P = ring.map((p) => toM(p, rr.o));
    if (P.length > 3 && Math.hypot(P[0][0] - P[P.length - 1][0], P[0][1] - P[P.length - 1][1]) < 0.01) P.pop();
    const want = ringAreaM(P), got = rr.faces.reduce((s, f) => s + triAreaXY(f.m), 0);
    assert.ok(Math.abs(got - want) <= 0.01 * want + 0.05, `${id}: roof ${got.toFixed(2)} m2 vs ring ${want.toFixed(2)} m2`);
  }
  const m = buildSceneModel({ topology, footprints, frame: null });
  assert.ok(m.roofs.length > topology.homes.length * 8, `${m.roofs.length} roof triangles`);
  for (const f of m.roofs.slice(0, 500)) { assert.equal(f.poly.length, 3); assert.ok(f.poly.every((p) => p.length === 3)); }
});

test('roof tint only at tier >= 1; service drops coloured by tier; tier 0 is sage, never bright green', () => {
  assert.deepEqual(TIER_RGB[0], [138, 165, 143]);
  assert.equal(TIER_RGB.length, 6);
  assert.equal(TIER_NAMES.length, 6);
  assert.equal(TIER_WORDS.length, 6);
  // the "sending power out" battery colour is not a tier colour (violet, not orange)
  for (const t of TIER_RGB) assert.notDeepEqual(STATE_RGB.D, t);
  const m = buildSceneModel({ topology, footprints, frame: null });
  const f = m.roofs[0];
  assert.deepEqual(roofColor(f, 0), f.color);
  const t4 = roofColor(f, 4);
  assert.notDeepEqual(t4, f.color);
  assert.ok(t4[0] > t4[1], 'an emergency roof reads red');
  assert.equal(dropStyle(0).width, 1.2);
  assert.deepEqual(dropStyle(3).color.slice(0, 3), TIER_RGB[3]);
  assert.equal(dropStyle(2).width, 3.5);
  assert.equal(m.drops.length, topology.homes.length);
  for (const d of m.drops.slice(0, 50)) assert.deepEqual(d.path[0].slice(0, 2), topology.transformers[d.tf].lonlat);
});

test('transformers: pad (plinth + green box) or pole (pole + arm + can) from topology `mount`; A and C on poles once l0 lands it', () => {
  const m = buildSceneModel({ topology, footprints, frame: null });
  assert.equal(m.tfs.length, topology.transformers.length);
  assert.equal(m.pads.length + m.poles.length, topology.transformers.length);
  assert.equal(m.pads.length, m.plinths.length);
  assert.equal(m.poles.length, m.cans.length);
  assert.equal(m.poles.length, m.arms.length);
  assert.deepEqual(m.colors.pad.slice(0, 3), PAD_RGB);
  for (const t of m.tfs) assert.equal(t.mount, mountOf(topology.transformers[t.i]));
  if (topology.transformers.some((t) => t.mount)) {
    const mt = (key) => m.tfs[focusTf(key)].mount;
    assert.deepEqual(['A', 'B', 'C', 'D'].map(mt), ['pole', 'pad', 'pole', 'pad']);
    assert.equal(m.tfs[topology.bridge[0].tf].mount, 'pad');
  } else {
    assert.equal(m.poles.length, 0, 'no `mount` in topology.json yet: every transformer is drawn as a pad');
  }
  const names = namedTfs(topology);
  assert.deepEqual([...names.values()].sort(), ['A', 'B', 'C', 'D', 'T-240']);
});

test('meters only on A-D, T-240 and transformers at tier >= 1; halos only at tier >= 1; the worst-now callout is the only number', () => {
  const doc = branchDoc('naive');
  const k = fmtStep('22:30');
  const frame = frameFromP1(doc, k);
  const m = buildSceneModel({ topology, footprints, frame });
  const named = new Set([...namedTfs(topology).keys()]);
  for (const mt of m.meters) {
    assert.ok(named.has(mt.i) || frame.tier[mt.i] >= 1, `meter on T-${mt.i}`);
    assert.equal(mt.icon, meterId(frame.tier[mt.i], frame.loadingPct[mt.i]));
  }
  const want = topology.transformers.filter((_, i) => named.has(i) || frame.tier[i] >= 1).length;
  assert.equal(m.meters.length, want);
  assert.equal(m.halos.length, frame.tier.filter((c) => c >= 1).length);
  assert.equal(m.worst.length, 1);
  const w = worstIndex(frame.loadingPct);
  assert.equal(m.worst[0].i, w);
  assert.equal(m.worst[0].text, `worst now ${frame.loadingPct[w].toFixed(1)}%`);
  assert.equal(m.worst[0].tag, doc.series.loading.label[0]);
  assert.equal(m.worst[0].name, namedTfs(topology).get(w) || `T-${w}`);   // the off-screen pointer names it
  if (p1Dir === 'p1') assert.equal(m.worst[0].text, `worst now ${(meta.summary.naive.maxLoading.v).toFixed(1)}%`);
  // labels: "A".."D", "T-240" only (no kVA, no room; never "Northbank")
  assert.deepEqual(m.labels.map((l) => l.text), ['A', 'B', 'C', 'D', 'T-240']);
  assert.deepEqual(m.labels.map((l) => l.key), ['A', 'B', 'C', 'D', '240']);
  const src = fs.readFileSync(path.join(UI, 'lib', 'scene-model.js'), 'utf8') + fs.readFileSync(path.join(UI, 'panels', 'p1.js'), 'utf8');
  assert.ok(!/Northbank/.test(src), 'audit L14: the invented name is gone');
  // P2 month peaks: no worst-now callout (it is a month, not a minute)
  const p2 = buildSceneModel({ topology, footprints, frame: frameFromP2({ baseline: { peak: topology.transformers.map(() => 500) } }), view: 'p2' });
  assert.equal(p2.worst.length, 0);
  function fmtStep(t) { const [h, mi] = t.split(':').map(Number); return ((h * 60 + mi - 16 * 60) + 1440) % 1440; }
});

test('batteries: 96 cabinets beside their homes + an icon each (fill = SoC, state), a pulse on a changed command; none hides them', () => {
  const n = topology.fleet.length;
  assert.equal(n, 96);
  const soc = Array.from({ length: n }, (_, j) => (j % 10) / 10);
  const batKW = Array.from({ length: n }, (_, j) => (j === 0 ? 12 : 0));
  const prevBatKW = Array.from({ length: n }, (_, j) => (j === 1 ? PULSE_KW / 2 : 0));
  const state = Array.from({ length: n }, (_, j) => (j === 0 ? 'C' : j === 1 ? 'D' : j === 2 ? 'S' : j === 3 ? 'X' : 'I')).join('');
  const m = buildSceneModel({ topology, footprints, frame: { step: 1, tier: topology.transformers.map(() => 0), loadingPct: topology.transformers.map(() => 0), batKW, prevBatKW, soc, state, homeStateChanges: [] } });
  assert.equal(m.batteries.length, n);
  assert.equal(m.cabinets.length, n);
  assert.equal(m.caps.length, n);
  for (const b of m.batteries) assert.equal(b.icon, batteryId(b.state, b.soc));
  assert.equal(m.batteries[0].icon, 'bat-C-0');
  assert.equal(m.batteries[1].icon, 'bat-D-1');
  assert.deepEqual(m.pulses.map((p) => p.j), [0]);
  // the cabinet stands outside the footprint, within a few metres of its wall
  for (const j of [0, 10, 50]) {
    const hi = topology.fleet[j];
    const ring = m.walls[hi].polygon;
    const sp = cabinetSpot(ring, topology.transformers[topology.homes[hi].tf].lonlat);
    const P = ring.map((p) => toM(p, sp.o));
    let d = Infinity;
    for (let a = 0; a < P.length; a++) { const A = P[a], B = P[(a + 1) % P.length]; const dx = B[0] - A[0], dy = B[1] - A[1], L2 = dx * dx + dy * dy || 1; const t = Math.max(0, Math.min(1, ((sp.cM[0] - A[0]) * dx + (sp.cM[1] - A[1]) * dy) / L2)); d = Math.min(d, Math.hypot(A[0] + dx * t - sp.cM[0], A[1] + dy * t - sp.cM[1])); }
    assert.ok(d > 0.5 && d < 4.5, `cabinet ${j} is ${d.toFixed(2)} m from its wall`);
  }
  const none = buildSceneModel({ topology, footprints, frame: null, hideBatteries: true });
  assert.equal(none.batteries.length + none.cabinets.length + none.caps.length, 0);
  // the static cabinets keep their identity across frames (no re-tessellation)
  const m2 = buildSceneModel({ topology, footprints, frame: null });
  assert.equal(m.cabinets, m2.cabinets);
});

test('P2 reuses the model: pins become labels, placed batteries become ghost cabinets + a new-battery icon', () => {
  const p2 = buildSceneModel({ topology, footprints, frame: null, view: 'p2', pins: [{ home: 408, text: '#1' }], placed: [{ home: 408 }] });
  assert.ok(p2.labels.some((l) => l.pin && l.text === '#1' && l.home === 408));
  assert.equal(p2.batteries.length, topology.fleet.length + 1);
  const pb = p2.batteries.find((b) => b.placed);
  assert.equal(pb.home, 408);
  assert.equal(pb.icon, batteryId('N', 0.9));
  assert.equal(p2.cabinets.filter((c) => c.placed).length, 1);
  assert.equal(p2.caps.filter((c) => c.placed).length, 1);
});

test('home states recolour the walls: dark and battery-backup homes', () => {
  const tier = topology.transformers.map(() => 0);
  const A = focusTf('A');
  const [h0, h1] = topology.transformers[A].homes;
  const frame = { step: 5, tier, loadingPct: tier.map(() => 50), batKW: null, prevBatKW: null, soc: null, state: null,
    homeStateChanges: [[3, h0, 'dark'], [4, h1, 'battery'], [9, 0, 'dark']] };
  const m = buildSceneModel({ topology, footprints, frame });
  assert.deepEqual(m.homes[h0].color.slice(0, 3), DARK_HOME);
  assert.deepEqual(m.homes[h1].color.slice(0, 3), BACKUP_GLOW);
  assert.notDeepEqual(m.homes[0].color.slice(0, 3), DARK_HOME, 'the step-9 change has not happened yet at step 5');
  assert.notEqual(m.homeKey, buildSceneModel({ topology, footprints, frame: { ...frame, homeStateChanges: [] } }).homeKey);
  assert.deepEqual(homeStatesAt([[1, 0, 'dark'], [5, 1, 'battery']], 5, 2), ['dark', 'battery']);
});

test('static geometry keeps its identity across frames (deck.gl does not re-tessellate)', () => {
  const doc = branchDoc('aware');
  const a = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, 1) });
  const b = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, 2) });
  for (const key of ['walls', 'roofs', 'drops', 'lines', 'context', 'pads', 'poles', 'cabinets', 'caps']) assert.equal(a[key], b[key], key);
  assert.equal(a.staticKey, b.staticKey);
  assert.equal(staticScene(topology, footprints, 'light'), staticScene(topology, footprints, 'light'));
  assert.notEqual(staticScene(topology, footprints, 'dark'), staticScene(topology, footprints, 'light'));
});

test('exportRoomKW / headroom / roomKW: unchanged physics (judge R1 F6)', () => {
  assert.ok(Math.abs(exportRoomKW(50, 98.4, -49.7) - 0.3) < 0.05);
  assert.ok(Math.abs(exportRoomKW(25, 80, -20) - 5) < 1e-9);
  assert.deepEqual(headroom(25, 80, -20), { dir: 'export', kw: exportRoomKW(25, 80, -20) });
  assert.deepEqual(headroom(25, 80, 20), { dir: 'charge', kw: roomKW(25, 80, 20) });
  assert.ok(Math.abs(roomKW(25, 80, 20) - 5) < 1e-9);
  assert.equal(roomKW(50, 50), 25);
});

test('frames: quantized contract arrays decode (pct x10, kW x10, SoC per mille); k clamps; P2 month peaks', () => {
  const doc = branchDoc('aware');
  const f = frameFromP1(doc, 3);
  assert.equal(f.loadingPct[7], doc.loading[3][7] / 10);
  assert.equal(f.batKW[0], doc.batKW[3][0] / 10);
  assert.equal(f.prevBatKW[0], doc.batKW[2][0] / 10);
  assert.equal(f.soc[0], doc.soc[3][0] / 1000);
  assert.equal(f.tierKey, doc.tier[3]);
  assert.equal(frameFromP1(doc, 1e9).step, doc.loading.length - 1);
  const p2 = frameFromP2({ baseline: { peak: topology.transformers.map((_, i) => (i === 3 ? 1195 : 500)) } });
  assert.equal(p2.loadingPct[3], 119.5);
  assert.equal(p2.tier[3], 2);
  assert.deepEqual([codeFromPct(99), codeFromPct(101), codeFromPct(111), codeFromPct(151)], [0, 1, 2, 4]);
});

test('every branch and step of the committed P1 data builds a valid model', () => {
  for (const b of meta.branches) {
    const doc = branchDoc(b);
    for (const k of [0, Math.floor(doc.loading.length / 2), doc.loading.length - 1]) {
      const m = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, k), hideBatteries: b === 'none' });
      for (const h of m.homes) assert.ok(h.color.length === 4);
      for (const bt of m.batteries) assert.match(bt.icon, /^bat-[CDISXB]-(10|\d)$/);
      for (const mt of m.meters) assert.match(mt.icon, /^m-[0-5]-\d+$/);
      for (const r of m.roofs.slice(0, 100)) assert.ok(roofColor(r, m.tier[r.tf]).every((x) => x >= 0 && x <= 255));
    }
  }
});

test('camera presets: whole feeder, street A-D (zoom ~18, pitch 55), T-240', () => {
  const s = cameraPreset(topology, 'street');
  assert.equal(s.zoom, 18);
  assert.equal(s.pitch, 55);
  for (const p of topology.focus.map((f) => topology.transformers[f.tf].lonlat)) assert.ok(Math.abs(p[0] - s.longitude) < 0.002 && Math.abs(p[1] - s.latitude) < 0.002);
  const t = cameraPreset(topology, 't240');
  const b = topology.transformers[topology.bridge[0].tf].lonlat;
  assert.ok(Math.abs(b[0] - t.longitude) < 0.001 && Math.abs(b[1] - t.latitude) < 0.001);
  const f = cameraPreset(topology, 'feeder');
  assert.ok(f.zoom < 16 && f.zoom > 13);
  assert.deepEqual(cameraPreset(topology, 'nope'), f);
  assert.equal(squareRing([-97.8, 30.42], 12).length, 4);
});

test('3D and 2D share the hover contract: onHover, pickingRadius 3, the pickable layers, the atlas from icons.js', () => {
  const s3 = fs.readFileSync(path.join(UI, 'lib', 'scene3d.js'), 'utf8');
  const s2 = fs.readFileSync(path.join(UI, 'lib', 'fallback2d.js'), 'utf8');
  assert.match(s3, /pickingRadius: 3/);
  assert.match(s3, /onHover\(cb\) \{ hover = cb; \}/);
  assert.match(s3, /buildAtlas\(64\)/);
  assert.match(s3, /radiusMinPixels: 6/);   // halos read at feeder zoom
  for (const id of ['walls', 'roofs', 'pads', 'poles', 'cans', 'cabinets', 'caps', 'meters', 'battery-icons']) {
    assert.match(s3, new RegExp(`id: '${id}'[^\\n]*\\n?[^\\n]*pickable: true`), `${id} is pickable in 3D`);
  }
  for (const gone of ['can-ghost', 'battery-ghost', 'can-ring110', 'can-cap150', 'battery-reserve', "id: 'alerts'"]) assert.ok(!s3.includes(gone), `${gone} removed`);
  assert.match(s2, /onHover\(cb\) \{ hover = cb; \}/);
  assert.match(s3, /hb-worst-ptr/, 'the off-screen worst pointer');
  for (const id of ['walls', 'pads', 'poles', 'cans', 'cabinets', 'meters', 'battery-icons']) assert.ok(s2.includes(`layer: '${id}'`), `2D hit-tests ${id}`);
});
