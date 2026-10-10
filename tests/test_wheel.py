"""nirmaldhara/wheel.py: a person's reading of a wheel as a depth, and what the engine may make of it.

The table must be METHOD C2's and the photo reader's, figure for figure. An answer by itself can
rule a class of road user out and can never let one in. Nothing here has been tried on a person.
"""

import re
from pathlib import Path

import pytest

from nirmaldhara import bands, reader, state, wheel

ROOT = Path(__file__).resolve().parents[1]
ROAD = [(-60, 2.4), (0, 0.0), (40, 2.0)]                           # METHOD 15.1: 4% down from the left, 5% up to the right


def test_the_table_is_the_methods_figure_for_figure():
    method = (ROOT / "METHOD.md").read_text("utf-8")
    rows = {"tyre": "Tyre sidewall only, rim dry", "rim": "Rim, below one-third of the wheel",
            "third": "One-third of the wheel up to the axle", "axle": "Axle up to the top of the tyre", "over": "Above the tyre"}
    for mark, words in rows.items():
        line = next(row for row in method.splitlines() if row.startswith(f"| {words} |"))
        cells = [cell.strip() for cell in line.strip("|").split("|")][1:]
        for name, cell in zip(("car", "motorcycle", "scooter"), cells):
            low, high = wheel.TABLE[name][mark]
            assert cell == (f"above {low} cm" if mark == "over" else f"{low}–{high} cm"), (name, mark, cell)


def test_the_question_a_person_is_asked_is_in_the_method_with_the_same_figures():
    method = (ROOT / "METHOD.md").read_text("utf-8")
    for mark, words in wheel.MARKS.items():
        low, high = wheel.TABLE["car"][mark]
        assert f"| {words} | " + (f"above {low} cm" if mark == "over" else f"{low}–{high} cm") + " |" in method, mark
    flat = " ".join(method.split())
    assert "at a confidence of 0.5, under the 0.6" in flat and "counts at 0.7" in flat
    assert (wheel.SOMEWHERE, bands.MIN_CONFIDENCE, wheel.PLACED) == (0.5, 0.6, 0.7)
    assert "Nothing here has been tried on a person" in flat


def test_the_photo_reader_is_told_the_same_figures():
    told = " ".join(reader.INSTRUCTION.split())
    for name, words in (("car", "Car wheel"), ("motorcycle", "Motorcycle wheel"), ("scooter", "Scooter or auto-rickshaw wheel")):
        sentence = told.split(words)[1].split(" - ")[0]
        for mark in ("tyre", "rim", "third", "axle"):
            low, high = wheel.TABLE[name][mark]
            assert f"{low}-{high}" in sentence, (name, mark)


def test_the_answers_run_from_shallow_to_deep_without_a_gap():
    assert list(wheel.MARKS) == ["tyre", "rim", "third", "axle", "over"] and set(wheel.WHEELS) == {"car", "auto", "motorcycle", "scooter"}
    for name, table in wheel.TABLE.items():
        ranges = [table[mark] for mark in wheel.MARKS]
        assert ranges[0][0] == 0 and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])), name
        assert ranges[-1][0] == ranges[-1][1]                      # "over" is a floor: the tyre's height and no more
    assert wheel.depth("auto", "rim") == wheel.depth("scooter", "rim") == (9, 14)
    with pytest.raises(ValueError):
        wheel.depth("bus", "rim")
    with pytest.raises(ValueError):
        wheel.depth("car", "roof")


def test_an_answer_by_itself_can_rule_a_class_out_and_never_lets_one_in():
    for name in wheel.WHEELS:
        for mark in wheel.MARKS:
            assert bands.PASSABLE not in wheel.answers(name, mark).values(), (name, mark)
    assert wheel.SOMEWHERE < bands.MIN_CONFIDENCE <= wheel.PLACED
    dry_rim = wheel.answers("car", "tyre")                         # up to 12 cm where the car stands: nobody ruled out, nobody let in
    assert all(dry_rim[v] == bands.UNKNOWN for v in bands.NO_GO_CM)
    wet_rim = wheel.answers("car", "rim")                          # 12 to 20 cm: bikes, autos and cars must not enter
    assert [v for v, said in wet_rim.items() if said == bands.NOT_SAFE] == ["two_wheeler", "auto", "car"]
    assert wet_rim["pedestrian"] == wet_rim["suv"] == bands.UNKNOWN
    assert all(wheel.answers("car", "third")[v] == bands.NOT_SAFE for v in bands.NO_GO_CM)
    assert set(wheel.answers("car", "axle").values()) == {bands.NOT_SAFE}      # at 62 cm, buses and trucks too


def test_where_the_vehicle_stands_is_known_the_depth_is_carried_to_the_lowest_point():
    low, high, confidence = wheel.estimate("car", "tyre", ROAD, -6, -4)       # 4 to 6 m up a 4% ramp, its rim dry
    assert abs(low - 16) < 1e-9 and abs(high - 36) < 1e-9 and confidence == wheel.PLACED
    assert set(bands.passability(low, high, confidence)[v] for v in bands.NO_GO_CM) == {bands.NOT_SAFE}
    at_the_bottom = wheel.estimate("car", "tyre", ROAD, 0, 0)                 # standing at the lowest point with its rim dry
    assert at_the_bottom == (0.0, 12.0, wheel.PLACED)
    assert all(bands.passability(*at_the_bottom)[v] == bands.PASSABLE for v in bands.NO_GO_CM)
    assert wheel.estimate("car", "tyre") == (0.0, 12.0, wheel.SOMEWHERE)


def test_several_answers_are_joined_by_the_engines_own_rule():
    found = wheel.together([wheel.estimate("car", "rim"), wheel.estimate("auto", "third"), wheel.estimate("motorcycle", "rim")])
    assert found == state.fuse([(12.0, 20.0, 0.5), (14.0, 22.0, 0.5), (9.0, 20.0, 0.5)])
    assert found[0] == 12.0 and found[1] == 22.0                   # the middle low end, the highest high end
    apart = wheel.together([wheel.estimate("car", "tyre"), wheel.estimate("car", "axle")])
    assert apart[2] == wheel.SOMEWHERE / 2                         # answers far apart: believed half as much
    assert wheel.together([]) is None


def test_an_answer_reaches_the_engine_as_a_reading_and_moves_the_place():
    reading = wheel.to_reading(wheel.estimate("car", "third"), 600, "guardian", "g1")
    assert (reading.low, reading.high, reading.confidence, reading.source) == (20.0, 31.0, wheel.SOMEWHERE, "guardian")
    site = state.apply_reading(state.Site("hyd-000"), reading)
    assert site.high == 31.0 and site.state != state.CLEAR
    assert bands.passability(site.low, site.high, reading.confidence)["car"] == bands.NOT_SAFE


def test_an_answer_is_a_measured_depth_to_teach_a_camera_with():
    assert wheel.label("car", "rim") == (16.0, 4.0) and wheel.label("scooter", "tyre") == (4.5, 4.5)
    assert wheel.label("car", "over") == (62.0, 0.0)


def test_the_module_says_it_has_been_tried_on_nobody():
    text = " ".join(wheel.__doc__.split())
    for must_say in ("nothing here has been tried on a person", "Nothing calls this module", "How well people read a wheel is not known",
                     "can never say that one may"):
        assert must_say in text, must_say
    assert re.fullmatch(r"[A-Z].*\?", wheel.ASK) and all(words.endswith(".") for words in wheel.MARKS.values())
