"""State engine: the only writer of site state.

Triggered by the FIFO queue, whose message group is the site id, so one site's
messages arrive in order and one at a time.

A change and the events it produces are saved in one write. The events are then
published and removed from the record. If the function dies in between, the next
run for the site (the same message redelivered, or any later one) finds them in
the record and publishes them. Each applied message leaves a key in the record,
so a redelivered message is not applied a second time.

Message body:
    {"type": "rain",    "city": "...", "site_id": "...", "index_mm": 24.0, "ts": 1760000000}
    {"type": "reading", "city": "...", "site_id": "...", "reading": {...Reading fields...}}
"""

import hashlib
import json
import os
from dataclasses import replace

import boto3

from nirmaldhara import store
from nirmaldhara.state import Reading, apply_rain, apply_reading

TABLE = boto3.resource("dynamodb").Table(os.environ["SITES_TABLE"])
EVENTS = boto3.client("events")
BUS = os.environ["EVENT_BUS"]
ATTEMPTS = 3
KEYS_KEPT = 16      # applied-message keys remembered per site


def message_key(message):
    """The same for a message however many times it is delivered or sent."""
    body = json.dumps(message, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def apply(site, message):
    if message["type"] == "rain":
        return apply_rain(site, message["index_mm"], message["ts"])
    return apply_reading(site, Reading(**message["reading"]))


def publish(city, site):
    entries = [{
        "EventBusName": BUS,
        "Source": "nirmaldhara",
        "DetailType": event[0],
        "Detail": json.dumps({
            "city": city, "site_id": site.site_id, "state": site.state,
            "low_cm": site.low, "high_cm": site.high, "trusted": site.trusted,
            "version": site.version, "event": list(event),
        }),
    } for event in site.events]
    for start in range(0, len(entries), 10):
        EVENTS.put_events(Entries=entries[start:start + 10])


def flush(city, site):
    """Publish the site's events, then take them out of the stored record."""
    if site.events:
        publish(city, site)
        store.mark_published(TABLE, city, site)


def process(message):
    """Load, apply and save one message. A lost race is retried at once."""
    city, key = message["city"], message_key(message)
    for _ in range(ATTEMPTS):
        before = store.load(TABLE, city, message["site_id"])
        flush(city, before)         # events an earlier run saved and never published
        if key in before.applied:
            return                  # this message has already been applied
        after = apply(before, message)
        after = replace(after, applied=(before.applied + (key,))[-KEYS_KEPT:])
        try:
            store.save(TABLE, city, after, before.version)
        except store.VersionMoved:
            continue
        flush(city, after)
        return
    raise store.VersionMoved()


def handler(event, context):
    failures, stopped = [], set()
    for record in event["Records"]:
        site = record.get("attributes", {}).get("MessageGroupId")
        try:
            # Once one of a site's messages has failed, the later ones in this batch
            # go back too. Handling them now would apply them ahead of the failed one.
            if site in stopped:
                raise RuntimeError("an earlier message for this site failed")
            process(json.loads(record["body"]))
        except Exception:
            # Returned to the queue; after three tries it goes to the dead-letter queue.
            failures.append({"itemIdentifier": record["messageId"]})
            if site is not None:
                stopped.add(site)
    return {"batchItemFailures": failures}
