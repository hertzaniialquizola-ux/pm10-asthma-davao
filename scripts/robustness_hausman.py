"""
robustness_hausman.py
=======================
Robustness upgrade #5 (of 10 requested this session): Hausman specification
test (fixed effects vs. random effects), formalizing the FE-over-RE choice
the manuscript currently just asserts (Methods: "the primary analytical
method was a two-way fixed-effects panel regression").

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv, 17 regions x 10
years, n=170):
    asthma_rate_per100k ~ pm25 + EntityEffects(region) + TimeEffects(year)
    beta = -2.5541, SE = 0.8247, p = 0.0024, within-R^2 = 0.0802

Why this check matters here specifically: the manuscript's own Discussion
argues that the pooled cross-sectional correlation (r=+0.887) is driven by
*time-invariant, region-level confounding* (urbanization, healthcare
infrastructure, diagnostic capacity) correlated with PM2.5 levels. That is
exactly the condition under which random effects (which assumes the region
effect is uncorrelated with the regressor) is invalid and fixed effects is
required. The Hausman test is the standard formal test of that assumption.

Implementation note (why this isn't just linearmodels.PanelOLS +
linearmodels.RandomEffects)
-------------------------------------------------------------------------
linearmodels is not importable in this sandbox (no network access to
install it; see scripts/stats_lite.py docstring). This script implements
both sides of the test from scratch, in a way built to be checked against
the repo's already-reported numbers before the Hausman statistic itself is
trusted:

  1. FE side: entity-only within regression (demean by region) with year
     DUMMIES included as explicit regressors (pm25 + 9 year dummies,
     2013 as baseline). For a *balanced* panel this is algebraically
     identical to the two-way EntityEffects+TimeEffects estimator already
     used throughout this project (a textbook FWL/dummy-variable
     equivalence) -- so the pm25 coefficient from this FE-with-dummies
     specification must reproduce beta=-2.5541 before anything else here
     is trusted. It is checked below.
  2. RE side: balanced one-way (region) random-effects estimator via the
     standard Swamy-Arora variance-components method (sigma_e^2 from the
     within regression, sigma_u^2 from the between regression), followed
     by quasi-demeaning GLS on the same regressor set (pm25 + 9 year
     dummies + constant), per Wooldridge (2010), Econometric Analysis of
     Cross Section and Panel Data, 2nd ed., Ch. 10.
  3. Hausman statistic: H = (b_FE - b_RE)' [Var(b_FE) - Var(b_RE)]^-1
     (b_FE - b_RE), computed only over the coefficients shared by both
     specifications (pm25 + year dummies; the RE model's extra constant
     term is dropped from the comparison, standard practice since FE
     cannot identify a level constant). Var(b_FE) uses the FE model's own
     (non-robust, classical) covariance matrix and Var(b_RE) the RE
     model's, per the standard Hausman auxiliary-regression convention
     (Wooldridge 2010, sec. 10.7.3) -- NOT the clustered SEs used
     elsewhere in this manuscript, because the Hausman test's asymptotic
     chi-square distribution relies on RE being efficient under H0, which
     requires classical (not cluster-robust) variances on both sides.
     This is a known limitation of the classical Hausman test with
     clustered data and is reported as such below.
  4. p-value via the chi-square survival function in scripts/stats_lite.py
     (validated there against textbook critical values).

Outputs:
    outputs/tables/hausman_test_results.csv
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import fe_fit, fe_fit_with_dummies, random_effects_fit, chi2_sf

DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/hausman_test_results.csv"
REPORTED_BETA = -2.5541

os.makedirs("outputs/tables", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & SANITY-CHECK THE TWO-WAY FE RESULT
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH).copy()
twfe = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"Two-way FE (EntityEffects+TimeEffects) beta = {twfe['beta']:.4f}  (reported: {REPORTED_BETA})")
assert round(twfe["beta"], 3) == round(REPORTED_BETA, 3), "Two-way FE beta mismatch -- stopping."

# ─────────────────────────────────────────────────────────────────────────
# 2. BUILD YEAR DUMMIES (2013 = baseline) AND DESIGN MATRICES
# ─────────────────────────────────────────────────────────────────────────
years = sorted(df["year"].unique())
baseline_year = years[0]
year_dummy_cols = []
for y in years[1:]:
    col = f"year_{y}"
    df[col] = (df["year"] == y).astype(float)
    year_dummy_cols.append(col)
df["const"] = 1.0

x_cols_fe = ["pm25"] + year_dummy_cols          # no constant: within-demeaning removes it
x_cols_re = ["const", "pm25"] + year_dummy_cols  # RE needs an explicit constant

# ---- FE with year dummies (entity-demean only) ----
beta_fe, vcov_fe, cols_fe = fe_fit_with_dummies(df, "region", "year", x_cols_fe, "asthma_rate_per100k")
beta_fe_pm25 = beta_fe[cols_fe.index("pm25")]
print(f"FE-with-year-dummies (entity demean only) beta(pm25) = {beta_fe_pm25:.4f}  "
      f"(should match two-way FE: {twfe['beta']:.4f})")
assert round(beta_fe_pm25, 3) == round(twfe["beta"], 3), \
    "FE-with-dummies does not match two-way FE -- equivalence check FAILED, stopping."
print("Sanity check PASSED (FE-with-year-dummies reproduces the two-way FE pm25 coefficient) "
      "— proceeding to random-effects estimation and the Hausman test.\n")

# ---- Random effects (Swamy-Arora) ----
re = random_effects_fit(df, "region", "year", x_cols_re, "asthma_rate_per100k")
beta_re_pm25 = re["beta"][re["x_cols"].index("pm25")]
print(f"Random effects (Swamy-Arora) beta(pm25) = {beta_re_pm25:.4f}")
print(f"  theta (quasi-demeaning weight) = {re['theta']:.4f}")
print(f"  sigma_e^2 (within/idiosyncratic variance) = {re['sigma_e2']:.4f}")
print(f"  sigma_u^2 (between/region-effect variance) = {re['sigma_u2']:.4f}")

# ─────────────────────────────────────────────────────────────────────────
# 3. HAUSMAN STATISTIC (over the coefficients common to both: pm25 + year dummies)
# ─────────────────────────────────────────────────────────────────────────
common_cols = x_cols_fe  # pm25 + year dummies, no constant (FE can't identify one)
idx_fe = [cols_fe.index(c) for c in common_cols]
idx_re = [re["x_cols"].index(c) for c in common_cols]

b_fe = beta_fe[idx_fe]
b_re = re["beta"][idx_re]
V_fe = vcov_fe[np.ix_(idx_fe, idx_fe)]
V_re = re["vcov"][np.ix_(idx_re, idx_re)]

diff = b_fe - b_re
V_diff = V_fe - V_re

# V_diff can be numerically non-PD with only 17 clusters / 10 years; use a
# pseudo-inverse and flag this explicitly rather than silently failing.
eigvals = np.linalg.eigvalsh(V_diff)
V_diff_is_pd = np.all(eigvals > 0)
V_diff_inv = np.linalg.pinv(V_diff)
H = float(diff @ V_diff_inv @ diff)
df_hausman = len(common_cols)  # 10: pm25 + 9 year dummies
p_hausman = chi2_sf(H, df_hausman)

print(f"\nHausman statistic H = {H:.4f} (df={df_hausman}, over pm25 + {len(year_dummy_cols)} year dummies)")
print(f"  V(b_FE - b_RE) positive-definite: {V_diff_is_pd} "
      f"({'no numerical issue' if V_diff_is_pd else 'used Moore-Penrose pseudo-inverse -- see note below'})")
print(f"  p-value = {p_hausman:.6f}")
print(f"  beta_FE(pm25)={b_fe[0]:.4f} vs beta_RE(pm25)={b_re[0]:.4f}  "
      f"(diff = {b_fe[0]-b_re[0]:.4f})")

# Also report the pm25-only Hausman comparison (single coefficient), which
# is less standard but easier to interpret directly and less prone to the
# small-df/near-singularity issue that can affect the full-vector version
# with only 17 regions and 10 year dummies.
pm25_i_fe = cols_fe.index("pm25")
pm25_i_re = re["x_cols"].index("pm25")
diff_pm25 = beta_fe_pm25 - beta_re_pm25
var_diff_pm25 = vcov_fe[pm25_i_fe, pm25_i_fe] - re["vcov"][pm25_i_re, pm25_i_re]
if var_diff_pm25 > 0:
    H_pm25 = diff_pm25 ** 2 / var_diff_pm25
    p_pm25 = chi2_sf(H_pm25, 1)
    print(f"\nSingle-coefficient Hausman (pm25 only): H={H_pm25:.4f}, df=1, p={p_pm25:.6f}")
else:
    H_pm25, p_pm25 = np.nan, np.nan
    print(f"\nSingle-coefficient Hausman (pm25 only): Var(b_FE)-Var(b_RE) <= 0 "
          f"({var_diff_pm25:.6f}) -- statistic not computable this way; "
          f"see full-vector Hausman above.")

# ─────────────────────────────────────────────────────────────────────────
# 3b. ONE-WAY (REGION-ONLY, NO YEAR EFFECTS) FE VS RE, FOR CONTEXT
# ─────────────────────────────────────────────────────────────────────────
# The two-way Hausman comparison above is degenerate (non-PD V_diff). As a
# second, much lower-dimensional check (2 parameters instead of 10, the
# textbook-simplest Hausman setup), also compare one-way region-only FE vs
# RE (no year effects/dummies at all). NOTE: dropping year effects changes
# what the FE coefficient even means (it no longer nets out the shared
# national year-to-year trend the way the two-way model does), so this is
# NOT a substitute for the paper's two-way model -- it exists purely to
# see whether the Hausman degeneracy is a two-way/year-dummy artifact.
x_cols_fe_1way = ["pm25"]
x_cols_re_1way = ["const", "pm25"]
beta_fe1, vcov_fe1, cols_fe1 = fe_fit_with_dummies(df, "region", "year", x_cols_fe_1way, "asthma_rate_per100k")
re1 = random_effects_fit(df, "region", "year", x_cols_re_1way, "asthma_rate_per100k")
b_fe1 = beta_fe1[cols_fe1.index("pm25")]
b_re1 = re1["beta"][re1["x_cols"].index("pm25")]
v_fe1 = vcov_fe1[cols_fe1.index("pm25"), cols_fe1.index("pm25")]
v_re1 = re1["vcov"][re1["x_cols"].index("pm25"), re1["x_cols"].index("pm25")]
print(f"\n[Context only, NOT the paper's model] One-way (region-only, no year effects):")
print(f"  beta_FE(pm25)={b_fe1:.4f}, beta_RE(pm25)={b_re1:.4f}  "
      f"(sign flips: one-way FE without year effects does not net out the shared\n"
      f"   national PM2.5/asthma time trend, so this number should not be quoted as a\n"
      f"   robustness result on its own -- it is here only to check the Hausman degeneracy.)")
var_diff_1way = v_fe1 - v_re1
print(f"  Var(b_FE)-Var(b_RE) = {var_diff_1way:.4f} "
      f"({'valid (PD)' if var_diff_1way > 0 else 'still degenerate (non-PD)'})")

# ─────────────────────────────────────────────────────────────────────────
# 4. SAVE RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────
results = pd.DataFrame({
    "quantity": [
        "beta_FE (pm25, two-way FE / FE-with-dummies, matched)",
        "beta_RE (pm25, Swamy-Arora RE)",
        "Hausman H (full vector: pm25 + 9 year dummies)",
        "Hausman df (full vector)",
        "Hausman p-value (full vector)",
        "V(diff) positive-definite (full vector)",
        "Hausman H (pm25 coefficient only)",
        "Hausman p-value (pm25 coefficient only)",
        "theta (RE quasi-demeaning weight)",
        "sigma_e^2 (within/idiosyncratic variance, RE)",
        "sigma_u^2 (between/region variance, RE)",
        "[context only] one-way beta_FE (pm25, no year effects)",
        "[context only] one-way beta_RE (pm25, no year effects)",
        "[context only] one-way Var(b_FE)-Var(b_RE)",
    ],
    "value": [
        beta_fe_pm25, beta_re_pm25, H, df_hausman, p_hausman, V_diff_is_pd,
        H_pm25, p_pm25, re["theta"], re["sigma_e2"], re["sigma_u2"],
        b_fe1, b_re1, var_diff_1way,
    ],
})
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")

print("\n── HAUSMAN TEST COMPLETE ──")
