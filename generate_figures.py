
#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

generate_figures.py

====================================================================

Publication-quality figures for:

    "PM2.5 Air Pollution and Pediatric Asthma Prevalence in the

     Philippines (2013-2022): A Subnational Panel Analysis with

     Davao City as a Grounding Case Study"

Produces five figures, each saved as 300-dpi PNG and vector PDF in

outputs/figures/:

    Fig 1  fig1_scatter                    PM2.5 vs asthma scatter (n=170)

    Fig 2  fig2_trends                     National dual-axis annual trends

    Fig 3  fig3_regional_pm25              Regional mean PM2.5 bar chart

    Fig 4  fig4_heatmap                    Asthma rate by region x year

    Fig 5  fig5_within_region_correlations Within-region r dot/forest plot

Input

-----

    data/processed/panel_merged.csv

    columns: region, year, asthma_rate_per100k, pm25   (170 rows)

Notes

-----

* Pure matplotlib (no seaborn dependency) so the script runs anywhere;

  top/right spines are removed manually to match a despined look.

* Fonts request Arial/Helvetica and fall back to DejaVu Sans if those

  are not installed on the host.

* Statistical labels (pooled r, fixed-effects beta, first-differences r)

  are taken from run_analysis.py and reproduced on the figures.

No network/API calls. Reads one CSV from disk.

====================================================================

"""

import os

import numpy as np

import pandas as pd

import matplotlib

matplotlib.use("Agg")  # safe headless backend

import matplotlib.pyplot as plt

from matplotlib.patches import Rectangle

from matplotlib.lines import Line2D

# --------------------------------------------------------------------------

# Paths

# --------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

PANEL = os.path.join(REPO_ROOT, "data", "processed", "panel_merged.csv")

FIG_DIR = os.path.join(REPO_ROOT, "outputs", "figures")

os.makedirs(FIG_DIR, exist_ok=True)

# --------------------------------------------------------------------------

# Design system (colorblind-friendly)

# --------------------------------------------------------------------------

BLUE = "#2166ac"

RED = "#d6604d"

GRAY = "#636363"

LIGHT = "#f7f7f7"

WHO = 15.0  # WHO annual PM2.5 guideline, ug/m3

# Pre-computed statistics from run_analysis.py (reproduced as on-figure labels)

STAT_PEARSON = 0.887

STAT_SPEARMAN = 0.583

STAT_FE_BETA = -2.554

STAT_FD_R = 0.199

plt.rcParams.update({

    "font.family": "sans-serif",

    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],

    "font.size": 11,

    "axes.titlesize": 13,

    "axes.labelsize": 11,

    "xtick.labelsize": 9,

    "ytick.labelsize": 9,

    "axes.edgecolor": "#444444",

    "axes.linewidth": 0.8,

    "figure.facecolor": "white",

    "axes.facecolor": "white",

    "savefig.facecolor": "white",

})

# --------------------------------------------------------------------------

# Small helpers

# --------------------------------------------------------------------------

def despine(ax):

    """Remove top and right spines (seaborn-despine look) and add a faint grid."""

    ax.spines["top"].set_visible(False)

    ax.spines["right"].set_visible(False)

    ax.grid(alpha=0.3, linewidth=0.6)

    ax.set_axisbelow(True)

def desaturate(hex_color, keep=0.45):

    """Blend a color toward medium gray to make a 'muted' version (keep in [0,1])."""

    rgb = np.array(matplotlib.colors.to_rgb(hex_color))

    gray = np.array([0.6, 0.6, 0.6])

    return tuple(keep * rgb + (1 - keep) * gray)

def save(fig, stem):

    """Save a figure as both 300-dpi PNG and vector PDF; print a confirmation."""

    png = os.path.join(FIG_DIR, stem + ".png")

    pdf = os.path.join(FIG_DIR, stem + ".pdf")

    fig.savefig(png, dpi=300, bbox_inches="tight")

    fig.savefig(pdf, bbox_inches="tight")

    plt.close(fig)

    rel = os.path.relpath(FIG_DIR, REPO_ROOT)

    print(f"  saved: {rel}/{stem}.png  and  {rel}/{stem}.pdf")

def titles(ax, title, subtitle):

    """Two-line self-contained heading: bold title + smaller gray subtitle."""

    ax.set_title(subtitle, fontsize=10, color=GRAY, loc="left", pad=6)

    ax.figure.suptitle(title, fontsize=14, fontweight="bold", x=0.5, y=1.0,

                       ha="center")

def pearson(x, y):

    x = np.asarray(x, float); y = np.asarray(y, float)

    return np.corrcoef(x, y)[0, 1]

# --------------------------------------------------------------------------

# Load + derive shared tables

# --------------------------------------------------------------------------

df = pd.read_csv(PANEL)

df = df.sort_values(["region", "year"]).reset_index(drop=True)

# Regional summary: mean PM2.5, mean asthma, WHO exceedance count (years > 15).

reg = (df.assign(exceed=df["pm25"] > WHO)

         .groupby("region")

         .agg(pm25=("pm25", "mean"),

              asthma=("asthma_rate_per100k", "mean"),

              exceed=("exceed", "sum"))

         .reset_index())

reg = reg.sort_values("pm25", ascending=False).reset_index(drop=True)

REGION_ORDER = reg["region"].tolist()  # high -> low PM2.5 (NCR first)

# National per-year means across the 17 regions.

nat = (df.groupby("year")

         .agg(asthma_mean=("asthma_rate_per100k", "mean"),

              pm25_mean=("pm25", "mean"),

              pm25_sd=("pm25", "std"))

         .reset_index())

# ==========================================================================

# FIGURE 1 — Scatter: PM2.5 vs pediatric asthma prevalence (n = 170)

# Caption: Annual mean PM2.5 versus pediatric asthma prevalence for all 170

# region-years. NCR (labeled) forms the high-pollution, high-prevalence

# outlier cluster. Line is the pooled OLS fit; the dashed line marks the WHO

# 15 ug/m3 annual guideline. The pooled correlation reflects between-region

# variation and is not a within-region causal estimate (see fixed effects).

# ==========================================================================

def figure1():

    fig, ax = plt.subplots(figsize=(7, 6))

    # Muted per-region colors so the plot is not a loud rainbow.

    base_cycle = plt.cm.tab20(np.linspace(0, 1, 20))

    region_color = {r: desaturate(matplotlib.colors.to_hex(base_cycle[i % 20]))

                    for i, r in enumerate(sorted(df["region"].unique()))}

    for r in sorted(df["region"].unique()):

        if r == "NCR":

            continue

        sub = df[df["region"] == r]

        ax.scatter(sub["pm25"], sub["asthma_rate_per100k"], s=30,

                   color=region_color[r], alpha=0.65, edgecolor="white",

                   linewidth=0.4, zorder=2)

    # NCR highlighted and year-labeled.

    ncr = df[df["region"] == "NCR"].sort_values("year")

    ax.scatter(ncr["pm25"], ncr["asthma_rate_per100k"], s=55, color=RED,

               edgecolor="black", linewidth=0.6, zorder=4, label="NCR")

    for _, row in ncr.iterrows():

        ax.annotate(str(int(row["year"])),

                    (row["pm25"], row["asthma_rate_per100k"]),

                    fontsize=7, color="#7a1f14", xytext=(4, 3),

                    textcoords="offset points", zorder=5)

    # Pooled OLS fit through all 170 points.

    x = df["pm25"].values; y = df["asthma_rate_per100k"].values

    b1, b0 = np.polyfit(x, y, 1)

    xs = np.linspace(x.min(), x.max(), 100)

    ax.plot(xs, b0 + b1 * xs, color="black", lw=1.6, zorder=3,

            label="Pooled OLS fit")

    # WHO threshold.

    ax.axvline(WHO, color=GRAY, ls="--", lw=1.2, zorder=1)

    ax.text(WHO + 0.2, ax.get_ylim()[1] * 0.5 + y.min() * 0.5,

            "WHO 15 µg/m³", rotation=90, va="center", ha="left",

            fontsize=9, color=GRAY)

    # Stats box (upper left).

    txt = (f"Pearson r = {STAT_PEARSON:.3f}, p < 0.001  |  "

           f"Spearman ρ = {STAT_SPEARMAN:.3f}, p < 0.001")

    ax.text(0.03, 0.97, txt, transform=ax.transAxes, fontsize=9, va="top",

            ha="left", bbox=dict(boxstyle="round,pad=0.4", fc=LIGHT,

                                 ec="#cccccc"))

    ax.text(0.03, 0.90,

            "Note: Raw correlation includes between-region variation.\n"

            "See Table 3 for fixed-effects estimates.",

            transform=ax.transAxes, fontsize=7.5, va="top", ha="left",

            color=GRAY)

    ax.set_xlabel("Annual Mean $PM_{2.5}$ (µg/m³)")

    ax.set_ylabel("Pediatric Asthma Prevalence (per 100,000), ages 5–14")

    ax.legend(loc="lower right", frameon=False, fontsize=9)

    despine(ax)

    titles(ax,

           "$PM_{2.5}$ and Pediatric Asthma Prevalence Across Philippine Region-Years",

           "Each point = one region-year (n = 170, 17 regions × 2013–2022); "

           "NCR points labeled by year")

    fig.tight_layout()

    save(fig, "fig1_scatter")

# ==========================================================================

# FIGURE 2 — National dual-axis annual trends

# Caption: National annual means (simple average across 17 regions) of

# pediatric asthma prevalence (left) and PM2.5 (right), 2013-2022. Shaded

# band shows +/-1 SD of regional PM2.5, indicating inter-regional spread.

# ==========================================================================

def figure2():

    fig, ax1 = plt.subplots(figsize=(9, 5))

    # Left axis: asthma (blue).

    l1, = ax1.plot(nat["year"], nat["asthma_mean"], "-o", color=BLUE, lw=2,

                   ms=6, label="Asthma prevalence (mean of regions)")

    ax1.set_xlabel("Year")

    ax1.set_ylabel("Pediatric Asthma Prevalence (per 100,000)", color=BLUE)

    ax1.tick_params(axis="y", labelcolor=BLUE)

    ax1.set_xticks(nat["year"])

    # Right axis: PM2.5 (red) with +/-1 SD band.

    ax2 = ax1.twinx()

    l2, = ax2.plot(nat["year"], nat["pm25_mean"], "-s", color=RED, lw=2,

                   ms=6, label="$PM_{2.5}$ (mean of regions)")

    band = ax2.fill_between(nat["year"],

                            nat["pm25_mean"] - nat["pm25_sd"],

                            nat["pm25_mean"] + nat["pm25_sd"],

                            color=RED, alpha=0.15,

                            label="±1 SD of regional $PM_{2.5}$")

    l3 = ax2.axhline(WHO, color=GRAY, ls="--", lw=1.2)

    ax2.text(nat["year"].max(), WHO + 0.15, "WHO 15 µg/m³", ha="right",

             va="bottom", fontsize=8.5, color=GRAY)

    ax2.set_ylabel("Annual Mean $PM_{2.5}$ (µg/m³)", color=RED)

    ax2.tick_params(axis="y", labelcolor=RED)

    # Combined legend inside the plot.

    handles = [l1, l2, band]

    labels = [h.get_label() for h in handles]

    ax1.legend(handles, labels, loc="upper center", frameon=False, fontsize=9,

               ncol=1)

    # Despine (twin axis keeps its right spine for the red ticks).

    ax1.spines["top"].set_visible(False)

    ax2.spines["top"].set_visible(False)

    ax1.grid(alpha=0.3, linewidth=0.6)

    ax1.set_axisbelow(True)

    titles(ax1,

           "National Annual Trends: $PM_{2.5}$ and Pediatric Asthma Prevalence, "

           "Philippines 2013–2022",

           "Lines show mean across 17 regions; shaded band = ±1 SD of regional $PM_{2.5}$")

    fig.tight_layout()

    save(fig, "fig2_trends")

# ==========================================================================

# FIGURE 3 — Regional mean PM2.5 with WHO threshold (horizontal bars)

# Caption: Region-level mean PM2.5 (2013-2022), sorted high to low. Bars

# above the WHO 15 ug/m3 guideline are red; values and the count of years

# exceeding the guideline are annotated at the bar end.

# ==========================================================================

def figure3():

    fig, ax = plt.subplots(figsize=(8, 7))

    order = reg.iloc[::-1].reset_index(drop=True)  # lowest at bottom for barh

    colors = [RED if v > WHO else BLUE for v in order["pm25"]]

    ypos = np.arange(len(order))

    ax.barh(ypos, order["pm25"], color=colors, edgecolor="white", height=0.72)

    ax.axvline(WHO, color=GRAY, ls="--", lw=1.3)

    ax.text(WHO, len(order) - 0.2, "WHO Annual Guideline (15 µg/m³)",

            rotation=90, va="top", ha="right", fontsize=8.5, color=GRAY)

    for i, row in order.iterrows():

        ax.text(row["pm25"] + 0.25, i,

                f"{row['pm25']:.2f}",

                va="center", ha="left", fontsize=9, fontweight="bold")

        ax.text(row["pm25"] + 1.9, i,

                f"({int(row['exceed'])}/10 yrs)",

                va="center", ha="left", fontsize=8, color=GRAY)

    ax.set_yticks(ypos)

    ax.set_yticklabels(order["region"])

    ax.set_xlabel("Mean Annual $PM_{2.5}$ (µg/m³)")

    ax.set_xlim(0, max(order["pm25"]) + 5)

    despine(ax)

    ax.grid(axis="y", visible=False)

    legend = [Line2D([0], [0], marker="s", color="w", markerfacecolor=RED,

                     markersize=10, label="Exceeds WHO guideline"),

              Line2D([0], [0], marker="s", color="w", markerfacecolor=BLUE,

                     markersize=10, label="At or below WHO guideline")]

    ax.legend(handles=legend, loc="lower right", frameon=False, fontsize=9)

    titles(ax,

           "Mean Annual $PM_{2.5}$ by Philippine Region (2013–2022)",

           "Red bars exceed WHO annual $PM_{2.5}$ guideline (15 µg/m³)")

    fig.tight_layout()

    save(fig, "fig3_regional_pm25")

# ==========================================================================

# FIGURE 4 — Heatmap: asthma prevalence by region x year

# Caption: Pediatric asthma prevalence (per 100,000) by region and year,

# regions ordered by mean PM2.5 (high to low). NCR is separated by a rule to

# flag its outlier magnitude.

# ==========================================================================

def figure4():

    mat = (df.pivot(index="region", columns="year",

                    values="asthma_rate_per100k")

             .reindex(REGION_ORDER))

    years = list(mat.columns)

    data = mat.values

    fig, ax = plt.subplots(figsize=(12, 7))

    im = ax.imshow(data, cmap="YlOrRd", aspect="auto")

    ax.set_xticks(np.arange(len(years)))

    ax.set_xticklabels(years)

    ax.set_yticks(np.arange(len(REGION_ORDER)))

    ax.set_yticklabels(REGION_ORDER)

    ax.set_xlabel("Year")

    # Annotate each cell; white text on dark cells, black on light.

    vmin, vmax = np.nanmin(data), np.nanmax(data)

    thresh = vmin + 0.6 * (vmax - vmin)

    for i in range(data.shape[0]):

        for j in range(data.shape[1]):

            val = data[i, j]

            ax.text(j, i, f"{val:,.0f}", ha="center", va="center",

                    fontsize=8,

                    color="white" if val > thresh else "black")

    # Thin separator rule beneath the NCR row (NCR is row 0 here).

    ax.axhline(0.5, color="#222222", lw=2)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)

    cbar.set_label("Asthma Prevalence (per 100,000)")

    ax.set_xticks(np.arange(-0.5, len(years), 1), minor=True)

    ax.set_yticks(np.arange(-0.5, len(REGION_ORDER), 1), minor=True)

    ax.grid(which="minor", color="white", linewidth=1.0)

    ax.tick_params(which="minor", length=0)

    titles(ax,

           "Pediatric Asthma Prevalence (per 100,000) by Region and Year",

           "Regions sorted by mean $PM_{2.5}$ (high to low). Ages 5–14, "

           "Philippines 2013–2022.")

    fig.tight_layout()

    save(fig, "fig4_heatmap")

# ==========================================================================

# FIGURE 5 — Within-region correlation dot/forest plot

# Caption: Within-region Pearson correlation between annual PM2.5 and

# pediatric asthma prevalence (10 years per region). Horizontal lines are

# approximate 95% CIs (r +/- 1.96*SE, SE = sqrt((1-r^2)/(n-2))). Reference

# lines mark the pooled (0.887) and first-differences (0.199) national r.

# ==========================================================================

def figure5():

    n = 10

    rows = []

    for r in df["region"].unique():

        sub = df[df["region"] == r]

        rr = pearson(sub["pm25"], sub["asthma_rate_per100k"])

        se = np.sqrt(max((1 - rr ** 2), 1e-9) / (n - 2))

        rows.append({"region": r, "r": rr,

                     "lo": max(-1, rr - 1.96 * se),

                     "hi": min(1, rr + 1.96 * se)})

    wr = pd.DataFrame(rows).sort_values("r").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(8, 6))

    ypos = np.arange(len(wr))

    for i, row in wr.iterrows():

        c = BLUE if row["r"] >= 0 else RED

        ax.plot([row["lo"], row["hi"]], [i, i], color=c, lw=1.4, alpha=0.7,

                zorder=2)

        ax.scatter(row["r"], i, color=c, s=45, zorder=3, edgecolor="white",

                   linewidth=0.5)

    ax.axvline(0, color="#222222", ls="--", lw=1.1, zorder=1)

    ax.axvline(STAT_PEARSON, color=GRAY, ls=":", lw=1.2)

    ax.text(STAT_PEARSON, len(wr) - 0.3, f"pooled r = {STAT_PEARSON:.3f}",

            rotation=90, va="top", ha="right", fontsize=8, color=GRAY)

    ax.axvline(STAT_FD_R, color=GRAY, ls=":", lw=1.2)

    ax.text(STAT_FD_R, len(wr) - 0.3, f"first-diff r = {STAT_FD_R:.3f}",

            rotation=90, va="top", ha="right", fontsize=8, color=GRAY)

    ax.set_yticks(ypos)

    ax.set_yticklabels(wr["region"])

    ax.set_xlabel("Within-region Pearson r ($PM_{2.5}$ vs asthma prevalence, 2013–2022)")

    ax.set_xlim(-1.05, 1.05)

    despine(ax)

    ax.grid(axis="y", visible=False)

    titles(ax,

           "Within-Region Correlation: $PM_{2.5}$ and Pediatric Asthma Prevalence "

           "(2013–2022)",

           "Each point = Pearson r over 10 years within that region; bars ≈ 95% CI. "

           "Reference lines: pooled (0.887) and first-differences (0.199) national r.")

    fig.tight_layout()

    save(fig, "fig5_within_region_correlations")

def main():

    print("Generating publication figures from", os.path.relpath(PANEL, REPO_ROOT))

    figure1()

    figure2()

    figure3()

    figure4()

    figure5()

    print("Done. All 5 figures saved to outputs/figures/ as PNG (300 dpi) + PDF.")

if __name__ == "__main__":

    main()

