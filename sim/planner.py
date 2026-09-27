"""The transformer capacity planner (RZ's three-layer scope; DESIGN-CAPACITY-PLANNER.md §2-3): `ui/data/p2/planner.json`.

    python -m sim.planner                 # build ui/data/p2/planner.json (sweeps cached in data/cache/planner/)
    python -m sim.planner --referee       # heavy: also run the OpenDSS referee (13 month solves) and merge it
    python -m sim.planner referee         # heavy: only the OpenDSS referee -> data/planner/referee.json
    python -m sim.planner ages            # regenerate data/planner/tf_simulated_ages.csv (DERIVED, seed 20260926)
    python -m sim.planner --quick         # 12 transformers, no file written: a smoke run (< 1 min)

Environment: PLAN_WORKERS (default 1) runs the feeder-aware sweep chunks in that many processes.

Layers (simulators/rz/research/capacity-planner/DATA-SCOPE-RZ-CAPACITY-PLANNER.md, binding):
  1. network view: every homes-serving transformer's room under naive and feeder-aware charging (`tfs[].cap`,
     `sizeSummary`, `baseline`);
  2. one transformer, 0-50 Cores: per-k loading and earnings (`perK.g0|g20|g50`), the three limits, one size up (`up`);
  3. the upgrade priority list (`ranking`), plus everything the browser's upgrade card needs (`survival`, `demand`,
     `money`, `decision`; the Monte Carlo decision itself runs in ui/lib/planner.js).

Physics (ported from the scout's tf_capacity_sweep.py, now on the repo's own root sim/, nothing read from elsewhere):
  naive  k Cores on T = k x one naive Core's month schedule (every naive Core follows the same zone signal from the
         same SoC; the identity is tested in sim/tests/test_planner.py). capNaive = the largest k with no
         battery-caused normal-tier event (> 110% for >= 30 min while the batteries raise the loading) at any j <= k.
  aware  sim.siting.simulate(..., "aware", "d26"), one column per (T, k). capAware = the largest k whose Cores each
         still earn >= PLAN_AWARE_EARN_MIN (90%) of one unconstrained Core, with no battery-caused event, at every
         j <= k. Feeder-aware never overloads; its limit is economic, and the UI says so.
  paper  floor((share x kVA - existing DG kW) / Core kW), share 1.0 (nameplate100) or 0.9 (ae90).
  up     the same with the next standard size and that size's median surrogate coefficients (screening).
OpenDSS referee (§3.1.7): naive at capNaive and capNaive + 1, aware at capAware, every 15-min step of August, several
transformers per month solve. It merges only when its sha256 equals the build's (the schedules it judged), else
`referee.status = "not run"` and every cap is labelled screening. Display rule: OpenDSS wins (`cap.*.shown`).

No language model produces any number here. Every number in planner.json is {v, label, cite} or a bulk array
labelled in `series`.
"""
import csv
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

from .constants import (TAG, const, export, CORE_POWER_KW, TIER_NORMAL_PCT, TIER_NORMAL_MIN, TIER_EMERGENCY_PCT,
                        TIER_AMBER_PCT, AWARE_MARGIN, GROWTH, STAND_IN, CURTAIL_CAP, DATA_FILE_CAP_MB)
from .contracts import envelope, inputs_sha, labelled, write_json, dumps

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "planner"
CACHE = ROOT / "data" / "cache" / "planner"
OUT = ROOT / "ui" / "data" / "p2" / "planner.json"
PRIVATE_OUT = ROOT / "ui" / "data" / "private" / "planner.json"
REFEREE_JSON = DATA / "referee.json"
AGES_CSV = DATA / "tf_simulated_ages.csv"
ASSETS_SIM = DATA / "assets.sim.csv"
ASSETS_LOCAL = DATA / "assets.local.csv"
DESIGN = "simulators/rz/research/capacity-planner/DESIGN-CAPACITY-PLANNER.md"
SIZE_CAP_BYTES = 2.0 * 1024 * 1024   # lead ruling 26 Sep: raised from 1.2 MB so perK.g20 / g50 stay (Learnings Q3)
SWEEP_VERSION = "planner-sweep-1"   # bump when the sweep code in this file changes (it keys data/cache/planner/)

# =================================================================================================================
# constants (registered here, never in sim/constants.py; each named, labelled and cited)
# =================================================================================================================
PUCT_54224_49 = "https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF"
NREL_COST_DB = "https://data.openei.org/submissions/8185"
PLAN_UPGRADE_USD = const("PLAN_UPGRADE_USD", 10000, "REAL",
                         f"Base told the PUCT a residential post-install transformer upgrade can cost about $10,000 "
                         f"(PUCT 54224 item 49, {PUCT_54224_49}); Base's figure, not a quote")
PLAN_UPGRADE_LOW_USD = const("PLAN_UPGRADE_LOW_USD", 4178, "REAL",
                             f"NREL distribution transformer cost database v2 (2017 dollars): installed cost of a 50 kVA "
                             f"single-phase overhead unit ({NREL_COST_DB}); equipment + install, not Base's all-in cost")
PLAN_UPGRADE_HIGH_USD = const("PLAN_UPGRADE_HIGH_USD", 15000, "ASSUMPTION",
                              "a high preset: prices have risen since 2017 (NREL 2024 transformer demand report, "
                              "https://www.osti.gov/biblio/2309697); no source gives this value")
PLAN_UNIT_USD = const("PLAN_UNIT_USD", {"25": 3853, "50": 4178, "75": 5249, "100": 6057}, "REAL",
                      f"NREL cost DB v2 (2017 dollars), installed single-phase overhead units ({NREL_COST_DB}); "
                      "no 10 kVA row")
PLAN_UP_SIZES = const("PLAN_UP_SIZES", {"10": 25, "25": 50, "50": 75, "75": 100}, "ASSUMPTION",
                      "one standard size up (DESIGN §3.1.5); 10 -> 25 added for T-253, the one 10 kVA unit "
                      "(CRITIQUE-CAP-base should-fix 6)")
PLAN_LEAD_MONTHS = const("PLAN_LEAD_MONTHS", 6, "ASSUMPTION",
                         "NREL reports lead times up to 2 years for distribution transformers (OSTI 2309697); a service "
                         "swap from stock is faster (UNVERIFIED)")
PLAN_DISCOUNT = const("PLAN_DISCOUNT", 0.08, "ASSUMPTION", "discount rate per year, a knob (DESIGN §2.2)")
PLAN_MEMBER_VALUE_USD_YR = const("PLAN_MEMBER_VALUE_USD_YR", 631, "DERIVED",
                                 "one Core, 2025 LZ_NORTH, planning on public day-ahead prices (DATA-MARKET-PROFIT.md §4); "
                                 "gross energy value, not Base's profit")
PLAN_MEMBERSHIP_USD_MO = const("PLAN_MEMBERSHIP_USD_MO", 19, "REAL",
                               "Base's $19 monthly membership (Base Help Center, "
                               "https://help.basepowercompany.com/en/categories/2347329-backup-battery-service)")
PLAN_MEMBER_VALUE_FEE_USD_YR = const("PLAN_MEMBER_VALUE_FEE_USD_YR", 631 + 12 * 19, "DERIVED",
                                     "$631 energy value + 12 x $19 membership (CRITIQUE-CAP-base must-fix 5); "
                                     "still not Base's profit")
PLAN_MEMBER_VALUE_CONTRACT_USD_YR = const("PLAN_MEMBER_VALUE_CONTRACT_USD_YR", 2040, "DERIVED",
                                          "Austin Energy's contract, up to $4.08M/yr for 40 MW, per 20 kW Core (City of "
                                          "Austin RCA 26-1526, https://services.austintexas.gov/edims/document.cfm?id=471637)")
PLAN_CONTRACT_YEARS = const("PLAN_CONTRACT_YEARS", 12, "REAL",
                            "Base Core Battery Services Agreement term "
                            "(https://help.basepowercompany.com/en/categories/2347329-backup-battery-service)")
PLAN_P_LOSS = const("PLAN_P_LOSS", 0.3, "ASSUMPTION", "the chance a member told 'wait' walks away; ask Base (DESIGN §7)")
PLAN_S_INCREMENT = const("PLAN_S_INCREMENT", 0.5, "ASSUMPTION",
                         "the chance the utility upsizes at a planned replacement and charges Base only the increment; "
                         "UNVERIFIED that any utility does this")
PLAN_AWARE_EARN_MIN = const("PLAN_AWARE_EARN_MIN", 0.90, "ASSUMPTION",
                            "feeder-aware limit: every Core still earns >= 90% of an unconstrained Core (the analogue "
                            "of CURTAIL_CAP; DATA-ASSETS-DEMAND.md §5.2)")
PLAN_AWARE_K95 = const("PLAN_AWARE_K95", 0.95, "ASSUMPTION",
                       "awareK95: the k at which the transformer's total earnings reach 95% of their ceiling (hover)")
PLAN_RADIUS_M = const("PLAN_RADIUS_M", 200, "ASSUMPTION", "neighbourhood circle for demand (DATA-ASSETS-DEMAND.md §5.2)")
PLAN_LAMBDA_BAR = const("PLAN_LAMBDA_BAR", 0.0044, "DERIVED",
                        "about 74 Base homes a day / 6,091,247 Texas owner-occupied detached homes (ACS 2024 B25032, "
                        "data/planner/acs2024_b25032_tx_and_tracts.csv; Base scale via TechCrunch 3 Aug 2026, research "
                        "notes, not re-fetched)")
PLAN_K_DISP = const("PLAN_K_DISP", 0.5, "ASSUMPTION",
                    "Gamma shape (range 0.3-1.0): CenterPoint per-feeder battery counts are strongly clustered "
                    "(variance/mean = 22, DERIVED from the 2025 DG reports, PUCT project 59167)")
PLAN_Q_REFERRAL = const("PLAN_Q_REFERRAL", 0.3, "ASSUMPTION",
                        "referral (Bass imitation) term per year when the toggle is on; PV peer effects (Graziano & "
                        "Gillingham 2015; NREL dGen Texas residential q = 0.648); off by default")
PLAN_T0_YEARS = const("PLAN_T0_YEARS", 1.5, "ASSUMPTION", "the years over which today's installed members arrived")
PLAN_CORES_PER_MEMBER = const("PLAN_CORES_PER_MEMBER", 1, "ASSUMPTION",
                              "Base averages about 1.35 batteries per home (research notes, REAL); 1 is the planner default")
PLAN_HORIZON_YEARS = const("PLAN_HORIZON_YEARS", 5, "ASSUMPTION", "decision horizon; joins after year 5 are ignored")
PLAN_DEMAND_PATHS = const("PLAN_DEMAND_PATHS", 4000, "ASSUMPTION", "Monte Carlo paths per neighbourhood key (DESIGN §3.3)")
PLAN_DECISION_PATHS = const("PLAN_DECISION_PATHS", 1000, "ASSUMPTION", "Monte Carlo paths per decile curve in the browser")
PLAN_SEED = const("PLAN_SEED", 20260926, "ASSUMPTION", "the planner's seed (ages, demand, the browser decision)")
PLAN_SCREEN = const("PLAN_SCREEN", "nameplate100", "REAL",
                    "nameplate <= transformer kVA is TDSP practice as Base describes it (PUCT 54233 items 85, 92); "
                    "alternative ae90: Austin Energy denies when all DG kW AC > 90% of the transformer rating "
                    "(AE DG guide rev 14, p. 13)")
PLAN_GROWTH_PCTS = const("PLAN_GROWTH_PCTS", [0, 20, 50], "ASSUMPTION",
                         "home-load growth levels for the 'as home load grows' view (docs/story-contract.md ruling 1; "
                         "+20% is GROWTH)")
PLAN_SURV_SHAPE = const("PLAN_SURV_SHAPE", 4.6141, "REAL",
                        "Weibull shape (Yao & Dvorkin, arXiv 2604.18411, Table 3, optimistic)")
PLAN_SURV_SCALE = const("PLAN_SURV_SCALE", 39.071, "DERIVED",
                        "Weibull scale solved so the DOE retirement function's mean life is 32.0 years (89 FR 29834; "
                        "DOE NOPR TSD §8.3.10)")
PLAN_SURV_RANDOM = const("PLAN_SURV_RANDOM", 0.005, "REAL", "DOE retirement function: 0.5%/yr random failure (TSD §8.3.10)")
PLAN_SURV_CORROSION = const("PLAN_SURV_CORROSION", 0.005, "REAL", "DOE: 0.5%/yr corrosion from age 15 (TSD §8.3.10)")
PLAN_SURV_CORROSION_FROM = const("PLAN_SURV_CORROSION_FROM", 15, "REAL", "DOE: corrosion term from age 15 (TSD §8.3.10)")
PLAN_SURV_MAX_AGE = const("PLAN_SURV_MAX_AGE", 60, "REAL", "DOE: no unit survives past 60 years (89 FR 29834)")
PLAN_NOW_YEAR = const("PLAN_NOW_YEAR", 2026, "ASSUMPTION", "ages are measured in 2026")
PLAN_ONCOR_FAIL_RATE = const("PLAN_ONCOR_FAIL_RATE", 0.0068, "REAL",
                             "Oncor's transformer failure rate, 0.68%/yr (PUCT 56545 item 58), shown beside P_rep for contrast")
PLAN_REF_BATCH_NAIVE = const("PLAN_REF_BATCH_NAIVE", 140, "ASSUMPTION", "OpenDSS referee: at most 140 naive Cores per month solve")
PLAN_REF_BATCH_AWARE = const("PLAN_REF_BATCH_AWARE", 400, "ASSUMPTION", "OpenDSS referee: at most 400 aware Cores per month solve")
PLAN_DEMO_TF = const("PLAN_DEMO_TF", 61, "ASSUMPTION", "the demo transformer: 50 kVA pole, 3 homes, old (DESIGN §3.7)")
PLAN_DEFAULT_TF = const("PLAN_DEFAULT_TF", 240, "ASSUMPTION", "P1's unrelieved transformer (BRIDGE_TF), the default pick")

K_MAX = 50
KS = list(range(K_MAX + 1))
K_GRID = list(range(13)) + [15, 20, 25, 30, 40, 50]          # the scout's 19-value aware grid
SIZES = [25, 50, 75, 100]
SCREENS = [{"id": "nameplate100", "share": 1.0, "label": "REAL",
            "cite": "nameplate <= transformer kVA: TDSP practice as Base describes it (PUCT 54233 items 85, 92)"},
           {"id": "ae90", "share": 0.9, "label": "REAL",
            "cite": "Austin Energy DG guide rev 14 p. 13: all DG kW AC <= 90% of the transformer rating"}]
SCOPE = ("Core battery · D-26 onset · August 2026 prices × SMART-DS 2018 August load · empty feeder · "
         "Oncor-suburb stand-in on NREL's synthetic feeder")
SWEEP_CITE = "sim.planner sweep on sim.siting.simulate / month_metrics (surrogate screen, calibrated vs OpenDSS)"


# =================================================================================================================
# ages and survival (DERIVED; DESIGN §3.2)
# =================================================================================================================
def survival(a, d=PLAN_SURV_SCALE, e=PLAN_SURV_SHAPE):
    """DOE retirement function r(a): P(a unit is still in service at age a)."""
    a = np.asarray(a, dtype=float)
    out = (np.exp(-(a / d) ** e) * (1 - PLAN_SURV_RANDOM) ** a
           * (1 - PLAN_SURV_CORROSION) ** np.maximum(0.0, a - PLAN_SURV_CORROSION_FROM))
    return np.where(a >= PLAN_SURV_MAX_AGE, 0.0, out)


def mean_life(d=PLAN_SURV_SCALE, e=PLAN_SURV_SHAPE):
    return float(survival(np.arange(0, 81), d, e)[:-1].sum())


def fit_scale(e=PLAN_SURV_SHAPE, target=32.0):
    lo, hi = 5.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mean_life(mid, e) < target else (lo, mid)
    return (lo + hi) / 2


def p_replace(n, a):
    """P(the unit is replaced, for any reason, within n years | age a)."""
    s0 = float(survival(a))
    return 1.0 - float(survival(a + n)) / s0 if s0 > 0 else 1.0


def acs_bins():
    rows = [l.strip().split("|") for l in (DATA / "acs2024_b25034_feeder_tracts.csv").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    h = rows[0]
    bins = {2: (2020, 2024), 3: (2010, 2019), 4: (2000, 2009), 5: (1990, 1999), 6: (1980, 1989), 7: (1970, 1979),
            8: (1960, 1969), 9: (1950, 1959), 10: (1940, 1949), 11: (1920, 1939)}
    out = {}
    for row in rows[1:]:
        d = dict(zip(h, row))
        w = np.array([int(d[f"B25034_E{k:03d}"]) for k in bins], dtype=float)
        out[d["GEO_ID"].split("US")[1]] = (list(bins.values()), w / w.sum())
    return out


def simulate_ages(tracts, draws=4000, seed=PLAN_SEED):
    """Renewal Monte Carlo (the scout's age_model.py): first install ~ the tract's year-built mix (uniform in the
    decade), lifetimes ~ the DOE retirement function, renewed until one runs past 2026. Returns ages [n_tf, draws]."""
    rng = np.random.default_rng(seed)
    S = survival(np.arange(0, 81))
    pmf = np.maximum(0.0, S[:-1] - S[1:])
    pmf = pmf / pmf.sum()
    life_vals = np.arange(1, 81)
    bins = acs_bins()
    ages = np.zeros((len(tracts), draws))
    for i, g in enumerate(tracts):
        rngs, w = bins[g]
        k = rng.choice(len(w), size=draws, p=w)
        lo = np.array([rngs[j][0] for j in k])
        hi = np.array([rngs[j][1] for j in k])
        last = rng.integers(lo, hi + 1).astype(float)
        alive = np.ones(draws, dtype=bool)
        while alive.any():
            L = rng.choice(life_vals, size=draws, p=pmf)
            ret = alive & (last + L <= PLAN_NOW_YEAR)
            last = np.where(ret, last + L, last)
            alive = ret
        ages[i] = PLAN_NOW_YEAR - last
    return ages


def write_ages_csv(path=AGES_CSV):
    """Regenerate the simulated-ages CSV (`python -m sim.planner ages`): the seeded draw is `rng(7)`'s pick, as the
    scout's file (so a rebuild reproduces it)."""
    tract_of = json.loads((DATA / "tf_census_tract.json").read_text(encoding="utf-8"))["tractOfTf"]
    tracts = [tract_of[str(i)] for i in range(len(tract_of))]
    ages = simulate_ages(tracts)
    pick = ages[np.arange(len(tracts)), np.random.default_rng(7).integers(0, ages.shape[1], len(tracts))]
    lines = ["tf_index,census_tract,age_draw_2026,age_p10,age_p50,age_p90,P_replace_1y_given_draw,"
             "P_replace_5y_given_draw,label"]
    for i in range(len(tracts)):
        a = float(pick[i])
        q = [int(np.percentile(ages[i], x)) for x in (10, 50, 90)]
        lines.append(f"{i},{tracts[i]},{int(a)},{q[0]},{q[1]},{q[2]},{round(p_replace(1, a), 4)},"
                     f"{round(p_replace(5, a), 4)},\"DERIVED age prior (ACS year built x DOE retirement function), "
                     f"one seeded draw\"")
    Path(path).write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    return path


def load_ages(path=AGES_CSV):
    rows = list(csv.DictReader(Path(path).read_text(encoding="utf-8").splitlines()))
    return {int(r["tf_index"]): {"age": int(r["age_draw_2026"]), "p10": int(r["age_p10"]), "p50": int(r["age_p50"]),
                                 "p90": int(r["age_p90"])} for r in rows}


# =================================================================================================================
# paper screen, circles and demand (DERIVED; DESIGN §3.1.3, §3.3)
# =================================================================================================================
def paper_screen(kva, share=1.0, dg_kw=0.0, p_kw=CORE_POWER_KW):
    """N_paper = floor((share x kVA - existing DG kW) / battery kW), never below 0."""
    return max(0, int(math.floor((share * float(kva) - float(dg_kw)) / float(p_kw) + 1e-9)))


def distances_m(lonlat_a, lonlat_b):
    """Equirectangular metres between every a [n, 2] and b [m, 2] (lon, lat) (DERIVED; < 0.1% error at 200 m)."""
    a = np.asarray(lonlat_a, dtype=float)
    b = np.asarray(lonlat_b, dtype=float)
    R = 6371008.8
    lat0 = math.radians(float(np.mean(a[:, 1])))
    dx = np.radians(a[:, None, 0] - b[None, :, 0]) * math.cos(lat0) * R
    dy = np.radians(a[:, None, 1] - b[None, :, 1]) * R
    return np.hypot(dx, dy)


def circles(topo, fleet_homes, tfs, radius=PLAN_RADIUS_M):
    """{tf: (M eligible homes within radius of T, n installed members among them, [transformers of those homes])}."""
    homes = topo["homes"]
    elig = np.array([i for i, h in enumerate(homes) if h["eligible"]])
    hl = np.array([homes[i]["lonlat"] for i in elig])
    tl = np.array([topo["transformers"][t]["lonlat"] for t in tfs])
    d = distances_m(tl, hl)
    fset = set(int(x) for x in fleet_homes)
    out = {}
    for r, t in enumerate(tfs):
        inside = elig[d[r] <= radius]
        out[t] = (int(len(inside)), int(sum(1 for h in inside if int(h) in fset)),
                  sorted({int(homes[h]["tf"]) for h in inside}))
    return out


def demand_curves(M, n, q, seed, paths=PLAN_DEMAND_PATHS, H=PLAN_HORIZON_YEARS, k=PLAN_K_DISP, lam_bar=PLAN_LAMBDA_BAR,
                  T0=PLAN_T0_YEARS):
    """Gamma-Poisson neighbourhood model with a referral term (DATA-ASSETS-DEMAND.md §3.2; DESIGN §3.3):
    lambda ~ Gamma(k + n, rate k / lam_bar + M T0); monthly hazard h = lambda + q N(t) / M;
    N(t+1) = N(t) + Binomial(M - N(t), 1 - exp(-h / 12)). Returns (F [9][H+1] per-home cumulative join probability
    1 - exp(-sum h / 12), pointwise deciles p10..p90 at yearly points; adds (p10, p50, p90) of N(60) - n)."""
    rng = np.random.default_rng(seed)
    lam = rng.gamma(k + n, 1.0 / (k / lam_bar + M * T0), paths)
    N = np.full(paths, n, dtype=np.int64)
    cum = np.zeros(paths)
    F = [np.zeros(paths)]
    for t in range(1, 12 * H + 1):
        h = lam + (q / M) * N if M > 0 else lam
        cum += h / 12.0
        N = N + rng.binomial(np.maximum(0, M - N), np.clip(1.0 - np.exp(-h / 12.0), 0.0, 1.0))
        if t % 12 == 0:
            F.append(1.0 - np.exp(-cum))
    F = np.array(F)                                          # [H+1, paths]
    dec = np.percentile(F, np.arange(10, 100, 10), axis=1)   # [9, H+1]
    add = N - n
    return (np.round(dec, 4), tuple(int(np.percentile(add, x)) for x in (10, 50, 90)), float(add.mean()))


# =================================================================================================================
# physics: the sweep (SIM)
# =================================================================================================================
class Inputs:
    """Loads per transformer, topology, surrogate coefficients (the same inputs as sim.p2_build)."""

    def __init__(self):
        from .loads import Loads
        from .siting import STEPS
        from .surrogate import coefficients
        from .topology import load_table
        self.loads = Loads()
        self.t = load_table()
        self.topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text(encoding="utf-8"))
        self.P, self.Q = self.loads.tf_pq(0, STEPS)
        self.kva = np.asarray(self.t["kva"], dtype=float)
        self.coeffs, _ = coefficients()
        self.tf_ids = list(self.t["tf_ids"])
        self.home_ids = list(self.t["home_ids"])
        self.home_tf = np.asarray(self.t["home_tf"])
        self.n_tf = len(self.kva)
        self.fleet = [int(x) for x in self.t["fleet"]]
        self.elig_on = [[] for _ in range(self.n_tf)]
        for i, h in enumerate(self.topo["homes"]):
            if h["eligible"]:
                self.elig_on[h["tf"]].append(i)
        self.homes_of = [np.flatnonzero(self.home_tf == i) for i in range(self.n_tf)]
        self.installed = np.bincount(self.home_tf[self.fleet], minlength=self.n_tf)
        # a transformer serves homes when it has at least one eligible home: excludes 123, 144, 366 (3-phase 480 V)
        self.res = [i for i in range(self.n_tf) if self.elig_on[i]]
        self.excluded = [i for i in range(self.n_tf) if not self.elig_on[i]]


def one_core_schedule(inp):
    """One naive Core's month (kW [STEPS]) and its revenue ($)."""
    from .siting import World, simulate
    w = World([0], [0], [0], ["core"], [True])
    s = simulate(w, inp.P, inp.Q, inp.kva, inp.coeffs, "naive", "d26")
    return s["kw"][:, 0].astype(float), float(s["revenue"][0])


def tier_of(M):
    """The month's worst tier code per column (sim.tiers codes): 5 protection, 4 above 150%, 3 a normal-tier event,
    2 above 110% (shorter than 30 min), 1 above 100%, 0 within nameplate."""
    return np.select([M["protection"] >= 0, M["emergencyN"] > 0, M["normalEvents"] > 0, M["h110"] > 0,
                      M["peak"] > TIER_AMBER_PCT], [5, 4, 3, 2, 1], 0).astype(np.int64)


def naive_sweep(inp, one, growth=1.0, kva=None, coeffs=None, ks=KS):
    """k x one Core on every transformer at once, k in ks. Returns [n_tf, len(ks)] arrays."""
    from .siting import month_metrics, REPORTED
    from .surrogate import loading
    c = coeffs if coeffs is not None else inp.coeffs
    n = REPORTED
    P, Q = inp.P[:n] * growth, inp.Q[:n] * growth
    pct0 = loading(P, Q, np.zeros((n, inp.n_tf)), c)
    out = {x: np.zeros((inp.n_tf, len(ks)), dtype=np.int64) for x in ("peak", "caused", "tier", "emerg", "prot")}
    for j, k in enumerate(ks):
        bk = np.outer(one[:n] * k, np.ones(inp.n_tf))
        pct = loading(P, Q, bk, c)
        M = month_metrics(pct, pct0, bk, steps=n)
        out["peak"][:, j] = np.round(M["peak"] * 10).astype(np.int64)
        out["caused"][:, j] = M["causedNormal"]
        out["tier"][:, j] = tier_of(M)
        out["emerg"][:, j] = M["emergencyN"]
        out["prot"][:, j] = (M["protection"] >= 0).astype(np.int64)
    return out


_W = {}


def _worker_inputs():
    if "inp" not in _W:
        _W["inp"] = Inputs()
    return _W["inp"]


def _aware_chunk(args):
    """One chunk of (transformer, k) columns, feeder-aware. Runs in a worker process or inline."""
    from .siting import World, simulate, month_metrics, REPORTED
    tfs, ks, growth, kva, coeffs, keep_cap, rev_one = args
    inp = _worker_inputs()
    kva = inp.kva if kva is None else np.asarray(kva)
    coeffs = inp.coeffs if coeffs is None else {k: np.asarray(v) for k, v in coeffs.items()}
    col_tf, col, ids, colkey = [], [], [], []
    for tf in tfs:
        for k in ks:
            c = len(col_tf)
            col_tf.append(tf)
            colkey.append((tf, k))
            for _ in range(k):
                col.append(c)
                ids.append(len(ids))
    w = World(col_tf, col, ids, ["core"] * len(col), [True] * len(col))
    s = simulate(w, inp.P * growth, inp.Q * growth, kva, coeffs, "aware", "d26")
    n = REPORTED
    M = month_metrics(s["pct"], s["pct_none"], s["col_kw"], steps=n)
    colidx = np.asarray(w.col)
    rev = np.bincount(colidx, weights=s["revenue"], minlength=w.W)
    res = {"rev": rev.reshape(len(tfs), len(ks)), "caused": M["causedNormal"].reshape(len(tfs), len(ks)),
           "peak": np.round(M["peak"] * 10).astype(np.int64).reshape(len(tfs), len(ks)),
           "emerg": M["emergencyN"].reshape(len(tfs), len(ks)), "capkw": {}}
    if keep_cap:
        for r, tf in enumerate(tfs):
            cap = aware_cap(ks, res["rev"][r], res["caused"][r], rev_one)[0]
            if cap > 0:
                c = colkey.index((tf, cap))
                res["capkw"][tf] = s["kw"][:n, colidx == c].astype(np.float32)
    del s
    return res


def aware_cap(ks, rev, caused, rev_one, earn=PLAN_AWARE_EARN_MIN):
    """(cap, exact): the largest grid k such that every grid j <= k earns >= earn x j x rev_one with no caused event.
    exact is False when the next grid point is more than one above the cap (the true cap may sit in the gap)."""
    ok = 0
    for j, k in enumerate(ks):
        if k == 0:
            continue
        if rev[j] >= earn * k * rev_one and caused[j] == 0:
            ok = k
        else:
            nxt = k
            return ok, nxt == ok + 1
    return ok, True


def aware_sweep(inp, tfs, ks, growth=1.0, kva=None, coeffs=None, keep_cap=False, rev_one=None, chunk=None,
                workers=None, out=print):
    """Feeder-aware sweep over (tf, k) columns in chunks (memory: a chunk of c transformers holds c x sum(ks) Cores)."""
    workers = int(os.environ.get("PLAN_WORKERS", "1")) if workers is None else workers
    chunk = chunk or max(1, 7000 // max(1, sum(ks)))
    groups = [tfs[i:i + chunk] for i in range(0, len(tfs), chunk)]
    kv = None if kva is None else np.asarray(kva).tolist()
    cf = None if coeffs is None else {k: np.asarray(v).tolist() for k, v in coeffs.items()}
    args = [(g, ks, growth, kv, cf, keep_cap, rev_one) for g in groups]
    t0 = time.perf_counter()
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as ex:
            parts = list(ex.map(_aware_chunk, args))
    else:
        _W["inp"] = inp
        parts = []
        for i, a in enumerate(args):
            parts.append(_aware_chunk(a))
            if i % 10 == 9:
                out(f"  aware chunk {i + 1}/{len(args)}  {time.perf_counter() - t0:.0f} s")
    res = {x: np.concatenate([p[x] for p in parts]) for x in ("rev", "caused", "peak", "emerg")}
    res["capkw"] = {}
    for p in parts:
        res["capkw"].update(p["capkw"])
    res["tfs"] = list(tfs)
    res["ks"] = list(ks)
    return res


def up_params(inp):
    """kVA one standard size up and that size's median surrogate coefficients (DERIVED); 100 kVA scales the 75 kVA
    medians by kVA (no-load terms up, per-kVA impedance terms down; ASSUMPTION). Returns (kva_up [n_tf], coeffs_up)."""
    c = inp.coeffs
    med = {}
    for s in (25, 50, 75):
        sel = [i for i in inp.res if inp.kva[i] == s]
        med[s] = {k: float(np.median(np.asarray(c[k])[sel])) for k in ("p0", "a", "q0", "b")}
    m75 = med[75]
    med[100] = {"p0": m75["p0"] * 100 / 75, "q0": m75["q0"] * 100 / 75, "a": m75["a"] * 75 / 100, "b": m75["b"] * 75 / 100}
    kva_up = inp.kva.copy()
    cu = {k: np.asarray(c[k], dtype=float).copy() for k in ("p0", "a", "q0", "b")}
    for i in inp.res:
        s = PLAN_UP_SIZES.get(str(int(inp.kva[i])))
        if s is None:
            continue
        kva_up[i] = s
        for k in ("p0", "a", "q0", "b"):
            cu[k][i] = med[s][k]
    cu["kva"] = kva_up
    return kva_up, cu


def _src_sha():
    h = hashlib.sha256()
    h.update(SWEEP_VERSION.encode())
    for f in ("siting.py", "surrogate.py", "loads.py", "prices.py", "caps.py"):
        h.update((ROOT / "sim" / f).read_bytes())
    for f in ("data/profiles/surrogate.json",):
        p = ROOT / f
        if p.exists():
            h.update(p.read_bytes())
    h.update(dumps(inputs_sha()).encode())
    return h.hexdigest()[:16]


def cached(tag, fn):
    """Run fn() once per (tag, source + inputs sha); cache in data/cache/planner/ (gitignored)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{tag}-{_src_sha()}.npz"
    if p.exists():
        z = np.load(p, allow_pickle=True)
        return z["res"].item()
    res = fn()
    np.savez_compressed(p, res=np.array(res, dtype=object))
    return res


def growth_levels():
    return {g: (1.0 + GROWTH) if g == 20 else 1.0 + g / 100.0 for g in PLAN_GROWTH_PCTS}


def physics(inp, quick=False, out=print):
    """All sweeps. Returns {one, rev_one, g{g: {naive, aware}}, up{naive, aware}, kva_up}."""
    if quick:
        one, rev_one = one_core_schedule(inp)
    else:
        oc = cached("one-core", lambda: dict(zip(("one", "rev"), one_core_schedule(inp))))
        one, rev_one = oc["one"], oc["rev"]
    tfs = inp.res if not quick else [i for i in (0, 54, 61, 95, 200, 240, 253, 12, 30, 100, 150, 300) if i in inp.res]
    res = {"one": one, "rev_one": rev_one, "tfs": tfs, "g": {}}
    for g, f in growth_levels().items():
        t0 = time.perf_counter()
        nv = naive_sweep(inp, one, f) if quick else cached(f"naive-g{g}", lambda: naive_sweep(inp, one, f))
        full = (g == 0) and not quick
        ks = KS if full else K_GRID
        tag = f"aware-g{g}-{'full' if full else 'grid'}{'-quick' if quick else ''}"
        aw = cached(tag, lambda: aware_sweep(inp, tfs, ks, f, keep_cap=(g == 0), rev_one=rev_one, out=out)) \
            if not quick else aware_sweep(inp, tfs, [0, 1, 2, 3, 4, 5, 6, 8, 10], f, keep_cap=(g == 0), rev_one=rev_one, out=out)
        res["g"][g] = {"naive": nv, "aware": aw}
        out(f"planner: g{g} naive + aware ({'full' if full else 'grid'}) {time.perf_counter() - t0:.1f} s")
    t0 = time.perf_counter()
    kva_up, cu = up_params(inp)
    res["kva_up"] = kva_up
    nu = naive_sweep(inp, one, 1.0, kva_up, cu, ks=list(range(16))) if quick else         cached("naive-up", lambda: naive_sweep(inp, one, 1.0, kva_up, cu, ks=list(range(16))))
    upks = K_GRID[:15] if not quick else [0, 1, 2, 3, 4, 5, 6, 8, 10]
    au = cached("aware-up-grid", lambda: aware_sweep(inp, tfs, upks, 1.0, kva_up, cu, rev_one=rev_one, out=out)) \
        if not quick else aware_sweep(inp, tfs, upks, 1.0, kva_up, cu, rev_one=rev_one, out=out)
    res["up"] = {"naive": nv_caps(nu), "aware": au}
    out(f"planner: one size up {time.perf_counter() - t0:.1f} s")
    return res


def nv_caps(nv):
    """Naive caps: the largest k with no battery-caused normal-tier event at any j <= k; first emergency / protection
    k (the first k at which battery Cores add an emergency interval / operate the fuse rule)."""
    caused = nv["caused"]
    n_tf, nk = caused.shape
    cap = np.full(n_tf, nk - 1)
    fe = np.full(n_tf, -1)
    fp = np.full(n_tf, -1)
    for i in range(n_tf):
        bad = np.flatnonzero(caused[i] > 0)
        if len(bad):
            cap[i] = bad[0] - 1
        be = np.flatnonzero(nv["emerg"][i] > nv["emerg"][i, 0])
        fe[i] = be[0] if len(be) else -1
        bp = np.flatnonzero(nv["prot"][i] > nv["prot"][i, 0])
        fp[i] = bp[0] if len(bp) else -1
    return {"cap": cap, "firstEmergency": fe, "firstProtection": fp, "raw": nv}


def aw_caps(aw, rev_one):
    """Per swept transformer: (cap, exact, k95)."""
    out = {}
    for r, tf in enumerate(aw["tfs"]):
        cap, exact = aware_cap(aw["ks"], aw["rev"][r], aw["caused"][r], rev_one)
        revs = aw["rev"][r]
        mx = float(revs.max())
        k95 = next(k for j, k in enumerate(aw["ks"]) if revs[j] >= PLAN_AWARE_K95 * mx) if mx > 0 else 0
        out[tf] = (int(cap), bool(exact), int(k95))
    return out


def per_k_aware(aw, rev_one):
    """awarePeak (tenths) and awareEff (effective full-value Cores x 100) at k = 0..50, linear between grid points."""
    ks = np.asarray(aw["ks"], dtype=float)
    peak = np.array([np.interp(KS, ks, aw["peak"][r]) for r in range(len(aw["tfs"]))])
    eff = np.array([np.interp(KS, ks, aw["rev"][r] / rev_one * 100.0) for r in range(len(aw["tfs"]))])
    return np.round(peak).astype(np.int64), np.round(eff).astype(np.int64)


# =================================================================================================================
# the OpenDSS referee (SIM; DESIGN §3.1.7)
# =================================================================================================================
def referee_sha(capN, capA, one, capkw):
    """sha256 of what the referee judges: the naive and aware caps, one naive Core's schedule and the aware schedules
    at capAware (float32), plus the input shas."""
    from .siting import REPORTED
    h = hashlib.sha256()
    h.update(dumps(inputs_sha()).encode())
    h.update(dumps({str(k): int(v) for k, v in sorted(capN.items())}).encode())
    h.update(dumps({str(k): int(v) for k, v in sorted(capA.items())}).encode())
    h.update(np.ascontiguousarray(np.asarray(one[:REPORTED], dtype=np.float64)).tobytes())
    for tf in sorted(capkw):
        h.update(str(tf).encode())
        h.update(np.ascontiguousarray(capkw[tf]).tobytes())
    return h.hexdigest()


def _batches(tfs, k_of, cap):
    out, cur, tot = [], [], 0
    for tf in tfs:
        k = k_of[tf]
        if k <= 0:
            continue
        if cur and tot + k > cap:
            out.append(cur)
            cur, tot = [], 0
        cur.append(tf)
        tot += k
    if cur:
        out.append(cur)
    return out


class _RefCtx:
    pass


def run_referee(inp, capN, capA, one, capkw, out=print):
    """OpenDSS month solves (every 15-min step of August) in batches: naive at capNaive, at capNaive + 1, aware at
    capAware. Battery kW goes round-robin over each transformer's homes (Core j -> home j mod n). Returns the doc."""
    from .feeder import Feeder
    from .referee import solve_month, caused
    from .siting import REPORTED
    n = REPORTED
    ctx = _RefCtx()
    ctx.n_tf, ctx.loads, ctx.home_ids = inp.n_tf, inp.loads, inp.home_ids
    feeder = Feeder()
    res = {"naiveAtCap": {}, "naiveAtCapPlus1": {}, "awareAtCap": {}}
    secs = []
    tfs = sorted(capN)

    def run(label, sel, kw_of_tf):
        kw_home = np.zeros((n, len(inp.home_ids)))
        col_kw = np.zeros((n, inp.n_tf))
        for tf in sel:
            per = kw_of_tf(tf)
            hs = inp.homes_of[tf]
            for j in range(per.shape[1]):
                kw_home[:, hs[j % len(hs)]] += per[:, j]
            col_kw[:, tf] = per.sum(axis=1)
        t0 = time.perf_counter()
        sol = solve_month(feeder, ctx, 0, kw_home, n)
        secs.append(round(time.perf_counter() - t0, 1))
        ev, _ = caused(sol["pct"], col_kw, sol["net"])
        ev_tf = {c for c, _, _ in ev}
        active = (col_kw > 0.5) | ((col_kw < -0.5) & (sol["net"] < 0))
        for tf in sel:
            vm = sol["vmonth"][inp.homes_of[tf]]
            vm = vm[np.isfinite(vm)]
            res[label][tf] = {"caused": tf in ev_tf, "maxPct": round(float(sol["pct"][:, tf].max()), 1),
                              "causedEmergencyN": int(((sol["pct"][:, tf] > TIER_EMERGENCY_PCT) & active[:, tf]).sum()),
                              "vminPu": round(float(vm.min()), 4) if len(vm) else None}
        out(f"  referee {label} batch of {len(sel)} tfs: {secs[-1]} s")

    for sel in _batches(tfs, {t: capN[t] for t in tfs}, PLAN_REF_BATCH_NAIVE):
        run("naiveAtCap", sel, lambda tf: np.outer(one[:n], np.ones(capN[tf])))
    for sel in _batches(tfs, {t: capN[t] + 1 for t in tfs}, PLAN_REF_BATCH_NAIVE):
        run("naiveAtCapPlus1", sel, lambda tf: np.outer(one[:n], np.ones(capN[tf] + 1)))
    for sel in _batches(tfs, {t: capA[t] for t in tfs}, PLAN_REF_BATCH_AWARE):
        run("awareAtCap", sel, lambda tf: capkw[tf].astype(float))
    return {"producer": "sim.planner referee", "label": "SIM (OpenDSS)", "sha256": referee_sha(capN, capA, one, capkw),
            "runs": len(secs), "secondsPerRun": secs, "steps": n,
            "results": {k: {str(t): x for t, x in v.items()} for k, v in res.items()}}


def load_referee(sha, path=REFEREE_JSON):
    """The referee doc when its sha256 equals the build's, else None (a stale file is never merged)."""
    if not Path(path).exists():
        return None
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc if doc.get("sha256") == sha else None


def verdicts(ref, tf, capN, capA):
    """(naive verdict, aware verdict) for one transformer: 'agree' | 'lower' | 'higher' | 'not run'."""
    if ref is None:
        return "not run", "not run"
    r = ref["results"]
    s = str(tf)
    at = r["naiveAtCap"].get(s)
    plus = r["naiveAtCapPlus1"].get(s)
    if (capN > 0 and at is None) or (plus is None and capN < K_MAX):
        nv = "not run"
    elif capN > 0 and at["caused"]:
        nv = "lower"
    elif capN >= K_MAX or plus["caused"]:
        nv = "agree"
    else:
        nv = "higher"
    a = r["awareAtCap"].get(s)
    if capA == 0:
        av = "agree"
    elif a is None:
        av = "not run"
    else:
        av = "lower" if (a["caused"] or a["causedEmergencyN"] > 0) else "agree"
    return nv, av


# =================================================================================================================
# the document
# =================================================================================================================
def L(v, label, cite=None, **extra):
    """A labelled number; extras that are None are left out (the file stays small and the UI tests `in`)."""
    return labelled(v, label, cite, **{k: x for k, x in extra.items() if x is not None})


def money_block():
    r, n = PLAN_DISCOUNT, PLAN_CONTRACT_YEARS
    af = (1 - (1 + r) ** -n) / r
    return {
        "upgradeUSD": L(PLAN_UPGRADE_USD, "REAL", "PLAN_UPGRADE_USD: Base's figure, PUCT 54224 item 49"),
        "upgradePresets": [L(PLAN_UPGRADE_LOW_USD, "REAL", "PLAN_UPGRADE_LOW_USD: NREL cost DB v2, 50 kVA installed (2017 $)"),
                           L(PLAN_UPGRADE_USD, "REAL", "PLAN_UPGRADE_USD: Base's figure, PUCT 54224 item 49"),
                           L(PLAN_UPGRADE_HIGH_USD, "ASSUMPTION", "PLAN_UPGRADE_HIGH_USD")],
        "unitUSD": {k: L(v, "REAL", "PLAN_UNIT_USD: NREL cost DB v2 (2017 $)") for k, v in PLAN_UNIT_USD.items()},
        "leadMonths": L(PLAN_LEAD_MONTHS, "ASSUMPTION", "PLAN_LEAD_MONTHS"),
        "discount": L(PLAN_DISCOUNT, "ASSUMPTION", "PLAN_DISCOUNT"),
        "memberValueUSDYr": L(PLAN_MEMBER_VALUE_USD_YR, "DERIVED", "PLAN_MEMBER_VALUE_USD_YR: gross energy value, not Base's profit"),
        "valuePresets": [L(PLAN_MEMBER_VALUE_USD_YR, "DERIVED", "PLAN_MEMBER_VALUE_USD_YR: energy value from real 2025 prices, not Base's profit"),
                         L(PLAN_MEMBER_VALUE_FEE_USD_YR, "DERIVED", "PLAN_MEMBER_VALUE_FEE_USD_YR: + $19/month membership"),
                         L(PLAN_MEMBER_VALUE_CONTRACT_USD_YR, "DERIVED", "PLAN_MEMBER_VALUE_CONTRACT_USD_YR: Austin Energy-style capacity contract")],
        "contractYears": L(PLAN_CONTRACT_YEARS, "REAL", "PLAN_CONTRACT_YEARS: Base Core Battery Services Agreement"),
        "annuityFactor": L(round(af, 4), "DERIVED", f"(1 - (1 + {r})^-{n}) / {r}"),
        "pLoss": L(PLAN_P_LOSS, "ASSUMPTION", "PLAN_P_LOSS"),
        "sIncrement": L(PLAN_S_INCREMENT, "ASSUMPTION", "PLAN_S_INCREMENT (UNVERIFIED that any utility does this)"),
        "horizonYears": L(PLAN_HORIZON_YEARS, "ASSUMPTION", "PLAN_HORIZON_YEARS"),
        "coresPerMember": L(PLAN_CORES_PER_MEMBER, "ASSUMPTION", "PLAN_CORES_PER_MEMBER"),
        "oncorFailRate": L(PLAN_ONCOR_FAIL_RATE, "REAL", "PLAN_ONCOR_FAIL_RATE: PUCT 56545 item 58"),
    }


def _pct_label(x):
    return L(round(float(x), 4), "DERIVED")


def build(quick=False, out=print, ref_override=None, run_ref=False):
    """Build the planner document. Returns (doc, info)."""
    t_all = time.perf_counter()
    inp = Inputs()
    ph = physics(inp, quick=quick, out=out)
    tfs = ph["tfs"]
    rev_one = ph["rev_one"]
    ages = load_ages()
    surv_r = [round(float(x), 6) for x in survival(np.arange(0, PLAN_SURV_MAX_AGE + 1))]

    # ---- caps per growth level ----------------------------------------------------------------------------------
    caps = {}
    perk = {}
    for g in PLAN_GROWTH_PCTS:
        nvc = nv_caps(ph["g"][g]["naive"])
        awc = aw_caps(ph["g"][g]["aware"], rev_one)
        ap, ae = per_k_aware(ph["g"][g]["aware"], rev_one)
        caps[g] = (nvc, awc)
        raw = nvc["raw"]
        rows = tfs
        perk[g] = {"capNaive": [int(nvc["cap"][t]) for t in rows],
                   "capAware": [awc[t][0] for t in rows],
                   "capAwareExact": [1 if awc[t][1] else 0 for t in rows],
                   "naivePeak": [raw["peak"][t].tolist() for t in rows],
                   "naiveCaused": [raw["caused"][t].tolist() for t in rows],
                   "naiveTier": [raw["tier"][t].tolist() for t in rows],
                   "awarePeak": ap.tolist(), "awareEff": ae.tolist(),
                   "awareGrid": None if ph["g"][g]["aware"]["ks"] == KS else ph["g"][g]["aware"]["ks"]}
        if perk[g]["awareGrid"] is not None:
            # lead ruling 26 Sep: grid resolution is acceptable for g20 / g50 when marked. naive* are exact at every k.
            perk[g]["awareInterp"] = ("awarePeak / awareEff were simulated at awareGrid only and are linear between "
                                      "grid points: show a k off the grid as approximate (≈). capAware is the "
                                      "conservative grid cap (capAwareExact = 0 when the true cap may sit in a gap).")
    nv0, aw0 = caps[0]
    capN = {t: int(nv0["cap"][t]) for t in tfs}
    capA = {t: aw0[t][0] for t in tfs}
    capkw = ph["g"][0]["aware"]["capkw"]
    sha = referee_sha(capN, capA, ph["one"], capkw)
    if run_ref:
        t0 = time.perf_counter()
        rdoc = run_referee(inp, capN, capA, ph["one"], capkw, out=out)
        if not quick:
            REFEREE_JSON.write_text(json.dumps(rdoc, indent=1), encoding="utf-8")
        out(f"planner: OpenDSS referee {rdoc['runs']} month solves in {time.perf_counter() - t0:.0f} s")
    ref = ref_override if ref_override is not None else load_referee(sha)
    if ref is not None and ref.get("sha256") != sha:
        ref = None
    upN = ph["up"]["naive"]
    upA = aw_caps(ph["up"]["aware"], rev_one)

    # ---- demand circles -------------------------------------------------------------------------------------------
    circ = circles(inp.topo, inp.fleet, tfs)
    keys = sorted({(M, n) for (M, n, _) in circ.values()})
    curves, adds = {}, {}
    for (M, n) in keys:
        key = f"{M}-{n}"
        cur, ad = {}, {}
        for qn, q in (("q0", 0.0), ("q30", PLAN_Q_REFERRAL)):
            dec, (p10, p50, p90), mean = demand_curves(M, n, q, seed=[PLAN_SEED, M, n, int(q * 100)])
            cur[qn] = dec.tolist()
            ad[qn] = L(p50, "DERIVED", "additions in 5 years (meta.cites.demand)",
                       p10=p10, p90=p90, mean=round(mean, 2))
        curves[key] = cur
        adds[key] = ad

    # ---- rows -----------------------------------------------------------------------------------------------------
    screen = PLAN_SCREEN
    share = next(s["share"] for s in SCREENS if s["id"] == screen)
    rows = []
    cite_n = f"August sweep: no battery-caused >{TIER_NORMAL_PCT:g}% {TIER_NORMAL_MIN}+ min (meta.cites.naive)"
    cite_a = f"August sweep: each Core earns >= {PLAN_AWARE_EARN_MIN:.0%} (meta.cites.aware)"
    ref_cite = "OpenDSS (sim.planner referee, every 15-min step of August)"
    for t in tfs:
        tr = inp.topo["transformers"][t]
        kva = float(inp.kva[t])
        homes = len(inp.elig_on[t])
        cn, ca = capN[t], capA[t]
        vn, va = verdicts(ref, t, cn, ca)
        shown_n = cn - 1 if vn == "lower" else cn
        shown_a = ca - 1 if va == "lower" else ca
        ag = ages.get(t)
        age = ag["age"]
        kup = float(ph["kva_up"][t])
        inc = None
        if str(int(kva)) in PLAN_UNIT_USD and str(int(kup)) in PLAN_UNIT_USD:
            inc = PLAN_UNIT_USD[str(int(kup))] - PLAN_UNIT_USD[str(int(kva))]
        M, n, _ = circ[t]
        row = {
            "tf": t, "id": inp.tf_ids[t],
            "kva": L(kva, "REAL", "SMART-DS nameplate"),
            "mount": tr.get("mount"),
            "phases": L(1, "REAL", "SMART-DS"),
            "homes": homes,
            "installed": L(int(inp.installed[t]), "ASSUMPTION", "prototype 96-Core placement"),
            "pending": L(0, "ASSUMPTION", "no pipeline in the sim"),
            "age": L(age, "DERIVED", "simulated (meta.cites.age)",
                     source="simulated", p10=ag["p10"], p50=ag["p50"], p90=ag["p90"],
                     pRep5=round(p_replace(5, age), 4)),
            "cap": {
                "naive": L(cn, "SIM", cite_n, opendss=vn, shown=shown_n,
                           firstEmergency=int(nv0["firstEmergency"][t]) if nv0["firstEmergency"][t] >= 0 else None,
                           firstProtection=int(nv0["firstProtection"][t]) if nv0["firstProtection"][t] >= 0 else None,
                           note=(f"OpenDSS found an overload at {cn}" if vn == "lower" else None),
                           screening=vn == "not run"),
                "aware": L(ca, "SIM", cite_a, opendss=va, shown=shown_a, k95=aw0[t][2],
                           note=(f"OpenDSS found an overload at {ca}" if va == "lower" else None),
                           screening=va == "not run"),
                "paper": L(paper_screen(kva, share), "DERIVED", f"utility rule {screen} (screens.profiles)",
                           profile=screen, ae90=paper_screen(kva, 0.9)),
            },
            "up": {
                "kva": L(kup, "ASSUMPTION", "PLAN_UP_SIZES"),
                "naive": L(int(upN["cap"][t]), "SIM", "screening: next size (meta.cites.up)", screening=True),
                "aware": L(upA[t][0], "SIM", "screening: next size (meta.cites.up)", screening=True),
                "paper": L(paper_screen(kup, share), "DERIVED", "utility rule at the next size"),
                "incrementUSD": L(inc, "DERIVED" if inc is not None else "ASSUMPTION",
                                  "PLAN_UNIT_USD step (NREL 2017 $)" if inc is not None
                                  else "no NREL unit cost for 10 kVA: the increment is not sourced"),
            },
            "nb": {"key": f"{M}-{n}", "homes": M, "installed": L(n, "ASSUMPTION", "prototype Cores in the circle")},
        }
        rows.append(row)

    # ---- size summary (Learnings Q2 headline) ---------------------------------------------------------------------
    size_summary = {}
    for s in sorted({int(inp.kva[t]) for t in tfs}):
        sel = [r for r in rows if int(r["kva"]["v"]) == s]
        med = lambda xs: float(np.median(xs))
        size_summary[str(s)] = {
            "count": L(len(sel), "REAL", "SMART-DS transformers of this size serving homes"),
            "homesP50": L(med([r["homes"] for r in sel]), "DERIVED", "median eligible homes per transformer"),
            "paper": L(med([r["cap"]["paper"]["v"] for r in sel]), "DERIVED", "median utility nameplate rule"),
            "naive": L(med([r["cap"]["naive"]["shown"] for r in sel]), "SIM",
                       "median naive cap (OpenDSS wins where checked)", p90=float(np.percentile([r["cap"]["naive"]["shown"] for r in sel], 90))),
            "aware": L(med([r["cap"]["aware"]["shown"] for r in sel]), "SIM",
                       "median feeder-aware cap (OpenDSS wins where checked)"),
            "naiveG20": L(med([perk[20]["capNaive"][tfs.index(r["tf"])] for r in sel]), "SIM", "median naive cap, +20% home load"),
            "awareG20": L(med([perk[20]["capAware"][tfs.index(r["tf"])] for r in sel]), "SIM", "median feeder-aware cap, +20% home load"),
            "naiveG50": L(med([perk[50]["capNaive"][tfs.index(r["tf"])] for r in sel]), "SIM", "median naive cap, +50% home load"),
            "awareG50": L(med([perk[50]["capAware"][tfs.index(r["tf"])] for r in sel]), "SIM", "median feeder-aware cap, +50% home load"),
        }

    # ---- the upgrade priority list (layer 3) ------------------------------------------------------------------------
    ranking = upgrade_ranking(rows, curves)

    # ---- referee block ------------------------------------------------------------------------------------------------
    if ref is not None:
        res_n = [r for r in rows]
        agree_n = sum(r["cap"]["naive"]["opendss"] == "agree" for r in res_n)
        lower_n = [r["tf"] for r in res_n if r["cap"]["naive"]["opendss"] == "lower"]
        higher_n = [r["tf"] for r in res_n if r["cap"]["naive"]["opendss"] == "higher"]
        plus = ref["results"]["naiveAtCapPlus1"]
        agree_p = sum(1 for r in res_n if plus.get(str(r["tf"]), {}).get("caused"))
        agree_a = sum(r["cap"]["aware"]["opendss"] == "agree" for r in res_n)
        vmins = [x["vminPu"] for part in ref["results"].values() for x in part.values() if x.get("vminPu")]
        referee = {"status": "checked", "runs": ref["runs"],
                   "secondsPerRun": L(round(float(np.mean(ref["secondsPerRun"])), 1), "SIM", "measured on the build machine"),
                   "naiveAtCap": {"agree": L(agree_n, "SIM", ref_cite), "of": len(res_n), "lower": lower_n, "higher": higher_n},
                   "naiveAtCapPlus1": {"agree": L(agree_p, "SIM", ref_cite), "of": len(res_n)},
                   "awareAtCap": {"agree": L(agree_a, "SIM", ref_cite), "of": len(res_n)},
                   "vminPu": L(round(min(vmins), 4), "SIM", "lowest home voltage on any checked transformer, any check")
                   if vmins else None,
                   "rule": "OpenDSS wins: where it is stricter, cap.*.shown = cap - 1 with its note",
                   "sha256": sha}
    else:
        referee = {"status": "not run", "runs": 0, "sha256": sha,
                   "reason": "no data/planner/referee.json with this build's sha256; every cap is screening "
                             "(run python -m sim.planner --referee)",
                   "rule": "OpenDSS wins: where it is stricter, cap.*.shown = cap - 1 with its note"}

    series = {
        "naivePeak": {"label": "SIM", "text": "August peak loading at k naive Cores, % of nameplate x 10 [tfs][51]"},
        "naiveCaused": {"label": "SIM", "text": "battery-caused normal-tier events in August at k naive Cores [tfs][51]"},
        "naiveTier": {"label": "SIM", "text": "the month's worst tier code (sim.tiers 0-5) at k naive Cores [tfs][51]"},
        "awarePeak": {"label": "SIM", "text": "August peak loading at k feeder-aware Cores, % x 10; linear between "
                                               "awareGrid points when awareGrid is set [tfs][51]"},
        "awareEff": {"label": "SIM", "text": "feeder-aware revenue at k Cores / one naive Core's revenue x 100 "
                                              "(effective full-value Cores x 100) [tfs][51]"},
        "capNaive": {"label": "SIM", "text": "naive cap per transformer at this growth level (surrogate screen)"},
        "capAware": {"label": "SIM", "text": "feeder-aware cap per transformer at this growth level (surrogate screen)"},
        "capAwareExact": {"label": "SIM", "text": "1 when capAware is exact on the simulated k grid"},
        "perK": {"label": "SIM", "text": "perK.g0 / g20 / g50: per-transformer arrays at +0 / +20 / +50% home load "
                                         "(surrogate screen; only g0 caps are OpenDSS-refereed)"},
        "survival": {"label": "DERIVED", "text": "DOE retirement function r(age), age 0..60 (DESIGN §3.2)"},
        "demandCurves": {"label": "DERIVED", "text": "per-home cumulative join probability, pointwise deciles p10..p90 "
                                                     "at months 0, 12, ..., 60 per neighbourhood key"},
        "baseline": {"label": "SIM", "text": "home load only, August: peak % and hours above 100% per transformer [379]"},
        "tfsOrder": {"label": "REAL", "text": "perK row r is transformer meta.tfOrder[r] (topology index)"},
    }
    sources = {
        "price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min, August 2026 (data/ercot)"},
        "loads": {"label": "SIM", "text": "NREL SMART-DS 2018 AUS P1U August profiles, paired by calendar date"},
        "feeder": {"label": "REAL", "text": f"{STAND_IN}: SMART-DS p1uhs19_1247--p1udt17263 topology and kVA"},
        "fleet": {"label": "ASSUMPTION", "text": "the prototype's 96-Core placement (data/fleet.json) as 'installed'"},
        "ages": {"label": "DERIVED", "text": "data/planner/tf_simulated_ages.csv (ACS 2024 B25034 x DOE retirement "
                                             "function, census tract per transformer from the Census geocoder)"},
        "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4, every 15-min step of August (data/planner/referee.json)"},
        "design": {"label": "ASSUMPTION", "text": f"{DESIGN} §2.3 contract; DATA-SCOPE-RZ-CAPACITY-PLANNER.md (binding)"},
    }
    names = sorted(k for k in TAG if k.startswith("PLAN_"))
    consts = export(*names, "CORE_POWER_KW", "TIER_NORMAL_PCT", "TIER_NORMAL_MIN", "TIER_EMERGENCY_PCT", "AWARE_MARGIN",
                    "GROWTH", "CURTAIL_CAP", "STAND_IN")
    doc = envelope("planner", "sim.planner", constants=consts, sources=sources, series=series)
    base_nv = ph["g"][0]["naive"]
    from .siting import month_metrics, REPORTED
    from .surrogate import loading
    pct0 = loading(inp.P[:REPORTED], inp.Q[:REPORTED], np.zeros((REPORTED, inp.n_tf)), inp.coeffs)
    M0 = month_metrics(pct0, steps=REPORTED)
    doc.update({
        "meta": {"month": "2026-08", "rule": "d26", "cls": "core", "fromEmptyFeeder": True, "kMax": K_MAX,
                 "radiusM": L(PLAN_RADIUS_M, "ASSUMPTION", "PLAN_RADIUS_M"), "sizes": SIZES, "scope": SCOPE,
                 "excluded": inp.excluded, "demoTf": PLAN_DEMO_TF, "defaultTf": PLAN_DEFAULT_TF,
                 "tfOrder": tfs, "growth": list(PLAN_GROWTH_PCTS), "screen": screen,
                 "oneCoreRevenueUSD": L(round(rev_one, 2), "SIM", "one naive Core's August revenue (the 100% of awareEff)"),
                 "naiveWords": "Naive: our assumption of one number, no feeder check",
                 "awareWords": "Feeder-aware: the most Cores that still earn at least 90% each; it never overloads the "
                               "transformer, it charges less instead (a money limit, not a safety one)",
                 "cites": {"naive": f"{SWEEP_CITE}: k x one naive Core; the largest k with no battery-caused "
                                    f"normal-tier event (> {TIER_NORMAL_PCT:g}% for >= {TIER_NORMAL_MIN} min while the "
                                    "batteries raise the loading) at any j <= k",
                           "aware": f"{SWEEP_CITE}: aware per (transformer, k); the largest k whose Cores each earn >= "
                                    f"{PLAN_AWARE_EARN_MIN:.0%} of one unconstrained Core with no battery-caused event",
                           "up": "the same rules with the next standard size's kVA and that size's median surrogate "
                                 "coefficients (100 kVA: the 75 kVA medians scaled by kVA, ASSUMPTION); screening, "
                                 "not OpenDSS-checked",
                           "demand": "Gamma-Poisson neighbourhood model with a referral term (DESIGN §3.3; "
                                     "DATA-ASSETS-DEMAND.md §3.2): lambda ~ Gamma(k + n, k / lambda_bar + M T0), monthly "
                                     "hazard lambda + q N / M, 4,000 paths, seed [20260926, M, n, 100 q]; eligible homes "
                                     "within PLAN_RADIUS_M of the transformer",
                           "age": "a utility value replaces it (label REAL). ACS 2024 B25034 year built per census tract x DOE retirement function (renewal "
                                  "Monte Carlo, 4,000 draws, seed 20260926); one seeded draw, p10/p50/p90 of the draws "
                                  "(data/planner/tf_simulated_ages.csv)"},
                 "quick": bool(quick)},
        "tfs": rows,
        "perK": {f"g{g}": perk[g] for g in PLAN_GROWTH_PCTS},
        "survival": {"years": list(range(PLAN_SURV_MAX_AGE + 1)), "r": surv_r,
                     "meanLife": L(round(mean_life(), 2), "DERIVED", "sum of r(a), a = 0..79 (DOE: 32 years)")},
        "demand": {"deciles": list(range(10, 100, 10)), "months": [12 * i for i in range(PLAN_HORIZON_YEARS + 1)],
                   "curves": curves, "adds": adds},
        "money": money_block(),
        "screens": {"profiles": [dict(s, share=L(s["share"], "REAL", s["cite"])) for s in SCREENS], "default": screen},
        "decision": {"label": "DERIVED", "cite": f"{DESIGN} §3.4; ui/lib/planner.js",
                     "paths": L(PLAN_DECISION_PATHS, "ASSUMPTION", "PLAN_DECISION_PATHS"), "seed": PLAN_SEED,
                     "defaults": {"setting": "aware-screen", "cost": 1, "value": 0, "referral": False, "growth": 0}},
        "referee": referee,
        "sizeSummary": size_summary,
        "ranking": ranking,
        "baseline": {"peak": [round(float(x), 1) for x in M0["peak"]], "h100": [round(float(x), 2) for x in M0["h100"]]},
    })
    info = {"seconds": round(time.perf_counter() - t_all, 1), "referee": referee["status"], "sha": sha,
            "rev_one": rev_one}
    return doc, info


def upgrade_ranking(rows, curves):
    """Layer 3 (RZ's scope): the transformers worth paying to upgrade, ranked by the members an upgrade unlocks in 5
    years at the typical (p50) neighbourhood growth, referral off, under 'feeder-aware, utility rule unchanged'
    (the binding cap is min(aware, rule); 'blocked' means the utility rule, CRITIQUE-CAP-base must-fix 1).
    Deterministic arithmetic (DERIVED): wanted(5 y) = installed + pending + non-member homes x F_q(60 months);
    unlocked = min(wanted, c_up) - min(wanted, c); value/yr = unlocked x PLAN_MEMBER_VALUE_USD_YR;
    payback = PLAN_UPGRADE_USD / value. Rows: every transformer at or over its binding cap today, or whose p90 wanted
    exceeds it; 'onboard' rows (every home already a member) say an upgrade unlocks nothing."""
    v = PLAN_MEMBER_VALUE_USD_YR
    C = PLAN_UPGRADE_USD
    out = []
    for r in rows:
        homes = r["homes"]
        k0 = r["installed"]["v"] + r["pending"]["v"]
        paper = r["cap"]["paper"]["v"]
        c = min(r["cap"]["aware"]["shown"], paper)
        c_up = min(r["up"]["aware"]["v"], r["up"]["paper"]["v"])
        m = max(0, homes - min(k0, homes))
        F = curves[r["nb"]["key"]]["q0"]
        want = {q: k0 + PLAN_CORES_PER_MEMBER * m * F[i][-1] for q, i in (("p10", 0), ("p50", 4), ("p90", 8))}
        if not (k0 >= c or want["p90"] >= c + 0.5):
            continue
        unl = {q: max(0.0, min(w, c_up) - min(w, c)) for q, w in want.items()}
        val = unl["p50"] * v
        why = ("blocked" if k0 > c else "onboard" if m == 0 else "unlocks" if unl["p50"] >= 0.5 else "little")
        out.append({"tf": r["tf"],
                    "why": why,
                    "blockedToday": L(max(0, k0 - c), "DERIVED", "installed + pending over min(feeder-aware cap, utility rule)"),
                    "wanted5y": L(round(want["p50"], 2), "DERIVED", "installed + pending + non-member homes x F_p50(5 y)",
                                  p10=round(want["p10"], 2), p90=round(want["p90"], 2)),
                    "unlocked": L(round(unl["p50"], 2), "DERIVED", "min(wanted, cap one size up) - min(wanted, cap)",
                                  p10=round(unl["p10"], 2), p90=round(unl["p90"], 2)),
                    "valueUSDYr": L(round(val), "DERIVED", f"unlocked x ${v}/yr (gross energy value, not Base's profit)"),
                    "costUSD": L(C, "REAL", "PLAN_UPGRADE_USD: Base's figure, PUCT 54224 item 49"),
                    "paybackYears": L(round(C / val, 1) if val > 0 else None, "DERIVED", "cost / value per year"),
                    "controlsFit": L(r["cap"]["aware"]["shown"], "SIM", "feeder-aware cap if the utility counted our "
                                                                         "control (UNVERIFIED in Texas)"),
                    "age": L(r["age"]["v"], "DERIVED", "simulated", pRep5=r["age"]["pRep5"])})
    out.sort(key=lambda x: (-x["unlocked"]["v"], -(x["age"]["pRep5"]), x["tf"]))
    for i, x in enumerate(out):
        x["rank"] = i + 1
    return out


# =================================================================================================================
# the asset file (DESIGN §2.1) and the shape check
# =================================================================================================================
ASSET_COLS = ["tf_id", "tf_index", "utility", "kva", "phases", "mount", "install_year", "last_replaced_year",
              "homes_served", "batteries_installed", "batteries_pending", "existing_dg_kw", "utility_headroom_kw",
              "export_limit_kw", "import_limit_kw", "source", "source_date", "notes"]


def assets_sim_csv(doc):
    lines = [",".join(ASSET_COLS)]
    for r in doc["tfs"]:
        notes = "P1's unrelieved transformer" if r["tf"] == PLAN_DEFAULT_TF else ""
        lines.append(",".join(str(x) for x in [
            r["id"], r["tf"], "Oncor stand-in", int(r["kva"]["v"]), 1, r["mount"] or "",
            PLAN_NOW_YEAR - r["age"]["v"], "", r["homes"], r["installed"]["v"], r["pending"]["v"], 0, "", "", "",
            f"SIM: SMART-DS + simulated age (seed {PLAN_SEED})", "2026-09-26", notes]))
    return "\n".join(lines) + "\n"


def apply_local_assets(doc, path=ASSETS_LOCAL):
    """Override SIM cells with a hand-filled portal read (same columns; a non-empty cell wins, labelled REAL).
    Only age, installed, pending and the utility headroom are applied; kVA physics is never re-simulated here."""
    rows = list(csv.DictReader(Path(path).read_text(encoding="utf-8").splitlines()))
    by = {r["tf"]: r for r in doc["tfs"]}
    for a in rows:
        r = by.get(int(a["tf_index"])) if a.get("tf_index") else None
        if r is None:
            continue
        src = f"{a.get('source') or 'utility portal read'}, {a.get('source_date') or ''}".strip(", ")
        yr = a.get("last_replaced_year") or a.get("install_year")
        if yr:
            age = PLAN_NOW_YEAR - int(yr)
            r["age"] = L(age, "REAL", src, source="utility", pRep5=round(p_replace(5, age), 4))
        for col, key in (("batteries_installed", "installed"), ("batteries_pending", "pending")):
            if a.get(col):
                r[key] = L(int(a[col]), "REAL", src)
        if a.get("utility_headroom_kw"):
            n = r["installed"]["v"] + int(math.floor(float(a["utility_headroom_kw"]) / CORE_POWER_KW))
            r["cap"]["utility"] = L(n, "REAL", f"installed + floor(headroom / {CORE_POWER_KW:g} kW); {src}")
    doc["meta"]["local"] = True
    return doc


def check_shape(doc):
    """Shape checks for p2/planner.json (DESIGN §2.3), for sim.contracts to call. Returns a list of errors."""
    errs = []

    def need(c, m):
        if not c:
            errs.append(m)
    try:
        need(doc["schema"] == "hb.planner.v1", "planner: schema")
        tfs = [r["tf"] for r in doc["tfs"]]
        need(not {123, 144, 366} & set(tfs), "planner: tfs must exclude 123, 144, 366")
        need(all(r["homes"] >= 1 for r in doc["tfs"]), "planner: every row serves >= 1 home")
        need(isinstance(doc["ranking"], list), "planner: ranking missing")
        need(doc["meta"]["tfOrder"] == tfs, "planner: meta.tfOrder != tfs order")
        n = len(tfs)
        need(sorted(doc["perK"]) == sorted(f"g{g}" for g in PLAN_GROWTH_PCTS), "planner: perK must hold g0, g20, g50")
        for g, blk in doc["perK"].items():
            for k in ("naivePeak", "naiveCaused", "naiveTier", "awarePeak", "awareEff"):
                need(k in blk, f"planner: perK.{g}.{k} missing")
            for k in ("capNaive", "capAware"):
                need(len(blk[k]) == n, f"planner: perK.{g}.{k} length != {n}")
            for k in ("naivePeak", "naiveCaused", "naiveTier", "awarePeak", "awareEff"):
                if k in blk:
                    need(len(blk[k]) == n and all(len(x) == K_MAX + 1 for x in blk[k]), f"planner: perK.{g}.{k} not [{n}][51]")
        r = doc["survival"]["r"]
        need(all(a >= b for a, b in zip(r, r[1:])), "planner: survival not non-increasing")
        for key, cur in doc["demand"]["curves"].items():
            for q, dec in cur.items():
                ok_t = all(all(a <= b + 1e-12 for a, b in zip(row, row[1:])) for row in dec)
                ok_d = all(all(dec[i][t] <= dec[i + 1][t] + 1e-12 for t in range(len(dec[0]))) for i in range(len(dec) - 1))
                need(ok_t and ok_d, f"planner: demand.curves.{key}.{q} not monotone")
        need(doc["referee"]["status"] in ("checked", "not run"), "planner: referee.status")
    except (KeyError, TypeError, IndexError) as e:
        errs.append(f"planner: missing or malformed field {e}")
    return errs


def fit_budget(doc, out=print):
    """The file must stay <= SIZE_CAP_BYTES (2.0 MB, lead ruling). perK.g20 / g50 are never dropped any more (Learnings
    Q3 needs them); an oversize file is reported and the CLI exits 1. (The 18:49 build exited 1 because the old 1.2 MB cap
    was still exceeded after dropping both growth levels' per-k detail: 1,291,630 > 1,258,291 bytes.)"""
    size = len(dumps(doc).encode("utf-8"))
    if size > SIZE_CAP_BYTES:
        out(f"planner: {size / 1048576:.2f} MB is over the {SIZE_CAP_BYTES / 1048576:.1f} MB cap")
    return doc


def write_outputs(doc, local=ASSETS_LOCAL, out=OUT, private=PRIVATE_OUT, assets_sim=ASSETS_SIM, say=print):
    """The privacy rule (DESIGN §2.1, Must). With a hand-filled local asset file, apply it and write ONLY the private
    file (plus a `*` .gitignore beside it, so it can never be committed); the public planner.json and assets.sim.csv
    stay untouched. Without one, write the public file and the SIM asset CSV. Returns (target path, bytes written)."""
    if Path(local).exists():
        doc = apply_local_assets(doc, local)
        target = Path(private)
        target.parent.mkdir(parents=True, exist_ok=True)
        (target.parent / ".gitignore").write_text("*\n", encoding="utf-8")
        say("planner: LOCAL UTILITY DATA found: writing ui/data/private/planner.json (do not publish)")
    else:
        Path(assets_sim).write_bytes(assets_sim_csv(doc).encode("utf-8"))
        target = Path(out)
    return target, write_json(target, doc)


def main(argv):
    if argv and argv[0] == "ages":
        print(f"planner: wrote {write_ages_csv()}")
        return 0
    quick = "--quick" in argv
    if argv and argv[0] == "referee":
        doc, info = build(quick=quick, run_ref=True)
    else:
        doc, info = build(quick=quick, run_ref="--referee" in argv)
    errs = check_shape(doc)
    for e in errs:
        print("  -", e)
    if quick:
        print(f"planner --quick: {len(doc['tfs'])} transformers, {info['seconds']} s, referee {info['referee']}, "
              f"{'shape ok' if not errs else 'SHAPE FAIL'}")
        return 1 if errs else 0
    doc = fit_budget(doc)
    target, size = write_outputs(doc)
    print(f"planner: wrote {target.relative_to(ROOT)} {size / 1024:.0f} KB ({len(doc['tfs'])} transformers, "
          f"referee {info['referee']}, {info['seconds']} s){'' if not errs else ' SHAPE FAIL'}")
    return 1 if errs or size > SIZE_CAP_BYTES else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
