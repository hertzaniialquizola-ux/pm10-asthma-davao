"""
robustness_region_trends.py
=============================
Robustness check #9: region-specific linear time trends.

WHY THIS CHECK, AND WHY THE 8 EXISTING ONES DON'T COVER IT
------------------------------------------------------------
An external peer-review pass on this manuscript (methods-focused, causal-
inference/panel-econometrics framing) pointed out a real gap: the paper's
own DAG names "unobserved region x year confounders -- local healthcare-
access changes, smoking prevalence, or socioeconomic shifts within a
region over time" as the one confounding path the two-way FE design does
NOT close. But every one of the 8 existing robustness checks (permutation
test, wild cluster bootstrap, jackknife, COVID exclusion, lag structure,
Hausman, Moran's I, placebo test) interrogates whether the STANDARD ERROR
on the primary coefficient is trustworthy given only 17 clusters -- none
of them test whether the coefficient ITSELF could be confounded by a
differential regional TRAJECTORY (e.g. staggered Universal Health Care Act
rollout, PhilHealth expansion) rather than a differential regional LEVEL
(which entity fixed effects already absorb).

This is the standard fix for exactly that threat in applied panel
econometrics: add a region-specific linear time trend for every region
alongside the existing entity and year fixed effects (e.g. Wolfers 2006,
"Did Unilateral Divorce Laws Raise Divorce Rates?", uses state-specific
trends for the same reason). If the primary result survives this far more
demanding specification, that's real evidence it isn't just picking up
differential regional trajectories; if it doesn't survive, that's an
important, honest limitation to report.

METHOD
------
y_it = beta*pm25_it + alpha_i (region FE) + gamma_t (year FE)
       + delta_i * t_i (one linear trend slope PER region) + e_it

Implemented via scripts/stats_lite.py's new fe_fit_with_region_trends():
build one (17 x 10) "trend" regressor matrix per region -- nonzero
(=0,1,...,9) only in that region's own row, zero elsewhere -- two-way
demean everything (Y, pm25, and all 17 trend regressors), then run one
joint OLS solve on the demeaned system (Frisch-Waugh-Lovell equivalent of
including entity dummies + year dummies + all 17 trend terms directly).
Cluster-robust SE uses the same sandwich formula as fe_fit_multi(), with
n_params = 1 (pm25) + 17 (one trend slope per region) = 18.

This is a demanding specification: 18 parameters fit to 170 observations
(only ~8 "spare" within-region data points per region once a level AND a
linear trend are both removed), so a large within-R^2 jump is expected
mechanically, not just from confounding removal -- reported and discussed,
not hidden.

Outputs:
    outputs/tables/region_specific_trends_results.csv
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import fe_fit, fe_fit_with_region_trends

DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/region_specific_trends_results.csv"

df = pd.read_csv(DATA_PATH)

base = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"Primary (no region trends): beta={base['beta']:.4f}, se={base['se']:.4f}, "
      f"p={base['p_value']:.4f}, within_r2={base['within_r2']:.4f}, df_t={base['df_t']}")

trend_fit = fe_fit_with_region_trends(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"\nWith 17 region-specific linear trends added:")
print(f"  n_params={trend_fit['n_params']} (1 pm25 + 17 region-trend slopes), df_t={trend_fit['df_t']}")
print(f"  beta_pm25={trend_fit['beta_pm25']:.4f}, se={trend_fit['se_pm25']:.4f}, "
      f"p={trend_fit['p_pm25']:.4f}, within_r2={trend_fit['within_r2']:.4f}")

pct_change = 100.0 * (trend_fit["beta_pm25"] - base["beta"]) / base["beta"]
print(f"\nChange in beta_pm25: {base['beta']:.4f} -> {trend_fit['beta_pm25']:.4f} ({pct_change:+.1f}%)")
if trend_fit["p_pm25"] >= 0.05:
    print("Does NOT survive at conventional 5% significance once region-specific trends are allowed.")
else:
    print(f"Survives at conventional 5% significance (p={trend_fit['p_pm25']:.4f}), "
          f"though the point estimate shrank substantially ({pct_change:+.1f}%) and this is a "
          f"far more demanding specification (within_r2 jumped from {base['within_r2']:.4f} to "
          f"{trend_fit['within_r2']:.4f}, meaning region-specific trends absorb most variance, "
          f"leaving relatively little to identify the PM2.5 coefficient from).")

results = pd.DataFrame([{
    "check": "primary_no_region_trends", "beta_pm25": base["beta"], "se": base["se"],
    "p": base["p_value"], "within_r2": base["within_r2"], "n_params": 1,
    "df_t": base["df_t"], "n": base["n_obs"],
}, {
    "check": "with_17_region_specific_linear_trends", "beta_pm25": trend_fit["beta_pm25"],
    "se": trend_fit["se_pm25"], "p": trend_fit["p_pm25"], "within_r2": trend_fit["within_r2"],
    "n_params": trend_fit["n_params"], "df_t": trend_fit["df_t"], "n": trend_fit["n_obs"],
}]).round(4)
os.makedirs("outputs/tables", exist_ok=True)
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")
