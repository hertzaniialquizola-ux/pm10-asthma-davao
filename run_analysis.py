import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from scipy import stats
from linearmodels.panel import PanelOLS
import warnings, os
warnings.filterwarnings("ignore")

os.makedirs("outputs/figures", exist_ok=True)
os.makedirs("outputs/tables",  exist_ok=True)

# ── 1. LOAD & MERGE ─────────────────────────────────────────────────────────
asthma = pd.read_csv("data/processed/asthma_regional_panel.csv")
pm25   = pd.read_csv("data/processed/pm25_regional_panel.csv")
panel  = asthma.merge(pm25, on=["region","year"], how="inner")
panel.to_csv("data/processed/panel_merged.csv", index=False)
print(f"Merged panel: {panel.shape}")
print(panel.head(10).to_string(index=False))

WHO_INTERIM_TARGET_3 = 15.0  # WHO 2021 Interim Target-3 for annual PM2.5 — an intermediate
                             # stepping-stone benchmark, NOT the primary guideline.
WHO_GUIDELINE_2021 = 5.0     # WHO 2021 annual PM2.5 guideline — the actual health-based standard.

panel["exceeds_who_it3"] = (panel["pm25"] > WHO_INTERIM_TARGET_3).astype(int)
print(f"\nRegion-years exceeding WHO Interim Target-3 (15 µg/m³): {panel['exceeds_who_it3'].sum()} / {len(panel)}")

panel["exceeds_who_guideline"] = (panel["pm25"] > WHO_GUIDELINE_2021).astype(int)
print(f"Region-years exceeding WHO's 2021 annual guideline ({WHO_GUIDELINE_2021} µg/m³): {panel['exceeds_who_guideline'].sum()} / {len(panel)}")

# ── 2. DESCRIPTIVE STATS ────────────────────────────────────────────────────
desc = panel[["asthma_rate_per100k","pm25"]].describe().round(2)
desc.to_csv("outputs/tables/descriptive_stats.csv")
print(f"\nDescriptive stats:\n{desc}")

# ── 3. PEARSON + SPEARMAN ───────────────────────────────────────────────────
r_p, p_p = stats.pearsonr(panel["pm25"], panel["asthma_rate_per100k"])
r_s, p_s = stats.spearmanr(panel["pm25"], panel["asthma_rate_per100k"])
print(f"\nPearson  r = {r_p:.3f}, p = {p_p:.4f}")
print(f"Spearman r = {r_s:.3f}, p = {p_s:.4f}")

# ── 4. TWO-WAY FIXED EFFECTS PANEL REGRESSION ───────────────────────────────
panel_fe = panel.copy()
panel_fe = panel_fe.set_index(["region","year"])
panel_fe["ln_asthma"] = np.log(panel_fe["asthma_rate_per100k"])
panel_fe["ln_pm25"]   = np.log(panel_fe["pm25"])

# Model A: levels
mod_a = PanelOLS.from_formula(
    "asthma_rate_per100k ~ pm25 + EntityEffects + TimeEffects",
    data=panel_fe)
res_a = mod_a.fit(cov_type="clustered", cluster_entity=True)

# Model B: log-log (elasticity)
mod_b = PanelOLS.from_formula(
    "ln_asthma ~ ln_pm25 + EntityEffects + TimeEffects",
    data=panel_fe)
res_b = mod_b.fit(cov_type="clustered", cluster_entity=True)

print("\n── Model A (levels, two-way FE) ──")
print(f"  β(pm25)  = {res_a.params['pm25']:.3f}")
print(f"  SE       = {res_a.std_errors['pm25']:.3f}")
print(f"  p-value  = {res_a.pvalues['pm25']:.4f}")
print(f"  R²(within)= {res_a.rsquared:.4f}")

print("\n── Model B (log-log, two-way FE) ──")
print(f"  β(ln_pm25) = {res_b.params['ln_pm25']:.3f}")
print(f"  SE         = {res_b.std_errors['ln_pm25']:.3f}")
print(f"  p-value    = {res_b.pvalues['ln_pm25']:.4f}")
print(f"  R²(within) = {res_b.rsquared:.4f}")

# Save results table
results_table = pd.DataFrame({
    "Model"     : ["A: Levels FE", "B: Log-Log FE"],
    "Beta"      : [res_a.params["pm25"], res_b.params["ln_pm25"]],
    "SE"        : [res_a.std_errors["pm25"], res_b.std_errors["ln_pm25"]],
    "p_value"   : [res_a.pvalues["pm25"], res_b.pvalues["ln_pm25"]],
    "R2_within" : [res_a.rsquared, res_b.rsquared],
}).round(4)
results_table.to_csv("outputs/tables/regression_results.csv", index=False)
print(f"\nRegression results saved.")

# ── 4b. MULTI-OUTCOME ANALYSIS ──────────────────────────────────────────────
# Same two-way fixed-effects specification (PM2.5 predicting outcome, region +
# year effects, SEs clustered by region), looped across all 5 GBD outcomes:
# asthma, lung cancer incidence, LRI incidence, COPD prevalence, and
# respiratory mortality. Each outcome's regional panel was built by
# aggregate_gbd_provinces.py and merged with pm25_regional_panel.csv on
# region+year (see data/processed/<outcome>_pm25_merged.csv).
MULTI_OUTCOMES = {
    "asthma":                 "asthma_rate_per100k",
    "lung_cancer_incidence":  "lung_cancer_incidence_rate_per100k",
    "lri_incidence":          "lri_incidence_rate_per100k",
    "copd_prevalence":        "copd_prevalence_rate_per100k",
    "respiratory_mortality":  "respiratory_mortality_rate_per100k",
}

multi_rows = []
for outcome_name, value_col in MULTI_OUTCOMES.items():
    outcome_df = pd.read_csv(f"data/processed/{outcome_name}_regional_panel.csv")
    merged = outcome_df.merge(pm25, on=["region", "year"], how="inner")
    merged.to_csv(f"data/processed/{outcome_name}_pm25_merged.csv", index=False)

    m_fe = merged.set_index(["region", "year"])
    mod = PanelOLS.from_formula(
        f"{value_col} ~ pm25 + EntityEffects + TimeEffects",
        data=m_fe)
    res = mod.fit(cov_type="clustered", cluster_entity=True)

    multi_rows.append({
        "outcome":   outcome_name,
        "beta":      round(res.params["pm25"], 4),
        "se":        round(res.std_errors["pm25"], 4),
        "p_value":   round(res.pvalues["pm25"], 4),
        "within_r2": round(res.rsquared, 4),
        "n":         len(merged),
    })
    print(f"  [{outcome_name}] beta={multi_rows[-1]['beta']}, se={multi_rows[-1]['se']}, "
          f"p={multi_rows[-1]['p_value']}, within_R2={multi_rows[-1]['within_r2']}, n={multi_rows[-1]['n']}")

multi_results = pd.DataFrame(multi_rows)
multi_results.to_csv("outputs/tables/multi_outcome_results.csv", index=False)
print(f"\nMulti-outcome results saved to outputs/tables/multi_outcome_results.csv")

# ── 5. FIRST DIFFERENCES (robustness) ───────────────────────────────────────
fd = panel.sort_values(["region","year"]).copy()
fd["d_asthma"] = fd.groupby("region")["asthma_rate_per100k"].diff()
fd["d_pm25"]   = fd.groupby("region")["pm25"].diff()
fd = fd.dropna(subset=["d_asthma","d_pm25"])
r_fd, p_fd = stats.pearsonr(fd["d_pm25"], fd["d_asthma"])
print(f"\nFirst differences (robustness):")
print(f"  Pearson r = {r_fd:.3f}, p = {p_fd:.4f}, n = {len(fd)}")

# ── 6. FIGURES ───────────────────────────────────────────────────────────────
sns.set_style("whitegrid")
BLUE = "#2166ac"; RED = "#d6604d"; GRAY = "#aaaaaa"

# Figure 1: Scatter PM2.5 vs asthma with regression line
fig, ax = plt.subplots(figsize=(7,5))
ax.scatter(panel["pm25"], panel["asthma_rate_per100k"],
           alpha=0.5, color=BLUE, edgecolors="white", s=40)
m, b = np.polyfit(panel["pm25"], panel["asthma_rate_per100k"], 1)
xline = np.linspace(panel["pm25"].min(), panel["pm25"].max(), 100)
ax.plot(xline, m*xline+b, color=RED, lw=2)
ax.axvline(WHO_INTERIM_TARGET_3, color=GRAY, ls="--", lw=1.2, label="WHO Interim Target-3 (15 µg/m³)")
ax.set_xlabel("Annual Mean PM2.5 (µg/m³)", fontsize=12)
ax.set_ylabel("Asthma Prevalence (per 100,000)", fontsize=12)
ax.set_title(f"PM2.5 vs Pediatric Asthma Prevalence\nPhilippines Regions 2013–2022 (n=170)\nPearson r={r_p:.3f}, p={p_p:.3f}", fontsize=11)
ax.legend()
plt.tight_layout()
plt.savefig("outputs/figures/fig1_scatter.png", dpi=150)
plt.close()
print("Saved fig1_scatter.png")

# Figure 2: National trend lines
nat = panel.groupby("year")[["asthma_rate_per100k","pm25"]].mean().reset_index()
fig, ax1 = plt.subplots(figsize=(8,4))
ax2 = ax1.twinx()
ax1.plot(nat["year"], nat["asthma_rate_per100k"], color=BLUE, lw=2.5, marker="o", label="Asthma rate")
ax2.plot(nat["year"], nat["pm25"], color=RED, lw=2.5, marker="s", ls="--", label="PM2.5")
ax2.axhline(WHO_INTERIM_TARGET_3, color=GRAY, ls=":", lw=1.2, label="WHO Interim Target-3 (15 µg/m³)")
ax1.set_xlabel("Year"); ax1.set_ylabel("Asthma Rate (per 100k)", color=BLUE)
ax2.set_ylabel("PM2.5 (µg/m³)", color=RED)
ax1.set_title("National Annual Trends: Asthma Prevalence and PM2.5\nPhilippines 2013–2022")
lines1,labs1 = ax1.get_legend_handles_labels()
lines2,labs2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labs1+labs2, loc="upper left", fontsize=9)
ax1.xaxis.set_major_locator(ticker.MultipleLocator(1))
plt.tight_layout()
plt.savefig("outputs/figures/fig2_trends.png", dpi=150)
plt.close()
print("Saved fig2_trends.png")

# Figure 3: Regional PM2.5 bar chart with WHO Interim Target-3 line
reg_pm25 = panel.groupby("region")["pm25"].mean().sort_values(ascending=False)
colors = [RED if v > WHO_INTERIM_TARGET_3 else BLUE for v in reg_pm25]
fig, ax = plt.subplots(figsize=(10,5))
ax.bar(reg_pm25.index, reg_pm25.values, color=colors, edgecolor="white")
ax.axhline(WHO_INTERIM_TARGET_3, color=GRAY, ls="--", lw=1.5, label="WHO Interim Target-3 (15 µg/m³)")
ax.set_xlabel("Region"); ax.set_ylabel("Mean PM2.5 2013–2022 (µg/m³)")
ax.set_title("Mean Annual PM2.5 by Philippine Region (2013–2022)\nRed = exceeds WHO Interim Target-3 (15 µg/m³)")
ax.legend(); plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig("outputs/figures/fig3_regional_pm25.png", dpi=150)
plt.close()
print("Saved fig3_regional_pm25.png")

# Figure 4: Regional asthma heatmap
pivot = panel.pivot(index="region", columns="year", values="asthma_rate_per100k")
fig, ax = plt.subplots(figsize=(12,6))
sns.heatmap(pivot, cmap="YlOrRd", ax=ax, linewidths=0.3,
            cbar_kws={"label":"Asthma Rate per 100k"})
ax.set_title("Pediatric Asthma Prevalence (per 100,000) by Region and Year\nPhilippines 2013–2022")
ax.set_xlabel("Year"); ax.set_ylabel("Region")
plt.tight_layout()
plt.savefig("outputs/figures/fig4_heatmap.png", dpi=150)
plt.close()
print("Saved fig4_heatmap.png")

print("\n── ANALYSIS COMPLETE ──")
print(f"Outputs in outputs/figures/ and outputs/tables/")
