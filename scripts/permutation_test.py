"""
Permutation test (small-cluster-robust robustness check) for the primary
asthma two-way fixed-effects regression.

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv, identical to
data/processed/panel_merged.csv; produced/estimated in run_analysis.py,
Model A):

    asthma_rate_per100k ~ pm25 + EntityEffects(region) + TimeEffects(year)
    fit via linearmodels.PanelOLS, cov_type="clustered", cluster_entity=True

    beta = -2.554, SE = 0.825, p = 0.0024, within-R^2 = 0.080
    (see outputs/tables/regression_results.csv, row "A: Levels FE")

Panel: 17 regions x 10 years (2013-2022) = 170 balanced region-year obs.

With only 17 clusters, the asymptotic cluster-robust SE (and its p-value)
is unreliable (rule of thumb wants 30-50+ clusters; Cameron & Miller 2015).
This script does NOT touch that result. It adds a nonparametric,
finite-sample-valid robustness check: a randomization/permutation test
(Fisher-style) that does not rely on cluster-asymptotics at all.

Estimator used inside the permutation loop
--------------------------------------------
The primary regression is a *balanced* two-way FE panel (17 x 10, no gaps),
so PanelOLS(EntityEffects + TimeEffects) coefficients are algebraically
identical to the classic two-way within (demeaning) estimator:

    y_tilde = y - mean_i(y) - mean_t(y) + mean(y)
    x_tilde = x - mean_i(x) - mean_t(x) + mean(x)
    beta_hat = sum(x_tilde * y_tilde) / sum(x_tilde^2)

This script verifies that identity against the actual linearmodels output
(if linearmodels is importable in the running environment) or, if not
available, against the beta/R^2 already reported in
outputs/tables/regression_results.csv. Either way, beta must match
-2.554 (to 3 dp) before any permutation is run. The demeaning estimator
(not the clustered-SE machinery) is what's repeated inside the permutation
loops, which is standard for randomization inference: the permutation
distribution itself is the source of inference, not a parametric SE.

Two permutation methods
------------------------
Method A - label permutation (full reshuffle across regions):
    Randomly reassign whole PM2.5 region-series to different regions
    (year structure within each series untouched), keeping the asthma
    outcome panel fixed. Re-estimate the two-way FE beta. Repeat 5,000x.
    This is the more standard/less conservative permutation test.

Method B - within-region circular time-shift (block permutation):
    For each region independently, circularly shift its own 10-year PM2.5
    series by a random number of years (1-9, i.e. never a null shift so
    every region actually moves), leaving asthma fixed. Re-estimate the
    two-way FE beta. Repeat 5,000x. This preserves each region's own
    PM2.5 level and trend shape, only breaking year-to-year alignment
    with asthma -- more conservative than Method A because it destroys
    less within-region structure that could spuriously correlate.

Reproducibility: numpy Generator seeded with 42.

Outputs:
    outputs/tables/permutation_test_results.csv
    outputs/figures/permutation_null_distribution.png  (Method B histogram)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SEED = 42
N_PERM = 5000
DATA_PATH = "data/processed/asthma_pm25_merged.csv"  # identical to panel_merged.csv
OUT_CSV = "outputs/tables/permutation_test_results.csv"
OUT_FIG = "outputs/figures/permutation_null_distribution.png"
REPORTED_BETA = -2.554  # from outputs/tables/regression_results.csv, Model A

os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & BUILD BALANCED (region x year) MATRICES
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
assert set(["region", "year", "asthma_rate_per100k", "pm25"]).issubset(df.columns)

regions = sorted(df["region"].unique())
years = sorted(df["year"].unique())
n_entities, n_time = len(regions), len(years)
print(f"Loaded {DATA_PATH}: {df.shape[0]} rows, {n_entities} regions x {n_time} years")
assert df.shape[0] == n_entities * n_time, "Panel is not balanced — script assumes a balanced panel."

Y = df.pivot(index="region", columns="year", values="asthma_rate_per100k").loc[regions, years].to_numpy()
X = df.pivot(index="region", columns="year", values="pm25").loc[regions, years].to_numpy()


def two_way_fe_beta(X, Y):
    """Two-way (entity + time) within estimator beta for a balanced panel matrix."""
    e_x = X.mean(axis=1, keepdims=True)
    e_y = Y.mean(axis=1, keepdims=True)
    m_x = X.mean(axis=0, keepdims=True)
    m_y = Y.mean(axis=0, keepdims=True)
    g_x, g_y = X.mean(), Y.mean()
    Xt = X - e_x - m_x + g_x
    Yt = Y - e_y - m_y + g_y
    beta = np.sum(Xt * Yt) / np.sum(Xt ** 2)
    within_r2 = 1.0 - np.sum((Yt - beta * Xt) ** 2) / np.sum(Yt ** 2)
    return beta, within_r2


# ─────────────────────────────────────────────────────────────────────────
# 2. SANITY CHECK: REPRODUCE THE ORIGINAL FE ESTIMATE
# ─────────────────────────────────────────────────────────────────────────
beta_obs, r2_obs = two_way_fe_beta(X, Y)
print(f"\nReproduced beta = {beta_obs:.4f}  (reported: {REPORTED_BETA})")
print(f"Reproduced within-R^2 = {r2_obs:.4f}  (reported: 0.0802)")

used_linearmodels = False
try:
    from linearmodels.panel import PanelOLS
    panel_fe = df.set_index(["region", "year"])
    mod = PanelOLS.from_formula("asthma_rate_per100k ~ pm25 + EntityEffects + TimeEffects", data=panel_fe)
    res = mod.fit(cov_type="clustered", cluster_entity=True)
    beta_lm = res.params["pm25"]
    print(f"linearmodels PanelOLS beta = {beta_lm:.4f} (direct cross-check, same environment as run_analysis.py)")
    assert abs(beta_lm - beta_obs) < 1e-6, "Manual two-way demeaning does not match linearmodels PanelOLS!"
    used_linearmodels = True
except ImportError:
    print("NOTE: linearmodels is not importable in this environment, so the direct "
          "PanelOLS cross-check was skipped. Sanity check instead compares the manual "
          "two-way demeaning estimate against the value already reported in "
          "outputs/tables/regression_results.csv.")

assert round(beta_obs, 3) == REPORTED_BETA, (
    f"Sanity check FAILED: reproduced beta {beta_obs:.4f} does not match reported {REPORTED_BETA}. "
    "Stopping before running any permutations."
)
print("Sanity check PASSED — proceeding to permutation tests.\n")


# ─────────────────────────────────────────────────────────────────────────
# 3. METHOD A — LABEL PERMUTATION (shuffle which PM2.5 series goes to which region)
# ─────────────────────────────────────────────────────────────────────────
rng_a = np.random.default_rng(SEED)
betas_a = np.empty(N_PERM)
for b in range(N_PERM):
    perm = rng_a.permutation(n_entities)
    X_perm = X[perm, :]  # whole regional series reassigned; year structure within a series untouched
    betas_a[b], _ = two_way_fe_beta(X_perm, Y)

p_a = np.mean(np.abs(betas_a) >= np.abs(beta_obs))
print(f"Method A (label permutation): mean(null beta)={betas_a.mean():.4f}, "
      f"sd(null beta)={betas_a.std(ddof=1):.4f}, empirical two-sided p = {p_a:.4f}")


# ─────────────────────────────────────────────────────────────────────────
# 4. METHOD B — WITHIN-REGION CIRCULAR TIME-SHIFT (block permutation)
# ─────────────────────────────────────────────────────────────────────────
rng_b = np.random.default_rng(SEED)
betas_b = np.empty(N_PERM)
for b in range(N_PERM):
    shifts = rng_b.integers(1, n_time, size=n_entities)  # 1..n_time-1, so every region actually shifts
    X_shift = np.empty_like(X)
    for i in range(n_entities):
        X_shift[i, :] = np.roll(X[i, :], shifts[i])
    betas_b[b], _ = two_way_fe_beta(X_shift, Y)

p_b = np.mean(np.abs(betas_b) >= np.abs(beta_obs))
print(f"Method B (within-region circular time-shift): mean(null beta)={betas_b.mean():.4f}, "
      f"sd(null beta)={betas_b.std(ddof=1):.4f}, empirical two-sided p = {p_b:.4f}")


# ─────────────────────────────────────────────────────────────────────────
# 5. SAVE RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────
results = pd.DataFrame({
    "method": [
        "A: label permutation (shuffle region-PM2.5 assignment)",
        "B: within-region circular time-shift (block permutation)",
    ],
    "observed_beta": [beta_obs, beta_obs],
    "n_permutations": [N_PERM, N_PERM],
    "empirical_p_value": [p_a, p_b],
    "null_distribution_mean": [betas_a.mean(), betas_b.mean()],
    "null_distribution_sd": [betas_a.std(ddof=1), betas_b.std(ddof=1)],
})
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")


# ─────────────────────────────────────────────────────────────────────────
# 6. FIGURE — METHOD B NULL DISTRIBUTION HISTOGRAM
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
ax.hist(betas_b, bins=60, color="#2166ac", alpha=0.75, edgecolor="white")
ax.axvline(beta_obs, color="#d6604d", lw=2.5,
           label=f"Observed β = {beta_obs:.3f}")
ax.axvline(-beta_obs, color="#d6604d", lw=1.5, ls="--",
           label=f"−(Observed β) = {-beta_obs:.3f}  (two-sided ref.)")
ax.set_xlabel("Permuted β (Method B: within-region circular time-shift)", fontsize=11)
ax.set_ylabel("Frequency", fontsize=11)
ax.set_title(
    f"Null Distribution of β under Within-Region Time-Shift Permutation (n={N_PERM:,})\n"
    f"Empirical two-sided p = {p_b:.4f}",
    fontsize=11,
)
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(OUT_FIG, dpi=150)
plt.close()
print(f"Saved {OUT_FIG}")

print("\n── PERMUTATION TEST COMPLETE ──")
print(f"Method A empirical p = {p_a:.4f}")
print(f"Method B empirical p = {p_b:.4f}  (more conservative — for reporting)")
