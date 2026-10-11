"""scripts/chennai_watch.py: the Hyderabad rain rule, unchanged, against Chennai's subways and the days they were closed.

The rain history and the reports are in the repository, so the figures in docs/chennai-watch.md are
worked out again here and must match.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import chennai_watch as cw  # noqa: E402
import watch_history as wh  # noqa: E402

REPORTS = json.loads((ROOT / "data" / "chennai-flood-reports.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def rain():
    return cw.load()


def test_every_report_names_a_listed_place_a_day_and_the_page_it_came_from():
    known = cw.sites()
    assert len(known) == 9 and all(s["rain_threshold_mm"] == 20 for s in known.values())
    for event in REPORTS["events"]:
        assert event["from"] <= event["to"] and event["url"].startswith("https://")
        assert event["sites"] and set(event["sites"]) <= set(known)
    assert sum(len(e["sites"]) for e in REPORTS["events"]) == 17


def test_the_rule_is_hyderabads_and_not_a_copy_of_it():
    assert cw.indexes is wh.indexes and cw.watches is wh.watches and cw.URL == wh.URL


def test_the_watch_opens_on_the_cyclone_and_on_none_of_the_smaller_rains(rain):
    rows = cw.study(rain, REPORTS)
    assert cw.caught(rows) == (17, 9)
    for event, _, _, result in rows:
        assert result["open"] == (event["name"] == "Cyclone Michaung")
    small = [r for e, _, _, r in rows if e["name"] != "Cyclone Michaung"]
    assert max(r["top_hour"] for r in small) < 10                 # the history never rains hard on those days


def test_the_watch_was_not_ahead_of_the_published_closures(rain):
    cyclone = [r for e, _, _, r in cw.study(rain, REPORTS) if e["name"] == "Cyclone Michaung"]
    first = min(r["since"] for r in cyclone)
    assert first.strftime("%d %b %H:%M") == "04 Dec 04:30"        # the list of closed subways was published at 04:10


def test_the_report_on_disk_is_the_one_the_data_gives(rain):
    text = cw.report(rain, REPORTS)
    assert "**A watch stood on 9 of 17 reports.**" in text and "Nothing is deployed in Chennai" in text
    assert (ROOT / "docs" / "chennai-watch.md").read_text("utf-8").startswith(text)
