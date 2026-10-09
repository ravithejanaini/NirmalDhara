"""The cross-section drawing (web/section.js): scale, limits and what it says. Run with Node."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from nirmaldhara import bands

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")


def run(sites):
    script = f"""
import {{ sectionModel, sectionSvg, CAR_WHEEL_CM, SCOOTER_WHEEL_CM, KNEE_CM }} from "{(ROOT / 'web' / 'section.js').as_uri()}";
const sites = {json.dumps(sites)};
console.log(JSON.stringify({{ models: sites.map(sectionModel), svg: sites.map((s) => sectionSvg(sectionModel(s))),
  sizes: [CAR_WHEEL_CM, SCOOTER_WHEEL_CM, KNEE_CM] }}));
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True,
                         encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def site(low, high):
    return {"id": "s", "low": low, "high": high}


def test_at_twenty_centimetres_the_water_reaches_a_third_of_the_car_wheel():
    [model] = run([site(15, 20)])["models"]
    assert 0.30 < model["carWheelShare"] < 0.35
    assert "about a third of the car's wheel" in model["label"]


def test_the_figures_are_drawn_to_the_sizes_the_photo_reader_is_told():
    out = run([site(15, 20)])
    assert out["sizes"] == [62, 43, 46]
    reader = (ROOT / "src" / "nirmaldhara" / "reader.py").read_text("utf-8")
    assert "about 62 cm" in reader and "about 43 cm" in reader      # the same wheels, in the reader's instruction
    svg = out["svg"][0]
    assert 'r="31"' in svg and svg.count('r="21.5"') == 2          # one car wheel, two scooter wheels
    assert "-46" in svg                                             # the knee


def test_the_limit_marks_are_the_limits_in_the_rules():
    out = run([site(15, 20)])
    assert out["models"][0]["limits"] == {
        "car": bands.NO_GO_CM["car"], "two_wheeler": bands.NO_GO_CM["two_wheeler"],
        "pedestrian": bands.NO_GO_CM["pedestrian"]}
    marks = re.findall(r'<text x="\d+" y="-\d+">(\d+)</text>', out["svg"][0])
    assert sorted(map(int, marks)) == [15, 20, 30]


def test_colour_follows_the_cautious_end_as_on_the_glyph():
    models = run([site(2, 11.9), site(5, 12), site(20, 30), site(20, 30.1)])["models"]
    assert [m["tone"] for m in models] == ["shallow", "water", "water", "deep"]


def test_water_above_a_metre_fills_the_drawing_and_goes_no_further():
    [model] = run([site(120, 150)])["models"]
    assert model["low"] == 100 and model["high"] == 100 and model["carWheelShare"] == 1
    assert "the top of the car's wheel" in model["label"]


def test_one_unit_is_one_centimetre():
    """The water's surface is placed by translating it up by its depth: no hidden scale factor."""
    script = f"""
import {{ sectionModel, sectionSvg }} from "{(ROOT / 'web' / 'section.js').as_uri()}";
console.log(JSON.stringify(sectionSvg(sectionModel({{id: "s", low: 15, high: 20}}), {{low: 15, high: 20}})));
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, encoding="utf-8")
    svg = json.loads(out.stdout)
    assert 'section-solid" style="transform: translateY(-15px)"' in svg
    assert 'section-surface" style="transform: translateY(-20px)"' in svg
    assert 'viewBox="0 -104 420 112"' in svg
