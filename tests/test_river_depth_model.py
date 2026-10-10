"""scripts/river_depth_model.py: how the depth model is judged on the real flood, and what its report may say.

The pictures are not in the repository, so the test itself is not run here. These check how the
strips' readings become witnesses' reports and moments, on made rows, and that the report says what it is.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import river_depth_model as rdm  # noqa: E402

DAYS = (21, 22, 23, 24, 25, 26, 27, 28)
LEVEL = {day: 10.0 + 0.25 * n for n, day in enumerate(DAYS)}


def strip(slope, seed, quiet=()):
    rng = np.random.default_rng(seed)
    out = {}
    for day in DAYS:
        for hour in (9, 10, 11, 12):
            key = (11, day, hour)
            found = day not in quiet
            out[key] = {"day": (11, day), "hour": hour, "level": LEVEL[day], "std": 0.05, "found": found,
                        "row": float(260 - slope * (LEVEL[day] - 10.0) + rng.normal(0, 1.5)) if found else None,
                        "reason": "ok" if found else "occluded"}
    return out


def test_a_strips_reading_becomes_a_line_dry_or_neither():
    assert rdm.said({"found": True, "row": 91.5, "reason": "ok"}) == ("line", 91.5)
    assert rdm.said({"found": False, "row": None, "reason": "dry"}) == ("dry", None)
    assert rdm.said({"found": False, "row": None, "reason": "occluded"}) == ("other", None)
    assert rdm.said({"found": False, "row": None}) == ("other", None)             # rows kept before reasons were


def test_moments_run_in_order_of_time_on_one_clock_across_the_end_of_the_month():
    assert rdm.clock((12, 1, 7)) - rdm.clock((11, 30, 16)) == 15.0               # 4 pm on the 30th to 7 am on the 1st
    readings = {"A": strip(100.0, 1), "B": strip(60.0, 2)}
    del readings["B"][(11, 23, 10)]                                               # one strip missed a picture
    keys, levels, days, hours, reports = rdm.moments_of(readings)
    assert len(keys) == 32 and (np.diff(hours) > 0).all() and list(days[:4]) == [1121] * 4
    assert reports["B"][keys.index((11, 23, 10))] == ("other", None) and reports["A"][0][0] == "line"
    assert levels[keys.index((11, 25, 9))] == LEVEL[25]


def test_every_way_of_reading_is_judged_on_the_half_of_the_days_not_learnt_from(monkeypatch):
    monkeypatch.setitem(rdm.STRIPS, "made", {"role": "made", "strips": {n: ((0, 0, 108, 840), False, n) for n in "ABC"}})
    readings = {"A": strip(100.0, 1), "B": strip(60.0, 2), "C": strip(140.0, 3, quiet={27, 28})}
    result = rdm.one_camera("made", readings)
    assert set(result["ways"]) == {"one strip", "strips joined", "the model, each moment", "the model, through time"}
    for way in ("the model, each moment", "the model, through time"):
        rows = result["ways"][way]
        assert len(rows) == 32                                                    # every picture, each read by the other half
        assert np.median([abs(read - measured) for measured, read, _, _ in rows]) < 0.2
    assert len(result["learnt"]) == 2 and all(set(m.witnesses) == {"A", "B", "C"} for m in result["learnt"])
    table = rdm.report({"made": result})
    assert "| **The model, through time** | 32 of 32 |" in table and "What the model learnt about each strip" in table


def test_the_strips_were_fixed_in_the_file_and_one_camera_is_marked_as_run_once():
    assert rdm.STRIPS["Strensham"]["role"] == "run once, with the strips and the model fixed beforehand"
    assert rdm.STRIPS["Tewkesbury"]["role"] == "used to build the model"
    assert len(rdm.STRIPS["Strensham"]["strips"]) == 7 and len(rdm.STRIPS["Tewkesbury"]["strips"]) == 5
    for camera, entry in rdm.STRIPS.items():
        assert entry["strips"]["A"][0] == rdm.river.CAMERAS[camera]["box"]                      # the first strip is the one used before
        for box, _, what in entry["strips"].values():
            left, top, right, bottom = box
            assert right - left == 108 and 0 <= left and right <= 2048 and 0 <= top < bottom <= 1536 and what


def test_the_script_reads_files_and_nothing_else():
    source = (ROOT / "scripts" / "river_depth_model.py").read_text("utf-8")
    for outside in ("urllib", "requests", "boto3", "subprocess", "http"):
        assert outside not in source.replace("https://", "").replace("doi:", ""), outside


def test_the_report_says_which_camera_is_the_test_what_was_gained_and_what_was_taken_out():
    report = (ROOT / "docs" / "depth-model-river.md").read_text("utf-8")
    assert report.splitlines()[2].startswith("**Real fixed cameras, a real flood, measured water levels.**")
    flat = " ".join(report.split())
    for must_say in ("Strensham is the test", "Tewkesbury was used to build the model", "One thing was tried after the run and taken out again",
                     "That is a small gain", "Seven surfaces are not seven opinions", "Most of the tail is water beyond what it had learnt from",
                     "The range is too narrow", "The limit is not the arithmetic of joining", "Not several cameras",
                     "Not a street, and not Hyderabad", "still not a reading to close a road on"):
        assert must_say in flat, must_say
    for name in ("docs/submission-writeup.md", "docs/video-script.md"):
        assert "depth-model-river" not in (ROOT / name).read_text("utf-8"), name
    readme = " ".join((ROOT / "README.md").read_text("utf-8").split())
    assert "docs/depth-model-river.md" in readme and "A small gain" in readme and "Run on rendered scenes only" in readme
