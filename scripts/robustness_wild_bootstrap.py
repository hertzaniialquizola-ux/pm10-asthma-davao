"""
robustness_wild_bootstrap.py
=============================
Robustness upgrade #1 (of 10 requested this session): wild cluster
bootstrap-restricted (WCR) p-value for the primary two-way fixed-effects
coefficient on PM2.5.

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv, same panel used by
run_analysis.py Model A and scripts/permutation_test.py):

    asthma_rate_per100k ~ pm25 + EntityEffects(region) + TimeEffects(year)
    fit via linearmodels.PanelOLS, cov_type="clustered", cluster_entity=True

    beta = -2.5541, SE = 0.8247, p = 0.0024, within-R^2 = 0.0802
    (outputs/tables/regression_results.csv, row "A: Levels FE")

Panel: 17 regions x 10 years (2013-2022) = 170 balanced region-year obs.

Why WCR on top of the existing permutation test
-------------------------------------------------
scripts/permutation_test.py already added a randomization-inference check
(justified there by the same small-cluster concern: only 17 clusters, below
the 30-50+ rule of thumb from Cameron & Miller 2015). This script adds a
second, methodologically distinct small-cluster-robust check: the wild
cluster bootstrap, restricted version (WCR; Cameron, Gelbach & Miller 2008,
"Bootstrap-Based Improvements for Inference with Clustered Errors"). WCR is
one of the most widely recommended small-G inference methods in applied
panel econometrics and is a natural complement (not a duplicate) of the
permutation test:
  - The permutation test asks "how surprising is beta under a fully
    randomized null" (no structural model assumed for the bootstrap DGP).
  - WCR asks "what does the *sampling distribution of the t-statistic*
    look like under the null beta=0, if we resample cluster-level (region)
    sign-flips of the model's own restricted residuals" — closer in spirit
    to the clustered-SE machinery it's meant to double-check, and is the
    standard reference method cited whenever G is small (here G=17).

Because linearmodels/scipy are not importable in this sandbox (no network
access to install them; see scripts/stats_lite.py docstring for why), all
of the two-way FE fitting, cluster-robust SE, and t-distribution p-values
below are computed with scripts/stats_lite.py, which is validated (see
`python3 scripts/stats_lite.py`) to reproduce the repo's already-reported
beta/SE/p (-2.5541 / 0.8247 / 0.0024) to the precision shown.

Method (WCR)
------------
1. Fit the RESTRICTED model (H0: beta_pm25 = 0), i.e. the two-way FE
   structure with no PM2.5 term. For a balanced panel this restricted fit
   is exactly the two-way-demeaned asthma series itself: the FE-only model
   fits region+year means perfectly, so restricted residuals = Yt (the
   two-way demeaned asthma matrix) and restricted fitted values = Y - Yt.
2. For b in 1..N_BOOT: draw one Rademacher weight w_i in {-1,+1} per
   region (cluster), independently. Construct the bootstrap outcome
       Y*_it = (Y_it - Yt_it) + w_i * Yt_it
   (equivalently Y* = Y when w_i=+1, Y* = Y - 2*Yt when w_i=-1).
   Re-estimate the UNRESTRICTED two-way FE model of Y* on the ORIGINAL
   (unchanged) PM2.5 matrix, using the same cluster-robust SE formula as
   the observed fit, to get t*_b.
3. WCR bootstrap p-value = fraction of bootstrap draws with
   |t*_b| >= |t_observed| (t_observed from the actual, non-bootstrapped
   fit -- this is what makes it "restricted": only step 1's residuals are
   restricted, step 3 always compares to the real, unrestricted t-stat).

Reproducibility: numpy Generator seeded with 42 (matches
scripts/permutation_test.py's convention), N_BOOT = 5,000.

Outputs:
    outputs/tables/wild_bootstrap_results.csv
    outputs/figures/wild_bootstrap_null_distribution.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import build_matrix, two_way_demean, two_way_fe_beta, cluster_robust_se, fe_fit

SEED = 42
N_BOOT = 5000
DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/wild_bootstrap_results.csv"
OUT_FIG = "outputs/figures/wild_bootstrap_null_distribution.png"
REPORTED_BETA = -2.5541
REPORTED_SE = 0.8247
REPORTED_P = 0.0024

os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & SANITY-CHECK AGAINST THE REPORTED RESULT
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
assert set(["region", "year", "asthma_rate_per100k", "pm25"]).issubset(df.columns)

fit = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"Loaded {DATA_PATH}: {df.shape[0]} rows, {fit['n_entities']} regions x {fit['n_time']} years")
print(f"Reproduced beta = {fit['beta']:.4f}  (reported: {REPORTED_BETA})")
print(f"Reproduced SE   = {fit['se']:.4f}  (reported: {REPORTED_SE})")
print(f"Reproduced p    = {fit['p_value']:.4f}  (reported: {REPORTED_P})")

assert round(fit["beta"], 3) == round(REPORTED_BETA, 3), "beta mismatch -- stopping before bootstrap."
assert round(fit["se"], 3) == round(REPORTED_SE, 3), "SE mismatch -- stopping before bootstrap."
assert round(fit["p_value"], 4) == REPORTED_P, "p-value mismatch -- stopping before bootstrap."
print("Sanity check PASSED (beta, SE, and p all match the reported clustered-SE result "
      "to reported precision) — proceeding to wild cluster bootstrap.\n")

X = fit["X"]              # levels PM2.5 matrix (N_entities x N_time), unchanged across draws
Y = fit["Y"]               # levels asthma matrix
Yt_obs = fit["Yt"]         # two-way demeaned asthma (= restricted residuals under H0: beta=0)
n_entities, n_time = fit["n_entities"], fit["n_time"]
t_obs = fit["t_stat"]
beta_obs = fit["beta"]

# ─────────────────────────────────────────────────────────────────────────
# 2. WILD CLUSTER BOOTSTRAP - RESTRICTED (WCR), RADEMACHER WEIGHTS
# ─────────────────────────────────────────────────────────────────────────
rng = np.random.default_rng(SEED)
betas_boot = np.empty(N_BOOT)
t_boot = np.empty(N_BOOT)

for b in range(N_BOOT):
    w = rng.choice([-1.0, 1.0], size=(n_entities, 1))  # one Rademacher draw per region
    Y_star = Y - (1.0 - w) * Yt_obs  # = Y when w=+1, Y - 2*Yt when w=-1
    beta_b, r2_b, Xt_b, Yt_b, resid_b = two_way_fe_beta(X, Y_star)
    se_b = cluster_robust_se(Xt_b, resid_b, n_entities, n_time, n_params=1)
    betas_boot[b] = beta_b
    t_boot[b] = beta_b / se_b

p_wcr = np.mean(np.abs(t_boot) >= np.abs(t_obs))

print(f"WCR wild cluster bootstrap ({N_BOOT} reps, Rademacher weights, seed={SEED}):")
print(f"  observed t = {t_obs:.4f} (beta={beta_obs:.4f}, SE={fit['se']:.4f})")
print(f"  bootstrap null t: mean={t_boot.mean():.4f}, sd={t_boot.std(ddof=1):.4f}")
print(f"  WCR bootstrap p-value = {p_wcr:.4f}")
print(f"  (existing clustered-SE p-value for comparison = {REPORTED_P})")
print(f"  (existing permutation-test p-values for comparison: "
      f"Method A = 0.0048, Method B = 0.0008 — outputs/tables/permutation_test_results.csv)")

# ─────────────────────────────────────────────────────────────────────────
# 3. SAVE RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────
results = pd.DataFrame({
    "check": ["Wild cluster bootstrap (WCR, Rademacher weights)"],
    "observed_beta": [beta_obs],
    "observed_se_clustered": [fit["se"]],
    "observed_t": [t_obs],
    "n_bootstrap_reps": [N_BOOT],
    "wcr_bootstrap_p_value": [p_wcr],
    "clustered_se_p_value_for_comparison": [REPORTED_P],
    "null_t_mean": [t_boot.mean()],
    "null_t_sd": [t_boot.std(ddof=1)],
})
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")

# ─────────────────────────────────────────────────────────────────────────
# 4. FIGURE — BOOTSTRAP NULL t-DISTRIBUTION
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
ax.hist(t_boot, bins=60, color="#2166ac", alpha=0.75, edgecolor="white")
ax.axvline(t_obs, color="#d6604d", lw=2.5, label=f"Observed t = {t_obs:.3f}")
ax.axvline(-t_obs, color="#d6604d", lw=1.5, ls="--", label=f"−(Observed t) = {-t_obs:.3f} (two-sided ref.)")
ax.set_xlabel("Bootstrap t* (wild cluster bootstrap, restricted, Rademacher weights)", fontsize=11)
ax.set_ylabel("Frequency", fontsize=11)
ax.set_title(
    f"Null Distribution of t under Wild Cluster Bootstrap (WCR, n={N_BOOT:,})\n"
    f"Bootstrap p = {p_wcr:.4f}  |  clustered-SE p = {REPORTED_P}",
    fontsize=11,
)
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(OUT_FIG, dpi=150)
plt.close()
print(f"Saved {OUT_FIG}")

print("\n── WILD CLUSTER BOOTSTRAP COMPLETE ──")
print(f"WCR bootstrap p = {p_wcr:.4f}")
