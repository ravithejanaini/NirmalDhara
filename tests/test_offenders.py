"""The repeat offenders page's rules (web/offenders.js) against the Python (nirmaldhara/history.py)."""

import json
import random
import shutil
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from nirmaldhara import history, workflow

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")


def event(site, start, cars=20, bikes=30, high=30, confirmed=True, outcome="flood"):
    return asdict(replace(workflow.open_event(site, start), peak_low=high - 8, peak_high=high,
                          blocked_cars_s=cars * 60, blocked_two_wheelers_s=bikes * 60, confirmed=confirmed,
                          closed_at=start + 3600, outcome=outcome, version=2))


def doc(entries, sample=False):
    d = history.document("hyderabad", 1000, entries)
    if sample:
        d["sample"] = True
    return d


def node(document, expression):
    script = f"""
import {{ offendersModel, factsLine, rowHtml, pageHtml, stripSvg, duration, toneFor }} from "{(ROOT / 'web' / 'offenders.js').as_uri()}";
const doc = {json.dumps(document)};
const model = offendersModel(doc);
console.log(JSON.stringify({expression}));
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def random_city(seed):
    rng = random.Random(seed)
    entries = []
    for n in range(12):
        events = [event(f"s{n}", 100 * k, cars=rng.choice([0, 15, 30, 30, 60, 90]), high=rng.randint(8, 70),
                        confirmed=rng.random() < 0.75, outcome=rng.choice(["flood"] * 4 + ["no_flood", "reset"]))
                  for k in range(rng.randint(0, 5))]
        entries.append(history.site_entry(f"s{n}", f"Site {rng.choice('ABCD')}{n % 3}", events))
    return doc(entries)


@pytest.mark.parametrize("seed", range(25))
def test_the_page_ranks_exactly_as_the_python_does(seed):
    document = random_city(seed)
    ranked = node(document, "model.ranked.map((s) => s.id)")
    assert ranked == history.ranking(document["sites"])


def test_unconfirmed_floods_never_rank_a_site_and_are_listed_apart():
    document = doc([history.site_entry("a", "A", [event("a", 1, cars=500, confirmed=False)]),
                    history.site_entry("b", "B", [event("b", 1, cars=10)]),
                    history.site_entry("c", "C", [])])
    out = node(document, "{ranked: model.ranked.map((s) => s.id), unranked: model.unranked.map((s) => s.id), quiet: model.quietCount, empty: model.empty}")
    assert out == {"ranked": ["b"], "unranked": ["a"], "quiet": 1, "empty": False}


def test_a_city_with_no_floods_says_so_and_names_how_many_places_are_watched():
    document = doc([history.site_entry(f"s{i}", f"S{i}", []) for i in range(3)])
    text = node(document, "pageHtml(model)")
    assert "No floods have been recorded yet." in text and "3 places are watched" in text


@pytest.mark.parametrize("minutes, words", [(0, "0 min"), (45, "45 min"), (59.6, "1 h"), (60, "1 h"),
                                            (65, "1 h 5 min"), (720, "12 h"), (1250, "20 h 50 min")])
def test_durations_are_plain_words(minutes, words):
    assert node(doc([]), f"duration({minutes})") == words


def test_the_facts_line_and_the_last_flood_describe_the_confirmed_floods_only():
    document = doc([history.site_entry("a", "A", [event("a", 100, cars=30, high=40),
                                                  event("a", 900, cars=999, high=65, confirmed=False)])])
    out = node(document, "{facts: factsLine(model.ranked[0]), row: rowHtml(model.ranked[0])}")
    assert out["facts"] == "1 flood · 30 min blocked for cars · peak 40 cm"
    assert "peak 40 cm" in out["row"] and "peak 65 cm +" not in out["row"] and "1 unconfirmed" in out["row"]


def test_the_strip_has_one_mark_per_flood_taller_for_deeper_and_outlined_when_unconfirmed():
    document = doc([history.site_entry("a", "A", [event("a", 1, high=20), event("a", 2, high=60),
                                                  event("a", 3, high=10, confirmed=False)])])
    svg = node(document, "stripSvg(model.ranked[0])")
    heights = [int(h) for h in __import__("re").findall(r'height="(\d+)" rx', svg)]
    assert len(heights) == 3 and heights[1] > heights[0] > heights[2] and heights[1] == 36
    assert svg.count("is-unconfirmed") == 1
    assert 'aria-label="3 floods, peaks 20, 60, 10 centimetres"' in svg
    assert node(document, "[toneFor(11.9), toneFor(12), toneFor(30), toneFor(30.1)]") == ["shallow", "water", "water", "deep"]


def test_a_place_name_cannot_inject_markup_and_sample_data_is_flagged():
    document = doc([history.site_entry("a", "A", [event("a", 1)])], sample=True)
    document["sites"][0]["name"] = '<img src=x onerror=alert(1)>'
    out = node(document, "{html: pageHtml(model), sample: model.sample}")
    assert "<img" not in out["html"] and "&lt;img" in out["html"] and out["sample"] is True
