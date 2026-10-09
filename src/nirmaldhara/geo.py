"""Grid cells for "who is near this site" lookups (DESIGN.md section 3.6).

A geohash names a rectangle of the earth with a short string. Storing each
subscriber's cell lets "everyone within 500 m" be answered by fetching a few
cells and filtering exactly, without scanning every subscriber.
"""

from math import cos, radians

from .intake import distance_m

ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
PRECISION = 6                       # cells about 1.2 km east-west by 0.6 km north-south
LAT_BITS = PRECISION * 5 // 2       # 15
LON_BITS = PRECISION * 5 - LAT_BITS  # 15
CELL_LAT_DEG = 180 / 2 ** LAT_BITS
CELL_LON_DEG = 360 / 2 ** LON_BITS
METRES_PER_DEG_LAT = 111_320


def encode(lat, lon):
    """Geohash of a point at PRECISION characters."""
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    bits, even = 0, True
    for _ in range(PRECISION * 5):
        rng, value = (lon_range, lon) if even else (lat_range, lat)
        mid = (rng[0] + rng[1]) / 2
        bits <<= 1
        if value >= mid:
            bits |= 1
            rng[0] = mid
        else:
            rng[1] = mid
        even = not even
    return "".join(ALPHABET[(bits >> shift) & 31]
                   for shift in range((PRECISION - 1) * 5, -1, -5))


def cells_covering(lat, lon, radius_m):
    """Every cell that a circle around the point can touch.

    Steps across the circle's bounding box one cell at a time, so no cell is
    skipped. At 500 m this is at most a handful of cells.
    """
    dlat = radius_m / METRES_PER_DEG_LAT
    dlon = radius_m / (METRES_PER_DEG_LAT * max(cos(radians(lat)), 0.01))
    cells = set()
    steps_lat = int(2 * dlat / CELL_LAT_DEG) + 2
    steps_lon = int(2 * dlon / CELL_LON_DEG) + 2
    for i in range(steps_lat + 1):
        for j in range(steps_lon + 1):
            cells.add(encode(min(lat - dlat + i * CELL_LAT_DEG, lat + dlat),
                             min(lon - dlon + j * CELL_LON_DEG, lon + dlon)))
    return cells


def within(points, lat, lon, radius_m):
    """Exact filter after the cell lookup. `points` is an iterable of (id, lat, lon)."""
    return [pid for pid, plat, plon in points
            if distance_m(lat, lon, plat, plon) <= radius_m]
