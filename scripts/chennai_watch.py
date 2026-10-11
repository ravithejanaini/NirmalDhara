"""REAL RAIN, REAL REPORTS, A SECOND CITY: would the rain rule have opened a watch in Chennai?

    python scripts/chennai_watch.py --fetch      # asks Open-Meteo for the rain history, kept in data/chennai-rain-history.json.gz
    python scripts/chennai_watch.py              # prints the results and writes docs/chennai-watch.md

In Hyderabad the rule opened on none of the days its places were reported under water
(docs/watch-history.md): the forecast it is fed never rains hard there. Chennai floods under a
different rain, the north-east monsoon and its cyclones, which falls for hours. This sets the same
rule, unchanged, against nine Chennai subways and the days the police closed them.

The rule, the replay and the rain provider are those of scripts/watch_history.py. Nothing here is
deployed in Chennai, and this tests the rain rule and nothing after it. It is not a measurement of
depth, and a subway with no report on a day was not shown to be dry.
"""

import argparse
import gzip
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from nirmaldhara import rain as live  # noqa: E402
from watch_history import IST, MODELS, OWN, TIMEOUT_S, URL, indexes, watches, window  # noqa: E402

SITES = ROOT / "data" / "chennai_sites.json"
REPORTS = ROOT / "data" / "chennai-flood-reports.json"
RAIN = ROOT / "data" / "chennai-rain-history.json.gz"
OUT = ROOT / "docs" / "chennai-watch.md"
NOTES = ROOT / "docs" / "chennai-watch-notes.md"
SEASON = ((10, 1), (12, 31))            # the north-east monsoon
THRESHOLDS = (10, 20, 30, 40, 50)


def sites():
    return {s["id"]: s for s in json.loads(SITES.read_text("utf-8"))["sites"]}


def cells():
    points = [(s["id"], s["lat"], s["lon"]) for s in sites().values()]
    return {site: f"{lat},{lon}" for (lat, lon), ids in live.grid_cells(points).items() for site in ids}


def fetch():
    wanted = sorted(set(cells().values()))
    events = json.loads(REPORTS.read_text("utf-8"))["events"]
    kept = {"credit": "Weather data by Open-Meteo.com (CC BY 4.0), from its archive of served forecasts. Hourly rain in mm, the hour ending "
                      "at each time, times in UTC.", "fetched": date.today().isoformat(), "cells": cells(), "series": {}}
    for year in sorted({int(e["from"][:4]) for e in events}):
        start, end = date(year, *SEASON[0]), date(year, *SEASON[1])
        query = urlencode({"latitude": ",".join(c.split(",")[0] for c in wanted), "longitude": ",".join(c.split(",")[1] for c in wanted),
                           "hourly": "precipitation", "start_date": start.isoformat(), "end_date": end.isoformat(), "timezone": "UTC",
                           "models": ",".join(MODELS)})
        with urlopen(f"{URL}?{query}", timeout=TIMEOUT_S) as response:
            payload = json.load(response)
        for cell, place in zip(wanted, payload if isinstance(payload, list) else [payload]):
            for model in MODELS:
                values = place["hourly"].get(f"precipitation_{model}")
                if values is None or sum(v is None for v in values) > len(values) // 20:
                    continue
                kept["series"].setdefault(model, {}).setdefault(cell, {})[str(year)] = {
                    "start": place["hourly"]["time"][0], "hours": len(values),
                    "wet": {str(i): round(v, 1) for i, v in enumerate(values) if v}}
        print(f"{year}: {len(wanted)} cells, models kept: {[m for m in MODELS if str(year) in kept['series'].get(m, {}).get(wanted[0], {})]}")
    RAIN.write_bytes(gzip.compress(json.dumps(kept, separators=(",", ":")).encode("utf-8"), mtime=0))


def load():
    return json.loads(gzip.decompress(RAIN.read_bytes()).decode("utf-8"))


def hourly(rain, model, cell, year):
    entry = rain["series"].get(model, {}).get(cell, {}).get(str(year))
    if entry is None:
        return None
    values = [0.0] * entry["hours"]
    for index, mm in entry["wet"].items():
        values[int(index)] = mm
    return datetime.fromisoformat(entry["start"]), values


def on_days(rain, model, cell, first_day, last_day, threshold=20):
    """What the rule did at one place between two days, or None with no rain history."""
    series = hourly(rain, model, cell, int(first_day[:4]))
    if series is None:
        return None
    start, values = series
    index = indexes(values)
    first, last = window(start, first_day, last_day)
    stood = [(a, b) for a, b in watches(index, threshold) if a < last and b > first]
    since = (start + timedelta(hours=stood[0][0]) + IST) if stood else None
    return {"open": bool(stood), "since": since, "peak": max(index[first:last], default=0.0), "mm": sum(values[first:last]),
            "top_hour": max(values[first:last], default=0.0)}


def watch_days(rain, model, year, threshold=20):
    """Days of the season with a watch standing, for one cell on average."""
    each = []
    for cell in sorted(set(rain["cells"].values())):
        series = hourly(rain, model, cell, year)
        if series is None:
            continue
        start, values = series
        days = {(start + timedelta(hours=h) + IST).date() for a, b in watches(indexes(values), threshold) for h in range(a, b)}
        each.append(len(days))
    return sum(each) / len(each) if each else None


def study(rain, reports, model=OWN, threshold=20):
    """One row for each place in each event: (event, site id, name, what the rule did)."""
    names = {key: s["name"] for key, s in sites().items()}
    return [(e, site, names[site], on_days(rain, model, rain["cells"][site], e["from"], e["to"], threshold))
            for e in reports["events"] for site in e["sites"]]


def caught(rows):
    held = [r for r in rows if r[3] is not None]
    return len(held), sum(r[3]["open"] for r in held)


def report(rain, reports):
    rows = study(rain, reports)
    total, opened = caught(rows)
    years = sorted({int(e["from"][:4]) for e in reports["events"]})
    lines = [
        "# The rain rule in a second city: Chennai",
        "",
        "**Real rain history and real reports. Nothing is deployed in Chennai.** Written by `scripts/chennai_watch.py` from",
        "`data/chennai-flood-reports.json`, news reports found on 11 October 2026 of nine Chennai subways closed for water,",
        "and `data/chennai-rain-history.json.gz`, hourly rain at each from Open-Meteo, the provider the live system asks",
        "(CC BY 4.0). The engine's own rule is replayed over the rain hour by hour, unchanged from Hyderabad: a watch opens",
        "when the rain index reaches 20 mm. This tests the first step of the system and nothing after it.",
        "",
        f"**A watch stood on {opened} of {total} reports.** In Hyderabad the same rule, on the same provider, stood on 0 of 20",
        "([watch-history.md](watch-history.md)).",
        "",
        "## Each event",
        "",
        "| Event | Report | Places named | A watch stood | Earliest watch | Rain in the history | Wettest hour |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in reports["events"]:
        mine = [r for r in rows if r[0] is e and r[3] is not None]
        if not mine:
            lines.append(f"| {e['name']} | [{e['publisher']}]({e['url']}): {e['says']} | {len(e['sites'])} | not held | | | |")
            continue
        n, k = caught(mine)
        first = min((r[3]["since"] for r in mine if r[3]["since"]), default=None)
        mm = sorted(r[3]["mm"] for r in mine)
        lines.append(f"| {e['name']} | [{e['publisher']}]({e['url']}): {e['says']} | {len(e['sites'])} | {k} of {n} | "
                     f"{first.strftime('%d %b %H:%M') if first else 'none'} | {mm[0]:.0f} to {mm[-1]:.0f} mm | {max(r[3]['top_hour'] for r in mine):.1f} mm |")
    lines += ["", "## Each place", "", "| Event | Place | The rule | Highest index | Rain on the days |", "|---|---|---|---|---|"]
    for e, _, name, r in rows:
        did = "not held" if r is None else (f"watch from {r['since'].strftime('%d %b %H:%M')}" if r["open"] else "**no watch**")
        lines.append(f"| {e['name']} | {name} | {did} | {'' if r is None else int(r['peak'])} | {'' if r is None else f'{r['mm']:.0f} mm'} |")
    lines += ["", "## What the rule costs", "",
              "Days from 1 October to 31 December with a watch standing, at one forecast cell on average, and the reports caught, at other thresholds.", "",
              "| Threshold | Reports caught | " + " | ".join(f"Watch days, {y}" for y in years) + " |", "|---|---|" + "---|" * len(years)]
    for t in THRESHOLDS:
        n, k = caught(study(rain, reports, threshold=t))
        mark = "**" if t == 20 else ""
        lines.append(f"| {mark}{t} mm{mark} | {k} of {n} | " + " | ".join(f"{watch_days(rain, OWN, y, t):.0f}" for y in years) + " |")
    lines += ["", "## Model by model", "", "| Rain from | Reports caught |", "|---|---|"]
    for model, what in MODELS.items():
        n, k = caught(study(rain, reports, model=model))
        lines.append(f"| {what[0].upper() + what[1:]} | {f'{k} of {n}' if n else 'not held'} |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fetch", action="store_true", help="ask the provider for the rain history first")
    args = parser.parse_args()
    if args.fetch:
        fetch()
    if not RAIN.exists():
        print(f"There is no rain history at {RAIN}. Run this with --fetch.")
        return 1
    text = report(load(), json.loads(REPORTS.read_text("utf-8")))
    print(text)
    OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
