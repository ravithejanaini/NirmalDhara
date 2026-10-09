"""Flood event orchestration: one step, two callers.

- `reactor` runs when the state engine publishes a change. This is the fast path:
  an alert goes out within one step of the reading that caused it.
- `tick` runs from the state machine's timer. It handles what becomes due because
  time has passed: photo re-asks, repeat alerts, escalation and closing.

Both call `run`. Alerts carry deterministic ids, so if both act on the same
decision the notifier sends it once.
"""

import json
import os
import time

import boto3

from nirmaldhara import store, workflow
from nirmaldhara.state import CLEAR

DYNAMO = boto3.resource("dynamodb")
SITES = DYNAMO.Table(os.environ["SITES_TABLE"])
FLOODS = DYNAMO.Table(os.environ["FLOODS_TABLE"])
EVENTS = boto3.client("events")
STATES = boto3.client("stepfunctions")
BUS = os.environ["EVENT_BUS"]
STATE_MACHINE = os.environ.get("FLOOD_STATE_MACHINE", "")
ATTEMPTS = 3


def publish(city, site, event, sent, closed):
    forecast = workflow.cars_lose_passage_min(site)
    entries = [{
        "EventBusName": BUS,
        "Source": "nirmaldhara",
        "DetailType": "PhotoRequested" if kind == "photo_request" else "AlertRequested",
        "Detail": json.dumps({
            "alert_id": alert_id, "city": city, "site_id": site.site_id,
            "audience": audience, "kind": kind, "contact": contact,
            "state": site.state, "low_cm": site.low, "high_cm": site.high,
            "confidence": workflow.confidence(site), "trusted": site.trusted,
            "cars_lose_passage_min": forecast, "site_version": site.version,
            "seen_at": site.readings[-1].ts if site.readings else None,
        }),
    } for alert_id, audience, kind, contact in sent]
    if closed:
        entries.append({
            "EventBusName": BUS, "Source": "nirmaldhara", "DetailType": "EventClosed",
            "Detail": json.dumps({"city": city, **workflow.summary(event)}),
        })
    for start in range(0, len(entries), 10):
        EVENTS.put_events(Entries=entries[start:start + 10])


def run(city, site_id, now):
    """One orchestration step. Returns (event or None, plan or None, opened)."""
    for _ in range(ATTEMPTS):
        site = store.load(SITES, city, site_id)
        event = store.load_open_event(FLOODS, site_id)
        opened = event is None
        if opened:
            if site.state == CLEAR:
                return None, None, False
            # The start is when the site left CLEAR, not when this code ran, so two
            # callers opening the same flood write the same item and one of them wins.
            event = workflow.open_event(site_id, now if site.since is None else site.since)
        before_version = event.version
        event = workflow.fold(event, site, now)
        plan = workflow.plan(event, site, now)
        sent = workflow.messages(event, site, plan, now)
        after = workflow.record(event, site, plan, now)
        # Sent before it is recorded. A crash or a lost race in between means the
        # same decision is made again with the same alert ids, which the notifier
        # drops as repeats. Recording first could lose an alert outright.
        publish(city, site, after, sent, plan.close is not None)
        try:
            store.save_event(FLOODS, after, before_version)
        except store.VersionMoved:
            continue        # the other caller got there first; decide again
        return after, plan, opened
    raise store.VersionMoved()


def ensure_ticker(city, flood):
    """Start this flood's timer loop unless it has already been started.

    Called on every reactor step, not only the one that opens the event: if the
    reactor dies between saving a new event and starting its timer, the next
    reading starts it. The name is fixed per flood, so a repeat starts nothing.
    """
    try:
        STATES.start_execution(
            stateMachineArn=STATE_MACHINE,
            name=f"{flood.site_id}-{flood.start}",
            input=json.dumps({"city": city, "site_id": flood.site_id, "start": flood.start}),
        )
    except STATES.exceptions.ExecutionAlreadyExists:
        pass        # that execution has ended, or handed over to a continuation


def reactor(event, context):
    """EventBridge: SiteStateChanged or ReadingAccepted."""
    detail = event["detail"]
    city, site_id = detail["city"], detail["site_id"]
    flood, plan, opened = run(city, site_id, int(time.time()))
    if flood is not None and plan.close is None and STATE_MACHINE:
        ensure_ticker(city, flood)
    return {"opened": opened}


def tick(event, context):
    """Step Functions task. Input and output: {city, site_id, start, done, wait_s, loops}."""
    flood, plan, _ = run(event["city"], event["site_id"], int(time.time()))
    done = flood is None or plan.close is not None or flood.start != event["start"]
    return {
        "city": event["city"], "site_id": event["site_id"], "start": event["start"],
        "done": done,
        "wait_s": 0 if done else plan.wait_s,
        "loops": event.get("loops", 0) + 1,
    }
