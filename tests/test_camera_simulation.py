"""scripts/simulate_cameras.py: the geometry is right, and the result is never passed off as real."""

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_cameras as sim  # noqa: E402

LEVEL = {"id": "level", "height_m": 0.75, "distance_m": 6.0, "side_m": 0.0, "tilt": 0.0, "roll": 0.0,
         "focal_px": 1000, "distortion": 0.0}
STEEP = {**LEVEL, "id": "steep", "height_m": 6.0, "distance_m": 4.0, "tilt": math.atan2(5.5, 4.0)}


def exact_marks(camera):
    return {name: sim.project(camera, cm) for name, cm in (("base", 0), ("middle", 75), ("top", 150))}


def test_a_level_camera_with_perfect_marks_reads_the_true_depth_by_both_methods():
    marks = exact_marks(LEVEL)
    for depth in sim.DEPTHS_CM:
        waterline = sim.project(LEVEL, depth)
        assert abs(sim.two_marks(marks, waterline) - depth) < 0.01
        assert abs(sim.three_marks(marks, waterline) - depth) < 0.01


def test_a_steep_camera_fools_two_marks_and_not_three():
    marks = exact_marks(STEEP)
    two = [abs(sim.two_marks(marks, sim.project(STEEP, d)) - d) for d in sim.DEPTHS_CM]
    three = [abs(sim.three_marks(marks, sim.project(STEEP, d)) - d) for d in sim.DEPTHS_CM]
    assert max(two) > 3.0                    # perspective alone, with no marking error at all
    assert max(three) < 0.01                 # three points undo it exactly


def test_roll_does_not_disturb_three_marks():
    rolled = {**STEEP, "roll": math.radians(4)}
    marks = exact_marks(rolled)
    assert all(abs(sim.three_marks(marks, sim.project(rolled, d)) - d) < 0.01 for d in sim.DEPTHS_CM)


def test_a_view_that_cannot_resolve_the_gauge_is_refused():
    assert sim.usable(LEVEL)
    assert not sim.usable({**LEVEL, "distance_m": 200.0})            # the gauge is a few pixels tall
    assert not sim.usable({**LEVEL, "side_m": 40.0})                 # the gauge is out of frame


def test_the_same_seed_gives_the_same_table():
    first, second = sim.run(seed=3, count=40), sim.run(seed=3, count=40)
    assert sim.summary(first[1]) == sim.summary(second[1])
    assert sim.summary(first[1]) != sim.summary(sim.run(seed=4, count=40)[1])


def test_the_written_report_matches_the_script_and_says_it_is_simulated():
    cameras, kept = sim.run(seed=7)
    text = sim.OUT.read_text("utf-8")
    assert text == sim.report(cameras, kept, 7)
    assert text.splitlines()[2].startswith("**SIMULATED.")
    assert "has never been tested" in sim.__doc__ and "untested" in text


def test_playing_a_camera_reaches_only_this_machine():
    source = (ROOT / "scripts" / "simulate_cameras.py").read_text("utf-8")
    assert 'default="http://127.0.0.1:8080"' in source and '"SIMULATED camera' in source.replace("f\"", '"')
    for remote in ("boto3", "import stack", "import send", "amazonaws", "rtsp", "cv2"):
        assert remote not in source, remote


def test_no_public_page_or_writeup_quotes_the_simulation_as_accuracy():
    for name in ("README.md", "docs/submission-writeup.md", "docs/video-script.md"):
        assert "camera-simulation" not in (ROOT / name).read_text("utf-8"), name
    rng = random.Random(1)
    assert len({sim.make_camera(rng, n)["id"] for n in range(5)}) == 5
