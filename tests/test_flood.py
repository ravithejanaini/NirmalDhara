"""The flood reactor, ticker and notifier against in-memory tables, bus and topic."""

import json
import os

import pytest

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
for name in ("SITES_TABLE", "FLOODS_TABLE", "ALERTS_TABLE", "EVENT_BUS", "ALERTS_TOPIC"):
    os.environ.setdefault(name, name.lower())
os.environ.setdefault("FLOOD_STATE_MACHINE", "arn:flood")

from handlers import flood, notifier  # noqa: E402
from nirmaldhara import alerts, store, workflow  # noqa: E402
from nirmaldhara.state import (CLEAR, WARNING, Reading, Site, apply_rain,  # noqa: E402
                               apply_reading)

CITY, SITE = "hyderabad", "hyd-001"
MIN = 60


class SitesTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, **_):
        item = self.items.get((Key["city"], Key["site_id"]))
        return {"Item": dict(item)} if item else {}

    def update_item(self, Key, ExpressionAttributeValues, **_):
        item = self.items.setdefault((Key["city"], Key["site_id"]), dict(Key))
        item.update(doc=ExpressionAttributeValues[":doc"])


class FloodsTable:
    def __init__(self):
        self.items = {}

    def query(self, ExpressionAttributeValues, **_):
        mine = [i for (site_id, _), i in self.items.items()
                if site_id == ExpressionAttributeValues[":s"]]
        return {"Items": sorted(mine, key=lambda i: i["start"], reverse=True)[:1]}

    def update_item(self, Key, ExpressionAttributeValues, **_):
        values = ExpressionAttributeValues
        item = self.items.get((Key["site_id"], Key["start"]))
        if item is not None and item["version"] != values[":expected"]:
            raise store.VersionMoved()
        self.items[(Key["site_id"], Key["start"])] = {
            **Key, "doc": values[":doc"], "version": values[":version"]}


class AlertsTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item, ExpressionAttributeValues, **_):
        old = self.items.get(Item["alert_id"])
        stale = ExpressionAttributeValues[":stale"]
        if old is not None and (old["sent"] or old["claimed_at"] >= stale):
            raise store.VersionMoved()
        self.items[Item["alert_id"]] = dict(Item)

    def update_item(self, Key, **_):
        self.items[Key["alert_id"]]["sent"] = True


class Bus:
    def __init__(self):
        self.sent = []

    def put_events(self, Entries):
        self.sent.extend(Entries)

    def of(self, detail_type):
        return [json.loads(e["Detail"]) for e in self.sent if e["DetailType"] == detail_type]


class Topic:
    def __init__(self):
        self.messages, self.failing = [], False

    def publish(self, Message, MessageAttributes, **_):
        if self.failing:
            raise RuntimeError("the topic is unavailable")
        self.messages.append((MessageAttributes["audience"]["StringValue"], Message))


class Machine:
    class exceptions:
        class ExecutionAlreadyExists(Exception):
            pass

    def __init__(self):
        self.started, self.ended = [], set()

    def start_execution(self, name, input, **_):
        if name in self.ended:
            raise self.exceptions.ExecutionAlreadyExists()
        if name not in [n for n, _ in self.started]:
            self.started.append((name, json.loads(input)))


class World:
    def __init__(self, monkeypatch):
        self.sites, self.floods, self.claims = SitesTable(), FloodsTable(), AlertsTable()
        self.bus, self.topic, self.machine = Bus(), Topic(), Machine()
        self.now = 0
        for module in (flood, notifier):
            monkeypatch.setattr(module, "SITES", self.sites)
            monkeypatch.setattr(module, "EVENTS", self.bus)
        monkeypatch.setattr(flood, "FLOODS", self.floods)
        monkeypatch.setattr(flood, "STATES", self.machine)
        monkeypatch.setattr(notifier, "ALERTS", self.claims)
        monkeypatch.setattr(notifier, "SNS", self.topic)
        monkeypatch.setattr(flood.time, "time", lambda: self.now)

    def put(self, site):
        store.save(self.sites, CITY, site, site.version)

    def react(self, minute):
        self.now = minute * MIN
        return flood.reactor({"detail": {"city": CITY, "site_id": SITE}}, None)

    def tick(self, minute, start=0, loops=0):
        self.now = minute * MIN
        return flood.tick({"city": CITY, "site_id": SITE, "start": start, "loops": loops}, None)

    def deliver(self):
        """Hand every requested alert to the notifier, as the bus would."""
        requests = [e for e in self.bus.sent
                    if e["DetailType"] in ("AlertRequested", "PhotoRequested")]
        return [notifier.handler({"detail": json.loads(e["Detail"])}, None) for e in requests]


@pytest.fixture
def world(monkeypatch):
    return World(monkeypatch)


def reading(minute, high, confidence=0.8):
    return Reading(minute * MIN, max(0, high - 5), high, confidence, "guardian", "g1")


def watch():
    return apply_rain(Site(SITE), 25, 0)


def test_a_clear_site_opens_nothing(world):
    world.put(Site(SITE))
    assert world.react(0) == {"opened": False}
    assert world.floods.items == {} and world.bus.sent == [] and world.machine.started == []


def test_a_watch_opens_an_event_asks_for_photos_and_starts_the_timer(world):
    world.put(watch())
    assert world.react(0) == {"opened": True}

    [ask] = world.bus.of("PhotoRequested")
    assert ask["audience"] == alerts.GUARDIANS
    assert ask["alert_id"] == "hyd-001#0#guardians#0#photo_request"
    assert world.bus.of("AlertRequested") == []
    assert world.machine.started == [
        ("hyd-001-0", {"city": CITY, "site_id": SITE, "start": 0})]
    assert store.load_open_event(world.floods, SITE).version == 1


def test_a_warning_alerts_each_audience_once_however_often_it_is_run(world):
    world.put(apply_reading(watch(), reading(5, 16, confidence=0.7)))
    world.react(5)
    world.tick(5)
    world.react(6)

    requested = world.bus.of("AlertRequested")
    assert sorted(a["audience"] for a in requested) == sorted(
        [alerts.RESIDENTS, alerts.TRAFFIC, alerts.PUMP, alerts.FLEET])
    assert all(a["confidence"] == 0.7 and a["state"] == WARNING for a in requested)
    assert len(world.machine.started) == 1


def test_a_lost_race_sends_the_same_ids_again_and_the_notifier_drops_them(world, monkeypatch):
    world.put(apply_reading(watch(), reading(5, 16)))
    real_save, calls = store.save_event, []

    def lose_once(table, event, expected):
        calls.append(1)
        if len(calls) == 1:
            # The other caller ran the same step and saved it first.
            real_save(table, event, expected)
            raise store.VersionMoved()
        real_save(table, event, expected)

    monkeypatch.setattr(store, "save_event", lose_once)
    world.react(5)

    ids = [e["alert_id"] for e in world.bus.of("AlertRequested") + world.bus.of("PhotoRequested")]
    assert len(calls) == 2
    assert len(ids) == 5 and len(set(ids)) == 5     # decided again: nothing new was due
    world.bus.sent *= 2                             # and the bus delivers everything twice
    outcomes = world.deliver()
    assert sum(o["sent"] for o in outcomes) == 5 and len(world.topic.messages) == 5


def test_a_milder_alert_from_an_older_view_cannot_stand_in_for_a_stronger_one(world):
    older = apply_reading(watch(), reading(5, 16))                 # WARNING
    newer = older
    for r in (reading(6, 26), reading(7, 30)):
        newer = apply_reading(newer, r)                            # CRITICAL
    event = workflow.open_event(SITE, 0)

    def residents(site):
        plan = workflow.plan(event, site, 7 * MIN)
        return [m for m in workflow.messages(event, site, plan, 7 * MIN)
                if m[1] == alerts.RESIDENTS][0]

    assert residents(older)[2] == "warning" and residents(newer)[2] == "do_not_enter"
    assert residents(older)[0] != residents(newer)[0]


def test_two_callers_opening_the_same_flood_write_one_event(world):
    world.put(apply_rain(Site(SITE), 25, 40))       # left CLEAR at second 40
    first, _, _ = flood.run(CITY, SITE, 41)
    world.floods.items.clear()                      # the second caller has not seen it yet
    second, _, _ = flood.run(CITY, SITE, 43)
    assert first.start == second.start == 40


def test_the_timer_is_started_by_a_later_step_if_the_first_one_failed_to(world):
    world.put(watch())
    flood.run(CITY, SITE, 0)                        # event saved, then the reactor died
    assert world.machine.started == []
    world.react(1)
    assert [name for name, _ in world.machine.started] == ["hyd-001-0"]

    world.machine.ended.add("hyd-001-0")            # handed over to a continuation
    world.react(2)                                  # must not raise


def test_tick_reports_how_long_to_wait_and_counts_loops(world):
    world.put(watch())
    world.react(0)
    assert world.tick(2, loops=7) == {
        "city": CITY, "site_id": SITE, "start": 0, "done": False, "wait_s": 120, "loops": 8}

    world.put(apply_reading(watch(), reading(5, 16)))
    assert world.tick(5)["wait_s"] == 60


def test_tick_closes_the_event_when_the_site_clears(world):
    world.put(apply_reading(watch(), reading(5, 16)))
    world.react(5)
    world.put(Site(SITE, state=CLEAR, version=9))

    assert world.tick(90)["done"] is True
    [closed] = world.bus.of("EventClosed")
    assert closed["outcome"] == workflow.FLOOD and closed["peak_depth_cm_high"] == 16
    assert closed["city"] == CITY and closed["end"] == 90 * MIN
    assert store.load_open_event(world.floods, SITE) is None
    assert world.tick(91)["done"] is True           # a late tick finds nothing to do


def test_a_timer_left_over_from_an_earlier_flood_stops(world):
    world.put(watch())
    world.react(0)
    world.put(Site(SITE, state=CLEAR, version=5))
    world.tick(70)
    world.put(apply_rain(Site(SITE, version=6), 25, 200 * MIN))
    world.react(200)

    assert world.tick(201, start=0)["done"] is True
    assert world.tick(201, start=200 * MIN)["done"] is False


def test_notifier_words_the_alert_from_the_registry_name_and_the_reading(world):
    world.sites.items[(CITY, SITE)] = {"city": CITY, "site_id": SITE, "name": "Malakpet RUB"}
    world.put(apply_reading(watch(), reading(5, 16, confidence=0.7)))
    world.react(5)
    world.deliver()

    sent = dict(world.topic.messages)
    assert set(sent) == {alerts.RESIDENTS, alerts.TRAFFIC, alerts.PUMP, alerts.FLEET,
                         alerts.GUARDIANS}
    assert sent[alerts.RESIDENTS].startswith("Water at Malakpet RUB is shin deep (11-16 cm")
    assert "seen 5:35 am" in sent[alerts.RESIDENTS]
    assert "confidence 0.7" in sent[alerts.TRAFFIC]
    assert "send a photo" in sent[alerts.GUARDIANS]
    assert len(world.bus.of("AlertSent")) == 5


def test_a_failed_send_is_not_lost(world):
    world.put(watch())
    world.react(0)

    world.topic.failing = True
    with pytest.raises(RuntimeError):
        world.deliver()
    world.topic.failing = False

    world.now = 10                                  # a retry inside the lease waits
    assert world.deliver() == [{"sent": False, "reason": "repeat"}]
    world.now = 60                                  # the first real retry comes a minute later
    assert world.deliver() == [{"sent": True}]
    assert world.deliver() == [{"sent": False, "reason": "repeat"}]
    assert len(world.topic.messages) == 1


def test_a_step_that_keeps_losing_the_race_gives_up_loudly(world, monkeypatch):
    world.put(watch())

    def always_lose(*_):
        raise store.VersionMoved()

    monkeypatch.setattr(store, "save_event", always_lose)
    with pytest.raises(store.VersionMoved):
        world.react(0)
