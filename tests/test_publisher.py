"""The publisher against an in-memory table and bucket."""

import gzip
import hashlib
import json
import os

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("SITES_TABLE", "sites")
os.environ.setdefault("PUBLIC_BUCKET", "public")
os.environ.setdefault("CITY", "hyderabad")

from handlers import publisher  # noqa: E402
from nirmaldhara import store  # noqa: E402
from nirmaldhara.state import WARNING, Reading, Site, apply_rain, apply_reading  # noqa: E402

NOW = 1_760_000_000


def error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "op")


class Table:
    """Two items to a page, so pagination is exercised."""

    def __init__(self):
        self.items = []

    def query(self, ExclusiveStartKey=None, **_):
        start = ExclusiveStartKey["n"] if ExclusiveStartKey else 0
        page = self.items[start:start + 2]
        out = {"Items": page}
        if start + 2 < len(self.items):
            out["LastEvaluatedKey"] = {"n": start + 2}
        return out


class Bucket:
    def __init__(self):
        self.object, self.writes, self.before_write = None, [], None

    def head_object(self, Bucket, Key):
        if self.object is None:
            raise error("404")
        return {"ETag": self.object["etag"]}

    def put_object(self, Bucket, Key, Body, IfMatch=None, IfNoneMatch=None, **meta):
        if self.before_write:                   # another run gets in just before this write
            hook, self.before_write = self.before_write, None
            hook()
        if IfNoneMatch == "*" and self.object is not None:
            raise error("PreconditionFailed")
        if IfMatch is not None and (self.object is None or self.object["etag"] != IfMatch):
            raise error("PreconditionFailed")
        self.object = {"body": Body, "etag": '"' + hashlib.md5(Body).hexdigest() + str(len(self.writes)) + '"', **meta}
        self.writes.append(Key)


@pytest.fixture
def world(monkeypatch):
    table, bucket = Table(), Bucket()
    monkeypatch.setattr(publisher, "SITES", table)
    monkeypatch.setattr(publisher, "S3", bucket)
    return table, bucket


def registry(site_id, name, lat=17.4, lon=78.45):
    return {"city": "hyderabad", "site_id": site_id, "name": name, "lat": str(lat), "lon": str(lon)}


def with_state(item, site):
    return {**item, "doc": store.to_doc(site), "state": site.state, "version": site.version}


def document(bucket):
    return json.loads(gzip.decompress(bucket.object["body"]))


def warning_site(site_id="hyd-002"):
    site = apply_rain(Site(site_id), 25, NOW - 1200)
    for minute, high in ((10, 14), (13, 16), (16, 18)):
        site = apply_reading(site, Reading(NOW - 1200 + minute * 60, high - 5, high, 0.8, "guardian", "g1"))
    assert site.state == WARNING
    return site


def test_writes_every_site_with_a_position_across_all_pages(world):
    table, bucket = world
    table.items = [registry(f"hyd-{n:03d}", f"Site {n}") for n in range(1, 6)]
    assert publisher.run(NOW)["sites"] == 5
    doc = document(bucket)
    assert [row[0] for row in doc["sites"]] == [f"hyd-{n:03d}" for n in range(1, 6)]
    assert doc["generated_at"] == NOW and doc["fields"][-1] == "c"


def test_a_site_without_a_position_is_left_out(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Has a position"),
                   {"city": "hyderabad", "site_id": "hyd-002", "name": "No position"}]
    assert publisher.run(NOW)["sites"] == 1
    assert [row[0] for row in document(bucket)["sites"]] == ["hyd-001"]


def test_state_and_depth_come_from_the_engines_record(world):
    table, bucket = world
    table.items = [with_state(registry("hyd-002", "Underpass"), warning_site()),
                   registry("hyd-001", "Never touched")]
    publisher.run(NOW)
    clear, wet = document(bucket)["sites"]
    assert clear[4] == "CLEAR" and clear[7] == 0 and clear[9] == NOW        # shown as current
    assert wet[:2] == ["hyd-002", "Underpass"]
    assert wet[4:9] == [WARNING, "B2", 11, 16, 1] and wet[10] == 0.8   # medians of the last three
    assert wet[9] == NOW - 1200 + 16 * 60                                    # newest reading


def test_an_unchanged_city_still_writes_a_valid_file(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]
    publisher.run(NOW)
    publisher.run(NOW + 900)
    assert len(bucket.writes) == 2
    assert document(bucket)["generated_at"] == NOW + 900 and len(document(bucket)["sites"]) == 1


def test_an_empty_city_writes_an_empty_valid_file(world):
    _, bucket = world
    publisher.run(NOW)
    assert document(bucket)["sites"] == []


def test_the_file_is_served_compressed_json_with_a_short_cache(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]
    publisher.run(NOW)
    obj = bucket.object
    assert obj["ContentEncoding"] == "gzip" and obj["CacheControl"] == "public, max-age=15"
    assert obj["ContentType"].startswith("application/json")


def test_the_same_content_always_compresses_to_the_same_bytes(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]
    publisher.run(NOW)
    first = bucket.object["body"]
    publisher.run(NOW)
    assert bucket.object["body"] == first


def test_a_run_that_loses_a_race_reads_again_and_writes_the_newer_data(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]
    publisher.run(NOW)                                    # the file exists

    def other_run_writes_first():
        table.items.append(registry("hyd-002", "Added meanwhile"))
        bucket.object = {**bucket.object, "etag": '"someone-else"'}

    bucket.before_write = other_run_writes_first
    result = publisher.run(NOW + 60)
    assert result["sites"] == 2                           # read again after losing
    assert [row[0] for row in document(bucket)["sites"]] == ["hyd-001", "hyd-002"]


def test_two_first_writers_one_wins_and_the_other_rereads(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]

    def other_creates_it():
        bucket.object = {"body": b"x", "etag": '"created-by-other"'}

    bucket.before_write = other_creates_it
    assert publisher.run(NOW)["sites"] == 1
    assert document(bucket)["generated_at"] == NOW


def test_it_gives_up_loudly_if_the_file_never_stops_changing(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]
    real = bucket.put_object

    def always_lose(**kwargs):
        raise error("PreconditionFailed")

    bucket.put_object = always_lose
    with pytest.raises(RuntimeError):
        publisher.run(NOW)
    bucket.put_object = real


def test_other_storage_errors_are_not_hidden(world):
    table, bucket = world
    table.items = [registry("hyd-001", "Site")]

    def denied(**kwargs):
        raise error("AccessDenied")

    bucket.put_object = denied
    with pytest.raises(ClientError):
        publisher.run(NOW)
