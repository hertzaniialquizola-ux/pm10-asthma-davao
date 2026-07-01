"""
clip_davao_acag.py

Purpose: Extract Davao City satellite PM2.5 (ACAG V6GL03) for 2020-2024,
to compare against ground-station data in davao_emb_pollution.csv.

BEFORE RUNNING:
1. Confirm these 5 files exist in data/raw/acag/davao_validation/:
   V6GL03.CNNPM25.0p10....202012.nc  (2020)
   V6GL03.CNNPM25.0p10....202112.nc  (2021)
   V6GL03.CNNPM25.0p10....202212.nc  (2022)
   V6GL03.CNNPM25.0p10....202312.nc  (2023)
   V6GL03.CNNPM25.0p10....202412.nc  (2024)
   (exact filenames may differ slightly - the glob below will find them)

2. Download a Davao City boundary shapefile:
   https://gadm.org/download_country.html -> Philippines -> Shapefile, Level 2
   (try Level 3 if Davao City isn't a separate polygon at Level 2)
   Place in: data/raw/shapefiles/

3. Install packages if needed:
   pip install xarray netCDF4 geopandas shapely

STEP 1 - run with CHECK_ONLY = False first to confirm variable names and
the shapefile's name column before trusting any numbers.
"""

import glob
import re
import xarray as xr
import geopandas as gpd
import numpy as np

# ---- CONFIG - edit these paths if yours differ ----
ACAG_DIR = "data/raw/acag/davao_validation"
SHAPEFILE_PATH = "data/raw/shapefiles/gadm41_PHL_shp/gadm41_PHL_2.shp" # adjust level/filename as needed
NAME_COLUMN_GUESS = ["NAME_2", "NAME_3", "NAME_1"]  # script will try these in order
CITY_NAME_MATCH = "Davao"  # will do a case-insensitive "contains" match
OUTPUT_CSV = "data/processed/davao_acag_satellite.csv"

CHECK_ONLY = False  # <-- set to False once Step 1 output looks right

# ---- STEP 1: inspect files before trusting anything ----
nc_files = sorted(glob.glob(f"{ACAG_DIR}/*.nc"))
print(f"Found {len(nc_files)} .nc files in {ACAG_DIR}:")
for f in nc_files:
    print(" ", f)

if len(nc_files) == 0:
    raise SystemExit("No .nc files found - check ACAG_DIR path above.")

print("\n--- Inspecting first file's variables ---")
ds0 = xr.open_dataset(nc_files[0])
print(ds0)
print("\nVariable names:", list(ds0.data_vars))
print("Coordinate names:", list(ds0.coords))
ds0.close()

print("\n--- Inspecting shapefile ---")
gdf = gpd.read_file(SHAPEFILE_PATH)
print("Columns:", list(gdf.columns))
found_col = None
for col in NAME_COLUMN_GUESS:
    if col in gdf.columns:
        matches = gdf[gdf[col].str.contains(CITY_NAME_MATCH, case=False, na=False)]
        if len(matches) > 0:
            print(f"\nMatches in column '{col}':")
            print(matches[[col]])
            found_col = col
            break

if found_col is None:
    print(f"\nNo column matched '{CITY_NAME_MATCH}' automatically.")
    print("Look through gdf.columns and gdf.head() manually to find the right")
    print("column and exact name for Davao City, then edit NAME_COLUMN_GUESS")
    print("and CITY_NAME_MATCH above.")

if CHECK_ONLY:
    print("\n=== CHECK_ONLY is True. Review output above, fix config as needed, ===")
    print("=== then set CHECK_ONLY = False and re-run for real extraction.   ===")
    raise SystemExit(0)

# ---- STEP 2: real extraction (only runs if CHECK_ONLY = False) ----

# EDIT THESE after confirming from Step 1 output:
PM25_VAR_NAME = "PM25"# <-- confirm/replace from ds0.data_vars above
LAT_NAME = "lat"              # <-- confirm from ds0.coords above
LON_NAME = "lon"              # <-- confirm from ds0.coords above
NAME_COL = found_col if found_col else "NAME_2"
EXACT_CITY_NAME = "Davao City"        # <-- set to exact string from Step 1 match, e.g. "City of Davao"

if EXACT_CITY_NAME is None:
    raise SystemExit("Set EXACT_CITY_NAME to the exact matched name from Step 1 before running.")

city_poly = gdf[gdf[NAME_COL] == EXACT_CITY_NAME].geometry.union_all()
minx, miny, maxx, maxy = city_poly.bounds
print(f"Davao City bounding box: lon [{minx:.3f}, {maxx:.3f}], lat [{miny:.3f}, {maxy:.3f}]")

results = []

year_pattern = re.compile(r"(\d{4})\d{2}-\d{4}\d{2}")

for f in nc_files:
    m = year_pattern.search(f)
    year = int(m.group(1)) if m else None

    ds = xr.open_dataset(f)
    pm25 = ds[PM25_VAR_NAME]

    # Subset to a bounding box around Davao first (fast), then check point-in-polygon
    sub = pm25.sel({LAT_NAME: slice(miny - 0.2, maxy + 0.2),
                    LON_NAME: slice(minx - 0.2, maxx + 0.2)})

    lats = sub[LAT_NAME].values
    lons = sub[LON_NAME].values
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    from shapely.geometry import Point
    mask = np.zeros(lon_grid.shape, dtype=bool)
    for i in range(lon_grid.shape[0]):
        for j in range(lon_grid.shape[1]):
            if city_poly.contains(Point(lon_grid[i, j], lat_grid[i, j])):
                mask[i, j] = True

    n_pixels = mask.sum()
    if n_pixels == 0:
        print(f"WARNING: {year} - no grid cells fell inside Davao City polygon. "
              "City may be smaller than one 0.1-degree pixel; consider using "
              "the nearest single pixel or a small buffer around the city centroid instead.")
        mean_val = np.nan
    else:
        vals = sub.values.squeeze()[mask]
        mean_val = float(np.nanmean(vals))

    print(f"{year}: {n_pixels} pixels, mean PM2.5 = {mean_val:.3f} ug/m3" if n_pixels else f"{year}: no pixels")
    results.append({"year": year, "davao_pm25_satellite_ugm3": mean_val, "n_pixels": n_pixels})
    ds.close()

import pandas as pd
out_df = pd.DataFrame(results).sort_values("year")
out_df.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved: {OUTPUT_CSV}")
print(out_df)
