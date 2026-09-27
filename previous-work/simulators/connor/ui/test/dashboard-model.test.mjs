// node --test ui/test/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { clock, ercot, ercotAt, fleet, homeFill, layout, markers, night, pulse, sample, seriesPath, stepAt, story, storyAt, tierCodes } from '../dashboard-model.js';

const replay = JSON.parse(readFileSync(new URL('../../data/replays/day.json', import.meta.url)));
const freq = JSON.parse(readFileSync(new URL('../../data/ems/freq-series.json', import.meta.url)));

test('clock and steps', () => {
  assert.equal(clock(0), '00:00'); assert.equal(clock(18.5), '18:30'); assert.equal(clock(23.999), '23:59');
  assert.deepEqual(stepAt(0, 288), { k: 0, t: 0, k2: 1 });
  assert.equal(stepAt(23.99, 288).k, 287);
  assert.ok(Math.abs(stepAt(1.5 / 12, 288).t - 0.5) < 1e-9);
});

test('pulse is a lub-dub and night is 0 by day, 1 by night', () => {
  assert.ok(pulse(0) > 0.99 && pulse(0.24) > 0.5 && pulse(0.5) < 0.05);
  assert.equal(night(3), 1); assert.equal(night(12), 0); assert.ok(night(6.25) > 0.4 && night(6.25) < 0.6);
});

test('interpolation between market steps', () => {
  const frames = replay.runs.naive;
  const a = frames[100].fleetKW, b = frames[101].fleetKW;
  assert.ok(Math.abs(sample(frames, 100.5 / 12, 'fleetKW') - (a + b) / 2) < 1e-9);
});

test('tier codes follow the referee, red only when sustained', () => {
  const f = { tier: ['ok', 'over_nameplate', 'normal_exceeded', 'normal_exceeded', 'emergency'], sustainedViolations: [3] };
  assert.deepEqual(tierCodes(f), [0, 1, 1, 2, 3]);
});

test('home fill runs from empty sage to brand green', () => {
  assert.equal(homeFill(0.2, 0), 'rgb(190,208,193)'); assert.equal(homeFill(1, 0), 'rgb(30,77,43)');
});

test('layout places every node and home inside the board', () => {
  const L = layout(replay.topology);
  assert.equal(L.txs.length, 4); assert.equal(L.homes.length, 4); assert.equal(L.edges.length, 4);
  for (const t of L.txs) assert.ok(t.x >= 380 && t.x <= 900);
  assert.ok(L.homes[3].y > L.homes[0].y, 'the long service drop hangs lower');
});

test('ercot series covers the file and converts inertia to GW·s', () => {
  const e = ercot(freq);
  assert.equal(e.rows.length, 1440); assert.equal(e.minutes, freq.series_1min.n);
  const r = ercotAt(e, 12);
  assert.ok(r.freq > 59.9 && r.freq < 60.1 && r.inert > 250 && r.inert < 400);
  assert.equal(ercotAt(e, 23.9).freq, null, 'minutes past the file end are gaps');
  assert.equal(e.thresholds.deadband, 0.017);
});

test('series paths break on gaps and stay in the plot box', () => {
  const d = seriesPath([{ h: 0, v: 1 }, { h: 1, v: null }, { h: 2, v: 3 }], 0, 4);
  assert.equal((d.match(/M/g) || []).length, 2);
  assert.ok(!d.includes('NaN'));
});

test('story is derived from the replay and ordered', () => {
  for (const policy of ['aware', 'naive']) {
    const s = story(replay, policy);
    assert.ok(s.length >= 6);
    assert.ok(s.every((x, i) => i === 0 || x.h >= s[i - 1].h));
    assert.ok(s.some(x => x.s.includes('soak')) && s.some(x => x.s.includes('discharges')));
    assert.ok(s.some(x => x.s.includes('member reserve')));
    assert.equal(storyAt(s, 0).t, '00:00');
    assert.ok(markers(s).length >= 3);
  }
});

test('fleet summary uses the replay parameters', () => {
  const f = fleet(replay, 'naive', 12);
  assert.equal(f.capKW, 80); assert.equal(f.kwh, 148);
  assert.ok(f.soc > 0.5 && f.soc <= 1 && f.pn >= 0 && f.pn <= 1);
});
