// ui/story/dev-b-fixtures/planner.js (UI-B, DEV ONLY; delete at integration): a stand-in for PLANNER's ui/lib/planner.js,
// used by dev-b.html only when the real module is missing. decide() and helpers are DESIGN-CAPACITY-PLANNER Appendix A
// verbatim; paramsFor() is UI-B's guess at PLANNER's signature paramsFor(planner, tfIndex, k, knobs).
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function monthly(yearly) {
  const out = [];
  for (let t = 0; t <= 12 * (yearly.length - 1); t++) {
    const i = Math.min(Math.floor(t / 12), yearly.length - 2), f = (t - 12 * i) / 12;
    out.push(yearly[i] + (yearly[i + 1] - yearly[i]) * f);
  }
  return out;
}
export function surv(table, a) {
  if (a >= table.length - 1) return 0;
  const i = Math.floor(a), f = a - i; return table[i] + (table[i + 1] - table[i]) * f;
}
export const pReplace = (table, age, years) => (surv(table, age) > 0 ? 1 - surv(table, age + years) / surv(table, age) : 1);
export const annuity = (v, r, life) => v * (1 - (1 + r) ** -life) / r;
export function scenarioCosts(p, F, seed) {
  const { k0, homes, c, cUp, age, survTable, C, Cinc, L, r, V, pLoss, s, H = 5, paths = 1000, perMember = 1 } = p;
  const T = 12 * H, rng = mulberry32(seed), m = Math.max(0, homes - Math.min(k0, homes));
  const disc = Array.from({ length: T + 1 }, (_, t) => (1 + r) ** (-t / 12));
  const sum = { upgrade: 0, wait: 0, never: 0, over: 0 };
  const N = new Array(T + 1);
  for (let p_ = 0; p_ < paths; p_++) {
    N.fill(k0);
    for (let j = 0; j < m; j++) {
      const u = rng(); if (u > F[T]) continue;
      let t = 1; while (F[t] < u) t++;
      for (let x = t; x <= T; x++) N[x] += perMember;
    }
    const newOver = (cap, t) => Math.max(0, N[t] - cap) - (t ? Math.max(0, N[t - 1] - cap) : 0);
    const newWait = (t) => newOver(c, t) - newOver(cUp, t);
    let lostUp = 0, lostC = 0, tau = -1;
    for (let t = 0; t <= T; t++) { lostUp += newOver(cUp, t) * disc[t]; lostC += newOver(c, t) * disc[t]; if (tau < 0 && N[t] > c) tau = t; }
    let delayNow = 0; for (let t = 0; t < Math.min(L, T + 1); t++) delayNow += newWait(t) * disc[t];
    sum.upgrade += C + pLoss * V * delayNow + V * lostUp;
    sum.never += V * lostC;
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
export function decide(p, deciles, seed = 20260926) {
  const sc = deciles.map((y, i) => scenarioCosts(p, monthly(y), seed + i));
  const acts = ['upgrade', 'wait', 'never'];
  const expected = Object.fromEntries(acts.map((a) => [a, sc.reduce((x, s) => x + s[a], 0) / sc.length]));
  const named = { p10: sc[0], p50: sc[4], p90: sc[8] };
  const regret = Object.fromEntries(acts.map((a) => [a, Math.max(...Object.values(named).map((s) => s[a] - Math.min(...acts.map((b) => s[b]))))]));
  const pick = (o) => acts.reduce((b, a) => (o[a] < o[b] - 1e-9 ? a : b), acts[0]);
  return { expected, regret, leastRegret: pick(regret), leastExpected: pick(expected), pOver: named.p50.pOver };
}
/** GUESS at PLANNER's API: the decide() inputs for one transformer at k Cores wanted now. */
export function paramsFor(planner, tfIndex, k, knobs = {}) {
  const t = planner.tfs.find((x) => x.tf === tfIndex);
  if (!t) return null;
  const m = planner.money, setting = knobs.setting || 'aware-screen';
  const rule = t.cap.paper.v;
  const c = setting === 'naive' ? Math.min(t.cap.naive.v, rule) : setting === 'aware-screen' ? Math.min(t.cap.aware.v, rule) : t.cap.aware.v;
  const cUp = setting === 'naive' ? Math.min(t.up.naive.v, t.up.paper.v) : setting === 'aware-screen' ? Math.min(t.up.aware.v, t.up.paper.v) : t.up.aware.v;
  const r = m.PLAN_DISCOUNT.v, V = annuity((m.valuePresets[knobs.value ?? 0] || m.PLAN_MEMBER_VALUE_USD_YR).v, r, m.PLAN_CONTRACT_YEARS.v);
  const q = knobs.referral ? 'q30' : 'q0';
  return {
    k0: k, homes: t.homes, c, cUp, age: t.age.v, survTable: planner.survival.r,
    C: (m.upgradePresets[knobs.cost ?? 1] || m.PLAN_UPGRADE_USD).v, Cinc: t.up.incrementUSD.v, L: m.PLAN_LEAD_MONTHS.v, r, V,
    pLoss: m.PLAN_P_LOSS.v, s: m.PLAN_S_INCREMENT.v, H: m.PLAN_HORIZON_YEARS.v, paths: planner.decision.paths.v,
    deciles: planner.demand.curves[t.nb.key][q],
  };
}
