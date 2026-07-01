"""
check_version_effect.py

Purpose: isolate whether the gap between satellite PM2.5 and Davao ground
stations (found using V6GL03) is partly caused by the ACAG *version* change,
by re-running the same Davao City clip on the OLD V6GL02.04 files for the
three overlapping years (2020, 2021, 2022) already sitting in
data/raw/acag/Annual-selected/.

STEP 1: run with CHECK_ONLY = True first to confirm the old files' variable
name (may be 'CNNPM25' instead of 'PM25' - do not assume, check it).
"""

import glob
import re
import xarray as xr
import geopandas as gpd
import numpy as np
from shapely.geometry import Point

# ---- CONFIG ----
OLD_ACAG_DIR = "data/raw/acag/Annual-selected"
YEARS_TO_CHECK = ["2020", "2021", "2022"]
SHAPEFILE_PATH = "data/raw/shapefiles/gadm41_PHL_shp/gadm41_PHL_2.shp"
NAME_COL = "NAME_2"
EXACT_CITY_NAME = "Davao City"

CHECK_ONLY = False  # <-- set to False after confirming variable name below

# ---- STEP 1: find old files for these years, inspect variable name ----
all_old_files = sorted(glob.glob(f"{OLD_ACAG_DIR}/*.nc"))
old_files = [f for f in all_old_files if any(y in f for y in YEARS_TO_CHECK)]

print(f"Found {len(all_old_files)} total files in {OLD_ACAG_DIR}")
print(f"Matched {len(old_files)} files for years {YEARS_TO_CHECK}:")
for f in old_files:
    print(" ", f)

if len(old_files) == 0:
    raise SystemExit("No matching old-version files found - check YEARS_TO_CHECK "
                      "against actual filenames in Annual-selected/.")

print("\n--- Inspecting first matched file's variables ---")
ds0 = xr.open_dataset(old_files[0])
print("Variable names:", list(ds0.data_vars))
print("Coordinate names:", list(ds0.coords))
ds0.close()

if CHECK_ONLY:
    print("\n=== CHECK_ONLY is True. Confirm variable name above, edit ===")
    print("=== PM25_VAR_NAME below if needed, then set CHECK_ONLY = False. ===")
    raise SystemExit(0)

# ---- STEP 2: real extraction ----
PM25_VAR_NAME = "PM25"  # <-- EDIT if Step 1 showed a different name
LAT_NAME = "lat"           # <-- EDIT if different
LON_NAME = "lon"           # <-- EDIT if different

gdf = gpd.read_file(SHAPEFILE_PATH)
city_poly = gdf[gdf[NAME_COL] == EXACT_CITY_NAME].geometry.union_all()
minx, miny, maxx, maxy = city_poly.bounds

year_pattern = re.compile(r"(\d{4})\d{2}-\d{4}\d{2}")
results = []

for f in old_files:
    m = year_pattern.search(f)
    year = int(m.group(1)) if m else None

    ds = xr.open_dataset(f)
    pm25 = ds[PM25_VAR_NAME]

    sub = pm25.sel({LAT_NAME: slice(miny - 0.2, maxy + 0.2),
                    LON_NAME: slice(minx - 0.2, maxx + 0.2)})
    lats = sub[LAT_NAME].values
    lons = sub[LON_NAME].values
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    mask = np.zeros(lon_grid.shape, dtype=bool)
    for i in range(lon_grid.shape[0]):
        for j in range(lon_grid.shape[1]):
            if city_poly.contains(Point(lon_grid[i, j], lat_grid[i, j])):
                mask[i, j] = True

    n_pixels = mask.sum()
    vals = sub.values.squeeze()[mask] if n_pixels else np.array([])
    mean_val = float(np.nanmean(vals)) if n_pixels else np.nan

    print(f"{year} (V6GL02.04): {n_pixels} pixels, mean PM2.5 = {mean_val:.3f} ug/m3")
    results.append({"year": year, "davao_pm25_v6gl0204": mean_val, "n_pixels": n_pixels})
    ds.close()

import pandas as pd
out_df = pd.DataFrame(results).sort_values("year")
print("\n=== Comparison reference (fill in from your V6GL03 run) ===")
print("2020 V6GL03 = 16.19 | 2021 V6GL03 = 15.53 | 2022 V6GL03 = 15.69")
print("2020 ground = 11.08 | 2021 ground = 10.85 | 2022 ground = 14.52")
print()
print(out_df)
out_df.to_csv("data/processed/davao_v6gl0204_check.csv", index=False)
print("\nSaved: data/processed/davao_v6gl0204_check.csv")
