// ui/test/scene-model.test.js (L4): the pure scene model on the committed topology, footprints and P1 data.
// Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildSceneModel, cameraPreset, frameFromP1, frameFromP2, homeStatesAt, roomKW, squareRing, staticScene, codeFromPct,
  TIER_RGB, TIER_NAMES, HOME_OK, DARK_HOME, BACKUP_GLOW, ACCENT, CAN_H_M, BAT_H_M, RESERVE_FRACTION, CAN_R_PER_SQRT_KVA,
  MISSING_SQUARE_M, homeHeight,
} from '../lib/scene-model.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJSON = (rel) => JSON.parse(fs.readFileSync(path.join(UI, 'data', rel), 'utf8'));
const topology = readJSON('topology.json');
const footprints = fs.existsSync(path.join(UI, 'data', 'footprints.json')) ? readJSON('footprints.json') : null;
// real P1 data when L2 has landed it, else the fixtures (same contract)
const p1Dir = fs.existsSync(path.join(UI, 'data', 'p1', 'meta.json')) ? 'p1' : 'fixtures/p1';
const meta = readJSON(`${p1Dir}/meta.json`);
const branchDoc = (b) => readJSON(`${p1Dir}/${b}.json`);

const M_PER_DEG = 6371008.8 * Math.PI / 180;
function ringSizeM(ring) {
  const lat = ring[0][1];
  const xs = ring.map((p) => p[0] * M_PER_DEG * Math.cos(lat * Math.PI / 180));
  const ys = ring.map((p) => p[1] * M_PER_DEG);
  return [Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
}
const focusTf = (key) => topology.focus.find((f) => f.key === key).tf;

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
  assert.ok(keys.length >= 900, `matched ${keys.length}`);
  for (const k of keys) assert.ok(ids.has(k), `unknown home id ${k}`);
  for (const r of [...Object.values(footprints.homes), ...footprints.others]) {
    assert.ok(r.length >= 3);
    for (const [lon, lat] of r) assert.ok(lon > -97.81 && lon < -97.78 && lat > 30.40 && lat < 30.44, `${lon},${lat}`);
  }
  // one home per footprint: no ring is used twice
  const seen = new Set(Object.values(footprints.homes).map((r) => JSON.stringify(r)));
  assert.equal(seen.size, keys.length);
});

test('homes: every home gets a polygon, the real footprint when matched, else a 12 m square (ASSUMPTION)', () => {
  const m = buildSceneModel({ topology, footprints, frame: null });
  assert.equal(m.homes.length, 1010);
  let real = 0;
  for (const h of m.homes) {
    assert.ok(h.polygon.length >= 3);
    assert.ok(h.height >= 6 && h.height <= 9, `height ${h.height}`);
    const fp = footprints && footprints.homes[h.id];
    if (fp) { real += 1; assert.equal(h.polygon, fp); } else {
      const [w, d] = ringSizeM(h.polygon);
      assert.ok(Math.abs(w - MISSING_SQUARE_M) < 0.05 && Math.abs(d - MISSING_SQUARE_M) < 0.05, `${w} x ${d}`);
    }
  }
  assert.equal(real, footprints ? footprints.meta.matched.v : 0);
  assert.equal(m.footprintsMatched, real);
  // without footprints every home is a box
  const bare = buildSceneModel({ topology, footprints: null, frame: null });
  assert.equal(bare.footprintsMatched, 0);
  assert.equal(homeHeight('p1ulv11991'), homeHeight('p1ulv11991'));
});

test('static geometry keeps its identity across frames (deck.gl does not re-tessellate 2,400 footprints per step)', () => {
  const doc = branchDoc('aware');
  const a = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, 1) });
  const b = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, 2) });
  assert.equal(a.homeGeom, b.homeGeom);
  assert.equal(a.lines, b.lines);
  assert.equal(a.context, b.context);
  assert.equal(a.staticKey, b.staticKey);
  assert.equal(a.lines.length, topology.edges.length);
  assert.equal(staticScene(topology, footprints, 'light'), staticScene(topology, footprints, 'light'));
  assert.notEqual(staticScene(topology, footprints, 'dark'), staticScene(topology, footprints, 'light'));
});

test('zone colour: homes take their transformer\'s tier code; dark and battery-backup homes override it', () => {
  const tier = topology.transformers.map(() => 0);
  const A = focusTf('A'), C = focusTf('C');
  tier[A] = 4;
  tier[C] = 1;
  const frame = { step: 5, tier, loadingPct: tier.map((c) => (c === 4 ? 197 : c === 1 ? 104 : 50)), batKW: null, prevBatKW: null, soc: null, state: null,
    homeStateChanges: [[3, topology.transformers[A].homes[0], 'dark'], [4, topology.transformers[A].homes[1], 'battery'], [9, topology.transformers[C].homes[0], 'dark']] };
  const m = buildSceneModel({ topology, footprints, frame });
  const [h0, h1] = topology.transformers[A].homes;
  assert.deepEqual(m.homes[h0].color.slice(0, 3), DARK_HOME);
  assert.equal(m.homes[h0].state, 'dark');
  assert.deepEqual(m.homes[h1].color.slice(0, 3), BACKUP_GLOW);
  // the step-9 change has not happened yet at step 5
  const c0 = topology.transformers[C].homes[0];
  assert.deepEqual(m.homes[c0].color.slice(0, 3), TIER_RGB[1]);
  const other = topology.homes.findIndex((h) => h.tf !== A && h.tf !== C);
  assert.deepEqual(m.homes[other].color.slice(0, 3), HOME_OK.light);
  assert.equal(TIER_NAMES.length, 6);
  assert.deepEqual(homeStatesAt([[1, 0, 'dark'], [2, 0, 'lit'], [5, 1, 'battery']], 4, 3), ['lit', 'lit', 'lit'].map((x, i) => (i === 0 ? 'lit' : x)));
  assert.deepEqual(homeStatesAt([[1, 0, 'dark'], [5, 1, 'battery']], 5, 2), ['dark', 'battery']);
});

test('cans: ghost = 100% of nameplate, fill = loading (pokes out when over), radius ~ sqrt(kVA), 110% ring and 150% cap, open = grey', () => {
  const tier = topology.transformers.map(() => 0);
  const pct = topology.transformers.map(() => 40);
  const A = focusTf('A'), D = focusTf('D');
  pct[A] = 197; tier[A] = 4;
  tier[D] = 5; pct[D] = 0;
  const m = buildSceneModel({ topology, footprints, frame: { step: 0, tier, loadingPct: pct, homeStateChanges: [] } });
  assert.equal(m.cans.length, 379);
  for (const g of m.canGhosts) assert.equal(g.height, CAN_H_M);
  assert.ok(Math.abs(m.cans[A].height - 1.97 * CAN_H_M) < 1e-9 && m.cans[A].height > m.canGhosts[A].height);
  assert.deepEqual(m.cans[A].color.slice(0, 3), TIER_RGB[4]);
  assert.ok(m.cans[D].open);
  assert.deepEqual(m.cans[D].color.slice(0, 3), TIER_RGB[5]);
  const k25 = m.cans.find((c) => c.kva === 25), k50 = m.cans.find((c) => c.kva === 50);
  assert.ok(Math.abs(k50.radius / k25.radius - Math.SQRT2) < 1e-9);
  assert.ok(Math.abs(k25.radius - CAN_R_PER_SQRT_KVA * 5) < 1e-9);
  const ringA = m.canRings.find((r) => r.i === A), capA = m.canCaps.find((r) => r.i === A);
  assert.ok(Math.abs(ringA.position[2] - 1.1 * CAN_H_M) < 1e-9 && Math.abs(capA.position[2] - 1.5 * CAN_H_M) < 1e-9);
  // rings only where they matter: named cans and cans over nameplate
  const plain = topology.transformers.findIndex((t, i) => !t.focus && i !== 240 && pct[i] <= 100);
  assert.ok(!m.canRings.some((r) => r.i === plain));
});

test('batteries: 96 columns beside their homes, fill = SoC, reserve ring at 20%, colour by state, pulse on a changed command, ! when stale', () => {
  const n = topology.fleet.length;
  const soc = Array.from({ length: n }, (_, j) => (j % 10) / 10);
  const batKW = Array.from({ length: n }, (_, j) => (j === 0 ? 12 : 0));
  const prevBatKW = Array.from({ length: n }, () => 0);
  const state = Array.from({ length: n }, (_, j) => (j === 0 ? 'C' : j === 1 ? 'D' : j === 2 ? 'S' : j === 3 ? 'X' : 'I')).join('');
  const m = buildSceneModel({ topology, footprints, frame: { step: 0, tier: topology.transformers.map(() => 0), loadingPct: topology.transformers.map(() => 0), batKW, prevBatKW, soc, state, homeStateChanges: [] } });
  assert.equal(m.batteries.length, n);
  assert.equal(m.batteryGhosts.length, n);
  for (const b of m.batteries) assert.ok(Math.abs(b.height - Math.max(0.3, BAT_H_M * b.soc)) < 1e-9);
  for (const r of m.reserveRings) assert.ok(Math.abs(r.position[2] - RESERVE_FRACTION * BAT_H_M) < 1e-9);
  assert.deepEqual(m.batteries[0].color.slice(0, 3), ACCENT);
  assert.deepEqual(m.batteries[1].color.slice(0, 3), [236, 131, 90]);
  assert.deepEqual(m.pulses.map((p) => p.j), [0]);
  assert.deepEqual(m.alerts.map((a) => a.text), ['!', '!']);
  // the P1 `none` branch draws no batteries at all
  const none = buildSceneModel({ topology, footprints, frame: null, hideBatteries: true });
  assert.equal(none.batteries.length + none.batteryGhosts.length + none.reserveRings.length, 0);
  // beside, not inside: east of the home's footprint
  const h0 = m.homeGeom[topology.fleet[0]];
  assert.ok(m.batteries[0].position[0] > Math.max(...h0.polygon.map((p) => p[0])));
});

test('labels: A-D with kVA and room to nameplate (DERIVED), T-240 with no battery; short forms for low zoom', () => {
  const doc = branchDoc('naive');
  const k = doc.loading.length - 1;
  const m = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, k) });
  const keys = m.labels.map((l) => l.key);
  assert.deepEqual(keys, ['A', 'B', 'C', 'D', '240'].filter((x) => keys.includes(x)));
  for (const key of ['A', 'B', 'C', 'D']) {
    const l = m.labels.find((x) => x.key === key);
    const tf = focusTf(key);
    const pct = doc.loading[k][tf] / 10, kva = topology.transformers[tf].kva;
    if (pct > 100) assert.equal(l.text, `${key} · ${kva} kVA · over by ${((pct / 100 - 1) * kva).toFixed(1)} kVA`);
    else assert.match(l.text, new RegExp(`^${key} · ${kva} kVA · room \\d+\\.\\d kW$`));
    assert.equal(l.short, key);
    const f = doc.focus[key];
    const expect = roomKW(kva, pct, f.homeKW[k] / 10 + f.batKW[k] / 10);
    assert.ok(Math.abs(l.room - expect) < 1e-9);
  }
  assert.match(m.labels.find((x) => x.key === '240').text, /^T-240 · 25 kVA · no battery$/);
  // pins and placed batteries (L5 reuses the model for P2)
  const p2 = buildSceneModel({ topology, footprints, frame: null, view: 'p2', pins: [{ home: 408, text: '#1' }], placed: [{ home: 408 }] });
  assert.ok(p2.labels.some((l) => l.pin && l.text === '#1'));
  assert.equal(p2.batteries.length, topology.fleet.length + 1);
});

test('roomKW: unity-pf room to nameplate from loading and real power; kVA difference without P', () => {
  assert.ok(Math.abs(roomKW(25, 80, 20) - 5) < 1e-9);                 // no reactive power: 25 - 20
  const S = 25 * 0.9, P = 18, Q = Math.sqrt(S * S - P * P);
  assert.ok(Math.abs(roomKW(25, 90, P) - (Math.sqrt(625 - Q * Q) - P)) < 1e-9);
  assert.ok(roomKW(25, 197, 49) < 0);
  assert.equal(roomKW(50, 50), 25);
});

test('frames: quantized contract arrays decode (pct x10, kW x10, SoC per mille); k clamps; P2 month peaks', () => {
  const doc = branchDoc('aware');
  const f = frameFromP1(doc, 3);
  assert.equal(f.loadingPct.length, 379);
  assert.equal(f.loadingPct[7], doc.loading[3][7] / 10);
  assert.equal(f.batKW[0], doc.batKW[3][0] / 10);
  assert.equal(f.prevBatKW[0], doc.batKW[2][0] / 10);
  assert.equal(f.soc[0], doc.soc[3][0] / 1000);
  assert.equal(f.tier.length, 379);
  assert.equal(f.state.length, 96);
  assert.equal(f.focus.A.tf, focusTf('A'));
  assert.equal(frameFromP1(doc, 1e9).step, doc.loading.length - 1);
  assert.equal(frameFromP1(doc, -5).step, 0);
  const p2 = frameFromP2({ baseline: { peak: topology.transformers.map((_, i) => (i === 3 ? 1195 : 500)) } });
  assert.equal(p2.loadingPct[3], 119.5);
  assert.equal(p2.tier[3], 2);
  assert.deepEqual([codeFromPct(99), codeFromPct(101), codeFromPct(111), codeFromPct(151)], [0, 1, 2, 4]);
});

test('every branch and step of the committed P1 data builds a valid model', () => {
  for (const b of meta.branches) {
    const doc = branchDoc(b);
    for (const k of [0, Math.floor(doc.loading.length / 2), doc.loading.length - 1]) {
      const m = buildSceneModel({ topology, footprints, frame: frameFromP1(doc, k) });
      for (const c of m.cans) assert.ok(Number.isFinite(c.height) && c.color.length === 4 && c.color.every((x) => x >= 0 && x <= 255));
      for (const h of m.homes) assert.ok(h.color.length === 4);
      for (const bt of m.batteries) assert.ok(Number.isFinite(bt.height) && bt.height >= 0.3 && bt.height <= BAT_H_M);
    }
  }
});

test('camera presets: whole feeder, street A-D (zoom ~18, pitch 55), Northbank T-240', () => {
  const s = cameraPreset(topology, 'street');
  assert.equal(s.zoom, 18);
  assert.equal(s.pitch, 55);
  const pts = topology.focus.map((f) => topology.transformers[f.tf].lonlat);
  for (const p of pts) assert.ok(Math.abs(p[0] - s.longitude) < 0.002 && Math.abs(p[1] - s.latitude) < 0.002);
  const t = cameraPreset(topology, 't240');
  const b = topology.transformers[topology.bridge[0].tf].lonlat;
  assert.ok(Math.abs(b[0] - t.longitude) < 0.001 && Math.abs(b[1] - t.latitude) < 0.001);
  const f = cameraPreset(topology, 'feeder');
  assert.ok(f.zoom < 16 && f.zoom > 13);
  // framed on the neighbourhood (the homes' median sits near the centre), not on the tail to the substation
  const lats = topology.homes.map((h) => h.lonlat[1]).sort((a, b) => a - b);
  assert.ok(Math.abs(lats[lats.length >> 1] - f.latitude) < 0.004);
  assert.deepEqual(cameraPreset(topology, 'nope'), f);
  const sq = squareRing([-97.8, 30.42], 12);
  assert.equal(sq.length, 4);
});
