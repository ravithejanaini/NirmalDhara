"""scripts/seed.py against an in-memory table."""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import seed  # noqa: E402


class Table:
    def __init__(self):
        self.items, self.writes = {}, 0

    def get_item(self, Key, **_):
        item = self.items.get((Key["city"], Key["site_id"]))
        return {"Item": dict(item)} if item else {}

    def update_item(self, Key, ExpressionAttributeValues, **_):
        self.writes += 1
        item = self.items.setdefault((Key["city"], Key["site_id"]), dict(Key))
        item.update({k.lstrip(":"): v for k, v in ExpressionAttributeValues.items()})


def doc(*sites):
    return {"city": "hyderabad", "sites": list(sites)}


def site(n=1, **over):
    return {"id": f"hyd-{n:03d}", "name": f"Underpass {n}", "lat": 17.4, "lon": 78.45,
            "rain_threshold_mm": 20, "source": "https://example.org/list", **over}


def test_second_run_changes_nothing():
    table, document = Table(), doc(site(1), site(2))
    first = seed.seed(table, document, apply=True)
    assert first["added"] == ["hyd-001", "hyd-002"] and table.writes == 2
    second = seed.seed(table, document, apply=True)
    assert second == {"added": [], "changed": [], "unchanged": ["hyd-001", "hyd-002"]}
    assert table.writes == 2


def test_the_engines_attributes_are_never_touched():
    table = Table()
    table.items[("hyderabad", "hyd-001")] = {
        "city": "hyderabad", "site_id": "hyd-001", "doc": "{}", "state": "WARNING", "version": 7}
    seed.seed(table, doc(site(1)), apply=True)
    item = table.items[("hyderabad", "hyd-001")]
    assert (item["state"], item["version"], item["doc"]) == ("WARNING", 7, "{}")
    assert item["lat"] == Decimal("17.4")


def test_a_changed_threshold_is_reported_and_written():
    table = Table()
    seed.seed(table, doc(site(1)), apply=True)
    result = seed.seed(table, doc(site(1, rain_threshold_mm=30)), apply=True)
    assert result["changed"] == ["hyd-001"]
    assert table.items[("hyderabad", "hyd-001")]["rain_threshold_mm"] == Decimal("30")


def test_without_apply_nothing_is_written():
    table = Table()
    assert seed.seed(table, doc(site(1)))["added"] == ["hyd-001"] and table.writes == 0


@pytest.mark.parametrize("bad, text", [
    (dict(source=""), "source"), (dict(source="a list I saw"), "source"),
    (dict(lat=12.9, lon=77.6), "outside Hyderabad"), (dict(lat=None), "position"),
    (dict(id="sample-01"), "id must"), (dict(name=" "), "no name"),
    (dict(rain_threshold_mm=0), "rain_threshold_mm"),
])
def test_a_site_is_refused_for_each_kind_of_fault(bad, text):
    found = seed.problems(doc(site(1, **bad)))
    assert any(text in line for line in found), found


def test_ids_must_be_unique():
    assert any("twice" in p for p in seed.problems(doc(site(1), site(1))))


def test_the_real_file_is_valid_whatever_it_holds():
    document = seed.load()
    assert seed.problems(document) == []
    assert len(document["sites"]) <= 20
