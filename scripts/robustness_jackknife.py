"""
robustness_jackknife.py
=========================
Robustness upgrade #3 (of 10 requested this session): leave-one-region-out
jackknife on the primary two-way fixed-effects coefficient on PM2.5.

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv):
    beta = -2.5541, SE = 0.8247, p = 0.0024, within-R^2 = 0.0802
    (outputs/tables/regression_results.csv, row "A: Levels FE")

The manuscript's Discussion and Results repeatedly single out the National
Capital Region (NCR) as structurally different from the other 16 regions
(highest PM2.5 at 26.74 ug/m3, highest asthma prevalence at 8,866 per
100,000, and — per Figure 1's caption — "clear outliers in the upper-right
quadrant" of the pooled scatter). Because NCR is such a clear outlier in
levels, a natural question the manuscript does not yet directly answer is
whether the two-way FE coefficient itself is being driven by NCR alone,
i.e., whether dropping NCR changes beta's sign, magnitude, or significance.

This check answers that generally: re-estimate the same two-way FE model
17 times, once per region, each time dropping that one region and refitting
on the remaining 16 regions x 10 years = 160 region-year panel. If beta
stays negative, similar in magnitude, and significant across all 17
leave-one-out refits (including leave-NCR-out), the primary result is not
being driven by any single region.

linearmodels/scipy are unavailable in this sandbox (see scripts/
stats_lite.py docstring); fitting uses the same fe_fit() helper already
validated there to reproduce the repo's reported beta/SE/p to the reported
precision.

Outputs:
    outputs/tables/jackknife_results.csv
    outputs/figures/jackknife_leave_one_region_out.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import fe_fit

DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/jackknife_results.csv"
OUT_FIG = "outputs/figures/jackknife_leave_one_region_out.png"
REPORTED_BETA = -2.5541
REPORTED_SE = 0.8247
REPORTED_P = 0.0024

os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & SANITY-CHECK FULL-SAMPLE RESULT
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
assert set(["region", "year", "asthma_rate_per100k", "pm25"]).issubset(df.columns)

full_fit = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"Loaded {DATA_PATH}: {df.shape[0]} rows, {full_fit['n_entities']} regions x {full_fit['n_time']} years")
print(f"Full-sample beta = {full_fit['beta']:.4f}  (reported: {REPORTED_BETA})")
print(f"Full-sample SE   = {full_fit['se']:.4f}  (reported: {REPORTED_SE})")
print(f"Full-sample p    = {full_fit['p_value']:.4f}  (reported: {REPORTED_P})")
assert round(full_fit["beta"], 3) == round(REPORTED_BETA, 3), "beta mismatch -- stopping."
assert round(full_fit["se"], 3) == round(REPORTED_SE, 3), "SE mismatch -- stopping."
print("Sanity check PASSED — proceeding to leave-one-region-out jackknife.\n")

regions = full_fit["entities"]
print(f"Regions ({len(regions)}): {regions}\n")

# ─────────────────────────────────────────────────────────────────────────
# 2. LEAVE-ONE-REGION-OUT
# ─────────────────────────────────────────────────────────────────────────
rows = []
for dropped in regions:
    sub = df[df["region"] != dropped]
    fit = fe_fit(sub, "region", "year", "pm25", "asthma_rate_per100k")
    rows.append({
        "region_dropped": dropped,
        "beta": fit["beta"],
        "se": fit["se"],
        "t_stat": fit["t_stat"],
        "p_value": fit["p_value"],
        "within_r2": fit["within_r2"],
        "n_regions_remaining": fit["n_entities"],
        "n_obs": fit["n_obs"],
    })
    print(f"  drop {dropped:12s}: beta={fit['beta']:.4f}, se={fit['se']:.4f}, "
          f"p={fit['p_value']:.4f}, within_R2={fit['within_r2']:.4f}")

jk = pd.DataFrame(rows).round(4)
jk.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")

# ─────────────────────────────────────────────────────────────────────────
# 3. SUMMARY
# ─────────────────────────────────────────────────────────────────────────
beta_min, beta_max = jk["beta"].min(), jk["beta"].max()
n_sig = (jk["p_value"] < 0.05).sum()
n_same_sign = (jk["beta"] < 0).sum()
ncr_row = jk[jk["region_dropped"] == "NCR"]
print(f"\nJackknife beta range: [{beta_min:.4f}, {beta_max:.4f}]  (full-sample: {full_fit['beta']:.4f})")
print(f"Negative sign preserved in {n_same_sign}/17 leave-one-out refits")
print(f"Significant at p<0.05 in {n_sig}/17 leave-one-out refits")
if not ncr_row.empty:
    print(f"Leave-NCR-out specifically: beta={ncr_row['beta'].values[0]:.4f}, "
          f"p={ncr_row['p_value'].values[0]:.4f}")

# ─────────────────────────────────────────────────────────────────────────
# 4. FIGURE
# ─────────────────────────────────────────────────────────────────────────
jk_sorted = jk.sort_values("beta")
fig, ax = plt.subplots(figsize=(9, 6))
colors = ["#d6604d" if r == "NCR" else "#2166ac" for r in jk_sorted["region_dropped"]]
ax.errorbar(jk_sorted["beta"], range(len(jk_sorted)),
            xerr=1.96 * jk_sorted["se"], fmt="o", color="gray", ecolor="gray",
            elinewidth=1, capsize=3, zorder=1)
ax.scatter(jk_sorted["beta"], range(len(jk_sorted)), color=colors, s=60, zorder=2)
ax.set_yticks(range(len(jk_sorted)))
ax.set_yticklabels([f"drop {r}" for r in jk_sorted["region_dropped"]], fontsize=9)
ax.axvline(0, color="black", lw=1, ls="-")
ax.axvline(full_fit["beta"], color="#d6604d", lw=1.5, ls="--",
           label=f"Full-sample β = {full_fit['beta']:.3f} (n=170)")
ax.set_xlabel("Two-way FE β (PM2.5 → asthma prevalence), region dropped", fontsize=11)
ax.set_title("Leave-One-Region-Out Jackknife\nPoints = β with one region excluded; bars = 95% CI (clustered SE)", fontsize=11)
ax.legend(fontsize=9, loc="lower right")
plt.tight_layout()
plt.savefig(OUT_FIG, dpi=150)
plt.close()
print(f"Saved {OUT_FIG}")

print("\n── JACKKNIFE COMPLETE ──")
