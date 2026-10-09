"""Flood history: writes data/<city>-floods.json for the repeat offenders page.

Runs when a flood closes, and every hour as a backstop (also what refreshes it after
scripts/reset.py removes records). Like the map publisher it ignores the event's content and
rebuilds the whole file, and writes through nirmaldhara.snapshot so overlapping runs cannot
leave an older picture in place.

One query per registered site: fine for the nine sites of the demonstration. At the 500 sites
of the design it would be 500 queries per closed flood; a global index on closed events would
replace them (DESIGN.md 17.2).
"""

import json
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

from nirmaldhara import history, snapshot

DYNAMO = boto3.resource("dynamodb")
SITES = DYNAMO.Table(os.environ["SITES_TABLE"])
FLOODS = DYNAMO.Table(os.environ["FLOODS_TABLE"])
S3 = boto3.client("s3")
BUCKET = os.environ["PUBLIC_BUCKET"]
CITY = os.environ["CITY"]
KEY = f"data/{CITY}-floods.json"
CACHE = "public, max-age=60"
REFRESH_S = 3600            # an unchanged file is rewritten hourly, to refresh generated_at


def pages(table, **query):
    items = []
    while True:
        response = table.query(**query)
        items += response["Items"]
        if "LastEvaluatedKey" not in response:
            return items
        query["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def site_events(site_id):
    return [json.loads(item["doc"]) for item in
            pages(FLOODS, KeyConditionExpression=Key("site_id").eq(site_id), ConsistentRead=True)]


def entries():
    registry = pages(SITES, KeyConditionExpression=Key("city").eq(CITY), ConsistentRead=True)
    return [history.site_entry(item["site_id"], item.get("name", item["site_id"]), site_events(item["site_id"]))
            for item in registry]


def run(now):
    def build():
        rows = entries()
        return rows, history.document(CITY, now, rows)

    result = snapshot.put(S3, BUCKET, KEY, build, now, cache=CACHE, refresh_s=REFRESH_S)
    return {"sites": result["rows"], "bytes": result["bytes"], "written": result["written"]}


def handler(event, context):
    return run(int(time.time()))
