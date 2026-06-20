import xarray as xr
import geopandas as gpd
import pandas as pd
import os
import glob
from shapely.geometry import Point

ACAG_DIR    = "data/raw/acag/Annual-selected/"
SHP_PATH    = "data/raw/shapefiles/gadm41_PHL_shp/gadm41_PHL_1.shp"
OUTPUT_FILE = "data/processed/pm25_regional_panel.csv"

LON_MIN, LON_MAX = 116.0, 127.5
LAT_MIN, LAT_MAX =   4.0,  22.0

# Map GADM province names → 17 regions
PROVINCE_TO_REGION = {
    "Metropolitan Manila"  : "NCR",
    "Abra"                 : "CAR",   "Apayao"              : "CAR",
    "Benguet"              : "CAR",   "Ifugao"              : "CAR",
    "Kalinga"              : "CAR",   "Mountain Province"   : "CAR",
    "Ilocos Norte"         : "Region I",   "Ilocos Sur"    : "Region I",
    "La Union"             : "Region I",   "Pangasinan"    : "Region I",
    "Batanes"              : "Region II",  "Cagayan"       : "Region II",
    "Isabela"              : "Region II",  "Nueva Vizcaya" : "Region II",
    "Quirino"              : "Region II",
    "Aurora"               : "Region III", "Bataan"        : "Region III",
    "Bulacan"              : "Region III", "Nueva Ecija"   : "Region III",
    "Pampanga"             : "Region III", "Tarlac"        : "Region III",
    "Zambales"             : "Region III",
    "Batangas"             : "Region IV-A","Cavite"        : "Region IV-A",
    "Laguna"               : "Region IV-A","Quezon"        : "Region IV-A",
    "Rizal"                : "Region IV-A",
    "Marinduque"           : "Region IV-B","Occidental Mindoro":"Region IV-B",
    "Oriental Mindoro"     : "Region IV-B","Palawan"       : "Region IV-B",
    "Romblon"              : "Region IV-B",
    "Albay"                : "Region V",   "Camarines Norte":"Region V",
    "Camarines Sur"        : "Region V",   "Catanduanes"   : "Region V",
    "Masbate"              : "Region V",   "Sorsogon"      : "Region V",
    "Aklan"                : "Region VI",  "Antique"       : "Region VI",
    "Capiz"                : "Region VI",  "Guimaras"      : "Region VI",
    "Iloilo"               : "Region VI",  "Negros Occidental":"Region VI",
    "Bohol"                : "Region VII", "Cebu"          : "Region VII",
    "Negros Oriental"      : "Region VII", "Siquijor"      : "Region VII",
    "Biliran"              : "Region VIII","Eastern Samar" : "Region VIII",
    "Leyte"                : "Region VIII","Northern Samar": "Region VIII",
    "Samar"                : "Region VIII","Southern Leyte": "Region VIII",
    "Zamboanga del Norte"  : "Region IX",  "Zamboanga del Sur":"Region IX",
    "Zamboanga Sibugay"    : "Region IX",
    "Bukidnon"             : "Region X",   "Camiguin"      : "Region X",
    "Lanao del Norte"      : "Region X",   "Misamis Occidental":"Region X",
    "Misamis Oriental"     : "Region X",
    "Compostela Valley"    : "Region XI",  "Davao del Norte":"Region XI",
    "Davao del Sur"        : "Region XI",  "Davao Oriental": "Region XI",
    "North Cotabato"       : "Region XII", "Sarangani"     : "Region XII",
    "South Cotabato"       : "Region XII", "Sultan Kudarat": "Region XII",
    "Agusan del Norte"     : "Region XIII","Agusan del Sur" : "Region XIII",
    "Dinagat Islands"      : "Region XIII","Surigao del Norte":"Region XIII",
    "Surigao del Sur"      : "Region XIII",
    "Basilan"              : "BARMM",      "Lanao del Sur" : "BARMM",
    "Maguindanao"          : "BARMM",      "Sulu"          : "BARMM",
    "Tawi-Tawi"            : "BARMM",
}

# Load shapefile and dissolve provinces → 17 region polygons
print("Loading shapefile...")
gdf = gpd.read_file(SHP_PATH)
gdf["region"] = gdf["NAME_1"].map(PROVINCE_TO_REGION)

unmatched = gdf[gdf["region"].isna()]["NAME_1"].tolist()
if unmatched:
    print(f"WARNING unmatched provinces: {unmatched}")
else:
    print("All provinces matched.")

gdf = gdf[gdf["region"].notna()].copy()
regions_gdf = gdf.dissolve(by="region").reset_index()[["region","geometry"]]
print(f"Dissolved to {len(regions_gdf)} region polygons\n")

# Process each NetCDF file
nc_files = sorted(glob.glob(os.path.join(ACAG_DIR, "*.nc")))
print(f"Found {len(nc_files)} NetCDF files")

results = []
for nc_file in nc_files:
    basename = os.path.basename(nc_file)
    year = int(basename.split(".")[-2].split("-")[0][:4])
    print(f"Processing {year}...", end=" ", flush=True)

    ds = xr.open_dataset(nc_file)
    var_name = next((v for v in ["PM25","CNNPM25","pm25"] if v in ds.data_vars),
                    list(ds.data_vars)[0])
    da = ds[var_name]

    lat_name = next((c for c in da.dims if "lat" in c.lower()), "lat")
    lon_name = next((c for c in da.dims if "lon" in c.lower()), "lon")

    time_dims = [d for d in da.dims if d not in [lat_name, lon_name]]
    if time_dims:
        da = da.mean(dim=time_dims[0])

    da_phl = da.sel({lat_name: slice(LAT_MIN, LAT_MAX),
                     lon_name: slice(LON_MIN, LON_MAX)})

    df_grid = da_phl.to_dataframe(name="pm25").reset_index()
    df_grid = df_grid.dropna(subset=["pm25"])
    df_grid = df_grid[df_grid["pm25"] > 0]
    print(f"{len(df_grid)} grid cells...", end=" ", flush=True)

    from shapely.geometry import Point
    geometry = [Point(xy) for xy in zip(df_grid[lon_name], df_grid[lat_name])]
    gdf_grid = gpd.GeoDataFrame(df_grid, geometry=geometry, crs="EPSG:4326")

    joined = gpd.sjoin(gdf_grid, regions_gdf, how="left", predicate="within")
    region_means = (joined.groupby("region")["pm25"]
                    .mean().reset_index().assign(year=year))
    results.append(region_means)
    ds.close()
    print(f"→ {len(region_means)} regions")

panel = pd.concat(results, ignore_index=True)
panel = panel[["region","year","pm25"]].sort_values(["region","year"])

os.makedirs("data/processed", exist_ok=True)
panel.to_csv(OUTPUT_FILE, index=False)

print(f"\nSaved: {OUTPUT_FILE}")
print(f"Shape: {panel.shape}  (target: 170)")
print(f"\nFirst 20 rows:")
print(panel.head(20).to_string(index=False))
print(f"\nPM2.5 stats (µg/m³):")
print(panel["pm25"].describe().round(2))
