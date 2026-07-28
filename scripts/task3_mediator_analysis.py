"""
task3_mediator_analysis.py
============================
Builds an indoor solid/biomass-fuel-use covariate for the 17-region,
2013-2022 panel from 3 NDHS survey rounds, and tests it as a mediator of
the PM2.5 -> pediatric asthma fixed-effects relationship (per the
feasibility memo in docs/mediator_feasibility_memo.md, which ranked
biomass-fuel-use the strongest of 4 candidate mediators).

DATA PROVENANCE -- every number below is transcribed directly from a
source PDF (page-checked), not estimated or fabricated by this script,
EXCEPT the 2013 regional values, which are a disclosed composite estimate
(see "2013" section below) built because no region-level breakdown exists
in the 2013 source at all.

────────────────────────────────────────────────────────────────────────
2022 (region-level, DIRECT — no aggregation needed)
────────────────────────────────────────────────────────────────────────
Source: data/raw/ndhs/FR381.pdf ("Philippines National Demographic and
Health Survey 2022 Final Report"), Table 2.4 "Primary reliance on clean
fuels and technologies", column "Primary reliance on solid fuels for
cooking" (its footnote 2 defines solid fuel as coal/lignite, charcoal,
wood, straw/shrubs/grass, agricultural crops, animal dung/waste,
processed biomass/pellets/woodchips, garbage/plastic, and sawdust --
FLAG: broader than "wood, charcoal, crop residue, animal dung" alone,
since it includes coal/lignite, processed pellets, garbage/plastic, and
sawdust. This is the NDHS's own standard definition; no equivalent
narrower breakdown is published, so it is used as-is with this caveat
disclosed everywhere the variable is used).

────────────────────────────────────────────────────────────────────────
2017 (province-level, AGGREGATED to region)
────────────────────────────────────────────────────────────────────────
Source: data/raw/ndhs/WP164.pdf (Wang et al. 2020, DHS Working Paper 164,
"Household Air Pollution: National and Subnational Trends..."), Appendix
Table A.9 "Province-level estimates of household use of solid fuel for
cooking, the Philippines NDHS 2017" -- 81 provinces. Aggregated to the
17-region panel using the SAME PROVINCE_TO_REGION mapping already used
throughout this project (aggregate_gbd_provinces.py, imported here, not
retyped), joining on province NAME rather than WP164's own "Region"
column, because WP164 uses an older region structure (ARMM instead of
BARMM, one undivided "Region IV (Southern Tagalog)" instead of the
current split IV-A/IV-B) that does not match this panel's 17-region
structure. A handful of WP164's own province-name spellings/orderings
differ from the project's canonical PROVINCE_TO_REGION keys (e.g.
"Tawi-tawi" vs "Tawi-Tawi", "Mindoro Occidental" vs "Occidental Mindoro",
"Saranggani" vs "Sarangani", "North Cotabato" vs "Cotabato (North
Cotabato)") and one province name is now defunct ("Shariff Kabunsuan",
created 2006, ruled unconstitutional and reverted to Maguindanao by the
Supreme Court in Sema v. COMELEC, 2008) -- all handled via an explicit
WP164_NAME_ALIAS dict below, checked to leave zero unmatched provinces.
Aggregation is an unweighted mean of provinces within each region (same
method aggregate_gbd_provinces.py already uses for the GBD outcome
panels, for consistency).

────────────────────────────────────────────────────────────────────────
2013 (NO region-level data exists in the source -- disclosed composite)
────────────────────────────────────────────────────────────────────────
data/raw/ndhs/FR294.pdf (2013 NDHS Final Report)'s own Table 2.4 reports
solid-fuel use ONLY by urban/rural residence (Urban 38.7%, Rural 81.1%,
National 60.8%) -- confirmed by reading the full 336-page report and
grepping it for any region-disaggregated fuel table; none exists. (The
2022 report's region-level breakdown is explicitly framed around SDG
indicator 7.1.2; the 2013 round predates the SDGs entirely, which is the
likely reason the earlier report wasn't published at that granularity.)

Per instruction, this gap is filled with a DISCLOSED COMPOSITE, not a
guess: each region's 2013 rate = (region's urban household share x 38.7%)
+ (region's rural household share x 81.1%), using each region's urban/
rural household split from FR294's own Appendix Table A.1 ("Households in
sampling frame", 2010 Census of Population and Housing -- the same census
that underlies the 2013 NDHS's sample design, so the urban/rural
definitions are internally consistent with the 38.7%/81.1% national
rates being combined here).

ASSUMPTION being made (stated, not hidden): that urban and rural
solid-fuel-use rates are roughly homogeneous ACROSS regions in 2013 --
i.e., that a region's overall rate is explained by its urban/rural
population mix alone, not by other regional factors. This is almost
certainly not exactly true and is flagged as a limitation everywhere this
2013 value is used downstream.

INTERNAL CONSISTENCY CHECK: reweighting the NATIONAL urban/rural
household split (46.7%/53.3%, also from Table A.1) through this same
formula recovers 61.3%, within 0.5 percentage points of the true reported
national rate (60.8%) -- i.e., the compositing method is accurate to
within about half a point when checked against a total the source report
actually publishes.

────────────────────────────────────────────────────────────────────────
INTERPOLATION
────────────────────────────────────────────────────────────────────────
2014-2016 and 2018-2021 are filled by LINEAR interpolation between the
bracketing real/composite anchors (2013-2017 and 2017-2022 respectively).
NO extrapolation beyond 2013 or 2022. This is a disclosed methodological
choice, not a data-quality workaround, per explicit instruction, and is
flagged in every output this script produces.

Outputs
-------
    data/processed/biomass_fuel_regional_panel.csv   (annual, 17x10, with
        a data_source column: "composite_2013", "real_2017", "real_2022",
        or "interpolated")
    data/processed/biomass_fuel_pm25_asthma_merged.csv (merged w/ pm25 +
        asthma_rate_per100k, for the mediation test)
    outputs/tables/mediator_biomass_fuel_results.csv (first-stage +
        second-stage results)
    outputs/figures/mediator_biomass_fuel_check.png (sanity-check /
        first-stage scatter + second-stage coefficient comparison)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stats_lite import fe_fit, fe_fit_multi
from aggregate_gbd_provinces import PROVINCE_TO_REGION

PANEL_REGIONS = [
    "NCR", "CAR", "Region I", "Region II", "Region III", "Region IV-A",
    "Region IV-B", "Region V", "Region VI", "Region VII", "Region VIII",
    "Region IX", "Region X", "Region XI", "Region XII", "Region XIII", "BARMM",
]
YEARS = list(range(2013, 2023))

# ─────────────────────────────────────────────────────────────────────────
# 1. 2013 — Table A.1 urban/rural household shares (FR294.pdf, p.214),
#    2010 CPH sampling frame, by region.  (Number: percent urban, percent
#    rural households.)  "ARMM" is this table's own label for what the
#    panel calls "BARMM"; "IVB - MIMAROPA" / "IVA - CALABARZON" match
#    Region IV-B / Region IV-A directly.
# ─────────────────────────────────────────────────────────────────────────
TABLE_A1_URBAN_RURAL_PCT = {
    "NCR":          (100.0, 0.0),
    "CAR":          (28.1, 71.9),
    "Region I":     (12.7, 87.3),
    "Region II":    (11.7, 88.3),
    "Region III":   (51.7, 48.3),
    "Region IV-A":  (60.6, 39.4),
    "Region IV-B":  (22.5, 77.5),
    "Region V":     (15.4, 84.6),
    "Region VI":    (35.2, 64.8),
    "Region VII":   (44.5, 55.5),
    "Region VIII":  (8.7, 91.3),
    "Region IX":    (34.1, 65.9),
    "Region X":     (42.0, 58.0),
    "Region XI":    (59.5, 40.5),
    "Region XII":   (46.6, 53.4),
    "Region XIII":  (27.7, 72.3),
    "BARMM":        (12.5, 87.5),
}
NATL_URBAN_PCT_2013 = 38.7   # FR294 Table 2.4, national urban solid-fuel rate
NATL_RURAL_PCT_2013 = 81.1   # FR294 Table 2.4, national rural solid-fuel rate
NATL_TOTAL_PCT_2013_REPORTED = 60.8  # FR294 Table 2.4, reported national total (for the consistency check)
NATL_URBAN_SHARE_2013 = 46.7  # FR294 Table A.1, national urban household %
NATL_RURAL_SHARE_2013 = 53.3  # FR294 Table A.1, national rural household %


def build_2013_composite():
    rows = []
    for region, (u_pct, r_pct) in TABLE_A1_URBAN_RURAL_PCT.items():
        est = (u_pct / 100.0) * NATL_URBAN_PCT_2013 + (r_pct / 100.0) * NATL_RURAL_PCT_2013
        rows.append({"region": region, "year": 2013, "biomass_fuel_pct": est,
                     "data_source": "composite_2013"})
    df = pd.DataFrame(rows)

    # Internal consistency check against the actually-reported national total.
    natl_check = (NATL_URBAN_SHARE_2013 / 100.0) * NATL_URBAN_PCT_2013 + \
                 (NATL_RURAL_SHARE_2013 / 100.0) * NATL_RURAL_PCT_2013
    diff = abs(natl_check - NATL_TOTAL_PCT_2013_REPORTED)
    print(f"  [2013 composite] National reweight check: {natl_check:.2f}% vs. reported "
          f"{NATL_TOTAL_PCT_2013_REPORTED:.1f}% (diff = {diff:.2f}pp)")
    assert diff < 1.0, "2013 composite reweighting is off by more than 1pp -- check inputs before proceeding!"
    return df


# ─────────────────────────────────────────────────────────────────────────
# 2. 2017 — WP164.pdf Appendix Table A.9, province-level, aggregated to
#    region via PROVINCE_TO_REGION (imported, not retyped).
# ─────────────────────────────────────────────────────────────────────────
WP164_PROVINCE_ESTIMATES_2017 = {
    "Lanao Del Sur": 88.3, "Sulu": 94.6, "Tawi-tawi": 89.6,
    "Abra": 73.3, "Apayao": 82.9, "Benguet": 11.0, "Ifugao": 61.1,
    "Kalinga": 69.2, "Mountain Province": 44.1,
    "Metropolitan Manila": 4.0,
    "Ilocos Norte": 47.4, "Ilocos Sur": 47.1, "La Union": 51.9, "Pangasinan": 56.7,
    "Cagayan": 66.5, "Isabela": 59.0, "Nueva Vizcaya": 61.8, "Quirino": 68.2,
    "Bataan": 19.2, "Bulacan": 15.6, "Nueva Ecija": 41.0, "Pampanga": 10.5,
    "Tarlac": 48.5, "Zambales": 43.6, "Aurora": 66.5,
    "Batangas": 46.6, "Cavite": 9.8, "Laguna": 15.0,
    "Marinduque": 74.2, "Mindoro Occidental": 86.4, "Mindoro Oriental": 66.8,
    "Palawan": 84.9, "Quezon": 61.9, "Rizal": 12.3, "Romblon": 80.0,
    "Basilan": 94.9, "Zamboanga Del Norte": 90.2,
    "Albay": 70.4, "Camarines Norte": 72.5, "Camarines Sur": 61.1,
    "Catanduanes": 72.3, "Masbate": 89.9, "Sorsogon": 77.0,
    "Aklan": 82.7, "Antique": 91.5, "Capiz": 86.9, "Guimaras": 90.6,
    "Iloilo": 84.8, "Negros Occidental": 78.1,
    "Bohol": 86.7, "Cebu": 55.6, "Negros Oriental": 77.7, "Siquijor": 85.6,
    "Biliran": 65.2, "Eastern Samar": 83.1, "Leyte": 71.7,
    "Northern Samar": 79.2, "Southern Leyte": 84.2, "Samar": 81.8,
    "Bukidnon": 77.8, "Camiguin": 83.0, "Misamis Occidental": 89.5,
    "Misamis Oriental": 71.8,
    "Compostela": 82.5, "Davao del Norte": 68.8, "Davao Del Sur": 69.1,
    "Davao Oriental": 89.1,
    "Saranggani": 88.2, "South Cotabato": 80.8, "Lanao Del Norte": 78.8,
    "North Cotabato": 91.8, "Sultan Kudarat": 89.6,
    "Agusan Del Norte": 66.9, "Agusan Del Sur": 87.5, "Surigao Del Sur": 80.1,
    "Zamboanga Sibugay": 92.7, "Zamboanga Del Sur": 77.6,
    "Dinagat": 78.3, "Surigao Del Norte": 84.4,
    "Maguindanao": 93.2, "Shariff Kabunsuan": 83.4,
}
assert len(WP164_PROVINCE_ESTIMATES_2017) == 81, "Expected 81 provinces from WP164 Appendix Table A.9"

# Aliases for WP164's own spelling/ordering quirks -> PROVINCE_TO_REGION's
# canonical keys. "Shariff Kabunsuan" -> "Maguindanao" is a real historical
# fact (created 2006, ruled unconstitutional & reverted to Maguindanao by
# the Supreme Court in 2008 -- Sema v. COMELEC), not a guess.
WP164_NAME_ALIAS = {
    "Tawi-tawi": "Tawi-Tawi",
    "Metropolitan Manila": "National Capital Region",
    "Mindoro Occidental": "Occidental Mindoro",
    "Mindoro Oriental": "Oriental Mindoro",
    "Compostela": "Compostela Valley",
    "Saranggani": "Sarangani",
    "North Cotabato": "Cotabato (North Cotabato)",
    "Dinagat": "Dinagat Islands",
    "Shariff Kabunsuan": "Maguindanao",
}
PROVINCE_TO_REGION_SPECIAL = dict(PROVINCE_TO_REGION)
PROVINCE_TO_REGION_SPECIAL["National Capital Region"] = "NCR"  # normal key already covers this but be explicit


def build_2017_from_wp164():
    rows = []
    unmatched = []
    for prov, est in WP164_PROVINCE_ESTIMATES_2017.items():
        std_name = WP164_NAME_ALIAS.get(prov, prov)
        region = PROVINCE_TO_REGION_SPECIAL.get(std_name)
        if region is None:
            unmatched.append(prov)
            continue
        rows.append({"province": prov, "region": region, "estimate_2017": est})
    if unmatched:
        print(f"  [2017] UNMATCHED PROVINCES (dropped): {unmatched}")
        raise RuntimeError("2017 province->region mapping incomplete -- fix aliases before proceeding.")
    else:
        print(f"  [2017] All {len(WP164_PROVINCE_ESTIMATES_2017)} provinces matched to a region.")

    prov_df = pd.DataFrame(rows)
    regional = (
        prov_df.groupby("region")["estimate_2017"].mean().reset_index()
        .rename(columns={"estimate_2017": "biomass_fuel_pct"})
    )
    regional["year"] = 2017
    regional["data_source"] = "real_2017"
    n_provinces_per_region = prov_df.groupby("region").size()
    print("  [2017] Provinces per region (aggregation weight, unweighted mean):")
    for r, n in n_provinces_per_region.items():
        print(f"      {r:14s}: {n} province(s)")
    return regional[["region", "year", "biomass_fuel_pct", "data_source"]]


# ─────────────────────────────────────────────────────────────────────────
# 3. 2022 — FR381.pdf Table 2.4, direct region-level breakdown.
# ─────────────────────────────────────────────────────────────────────────
FR381_2022_SOLID_FUEL_PCT = {
    "NCR": 1.2, "CAR": 24.4, "Region I": 43.0, "Region II": 48.4,
    "Region III": 13.5, "Region IV-A": 15.5, "Region IV-B": 70.9,
    "Region V": 63.5, "Region VI": 71.4, "Region VII": 44.6,
    "Region VIII": 55.4, "Region IX": 80.6, "Region X": 68.8,
    "Region XI": 55.2, "Region XII": 72.8, "Region XIII": 67.5,
    "BARMM": 88.1,
}
NATL_TOTAL_PCT_2022_REPORTED = 41.5  # FR381 Table 2.4, reported national total


def build_2022_direct():
    rows = [{"region": r, "year": 2022, "biomass_fuel_pct": v, "data_source": "real_2022"}
            for r, v in FR381_2022_SOLID_FUEL_PCT.items()]
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────
# 4. Assemble 3 anchor points + linear interpolation (no extrapolation
#    beyond 2013/2022) into an annual 17x10 panel.
# ─────────────────────────────────────────────────────────────────────────
def build_annual_panel():
    anchors = pd.concat([build_2013_composite(), build_2017_from_wp164(), build_2022_direct()],
                         ignore_index=True)
    assert set(anchors["region"]) == set(PANEL_REGIONS), \
        f"Region mismatch: {set(anchors['region']) ^ set(PANEL_REGIONS)}"

    full = pd.DataFrame([(r, y) for r in PANEL_REGIONS for y in YEARS], columns=["region", "year"])
    full = full.merge(anchors, on=["region", "year"], how="left")

    # Linear interpolation strictly between known anchors, per region; no
    # extrapolation beyond the first (2013) or last (2022) anchor.
    full = full.sort_values(["region", "year"]).reset_index(drop=True)
    full["biomass_fuel_pct"] = full.groupby("region")["biomass_fuel_pct"].transform(
        lambda s: s.interpolate(method="linear", limit_area="inside")
    )
    full["data_source"] = full["data_source"].fillna("interpolated")

    assert full["biomass_fuel_pct"].isna().sum() == 0, "Missing values remain after interpolation!"
    return full


# ─────────────────────────────────────────────────────────────────────────
# 5. Sanity checks (same spirit as the placebo test's pre-flight checks)
# ─────────────────────────────────────────────────────────────────────────
def sanity_check(panel):
    print("\n── SANITY CHECK ──")
    by_region_var = panel.groupby("region")["biomass_fuel_pct"].std()
    flat = by_region_var[by_region_var < 1e-6]
    print(f"Regions with ~zero within-region variance (expected: none, since 3 different "
          f"anchors per region unless a region happened to have near-identical rates in "
          f"2013/2017/2022): {list(flat.index) if len(flat) else 'none'}")

    by_year_var = panel.groupby("year")["biomass_fuel_pct"].std()
    print(f"Cross-region SD by year (should be well above 0 every year):")
    for y, sd in by_year_var.items():
        print(f"    {y}: SD={sd:.2f}")
    assert (by_year_var > 1.0).all(), "A year has near-zero cross-region variance -- investigate!"

    zero_cols = (panel.groupby("region")["biomass_fuel_pct"].max() < 0.5)
    print(f"Regions that are flat-zero throughout (expected: none): "
          f"{list(zero_cols[zero_cols].index) if zero_cols.any() else 'none'}")
    assert not zero_cols.any(), "A region is flat-zero across the whole panel -- investigate!"

    # Directional spot-check on the REAL anchors only (2017, 2022 -- not the
    # 2013 composite, which is checked separately below since it's not a
    # direct measurement). BARMM and CAR are known high-biomass-use regions;
    # NCR is the canonical low-biomass region.
    real_panel = panel[panel["data_source"].isin(["real_2017", "real_2022"])]
    checks = {"BARMM": (">", 70), "CAR": (">", 15), "NCR": ("<", 10)}
    for region, (direction, threshold) in checks.items():
        vals = real_panel.loc[real_panel["region"] == region, "biomass_fuel_pct"]
        ok = (vals > threshold).all() if direction == ">" else (vals < threshold).all()
        print(f"  {region} (real 2017/2022 anchors only): expected {direction} {threshold}% -> "
              f"{'PASS' if ok else 'FAIL'} (range {vals.min():.1f}-{vals.max():.1f}%)")
        assert ok, f"Directional spot-check failed for {region}!"

    # Composite-vs-real discontinuity check: flag (not hard-fail, since a
    # real secular decline in solid-fuel use 2013->2022 is plausible
    # nationally) any region where the 2013 COMPOSITE anchor implies an
    # implausibly large jump to the 2017 REAL anchor -- this is exactly the
    # kind of artifact the composite method (pinning fully-urban/fully-rural
    # regions to a single national marginal rate) can produce.
    print("\n  Composite (2013) -> real (2017) discontinuity check (all regions):")
    c13 = panel[panel["data_source"] == "composite_2013"].set_index("region")["biomass_fuel_pct"]
    r17 = panel[panel["data_source"] == "real_2017"].set_index("region")["biomass_fuel_pct"]
    jump = (r17 - c13).sort_values()
    flagged_regions = []
    for region, delta in jump.items():
        flag = " <-- LARGE JUMP, composite likely unreliable for this region" if abs(delta) > 20 else ""
        if flag:
            flagged_regions.append(region)
        print(f"    {region:14s}: 2013 composite={c13[region]:5.1f}%  2017 real={r17[region]:5.1f}%  "
              f"delta={delta:+6.1f}pp{flag}")
    if flagged_regions:
        print(f"\n  FLAGGED: {flagged_regions} -- 2013 composite is a poor proxy for these regions "
              f"specifically (extreme urban/rural share pins them close to a single national rate, "
              f"but their true rate is evidently far from the mix implied). This is disclosed as a "
              f"limitation; a jackknife re-run dropping each flagged region is done below.")

    print("\nSANITY CHECKS PASSED (with the above discontinuity flags noted, not hidden).\n")
    return flagged_regions


# ─────────────────────────────────────────────────────────────────────────
# 6. Mediation test: (a) first-stage correlation w/ PM2.5, (b)
#    covariate-adjusted FE re-estimation.
# ─────────────────────────────────────────────────────────────────────────
def run_mediation_test(biomass_panel, flagged_regions=None):
    flagged_regions = flagged_regions or []
    pm25_asthma = pd.read_csv("data/processed/asthma_pm25_merged.csv")
    merged = pm25_asthma.merge(biomass_panel, on=["region", "year"], how="inner")
    assert len(merged) == 170, f"Expected 170 merged rows, got {len(merged)}"
    merged.to_csv("data/processed/biomass_fuel_pm25_asthma_merged.csv", index=False)
    print(f"Saved data/processed/biomass_fuel_pm25_asthma_merged.csv ({merged.shape})")

    print("\n── (a) FIRST STAGE: does biomass-fuel-use correlate with PM2.5? ──")
    # Pooled (region-year) correlation.
    r_pooled = np.corrcoef(merged["biomass_fuel_pct"], merged["pm25"])[0, 1]
    print(f"Pooled (region-year, n=170) correlation(biomass_fuel_pct, pm25) = {r_pooled:.4f}")
    # Between-region correlation (region means) -- more meaningful here since
    # biomass-fuel-use is close to time-invariant per region (only 3 real
    # anchors + interpolation), so most of its variation IS between-region.
    region_means = merged.groupby("region")[["biomass_fuel_pct", "pm25"]].mean()
    r_between = np.corrcoef(region_means["biomass_fuel_pct"], region_means["pm25"])[0, 1]
    print(f"Between-region (17 region means) correlation = {r_between:.4f}")

    print("\n── (b) SECOND STAGE: does adding biomass-fuel-use as a covariate change ──")
    print("      the primary PM2.5 -> asthma two-way FE coefficient?")
    base = fe_fit(merged, "region", "year", "pm25", "asthma_rate_per100k")
    print(f"  WITHOUT covariate: beta_pm25={base['beta']:.4f}, se={base['se']:.4f}, "
          f"p={base['p_value']:.4f}  (reported primary result: -2.5541, 0.8247, 0.0024)")

    adj = fe_fit_multi(merged, "region", "year", ["pm25", "biomass_fuel_pct"], "asthma_rate_per100k")
    b_pm25, b_biomass = adj["beta"]
    se_pm25, se_biomass = adj["se"]
    p_pm25, p_biomass = np.atleast_1d(adj["p_value"])
    print(f"  WITH covariate:    beta_pm25={b_pm25:.4f}, se={se_pm25:.4f}, p={p_pm25:.4f}")
    print(f"                     beta_biomass_fuel={b_biomass:.4f}, se={se_biomass:.4f}, p={p_biomass:.4f}")

    pct_change = 100.0 * (b_pm25 - base["beta"]) / base["beta"]
    print(f"\n  Change in beta_pm25: {base['beta']:.4f} -> {b_pm25:.4f} ({pct_change:+.1f}%)")
    if abs(pct_change) < 10:
        interp = "NEGLIGIBLE change -- little evidence biomass-fuel-use mediates the PM2.5-asthma relationship."
    elif abs(pct_change) < 25:
        interp = "MODEST change -- some evidence of partial mediation/confounding overlap, not conclusive."
    else:
        interp = "SUBSTANTIAL change -- biomass-fuel-use overlaps meaningfully with the PM2.5-asthma estimate."
    print(f"  Interpretation: {interp}")

    # ── Robustness: does the result hinge on the flagged region(s) whose
    # 2013 composite is a poor proxy (per the sanity check above)? Same
    # leave-one-out logic as scripts/robustness_jackknife.py, applied here
    # specifically to the region(s) flagged as having an unreliable 2013
    # composite anchor, not to every region.
    jackknife_rows = []
    if flagged_regions:
        print(f"\n── ROBUSTNESS: re-running (a) and (b) with each flagged region dropped ──")
        for dropped in flagged_regions:
            sub = merged[merged["region"] != dropped]
            sub_region_means = sub.groupby("region")[["biomass_fuel_pct", "pm25"]].mean()
            r_between_sub = np.corrcoef(sub_region_means["biomass_fuel_pct"], sub_region_means["pm25"])[0, 1]
            adj_sub = fe_fit_multi(sub, "region", "year", ["pm25", "biomass_fuel_pct"], "asthma_rate_per100k")
            b_pm25_sub = adj_sub["beta"][0]
            se_pm25_sub = adj_sub["se"][0]
            p_pm25_sub = np.atleast_1d(adj_sub["p_value"])[0]
            print(f"  DROP {dropped}: between-region r={r_between_sub:.4f} (full sample: {r_between:.4f}); "
                  f"beta_pm25(+covariate)={b_pm25_sub:.4f}, se={se_pm25_sub:.4f}, p={p_pm25_sub:.4f} "
                  f"(full sample: {b_pm25:.4f}, {se_pm25:.4f}, {p_pm25:.4f})")
            jackknife_rows.append({
                "check": f"drop_{dropped}_between_region_correlation", "value": r_between_sub, "n": 16,
            })
            jackknife_rows.append({
                "check": f"drop_{dropped}_beta_pm25_with_covariate", "value": b_pm25_sub,
                "se": se_pm25_sub, "p": p_pm25_sub, "n": adj_sub["n_obs"],
            })

    results = pd.DataFrame([{
        "check": "first_stage_pooled_correlation", "value": r_pooled, "n": 170,
    }, {
        "check": "first_stage_between_region_correlation", "value": r_between, "n": 17,
    }, {
        "check": "beta_pm25_without_covariate", "value": base["beta"], "se": base["se"], "p": base["p_value"], "n": base["n_obs"],
    }, {
        "check": "beta_pm25_with_biomass_covariate", "value": b_pm25, "se": se_pm25, "p": p_pm25, "n": adj["n_obs"],
    }, {
        "check": "beta_biomass_fuel_covariate", "value": b_biomass, "se": se_biomass, "p": p_biomass, "n": adj["n_obs"],
    }, {
        "check": "pct_change_in_beta_pm25", "value": pct_change,
    }] + jackknife_rows).round(4)
    os.makedirs("outputs/tables", exist_ok=True)
    results.to_csv("outputs/tables/mediator_biomass_fuel_results.csv", index=False)
    print("\nSaved outputs/tables/mediator_biomass_fuel_results.csv")

    return merged, base, adj, r_pooled, r_between


# ─────────────────────────────────────────────────────────────────────────
# 7. Figure: panel trajectories (sanity) + first-stage scatter + beta comparison
# ─────────────────────────────────────────────────────────────────────────
def make_figure(panel, merged, base, adj, r_between):
    os.makedirs("outputs/figures", exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    ax = axes[0]
    for region in PANEL_REGIONS:
        sub = panel[panel["region"] == region].sort_values("year")
        ax.plot(sub["year"], sub["biomass_fuel_pct"], marker="o", markersize=3, lw=1, alpha=0.7)
        anchor = sub[sub["data_source"].isin(["composite_2013", "real_2017", "real_2022"])]
        ax.scatter(anchor["year"], anchor["biomass_fuel_pct"], s=25, color="black", zorder=3)
    ax.set_title("Biomass-fuel-use %, 17 regions\n(dots = real/composite anchors: 2013 composite, 2017, 2022;\nlines = linear interpolation)", fontsize=9)
    ax.set_xlabel("Year"); ax.set_ylabel("% households using solid/biomass fuel")

    ax = axes[1]
    region_means = merged.groupby("region")[["biomass_fuel_pct", "pm25"]].mean()
    ax.scatter(region_means["biomass_fuel_pct"], region_means["pm25"], s=40, color="#2166ac")
    for r, row in region_means.iterrows():
        ax.annotate(r, (row["biomass_fuel_pct"], row["pm25"]), fontsize=6, alpha=0.7)
    ax.set_xlabel("Mean biomass-fuel-use % (region)"); ax.set_ylabel("Mean PM2.5 (region)")
    ax.set_title(f"First stage: between-region correlation\nr={r_between:.3f}", fontsize=9)

    ax = axes[2]
    labels = ["PM2.5 alone\n(primary model)", "PM2.5\n(+biomass covariate)"]
    betas = [base["beta"], adj["beta"][0]]
    ses = [base["se"], adj["se"][0]]
    ax.errorbar(range(2), betas, yerr=[1.96 * s for s in ses], fmt="o", markersize=10,
                color="black", ecolor="gray", elinewidth=2, capsize=6)
    ax.axhline(0, color="black", lw=1)
    ax.set_xticks(range(2)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Two-way FE beta (per 1 ug/m3 PM2.5)")
    ax.set_title("Second stage: covariate-adjusted beta_pm25\nPoints = beta; bars = 95% CI (clustered SE)", fontsize=9)

    plt.tight_layout()
    plt.savefig("outputs/figures/mediator_biomass_fuel_check.png", dpi=150)
    plt.close()
    print("Saved outputs/figures/mediator_biomass_fuel_check.png")


if __name__ == "__main__":
    print("=" * 78)
    print("BUILDING BIOMASS-FUEL-USE MEDIATOR PANEL (2013 composite + 2017 WP164 + 2022 direct)")
    print("=" * 78)
    panel = build_annual_panel()
    os.makedirs("data/processed", exist_ok=True)
    panel.to_csv("data/processed/biomass_fuel_regional_panel.csv", index=False)
    print(f"\nSaved data/processed/biomass_fuel_regional_panel.csv (shape={panel.shape}, should be 170=17x10)")
    print(panel["data_source"].value_counts())

    flagged_regions = sanity_check(panel)

    merged, base, adj, r_pooled, r_between = run_mediation_test(panel, flagged_regions=flagged_regions)
    make_figure(panel, merged, base, adj, r_between)

    print("\n" + "=" * 78)
    print("DONE.")
    print("=" * 78)
