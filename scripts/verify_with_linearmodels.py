#!/usr/bin/env python3
"""
verify_with_linearmodels.py
=============================
Run this on your Mac (PyCharm, with a working venv that actually has
scipy/statsmodels/linearmodels installed -- NOT in the Cowork sandbox,
which had no network access and couldn't install them; see
scripts/stats_lite.py's docstring for the full explanation).

WHY THIS SCRIPT EXISTS
-----------------------
Every number in this project's 8 new robustness checks was computed with
scripts/stats_lite.py, a from-scratch pure-numpy reimplementation of the
statistics linearmodels/scipy would normally provide (t/chi-square/F
distributions, two-way FE demeaning, cluster-robust SE, a Swamy-Arora RE
estimator). It was validated by reproducing the ALREADY-TRUSTED reported
result (beta=-2.5541, SE=0.8247, p=0.0024) to the same precision -- but
that's not the same as an independent library confirming the NEW numbers
(wild bootstrap p=0.036, jackknife range, COVID exclusion, lag/rolling-
mean betas, in particular the surprisingly large 3-year rolling-mean
result beta=-6.040). This script redoes the most important of those
checks with the real linearmodels.PanelOLS / linearmodels.RandomEffects,
so you can compare against outputs/tables/*.csv and confirm nothing was
lost in the from-scratch translation.

If a number here differs meaningfully from the corresponding
outputs/tables/*.csv value, TRUST THIS SCRIPT (real linearmodels) and
treat stats_lite.py as having a bug to report, not the other way around.

Requires: pandas, numpy, linearmodels (pip install linearmodels; pulls in
scipy/statsmodels/pandas as dependencies if not already present).
"""

import pandas as pd
import numpy as np
from linearmodels.panel import PanelOLS, RandomEffects
import warnings
warnings.filterwarnings("ignore")

DATA_PATH = "data/processed/asthma_pm25_merged.csv"


def fit_fe(df, x_col, y_col):
    panel = df.set_index(["region", "year"])
    mod = PanelOLS.from_formula(f"{y_col} ~ {x_col} + EntityEffects + TimeEffects", data=panel)
    res = mod.fit(cov_type="clustered", cluster_entity=True)
    return res.params[x_col], res.std_errors[x_col], res.pvalues[x_col], res.rsquared, len(panel)


df = pd.read_csv(DATA_PATH)
print("=" * 78)
print("0. PRIMARY MODEL SANITY CHECK (should match outputs/tables/regression_results.csv)")
print("=" * 78)
b, se, p, r2, n = fit_fe(df, "pm25", "asthma_rate_per100k")
print(f"beta={b:.4f} (reported -2.5541)  se={se:.4f} (reported 0.8247)  "
      f"p={p:.4f} (reported 0.0024)  within_R2={r2:.4f} (reported 0.0802)  n={n}")

print("\n" + "=" * 78)
print("1. WILD CLUSTER BOOTSTRAP (WCR), real PanelOLS refits each draw")
print("=" * 78)
print("(compare to outputs/tables/wild_bootstrap_results.csv: p=0.0362)")
print("NOTE: an earlier run of this section used N_BOOT=1000 (vs. the sandbox's 5000) purely")
print("for runtime reasons, and got p=0.0420 -- this is NOT a disagreement between stats_lite.py")
print("and real linearmodels. Re-running the sandbox's own closed-form formula (same seed=42) at")
print("N_BOOT=1000/5000/20000/100000 gives p=0.0420/0.0362/0.0347/0.0345 -- i.e. 1000 reps")
print("reproduces 0.0420 EXACTLY regardless of which implementation computes it, and the true")
print("bootstrap p-value is converging toward ~0.034-0.035 as reps increase. The manuscript's")
print("5000-rep number (0.036) is the better-converged estimate, not the less-verified one. This")
print("section now uses N_BOOT=5000 to match the manuscript exactly rather than re-litigating this.")
regions = sorted(df["region"].unique())
years = sorted(df["year"].unique())
Y = df.pivot(index="region", columns="year", values="asthma_rate_per100k").loc[regions, years].to_numpy()
e = Y.mean(axis=1, keepdims=True)
m = Y.mean(axis=0, keepdims=True)
g = Y.mean()
Yt = Y - e - m + g  # restricted (H0: beta=0) residuals = two-way demeaned Y

base_fit = fit_fe(df, "pm25", "asthma_rate_per100k")
t_obs = base_fit[0] / base_fit[1]

rng = np.random.default_rng(42)
N_BOOT = 5000  # matched to the sandbox's N_BOOT so this reproduces the manuscript's number exactly
t_boot = np.empty(N_BOOT)
for b_i in range(N_BOOT):
    w = rng.choice([-1.0, 1.0], size=(len(regions), 1))
    Y_star = Y - (1.0 - w) * Yt
    df_star = df.copy()
    y_lookup = pd.DataFrame(Y_star, index=regions, columns=years)
    df_star["asthma_star"] = df_star.apply(lambda row: y_lookup.loc[row["region"], row["year"]], axis=1)
    _, se_b, _, _, _ = fit_fe(df_star, "pm25", "asthma_star")
    panel = df_star.set_index(["region", "year"])
    mod = PanelOLS.from_formula("asthma_star ~ pm25 + EntityEffects + TimeEffects", data=panel)
    res = mod.fit(cov_type="clustered", cluster_entity=True)
    t_boot[b_i] = res.params["pm25"] / res.std_errors["pm25"]

p_wcr = np.mean(np.abs(t_boot) >= np.abs(t_obs))
print(f"WCR bootstrap p-value (real linearmodels, {N_BOOT} reps) = {p_wcr:.4f}")

print("\n" + "=" * 78)
print("2. LEAVE-ONE-REGION-OUT JACKKNIFE")
print("=" * 78)
print("(compare to outputs/tables/jackknife_results.csv)")
for dropped in regions:
    sub = df[df["region"] != dropped]
    b, se, p, r2, n = fit_fe(sub, "pm25", "asthma_rate_per100k")
    flag = "  <-- NCR" if dropped == "NCR" else ""
    print(f"  drop {dropped:12s}: beta={b:.4f}, se={se:.4f}, p={p:.4f}{flag}")

print("\n" + "=" * 78)
print("3. EXCLUDING 2020-2021 (COVID)")
print("=" * 78)
print("(compare to outputs/tables/exclude_covid_results.csv: beta=-2.1126, p=0.0875)")
sub = df[~df["year"].isin([2020, 2021])]
b, se, p, r2, n = fit_fe(sub, "pm25", "asthma_rate_per100k")
print(f"beta={b:.4f}, se={se:.4f}, p={p:.4f}, n={n}")

print("\n" + "=" * 78)
print("4. LAG STRUCTURE + 3-YEAR ROLLING MEAN (the one you specifically asked to double-check)")
print("=" * 78)
print("(compare to outputs/tables/lag_structure_results.csv: rolling mean beta=-6.0401, p<0.0001)")
dfl = df.sort_values(["region", "year"]).copy()
g_ = dfl.groupby("region")["pm25"]
dfl["pm25_lag1"] = g_.shift(1)
dfl["pm25_lag2"] = g_.shift(2)
dfl["pm25_lag3"] = g_.shift(3)
dfl["pm25_roll3"] = g_.transform(lambda s: s.rolling(window=3, min_periods=3).mean())
for label, col in [("lag0 (same-year)", "pm25"), ("lag1", "pm25_lag1"), ("lag2", "pm25_lag2"),
                    ("lag3", "pm25_lag3"), ("3yr rolling mean", "pm25_roll3")]:
    sub = dfl.dropna(subset=[col, "asthma_rate_per100k"])
    b, se, p, r2, n = fit_fe(sub, col, "asthma_rate_per100k")
    print(f"  {label:20s}: beta={b:.4f}, se={se:.4f}, p={p:.4f}, within_R2={r2:.4f}, n={n}")

print("\n" + "=" * 78)
print("5. HAUSMAN TEST — real linearmodels.RandomEffects (the sandbox's from-scratch")
print("   Swamy-Arora RE produced a degenerate/non-computable classical Hausman stat;")
print("   this uses linearmodels' actual RE implementation, which may behave differently)")
print("=" * 78)
# NOTE: set_index(["region","year"]) moves "year" into the MultiIndex, so it
# stops existing as an ordinary column and "C(year)" below can't resolve it
# (this is what threw formulaic.errors.FactorEvaluationError: NameError:
# name 'year' is not defined the first time this ran). Fix: keep a plain
# "yr" column alongside the index specifically so the RE formula has a
# real column to build year dummies from.
df_h = df.copy()
df_h["yr"] = df_h["year"]
panel = df_h.set_index(["region", "year"])
fe_mod = PanelOLS.from_formula("asthma_rate_per100k ~ pm25 + EntityEffects + TimeEffects", data=panel)
fe_res = fe_mod.fit(cov_type="unadjusted")  # classical (non-clustered) SE, required for a valid Hausman test
re_mod = RandomEffects.from_formula("asthma_rate_per100k ~ pm25 + C(yr)", data=panel)
re_res = re_mod.fit(cov_type="unadjusted")
b_fe, b_re = fe_res.params["pm25"], re_res.params["pm25"]
v_fe, v_re = fe_res.std_errors["pm25"] ** 2, re_res.std_errors["pm25"] ** 2
print(f"beta_FE(pm25)={b_fe:.4f} (var={v_fe:.6f})   beta_RE(pm25)={b_re:.4f} (var={v_re:.6f})")
if v_fe > v_re:
    from scipy import stats as sp_stats
    H = (b_fe - b_re) ** 2 / (v_fe - v_re)
    p_h = 1 - sp_stats.chi2.cdf(H, df=1)
    print(f"Hausman H (pm25 only) = {H:.4f}, p = {p_h:.6f}  <-- if this ran, it's a VALID result")
else:
    print("Var(FE) <= Var(RE) again -- same degeneracy as the sandbox's from-scratch version. "
          "This would mean the degeneracy is a real feature of this dataset (very high between-"
          "region variance relative to within-region variance), not a bug in stats_lite.py.")

print("\n" + "=" * 78)
print("6. PLACEBO/NEGATIVE-CONTROL TEST (added after the other 7 -- the GBD export you ran")
print("   arrived later). Outcome: 'Low back pain', ages 5-14, no plausible PM2.5 pathway.")
print("=" * 78)
print("(compare to outputs/tables/placebo_test_results.csv: beta=-0.1801, se=0.4136, p=0.6640)")
placebo_path = "data/processed/placebo_lowbackpain_pm25_merged.csv"
try:
    dfp = pd.read_csv(placebo_path)
    b, se, p, r2, n = fit_fe(dfp, "pm25", "placebo_lowbackpain_rate_per100k")
    print(f"beta={b:.4f}, se={se:.4f}, p={p:.4f}, within_R2={r2:.4f}, n={n}")
    if p >= 0.05:
        print("No significant PM2.5 association with the negative control -- supports reading the")
        print("asthma null as real, not an artifact of the GBD subnational estimation pipeline.")
    else:
        print("SIGNIFICANT PM2.5 association with a placebo outcome that has no plausible pathway --")
        print("this would be the more important finding; it would call the asthma result's")
        print("interpretation into question too. Report this to the author if it happens here.")
except FileNotFoundError:
    print(f"Could not find {placebo_path} -- run scripts/robustness_placebo.py first "
          "(it writes this file as part of the aggregation step).")

print("\n" + "=" * 78)
print("7. BIOMASS-FUEL-USE MEDIATOR CHECK (real PanelOLS, multi-regressor)")
print("=" * 78)
print("(compare to outputs/tables/mediator_biomass_fuel_results.csv)")
biomass_path = "data/processed/biomass_fuel_pm25_asthma_merged.csv"
try:
    dfb = pd.read_csv(biomass_path)
    b0, se0, p0, r20, n0 = fit_fe(dfb, "pm25", "asthma_rate_per100k")
    print(f"WITHOUT covariate: beta={b0:.4f} (reported -2.5541), se={se0:.4f}, p={p0:.4f}")

    panel = dfb.set_index(["region", "year"])
    mod = PanelOLS.from_formula(
        "asthma_rate_per100k ~ pm25 + biomass_fuel_pct + EntityEffects + TimeEffects", data=panel)
    res = mod.fit(cov_type="clustered", cluster_entity=True)
    print(f"WITH covariate:    beta_pm25={res.params['pm25']:.4f} "
          f"(reported -2.0955), se={res.std_errors['pm25']:.4f}, p={res.pvalues['pm25']:.4f}")
    print(f"                   beta_biomass_fuel={res.params['biomass_fuel_pct']:.4f} "
          f"(reported 0.3671), se={res.std_errors['biomass_fuel_pct']:.4f}, "
          f"p={res.pvalues['biomass_fuel_pct']:.4f}")

    region_means = dfb.groupby("region")[["biomass_fuel_pct", "pm25"]].mean()
    r_between = region_means["biomass_fuel_pct"].corr(region_means["pm25"])
    print(f"Between-region correlation = {r_between:.4f} (reported -0.7257)")

    print("\nNOTE: NCR is a highly influential single point in this correlation and in the")
    print("covariate-adjusted beta (see outputs/tables/mediator_biomass_fuel_results.csv rows")
    print("'drop_NCR_*') -- dropping NCR alone drops the between-region r from -0.73 to -0.42 and")
    print("makes beta_pm25(+covariate) non-significant (p=0.15). This mirrors the already-known")
    print("NCR sensitivity of the PRIMARY model itself (see section 2 above / jackknife_results.csv:")
    print("dropping NCR from the primary model alone already weakens it from p=0.0024 to p=0.0448),")
    print("so this is a known, previously-disclosed feature of the dataset's NCR row, not a new")
    print("problem introduced by the mediator check.")
except FileNotFoundError:
    print(f"Could not find {biomass_path} -- run scripts/task3_mediator_analysis.py first.")

print("\n" + "=" * 78)
print("8. REGION-SPECIFIC LINEAR TIME TRENDS (real PanelOLS, 17 extra trend regressors)")
print("=" * 78)
print("(compare to outputs/tables/region_specific_trends_results.csv)")
print("This is the peer-review-flagged identification check: does the primary result survive")
print("once each region is allowed its own linear trajectory, not just its own level?")
dft = df.sort_values(["region", "year"]).reset_index(drop=True).copy()
dft["t_idx"] = dft.groupby("region").cumcount()  # 0..9 in year order, same convention as the
                                                   # sandbox's fe_fit_with_region_trends (explicit
                                                   # sorted-year index, not raw file row order)
for region in sorted(dft["region"].unique()):
    dft[f"trend_{region}"] = dft["t_idx"] * (dft["region"] == region).astype(float)
trend_cols = [c for c in dft.columns if c.startswith("trend_")]
panel = dft.set_index(["region", "year"])
formula = "asthma_rate_per100k ~ pm25 + " + " + ".join(trend_cols) + " + EntityEffects + TimeEffects"
mod = PanelOLS.from_formula(formula, data=panel)
res = mod.fit(cov_type="clustered", cluster_entity=True)
print(f"beta_pm25={res.params['pm25']:.4f} (reported -0.9373), se={res.std_errors['pm25']:.4f} "
      f"(reported 0.4463), p={res.pvalues['pm25']:.4f} (reported 0.0377)")
print(f"within_r2={res.rsquared:.4f} (reported 0.7908)")
primary_beta = -2.5541  # hardcoded, not the reused `b` variable above (which by this point in
                         # the script holds the placebo/jackknife/lag section's last value, not
                         # the primary pm25 coefficient)
pct_change = 100.0 * (res.params["pm25"] - primary_beta) / primary_beta
print(f"Change from primary beta ({b:.4f}): {pct_change:+.1f}%")
if res.pvalues["pm25"] >= 0.05:
    print("Does NOT survive at conventional 5% significance here -- if this differs from the")
    print("sandbox's p=0.0377, TRUST THIS (real linearmodels) result.")
else:
    print("Survives at conventional 5% significance, consistent with the sandbox result -- but note")
    print("the point estimate shrinks substantially and this is a demanding 18-parameter/170-obs")
    print("specification (see script docstring in scripts/robustness_region_trends.py).")

print("\nDONE. Compare every number above to the corresponding outputs/tables/*.csv file.")
