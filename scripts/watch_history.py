"""REAL RAIN, REAL REPORTS: would the rain rule have opened a watch on the days these places were under water?

    python scripts/watch_history.py --fetch      # asks Open-Meteo for the rain history, kept in data/rain-history.json.gz
    python scripts/watch_history.py              # prints the results and writes docs/watch-history.md

The watch is the first thing the system does (METHOD.md section 4). Every 15 minutes it works out a
rain index for each place, and when the index reaches 20 mm it opens a watch. The 20 was a design
choice. Until now it had not been set against a single day on which one of the nine places flooded.

Two things are put side by side here:

    reports     data/flood-reports.json: news reports that name one of the nine places, or its
                neighbourhood, as under water on a stated day. Found on 11 October 2026.
    rain        hourly rain at each place from Open-Meteo, the provider the live system asks, out of
                its archive of the forecasts it served. First as the live system asks for it, with the
                provider choosing the weather model. Then from six models asked for by name, and from
                the highest of all seven hour by hour.

The engine's own rule is replayed over the rain, hour by hour (state.rain_index, state.apply_rain),
with the two hours ahead taken as the archive holds them. For each report it says whether a watch
stood on the day, and what the rule costs: the days in a season on which a watch stands at all.

This tests the rain rule and nothing after it. It is not a measurement of depth, and a place with no
report on a day was not shown to be dry.
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

from nirmaldhara import rain as live  # noqa: E402
from nirmaldhara.state import CLEAR, WATCH, Site, apply_rain, rain_index  # noqa: E402

SITES = ROOT / "data" / "hyderabad_sites.json"
REPORTS = ROOT / "data" / "flood-reports.json"
RAIN = ROOT / "data" / "rain-history.json.gz"
OUT = ROOT / "docs" / "watch-history.md"
NOTES = ROOT / "docs" / "watch-history-notes.md"
URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
MODELS = {                              # the provider's name for each, and what it is
    "best_match": "the provider's own choice",
    "ecmwf_ifs025": "ECMWF IFS",
    "gfs_seamless": "NOAA GFS",
    "icon_seamless": "DWD ICON",
    "gem_seamless": "Canadian GEM",
    "jma_seamless": "JMA",
    "ukmo_seamless": "UK Met Office",
}
OWN, HIGHEST = "best_match", "highest"
SEASON = ((3, 1), (10, 31))             # 1 March to 31 October: the monsoon and the storms before it
LAST_DAY = date(2026, 10, 9)
IST = timedelta(hours=5, minutes=30)
THRESHOLDS = (5, 10, 15, 20, 30, 40, 50)
TIMEOUT_S = 180


def sites():
    return {s["id"]: s for s in json.loads(SITES.read_text("utf-8"))["sites"]}


def cells():
    """{site: 'lat,lon' of the forecast cell the live system asks for it}, by the live system's own rule."""
    points = [(s["id"], s["lat"], s["lon"]) for s in sites().values()]
    return {site: f"{lat},{lon}" for (lat, lon), ids in live.grid_cells(points).items() for site in ids}


def years_wanted():
    reports = json.loads(REPORTS.read_text("utf-8"))
    days = [r["from"] for r in reports["reports"]] + [reports["advisory_without_days"]["from"]]
    return sorted({int(day[:4]) for day in days})


def load():
    return json.loads(gzip.decompress(RAIN.read_bytes()).decode("utf-8"))


def fetch():
    """Ask the provider for every cell's hourly rain, from each model, in each year that has a report,
    and keep it thin: only the hours with rain, by their place in the season."""
    wanted = sorted(set(cells().values()))
    kept = {"credit": "Weather data by Open-Meteo.com (CC BY 4.0), from its archive of served forecasts. Hourly rain in mm, the hour ending "
                      "at each time, times in UTC. 'best_match' is the provider's own choice of model, as the live system asks for it.",
            "fetched": date.today().isoformat(), "cells": cells(), "series": {}}
    for year in years_wanted():
        start, end = date(year, *SEASON[0]), min(date(year, *SEASON[1]), LAST_DAY)
        query = urlencode({"latitude": ",".join(c.split(",")[0] for c in wanted), "longitude": ",".join(c.split(",")[1] for c in wanted),
                           "hourly": "precipitation", "start_date": start.isoformat(), "end_date": end.isoformat(), "timezone": "UTC",
                           "models": ",".join(MODELS)})
        with urlopen(f"{URL}?{query}", timeout=TIMEOUT_S) as response:
            payload = json.load(response)
        for cell, place in zip(wanted, payload if isinstance(payload, list) else [payload]):
            for model in MODELS:
                values = place["hourly"][f"precipitation_{model}"]
                if sum(v is None for v in values) > len(values) // 20:      # a model the archive does not hold for this year
                    continue
                kept["series"].setdefault(model, {}).setdefault(cell, {})[str(year)] = {
                    "start": place["hourly"]["time"][0], "hours": len(values), "missing": sum(v is None for v in values),
                    "grid": [place["latitude"], place["longitude"]],
                    "wet": {str(i): round(v, 1) for i, v in enumerate(values) if v}}
        print(f"{year}: {start} to {end}, {len(wanted)} cells, models kept: {[m for m in MODELS if str(year) in kept['series'].get(m, {}).get(wanted[0], {})]}")
    RAIN.write_bytes(gzip.compress(json.dumps(kept, separators=(",", ":")).encode("utf-8"), mtime=0))
    return kept


def hourly(rain, source, cell, year):
    """(time of the first hour in UTC, [mm in each hour]) or None if that source has nothing for the year.
    The source `highest` is the largest of the seven models in each hour, where all seven are held."""
    if source == HIGHEST:
        each = [hourly(rain, model, cell, year) for model in MODELS]
        if any(e is None for e in each):
            return None
        return each[0][0], [max(hour) for hour in zip(*(values for _, values in each))]
    entry = rain["series"].get(source, {}).get(cell, {}).get(str(year))
    if entry is None:
        return None
    values = [0.0] * entry["hours"]
    for index, mm in entry["wet"].items():
        values[int(index)] = mm
    return datetime.fromisoformat(entry["start"]), values


def indexes(values, coming=True):
    """The rain index at each hour, as the live system works it out on the hour: the hour just ended, half
    weight for the two before, and the larger of the two hours ahead (rain.parse). Without `coming`, the
    hours ahead are left out, as if nothing were forecast."""
    out = []
    for i, now in enumerate(values):
        before = sum(values[max(i - 2, 0):i])
        ahead = max(values[i + 1:i + 3], default=0.0) if coming else 0.0
        out.append(rain_index(now, now + before, ahead))
    return out


def watches(index, threshold=20):
    """The hours between which a watch would have stood, by the engine's own rule: [(opened, closed)] as
    places in the list. A watch still open at the end is closed there."""
    site, out, opened = Site("replay", rain_threshold_mm=threshold), [], None
    for hour, value in enumerate(index):
        if site.state == CLEAR and value < threshold:
            continue                              # the engine would note a dry hour and change nothing that a later hour reads
        site = apply_rain(site, value, hour * 3600)
        if site.state == WATCH and opened is None:
            opened = hour
        elif site.state == CLEAR and opened is not None:
            out.append((opened, hour))
            opened = None
    if opened is not None:
        out.append((opened, len(index)))
    return out


_KEPT = {}


def replayed(rain, source, cell, year, threshold=20, coming=True):
    """(first hour in UTC, the rain, the index, the watches) for one place and year, worked out once."""
    key = (id(rain), source, cell, year, threshold, coming)
    if key not in _KEPT:
        series = hourly(rain, source, cell, year)
        if series is None:
            _KEPT[key] = None
        else:
            index = indexes(series[1], coming)
            _KEPT[key] = (series[0], series[1], index, watches(index, threshold))
    return _KEPT[key]


def window(start, first_day, last_day):
    """The places in an hourly list, starting at `start` in UTC, that fall on these days in Indian time."""
    begin = datetime.fromisoformat(first_day) - IST
    finish = datetime.fromisoformat(last_day) + timedelta(days=1) - IST
    return int((begin - start).total_seconds() // 3600) + 1, int((finish - start).total_seconds() // 3600) + 1


def on_days(rain, source, cell, first_day, last_day, threshold=20, coming=True):
    """What the rule did at one place between two days: None with no rain history, else {open: whether a
    watch stood at any time in them, since: when the first one opened in Indian time, peak: the highest
    index, mm: the rain that fell}."""
    done = replayed(rain, source, cell, int(first_day[:4]), threshold, coming)
    if done is None:
        return None
    start, values, index, every = done
    first, last = window(start, first_day, last_day)
    if first < 0 or last > len(values):
        return None
    stood = [(a, b) for a, b in every if a < last and b > first]
    since = (start + timedelta(hours=stood[0][0]) + IST).strftime("%d %b %H:%M") if stood else None
    return {"open": bool(stood), "since": since, "peak": max(index[first:last], default=0.0), "mm": sum(values[first:last])}


def season(rain, source, cell, year, threshold=20, coming=True):
    """(watches opened, days in Indian time with a watch standing, days in the history) for one place and year."""
    done = replayed(rain, source, cell, year, threshold, coming)
    if done is None:
        return None
    start, values, _, stood = done
    days = set()
    for opened, closed in stood:
        for hour in range(opened, closed):
            days.add((start + timedelta(hours=hour) + IST).date())
    return len(stood), len(days), len(values) // 24


def caught(rain, rows, source, basis="place", threshold=20, coming=True):
    """(reports this source has rain for, how many had a watch standing on the day)."""
    cell = rain["cells"]
    had = [on_days(rain, source, cell[r["site"]], r["from"], r["to"], threshold, coming) for r in rows if r["basis"] == basis]
    had = [h for h in had if h is not None]
    return len(had), sum(h["open"] for h in had)


def watch_days(rain, source, years, threshold=20):
    """Days in a season with a watch standing, for one place on average, over these years; None with no history."""
    each = [season(rain, source, cell, year, threshold) for cell in rain["cells"].values() for year in years]
    each = [e for e in each if e is not None]
    return sum(e[1] for e in each) / len(each) if each else None


def study(rain, reports):
    """Everything the report is written from."""
    cell, names = rain["cells"], {key: s["name"] for key, s in sites().items()}
    years = sorted({int(y) for by_year in rain["series"][OWN].values() for y in by_year})
    full = [y for y in years if hourly(rain, HIGHEST, next(iter(cell.values())), y) is not None]       # the years all seven models are held
    rows = [dict(r, name=names[r["site"]], **{s: on_days(rain, s, cell[r["site"]], r["from"], r["to"]) for s in (OWN, HIGHEST)})
            for r in reports["reports"]]
    recent = [r for r in rows if int(r["from"][:4]) in full]
    advisory = reports["advisory_without_days"]
    undated = [dict(site=site, name=names[site], own=on_days(rain, OWN, cell[site], advisory["from"], advisory["to"])) for site in advisory["sites"]]
    models = {s: (caught(rain, recent, s), caught(rain, recent, s, "area"), watch_days(rain, s, full)) for s in (*MODELS, HIGHEST)}
    cost = {(s, y): [sum(e[k] for e in each) / len(each) for k in (0, 1)] + [each[0][2]]
            for s in (OWN, HIGHEST) for y in years
            for each in [[e for e in (season(rain, s, c, y) for c in cell.values()) if e is not None]] if each}
    sweep = {t: (caught(rain, rows, OWN, threshold=t), watch_days(rain, OWN, years, t),
                 caught(rain, recent, HIGHEST, threshold=t), watch_days(rain, HIGHEST, full, t)) for t in THRESHOLDS}
    gauges = []
    for g in reports["gauges"]:
        year = int(g["from"][:4])
        each = {m: on_days(rain, m, cell[g["site"]], g["from"], g["to"]) for m in MODELS}
        wettest = max((e["mm"] for e in each.values() if e is not None), default=None) if year in full else None
        gauges.append(dict(g, name=names[g["site"]], own=None if each[OWN] is None else each[OWN]["mm"], wettest=wettest))
    holds = {}
    for year in years:
        each = [hourly(rain, OWN, c, year)[1] for c in sorted(set(cell.values()))]
        holds[year] = (sum(sum(v) for v in each) / len(each), sum(sum(x > 0 for x in v) for v in each) / len(each),
                       max(max(v) for v in each), sum(sum(x >= 10 for x in v) for v in each) / len(each), len(each[0]) // 24)
    return {"rows": rows, "recent": recent, "undated": undated, "models": models, "cost": cost, "sweep": sweep, "gauges": gauges, "holds": holds,
            "advisory": advisory, "years": years, "full": full,
            "blind": (caught(rain, rows, OWN, coming=False), caught(rain, recent, HIGHEST, coming=False))}


def cell_of(result, absent="not held"):
    if result is None:
        return absent
    return f"watch from {result['since']}, index to {int(result['peak'])}" if result["open"] else f"**no watch**, index to {int(result['peak'])}"


def day_of(r):
    first, last = date.fromisoformat(r["from"]), date.fromisoformat(r["to"])
    return f"{first.day} {first:%b %Y}" if first == last else f"{first.day} to {last.day} {last:%b %Y}"


def of(pair):
    return f"{pair[1]} of {pair[0]}"


def report(found, rain):
    rows, full = found["rows"], found["full"]
    span = f"{full[0]} and {full[-1]}" if len(full) == 2 else ", ".join(map(str, full))
    lines = [
        "# The rain rule against the days these places were reported under water",
        "",
        "**Real rain history and real reports.** Written by `scripts/watch_history.py` from `data/flood-reports.json`,",
        "news reports found on 11 October 2026 that name one of the nine places or its neighbourhood as under water on a",
        "stated day, and `data/rain-history.json.gz`, hourly rain at each place from Open-Meteo, the provider the live",
        "system asks (CC BY 4.0). The engine's own rule is replayed over the rain hour by hour. This tests the first",
        "step of the system, the watch, and nothing after it. It is not a measurement of depth.",
        "",
        "\"The provider's own choice\" is the rain as the live system asks for it, with the provider picking the weather",
        "model. \"The highest of seven\" takes that and six models asked for by name, and uses the largest of the seven in each",
        f"hour; all seven are held for {span}.",
        "A watch opens when the rain index reaches 20 mm.",
        "",
        "## Each report",
        "",
        "| Place | Day | The report | The provider's own choice | The highest of seven models |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        said = ("Names the place. " if r["basis"] == "place" else "Names the area only. ") + f"[{r['publisher']}]({r['url']}): {r['says']}"
        lines.append(f"| {r['name']} | {day_of(r)} | {said} | {cell_of(r[OWN])} | {cell_of(r[HIGHEST], 'seven not held')} |")
    blind_own, blind_high = found["blind"]
    lines += ["", "## How many were caught", "",
              "| Reports | Rain | A watch stood on the day |", "|---|---|---|",
              f"| That name the place | The provider's own choice | {of(caught(rain, rows, OWN))} |",
              f"| That name the area only | The provider's own choice | {of(caught(rain, rows, OWN, 'area'))} |",
              f"| That name the place, {span} | The highest of seven models | {of(caught(rain, found['recent'], HIGHEST))} |",
              f"| That name the area only, {span} | The highest of seven models | {of(caught(rain, found['recent'], HIGHEST, 'area'))} |",
              "", f"With nothing forecast for the hours ahead, the rule counting only rain already fallen: {of(blind_own)} with the provider's own "
              f"choice, {of(blind_high)} with the highest of seven.", ""]
    advisory = found["advisory"]
    lines += [f"One more report gives no day. [{advisory['publisher']}]({advisory['url']}): {advisory['says']}", "",
              "| Place | The provider's own choice |", "|---|---|"]
    lines += [f"| {u['name']} | {cell_of(u['own'])} |" for u in found["undated"]]
    lines += ["", f"## Model by model, {span}", "",
              "The reports of those years, and the days from 1 March to 31 October with a watch standing, for one place on average.", "",
              "| Rain from | Caught, of those that name the place | Caught, of those that name the area | Watch days a season |", "|---|---|---|---|"]
    for source, (placed, area, days) in found["models"].items():
        label = "**The highest of the seven, hour by hour**" if source == HIGHEST else MODELS[source][0].upper() + MODELS[source][1:]
        lines.append(f"| {label} | {of(placed)} | {of(area)} | {days:.0f} |")
    lines += ["", "## What the rule costs, year by year", "",
              "| Year | Rain | Days of history | Watches opened at one place | Days with a watch standing |", "|---|---|---|---|---|"]
    for (source, year), (opened, days, length) in sorted(found["cost"].items(), key=lambda item: (item[0][1], item[0][0] == HIGHEST)):
        lines.append(f"| {year} | {'The highest of seven' if source == HIGHEST else 'The provider' + chr(39) + 's own choice'} | {length} | {opened:.0f} | {days:.0f} |")
    lines += ["", "## Other thresholds", "",
              "The reports that name the place, and the days in a season with a watch standing at one place, on average.", "",
              "| Threshold | Caught, the provider's own choice | Watch days a season | Caught, the highest of seven | Watch days a season |", "|---|---|---|---|---|"]
    for threshold in THRESHOLDS:
        own, own_days, high, high_days = found["sweep"][threshold]
        mark = "**" if threshold == 20 else ""
        lines.append(f"| {mark}{threshold} mm{mark} | {of(own)} | {own_days:.0f} | {of(high)} | {high_days:.0f} |")
    lines += ["", "## What the rain history holds", "",
              "The provider's own choice, at one forecast cell on average. A watch needs an index of 20 mm, which one hour of 20 mm gives by itself.", "",
              "| Year | Days | Rain in all | Hours with rain | Hours of 10 mm or more | The wettest hour at any of the cells |", "|---|---|---|---|---|---|"]
    for year, (total, wet, top, heavy, days) in found["holds"].items():
        lines.append(f"| {year} | {days} | {total:.0f} mm | {wet:.0f} | {heavy:.0f} | {top:.1f} mm |")
    lines += ["", "## The rain history against gauges", "",
              "Where a report gives what a rain gauge near the place recorded, beside what the rain history holds for the same days.", "",
              "| Place | Days | Gauge | The provider's own choice | The wettest of the seven models |", "|---|---|---|---|---|"]
    for g in found["gauges"]:
        show = lambda mm, absent: absent if mm is None else f"{mm:.0f} mm"      # noqa: E731
        lines.append(f"| {g['name']} | {day_of(g)} | [{g['where']}]({g['url']}): {g['mm']:.0f} mm | {show(g['own'], 'not held')} | {show(g['wettest'], 'seven not held')} |")
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
    rain = load()
    text = report(study(rain, json.loads(REPORTS.read_text("utf-8"))), rain)
    print(text)
    OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
