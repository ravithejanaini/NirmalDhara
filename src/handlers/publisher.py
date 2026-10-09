"""Publisher: writes the city's public map file (ARCHITECTURE.md section 6.8).

Runs when a site's state or depth changes, and every 15 minutes as a backstop. It ignores the
content of the event: each run reads the sites as they are now and writes one snapshot, so a
repeated, late or out-of-order event can only cause a redundant run.

Events do not reach this function one at a time. They go through a queue, ten to an
invocation, and at most two invocations run at once, so a flood cannot start more than two
full reads at a time, however many readings arrive. Most events in a burst find the sites
unchanged since the last run: a run that finds nothing changed since the last file, and the
file under five minutes old, writes nothing.

Two runs can overlap. Each reads the file's version (ETag) first, then the sites, and writes
only if the file is still at that version. The run that loses starts again with fresh data, so
an older snapshot can never replace a newer one.
"""

import gzip
import hashlib
import json
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
REFRESH_S = 300             # an unchanged file is still rewritten after this, to refresh generated_at
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
    """When the site's picture last changed: its newest reading, else when it left CLEAR, else 0
    (nothing reported). Never the current time, so an idle site's row does not change from run
    to run and an unchanged city can be recognised."""
    if site.readings:
        return site.readings[-1].ts
    return site.since if site.since is not None else 0


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


def current():
    """(version, fingerprint of its rows, time written) of the file, or None if absent."""
    try:
        head = S3.head_object(Bucket=BUCKET, Key=KEY)
    except ClientError as error:
        if error.response["Error"]["Code"] in MISSING:
            return None
        raise
    return head["ETag"], head.get("Metadata", {}).get("rows"), head["LastModified"].timestamp()


def fingerprint(rows):
    """Identifies the rows and nothing else, so generated_at does not count as a change."""
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def write(body, etag, rows_fingerprint):
    """Write only if the file is still at `etag` (or still absent, when etag is None)."""
    guard = {"IfMatch": etag} if etag else {"IfNoneMatch": "*"}
    S3.put_object(Bucket=BUCKET, Key=KEY, Body=body, ContentType="application/json; charset=utf-8",
                  ContentEncoding="gzip", CacheControl=CACHE, Metadata={"rows": rows_fingerprint},
                  **guard)


def run(now):
    for _ in range(ATTEMPTS):
        existing = current()                        # before the sites are read, never after
        etag = existing[0] if existing else None
        rows = entries(city_items(SITES, CITY), now)
        rows_fingerprint = fingerprint(rows)
        if existing and existing[1] == rows_fingerprint and now - existing[2] < REFRESH_S:
            return {"sites": len(rows), "bytes": 0, "written": False}
        document = publish.city_document(CITY, now, rows)
        # mtime=0 so the same content always compresses to the same bytes.
        body = gzip.compress(publish.to_json(document).encode("utf-8"), mtime=0)
        try:
            write(body, etag, rows_fingerprint)
        except ClientError as error:
            if error.response["Error"]["Code"] in LOST_RACE:
                continue                            # another run wrote first: read again
            raise
        return {"sites": len(rows), "bytes": len(body), "written": True}
    raise RuntimeError("the map file kept changing under this run")


def handler(event, context):
    return run(int(time.time()))
