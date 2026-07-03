import pandas as pd
import glob
import os

PROVINCE_TO_REGION = {
    # NCR — GBD calls it this, not "Metro Manila"
    "National Capital Region": "NCR",
    # CAR
    "Abra": "CAR", "Apayao": "CAR", "Benguet": "CAR",
    "Ifugao": "CAR", "Kalinga": "CAR", "Mountain Province": "CAR",
    # Region I
    "Ilocos Norte": "Region I", "Ilocos Sur": "Region I",
    "La Union": "Region I", "Pangasinan": "Region I",
    # Region II
    "Batanes": "Region II", "Cagayan": "Region II",
    "Isabela": "Region II", "Nueva Vizcaya": "Region II",
    "Quirino": "Region II",
    # Region III
    "Aurora": "Region III", "Bataan": "Region III",
    "Bulacan": "Region III", "Nueva Ecija": "Region III",
    "Pampanga": "Region III", "Tarlac": "Region III",
    "Zambales": "Region III",
    # Region IV-A
    "Batangas": "Region IV-A", "Cavite": "Region IV-A",
    "Laguna": "Region IV-A", "Quezon": "Region IV-A",
    "Rizal": "Region IV-A",
    # Region IV-B
    "Marinduque": "Region IV-B", "Occidental Mindoro": "Region IV-B",
    "Oriental Mindoro": "Region IV-B", "Palawan": "Region IV-B",
    "Romblon": "Region IV-B",
    # Region V
    "Albay": "Region V", "Camarines Norte": "Region V",
    "Camarines Sur": "Region V", "Catanduanes": "Region V",
    "Masbate": "Region V", "Sorsogon": "Region V",
    # Region VI
    "Aklan": "Region VI", "Antique": "Region VI",
    "Capiz": "Region VI", "Guimaras": "Region VI",
    "Iloilo": "Region VI", "Negros Occidental": "Region VI",
    # Region VII
    "Bohol": "Region VII", "Cebu": "Region VII",
    "Negros Oriental": "Region VII", "Siquijor": "Region VII",
    # Region VIII — GBD uses "Samar (Western Samar)"
    "Biliran": "Region VIII", "Eastern Samar": "Region VIII",
    "Leyte": "Region VIII", "Northern Samar": "Region VIII",
    "Samar": "Region VIII", "Samar (Western Samar)": "Region VIII",
    "Southern Leyte": "Region VIII",
    # Region IX — GBD capitalizes "Del"
    "Zamboanga del Norte": "Region IX", "Zamboanga Del Norte": "Region IX",
    "Zamboanga del Sur": "Region IX",  "Zamboanga Del Sur": "Region IX",
    "Zamboanga Sibugay": "Region IX",
    # Region X — GBD capitalizes "Del"
    "Bukidnon": "Region X", "Camiguin": "Region X",
    "Lanao del Norte": "Region X", "Lanao Del Norte": "Region X",
    "Misamis Occidental": "Region X", "Misamis Oriental": "Region X",
    # Region XI — GBD capitalizes "Del"
    "Compostela Valley": "Region XI", "Davao de Oro": "Region XI",
    "Davao del Norte": "Region XI", "Davao Del Norte": "Region XI",
    "Davao del Sur": "Region XI",   "Davao Del Sur": "Region XI",
    "Davao Occidental": "Region XI", "Davao Oriental": "Region XI",
    # Region XII — GBD uses "Cotabato (North Cotabato)"
    "Cotabato": "Region XII", "Cotabato (North Cotabato)": "Region XII",
    "Sarangani": "Region XII", "South Cotabato": "Region XII",
    "Sultan Kudarat": "Region XII",
    # Region XIII — GBD capitalizes "Del"
    "Agusan del Norte": "Region XIII", "Agusan Del Norte": "Region XIII",
    "Agusan del Sur": "Region XIII",  "Agusan Del Sur": "Region XIII",
    "Dinagat Islands": "Region XIII",
    "Surigao del Norte": "Region XIII", "Surigao Del Norte": "Region XIII",
    "Surigao del Sur": "Region XIII",  "Surigao Del Sur": "Region XIII",
    # BARMM
    "Basilan": "BARMM", "Lanao del Sur": "BARMM", "Lanao Del Sur": "BARMM",
    "Maguindanao": "BARMM", "Sulu": "BARMM", "Tawi-Tawi": "BARMM",
    "Maguindanao del Norte": "BARMM", "Maguindanao del Sur": "BARMM",
}


def aggregate_gbd_outcome(input_path, outcome_name, value_col=None, out_dir="data/processed"):
    """
    Aggregate a province-level GBD outcome file into a 17-region annual panel.

    Parameters
    ----------
    input_path : str
        Path to the raw GBD CSV (province-level, one cause_name/measure_name).
    outcome_name : str
        Short slug used for the output filename and, by default, the value
        column name (e.g. "asthma" -> data/processed/asthma_regional_panel.csv).
    value_col : str, optional
        Name for the aggregated value column. Defaults to
        "{outcome_name}_rate_per100k".
    out_dir : str
        Output directory for the regional panel CSV.

    Returns
    -------
    (pandas.DataFrame, str) : the regional panel and the path it was written to.
    """
    value_col = value_col or f"{outcome_name}_rate_per100k"

    gbd_files = glob.glob(input_path)
    if not gbd_files:
        print(f"ERROR: Cannot find GBD file matching {input_path!r} for outcome {outcome_name!r}.")
        return None, None

    df = pd.read_csv(gbd_files[0])
    df = df[df["location_name"] != "Philippines"].copy()

    unmatched = set(df["location_name"].unique()) - set(PROVINCE_TO_REGION.keys())
    if unmatched:
        print(f"  [{outcome_name}] Still unmatched (will be dropped): {sorted(unmatched)}")
    else:
        print(f"  [{outcome_name}] All provinces matched successfully.")

    df["region"] = df["location_name"].map(PROVINCE_TO_REGION)
    df_matched = df[df["region"].notna()].copy()

    regional = (
        df_matched.groupby(["region", "year"])["val"]
        .mean()
        .reset_index()
        .rename(columns={"val": value_col})
    )

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{outcome_name}_regional_panel.csv")
    regional.to_csv(out_path, index=False)

    print(f"  [{outcome_name}] Shape: {regional.shape}  (should be 170 = 17 regions × 10 years)")
    print(f"  [{outcome_name}] Regions ({len(regional['region'].unique())}): {sorted(regional['region'].unique())}")
    print(f"  [{outcome_name}] Wrote {out_path}")

    return regional, out_path


if __name__ == "__main__":
    # (raw GBD file glob, outcome slug, value column name)
    OUTCOMES = [
        ("data/raw/gbd/IHME-GBD_2023_DATA-fa7d3ed4-1.csv", "asthma", "asthma_rate_per100k"),
        ("data/raw/gbd/gbd_lung_cancer_incidence.csv",      "lung_cancer_incidence",  None),
        ("data/raw/gbd/gbd_lri_incidence.csv",               "lri_incidence",          None),
        ("data/raw/gbd/gbd_copd_prevalence.csv",             "copd_prevalence",        None),
        ("data/raw/gbd/gbd_respiratory_mortality.csv",       "respiratory_mortality",  None),
    ]

    print(f"Aggregating {len(OUTCOMES)} GBD outcomes to regional panels...\n")
    for input_path, outcome_name, value_col in OUTCOMES:
        print(f"--- {outcome_name} ---")
        aggregate_gbd_outcome(input_path, outcome_name, value_col=value_col)
        print()
