"""Write data/sample-floods.json: invented flood history, for developing the repeat offenders page.

    python scripts/make_sample_history.py

Every number is made up and the sites are called "Sample site N", not real places. The file is
marked "sample": true, and the page then shows a banner saying so. The development server
(scripts/serve_web.py) serves it; it is never uploaded.
"""

import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import history, workflow  # noqa: E402

DAY = 86400
NOW = int(time.time())

# site: list of (days ago, peak low, peak high, minutes blocked for cars, for two-wheelers, confirmed)
FLOODS = {
    "Sample site 1": [(34, 20, 34, 95, 140, True), (27, 25, 41, 130, 175, True), (19, 30, 48, 170, 210, True),
                      (11, 22, 36, 110, 150, True), (4, 35, 52, 205, 260, True)],
    "Sample site 2": [(30, 15, 24, 60, 100, True), (16, 18, 29, 75, 120, True), (6, 21, 33, 90, 135, True)],
    "Sample site 3": [(22, 12, 19, 25, 70, True), (8, 14, 22, 40, 80, True)],
    "Sample site 4": [(13, 10, 17, 0, 35, True), (3, 28, 45, 120, 160, False)],
    "Sample site 5": [(9, 24, 38, 0, 0, False)],
    "Sample site 6": [],
}


def make():
    entries = []
    for n, (name, floods) in enumerate(FLOODS.items(), 1):
        site_id, events = f"sample-{n:02d}", []
        for ago, low, high, cars, bikes, confirmed in floods:
            start = NOW - ago * DAY
            events.append(asdict(replace(
                workflow.open_event(site_id, start), peak_low=low, peak_high=high, confirmed=confirmed,
                blocked_cars_s=cars * 60, blocked_two_wheelers_s=bikes * 60,
                closed_at=start + max(cars, bikes, 30) * 60, outcome="flood", version=2)))
        entries.append(history.site_entry(site_id, name, events))
    doc = history.document("hyderabad", NOW, entries)
    doc["sample"] = True
    return doc


if __name__ == "__main__":
    out = ROOT / "data" / "sample-floods.json"
    out.write_text(json.dumps(make(), separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {out}")
