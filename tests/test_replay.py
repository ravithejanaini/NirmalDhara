"""scripts/replay.py (the schedule) and scripts/reset.py (what it clears and what it leaves)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import replay  # noqa: E402
import reset  # noqa: E402
from nirmaldhara import store, workflow  # noqa: E402
from nirmaldhara.state import Site, apply_rain  # noqa: E402

SCENARIO = json.loads((ROOT / "data" / "scenarios" / "evening.json").read_text("utf-8"))
START = 1_800_000_000


# --- the schedule ---------------------------------------------------------------------------

def test_default_speed_plays_ninety_minutes_in_two():
    steps = replay.plan(SCENARIO, replay.DEFAULT_SITES, START, 45)
    assert len(steps) == 43 and steps[0]["delay_s"] == 0
    assert steps[-1]["delay_s"] == pytest.approx(120.0)             # 90 min at 45x


def test_real_time_speed_keeps_the_scenarios_own_clock():
    steps = replay.plan(SCENARIO, replay.DEFAULT_SITES, START, 1)
    assert steps[-1]["delay_s"] == 90 * 60


def test_messages_carry_simulated_times_not_wall_clock_times():
    steps = replay.plan(SCENARIO, replay.DEFAULT_SITES, START, 45)
    for step in steps:
        message = step["message"]
        ts = message["ts"] if message["type"] == "rain" else message["reading"]["ts"]
        assert ts == START + step["sim_min"] * 60


def test_every_message_is_for_a_mapped_registry_site_in_order_per_site():
    steps = replay.plan(SCENARIO, replay.DEFAULT_SITES, START, 45)
    assert {s["site"] for s in steps} == set(replay.DEFAULT_SITES.values())
    assert [s["delay_s"] for s in steps] == sorted(s["delay_s"] for s in steps)
    for site in replay.DEFAULT_SITES.values():
        times = [s["sim_min"] for s in steps if s["site"] == site]
        assert times == sorted(times)


def test_the_plan_is_the_scenario_and_nothing_else():
    steps = replay.plan(SCENARIO, replay.DEFAULT_SITES, START, 45)
    readings = [s["message"]["reading"] for s in steps if s["message"]["type"] == "reading"]
    assert len(readings) == 15 and all(r["low"] <= r["high"] for r in readings)
    assert {r["source"] for r in readings} == {"guardian", "resident"}
    assert all(r["device"].startswith(("guardian", "resident")) for r in readings)


def test_sites_can_be_remapped_and_bad_mappings_are_refused():
    assert replay.parse_sites("b=hyd-009")["b"] == "hyd-009"
    assert replay.parse_sites("")["a"] == "hyd-006"
    for bad in ("e=hyd-001", "a=somewhere", "a=hyd-002"):          # unknown key, not a site, duplicate
        with pytest.raises(ValueError):
            replay.parse_sites(bad)


def test_a_scenario_site_with_no_registry_site_is_refused():
    with pytest.raises(ValueError, match="no registry site"):
        replay.plan(SCENARIO, {"a": "hyd-006"}, START, 45)
    with pytest.raises(ValueError):
        replay.plan(SCENARIO, replay.DEFAULT_SITES, START, 0)


# --- reset ------------------------------------------------------------------------------------

class Sites:
    def __init__(self):
        self.items = {("hyderabad", "hyd-006"): {
            "city": "hyderabad", "site_id": "hyd-006", "name": "Lakdikapul", "lat": "17.4", "lon": "78.4",
            "rain_threshold_mm": "20", "doc": "{}", "state": "WARNING", "version": 9}}

    def get_item(self, Key, **_):
        item = self.items.get((Key["city"], Key["site_id"]))
        return {"Item": dict(item)} if item else {}

    def update_item(self, Key, ExpressionAttributeNames, **_):
        item = self.items[(Key["city"], Key["site_id"])]
        for real in ExpressionAttributeNames.values():
            item.pop(real, None)


class Floods:
    def __init__(self, *events):
        self.items = {(e.site_id, e.start): {"site_id": e.site_id, "start": e.start,
                                            "doc": json.dumps(e.__dict__), "version": e.version} for e in events}

    def query(self, ExpressionAttributeValues=None, KeyConditionExpression=None, **options):
        """Accepts both forms real DynamoDB does: store.py's expression string, or a Key condition."""
        site = (ExpressionAttributeValues[":s"] if ExpressionAttributeValues
                else KeyConditionExpression.get_expression()["values"][1])
        found = [i for (key, _), i in self.items.items() if key == site]
        newest_first = sorted(found, key=lambda i: i["start"], reverse=True)
        return {"Items": newest_first[:options["Limit"]] if "Limit" in options else found}

    def update_item(self, Key, ExpressionAttributeValues, **_):
        item = self.items[(Key["site_id"], Key["start"])]
        if item["version"] != ExpressionAttributeValues[":expected"]:
            raise store.VersionMoved()
        item.update(doc=ExpressionAttributeValues[":doc"], version=ExpressionAttributeValues[":version"])

    def delete_item(self, Key):
        self.items.pop((Key["site_id"], Key["start"]))


class Alerts:
    def __init__(self):
        self.items = {"hyd-006#1#residents#0#warning": {"alert_id": "hyd-006#1#residents#0#warning", "site_id": "hyd-006"},
                      "hyd-002#1#residents#0#warning": {"alert_id": "hyd-002#1#residents#0#warning", "site_id": "hyd-002"}}

    def scan(self, **_):
        return {"Items": [i for i in self.items.values() if i["site_id"] == "hyd-006"]}

    def delete_item(self, Key):
        self.items.pop(Key["alert_id"])


def open_flood(site="hyd-006", start=100):
    return workflow.open_event(site, start)


def test_reset_removes_the_engines_record_and_keeps_the_registry():
    sites = Sites()
    assert reset.clear_engine_record(sites, "hyd-006", apply=False) is True
    assert "state" in sites.items[("hyderabad", "hyd-006")]                 # a dry run changes nothing
    reset.clear_engine_record(sites, "hyd-006", apply=True)
    item = sites.items[("hyderabad", "hyd-006")]
    assert not {"doc", "state", "version"} & set(item)
    assert (item["name"], item["lat"], item["rain_threshold_mm"]) == ("Lakdikapul", "17.4", "20")
    assert reset.clear_engine_record(sites, "hyd-006", apply=True) is False   # already clear


def test_a_cleared_site_reads_as_clear_to_the_engine():
    sites = Sites()
    reset.clear_engine_record(sites, "hyd-006", apply=True)
    site = store.load(sites, "hyderabad", "hyd-006")
    assert (site.state, site.version) == ("CLEAR", 0) and site.rain_threshold_mm == 20


def test_an_open_flood_is_closed_as_reset_and_a_closed_one_is_left_alone():
    closed = workflow.record(open_flood("hyd-006", 50), Site("hyd-006", state="CLEAR"),
                             workflow.plan(open_flood("hyd-006", 50), Site("hyd-006", state="CLEAR"), 60), 60)
    floods = Floods(closed, open_flood("hyd-006", 100))
    assert reset.close_open_flood(floods, "hyd-006", 500, apply=False) == 100
    assert json.loads(floods.items[("hyd-006", 100)]["doc"])["closed_at"] is None       # dry run
    assert reset.close_open_flood(floods, "hyd-006", 500, apply=True) == 100
    doc = json.loads(floods.items[("hyd-006", 100)]["doc"])
    assert doc["closed_at"] == 500 and doc["outcome"] == "reset"
    assert json.loads(floods.items[("hyd-006", 50)]["doc"])["outcome"] == "no_flood"   # history kept
    assert reset.close_open_flood(floods, "hyd-006", 600, apply=True) is None


def test_forget_deletes_only_this_sites_records():
    floods, alerts = Floods(open_flood("hyd-006", 100), open_flood("hyd-002", 100)), Alerts()
    assert reset.forget_floods(floods, alerts, "hyd-006", apply=False) == (1, 1) and len(floods.items) == 2
    assert reset.forget_floods(floods, alerts, "hyd-006", apply=True) == (1, 1)
    assert list(floods.items) == [("hyd-002", 100)] and list(alerts.items) == ["hyd-002#1#residents#0#warning"]


def test_only_this_sites_timers_are_stopped():
    class Steps:
        def __init__(self):
            self.stopped = []

        def list_executions(self, **_):
            return {"executions": [
                {"name": "hyd-006-100", "executionArn": "arn:x:execution:m:hyd-006-100"},
                {"name": "hyd-0061-100", "executionArn": "arn:x:execution:m:hyd-0061-100"},
                {"name": "hyd-002-100", "executionArn": "arn:x:execution:m:hyd-002-100"}]}

        def stop_execution(self, executionArn, **_):
            self.stopped.append(executionArn)

    steps = Steps()
    assert reset.stop_timers(steps, "m", "hyd-006", apply=False) == ["hyd-006-100"] and steps.stopped == []
    reset.stop_timers(steps, "m", "hyd-006", apply=True)
    assert steps.stopped == ["arn:x:execution:m:hyd-006-100"]
