"""
robustness_mde.py
===================
Robustness upgrade #7 (of 10 requested this session, "if time allows"):
minimum detectable effect (MDE) calculation from the primary model's
existing clustered SE, turning the manuscript's qualitative "this study is
likely underpowered to detect a small true effect" framing (implicit in
the low within-R^2 discussion) into a stated number.

Context
-------
Primary result (data/processed/asthma_pm25_merged.csv, n=170,
outputs/tables/regression_results.csv, "A: Levels FE"):
    beta = -2.5541, SE = 0.8247, df ≈ 143 (two-way FE residual df; see
    scripts/stats_lite.py, validated to reproduce the reported p=0.0024)

Standard MDE formula (two-sided test, given alpha and target power 1-beta):
    MDE = (t_{1-alpha/2, df} + t_{power, df}) * SE

This says: "given this study's actual sample size, panel structure, and
residual variance (all baked into SE=0.8247), the smallest true beta this
design could detect with probability = power, at significance level alpha,
is MDE." Anything smaller than MDE could be genuinely present in the
population and this study would very plausibly fail to detect it -- this
is the standard, honest way to state "underpowered" as a number instead of
a qualitative caveat.

We report MDE at the conventional alpha=0.05 / power=0.80 combination, and
also show alpha=0.05/power=0.90 and alpha=0.10/power=0.80 for context.

t-critical and t-power values come from scripts/stats_lite.py's
t_ppf_one_sided() (bisection on the same t_sf_twosided() already validated
against the repo's reported p=0.0024).

Outputs:
    outputs/tables/mde_results.csv
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_lite import fe_fit, t_ppf_one_sided

DATA_PATH = "data/processed/asthma_pm25_merged.csv"
OUT_CSV = "outputs/tables/mde_results.csv"
REPORTED_BETA = -2.5541
REPORTED_SE = 0.8247

os.makedirs("outputs/tables", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA & SANITY-CHECK
# ─────────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
fit = fe_fit(df, "region", "year", "pm25", "asthma_rate_per100k")
print(f"beta = {fit['beta']:.4f}  (reported: {REPORTED_BETA})")
print(f"SE   = {fit['se']:.4f}  (reported: {REPORTED_SE})")
print(f"df_t (two-way FE residual df) = {fit['df_t']}")
assert round(fit["beta"], 3) == round(REPORTED_BETA, 3), "beta mismatch -- stopping."
assert round(fit["se"], 3) == round(REPORTED_SE, 3), "SE mismatch -- stopping."
print("Sanity check PASSED — proceeding to MDE calculation.\n")

SE = fit["se"]
DF = fit["df_t"]

# ─────────────────────────────────────────────────────────────────────────
# 2. MDE UNDER SEVERAL (alpha, power) COMBINATIONS
# ─────────────────────────────────────────────────────────────────────────
scenarios = [
    ("alpha=0.05, power=0.80 (conventional)", 0.05, 0.80),
    ("alpha=0.05, power=0.90", 0.05, 0.90),
    ("alpha=0.10, power=0.80", 0.10, 0.80),
]

rows = []
for label, alpha, power in scenarios:
    t_alpha = t_ppf_one_sided(alpha / 2.0, DF)
    t_power = t_ppf_one_sided(1.0 - power, DF)
    mde = (t_alpha + t_power) * SE
    rows.append({
        "scenario": label, "alpha": alpha, "power": power, "df": DF,
        "t_critical_alpha": t_alpha, "t_critical_power": t_power,
        "se": SE, "mde": mde,
        "mde_as_pct_of_observed_beta": abs(mde / fit["beta"]) * 100,
    })
    print(f"{label}: t_alpha={t_alpha:.4f}, t_power={t_power:.4f}, "
          f"MDE = {mde:.4f} (per 100,000 asthma rate per 1 ug/m3 PM2.5)")
    print(f"   -> {abs(mde/fit['beta'])*100:.1f}% of the actually-observed |beta|={abs(fit['beta']):.4f}")

results = pd.DataFrame(rows).round(4)
results.to_csv(OUT_CSV, index=False)
print(f"\nSaved {OUT_CSV}")

# ─────────────────────────────────────────────────────────────────────────
# 3. PLAIN-LANGUAGE INTERPRETATION (printed for the write-up, not saved)
# ─────────────────────────────────────────────────────────────────────────
main = results.iloc[0]
print(f"\nPlain-language: at alpha=0.05 and 80% power, this design (17 regions x 10 years, "
      f"n=170, clustered SE=0.8247) can only reliably detect a true |beta| >= {main['mde']:.2f} "
      f"(asthma cases per 100,000 per 1 ug/m3 PM2.5). The observed |beta|={abs(fit['beta']):.2f} is "
      f"itself only {main['mde_as_pct_of_observed_beta']:.0f}% of that threshold's... "
      f"[note: since observed beta already cleared the threshold and was significant, phrase this "
      f"as: a TRUE effect smaller than {main['mde']:.2f} could very plausibly go undetected by this design]")

print("\n── MDE CALCULATION COMPLETE ──")
