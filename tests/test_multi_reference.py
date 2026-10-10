"""scripts/river_multi_reference.py: how several strips in one view are joined and scored on the real flood.

The pictures are not in the repository, so the test itself is not run here. These check the joining
on made rows, and that the report says what it is.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import river_multi_reference as multi  # noqa: E402

DAYS = (21, 22, 23, 24, 25, 26, 27, 28)
LEVEL = {day: 10.0 + 0.25 * n for n, day in enumerate(DAYS)}


def strip(slope=100.0, wild=(), silent=(), seed=0):
    """One strip's rows for four pictures a day: the row rises with the level, a pixel or two out."""
    rng = np.random.default_rng(seed)
    out = {}
    for day in DAYS:
        for hour in (9, 10, 11, 12):
            key = (11, day, hour)
            row = slope * (LEVEL[day] - 10.0) + 40 + rng.normal(0, 1.5) + (90 if key in wild else 0)
            out[key] = {"day": (11, day), "hour": hour, "level": LEVEL[day], "std": 0.05, "found": key not in silent,
                        "row": None if key in silent else float(row)}
    return out


def test_a_strips_record_comes_from_days_it_was_made_to_do_without():
    found = [r for r in strip().values() if r["day"][1] % 2 == 1]
    curve, errors = multi.record(found)
    assert len(errors) == len(found) and float(np.median(errors)) < 0.30         # each day read by a curve that never saw it
    assert abs(float(curve(40 + 100 * 0.5)) - 10.5) < 0.05
    assert multi.record(found[:8]) is None                                       # too few lines, and only two days


def test_three_strips_are_joined_by_the_middle_one_so_a_wild_strip_does_not_move_the_level():
    key = (11, 24, 10)
    readings = {"A": strip(seed=1), "B": strip(slope=80.0, seed=2), "C": strip(slope=120.0, seed=3, wild={key})}
    rows = {r["key"]: r for r in multi.joined(readings)}
    assert len(rows) == 32 and all(r["used"] == 3 for r in rows.values())
    hit = rows[key]
    assert abs(hit["alone"]["C"] - hit["level"]) > 0.4                           # that strip is far out there
    assert abs(hit["together"] - hit["level"]) < 0.2 and hit["agreed"]           # and the three together are not
    errors = [abs(r["together"] - r["level"]) for r in rows.values()]
    assert float(np.median(errors)) < 0.2


def test_every_unseen_day_is_read_by_curves_from_the_other_half_of_the_days():
    readings = {"A": strip(seed=1), "B": strip(slope=80.0, seed=2), "C": strip(slope=120.0, seed=3)}
    shifted = {name: {k: ({**r, "level": r["level"] + 5.0} if r["day"][1] % 2 else r) for k, r in by_key.items()} for name, by_key in readings.items()}
    rows = multi.joined(shifted)                                                 # odd days measured 5 m higher than even ones
    odd = [abs(r["together"] - r["level"]) for r in rows if r["key"][1] % 2]
    assert min(odd) > 3.0                                                        # so a curve from even days must miss them


def test_two_strips_give_their_mean_and_the_cautious_range_and_a_silent_strip_is_left_out():
    quiet = set(strip())                                                          # a strip that never reports a line
    readings = {"A": strip(seed=1), "B": strip(slope=80.0, seed=2), "C": strip(seed=3, silent=quiet)}
    rows = multi.joined(readings)
    assert all(r["used"] == 2 and r["agreed"] is False and "C" not in r["alone"] for r in rows)
    for r in rows:
        assert min(r["alone"].values()) - 1e-9 <= r["together"] <= max(r["alone"].values()) + 1e-9
        assert r["high"] >= max(r["alone"].values())                              # the highest high end stands


def test_the_strips_were_fixed_in_the_file_and_one_camera_is_marked_as_run_once():
    assert multi.STRIPS["Strensham"]["role"] == "run once, with the new strips fixed beforehand"
    assert "work out" in multi.STRIPS["Tewkesbury"]["role"]
    for camera, entry in multi.STRIPS.items():
        assert entry["strips"]["A"][0] == multi.river.CAMERAS[camera]["box"]                      # the strip used before, unchanged
        assert entry["strips"]["A"][1] == multi.river.CAMERAS[camera]["from_bottom"]
        for box, _, what in entry["strips"].values():
            left, top, right, bottom = box
            assert right - left == 108 and 0 <= left and right <= 2048 and 0 <= top < bottom <= 1536 and what
    assert len(multi.STRIPS["Strensham"]["strips"]) == 4


def test_the_script_reads_files_and_nothing_else():
    source = (ROOT / "scripts" / "river_multi_reference.py").read_text("utf-8")
    for outside in ("urllib", "requests", "boto3", "subprocess", "http"):
        assert outside not in source.replace("https://", "").replace("doi:", ""), outside


def test_the_report_says_which_camera_is_the_test_and_what_joining_gained():
    report = (ROOT / "docs" / "multi-reference-river.md").read_text("utf-8")
    assert report.splitlines()[2].startswith("**Real fixed cameras, a real flood, measured water levels.**")
    flat = " ".join(report.split())
    for must_say in ("Strensham is the test", "Tewkesbury was used to work out the joining", "10 cm out, typically, against 13 cm",
                     "They did not beat the best single surface", "No gain", "The gain is modest", "Not several cameras",
                     "Not marks of known size", "Not a street, and not Hyderabad", "still not a reading to close a road on"):
        assert must_say in flat, must_say
    assert "nan" not in report
    for name in ("docs/submission-writeup.md", "docs/video-script.md"):
        assert "multi-reference-river" not in (ROOT / name).read_text("utf-8"), name
    readme = " ".join((ROOT / "README.md").read_text("utf-8").split())
    assert "docs/multi-reference-river.md" in readme and "against 13 cm for one" in readme and "joining gained nothing" in readme
    assert "No place has two cameras on one water" in readme                 # the several-camera part is tests and a simulation only
