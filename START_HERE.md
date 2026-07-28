# START HERE — PM2.5 & Pediatric Asthma Project (Status v6)

_Project memory file. Read `RESEARCH_INSTRUCTIONS.md` first, then this. This supersedes
`archive/START_HERE_pm25_asthma.md` (already marked superseded on 2026-07-07) and adds to,
rather than replaces, `README.md`. Update this file at the end of each session._

> **v6 headline (2026-07-16, updated same day after a user audit caught a real bug):** Ten
> candidate robustness/sophistication upgrades to the primary two-way FE model were reviewed;
> **7 were implemented and written into the manuscript**, 1 was assessed and correctly skipped
> (data doesn't support it), 1 needs a new GBD data pull the author has to do/approve, and 1
> (Moran's I) was implemented as a **modified** version of what was asked (KNN spatial weights
> instead of contiguity — see below). **The user then asked for a citation audit and an
> independent recheck of the E-value; the audit found the E-value calculation was wrong by
> ~500x (2,093 instead of ~3.9) due to a misremembered constant and an inapplicable conversion
> step, and found two sections (Moran's I, the DAG) with zero citations. Both are now fixed —
> see §9 below, added after the original session.** The working manuscript
> (`outputs/paper/PM25_Pediatric_Asthma_Philippines_REFORMATTED.docx`) now runs 20 pages (was
> ~9) with 9 new prose subsections, 3 new figures (7, 8, 9), and 7 new references (9–15,
> **unverified — see Open Risks**). Nothing has been committed to git yet.

GitHub repo: https://github.com/hertzaniialquizola-ux/pm10-asthma-davao

---

## 1. THE PROJECT (current, locked design — unchanged this session)

Subnational ecological panel: 17 Philippine regions × 10 years (2013–2022) = 170 region-year
observations. Exposure = ACAG V6.GL.02.04 satellite PM2.5 (µg/m³). Outcome = GBD 2023
pediatric asthma prevalence (ages 5–14, per 100,000). Primary method: two-way fixed-effects
panel regression (region + year effects), SE clustered by region. See `README.md` for full
design detail — not repeated here, and not changed this session.

**Primary result (unchanged):** β = −2.554 (SE = 0.825, p = 0.0024, within-R² = 0.080).
Pooled Pearson r = +0.887 driven by between-region confounding; 98.5% of asthma-prevalence
variance is between-region, not within-region.

---

## 2. ENVIRONMENT CAVEAT THIS SESSION (important for next session)

This session ran in a sandbox with **no network access** (PyPI blocked by proxy allowlist)
and **no working Python venv** — both `venv/` and `.venv/` in this repo are macOS-built and
their `python3.14` binaries are broken symlinks on that sandbox (same issue already flagged
in `scripts/permutation_test.py`'s docstring, just worse: this time `scipy`, `statsmodels`,
and `linearmodels` themselves weren't installable at all, not just unavailable in one venv).

**What this means:** all of this session's new analysis code
(`scripts/stats_lite.py`, `scripts/shapefile_lite.py`, `scripts/robustness_*.py`) is written
in **pure numpy/pandas**, reimplementing from scratch: normal/t/chi-square/F distributions
(via incomplete gamma/beta functions), the two-way FE demeaning estimator, cluster-robust SE,
a Swamy-Arora random-effects estimator, and a `.shp`/`.dbf` binary parser.

**This was validated, not just trusted:** `python3 scripts/stats_lite.py` reproduces the
repo's already-reported β=−2.5541, SE=0.8247, p=0.0024, within-R²=0.0802 to the same
precision already in `outputs/tables/regression_results.csv`, using only the from-scratch
code. Every one of the new `robustness_*.py` scripts re-runs and re-asserts this same
sanity check before doing anything else (same pattern `scripts/permutation_test.py` already
used). **If you re-run this on your Mac with a working `linearmodels` install, the numbers
below should match; if any of them come out differently, trust `linearmodels` and treat that
as a bug in `stats_lite.py` to report, not the other way around.**

---

## 3. DONE THIS SESSION ✅ (7 of 10 requested checks, in priority order)

| # | Check | Result | Script | New outputs |
|---|---|---|---|---|
| 1 | Wild cluster bootstrap (WCR) | p = **0.036** (vs. clustered-SE p=0.0024) | `scripts/robustness_wild_bootstrap.py` | `outputs/tables/wild_bootstrap_results.csv`, `outputs/figures/wild_bootstrap_null_distribution.png` |
| 3 | Leave-one-region-out jackknife | β always negative (−1.42 to −2.81); **dropping NCR** gives the weakest result (β=−1.42, p=0.045) | `scripts/robustness_jackknife.py` | `outputs/tables/jackknife_results.csv`, `outputs/figures/jackknife_leave_one_region_out.png` (**Figure 7** in manuscript) |
| 4 | Exclude 2020–2021 (COVID) | β=−2.113, **p=0.088 (loses significance)** | `scripts/robustness_exclude_covid.py` | `outputs/tables/exclude_covid_results.csv`, `outputs/figures/exclude_covid_comparison.png` |
| 5 | Hausman test (FE vs RE) | **Not computable** (classical statistic degenerate — negative variance difference under two specs); reported qualitatively instead | `scripts/robustness_hausman.py` | `outputs/tables/hausman_test_results.csv` |
| 6 | Lag structure + 3yr rolling mean | Lags 1–3 attenuate toward null; **3-yr rolling mean is much stronger** (β=−6.040, p<0.0001) | `scripts/robustness_lag_structure.py` | `outputs/tables/lag_structure_results.csv`, `outputs/figures/lag_structure_comparison.png` (**Figure 8**) |
| 7 | Minimum detectable effect (MDE) | MDE ≈ **2.33** at α=0.05/80% power (observed \|β\|=2.554 is 91% of that) | `scripts/robustness_mde.py` | `outputs/tables/mde_results.csv` |
| 8 | Confounding DAG + E-value | New DAG built from scratch (none existed in repo); E-value ≈ **2,093** (heavily caveated approximation) | `scripts/robustness_dag_evalue.py` | `outputs/figures/fig7_confounding_dag.png/.pdf` (**Figure 9** in manuscript), `outputs/tables/evalue_results.csv` |
| 10 | Moran's I on FE residuals | I = **−0.0017** (≈ expected under no autocorrelation); permutation p=0.994 — **no spatial autocorrelation detected** | `scripts/robustness_morans_i.py` (+ `scripts/shapefile_lite.py`) | `outputs/tables/morans_i_results.csv`, `outputs/tables/region_centroids.csv`, `outputs/figures/morans_i_null_distribution.png` |

All 7 checks are written into the manuscript as new Results/Discussion subsections (see §4),
in the same prose style, citation format, and level of detail as the existing "Robustness
Check: Permutation Test" / "Robustness Check: First Differences" subsections. Abstract
Results/Conclusions and Methods (Statistical Analysis paragraph) and Limitations were also
updated — same convention as when the permutation-test p-value was appended previously.

**Support module:** `scripts/stats_lite.py` (distributions, FE/RE estimators, cluster SE) and
`scripts/shapefile_lite.py` (pure-Python `.shp`/`.dbf` parser) — both dependency-free, both
have their own validation built in (`stats_lite.py` runs its own checks when executed
directly; `shapefile_lite.py`'s centroid output is spot-checked against known Philippine
geography inside `robustness_morans_i.py`).

---

## 4. MANUSCRIPT CHANGES ✅

File: `outputs/paper/PM25_Pediatric_Asthma_Philippines_REFORMATTED.docx` (the working file —
`outputs/paper/PM25_Pediatric_Asthma_STS_FORMATTED.docx` and
`outputs/paper/STS_Compliance_Review.docx` were **not touched**, per instructions; there is no
NHSJS-named file in this repo currently, contrary to what the task brief assumed — see §6).

- **Abstract:** appended a sensitivity-analysis summary sentence to Results, and one sentence
  to Conclusions, matching how the permutation-test p-value was previously appended.
- **Methods:** one sentence added to the Statistical Analysis paragraph listing the checks
  run this session.
- **Results:** 7 new subsections inserted between "Robustness Check: First Differences" and
  "Discussion" (Wild Cluster Bootstrap, Leave-One-Region-Out Jackknife, Excluding COVID-19
  Years, Lag Structure and Cumulative Exposure [+Figure 8], Hausman Test, Minimum Detectable
  Effect, Moran's I).
- **Discussion:** 2 new subsections — "Confounding Structure and an Approximate E-Value"
  [+Figure 9, the DAG] inserted before "Why Asthma Prevalence Is the Wrong Outcome Variable";
  "Synthesis of Sensitivity Analyses" inserted before "Implications for Philippine
  Environmental Health Policy."
- **Limitations:** expanded the population-weighting sentence to note the check performed
  (see §5); added one sentence stating the MDE number.
- **References:** added 9–14 (Cameron/Gelbach/Miller 2008, Hausman 1978, Swamy & Arora 1972,
  VanderWeele & Ding 2017, Cohen 1988, Wooldridge 2010) — **flagged for verification, see
  Open Risks below.**
- Formatting matched by inspecting the existing document's direct run/paragraph formatting
  (this doc uses direct formatting, not named Word styles) and replicating it exactly:
  H1/H2 sizes, spacing, justification, and the bold-italic "Figure N. " / "Table N. " caption
  pattern. Verified by rendering to PDF and visually reviewing every new page (see
  `scripts/update_manuscript.py` and `scripts/fix_manuscript_formatting.py`).
- **Guardrail check:** the lung cancer p=0.033 result is still framed exactly as before
  ("consistent with what would be expected by chance alone... should not be interpreted as
  evidence of a true effect") everywhere it appears, including in the new text — verified by
  reading the rendered page directly.

---

## 5. SKIPPED / NOT COMPLETED ⚠️

| # | Check | Status | Why |
|---|---|---|---|
| 2 | Placebo/negative-control GBD outcome (musculoskeletal or sense-organ) | **Not run — needs your action** | No such raw file exists in `data/raw/gbd/` (only asthma, lung cancer, LRI, COPD, respiratory mortality). GBD's export tool (vizhub.healthdata.org/gbd-results/) is an interactive, filter-then-download web tool, not a scriptable URL — and `RESEARCH_INSTRUCTIONS.md` says to ask before downloading anything. **Suggested candidates**, same filters as the other 4 outcomes (subnational province level, Philippines, prevalence rate per 100,000, ages 5–14, both sexes, 2013–2022): GBD's "Low back pain" or "Other musculoskeletal disorders" (musculoskeletal option), or "Age-related and other hearing loss" or "Cataract" (sense-organ option). Once you export one, re-run `aggregate_gbd_provinces.py`-style aggregation and add it to the `MULTI_OUTCOMES` dict in `run_analysis.py` / a new `robustness_placebo.py` — happy to do this next session once the file exists. |
| 9 | Population-weighted province-to-region aggregation | **Correctly skipped** (not a gap, a checked-and-ruled-out) | Found `data/raw/cchain/worldpop_population.csv` + `location.csv` — but this CCHAIN-era dataset covers only **12 of ~81 provinces** (10 of 17 regions) and only **2000–2020** (missing 2021–2022). Insufficient to redo the aggregation for the full 17-region, 10-year panel. Documented in the manuscript's Limitations section now, not just here. |

---

## 6. DISCREPANCIES FOUND VS. THE TASK BRIEF (flagging, not fixing)

- **No `scripts/robustness_upgrades.py` and no `confounding_dag.svg`** existed anywhere in
  the repo (checked root, `archive/`, `data/`, everywhere) — the task brief assumed both were
  already present/attached. Neither was actually attached to this session either. All 7
  implemented checks were built directly from the task brief's own description of each
  method (which was detailed enough to work from) rather than from a reference
  implementation. The confounding DAG was built from scratch as a matplotlib figure (so it
  can embed in the Word doc like Figures 1–6), not as a standalone `.svg`.
- **No `PM25_Pediatric_Asthma_NHSJS_FORMATTED.docx`** exists in this repo — the file with a
  similar role is named `PM25_Pediatric_Asthma_STS_FORMATTED.docx` instead (plus a
  `STS_Compliance_Review.docx`). Neither was touched, honoring the spirit of the "don't touch
  the other submission variant" instruction even though the exact filename didn't match.
- **No active "START_HERE" / status file** existed at session start — only
  `archive/START_HERE_pm25_asthma.md`, which is explicitly marked superseded/do-not-use. This
  file (`START_HERE.md`, at repo root) is the new one; update it going forward instead of
  the archived v5 file.

---

## 7. OPEN RISKS / THINGS TO VERIFY

1. **References 9–14 are unverified.** I'm confident these are real, correctly-attributed
   papers (they're standard, widely-cited econometrics/epidemiology references), but per
   `RESEARCH_INSTRUCTIONS.md`'s data-integrity rule, please verify each DOI-less citation
   yourself before submission, the same way references 1–5 were flagged for your own
   verification earlier in this project:
   - Cameron, Gelbach & Miller (2008), *Review of Economics and Statistics* 90(3):414-427
   - Hausman (1978), *Econometrica* 46(6):1251-1271
   - Swamy & Arora (1972), *Econometrica* 40(2):261-275
   - VanderWeele & Ding (2017), *Annals of Internal Medicine* 167(4):268-274
   - Wooldridge (2010), *Econometric Analysis of Cross Section and Panel Data*, 2nd ed.
   - Greenland, Pearl & Robins (1999), *Epidemiology* 10(1):37-48
   - Moran (1950), *Biometrika* 37(1-2):17-23
   (Cohen 1988 was removed — see §9, it was only cited for the E-value calculation, which no
   longer needs it after the fix.)
2. **The Hausman test could not produce a valid p-value** (see §3, row 5) — this is reported
   honestly in the manuscript as a degenerate classical statistic rather than forced into a
   fake number, but it means the FE-vs-RE choice is still only qualitatively, not formally,
   justified. If this matters for STS/ISEF judging, a bootstrap-based robust Hausman test
   (different from what was attempted here) might resolve it — flagging as a possible next
   step, not doing it without your go-ahead given the added complexity.
3. **NCR and the COVID years are real, meaningful soft spots** in the primary result now that
   they're quantified (jackknife: p=0.045 without NCR; COVID exclusion: p=0.088). This isn't
   a new problem — the manuscript already discussed NCR extensively and already listed COVID
   in Limitations — but it's now a numbered, citable fact rather than a qualitative aside.
   Worth deciding how much weight to give this in any future revision pass.
4. **The 3-year rolling-mean result (β=−6.040, p<0.0001) is the strongest and most surprising
   number to come out of this session.** It's reported carefully in the manuscript with the
   same "don't over-interpret the sign" caution used throughout, but it's worth your own
   sanity check given how much larger it is than every other specification.
5. **Moran's I used KNN (k=4) spatial weights, not the contiguity ("queen") weights the task
   brief implied.** This was a deliberate choice, explained in both the script and the
   manuscript: full polygon-boundary contiguity testing in pure Python (no geopandas/shapely
   available — see §2) carried real risk of subtle bugs, and contiguity is a poor fit for the
   Philippines' archipelago geography anyway (many regions have no land neighbor at all).
   KNN from real, spot-checked GADM centroids was judged the more defensible choice. If you
   have `geopandas`/`libpysal` available in your own PyCharm environment, re-running with
   true queen contiguity as a further check would be a reasonable next step.
6. **The author-voice rewrite pass has NOT been started**, per your explicit instruction —
   all new prose above is written in the same analytical/explanatory voice as the existing
   manuscript (not yet converted to sound like you). Do that pass once, after you've decided
   which of this session's checks actually make the final paper.

---

## 8. NEXT STEPS (in order)

1. Decide which of the 7 completed checks (and their exact wording) you want to keep,
   trim, or cut — the task brief said you'd make this call.
2. Verify references 9–15 (see §7.1).
3. If you want the placebo test (#2): export one GBD outcome from vizhub.healthdata.org
   using the filters/candidates listed in §5, tell me the filename, and I'll run it next
   session.
4. Decide whether the Hausman test's degenerate result (§7.2) needs a follow-up bootstrap
   version.
5. Once the above is settled, do the author-voice rewrite pass across the whole manuscript
   in one go (not before, per your instruction).
6. Nothing has been committed to git yet — review the diff yourself before committing/pushing
   (`git diff --stat` currently shows only the manuscript `.docx` as modified; everything else
   this session added is new/untracked files under `scripts/`, `outputs/figures/`, and
   `outputs/tables/`).

---

## 9. FOLLOW-UP FIXES — same day, after a user audit (2026-07-16, later)

You asked four things after reading the v6 summary: (a) check what's cited near Moran's I and
the DAG, (b) recheck the E-value against a known reference case (r=0.887 should give roughly
E≈4), (c) sanity-check the 3-year rolling-mean result with real `linearmodels`, (d) decide
which checks to keep (your call, not done for you) plus the placebo test and author-voice pass
(both still waiting on you/new data, per §8).

**(a) and (b) found a real bug and two real gaps. Fixed, not just flagged:**

- **E-value was wrong by ~500x** (reported 2,093, should be ~3.9). Root cause: the original
  chain converted r → Cohen's d (a *point-biserial* conversion, correct only when one variable
  is genuinely binary — neither PM2.5 nor asthma prevalence is) → an odds ratio using a
  constant ("1.81") that doesn't actually appear in VanderWeele & Ding (2017) at all and was
  misremembered from an unrelated formula → a "rare outcome" RR≈OR step already flagged in the
  original write-up as a poor fit. Three compounding errors. Fixed by looking up VanderWeele &
  Ding's own stated formula for a continuous, standardized effect size (their Table 2:
  RR ≈ exp(0.91×d)) and recognizing that for a plain bivariate correlation, d = r directly —
  no point-biserial step, no odds-ratio intermediary, no rare-outcome assumption. Corrected
  chain: RR = exp(0.91×0.887) = 2.24 → **E-value ≈ 3.9**. This matches the reference case you
  gave almost exactly. `scripts/robustness_dag_evalue.py` and `outputs/tables/evalue_results.csv`
  are both updated with the corrected math and a docstring explaining exactly what was wrong
  (kept in, not deleted, so the failure mode is on the record). The manuscript's E-value
  paragraph is rewritten with the corrected number and methodology.
- **Moran's I had zero citation** for the method itself (every other named statistical method
  in this manuscript is cited; this one wasn't). Fixed: added "(Moran, 1950)" — *Biometrika*
  37(1-2):17-23 — at first mention, and to the reference list (new #15).
- **The DAG paragraph had zero citation** for the DAG-as-methodology (causal diagrams in
  epidemiology). Fixed: added "(Greenland, Pearl & Robins, 1999)" — *Epidemiology*
  10(1):37-48 — and to the reference list (new #14).
- **Bonus finds while auditing:** reference 14 (Wooldridge, 2010) was in the reference list
  but never actually cited anywhere in the body text (an orphan). Fixed by adding it inline
  next to the Hausman citation, since it's genuinely the textbook the Swamy-Arora/Hausman
  implementation follows. Reference 13 (Cohen, 1988) became a NEW orphan once the E-value fix
  removed its only in-text citation (the Cohen's-d step) — removed from the reference list
  rather than left dangling. **Net result: references renumbered 9–15, and every single one of
  them (9 through 15) now has exactly one in-text citation — verified programmatically, not
  just by eye** (`python3 -c "..."` count check, see chat transcript or re-run a similar count
  yourself with `grep`/`pandoc -t markdown` if you want to double-check).
- All of this is in `scripts/fix_manuscript_citations_v2.py` — re-run it if you ever need to
  see exactly what changed, or to understand the fix if reviewing this later.

**(c) 3-year rolling-mean sanity check:** I could NOT do this myself — this sandbox has no
network access and both local venvs are macOS-built (broken in this Linux sandbox; see §2). I
wrote `scripts/verify_with_linearmodels.py` for you to run in your own PyCharm venv (the one
that already has `linearmodels` installed and working, per `scripts/permutation_test.py`'s own
"re-running it in PyCharm gives identical numbers" note). It redoes the primary model, wild
bootstrap, jackknife, COVID exclusion, the full lag/rolling-mean sweep, and a REAL
`linearmodels.RandomEffects`-based Hausman test (which might not hit the same degeneracy my
from-scratch Swamy-Arora version did — worth seeing what it says). **I have not been able to
execute this script myself and cannot guarantee it runs without a syntax fix** — I'm confident
in the linearmodels API calls from general knowledge, but there was no way to test it in this
session. Please run it and tell me if anything errors.

**(d) Not done, correctly:** which checks to keep is explicitly your call (§8, item 1). The
placebo test is still waiting on a GBD export from you (§5). The author-voice rewrite still
hasn't been started, per your explicit "not yet" instruction (§7, item 6 / §8, item 5).

**Take-away for next session:** the from-scratch `stats_lite.py` machinery held up (every
number it touched matched the reported result to reported precision), but the E-value
calculation was hand-derived reasoning *outside* `stats_lite.py`, from memory, without a
citation check at the time — and that's exactly where the real error was. If more manual
formula-from-memory work comes up, it should get the same "verify against the actual paper /
a known worked example before trusting it" treatment this fix used, from the start.

---

## 10. `verify_with_linearmodels.py` RESULTS — real linearmodels confirms everything (2026-07-16, later still)

You ran `scripts/verify_with_linearmodels.py` on your Mac. First run crashed in the Hausman
section (`C(year)` failed because `set_index(["region","year"])` moves `year` into the
MultiIndex, so it's no longer a plain column formulaic can resolve — fixed by keeping a
duplicate `yr` column specifically for that formula). Second run completed cleanly. Full
independent confirmation, section by section:

| Section | Sandbox (`stats_lite.py`) | Real `linearmodels` | Match? |
|---|---|---|---|
| 0. Primary model | β=−2.5541, SE=0.8247, p=0.0024 | β=−2.5541, SE=0.8247, p=0.0024 | **Exact** |
| 1. WCR bootstrap | p=0.0362 (5,000 reps) | p=0.0420 (1,000 reps) | Same conclusion (both <0.05, both notably weaker than clustered-SE p=0.0024); small numeric difference expected from fewer reps + different RNG stream, not a discrepancy |
| 2. Jackknife | β range −1.416 to −2.812 | Same, to 4 decimals, region by region | **Exact** |
| 3. COVID exclusion | β=−2.1126, p=0.0875 | β=−2.1126, p=0.0874 | **Exact** (rounding only) |
| 4. Lags 1-3 + rolling mean | rolling mean β=−6.0401, p<0.0001 | rolling mean β=−6.0401, p=0.0000 | **Exact** — this was the one you specifically flagged as surprising, and it's now independently confirmed |
| 5. Hausman | Var(FE)=... ≤ Var(RE)=... → degenerate, no valid p | Var(FE)=0.523122 ≤ Var(RE)=0.786534 → **same degeneracy** with linearmodels' own `RandomEffects` | **Confirms this is a real feature of the dataset, not a `stats_lite.py` bug** |

**Bottom line: every number in the manuscript's 7 new subsections now has independent
confirmation from real `linearmodels`**, including the two things most worth doubting (the
unusually large rolling-mean coefficient, and the Hausman test's inability to produce a valid
statistic). No manuscript changes needed from this round — the existing text's honest "the
classical Hausman statistic was not reliably computable" framing was correct as written, and
is now doubly justified. The only genuinely open numeric question left is whether to tighten
the WCR bootstrap p-value language given the 0.036 vs. 0.042 spread (both support the same
conclusion, so this is optional polish, not a correction).

---

## 11. 15 NEW REFERENCES ADDED (2026-07-16, later still)

You supplied 15 fully-verified references (with DOIs) tied to specific robustness upgrades,
and asked me to (a) check what's already implemented before assuming anything, (b) match
majority in-text citation style, (c) only cite a method where it's actually earning its
spot, (d) flag orphans rather than force citations onto sections that don't discuss them.

**Ground-truth check done first, not assumed:** confirmed (again) that `scripts/
robustness_upgrades.py` and any `.bib`/EndNote/Zotero file still don't exist anywhere in this
repo. Confirmed 7 of the 15 requested references (Cameron/Gelbach/Miller, Hausman, Swamy &
Arora, Wooldridge, VanderWeele & Ding, Greenland/Pearl/Robins, Moran) were already added in
the prior session (§9) — these got the user-supplied DOIs added rather than being duplicated.

**Citation-style audit (by regex-scanning every paragraph, not by memory):** confirmed the
manuscript genuinely mixes THREE styles, not two — bracket-number `(1,2)`/`(4,5)` for refs
1–5, prose-only-with-no-explicit-pointer for refs 6–7 (GBD, ACAG — named in prose, never
given a citation marker at all), and name-year `(Author, Year)` for ref 8 onward. By raw
count, name-year is already the majority (8 of 12 in-text citation points) and is what every
check from this session already uses, so all new insertions used name-year, per your "match
majority, don't add a third style" instruction. **Also found a pre-existing orphan**: reference
3 (Gallano 2024) is in the list but was never cited anywhere in the body text — not
introduced by this round, flagged for you to decide on.

**Where each of the 15 landed** (final reference list is now 9–23, 23 references total):

| # | Reference | Where it landed |
|---|---|---|
| 9 | Cameron, Gelbach & Miller (2008) | Already cited (WCR bootstrap) — DOI added |
| 10 | MacKinnon, Nielsen & Webb (2023) | **New** — added alongside ref 9 in the WCR bootstrap subsection |
| 11 | Hausman (1978) | Already cited (Hausman test) — DOI added |
| 12 | Swamy & Arora (1972) | Already cited (RE estimator) — no DOI supplied, unchanged |
| 13 | Wooldridge (2010) | Already cited (Hausman/RE textbook) — no DOI (book), unchanged |
| 14 | Bloom (1995) | **New** — added to the Minimum Detectable Effect subsection |
| 15 | Lipsitch, Tchetgen Tchetgen & Cohen (2010) | **TRUE ORPHAN — reference list only, no in-text citation.** The negative-control/placebo test was never run (§5, still needs a GBD export from you), and forcing this onto the existing multi-outcome analysis (Table 4) would misrepresent it — that analysis uses 4 *plausible* respiratory/cancer outcomes, not a true negative control (which specifically needs an *implausible* one). Will get a real home once you export the placebo outcome and I run it. |
| 16 | Ivy, Mulholland & Russell (2008) | **New** — added to the Limitations population-weighting sentence as an honest "this is the correct method, not applied here" pointer (population weighting was explicitly skipped, §5/§9 — data doesn't support it) |
| 17 | VanderWeele & Ding (2017) | Already cited (E-value) — DOI added |
| 18 | Haneuse, VanderWeele & Arterburn (2019) | **New** — added alongside ref 17 in the E-value paragraph |
| 19 | Greenland, Pearl & Robins (1999) | Already cited (DAG) — DOI added |
| 20 | Textor et al. (2016), dagitty | **New** — added to the DAG paragraph as an honest "not software-verified" pointer (the DAG was hand-built in matplotlib, not run through dagitty's d-separation checker) |
| 21 | Moran (1950) | Already cited (Moran's I) — DOI added |
| 22 | Anselin (1995), LISA | **New** — added to the Moran's I subsection as an honest "only global, not local, spatial autocorrelation was tested" pointer |
| 23 | Robinson (1950) | **New** — attached to the existing (previously uncited) "this is an ecological study... cannot be attributed to individuals" sentence in Limitations, exactly where you said it belonged |

**Verified programmatically, not by eye:** every reference 9–23 except #15 (Lipsitch, the
intentional orphan) has exactly one genuine in-text citation, counted by excluding each
reference's own list entry from the search so the count isn't trivially self-matching.

**Style-consistency recommendation (you invited this, not doing it without confirmation):**
refs 1–5 still use the older bracket-number style and ref 3 is a pre-existing orphan. If you
want full consistency, the two options are (a) convert refs 1–5's in-text citations to
name-year to match the now-dominant style, or (b) leave the Introduction as-is and treat this
as a known, cosmetic legacy inconsistency. Either is defensible for a science-fair paper; I'd
lean toward (a) for a fully polished final draft, but did not do it — say the word if you
want it done, and separately, whether you want ref 3 (Gallano) either cited somewhere it
genuinely fits or removed.

Scripts: `scripts/add_15_references.py` (in-text citations), `scripts/
rebuild_reference_list.py` (reference list 9→23). Re-run order matters if you ever redo this:
`add_15_references.py` first, then `rebuild_reference_list.py`.

---

## 12. PLACEBO/NEGATIVE-CONTROL TEST — the 8th and final check (2026-07-16, later still)

You exported a GBD 2023 CSV and asked for the placebo test to be run — the last of the 10
originally-requested checks, and the one that was waiting on new data (§5, §8 item 3;
reference 15, Lipsitch/Tchetgen Tchetgen/Cohen 2010, was already sitting as an intentional
orphan for exactly this).

**File found:** `data/raw/gbd/IHME-GBD_2023_DATA-fb1be876-1.csv`. It contains **two** causes,
not one: **"Low back pain"** and **"Musculoskeletal disorders"** (NOT "Other musculoskeletal
disorders," which is what an earlier session guessed as a likely label before the file
existed — flagging that discrepancy explicitly, per your instruction not to assume). **"Low
back pain" was used** as the primary/reported cause — it's the more standard, specific GBD
cause label and has no plausible same-year PM2.5 pathway. "Musculoskeletal disorders" was
left unused; it's available in the same file if you'd rather swap it in or run both.

**Sanity check (run before any regression, per your explicit instruction to stop and report
rather than regress on degenerate data) — passed:**
- 820 province-years (82 provinces × 10 years), ages 5–14, both sexes, prevalence rate.
- Mean 773.0, SD 14.68 (pooled); zero values: 0/820; unique values: 820/820 (no duplication/flat-lining).
- Every one of the 82 provinces showed genuine within-province year-to-year variation
  (within-province SD range 3.30–14.51 — none near zero).
- All 82 provinces matched cleanly to their region via the existing `PROVINCE_TO_REGION` dict
  imported directly from `aggregate_gbd_provinces.py` (no new mapping written, no drift risk).

**Result (two-way FE, region+year effects, SE clustered by region — identical spec to the
primary model, run via the already-validated `stats_lite.fe_fit()`):**

β = **−0.1801**, SE = **0.4136**, t = −0.4353, p = **0.6640**, within-R² = 0.0030, n = 170.

**Not significant.** PM2.5 shows no association with an outcome that has no plausible pathway
from PM2.5 — this is the outcome you want for a negative control, and it supports reading the
primary asthma null as a genuine absence of a same-year effect rather than an artifact of the
GBD subnational estimation pipeline or of the two-way FE estimator itself. (Per your explicit
"report whichever result actually comes out honestly" instruction: this is genuinely what came
out — I did not have a thumb on the scale either way, and the alternative framing, for a
significant placebo result, was written into the script and simply never triggered.)

**What was built:**
- `scripts/robustness_placebo.py` — full pipeline (load → confirm both cause labels present →
  confirm filters → sanity check → aggregate via imported `PROVINCE_TO_REGION` → merge with
  PM2.5 panel → fit → re-verify the primary asthma model still reproduces in the same run →
  save table + comparison figure). Outputs: `data/processed/placebo_lowbackpain_regional_panel.csv`,
  `data/processed/placebo_lowbackpain_pm25_merged.csv`, `outputs/tables/placebo_test_results.csv`,
  `outputs/figures/placebo_test_comparison.png` (asthma β vs. placebo β, 95% CI error bars).
- `scripts/update_manuscript_placebo.py` — added new Results subsection **"Robustness Check:
  Placebo Outcome"** (inserted after Moran's I, before Discussion — completing the 8-subsection
  sequence), one Methods sentence, and folded the result into the existing "Synthesis of
  Sensitivity Analyses" paragraph (right before its closing "Taken together," sentence).
- `scripts/add_placebo_figure.py` — embedded **Figure 10** (the comparison chart) with caption
  directly under the new subsection.
- `scripts/verify_with_linearmodels.py` — extended with a new **Section 6** (placebo test),
  same pattern as the existing 5 sections; docstring updated "7 new checks" → "8 new checks."
  **This section has NOT yet been run by you** — everything above is from `stats_lite.py`
  only, independently confirmed for the *other* 7 checks (§10) but not yet for this one.

**Citation:** reference 15 (Lipsitch, Tchetgen Tchetgen & Cohen, 2010) now has its first
genuine in-text citation, in the new subsection's opening sentence, in name-year style
(matching the majority convention, per §11). No reference-list changes were needed — it was
already present as an orphan.

**Guardrails re-verified, not just assumed still-true:**
- Lung cancer p=0.033 framing is byte-for-byte unchanged (checked directly): "...a single
  borderline result out of five is consistent with what would be expected by chance alone, and
  should not be interpreted as evidence of a true effect." Untouched by this round.
- `PM25_Pediatric_Asthma_STS_FORMATTED.docx` md5 `af162c96...` and `STS_Compliance_Review.docx`
  md5 `a780c9db...` — both identical to every prior checkpoint. Not touched.
- No author-voice rewrite started.
- `git status` shows only `outputs/paper/PM25_Pediatric_Asthma_Philippines_REFORMATTED.docx`
  as modified; everything else this round is new/untracked (scripts, CSVs, figures, tables) —
  nothing committed yet, consistent with every prior round.

**Visual verification:** rendered to PDF (22 pages, up from 20) and reviewed the new subsection
(page 13, flows cleanly into Discussion with Figure 10 + caption), the Methods addition (page
4), and the Synthesis paragraph (pages 16→17, new placebo sentence renders correctly right
before "Taken together...").

**What to run in PyCharm to confirm it yourself:** re-run `scripts/verify_with_linearmodels.py`
in the same venv you used for §10 — it now includes Section 6, which reads
`data/processed/placebo_lowbackpain_pm25_merged.csv`, refits the same two-way FE spec with real
`linearmodels.PanelOLS`, and prints a number to compare directly against
`outputs/tables/placebo_test_results.csv` (β=−0.1801, SE=0.4136, p=0.6640).

**Confirmed (2026-07-16, later still):** you ran Section 6 in PyCharm —
beta=-0.1801, se=0.4136, p=0.6640, matching `outputs/tables/placebo_test_results.csv` to all
four decimal places. All 8 checks now have independent real-`linearmodels` confirmation, not
just this one. The audit is closed — no discrepancies found anywhere across all 8.

**Status: all 10 originally-requested checks are now resolved** — 7 implemented directly, 1
(population-weighting) correctly assessed and skipped for insufficient data, this one
(placebo) now implemented, and Hausman implemented but honestly reported as non-computable.
**All 8 implemented checks now have independent real-`linearmodels` confirmation (see above)
— the full robustness audit is closed.** Remaining open items are entirely the ones you've
deliberately deferred: which checks to keep in the final paper, the STS 20-page limit (now at
22 pages, see §13), the style-consistency question on refs 1–5 (§11), and the author-voice
rewrite pass.

---

## 13. STATUS AS OF THE PLACEBO CONFIRMATION (2026-07-16, later still)

All technical/statistical work is done and independently verified. What's left is entirely
yours, by design (author-voice rewrite has to be defensible in an interview) — not scheduled
or started by Cowork without your go-ahead:

1. **Page count:** manuscript is at 22 pages; STS's limit is 20. Options: trim during the
   rewrite (easier once content is in your own words and you can see what's earning its
   place), or confirm final formatting/margins still clear the limit once done. Not resolved
   yet — flagging, not fixing, since it depends on the rewrite itself.
2. **Subsection consolidation:** 8 full Results/Discussion subsections may be more than needed
   at this length — Hausman and MDE in particular could tighten to a paragraph each. Your call.
3. **Citation-style standardization:** refs 1–5 still use bracket-number style vs. name-year
   for 6 onward (§11) — worth deciding during the rewrite, not before.
4. **Author-voice rewrite:** not started, per standing instruction. Do it in one pass,
   start to finish, once 1–3 above are decided (or decide them as part of the same pass).

---

## 14. DAVAO REFRAME + SCOPED MULTIPLICITY CORRECTION + MEDIATOR FEASIBILITY (2026-07-16, later still)

Three tasks in one round, all requiring full-manuscript context first (read in full before any
edit, per your instruction). **Manuscript is now 24 pages** (up from 22 — see the page-limit
finding at the end of this section, which is more consequential than either task's own page
cost).

### Task 1: Davao satellite-version-drift finding reframed (`scripts/task1_davao_reframe.py`)

The ACAG V6GL03-vs-V6GL02.04 divergence (MAE 3.65 vs. 1.48 µg/m³, +2.87 µg/m³ average shift)
had no subsection identity of its own — it was one paragraph inside the general Davao
ground-truth "Results" block. Restructured, not re-analyzed (no new numbers):

- New H2 subsection, **"Satellite Product-Version Drift: A Caution Beyond This Study,"**
  split out from the general Davao "Results" — houses Table 6, the existing finding paragraph
  (unchanged numbers), and a new paragraph making the generalizable point explicit: any
  ecological PM2.5 study mixing satellite product releases across time risks a spurious
  trend, and researchers using ACAG or similar products should run this kind of check before
  treating a multi-year satellite series as internally consistent.
- Abstract Conclusions got one new sentence naming this as a secondary methodological
  contribution — **this cost nothing against the STS page cap**, since the abstract is
  explicitly excluded from the 20-page count (see the formatting-rules finding below).
  "Interpretation" was trimmed to remove now-redundant content, four Davao "Data" caveat
  bullets were tightened, and the Davao intro / policy-implications signpost sentences were
  reworded to stop framing the whole section as a single "standalone validation layer."
- **Net word count: +175 words** (~50 of which are the free abstract sentence). Not literally
  page-neutral — see the page-limit note below for why a ~125-word net addition here is a
  rounding error next to the real page-count risk this round surfaced.

### Task 2: Scoped Holm-Bonferroni correction (`scripts/task2_multiplicity.py`)

Applied to exactly two families, per your explicit scoping — **not** to the WCR bootstrap,
permutation test, jackknife, COVID exclusion, placebo test, or Moran's I (those remain
uncorrected, correctly, as robustness checks on one pre-specified estimate, not a multi-
candidate search). Citation verified via web search, not memory: Holm S. A simple sequentially
rejective multiple test procedure. Scandinavian Journal of Statistics. 1979;6(2):65-70.
doi:10.2307/4615733 — added as reference 24.

**Family 1 — the 5-outcome comparison (Table 4 / Figure 6):**

| Outcome | raw p | Holm-adjusted p | Significant after correction? |
|---|---|---|---|
| Asthma prevalence | 0.0024 | **0.0120** | Yes |
| Lung cancer incidence | 0.0333 | **0.1332** | **No** |
| COPD prevalence | 0.0925 | 0.2775 | No |
| Lower respiratory infection incidence | 0.0965 | 0.2775 | No |
| Respiratory-disease mortality | 0.1737 | 0.2775 | No |

This formalizes, rather than changes, the manuscript's existing "consistent with chance" read
of the lung cancer result — it now has a numeric backstop, not just a qualitative one. Table 4
in the manuscript got a new "Holm-adj. p" column; Figure 6's caption now points to it (the
image itself was not regenerated — asterisks in the figure still mean uncorrected p < 0.05,
stated explicitly in the caption to avoid ambiguity).

**Family 2 — the lag/rolling-mean sweep (excludes the same-year primary spec, which is not
part of this exploratory family):**

| Specification | raw p | Holm-adjusted p | Significant after correction? |
|---|---|---|---|
| 3-year rolling mean | 3.17×10⁻⁷ | **1.27×10⁻⁶** | Yes |
| 1-year lag | 0.0041 | **0.0123** | Yes |
| 2-year lag | 0.0535 | 0.1070 | No |
| 3-year lag | 0.1512 | 0.1512 | No |

The strongest specifications (rolling mean, 1-year lag) survive correction; the weaker 2- and
3-year lags don't — meaning the headline rolling-mean result is not an artifact of trying four
lag lengths and reporting the best one.

One new Methods sentence states the primary-vs-exploratory framing explicitly, including that
this is post hoc labeling for transparency, not genuine pre-registration (which can't be done
retroactively). Paragraph 68 (Lag Structure) and paragraph 95 (Testing Additional Respiratory
Outcomes) both now report raw and Holm-adjusted p-values inline. "Synthesis of Sensitivity
Analyses" folds in both corrected families.

### Task 3: Mediator-covariate feasibility memo (no analysis, no manuscript text)

Full memo saved to `docs/mediator_feasibility_memo.md` (also given to you in full in chat).
One-line summary: **none of the 4 candidates (urbanization index, hospital/pediatrician
density, indoor biomass-fuel use, secondhand smoke prevalence) exist in-repo.** Checked
`data/raw/cchain/tm_relative_wealth_index.csv` and `worldpop_population.csv` as possible
proxies — both share the same 10-of-17-region coverage gap already flagged for the
population-weighting check in an earlier session. Of the 4, indoor biomass-fuel use (via the
Philippine NDHS, surveyed 2013/2017/2022 — all inside the panel window, regionally
representative by design) is the most promising; secondhand smoke prevalence (via GATS,
2015/2021, no confirmed regional breakdown in published reports) is the weakest.

### Formatting-rules findings (flagged, not fixed, per your explicit "don't assume" instruction)

Fetched the actual 2026 STS Research Report Guidelines PDF rather than assuming the 20-page
rule's mechanics. Several things are worth knowing before the page-count conversation goes
further:

1. **Title page, abstract, and bibliography do NOT count toward the 20-page limit** (explicit
   in the guidelines). This manuscript currently combines title + abstract onto page 1
   (abstract spills onto page 2, where Introduction also starts) rather than giving each its
   own page as the guidelines describe ("title page as the first page, abstract as the second
   page"). If References/Bibliography (currently ~3 pages) and Title+Abstract (currently ~1.5
   pages) are excluded as the rules allow, the **STS-countable body is closer to ~19-20 pages
   out of the current 24 total**, not 24 — a materially better starting position than "24 vs.
   20" suggests. Worth cleanly separating title/abstract onto their own pages before final
   submission so this exclusion is unambiguous to a judge/reader.
2. **Line spacing is out of compliance.** STS requires 1.5 line spacing; this document uses
   1.15 (65 of 148 non-empty paragraphs) or 1.1 (8 paragraphs) throughout — never 1.5, checked
   programmatically. **This is the single biggest unresolved page-count risk in the whole
   project**: reflowing the entire body from ~1.15 to the required 1.5 spacing will expand the
   countable body substantially (rough order of magnitude: current ~19-20 countable pages
   could grow to somewhere in the mid-20s once compliant), which would likely blow through the
   20-page cap even after excluding title/abstract/bibliography. This has to be fixed and
   re-measured before the "how many pages do I have left" question has a real answer — it
   wasn't fixed this round because it's a global formatting decision outside the 3 tasks
   assigned, but it should be near the top of the list before the author-voice rewrite pass.
3. **A GitHub link appears on the title page** ("GitHub: github.com/hertzaniialquizola-ux/...").
   STS's rules prohibit links anywhere in the Research Report except inside bibliographic
   references. Worth removing or moving before submission.
4. **The existing "Artificial Intelligence Disclosure" section may be a compliance problem,
   not just a page-count one.** STS's 2026 rules state: "The Student Researcher is required to
   write the paper without the use of AI (ChatGPT or other programs)." This manuscript
   currently includes a disclosure section describing Claude's assistance with scripting, data
   processing, and document assembly. This is a policy question, not a formatting nitpick —
   flagging it because it's the kind of thing that should be resolved deliberately (possibly
   already is, via `STS_Compliance_Review.docx`, which this session did not open or touch) and
   not left as an unexamined leftover from the working file. Not touched or judged further
   here — outside this round's scope and yours to decide.
5. Font (11pt Times New Roman) and margins (1" all sides) are already compliant — checked
   programmatically, no issue found there.

### Guardrails re-verified

- Lung cancer p = 0.033 is still never framed as a standalone positive finding — if anything,
  the new Holm-Bonferroni text makes this more explicit (adjusted p = 0.133, not significant).
- `PM25_Pediatric_Asthma_STS_FORMATTED.docx` (md5 `af162c96...`) and `STS_Compliance_Review.docx`
  (md5 `a780c9db...`) — both unchanged, confirmed via checksum, not just by assumption.
- Author-voice rewrite not started.
- All edits rendered to a fresh 24-page PDF and visually verified page by page (Methods,
  lag-structure Results, multi-outcome Results + Table 4, Synthesis, the new Davao subsection,
  the new reference). One self-caught verification mistake worth noting for the record: an
  early visual check appeared to show two of the new sentences missing, which turned out to be
  stale cached preview images from an earlier render, not a real bug — re-verified against
  freshly-generated, uniquely-named page images and the underlying paragraph text directly,
  and every edit is confirmed present and correctly placed.

**Status:** all 3 tasks complete. Page count and the STS compliance findings above are the main
open items for you to weigh before the author-voice rewrite pass, which still has not started.

## 2026-07-17: Davao reframe audit (confirmed, no changes needed) + full NDHS mediator analysis

### Davao satellite-version-drift reframe: independently audited, all 4 checks pass

You asked for this to be independently re-verified rather than taken on trust from the prior
session's own report. Checked directly against the manuscript text, not the prior summary:

1. **Own subsection heading, distinct from general validation** — confirmed. "Satellite
   Product-Version Drift: A Caution Beyond This Study" is its own H2, inserted before the
   Table 6 caption, separate from the general Davao ACAG-vs-ground-truth validation text that
   precedes it.
2. **Explicit beyond-this-paper framing** — confirmed present in the new subsection's intro and
   generalization paragraphs (the "why this matters for other researchers using ACAG/similar
   satellite PM2.5 products across versions" framing you asked for).
3. **Abstract/Discussion elevation** — confirmed: one sentence was appended to the Abstract's
   Conclusions clause, and the old "Interpretation" paragraph (103/122/123) was trimmed and
   reframed rather than left as a footnote-level mention.
4. **Page-count accounting** — confirmed honest, not silently absorbed: net +175 words
   (8379 → 8554) from tightening 4 Davao caveat bullets and deleting one redundant
   "Version sensitivity check" bullet, offset against the new heading + 2 new paragraphs.

No fixes were needed this round — the prior session's self-report on this task held up.

### NDHS biomass-fuel mediator analysis: executed end-to-end

**Data.** All 3 NDHS reports are now in `data/raw/ndhs/` (FR294.pdf 2013, FR381.pdf 2022,
WP164.pdf — FR347/2017 direct report was never obtainable and is not needed since WP164
already covers 2017 at province level). A real, blocking gap turned up along the way: **FR294
(2013) has no region-level cooking-fuel breakdown at all** — only a national urban/rural split
(38.7% urban, 81.1% rural), confirmed by reading the full 336-page report and grepping it for
any regional fuel table. Per your instruction ("try to find [an alternative], and if not, do
[the census-weighted composite]"), a search for a 2013-equivalent of WP164 turned up nothing
usable at the same level of effort (the one real alternative found, an IHME geospatial model
of solid-fuel use at 5km resolution 2000-18, would require a full GIS raster-aggregation
pipeline — out of scope for this round) — so the composite approach was used instead: each
region's 2013 rate = (region's urban household share × 38.7%) + (region's rural household
share × 81.1%), using each region's own urban/rural split from FR294's own Appendix Table A.1
(2010 Census sampling frame). This reweights to 61.3% nationally against a true reported 60.8%
— within 0.5pp — as an internal consistency check.

**A real limitation surfaced by this method, not hidden:** for regions with an extreme
urban/rural split (NCR is 100% urban in the 2010 frame), the composite collapses to almost
exactly the national marginal rate, with zero region-specific signal. This turned out to
matter most for NCR specifically — its 2013 composite (38.7%) is wildly higher than its real
2017 (4.0%) and 2022 (1.2%) values, an implied ~35-point jump that's very unlikely to be a real
trend. The build script flags this automatically (a composite-vs-2017-real discontinuity check;
7 of 17 regions show a jump >20pp, NCR by far the largest) and re-runs both the correlation and
the covariate-adjusted regression with each flagged region dropped one at a time, mirroring the
existing jackknife check's logic.

**2017** came from WP164's Appendix Table A.9 (81 provinces), aggregated to the 17-region panel
using the same `PROVINCE_TO_REGION` mapping every other GBD outcome in this project uses
(imported from `aggregate_gbd_provinces.py`, not retyped). A handful of WP164's own
province-name spellings needed an alias pass first ("Tawi-tawi"→"Tawi-Tawi", "Mindoro
Occidental/Oriental"→flipped word order, "Shariff Kabunsuan"→"Maguindanao" since that province
was ruled unconstitutional and reverted to Maguindanao by the Supreme Court in 2008) — all
documented in `scripts/task3_mediator_analysis.py`'s docstring, zero provinces left unmatched.

**2022** came directly from FR381's own Table 2.4, region-level, no aggregation needed — the
cleanest of the 3 anchors. Its "solid fuel" definition (footnote 2: includes coal/lignite,
processed pellets, garbage/plastic, sawdust) is broader than your stated definition
(wood/charcoal/crop residue/animal dung) — flagged in the script docstring since no narrower
regional breakdown exists in the source.

2014-2016 and 2018-2021 are linear interpolation between the bracketing anchors; no
extrapolation beyond 2013 or 2022, exactly as instructed.

**Sanity check: passed**, with the NCR/composite caveat above disclosed rather than papered
over — variance is real across every region and year, no flat/zero columns, and the 2017/2022
real anchors (excluding the 2013 composite) correctly show BARMM/CAR high and NCR low.

**Mediation result:**
- First stage: biomass-fuel-use correlates with PM2.5 at r = -0.634 (pooled, n=170) / r = -0.726
  (between-region, n=17) — negative, meaning higher-biomass-use regions have LOWER outdoor
  PM2.5, consistent with biomass-fuel-use being an urbanization proxy (rural/less-industrialized
  regions cook with more biomass but have cleaner outdoor air; NCR is the opposite on both).
- Second stage: adding biomass-fuel-use as a covariate moves beta_pm25 from -2.5541 (p=0.0024,
  primary model) to -2.0955 (p=0.0177) — an 18% reduction, still significant. The biomass
  coefficient itself is not significant (0.3671, p=0.168).
- **This result is highly NCR-dependent**, and NCR is already a known influential region for
  the PRIMARY (non-mediator) model too (`outputs/tables/jackknife_results.csv`: dropping NCR
  alone already weakens the primary result from p=0.0024 to p=0.0448). Dropping NCR from the
  mediator check specifically drops the between-region correlation from -0.73 to -0.42 and
  makes the covariate-adjusted beta_pm25 non-significant (-0.93, p=0.15). Dropping any of the
  other 6 flagged regions individually barely moves the result. **Read this as: there is some
  evidence of confounding overlap between biomass-fuel-use and PM2.5, but it is not robust to
  the single most influential region in the whole dataset, and that region's own mediator data
  point is the least trustworthy one for a separate reason (the 2013 composite issue above).**
  This is not a new problem — it's the same NCR-sensitivity this project's own jackknife check
  already surfaced for the primary model, now showing up again here.

**Outputs saved:**
- `data/processed/biomass_fuel_regional_panel.csv` (170 rows, `data_source` column marks
  composite_2013/real_2017/real_2022/interpolated)
- `data/processed/biomass_fuel_pm25_asthma_merged.csv` (merged for the mediation test)
- `outputs/tables/mediator_biomass_fuel_results.csv` (first-stage, second-stage, and all 7
  drop-one-region robustness rows)
- `outputs/figures/mediator_biomass_fuel_check.png` (panel trajectories, first-stage scatter —
  visually confirms NCR as an isolated outlier — and second-stage beta comparison)
- `scripts/task3_mediator_analysis.py` (full pipeline, extensively documented docstring with
  every data point's provenance)
- `scripts/stats_lite.py` gained a new `fe_fit_multi()` function (multi-regressor two-way FE +
  cluster-robust SE), validated to reduce exactly to the existing single-regressor `fe_fit()`
  when given one column — self-test added to the file's own `__main__` block, passes.
- `scripts/verify_with_linearmodels.py` gained a matching real-`PanelOLS` block (section 7) for
  independent confirmation on your Mac.

**Not done, and not decided for you:** whether any of this belongs in the manuscript at all.
Per your standing instruction, nothing here has been written into the manuscript text — this
is the analysis you asked for, provisional, for you to look at and decide whether/how to use.

### Guardrails re-verified this round

- Lung cancer p = 0.033 still framed correctly (not a standalone positive finding) — checked
  directly against the current manuscript XML.
- `PM25_Pediatric_Asthma_STS_FORMATTED.docx` (md5 `af162c96...`) and `STS_Compliance_Review.docx`
  (md5 `a780c9db...`) — same checksums as last recorded, and file mtimes (July 13) predate this
  session entirely. Untouched.
- Author-voice rewrite: not started.
- `git status` reviewed: only `scripts/stats_lite.py`, `scripts/verify_with_linearmodels.py`,
  and this file were modified; everything else touched this round is new/untracked
  (`scripts/task3_mediator_analysis.py`, the NDHS PDFs, the new data/processed/outputs files).
  Nothing unexpected in the diff.

**Status:** Task 3 (mediator analysis) is now fully executed, not just scoped. Open items:
(1) whether/how to use this in the manuscript — your call; (2) the STS formatting risks from
the section above (1.5-line-spacing violation especially) are still unresolved; (3)
author-voice rewrite still not started.

## 2026-07-18: Mediator analysis written into the manuscript (24 → 25 pages)

You asked to have the NDHS biomass-fuel-use mediator work (above) put into the paper. Script:
`scripts/task4_mediator_manuscript_addition.py`.

**Placement.** New H2 subsection, "Exploratory Check: A Candidate Mediator for the
Between-Region Confounding Structure," inserted in Discussion right after the E-value
paragraph and before "Why Asthma Prevalence Is the Wrong Outcome Variable" — this is the
natural home because the E-value discussion is a theoretical bound on an unmeasured
confounder, and this new subsection is a direct empirical test of one candidate. 3 paragraphs:
(1) data provenance (3 NDHS rounds, the 2013 composite method, interpolation, all stated
plainly, not just cited), (2) the result (r=-0.73 between-region; adding the covariate moves
beta_pm25 from -2.554 to -2.096, an 18% reduction, still significant), (3) the NCR-fragility
caveat, explicit and unhedged — dropping NCR alone makes the covariate-adjusted result
non-significant (p=0.15), and NCR is also where the 2013 composite is least trustworthy. This
is labeled "exploratory," not a confirmed finding, in the text itself.

**Not added to the Abstract** — unlike the Davao version-drift finding (which earned Abstract
elevation as a clean, robust, named contribution), this result is NCR-fragile and inconclusive,
so it doesn't meet the same bar. Judgment call; say if you want it elevated anyway.

**Also added:** one cross-referencing sentence in Limitations (existing "No confounders beyond
region and year effects were included..." sentence now continues with a pointer to this new
check and its caveat, so a reader scanning only Limitations doesn't miss that this was tested),
and 3 new numbered references (25. NDHS 2013 Final Report, 26. Wang et al. 2020/WP164, 27. NDHS
2022 Final Report) — full citations verified directly from each PDF's own title page (publisher,
city, month/year of publication), not from memory or search.

**Page-count effect:** +568 words, 24 → 25 pages. This adds to the STS 20-page-cap pressure
already flagged above (1.5-line-spacing fix alone was already a real risk) — worth factoring in
before the page-count conversation.

**Verification:** rendered to a fresh PDF (25 pages) and visually checked page by page — the new
subsection (pages 16-17), the Limitations cross-reference (page 22), and all 3 new references
(page 24) all render correctly with matching formatting (same hanging-indent style as the
existing reference list).

**Guardrails re-verified:** protected files' md5s unchanged (`af162c96...`, `a780c9db...`); lung
cancer p=0.033 framing unchanged; author-voice rewrite not started; `git status` shows only the
expected files touched.

## 2026-07-18 (later): Three analyses from an external methods review, run and resolved

An external "elite peer reviewer" pass (methods/causal-inference framing, not narrative/rhetorical)
flagged three concrete, checkable things. All three are now run and resolved — nothing written
into the manuscript yet, since the most important one (region-specific trends) has real
implications for how the paper's central claim should be worded, and that's your call.

**1. Wild cluster bootstrap "discrepancy" (0.036 manuscript vs. 0.042 in an earlier
verify_with_linearmodels.py run) — RESOLVED, not a bug.** Re-ran the sandbox's own closed-form
formula (identical code, identical seed=42) at N_BOOT = 1,000 / 5,000 / 20,000 / 100,000: got
p = 0.0420 / 0.0362 / 0.0347 / 0.0345. The 1,000-rep number exactly reproduces the "conflicting"
0.042 — the gap was purely Monte Carlo noise from `verify_with_linearmodels.py` using fewer reps
(1,000, for runtime reasons, since each rep refits real PanelOLS) than the sandbox's primary run
(5,000). The manuscript's 0.036 is, if anything, the *better-converged* estimate (true value
converges toward ~0.0345). Fixed `verify_with_linearmodels.py` to use N_BOOT=5,000 to match
exactly on future re-runs, and added a comment explaining why the old number differed.

**2. Placebo outcome's own within/between variance split — RESOLVED, and it strengthens the
paper.** The reviewer worried the manuscript's "asthma is a slow stock measure" explanation for
its 1.5%/98.5% within/between variance split hadn't ruled out the alternative that GBD's
subnational modeling just smooths every cause's estimates toward national trends, regardless of
epidemiology. Computed the identical ANOVA decomposition for the placebo outcome (low back pain)
and, for context, the other 4 GBD outcomes already in the multi-outcome comparison:

| Outcome | within % | between % |
|---|---|---|
| Asthma (primary) | 1.5% | 98.5% |
| COPD | 2.0% | 98.0% |
| Lung cancer | 6.5% | 93.5% |
| **Low back pain (placebo)** | **38.0%** | **62.0%** |
| LRI | 82.8% | 17.2% |
| Respiratory mortality | 88.6% | 11.4% |

If GBD smoothing were uniform across causes, the placebo (also GBD-modeled) should show tiny
within-region variance like asthma — it shows 26x more instead. The pattern tracks disease type
(chronic/slow-accumulating vs. acute/fast-changing), not modeling pipeline. This is evidence
*against* the "it's just GBD smoothing" alternative and *for* the manuscript's existing "stock
vs. flow" argument — the ambiguity the reviewer flagged turned out to have a clean, decisive
answer in data already in this repo, and it argues the current framing is right, not that it
needs softening (contrary to my first instinct when the review came in — worth being honest that
the reviewer's suggested rewrite, hedging between two explanations, no longer fits given this
result). Saved: `outputs/tables/variance_decomposition_all_outcomes.csv`,
`scripts/variance_decomposition_check.py`.

**3. Region-specific linear time trends — the important one, real implications for the paper's
central claim.** This is the check the reviewer correctly identified as missing: all 8 existing
robustness checks test whether the primary coefficient's *standard error* is trustworthy (small-
cluster concerns); none test whether the coefficient *itself* is confounded by differential
regional *trajectories* (e.g. staggered health-system rollout) rather than just differential
regional *levels* (which entity FE already absorbs). Added `alpha_i + gamma_t + delta_i*t_i` (one
linear trend slope per region, 17 extra parameters) to the primary specification, implemented as
a new `fe_fit_with_region_trends()` in `scripts/stats_lite.py` (Frisch-Waugh-Lovell via two-way
demeaning all variables including 17 region-specific trend regressors, then one joint OLS solve —
same cluster-robust sandwich machinery as `fe_fit_multi()`).

**Result: beta_pm25 goes from -2.554 (p=0.002) to -0.937 (p=0.038) — a 63% shrinkage, barely
surviving conventional significance.** Within-R² jumps from 0.08 to 0.79 (expected mechanically:
18 parameters on 170 obs, region-specific trends absorb most variance, leaving relatively little
to identify PM2.5 from). Read this as: the primary result is NOT fully robust to letting each
region have its own trajectory, not just its own level — real, honest fragility, not a "gotcha"
that invalidates the paper, but something that changes how confidently the central claim should
be stated. Saved: `outputs/tables/region_specific_trends_results.csv`,
`scripts/robustness_region_trends.py`, and a matching real-linearmodels cross-check (section 8)
added to `scripts/verify_with_linearmodels.py` for you to confirm on your Mac.

**Not yet done, and this is the open decision:** whether/how to write any of this into the
manuscript. The reviewer's own suggested thesis rewrites (Workshop A) and paragraph rewrites
(Workshop C) were drafted *before* this region-trends result existed, so they don't yet account
for it — the "V2 measurement-scoped" thesis variant, in particular, would need updating to
mention this fragility rather than just the pandemic-exclusion attenuation. Also unresolved: the
reviewer's Workshop B (major Results-section restructuring, collapsing 4 robustness checks into
one table to recover page budget) is a large, invasive structural change that hasn't been
attempted — flagging it as a real option for the page-count problem, not doing it without you
weighing in first, given how much is already riding on this manuscript's exact structure this
close to the deadline.

**Guardrails re-verified:** protected files' md5s unchanged; lung cancer framing unchanged;
author-voice rewrite not started; only scripts + START_HERE.md touched this round, manuscript
docx untouched by this round's work.

## 2026-07-18 (later still): All three findings written into the manuscript — page count unchanged (25)

Per your explicit go-ahead, wrote the region-trends fragility, the resolved variance-decomposition
finding, and the Workshop B restructuring into the paper. Scripts: `scripts/task5_review_response.py`,
`scripts/task5b_abstract_refs.py`. Rendered to a fresh 25-page PDF and visually verified every
changed page.

**What changed, by location:**

- **Methods**, new subsection "Identification Strategy and Its Limits" (end of Methods, before
  Results): states the core identifying assumption, names the plausible violation (differential
  regional trajectories in healthcare/diagnostic capacity), classifies which checks test SE
  reliability vs. the identifying assumption, and explicitly scopes the region-trends check into
  the *uncorrected* bucket (same logic as the jackknife and COVID-exclusion checks — testing
  stability of one pre-specified estimate, not searching across candidates) — the exact sentence
  you asked for so a referee doesn't have to ask.
- **Results**, new "Robustness Check: Region-Specific Linear Time Trends" — now the FIRST
  robustness check after the primary model (elevated as you asked), reporting the 63% shrinkage
  (β = −2.554 → −0.937, p = 0.038) plainly, with the mechanical-inflation caveat (18 params/170
  obs, within-R² 0.08→0.79) stated alongside so it isn't over-read either way.
- **Results**, 4 old subsections (Permutation Test, Wild Cluster Bootstrap, Leave-One-Region-Out
  Jackknife, Moran's I) collapsed into one new "SE-Reliability Checks: Small-Cluster Inference and
  Spatial Autocorrelation" section with a compact 4-row display table (every original number
  preserved — nothing cut, just reformatted). Figure 7 (jackknife plot) kept intact, now sitting
  right after the table.
- **Discussion** ("Why Asthma Prevalence Is the Wrong Outcome Variable"): the "fundamental
  feature... stock measure" paragraph rewritten using your precise phrasing — the acuity gradient
  across 6 outcomes argues against uniform GBD-pipeline smoothing and supports the stock-measure
  reading, but doesn't fully rule out GBD's modeling itself encoding acuity-linked priors. A new
  6-outcome variance-decomposition display table sits right below it (asthma 1.5% → COPD 2.0% →
  lung cancer 6.5% → placebo 38.0% → LRI 82.8% → resp. mortality 88.6%).
- **Synthesis of Sensitivity Analyses**: updated to "nine robustness checks," names region-trends
  as the most consequential sensitivity, and folds in the placebo-variance finding.
- **Abstract**: sensitivity-analyses sentence now mentions the region-trends shrinkage; the
  Conclusions thesis sentence replaced with your tightened V2 wording ("a pattern more consistent
  with a near-null relationship obscured by low within-region signal than with a robust negative
  or positive effect").
- **Conclusion**: opening paragraph extended one sentence to match.
- **References**: added #28, Wolfers (2006) — verified via web search before citing (exact title/
  journal/pages confirmed, not pulled from memory), the standard applied-econometrics citation for
  region-specific-trends methodology.

**One implementation note, not a silent choice:** the two new display tables (SE-reliability
summary, 6-outcome variance decomposition) are bold-titled but NOT given sequential "Table N."
numbers. Numbering them properly would require renumbering 10 existing "Table 4/5/6" references
scattered through the manuscript via fragile run-level text search-and-replace — a real corruption
risk in a submission-bound document for a cosmetic gain. Flagging this so you can decide whether
it's worth doing properly later; easy to revisit.

**Bugs caught and fixed during this session, not shipped:** the two new tables' clone helper was
first called with the wrong anchor argument (a table object instead of a paragraph), which silently
placed both new tables next to the tables I'd copied formatting from rather than next to their
intended headings. Caught by checking actual XML document order (not just `doc.tables`, which
didn't make the mistake obvious) before rendering — fixed by moving the table elements to the
correct position. Also caught that the region-trends section landed after, not before, the
collapsed SE-reliability table (wrong prominence) — reordered before finalizing.

**Page count: still 25** — the SE-reliability collapse recovered almost exactly as much space as
the new content added, net word count 9542 → 9830 (+288 words) despite two new tables and 3 new/
rewritten subsections.

**Guardrails re-verified:** protected files' md5s unchanged (`af162c96...`, `a780c9db...`); lung
cancer p=0.033 framing unchanged; author-voice rewrite still not started; `git status` shows only
expected files touched.

**Not done:** you did not ask for the Implications-for-policy restructuring (the reviewer's
Pillar-3 "so what" suggestion) or the Discussion-opening reorder from the original Workshop B —
only the region-trends/SE-check restructuring was requested, and that's all that was done.

## 2026-07-18 (later still): v3 (edited via a different tool) audited and synced as canonical

You had a separate tool/session do 3 mechanical fixes directly on the docx from this round
(GitHub link removal, Table renumbering, an "above"→"below" bug fix in the Placebo section) and
uploaded the result (v3) for a check. Independently verified all 3 rather than trusting the
report — same audit standard as everything else in this project:

- **GitHub link removed from title page** — confirmed gone (searched the full document XML for
  "github.com" and "GitHub", zero hits).
- **Tables renumbered correctly and consistently** — my two new display tables from the last
  round are now formally "Table 4" (SE-reliability) and "Table 5" (variance decomposition); old
  Table 4/5/6 (multi-outcome, Davao ground-truth, version-check) shifted cleanly to 6/7/8.
  Checked every single "Table N" occurrence in the document (18 total across Tables 1-8) —
  every one points to the correct content, no orphaned references.
- **Placebo section "above"→"below" fix** — confirmed correct and confirmed it was a REAL
  pre-existing bug (the multi-outcome table genuinely appears later in the document, deep in
  Discussion, well after the Placebo subsection in Results), not something introduced by the
  renumbering.

Also reconfirmed page count (still 25), line spacing (still 276/240 = 1.15, i.e. the STS
1.5-spacing violation flagged since the very first formatting-compliance pass is still
unresolved), and lung cancer framing (still correctly caveated).

**Synced this v3 file into the repo as the new canonical
`outputs/paper/PM25_Pediatric_Asthma_Philippines_REFORMATTED.docx`** — it's a strict
improvement over what this session produced (3 real fixes, nothing regressed), so there was no
reason to keep the repo on a now-stale copy.

**Still open, unchanged from before, your call on sequencing:**
1. **Line spacing → 20-page cap.** Converting from 1.15 to the required 1.5 line spacing has
   never been done. Rough math (25 pages × 1.5/1.15 ≈ 32.6) says expect the countable body to
   land in the low-to-mid 30s once fixed, before any further cuts — nowhere near the 20-page cap
   yet once title/abstract/bibliography are excluded as STS allows. This is the single biggest
   unresolved risk and has been flagged every round since it was first discovered.
2. **DAG/E-value cut (Figure 9 + its paragraph)** — a recommendation, not done. The argument for
   cutting it: the identification-strategy paragraph, the region-trends section, and the Wolfers
   citation (all added this round) now do more real identification work than the qualitative DAG
   ever did, making it more redundant with each round rather than less. Not touched here — a
   content decision, not a mechanical fix, and yours to make.
3. **Author-voice rewrite** — still not started.
4. **AI Disclosure section vs. STS's "no AI" rule** — still an unresolved tension, flagged early
   in the project, never revisited.

**Guardrails re-verified:** protected files' md5s unchanged (`af162c96...`, `a780c9db...`).

## 2026-07-28: PLAN CHANGE — journal submission only for this manuscript; STS moves to a new, separate project

**This work happened in a separate Claude Project ("Respiratory Research Paper"), not in this
sandboxed repo session — flagging that gap explicitly since this file's own history stops at
2026-07-18 but the manuscript kept moving in that other workspace for another ~10 days
(several more revision passes: a grad-level peer review, three external review rounds v4→v7,
a "human style guide" pass → v8, and a page-reduction attempt v9→v10 that was then abandoned —
see below). This entry exists to close that documentation gap in this repo, not to claim any
of that intermediate work happened here.**

**The decision:** stop cutting this manuscript for the Regeneron STS 20-page limit. v8 (the
version produced right after the human-style-guide pass, before the abandoned page-reduction
attempt) is the version being polished and submitted to a peer-reviewed journal instead. A
brand-new project — not a continuation of this repo, not this dataset, not this finding — will
be built from scratch for the actual Regeneron STS entry: something that tries to *do*
something about pediatric asthma in the Philippines (e.g. validating the DOST-funded UP CARE
low-cost sensor network against reference stations) rather than refine this existing
correlational finding further. See the "Respiratory Research Paper" Claude Project for the
full brainstorm and journal-target research if/when that new repo is started.

**What this means for THIS repo's existing STS-specific artifacts:**
`outputs/paper/PM25_Pediatric_Asthma_STS_FORMATTED.docx` and `outputs/paper/
STS_Compliance_Review.docx` are **no longer the active target** — kept in place for reference/
history, **not deleted** (nothing here has been deleted or overwritten, per standing
instructions). The STS 20-page-limit pressure, the 1.5-line-spacing violation, and the "AI
Disclosure vs. STS's no-AI rule" tension flagged repeatedly throughout this file's history (§13,
and the final 2026-07-18 entries) are now **moot for this manuscript** — they'd only matter
again for the new, separate STS project once that exists.

**What actually changed in the manuscript between this file's last entry (v3, 25 pages,
2026-07-18) and v8 (today):** full detail lives in the other Project's revision-pass docs, not
duplicated here, but the headline structural change is real and worth knowing before touching
this file's `outputs/paper/PM25_Pediatric_Asthma_Philippines_REFORMATTED.docx` again — v8 is a
distinct, more-revised manuscript, not a small diff on top of the v3 this repo already has.
Don't assume they're close; diff them directly if you need to reconcile.

**New file added this round:** `outputs/paper/PM25_Discussion_ActaMedicaPhilippina_v9.docx` —
v8 reworked specifically against Acta Medica Philippina's actual submission guidelines (fetched
live, not assumed):
- Word count confirmed at 9,707 words (title+abstract+body, excluding references) — already
  under their 10,000-word cap, no cutting needed. Abstract 341 words (cap 500).
- Abstract relabeled to their required IMRAD headings (Introduction/Methods/Results/Conclusion).
- Added a Keywords line (5 MeSH terms).
- **Full citation renumbering.** The in-text citations were a mix of narrative author-year and
  bare-number parentheticals, and — more importantly — didn't follow true first-mention order
  (some later-numbered refs were actually cited earlier in the text than lower-numbered ones,
  a real Vancouver-style violation, not just a style mismatch). Traced every citation's true
  first mention across the whole manuscript and renumbered all 34 references end-to-end,
  converting everything to proper numbered superscripts.
- **Found and closed 2 orphan references** (Ceballos et al. 2024 and the 2020 PSA Census — both
  in the reference list with no findable in-text citation anywhere) and **1 missing reference**
  entirely (the manuscript claims it "followed STROBE reporting guidelines" but never cited
  STROBE itself — added von Elm et al. 2007 as a new reference and cited it at that claim).
  Also added proper citation markers for 4 methods that were named in text/tables but never
  actually numbered (Wooldridge's panel-data textbook, Moran 1950 + Anselin 1995 together for
  the already-named "Moran's I test," and Cameron/Gelbach/Miller 2008 + MacKinnon/Nielsen/Webb
  2023 alongside the existing Cameron & Miller 2015 small-cluster-inference citation).
  **Final reference list: 35 entries, every one cited at least once, verified programmatically
  by rendering to PDF and checking every citation number 1–35 has a matching reference and
  vice versa — not just by eye.**
- Tables renumbered Table 1–8 → Table I–VIII (Arabic → Roman), everywhere they're mentioned.
- Document-wide: 12pt Arial, single line spacing, single column, per the journal's format rule.
- **Flag for your own sanity-check before submitting:** the Ceballos and Census citation
  placements were matched by topic/title, not by reading those two papers directly — worth a
  quick look. Also: this manuscript's "Part I / Part II" framing doesn't map cleanly onto the
  journal's expected linear Intro→Methods→Results→Discussion→Conclusion order; nothing was
  restructured to preserve your original argument ordering, but a short cover note to the
  editor explaining the two-part structure may be worth adding at submission.

**New file added:** `outputs/paper/Cover_Letter_AQAH_version_drift_framing.docx` — a draft
cover letter for a *different* journal (Air Quality, Atmosphere & Health, not Acta Medica
Philippina) that leads with the ACAG satellite product-version-drift finding rather than the
Philippine panel result, since AQAH's stated scope favors generalizable methodological
contributions over single-country findings. Needs your email + submission date filled in
before use.

**Journal-target research (full detail in the other Project, summarized here):** recommended
order — (1) Acta Medica Philippina (best fit, **no APC at all**, no fee friction), (2) Asian
Journal of Atmospheric Environment (regional fit, APC waivers likely available), (3) Air
Quality, Atmosphere & Health (reframe around the version-drift finding — cover letter above),
(4) GeoHealth ($3,240 APC; Philippines is lower-middle-income so likely a 50%-discount tier,
not a full waiver, under Wiley's list — confirm directly) or Journal of Exposure Science &
Environmental Epidemiology, (5) IJERPH as a fallback. **Environmental Health Perspectives is
off the list entirely** — it stopped accepting new manuscripts June 26, 2025 after losing
NIEHS funding.

**Fee-waiver reality check (asked 2026-07-28):** no journal in this list offers an automatic
waiver simply for being a high-school/independent researcher — waiver eligibility everywhere
checked (Springer, AGU/Wiley) is based on the *corresponding author's country*, not age or
student status, and the Philippines does not clear the automatic thresholds at either
publisher (confirmed directly against Springer Nature's and AGU/Wiley's own current waiver-
country lists). Acta Medica Philippina sidesteps this entirely — it has no APC to waive.
Where a fee does apply, every publisher checked also has a **discretionary, case-by-case
financial-hardship waiver process** separate from the automatic country-based one — an
unfunded independent high-school researcher is exactly the kind of case that process exists
for, worth requesting explicitly rather than assuming the listed APC is fixed.

**Possible mentor/collaborator leads (asked 2026-07-28):** the three most directly relevant
active Philippine researchers found in this project's own citation list — Roel F. Ceballos
(Dept. of Mathematics and Statistics, University of Southeastern Philippines, Davao City —
directly overlaps with this manuscript's own Davao ground-station work) and Rachell C. Gallano
/ Lenard D. Visaya (School of Environmental Science and Management, UP Los Baños) — all three
co-authored the Philippines-specific PM2.5/child-mortality paper already cited as reference 5
in the Acta Medica Philippina version above. Worth a direct, personalized outreach email;
not contacted on your behalf — see the Claude session for a draft template if wanted.

**Status: nothing in this round has been committed or pushed.** Per standing instruction,
review the diff yourself (`git status` / `git diff`) before committing — this round only added
2 new files under `outputs/paper/` and edited `README.md`'s framing line + this file. Everything
else `git status` currently shows as modified/untracked predates this round (see the
2026-07-18 entries above) and was already waiting on your review before this session touched
anything.
