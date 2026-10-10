"""scripts/simulate_multiview.py: the simulation of several marks, several objects and several cameras.

A small run, to check that it measures what its report says it measures, and that the report says it
is a simulation.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_multiview as sim  # noqa: E402


@pytest.fixture(scope="module")
def small():
    return sim.run(seed=3, count=40)


def test_every_made_camera_sees_every_mark_through_a_lens_that_bends():
    rng = np.random.default_rng(1)
    for _ in range(20):
        camera = sim.make_camera(rng)
        seen = sim.picture(camera, sim.MARKS)
        assert (seen[:, 0] > 0).all() and (seen[:, 0] < sim.IMAGE[0]).all() and (seen[:, 1] > 0).all() and (seen[:, 1] < sim.IMAGE[1]).all()
        assert -0.10 <= camera["bend"] <= 0.0 and 3.0 <= camera["at"][2] <= 7.0
    assert len(sim.MARKS) == 18 and len({tuple(m) for m in sim.MARKS}) == 18             # heights, lengths and widths, none twice


def test_the_same_waterline_is_read_three_ways_and_each_is_within_centimetres(small):
    for tilt, (one_scale, four_marks, fixed) in small["one"].items():
        if len(fixed):
            assert np.median(fixed) < 0.05 and np.median(four_marks) < 0.05 and np.median(one_scale) < 0.06, tilt


def test_three_readings_throw_a_wild_one_away_and_two_cannot(small):
    errors, agreed = small["wild"]
    out = lambda name: float(np.mean(errors[name] > 0.10))                    # noqa: E731
    assert out("one") > 0.05                                                 # about one in ten is far out, as it was made
    assert out("three posts") < 0.5 * out("one") and out("three cameras") < 0.5 * out("one")
    assert out("two cameras") > out("three cameras")                         # two are not enough
    assert 0.85 < agreed["three cameras"] <= 1.0
    clean, _ = small["clean"]
    assert np.median(clean["three posts"]) <= np.median(clean["one"]) + 0.002


def test_two_cameras_give_a_speed_without_the_level_and_one_camera_needs_it(small):
    flow = small["flow"]
    assert np.median(flow["two cameras"]) < 0.1                               # metres a second
    assert np.median(flow["one camera, told the road is dry"]) > np.median(flow["one camera, told the true level"])


def test_the_report_is_labelled_simulated_and_says_what_it_does_not_test():
    report = sim.OUT.read_text("utf-8")
    assert report.splitlines()[2].startswith("**SIMULATED. No real camera, photo or flood is behind any number here.**")
    flat = " ".join(report.split())
    for must_say in ("It does not test finding a waterline or a floating thing in a real picture",
                     "These are the errors of the geometry, not of the method", "Two readings are not enough",
                     "they will be wrong together more often than this assumes", "No site has two cameras on one water"):
        assert must_say in flat, must_say
    for name in ("README.md", "docs/submission-writeup.md", "docs/video-script.md"):
        assert "multiview-simulation" not in (ROOT / name).read_text("utf-8"), name       # made scenes are never quoted as accuracy
