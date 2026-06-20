#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
process_acag_pm25.py
====================================================================
Build a subnational PM2.5 exposure panel for the Philippines (2013-2022).

What this script does
---------------------
1. Loads annual ACAG (Atmospheric Composition Analysis Group) V5.GL.03
   surface PM2.5 NetCDF files (.nc4) from data/raw/acag/ for 2013-2022.
   The PM2.5 variable is usually called "GWRPM25"; the script auto-detects
   it if the name differs.
2. Loads the GADM Philippines level-1 (region) polygon shapefile from
   data/raw/shapefiles/ with geopandas.
3. For each year, computes the AREA-WEIGHTED mean PM2.5 (ug/m3) for every
   GADM level-1 region. On a regular lon/lat grid the physical area of a
   cell is proportional to cos(latitude), so we weight every grid cell by
   cos(lat) when averaging inside each region (a proper area weighting).
4. Writes a tidy long-format panel to
   data/processed/pm25_regional_panel.csv with columns:
       region_name, year, pm25_mean
5. Prints the first 10 rows of the output.

No network/API calls are made anywhere. Everything is read from disk.

Dependencies
------------
    pip install xarray netCDF4 geopandas regionmask numpy pandas
(regionmask is used to rasterize the region polygons onto the PM2.5 grid.
 An alternative using rioxarray/rasterio is described in the comments of
 zonal_means_for_year() but is not required.)

Run
---
    python process_acag_pm25.py
from the repository root.
====================================================================
"""

from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np
import pandas as pd

# Geospatial / NetCDF stack. Imported with a friendly message if missing.
try:
    import xarray as xr
    import geopandas as gpd
    import regionmask
except ImportError as exc:  # pragma: no cover - guidance only
    sys.exit(
        "Missing a required package: {}\n"
        "Install the geospatial stack first, e.g.:\n"
        "    pip install xarray netCDF4 geopandas regionmask numpy pandas\n"
        .format(exc.name)
    )

# --------------------------------------------------------------------------
# Configuration -- paths are relative to the repo root (where this file lives)
# --------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

ACAG_DIR = os.path.join(REPO_ROOT, "data", "raw", "acag")
SHAPE_DIR = os.path.join(REPO_ROOT, "data", "raw", "shapefiles")
OUT_DIR = os.path.join(REPO_ROOT, "data", "processed")
OUT_CSV = os.path.join(OUT_DIR, "pm25_regional_panel.csv")

YEARS = list(range(2013, 2023))  # 2013..2022 inclusive

# Candidate names for the PM2.5 data variable, the longitude/latitude
# coordinates, and the GADM region-name column. The script tries each in
# order and falls back to auto-detection if none match.
PM25_VAR_CANDIDATES = ["GWRPM25", "PM25", "pm25", "PM2.5"]
LON_CANDIDATES = ["lon", "longitude", "x", "LON", "Longitude"]
LAT_CANDIDATES = ["lat", "latitude", "y", "LAT", "Latitude"]
REGION_NAME_CANDIDATES = ["NAME_1", "NAME1", "REGION", "region", "name"]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _first_match(available, candidates):
    """Return the first candidate present in `available`, else None."""
    aset = {a.lower(): a for a in available}
    for c in candidates:
        if c.lower() in aset:
            return aset[c.lower()]
    return None


def find_year_file(year: int) -> str | None:
    """
    Locate the ACAG NetCDF file for a given year inside ACAG_DIR.

    ACAG annual filenames look something like:
        V5GL03.HybridPM25.Global.201301-201312.nc
        V5GL0302.HybridPM25.Global.YYYY01-YYYY12.nc4
    so we simply glob every .nc/.nc4 file and keep the one whose name
    contains the 4-digit year. This is deliberately tolerant of the exact
    ACAG naming so you don't have to rename downloads.
    """
    patterns = [
        os.path.join(ACAG_DIR, "*.nc4"),
        os.path.join(ACAG_DIR, "*.nc"),
    ]
    candidates = []
    for pat in patterns:
        candidates.extend(glob.glob(pat))

    # Prefer files that contain the year as a standalone 4-digit token.
    year_str = str(year)
    matches = [f for f in candidates if year_str in os.path.basename(f)]

    if not matches:
        return None
    # If several files mention the year (e.g. monthly + annual), pick the
    # shortest filename, which is typically the plain annual product.
    matches.sort(key=lambda p: len(os.path.basename(p)))
    return matches[0]


def detect_pm25_variable(ds: "xr.Dataset") -> str:
    """Pick the PM2.5 variable name, trying known names then a 2-D fallback."""
    name = _first_match(list(ds.data_vars), PM25_VAR_CANDIDATES)
    if name is not None:
        return name
    # Fallback: choose the data variable with the most cells that also has
    # both a lon-like and lat-like dimension -- almost always the PM2.5 grid.
    best = None
    best_size = -1
    for v in ds.data_vars:
        dims = [d.lower() for d in ds[v].dims]
        has_lon = any(any(k in d for k in ["lon", "x"]) for d in dims)
        has_lat = any(any(k in d for k in ["lat", "y"]) for d in dims)
        if has_lon and has_lat and ds[v].size > best_size:
            best, best_size = v, ds[v].size
    if best is None:
        raise ValueError(
            "Could not identify a PM2.5 variable in the NetCDF. "
            "Variables present: {}".format(list(ds.data_vars))
        )
    print("    [info] PM2.5 variable name not in known list; "
          "auto-detected '{}'".format(best))
    return best


def get_lonlat_names(da: "xr.DataArray") -> tuple[str, str]:
    """Return (lon_name, lat_name) for a DataArray's coordinates/dims."""
    coords = list(da.coords) + list(da.dims)
    lon = _first_match(coords, LON_CANDIDATES)
    lat = _first_match(coords, LAT_CANDIDATES)
    if lon is None or lat is None:
        raise ValueError(
            "Could not find lon/lat coordinates. Found coords: {}".format(coords)
        )
    return lon, lat


def load_pm25_dataarray(path: str) -> "xr.DataArray":
    """
    Open one annual ACAG file and return a 2-D DataArray (lat x lon) of PM2.5
    with coordinates renamed to the canonical 'lon'/'lat'.
    """
    ds = xr.open_dataset(path)
    var = detect_pm25_variable(ds)
    da = ds[var]

    lon_name, lat_name = get_lonlat_names(da)
    da = da.rename({lon_name: "lon", lat_name: "lat"})

    # Some files carry a singleton time/level dimension; squeeze it away so
    # we are left with a clean 2-D (lat, lon) field.
    squeeze_dims = [d for d in da.dims if d not in ("lon", "lat") and da.sizes[d] == 1]
    if squeeze_dims:
        da = da.squeeze(squeeze_dims, drop=True)
    if set(da.dims) != {"lon", "lat"}:
        # If extra non-singleton dims remain, take the first index of each
        # (defensive; ACAG annual files are 2-D so this should not trigger).
        for d in list(da.dims):
            if d not in ("lon", "lat"):
                da = da.isel({d: 0}, drop=True)

    # Ensure latitude is ascending; regionmask is happy either way, but a
    # consistent orientation avoids surprises in slicing.
    if da["lat"][0] > da["lat"][-1]:
        da = da.sortby("lat")
    da = da.sortby("lon")
    return da


def load_regions() -> "gpd.GeoDataFrame":
    """
    Load the GADM Philippines level-1 shapefile from SHAPE_DIR.

    Picks a level-1 file if one is obvious (filename ending in _1.shp, the
    GADM convention), otherwise the first .shp found. Reprojects to EPSG:4326
    (lon/lat degrees) to match the ACAG grid.
    """
    shp_files = glob.glob(os.path.join(SHAPE_DIR, "**", "*.shp"), recursive=True)
    if not shp_files:
        raise FileNotFoundError(
            "No .shp file found under {}. Place the GADM PH level-1 "
            "shapefile (e.g. gadm41_PHL_1.shp and its sidecar files) there."
            .format(SHAPE_DIR)
        )

    # Prefer the GADM level-1 file by its conventional "_1" suffix.
    level1 = [f for f in shp_files if re.search(r"_1\.shp$", os.path.basename(f))]
    shp_path = level1[0] if level1 else sorted(shp_files)[0]
    print("Using shapefile: {}".format(os.path.relpath(shp_path, REPO_ROOT)))

    gdf = gpd.read_file(shp_path)

    # Always work in lon/lat degrees (WGS84) to align with the ACAG grid.
    if gdf.crs is None:
        print("    [warn] shapefile has no CRS; assuming EPSG:4326 (WGS84).")
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    name_col = _first_match(list(gdf.columns), REGION_NAME_CANDIDATES)
    if name_col is None:
        raise ValueError(
            "Could not find a region-name column. Columns present: {}. "
            "Edit REGION_NAME_CANDIDATES if your GADM file differs."
            .format(list(gdf.columns))
        )
    gdf = gdf.rename(columns={name_col: "region_name"})
    # Keep just what we need.
    gdf = gdf[["region_name", "geometry"]].reset_index(drop=True)
    return gdf


def build_region_mask(gdf: "gpd.GeoDataFrame", da: "xr.DataArray"):
    """
    Rasterize region polygons onto the PM2.5 grid with regionmask.

    Returns a boolean 3-D mask (region, lat, lon): True where a grid cell
    falls inside that region. Building it once is enough because every annual
    ACAG file shares the same global grid.
    """
    regions = regionmask.from_geopandas(
        gdf, names="region_name", name="GADM_L1", overlap=False
    )
    # mask_3D gives one boolean layer per region -- convenient for looping.
    mask_3d = regions.mask_3D(da["lon"], da["lat"])
    return regions, mask_3d


def zonal_means_for_year(da: "xr.DataArray", mask_3d, gdf) -> dict[str, float]:
    """
    Compute the area-weighted mean PM2.5 per region for a single year.

    Area weighting: on a regular lon/lat grid, cell area is proportional to
    cos(latitude). We therefore weight each cell by cos(lat) and take, within
    each region's mask:
        weighted_mean = sum(pm25 * w * inside) / sum(w * inside)
    where w = cos(lat) broadcast across longitude and `inside` is the region
    mask. NaN PM2.5 cells (e.g. ocean / fill values) are excluded.

    (Alternative not used here: reproject both raster and polygons to an
    equal-area CRS and use rioxarray's `.rio.clip` per polygon. The cos(lat)
    weighting below is simpler and accurate for a country the size of the
    Philippines.)
    """
    # cos(lat) weights, broadcast to the 2-D grid shape (lat, lon).
    weights = np.cos(np.deg2rad(da["lat"]))
    w2d = weights.broadcast_like(da)  # (lat, lon)

    pm = da  # (lat, lon)
    valid = pm.notnull()

    out = {}
    n_regions = mask_3d.sizes["region"]
    for i in range(n_regions):
        inside = mask_3d.isel(region=i)  # boolean (lat, lon)
        sel = inside & valid
        w = w2d.where(sel)
        num = (pm.where(sel) * w).sum(skipna=True)
        den = w.sum(skipna=True)
        # region_name lives on the mask's "names" coordinate (or fall back
        # to the GeoDataFrame order).
        try:
            region_name = str(mask_3d["names"].isel(region=i).values)
        except Exception:
            region_name = str(gdf["region_name"].iloc[i])
        if float(den) > 0:
            out[region_name] = float(num / den)
        else:
            # No valid grid cell fell inside this region (tiny/island region
            # vs. grid resolution). Record NaN rather than inventing a value.
            out[region_name] = float("nan")
            print("    [warn] {}: no valid PM2.5 cells inside region "
                  "(reported as NaN).".format(region_name))
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading GADM Philippines level-1 regions ...")
    gdf = load_regions()
    print("  {} regions loaded.".format(len(gdf)))

    region_mask = None  # built lazily on the first available NetCDF grid
    mask_regions = None

    rows = []
    missing_years = []

    for year in YEARS:
        path = find_year_file(year)
        if path is None:
            missing_years.append(year)
            print("[{}] no NetCDF found in data/raw/acag/ -- skipping.".format(year))
            continue

        print("[{}] reading {}".format(year, os.path.basename(path)))
        da = load_pm25_dataarray(path)

        # Build the region mask once, on the first year's grid (all annual
        # ACAG files share the same global grid, so this is reused).
        if region_mask is None:
            print("  Building region mask on the PM2.5 grid (one-time) ...")
            mask_regions, region_mask = build_region_mask(gdf, da)

        year_means = zonal_means_for_year(da, region_mask, gdf)
        for region_name, value in year_means.items():
            rows.append({"region_name": region_name, "year": year,
                         "pm25_mean": value})

        da.close()

    if not rows:
        sys.exit(
            "No data produced. Check that .nc4 files for 2013-2022 are in {} "
            "and that the shapefile is in {}.".format(ACAG_DIR, SHAPE_DIR)
        )

    panel = pd.DataFrame(rows, columns=["region_name", "year", "pm25_mean"])
    # Tidy ordering: by region, then year.
    panel = panel.sort_values(["region_name", "year"]).reset_index(drop=True)
    # Round to a sensible precision for a concentration in ug/m3.
    panel["pm25_mean"] = panel["pm25_mean"].round(3)

    panel.to_csv(OUT_CSV, index=False)
    print("\nSaved panel -> {}".format(os.path.relpath(OUT_CSV, REPO_ROOT)))
    print("  rows: {}  | regions: {}  | years: {}".format(
        len(panel), panel["region_name"].nunique(), panel["year"].nunique()))
    if missing_years:
        print("  [note] no NetCDF found for years: {}".format(missing_years))

    print("\nFirst 10 rows of the output:")
    # to_string avoids pandas truncating and shows it cleanly in a terminal.
    print(panel.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
