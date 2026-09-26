// ui/test/core.test.js (L0): the shell's pure pieces and the static-demo check. Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import { fmt, fmtHTML, fmtValue, chip, isLabelled, LabelError, pct10, kw10, socPm, timeToStep, stepToTime, hhmmToMin, minToHHMM } from '../lib/format.js';
import { parseLink, linkQuery, applyBeat, _configure, getWithFixture, getOptional, isFixture, onFixture, HttpError } from '../lib/data.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

test('format: a bare number throws, a labelled one formats with its chip', () => {
  assert.throws(() => fmt(197), LabelError);
  assert.throws(() => fmtHTML({ v: 1 }), LabelError);
  assert.throws(() => fmtHTML({ v: 1, label: 'SOURCED' }), LabelError);
  assert.throws(() => chip('GUESS'), LabelError);
  assert.equal(fmt({ v: 197.04, label: 'SIM' }, { unit: '%' }), '197.0% SIM');
  assert.equal(fmtValue({ v: -1234.5, label: 'DERIVED' }, { money: true, digits: 2 }), '-$1,234.50');
  assert.equal(fmtValue({ v: 3, label: 'SIM' }, { signed: true }), '+3');
  assert.equal(fmtValue({ v: true, label: 'SIM' }), 'yes');
  assert.match(fmtHTML({ v: 55.42, label: 'REAL', cite: 'ERCOT <RTM>' }, { digits: 2 }), /chip-REAL" title="ERCOT &lt;RTM&gt;"/);
  assert.ok(isLabelled({ v: 0, label: 'ASSUMPTION' }));
  assert.ok(!isLabelled([1]));
});

test('format: quantized bulk values', () => {
  assert.equal(pct10(1970), '197.0%');
  assert.equal(kw10(-200), '-20.0 kW');
  assert.equal(socPm(905), '91%');
});

test('format: time <-> step across midnight', () => {
  const meta = { start: '16:00', stepSeconds: 60, steps: 720 };
  assert.equal(timeToStep(meta, '16:00'), 0);
  assert.equal(timeToStep(meta, '22:30'), 390);
  assert.equal(timeToStep(meta, '03:59'), 719);
  assert.equal(timeToStep(meta, '05:00'), 719);     // clamped (13 h after start)
  assert.equal(timeToStep(meta, 'nope'), null);
  assert.equal(stepToTime(meta, 480), '00:00');
  assert.equal(hhmmToMin('24:00'), null);
  assert.equal(minToHHMM(1500), '01:00');
});

test('data: parseLink defaults, validation and round trip', () => {
  const d = parseLink('');
  assert.deepEqual([d.view, d.branch, d.t, d.cam, d.combo, d.nowebgl], ['p1', 'aware', null, null, null, false]);
  const l = parseLink('?view=p1&branch=aware_faults&t=22:16&cam=street&nowebgl=1');
  assert.deepEqual([l.view, l.branch, l.t, l.cam, l.nowebgl], ['p1', 'aware_faults', '22:16', 'street', true]);
  const bad = parseLink('?view=evil&branch=x&t=9pm&cam=moon&n=99&combo=../../etc');
  assert.deepEqual([bad.view, bad.branch, bad.t, bad.cam, bad.n, bad.combo], ['p1', 'aware', null, null, null, null]);
  const p2 = parseLink('?view=p2&combo=naive-core-d26-g20&home=p1ulv24700&n=5');
  assert.deepEqual([p2.view, p2.combo, p2.home, p2.n], ['p2', 'naive-core-d26-g20', 'p1ulv24700', 5]);
  assert.deepEqual(parseLink(linkQuery(p2)), p2);
  assert.equal(parseLink('?smoke=dump').smoke, 'dump');
  assert.equal(parseLink('?smoke=1').smoke, null);
});

test('data: a beat sets every key it names', () => {
  const beats = { beats: [{ id: 'rebound', link: 'view=p1&branch=naive&t=22:30&cam=street' }] };
  const l = applyBeat(parseLink('?view=p2&beat=rebound&nowebgl=1'), beats);
  assert.deepEqual([l.view, l.branch, l.t, l.cam, l.nowebgl], ['p1', 'naive', '22:30', 'street', true]);
  assert.equal(applyBeat(parseLink('?beat=missing'), beats).view, 'p1');
});

test('data: real file first, fixture on 404 (and the page is marked)', async () => {
  const files = { 'data/fixtures/p1/meta.json': { fixture: true }, 'data/p2/index.json': { real: true } };
  _configure({ base: 'data/', fetchFn: async (u) => (u in files
    ? { ok: true, status: 200, json: async () => files[u] } : { ok: false, status: 404, json: async () => null }) });
  let marked = 0;
  onFixture(() => { marked += 1; });
  assert.deepEqual(await getWithFixture('p2/index.json'), { real: true });
  assert.equal(isFixture(), false);
  assert.deepEqual(await getWithFixture('p1/meta.json'), { fixture: true });
  assert.equal(isFixture(), true);
  assert.equal(marked, 1);
  assert.equal(await getOptional('beats.json'), null);
  await assert.rejects(getWithFixture('p1/none.json'), HttpError);
});

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (!['vendor', 'data', 'test'].includes(e.name)) walk(p, out); }
    else if (/\.(html|js|css)$/.test(e.name)) out.push(p);
  }
  return out;
}

test('static demo: no absolute http(s) URL in any src, href, import, fetch or url() (vendor excluded)', () => {
  const pats = [
    /\bsrc\s*=\s*["'`]\s*(https?:)?\/\//i,
    /<link[^>]+href\s*=\s*["'`]\s*(https?:)?\/\//i,
    /\bimport\s*(?:[^'"`]*?\bfrom\s*)?\(?\s*["'`]\s*(https?:)?\/\//i,
    /\bfetch\s*\(\s*["'`]\s*(https?:)?\/\//i,
    /url\(\s*["']?\s*(https?:)?\/\//i,
    /new\s+(?:Worker|WebSocket|EventSource)\s*\(/i,
  ];
  // the admit half: each pattern does catch an offsite load
  const bad = ['<script src="https://cdn.x/y.js">', '<link rel="stylesheet" href="//fonts.x/css">', "import x from 'https://esm.sh/x'",
    "fetch('https://api.ercot.com/x')", 'background: url(https://x/y.png)', "new WebSocket('wss://x')"];
  bad.forEach((b, i) => assert.ok(pats[i].test(b), `pattern ${i} misses ${b}`));
  const files = walk(UI);
  assert.ok(files.length >= 10, `found ${files.length} files`);
  for (const f of files) {
    const s = fs.readFileSync(f, 'utf8');
    for (const re of pats) assert.ok(!re.test(s), `${path.relative(UI, f)} matches ${re}`);
  }
});

test('shell: index.html carries the health flags and loads the vendored deck.gl 9.4.0', () => {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  for (const k of ['data-status="loading"', 'data-webgl=', 'data-errors="0"', 'data-fixture="0"', 'data-offsite="0"']) assert.ok(html.includes(k), k);
  assert.ok(html.includes('src="vendor/deck-9.4.0.min.js"'));
  const sha = crypto.createHash('sha256').update(fs.readFileSync(path.join(UI, 'vendor', 'deck-9.4.0.min.js'))).digest('hex');
  assert.equal(sha, '2eb6a1ae0d58604b1378682cd1136f8793478ba801e43dae48b3807e48758a6b');
  assert.ok(fs.existsSync(path.join(UI, 'vendor', 'LICENSE-deck.gl')));
});

test('shell: the stubs export the agreed names', async () => {
  for (const p of ['p1', 'p2', 'more']) assert.equal(typeof (await import(`../panels/${p}.js`)).mount, 'function', p);
  const sm = await import('../lib/scene-model.js');
  for (const k of ['buildSceneModel', 'cameraPreset', 'frameFromP1', 'frameFromP2']) assert.equal(typeof sm[k], 'function', k);
  assert.equal(sm.TIER_RGB.length, 6);
  for (const m of ['../lib/scene3d.js', '../lib/fallback2d.js']) assert.equal(typeof (await import(m)).createScene, 'function', m);
  const charts = await import('../lib/charts.js');
  for (const k of ['priceStrip', 'heatStrip', 'lineChart', 'barChart']) assert.equal(typeof charts[k], 'function', k);
});

test('topology.json: 1,010 homes, 379 transformers, 96 batteries, focus A-D by id', () => {
  const t = JSON.parse(fs.readFileSync(path.join(UI, 'data', 'topology.json'), 'utf8'));
  assert.equal(t.homes.length, 1010);
  assert.equal(t.transformers.length, 379);
  assert.equal(t.fleet.length, 96);
  assert.deepEqual(t.focus.map((f) => [f.key, f.tf]), [['A', 150], ['B', 357], ['C', 246], ['D', 156]]);
  assert.equal(t.transformers[150].id, 'tr(r:p1udt9411-p1udt9411lv)');
  assert.equal(t.bridge[0].tf, 240);
});
