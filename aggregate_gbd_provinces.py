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

gbd_files = glob.glob("data/raw/gbd/IHME-GBD_2023_DATA-fa7d3ed4-1.csv")
if not gbd_files:
    print("ERROR: Cannot find province GBD file.")
    exit(1)

df = pd.read_csv(gbd_files[0])
df = df[df["location_name"] != "Philippines"].copy()

unmatched = set(df["location_name"].unique()) - set(PROVINCE_TO_REGION.keys())
if unmatched:
    print(f"Still unmatched (will be dropped): {sorted(unmatched)}")
else:
    print("All provinces matched successfully.")

df["region"] = df["location_name"].map(PROVINCE_TO_REGION)
df_matched = df[df["region"].notna()].copy()

regional = (
    df_matched.groupby(["region", "year"])["val"]
    .mean()
    .reset_index()
    .rename(columns={"val": "asthma_rate_per100k"})
)

os.makedirs("data/processed", exist_ok=True)
regional.to_csv("data/processed/asthma_regional_panel.csv", index=False)

print(f"\nShape: {regional.shape}  (should be 170 = 17 regions × 10 years)")
print(f"Regions ({len(regional['region'].unique())}): {sorted(regional['region'].unique())}")
print(f"\nFirst 20 rows:")
print(regional.head(20).to_string(index=False))
