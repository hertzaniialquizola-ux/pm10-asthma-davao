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
N_BOOT = 1000  # fewer than the sandbox's 5000 since each draw refits real PanelOLS (slower)
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

print("\nDONE. Compare every number above to the corresponding outputs/tables/*.csv file.")
