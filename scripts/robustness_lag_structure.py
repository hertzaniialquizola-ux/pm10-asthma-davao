"""
robustness_lag_structure.py
=============================
Robustness upgrade #6 (of 10 requested this session, "if time allows"):
lagged PM2.5 exposure (1/2/3-year lags) and a 3-year rolling-mean exposure
specification, using the same two-way fixed-effects spec as the primary
model.

Context / motivation
---------------------
Primary result uses same-year PM2.5 (data/processed/asthma_pm25_merged.csv):
    beta = -2.5541, SE = 0.8247, p = 0.0024, within-R^2 = 0.0802 (n=170)

The manuscript's own Discussion argues that asthma prevalence, as a "stock"
measure that "changes slowly," is poorly suited to detecting a same-year
PM2.5 effect. Chronic pediatric asthma burden is also biologically more
plausibly linked to *cumulative* exposure than to a single year's mean
concentration. This check asks whether the null/negative same-year result
is an artifact of that specific timing choice, by re-running the identical
two-way FE spec with:
  - PM2.5 lagged 1, 2, and 3 years (asthma_t ~ pm25_{t-1/2/3})
  - a 3-year trailing rolling-mean of PM2.5 (mean of pm25_t, pm25_{t-1},
    pm25_{t-2}), a simple cumulative-exposure proxy

Each lag/rolling spec necessarily drops the earliest year(s) per region
(no data before 2013), so each of these models is fit on a smaller,
STILL-BALANCED (every remaining region x year cell present) rectangular
panel -- balance is what lets the two-way demeaning identity from
scripts/stats_lite.py (validated against the repo's reported beta/SE/p)
keep applying unchanged.

linearmodels/scipy are unavailable in this sandbox (see scripts/
stats_lite.py docstring); all fitting uses the validated fe_fit() helper.

Outputs:
    outputs/tables/lag_structure_results.csv
    outputs/figures/lag_structure_comparison.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import fe_fit

DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/lag_structure_results.csv"
OUT_FIG = "outputs/figures/lag_structure_comparison.png"
REPORTED_BETA = -2.5541

os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & SANITY-CHECK SAME-YEAR (LAG 0) RESULT
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH).sort_values(["region", "year"]).reset_index(drop=True)
lag0 = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"Lag-0 (same-year, primary spec) beta = {lag0['beta']:.4f}  (reported: {REPORTED_BETA})")
assert round(lag0["beta"], 3) == round(REPORTED_BETA, 3), "Lag-0 beta mismatch -- stopping."
print("Sanity check PASSED — proceeding to lagged / rolling-mean specifications.\n")

# ─────────────────────────────────────────────────────────────────────────
# 2. BUILD LAGGED / ROLLING-MEAN PM2.5 COLUMNS (WITHIN REGION, YEAR-SORTED)
# ─────────────────────────────────────────────────────────────────────────
g = df.groupby("region")["pm25"]
df["pm25_lag1"] = g.shift(1)
df["pm25_lag2"] = g.shift(2)
df["pm25_lag3"] = g.shift(3)
df["pm25_roll3"] = g.transform(lambda s: s.rolling(window=3, min_periods=3).mean())

specs = [
    ("Lag 0 (same-year, primary spec)", "pm25", 0),
    ("Lag 1 year", "pm25_lag1", 1),
    ("Lag 2 years", "pm25_lag2", 2),
    ("Lag 3 years", "pm25_lag3", 3),
    ("3-year trailing rolling mean", "pm25_roll3", 2),
]

rows = []
for label, col, min_lag in specs:
    sub = df.dropna(subset=[col, "asthma_rate_per100k"]).copy()
    # Confirm the retained panel is still balanced (every region has the
    # same set of years) before trusting the two-way demeaning identity.
    years_per_region = sub.groupby("region")["year"].apply(lambda s: tuple(sorted(s)))
    balanced = years_per_region.nunique() == 1
    fit = fe_fit(sub, "region", "year", col, "asthma_rate_per100k")
    rows.append({
        "spec": label,
        "exposure_var": col,
        "years_used": f"{sub['year'].min()}-{sub['year'].max()}",
        "n_years": fit["n_time"],
        "n_regions": fit["n_entities"],
        "n_obs": fit["n_obs"],
        "panel_balanced": balanced,
        "beta": fit["beta"],
        "se": fit["se"],
        "t_stat": fit["t_stat"],
        "p_value": fit["p_value"],
        "within_r2": fit["within_r2"],
    })
    print(f"  {label:35s}: n={fit['n_obs']:3d} ({sub['year'].min()}-{sub['year'].max()}), "
          f"beta={fit['beta']:.4f}, se={fit['se']:.4f}, p={fit['p_value']:.4f}, "
          f"within_R2={fit['within_r2']:.4f}, balanced={balanced}")

results = pd.DataFrame(rows).round(4)
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")

# ─────────────────────────────────────────────────────────────────────────
# 3. FIGURE
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
x = range(len(results))
ax.errorbar(x, results["beta"], yerr=1.96 * results["se"], fmt="o", markersize=9,
            color="#2166ac", ecolor="gray", elinewidth=2, capsize=5)
ax.axhline(0, color="black", lw=1)
ax.set_xticks(list(x))
ax.set_xticklabels([s.replace(" (", "\n(") for s in results["spec"]], fontsize=8.5, rotation=0)
ax.set_ylabel("Two-way FE β (PM2.5 exposure spec → asthma prevalence)", fontsize=11)
ax.set_title("Exposure Timing / Cumulative-Exposure Robustness\nPoints = β; bars = 95% CI (clustered SE)", fontsize=11)
plt.tight_layout()
plt.savefig(OUT_FIG, dpi=150)
plt.close()
print(f"Saved {OUT_FIG}")

print("\n── LAG STRUCTURE / ROLLING-MEAN CHECK COMPLETE ──")
