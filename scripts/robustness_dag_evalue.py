"""
robustness_dag_evalue.py
==========================
Robustness upgrade #8 (of 10 requested this session, "if time allows"):
(a) a confounding DAG figure matching the manuscript's actual variables and
    argument, and (b) an E-value for the pooled cross-sectional correlation
    (r = +0.887), explicitly flagged as an approximation.

Part A: DAG
-----------
No confounding_dag.svg or similar file was found anywhere in this repo (a
full search of the repo tree, including archive/, turned up nothing) --
the task description assumed one had been attached/already present, but it
was not, so this builds one from scratch to match the manuscript's own,
already-written confounding argument (Discussion, "The Between-Region
Confounding Problem" and "Why Asthma Prevalence Is the Wrong Outcome
Variable" subsections) rather than a generic DAG template:
  - Region (time-invariant: urbanization, healthcare infrastructure,
    diagnostic capacity) -> both PM2.5 and Asthma prevalence. This is the
    confounding path the manuscript identifies as dominating the pooled
    r=+0.887. It is BLOCKED by region fixed effects (alpha_i).
  - Year (shared national trend) -> both PM2.5 and Asthma prevalence.
    BLOCKED by year fixed effects (gamma_t).
  - PM2.5 -> Asthma prevalence: the path of interest, estimated by the
    two-way FE model as beta=-2.554 once the two paths above are blocked.
  - Residual, region-year-varying unobserved confounders (e.g. local
    healthcare-access changes, smoking prevalence, socioeconomic shifts
    within a region over time) -> both PM2.5 and Asthma. This path is
    explicitly named in the manuscript's existing Limitations section
    ("No confounders beyond region and year effects were included;
    residual confounding from healthcare access, smoking, and
    socioeconomic factors may remain") and is NOT blocked by the two-way
    FE design -- drawn as the one open/unresolved path.

Saved as a matplotlib figure (not a hand-written SVG) so it can be embedded
in the Word manuscript the same way Figures 1-6 already are.

Part B: E-value (approximation, not a bound)
---------------------------------------------
The E-value (VanderWeele & Ding, 2017, Annals of Internal Medicine) is
defined for a risk ratio: the minimum strength of association, on the risk
ratio scale, that an unmeasured confounder would need to have with both
the exposure and the outcome to fully explain away an observed
exposure-outcome association, given the measured covariates. It is not
natively defined for a Pearson correlation coefficient.

CORRECTED 2026-07-16: the first version of this script chained
r -> Cohen's d (point-biserial conversion, treating r as if it came from
comparing two discrete groups) -> odds ratio (using an exp(1.81*d)
constant) -> "rare-outcome" RR~=OR approximation -> E-value, and produced
an absurd E-value (~2,093). Cross-checked against a known worked example
(r=0.887 should give E-value on the order of ~4) and found wrong for
three compounding reasons: (a) the point-biserial d formula is the wrong
conversion for a continuous-continuous correlation like PM2.5 vs. asthma
prevalence -- nothing here is a two-group comparison; (b) the "1.81"
constant does not appear in VanderWeele & Ding (2017) at all, it was
misremembered from an unrelated logistic-regression conversion; (c) the
"rare outcome" RR~OR step, already flagged as a poor fit in the original
docstring, added further distortion on top of (a) and (b).

The corrected approach uses VanderWeele & Ding (2017)'s own stated
formula for a continuous, standardized effect size d (their Table 2):
    RR ~= exp(0.91 * d)
For a bivariate relationship between two continuous, standardized
variables, the standardized regression coefficient IS the Pearson
correlation r itself (beta_standardized = r in simple linear regression),
so d = r directly here -- no point-biserial conversion, no odds-ratio
intermediary, no rare-outcome assumption needed. This removes two of the
three error sources above, not just the wrong constant:

    r (Pearson, already a standardized bivariate slope) = 0.887
    RR ~= exp(0.91 * r)                 [VanderWeele & Ding 2017, Table 2]
    E-value = RR + sqrt(RR * (RR - 1))  [VanderWeele & Ding 2017, main formula]

This is still an approximation -- VanderWeele & Ding note this conversion
has "modest" error for typical effect sizes and more for very large ones,
and r=0.887 is a very large one -- and is computed on the POOLED
r=+0.887 (the between-region-confounded correlation), not on the
FE-adjusted null result, which has no correlation coefficient to convert
(beta=-2.554 is already a regression coefficient in the outcome's natural
units, not a standardized r). The E-value is best read as "how strong
would a confounder need to be to produce the *pooled* association on its
own," which is directly informative given the manuscript's own claim that
region-level confounding (urbanization, diagnostic capacity) explains that
pooled association -- see the interpretation note printed at the end.

Outputs:
    outputs/figures/fig7_confounding_dag.png (+ .pdf)
    outputs/tables/evalue_results.csv
"""

import os
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

os.makedirs("outputs/figures", exist_ok=True)
os.makedirs("outputs/tables", exist_ok=True)

POOLED_R = 0.887

# ─────────────────────────────────────────────────────────────────────────
# PART A: DAG FIGURE
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 6.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 8)
ax.axis("off")

BLUE = "#2166ac"
RED = "#d6604d"
GRAY = "#888888"
BLACK = "#222222"

def node(x, y, w, h, label, fc="white", ec=BLACK, fontsize=10, fontweight="normal"):
    box = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                          boxstyle="round,pad=0.08,rounding_size=0.08",
                          linewidth=1.6, edgecolor=ec, facecolor=fc, zorder=3)
    ax.add_patch(box)
    ax.text(x, y, label, ha="center", va="center", fontsize=fontsize,
            fontweight=fontweight, zorder=4, wrap=True)
    return (x, y, w, h)


def arrow(n1, n2, color=BLACK, style="-", lw=1.8, label=None, label_offset=(0, 0.25), curve=0.0):
    x1, y1, w1, h1 = n1
    x2, y2, w2, h2 = n2
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy)
    ux, uy = dx / dist, dy / dist
    start = (x1 + ux * (w1 / 2 + 0.05) * 1.3, y1 + uy * (h1 / 2 + 0.05) * 1.3)
    end = (x2 - ux * (w2 / 2 + 0.08) * 1.3, y2 - uy * (h2 / 2 + 0.08) * 1.3)
    patch = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16,
                             linewidth=lw, color=color, linestyle=style,
                             connectionstyle=f"arc3,rad={curve}", zorder=2)
    ax.add_patch(patch)
    if label:
        mx, my = (start[0] + end[0]) / 2 + label_offset[0], (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=8.5, color=color, zorder=5,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))


# Nodes
region = node(1.6, 6.3, 2.6, 1.15,
              "REGION\n(time-invariant: urbanization,\nhealthcare infra, diagnostic capacity)",
              fc="#dbe9f6", fontsize=8.3)
year = node(1.6, 1.7, 2.6, 1.15,
            "YEAR\n(shared national trend)",
            fc="#dbe9f6", fontsize=9)
pm25 = node(5.0, 4.0, 1.9, 1.0, "PM2.5\n(exposure)", fc="white", fontsize=10, fontweight="bold")
asthma = node(8.6, 4.0, 2.4, 1.0, "Pediatric asthma\nprevalence (outcome)", fc="white", fontsize=10, fontweight="bold")
unobs = node(5.0, 7.2, 3.6, 1.0,
             "Unobserved region x year confounders\n(e.g. local healthcare access, smoking,\nsocioeconomic shifts within a region)",
             fc="#fbe3e0", fontsize=8, ec=RED)

# Blocked paths (region, year -> pm25 and asthma), drawn gray/dashed with an "X"
arrow(region, pm25, color=GRAY, style="--", lw=1.4, label="blocked by\nregion FE (α_i)", label_offset=(-0.3, 0.5))
arrow(region, asthma, color=GRAY, style="--", lw=1.4, curve=-0.25)
arrow(year, pm25, color=GRAY, style="--", lw=1.4, curve=0.2)
arrow(year, asthma, color=GRAY, style="--", lw=1.4, label="blocked by\nyear FE (γ_t)", label_offset=(0.3, -0.5))

# Open/unresolved path (unobserved confounders), drawn red/solid
arrow(unobs, pm25, color=RED, style="-", lw=1.8, curve=-0.15)
arrow(unobs, asthma, color=RED, style="-", lw=1.8, curve=0.15)

# Path of interest: PM2.5 -> asthma
arrow(pm25, asthma, color=BLUE, style="-", lw=2.6,
      label="β = −2.554, p = 0.0024\n(within-region, after FE)", label_offset=(0, 0.55))

# Legend
ax.text(0.2, 0.55, "— blue solid: path of interest (two-way FE estimate)", fontsize=8.5, color=BLUE)
ax.text(0.2, 0.15, "- - gray dashed: confounding path CLOSED by region/year fixed effects", fontsize=8.5, color=GRAY)
legend_red_y = 0.35
ax.text(5.3, 0.55, "— red solid: confounding path NOT closed by this design\n(named in Limitations: healthcare access, smoking, SES)",
        fontsize=8.5, color=RED)

ax.set_title(
    "Confounding structure of the PM2.5 -> pediatric asthma prevalence association\n"
    "(matches manuscript Discussion: \"The Between-Region Confounding Problem\")",
    fontsize=11, pad=10)

plt.tight_layout()
plt.savefig("outputs/figures/fig7_confounding_dag.png", dpi=300)
plt.savefig("outputs/figures/fig7_confounding_dag.pdf")
plt.close()
print("Saved outputs/figures/fig7_confounding_dag.png (+ .pdf)")

# ─────────────────────────────────────────────────────────────────────────
# PART B: E-VALUE (VanderWeele & Ding 2017, Table 2 continuous-outcome
# approximation -- corrected 2026-07-16, see docstring above for what was
# wrong with the original version and why)
# ─────────────────────────────────────────────────────────────────────────
r = POOLED_R
d = r  # standardized bivariate slope = Pearson r for a simple linear relationship; no
        # point-biserial conversion, because nothing here is a two-group comparison
RR = math.exp(0.91 * d)  # VanderWeele & Ding (2017), Table 2: RR ~= exp(0.91*d)
if RR >= 1:
    evalue = RR + math.sqrt(RR * (RR - 1))
else:
    RR_inv = 1 / RR
    evalue = RR_inv + math.sqrt(RR_inv * (RR_inv - 1))

print(f"\nPooled Pearson r = {r}")
print(f"  -> standardized effect size d (= r directly, bivariate case) = {d:.4f}")
print(f"  -> approx RR = exp(0.91*d) [VanderWeele & Ding 2017, Table 2] = {RR:.4f}")
print(f"  -> E-value (VanderWeele & Ding 2017) = {evalue:.2f}")

evalue_table = pd.DataFrame({
    "quantity": ["pooled_pearson_r", "standardized_effect_size_d", "risk_ratio_approx", "e_value_approx"],
    "value": [r, d, RR, evalue],
    "caveat": [
        "n/a",
        "d = r directly (standardized bivariate slope), NOT a point-biserial conversion -- "
        "corrected 2026-07-16, see script docstring",
        "VanderWeele & Ding (2017) Table 2 approximation RR~=exp(0.91*d); the paper notes "
        "modest error for typical effect sizes, more for very large ones (r=0.887 is very large)",
        "APPROXIMATION ONLY, not a precise bound -- computed on the pooled/confounded r=+0.887, "
        "not on the FE-adjusted null result (which has no correlation coefficient to convert)",
    ],
})
evalue_table.to_csv("outputs/tables/evalue_results.csv", index=False)
print("Saved outputs/tables/evalue_results.csv")

print("\nInterpretation note (for the manuscript, not a claim of precision):")
print(f"  An E-value of {evalue:.1f} means an unmeasured confounder would need to be associated")
print(f"  with both PM2.5 and asthma prevalence by a risk ratio of at least ~{evalue:.1f}, above and")
print("  beyond region and year, to fully explain away the POOLED r=+0.887 association. This is a")
print("  substantial but not extreme bar. It is consistent with -- not contradictory to -- the")
print("  manuscript's own argument: region-level confounding (urbanization, diagnostic capacity) is")
print("  independently identified and adjusted for via fixed effects, which is exactly why the pooled")
print("  association collapses under the FE model. The E-value should not be read as evidence FOR a")
print("  causal PM2.5 effect.")

print("\n── DAG + E-VALUE COMPLETE ──")
