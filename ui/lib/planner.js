// ui/lib/planner.js (PLANNER): the capacity planner's upgrade decision, pure, seeded and node-testable.
// Ported from DESIGN-CAPACITY-PLANNER.md Appendix A (same exported names). Physics is never computed here: every
// capacity comes from ui/data/p2/planner.json (sim.planner). This module only does the money arithmetic of §3.4:
// three actions (upgrade now / wait and watch / don't upgrade) over nine demand-decile curves x 1,000 seeded paths.
// Every number it returns is DERIVED; wrap it with `labelOf(planner, x)` before it reaches format.js.

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
/** The member value per year at which an upgrade that unlocks `unlocked` members pays for itself (CRITIQUE must-fix 5). */
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
  const { k0, homes, c, cUp, age, survTable, C, Cinc, L, r, V, pLoss, s, H = 5, paths = 1000, perMember = 1 } = p;
  const T = 12 * H, rng = mulberry32(seed), m = Math.max(0, homes - Math.min(k0, homes));
  const disc = Array.from({ length: T + 1 }, (_, t) => (1 + r) ** (-t / 12));
  const sum = { upgrade: 0, wait: 0, never: 0, over: 0 };
  const N = new Array(T + 1);
  for (let p_ = 0; p_ < paths; p_++) {
    N.fill(k0);
    for (let j = 0; j < m; j++) {                     // each non-member home joins at the first month F(t) >= u
      const u = rng(); if (u > F[T]) continue;
      let t = 1; while (F[t] < u) t++;
      for (let x = t; x <= T; x++) N[x] += perMember;
    }
    const newOver = (cap, t) => Math.max(0, N[t] - cap) - (t ? Math.max(0, N[t - 1] - cap) : 0);
    const newWait = (t) => newOver(c, t) - newOver(cUp, t);        // over c but within cUp: served once the upgrade lands
    let lostUp = 0, lostC = 0, tau = -1;
    for (let t = 0; t <= T; t++) { lostUp += newOver(cUp, t) * disc[t]; lostC += newOver(c, t) * disc[t]; if (tau < 0 && N[t] > c) tau = t; }
    let delayNow = 0; for (let t = 0; t < Math.min(L, T + 1); t++) delayNow += newWait(t) * disc[t];
    sum.upgrade += C + pLoss * V * delayNow + V * lostUp;
    sum.never += V * lostC;
    // replacement month rho from the age survival curve (inverse CDF), then does the utility upsize at it (prob s)?
    const ur = rng(), us = rng();
    let rho = Infinity; for (let t = 1; t <= T; t++) if (pReplace(survTable, age, t / 12) >= ur) { rho = t; break; }
    if (tau >= 0) {
      sum.over += 1;
      if (rho < tau && us < s) sum.wait += Cinc * disc[rho] + V * lostUp;
      else { let d = 0; for (let t = tau; t < Math.min(tau + L, T + 1); t++) d += newWait(t) * disc[t];
        sum.wait += C * disc[tau] + pLoss * V * d + V * lostUp; }
    }
  }
  return { upgrade: sum.upgrade / paths, wait: sum.wait / paths, never: sum.never / paths, pOver: sum.over / paths };
}
/** Nine decile curves (p10..p90): expected = their mean; worst regret over p10, p50, p90 (§3.4.3).
 *  Returns {expected{upgrade,wait,never}, regret{upgrade,wait,never}, leastRegret, leastExpected, pOver (p50 curve),
 *  pOverP90 (p90 curve: the chance of outgrowing the cap within the horizon in the fast-growth scenario)}. */
export function decide(p, deciles, seed = 20260926) {
  const sc = deciles.map((y, i) => scenarioCosts(p, monthly(y), seed + i));
  const acts = ['upgrade', 'wait', 'never'];
  const expected = Object.fromEntries(acts.map((a) => [a, sc.reduce((x, s) => x + s[a], 0) / sc.length]));
  const named = { p10: sc[0], p50: sc[4], p90: sc[8] };
  const regret = Object.fromEntries(acts.map((a) => [a, Math.max(...Object.values(named).map((s) => s[a] - Math.min(...acts.map((b) => s[b]))))]));
  const pick = (o) => acts.reduce((b, a) => (o[a] < o[b] - 1e-9 ? a : b), acts[0]);
  return { expected, regret, leastRegret: pick(regret), leastExpected: pick(expected), pOver: named.p50.pOver, pOverP90: named.p90.pOver };
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

/** A preset index or a raw number -> the value (and its labelled source). */
function pick(list, x, dflt) {
  if (typeof x === 'number' && Number.isInteger(x) && x >= 0 && x < list.length) return list[x];
  if (typeof x === 'number') return { v: x, label: 'ASSUMPTION', cite: 'entered on the card' };
  return list[dflt];
}

/** The capacities of one transformer at a growth level: OpenDSS wins at g0 (cap.*.shown), screening otherwise. */
export function capsFor(planner, row, growth = 0) {
  const g = `g${growth}`;
  const r = planner.meta.tfOrder.indexOf(row.tf);
  const blk = planner.perK[g] ?? planner.perK.g0;
  const g0 = growth === 0 || !planner.perK[g];
  return {
    naive: g0 ? row.cap.naive.shown : blk.capNaive[r],
    aware: g0 ? row.cap.aware.shown : blk.capAware[r],
    paper: row.cap.paper.v,
    ae90: row.cap.paper.ae90,
    utility: row.cap.utility ? row.cap.utility.v : null,
    upNaive: row.up.naive.v, upAware: row.up.aware.v, upPaper: row.up.paper.v,
    checked: g0 && planner.referee.status === 'checked',
  };
}

/**
 * Build decide()'s parameters from planner.json so the UI never assembles them by hand.
 * knobs: {setting: 'naive'|'aware-screen'|'aware-credit' (default planner.decision.defaults.setting),
 *         cost: preset index into money.upgradePresets or USD, value: preset index into money.valuePresets or USD/yr,
 *         referral: bool (q30 curves), growth: 0|20|50 (caps from perK.g<growth>), screen: 'nameplate100'|'ae90',
 *         paths: override of decision.paths}
 * k is "Cores wanted here now" (installed + pending + the slider). Returns p (decide's input) plus
 * p.deciles (the nine curves to pass to decide), p.caps, p.row, p.setting, p.v (member value/yr), p.knobs.
 */
export function paramsFor(planner, tfIndex, k, knobs = {}) {
  const row = tfRow(planner, tfIndex);
  if (!row) throw new Error(`planner: transformer ${tfIndex} is not a homes-serving transformer`);
  const d = planner.decision.defaults ?? {};
  const setting = knobs.setting ?? d.setting ?? 'aware-screen';
  if (!SETTINGS.includes(setting)) throw new Error(`planner: setting ${setting} not in ${SETTINGS}`);
  const growth = knobs.growth ?? d.growth ?? 0;
  const m = planner.money;
  const caps = capsFor(planner, row, growth);
  const paper = knobs.screen === 'ae90' ? caps.ae90 : caps.paper;
  const upPaper = knobs.screen === 'ae90' ? Math.floor((0.9 * row.up.kva.v) / 20 + 1e-9) : caps.upPaper;
  const c = bindingCap({ naive: caps.naive, aware: caps.aware, paper, utility: caps.utility }, setting);
  const cUp = Math.max(c, bindingCap({ naive: caps.upNaive, aware: caps.upAware, paper: upPaper }, setting));
  const Cl = pick(m.upgradePresets, knobs.cost, d.cost ?? 1);
  const vl = pick(m.valuePresets, knobs.value, d.value ?? 0);
  const r = m.discount.v;
  const C = Cl.v;
  const inc = row.up.incrementUSD.v;
  const curves = planner.demand.curves[row.nb.key];
  const referral = knobs.referral ?? d.referral ?? false;
  const p = {
    k0: Math.max(0, Math.round(k)), homes: row.homes, c, cUp, age: row.age.v, survTable: planner.survival.r,
    C, Cinc: inc == null ? C : Math.min(C, inc), L: m.leadMonths.v, r, V: annuity(vl.v, r, m.contractYears.v),
    pLoss: m.pLoss.v, s: m.sIncrement.v, H: m.horizonYears.v, paths: knobs.paths ?? planner.decision.paths.v,
    perMember: m.coresPerMember.v, life: m.contractYears.v,
  };
  return Object.assign(p, { deciles: referral ? curves.q30 : curves.q0, caps: { ...caps, paper, upPaper, c, cUp },
    row, setting, v: vl.v, cost: Cl, value: vl, knobs: { setting, growth, referral } });
}

/**
 * The card's verdict (§3.4.4) as a code, never a sentence (the UI words it):
 *  'no-upgrade'        fits today and < 5% chance of outgrowing within the horizon in the fast (p90) scenario
 *  'wait-and-watch'    fits today; least regret is to wait (upgrade when the next Core is sold)
 *  'upgrade-now'       least regret is to upgrade now
 *  'dont-upgrade'      fits today; least regret is never to upgrade
 *  'dont-upgrade-tell' over the cap today and not upgrading wins: tell the member(s) before install day
 * Returns {code, overToday, blockedToday, roomToday, unlocksNow, breakEven, breakEvenValue, twoRows}.
 */
export function verdict(p, d) {
  const overToday = p.k0 > p.c;
  const unlocksNow = Math.max(0, p.cUp - p.c);
  let code;
  if (!overToday && d.pOverP90 < 0.05) code = 'no-upgrade';
  else if (overToday) code = d.leastRegret === 'never' ? 'dont-upgrade-tell' : 'upgrade-now';
  else code = { wait: 'wait-and-watch', upgrade: 'upgrade-now', never: 'dont-upgrade' }[d.leastRegret];
  return { code, overToday, blockedToday: Math.max(0, p.k0 - p.c), roomToday: Math.max(0, p.c - p.k0), unlocksNow,
    breakEven: breakEven(p.C, p.V), breakEvenValue: breakEvenValue(p.C, unlocksNow, p.r, p.life ?? 12),
    twoRows: overToday };
}

/**
 * The battery rack (§4.3): one state per Core j = 1..k under a setting at a growth level.
 * 'fits' | 'paper' (past the utility rule, within physics) | 'overload' (naive: a battery-caused normal-tier event) |
 * 'earnsLess' (feeder-aware past its 90% line); plus hypothetical (j > 2 x homes) and tier (naive month worst tier).
 */
export function rackStates(planner, tfIndex, k, setting = 'aware-screen', growth = 0) {
  const row = tfRow(planner, tfIndex);
  const caps = capsFor(planner, row, growth);
  const blk = planner.perK[`g${growth}`] ?? planner.perK.g0;
  const r = planner.meta.tfOrder.indexOf(row.tf);
  const rule = caps.utility ?? caps.paper;
  const out = [];
  for (let j = 1; j <= Math.min(k, planner.meta.kMax); j++) {
    let state = 'fits';
    if (setting === 'naive' && j > caps.naive) state = 'overload';
    else if (setting !== 'naive' && j > caps.aware) state = 'earnsLess';
    else if (setting !== 'aware-credit' && j > rule) state = 'paper';
    out.push({ j, state, hypothetical: j > 2 * row.homes, tier: blk.naiveTier ? blk.naiveTier[r][j] : null });
  }
  return out;
}
