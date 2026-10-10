"""scripts/simulate_site.py: three rendered cameras on one water, from frames to the site engine's answer.

A short run of the whole chain, to check that the parts fit together and that the report says it is a
simulation.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_site as site  # noqa: E402
from nirmaldhara import bands  # noqa: E402


@pytest.fixture(scope="module")
def short():
    return site.run(seed=5, evenings=12)


def test_the_detector_reads_a_rendered_camera_and_the_row_follows_the_depth():
    rng = np.random.default_rng(0)
    camera = site.make_camera(rng)
    rows = []
    for depth in (10.0, 25.0, 40.0):
        kind, row = site.look(rng, camera, "clear", depth, 0.6)
        assert kind == "line" and abs(row - (site.BASE_ROW - depth / 0.6)) <= 5
        rows.append(row)
    assert rows[0] > rows[1] > rows[2]                                     # deeper water, a line nearer the dry end
    assert site.look(rng, camera, "clear", 0.0, 0.6)[0] == "dry"


def test_every_moment_has_a_report_from_every_camera_and_evenings_rise_and_fall():
    depths, days, hours, reports, conditions = site.make_history(seed=3, evenings=3)
    assert len(depths) == 3 * site.MOMENTS and all(len(reports[name]) == len(depths) for name in site.CAMERAS)
    assert set(np.round(np.diff(hours[:site.MOMENTS]) * 60).tolist()) == {float(site.EVERY)}
    for evening in range(3):
        d = depths[days == evening]
        assert d.argmax() == site.SHAPE.index(1.0) and (d[0] < d.max() or d.max() == 0)
        assert len({conditions[name][evening * site.MOMENTS] for name in site.CAMERAS}) >= 1


def test_the_chain_holds_from_frames_to_the_engines_answer(short):
    three, one = short["errors"]["all three, each moment"], short["errors"]["south alone, each moment"]
    assert np.median(three) < 8.0 and np.percentile(three, 90) <= np.percentile(one, 90) + 1e-9
    assert short["known"]["all three, through time"] >= short["known"]["south alone, through time"]
    answers = short["answers"]
    assert len(answers) == short["moments"][1] and {truth for _, truth, _ in answers} <= {bands.PASSABLE, bands.NOT_SAFE}
    unsafe = sum(model == bands.PASSABLE and truth != bands.PASSABLE for model, truth, _ in answers)
    assert unsafe <= 1                                                     # the engine is not told a flooded road is passable
    assert {s for _, _, s in answers} - {"CLEAR"}                          # and the site did leave CLEAR


def test_each_camera_is_its_own_witness_with_its_own_share(short):
    model = short["model"]
    assert set(model.witnesses) == set(site.CAMERAS) and set(model.share) == set(site.CAMERAS)
    assert {w.camera for w in model.witnesses.values()} == set(site.CAMERAS)


def test_the_report_is_labelled_simulated_and_says_what_it_is_not():
    report = site.OUT.read_text("utf-8")
    assert report.splitlines()[2].startswith("**SIMULATED. No real camera, photo or flood is behind any number here.**")
    flat = " ".join(report.split())
    for must_say in ("no real pair has been looked at", "The errors are the renderer's", "Following the level through time did not help here",
                     "Passable when the true depth said not", "nothing in the system calls this chain"):
        assert must_say in flat, must_say
    for name in ("README.md", "docs/submission-writeup.md", "docs/video-script.md"):
        assert "site-simulation" not in (ROOT / name).read_text("utf-8"), name       # made scenes are never quoted as accuracy
