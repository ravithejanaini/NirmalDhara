"""nirmaldhara/waterline.py: finding the water on a fixed camera's strip, and saying when it cannot.

Small rendered scenes with a known line. The full measurement is scripts/simulate_waterline.py.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import simulate_waterline as sim  # noqa: E402
from nirmaldhara import waterline  # noqa: E402

TOLERANCE_ROWS = 5          # 3 cm at the simulation's scale


def scene(condition, line, seed=1):
    return sim.render(np.random.default_rng(seed), condition, line)


@pytest.mark.parametrize("condition", ["clear", "murky", "shadow", "tide mark", "vehicle passing"])
@pytest.mark.parametrize("line", [70, 130, 190])
def test_the_line_is_found_within_three_centimetres_in_daylight(condition, line):
    frames, reference, _ = scene(condition, line)
    result = waterline.locate(frames, reference)
    assert result.found and abs(result.row - line) <= TOLERANCE_ROWS, (result.row, result.reason)
    assert result.low <= result.row <= result.high


def test_a_dry_strip_is_reported_dry_not_given_a_line():
    for seed in range(6):
        frames, reference, _ = sim.render(np.random.default_rng(seed), "clear", None)
        result = waterline.locate(frames, reference)
        assert not result.found and result.reason == "dry", seed


def test_a_shadow_edge_is_not_mistaken_for_the_water():
    # The shadow darkens everything below a row well above the water. Brightness alone would stop there.
    rng = np.random.default_rng(4)
    frames, reference, _ = sim.render(rng, "shadow", 200)
    assert abs(waterline.locate(frames, reference).row - 200) <= TOLERANCE_ROWS


def test_a_blocked_view_is_refused_when_the_dry_part_no_longer_matches():
    frames, reference, _ = scene("clear", 150)
    blocked = frames.copy()
    blocked[:] = np.random.default_rng(2).uniform(40, 90, size=blocked.shape)      # something in front of everything
    result = waterline.locate(blocked, reference)
    assert not result.found


def test_the_interval_widens_when_the_picture_is_worse():
    clear = waterline.locate(*scene("clear", 130)[:2])
    night = waterline.locate(*scene("storm at night", 130)[:2])
    assert clear.found
    assert (not night.found) or (night.high - night.low) >= (clear.high - clear.low)


def test_tracking_holds_the_line_through_a_reading_that_saw_nothing():
    frames, reference, obj = scene("clear", 120)
    good = waterline.locate(frames, reference)
    nothing = waterline.Waterline(False, float("nan"), 0.0, 240.0, 0.0, "occluded", np.full(240, -np.log(240)))
    out = waterline.track([good, nothing, nothing])
    assert out[-1].found and out[-1].reason == "held: occluded"
    assert abs(out[-1].row - good.row) < 1.0
    assert (out[-1].high - out[-1].low) >= (out[0].high - out[0].low)              # less sure the longer it waits


def test_tracking_reports_nothing_until_something_has_been_seen():
    nothing = waterline.Waterline(False, float("nan"), 0.0, 240.0, 0.0, "dry", np.full(240, -np.log(240)))
    assert not waterline.track([nothing, nothing])[-1].found


def test_one_wild_reading_does_not_drag_a_settled_line_far():
    rng = np.random.default_rng(8)
    frames, reference, obj = sim.render(rng, "clear", 120)
    steady = [waterline.locate(sim.render(rng, "clear", 120, obj=obj)[0], reference) for _ in range(4)]
    wild = waterline.locate(sim.render(rng, "clear", 190, obj=obj)[0], reference)
    out = waterline.track(steady + [wild])
    assert abs(out[-2].row - 120) <= TOLERANCE_ROWS
    assert abs(out[-1].row - 120) < abs(wild.row - 120)                             # pulled back toward what was known


def test_rows_become_centimetres_from_the_base_and_never_negative():
    assert waterline.depth_cm(row=200, base_row=240, cm_per_row=0.6) == pytest.approx(24.0)
    assert waterline.depth_cm(row=250, base_row=240, cm_per_row=0.6) == 0.0


def test_a_single_photo_uses_the_weaker_model_and_says_so_in_the_module():
    frames, _, _ = scene("murky", 130)
    result = waterline.locate(frames[0])
    assert result.found and abs(result.row - 130) <= TOLERANCE_ROWS                # the easy case it can do
    assert "easily" in waterline.__doc__ and "not been" in waterline.__doc__


def test_the_report_is_labelled_simulated_and_lists_what_fails():
    text = sim.OUT.read_text("utf-8")
    assert text.splitlines()[2].startswith("**SIMULATED.")
    for must_say in ("vehicle parked", "night", "One photo", "has not been"):
        assert must_say in text, must_say
    for name in ("README.md", "docs/submission-writeup.md", "docs/video-script.md"):
        assert "waterline-simulation" not in (ROOT / name).read_text("utf-8"), name
