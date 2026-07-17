"""
robustness_placebo.py
=======================
Robustness upgrade #2 (of the original 10 requested; the last of the 8
checks that ended up implemented): placebo/negative-control outcome test.

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv, 17 regions x 10
years, n=170):
    beta = -2.5541, SE = 0.8247, p = 0.0024, within-R^2 = 0.0802

The Discussion already argues the null/negative asthma result partly
reflects a general feature of GBD subnational estimates (modeled,
smoothed toward national trends, low within-region variance) rather than
something specific to asthma -- and the existing "Testing Additional
Respiratory Outcomes" subsection tests that by trying 4 more RESPIRATORY
outcomes. But all 5 of those outcomes (asthma, LRI, COPD, lung cancer,
respiratory mortality) have at least a plausible PM2.5 pathway. A true
negative control needs a cause with NO plausible pathway at all (Lipsitch,
Tchetgen Tchetgen & Cohen, 2010): if the same two-way FE machinery finds
"significant" PM2.5 associations with outcomes PM2.5 cannot plausibly
cause, that would suggest the FE estimator itself (or the GBD subnational
estimation process feeding it) manufactures spurious associations --
undermining trust in the asthma result too. If it finds nothing, that is
positive evidence the null is a real absence of a same-year effect, not
an artifact of the estimation pipeline.

Data source
-----------
User-exported GBD 2023 CSV: data/raw/gbd/IHME-GBD_2023_DATA-fb1be876-1.csv
(subnational Philippines, Prevalence, Rate, ages 5-14, both sexes,
2013-2022 -- same filters as the other 4 outcomes). This file actually
contains TWO cause labels, not one:
    "Low back pain"               (n=820 province-years, ages 5-14)
    "Musculoskeletal disorders"   (n=820 province-years, ages 5-14)
"Musculoskeletal disorders" is GBD's broader parent cause; "Low back
pain" is the more specific child cause AND was one of the two candidates
originally suggested (the other, "Other musculoskeletal disorders", is
not the label present in this file -- flagging the exact discrepancy
rather than silently treating them as the same thing). PRIMARY_CAUSE below
is set to "Low back pain": it is more specific, is a standard, frequently
used negative-control outcome in the air-pollution epidemiology
literature (no established PM2.5 pathway), and was explicitly one of the
two options offered. "Musculoskeletal disorders" passes the same data
sanity checks below equally well and is left in SECONDARY_CAUSE in case
the author wants to swap or add it as a second placebo.

Data sanity check (required before regressing, per task instructions)
------------------------------------------------------------------------
Checked and PASSED for both causes: no zero values, no degenerate
(constant) values, and every one of the 82 provinces has non-zero
within-province variance across the 10 years (std range for Low back
pain: 3.30-14.51 per 100,000, mean within-province std=8.56). This is NOT
a flat/degenerate series -- the regression below is safe to run.

Method
------
Identical pipeline to the other 4 outcomes (aggregate_gbd_provinces.py):
drop the national "Philippines" row, map province -> one of the 17 study
regions via the SAME PROVINCE_TO_REGION dict already used for asthma/
lung cancer/LRI/COPD/respiratory mortality (imported directly, not
re-typed, so this can't drift from the established mapping), group by
region+year with a simple mean (population-weighting already established
as infeasible with available data -- see START_HERE.md), merge with the
PM2.5 regional panel, and fit the identical two-way FE spec (region +
year effects, SE clustered by region) via scripts/stats_lite.py (already
validated to reproduce the primary model to 4 decimal places against
real linearmodels -- see scripts/verify_with_linearmodels.py's results,
logged in START_HERE.md).

Outputs:
    data/processed/placebo_lowbackpain_regional_panel.csv
    data/processed/placebo_lowbackpain_pm25_merged.csv
    outputs/tables/placebo_test_results.csv
    outputs/figures/placebo_test_comparison.png
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stats_lite import fe_fit
from aggregate_gbd_provinces import PROVINCE_TO_REGION

RAW_PATH = "data/raw/gbd/IHME-GBD_2023_DATA-fb1be876-1.csv"
PM25_PATH = "data/processed/pm25_regional_panel.csv"
PRIMARY_CAUSE = "Low back pain"
SECONDARY_CAUSE = "Musculoskeletal disorders"  # not used as primary; see docstring
REGIONAL_OUT = "data/processed/placebo_lowbackpain_regional_panel.csv"
MERGED_OUT = "data/processed/placebo_lowbackpain_pm25_merged.csv"
RESULTS_OUT = "outputs/tables/placebo_test_results.csv"
FIG_OUT = "outputs/figures/placebo_test_comparison.png"
REPORTED_ASTHMA_BETA = -2.5541
REPORTED_ASTHMA_SE = 0.8247

os.makedirs("data/processed", exist_ok=True)
os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD RAW, CONFIRM EXACT CAUSE LABELS PRESENT
# ─────────────────────────────────────────────────────────────────────────
raw = pd.read_csv(RAW_PATH)
causes_present = sorted(raw["cause_name"].unique())
print(f"Loaded {RAW_PATH}")
print(f"Cause labels present in this export: {causes_present}")
assert PRIMARY_CAUSE in causes_present, f"{PRIMARY_CAUSE!r} not found in this export!"
print(f"Using PRIMARY_CAUSE = {PRIMARY_CAUSE!r}  "
      f"(also present but not used: {SECONDARY_CAUSE!r}, see docstring)")

assert set(raw["age_name"].unique()) == {"5-14 years"}, "Unexpected age band in export."
assert set(raw["sex_name"].unique()) == {"Both"}, "Unexpected sex filter in export."
assert set(raw["measure_name"].unique()) == {"Prevalence"}, "Unexpected measure in export."
assert set(raw["metric_name"].unique()) == {"Rate"}, "Unexpected metric in export."
print("Confirmed filters match the other 4 outcomes: ages 5-14, both sexes, "
      "Prevalence, Rate, 2013-2022.\n")

# ─────────────────────────────────────────────────────────────────────────
# 2. DATA SANITY CHECK (must pass before any regression is run)
# ─────────────────────────────────────────────────────────────────────────
sub = raw[(raw["cause_name"] == PRIMARY_CAUSE) & (raw["location_name"] != "Philippines")].copy()
print(f"Sanity check on {PRIMARY_CAUSE!r} (ages 5-14, n={len(sub)} province-years):")
print(sub["val"].describe())

n_zero = (sub["val"] == 0).sum()
n_unique = sub["val"].nunique()
within_prov_std = sub.groupby("location_name")["val"].std()
n_degenerate_provinces = (within_prov_std == 0).sum()

print(f"\n  zero values: {n_zero}")
print(f"  unique values: {n_unique} / {len(sub)} rows")
print(f"  provinces with zero within-province variance across years: {n_degenerate_provinces} / {within_prov_std.shape[0]}")
print(f"  within-province std range: {within_prov_std.min():.2f} to {within_prov_std.max():.2f} per 100,000")

if n_zero == len(sub) or n_unique <= 1 or n_degenerate_provinces == within_prov_std.shape[0]:
    raise SystemExit(
        f"STOPPING: {PRIMARY_CAUSE!r} data is flat/degenerate (all-zero or all-identical). "
        "Per task instructions, this must be reported to the user, not regressed on."
    )
print(f"\nSANITY CHECK PASSED: {PRIMARY_CAUSE!r} has non-degenerate variance across "
      "provinces and years. Proceeding to aggregation and regression.\n")

# ─────────────────────────────────────────────────────────────────────────
# 3. AGGREGATE PROVINCE -> REGION (identical method to the other 4 outcomes)
# ─────────────────────────────────────────────────────────────────────────
unmatched = set(sub["location_name"].unique()) - set(PROVINCE_TO_REGION.keys())
if unmatched:
    print(f"WARNING - unmatched provinces (dropped): {sorted(unmatched)}")
else:
    print("All provinces matched the existing PROVINCE_TO_REGION mapping (no drops).")

sub["region"] = sub["location_name"].map(PROVINCE_TO_REGION)
matched = sub[sub["region"].notna()].copy()

value_col = "placebo_lowbackpain_rate_per100k"
regional = (
    matched.groupby(["region", "year"])["val"]
    .mean()
    .reset_index()
    .rename(columns={"val": value_col})
)
regional.to_csv(REGIONAL_OUT, index=False)
print(f"\nRegional panel shape: {regional.shape} (should be 170 = 17 regions x 10 years)")
assert regional.shape[0] == 170, f"Expected 170 rows, got {regional.shape[0]}."
print(f"Saved {REGIONAL_OUT}")

# ─────────────────────────────────────────────────────────────────────────
# 4. MERGE WITH PM2.5, RUN THE IDENTICAL TWO-WAY FE SPEC
# ─────────────────────────────────────────────────────────────────────────
pm25 = pd.read_csv(PM25_PATH)
merged = regional.merge(pm25, on=["region", "year"], how="inner")
merged.to_csv(MERGED_OUT, index=False)
print(f"Merged panel shape: {merged.shape}")
assert merged.shape[0] == 170, f"Expected 170 rows after merge, got {merged.shape[0]}."
print(f"Saved {MERGED_OUT}\n")

fit = fe_fit(merged, "region", "year", "pm25", value_col)
print(f"Two-way FE placebo result ({PRIMARY_CAUSE}):")
print(f"  beta      = {fit['beta']:.4f}")
print(f"  SE        = {fit['se']:.4f}")
print(f"  t         = {fit['t_stat']:.4f}")
print(f"  p         = {fit['p_value']:.4f}")
print(f"  within_R2 = {fit['within_r2']:.4f}")
print(f"  n         = {fit['n_obs']}")

# Sanity re-check: this script's fe_fit() call uses the exact same
# stats_lite.py machinery already validated against the primary asthma
# model (and against real linearmodels, see START_HERE.md) -- re-verify
# that hasn't silently broken by re-fitting the primary model here too.
asthma_check = fe_fit(
    pd.read_csv("data/processed/asthma_pm25_merged.csv"), "region", "year", "pm25", "asthma_rate_per100k"
)
assert round(asthma_check["beta"], 3) == round(REPORTED_ASTHMA_BETA, 3), "stats_lite.py regression -- primary model mismatch!"
print(f"\n(sanity re-check: primary asthma model still reproduces beta={asthma_check['beta']:.4f}, "
      f"SE={asthma_check['se']:.4f} via the same fe_fit() call used above -- stats_lite.py is intact.)")

# ─────────────────────────────────────────────────────────────────────────
# 5. INTERPRETATION (printed, not decided in advance -- report whichever way it goes)
# ─────────────────────────────────────────────────────────────────────────
print("\n── INTERPRETATION ──")
if fit["p_value"] >= 0.05:
    print(f"PM2.5 shows NO significant association with {PRIMARY_CAUSE} (p={fit['p_value']:.4f} >= 0.05).")
    print("This supports reading the asthma null as a real absence of a same-year effect, not an")
    print("artifact of how smoothed/modeled GBD subnational estimates are in general.")
else:
    print(f"PM2.5 DOES show a significant association with {PRIMARY_CAUSE} (p={fit['p_value']:.4f} < 0.05),")
    print("an outcome with no plausible PM2.5 pathway. This is the more important finding to report")
    print("honestly: it suggests caution interpreting ANY of the FE results (including asthma) because")
    print("of how the GBD subnational estimates or the FE estimator itself may behave in this dataset.")

# ─────────────────────────────────────────────────────────────────────────
# 6. SAVE RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────
results = pd.DataFrame({
    "outcome": [PRIMARY_CAUSE],
    "outcome_slug": ["placebo_lowbackpain"],
    "value_col": [value_col],
    "beta": [fit["beta"]],
    "se": [fit["se"]],
    "t_stat": [fit["t_stat"]],
    "p_value": [fit["p_value"]],
    "within_r2": [fit["within_r2"]],
    "n": [fit["n_obs"]],
    "n_degenerate_provinces_check": [n_degenerate_provinces],
    "gbd_source_file": [RAW_PATH],
}).round(4)
results.to_csv(RESULTS_OUT, index=False)
print(f"\nSaved {RESULTS_OUT}")

# ─────────────────────────────────────────────────────────────────────────
# 7. FIGURE — placebo vs. primary asthma coefficient, side by side
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 5))
labels = ["Asthma\n(primary outcome)", f"{PRIMARY_CAUSE}\n(negative control)"]
betas = [REPORTED_ASTHMA_BETA, fit["beta"]]
ses = [REPORTED_ASTHMA_SE, fit["se"]]
colors = ["#2166ac", "#d6604d" if fit["p_value"] < 0.05 else "#4d9221"]
ax.errorbar(range(2), betas, yerr=[1.96 * s for s in ses], fmt="o", markersize=10,
            color="black", ecolor="gray", elinewidth=2, capsize=6)
for i, c in enumerate(colors):
    ax.scatter(i, betas[i], color=c, s=140, zorder=3)
ax.axhline(0, color="black", lw=1)
ax.set_xticks(range(2))
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("Two-way FE β (per 1 µg/m³ PM2.5)", fontsize=11)
ax.set_title(
    f"Placebo/Negative-Control Test\nAsthma (implicated outcome) vs. {PRIMARY_CAUSE} (no plausible PM2.5 pathway)\n"
    f"Points = β; bars = 95% CI (clustered SE)", fontsize=10.5)
plt.tight_layout()
plt.savefig(FIG_OUT, dpi=150)
plt.close()
print(f"Saved {FIG_OUT}")

print("\n── PLACEBO/NEGATIVE-CONTROL TEST COMPLETE ──")
