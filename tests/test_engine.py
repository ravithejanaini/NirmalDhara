"""The engine handler against an in-memory table and event bus."""

import json
import os

import pytest

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("SITES_TABLE", "sites")
os.environ.setdefault("EVENT_BUS", "nirmaldhara")

from handlers import engine  # noqa: E402
from nirmaldhara import store  # noqa: E402
from nirmaldhara.state import CRITICAL, WARNING, WATCH  # noqa: E402


class VersionMoved(Exception):
    pass


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key):
        item = self.items.get((Key["city"], Key["site_id"]))
        return {"Item": dict(item)} if item else {}

    def update_item(self, Key, ExpressionAttributeValues, **_):
        item = self.items.setdefault((Key["city"], Key["site_id"]), dict(Key))
        values = ExpressionAttributeValues
        if "version" in item and item["version"] != values[":expected"]:
            raise VersionMoved()
        item.update(doc=values[":doc"], state=values[":state"], version=values[":version"])


class FakeBus:
    def __init__(self):
        self.sent = []

    def put_events(self, Entries):
        self.sent.extend(Entries)


@pytest.fixture
def world(monkeypatch):
    table, bus = FakeTable(), FakeBus()
    monkeypatch.setattr(engine, "TABLE", table)
    monkeypatch.setattr(engine, "EVENTS", bus)
    return table, bus


def record(message_id, body):
    return {"messageId": message_id, "body": json.dumps({"city": "hyderabad", **body})}


def rain(index_mm, ts=0):
    return {"type": "rain", "site_id": "hyd-001", "index_mm": index_mm, "ts": ts}


def depth(ts, high, source="guardian", device="g1"):
    return {"type": "reading", "site_id": "hyd-001", "reading": {
        "ts": ts, "low": high - 5, "high": high, "confidence": 0.8,
        "source": source, "device": device}}


def test_rain_then_readings_walk_the_site_to_critical(world):
    table, bus = world
    out = engine.handler({"Records": [
        record("m1", rain(25)),
        record("m2", depth(300, 15)),
        record("m3", depth(600, 24)),
        record("m4", depth(900, 28)),
    ]}, None)

    assert out == {"batchItemFailures": []}
    site = store.load(table, "hyderabad", "hyd-001")
    assert site.state == CRITICAL
    assert site.version == 4
    changes = [json.loads(e["Detail"])["event"][1:3] for e in bus.sent
               if e["DetailType"] == "SiteStateChanged"]
    assert changes == [["CLEAR", WATCH], [WATCH, WARNING], [WARNING, CRITICAL]]


def test_registry_details_survive_a_state_write(world):
    table, _ = world
    table.items[("hyderabad", "hyd-001")] = {
        "city": "hyderabad", "site_id": "hyd-001", "lat": "17.4", "lon": "78.4",
        "rain_threshold_mm": "30"}

    engine.handler({"Records": [record("m1", rain(25))]}, None)   # below this site's 30 mm
    item = table.items[("hyderabad", "hyd-001")]
    assert item["lat"] == "17.4"
    assert item["state"] == "CLEAR"

    engine.handler({"Records": [record("m2", rain(35, ts=900))]}, None)
    assert table.items[("hyderabad", "hyd-001")]["state"] == WATCH


def test_a_bad_message_fails_alone(world):
    table, _ = world
    out = engine.handler({"Records": [
        {"messageId": "bad", "body": "not json"},
        record("ok", rain(25)),
    ]}, None)
    assert out == {"batchItemFailures": [{"itemIdentifier": "bad"}]}
    assert table.items[("hyderabad", "hyd-001")]["state"] == WATCH


def test_a_stale_write_is_refused(world):
    table, _ = world
    engine.handler({"Records": [record("m1", rain(25))]}, None)
    site = store.load(table, "hyderabad", "hyd-001")
    with pytest.raises(VersionMoved):
        store.save(table, "hyderabad", site, expected_version=0)
