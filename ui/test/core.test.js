// ui/test/core.test.js (L0): the shell's pure pieces and the static-demo check. Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import zlib from 'node:zlib';
import { fmt, fmtHTML, fmtValue, chip, isLabelled, LabelError, pct10, kw10, socPm, timeToStep, stepToTime, hhmmToMin, minToHHMM,
  dateLabel, addDays, dateAtStep } from '../lib/format.js';
import { parseLink, linkQuery, applyBeat, _configure, getWithFixture, getOptional, isFixture, onFixture, HttpError,
  DEFAULT_DATE, SPEEDS, getGz, loadP1MetaFor, loadP1BranchFor, resolveP1Date } from '../lib/data.js';
import * as icons from '../lib/icons.js';
import { LABEL_TIPS, tipHTMLFor, chipLabel, speedTip } from '../lib/tip.js';
import { dayChipHTML, dayRowsHTML, sparklineSVG, calendarStripHTML, netColour } from '../lib/days.js';

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

test('data: round-2 link keys (date, speed, hold, cap, bare): defaults, validation, round trips', () => {
  const d = parseLink('');
  assert.deepEqual([d.date, d.speed, d.hold, d.cap, d.bare], [DEFAULT_DATE, null, true, true, true]);
  assert.equal(DEFAULT_DATE, '2026-08-23');
  assert.deepEqual(SPEEDS, [0.1, 0.25, 0.5, 1, 2, 4]);
  const l = parseLink('?view=p1&date=2026-07-22&branch=naive&t=23:15&speed=0.1&hold=0&cap=0');
  assert.deepEqual([l.date, l.speed, l.hold, l.cap, l.bare], ['2026-07-22', 0.1, false, false, false]);
  assert.deepEqual(parseLink(linkQuery(l)), l);
  for (const q of ['?speed=8', '?speed=abc', '?speed=', '?speed=0']) assert.equal(parseLink(q).speed, null, q);
  for (const q of ['?date=22-07-2026', '?date=2026-7-22', '?date=../../x']) assert.equal(parseLink(q).date, DEFAULT_DATE, q);
  assert.equal(parseLink('?speed=0.25').speed, 0.25);
  assert.equal(parseLink('?hold=1').hold, true);
  // defaults are never written: no date=2026-08-23, no hold=1, no cap=1, no speed
  const q = linkQuery(parseLink('?view=p1&branch=aware&date=2026-08-23'));
  assert.equal(q, '?view=p1&branch=aware');
  assert.ok(!linkQuery(parseLink('?date=2026-08-23&hold=1&cap=1')).includes('date='));
  // bare: only a link that names none of branch, t, beat, date (the first open; beat and derived links are never bare)
  assert.equal(parseLink('?view=p1').bare, true);
  for (const k of ['branch=naive', 't=22:00', 'beat=money', 'date=2026-08-14']) assert.equal(parseLink(`?view=p1&${k}`).bare, false, k);
  assert.equal({ ...parseLink('?view=p1') }.bare, undefined, 'a spread link is not bare');
  assert.ok(!Object.keys(parseLink('')).includes('bare'));
  // every round trip holds, including the P2 and More links
  for (const s of ['', '?view=p2&combo=naive-core-d26-g20&home=p1ulv24700&n=5', '?view=more&beat=money', '?view=p1&branch=aware_faults&t=22:16&cam=street&nowebgl=1&speed=2']) {
    assert.deepEqual(parseLink(linkQuery(parseLink(s))), parseLink(s), s);
  }
});

test('format: calendar dates (weekday computed, clock rolls past midnight)', () => {
  assert.equal(dateLabel('2026-08-23'), 'Sun 23 Aug 2026');
  assert.equal(dateLabel('2026-07-22'), 'Wed 22 Jul 2026');
  assert.equal(dateLabel('2026-08-14'), 'Fri 14 Aug 2026');
  assert.equal(dateLabel('2026-08-23', { year: false }), 'Sun 23 Aug');
  assert.equal(dateLabel('2026-02-30'), null);
  assert.equal(dateLabel('nope'), null);
  assert.equal(addDays('2026-08-31', 1), '2026-09-01');
  const meta = { day: '2026-08-23', start: '16:00', stepSeconds: 60, steps: 720 };
  assert.equal(dateAtStep(meta, 0), '2026-08-23');
  assert.equal(dateAtStep(meta, 479), '2026-08-23');   // 23:59
  assert.equal(dateAtStep(meta, 480), '2026-08-24');   // 00:00
});

test('data: gzipped history files (getGz) and the per-date loaders never fall back to a fixture', async () => {
  const doc = { schema: 'hb.p1-branch.v1', loading: [[1, 2]], label: 'SIM' };
  const gz = zlib.gzipSync(Buffer.from(JSON.stringify(doc)));
  const plain = Buffer.from(JSON.stringify({ plain: true }));
  const files = {
    'data/p1/days/2026-07-22/naive.json.gz': gz, 'data/p1/days/2026-07-22/aware.json.gz': plain,
    'data/p1/days/2026-07-22/meta.json': { day: '2026-07-22' }, 'data/p1/meta.json': { day: '2026-08-23' },
    'data/p1/naive.json': { branch: 'naive' },
    'data/p1/days/index.json': { days: [{ date: '2026-08-23', dir: '' }, { date: '2026-07-22', dir: 'days/2026-07-22', tag: "Texas's record demand" }] },
    'data/fixtures/p1/days/2026-08-14/meta.json': { fixture: true },
  };
  const fetchFn = async (u) => {
    if (!(u in files)) return { ok: false, status: 404, json: async () => null, arrayBuffer: async () => new ArrayBuffer(0) };
    const v = files[u];
    const bytes = Buffer.isBuffer(v) ? v : Buffer.from(JSON.stringify(v));
    return { ok: true, status: 200, json: async () => JSON.parse(bytes.toString()), arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length) };
  };
  _configure({ base: 'data/', fetchFn });
  assert.deepEqual(await getGz('p1/days/2026-07-22/naive.json.gz'), doc);
  assert.deepEqual(await getGz('p1/days/2026-07-22/aware.json.gz'), { plain: true }, 'a host that already gunzipped');
  assert.deepEqual(await loadP1BranchFor('2026-07-22', 'naive'), doc);
  assert.deepEqual(await loadP1BranchFor(DEFAULT_DATE, 'naive'), { branch: 'naive' });
  assert.deepEqual(await loadP1MetaFor('2026-07-22'), { day: '2026-07-22' });
  assert.deepEqual(await loadP1MetaFor(DEFAULT_DATE), { day: '2026-08-23' });
  await assert.rejects(loadP1MetaFor('2026-08-14'), HttpError);   // no fixture for a history day
  assert.equal(isFixture(), false);
  const hit = await resolveP1Date('2026-07-22');
  assert.deepEqual([hit.date, hit.simulated, hit.faults, hit.notice], ['2026-07-22', true, false, null]);
  const miss = await resolveP1Date('2026-01-01');
  assert.deepEqual([miss.date, miss.simulated], [DEFAULT_DATE, false]);
  assert.equal(miss.notice, 'Thu 1 Jan 2026 is not simulated; showing Sun 23 Aug 2026.');
  assert.equal((await resolveP1Date(DEFAULT_DATE)).faults, true);
  _configure({ base: 'data/', fetchFn: async () => ({ ok: false, status: 404, json: async () => null }) });
  assert.equal((await resolveP1Date('2026-07-22')).simulated, false, 'no index yet: every other date is a notice');
});

test('icons: every path is well-formed SVG; meter and battery ids; tier words; sage tier 0 and violet selling', () => {
  const pathRe = /^[MmLlHhVvCcSsQqTtAaZz0-9.,\s-]+$/;
  const names = [...Object.keys(icons.PATHS), ...Object.keys(icons.ALIASES)];
  for (const name of names) {
    const paths = icons.pathsFor(name);
    assert.ok(Array.isArray(paths) && paths.length, name);
    for (const d of paths) assert.match(d.replace(/^f:/, ''), pathRe, `${name}: ${d}`);
    const s = icons.svg(name, { title: 'x <y>' });
    assert.match(s, /^<svg [^>]*viewBox="0 0 24 24"[^>]*>.*<\/svg>$/s, name);
    assert.equal((s.match(/<path /g) || []).length, paths.length, name);
    assert.ok(s.includes('<title>x &lt;y&gt;</title>'));
  }
  for (const [st, lvl] of [['C', 0.5], ['D', 1], ['I', 0], ['S', 0.3], ['X', 0.2], ['B', 0.9]]) {
    assert.match(icons.svg('battery', { state: st, level: lvl }), /^<svg [^>]*class="ic ic-battery s-[A-Z] ?[^"]*"[^>]*>.*<\/svg>$/s);
  }
  for (const [pct, tier] of [[0, 0], [97.8, 0], [122.1, 2], [201.2, 4], [260, 5]]) {
    const m = icons.svg('meter', { pct, tier });
    assert.match(m, /^<svg [^>]*class="ic ic-meter t\d[^"]*"[^>]*>.*<\/svg>$/s);
  }
  assert.ok(icons.svg('meter', { pct: 120, tier: 2, homeKW: 30, batKW: 10 }).includes('m-bat'), 'split fill');
  assert.ok(icons.svg('meter', { pct: 90, tier: 0, exporting: true }).includes('exporting'));
  assert.equal(icons.meterGeom(200).overTop, 2);
  assert.equal(icons.batteryId('C', 0.47), 'bat-C-5');
  assert.equal(icons.batteryId('?', 2), 'bat-I-10');
  assert.equal(icons.meterId(4, 201.2), 'm-4-200');
  assert.equal(icons.meterId(2, 122.1), 'm-2-120');
  assert.equal(icons.meterId(9, -5), 'm-5-0');
  const ids = icons.atlasIds().map((x) => x[1]);
  for (const id of [icons.batteryId('D', 0.9), icons.meterId(4, 201.2), 'g-turns', 'g-check']) assert.ok(ids.includes(id), id);
  assert.equal(new Set(ids).size, ids.length, 'atlas ids unique');
  assert.equal(icons.TIER_WORDS.length, 6);
  assert.equal(icons.TIER_TIPS.length, 6);
  assert.deepEqual(icons.TIER_WORDS, ['Within rating', 'Over', 'Overloaded', 'Overloaded 30+ min', 'Emergency', 'Fuse open']);
  assert.match(icons.TIER_TIPS[3], /30 minutes/);
  assert.deepEqual(icons.TIER_RGB[0], [138, 165, 143], 'green never means safe: tier 0 is sage');
  assert.ok(!icons.TIER_RGB.some((c) => String(c) === String(icons.STATE_RGB.D)), 'selling violet is not a tier colour');
  for (const k of 'CDISXB') assert.ok(icons.STATE_WORDS[k], k);
  const leg = icons.legendHTML({ cls: 'p1-legend', foot: 'Objects not to scale' });
  assert.match(leg, /^<details class="hb-legend p1-legend" open>/);
  for (const w of ['home', 'battery (fill = charge)', 'transformer on the ground', 'transformer on a pole', 'R S D A']) assert.ok(leg.includes(w), w);
});

test('tip: label tips, what an element says, speed copy', () => {
  assert.deepEqual(Object.keys(LABEL_TIPS), ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION']);
  const el = (attrs, cls = '', text = '') => ({ getAttribute: (k) => (k in attrs ? attrs[k] : null), classList: { contains: (c) => cls.split(' ').includes(c) }, textContent: text });
  // a provenance tag: the label line in bold, then the cite (escaped)
  const c = el({ class: 'chip chip-SIM', title: 'OpenDSS <solve>' }, 'chip chip-SIM', 'SIM');
  assert.equal(chipLabel(c), 'SIM');
  assert.equal(tipHTMLFor(c), `<div class="tip-h">${LABEL_TIPS.SIM}</div><div class="tip-sub">OpenDSS &lt;solve&gt;</div>`);
  // after the first hover the title has moved to data-cite: the same tip
  assert.equal(tipHTMLFor(el({ class: 'chip chip-REAL', 'data-cite': 'ERCOT' }, 'chip chip-REAL', 'REAL')), `<div class="tip-h">${LABEL_TIPS.REAL}</div><div class="tip-sub">ERCOT</div>`);
  assert.equal(tipHTMLFor(el({ 'data-tip': 'a < b' })), 'a &lt; b');
  assert.equal(tipHTMLFor(el({ 'data-tip-html': '<b>ok</b>', 'data-tip': 'ignored' })), '<b>ok</b>');
  assert.equal(tipHTMLFor(el({ title: 'plain' })), 'plain');
  assert.equal(tipHTMLFor(el({})), null);
  assert.equal(tipHTMLFor(null), null);
  // every provenance tag the formatter emits has a tip
  for (const L of Object.keys(LABEL_TIPS)) assert.match(chip(L, 'cite'), new RegExp(`class="chip chip-${L}"`));
  assert.equal(speedTip(0.1), '0.1×: 1 simulated minute per second (the evening in 12 min)');
  assert.equal(speedTip(0.25), '0.25×: 2.5 simulated minutes per second (the evening in 4 min 48 s)');
  assert.equal(speedTip(1), '1×: 10 simulated minutes per second (the evening in 72 s)');
});

test('days: the day chip and the popover rows read index.json only, with labels from it', () => {
  const index = {
    series: { sparkline: { label: 'REAL', unit: '$/MWh' } },
    days: [
      { date: '2026-08-23', tag: 'The demo evening', dir: '', sparkline: [30, 40, 566, 55], perBattery: { aware: { v: 9.55, label: 'DERIVED' } },
        naiveMax: { v: 201.2, label: 'SIM', tf: 'A', t: '22:30', tier: 4 }, awareBatteryCaused: { v: 0, label: 'SIM' } },
      { date: '2026-07-22', tag: "Texas's record demand", dir: 'days/2026-07-22', sparkline: [1, 2, 3], perBattery: { aware: { v: 3.1, label: 'DERIVED' } },
        naiveMax: { v: 150.5, label: 'SIM', tf: 240, t: '23:15' }, awareBatteryCaused: { v: 0, label: 'SIM' } },
    ],
  };
  const chipH = dayChipHTML(index, '2026-07-22');
  assert.ok(chipH.includes('Wed 22 Jul 2026'));
  assert.ok(chipH.includes('Texas&#39;s record demand'));
  assert.match(chipH, /chip chip-REAL/);
  assert.ok(dayChipHTML(null, '2026-08-23').includes('Sun 23 Aug 2026'), 'no index yet: the date alone');
  const rows = dayRowsHTML(index, '2026-07-22');
  assert.equal((rows.match(/<li>/g) || []).length, 2);
  assert.match(rows, /data-date="2026-07-22" aria-current="true"/);
  assert.ok(rows.includes('Sun 23 Aug 2026') && rows.includes('Wed 22 Jul 2026'));
  assert.match(rows, /<span class="num">\$9\.55<\/span><span class="chip chip-DERIVED"/);
  assert.ok(rows.includes('on T-240'), 'a transformer index reads T-<index>');
  // no bare digits: every number in a row sits in <span class="num"> (tooltips and svg geometry aside)
  const visible = rows.replace(/<svg[\s\S]*?<\/svg>/g, '').replace(/data-[a-z-]+="[^"]*"/g, '').replace(/<span class="num">[^<]*<\/span>/g, '')
    .replace(/<[^>]+>/g, ' ').replace(/&#?\w+;/g, '').replace(/\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b/g, '');
  assert.doesNotMatch(visible, /\d/, visible);
  assert.match(sparklineSVG([1, 2, 3]), /^<svg class="hb-spark"/);
  assert.equal(sparklineSVG([1]), '');
});

test('days: the money calendar strip (A.9h): a cell per evening, sim days clickable, labels from series', () => {
  const cal = { from: '2026-07-30', n: 5, net: [1234, -56, null, 0, 90000], sold: [], bought: [], peak: [56642, 3000, null, 2500, 78072],
    peakT: '2100 1845 - 1900 2215', onset: '2200 2130 - 2200 2300', mode: 'bb-bb', negMin: [0, 15, 0, 0, 0],
    sim: { '2026-08-23': '', '2026-08-01': 'days/2026-08-01' }, gaps: [{ day: '2026-08-01', reason: 'DST test gap' }],
    headline: { perBattery2026ytd: { v: 284.68, label: 'DERIVED' }, top10Share2026: { v: 55, label: 'DERIVED' }, losingNights2026: { v: 85, label: 'DERIVED' } },
    series: { net: { label: 'DERIVED' }, peak: { label: 'REAL' }, negMin: { label: 'REAL' } } };
  const h = calendarStripHTML(cal, '2026-08-03');
  assert.equal((h.match(/class="hb-cal-cell[^"]*" data-date=/g) || []).length, 5);
  assert.equal((h.match(/class="hb-cal-row"/g) || []).length, 2, 'Jul and Aug rows');
  assert.match(h, /<button type="button" class="hb-cal-cell gap sim" data-date="2026-08-01"/);
  assert.match(h, /class="hb-cal-cell lose paid" data-date="2026-07-31"/);
  assert.match(h, /class="hb-cal-cell cur" data-date="2026-08-03"/);
  assert.ok(h.includes('DST test gap'));
  assert.ok(h.includes('a smart dispatcher sits out'));
  assert.ok(h.includes('$284.68') && h.includes('chip-DERIVED'));
  assert.ok(h.includes('566.42 $/MWh') && h.includes('at 21:00'));
  assert.deepEqual(netColour(-1, 10), [125, 147, 178]);
  assert.deepEqual(netColour(10, 10), [184, 134, 11]);
  assert.equal(netColour(null, 10), null);
  assert.equal(calendarStripHTML(null), '');
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

// scripts/deeplinks.txt is derived from committed data (build prompt 7.5; C3 "every beat link is smoke-ok").
// These keep it derived: when a producer's data changes a link, this fails until a lead PR regenerates the line.
const REPO = path.resolve(UI, '..');
const readJSON = (p) => (fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null);
function deeplinks() {
  return fs.readFileSync(path.join(REPO, 'scripts', 'deeplinks.txt'), 'utf8').split('\n')
    .map((l) => l.trim()).filter((l) => l && !l.startsWith('#'))
    .map((l) => { const i = l.indexOf(' '); return { tags: l.slice(0, i).split(','), query: l.slice(i + 1).trim() }; });
}
const param = (q, k) => new URLSearchParams(q).get(k);

test('deeplinks: exactly three canaries, one P1, one P2 (the default combo) and view=more', () => {
  const c = deeplinks().filter((d) => d.tags.includes('canary'));
  assert.deepEqual(c.map((d) => param(d.query, 'view')), ['p1', 'p2', 'more']);
  const idx = readJSON(path.join(UI, 'data', 'p2', 'index.json'));
  if (idx) assert.equal(param(c[1].query, 'combo'), idx.default);
});

test('deeplinks: one beat line per ui/data/beats.json beat ("<link>&beat=<id>", same order), none without it', () => {
  const beats = readJSON(path.join(UI, 'data', 'beats.json'));
  const got = deeplinks().filter((d) => d.tags.includes('beat')).map((d) => d.query);
  const want = beats ? beats.beats.map((b) => `${b.link}&beat=${b.id}`) : [];
  assert.deepEqual(got, want, 'regenerate the beat lines of scripts/deeplinks.txt from ui/data/beats.json (a lead PR)');
});

test('deeplinks: every P2 combo in p2/index.json, the home= link at its measured top 1, aware_faults at Tc+16', () => {
  const links = deeplinks().filter((d) => !d.tags.includes('beat')).map((d) => d.query);
  const idx = readJSON(path.join(UI, 'data', 'p2', 'index.json'));
  if (idx) {
    const plain = links.filter((q) => param(q, 'view') === 'p2' && !param(q, 'home') && !param(q, 'n')).map((q) => param(q, 'combo'));
    assert.deepEqual([...plain].sort(), [...idx.combos].sort());
    const topo = readJSON(path.join(UI, 'data', 'topology.json'));
    const h = readJSON(path.join(UI, 'data', 'p2', `${idx.default}.json`)).ranking[0].home;
    const top = typeof h === 'number' ? topo.homes[h].id : h;
    const homeLinks = links.filter((q) => param(q, 'home'));
    assert.ok(homeLinks.length >= 1, 'a P2 home= link');
    for (const q of homeLinks) assert.equal(param(q, 'home'), top, `home= must be ${idx.default}'s rank 1`);
  }
  const meta = readJSON(path.join(UI, 'data', 'p1', 'meta.json'));
  if (meta && meta.tc) {
    const f = links.filter((q) => param(q, 'branch') === 'aware_faults');
    assert.ok(f.length >= 1, 'an aware_faults link');
    for (const q of f) assert.equal(param(q, 't'), minToHHMM(hhmmToMin(meta.tc.t) + 16), 'aware_faults t = Tc + 16 (meta.tc)');
  }
});
