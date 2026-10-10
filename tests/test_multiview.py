"""nirmaldhara/multiview.py: several reference objects in one view, and several cameras at one place.

Made cameras looking at made marks, so the right answer is known exactly. What this does on a real
flood is measured by scripts/river_multi_reference.py; what the geometry allows with the errors of a
real camera is tried in scripts/simulate_multiview.py.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import multiview  # noqa: E402


def a_camera(at, look, focal=1400.0, centre=(960.0, 540.0)):
    """A pinhole camera at `at` looking towards `look`, as the 3 by 4 matrix that pictures the world."""
    at, look = np.asarray(at, float), np.asarray(look, float)
    forward = (look - at) / np.linalg.norm(look - at)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    turn = np.array([right, down, forward])
    inside = np.array([[focal, 0, centre[0]], [0, focal, centre[1]], [0, 0, 1.0]])
    return inside @ np.column_stack([turn, -turn @ at])


# A kerb 6 m long, a lane 3.5 m wide and two posts 1.5 m high: lengths, widths and heights, in metres.
MARKS = np.array([[0, 0, 0], [6, 0, 0], [0, 3.5, 0], [6, 3.5, 0], [0, 0, 1.5], [6, 3.5, 1.5], [3, 0, 0], [3, 3.5, 0.75]], float)
CAMERA = a_camera((-4.0, -6.0, 5.0), (3.0, 1.5, 0.3))
OTHER = a_camera((11.0, -5.0, 4.0), (3.0, 1.5, 0.3))


def test_marks_of_known_height_length_and_width_fix_the_camera():
    found = multiview.camera_from_points(MARKS, multiview.project(CAMERA, MARKS))
    assert multiview.misfit(found, MARKS, multiview.project(CAMERA, MARKS)) < 1e-6
    elsewhere = np.array([[2.0, 1.0, 0.4], [5.0, 3.0, 1.1], [1.0, 2.5, 0.0]])
    assert np.allclose(multiview.project(found, elsewhere), multiview.project(CAMERA, elsewhere), atol=1e-5)


def test_heights_alone_or_ground_distances_alone_do_not_fix_it():
    on_the_ground = np.array([[x, y, 0.0] for x in (0, 2, 4, 6) for y in (0, 3.5)])
    with pytest.raises(ValueError, match="one plane"):
        multiview.camera_from_points(on_the_ground, multiview.project(CAMERA, on_the_ground))
    with pytest.raises(ValueError, match="six marks"):
        multiview.camera_from_points(MARKS[:5], multiview.project(CAMERA, MARKS[:5]))


@pytest.mark.parametrize("depth", [0.05, 0.19, 0.33, 0.6])
def test_where_the_water_meets_a_post_is_a_height_whatever_the_angle(depth):
    for camera in (CAMERA, OTHER, a_camera((3.0, -3.0, 9.0), (3.0, 1.5, 0.0))):      # the last looks steeply down
        pixel = multiview.project(camera, [6.0, 3.5, depth])
        assert multiview.height_on_post(camera, pixel, 6.0, 3.5) == pytest.approx(depth, abs=1e-9)


def test_one_scale_from_two_marks_is_wrong_for_a_tilted_camera_and_three_marks_are_right():
    steep = a_camera((2.0, -2.5, 6.0), (6.0, 3.5, 0.5))
    along = lambda z: float(np.linalg.norm(multiview.project(steep, [6.0, 3.5, z]) - multiview.project(steep, [6.0, 3.5, 0.0])))   # noqa: E731
    two = multiview.height_map([(along(0.0), 0.0), (along(1.5), 1.5)])
    three = multiview.height_map([(along(0.0), 0.0), (along(0.75), 0.75), (along(1.5), 1.5)])
    assert abs(two(along(0.3)) - 0.3) > 0.01                                 # more than a centimetre out
    assert three(along(0.3)) == pytest.approx(0.3, abs=1e-9)
    five = multiview.height_map([(along(z), z) for z in (0.0, 0.4, 0.75, 1.1, 1.5)])
    assert five(along(0.3)) == pytest.approx(0.3, abs=1e-9)


def test_two_cameras_place_a_floating_thing_and_time_gives_its_speed():
    start, end = np.array([2.0, 1.0, 0.25]), np.array([3.2, 1.9, 0.25])       # 1.5 m in 2 s on water 25 cm deep
    cameras = [CAMERA, OTHER]
    before, after = [multiview.project(c, start) for c in cameras], [multiview.project(c, end) for c in cameras]
    assert np.allclose(multiview.locate(cameras, before), start, atol=1e-8)
    speed, heading, level = multiview.surface_speed(cameras, before, after, seconds=2.0)
    assert speed == pytest.approx(0.75) and heading == pytest.approx(36.87, abs=0.01) and level == pytest.approx(0.25)
    with pytest.raises(ValueError, match="two cameras"):
        multiview.locate([CAMERA], [before[0]])


def test_one_camera_needs_the_level_and_is_wrong_by_as_much_as_the_level_is():
    start, end = np.array([2.0, 1.0, 0.25]), np.array([3.2, 1.9, 0.25])
    before, after = multiview.project(CAMERA, start), multiview.project(CAMERA, end)
    assert np.allclose(multiview.meet_plane(CAMERA, before, 0.25), start[:2], atol=1e-8)
    right, _ = multiview.speed_on_plane(CAMERA, before, after, level=0.25, seconds=2.0)
    assert right == pytest.approx(0.75)
    off, _ = multiview.speed_on_plane(CAMERA, before, after, level=0.0, seconds=2.0)
    assert abs(off - 0.75) > 0.01                                            # told the road is dry, it gets the speed wrong


def test_three_readings_that_agree_give_the_middle_one_and_one_wild_reading_cannot_move_it():
    low, high, agreed = multiview.combine([(14, 19, 1.0), (15, 20, 1.0), (13, 18, 1.0)])
    assert (low, high, agreed) == (14.0, 19.0, True)
    assert multiview.combine([(14, 19, 1.0), (15, 20, 1.0), (60, 70, 1.0)]) == (15.0, 20.0, True)      # one far too high
    assert multiview.combine([(14, 19, 1.0), (15, 20, 1.0), (0, 2, 1.0)]) == (14.0, 19.0, True)        # one far too low


def test_with_fewer_than_three_or_no_agreement_the_cautious_rule_stands():
    assert multiview.combine([]) is None
    assert multiview.combine([(14, 19, 1.0)]) == (14.0, 19.0, False)
    assert multiview.combine([(14, 19, 1.0), (30, 36, 1.0)]) == (14.0, 36.0, False)                    # two: the highest high end
    low, high, agreed = multiview.combine([(2, 6, 1.0), (20, 26, 1.0), (45, 52, 1.0)])                 # three that do not overlap
    assert agreed is False and high == 52.0


def test_a_reading_with_a_better_record_counts_for_more():
    assert multiview.combine([(14, 19, 5.0), (30, 35, 1.0), (31, 36, 1.0)])[:2] == (14.0, 19.0)
    assert multiview.combine([(14, 19, 1.0), (30, 35, 1.0), (31, 36, 1.0)])[:2] == (30.0, 35.0)
    assert multiview.combine([(14, 19, 0.0), (15, 20, 0.0), (13, 18, 0.0)]) == (14.0, 19.0, True)      # no weights: equal ones


def test_the_module_says_what_was_measured_and_that_it_installs_nothing():
    for must_say in ("Nothing here installs a camera", "no site has two cameras on one\nwater", "only\nbeen checked on made scenes",
                     "measured on a real flood by scripts/river_multi_reference.py"):
        assert must_say in multiview.__doc__, must_say


def test_one_figure_from_several_is_the_middle_of_three_and_the_mean_of_two():
    assert multiview.best_guess([14.0, 60.0, 15.0], [1, 1, 1]) == 15.0          # the wild one is outvoted
    assert multiview.best_guess([14.0, 60.0], [1, 1]) == 37.0                   # two cannot say which is wrong
    assert multiview.best_guess([14.0, 60.0], [3, 1]) == pytest.approx(25.5)    # but the better record counts for more
    assert multiview.best_guess([14.0], [1]) == 14.0
