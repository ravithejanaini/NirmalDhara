"""nirmaldhara/ramp.py: depth from where the water's edge sits on a ramp, on a made road.

The road is METHOD 15.1's example: 4% down from the left, 5% up to the right. Every test places an
edge whose true depth is known from the profile. No edge on a real road has been read.
"""

import sys
from pathlib import Path

import numpy as np

from nirmaldhara import depthmodel, ramp

ROOT = Path(__file__).resolve().parents[1]

ROAD = [(-60, 2.4), (0, 0.0), (40, 2.0)]


def strip(rows=200):
    """A made strip along the left ramp: the row at each distance by a map that perspective obeys, and the
    marks a person would place on it."""
    row_at = lambda distance: 199.0 * (distance + 50.0) / (48.0 + 0.012 * (distance + 50.0) * 40.0)      # noqa: E731
    marks = [(row_at(d), d) for d in (-50.0, -35.0, -20.0, -8.0, -2.0)]
    return row_at, marks, rows


def test_a_metre_of_ramp_is_as_many_centimetres_as_the_ramp_is_steep():
    assert ramp.lowest(ROAD) == (0.0, 0.0)
    assert abs(ramp.height_at(ROAD, -10) - 0.40) < 1e-12 and abs(ramp.height_at(ROAD, 8) - 0.40) < 1e-12
    assert abs(ramp.slope_at(ROAD, -10) - 0.04) < 1e-12 and abs(ramp.slope_at(ROAD, 8) - 0.05) < 1e-12
    low, high = ramp.depth_from_edge(ROAD, -10, -10)
    assert abs(low - 40) < 1e-9 and abs(high - 40) < 1e-9
    low, high = ramp.depth_from_edge(ROAD, -9, -11)                # placed to within a metre either way
    assert abs(low - 36) < 1e-9 and abs(high - 44) < 1e-9
    assert abs(ramp.height_at(ROAD, -70) - 2.8) < 1e-12            # past the end of the profile, the last stretch carried on


def test_an_edge_that_may_lie_either_side_of_the_lowest_point_may_be_no_water():
    low, high = ramp.depth_from_edge(ROAD, -1, 2)
    assert low == 0.0 and abs(high - 10) < 1e-9


def test_the_edges_on_two_ramps_must_give_one_level():
    left, right = ramp.depth_from_edge(ROAD, -11, -9.5), ramp.depth_from_edge(ROAD, 7.8, 9)
    low, high, agreed = ramp.together([left, right])
    assert agreed and abs(low - 39) < 1e-9 and abs(high - 44) < 1e-9          # narrower than either alone
    wrong = ramp.depth_from_edge(ROAD, 14, 15)                                 # an edge misread on the right ramp
    low, high, agreed = ramp.together([left, wrong])
    assert not agreed and abs(low - 38) < 1e-9 and abs(high - 75) < 1e-9       # said, and nothing is thrown away


def test_a_depth_read_up_the_ramp_is_deeper_at_the_lowest_point():
    low, high = ramp.at_lowest(ROAD, -6, -4, 0, 12)                # a car between 4 and 6 m up the ramp, its tyre wet and its rim dry
    assert abs(low - 16) < 1e-9 and abs(high - 36) < 1e-9
    assert ramp.at_lowest(ROAD, 0, 0, 5, 9) == (5.0, 9.0)          # at the lowest point itself, nothing is added


def test_what_the_answer_rests_on_is_said_in_centimetres():
    assert abs(ramp.doubt(ROAD, -10, 2.0) - 8.0) < 1e-9            # an edge placed to 2 m on a 4% ramp
    assert abs(ramp.doubt(ROAD, 10, 2.0, heights_cm=1.0) - 11.0) < 1e-9
    low, high = ramp.guessed(10)                                   # a profile from a map: the same edge, three times apart
    assert abs(low - 20) < 1e-9 and abs(high - 60) < 1e-9 and ramp.guessed(-10) == (low, high)


def test_marks_at_known_distances_turn_a_row_into_a_place_on_the_road():
    row_at, marks, _ = strip()
    along = ramp.distance_map(marks)
    for distance in (-45.0, -27.5, -9.25, -3.0):
        assert abs(along(row_at(distance)) - distance) < 1e-6      # the map that perspective obeys, found exactly
    two = ramp.distance_map(marks[:2])
    assert abs(two(marks[0][0]) + 50) < 1e-9 and abs(two(marks[1][0]) + 35) < 1e-9
    low, high = ramp.depth_from_rows(ROAD, marks, row_at(-9.0), row_at(-9.5))
    assert abs(low - 36) < 1e-4 and abs(high - 38) < 1e-4


def test_a_witness_made_from_the_road_reads_a_depth_no_flood_taught_it():
    row_at, marks, rows = strip()
    model = ramp.site_model(ROAD, {"left ramp": lambda grid: ramp.witness("left ramp", grid, ROAD, marks, rows, spread=2.0, camera="cam")})
    assert model.grid[0] == 0.0 and abs(model.grid[-1] - 2.0) < 0.011 and model.witnesses["left ramp"].lines == 0
    for depth in (0.12, 0.37, 0.90, 1.60):                         # nothing was learnt, so nothing is "past what was learnt"
        answer = depthmodel.believe(model, {"left ramp": ("line", row_at(-depth / 0.04))})
        assert abs(answer.level - depth) < 0.03 and answer.low <= depth <= answer.high, depth
    reading = depthmodel.to_reading(depthmodel.believe(model, {"left ramp": ("line", row_at(-0.37 / 0.04))}), road=0.0, ts=0, device="cam")
    assert reading.low <= 37 <= reading.high and reading.high - reading.low < 25 and reading.source == "cctv"


def test_it_carries_a_learnt_witness_past_the_levels_it_learnt():
    row_at, marks, rows = strip()
    model = ramp.site_model(ROAD, {"left ramp": lambda grid: ramp.witness("left ramp", grid, ROAD, marks, rows, spread=2.0, camera="cam")})
    levels = np.repeat(np.linspace(0.10, 0.40, 16), 2)             # a post watched only up to 40 cm
    post_row = lambda level: 300.0 - 250.0 * level                 # noqa: E731
    post = depthmodel.learn_witness("post", model.grid, levels, [("line", post_row(v)) for v in levels], rows=300, camera="cam")
    assert np.ptp(post.row[model.grid > 0.45]) == 0                # blind above what it learnt
    alone = depthmodel.SiteModel(model.grid, {"post": post}, {"cam": 1.0}, {"cam": 1.0}, model.rate)
    seen = {"post": ("line", post_row(0.90)), "left ramp": ("line", row_at(-0.90 / 0.04))}
    assert depthmodel.believe(alone, seen).level < 0.60            # the post alone reads 90 cm as something it knows
    model.witnesses["post"] = post
    assert abs(depthmodel.believe(model, seen).level - 0.90) < 0.04


def test_two_ramps_are_two_witnesses_and_agree():
    row_at, marks, rows = strip()
    right_row = lambda distance: 180.0 - 4.0 * distance            # noqa: E731   a second strip, up the right ramp
    right_marks = [(right_row(d), d) for d in (2.0, 20.0, 38.0)]
    make = {"left ramp": lambda grid: ramp.witness("left ramp", grid, ROAD, marks, rows, spread=3.0, camera="a"),
            "right ramp": lambda grid: ramp.witness("right ramp", grid, ROAD, right_marks, 180, spread=3.0, camera="b")}
    model = ramp.site_model(ROAD, make)
    both = depthmodel.believe(model, {"left ramp": ("line", row_at(-0.50 / 0.04)), "right ramp": ("line", right_row(0.50 / 0.05))})
    one = depthmodel.believe(model, {"left ramp": ("line", row_at(-0.50 / 0.04))})
    assert abs(both.level - 0.50) < 0.02 and both.high - both.low <= one.high - one.low


def test_a_strip_that_runs_to_the_horizon_is_mapped_all_the_same():
    row_at = lambda up: 239.0 * 20.0 / (up + 20.0)                 # noqa: E731   row 0 is the horizon: any distance at all
    marks = [(row_at(up), -up) for up in (0.0, 5.0, 15.0, 30.0, 50.0)]
    along = ramp.distance_map(marks)
    for up in (0.0, 2.5, 12.5, 27.5, 45.0):
        assert abs(along(row_at(up)) + up) < 1e-6
    assert along(0.0) == float("inf") or abs(along(0.0)) > 1e6    # and the horizon itself is no distance, not a crash
    made = ramp.witness("ramp", np.arange(0.0, 2.0, 0.01), ROAD, marks, 240, spread=2.0)
    assert np.isfinite(made.row).all() and made.row[20] > made.row[110]      # deeper water, an edge further up the strip


def test_the_real_detector_on_a_made_strip_gives_the_depth_through_the_road():
    """The waterline detector itself, on rendered frames of a strip laid along the left ramp. A made strip:
    it shows the chain holds, not that the detector finds the edge of water on a real road."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import simulate_waterline as sim
    from nirmaldhara import waterline
    row_at = lambda up: 239.0 * 20.0 / (up + 20.0)                 # noqa: E731
    marks = [(row_at(up), -up) for up in (0.0, 5.0, 15.0, 30.0, 50.0)]
    right_row = lambda up: 239.0 * 24.0 / (up + 24.0)              # noqa: E731   a second strip, up the 5% ramp
    right_marks = [(right_row(up), up) for up in (0.0, 4.0, 12.0, 24.0, 38.0)]
    rng = np.random.default_rng(7)
    scene = sim.make_scene(rng, "clear")
    one = ramp.site_model(ROAD, {"left": lambda grid: ramp.witness("left", grid, ROAD, marks, 240, spread=2.0, camera="a")})
    two = ramp.site_model(ROAD, {"left": lambda grid: ramp.witness("left", grid, ROAD, marks, 240, spread=2.0, camera="a"),
                                 "right": lambda grid: ramp.witness("right", grid, ROAD, right_marks, 240, spread=2.0, camera="b")})
    for depth in (0.20, 0.50, 1.10):
        left = waterline.locate(sim.render_frames(rng, scene, int(round(row_at(depth / 0.04)))), scene["reference"])
        right = waterline.locate(sim.render_frames(rng, scene, int(round(right_row(depth / 0.05)))), scene["reference"])
        assert left.found and right.found
        low, high = ramp.depth_from_rows(ROAD, marks, left.low, left.high)
        assert low - 2 <= 100 * depth <= high + 2 and high - low < 8, depth          # the detector's own range of rows, as a depth
        both = ramp.together([(low, high), ramp.depth_from_rows(ROAD, right_marks, right.low, right.high)])
        assert both[2] and both[0] - 2 <= 100 * depth <= both[1] + 2
        alone = depthmodel.believe(one, {"left": ("line", left.row)})
        pair = depthmodel.believe(two, {"left": ("line", left.row), "right": ("line", right.row)})
        assert abs(alone.level - depth) < 0.03 and abs(pair.level - depth) < 0.03
        assert pair.high - pair.low < 0.15 and pair.high - pair.low <= alone.high - alone.low + 1e-9
    assert alone.high - alone.low < 0.2                            # deep water: one ramp is enough for a narrow range


def test_the_methods_table_is_the_arithmetic():
    method = (ROOT / "METHOD.md").read_text("utf-8")
    for metres in (1, 2, 5):
        cells = [f"{ramp.doubt([(0, 0.0), (100, 100 * slope)], 50, metres):.0f} cm" for slope in (0.02, 0.04, 0.06)]
        assert f"| {metres} m | " + " | ".join(cells) + " |" in method, metres
    assert "anything from 20 to 60 cm" in method and ramp.guessed(10) == (20.0, 60.0)
    flat = " ".join(method.split())
    assert "Tested on made roads only. No place in the registry has a profile" in flat


def test_the_module_says_it_has_read_no_real_road():
    text = " ".join(ramp.__doc__.split())
    for must_say in ("Tested on made roads only", "No place in the registry has a profile", "Nothing calls it",
                     "everything rests on the profile", "three times apart"):
        assert must_say in text, must_say
