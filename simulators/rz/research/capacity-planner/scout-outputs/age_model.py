"""Transformer age prior and replacement probability for the 379 SMART-DS transformers (DERIVED from REAL inputs).

Inputs (all REAL, cited in DATA-ASSETS-DEMAND.md):
  - DOE retirement function (2012 NOPR TSD ch. 9.3.7 and 8.3.10): r(age) = exp(-(age/d)^e) x (1-0.005)^age x
    (1-0.005)^max(0, age-15); average life 32 years, maximum 60 (2024 final rule, 89 FR 29834). d and e are not printed
    in the TSD text, so e is taken from the Weibull shapes in Yao & Dvorkin (arXiv 2604.18411, Table 3: 4.6141
    optimistic, 7.3410 pessimistic) and d is solved so the mean life is 32 years (DERIVED).
  - ACS 2024 5-year B25034 (year structure built) for the 5 census tracts under the feeder (www2.census.gov summary
    file), and each transformer's tract from the Census geocoder (tf_census_tract.json).
ASSUMPTION: a transformer was first installed the year its tract's housing was built (NREL's own method uses building
stock age as the proxy for first deployment, NREL/FS-6A40-92076), and each retirement (failure, upgrade, storm,
road work) is replaced by a new unit that restarts the clock (renewal process).

    python3 age_model.py      (needs numpy; writes age_model_out.json and tf_simulated_ages.csv)
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NOW = 2026
AMAX = 60
CONST, CORR, CORR_FROM = 0.005, 0.005, 15
# name -> (shape e, fixed scale d or None to fit the DOE 32-year mean, DOE constant+corrosion terms on/off)
SHAPES = {"doe32_e4.61": (4.6141, None, True), "doe32_e7.34": (7.3410, None, True),
          "yao_dvorkin_optimistic": (4.6141, 49.5663, False), "yao_dvorkin_pessimistic": (7.3410, 40.9500, False)}
PURE = {"on": False}


def r(age, d, e):
    age = np.asarray(age, dtype=float)
    if PURE["on"]:
        out = np.exp(-(age / d) ** e)
        return np.where(age >= 80, 0.0, out)
    out = np.exp(-(age / d) ** e) * (1 - CONST) ** age * (1 - CORR) ** np.maximum(0.0, age - CORR_FROM)
    return np.where(age >= AMAX, 0.0, out)


def mean_life(d, e):
    a = np.arange(0, 81)
    return float(r(a, d, e)[:-1].sum())          # E[L] = sum_a S(a) (annual steps; DOE: all gone by 60)


def fit_d(e, target=32.0):
    lo, hi = 5.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mean_life(mid, e) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def p_replace_within(age, n, d, e):
    s0 = r(age, d, e)
    return float(1 - r(age + n, d, e) / s0) if s0 > 0 else 1.0


def acs_bins():
    rows = [l.strip().split("|") for l in open(HERE / "acs2024_b25034_feeder_tracts.csv")]
    h = rows[0]
    bins = {2: (2020, 2024), 3: (2010, 2019), 4: (2000, 2009), 5: (1990, 1999), 6: (1980, 1989), 7: (1970, 1979),
            8: (1960, 1969), 9: (1950, 1959), 10: (1940, 1949), 11: (1920, 1939)}
    out = {}
    for row in rows[1:]:
        d = dict(zip(h, row))
        geoid = d["GEO_ID"].split("US")[1]
        w = np.array([int(d[f"B25034_E{k:03d}"]) for k in bins], dtype=float)
        out[geoid] = (list(bins.values()), w / w.sum())
    return out


def simulate_ages(tracts, d, e, draws=4000, seed=20260926):
    """Monte Carlo renewal: install year ~ tract's year-built mix (uniform inside the decade bin), lifetimes ~ DOE
    retirement function; returns ages [n_tf, draws] in 2026 and the number of replacements so far."""
    rng = np.random.default_rng(seed)
    a = np.arange(0, 81)
    S = r(a, d, e)
    pmf = np.maximum(0.0, S[:-1] - S[1:])       # P(L = a+1) (retire during year a -> a+1)
    pmf = pmf / pmf.sum()
    life_vals = np.arange(1, 81)
    bins = acs_bins()
    ages = np.zeros((len(tracts), draws))
    nrep = np.zeros((len(tracts), draws))
    for i, g in enumerate(tracts):
        rngs, w = bins[g]
        k = rng.choice(len(w), size=draws, p=w)
        lo = np.array([rngs[j][0] for j in k]); hi = np.array([rngs[j][1] for j in k])
        y = rng.integers(lo, hi + 1)
        last = y.astype(float)
        reps = np.zeros(draws)
        alive = np.ones(draws, dtype=bool)
        while alive.any():
            L = rng.choice(life_vals, size=draws, p=pmf)
            end = last + L
            ret = alive & (end <= NOW)
            last = np.where(ret, end, last)
            reps += ret
            alive = ret
        ages[i] = NOW - last
        nrep[i] = reps
    return ages, nrep


def main():
    tract_of = json.loads((HERE / "tf_census_tract.json").read_text())["tractOfTf"]
    n_tf = len(tract_of)
    tracts = [tract_of[str(i)] for i in range(n_tf)]
    out = {"method": __doc__.strip().splitlines()[0], "now": NOW, "shapes": {}}
    for name, (e, d_fixed, doe) in SHAPES.items():
        PURE["on"] = not doe
        d = fit_d(e) if d_fixed is None else d_fixed
        tab = {}
        for age in (0, 5, 10, 15, 20, 25, 30, 35, 40, 50):
            tab[age] = {f"P_{n}y": round(p_replace_within(age, n, d, e), 4) for n in (1, 2, 5, 10)}
        hazard = {age: round(p_replace_within(age, 1, d, e), 4) for age in range(0, 60, 5)}
        ages, nrep = simulate_ages(tracts, d, e)
        flat = ages.ravel()
        bands = {"0-5": ((flat >= 0) & (flat < 5)), "5-10": ((flat >= 5) & (flat < 10)),
                 "10-20": ((flat >= 10) & (flat < 20)), "20-33": ((flat >= 20) & (flat <= 33)), ">33": flat > 33}
        # fleet-average one-year replacement probability under the simulated ages
        p1 = np.mean([p_replace_within(a, 1, d, e) for a in flat[::97]])
        p5 = np.mean([p_replace_within(a, 5, d, e) for a in flat[::97]])
        out["shapes"][name] = {
            "e": e, "d_fitted": round(d, 3), "meanLife": round(mean_life(d, e), 2),
            "P_replace_within_N_given_age": tab, "annualHazardByAge": hazard,
            "feederAgeShare": {k: round(float(v.mean()), 3) for k, v in bands.items()},
            "feederAgeQuantiles": {q: round(float(np.percentile(flat, q)), 1) for q in (10, 25, 50, 75, 90)},
            "shareEverReplaced": round(float((nrep > 0).mean()), 3),
            "fleetP1y": round(float(p1), 4), "fleetP5y": round(float(p5), 4),
        }
        if name == "doe32_e4.61":
            rng = np.random.default_rng(7)
            pick = ages[np.arange(n_tf), rng.integers(0, ages.shape[1], n_tf)]
            with open(HERE / "tf_simulated_ages.csv", "w", newline="") as fh:
                wr = csv.writer(fh)
                wr.writerow(["tf_index", "census_tract", "age_draw_2026", "age_p10", "age_p50", "age_p90",
                             "P_replace_1y_given_draw", "P_replace_5y_given_draw", "label"])
                for i in range(n_tf):
                    a = float(pick[i])
                    wr.writerow([i, tracts[i], int(a), *[int(np.percentile(ages[i], q)) for q in (10, 50, 90)],
                                 round(p_replace_within(a, 1, d, e), 4), round(p_replace_within(a, 5, d, e), 4),
                                 "DERIVED age prior (ACS year built x DOE retirement function), one seeded draw"])
    (HERE / "age_model_out.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
