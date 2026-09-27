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
import { tagHTML, FEEDER_TAG, vsDefaultInfo, vsDefaultHTML, leverTag, LEVER_SET, runTitleHTML } from './shell.js';
import { dateLabel, stepToTime } from '../lib/format.js';

export const LEVER_KEYS = ['evening', 'policy', 'failure', 'fleet', 'cls', 'reserve', 'soc0', 'growth'];
export const FLEET_KEYS = ['fleet', 'cls', 'reserve', 'soc0', 'growth'];
export const ONE_LEVER_REASON = 'the engine ran the fleet levers one away from the default at a time';
export const NO_BATTERIES_REASON = 'No batteries in this run: pick a dispatch policy first';
export const NOT_RUN_REASON = 'Not run: no engine run in the catalogue has these settings';
const LABEL_OK = (l) => ['REAL', 'SIM', 'DERIVED', 'ASSUMPTION', 'UNVERIFIED', 'SCREENING'].includes(l);
const tagOpt = (label, cite) => (LABEL_OK(label) ? tagHTML(label, cite) : '');

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

/** The first `unavailable` reason whose partial levers all match `levers` (a list = any of), else null. This is the
 *  catalogue's own `match` rule: "a scenario is found by its id; otherwise the first unavailable row whose every lever
 *  matches gives the reason". */
export function unavailableReason(cat, levers) {
  for (const u of cat.unavailable || []) {
    const p = u.levers || {};
    const keys = Object.keys(p);
    if (keys.length && keys.every((k) => (Array.isArray(p[k]) ? p[k].some((x) => same(x, levers[k])) : same(p[k], levers[k])))) return u.reason;
  }
  return null;
}

/** Fleet levers away from their default. */
export function offDefault(cat, levers) {
  const d = defaultLevers(cat);
  return FLEET_KEYS.filter((k) => levers[k] !== undefined && !same(levers[k], d[k]));
}

/** What choosing `value` for lever `key` does from `current` (a levers object):
 *  {selected, enabled, reason, scenario, levers, changes[{key, from, to, reason}]}. Pure; the tests pin it.
 *  - The one-lever rule (ruling 1): moving a fleet lever off its default resets any other off-default fleet lever;
 *    each reset is a `change` with ONE_LEVER_REASON (the page shows it as a note).
 *  - Otherwise the setting must be a catalogue run: when it is not, the option is DISABLED with the catalogue's
 *    reason (its `unavailable` rows), never moved somewhere else behind the user's back. */
export function optionState(cat, current, key, value) {
  const d = defaultLevers(cat);
  if (same(current[key], value)) {
    return { selected: true, enabled: true, reason: null, scenario: scenarioFor(cat, current), levers: { ...current }, changes: [] };
  }
  const want = { ...current, [key]: value };
  const changes = [];
  if (FLEET_KEYS.includes(key) && !same(value, d[key])) {
    for (const k of FLEET_KEYS) {
      if (k !== key && !same(want[k], d[k])) { changes.push({ key: k, from: want[k], to: d[k], reason: ONE_LEVER_REASON }); want[k] = d[k]; }
    }
  }
  const scenario = scenarioFor(cat, want);
  if (scenario) return { selected: false, enabled: true, reason: null, scenario, levers: { ...scenario.levers }, changes };
  const reason = unavailableReason(cat, want) || unavailableReason(cat, { [key]: value })
    || (current.policy === 'none' && FLEET_KEYS.includes(key) ? NO_BATTERIES_REASON : NOT_RUN_REASON);
  return { selected: false, enabled: false, reason, scenario: null, levers: null, changes: [] };
}

/** Apply a lever: {scenario, levers, notes[]} or null when the option is disabled. */
export function applyLever(cat, current, key, value) {
  const st = optionState(cat, current, key, value);
  if (!st.enabled || !st.scenario) return null;
  const notes = st.changes.map((c) => `${leverLabel(cat, c.key)} ${same(c.to, defaultLevers(cat)[c.key]) ? 'back to' : 'set to'} ${optionLabel(cat, c.key, c.to)}: ${c.reason}.`);
  return { scenario: st.scenario, levers: st.levers, notes };
}

/** Customers on the feeder from topology meta: every load bus is a customer (`counts.homes` counts load buses, not
 *  only houses); `counts.residential` / `counts.commercial` split them, labelled by `meta.customerUse` {label, cite}.
 *  The split shows only when the data carries it; never a literal. */
export function customerCounts(meta) {
  const counts = meta && meta.counts;
  if (!counts || !Number.isFinite(counts.homes)) return null;
  const use = meta.customerUse && LABEL_OK(meta.customerUse.label) ? meta.customerUse : { label: null, cite: '' };
  const split = Number.isFinite(counts.residential) && Number.isFinite(counts.commercial);
  return { customers: counts.homes, residential: split ? counts.residential : null, commercial: split ? counts.commercial : null,
    fleetOnCommercial: Number.isFinite(counts.fleetOnCommercial) ? counts.fleetOnCommercial : null, label: use.label, cite: use.cite || '' };
}
/** HTML: "1,010 customers (971 homes, 39 small businesses)". The split carries meta.customerUse's label; the total
 *  is a count the topology does not label, so it shows without a tag (the page never assigns a label itself). */
export function customersHTML(cc, num) {
  if (!cc) return '';
  const total = `<span class="num" title="every load bus in the feeder is a customer (topology.json meta.counts)">${Number(cc.customers).toLocaleString('en-US')}</span> customers`;
  if (cc.residential === null) return total;
  const t = (v) => (cc.label ? num({ v, label: cc.label, cite: cc.cite }) : `<span class="num">${Number(v).toLocaleString('en-US')}</span>`);
  return `${total} (${t(cc.residential)} homes, ${t(cc.commercial)} small businesses)`;
}

/** The first calendar year named in a text ("2018 SMART-DS weather-year load ..." -> 2018), or null. */
export const yearIn = (text) => { const m = /\b(19|20)\d{2}\b/.exec(String(text || '')); return m ? m[0] : null; };

/** The evening's load/price pairing, disclosed (data-truth audit #9): the price date and the load profile's date of
 *  the same calendar day (LOAD_PAIRING), both weekdays COMPUTED from the dates, and the unverified DST clock
 *  (PROFILE_INDEX_RULE). `constants` = the run meta's constants; `dataset` = the feeder dataset's name (topology
 *  FEEDER_NAME). The profile year is read from LOAD_PAIRING's text, else the dataset name; without one, no weekday. */
export function pairingText(date, constants = {}, dataset = '') {
  const m = /^(\d{4})-(\d{2}-\d{2})$/.exec(String(date || ''));
  if (!m) return null;
  const pair = constants.LOAD_PAIRING, clock = constants.PROFILE_INDEX_RULE;
  const year = yearIn(pair && pair.value) || yearIn(dataset);
  const price = dateLabel(date), loadDay = year ? dateLabel(`${year}-${m[2]}`) : null;
  if (!price) return null;
  const sameWeekday = loadDay ? price.slice(0, 3) === loadDay.slice(0, 3) : null;
  const src = dataset ? `the ${dataset} load profile` : 'the feeder dataset\'s load profile';
  return {
    price, load: loadDay, sameWeekday, label: pair && LABEL_OK(pair.label) ? pair.label : null,
    short: loadDay ? `Home load: the profile of ${loadDay}` : 'Home load: the profile of the same calendar date',
    text: `Prices: ERCOT LZ_NORTH on ${price}. Home load: ${src} of the same calendar date${loadDay ? `, ${loadDay}` : ''}${pair ? ` (${LABEL_OK(pair.label) ? `${pair.label}: ` : ''}${pair.value})` : ''}. `
      + (sameWeekday === null ? '' : sameWeekday ? 'The weekdays match. ' : `The weekday differs (${price.slice(0, 3)} prices, ${loadDay.slice(0, 3)} load). `)
      + `The profiles have no daylight-saving shift, so the load may sit one hour early against the CDT prices${clock ? ` (${clock.value})` : ''}.`,
  };
}

/** The feeder dataset's name and its label: topology constants.FEEDER_NAME, else meta.feeder; null when neither. */
export function feederName(topology) {
  const c = topology && topology.constants && topology.constants.FEEDER_NAME;
  if (c && c.value) return { name: String(c.value), label: LABEL_OK(c.label) ? c.label : null, cite: c.cite || '' };
  const f = topology && topology.meta && topology.meta.feeder;
  return f ? { name: String(f), label: null, cite: 'topology.json meta.feeder' } : null;
}

/** The presets, in the catalogue's order: [{name, id, scenario}]. `catalogue.presets` ([{name, id}]) when present,
 *  else the scenarios that carry a `preset` name. A preset whose id is not a scenario is dropped. */
export function presets(cat) {
  const list = Array.isArray(cat.presets) ? cat.presets.map((p) => ({ name: p.name, id: p.id }))
    : (cat.scenarios || []).filter((s) => s.preset).map((s) => ({ name: s.preset, id: s.id }));
  return list.map((p) => ({ ...p, scenario: scenarioById(cat, p.id) })).filter((p) => p.scenario && p.name);
}
/** The preset name of the run these levers select, or null (Custom). */
export function presetOf(cat, levers) {
  const s = scenarioFor(cat, levers);
  const p = s ? presets(cat).find((x) => x.id === s.id) : null;
  return p ? p.name : null;
}

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
  root.innerHTML = '<div class="rv-loading">Loading the scenario catalogue runs…</div>';
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
        <section class="cfg-col cfg-col-evening"><div class="cfg-colhead"><div class="st-eyebrow">EVENING</div><div class="cfg-colsub">Real ERCOT prices; the home load is NREL's synthetic profile for the same calendar date (ASSUMPTION)</div></div><div class="cfg-evenings"></div></section>
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

  function optionButton(key, o, extraHTML = '', title = '') {
    const st = optionState(cat, scenario.levers, key, o.id);
    const sub = (SUBS[key] && SUBS[key][o.id]) || '';
    const tip = [st.enabled ? '' : st.reason, title].filter(Boolean).join(' · ');
    return `<button type="button" class="cfg-opt${st.selected ? ' on' : ''}" data-key="${key}" data-val="${esc(o.id)}"
      aria-pressed="${st.selected}"${st.enabled ? '' : ' disabled aria-disabled="true"'}${tip ? ` title="${esc(tip)}"` : ''}>
      <span class="t">${esc(o.label)}${key !== 'evening' && o.why && LABEL_OK(o.why.label) ? tagHTML(o.why.label, [o.why.text, o.why.cite].filter(Boolean).join(' · ')) : ''}${o.tag && key !== 'evening' ? ` <span class="cfg-tagline">${esc(o.tag)}</span>` : ''}</span>
      ${sub ? `<span class="s">${esc(sub)}</span>` : ''}${extraHTML}
      ${!st.enabled ? `<span class="cfg-why-off">${esc(st.reason)}</span>` : ''}</button>`;
  }
  const changedBadge = (key) => (!same(scenario.levers[key], cat.levers[key].default) ? '<span class="cfg-changed">changed</span>' : '');

  // the catalogue's vsDefault (what this run changed against the default run), shown by the lever that moved
  // the catalogue's reference run (vsDefaultRef) and what this run moved against it, shown by the lever(s) that differ
  function movedLevers() {
    const end = meta && meta.start && meta.steps ? stepToTime(meta, meta.steps) : null;
    const info = vsDefaultInfo(cat, scenario, { end });
    if (!info || !info.ref) return { keys: [], info };
    return { keys: LEVER_KEYS.filter((k) => !same(info.ref.levers[k], scenario.levers[k])), info };
  }
  const vsBlock = (key) => {
    const m = movedLevers();
    if (!m.keys.includes(key) || key !== m.keys[m.keys.length - 1]) return '';
    const body = m.info.rows.length ? vsDefaultHTML(m.info.rows) : '<span class="vs-row">no headline value moved</span>';
    return `<div class="cfg-vs"><div class="cfg-vs-h" title="${esc(m.info.refId)}">vs ${esc(m.info.refTitle)}</div>${body}</div>`;
  };
  function leverCard(key, bodyHTML, { desc = '', compact = false } = {}) {
    const L = cat.levers[key];
    const lt = leverTag(cat, key, scenario.levers[key]);
    return `<div class="cfg-card${compact ? ' compact' : ''}" data-lever="${key}"><div class="cfg-card-h"><span class="cfg-card-t">${esc(L.label)}</span>${lt ? tagHTML(lt.label, lt.cite) : ''}${changedBadge(key)}</div>
      ${desc ? `<div class="cfg-desc">${esc(desc)}</div>` : ''}${bodyHTML}${vsBlock(key)}<div class="cfg-changes">Changes → ${esc(CHANGES[key] || '')}</div></div>`;
  }

  function renderScenarioBar() {
    const pre = presets(cat);
    const active = presetOf(cat, scenario.levers);
    $('.cfg-seg').innerHTML = pre.map((p) => `<button type="button" role="radio" aria-checked="${p.name === active}" class="${p.name === active ? 'on' : ''}" data-s="${esc(p.id)}">${esc(p.name)}</button>`).join('')
      + `<button type="button" role="radio" aria-checked="${!active}" class="${!active ? 'on' : ''}" data-custom="1">Custom</button>`;
    $('.cfg-scn-note').innerHTML = runTitleHTML(cat, scenario, { prefix: active ? '' : 'Your own settings: ', naive: meta && meta.naiveLabel });
  }

  function renderEvenings() {
    const L = cat.levers.evening;
    $('.cfg-evenings').innerHTML = (L.options || []).map((o) => {
      const pk = peakOf(o.id);
      const fn = feederName(topo);
      const pair = pairingText(o.id, (meta && meta.constants) || {}, fn ? fn.name : '');
      const extra = `<span class="cfg-ev-tag">${esc(o.tag || '')}</span>${whyHTML(o.why)}
        ${pk ? `<span class="cfg-ev-peak">Peak price ${ctx.num(pk, { money: true, digits: 2, unit: '/MWh' })}${pk.t ? ` at ${esc(pk.t)}` : ''}</span>` : ''}
        ${pair ? `<span class="cfg-ev-load">${esc(pair.short)}${pair.sameWeekday === false ? esc(` (a different day of the week from ${String(o.id).slice(0, 4)}'s)`) : ''} ${pair.label ? tagHTML(pair.label, pair.text) : ''}</span>` : ''}`;
      return optionButton('evening', { ...o, tag: null }, extra, pair ? pair.text : '');
    }).join('') + vsBlock('evening');
  }

  function renderController() {
    const pol = cat.levers.policy, fail = cat.levers.failure;
    const attacker = scenario.levers.failure === 'covert' ? '<span class="cfg-fict">Fictional attacker</span>' : '';
    $('.cfg-ctl').innerHTML = leverCard('policy', `<div class="cfg-stack">${(pol.options || []).map((o) => optionButton('policy', o)).join('')}</div>`)
      + leverCard('failure', `<div class="cfg-stack">${(fail.options || []).map((o) => optionButton('failure', o)).join('')}</div>${attacker}`);
  }

  function renderFleet() {
    const cards = FLEET_KEYS.filter((k) => cat.levers[k]).map((k) => {
      const L = cat.levers[k];
      const sc = cat.constants && cat.constants[LEVER_SET[k]];
      const setTag = sc && LABEL_OK(sc.label) ? tagHTML(sc.label, `the options of this lever: ${sc.cite || LEVER_SET[k]}`) : '';
      const opts = (L.options || []).map((o) => {
        const st = optionState(cat, scenario.levers, k, o.id);
        return { o, st };
      });
      const seg = `<div class="cfg-seg-sm" role="radiogroup" aria-label="${esc(L.label)}">${opts.map(({ o, st }) => `<button type="button" data-key="${k}" data-val="${esc(o.id)}"
          class="${st.selected ? 'on' : ''}" aria-pressed="${st.selected}"${st.enabled ? '' : ' disabled aria-disabled="true"'}${reasonHTML(st)}>${esc(o.label)}${setTag ? '' : tagOpt(o.why && o.why.label, o.why && [o.why.text, o.why.cite].filter(Boolean).join(' · '))}</button>`).join('')}${setTag}</div>`;
      const sel = optionOf(cat, k, scenario.levers[k]);
      const selWhy = sel && sel.why && sel.why.text ? `<div class="cfg-desc">${esc(sel.label)}: ${esc(sel.why.text)}${tagOpt(sel.why.label, sel.why.cite)}</div>` : '';
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
    const cc = customerCounts(topo && topo.meta);

    const grid = [];
    if (topo) {
      const fn = feederName(topo);
      grid.push(row('Feeder', `${fn ? `${esc(fn.name)} ${LABEL_OK(fn.label) ? tagHTML(fn.label, fn.cite) : ''}` : ''} <span class="cfg-synth"${fn && fn.cite ? ` title="${esc(fn.cite)}"` : ''}>${esc(FEEDER_TAG)}</span>`
        + (counts && cc ? `<br><span class="num" title="topology.json meta.counts">${Number(counts.transformers).toLocaleString('en-US')}</span> transformers · ${customersHTML(cc, ctx.num)}` : '')));
      // the stress placement (data-truth #5): topology's FLEET_SIZE constant says so, else meta.shaping
      const fs = topo.constants && topo.constants.FLEET_SIZE, sh = topo.meta.shaping;
      const pl = fs && LABEL_OK(fs.label) ? { label: fs.label, cite: fs.cite } : sh && LABEL_OK(sh.label) ? { label: sh.label, cite: sh.description } : null;
      if (fs || sh) grid.push(row('Fleet placement', `a deliberate stress placement, not a neutral one ${pl ? tagHTML(pl.label, pl.cite) : ''}`));
    }
    if (c.TIER_AMBER_PCT) grid.push(row('Over nameplate', `above ${n(K(c.TIER_AMBER_PCT), { unit: '%' })} of kVA as shipped (counted, not a violation)`));
    if (c.TIER_NORMAL_PCT) grid.push(row('Normal rating', `above ${n(K(c.TIER_NORMAL_PCT), { unit: '%' })} for ${n(K(c.TIER_NORMAL_MIN), { unit: ' min' })} or more`));
    if (c.TIER_EMERGENCY_PCT) grid.push(row('Emergency', `above ${n(K(c.TIER_EMERGENCY_PCT), { unit: '%' })}`));
    if (c.FUSE_PCT) grid.push(row('Fuse rule', `${n(K(c.FUSE_PCT), { unit: '%' })} for ${n(K(c.FUSE_MINUTES), { unit: ' min' })}, or ${n(K(c.FUSE_INSTANT_PCT), { unit: '%' })} for ${n(K(c.FUSE_INSTANT_SECONDS), { unit: ' s' })}`));
    const market = [];
    if (m && m.sources && m.sources.price) market.push(row('Prices', `${esc(m.sources.price.text)}, ${esc(m.day || '')} ${tagHTML(m.sources.price.label, m.sources.price.text)}`));
    if (m && m.plan) {
      const pl = m.plan;
      market.push(row('Charge onset', `${esc(pl.rule || '')} onset ${esc(pl.onset || '')}${LABEL_OK(pl.label) ? tagHTML(pl.label, `the run's plan (${pl.mode || 'rule'})`) : ''}`
        + `${pl.onsetPrice ? ` at ${n(pl.onsetPrice, { money: true, digits: 2, unit: '/MWh' })}` : ''}${pl.threshold ? ` · at or below ${n(pl.threshold, { money: true, digits: 2, unit: '/MWh' })}` : ''}`));
    }
    if (c.CONTROLLER_VIEW) market.push(row('What the controller sees', `${esc(c.CONTROLLER_VIEW.value)} ${tagHTML(c.CONTROLLER_VIEW.label, c.CONTROLLER_VIEW.cite)}`));
    $('.cfg-fixed').innerHTML = `<div class="st-eyebrow sm">GRID</div>${grid.join('')}<div class="st-eyebrow sm">MARKET</div>${market.join('')}`
      + (m ? '' : '<div class="cfg-desc">The run\'s meta file did not load.</div>');
  }

  function renderFoot() {
    $('.cfg-notes').innerHTML = notes.map((t) => `<div>${esc(t)}</div>`).join('');
    const e = scenario.engine || {};
    const cost = [e.solves ? `${ctx.num(e.solves)} OpenDSS solves` : '', e.buildSeconds ? `${ctx.num(e.buildSeconds, { unit: ' s' })} to build` : ''].filter(Boolean).join(' · ');
    $('.cfg-run').innerHTML = `<span class="cfg-run-id">${runTitleHTML(cat, scenario, { naive: meta && meta.naiveLabel })}</span>${cost ? `<span class="cfg-run-cost">${cost}</span>` : ''}`;
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
