# START HERE — PM2.5 & Pediatric Asthma Project (Status v5)

_Project memory file. Read RESEARCH_INSTRUCTIONS.md first, then this. This supersedes all
earlier status notes (Md_file, Start_md v2/v3/v4). Update this file at the end of each session._

> **v5 headline (2026-06-18):** Pollution data is in (GBD PM2.5 SEV), the notebook runs
> end-to-end, the **analysis is DONE**, and a **full manuscript draft is built** (Word doc in
> `outputs/paper/`). Result is a **null finding** — no meaningful association between annual
> PM2.5 exposure and pediatric asthma prevalence once the shared time trend is removed. Numbers
> in **Section 10 — RESULTS**; manuscript status in **Section 7**. Two open items: GBD citation
> (ref 6) is a placeholder pending `citation.txt`, and refs 1–5 need verification. Nothing has
> been committed/pushed to GitHub yet.

GitHub repo: https://github.com/hertzaniialquizola-ux/pm10-asthma-davao

---

## 1. THE PROJECT (current, locked design)
**Air pollution and pediatric asthma in the Philippines (2013–2022), with Davao City as the
grounding case study.**

- Pediatric focus: ages **5–14** (the GBD age band).
- Relationship studied: **PM2.5 air pollution ↔ asthma prevalence** (annual correlation).
- Davao City = the framing / motivation / lived-experience anchor of the paper. It is NOT a
  data restriction anymore (see why below). The data series are national (Philippines).
- Time resolution: **annual trend, 2013–2022**. Seasonal/monthly was dropped because the
  data to support it does not exist.
- Design type: **ecological correlation.** Stated limitations: correlation ≠ causation,
  annual resolution, modeled (not measured) pollution, small n, and a very stable asthma rate.

---

## 2. THE BIG PIVOT — what changed from the original plan and why
The project STARTED as a Davao-City-specific, seasonal, PM10-vs-asthma study using the
CCHAIN dataset. That had to be abandoned because the data couldn't support it:

- `disease_lgu_disaggregated_totals.csv` → no Davao at all.
- `disease_pidsr_totals.csv` → Davao present, but only infectious diseases (dengue, typhoid,
  etc.). **Zero asthma rows.**
- `disease_fhsis_totals.csv` → no Davao.
- Cagayan de Oro (the fallback city) → asthma data far too sparse (2 cases, 5 months, no
  barangay geography).

**Conclusion:** CCHAIN cannot support an asthma study. The project was redesigned around
**GBD (Global Burden of Disease) data + a pollution series**, national-level, annual.
Davao stays as the narrative case study / motivation.

---

## 3. DONE & WORKING ✅
- Python environment set up: venv, Python 3.14.
- Packages installed: pandas, numpy, matplotlib, seaborn, scipy, statsmodels, jupyter.
- Working notebook in place: `notebooks/02_analysis_v2.ipynb`.
- Folder structure created: `data/raw/gbd`, `data/processed`, `outputs/figures`,
  `outputs/tables`.
- **GBD pediatric asthma data exported, downloaded, and loaded** ✅
  - File: `data/raw/gbd/IHME-GBD_2023_DATA-373d5433-1.csv`
  - Contents: Philippines, ages 5–14, both sexes, Prevalence, Rate, years 2013–2022.
  - Columns: `measure_name`, `age_name` (= "5-14 years"), `sex_name`, `cause_name`,
    `metric_name`, `year`, `val`, `upper`, `lower`.
  - **Key note:** the asthma rate is very stable across the decade (~7,448 → 7,598 per
    100,000). So a weak or flat correlation is a REAL, reportable finding — expected, not a
    failure. Do not try to force a strong result.
- **PM2.5 exposure data exported, downloaded, and loaded** ✅ (Option A, done 2026-06-18)
  - File: `data/raw/gbd/IHME-GBD_2023_DATA-b9d80ff9-1.csv`
  - Contents: Philippines, both sexes, **all ages**, measure = **Summary exposure value (SEV)**,
    risk = **Ambient particulate matter pollution**, years **2013–2022** (all 10 present).
  - Columns: same GBD layout as the asthma file but with `rei_name`/`rei_id` in place of
    `cause_name`/`cause_id`. Value column is `val`.
  - **CRITICAL UNITS NOTE:** SEV is a **0–100 risk-weighted exposure index**, NOT a µg/m³
    concentration. The notebook column is named `pm25_sev` and every axis/label says
    "SEV index (0-100)". The paper must describe this as **modeled exposure index**, not
    measured concentration. Old Open-Meteo µg/m³ plan is dead and removed.
- **Notebook runs end-to-end and analysis is complete** ✅ (2026-06-18)
  - Step 1 rewritten to **load PM2.5 from disk** (no more Open-Meteo API call).
  - Step 2b age filter fixed: `PED_AGES = ["5-14 years"]` (old `5-9`/`10-14` matched 0 rows).
  - Steps 4–6 updated to PM2.5-only (PM10 branch removed; GBD SEV export has no PM10).
  - Added **Step 4b** = detrend / first-differences robustness check.
  - Outputs saved: `outputs/figures/fig1_trends.png`, `outputs/figures/fig2_scatter_pm25.png`
    (both 300 dpi); `outputs/tables/results_annual.csv`,
    `outputs/tables/correlation_stats.csv`; processed CSVs in `data/processed/`.
  - **Tooling caveat:** the saved figures/tables were produced via an equivalent
    Pearson/Spearman implementation (t-based p-values + permutation check) because scipy
    wasn't available in that session and the `.venv` was macOS-built. The notebook itself
    still imports scipy — re-running it in PyCharm gives identical numbers.

---

## 4. PROBLEM (RESOLVED ✅) — the pollution data
The notebook's original Step 1 pulled Davao PM2.5/PM10 from the **Open-Meteo air-quality
API**, which only archives ~2 recent years (0 days for 2013–2021, ~150 days for 2022) and
could not provide a 2013–2022 trend. **Fixed** by switching to the GBD PM2.5 SEV export
(Option A below). The Open-Meteo cell has been replaced with a load-from-disk cell.

---

## 5. DECISION (DONE ✅) → Option A was used
**Got PM2.5 exposure from GBD itself** (same site/country/years as asthma, lines up on `year`).
Export filters used on https://vizhub.healthdata.org/gbd-results/ : GBD Estimate = Risk factor
exposure; Risk = Ambient particulate matter pollution; Measure = Summary exposure value;
Location = Philippines; Sex = Both; Age = All ages; Year = 2013–2022. Saved as
`data/raw/gbd/IHME-GBD_2023_DATA-b9d80ff9-1.csv`.

**Backups (not used, kept for validation if a reviewer asks):**
- **WHO Philippines file** — national annual PM2.5: https://data.humdata.org/dataset/who-data-for-phl
- **EMB-XI Annual Airshed Report (PDF)** — measured Davao PM10, a few years, manual extraction;
  validation cross-check only:
  https://r11.emb.gov.ph/wp-content/uploads/2024/02/Annual-Airshed-Status-Report-2023-1-31.pdf

---

## 6. NEXT STEPS (in order) — analysis pipeline is now DONE ✅
Steps 1–6 below are all complete (export, load-from-disk, merge, Pearson+Spearman, figures at
300 dpi, results tables). Remaining work is the **write-up** — see Section 7. Optional, only if
a reviewer pushes: cross-check against EMB-XI measured Davao PM10 for a validation paragraph.

Immediate next session:
1. Decide whether to commit the analysis to GitHub (commit was previewed but NOT pushed — user
   wanted to review first). NOTE: the new manuscript + `.gitignore` are also uncommitted.
2. Finish the two open items on the manuscript (see Section 7): paste the real GBD citation
   into ref 6, and verify refs 1–5.

---

## 7. MANUSCRIPT — DRAFT BUILT ✅ (2026-06-18)
**Full first draft assembled and saved as a Word document:**
`outputs/paper/PM25_pediatric_asthma_Philippines_2013-2022.docx`
- Title (retitled): "Modeled PM2.5 Exposure and Pediatric Asthma Prevalence in the
  Philippines, 2013–2022: An Ecological Time-Series Analysis with Davao City as a Case Study"
  — "Seasonal" and "PM10/Davao-only" dropped, as planned.
- Sections present: Title, Abstract, Research Question, Introduction, Methods, Results
  (with Figure 1 and Figure 2 embedded at their citations), Discussion, Limitations,
  Conclusion, References. ~9 pages, Times New Roman, 1.5 spacing, US Letter.
- Results and Limitations text is the user's own approved wording, used verbatim.
- **Fix 1 applied:** the age-mismatch sentence (pediatric 5–14 outcome vs all-ages SEV
  exposure) is appended to the end of the Limitations section.

**TWO ITEMS STILL OPEN on the manuscript:**
1. **GBD citation (Reference 6) is a PLACEHOLDER, not real.** The `citation.txt` that was
   supposed to accompany the GBD download is NOT in the repo (only `requirements.txt` exists).
   No GBD citation was invented (data-integrity rule). → Re-download from the GBD tool to
   regenerate `citation.txt`, then paste its exact text (release name + access date) over the
   italicized placeholder line for ref 6.
2. **References 1–5 still need the user's verification** (DOIs/PMCIDs and that each supports
   the sentence it's attached to) before submission. User said they will do this themselves.

Earlier drafted Title/Abstract/References/Appendix notes are superseded by this built draft.

---

## 8. KEY LINKS
| Source | URL | Use |
|---|---|---|
| GBD Results tool | https://vizhub.healthdata.org/gbd-results/ | Asthma (done) + PM2.5 exposure (next) |
| WHO PH (HDX) | https://data.humdata.org/dataset/who-data-for-phl | Backup PM2.5 series |
| EMB-XI report (PDF) | https://r11.emb.gov.ph/wp-content/uploads/2024/02/Annual-Airshed-Status-Report-2023-1-31.pdf | Measured-Davao validation cross-check |

## 9. KEY REFERENCES (verify before citing)
1. Ho et al. (2023) — Pediatric asthma Philippines. doi:10.1016/j.lanwpc.2023.100806
2. Yang et al. (2024) — Asthma trends Western Pacific 1990–2045. doi:10.2196/55327
3. Gallano et al. (2024) — PM2.5 + child respiratory illness Philippines (TCI-Thaijo).
4. Zhang et al. (2021) — PM + pediatric asthma exacerbation. PMC8312457
5. Ye et al. (2023) — PM10 + pediatric hospitalization. PMC9908005

---

## 10. RESULTS (final, 2026-06-18) — the headline finding
**Design as run:** ecological, national (Philippines), annual, 2013–2022, n = **10 yearly
points**. Exposure = GBD PM2.5 **SEV index (0–100)**, all ages, both sexes. Outcome = GBD
pediatric asthma **prevalence rate** (ages 5–14, per 100,000), both sexes.

**Correlation — levels (raw):**
- Pearson  r = **+0.470**, p = **0.170**
- Spearman r = **+0.394**, p = **0.260**
- (permutation check agrees: p ≈ 0.16 / 0.26)

**Correlation — detrended (year-over-year first differences, n = 9):**
- Pearson  r = **−0.100**, p = **0.799**
- Spearman r = **−0.133**, p = **0.732**

**CONCLUSION — NULL RESULT.** There is **no meaningful association** between annual PM2.5
exposure and pediatric asthma prevalence. The modest positive correlation in the levels is
**not statistically significant** (p = 0.17, n = 10) and, more tellingly, **collapses to ~0
(slightly negative) once the shared time trend is removed**. So the level correlation is
driven by a **common temporal trend** — PM2.5 exposure rises steadily (≈16.6 → 22.8) while the
asthma rate stays essentially flat (≈7,448 → 7,598 per 100,000) — not by any real link. This
is a legitimate, reportable finding, not a failure.

**Limitations to state in the paper:** ecological design (correlation ≠ causation); very small
n (10 annual points); exposure is a **modeled SEV index, not measured µg/m³**; annual (not
finer) resolution; and a near-flat asthma series with little variance to explain. The
confounding-by-time issue is exactly why the detrended check matters and should be reported.

**Output files (all under `outputs/`):** `figures/fig1_trends.png`,
`figures/fig2_scatter_pm25.png` (300 dpi); `tables/results_annual.csv`,
`tables/correlation_stats.csv`. Merged series in `data/processed/merged_annual.csv`.
