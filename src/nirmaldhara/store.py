"""Site records in DynamoDB, written with a version check (ARCHITECTURE.md section 6.2)."""

import json
from dataclasses import asdict, replace

from .state import Reading, Site
from .workflow import FloodEvent

CITY_KEY, SITE_KEY = "city", "site_id"


def to_doc(site):
    """The full record as JSON, which avoids DynamoDB's number-type traps."""
    return json.dumps(asdict(site))


def from_item(item):
    doc = json.loads(item["doc"])
    doc["readings"] = tuple(Reading(**r) for r in doc["readings"])
    doc["held"] = Reading(**doc["held"]) if doc["held"] else None
    doc["applied"] = tuple(doc.get("applied", ()))
    doc["events"] = tuple(tuple(e) for e in doc.get("events", ()))
    return Site(**doc)


def load(table, city, site_id):
    """The stored Site, or a new one in its default state."""
    # A strongly consistent read: a caller woken by a change must see that change.
    item = table.get_item(Key={CITY_KEY: city, SITE_KEY: site_id},
                          ConsistentRead=True).get("Item")
    item = item or {}
    site = from_item(item) if "doc" in item else Site(site_id)
    # The registry owns the threshold: a change there takes effect on the next load.
    if "rain_threshold_mm" in item:
        site = replace(site, rain_threshold_mm=float(item["rain_threshold_mm"]))
    return site


class VersionMoved(Exception):
    """Someone else wrote the record after it was loaded."""


def guarded(write):
    try:
        write()
    except Exception as error:
        code = getattr(error, "response", {}).get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            raise VersionMoved() from error
        raise


def save(table, city, site, expected_version):
    """Write the Site only if nobody else has written it since it was loaded.

    The site's events are written with it. They stay in the record until
    `mark_published` removes them, so whoever loads the site next can see that
    they were never sent and send them.

    Only the engine's own attributes are set, so registry attributes on the same
    item (name, position, contacts) are left alone. Raises VersionMoved if the
    version has moved.
    """
    guarded(lambda: table.update_item(
        Key={CITY_KEY: city, SITE_KEY: site.site_id},
        UpdateExpression="SET #doc = :doc, #state = :state, #version = :version",
        ConditionExpression="attribute_not_exists(#version) OR #version = :expected",
        ExpressionAttributeNames={"#doc": "doc", "#state": "state", "#version": "version"},
        ExpressionAttributeValues={
            ":doc": to_doc(site), ":state": site.state,
            ":version": site.version, ":expected": expected_version,
        },
    ))


def mark_published(table, city, site):
    """Remove the site's events from the stored record now that they are on the bus."""
    try:
        save(table, city, replace(site, events=()), site.version)
    except VersionMoved:
        pass    # a later step has replaced the record, and dealt with these events first


# --- flood events: one item per site per flood, owned by the workflow ----------

def load_open_event(table, site_id):
    """The site's flood event that has not closed yet, or None."""
    items = table.query(
        KeyConditionExpression="site_id = :s",
        ExpressionAttributeValues={":s": site_id},
        ScanIndexForward=False, Limit=1, ConsistentRead=True,
    )["Items"]
    if not items:
        return None
    event = FloodEvent(**json.loads(items[0]["doc"]))
    return None if event.closed_at is not None else event


def save_event(table, event, expected_version):
    """Write the event if its version has not moved. A new event expects version 0."""
    guarded(lambda: table.update_item(
        Key={"site_id": event.site_id, "start": event.start},
        UpdateExpression="SET #doc = :doc, #version = :version, #open = :open",
        ConditionExpression="attribute_not_exists(#version) OR #version = :expected",
        ExpressionAttributeNames={"#doc": "doc", "#version": "version", "#open": "open"},
        ExpressionAttributeValues={
            ":doc": json.dumps(asdict(event)), ":version": event.version,
            ":expected": expected_version, ":open": event.closed_at is None,
        },
    ))
