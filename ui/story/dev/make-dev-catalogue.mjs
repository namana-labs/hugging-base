#!/usr/bin/env node
// ui/story/dev/make-dev-catalogue.mjs (UI-A, dev only): a contract-shaped story catalogue (docs/story-contract.md,
// `ui/data/story/index.json`, schema hb.story.v1) built from COMMITTED files only, so the story pages can be built and
// smoke-tested before ENGINE's sim.scenarios writes the real one. It never invents a number: every value is copied
// from ui/data/p1/meta.json, ui/data/p1/days/**, ui/data/engine.json or mpalacios/out/** (the two runtime files the
// contract says ENGINE copies into ui/data), with its label and cite.
//
//   node ui/story/dev/make-dev-catalogue.mjs            writes ui/data/story/dev-catalogue.json
//   open ui/index.html?cat=story/dev-catalogue.json     (the app also falls back to it, with a visible notice,
//                                                         while ui/data/story/index.json does not exist)
//
// What the dev catalogue can play: 23 Aug none/naive/aware/aware+faults (p1/*.json), the three history evenings'
// none/naive/aware (p1/days/<date>/*.json.gz), worker_kill and covert (from mpalacios/out/, outside ui/data: fine on
// the dev server, which serves the repo root). The fleet variants are listed as unavailable ("not built yet").
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { dateLabel } from '../../lib/format.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI = path.resolve(HERE, '..', '..');
const DATA = path.join(UI, 'data');
const REPO = path.resolve(UI, '..');
const read = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

// The lever sets of the story contract's ruling 1 (docs/story-contract.md). ENGINE's catalogue replaces this file;
// the UI reads the sets from whichever catalogue it loads and never types them.
const RULING_1 = {
  fleet: [48, 96, 144, 192], cls: ['core', 'legacy'], reserve: [20, 30, 40, 50], soc0: [60, 75, 90, 100], growth: [0, 20, 50],
};
const CONTRACT = 'docs/story-contract.md ruling 1';

const topo = read(path.join(DATA, 'topology.json'));
const days = read(path.join(DATA, 'p1', 'days', 'index.json'));
const engine = read(path.join(DATA, 'engine.json'));
const meta23 = read(path.join(DATA, 'p1', 'meta.json'));
const DEFAULT_DATE = days.default;

// defaults, all from committed data
const DEF = {
  evening: DEFAULT_DATE,
  policy: 'aware',
  failure: 'none',
  fleet: topo.fleet.length,                                           // topology.json fleet[] (the committed 96)
  cls: 'core',                                                        // every committed battery is a Core (topology homes[].battery.cls)
  reserve: Math.round(meta23.constants.RESERVE_FLOOR.value * 100),    // RESERVE_FLOOR (REAL)
  soc0: Math.round(meta23.constants.SOC0.value * 100),                // SOC0 (ASSUMPTION)
  growth: 0,                                                          // P1 runs today's load
};
for (const k of ['fleet', 'reserve', 'soc0', 'growth']) {
  if (!RULING_1[k].includes(DEF[k])) throw new Error(`default ${k}=${DEF[k]} is not in the ruling's set`);
}
const clsSeen = new Set(topo.homes.filter((h) => h.battery).map((h) => h.battery.cls));
if (clsSeen.size !== 1 || !clsSeen.has(DEF.cls)) throw new Error(`fleet classes ${[...clsSeen]} are not all ${DEF.cls}`);

const POLICY = { none: 'No batteries', naive: 'Naive split', aware: 'Feeder-aware' };
const FAILURE = { none: 'No failures', faults: 'Pieces fail', worker_kill: 'Controller crash', covert: 'Hidden attacker' };
const CLS = { core: 'Core', legacy: 'Legacy' };
const c = meta23.constants;

const levers = {
  evening: {
    label: 'Evening', default: DEF.evening,
    options: days.days.map((d) => ({ id: d.date, label: dateLabel(d.date, { year: false }), tag: d.tag, why: d.why, peak: d.peak })),
  },
  policy: {
    label: 'Dispatch policy', default: DEF.policy,
    options: [
      { id: 'none', label: POLICY.none },
      { id: 'naive', label: POLICY.naive, why: { text: meta23.naiveLabel.text, label: meta23.naiveLabel.label, cite: meta23.naiveLabel.cite } },
      { id: 'aware', label: POLICY.aware },
    ],
  },
  failure: {
    label: 'Failures', default: DEF.failure,
    options: [
      { id: 'none', label: FAILURE.none },
      { id: 'faults', label: FAILURE.faults, why: { text: (meta23.events.aware_faults || []).map((e) => e.text).join('; '), label: 'ASSUMPTION', cite: 'p1/meta.json events.aware_faults' } },
      { id: 'worker_kill', label: FAILURE.worker_kill },
      { id: 'covert', label: FAILURE.covert },
    ],
  },
  fleet: { label: 'Fleet size', default: DEF.fleet, options: RULING_1.fleet.map((v) => ({ id: v, label: String(v) })) },
  cls: {
    label: 'Battery class', default: DEF.cls,
    options: [
      { id: 'core', label: CLS.core, why: { text: `${c.CORE_POWER_KW.value} kW · ${c.CORE_USABLE_KWH.value} kWh`, label: c.CORE_POWER_KW.label, cite: `CORE_POWER_KW: ${c.CORE_POWER_KW.cite}; CORE_USABLE_KWH: ${c.CORE_USABLE_KWH.cite}` } },
      { id: 'legacy', label: CLS.legacy },
    ],
  },
  reserve: { label: 'Member reserve', default: DEF.reserve, options: RULING_1.reserve.map((v) => ({ id: v, label: `${v}%` })) },
  soc0: { label: 'Starting charge', default: DEF.soc0, options: RULING_1.soc0.map((v) => ({ id: v, label: `${v}%` })) },
  growth: { label: 'Home-load growth', default: DEF.growth, options: RULING_1.growth.map((v) => ({ id: v, label: `+${v}%` })) },
};

const scenarios = [];
const idOf = (l) => `${l.evening}/${l.policy}${l.failure !== 'none' ? `/${l.failure}` : ''}`;
function add(l, files, extra = {}) {
  const levs = { ...DEF, ...l };
  const b = files.branchDoc;
  scenarios.push({
    id: idOf(levs),
    title: [dateLabel(levs.evening, { year: false }), POLICY[levs.policy], levs.failure !== 'none' ? FAILURE[levs.failure] : null].filter(Boolean).join(' · '),
    ...(extra.preset ? { preset: extra.preset } : {}),
    levers: levs,
    meta: files.meta, branch: files.branch, extras: null, compare: files.compare, gz: /\.gz$/.test(files.branch),
    summary: files.summary,
    engine: files.engine,
    ...(extra.more || {}),
  });
  return b;
}

const PRESETS = { [`${DEFAULT_DATE}/aware`]: 'The demo evening', [`${DEFAULT_DATE}/aware/faults`]: 'Pieces fail',
  [`${DEFAULT_DATE}/aware/worker_kill`]: 'Controller crash', [`${DEFAULT_DATE}/aware/covert`]: 'Hidden attacker' };
// the history presets: the rows whose tags name the record-demand and the priciest evening (p1/days/index.json)
const byTag = (re) => (days.days.find((d) => re.test(d.tag)) || {}).date;
if (byTag(/record demand/i)) PRESETS[`${byTag(/record demand/i)}/aware`] = 'Record demand';
if (byTag(/priciest/i)) PRESETS[`${byTag(/priciest/i)}/aware`] = 'Priciest evening';

for (const d of days.days) {
  const dir = d.dir ? `p1/${d.dir}` : 'p1';
  const metaPath = `${dir}/meta.json`;
  const meta = read(path.join(DATA, metaPath));
  const bpath = (b) => (d.dir ? `${dir}/${b}.json.gz` : `${dir}/${b}.json`);
  const compare = {};
  for (const b of ['none', 'naive', 'aware']) if (d.branches.includes(b)) compare[b] = bpath(b);
  // the engine's measured cost: solves per evening build (meta.engine, SIM); build seconds only for 23 Aug (engine.json,
  // DERIVED, the whole 4-branch build: the cite says so). A history evening has no measured seconds.
  const eng = {
    buildSeconds: d.dir ? null : { ...engine.p1.buildSeconds },
    solves: { ...meta.engine.solves },
  };
  for (const b of ['none', 'naive', 'aware']) {
    if (!d.branches.includes(b)) continue;
    const id = `${d.date}/${b}`;
    add({ evening: d.date, policy: b }, { meta: metaPath, branch: bpath(b), compare, summary: meta.summary[b], engine: eng },
      { preset: PRESETS[id] });
  }
  if (d.branches.includes('aware_faults')) {
    add({ evening: d.date, policy: 'aware', failure: 'faults' },
      { meta: metaPath, branch: `${dir}/aware_faults.json`, compare, summary: meta.summary.aware_faults, engine: eng },
      { preset: PRESETS[`${d.date}/aware/faults`] });
  }
  if (!d.dir) {
    // the runtime files (A.6b, A.11), read where they are committed today; ENGINE copies them to p1/worker_kill.json and
    // p3/covert.json. Paths are relative to ui/data, so "../../mpalacios/..." is the repo's mpalacios/ on the dev server.
    const wkRel = '../../mpalacios/out/p1/worker_kill.json', cvRel = '../../mpalacios/out/p3/covert.json';
    const wk = read(path.join(DATA, wkRel));
    const cv = read(path.join(DATA, cvRel));
    const ws = {};
    for (const k of Object.keys(meta.summary.aware)) if (wk.summary[k] !== undefined) ws[k] = wk.summary[k];
    add({ evening: d.date, policy: 'aware', failure: 'worker_kill' },
      { meta: metaPath, branch: wkRel, compare, summary: ws, engine: { buildSeconds: null, solves: null } },
      { preset: PRESETS[`${d.date}/aware/worker_kill`] });
    add({ evening: d.date, policy: 'aware', failure: 'covert' },
      { meta: metaPath, branch: bpath('aware'), compare, summary: meta.summary.aware, engine: eng },
      { preset: PRESETS[`${d.date}/aware/covert`], more: { covert: cvRel, attacker: cv.sources.adversary } });
  }
}

const unavailable = [];
for (const k of ['fleet', 'cls', 'reserve', 'soc0', 'growth']) {
  for (const o of levers[k].options) {
    if (o.id === DEF[k]) continue;
    unavailable.push({ levers: { [k]: o.id }, reason: `Not built yet: the engine has not written p1/variants/${k}=${o.id} (dev catalogue: committed files only)` });
  }
}
unavailable.push({ levers: { failure: 'faults', policy: 'naive' }, reason: 'Failures are run with feeder-aware control only' });
unavailable.push({ levers: { failure: 'worker_kill', policy: 'naive' }, reason: 'The controller crash is a feeder-aware run' });
unavailable.push({ levers: { failure: 'covert', policy: 'naive' }, reason: 'The hidden attacker plays the feeder-aware evening' });
for (const f of ['faults', 'worker_kill', 'covert']) unavailable.push({ levers: { failure: f, policy: 'none' }, reason: 'No batteries, so nothing to fail' });
for (const d of days.days) {
  if (d.date === DEFAULT_DATE) continue;
  for (const f of ['faults', 'worker_kill', 'covert']) unavailable.push({ levers: { evening: d.date, failure: f }, reason: `Failures exist on ${dateLabel(DEFAULT_DATE, { year: false })} only` });
}

const doc = {
  schema: 'hb.story.v1', producer: 'scripts.make_dev_catalogue',
  inputs: { prices_sha256: null, loads_sha256: null, topology_sha256: null },
  constants: {},
  sources: {
    catalogue: { label: 'DERIVED', text: 'DEV CATALOGUE: built by ui/story/dev/make-dev-catalogue.mjs from committed files only; ENGINE\'s sim.scenarios writes story/index.json' },
    days: { label: 'REAL', text: 'p1/days/index.json (evening tags, why, peak price)' },
  },
  series: {},
  dev: true,
  default: `${DEFAULT_DATE}/aware`,
  levers, scenarios, unavailable,
};
if (!scenarios.some((s) => s.id === doc.default)) throw new Error('default scenario missing');
const out = path.join(DATA, 'story', 'dev-catalogue.json');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(doc));
console.log(`wrote ${path.relative(REPO, out)}: ${scenarios.length} scenarios, ${unavailable.length} unavailable rules, ${fs.statSync(out).size} bytes`);
