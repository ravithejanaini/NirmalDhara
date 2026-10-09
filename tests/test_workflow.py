import random

from nirmaldhara import alerts, workflow as wf
from nirmaldhara.state import (CLEAR, CRITICAL, WARNING, WATCH, Reading, Site, apply_rain,
                               apply_reading)

MIN = 60


def reading(minute, high, source="guardian", device="g1"):
    return Reading(minute * MIN, max(0, high - 5), high, 0.8, source, device)


def step(event, site, now):
    """One orchestration step, as the reactor or the ticker runs it."""
    event = wf.fold(event, site, now)
    plan = wf.plan(event, site, now)
    return wf.record(event, site, plan, now), plan, wf.messages(event, site, plan, now)


def watching():
    site = apply_rain(Site("hyd-001"), 25, 0)
    return site, wf.open_event("hyd-001", 0)


def test_a_watch_asks_for_photos_and_alerts_nobody():
    site, event = watching()
    event, plan, sent = step(event, site, 0)
    assert plan.alerts == {} and plan.ask_photos and plan.wait_s == 120
    assert [(m[1], m[2]) for m in sent] == [(alerts.GUARDIANS, "photo_request")]
    assert event.asks == 1


def test_photo_requests_stop_after_three_unanswered_and_resume_on_a_reading():
    site, event = watching()
    asked_at = []
    for minute in range(0, 61, 2):
        event, plan, _ = step(event, site, minute * MIN)
        if plan.ask_photos:
            asked_at.append(minute)
    assert asked_at == [0, 10, 20]            # every 10 minutes in a watch, then silence

    site = apply_reading(site, reading(62, 8))
    event, plan, _ = step(event, site, 63 * MIN)
    assert plan.ask_photos and event.unanswered_asks == 1


def test_warning_alerts_each_audience_once():
    site, event = watching()
    site = apply_reading(site, reading(5, 16))
    assert site.state == WARNING
    event, plan, sent = step(event, site, 5 * MIN)
    assert set(plan.alerts) == {alerts.RESIDENTS, alerts.TRAFFIC, alerts.PUMP, alerts.FLEET}
    assert plan.wait_s == 60

    event, plan, _ = step(event, site, 6 * MIN)
    assert plan.alerts == {}


def test_two_callers_at_once_produce_the_same_alert_ids():
    site, event = watching()
    site = apply_reading(site, reading(5, 16))
    _, _, from_reactor = step(event, site, 5 * MIN)
    _, _, from_ticker = step(event, site, 5 * MIN + 2)
    assert [m[0] for m in from_reactor] == [m[0] for m in from_ticker]
    assert from_reactor[0][0] == "hyd-001#0#residents#0#warning"


def test_unacknowledged_closure_recommendation_escalates_twice_then_stops():
    site, event = watching()
    for r in (reading(5, 22), reading(8, 26), reading(11, 30)):
        site = apply_reading(site, r)
    assert site.state == CRITICAL
    event, plan, _ = step(event, site, 11 * MIN)
    assert plan.alerts[alerts.TRAFFIC] == "closure_recommendation"

    contacts = []
    for minute in range(12, 30):
        event, plan, sent = step(event, site, minute * MIN)
        contacts += [m[3] for m in sent if m[1] == alerts.TRAFFIC]
    assert contacts == [1, 2]                 # 5 and 10 minutes later, then no one left


def test_acknowledgement_stops_escalation():
    site, event = watching()
    for r in (reading(5, 22), reading(8, 26), reading(11, 30)):
        site = apply_reading(site, r)
    event, _, _ = step(event, site, 11 * MIN)
    event = wf.acknowledge(event, alerts.TRAFFIC, 12 * MIN)
    for minute in range(13, 25):
        event, plan, _ = step(event, site, minute * MIN)
        assert plan.escalate == ()


def test_blocked_time_and_peak_are_accumulated():
    site, event = watching()
    site = apply_reading(site, reading(0, 18))        # blocks two-wheelers, not cars
    for minute in range(1, 11):
        event, _, _ = step(event, site, minute * MIN)
    assert event.blocked_two_wheelers_s == 10 * MIN and event.blocked_cars_s == 0
    assert event.peak_high == 18


def test_a_long_silence_is_not_counted_as_blocked_time():
    site, event = watching()
    site = apply_reading(site, reading(0, 30))
    event, _, _ = step(event, site, 0)
    event, _, _ = step(event, site, 60 * MIN)         # nothing ran for an hour
    assert event.blocked_cars_s == wf.MAX_FOLD_GAP_S


def test_event_closes_as_a_flood_or_as_no_flood():
    site, event = watching()
    event, _, _ = step(event, site, 0)
    dry = apply_rain(apply_rain(site, 2, 10 * MIN), 2, 80 * MIN)
    assert dry.state == CLEAR
    closed, plan, sent = step(event, dry, 80 * MIN)
    assert plan.close == wf.NO_FLOOD and sent == [] and closed.closed_at == 80 * MIN

    wet = apply_reading(site, reading(5, 16))
    event, _, _ = step(event, wet, 5 * MIN)
    cleared = Site("hyd-001", state=CLEAR)
    closed, plan, _ = step(event, cleared, 90 * MIN)
    assert plan.close == wf.FLOOD
    assert wf.summary(closed)["outcome"] == wf.FLOOD
    assert wf.summary(closed)["peak_depth_cm_high"] == 16


def test_time_until_cars_lose_passage():
    site = Site("s", state=WATCH)
    for r in (reading(0, 8), reading(5, 11), reading(10, 14)):   # 0.6 cm a minute
        site = apply_reading(site, r)
    sooner, later = wf.cars_lose_passage_min(site)
    assert 10 < sooner < later < 30
    assert wf.cars_lose_passage_min(Site("s")) is None


def test_alert_ids_never_repeat_within_an_event():
    rng = random.Random(4)
    for _ in range(100):
        site, event, seen, now = Site("s"), wf.open_event("s", 0), set(), 0
        site = apply_rain(site, 30, 0)
        for _ in range(60):
            now += rng.choice([30, 60, 120, 400])
            if rng.random() < 0.5:
                site = apply_reading(site, Reading(
                    now, 0, rng.uniform(0, 60), 0.8,
                    rng.choice(["guardian", "resident"]), rng.choice(["a", "b"])))
            before = event
            event, plan, sent = step(event, site, now)
            ids = [m[0] for m in sent]
            assert len(ids) == len(set(ids)) and not seen & set(ids)
            seen |= set(ids)
            assert event.version == before.version + 1
            if plan.close:
                break


def test_a_flood_that_ends_tells_everyone_it_warned_and_a_dry_watch_tells_nobody():
    site, event = watching()
    for r in (reading(5, 22), reading(8, 26), reading(11, 30)):
        site = apply_reading(site, r)
    event, _, _ = step(event, site, 11 * MIN)                     # critical: four audiences alerted
    cleared = Site("hyd-001", state=CLEAR, low=2, high=6, readings=(reading(40, 6),))
    closed, plan, sent = step(event, cleared, 41 * MIN)
    assert plan.close == wf.FLOOD
    assert {(m[1], m[2]) for m in sent} == {
        (alerts.RESIDENTS, "cleared"), (alerts.TRAFFIC, "cleared"),
        (alerts.PUMP, "cleared"), (alerts.FLEET, "cleared")}
    assert all(m[0].endswith("#cleared") for m in sent) and closed.closed_at == 41 * MIN

    site, event = watching()
    event, _, _ = step(event, site, 0)                            # a watch: only a photo request
    _, plan, sent = step(event, Site("hyd-001", state=CLEAR), 80 * MIN)
    assert plan.close == wf.NO_FLOOD and sent == []
