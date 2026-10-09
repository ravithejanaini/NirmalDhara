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


VersionMoved = store.VersionMoved


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, **_):
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
        self.sent, self.failing = [], False

    def put_events(self, Entries):
        if self.failing:
            raise RuntimeError("the bus is unavailable")
        self.sent.extend(Entries)

    def of(self, detail_type):
        return [json.loads(e["Detail"]) for e in self.sent if e["DetailType"] == detail_type]


@pytest.fixture
def world(monkeypatch):
    table, bus = FakeTable(), FakeBus()
    monkeypatch.setattr(engine, "TABLE", table)
    monkeypatch.setattr(engine, "EVENTS", bus)
    return table, bus


def record(message_id, body):
    return {"messageId": message_id, "body": json.dumps({"city": "hyderabad", **body}),
            "attributes": {"MessageGroupId": body["site_id"]}}


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


def test_a_changed_registry_threshold_takes_effect(world):
    table, _ = world
    table.items[("hyderabad", "hyd-001")] = {
        "city": "hyderabad", "site_id": "hyd-001", "rain_threshold_mm": "30"}
    engine.handler({"Records": [record("m1", rain(25))]}, None)
    assert table.items[("hyderabad", "hyd-001")]["state"] == "CLEAR"

    table.items[("hyderabad", "hyd-001")]["rain_threshold_mm"] = "20"
    engine.handler({"Records": [record("m2", rain(25, ts=900))]}, None)
    assert table.items[("hyderabad", "hyd-001")]["state"] == WATCH


def test_a_lost_race_is_retried_at_once(world, monkeypatch):
    table, _ = world
    real_save, calls = store.save, []

    def flaky_save(*args):
        calls.append(1)
        if len(calls) == 1:
            raise store.VersionMoved()
        real_save(*args)

    monkeypatch.setattr(store, "save", flaky_save)
    out = engine.handler({"Records": [record("m1", rain(25))]}, None)
    # Lost, saved, and then the write that takes the published event out of the record.
    assert out == {"batchItemFailures": []} and len(calls) == 3
    assert table.items[("hyderabad", "hyd-001")]["state"] == WATCH


def test_a_stale_write_is_refused(world):
    table, _ = world
    engine.handler({"Records": [record("m1", rain(25))]}, None)
    site = store.load(table, "hyderabad", "hyd-001")
    with pytest.raises(VersionMoved):
        store.save(table, "hyderabad", site, expected_version=0)


def test_an_event_saved_but_not_published_goes_out_when_the_message_comes_back(world):
    table, bus = world
    bus.failing = True                              # dies after the save, before the publish
    out = engine.handler({"Records": [record("m1", rain(25))]}, None)
    assert out == {"batchItemFailures": [{"itemIdentifier": "m1"}]}
    assert table.items[("hyderabad", "hyd-001")]["state"] == WATCH and bus.sent == []

    bus.failing = False
    out = engine.handler({"Records": [record("m1", rain(25))]}, None)   # redelivered
    assert out == {"batchItemFailures": []}
    assert [e["event"][1:3] for e in bus.of("SiteStateChanged")] == [["CLEAR", WATCH]]
    site = store.load(table, "hyderabad", "hyd-001")
    assert site.version == 1 and site.events == ()  # not applied again, nothing left to send


def test_an_unpublished_event_goes_out_with_the_next_message_if_the_first_never_returns(world):
    table, bus = world
    bus.failing = True
    engine.handler({"Records": [record("m1", rain(25))]}, None)
    bus.failing = False

    engine.handler({"Records": [record("m2", rain(26, ts=900))]}, None)  # the next rain check
    assert [e["event"][1:3] for e in bus.of("SiteStateChanged")] == [["CLEAR", WATCH]]
    assert store.load(table, "hyderabad", "hyd-001").events == ()


def test_a_redelivered_reading_is_counted_once(world):
    table, bus = world
    engine.handler({"Records": [record("m1", rain(25)), record("m2", depth(300, 15))]}, None)
    bus.failing = True
    engine.handler({"Records": [record("m3", depth(600, 24))]}, None)
    bus.failing = False
    engine.handler({"Records": [record("m3", depth(600, 24))]}, None)
    engine.handler({"Records": [record("m9", depth(600, 24))]}, None)   # sent again as new

    site = store.load(table, "hyderabad", "hyd-001")
    assert [r.high for r in site.readings] == [15, 24]
    assert len(bus.of("ReadingAccepted")) == 2


def test_only_the_last_few_message_keys_are_kept(world):
    table, _ = world
    for n in range(engine.KEYS_KEPT + 10):
        engine.handler({"Records": [record(f"m{n}", rain(5, ts=n))]}, None)
    assert len(store.load(table, "hyderabad", "hyd-001").applied) == engine.KEYS_KEPT


def test_after_a_failure_the_sites_later_messages_wait_their_turn(world):
    table, bus = world
    other = {"type": "rain", "site_id": "hyd-002", "index_mm": 25, "ts": 0}
    broken = {"messageId": "m1", "body": "not json",
              "attributes": {"MessageGroupId": "hyd-001"}}
    out = engine.handler({"Records": [
        broken, record("m2", rain(25)), record("m3", other)]}, None)

    assert out == {"batchItemFailures": [{"itemIdentifier": "m1"}, {"itemIdentifier": "m2"}]}
    assert ("hyderabad", "hyd-001") not in table.items       # m2 was not applied ahead of m1
    assert table.items[("hyderabad", "hyd-002")]["state"] == WATCH
