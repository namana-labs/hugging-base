// ui/lib/planner.js (PLANNER): the capacity planner's upgrade decision, pure, seeded and node-testable.
// Ported from DESIGN-CAPACITY-PLANNER.md Appendix A (same exported names). Physics is never computed here: every
// capacity comes from ui/data/p2/planner.json (sim.planner). This module only does the money arithmetic of §3.4:
// three actions (upgrade now / wait and watch / don't upgrade) over nine demand-decile curves x 1,000 seeded paths.
// No language model produces any number, rank or verdict here. Every number it returns is DERIVED: wrap it with
// `labelOf(planner, x)` before it reaches format.js. Contract: docs/contracts-planner.md.
//
// ---- STABLE API (UI-B's Learnings page calls these; names and shapes do not change) --------------------------------
//
// mulberry32(seed) -> () => number in [0, 1)                    the seeded generator (same stream as Appendix A)
// monthly(yearly[6]) -> F[61]                                   yearly decile points -> monthly, linear
// surv(table, age) -> r                                         planner.survival.r, linear between whole years, 0 past 60
// pReplace(table, age, years) -> P(replaced for any reason within `years` | age)
// annuity(v, r, life) -> $ ; breakEven(C, V) -> members ; breakEvenValue(C, unlocked, r, life) -> $/yr per member
// bindingCap({naive, aware, paper, utility?}, setting) -> cap   (§3.4.1; utility headroom replaces the paper rule)
//
// paramsFor(planner, tfIndex, k, knobs = {}) -> p
//   planner: the parsed ui/data/p2/planner.json; tfIndex: topology index (throws for 123 / 144 / 366 or unknown);
//   k: Cores wanted here now (installed + pending + the slider; rounded, >= 0).
//   knobs (all optional; defaults from planner.decision.defaults):
//     setting  'naive' | 'aware-screen' | 'aware-credit'   (or dispatch: 'naive'|'aware' + credit: bool)
//     growth   0 | 20 | 50 or 'g0' | 'g20' | 'g50'        caps from perK.g<growth>; one size up stays at today's load
//     cost     index into money.upgradePresets (default 1 = $10,000) or a USD number
//     value    index into money.valuePresets (default 0 = $631/yr) or a USD/yr number
//     referral bool (or q: 'q0' | 'q30')                   q30 = the referral-on demand curves
//     screen   'nameplate100' | 'ae90' ; paths: Monte Carlo paths per decile curve (default decision.paths)
//   returns p = { k0, homes, c, cUp, age, survTable, C, Cinc, L, r, V, pLoss, s, H, paths, perMember, life,   // decide() input
//                 deciles: [9][6] (pass as decide's 2nd argument), caps: {naive, aware, paper, ae90, utility, upNaive,
//                 upAware, upPaper, upAe90, c, cUp, checked, growth, upAtToday}, row (the planner.tfs row), setting,
//                 v ($/yr), cost {v,label,cite}, value {v,label,cite}, knobs {setting, growth, referral},
//                 rules: planRules(planner) }
//   (p itself is returned, not {p}: callers written as `pr.p || pr` work.)
//
// decide(p, deciles, seed = 20260926) -> {
//   expected:    {upgrade, wait, never}   $ mean over the nine decile curves (2026 $, 5-year horizon, discounted)
//   regret:      {upgrade, wait, never}   $ worst regret over the named scenarios p10 / p50 / p90
//   leastRegret: 'upgrade'|'wait'|'never' ; leastExpected: same
//   pOver:       P(Cores wanted exceed the binding cap within the horizon), typical (p50) curve
//   pOverP90:    the same in the fast-growth (p90) curve (the §3.4.4 "under 5%" test)
//   named:       {p10, p50, p90: {upgrade, wait, never, pOver, meanJoins}}  per-scenario costs
//   regretBy:    {p10, p50, p90: {upgrade, wait, never}}                   per-scenario regret (min is 0 in each)
// }
// planRules(planner) -> { hypotheticalPerHome, noUpgradePOver, ae90Share, nameplateShare, corePowerKw }
//   read from planner.constants (PLAN_HYPOTHETICAL_PER_HOME, PLAN_NO_UPGRADE_P_OVER, PLAN_SCREEN_SHARE_AE90,
//   PLAN_SCREEN_SHARE_NAMEPLATE, CORE_POWER_KW .value); a constant missing from the file is null and its rule is off
//   (no literal fallback): no 'no-upgrade' verdict, no hypothetical Cores.
// verdict(p, d) -> { code: 'no-upgrade'|'wait-and-watch'|'upgrade-now'|'dont-upgrade'|'dont-upgrade-tell',
//                    overToday, blockedToday, roomToday, unlocksNow, breakEven, breakEvenValue, twoRows }
//   'no-upgrade' needs p.rules.noUpgradePOver (fits today and pOverP90 < it)
// rackStates(planner, tfIndex, k, setting, growth) -> [{j, state: 'fits'|'paper'|'overload'|'earnsLess', hypothetical
//                    (j > PLAN_HYPOTHETICAL_PER_HOME x homes), approx (k off the aware grid at g20/g50), tier}]
// tfRow(planner, tfIndex) -> row | null ; capsFor(planner, row, growth) -> caps ; labelOf(planner, v) -> {v,label,cite}

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
/** yearly points [F(0), F(12), ..., F(60)] -> monthly F[0..60] (linear) */
export function monthly(yearly) {
  const out = [];
  for (let t = 0; t <= 12 * (yearly.length - 1); t++) {
    const i = Math.min(Math.floor(t / 12), yearly.length - 2), f = (t - 12 * i) / 12;
    out.push(yearly[i] + (yearly[i + 1] - yearly[i]) * f);
  }
  return out;
}
/** P(unit still in service at age a), linear between whole years; 0 beyond the table */
export function surv(table, a) {
  if (a >= table.length - 1) return 0;
  const i = Math.floor(a), f = a - i; return table[i] + (table[i + 1] - table[i]) * f;
}
export const pReplace = (table, age, years) => (surv(table, age) > 0 ? 1 - surv(table, age + years) / surv(table, age) : 1);
export const annuity = (v, r, life) => v * (1 - (1 + r) ** -life) / r;
export const breakEven = (C, V) => Math.ceil(C / V);
/** The member value per year at which an upgrade that unlocks `unlocked` members pays for itself (CRITIQUE must-fix 5):
 *  C / (unlocked x annuity factor). Infinity when it unlocks nobody. */
export const breakEvenValue = (C, unlocked, r, life) => (unlocked > 0 ? C / (unlocked * annuity(1, r, life)) : Infinity);
/** The binding capacity for a setting (§3.4.1). */
export function bindingCap({ naive, aware, paper, utility = null }, setting) {
  const rule = utility ?? paper;
  if (setting === 'naive') return Math.min(naive, rule);
  if (setting === 'aware-screen') return Math.min(aware, rule);
  return aware;                                   // 'aware-credit': the utility counts the control (UNVERIFIED in Texas)
}
/** Mean cost of the three actions over `paths` demand paths for ONE demand scenario curve F (monthly). */
export function scenarioCosts(p, F, seed) {
  const { k0, homes, c, cUp, age, survTable, C, Cinc, L, r, V, pLoss, s, H, paths, perMember } = p;   // all from paramsFor
  const T = 12 * H, rng = mulberry32(seed), m = Math.max(0, homes - Math.min(k0, homes));
  const disc = Array.from({ length: T + 1 }, (_, t) => (1 + r) ** (-t / 12));
  // P(replaced by month t | age): the same for every path, so computed once (Appendix A recomputed it per path;
  // identical numbers and the same random stream, about 10x faster)
  const prep = Array.from({ length: T + 1 }, (_, t) => (t ? pReplace(survTable, age, t / 12) : 0));
  const sum = { upgrade: 0, wait: 0, never: 0, over: 0, joins: 0 };
  const N = new Array(T + 1);
  for (let p_ = 0; p_ < paths; p_++) {
    N.fill(k0);
    for (let j = 0; j < m; j++) {                     // each non-member home joins at the first month F(t) >= u
      const u = rng(); if (u > F[T]) continue;
      let t = 1; while (F[t] < u) t++;
      for (let x = t; x <= T; x++) N[x] += perMember;
    }
    sum.joins += (N[T] - k0) / perMember;
    const newOver = (cap, t) => Math.max(0, N[t] - cap) - (t ? Math.max(0, N[t - 1] - cap) : 0);
    const newWait = (t) => newOver(c, t) - newOver(cUp, t);        // over c but within cUp: served once the upgrade lands
    let lostUp = 0, lostC = 0, tau = -1;
    for (let t = 0; t <= T; t++) { lostUp += newOver(cUp, t) * disc[t]; lostC += newOver(c, t) * disc[t]; if (tau < 0 && N[t] > c) tau = t; }
    let delayNow = 0; for (let t = 0; t < Math.min(L, T + 1); t++) delayNow += newWait(t) * disc[t];
    sum.upgrade += C + pLoss * V * delayNow + V * lostUp;
    sum.never += V * lostC;
    // replacement month rho from the age survival curve (inverse CDF), then does the utility upsize at it (prob s)?
    const ur = rng(), us = rng();
    let rho = Infinity; for (let t = 1; t <= T; t++) if (prep[t] >= ur) { rho = t; break; }
    if (tau >= 0) {
      sum.over += 1;
      if (rho < tau && us < s) sum.wait += Cinc * disc[rho] + V * lostUp;
      else { let d = 0; for (let t = tau; t < Math.min(tau + L, T + 1); t++) d += newWait(t) * disc[t];
        sum.wait += C * disc[tau] + pLoss * V * d + V * lostUp; }
    }
  }
  return { upgrade: sum.upgrade / paths, wait: sum.wait / paths, never: sum.never / paths, pOver: sum.over / paths,
    meanJoins: sum.joins / paths };
}
/** Nine decile curves (p10..p90): expected = their mean; worst regret over p10, p50, p90 (§3.4.3). Shape: see the top. */
export function decide(p, deciles, seed = 20260926) {
  const sc = deciles.map((y, i) => scenarioCosts(p, monthly(y), seed + i));
  const acts = ['upgrade', 'wait', 'never'];
  const expected = Object.fromEntries(acts.map((a) => [a, sc.reduce((x, s) => x + s[a], 0) / sc.length]));
  const named = { p10: sc[0], p50: sc[4], p90: sc[8] };
  const regretBy = Object.fromEntries(Object.entries(named).map(([k, s]) => {
    const best = Math.min(...acts.map((b) => s[b]));
    return [k, Object.fromEntries(acts.map((a) => [a, s[a] - best]))];
  }));
  const regret = Object.fromEntries(acts.map((a) => [a, Math.max(...Object.values(regretBy).map((s) => s[a]))]));
  const pick = (o) => acts.reduce((b, a) => (o[a] < o[b] - 1e-9 ? a : b), acts[0]);
  return { expected, regret, leastRegret: pick(regret), leastExpected: pick(expected), pOver: named.p50.pOver,
    pOverP90: named.p90.pOver, named, regretBy };
}

// ---- planner.json helpers (PLANNER; docs/contracts-planner.md) ------------------------------------------------------

export const SETTINGS = ['naive', 'aware-screen', 'aware-credit'];

/** The row of `planner.tfs` for a topology index, or null (excluded or unknown). */
export function tfRow(planner, tfIndex) {
  return planner.tfs.find((r) => r.tf === Number(tfIndex)) ?? null;
}

/** Wrap a decision output as a labelled number (DERIVED, planner.decision.cite). */
export function labelOf(planner, v) {
  return { v, label: planner.decision.label, cite: planner.decision.cite };
}

/** The planner's rule constants, read from planner.constants (sim.planner registers them with const()). A constant
 *  the file does not carry is null, and the rule that needs it is off: nothing here falls back to a literal. */
export function planRules(planner) {
  const c = (planner && planner.constants) || {};
  const val = (name) => (c[name] && c[name].value != null ? c[name].value : null);
  return { hypotheticalPerHome: val('PLAN_HYPOTHETICAL_PER_HOME'), noUpgradePOver: val('PLAN_NO_UPGRADE_P_OVER'),
    ae90Share: val('PLAN_SCREEN_SHARE_AE90'), nameplateShare: val('PLAN_SCREEN_SHARE_NAMEPLATE'),
    corePowerKw: val('CORE_POWER_KW') };
}

/** 0 | 20 | 50 from 0, '20', 'g20', ... (unknown -> 0). */
export function growthOf(g) {
  const n = typeof g === 'string' ? Number(g.replace(/^g/, '')) : Number(g ?? 0);
  return Number.isFinite(n) ? n : 0;
}

/** A preset index or a raw number -> the value (and its labelled source). */
function preset(list, x, dflt) {
  if (typeof x === 'number' && Number.isInteger(x) && x >= 0 && x < list.length) return list[x];
  if (typeof x === 'number') return { v: x, label: 'ASSUMPTION', cite: 'entered on the card' };
  return list[dflt];
}

/** The capacities of one transformer at a growth level: OpenDSS wins at g0 (cap.*.shown), screening otherwise. */
export function capsFor(planner, row, growth = 0) {
  const gn = growthOf(growth);
  const g = `g${gn}`;
  const r = planner.meta.tfOrder.indexOf(row.tf);
  const blk = planner.perK[g] ?? planner.perK.g0;
  const g0 = gn === 0 || !planner.perK[g];
  return {
    naive: g0 ? row.cap.naive.shown : blk.capNaive[r],
    aware: g0 ? row.cap.aware.shown : blk.capAware[r],
    paper: row.cap.paper.v,
    ae90: row.cap.paper.ae90,
    utility: row.cap.utility ? row.cap.utility.v : null,
    upNaive: row.up.naive.v, upAware: row.up.aware.v, upPaper: row.up.paper.v, upAe90: row.up.paper.ae90 ?? null,
    checked: g0 && planner.referee.status === 'checked',
    growth: g0 ? 0 : gn,
    upAtToday: !g0,                                  // one size up was simulated at today's load only (screening)
  };
}

function settingOf(knobs, dflt) {
  if (knobs.setting) return knobs.setting;
  if (knobs.dispatch === 'naive') return 'naive';
  if (knobs.dispatch === 'aware') return knobs.credit ? 'aware-credit' : 'aware-screen';
  return dflt;
}

/**
 * Build decide()'s parameters from planner.json so the UI never assembles them by hand (shape: see the top).
 */
export function paramsFor(planner, tfIndex, k, knobs = {}) {
  const row = tfRow(planner, tfIndex);
  if (!row) throw new Error(`planner: transformer ${tfIndex} is not a homes-serving transformer`);
  const d = planner.decision.defaults ?? {};
  const setting = settingOf(knobs, d.setting ?? 'aware-screen');
  if (!SETTINGS.includes(setting)) throw new Error(`planner: setting ${setting} not in ${SETTINGS}`);
  const growth = growthOf(knobs.growth ?? d.growth ?? 0);
  const m = planner.money;
  const caps = capsFor(planner, row, growth);
  const paper = knobs.screen === 'ae90' ? caps.ae90 : caps.paper;
  const upPaper = knobs.screen === 'ae90' ? caps.upAe90 : caps.upPaper;
  if (upPaper == null || paper == null) throw new Error(`planner: no ${knobs.screen ?? 'nameplate100'} paper screen in planner.json`);
  const c = bindingCap({ naive: caps.naive, aware: caps.aware, paper, utility: caps.utility }, setting);
  const cUp = Math.max(c, bindingCap({ naive: caps.upNaive, aware: caps.upAware, paper: upPaper }, setting));
  const Cl = preset(m.upgradePresets, knobs.cost, d.cost ?? 1);
  const vl = preset(m.valuePresets, knobs.value, d.value ?? 0);
  const r = m.discount.v;
  const C = Cl.v;
  const inc = row.up.incrementUSD.v;
  const curves = planner.demand.curves[row.nb.key];
  const referral = knobs.q ? knobs.q === 'q30' : (knobs.referral ?? d.referral ?? false);
  const p = {
    k0: Math.max(0, Math.round(k)), homes: row.homes, c, cUp, age: row.age.v, survTable: planner.survival.r,
    C, Cinc: inc == null ? C : Math.min(C, inc), L: m.leadMonths.v, r, V: annuity(vl.v, r, m.contractYears.v),
    pLoss: m.pLoss.v, s: m.sIncrement.v, H: m.horizonYears.v, paths: knobs.paths ?? planner.decision.paths.v,
    perMember: m.coresPerMember.v, life: m.contractYears.v,
  };
  Object.assign(p, { deciles: referral ? curves.q30 : curves.q0, caps: { ...caps, paper, upPaper, c, cUp },
    row, setting, v: vl.v, cost: Cl, value: vl, knobs: { setting, growth, referral }, rules: planRules(planner) });
  return p;
}

/**
 * The card's verdict (§3.4.4) as a code, never a sentence (the UI words it):
 *  'no-upgrade'        fits today and < 5% chance of outgrowing within the horizon in the fast (p90) scenario
 *  'wait-and-watch'    fits today; least regret is to wait (upgrade when the next Core is sold)
 *  'upgrade-now'       least regret is to upgrade now
 *  'dont-upgrade'      fits today; least regret is never to upgrade
 *  'dont-upgrade-tell' over the cap today and not upgrading wins: tell the member(s) before install day
 */
export function verdict(p, d) {
  const overToday = p.k0 > p.c;
  const unlocksNow = Math.max(0, p.cUp - p.c);
  let code;
  const pMax = p.rules ? p.rules.noUpgradePOver : null;          // PLAN_NO_UPGRADE_P_OVER; null = the rule is off
  if (!overToday && pMax != null && d.pOverP90 < pMax) code = 'no-upgrade';
  else if (overToday) code = d.leastRegret === 'never' ? 'dont-upgrade-tell' : 'upgrade-now';
  else code = { wait: 'wait-and-watch', upgrade: 'upgrade-now', never: 'dont-upgrade' }[d.leastRegret];
  return { code, overToday, blockedToday: Math.max(0, p.k0 - p.c), roomToday: Math.max(0, p.c - p.k0), unlocksNow,
    breakEven: breakEven(p.C, p.V), breakEvenValue: breakEvenValue(p.C, unlocksNow, p.r, p.life),
    twoRows: overToday };
}

/**
 * The battery rack (§4.3): one state per Core j = 1..k under a setting at a growth level.
 * 'fits' | 'paper' (past the utility rule, within physics) | 'overload' (naive: a battery-caused normal-tier event) |
 * 'earnsLess' (feeder-aware past its 90% line); plus hypothetical (j > 2 x homes), approx (j off the aware grid at
 * g20 / g50: the aware per-k values there are interpolated) and tier (the naive month's worst tier code at j).
 */
export function rackStates(planner, tfIndex, k, setting = 'aware-screen', growth = 0) {
  const row = tfRow(planner, tfIndex);
  const caps = capsFor(planner, row, growth);
  const blk = planner.perK[`g${caps.growth}`] ?? planner.perK.g0;
  const grid = blk.awareGrid ? new Set(blk.awareGrid) : null;
  const r = planner.meta.tfOrder.indexOf(row.tf);
  const rule = caps.utility ?? caps.paper;
  const perHome = planRules(planner).hypotheticalPerHome;        // PLAN_HYPOTHETICAL_PER_HOME; null = none hatched
  const out = [];
  for (let j = 1; j <= Math.min(k, planner.meta.kMax); j++) {
    let state = 'fits';
    if (setting === 'naive' && j > caps.naive) state = 'overload';
    else if (setting !== 'naive' && j > caps.aware) state = 'earnsLess';
    else if (setting !== 'aware-credit' && j > rule) state = 'paper';
    out.push({ j, state, hypothetical: perHome != null && j > perHome * row.homes, approx: setting !== 'naive' && !!grid && !grid.has(j),
      tier: blk.naiveTier ? blk.naiveTier[r][j] : null });
  }
  return out;
}
