"""Site records in DynamoDB, written with a version check (ARCHITECTURE.md section 6.2)."""

import json
from dataclasses import asdict

from .state import Reading, Site

CITY_KEY, SITE_KEY = "city", "site_id"


def to_doc(site):
    """The full record as JSON, which avoids DynamoDB's number-type traps."""
    doc = asdict(site)
    doc.pop("events")
    return json.dumps(doc)


def from_item(item):
    doc = json.loads(item["doc"])
    doc["readings"] = tuple(Reading(**r) for r in doc["readings"])
    doc["held"] = Reading(**doc["held"]) if doc["held"] else None
    return Site(**doc)


def load(table, city, site_id):
    """The stored Site, or a new one in its default state."""
    item = table.get_item(Key={CITY_KEY: city, SITE_KEY: site_id}).get("Item")
    if item and "doc" in item:
        return from_item(item)
    # A registry item the engine has not written yet carries only its settings.
    threshold = float((item or {}).get("rain_threshold_mm", Site.rain_threshold_mm))
    return Site(site_id, rain_threshold_mm=threshold)


def save(table, city, site, expected_version):
    """Write the Site only if nobody else has written it since it was loaded.

    Only the engine's own attributes are set, so registry attributes on the same
    item (name, position, contacts) are left alone. Raises the table's
    ConditionalCheckFailedException if the version has moved.
    """
    table.update_item(
        Key={CITY_KEY: city, SITE_KEY: site.site_id},
        UpdateExpression="SET #doc = :doc, #state = :state, #version = :version",
        ConditionExpression="attribute_not_exists(#version) OR #version = :expected",
        ExpressionAttributeNames={"#doc": "doc", "#state": "state", "#version": "version"},
        ExpressionAttributeValues={
            ":doc": to_doc(site), ":state": site.state,
            ":version": site.version, ":expected": expected_version,
        },
    )
