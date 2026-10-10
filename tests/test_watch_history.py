"""scripts/watch_history.py: the rain rule replayed over real rain history, against dated reports of real floods.

The rain history and the reports are in the repository, so the figures in docs/watch-history.md are
worked out again here and must match. The rest checks how the rule is replayed: by the engine's own
functions, on Indian days, with the hours ahead taken or left out.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import watch_history as wh  # noqa: E402

REPORTS = json.loads((ROOT / "data" / "flood-reports.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def rain():
    return wh.load()


@pytest.fixture(scope="module")
def found(rain):
    return wh.study(rain, REPORTS)


def test_the_index_is_the_live_systems_with_the_hours_ahead_taken_or_left_out():
    values = [0, 0, 6, 10, 2, 30, 0]
    with_coming, without = wh.indexes(values), wh.indexes(values, coming=False)
    assert without[3] == 10 + 0.5 * (0 + 6)                       # the hour just ended, half weight for the two before
    assert with_coming[3] == without[3] + 30                      # and the larger of the two hours ahead
    assert with_coming[0] == 6 and with_coming[-1] == 0 + 0.5 * (2 + 30)
    assert wh.indexes([]) == []


def test_a_watch_opens_and_closes_by_the_engines_own_rule():
    index = [0, 5, 25, 30, 4, 3, 2, 0, 22, 21]                    # over 20 twice
    assert wh.watches(index) == [(2, 5), (8, 10)]                 # shut after an hour of light rain; still open at the end
    assert wh.watches(index, threshold=40) == []
    assert wh.watches(index, threshold=5) == [(1, 5), (8, 10)]


def test_skipping_dry_hours_while_clear_changes_nothing(rain):
    from nirmaldhara.state import CLEAR, WATCH, Site, apply_rain
    index = wh.indexes(wh.hourly(rain, wh.HIGHEST, rain["cells"]["hyd-008"], 2025)[1])
    for threshold in (5, 20):
        site, plain, opened = Site("every hour", rain_threshold_mm=threshold), [], None
        for hour, value in enumerate(index):                      # the engine asked at every hour, dry or not
            site = apply_rain(site, value, hour * 3600)
            if site.state == WATCH and opened is None:
                opened = hour
            elif site.state == CLEAR and opened is not None:
                plain.append((opened, hour))
                opened = None
        if opened is not None:
            plain.append((opened, len(index)))
        assert wh.watches(index, threshold) == plain and len(plain) > 3


def test_a_day_is_an_indian_day():
    start = datetime(2025, 8, 1)                                  # the first hour of the history, in UTC
    first, last = wh.window(start, "2025-08-07", "2025-08-07")
    assert (first, last) == (6 * 24 - 5, 7 * 24 - 5)              # the hours ending 19:00 UTC on the 6th to 18:00 UTC on the 7th
    assert last - first == 24 and wh.window(start, "2025-08-07", "2025-08-08")[1] - first == 48


def test_every_report_has_a_place_a_day_and_a_page_it_came_from():
    places = wh.sites()
    assert len(REPORTS["reports"]) == 16 and sum(r["basis"] == "place" for r in REPORTS["reports"]) == 11
    for r in REPORTS["reports"]:
        assert r["site"] in places and r["basis"] in ("place", "area")
        assert date.fromisoformat(r["from"]) <= date.fromisoformat(r["to"]) <= date.fromisoformat(r["published"])
        assert r["url"].startswith("https://") and r["publisher"] and len(r["says"]) > 30
    assert set(REPORTS["advisory_without_days"]["sites"]) <= set(places)
    for g in REPORTS["gauges"]:
        assert g["site"] in places and g["mm"] > 0 and g["url"].startswith("https://")


def test_the_rain_history_is_the_providers_and_covers_every_report(rain):
    assert "Open-Meteo.com (CC BY 4.0)" in rain["credit"] and rain["cells"] == wh.cells()
    assert set(rain["series"]) == set(wh.MODELS)
    for r in REPORTS["reports"]:
        assert wh.on_days(rain, wh.OWN, rain["cells"][r["site"]], r["from"], r["to"]) is not None, r
    cell = rain["cells"]["hyd-008"]
    start, values = wh.hourly(rain, wh.OWN, cell, 2025)
    assert start == datetime(2025, 3, 1) and len(values) == 245 * 24 and min(values) == 0.0
    highest = wh.hourly(rain, wh.HIGHEST, cell, 2025)[1]
    assert all(top >= own for top, own in zip(highest, values)) and sum(highest) > sum(values)
    assert wh.hourly(rain, wh.HIGHEST, cell, 2019) is None        # only two of the seven are held that far back


def test_the_figures_in_the_report_are_the_ones_the_data_gives(rain, found):
    assert wh.caught(rain, found["rows"], wh.OWN) == (11, 0)                    # none of the eleven that name the place
    assert wh.caught(rain, found["rows"], wh.OWN, "area") == (5, 0)
    assert wh.caught(rain, found["recent"], wh.HIGHEST) == (7, 1)
    assert found["blind"][0] == (11, 0)
    assert found["full"] == [2025, 2026] and found["years"] == [2019, 2020, 2025, 2026]
    assert max(days for (source, _), (_, days, _) in found["cost"].items() if source == wh.OWN) <= 1.5
    own, _, high, high_days = found["sweep"][10]
    assert own == (11, 3) and high == (7, 6) and 35 < high_days < 50
    text = wh.report(found, rain)
    written = (ROOT / "docs" / "watch-history.md").read_text("utf-8")
    assert written.startswith(text)                                              # the notes follow the tables
    assert "| That name the place | The provider's own choice | 0 of 11 |" in text
    assert "| **20 mm** | 0 of 11 | 0 | 1 of 7 | 10 |" in text


def test_the_models_rain_is_set_beside_what_gauges_recorded(found):
    by_place = {(g["site"], g["from"]): g for g in found["gauges"]}
    lingampally = by_place[("hyd-001", "2025-06-11")]
    assert lingampally["mm"] == 148.5 and lingampally["own"] < 20 and lingampally["wettest"] < 100
    below = [g for g in found["gauges"] if g["own"] < 0.3 * g["mm"]]
    assert len(below) == 5 and len(found["gauges"]) == 6                         # five of six far below the gauge


def test_fetching_is_asked_for_and_nothing_else_reaches_out():
    source = (ROOT / "scripts" / "watch_history.py").read_text("utf-8")
    assert source.count("urlopen(") == 1 and "def fetch():" in source and 'if args.fetch:' in source
    for outside in ("requests", "boto3", "subprocess"):
        assert outside not in source, outside


def test_the_report_says_what_was_tested_what_was_found_and_what_it_is_not():
    report = (ROOT / "docs" / "watch-history.md").read_text("utf-8")
    assert report.splitlines()[2].startswith("**Real rain history and real reports.**")
    flat = " ".join(report.split())
    for must_say in ("It is not a measurement of depth", "The watch would not have opened for any of them",
                     "The rain it is fed is far too small", "No other model does better",
                     "The first step of the system does not work as built", "The 20 mm was never the question",
                     "What would mend it is rain measured on the ground", "Not a count of false alarms",
                     "Not a tuned threshold", "It is not a recommendation"):
        assert must_say in flat, must_say
    readme = " ".join((ROOT / "README.md").read_text("utf-8").split())
    assert "docs/watch-history.md" in readme and "would not have opened a watch on any of the 11" in readme
    writeup = " ".join((ROOT / "docs" / "submission-writeup.md").read_text("utf-8").split())
    assert "would not have opened on any of the 11" in writeup
    sources = (ROOT / "data" / "SOURCES.md").read_text("utf-8")
    assert "flood-reports.json" in sources and "rain-history.json.gz" in sources
