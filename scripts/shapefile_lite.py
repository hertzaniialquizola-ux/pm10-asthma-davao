"""
shapefile_lite.py
===================
A minimal, dependency-free .shp/.dbf reader (pure Python `struct`, no
pyshp/geopandas/fiona/shapely), written because none of those are
installable in this sandbox (no network access to PyPI -- see
scripts/stats_lite.py docstring for the same constraint affecting scipy/
statsmodels/linearmodels).

Only implements what's needed for robustness upgrade #10 (Moran's I):
reading Polygon-type (shape type 5) records from
data/raw/shapefiles/gadm41_PHL_shp/gadm41_PHL_1.shp (GADM level-1 =
Philippine provinces, 81 records; already used elsewhere in this project
for PM2.5 area-weighting per README.md) and the parallel .dbf attribute
table, and computing each polygon's true area-weighted centroid (handling
multi-part polygons / holes via the standard signed-area-weighted-centroid
method, not just an unweighted mean of vertices, which would be biased for
irregular archipelago provinces).

Binary format references: ESRI Shapefile Technical Description (1998),
"whitepaper.esri.com" (well-established fixed public spec, reproduced from
memory -- struct layout: 100-byte header, then repeated (8-byte big-endian
record header + little-endian record content) records; Polygon records =
shape type(4B LE) + bbox(4 doubles LE) + numParts(4B LE) + numPoints(4B LE)
+ parts[numParts](4B LE each) + points[numPoints](2x8B LE doubles each)).
"""

import struct


def read_dbf(path):
    """Return (field_names, list_of_dicts) for all records in a .dbf file."""
    with open(path, "rb") as f:
        header = f.read(32)
        num_records = struct.unpack("<I", header[4:8])[0]
        header_size = struct.unpack("<H", header[8:10])[0]
        record_size = struct.unpack("<H", header[10:12])[0]
        num_fields = (header_size - 33) // 32
        fields = []
        for _ in range(num_fields):
            fdesc = f.read(32)
            name = fdesc[:11].split(b"\x00")[0].decode("latin1")
            flen = fdesc[16]
            fields.append((name, flen))
        f.read(1)  # header terminator (0x0D)
        rows = []
        for _ in range(num_records):
            rec = f.read(record_size)
            if not rec or len(rec) < record_size:
                break
            row = {}
            offset = 1  # first byte = deletion flag
            for name, flen in fields:
                raw = rec[offset:offset + flen].decode("latin1").strip()
                row[name] = raw
                offset += flen
            rows.append(row)
    return [f[0] for f in fields], rows


def read_shp_polygons(path):
    """
    Return a list (one per record, same order as the .dbf) of polygons,
    where each polygon is a list of rings, and each ring is a list of
    (x, y) tuples (x=longitude, y=latitude for GADM's unprojected WGS84
    shapefiles).
    """
    polygons = []
    with open(path, "rb") as f:
        f.read(100)  # main file header
        while True:
            rec_header = f.read(8)
            if len(rec_header) < 8:
                break
            rec_number, content_len_words = struct.unpack(">II", rec_header)
            content_len_bytes = content_len_words * 2
            content = f.read(content_len_bytes)
            shape_type = struct.unpack("<I", content[0:4])[0]
            if shape_type == 0:  # null shape
                polygons.append([])
                continue
            # bbox = content[4:36] (unused here)
            num_parts, num_points = struct.unpack("<II", content[36:44])
            parts_offset = 44
            parts = struct.unpack(f"<{num_parts}I", content[parts_offset:parts_offset + 4 * num_parts])
            points_offset = parts_offset + 4 * num_parts
            coords = struct.unpack(f"<{2 * num_points}d", content[points_offset:points_offset + 16 * num_points])
            xy = list(zip(coords[0::2], coords[1::2]))
            ring_bounds = list(parts) + [num_points]
            rings = [xy[ring_bounds[i]:ring_bounds[i + 1]] for i in range(num_parts)]
            polygons.append(rings)
    return polygons


def ring_signed_area_and_centroid(ring):
    """Shoelace signed area and centroid of a single ring (list of (x,y))."""
    n = len(ring)
    if n < 3:
        return 0.0, 0.0, 0.0
    a_sum = 0.0
    cx_sum = 0.0
    cy_sum = 0.0
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a_sum += cross
        cx_sum += (x0 + x1) * cross
        cy_sum += (y0 + y1) * cross
    signed_area = a_sum / 2.0
    if signed_area == 0.0:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / n, sum(ys) / n
    cx = cx_sum / (6.0 * signed_area)
    cy = cy_sum / (6.0 * signed_area)
    return signed_area, cx, cy


def polygon_area_and_centroid(rings):
    """
    Multi-ring polygon area + centroid. Sums each ring's SIGNED area and
    area-weighted centroid contribution directly: because ESRI shapefiles
    encode outer rings and holes with opposite winding order, their signed
    areas have opposite sign, so a plain sum correctly nets out holes
    without needing to separately classify which rings are holes.
    """
    total_signed_area = 0.0
    cx_num = 0.0
    cy_num = 0.0
    for ring in rings:
        a, cx, cy = ring_signed_area_and_centroid(ring)
        total_signed_area += a
        cx_num += a * cx
        cy_num += a * cy
    if total_signed_area == 0.0:
        return 0.0, 0.0, 0.0
    return abs(total_signed_area), cx_num / total_signed_area, cy_num / total_signed_area
