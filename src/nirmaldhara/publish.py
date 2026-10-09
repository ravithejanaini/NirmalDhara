"""The public map file: one small JSON document per city (ARCHITECTURE.md section 6.8).

Residents' phones read this file from the content network. Passability is worked
out in the browser from the depth, so it is not repeated here for every site.
"""

import json

from .bands import band_for
from .workflow import confidence

# Short keys: the file is fetched by every resident on a flood day.
# i id, n name, y latitude, x longitude, s state, b band, l low cm, h high cm,
# t trusted, u updated (seconds), c confidence of the depth (0 to 1). The browser needs
# c because "passable" requires a confidence of at least 0.6 (bands.MIN_CONFIDENCE).
FIELDS = ("i", "n", "y", "x", "s", "b", "l", "h", "t", "u", "c")


def site_entry(site_id, name, lat, lon, site, updated_at):
    """One site as a compact list in the order of FIELDS."""
    return [site_id, name, round(lat, 5), round(lon, 5), site.state,
            band_for(site.high), round(site.low), round(site.high),
            1 if site.trusted else 0, int(updated_at), round(confidence(site), 2)]


def city_document(city, generated_at, entries):
    """`entries` is an iterable of site_entry lists."""
    return {"city": city, "generated_at": int(generated_at), "fields": list(FIELDS),
            "sites": sorted(entries, key=lambda e: e[0])}


def to_json(document):
    return json.dumps(document, separators=(",", ":"), ensure_ascii=False)
