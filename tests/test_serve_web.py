"""scripts/serve_web.py: the development stand-in for the map file."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import serve_web  # noqa: E402


@pytest.fixture(autouse=True)
def clean():
    serve_web.STATE.update(overrides={}, fail=False, age_s=0)
    yield
    serve_web.STATE.update(overrides={}, fail=False, age_s=0)


def rows(doc):
    index = {name: i for i, name in enumerate(doc["fields"])}
    return {r[index["i"]]: {name: r[i] for name, i in index.items()} for r in doc["sites"]}


def test_the_sample_always_looks_current():
    doc = serve_web.current_document(now=2_000_000_000)
    assert doc["generated_at"] == 2_000_000_000
    wet = rows(doc)["sample-04"]
    assert 0 < 2_000_000_000 - wet["u"] < 3_600                 # minutes old, whatever day it is


def test_a_site_that_never_reported_stays_at_zero():
    assert rows(serve_web.current_document())["sample-01"]["u"] == 0


def test_set_changes_one_site_and_recomputes_its_band():
    serve_web.apply_set({"site": ["sample-04"], "low": ["30"], "high": ["42"], "state": ["CRITICAL"]})
    changed = rows(serve_web.current_document())
    assert (changed["sample-04"]["h"], changed["sample-04"]["s"], changed["sample-04"]["b"]) == (42, "CRITICAL", "B4")
    assert changed["sample-03"]["h"] == 17                       # the others are untouched


def test_age_makes_the_whole_file_look_old():
    serve_web.STATE["age_s"] = 25 * 60
    assert serve_web.current_document(now=2_000_000_000)["generated_at"] == 2_000_000_000 - 1500
