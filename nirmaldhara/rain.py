"""Rain for every site in one request (ARCHITECTURE.md section 6.1).

Hourly values are used: outside Europe and North America the provider's 15-minute
values are interpolated from hourly ones.
"""

import json
from urllib.parse import urlencode
from urllib.request import urlopen

from .state import rain_index

URL = "https://api.open-meteo.com/v1/forecast"
PAST_HOURS = 3
FORECAST_HOURS = 3   # the hour in progress and the two after it
CHUNK = 100          # points per request, to keep the address a safe length
CELL_DEG = 0.05      # forecast grid cell, about 5 km; the provider's grid is 1 to 11 km
TIMEOUT_S = 30       # the service has taken 8 to 16 seconds per request when measured


def build_url(sites):
    """`sites` is a list of (site_id, lat, lon)."""
    return URL + "?" + urlencode({
        "latitude": ",".join(str(lat) for _, lat, _ in sites),
        "longitude": ",".join(str(lon) for _, _, lon in sites),
        "hourly": "precipitation",
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "timezone": "UTC",
    })


def parse(sites, payload):
    """Return {site_id: (past1_mm, past3_mm, next1_mm)}.

    Each hourly value is the rain in the hour ending at that time. The first
    PAST_HOURS values are complete hours; the rest are the hour in progress and
    the forecast. The larger of the hour in progress and the next one is used as
    the coming hour, since a missed watch costs more than a false one.
    """
    locations = payload if isinstance(payload, list) else [payload]
    out = {}
    for (site_id, _, _), location in zip(sites, locations):
        values = [v or 0.0 for v in location["hourly"]["precipitation"]]
        past, coming = values[:PAST_HOURS], values[PAST_HOURS:]
        out[site_id] = (past[-1], sum(past), max(coming[:2], default=0.0))
    return out


def grid_cells(sites):
    """Group sites by forecast grid cell: {(cell_lat, cell_lon): [site_id, ...]}.

    The forecast is far coarser than a street, so nearby sites get the same
    answer. Asking once per cell turns hundreds of sites into a few dozen points.
    """
    cells = {}
    for site_id, lat, lon in sites:
        key = (round(round(lat / CELL_DEG) * CELL_DEG, 4),
               round(round(lon / CELL_DEG) * CELL_DEG, 4))
        cells.setdefault(key, []).append(site_id)
    return cells


def fetch(sites, timeout=TIMEOUT_S):
    """Rain amounts for every site: one forecast point per grid cell."""
    cells = grid_cells(sites)
    points = [(f"{lat},{lon}", lat, lon) for lat, lon in cells]
    by_point = {}
    for start in range(0, len(points), CHUNK):
        chunk = points[start:start + CHUNK]
        with urlopen(build_url(chunk), timeout=timeout) as response:
            by_point.update(parse(chunk, json.load(response)))
    return {site_id: by_point[f"{lat},{lon}"]
            for (lat, lon), site_ids in cells.items() for site_id in site_ids}


def indexes(sites, timeout=TIMEOUT_S):
    """Rain index in mm for every site."""
    return {site_id: rain_index(*amounts)
            for site_id, amounts in fetch(sites, timeout).items()}
