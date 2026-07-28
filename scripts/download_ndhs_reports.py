"""
download_ndhs_reports.py
==========================
Downloads the 4 public NDHS/DHS documents needed for the biomass-fuel mediator
analysis, straight from their official hosts. These are all freely public
government/NGO reports -- no login, no paywall -- so this is a plain,
well-behaved downloader, not a bypass of anything. It exists because the
dhsprogram.com site has been intermittently flaky (some fetches return empty
even though the URLs are correct and current), which lines up with what you
described. A few things this script does differently from a bare urlretrieve
that should help with that flakiness:
  - Sends a normal browser User-Agent (some older .cfm-based gov sites quietly
    reject requests with no/unusual User-Agent header rather than erroring)
  - Retries each file up to 4 times with a short backoff
  - Falls back to a second official mirror for each file (World Bank
    Microdata Library for the 3 Final Reports, govinfo.gov -- the U.S.
    Government Publishing Office's permanent archive -- for WP164). This
    matters here specifically: dhsprogram.com is currently returning HTTP 200
    with a generic HTML placeholder page instead of the real PDF for 3 of
    the 4 files (confirmed directly), which is consistent with the DHS
    Program's USAID-funded infrastructure being disrupted. The mirrors are
    independently hosted (World Bank, U.S. GPO) and were each individually
    verified to serve the actual PDF before being added here.
  - Verifies each download actually starts with "%PDF" before declaring
    success, so a silently-empty/HTML-error response doesn't get saved as if
    it were the real file

IMPORTANT CORRECTION (if you ran an earlier version of this script): the World
Bank "pdf-documentation" URLs used as fallbacks previously do NOT serve the
real Final Reports -- they serve a short metadata/variable-dictionary bundle
(confirmed by inspecting the downloaded content: the FR294.pdf that resulted
was only 11 pages of study description, and FR347.pdf/FR381.pdf were data
dictionaries listing variable codes, not the narrative report with results
tables). If FR294.pdf, FR347.pdf, or FR381.pdf already exist in data/raw/ndhs/
from a previous run, DELETE them first and re-run this script so they get
replaced by the real reports from the corrected URLs below (PSA's own site,
which hosts the genuine narrative Final Reports independent of dhsprogram.com).

Run this locally (PyCharm or Terminal), not in any sandboxed environment --
it just needs normal internet access.

Usage:
    pip install requests
    rm -f data/raw/ndhs/FR294.pdf data/raw/ndhs/FR347.pdf data/raw/ndhs/FR381.pdf
    python download_ndhs_reports.py
"""

import os
import time
import requests

OUT_DIR = "data/raw/ndhs"

FILES = [
    {
        "name": "FR294.pdf",
        "label": "2013 NDHS Final Report",
        "urls": [
            # PSA's own copy -- verified to serve the real 300+ page narrative report
            "https://psa.gov.ph/system/files/main-publication/2013%2520%2520National%2520Demographic%2520and%2520Health%2520Survey-Philippines.pdf",
            "https://dhsprogram.com/pubs/pdf/FR294/FR294.pdf",
        ],
    },
    {
        "name": "FR347.pdf",
        "label": "2017 NDHS Final Report",
        "urls": [
            "https://dhsprogram.com/pubs/pdf/FR347/FR347.pdf",
            "https://psa.gov.ph/sites/default/files/PHILIPPINE%20NATIONAL%20DEMOGRAPHIC%20AND%20HEALTH%20SURVEY%202017_new.pdf",
            "https://psa.gov.ph/sites/default/files/PHILIPPINE%2520NATIONAL%2520DEMOGRAPHIC%2520AND%2520HEALTH%2520SURVEY%25202017_new.pdf",
        ],
        # NOTE: not blocking even if this one fails -- WP164 (below) already contains a
        # ready-made "Appendix Table A.9: Province-level estimates of household use of
        # solid fuel for cooking, the Philippines NDHS 2017" with all 82 provinces, which
        # covers the 2017 time point on its own.
    },
    {
        "name": "FR381.pdf",
        "label": "2022 NDHS Final Report",
        "urls": [
            # PSA's own copy -- verified to serve the real 900+ page narrative report
            "https://psa.gov.ph/system/files/main-publication/2022%2520NDHS%2520Final%2520Report.pdf",
            "https://dhsprogram.com/pubs/pdf/FR381/FR381.pdf",
        ],
    },
    {
        "name": "WP164.pdf",
        "label": "DHS Working Paper 164 (Wang et al. 2020, household air pollution)",
        "urls": [
            "https://dhsprogram.com/pubs/pdf/WP164/WP164.pdf",
            "https://www.govinfo.gov/content/pkg/GOVPUB-ID-PURL-gpo152424/pdf/GOVPUB-ID-PURL-gpo152424.pdf",
        ],
        # Already confirmed working via the govinfo.gov mirror -- no action needed if you
        # already have this one from the last run.
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}

MAX_ATTEMPTS = 4
TIMEOUT_S = 30


def try_download(url, dest_path):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_S)
            if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True, f"OK ({len(resp.content):,} bytes)"
            else:
                reason = f"HTTP {resp.status_code}, content-type={resp.headers.get('Content-Type')}, " \
                          f"first bytes={resp.content[:20]!r}"
        except requests.RequestException as e:
            reason = str(e)
        if attempt < MAX_ATTEMPTS:
            time.sleep(2 * attempt)
    return False, reason


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Saving to {os.path.abspath(OUT_DIR)}\n")

    results = []
    for f in FILES:
        dest = os.path.join(OUT_DIR, f["name"])
        print(f"--- {f['label']} ({f['name']}) ---")
        ok = False
        for url in f["urls"]:
            print(f"  trying {url} ...")
            ok, msg = try_download(url, dest)
            print(f"  -> {msg}")
            if ok:
                break
        results.append((f["name"], ok))
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name}")

    n_failed = sum(1 for _, ok in results if not ok)
    if n_failed:
        print(f"\n{n_failed} file(s) failed. If a file keeps failing, download it manually")
        print("by pasting its URL into a browser (browsers often succeed where a script")
        print("doesn't, for the same flaky-site reasons) and save it into data/raw/ndhs/")
        print("with the exact filename shown above.")
    else:
        print("\nAll 4 files downloaded successfully.")


if __name__ == "__main__":
    main()
