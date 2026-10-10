"""nirmaldhara/waterline.py: finding the water on a fixed camera's strip, and saying when it cannot.

Small rendered scenes with a known line. The full measurements are scripts/simulate_waterline.py
(rendered) and scripts/real_strip_test.py (real video), whose results these tests do not repeat.
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

CLOSE = 5                   # rows: 3 cm at the simulation's scale


def scene(condition, line, seed=1):
    return sim.render(np.random.default_rng(seed), condition, line)


@pytest.mark.parametrize("condition", ["clear", "murky", "rain", "shadow", "tide mark", "vehicle passing", "night"])
@pytest.mark.parametrize("line", [90, 140, 190])
def test_the_line_is_found_within_three_centimetres(condition, line):
    frames, reference, _ = scene(condition, line)
    result = waterline.locate(frames, reference)
    assert result.found and abs(result.row - line) <= CLOSE, (result.row, result.reason)
    assert result.low <= result.row <= result.high


def test_a_dry_strip_is_reported_dry_not_given_a_line():
    for seed in range(6):
        for condition in ("clear", "rain", "night"):
            frames, reference, _ = sim.render(np.random.default_rng(seed), condition, None)
            result = waterline.locate(frames, reference)
            assert not result.found and result.reason == "dry", (seed, condition, result.reason)


def test_a_shadow_edge_is_not_mistaken_for_the_water():
    # The shadow darkens everything below a row well above the water. Brightness alone would stop there.
    for seed in (4, 5, 6):
        frames, reference, made = sim.render(np.random.default_rng(seed), "shadow", 200)
        result = waterline.locate(frames, reference)
        assert result.found and abs(result.row - 200) <= CLOSE, (seed, made["shadow_row"], result.row)


def test_a_parked_vehicle_is_reported_as_blocking_the_view_not_as_water():
    blocked = 0
    for seed in range(8):
        frames, reference, made = sim.render(np.random.default_rng(seed), "vehicle parked", 200)
        result = waterline.locate(frames, reference)
        assert made["parked_top"] < 200                               # the vehicle hides the line
        assert not result.found or abs(result.row - 200) <= CLOSE     # never a line at the vehicle's roof
        blocked += result.reason == "occluded"
    assert blocked >= 6


def test_still_water_that_mirrors_the_surface_is_water_and_not_an_object():
    found = 0
    for seed in range(8):
        frames, reference, _ = sim.render(np.random.default_rng(seed), "mirror", 150)
        result = waterline.locate(frames, reference)
        found += result.found and abs(result.row - 150) <= CLOSE
    assert found >= 6


def test_a_view_that_no_longer_shows_the_surface_is_refused():
    frames, reference, _ = scene("clear", 150)
    other = np.random.default_rng(2).uniform(40, 90, size=frames.shape[1:])     # something in front of everything
    result = waterline.locate(np.clip(other + np.random.default_rng(3).normal(0, 3, frames.shape), 0, 255), reference)
    assert not result.found and result.reason in ("occluded", "unreadable")


def test_a_reading_says_what_it_rested_on_when_asked():
    frames, reference, _ = scene("clear", 150)
    trace = {}
    waterline.locate(frames, reference, trace=trace)
    assert {"level", "predicted", "q", "expected", "flicker", "colour", "noise_row", "blur", "ends"} <= set(trace)
    assert len(trace["level"]) == frames.shape[1]


def test_brightness_is_fitted_as_a_gain_unless_an_offset_earns_its_place():
    rng = np.random.default_rng(0)
    x = rng.uniform(0.2, 0.9, 2000)
    a, b = waterline._fit(x, 0.5 * x + rng.normal(0, 0.01, 2000))
    assert b == 0.0 and abs(a - 0.5) < 0.01                    # no haze: a gain alone
    a, b = waterline._fit(x, 0.5 * x + 0.2 + rng.normal(0, 0.01, 2000))
    assert abs(a - 0.5) < 0.02 and abs(b - 0.2) < 0.02         # haze: the offset is clearly needed


def test_the_fit_keeps_the_few_pixels_that_carry_the_pattern():
    # A gauge: nine pixels in ten are white, the marks are the rest. A fit that drops what it misses loses them.
    x = np.where(np.arange(1000) % 10 == 0, 0.2, 0.8)
    a, b = waterline._fit(x, 0.7 * x)
    assert abs(a - 0.7) < 1e-6 and b == 0.0


def test_a_box_blur_averages_and_a_shift_repeats_the_edge():
    image = np.arange(20.0).reshape(5, 4)
    assert waterline._box(image, 3, 1)[2, 0] == pytest.approx((4 + 8 + 12) / 3)
    assert waterline._box(image, 1, 1) is image
    moved = waterline._shift(image, 1, -1)
    assert moved[1, 0] == image[0, 1] and moved[0, 0] == image[0, 1] and moved[2, 3] == image[1, 3]


def test_trembling_frames_are_lined_up_before_anything_is_measured():
    frames, _, _ = scene("clear", 150)
    moves = [(0, 0), (1, 0), (-1, 1), (0, -1), (1, 1), (-1, -1)]
    shaken = np.array([np.roll(np.roll(frame, dy, axis=0), dx, axis=1) for frame, (dy, dx) in zip(frames, moves)]).astype(np.float32)
    spread = lambda stack: float(np.abs(stack.mean(axis=-1) - np.median(stack.mean(axis=-1), axis=0))[:, 4:48].mean())   # noqa: E731
    assert spread(waterline.stabilise(shaken)) < 0.6 * spread(shaken)


def test_tracking_holds_the_line_through_a_reading_that_saw_nothing():
    frames, reference, _ = scene("clear", 120)
    good = waterline.locate(frames, reference)
    blind = waterline.Waterline(False, float("nan"), 0.0, 240.0, 0.0, "occluded", np.full(240, -np.log(240)))
    out = waterline.track([good, blind, blind])
    assert out[-1].found and out[-1].reason == "held: occluded"
    assert abs(out[-1].row - good.row) < 1.0
    assert out[-1].spread >= out[0].spread                       # less sure the longer it waits


def test_tracking_reports_nothing_until_something_has_been_seen_and_follows_the_water_away():
    frames, reference, _ = scene("clear", 120)
    wet = waterline.locate(frames, reference)
    dry = waterline.Waterline(False, float("nan"), 0.0, 240.0, 0.0, "dry", np.full(240, -np.log(240)), p_dry=1.0)
    blind = waterline.Waterline(False, float("nan"), 0.0, 240.0, 0.0, "occluded", np.full(240, -np.log(240)))
    assert not waterline.track([blind, blind])[-1].found
    assert not waterline.track([wet, dry, dry, dry])[-1].found   # the strip has gone dry: the old line is dropped


def test_one_wild_reading_does_not_drag_a_settled_line_far():
    rng = np.random.default_rng(8)
    _, reference, made = sim.render(rng, "clear", 120)
    steady = [waterline.locate(sim.render_frames(rng, made, 120), reference) for _ in range(4)]
    wild = waterline.locate(sim.render_frames(rng, made, 190), reference)
    out = waterline.track(steady + [wild])
    assert abs(out[-2].row - 120) <= CLOSE
    assert abs(out[-1].row - 120) < abs(wild.row - 120)          # pulled back toward what was known


def test_rows_become_centimetres_from_the_base_and_never_negative():
    assert waterline.depth_cm(row=200, base_row=240, cm_per_row=0.6) == pytest.approx(24.0)
    assert waterline.depth_cm(row=250, base_row=240, cm_per_row=0.6) == 0.0


def test_the_interval_widths_are_the_calibrated_ones_and_the_module_says_where_they_came_from():
    source = (ROOT / "src" / "nirmaldhara" / "waterline.py").read_text("utf-8")
    assert set(waterline.QUANTILE) == {"normal", "soft", "low light", "tracked"}
    assert "--calibrate" in source and "On real pictures these have to be fitted again" in source
    assert "tens of centimetres" in waterline.__doc__ and "It has not been measured on a street" in waterline.__doc__


def test_the_reports_say_what_they_are_and_are_kept_out_of_the_submission():
    rendered, real = sim.OUT.read_text("utf-8"), (ROOT / "docs" / "waterline-real.md").read_text("utf-8")
    assert rendered.splitlines()[2].startswith("**SIMULATED.")
    assert real.splitlines()[2].startswith("**Real video, but not a real measurement of depth.**")
    for must_say in ("held out", "parked at night", "One photo", "first look", "tens of centimetres"):
        assert must_say in rendered, must_say
    for must_say in ("hand-held", "marked by eye", "not a clean test", "No depth"):
        assert must_say in real, must_say
    for name in ("README.md", "docs/submission-writeup.md", "docs/video-script.md"):
        text = (ROOT / name).read_text("utf-8")
        assert "waterline-simulation" not in text and "waterline-real" not in text, name
