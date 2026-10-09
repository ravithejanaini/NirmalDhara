"""Notifier: turns an AlertRequested or PhotoRequested event into a sent message.

An alert id is claimed with a conditional write before sending, so the same alert
arriving twice is sent once. The claim is a lease: if the send fails, or the
function dies before marking the alert sent, a retry may take the claim over once
the lease has run out. So an alert can be sent twice in that one case, and is not
lost. The wording here is the fixed template; the agent's wording replaces it when
it arrives in time (ARCHITECTURE.md section 6.4).
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone

import boto3

from nirmaldhara import alerts, store

DYNAMO = boto3.resource("dynamodb")
SITES = DYNAMO.Table(os.environ["SITES_TABLE"])
ALERTS = DYNAMO.Table(os.environ["ALERTS_TABLE"])
SNS = boto3.client("sns")
TOPIC = os.environ["ALERTS_TOPIC"]
EVENTS = boto3.client("events")
BUS = os.environ["EVENT_BUS"]
IST = timezone(timedelta(hours=5, minutes=30))
KEEP_S = 30 * 24 * 3600
LEASE_S = 45                # shorter than the one minute before the first retry


def clock(ts):
    return datetime.fromtimestamp(ts, IST).strftime("%I:%M %p").lstrip("0").lower()


def wording(detail, site_name):
    forecast = detail.get("cars_lose_passage_min")
    return alerts.template(
        detail["kind"], site_name, detail["low_cm"], detail["high_cm"], detail["confidence"],
        clock(detail["seen_at"] or time.time()), trusted=detail["trusted"],
        cars_lose_passage_min=tuple(forecast) if forecast else None)


def claim(alert_id, detail, now):
    """True if this alert is ours to send: new, or claimed a while ago and never sent."""
    try:
        store.guarded(lambda: ALERTS.put_item(
            Item={"alert_id": alert_id, "site_id": detail["site_id"],
                  "audience": detail["audience"], "kind": detail["kind"],
                  "sent": False, "claimed_at": now, "expires_at": now + KEEP_S},
            ConditionExpression="attribute_not_exists(alert_id)"
                                " OR (#sent = :no AND claimed_at < :stale)",
            ExpressionAttributeNames={"#sent": "sent"},
            ExpressionAttributeValues={":no": False, ":stale": now - LEASE_S}))
        return True
    except store.VersionMoved:
        return False


def mark_sent(alert_id, now):
    ALERTS.update_item(
        Key={"alert_id": alert_id},
        UpdateExpression="SET #sent = :yes, sent_at = :now",
        ExpressionAttributeNames={"#sent": "sent"},
        ExpressionAttributeValues={":yes": True, ":now": now})


def handler(event, context):
    detail = event["detail"]
    now = int(time.time())
    if not claim(detail["alert_id"], detail, now):
        return {"sent": False, "reason": "repeat"}

    item = SITES.get_item(Key={"city": detail["city"], "site_id": detail["site_id"]}).get("Item", {})
    text = wording(detail, item.get("name", detail["site_id"]))
    SNS.publish(
        TopicArn=TOPIC, Message=text, Subject=f"NirmalDhara: {detail['site_id']}"[:100],
        MessageAttributes={
            "audience": {"DataType": "String", "StringValue": detail["audience"]},
            "contact": {"DataType": "Number", "StringValue": str(detail["contact"])},
        })
    mark_sent(detail["alert_id"], now)
    EVENTS.put_events(Entries=[{
        "EventBusName": BUS, "Source": "nirmaldhara", "DetailType": "AlertSent",
        "Detail": json.dumps({"alert_id": detail["alert_id"], "city": detail["city"],
                              "site_id": detail["site_id"], "audience": detail["audience"],
                              "sent_at": now}),
    }])
    return {"sent": True}
