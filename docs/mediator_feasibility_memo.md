# Feasibility Memo: Candidate Mediator Covariates for a Future Mediation Analysis

**Purpose:** scoping only, per your explicit instruction. No analysis was run, no manuscript
text was written, and no data was downloaded. This is informational, for you to decide whether
pursuing a mediation analysis is worth it given the November 5 deadline.

**Candidates:** urbanization index, hospital/pediatrician density, indoor biomass-fuel use,
secondhand smoke (SHS) prevalence — proposed as covariates that might explain the
between-region confounding this manuscript already identifies (region is higher-PM2.5 →
also more urbanized, better-resourced, etc.).

---

## What already exists in this repo

Checked `data/raw/` and `data/processed/` in full. Nothing in the repo directly measures any
of the 4 candidates. The closest things found:

- `data/raw/cchain/tm_relative_wealth_index.csv` — Meta/World Bank Relative Wealth Index,
  barangay-level (adm4), 2016–2022 (7 of this study's 10 years). Could serve as a rough
  urbanization/socioeconomic proxy, but **covers only 10 of the Philippines' 17 regions**
  (confirmed by joining against `data/raw/cchain/location.csv`: NCR, Regions I, III, V, VI,
  VII, VIII, IX, X, XI — missing CAR, Region II, Region IV-A, Region IV-B, Region XII, Region
  XIII, and BARMM). This is the same CCHAIN dataset already flagged in an earlier session for
  the population-weighting check, and it has the identical limitation here.
- `data/raw/cchain/worldpop_population.csv` — population density by barangay, 2000–2020, same
  10-region coverage as above (already ruled insufficient for population-weighting in a prior
  session; the coverage gap applies equally here).
- `data/raw/cchain/disease_fhsis_totals.csv`, `disease_lgu_disaggregated_totals.csv`,
  `disease_pidsr_totals.csv` — disease case/death surveillance totals, not exposure or
  infrastructure covariates. Not relevant to any of the 4 candidates.

**Bottom line: none of the 4 candidates can be built from what's already in this repo.**

---

## Candidate 1: Urbanization index

**In-repo data:** none directly; the RWI proxy above is a weak stand-in and only covers 10/17
regions.

**Most likely real source:** Philippine Statistics Authority (PSA) Census of Population and
Housing — PSA publishes region-level percent-urban-population figures from the 2015 and 2020
censuses (e.g., PSA reported 55.2% national urbanization in 2024 estimates, with regional
breakdowns like CALABARZON at 73.0% and Eastern Visayas at 17.3% as of the most recent PSA
release). This is a real, publicly available, regionally complete dataset.

**Coverage judgment:** **Regional coverage would likely be complete (all 17 regions)** — PSA
census data is designed to cover the whole country. **Temporal coverage is the real problem**:
percent-urban is only measured at census years (2015, 2020, and historically 2000, 2010), not
annually. For a 2013–2022 panel, you would have at most 2 usable data points (2015, 2020) and
would need to either interpolate/extrapolate for the other 8 years or treat urbanization as
approximately time-invariant per region. That second option has a methodological wrinkle worth
flagging now: this manuscript's region and year fixed effects already absorb any
time-invariant regional characteristic, including urbanization if it doesn't change much
within the study window. A mediator that's essentially constant within each region over
2013–2022 would explain the *pooled/between-region* correlation (useful for a mediation
decomposition of the r = +0.887 pooled correlation) but would contribute close to nothing to
the *within-region* fixed-effects estimate specifically, since FE already nets out
time-invariant regional differences. Worth deciding up front which correlation you're trying
to mediate.

---

## Candidate 2: Hospital / pediatrician density

**In-repo data:** none.

**Most likely real source:** DOH National Health Facility Registry (NHFR), the official
master list of licensed health facilities in the Philippines, publicly browsable/downloadable
by facility type and region at nhfr.doh.gov.ph.

**Coverage judgment:** **Regional coverage is likely complete** — it's the national registry.
**Two real risks**: (1) the NHFR is a live/current-snapshot registry, not clearly an archived
annual time series — getting *2013 vs. 2022* facility counts (rather than just today's count)
may require either an explicit historical-data request to DOH or accepting a single
current-year snapshot as a rough, time-invariant proxy (same caveat as urbanization above).
(2) **Pediatrician-specific counts may not exist as a distinct field at all** — the general
health-workforce statistic found in this search (3.9 doctors per 10,000 population nationally,
highest in NCR, lowest in Bangsamoro) is for doctors broadly, not pediatricians specifically.
A hospital-density or general-physician-density proxy is plausible; a genuinely
pediatrician-specific regional density figure is not confirmed to exist in a readily
accessible form.

---

## Candidate 3: Indoor biomass-fuel use

**In-repo data:** none.

**Most likely real source:** the Philippine National Demographic and Health Survey (NDHS),
run by PSA/DHS Program. Household cooking-fuel type is a standard NDHS module question, and
NDHS survey rounds were conducted in **2013, 2017, and 2022** — all three falling inside this
study's exact panel window.

**Coverage judgment:** this is the **most promising of the 4 candidates**. NDHS is explicitly
designed to be representative at the regional level (region is one of its standard reporting
strata), so **regional coverage for all 17 regions is likely for each of the 3 survey years**.
Temporal coverage is still not annual — 3 time points across a 10-year panel, same
interpolation question as urbanization above — but 3 points spread across the exact study
window (start, middle, end) is meaningfully better than the 2 census-year points available for
urbanization. Getting the actual regional tables would mean requesting/downloading the NDHS
2013, 2017, and 2022 datasets or published regional fact sheets from the DHS Program or PSA.

---

## Candidate 4: Secondhand smoke (SHS) prevalence

**In-repo data:** none.

**Most likely real source:** the Global Adult Tobacco Survey (GATS) Philippines, run by
PSA/DOH with WHO/CDC support. GATS rounds were conducted in **2009, 2015, and 2021** — 2 of
those (2015, 2021) fall inside the 2013–2022 window; the 2009 round predates it.

**Coverage judgment:** the weakest of the 4 on temporal grounds — only 2 usable time points
within the study window (vs. 3 for the NDHS/biomass-fuel candidate), and the published summary
reports checked here **do not appear to include a regional breakdown of SHS exposure** (the
2015 vs. 2021 comparison found was national-level only). Regional-level estimates may exist in
the raw GATS microdata, which the WHO NCD Microdata Repository lists as available for
researcher request (extranet.who.int/ncdsmicrodata) — but that would require a specific data
request and there's no guarantee the regional sample sizes are large enough to produce stable
region-level estimates (GATS is powered for national and sometimes urban/rural estimates, not
necessarily for all 17 regions individually). **Realistically the highest-effort, lowest-
confidence candidate of the 4.**

---

## Summary judgment

| Candidate | In-repo? | Regional coverage (17/17)? | Temporal coverage in 2013–2022 | Overall feasibility |
|---|---|---|---|---|
| Urbanization index | No (weak 10/17-region proxy only) | Likely yes (PSA census) | 2 points (2015, 2020) | Moderate — good source, sparse over time, largely time-invariant per region |
| Hospital/pediatrician density | No | Likely yes for facilities; pediatrician-specific uncertain | Uncertain (current snapshot only, unclear history) | Moderate-low — real registry exists, but historical + pediatrician-specific data both uncertain |
| Indoor biomass-fuel use | No | Likely yes (NDHS design) | 3 points (2013, 2017, 2022) | **Best of the 4** — real source, 3 points spanning the exact window, designed for regional reporting |
| Secondhand smoke prevalence | No | Uncertain/unlikely at published-report level | 2 points (2015, 2021) | Weakest — may need a microdata request with no guarantee of usable regional estimates |

None of the 4 would give you a true annual 17-region panel without interpolation. All 4 would
need external data requests/downloads I did not attempt, per your explicit instruction not to
source new data given the sandbox's network limitations. If you want to pursue this, indoor
biomass-fuel use (via NDHS) is the strongest starting point on both the regional-coverage and
temporal-coverage dimensions.
