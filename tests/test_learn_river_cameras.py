"""scripts/learn_river_cameras.py: how the learnt gauge is judged on the real flood, and what its report may say.

The pictures are not in the repository, so the test itself is not run here. These check that a gauge is
never judged on a day it learnt from, how its answers are counted, and that the report says what it is.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import learn_river_cameras as learn  # noqa: E402

DAYS = np.array([1121] * 3 + [1122] * 3 + [1123] * 2 + [1124] * 3 + [1125] * 2 + [1130] * 2 + [1201] * 2)


@pytest.mark.parametrize("way", learn.WAYS)
def test_a_gauge_is_never_judged_on_a_day_it_learnt_from(way):
    folds = learn.folds(way, DAYS)
    assert folds
    for seen, unseen in folds:
        assert unseen.any() and not (seen & unseen).any()
        assert not set(DAYS[seen].tolist()) & set(DAYS[unseen].tolist())


def test_each_day_is_left_out_once_and_all_the_others_are_learnt_from():
    folds = learn.folds("each day left out", DAYS)
    assert len(folds) == 7
    assert np.array([unseen for _, unseen in folds]).sum(axis=0).tolist() == [1] * len(DAYS)
    assert all((seen == ~unseen).all() for seen, unseen in folds)


def test_half_the_days_are_the_odd_and_the_even_dates_as_they_were_for_the_detector():
    (even, odd), (odd_again, even_again) = learn.folds("half the days", DAYS)
    assert set(DAYS[even].tolist()) == {1122, 1124, 1130} and set(DAYS[odd].tolist()) == {1121, 1123, 1125, 1201}
    assert (even == even_again).all() and (odd == odd_again).all()


def test_earlier_days_only_waits_for_four_days_and_never_looks_ahead():
    folds = learn.folds("earlier days only", DAYS)
    assert [int(DAYS[unseen][0]) for _, unseen in folds] == [1125, 1130, 1201]
    for seen, unseen in folds:
        assert DAYS[seen].max() < DAYS[unseen].min()


def row(reason, level, read, doubt=0.1):
    return {"index": 0, "level": level, "doubt": doubt, "reason": reason, "found": reason == "ok", "read": read, "guess": 11.0, "inside": None}


def test_a_floor_or_a_ceiling_is_wrong_only_when_the_level_is_past_it_by_more_than_its_own_error():
    assert not learn.wrong_side(row("above what was learnt", 12.5, 12.0))
    assert not learn.wrong_side(row("above what was learnt", 11.95, 12.0))          # under the floor, but within the level's error
    assert learn.wrong_side(row("above what was learnt", 11.7, 12.0))
    assert not learn.wrong_side(row("below what was learnt", 10.0, 10.5))
    assert learn.wrong_side(row("below what was learnt", 10.9, 10.5))
    assert not learn.wrong_side(row("ok", 10.0, 12.0)) and not learn.wrong_side(row("unreadable", 10.0, float("nan")))


def test_levels_floors_and_no_answers_are_counted_apart():
    rows = [row("ok", 11.0, 11.1), row("ok", 11.5, 11.2), row("above what was learnt", 12.5, 12.0),
            row("below what was learnt", 10.9, 10.5), row("unreadable", 11.0, float("nan")),
            row("too few days to learn from", 11.0, float("nan"))]
    s = learn.score(rows)
    assert (s["pictures"], s["found"], s["bounds"], s["wrong"], s["unreadable"], s["too_few"]) == (6, 2, 2, 1, 1, 1)
    assert np.allclose(s["errors"], [0.1, 0.3]) and np.allclose(s["guesses"], [0.0, 0.5])       # only where a level was given
    line = learn.line("a camera", s)
    assert "| 6 | 2 (33%) | 20 cm |" in line and "| 2 (1 wrong) | 2 |" in line


def test_with_too_few_days_nothing_is_learnt_and_that_is_what_is_reported():
    pictures = np.zeros((6, 16, 16, 3), dtype=np.uint8)
    days = np.array([1125, 1125, 1126, 1126, 1127, 1127])
    out = learn.read_unseen(pictures, np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0]), days, np.full(6, 0.1), "each day left out")
    assert len(out) == 6 and all(r["reason"] == "too few days to learn from" and not r["found"] for r in out)


def test_one_camera_built_the_gauge_and_the_other_three_were_run_once():
    assert learn.CAMERAS["Tewkesbury"] == "used to build the gauge"
    assert [learn.CAMERAS[name] for name in ("Strensham", "DiglisLock", "Evesham")] == ["run once, after the gauge was fixed"] * 3
    assert learn.LEVELS == learn.river.LEVELS and learn.DATA == learn.river.DATA             # the same data as the detector's test


def test_the_script_reads_files_and_nothing_else():
    source = (ROOT / "scripts" / "learn_river_cameras.py").read_text("utf-8")
    for outside in ("urllib", "requests", "boto3", "subprocess", "http"):
        assert outside not in source.replace("https://", "").replace("doi:", ""), outside


def test_the_report_says_which_cameras_were_run_once_and_what_was_changed_after():
    report = (ROOT / "docs" / "gauge-river.md").read_text("utf-8")
    assert report.splitlines()[2].startswith("**Real fixed cameras, a real flood, measured water levels.**")
    flat = " ".join(report.split())                                          # a sentence may be broken across lines
    for must_say in ("Tewkesbury was used to build the gauge", "were run once, after `gauge.py` had been fixed",
                     "One thing was changed after that run", "34 of its 67", "It gave a level for 4 pictures in 10",
                     "Diglis Lock: nothing", "Evesham: worse than not looking", "Learning only from earlier days",
                     "It cannot be used at any of the nine sites", "Not a street, and not Hyderabad",
                     "Not independent levels", "Not a second flood", "not a reading to close a road on"):
        assert must_say in flat, must_say
    for way in learn.WAYS:
        assert f"## Learning from {way}" in report
    for name in ("docs/submission-writeup.md", "docs/video-script.md"):
        assert "gauge-river" not in (ROOT / name).read_text("utf-8"), name
