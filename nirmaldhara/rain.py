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


def fetch(sites, timeout=10):
    with urlopen(build_url(sites), timeout=timeout) as response:
        return parse(sites, json.load(response))


def indexes(sites, timeout=10):
    """Rain index in mm for every site."""
    return {site_id: rain_index(*amounts)
            for site_id, amounts in fetch(sites, timeout).items()}
