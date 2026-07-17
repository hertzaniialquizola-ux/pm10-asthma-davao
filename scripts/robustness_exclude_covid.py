"""
robustness_exclude_covid.py
=============================
Robustness upgrade #4 (of 10 requested this session): re-estimate the
primary two-way fixed-effects model excluding 2020-2021, to check whether
the result is sensitive to COVID-19 pandemic-era healthcare-utilization
disruption.

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv, 17 regions x 10
years 2013-2022, n=170):
    beta = -2.5541, SE = 0.8247, p = 0.0024, within-R^2 = 0.0802

The manuscript's Limitations section already flags this qualitatively:
"The study period includes COVID-19 pandemic years (2020-2021), which
disrupted healthcare utilization and likely affected formal diagnosis
rates." This check turns that qualitative caveat into a quantitative one:
does the two-way FE coefficient move if those two years are dropped
entirely, leaving a 17-region x 8-year (2013-2019, 2022) panel, n=136?

Note this is not a continuous 8-year run (2013-2019 then 2022) but a
17 x 8 panel with a 2-year gap; the balanced two-way demeaning identity
used throughout this session (see scripts/stats_lite.py, scripts/
permutation_test.py) only requires a *rectangular* (every region observed
in every retained year) panel, not a contiguous one, so it still applies
directly.

linearmodels/scipy are unavailable in this sandbox (see scripts/
stats_lite.py docstring); fitting uses the same fe_fit() helper already
validated there to reproduce the repo's reported beta/SE/p.

Outputs:
    outputs/tables/exclude_covid_results.csv
    outputs/figures/exclude_covid_comparison.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import fe_fit

DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/exclude_covid_results.csv"
OUT_FIG = "outputs/figures/exclude_covid_comparison.png"
REPORTED_BETA = -2.5541
REPORTED_SE = 0.8247
REPORTED_P = 0.0024
COVID_YEARS = [2020, 2021]

os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & SANITY-CHECK FULL-SAMPLE RESULT
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
assert set(["region", "year", "asthma_rate_per100k", "pm25"]).issubset(df.columns)

full_fit = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"Loaded {DATA_PATH}: {df.shape[0]} rows, {full_fit['n_entities']} regions x {full_fit['n_time']} years")
print(f"Full-sample (2013-2022) beta = {full_fit['beta']:.4f}  (reported: {REPORTED_BETA})")
print(f"Full-sample SE   = {full_fit['se']:.4f}  (reported: {REPORTED_SE})")
print(f"Full-sample p    = {full_fit['p_value']:.4f}  (reported: {REPORTED_P})")
assert round(full_fit["beta"], 3) == round(REPORTED_BETA, 3), "beta mismatch -- stopping."
assert round(full_fit["se"], 3) == round(REPORTED_SE, 3), "SE mismatch -- stopping."
print("Sanity check PASSED — proceeding to COVID-year exclusion.\n")

# ─────────────────────────────────────────────────────────────────────────
# 2. EXCLUDE 2020-2021
# ─────────────────────────────────────────────────────────────────────────
sub = df[~df["year"].isin(COVID_YEARS)]
years_kept = sorted(sub["year"].unique())
print(f"Years retained ({len(years_kept)}): {years_kept}")
print(f"Rows retained: {len(sub)} (should be 17 regions x {len(years_kept)} years = {17*len(years_kept)})")

covid_fit = fe_fit(sub, "region", "year", "pm25", "asthma_rate_per100k")
print(f"\nExcluding {COVID_YEARS}: beta={covid_fit['beta']:.4f}, se={covid_fit['se']:.4f}, "
      f"t={covid_fit['t_stat']:.4f}, p={covid_fit['p_value']:.4f}, within_R2={covid_fit['within_r2']:.4f}, "
      f"n={covid_fit['n_obs']}")

# ─────────────────────────────────────────────────────────────────────────
# 3. SAVE RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────
results = pd.DataFrame({
    "specification": ["Full sample (2013-2022)", "Excluding 2020-2021 (2013-2019, 2022)"],
    "years": [str(full_fit["times"]), str(years_kept)],
    "beta": [full_fit["beta"], covid_fit["beta"]],
    "se": [full_fit["se"], covid_fit["se"]],
    "t_stat": [full_fit["t_stat"], covid_fit["t_stat"]],
    "p_value": [full_fit["p_value"], covid_fit["p_value"]],
    "within_r2": [full_fit["within_r2"], covid_fit["within_r2"]],
    "n_obs": [full_fit["n_obs"], covid_fit["n_obs"]],
}).round(4)
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")

pct_change = (covid_fit["beta"] - full_fit["beta"]) / full_fit["beta"] * 100
print(f"\nbeta change vs full sample: {pct_change:+.1f}%")

# ─────────────────────────────────────────────────────────────────────────
# 4. FIGURE
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 5))
specs = ["Full sample\n(2013-2022, n=170)", "Excl. 2020-2021\n(2013-2019+2022, n=136)"]
betas = [full_fit["beta"], covid_fit["beta"]]
ses = [full_fit["se"], covid_fit["se"]]
colors = ["#2166ac", "#d6604d"]
ax.errorbar(range(2), betas, yerr=[1.96 * s for s in ses], fmt="o", markersize=10,
            color="black", ecolor="gray", elinewidth=2, capsize=6)
for i, c in enumerate(colors):
    ax.scatter(i, betas[i], color=c, s=140, zorder=3)
ax.axhline(0, color="black", lw=1)
ax.set_xticks(range(2))
ax.set_xticklabels(specs, fontsize=10)
ax.set_ylabel("Two-way FE β (PM2.5 → asthma prevalence)", fontsize=11)
ax.set_title("Robustness to Excluding COVID-19 Pandemic Years (2020-2021)\nPoints = β; bars = 95% CI (clustered SE)", fontsize=11)
plt.tight_layout()
plt.savefig(OUT_FIG, dpi=150)
plt.close()
print(f"Saved {OUT_FIG}")

print("\n── COVID-EXCLUSION ROBUSTNESS CHECK COMPLETE ──")
