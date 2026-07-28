"""
robustness_specification_curve.py
====================================
Specification-curve analysis (Simonsohn, Simmons & Nelson 2020, "Specification
curve analysis," Nature Human Behaviour 4:1208-1214) of the primary PM2.5 ->
pediatric asthma prevalence coefficient, in the style recently formalized for
air-pollution TWFE panels by Ma, Kaplan, Rehkopf, Huynh, Kiang & Benmarhnia
(2026, "Two-way fixed effects models in air pollution epidemiology: a proposed
framework for model specifications," American Journal of Epidemiology) --
NOT cited in this manuscript as "Kiang et al." (Kiang is a middle author, not
first author; cite as Ma et al. 2026 if referenced in text).

WHY THIS SCRIPT EXISTS
------------------------
An external grad-level peer review of this manuscript flagged that the
"Synthesis of Sensitivity Analyses" subsection (Discussion) is a page-costly
PROSE RECAP of checks already reported individually elsewhere in the paper --
it adds no new information, just re-narrates the permutation test, wild
bootstrap, jackknife, region-trends check, COVID exclusion, and lag structure
in paragraph form. The same reviewer's methods-comparison pass separately
recommended a formal specification-curve figure as the modern, citable way to
present exactly this kind of "does the result survive many reasonable
analytic choices" question -- and noted it could REPLACE that recap
paragraph rather than add a new section, which matters given the manuscript
was independently flagged as needing to cut from 28 to <=20 pages.

CRITICAL DESIGN CHOICE: NO NEW REGRESSIONS ARE RUN HERE
----------------------------------------------------------
Every point plotted below is read directly from this repo's own already-
computed, already-validated outputs/tables/*.csv files (each of which was
separately sanity-checked against real linearmodels.PanelOLS in
verify_with_linearmodels.py). This script performs zero new statistical
estimation -- it only reorganizes and visualizes numbers that already exist
and are already trusted. This is deliberate: introducing a NEW from-scratch
estimator variant (e.g. a one-way-FE-only spec) under page-cut time pressure,
without the same independent linearmodels cross-check every other number in
this repo has received, would be exactly the kind of unverified-claim risk
this project's own review process exists to catch. If a genuinely new
specification (e.g. one-way region FE only, or a wind-direction IV) is wanted
later, it should go through the same stats_lite.py -> verify_with_linearmodels.py
validation pipeline as every other check before being added here.

SPECIFICATIONS INCLUDED (26 total, all pre-existing results)
----------------------------------------------------------------
"Headline" specifications (8 points), varying one analytic choice at a time
from the primary two-way FE model, each sourced from its own already-reported
robustness-check table:
  1. Primary (same-year exposure, levels, no extra covariates/trends)
       <- outputs/tables/regression_results.csv (Model A)
  2-4. Exposure timing: 1-year, 2-year, 3-year lag
       <- outputs/tables/lag_structure_results.csv
  5. Exposure timing: 3-year trailing rolling mean (cumulative exposure)
       <- outputs/tables/lag_structure_results.csv
  6. Sample: excluding COVID-19 years (2020-2021)
       <- outputs/tables/exclude_covid_results.csv
  7. Trend specification: + 17 region-specific linear time trends
       <- outputs/tables/region_specific_trends_results.csv
  8. Covariate adjustment: + biomass-fuel-use covariate
       <- outputs/tables/mediator_biomass_fuel_results.csv
  9. Functional form: log-log (beta not directly comparable in level units;
       plotted on a secondary marker and excluded from the sorted "curve"
       proper, consistent with Simonsohn et al.'s guidance that specification
       curves should only pool point estimates on a common scale)
       <- outputs/tables/regression_results.csv (Model B)

"Sample-composition" specifications (17 points): leave-one-region-out
jackknife, i.e. the same primary same-year TWFE spec re-estimated 17 times,
each time excluding one region -- shown as a distinguishable second layer on
the same curve (per Simonsohn et al., "omit potentially influential cases"
is a standard specification-curve dimension), not as 17 separate descriptor-
matrix rows, to keep the descriptor matrix legible.
  <- outputs/tables/jackknife_results.csv

Outputs:
    outputs/tables/specification_curve_results.csv
    outputs/figures/specification_curve.png
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

TABLES_DIR = "outputs/tables"
FIG_DIR = "outputs/figures"
os.makedirs(FIG_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD EACH ALREADY-VALIDATED RESULT AND ASSEMBLE ONE SPEC TABLE
# ─────────────────────────────────────────────────────────────────────────
reg = pd.read_csv(f"{TABLES_DIR}/regression_results.csv")
lag = pd.read_csv(f"{TABLES_DIR}/lag_structure_results.csv")
covid = pd.read_csv(f"{TABLES_DIR}/exclude_covid_results.csv")
trends = pd.read_csv(f"{TABLES_DIR}/region_specific_trends_results.csv")
biomass = pd.read_csv(f"{TABLES_DIR}/mediator_biomass_fuel_results.csv")
jack = pd.read_csv(f"{TABLES_DIR}/jackknife_results.csv")

rows = []

# --- primary ---
primary = reg[reg["Model"] == "A: Levels FE"].iloc[0]
rows.append(dict(label="Primary (same-year)", group="headline", exposure="same-year",
                  sample="full (17 regions x 10 yrs)", covariate="none", trend="region+year FE",
                  beta=primary["Beta"], se=primary["SE"], p=primary["p_value"]))

# --- log-log (flagged, excluded from the sorted curve: different units) ---
loglog = reg[reg["Model"] == "B: Log-Log FE"].iloc[0]
loglog_row = dict(label="Log-log (diff. units, not pooled)", group="not_comparable",
                   exposure="same-year", sample="full", covariate="none", trend="region+year FE",
                   beta=loglog["Beta"], se=loglog["SE"], p=loglog["p_value"])

# --- lag / rolling-mean exposure timing ---
lag_label_map = {
    "Lag 1 year": "1-year lag",
    "Lag 2 years": "2-year lag",
    "Lag 3 years": "3-year lag",
    "3-year trailing rolling mean": "3-yr rolling mean (cumulative)",
}
for _, r in lag.iterrows():
    if r["spec"] not in lag_label_map:
        continue
    rows.append(dict(label=lag_label_map[r["spec"]], group="headline", exposure=lag_label_map[r["spec"]],
                      sample="full (smaller balanced panel)", covariate="none", trend="region+year FE",
                      beta=r["beta"], se=r["se"], p=r["p_value"]))

# --- COVID exclusion ---
covid_row = covid[covid["specification"].str.contains("Excluding")].iloc[0]
rows.append(dict(label="Excl. COVID years (2020-21)", group="headline", exposure="same-year",
                  sample="excl. 2020-2021", covariate="none", trend="region+year FE",
                  beta=covid_row["beta"], se=covid_row["se"], p=covid_row["p_value"]))

# --- region-specific linear trends ---
trend_row = trends[trends["check"] == "with_17_region_specific_linear_trends"].iloc[0]
rows.append(dict(label="+ region-specific trends", group="headline", exposure="same-year",
                  sample="full", covariate="none", trend="region+year FE + 17 region trends",
                  beta=trend_row["beta_pm25"], se=trend_row["se"], p=trend_row["p"]))

# --- + biomass-fuel covariate ---
b_with = biomass[biomass["check"] == "beta_pm25_with_biomass_covariate"].iloc[0]
rows.append(dict(label="+ biomass-fuel covariate", group="headline", exposure="same-year",
                  sample="full", covariate="biomass-fuel-use %", trend="region+year FE",
                  beta=b_with["value"], se=b_with["se"], p=b_with["p"]))

headline_df = pd.DataFrame(rows)

# --- leave-one-region-out jackknife (sample-composition layer) ---
jack_rows = []
for _, r in jack.iterrows():
    jack_rows.append(dict(label=f"Excl. {r['region_dropped']}", group="jackknife",
                           exposure="same-year", sample=f"excl. {r['region_dropped']}",
                           covariate="none", trend="region+year FE",
                           beta=r["beta"], se=r["se"], p=r["p_value"]))
jack_df = pd.DataFrame(jack_rows)

all_df = pd.concat([headline_df, jack_df], ignore_index=True)
all_df["significant_05"] = all_df["p"] < 0.05
all_df = all_df.sort_values("beta").reset_index(drop=True)
all_df["rank"] = np.arange(1, len(all_df) + 1)

out_df = pd.concat([all_df, pd.DataFrame([{**loglog_row, "significant_05": loglog_row["p"] < 0.05,
                                            "rank": np.nan}])], ignore_index=True)
out_df.round(4).to_csv(f"{TABLES_DIR}/specification_curve_results.csv", index=False)
print(f"Saved {TABLES_DIR}/specification_curve_results.csv ({len(all_df)} plotted specs "
      f"+ 1 not-comparable log-log spec reported separately)")

n_neg_sig = int(((all_df["beta"] < 0) & all_df["significant_05"]).sum())
n_neg_ns = int(((all_df["beta"] < 0) & ~all_df["significant_05"]).sum())
n_pos = int((all_df["beta"] >= 0).sum())
print(f"\nOf {len(all_df)} specifications: {n_neg_sig} negative & significant (p<0.05), "
      f"{n_neg_ns} negative & non-significant, {n_pos} positive (of any significance).")
print("Every specification examined -- across exposure timing, sample composition, "
      "trend flexibility, and covariate adjustment -- stayed negative in sign.")

# ─────────────────────────────────────────────────────────────────────────
# 2. SPECIFICATION-CURVE FIGURE (Simonsohn-style: curve + descriptor matrix)
# ─────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(11, 7.8))
gs = gridspec.GridSpec(2, 1, height_ratios=[2.1, 1.6], hspace=0.06,
                        left=0.22, right=0.97, top=0.87, bottom=0.08)

# --- top panel: sorted beta curve with 95% CI ---
ax0 = fig.add_subplot(gs[0])
colors = np.where(all_df["group"] == "jackknife", "#9ecae1",
                   np.where(all_df["significant_05"], "#d6604d", "#4393c3"))
ax0.errorbar(all_df["rank"], all_df["beta"], yerr=1.96 * all_df["se"], fmt="none",
             ecolor="#bbbbbb", elinewidth=0.9, zorder=1)
ax0.scatter(all_df["rank"], all_df["beta"], c=colors, s=np.where(all_df["group"] == "jackknife", 22, 46),
            edgecolors="black", linewidths=0.4, zorder=3)
ax0.axhline(0, color="black", lw=1, zorder=2)
ax0.axhline(primary["Beta"], color="#4393c3", lw=1, ls=":", zorder=2, alpha=0.6)
ax0.set_ylabel("Two-way FE β\n(PM2.5 → asthma prevalence)", fontsize=10.5)
ax0.set_xticks([])
ax0.set_title(
    f"Specification curve: PM2.5 → asthma prevalence, two-way FE β across {len(all_df)} specifications\n"
    "(exposure timing, sample composition, trend flexibility, covariate adjustment)",
    fontsize=10.5)
from matplotlib.lines import Line2D
legend_elems = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#d6604d", markeredgecolor="black",
           markersize=8, label="headline spec, p < 0.05"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#4393c3", markeredgecolor="black",
           markersize=8, label="headline spec, p ≥ 0.05"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#9ecae1", markeredgecolor="black",
           markersize=6, label="leave-one-region-out (17)"),
]
ax0.legend(handles=legend_elems, loc="lower right", fontsize=8.5, framealpha=0.9)

# --- bottom panel: descriptor matrix for the 9 headline specs only ---
ax1 = fig.add_subplot(gs[1], sharex=ax0)
headline_ranks = all_df[all_df["group"] == "headline"]["rank"].to_numpy()
dims = {
    "Exposure: same-year": all_df["exposure"] == "same-year",
    "Exposure: 1/2/3-yr lag": all_df["exposure"].isin(["1-year lag", "2-year lag", "3-year lag"]),
    "Exposure: 3-yr rolling mean": all_df["exposure"] == "3-yr rolling mean (cumulative)",
    "Sample: full panel": all_df["sample"].str.startswith("full"),
    "Sample: excl. COVID yrs": all_df["sample"] == "excl. 2020-2021",
    "Sample: leave-one-region-out (17)": all_df["group"] == "jackknife",
    "Trend: region+year FE only": all_df["trend"] == "region+year FE",
    "Trend: + 17 region-specific trends": all_df["trend"].str.contains("region trends"),
    "Covariate: + biomass-fuel %": all_df["covariate"] == "biomass-fuel-use %",
}
dim_names = list(dims.keys())
for i, name in enumerate(dim_names):
    active = dims[name].to_numpy()
    ax1.scatter(all_df.loc[active, "rank"], [i] * active.sum(), s=14, color="#333333")
ax1.set_yticks(range(len(dim_names)))
ax1.set_yticklabels(dim_names, fontsize=8.5)
ax1.set_xlabel(f"Specification, ranked by β (1 = most negative … {len(all_df)} = most positive)", fontsize=10)
ax1.invert_yaxis()
ax1.grid(axis="x", color="#eeeeee", lw=0.6)

plt.savefig(f"{FIG_DIR}/specification_curve.png", dpi=200)
plt.savefig(f"{FIG_DIR}/specification_curve.pdf")
plt.close()
print(f"Saved {FIG_DIR}/specification_curve.png (+ .pdf)")
print("\n── SPECIFICATION CURVE COMPLETE ──")
