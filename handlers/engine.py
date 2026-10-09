"""State engine: the only writer of site state.

Triggered by the FIFO queue, whose message group is the site id, so one site's
messages arrive in order and one at a time.

Message body:
    {"type": "rain",    "city": "...", "site_id": "...", "index_mm": 24.0, "ts": 1760000000}
    {"type": "reading", "city": "...", "site_id": "...", "reading": {...Reading fields...}}
"""

import json
import os

import boto3

from nirmaldhara import store
from nirmaldhara.state import Reading, apply_rain, apply_reading

TABLE = boto3.resource("dynamodb").Table(os.environ["SITES_TABLE"])
EVENTS = boto3.client("events")
BUS = os.environ["EVENT_BUS"]


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


def handler(event, context):
    failures = []
    for record in event["Records"]:
        try:
            message = json.loads(record["body"])
            city = message["city"]
            before = store.load(TABLE, city, message["site_id"])
            after = apply(before, message)
            store.save(TABLE, city, after, before.version)
            publish(city, after)
        except Exception:
            # Returned to the queue; after three tries it goes to the dead-letter queue.
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
