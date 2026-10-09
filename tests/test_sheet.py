"""The site sheet's words (web/sheet.js, `sheetModel`) against the Python rules.

The sheet must give the same per-vehicle answers as `python -m nirmaldhara check`, the same
sentence as an alert, and the same name for each depth band. Run with Node.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from nirmaldhara import alerts, bands

ROOT = Path(__file__).resolve().parents[1]
NOW = 1_760_000_000
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")


def site(low, high, state="WARNING", confidence=0.8, trusted=True, age_min=6, name="Malakpet underpass"):
    return {"id": "hyd-001", "name": name, "state": state, "low": low, "high": high,
            "confidence": confidence, "trusted": trusted, "updated": NOW - age_min * 60 if high else 0}


def models(sites):
    script = f"""
import {{ sheetModel, sheetHtml, BAND_LABEL }} from "{(ROOT / 'web' / 'sheet.js').as_uri()}";
const sites = {json.dumps(sites)};
console.log(JSON.stringify({{ models: sites.map((s) => sheetModel(s, {NOW})),
  html: sites.map((s) => sheetHtml(sheetModel(s, {NOW}))), bands: BAND_LABEL }}));
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True,
                         encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# The task's check: five ranges, the same answers as `python -m nirmaldhara check`.
FIVE = [(0, 8, 0.8), (10, 14, 0.8), (14, 19, 0.8), (22, 28, 0.9), (45, 55, 0.9)]


@pytest.mark.parametrize("low, high, confidence", FIVE + [(14, 19, 0.5), (5, 9, 0.59), (29, 30, 0.6)])
def test_rows_give_the_same_answers_as_the_python_check(low, high, confidence):
    [model] = models([site(low, high, confidence=confidence)])["models"]
    expected = bands.passability(low, high, confidence)
    assert {row["id"]: row["answer"] for row in model["rows"]} == {
        v: expected[v] for v in ("two_wheeler", "auto", "car", "suv", "pedestrian")}
    assert [row["label"] for row in model["rows"]] == [
        "Bikes and scooters", "Autos", "Cars", "SUVs", "People on foot"]


def test_the_sentence_is_the_one_an_alert_would_send():
    cases = [(low, high, c) for low, high in ((0, 8), (10, 14), (14, 19), (22, 28), (29, 31), (45, 55))
             for c in (0.5, 0.8)]
    got = models([site(low, high, confidence=c) for low, high, c in cases])["models"]
    for (low, high, c), model in zip(cases, got):
        assert model["sentence"] == alerts._advice(low, high, c, False), (low, high, c)


def test_band_names_match_the_alerts():
    assert models([])["bands"] == alerts.BAND_LABEL
    [model] = models([site(14, 19)])["models"]
    assert model["band"] == "shin deep" and model["headline"] == "14–19 cm"


def test_every_row_has_a_word_and_a_mark_so_colour_is_never_the_only_signal():
    out = models([site(14, 19), site(14, 19, confidence=0.4), site(45, 55)])
    for model, html in zip(out["models"], out["html"]):
        assert all(row["word"] and row["mark"] in ("tick", "cross", "query") for row in model["rows"])
        assert html.count('class="sheet-mark"') == 5
    unsure = out["models"][1]
    assert {row["word"] for row in unsure["rows"]} == {"Not safe", "Unsure: treat as not safe"}
    assert "uncertain" in unsure["notes"][0]


def test_trust_age_and_state_are_said_in_words():
    one_photo, critical, receding, old = models([
        site(12, 17, trusted=False, age_min=4), site(28, 38, state="CRITICAL"),
        site(8, 13, state="RECEDING"), site(13, 18, age_min=45)])["models"]
    assert one_photo["trust"] == "From one unconfirmed photo" and one_photo["seen"] == "Seen 4 minutes ago"
    assert critical["urgent"] == "Do not enter." and critical["trust"] == "Confirmed"
    assert receding["urgent"] == "The water is falling."
    assert any("old" in note for note in old["notes"]) and not any("old" in n for n in critical["notes"])


def test_a_dry_site_says_so_and_shows_no_vehicle_rows():
    clear, watch = models([site(0, 0, state="CLEAR"), site(0, 0, state="WATCH")])["models"]
    assert clear["headline"] == "No water" and clear["rows"] == [] and clear["seen"] is None
    assert clear["sentence"] == "No water has been reported here."
    assert watch["band"] == "Watch" and "forecast" in watch["sentence"]


def test_the_sheet_never_says_a_road_is_closed_and_always_warns_of_moving_water():
    out = models([site(0, 0, state="CLEAR"), site(14, 19), site(45, 55, state="CRITICAL")])
    for model, html in zip(out["models"], out["html"]):
        assert model["moving"] == alerts.MOVING_WATER and alerts.MOVING_WATER in html
        assert "closed" not in html.lower().replace('aria-label="close"', "").replace("sheet-close", "")


def test_a_site_name_cannot_inject_markup():
    [html] = models([site(14, 19, name='<img src=x onerror=alert(1)> & "Co"')])["html"]
    assert "<img" not in html and "&lt;img" in html and "&amp;" in html


def test_rounding_in_the_map_file_never_makes_the_sheet_less_cautious():
    """The file carries whole centimetres. Rounding may only tip an answer towards "not safe"."""
    order = {bands.PASSABLE: 0, bands.UNKNOWN: 1, bands.NOT_SAFE: 1}
    for tenth in range(0, 600):
        high = tenth / 10
        for vehicle in bands.NO_GO_CM:
            exact = bands.answer_for(vehicle, high, high, 0.9)
            rounded = bands.answer_for(vehicle, round(high), round(high), 0.9)
            assert order[rounded] >= order[exact], (vehicle, high)
