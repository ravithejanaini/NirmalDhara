"""Publisher: writes the city's public map file (ARCHITECTURE.md section 6.8).

Runs when a site's state or depth changes, and every 15 minutes as a backstop. It ignores the
content of the event: each run reads the sites as they are now and writes one snapshot, so a
repeated, late or out-of-order event can only cause a redundant write.

Two runs can overlap. Each reads the file's version (ETag) first, then the sites, and writes
only if the file is still at that version. The run that loses starts again with fresh data, so
an older snapshot can never replace a newer one.
"""

import gzip
import os
import time

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from nirmaldhara import publish
from nirmaldhara.state import Site
from nirmaldhara import store

DYNAMO = boto3.resource("dynamodb")
SITES = DYNAMO.Table(os.environ["SITES_TABLE"])
S3 = boto3.client("s3")
BUCKET = os.environ["PUBLIC_BUCKET"]
CITY = os.environ["CITY"]
KEY = f"data/{CITY}.json"
CACHE = "public, max-age=15"
ATTEMPTS = 4
LOST_RACE = ("PreconditionFailed", "ConditionalRequestConflict")
MISSING = ("404", "NoSuchKey", "NotFound")


def city_items(table, city):
    """Every site in the city, all pages."""
    query = {"KeyConditionExpression": Key("city").eq(city), "ConsistentRead": True}
    items = []
    while True:
        response = table.query(**query)
        items += response["Items"]
        if "LastEvaluatedKey" not in response:
            return items
        query["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def updated_at(site, now):
    """When the site's picture last changed: its newest reading, else when it left CLEAR.
    A site that has never had either is shown as current."""
    if site.readings:
        return site.readings[-1].ts
    return site.since if site.since is not None else now


def entries(items, now):
    """Map-file rows for the sites that have a position. A site without one is left out."""
    rows = []
    for item in items:
        if "lat" not in item or "lon" not in item:
            continue
        site = store.from_item(item) if "doc" in item else Site(item["site_id"])
        rows.append(publish.site_entry(
            item["site_id"], item.get("name", item["site_id"]),
            float(item["lat"]), float(item["lon"]), site, updated_at(site, now)))
    return rows


def current_etag():
    """The file's version, or None if it has not been written yet."""
    try:
        return S3.head_object(Bucket=BUCKET, Key=KEY)["ETag"]
    except ClientError as error:
        if error.response["Error"]["Code"] in MISSING:
            return None
        raise


def write(body, etag):
    """Write only if the file is still at `etag` (or still absent, when etag is None)."""
    guard = {"IfMatch": etag} if etag else {"IfNoneMatch": "*"}
    S3.put_object(Bucket=BUCKET, Key=KEY, Body=body, ContentType="application/json; charset=utf-8",
                  ContentEncoding="gzip", CacheControl=CACHE, **guard)


def run(now):
    for _ in range(ATTEMPTS):
        etag = current_etag()                       # before the sites are read, never after
        rows = entries(city_items(SITES, CITY), now)
        document = publish.city_document(CITY, now, rows)
        # mtime=0 so the same content always compresses to the same bytes.
        body = gzip.compress(publish.to_json(document).encode("utf-8"), mtime=0)
        try:
            write(body, etag)
        except ClientError as error:
            if error.response["Error"]["Code"] in LOST_RACE:
                continue                            # another run wrote first: read again
            raise
        return {"sites": len(rows), "bytes": len(body)}
    raise RuntimeError("the map file kept changing under this run")


def handler(event, context):
    return run(int(time.time()))
