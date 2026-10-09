"""The public map file: one small JSON document per city (ARCHITECTURE.md section 6.8).

Residents' phones read this file from the content network. Passability is worked
out in the browser from the depth, so it is not repeated here for every site.
"""

import json

from .bands import band_for

# Short keys: the file is fetched by every resident on a flood day.
FIELDS = ("i", "n", "y", "x", "s", "b", "l", "h", "t", "u")


def site_entry(site_id, name, lat, lon, site, updated_at):
    """One site as a compact list in the order of FIELDS."""
    return [site_id, name, round(lat, 5), round(lon, 5), site.state,
            band_for(site.high), round(site.low), round(site.high),
            1 if site.trusted else 0, int(updated_at)]


def city_document(city, generated_at, entries):
    """`entries` is an iterable of site_entry lists."""
    return {"city": city, "generated_at": int(generated_at), "fields": list(FIELDS),
            "sites": sorted(entries, key=lambda e: e[0])}


def to_json(document):
    return json.dumps(document, separators=(",", ":"), ensure_ascii=False)
