"""scripts/river_camera_test.py: how the real-flood test is scored, and what it may and may not publish.

The pictures are not in the repository, so the test itself is not run here. These check the parts
that turn the detector's rows into an error, and that the report says what it is.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import river_camera_test as river  # noqa: E402


def reading(day, row, level, std=0.05):
    return {"day": (11, day), "hour": 12, "level": level, "std": std, "found": True, "row": row, "low": row - 2, "high": row + 2, "reason": "ok"}


def test_the_levels_file_is_the_datasets_own_readings_with_its_source_and_licence():
    levels = json.loads(river.LEVELS.read_text("utf-8"))
    assert "10.17632/769cyvdznp.1" in levels["source"] and "BY-NC" in levels["licence"] and "Attribution 4.0" in levels["licence"]
    assert set(levels["cameras"]) == {"Tewkesbury", "Strensham", "DiglisLock", "Evesham"}
    counted = {name: sum(1 for r in camera["readings"] if r["level_m"] is not None and r["image"])
               for name, camera in levels["cameras"].items()}
    assert counted == {"Tewkesbury": 138, "Strensham": 114, "DiglisLock": 50, "Evesham": 46}
    for camera in levels["cameras"].values():
        for r in camera["readings"]:
            assert r["level_m"] is None or 5 < r["level_m"] < 30            # metres above datum, never a blank read as zero
            assert r["std_m"] is None or 0 < r["std_m"] <= 0.25             # the authors left out anything worse


def test_the_curve_from_row_to_level_only_ever_goes_one_way():
    rng = np.random.default_rng(0)
    rows = rng.uniform(50, 200, 60)
    for sign in (1, -1):                                                     # the level may rise or fall with the row
        levels = 10 + sign * 0.01 * rows + rng.normal(0, 0.05, 60)
        curve = river.rising_curve(rows, levels)
        fitted = np.array([float(curve(r)) for r in np.linspace(40, 210, 80)])
        steps = np.diff(fitted) * sign
        assert (steps >= -1e-9).all()
        assert abs(float(curve(125)) - (10 + sign * 1.25)) < 0.08


def test_the_error_is_measured_on_days_the_curve_did_not_see():
    # Odd days follow one relation and even days another. A curve judged on its own days would show no error.
    found = [reading(day, row, 10 + 0.01 * row + (0.5 if day % 2 else 0.0)) for day in range(21, 29) for row in (60, 90, 120, 150)]
    errors, guesses = river.judged(found)
    assert len(errors) == len(found) and np.median(errors) == pytest.approx(0.5, abs=0.05)
    same = [reading(day, row, 10 + 0.01 * row) for day in range(21, 29) for row in (60, 90, 120, 150)]
    errors, guesses = river.judged(same)
    assert errors.max() < 0.01 and np.median(guesses) > 0.2                  # and guessing the middle level is far worse


def test_pairs_in_order_ignores_pairs_the_measurement_cannot_tell_apart():
    rising = [reading(21, row, 10 + 0.01 * row) for row in range(50, 150, 10)]
    assert river.in_order(rising)[0] == 1.0
    falling = [reading(21, row, 12 - 0.01 * row) for row in range(50, 150, 10)]
    assert river.in_order(falling)[0] == 1.0                                 # either direction, so long as it is one
    close = [reading(21, row, 10 + 0.0001 * row, std=0.05) for row in range(50, 150, 10)]
    assert river.in_order(close)[1] == 0                                     # all within their stated error: no pairs to judge


def test_a_strip_is_cut_shrunk_and_turned_dry_end_first(tmp_path, monkeypatch):
    picture = np.zeros((60, 40, 3), dtype=np.uint8)
    picture[:, :, 0] = np.arange(60)[:, None]                                # red rises down the picture
    path = tmp_path / "p.png"
    Image.fromarray(picture).save(path)
    monkeypatch.setitem(river.CAMERAS, "down", {"box": (10, 6, 22, 36), "shrink": 3, "from_bottom": False})
    monkeypatch.setitem(river.CAMERAS, "up", {"box": (10, 6, 22, 36), "shrink": 3, "from_bottom": True})
    down, up = river.strip_of(path, "down"), river.strip_of(path, "up")
    assert down.shape == (10, 4, 3) and down[0, 0, 0] == pytest.approx(7.0) and down[-1, 0, 0] == pytest.approx(34.0)
    assert np.array_equal(up, down[::-1])


def test_the_strips_were_fixed_in_the_file_and_one_camera_is_marked_as_the_test():
    assert river.CAMERAS["Strensham"]["role"] == "run once, with the strip fixed beforehand"
    assert "find out" in river.CAMERAS["Tewkesbury"]["role"]
    for camera in river.CAMERAS.values():
        left, top, right, bottom = camera["box"]
        assert 0 <= left < right <= 2048 and 0 <= top < bottom <= 1536
        assert (right - left) // camera["shrink"] == 36                      # the width the detector was built on


def test_the_script_reads_files_and_nothing_else():
    source = (ROOT / "scripts" / "river_camera_test.py").read_text("utf-8")
    for outside in ("urllib", "requests", "boto3", "subprocess", "http"):
        assert outside not in source.replace("https://", "").replace("doi:", ""), outside


def test_the_report_says_which_camera_is_the_test_and_how_far_out_it_was():
    report = (ROOT / "docs" / "waterline-river.md").read_text("utf-8")
    assert report.splitlines()[2].startswith("**Real fixed cameras, a real flood, measured water levels.**")
    report = " ".join(report.split())                                        # a sentence may be broken across lines
    for must_say in ("Strensham is the test", "13 cm", "tens of centimetres", "Not a street, and not Hyderabad",
                     "Not a surveyed scale", "hidden behind the wall", "cannot decide whether a road is passable"):
        assert must_say in report, must_say
    for name in ("docs/submission-writeup.md", "docs/video-script.md"):
        assert "waterline-river" not in (ROOT / name).read_text("utf-8"), name


def test_the_pictures_are_credited_and_kept_out_of_the_repository():
    credits = (ROOT / "samples" / "tewkesbury" / "CREDITS.md").read_text("utf-8")
    for must_say in ("10.17632/769cyvdznp.1", "University of Reading", "Farson Digital", "CC BY 4.0", "CC BY-NC 4.0", "no commercial use"):
        assert must_say in credits, must_say
    assert "samples/tewkesbury/data/" in (ROOT / ".gitignore").read_text("utf-8")
    tracked = subprocess.run(["git", "ls-files", "samples/tewkesbury"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert [name for name in tracked if not name.endswith("CREDITS.md")] == []
