"""nirmaldhara/depthmodel.py: one water level from several witnesses, followed through time.

Made witnesses with known faults: one sharp, one blunt, one that goes blind above a level, one that is
often wild, one that goes quiet. What the model does on a real flood is measured by
scripts/river_depth_model.py, whose results these tests do not repeat.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import depthmodel as dm  # noqa: E402

BASE = [10.0, 10.3, 10.9, 11.4, 11.8, 12.0, 11.9, 11.6, 11.2, 10.8, 10.4, 10.1, 10.6, 11.1, 11.7, 11.3]
HOURS = range(8, 16)
ROWS = 280
# name: (rows per metre, row at 10 m, blind above, wild share, quiet above, camera)
FIVE = {
    "sharp": (100.0, 250.0, None, 0.05, None, "one"),
    "blunt": (25.0, 200.0, None, 0.05, None, "one"),
    "blind": (120.0, 240.0, 11.0, 0.05, None, "one"),
    "wild": (100.0, 260.0, None, 0.30, None, "one"),
    "quiet": (25.0, 190.0, None, 0.05, 11.5, "one"),
}
UNSEEN = [3, 6, 9, 12, 14]


def site(seed=0, kinds=FIVE, within=2.0, between=3.0, shared_cm=0.0):
    """(levels, reports, rows, days, hours, cameras). Each day's light moves every witness by its own
    amount, and every witness of one camera by a common amount worth `shared_cm` of level."""
    rng = np.random.default_rng(seed)
    levels, day_of, hour_of = [], [], []
    reports = {name: [] for name in kinds}
    for d in range(len(BASE)):
        common = {camera: rng.normal(0, shared_cm) for camera in sorted({k[5] for k in kinds.values()})}
        own = {name: rng.normal(0, between) for name in kinds}
        for h in HOURS:
            level = BASE[d] + 0.02 * (h - 12) * (1 if d % 2 else -1)
            levels.append(level)
            day_of.append(d)
            hour_of.append(d * 24 + h)
            for name, (slope, zero, blind, wild, quiet, camera) in kinds.items():
                if quiet is not None and level > quiet and rng.random() < 0.9:
                    reports[name].append(("other", None))
                    continue
                row = zero - slope * ((min(level, blind) if blind is not None else level) - 10.0)
                row += slope * common[camera] / 100.0 + own[name] + rng.normal(0, within)
                reports[name].append(("line", float(np.clip(rng.uniform(0, ROWS) if rng.random() < wild else row, 0, ROWS - 1))))
    return (np.array(levels), reports, {name: ROWS for name in kinds}, np.array(day_of), np.array(hour_of, float),
            {name: k[5] for name, k in kinds.items()})


def halves(data, unseen=UNSEEN):
    levels, reports, rows, days, hours, cameras = data
    out = []
    for mask in (~np.isin(days, unseen), np.isin(days, unseen)):
        out.append((levels[mask], {n: [s for s, k in zip(r, mask) if k] for n, r in reports.items()}, rows, days[mask], hours[mask], cameras))
    return out


def errors(readings, levels):
    return np.array([abs(r.level - level) for r, level in zip(readings, levels)])


def middle_half(model, reading):
    """How wide the middle half of the belief is: small when the witnesses pin the level down."""
    running = np.cumsum(reading.belief)
    return float(model.grid[np.searchsorted(running, 0.75)] - model.grid[np.searchsorted(running, 0.25)])


@pytest.fixture(scope="module")
def taught():
    seen, unseen = halves(site(seed=1))
    return dm.learn(*seen), unseen


def test_each_witness_is_learnt_for_what_it_is(taught):
    model, _ = taught
    w = model.witnesses
    assert set(w) == set(FIVE)
    at = lambda level: int(np.argmin(np.abs(model.grid - level)))                 # noqa: E731
    assert abs(w["sharp"].row[at(11.0)] - 150.0) < 8 and abs(w["blunt"].row[at(11.0)] - 175.0) < 8      # the curves
    span = slice(at(10.2), at(11.8))
    assert w["sharp"].sharpness()[span].mean() > 2 * w["blunt"].sharpness()[span].mean()             # sharp, and blunt
    assert w["blind"].sharpness()[at(11.6):at(11.9)].max() < 0.2 * w["blind"].sharpness()[at(10.3):at(10.8)].max()   # blind above 11 m
    assert w["wild"].wild > 2 * w["sharp"].wild                                                    # the wild one is known to be
    assert w["quiet"].says[at(11.9), 2] > 0.6 and w["quiet"].says[at(10.3), 0] > 0.6               # and when the quiet one goes quiet
    assert all(x.between > 0 and x.within > 0 and x.spread >= dm.LEAST_SPREAD for x in w.values())


def test_together_they_are_closer_than_the_best_of_them_and_far_closer_than_the_rest(taught):
    model, (levels, reports, _, _, _, _) = taught
    together = errors([dm.believe(model, {n: reports[n][i] for n in reports}) for i in range(len(levels))], levels)
    alone = {n: errors([dm.believe(model, {n: reports[n][i]}) for i in range(len(levels))], levels) for n in reports}
    assert np.median(together) <= np.median(alone["sharp"]) + 0.005
    assert np.percentile(together, 90) < np.percentile(alone["wild"], 90) / 3      # the wild one's tail is gone
    assert np.median(together) < np.median(alone["blunt"]) / 3


def test_a_blind_witness_says_nothing_where_it_is_blind_and_does_not_vote_for_where_it_points():
    seen, unseen = halves(site(seed=4, kinds={k: FIVE[k] for k in ("blunt", "blind")}))
    model = dm.learn(*seen)
    high = dm.believe(model, {"blind": ("line", 120.0)})                           # its row for every level above 11 m
    assert middle_half(model, high) > 0.4 and high.level > 11.0                    # so all it says is "above 11 m"
    low = dm.believe(model, {"blind": ("line", 180.0)})                            # 10.5 m, where it can see
    assert abs(low.level - 10.5) < 0.1 and middle_half(model, low) < 0.15
    levels, reports = unseen[0], unseen[1]
    flooded = [i for i, level in enumerate(levels) if level > 11.3]
    both = errors([dm.believe(model, {n: reports[n][i] for n in reports}) for i in flooded], levels[flooded])
    blunt = errors([dm.believe(model, {"blunt": reports["blunt"][i]}) for i in flooded], levels[flooded])
    assert np.median(both) <= np.median(blunt) + 0.03                              # the blind one has not dragged it to 11 m


def test_a_wild_report_is_outvoted_and_never_vetoes(taught):
    model, _ = taught
    steady = {"sharp": ("line", 150.0), "blunt": ("line", 175.0), "blind": ("line", 120.0)}       # all three say 11.0 m
    calm = dm.believe(model, steady)
    upset = dm.believe(model, dict(steady, wild=("line", 20.0)))                                   # and one says something absurd
    assert abs(calm.level - 11.0) < 0.06 and abs(upset.level - calm.level) < 0.03
    lone = dm.believe(model, {"wild": ("line", 20.0)})
    assert np.isfinite(lone.level) and lone.belief.min() > 0                       # no level is ever ruled out by one witness


def test_a_witness_that_goes_quiet_is_saying_something_by_it(taught):
    model, _ = taught
    assert dm.believe(model, {"quiet": ("other", None)}).level > 11.4              # it goes quiet above 11.5 m
    assert dm.believe(model, {"quiet": ("line", 180.0)}).level < 11.4


def test_followed_through_time_one_wild_moment_does_not_move_the_level(taught):
    model, (levels, reports, _, _, hours, _) = taught
    day = [i for i in range(len(levels)) if 6 * 24 <= hours[i] < 7 * 24]            # one unseen day, around 11.9 m
    moments = [(hours[i], {"blunt": reports["blunt"][i]}) for i in day]
    moments[4] = (moments[4][0], {"blunt": ("line", 250.0)})                       # at one hour the only witness says 8 m
    through = dm.follow(model, moments)
    alone = dm.believe(model, moments[4][1])
    assert abs(alone.level - levels[day[4]]) > 0.5 and alone.informed < 0.3        # by itself that moment knows nothing
    assert abs(through[4].level - levels[day[4]]) < 0.4                            # among its neighbours it is outvoted
    assert through[4].belief.sum() == pytest.approx(1.0) and len(through) == len(day)


def test_the_range_is_stretched_until_it_would_have_held_nine_in_ten_of_the_days_left_out(taught):
    model, (levels, reports, _, _, hours, _) = taught
    assert model.stretch >= 1.0 and model.stretch_through >= 1.0 and 9 * 8 <= len(model.left_out) <= 11 * 8
    held = np.mean([low <= measured <= high for measured, _, low, high in model.left_out])
    assert held >= 0.85
    through = dm.follow(model, [(hours[i], {n: reports[n][i] for n in reports}) for i in range(len(levels))])
    assert np.mean([r.low <= level <= r.high for r, level in zip(through, levels)]) > 0.6          # and on days it never saw


def test_past_the_levels_it_learnt_from_it_does_not_know_it_is_there():
    # The limit, stated as a test so that it cannot be forgotten: taught only between 10.5 and 11.5 m, it
    # reads water at 12 m as something inside what it was taught. It gives no floor and raises no flag.
    kinds = {k: FIVE[k] for k in ("sharp", "blunt")}
    levels, reports, rows, days, hours, cameras = site(seed=6, kinds=kinds)
    middling = (levels > 10.5) & (levels < 11.5)
    model = dm.learn(levels[middling], {n: [s for s, k in zip(r, middling) if k] for n, r in reports.items()}, rows, days[middling], hours[middling], cameras)
    highest = float(levels[middling].max())
    beyond = [i for i in range(len(levels)) if levels[i] > highest + 0.4]
    read = [dm.believe(model, {n: reports[n][i] for n in reports}).level for i in beyond]
    assert len(beyond) >= 8 and max(read) <= highest + dm.PAD + 1e-9
    assert min(levels[i] - r for i, r in zip(beyond, read)) > 0.2                  # every one of them read too low


def test_witnesses_that_are_wrong_together_are_counted_for_less():
    own = dm.learn(*halves(site(seed=2, shared_cm=0.0))[0])
    together = dm.learn(*halves(site(seed=2, shared_cm=25.0))[0])                  # one light pushes them all the same way
    assert together.share["one"] < own.share["one"] and together.through["one"] <= own.through["one"]
    assert together.through["one"] <= together.share["one"]                        # and hour after hour is not new evidence


def test_a_witness_that_brings_its_own_likelihood_is_used_as_far_as_it_helps():
    seen, _ = halves(site(seed=3, kinds={k: FIVE[k] for k in ("blunt", "quiet")}))
    levels = seen[0]
    grid = dm.grid_for(levels)
    rng = np.random.default_rng(0)
    good = [-0.5 * ((grid - level - rng.normal(0, 0.03)) / 0.05) ** 2 for level in levels]      # knows the level to 5 cm
    useless = [-0.5 * ((grid - rng.uniform(grid[0], grid[-1])) / 0.05) ** 2 for _ in levels]    # points anywhere
    model = dm.learn(*seen, extras={"good": good, "useless": useless})
    assert model.extras["useless"][0] <= 0.01 < 0.1 <= model.extras["good"][0]     # next to nothing, against most of what it claims
    with_it = dm.believe(model, {}, extra={"good": good[5], "useless": useless[5]})
    assert abs(with_it.level - levels[5]) < 0.1
    assert dm.believe(model, {}, extra={"good": None}).informed == pytest.approx(0.0, abs=1e-6)    # nothing said, nothing learnt


def test_too_little_to_learn_from_is_refused_and_not_guessed():
    grid = np.arange(10.0, 12.0, 0.01)
    assert dm.learn_witness("w", grid, [10.0, 10.5, 11.0], [("line", 200.0), ("line", 150.0), ("line", 100.0)], ROWS) is None
    stuck = [("line", 120.0)] * 12
    assert dm.learn_witness("w", grid, np.linspace(10, 12, 12), stuck, ROWS) is None      # always the same row: it sees nothing
    seen, _ = halves(site(seed=5, kinds={"sharp": FIVE["sharp"]}))
    model = dm.learn(seen[0][:8], {"sharp": seen[1]["sharp"][:8]}, seen[2], seen[3][:8], seen[4][:8])          # one day only
    assert model.share == {"": 1.0} and model.stretch == 1.0 and model.left_out == ()


def test_the_curve_only_ever_goes_one_way_and_a_wild_value_does_not_bend_it():
    levels = np.linspace(10, 12, 41)
    rows = 250 - 100 * (levels - 10)
    rows[20] = 5.0                                                                 # one absurd row in the middle
    at, value = dm.one_way(levels, rows)
    assert (np.diff(value) <= 1e-9).all()
    assert abs(np.interp(11.0, at, value) - 150.0) < 6
    up_at, up_value = dm.one_way(levels, 100 * (levels - 10))
    assert (np.diff(up_value) >= -1e-9).all()


def test_the_module_says_what_it_learns_from_and_that_nothing_calls_it():
    for must_say in ("a blind witness says nothing", "learns from measured levels, which no site in this project\nhas yet",
                     "nothing calls it", "Only the past is used"):
        assert must_say in dm.__doc__, must_say


def test_an_answer_becomes_the_reading_the_site_engine_takes(taught):
    from nirmaldhara import state
    from nirmaldhara.bands import passability
    model, _ = taught
    steady = {"sharp": ("line", 150.0), "blunt": ("line", 175.0)}                  # both say 11.0 m
    reading = dm.to_reading(dm.believe(model, steady), road=10.8, ts=1000.0, device="cam-1")
    assert isinstance(reading, state.Reading) and reading.source == "cctv" and reading.device == "cam-1"
    assert reading.low <= 20.0 <= reading.high and reading.high - reading.low < 40             # about 20 cm above the road
    assert 0.6 < reading.confidence <= 0.95
    site = state.apply_reading(state.Site("s"), reading)
    assert site.high == reading.high and site.state != state.CLEAR                # and the engine acts on it
    nothing = dm.to_reading(dm.believe(model, {}), road=10.8, ts=1000.0, device="cam-1")
    assert nothing.confidence == 0.0                                               # no witness looked: nothing is known
    assert "passable" not in {str(v).lower() for v in passability(nothing.low, nothing.high, nothing.confidence).values()}
    dry = dm.to_reading(dm.believe(model, {"sharp": ("line", 250.0), "blunt": ("line", 200.0)}), road=10.8, ts=1.0, device="c")
    assert dry.low == 0.0                                                          # a level below the road is no depth
