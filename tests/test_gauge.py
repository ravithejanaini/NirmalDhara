"""nirmaldhara/gauge.py: a water-level gauge learnt from one camera's pictures and their measured levels.

A made wall, three metres high, that the water climbs. What the gauge does on a real flood is measured
by scripts/learn_river_cameras.py, whose results these tests do not repeat.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import gauge  # noqa: E402

ROWS, COLUMNS, TOP = 80, 96, 3.0            # the top row of the picture is 3 m up the wall, the bottom row at 0
TAUGHT = [0.45 + 0.3 * day for day in range(8)]      # one level a day, 0.45 to 2.55 m


def wall(seed=0):
    coarse = np.random.default_rng(seed).uniform(50, 200, (ROWS // 2, COLUMNS // 2))
    return np.kron(coarse, np.ones((2, 2)))


def heights():
    return TOP * (1 - (np.arange(ROWS) + 0.5) / ROWS)


def picture(surface, level, light=1.0, seed=0, under=None):
    """The wall with everything below `level` under flat grey water, in a given light."""
    rng = np.random.default_rng(seed)
    image = surface.copy()
    wet = (heights() < level) if under is None else under
    image[wet] = 110 + rng.normal(0, 1.0, (int(wet.sum()), COLUMNS))
    image = light * image + rng.normal(0, 2.0, image.shape)
    return np.clip(np.repeat(image[:, :, None], 3, axis=2), 0, 255)


def taught(surface, levels=TAUGHT, each=5, seed=1):
    """(pictures, levels, days): `each` pictures a day, every day in its own light."""
    rng = np.random.default_rng(seed)
    pictures, measured, days = [], [], []
    for day, level in enumerate(levels):
        light = rng.uniform(0.6, 1.2)
        for shot in range(each):
            pictures.append(picture(surface, level, light * rng.uniform(0.95, 1.05), seed=1000 * day + shot))
            measured.append(level)
            days.append(day)
    return np.array(pictures), np.array(measured), np.array(days)


@pytest.fixture(scope="module")
def learnt():
    surface = wall()
    return surface, gauge.learn(*taught(surface), check=False)


@pytest.mark.parametrize("level", [1.05, 1.35, 1.5, 1.8, 2.1])
def test_a_picture_from_a_day_it_never_saw_is_read_to_within_the_gap_between_the_days_it_did(learnt, level):
    surface, g = learnt
    reading = g.read(picture(surface, level, light=0.9, seed=77))
    assert reading.found and reading.reason == "ok"
    assert abs(reading.level - level) < 0.2, reading.level
    assert reading.low <= reading.level <= reading.high


def test_between_two_days_it_was_taught_the_reading_comes_from_the_share_of_patches_under():
    surface = wall()
    levels = [0.3, 0.6, 0.9, 2.1, 2.4, 2.7]                      # nothing taught between 0.9 and 2.1
    g = gauge.learn(*taught(surface, levels), check=False)
    read = [g.read(picture(surface, level, seed=5)).level for level in (1.2, 1.5, 1.8)]
    assert read[0] < read[1] < read[2]                           # still in order across the gap
    assert all(abs(got - level) < 0.3 for got, level in zip(read, (1.2, 1.5, 1.8))), read


def test_past_what_it_has_seen_it_gives_a_floor_or_a_ceiling_and_not_a_level(learnt):
    surface, g = learnt
    lowest, highest = g.reads()
    high = g.read(picture(surface, 2.45, seed=3))
    assert not high.found and high.reason == "above what was learnt"
    assert high.low == high.level and high.high == float("inf")
    assert 1.9 <= high.level <= highest and high.level <= 2.45        # a floor inside its last step, and a true one
    low = g.read(picture(surface, 0.1, seed=4))
    assert not low.found and low.reason == "below what was learnt"
    assert low.high == low.level and low.low == float("-inf")
    assert lowest <= low.level <= 1.1 and low.level >= 0.1           # a ceiling inside its first step, and a true one


def test_a_floor_claims_no_more_than_the_picture_shows():
    # Taught 2.25 m and then 2.85 m, with nothing between. Water at 2.5 m covers some of the patches that
    # went under between those two, so it cannot be told how far past 2.25 m it is. The floor it gives
    # must not be the far end of that step.
    surface = wall()
    g = gauge.learn(*taught(surface, [0.45, 0.75, 1.05, 1.35, 1.65, 1.95, 2.25, 2.85, 2.9]), check=False)
    for level in (2.75, 2.8):
        reading = g.read(picture(surface, level, seed=3))
        if not reading.found:
            assert reading.reason == "above what was learnt" and reading.level <= level, (level, reading)


def test_when_the_water_covers_what_it_knows_the_view_by_it_refuses_and_does_not_guess(learnt):
    # The patches it recognises the view by are the ones that stayed dry in everything it learnt from.
    # With those under water too it cannot tell a flood from a cover over the lens.
    surface, g = learnt
    reading = g.read(picture(surface, 2.95, seed=3))
    assert not reading.found and reading.reason == "unreadable"


@pytest.mark.parametrize("light", [0.5, 0.8, 1.25])
def test_brighter_or_dimmer_light_does_not_move_the_reading(learnt, light):
    surface, g = learnt
    reading = g.read(picture(surface, 1.5, light=light, seed=9))
    assert reading.found and abs(reading.level - 1.5) < 0.2, (light, reading)


def test_what_is_kept_about_a_patch_ignores_how_brightly_it_is_lit():
    surface = wall()
    dry = surface.astype(np.float32)
    full, dim = gauge.describe(picture(surface, 0.0, 1.0), dry), gauge.describe(picture(surface, 0.0, 0.5), dry)
    assert full.shape == ((ROWS - gauge.PATCH) // gauge.STEP + 1, (COLUMNS - gauge.PATCH) // gauge.STEP + 1, 2)
    assert np.median(full[..., 0]) > 0.95 and np.median(dim[..., 0]) > 0.9           # the same pattern, half as bright
    assert np.median(np.abs(full[..., 1] - dim[..., 1])) < 0.1                         # and the same contrast
    water = gauge.describe(picture(surface, TOP + 1, 1.0), dry)
    assert abs(np.median(water[..., 0])) < 0.2 and np.median(water[..., 1]) < np.median(full[..., 1]) - 1.0


def test_a_step_is_put_between_days_and_never_inside_one():
    days = np.repeat(np.arange(6), 4)
    levels = np.repeat([1.0, 1.2, 1.4, 1.6, 1.8, 2.0], 4) + np.tile([0.0, 0.01, 0.02, 0.03], 6)
    order, starts, middles = gauge._in_days(levels, days)
    assert list(starts) == [4, 8, 12, 16, 20] and np.allclose(middles, [1.015, 1.215, 1.415, 1.615, 1.815, 2.015])
    by_level = np.where(np.arange(24) >= 12, 0.1, 0.9)                 # changes when the level passes 1.5 m
    by_hour = np.tile([0.9, 0.9, 0.1, 0.1], 6)                         # changes every afternoon, whatever the level
    described = np.stack([np.stack([by_level, np.full(24, -1.0)], axis=1), np.stack([by_hour, np.full(24, -1.0)], axis=1)], axis=1)
    gain, first_wet = gauge._steps(described.astype(np.float32), order, starts)
    assert gain[0] > gauge.GAIN and first_wet[0] == 3                  # the fourth day is the first wet one
    assert gain[1] < 0.1 * gauge.GAIN                                  # no cut between days explains the afternoons


def test_one_side_of_a_step_must_hold_more_than_one_day():
    surface = wall()
    g = gauge.learn(*taught(surface, [0.5, 1.0, 1.5, 2.0, 2.5]), check=False)
    lowest, highest = g.reads()
    assert lowest >= 1.0 and highest <= 2.0          # the lowest and highest day alone cannot make a step
    few = gauge.learn(*taught(surface, [0.5, 1.5, 2.5]), check=False)
    assert few.reads() is None and len(few.where) == 0
    assert few.read(picture(surface, 1.5)).reason == "unreadable"


def test_a_part_of_the_view_that_changed_on_one_day_only_is_not_taken_for_water():
    surface = wall()
    pictures, levels, days = taught(surface)
    corner = (slice(0, 16), slice(0, 24))                                # high on the wall, never under
    for i in np.flatnonzero(days == 4):
        pictures[i][corner] = 90                                         # something stood in front of it that day
    g = gauge.learn(pictures, levels, days, check=False)
    down, across = np.unravel_index(g.where, g.shape)
    in_corner = (down * gauge.STEP + gauge.PATCH <= 16) & (across * gauge.STEP + gauge.PATCH <= 24)
    assert not in_corner.any()


def test_a_view_that_is_not_this_cameras_is_unreadable(learnt):
    _, g = learnt
    assert len(g.anchors) > 0 and g.anchor_like > 0.8
    other = g.read(picture(wall(seed=99), 1.5))
    assert not other.found and other.reason == "unreadable"
    assert g.read(np.zeros((10, 10, 3))).reason == "unreadable"         # nor a picture of another size


def test_a_picture_that_no_level_explains_is_unreadable(learnt):
    surface, g = learnt
    upside_down = (heights() > 1.3) & (heights() < 2.4)                 # wet above, dry below: water does not do that
    reading = g.read(picture(surface, 0.0, under=upside_down, seed=6))
    assert not reading.found and reading.reason == "unreadable" and reading.explained < gauge.EXPLAINED


def test_how_far_out_it_is_comes_from_days_it_was_made_to_do_without():
    surface = wall()
    g = gauge.learn(*taught(surface, each=4), doubt=0.05, check=True)
    assert len(g.left_out) >= 10 and np.isfinite(g.error)
    assert g.error == pytest.approx(np.percentile([abs(read - measured) for measured, read in g.left_out], 90))
    reading = g.read(picture(surface, 1.5, seed=8))
    assert reading.high - reading.level >= g.error - 1e-9 and reading.level - reading.low >= g.error - 1e-9


def test_a_step_is_never_taken_as_known_more_closely_than_the_levels_were_measured():
    surface = wall()
    sharp = gauge.learn(*taught(surface), doubt=0.0, check=False)
    blunt = gauge.learn(*taught(surface), doubt=0.2, check=False)
    assert np.allclose(sharp.above - sharp.below, 0.3)                  # the gap between one day's level and the next
    assert np.allclose(blunt.above - blunt.below, 0.7)                  # and 0.2 m more on each side


def test_a_gauge_is_kept_in_one_file_and_reads_the_same_when_brought_back(learnt, tmp_path):
    surface, g = learnt
    g.save(tmp_path / "camera.npz")
    again = gauge.Gauge.load(tmp_path / "camera.npz")
    shot = picture(surface, 1.7, seed=12)
    assert again.read(shot) == g.read(shot)
    assert again.shape == g.shape and again.learnt == g.learnt and again.pictures == g.pictures


def test_with_another_method_the_gauge_goes_first_and_its_floor_or_ceiling_is_kept():
    ok = gauge.Level(True, 1.5, 1.3, 1.7, "ok")
    above = gauge.Level(False, 2.4, 2.4, float("inf"), "above what was learnt")
    below = gauge.Level(False, 0.8, float("-inf"), 0.8, "below what was learnt")
    blind = gauge.Level(False, float("nan"), float("-inf"), float("inf"), "unreadable")
    assert gauge.with_fallback(ok, 9.9) == (1.5, "learnt")
    assert gauge.with_fallback(above, 2.0) == (2.4, "other, held") and gauge.with_fallback(above, 2.9) == (2.9, "other, held")
    assert gauge.with_fallback(below, 1.0) == (0.8, "other, held") and gauge.with_fallback(below, 0.3) == (0.3, "other, held")
    assert gauge.with_fallback(blind, 1.1) == (1.1, "other") and gauge.with_fallback(blind, None) == (None, None)


def test_the_module_says_what_it_needs_and_where_it_was_measured():
    for must_say in ("needs measured levels to learn from", "which no site in this project has yet",
                     "It has not been used on a street", "Brightness and\ncolour were tried and thrown out"):
        assert must_say in gauge.__doc__, must_say
