"""The flood history file: what counts as a flood, how sites are ranked, and the handler."""

import gzip
import json
import os
from dataclasses import asdict, replace

import pytest

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("SITES_TABLE", "sites")
os.environ.setdefault("FLOODS_TABLE", "floods")
os.environ.setdefault("PUBLIC_BUCKET", "public")
os.environ.setdefault("CITY", "hyderabad")

from handlers import history as handler  # noqa: E402
from nirmaldhara import history, workflow  # noqa: E402

MIN = 60


def event(site="a", start=1000, outcome="flood", confirmed=True, low=10, high=20, cars=20, bikes=30, closed=5000):
    e = workflow.open_event(site, start)
    return asdict(replace(e, peak_low=low, peak_high=high, blocked_cars_s=cars * MIN,
                          blocked_two_wheelers_s=bikes * MIN, confirmed=confirmed, closed_at=closed,
                          outcome=outcome, version=3))


def test_only_closed_floods_count_and_resets_watches_and_open_events_are_not_floods():
    events = [event(start=1, outcome="flood"), event(start=2, outcome="flood"),
              event(start=3, outcome="no_flood"), event(start=4, outcome="reset"),
              event(start=5, outcome="flood", closed=None)]
    entry = history.site_entry("a", "Site A", events)
    assert [f["start"] for f in entry["floods"]] == [1, 2]
    assert entry["confirmed"] == 2 and entry["dry_watches"] == 1


def test_totals_are_confirmed_floods_only_and_unconfirmed_are_counted_apart():
    entry = history.site_entry("a", "A", [
        event(start=1, cars=30, bikes=50, high=40), event(start=2, cars=10, bikes=20, high=25),
        event(start=3, confirmed=False, cars=500, bikes=500, high=90)])
    assert (entry["confirmed"], entry["unconfirmed"]) == (2, 1)
    assert (entry["cars_min"], entry["two_wheelers_min"], entry["peak_high"]) == (40, 70, 40)
    assert len(entry["floods"]) == 3 and entry["floods"][-1]["confirmed"] is False   # still listed


def test_a_site_with_no_floods_is_kept_and_empty():
    entry = history.site_entry("a", "A", [])
    assert entry["floods"] == [] and entry["peak_high"] == 0 and entry["confirmed"] == 0


def test_floods_are_listed_oldest_first_and_minutes_are_whole():
    entry = history.site_entry("a", "A", [event(start=9), event(start=3)])
    assert [f["start"] for f in entry["floods"]] == [3, 9]
    assert entry["floods"][0]["cars_min"] == 20


def test_ranking_is_minutes_blocked_for_cars_then_floods_then_name_and_skips_unconfirmed_sites():
    entries = [
        history.site_entry("a", "Alpha", [event(cars=60)]),
        history.site_entry("b", "Bravo", [event(start=1, cars=30), event(start=2, cars=30)]),     # 60 min, 2 floods
        history.site_entry("c", "Charlie", [event(cars=90)]),
        history.site_entry("d", "Delta", [event(confirmed=False, cars=999)]),                      # unconfirmed only
        history.site_entry("e", "Echo", []),
        history.site_entry("f", "Foxtrot", [event(cars=60)])]                                      # ties with Alpha
    assert history.ranking(entries) == ["c", "b", "a", "f"]


def test_the_document_is_ordered_by_id_so_an_unchanged_city_is_recognised():
    a, b = history.site_entry("a", "A", []), history.site_entry("b", "B", [])
    assert history.document("x", 5, [b, a])["sites"] == history.document("x", 5, [a, b])["sites"]


# --- the handler ------------------------------------------------------------------------------

class Sites:
    def query(self, **_):
        return {"Items": [{"city": "hyderabad", "site_id": "hyd-001", "name": "Lakdikapul"},
                          {"city": "hyderabad", "site_id": "hyd-002"}]}


class Floods:
    def __init__(self, docs):
        self.docs = docs

    def query(self, KeyConditionExpression, **_):
        site = KeyConditionExpression.get_expression()["values"][1]
        return {"Items": [{"doc": json.dumps(d)} for d in self.docs if d["site_id"] == site]}


class Bucket:
    def __init__(self):
        self.object, self.written = None, 0

    def head_object(self, **_):
        from datetime import datetime, timezone
        from botocore.exceptions import ClientError
        if self.object is None:
            raise ClientError({"Error": {"Code": "404", "Message": "x"}}, "head")
        return {"ETag": '"e"', "Metadata": self.object["Metadata"],
                "LastModified": datetime.fromtimestamp(self.written, timezone.utc)}

    def put_object(self, Body, **kwargs):
        self.object = {"Body": Body, **kwargs}


@pytest.fixture
def world(monkeypatch):
    bucket = Bucket()
    docs = [event("hyd-001", start=10, cars=45, high=35), event("hyd-001", start=20, outcome="reset")]
    monkeypatch.setattr(handler, "SITES", Sites())
    monkeypatch.setattr(handler, "FLOODS", Floods(docs))
    monkeypatch.setattr(handler, "S3", bucket)
    return bucket


def test_the_handler_writes_every_registry_site_with_its_floods(world):
    assert handler.run(10_000) == {"sites": 2, "bytes": len(world.object["Body"]), "written": True}
    doc = json.loads(gzip.decompress(world.object["Body"]))
    first, second = doc["sites"]
    assert (first["id"], first["name"], first["confirmed"], first["cars_min"]) == ("hyd-001", "Lakdikapul", 1, 45)
    assert second["name"] == "hyd-002" and second["floods"] == []           # no name: falls back to the id
    assert world.object["CacheControl"] == "public, max-age=60" and world.object["ContentEncoding"] == "gzip"


def test_an_unchanged_history_is_rewritten_only_once_an_hour_has_passed(world):
    assert handler.run(10_000)["written"] is True
    world.written = 10_000                                   # when the file was last written
    first = world.object["Body"]
    world.object["Body"] = b"marker"                         # so a rewrite would be seen
    assert handler.run(10_000 + 3_599)["written"] is False and world.object["Body"] == b"marker"
    assert handler.run(10_000 + 3_600)["written"] is True and world.object["Body"] != b"marker"
    assert gzip.decompress(world.object["Body"]) != gzip.decompress(first)     # only generated_at differs
    assert json.loads(gzip.decompress(world.object["Body"]))["sites"] == json.loads(gzip.decompress(first))["sites"]


def test_a_new_flood_is_written_at_once_even_though_the_file_is_fresh(world, monkeypatch):
    handler.run(10_000)
    world.written = 10_000
    monkeypatch.setattr(handler, "FLOODS", Floods([event("hyd-001", start=10, cars=45, high=35),
                                                   event("hyd-001", start=30, cars=15, high=22)]))
    assert handler.run(10_001)["written"] is True
    assert json.loads(gzip.decompress(world.object["Body"]))["sites"][0]["confirmed"] == 2
