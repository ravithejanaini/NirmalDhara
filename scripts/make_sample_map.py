"""Write data/sample-map.json: eight made-up sites covering every state.

The web pages are built against this file until the publisher is deployed. The sites are
samples, not real locations or readings. Run it again to refresh the timestamps:

    python scripts/make_sample_map.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nirmaldhara.publish import city_document, site_entry, to_json  # noqa: E402
from nirmaldhara.state import (CLEAR, CRITICAL, RECEDING, WARNING, WATCH,  # noqa: E402
                               Reading, Site)

NOW = int(time.time())
MIN = 60


def site(state, low, high, trusted, confidence, age_min, source="guardian"):
    """A site whose last three readings are `age_min` minutes old and agree."""
    ts = NOW - age_min * MIN
    readings = tuple(Reading(ts - k * 3 * MIN, low, high, confidence, source, f"d{k}")
                     for k in (2, 1, 0)) if high else ()
    return Site("x", state=state, low=low, high=high, trusted=trusted, readings=readings), ts


# id, name, lat, lon, site, last update
SAMPLES = [
    ("sample-01", "Sample site 1: dry", 17.3850, 78.4867, *site(CLEAR, 0, 0, False, 0, 0)),
    ("sample-02", "Sample site 2: watch, no water yet", 17.4065, 78.4772, *site(WATCH, 0, 0, False, 0, 0)),
    ("sample-03", "Sample site 3: ankle deep, one photo", 17.4399, 78.4983,
     *site(WARNING, 12, 17, False, 0.7, 4, "resident")),
    ("sample-04", "Sample site 4: shin deep, confirmed", 17.3616, 78.4747,
     *site(WARNING, 14, 19, True, 0.8, 6)),
    ("sample-05", "Sample site 5: critical", 17.4239, 78.4738, *site(CRITICAL, 28, 38, True, 0.85, 3)),
    ("sample-06", "Sample site 6: receding", 17.4486, 78.3908, *site(RECEDING, 8, 13, True, 0.8, 9)),
    ("sample-07", "Sample site 7: stale reading", 17.3300, 78.5100,
     *site(WARNING, 13, 18, True, 0.8, 45)),
    ("sample-08", "Sample site 8: low confidence", 17.4700, 78.5200,
     *site(WARNING, 10, 22, True, 0.45, 7)),
]

entries = [site_entry(i, n, lat, lon, s, u) for i, n, lat, lon, s, u in SAMPLES]
document = city_document("hyderabad", NOW, entries)
document["sample"] = True
out = Path(__file__).resolve().parents[1] / "data" / "sample-map.json"
out.write_text(to_json(document) + "\n", encoding="utf-8")
print(f"wrote {out} with {len(entries)} sites")
