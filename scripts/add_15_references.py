"""
add_15_references.py
======================
Adds the user's 15 new, pre-verified references to the manuscript. Ground-
truthed against the CURRENT manuscript state first (not assumed):

- scripts/robustness_upgrades.py does not exist anywhere in this repo
  (checked root, archive/, everywhere) -- same finding as the original
  session. No .bib/.enl/.ris/Zotero export exists either; the only
  bibliography is the plain numbered list at the end of the .docx.
- Refs 9-15 (Cameron/Gelbach/Miller 2008, Hausman 1978, Swamy & Arora 1972,
  VanderWeele & Ding 2017, Wooldridge 2010, Greenland/Pearl/Robins 1999,
  Moran 1950) were ALREADY added and cited in a prior session -- confirmed
  by reading the doc, not assumed. 7 of this round's 15 requested refs are
  duplicates of those; they get DOIs added (the user now supplied DOIs
  that weren't in hand before) rather than being re-added.
- In-text citation style audit (done by regex-scanning every paragraph,
  not by memory): the manuscript currently mixes THREE styles --
  bracket-number "(1,2)" / "(4,5)" for refs 1-5, prose-only-no-pointer for
  refs 6-7 (GBD, ACAG -- named in prose, never given an explicit inline
  citation marker at all), and name-year "(Author, Year)" for ref 8 onward.
  By raw count, name-year is already the majority (8 of 12 in-text citation
  points) and is the style every check added this session already uses, so
  all new insertions below use name-year, per the user's "match the
  majority, don't add a third style" instruction. Ref 3 (Gallano 2024) is
  a PRE-EXISTING orphan -- named in the reference list, never cited in
  text -- not introduced by this script, but worth flagging back to the
  user (done in the chat reply, not silently left for them to discover).

Analysis-implementation ground truth (checked against the manuscript body,
not assumed from memory): wild cluster bootstrap, leave-one-region-out
jackknife, COVID exclusion, lag/rolling-mean, Hausman test, MDE, DAG, and
E-value are ALL implemented and already in the manuscript. The
placebo/negative-control test and population-weighted aggregation are
NOT implemented (still pending a GBD export and adequate population data,
respectively -- see START_HERE.md). This determines which of the 8
genuinely new references get a real in-text home vs. an honest
"not performed here" pointer vs. reference-list-only orphan status:

  - Bloom (1995)                    -> real home: MDE subsection (MDE IS implemented)
  - MacKinnon/Nielsen/Webb (2023)   -> real home: WCR bootstrap subsection (WCR IS implemented)
  - Haneuse/VanderWeele/Arterburn (2019) -> real home: E-value paragraph (E-value IS implemented)
  - Robinson (1950)                 -> real home: Limitations' ecological-study sentence
                                        (this claim is already in the manuscript, just uncited)
  - Ivy/Mulholland/Russell (2008)   -> honest "not performed here" pointer in Limitations
                                        (population weighting was NOT run -- this cites what
                                        the correct method would be, without claiming it was used)
  - Textor et al. (2016), dagitty   -> honest "not performed here" pointer in the DAG paragraph
                                        (the DAG was hand-built, not verified with dagitty's
                                        d-separation tooling)
  - Anselin (1995), LISA            -> honest "not performed here" pointer in the Moran's I
                                        subsection (only the GLOBAL statistic was computed, not
                                        local/per-region LISA)
  - Lipsitch/Tchetgen Tchetgen/Cohen (2010) -> TRUE ORPHAN, reference-list only. The negative-
                                        control/placebo check was never run (no musculoskeletal/
                                        sense-organ GBD outcome in the repo), and there's no
                                        honest way to attach this citation to the existing
                                        multi-outcome analysis (Table 4) without misrepresenting
                                        it -- that analysis uses 4 PLAUSIBLE respiratory/cancer
                                        outcomes, not a true negative control, which specifically
                                        requires an IMPLAUSIBLE outcome. Flagged, not forced in.
"""

import docx
from docx.shared import Pt, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH

PATH = "outputs/paper/PM25_Pediatric_Asthma_Philippines_REFORMATTED.docx"
FONT = "Times New Roman"

doc = docx.Document(PATH)


def find_para(text_exact=None, text_startswith=None, text_contains=None):
    for p in doc.paragraphs:
        t = p.text.strip()
        if text_exact is not None and t == text_exact:
            return p
        if text_startswith is not None and t.startswith(text_startswith):
            return p
        if text_contains is not None and text_contains in t:
            return p
    raise ValueError(f"paragraph not found: {text_exact or text_startswith or text_contains}")


def style_run(run, size=11, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    return run


def replace_in_runs(para, old, new, required=True):
    hit = False
    for r in para.runs:
        if old in r.text:
            r.text = r.text.replace(old, new)
            hit = True
    if required and not hit:
        raise ValueError(f"text not found in paragraph: {old!r}")
    return hit


# ─────────────────────────────────────────────────────────────────────────
# 1. IN-TEXT CITATIONS FOR THE 4 REFERENCES WITH A REAL, ALREADY-DONE HOME
# ─────────────────────────────────────────────────────────────────────────

# 1a. MacKinnon, Nielsen & Webb (2023) -- alongside the WCR bootstrap citation
wcr_para = find_para(text_contains="the wild cluster bootstrap, restricted version")
replace_in_runs(
    wcr_para,
    "(WCR; Cameron, Gelbach & Miller, 2008), one of the most widely recommended",
    "(WCR; Cameron, Gelbach & Miller, 2008; MacKinnon, Nielsen & Webb, 2023), "
    "one of the most widely recommended",
)

# 1b. Bloom (1995) -- alongside the MDE citation
mde_para = find_para(text_contains="we calculated the minimum detectable effect (MDE)")
replace_in_runs(
    mde_para,
    "we calculated the minimum detectable effect (MDE) implied by",
    "we calculated the minimum detectable effect (MDE; Bloom, 1995) implied by",
)

# 1c. Haneuse, VanderWeele & Arterburn (2019) -- alongside the E-value citation
evalue_para = find_para(text_startswith="As a complementary, approximate quantification")
replace_in_runs(
    evalue_para,
    "we calculated an E-value (VanderWeele & Ding, 2017) for the pooled",
    "we calculated an E-value (VanderWeele & Ding, 2017; Haneuse, VanderWeele & "
    "Arterburn, 2019) for the pooled",
)

# 1d. Robinson (1950) -- the ecological-fallacy sentence in Limitations, which
# already makes exactly this claim but had no citation attached
limitations_para = find_para(text_startswith="Several limitations must be acknowledged")
replace_in_runs(
    limitations_para,
    "regional-level associations cannot be attributed to individuals, and correlation",
    "regional-level associations cannot be attributed to individuals (Robinson, 1950), "
    "and correlation",
)

print("Fix 1 applied: 4 real-home citations added (MacKinnon/Nielsen/Webb, Bloom, "
      "Haneuse/VanderWeele/Arterburn, Robinson).")

# ─────────────────────────────────────────────────────────────────────────
# 2. HONEST "NOT PERFORMED HERE" POINTERS FOR 3 REFERENCES WHOSE UPGRADE
#    WASN'T ACTUALLY RUN (population weighting, dagitty-verified DAG, LISA)
# ─────────────────────────────────────────────────────────────────────────

# 2a. Ivy, Mulholland & Russell (2008) -- population-weighting Limitations sentence
replace_in_runs(
    limitations_para,
    "was judged insufficient to redo the aggregation credibly for the full "
    "panel. ",
    "was judged insufficient to redo the aggregation credibly for the full "
    "panel (see Ivy, Mulholland & Russell, 2008, for standard population-weighted "
    "exposure-metric methodology, which was not applied here). ",
)

# 2b. Textor et al. (2016), dagitty -- DAG paragraph
dag_para = find_para(text_startswith="Figure 9 lays out the argument")
replace_in_runs(
    dag_para,
    "or socioeconomic shifts within a region over time (already named "
    "in Limitations) — remains open.",
    "or socioeconomic shifts within a region over time (already named "
    "in Limitations) — remains open. A formal d-separation check of this "
    "graph using dedicated software (e.g. the dagitty R package; Textor et al., "
    "2016) was not performed here; the DAG above is a descriptive summary of the "
    "argument, not a software-verified causal model.",
)

# 2c. Anselin (1995), LISA -- Moran's I subsection
morans_para = find_para(text_contains="We tested this using Moran")
replace_in_runs(
    morans_para,
    "supporting the validity of region-clustered (rather than spatially "
    "adjusted) standard errors for this dataset.",
    "supporting the validity of region-clustered (rather than spatially "
    "adjusted) standard errors for this dataset. This tests only global spatial "
    "autocorrelation; local indicators of spatial association (LISA; Anselin, "
    "1995), which could identify whether any individual region drives a spatial "
    "pattern the global statistic would miss, were not computed, since the global "
    "result gave no overall signal to localize.",
)

print("Fix 2 applied: 3 honest 'not performed here' pointers added (Ivy/Mulholland/"
      "Russell, Textor et al., Anselin) -- none claim an unrun analysis was applied.")

doc.save(PATH)
print("\nSaved (in-text citations)", PATH)
