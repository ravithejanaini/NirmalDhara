"""Rain check: one forecast request for the city, one queue message per site.

Runs on a schedule. It does not write site state; it sends the rain index to the
state engine through the same queue as depth readings.
"""

import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

from nirmaldhara.rain import indexes

TABLE = boto3.resource("dynamodb").Table(os.environ["SITES_TABLE"])
SQS = boto3.client("sqs")
QUEUE_URL = os.environ["ENGINE_QUEUE_URL"]
CITY = os.environ["CITY"]


def city_sites():
    """(site_id, lat, lon) for every registered site in the city."""
    query = {"KeyConditionExpression": Key("city").eq(CITY),
             "ProjectionExpression": "site_id, lat, lon"}
    sites = []
    while True:
        response = TABLE.query(**query)
        sites += [(i["site_id"], float(i["lat"]), float(i["lon"]))
                  for i in response["Items"] if "lat" in i]
        if "LastEvaluatedKey" not in response:
            return sites
        query["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def messages(rain_by_site, now):
    """One queue entry per site. The id repeats within a 15-minute window, so a
    retried run does not send the same rain twice."""
    window = now // 900
    return [{
        "Id": str(n),
        "MessageGroupId": site_id,
        "MessageDeduplicationId": f"rain-{site_id}-{window}",
        "MessageBody": json.dumps({"type": "rain", "city": CITY, "site_id": site_id,
                                   "index_mm": index_mm, "ts": now}),
    } for n, (site_id, index_mm) in enumerate(rain_by_site.items())]


def handler(event, context):
    sites = city_sites()
    if not sites:
        return {"sites": 0}
    entries = messages(indexes(sites), int(time.time()))
    for start in range(0, len(entries), 10):  # the queue accepts ten per call
        result = SQS.send_message_batch(QueueUrl=QUEUE_URL,
                                        Entries=entries[start:start + 10])
        if result.get("Failed"):
            # Fail the run so the schedule's retry sends them; duplicates are dropped.
            raise RuntimeError(f"{len(result['Failed'])} rain messages were not queued")
    return {"sites": len(sites)}
