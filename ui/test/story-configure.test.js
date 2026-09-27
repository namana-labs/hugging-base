// ui/test/story-configure.test.js (UI-A): Configure's lever logic (ui/story/configure.js) against a catalogue fixture in
// the hb.story.v1 shape (docs/story-contract.md), the committed dev catalogue, and ENGINE's ui/data/story/index.json
// when it exists. Run: node --test ui/test/*.test.js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LEVER_KEYS, FLEET_KEYS, ONE_LEVER_REASON, NO_BATTERIES_REASON, NOT_RUN_REASON, defaultLevers, scenarioFor, scenarioById,
  unavailableReason, optionState, applyLever, presets, presetOf, offDefault } from '../story/configure.js';

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJSON = (p) => JSON.parse(fs.readFileSync(path.join(UI, 'data', p), 'utf8'));

// ---- the fixture: two evenings built, one not; fleet levers one away from the default on the first evening only ----
const E1 = '2026-08-23', E2 = '2026-07-22', E3 = '2026-08-26';
const LEVERS = {
  evening: { label: 'Evening', default: E1, options: [{ id: E1, label: '23 Aug 2026', tag: 'The evening we know best' }, { id: E2, label: '22 Jul 2026' }, { id: E3, label: '26 Aug 2026' }] },
  policy: { label: 'Charging policy', default: 'aware', options: [{ id: 'none', label: 'No batteries' }, { id: 'naive', label: 'Naive: our assumption of one number, no feeder check' }, { id: 'aware', label: 'Feeder-aware' }] },
  failure: { label: 'Failures', default: 'none', options: [{ id: 'none', label: 'No failures' }, { id: 'faults', label: 'Pieces fail: silent battery, EV spike, controller stall' }] },
  fleet: { label: 'Fleet size', default: 96, options: [{ id: 48, label: '48 batteries' }, { id: 96, label: '96 batteries' }, { id: 192, label: '192 batteries' }] },
  cls: { label: 'Battery class', default: 'core', options: [{ id: 'core', label: 'Core (20 kW, 37 kWh)' }, { id: 'legacy', label: 'Legacy (11.4 kW, 22.5 kWh)' }] },
  reserve: { label: 'Member reserve', default: 20, options: [{ id: 20, label: '20% reserve' }, { id: 30, label: '30% reserve' }] },
  soc0: { label: 'Start charge', default: 90, options: [{ id: 90, label: '90% at 16:00' }] },
  growth: { label: 'Home-load growth', default: 0, options: [{ id: 0, label: "Today's load" }, { id: 20, label: '+20% home load' }] },
};
const DEF = { evening: E1, policy: 'aware', failure: 'none', fleet: 96, cls: 'core', reserve: 20, soc0: 90, growth: 0 };
function fixture() {
  const scenarios = [];
  const add = (id, levers, extra = {}) => scenarios.push({ id, title: id, levers: { ...DEF, ...levers }, meta: 'p1/meta.json', branch: 'p1/aware.json', ...extra });
  for (const e of [E1, E2]) for (const p of ['none', 'naive', 'aware']) add(`${e}/${p}`, { evening: e, policy: p });
  add(`${E1}/aware/faults`, { failure: 'faults' });
  for (const [k, vals] of [['fleet', [48, 192]], ['cls', ['legacy']], ['reserve', [30]]]) {
    for (const v of vals) {
      for (const p of ['naive', 'aware']) add(`${E1}/${p}/${k}=${v}`, { policy: p, [k]: v });
      add(`${E1}/none/${k}=${v}`, { policy: 'none', [k]: v }, { alias: `${E1}/none` });    // no batteries: the none run
    }
  }
  for (const p of ['none', 'naive', 'aware']) add(`${E1}/${p}/growth=20`, { policy: p, growth: 20 });
  const pairs = [];
  const off = { fleet: [48, 192], cls: ['legacy'], reserve: [30], growth: [20] };
  const keys = Object.keys(off);
  for (let i = 0; i < keys.length; i++) for (let j = i + 1; j < keys.length; j++) {
    pairs.push({ levers: { [keys[i]]: off[keys[i]], [keys[j]]: off[keys[j]] }, reason: 'One lever away from the default at a time: each fleet lever is its own engine run' });
  }
  return {
    schema: 'hb.story.v1', default: `${E1}/aware`, levers: LEVERS, leverOrder: LEVER_KEYS,
    presets: [{ name: 'The demo evening', id: `${E1}/aware` }, { name: 'Pieces fail', id: `${E1}/aware/faults` }, { name: 'Gone', id: `${E1}/aware/nope` }],
    scenarios,
    unavailable: [
      { levers: { evening: [E3] }, reason: "This evening's Results exports are not built yet" },
      { levers: { evening: [E2, E3], failure: ['faults'] }, reason: 'Failures are scripted on 23 Aug only' },
      { levers: { policy: ['none', 'naive'], failure: ['faults'] }, reason: 'Failures test the feeder-aware controller: choose Feeder-aware' },
      ...keys.map((k) => ({ levers: { evening: [E2, E3], [k]: off[k] }, reason: 'Fleet levers were run on 23 Aug only' })),
      ...keys.map((k) => ({ levers: { failure: ['faults'], [k]: off[k] }, reason: 'Failures run with the default fleet only: set this lever back to its default' })),
      ...pairs,
    ],
  };
}
const at = (cat, id) => scenarioById(cat, id).levers;

test('configure: unavailableReason follows the catalogue match rule (a list = any of; every lever must match)', () => {
  const cat = fixture();
  assert.equal(unavailableReason(cat, { ...DEF, evening: E3 }), "This evening's Results exports are not built yet");
  assert.equal(unavailableReason(cat, { ...DEF, policy: 'naive', failure: 'faults' }), 'Failures test the feeder-aware controller: choose Feeder-aware');
  assert.equal(unavailableReason(cat, { ...DEF, evening: E2, fleet: 192 }), 'Fleet levers were run on 23 Aug only');
  assert.equal(unavailableReason(cat, { ...DEF, fleet: 48, cls: 'legacy' }), 'One lever away from the default at a time: each fleet lever is its own engine run');
  assert.equal(unavailableReason(cat, DEF), null);
  assert.equal(unavailableReason(cat, { ...DEF, fleet: 144 }), null, 'an id the rows do not list');
  // ids compare as strings: 48 and "48" are one option
  assert.equal(unavailableReason(cat, { ...DEF, evening: E2, fleet: '48' }), 'Fleet levers were run on 23 Aug only');
  // the single-value form of the dev catalogue still matches
  assert.equal(unavailableReason({ unavailable: [{ levers: { fleet: 48 }, reason: 'x' }] }, { fleet: '48' }), 'x');
});

test('configure: every lever option comes from the catalogue; the defaults are its defaults', () => {
  const cat = fixture();
  assert.deepEqual(defaultLevers(cat), DEF);
  assert.equal(scenarioFor(cat, DEF).id, cat.default);
  assert.deepEqual(offDefault(cat, at(cat, `${E1}/aware/fleet=48`)), ['fleet']);
  assert.deepEqual(offDefault(cat, DEF), []);
});

test('configure: a reachable setting moves to its catalogue run; the selected option is marked', () => {
  const cat = fixture();
  const sel = optionState(cat, DEF, 'policy', 'aware');
  assert.equal(sel.selected, true);
  const st = optionState(cat, DEF, 'policy', 'naive');
  assert.equal(st.enabled, true);
  assert.equal(st.scenario.id, `${E1}/naive`);
  assert.deepEqual(st.changes, []);
  assert.equal(optionState(cat, DEF, 'evening', E2).scenario.id, `${E2}/aware`);
  assert.equal(optionState(cat, DEF, 'failure', 'faults').scenario.id, `${E1}/aware/faults`);
  assert.equal(optionState(cat, DEF, 'fleet', '192').scenario.id, `${E1}/aware/fleet=192`, 'a string id from a data-val attribute');
});

test('configure: anything not run is disabled with the catalogue reason, never moved behind the user', () => {
  const cat = fixture();
  const e3 = optionState(cat, DEF, 'evening', E3);
  assert.equal(e3.enabled, false);
  assert.equal(e3.reason, "This evening's Results exports are not built yet");
  assert.equal(e3.scenario, null);
  assert.equal(optionState(cat, at(cat, `${E1}/naive`), 'failure', 'faults').reason, 'Failures test the feeder-aware controller: choose Feeder-aware');
  assert.equal(optionState(cat, at(cat, `${E1}/aware/faults`), 'policy', 'naive').reason, 'Failures test the feeder-aware controller: choose Feeder-aware');
  assert.equal(optionState(cat, at(cat, `${E1}/aware/faults`), 'evening', E2).reason, 'Failures are scripted on 23 Aug only');
  assert.equal(optionState(cat, at(cat, `${E1}/aware/fleet=48`), 'evening', E2).reason, 'Fleet levers were run on 23 Aug only');
  assert.equal(optionState(cat, at(cat, `${E2}/aware`), 'fleet', 48).reason, 'Fleet levers were run on 23 Aug only');
  assert.equal(optionState(cat, at(cat, `${E1}/aware/faults`), 'fleet', 48).reason, 'Failures run with the default fleet only: set this lever back to its default');
  assert.equal(applyLever(cat, DEF, 'evening', E3), null);
  // a setting no row explains
  const bare = { ...fixture(), unavailable: [] };
  assert.equal(optionState(bare, DEF, 'evening', E3).reason, NOT_RUN_REASON);
});

test('configure: the one-lever rule resets the other fleet lever to its default, with a note', () => {
  const cat = fixture();
  const from = at(cat, `${E1}/aware/fleet=48`);
  const st = optionState(cat, from, 'cls', 'legacy');
  assert.equal(st.enabled, true);
  assert.equal(st.scenario.id, `${E1}/aware/cls=legacy`);
  assert.deepEqual(st.changes, [{ key: 'fleet', from: 48, to: 96, reason: ONE_LEVER_REASON }]);
  const res = applyLever(cat, from, 'cls', 'legacy');
  assert.equal(res.scenario.id, `${E1}/aware/cls=legacy`);
  assert.deepEqual(res.notes, [`Fleet size back to 96 batteries: ${ONE_LEVER_REASON}.`]);
  // moving the same lever, or back to a default, resets nothing
  assert.deepEqual(optionState(cat, from, 'fleet', 192).changes, []);
  assert.equal(optionState(cat, from, 'fleet', 192).scenario.id, `${E1}/aware/fleet=192`);
  assert.equal(optionState(cat, from, 'fleet', 96).scenario.id, `${E1}/aware`);
  // growth is a fleet lever too (ruling 1), and the rule never leaves two levers off the default
  const g = applyLever(cat, at(cat, `${E1}/naive/reserve=30`), 'growth', 20);
  assert.equal(g.scenario.id, `${E1}/naive/growth=20`);
  assert.deepEqual(offDefault(cat, g.levers), ['growth']);
  for (const s of cat.scenarios) {
    for (const k of FLEET_KEYS) for (const o of cat.levers[k].options) {
      const r = applyLever(cat, s.levers, k, o.id);
      if (r) assert.ok(offDefault(cat, r.levers).length <= 1, `${s.id} + ${k}=${o.id}`);
    }
  }
});

test('configure: with no batteries, a fleet lever is an alias run or disabled "No batteries"', () => {
  const cat = fixture();
  const none = at(cat, `${E1}/none`);
  assert.equal(optionState(cat, none, 'fleet', 48).scenario.id, `${E1}/none/fleet=48`, 'the alias keeps the lever for the next policy');
  assert.equal(optionState(cat, none, 'growth', 20).scenario.id, `${E1}/none/growth=20`, 'growth is a real no-battery run');
  const noAlias = { ...cat, scenarios: cat.scenarios.filter((s) => !s.alias) };
  const st = optionState(noAlias, none, 'fleet', 48);
  assert.equal(st.enabled, false);
  assert.equal(st.reason, NO_BATTERIES_REASON);
});

test('configure: presets come from catalogue.presets (else scenario.preset); a missing id is dropped', () => {
  const cat = fixture();
  assert.deepEqual(presets(cat).map((p) => [p.name, p.id]), [['The demo evening', `${E1}/aware`], ['Pieces fail', `${E1}/aware/faults`]]);
  assert.equal(presetOf(cat, DEF), 'The demo evening');
  assert.equal(presetOf(cat, at(cat, `${E1}/naive`)), null, 'Custom');
  const old = { ...cat, presets: undefined, scenarios: cat.scenarios.map((s) => (s.id === `${E2}/aware` ? { ...s, preset: 'Record demand' } : s)) };
  assert.deepEqual(presets(old).map((p) => p.name), ['Record demand']);
});

// ---- the real files ----
function invariants(cat, where) {
  assert.ok(scenarioById(cat, cat.default), `${where}: default ${cat.default} is a scenario`);
  const ids = new Set();
  for (const s of cat.scenarios) {
    assert.ok(!ids.has(s.id), `${where}: duplicate id ${s.id}`);
    ids.add(s.id);
    for (const k of LEVER_KEYS) assert.ok(cat.levers[k].options.some((o) => String(o.id) === String(s.levers[k])), `${where}: ${s.id} ${k}=${s.levers[k]} is an option`);
    assert.equal(scenarioFor(cat, s.levers).id, s.id, `${where}: ${s.id}'s levers select it`);
    assert.ok(offDefault(cat, s.levers).length <= 1, `${where}: ${s.id} is one lever away from the default at most`);
    for (const p of ['meta', 'branch']) assert.equal(typeof s[p], 'string', `${where}: ${s.id}.${p}`);
  }
  for (const p of presets(cat)) assert.ok(ids.has(p.id), `${where}: preset ${p.name}`);
  // from every scenario, every option is selected, a run, or disabled WITH a reason
  for (const s of cat.scenarios) for (const k of LEVER_KEYS) for (const o of cat.levers[k].options) {
    const st = optionState(cat, s.levers, k, o.id);
    assert.ok(st.selected || (st.enabled && st.scenario) || (!st.enabled && st.reason), `${where}: ${s.id} ${k}=${o.id}`);
  }
}

test('configure: the committed dev catalogue holds the invariants', () => {
  invariants(readJSON('story/dev-catalogue.json'), 'dev-catalogue');
});

test('configure: ENGINE\'s story/index.json holds the invariants (when built)', (t) => {
  if (!fs.existsSync(path.join(UI, 'data', 'story', 'index.json'))) { t.skip('ui/data/story/index.json not built in this checkout'); return; }
  const cat = readJSON('story/index.json');
  assert.equal(cat.schema, 'hb.story.v1');
  invariants(cat, 'index.json');
  for (const k of ['fleet', 'cls', 'reserve', 'soc0', 'growth']) assert.ok(cat.levers[k], k);
  assert.ok(cat.levers.reserve.options.every((o) => Number(o.id) >= 20), 'the reserve is never below 20% (ruling 1)');
});
