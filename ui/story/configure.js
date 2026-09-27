// ui/story/configure.js (UI-A): step 1, Configure (story-flow spec v2, screen 1a), plus the pure lever logic the
// tests import (no DOM at import).
//
// Every lever, option, default, preset and disabled reason comes from the catalogue (ui/data/story/index.json,
// hb.story.v1; docs/story-contract.md). The page state IS a scenario: every reachable setting is a catalogue run, so a
// lever click moves to the closest run that has the new value, and says what else changed and why:
//   - an option is DISABLED when no run in the catalogue has it (reason: the catalogue's `unavailable` entry for it), or
//     when the policy is "none" and the lever needs batteries;
//   - the one-lever rule (ruling 1): the fleet levers are run one away from the default at a time, so moving a second
//     one resets the first (the note says so); any other lever the move changes carries the catalogue's reason.
// Nothing here invents a number: the Fixed column reads the scenario's meta (constants, plan, sources) and topology.
import { tagHTML } from './shell.js';

export const LEVER_KEYS = ['evening', 'policy', 'failure', 'fleet', 'cls', 'reserve', 'soc0', 'growth'];
export const FLEET_KEYS = ['fleet', 'cls', 'reserve', 'soc0', 'growth'];
export const ONE_LEVER_REASON = 'the engine ran the fleet levers one away from the default at a time';
export const NO_BATTERIES_REASON = 'No batteries in this run: pick a dispatch policy first';
const same = (a, b) => String(a) === String(b);

export const defaultLevers = (cat) => Object.fromEntries(LEVER_KEYS.map((k) => [k, cat.levers && cat.levers[k] ? cat.levers[k].default : undefined]));
export const leversEqual = (a, b) => LEVER_KEYS.every((k) => same(a[k], b[k]));
export const scenarioById = (cat, id) => (cat.scenarios || []).find((s) => s.id === id) || null;
export const scenarioFor = (cat, levers) => (cat.scenarios || []).find((s) => leversEqual(s.levers, levers)) || null;

/** The option object of lever `key` with id `value` (ids compare as strings: 96 and "96" are the same option). */
export function optionOf(cat, key, value) {
  const L = cat.levers && cat.levers[key];
  return L ? (L.options || []).find((o) => same(o.id, value)) || null : null;
}
export const optionLabel = (cat, key, value) => { const o = optionOf(cat, key, value); return o ? o.label : String(value); };
export const leverLabel = (cat, key) => (cat.levers && cat.levers[key] ? cat.levers[key].label : key);

/** The first `unavailable` reason whose partial levers all match `levers`, else null. */
export function unavailableReason(cat, levers) {
  for (const u of cat.unavailable || []) {
    const p = u.levers || {};
    const keys = Object.keys(p);
    if (keys.length && keys.every((k) => same(p[k], levers[k]))) return u.reason;
  }
  return null;
}

/** Fleet levers away from their default. */
export function offDefault(cat, levers) {
  const d = defaultLevers(cat);
  return FLEET_KEYS.filter((k) => levers[k] !== undefined && !same(levers[k], d[k]));
}

/** What choosing `value` for lever `key` does from `current` (a levers object):
 *  {selected, enabled, reason, scenario, levers, changes[{key, from, to, reason}]}. Pure; the tests pin it. */
export function optionState(cat, current, key, value) {
  const d = defaultLevers(cat);
  if (same(current[key], value)) {
    return { selected: true, enabled: true, reason: null, scenario: scenarioFor(cat, current), levers: { ...current }, changes: [] };
  }
  const out = (enabled, reason, scenario = null, changes = []) =>
    ({ selected: false, enabled, reason, scenario, levers: scenario ? { ...scenario.levers } : null, changes });
  if (current.policy === 'none' && (FLEET_KEYS.includes(key) || key === 'failure')) {
    return out(false, (key === 'failure' && unavailableReason(cat, { ...current, [key]: value })) || NO_BATTERIES_REASON);
  }
  // the requested setting, with the one-lever rule applied to the fleet levers
  const want = { ...current, [key]: value };
  const ruled = new Map();
  if (FLEET_KEYS.includes(key) && !same(value, d[key])) {
    for (const k of FLEET_KEYS) if (k !== key && !same(want[k], d[k])) { want[k] = d[k]; ruled.set(k, ONE_LEVER_REASON); }
  }
  const withValue = (cat.scenarios || []).filter((s) => same(s.levers[key], value));
  if (!withValue.length) {
    return out(false, unavailableReason(cat, { [key]: value }) || unavailableReason(cat, want) || 'Not run: no engine run in the catalogue has this setting');
  }
  // the closest run with that value: fewest other levers changed, preferring changes back to the default
  let best = null, bestCost = Infinity;
  for (const s of withValue) {
    let cost = 0;
    for (const k of LEVER_KEYS) {
      if (k === key || same(s.levers[k], want[k])) continue;
      cost += 1 + (same(s.levers[k], d[k]) ? 0 : 0.5);
    }
    if (cost < bestCost) { best = s; bestCost = cost; }
  }
  const why = unavailableReason(cat, want);
  const changes = [];
  for (const k of LEVER_KEYS) {
    if (k === key || same(best.levers[k], current[k])) continue;
    const reason = ruled.has(k) && same(best.levers[k], want[k]) ? ruled.get(k)
      : why || (value === 'none' && key === 'policy' ? 'no batteries in this run' : 'no engine run combines these settings');
    changes.push({ key: k, from: current[k], to: best.levers[k], reason });
  }
  return out(true, null, best, changes);
}

/** Apply a lever: {scenario, levers, notes[]} or null when the option is disabled. */
export function applyLever(cat, current, key, value) {
  const st = optionState(cat, current, key, value);
  if (!st.enabled || !st.scenario) return null;
  const notes = st.changes.map((c) => `${leverLabel(cat, c.key)} ${same(c.to, defaultLevers(cat)[c.key]) ? 'back to' : 'set to'} ${optionLabel(cat, c.key, c.to)}: ${c.reason}.`);
  return { scenario: st.scenario, levers: st.levers, notes };
}

/** The preset name of the run these levers select, or null (Custom). */
export function presetOf(cat, levers) {
  const s = scenarioFor(cat, levers);
  return s && s.preset ? s.preset : null;
}
export const presets = (cat) => (cat.scenarios || []).filter((s) => s.preset);

// ---------------------------------------------------------------------------------------------------------- the page
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const K = (c) => (c ? { v: c.value, label: c.label, cite: c.cite } : null);   // envelope constant -> labelled value

// Plain-language copy for each option (words only: every number on the page comes from data).
const SUBS = {
  policy: {
    none: 'Homes alone. The baseline every other run is compared with.',
    naive: 'Naive: our assumption of one number, no feeder check. The zone signal is split evenly, all at once.',
    aware: 'Checks each transformer\'s headroom before sending charge, and only sends what fits.',
  },
  failure: {
    none: 'Everything works as designed.',
    faults: 'A battery goes silent, an EV plugs in on a busy street, and our controller stalls.',
    worker_kill: 'A controller worker is killed mid-evening; another takes over its lease.',
    covert: 'Fictional attacker: a hidden carrier rides on some batteries. The detector finds it from physics.',
  },
};
const CHANGES = {
  evening: 'prices, home load, when the fleet discharges and recharges',
  policy: 'transformer loading, fleet charge, energy value',
  failure: 'what breaks, and whether the feeder notices',
  fleet: 'how much load the fleet can shift, energy value',
  cls: 'peak kW each home can shift, hours of cover',
  reserve: 'energy the fleet can offer; the floor it never crosses',
  soc0: 'evening discharge, how much must recharge overnight',
  growth: 'home load on every transformer, room left to charge',
};
const DESC = {
  fleet: 'Homes on this feeder with one of our batteries.',
  cls: 'The unit in every fleet home.',
  reserve: 'Charge kept back for the member\'s own backup. The grid never uses it.',
  soc0: 'Fleet state of charge at the start of the evening.',
  growth: 'Home load added on every home, for a future feeder.',
};

export async function mount(root, ctx) {
  const cat = ctx.catalogue;
  let scenario = ctx.scenario;
  let notes = [];
  let disposed = false;
  const [days, topo] = await Promise.all([
    ctx.getJSON('p1/days/index.json').catch(() => null),
    ctx.getJSON('topology.json').catch(() => null),
  ]);
  const metaCache = new Map();
  const metaFor = (s) => {
    if (!metaCache.has(s.meta)) metaCache.set(s.meta, ctx.getAny(s.meta).catch(() => null));
    return metaCache.get(s.meta);
  };
  let meta = await metaFor(scenario);

  root.innerHTML = `<div class="cfg">
    <div class="cfg-scn"><span class="st-eyebrow">SCENARIO</span><div class="cfg-seg" role="radiogroup" aria-label="Scenario presets"></div><span class="cfg-scn-note"></span></div>
    <div class="cfg-body">
      <div class="cfg-title"><div><div class="st-title">What you can change</div>
        <div class="cfg-sub">Pick an evening and set the levers. Every setting you can reach is a run the engine already made: one OpenDSS power flow per minute of the evening. The right-hand column stays fixed.</div></div>
        <button type="button" class="st-btn-ghost cfg-reset">Reset to defaults</button></div>
      <div class="cfg-grid">
        <section class="cfg-col cfg-col-evening"><div class="cfg-colhead"><div class="st-eyebrow">EVENING</div><div class="cfg-colsub">A real ERCOT evening: its prices, and its home load</div></div><div class="cfg-evenings"></div></section>
        <section class="cfg-col"><div class="cfg-colhead"><div class="st-eyebrow">CONTROLLER</div><div class="cfg-colsub">Who decides each battery's charge, and what goes wrong</div></div><div class="cfg-ctl"></div></section>
        <section class="cfg-col"><div class="cfg-colhead"><div class="st-eyebrow">FLEET</div><div class="cfg-colsub">Our batteries: one lever away from the default at a time</div></div><div class="cfg-fleet"></div></section>
        <section class="cfg-col"><div class="cfg-colhead"><div class="st-eyebrow">FIXED IN THIS RUN</div><div class="cfg-colsub">Grid and market inputs the result depends on</div></div><div class="cfg-fixed"></div></section>
      </div>
      <div class="cfg-foot"><div class="cfg-notes" role="status"></div><div class="cfg-run"></div><button type="button" class="st-btn st-btn-lg cfg-start">Start the sim →</button></div>
    </div></div>`;
  const $ = (sel) => root.querySelector(sel);

  const peakOf = (date) => {
    const o = optionOf(cat, 'evening', date);
    if (o && o.peak) return o.peak;
    const row = days && Array.isArray(days.days) ? days.days.find((d) => d.date === date) : null;
    return row ? row.peak : null;
  };
  const whyHTML = (why) => (why && why.text ? `<span class="cfg-why">${esc(why.text)} ${why.label ? tagHTML(why.label, why.cite) : ''}</span>` : '');
  const reasonHTML = (st) => (st.enabled ? '' : ` title="${esc(st.reason)}"`);

  function optionButton(key, o, extraHTML = '') {
    const st = optionState(cat, scenario.levers, key, o.id);
    const sub = (SUBS[key] && SUBS[key][o.id]) || '';
    return `<button type="button" class="cfg-opt${st.selected ? ' on' : ''}" data-key="${key}" data-val="${esc(o.id)}"
      aria-pressed="${st.selected}"${st.enabled ? '' : ' disabled aria-disabled="true"'}${reasonHTML(st)}>
      <span class="t">${esc(o.label)}${o.tag && key !== 'evening' ? ` <span class="cfg-tagline">${esc(o.tag)}</span>` : ''}</span>
      ${sub ? `<span class="s">${esc(sub)}</span>` : ''}${extraHTML}
      ${!st.enabled ? `<span class="cfg-why-off">${esc(st.reason)}</span>` : ''}</button>`;
  }
  const changedBadge = (key) => (!same(scenario.levers[key], cat.levers[key].default) ? '<span class="cfg-changed">changed</span>' : '');

  function leverCard(key, bodyHTML, { desc = '', compact = false } = {}) {
    const L = cat.levers[key];
    return `<div class="cfg-card${compact ? ' compact' : ''}" data-lever="${key}"><div class="cfg-card-h"><span class="cfg-card-t">${esc(L.label)}</span>${changedBadge(key)}</div>
      ${desc ? `<div class="cfg-desc">${esc(desc)}</div>` : ''}${bodyHTML}<div class="cfg-changes">Changes → ${esc(CHANGES[key] || '')}</div></div>`;
  }

  function renderScenarioBar() {
    const pre = presets(cat);
    const active = presetOf(cat, scenario.levers);
    $('.cfg-seg').innerHTML = pre.map((s) => `<button type="button" role="radio" aria-checked="${s.preset === active}" class="${s.preset === active ? 'on' : ''}" data-s="${esc(s.id)}">${esc(s.preset)}</button>`).join('')
      + `<button type="button" role="radio" aria-checked="${!active}" class="${!active ? 'on' : ''}" data-custom="1">Custom</button>`;
    $('.cfg-scn-note').textContent = active ? scenario.title || scenario.id : `Your own settings: ${scenario.title || scenario.id}`;
  }

  function renderEvenings() {
    const L = cat.levers.evening;
    $('.cfg-evenings').innerHTML = (L.options || []).map((o) => {
      const pk = peakOf(o.id);
      const extra = `<span class="cfg-ev-tag">${esc(o.tag || '')}</span>${whyHTML(o.why)}
        ${pk ? `<span class="cfg-ev-peak">Peak price ${ctx.num(pk, { money: true, digits: 2, unit: '/MWh' })}${pk.t ? ` at ${esc(pk.t)}` : ''}</span>` : ''}`;
      return optionButton('evening', { ...o, tag: null }, extra);
    }).join('');
  }

  function renderController() {
    const pol = cat.levers.policy, fail = cat.levers.failure;
    const attacker = scenario.levers.failure === 'covert' ? '<span class="cfg-fict">Fictional attacker</span>' : '';
    $('.cfg-ctl').innerHTML = leverCard('policy', `<div class="cfg-stack">${(pol.options || []).map((o) => optionButton('policy', o, o.why ? `<span class="cfg-why">${tagHTML(o.why.label, [o.why.text, o.why.cite].filter(Boolean).join(' '))}</span>` : '')).join('')}</div>`)
      + leverCard('failure', `<div class="cfg-stack">${(fail.options || []).map((o) => optionButton('failure', o)).join('')}</div>${attacker}`);
  }

  function renderFleet() {
    const cards = FLEET_KEYS.filter((k) => cat.levers[k]).map((k) => {
      const L = cat.levers[k];
      const opts = (L.options || []).map((o) => {
        const st = optionState(cat, scenario.levers, k, o.id);
        return { o, st };
      });
      const seg = `<div class="cfg-seg-sm" role="radiogroup" aria-label="${esc(L.label)}">${opts.map(({ o, st }) => `<button type="button" data-key="${k}" data-val="${esc(o.id)}"
          class="${st.selected ? 'on' : ''}" aria-pressed="${st.selected}"${st.enabled ? '' : ' disabled aria-disabled="true"'}${reasonHTML(st)}>${esc(o.label)}</button>`).join('')}</div>`;
      const sel = optionOf(cat, k, scenario.levers[k]);
      const selWhy = sel && sel.why ? `<div class="cfg-desc">${esc(sel.label)}: ${whyHTML(sel.why)}</div>` : '';
      const off = [...new Set(opts.filter(({ st }) => !st.enabled).map(({ st }) => st.reason))];
      const offIds = opts.filter(({ st }) => !st.enabled).map(({ o }) => o.label);
      const offHTML = off.length ? `<div class="cfg-off">Not available: ${esc(offIds.join(', '))}. ${esc(off.length === 1 ? off[0] : off.join(' · '))}</div>` : '';
      return leverCard(k, `${seg}${selWhy}${offHTML}`, { desc: DESC[k] || '' });
    });
    $('.cfg-fleet').innerHTML = cards.join('');
  }

  function row(k, vHTML, extra = '') { return `<div class="cfg-fx"><div class="k">${esc(k)}</div><div class="v">${vHTML}</div>${extra}</div>`; }
  function renderFixed() {
    const m = meta, c = (m && m.constants) || {};
    const n = (x, o) => (x ? ctx.num(x, o) : '');
    const counts = topo && topo.meta && topo.meta.counts;
    const grid = [];
    if (topo) grid.push(row('Feeder', `${esc(topo.meta.feeder ? 'NREL SMART-DS 2018 AUS P1U' : '')} · ${counts ? `${ctx.num({ v: counts.transformers, label: 'REAL', cite: 'topology.json meta.counts (SMART-DS)' })} transformers · ${ctx.num({ v: counts.homes, label: 'REAL', cite: 'topology.json meta.counts (SMART-DS)' })} homes` : ''}`));
    if (c.TIER_AMBER_PCT) grid.push(row('Over nameplate', `above ${n(K(c.TIER_AMBER_PCT), { unit: '%' })} of kVA as shipped (counted, not a violation)`));
    if (c.TIER_NORMAL_PCT) grid.push(row('Normal rating', `above ${n(K(c.TIER_NORMAL_PCT), { unit: '%' })} for ${n(K(c.TIER_NORMAL_MIN), { unit: ' min' })} or more`));
    if (c.TIER_EMERGENCY_PCT) grid.push(row('Emergency', `above ${n(K(c.TIER_EMERGENCY_PCT), { unit: '%' })}`));
    if (c.FUSE_PCT) grid.push(row('Fuse rule', `${n(K(c.FUSE_PCT), { unit: '%' })} for ${n(K(c.FUSE_MINUTES), { unit: ' min' })}, or ${n(K(c.FUSE_INSTANT_PCT), { unit: '%' })} for ${n(K(c.FUSE_INSTANT_SECONDS), { unit: ' s' })}`));
    const market = [];
    if (m && m.sources && m.sources.price) market.push(row('Prices', `${esc(m.sources.price.text)}, ${esc(m.day || '')} ${tagHTML(m.sources.price.label, m.sources.price.text)}`));
    if (m && m.plan) market.push(row('Charge onset', `${esc(m.plan.rule || '')} onset ${esc(m.plan.onset || '')}${m.plan.threshold ? ` · at or below ${n(m.plan.threshold, { money: true, digits: 2, unit: '/MWh' })}` : ''}`));
    if (c.CONTROLLER_VIEW) market.push(row('What the controller sees', `${esc(c.CONTROLLER_VIEW.value)} ${tagHTML(c.CONTROLLER_VIEW.label, c.CONTROLLER_VIEW.cite)}`));
    $('.cfg-fixed').innerHTML = `<div class="st-eyebrow sm">GRID</div>${grid.join('')}<div class="st-eyebrow sm">MARKET</div>${market.join('')}`
      + (m ? '' : '<div class="cfg-desc">The run\'s meta file did not load.</div>');
  }

  function renderFoot() {
    $('.cfg-notes').innerHTML = notes.map((t) => `<div>${esc(t)}</div>`).join('');
    const e = scenario.engine || {};
    const cost = [e.solves ? `${ctx.num(e.solves)} OpenDSS solves` : '', e.buildSeconds ? `${ctx.num(e.buildSeconds, { unit: ' s' })} to build` : ''].filter(Boolean).join(' · ');
    $('.cfg-run').innerHTML = `<span class="cfg-run-id">${esc(scenario.title || scenario.id)}</span>${cost ? `<span class="cfg-run-cost">${cost}</span>` : ''}`;
  }

  function render() {
    renderScenarioBar(); renderEvenings(); renderController(); renderFleet(); renderFixed(); renderFoot();
  }

  async function goTo(s, newNotes = []) {
    scenario = s;
    notes = newNotes;
    history.replaceState(history.state, '', ctx.link({ page: 'configure', s: s.id }));
    const m = await metaFor(s);
    if (disposed) return;
    meta = m;
    render();
  }

  root.addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b || b.disabled || !root.contains(b)) return;
    if (b.dataset.key) {
      const res = applyLever(cat, scenario.levers, b.dataset.key, b.dataset.val);
      if (res) goTo(res.scenario, res.notes);
    } else if (b.dataset.s) {
      const s = scenarioById(cat, b.dataset.s);
      if (s) goTo(s, []);
    } else if (b.classList.contains('cfg-reset')) {
      const s = scenarioById(cat, cat.default);
      if (s) goTo(s, []);
    } else if (b.classList.contains('cfg-start')) {
      ctx.nav('running', { s: scenario.id, k: null });
    }
  });

  render();
  return { dispose() { disposed = true; root.innerHTML = ''; } };
}
