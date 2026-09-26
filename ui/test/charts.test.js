// ui/test/charts.test.js (L5): the SVG charts are pure and labelled. Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  heatStripSVG, lineChartSVG, barChartSVG, priceStripSVG, cliffStripSVG, chartHTML, captionHTML, band, modeIndex,
  ChartLabelError, parseISOmin, priceStrip, heatStrip, lineChart, barChart, cliffStrip, axisTickTexts,
} from '../lib/charts.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const count = (s, re) => (s.match(re) || []).length;

test('charts: every chart refuses to draw without an honesty label', () => {
  const cases = [
    () => heatStripSVG({ values: [1, 2] }),
    () => lineChartSVG({ series: [{ values: [1, 2] }] }),
    () => barChartSVG({ categories: ['a'], series: [{ values: [1] }] }),
    () => priceStripSVG({ price: [1, 2], label: 'GUESS' }),
    () => cliffStripSVG({ events: [], label: 'SOURCED' }),
    () => captionHTML('x', undefined),
  ];
  for (const f of cases) assert.throws(f, ChartLabelError);
  // the admit half: the same calls with a label draw
  assert.match(heatStripSVG({ values: [1, 2], label: 'SIM', days: 1, hours: 2 }), /^<svg/);
  assert.match(priceStripSVG({ price: [1, 2], label: 'REAL' }), /^<svg/);
});

test('charts: loading bands (display only) at the tier lines', () => {
  assert.deepEqual([50, 100, 100.1, 110, 110.1, 150, 150.1].map(band), ['b0', 'b0', 'b1', 'b1', 'b2', 'b2', 'b4']);
  assert.equal(band(NaN), 'na');
  assert.equal(band(undefined), 'na');
});

test('charts: a 31 x 24 heat strip draws 744 cells in the right bands (pct tenths in)', () => {
  const v = Array.from({ length: 744 }, (_, i) => [500, 1050, 1200, 1600][i % 4]);
  const s = heatStripSVG({ values: v, label: 'SIM' });
  assert.equal(count(s, /<rect /g), 744);
  assert.equal(count(s, /class="hs-b0"/g), 186);
  assert.equal(count(s, /class="hs-b1"/g), 186);
  assert.equal(count(s, /class="hs-b2"/g), 186);
  assert.equal(count(s, /class="hs-b4"/g), 186);
  assert.match(s, /day 1 00:00 50%/);
  assert.match(s, /day 1 03:00 160%/);
  const missing = heatStripSVG({ values: [1000], label: 'SIM', days: 1, hours: 2 });
  assert.equal(count(missing, /class="hs-na"/g), 1);
});

test('charts: line chart draws one path per series, breaks on gaps, and draws reference lines', () => {
  const s = lineChartSVG({
    label: 'SIM',
    series: [{ name: 'without', values: [90, 120, null, 80], cls: 's-without' }, { name: 'with', values: [60, 70, 80, 90], cls: 's-with' }],
    refs: [{ y: 100, text: 'nameplate' }, { y: 110, text: 'normal' }, { y: 400, text: 'off the chart' }],
    xTicks: [{ i: 0, text: '00:00' }], yMax: 200,
  });
  assert.equal(count(s, /<path class="lc-line/g), 2);
  const d = /class="lc-line s-without" d="([^"]+)"/.exec(s)[1];
  assert.equal(count(d, /M/g), 2, 'a null breaks the line');
  assert.equal(count(s, /class="lc-ref /g), 2, 'a reference outside the range is skipped');
  assert.match(s, /nameplate/);
  assert.throws(() => lineChartSVG({ label: 'SIM', series: [] }), TypeError);
});

test('charts: bar chart draws only positive bars; histogram mode', () => {
  const s = barChartSVG({ label: 'REAL', categories: ['00', '01', '02'], series: [{ values: [0, 3, 1], cls: 's-price' }] });
  assert.equal(count(s, /<rect class="bc-bar/g), 2);
  assert.equal(modeIndex([0, 3, 1, 3]), 1);
  assert.equal(modeIndex([0, 0]), null);
  assert.equal(modeIndex([]), null);
});

test('charts: price strip and the price-cliff strip on the committed fixture (REAL prices, 27 cliffs, 13 evening)', () => {
  const idx = JSON.parse(fs.readFileSync(path.join(UI, 'data', 'fixtures', 'p2', 'index.json'), 'utf8'));
  const ps = priceStripSVG({ price: idx.price, label: idx.series.price.label, markers: [{ i: 10, text: 'm' }] });
  assert.equal(count(ps, /class="ps-area"/g), 1);
  assert.equal(count(ps, /class="ps-mark"/g), 1);
  const cs = cliffStripSVG({ events: idx.cliffs.events, period: idx.cliffs.period, label: idx.cliffs.count.label });
  assert.equal(count(cs, /<line class="cs-tick/g), idx.cliffs.count.v);
  assert.equal(count(cs, /cs-tick cs-evening/g), idx.cliffs.evening.v);
  assert.equal(idx.cliffs.count.v, 27);
  assert.equal(idx.cliffs.evening.v, 13);
  assert.equal(parseISOmin('2026-01-01T00:15') - parseISOmin('2026-01-01'), 15);
  assert.equal(parseISOmin('nope'), null);
});

test('charts: chartHTML wraps the SVG with a caption carrying the chip; DOM wrappers keep L0 names', () => {
  const h = chartHTML('heat', { values: [1000, 1200], days: 1, hours: 2, label: 'SIM', caption: 'Without the battery' });
  assert.match(h, /^<figure class="hb-fig"><svg/);
  assert.match(h, /<div class="hb-chart-cap">Without the battery<span class="chip chip-SIM">SIM<\/span><\/div><\/figure>$/);
  assert.throws(() => chartHTML('pie', { label: 'SIM' }), TypeError);
  for (const f of [priceStrip, heatStrip, lineChart, barChart, cliffStrip]) assert.equal(f(null, {}), null);
  const el = { innerHTML: '' };
  assert.equal(heatStrip(el, { values: [1], days: 1, hours: 1, label: 'SIM', caption: 'c' }), el);
  assert.match(el.innerHTML, /^<svg.*chip-SIM/s);
});

test('charts: y-axis ticks stay distinct on small ranges (judge R0: the naive capacity curve printed "1, 1, 0")', () => {
  assert.deepEqual(axisTickTexts([0, 0.5, 1]), ['0', '0.5', '1']);
  assert.deepEqual(axisTickTexts([0, 50, 100]), ['0', '50', '100']);
  assert.deepEqual(axisTickTexts([0, 0.05, 0.1]), ['0', '0.05', '0.1']);
  assert.deepEqual(axisTickTexts([2, 2, 2]), ['2', '2', '2']);
  // the chart itself: a 0/1 series (transformers with a battery-caused event) draws three different tick labels
  const svg = lineChartSVG({ series: [{ values: [0, 0, 0, 1] }], label: 'SIM' });
  const ticks = [...svg.matchAll(/<text class="lc-tick"[^>]*text-anchor="end">([^<]*)<\/text>/g)].map((m) => m[1]);
  assert.equal(ticks.length, 3);
  assert.equal(new Set(ticks).size, 3, `duplicate ticks ${ticks}`);
});
