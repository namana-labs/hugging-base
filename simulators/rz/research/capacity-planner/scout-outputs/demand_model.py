"""How many more Base members will a neighbourhood add? A Poisson-gamma (negative binomial) posterior with an optional
peer/referral term (DERIVED method; every parameter below is labelled).

Neighbourhood: M eligible homes (owner-occupied single-family), n0 current Base members acquired over T0 years.
Each non-member home adopts at hazard lam_i(t) = lam + gamma * N(t) per year, where
  lam   ~ Gamma(shape k, rate k / lam_bar) across neighbourhoods   (heterogeneity -> negative binomial counts)
  gamma = q / M                                                     (Bass imitation / referral, per member)
Closed form (gamma = 0): posterior lam | n0 ~ Gamma(k + n0, k / lam_bar + M * T0); additional members over H years
  N_add ~ NegBin(r = k + n0, success p = b / (b + (M - n0) H)), b = k / lam_bar + M * T0
  mean = (k + n0) (M - n0) H / b ;  var = mean + mean^2 / (k + n0)
(ignores depletion of the M - n0 pool, so it overstates slightly when mean is a large share of M; the Monte Carlo
below includes depletion and the peer term).

Inputs:
  lam_bar = 36,500 installs/yr / 6,091,247 Texas owner-occupied 1-unit detached homes = 0.0060 /home-yr
            (DERIVED: ~100 installs/day, Base blog via research notes; ACS 2024 5-yr B25032, REAL). It is an average
            over all of Texas, including places Base does not serve, so it is a floor for served areas.
  k       = 0.3 (very clustered) .. 1.0 (ASSUMPTION): Base's 17,000 homes are clustered (builder communities,
            referrals); calibrate against Base's own neighbourhood counts.
  q       = 0 .. 0.4 /yr (ASSUMPTION anchored on Graziano & Gillingham 2015: +0.44 installs per block group per
            quarter per recent install within 0.5 mi; dGen residential median q = 0.36; TX q = 0.648, both for PV;
            batteries are less visible than PV, Base pays $150-250 referral credits to both sides).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LAM_BAR = 36500 / 6091247


def nb_closed(M, n0, T0, H, k, lam_bar=LAM_BAR):
    r = k + n0
    b = k / lam_bar + M * T0
    mu = r * (M - n0) * H / b
    p = b / (b + (M - n0) * H)
    rng = np.random.default_rng(1)
    x = rng.negative_binomial(r, p, 200000)
    x = np.minimum(x, M - n0)
    return {"mean": round(float(x.mean()), 2), "p10": int(np.percentile(x, 10)), "p50": int(np.percentile(x, 50)),
            "p90": int(np.percentile(x, 90)), "lamPostPerYr": round(r / b, 4)}


def mc(M, n0, T0, H, k, q, lam_bar=LAM_BAR, sims=20000, seed=2):
    """Posterior lam draws (closed form, gamma ignored in the update: conservative), then a monthly simulation of the
    remaining homes with depletion and the peer term gamma = q / M."""
    rng = np.random.default_rng(seed)
    lam = rng.gamma(k + n0, 1.0 / (k / lam_bar + M * T0), sims)
    N = np.full(sims, n0, dtype=float)
    dt = 1 / 12
    for _ in range(int(H * 12)):
        haz = lam + (q / M) * N
        pr = 1 - np.exp(-haz * dt)
        N = N + rng.binomial((M - N).astype(int), np.clip(pr, 0, 1))
    add = N - n0
    return {"mean": round(float(add.mean()), 2), "p10": int(np.percentile(add, 10)), "p50": int(np.percentile(add, 50)),
            "p90": int(np.percentile(add, 90))}


def main():
    out = {"lamBarPerHomeYr": round(LAM_BAR, 5), "cases": []}
    for (M, n0, T0) in [(30, 5, 1.5), (50, 10, 1.5), (100, 20, 1.5), (100, 5, 1.5), (100, 0, 1.5), (40, 30, 2.0)]:
        for H in (1, 2, 5):
            for k in (0.3, 1.0):
                row = {"M": M, "n0": n0, "T0": T0, "H": H, "k": k, "closedForm": nb_closed(M, n0, T0, H, k)}
                for q in (0.0, 0.3):
                    row[f"mc_q{q}"] = mc(M, n0, T0, H, k, q)
                out["cases"].append(row)
    (HERE / "demand_model_out.json").write_text(json.dumps(out, indent=1))
    for c in out["cases"]:
        if c["H"] == 2:
            print(c["M"], c["n0"], "k", c["k"], "closed", c["closedForm"], "| mc q0", c["mc_q0.0"], "| mc q0.3", c["mc_q0.3"])


if __name__ == "__main__":
    main()
