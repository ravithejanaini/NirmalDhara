"""data/scenarios/evening.json against the real state and workflow functions.

The replay (scripts/replay.py) sends this file to a deployed system. This test sends it to
the same logic in memory, so a change to either the file or the rules that makes the demo
tell a different story fails here first.
"""

import json
from pathlib import Path

import pytest

from nirmaldhara import alerts, workflow
from nirmaldhara.state import CLEAR, Reading, Site, apply_rain, apply_reading

PATH = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "evening.json"
SCENARIO = json.loads(PATH.read_text(encoding="utf-8"))
MIN = 60


def run(site_key):
    """Play one site's events, stepping the workflow once a minute as the timer does."""
    events = [e for e in SCENARIO["events"] if e["site"] == site_key]
    site, flood = Site(site_key), None
    reached, kinds, outcome = [], set(), None
    for minute in range(SCENARIO["duration_min"] + 1):
        now = minute * MIN
        for e in (e for e in events if e["t_min"] == minute):
            if e["type"] == "rain":
                site = apply_rain(site, e["index_mm"], now)
            else:
                site = apply_reading(site, Reading(
                    now, e["low"], e["high"], e["confidence"], e["source"], e["device"]))
            reached += [ev[2] for ev in site.events if ev[0] == "SiteStateChanged"]
        if flood is None:
            if site.state == CLEAR:
                continue
            flood = workflow.open_event(site_key, site.since)
        flood = workflow.fold(flood, site, now)
        plan = workflow.plan(flood, site, now)
        kinds |= {kind for _, _, kind, _ in workflow.messages(flood, site, plan, now)}
        flood = workflow.record(flood, site, plan, now)
        if plan.close:
            outcome, flood = plan.close, None
    return site, reached, kinds, outcome


@pytest.mark.parametrize("key", sorted(SCENARIO["sites"]))
def test_each_site_tells_the_story_the_file_says(key):
    expect = SCENARIO["sites"][key]["expect"]
    site, reached, kinds, outcome = run(key)
    assert site.state == expect["final_state"]
    assert reached == expect["reached"]
    assert outcome == expect["outcome"]
    assert ("closure_recommendation" in kinds) == expect["closure_recommended"]
    assert ("do_not_enter" in kinds) == expect["residents_told_do_not_enter"]
    if "trusted" in expect:
        assert site.trusted == expect["trusted"]


def test_the_file_is_well_formed():
    events = SCENARIO["events"]
    assert set(SCENARIO["sites"]) == {"a", "b", "c", "d"}
    assert events == sorted(events, key=lambda e: (e["t_min"], e["site"], e["type"] != "rain"))
    assert all(0 <= e["t_min"] <= SCENARIO["duration_min"] for e in events)
    assert all(e["site"] in SCENARIO["sites"] for e in events)
    for e in events:
        if e["type"] == "reading":
            assert 0 <= e["low"] <= e["high"] and 0 <= e["confidence"] <= 1
            assert e["source"] in ("cctv", "guardian", "resident")
        else:
            assert e["type"] == "rain" and e["index_mm"] >= 0
    # Rain arrives every 15 minutes for every site, as the rain check does.
    for key in SCENARIO["sites"]:
        times = [e["t_min"] for e in events if e["site"] == key and e["type"] == "rain"]
        assert times == list(range(0, SCENARIO["duration_min"] + 1, 15))
    # No two readings for a site fall within the 2-minute jump window.
    for key in SCENARIO["sites"]:
        times = [e["t_min"] for e in events if e["site"] == key and e["type"] == "reading"]
        assert all(b - a >= 3 for a, b in zip(times, times[1:]))
