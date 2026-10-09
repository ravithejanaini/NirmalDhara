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
    response = TABLE.query(KeyConditionExpression=Key("city").eq(CITY),
                           ProjectionExpression="site_id, lat, lon")
    return [(i["site_id"], float(i["lat"]), float(i["lon"]))
            for i in response["Items"] if "lat" in i]


def handler(event, context):
    sites = city_sites()
    if not sites:
        return {"sites": 0}
    now = int(time.time())
    window = now // 900  # one message per site per 15-minute window
    for site_id, index_mm in indexes(sites).items():
        SQS.send_message(
            QueueUrl=QUEUE_URL,
            MessageGroupId=site_id,
            MessageDeduplicationId=f"rain-{site_id}-{window}",
            MessageBody=json.dumps({"type": "rain", "city": CITY, "site_id": site_id,
                                    "index_mm": index_mm, "ts": now}),
        )
    return {"sites": len(sites)}
