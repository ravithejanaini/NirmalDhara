"""scripts/river_forecast.py: how the prediction stage's slope is judged on the real flood, and what its report may say.

The pictures are not in the repository, so the test itself is not run here. These check, on made
readings, which moments are forecast from which, what each way of forecasting says, and that the
report says what it is.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import river_forecast as rf  # noqa: E402

DAYS = tuple(range(21, 30))                                                    # nine days: three runs of three
HOURS = (9, 10, 11, 12)


def level_at(day, hour):
    since = (day - 21) * 24 + hour - 9
    return 10.0 + 0.02 * (96 - abs(since - 96))                               # two centimetres an hour: up for four days, then down


def strip(slope, seed):
    rng = np.random.default_rng(seed)
    out = {}
    for day in DAYS:
        for hour in HOURS:
            level = level_at(day, hour)
            out[(11, day, hour)] = {"day": (11, day), "hour": hour, "level": level, "std": 0.05, "found": True,
                                    "row": float(700 - slope * (level - 10.0) + rng.normal(0, 1.0)), "reason": "ok"}
    return out


def test_days_are_left_out_three_in_a_row_and_a_short_last_run_joins_the_one_before():
    assert rf.runs(np.array([1121, 1122, 1123, 1124, 1125, 1126])) == [[1121, 1122, 1123], [1124, 1125, 1126]]
    assert rf.runs(np.array([1129, 1130, 1201, 1202, 1203])) == [[1129, 1130, 1201, 1202, 1203]]
    assert rf.runs(np.array([1121, 1121, 1122, 1123, 1124, 1125, 1126, 1127])) == [[1121, 1122, 1123], [1124, 1125, 1126, 1127]]
    assert rf.runs(np.array([1121, 1122])) == [[1121, 1122]]


def test_forecasts_run_within_a_day_and_across_a_night():
    days = np.array([1121] * 4 + [1122] * 3)
    hours = np.array([9.0, 10.0, 12.0, 16.0, 31.0, 33.0, 40.0])                # 7 am, 9 am and 4 pm on the second day
    made = rf.pairs(days, hours)
    assert (0, 1, "1 hour") in made and (0, 2, "3 hours") in made and (1, 3, "6 hours") in made
    assert (3, 4, "the next morning") in made and (3, 6, "24 hours") in made and (0, 5, "24 hours") in made
    assert not any(far == "the next morning" for i, _, far in made if i != 3)  # only from a day's last picture
    assert all(hours[j] - hours[i] <= 30 for i, j, _ in made)
    assert rf.pairs(np.array([1121, 1123]), np.array([16.0, 55.0])) == []      # a day missing between: too far ahead


def test_the_slope_is_carried_forward_and_used_only_when_the_ranges_stand_clear():
    times, middles = [0.0, 1.0, 2.0, 3.0], [10.0, 10.1, 10.2, 10.3]            # ten centimetres an hour
    narrow = rf.told(times, [m - 0.05 for m in middles], middles, [m + 0.05 for m in middles], 2.0)
    assert narrow["no change"] == (10.3, None)
    assert abs(narrow["the slope"][0] - 10.5) < 1e-9
    assert narrow["the slope when it is clear"][1] is True and abs(narrow["the slope when it is clear"][0] - 10.5) < 1e-9
    wide = rf.told(times, [m - 0.4 for m in middles], middles, [m + 0.4 for m in middles], 2.0)
    assert wide["the slope when it is clear"] == (10.3, False)                 # the ranges overlap: it says no change
    falling = rf.told(times, [10.25, 10.15, 10.05, 9.95], [10.3, 10.2, 10.1, 10.0], [10.35, 10.25, 10.15, 10.05], 1.0)
    assert falling["the slope when it is clear"][1] is True and abs(falling["the slope when it is clear"][0] - 9.9) < 1e-9
    assert rf.told(times[:2], [9.9, 10.0], middles[:2], [10.1, 10.2], 1.0) is None       # two readings make no slope


def test_every_forecast_is_judged_on_days_the_model_never_saw(monkeypatch):
    monkeypatch.setitem(rf.rdm.STRIPS, "made", {"role": "made", "strips": {n: ((0, 0, 108, 2400), False, n) for n in "ABC"}})
    result = rf.one_camera("made", {"A": strip(100.0, 1), "B": strip(60.0, 2), "C": strip(140.0, 3)})
    assert result["runs"] == 3 and result["days"] == 9 and len(result["now"]) == 36
    assert all(set(m.witnesses) == {"A", "B", "C"} for m in result["learnt"])
    assert np.median([abs(read - measured) for measured, read, _, _ in result["now"]]) < 0.2
    exact = result["ahead"]["the measured levels"]
    miss = lambda rows: float(np.median([abs(told - measured) for measured, told, _ in rows]))      # noqa: E731
    assert abs(miss(exact["24 hours"]["no change"]) - 0.48) < 1e-6             # a day's rise, missed whole by saying no change
    assert miss(exact["24 hours"]["the slope"]) < 0.01                         # and caught by the slope, the levels being exact
    clear = [used for _, _, used in exact["1 hour"]["the slope when it is clear"]]
    assert any(clear) and not all(clear)                                       # clear across a night, not within one morning
    for kind in rf.KINDS:
        assert len(result["ahead"][kind]["the next morning"]["no change"]) == 6      # two nights inside each run of three days
        assert len(result["ahead"][kind]["1 hour"]["no change"]) == len(result["ahead"][kind]["1 hour"]["the slope"])
    every, clear = rf.tally(exact, False), rf.tally(exact, True)
    assert every[0] == sum(len(exact[far]["no change"]) for far in rf.AHEAD) and clear[0] < every[0]
    assert clear[1] > clear[2] and clear[1] + clear[2] <= clear[0]             # where the rise was clear the slope was closer
    table = rf.report({"Tewkesbury": result})
    assert f"Of the {clear[0]} in which it was clear, it was closer in {clear[1]} and further out in {clear[2]}." in table
    assert "| 24 hours | " in table and "left out in 3 runs of three days" in table and "From the measured levels themselves" in table


def test_the_cameras_and_strips_are_the_depth_models_and_one_is_marked_as_run_once():
    assert rf.ROLES == {"Tewkesbury": "used to choose the guard", "Strensham": "run once, with the guard fixed beforehand"}
    assert set(rf.ROLES) == set(rf.rdm.STRIPS) and rf.RUN == 3
    source = (ROOT / "scripts" / "river_forecast.py").read_text("utf-8")
    assert "STRIPS = " not in source and "predict.rise_rate" in source and "predict.clear_rise" in source


def test_the_script_reads_files_and_nothing_else():
    source = (ROOT / "scripts" / "river_forecast.py").read_text("utf-8")
    for outside in ("urllib", "requests", "boto3", "subprocess", "http"):
        assert outside not in source.replace("https://", "").replace("doi:", ""), outside


def test_the_report_says_which_camera_is_the_test_what_was_found_and_what_was_not_kept():
    report = (ROOT / "docs" / "forecast-river.md").read_text("utf-8")
    assert report.splitlines()[2].startswith("**Real fixed cameras, a real flood, measured water levels.**")
    assert "## Tewkesbury: used to choose the guard" in report and "## Strensham: run once, with the guard fixed beforehand" in report
    flat = " ".join(report.split())
    for must_say in ("Strensham is the test", "Tewkesbury was used to choose the guard", "No figure in the tables changed",
                     "A forecast is as good as the reading it starts from", "On this river the slope did not earn its place",
                     "The guard did not pick the moments when the slope was right", "The guard is a rule to say less",
                     "It was kept as a design choice, not as a finding", "has nothing real behind it",
                     "What was tried on the way and not kept", "Three days in a row is much harder than every other day",
                     "Not a street, and not Hyderabad", "Not a forecast from rain", "Not many forecasts across a night"):
        assert must_say in flat, must_say
    for name in ("docs/submission-writeup.md", "docs/video-script.md"):
        assert "forecast-river" not in (ROOT / name).read_text("utf-8"), name
    readme = " ".join((ROOT / "README.md").read_text("utf-8").split())
    assert "docs/forecast-river.md" in readme and "no better than saying \"no change\"" in readme
    assert "a rule to say less, which this trial did not confirm" in readme and "has nothing real behind it" in readme
    credits = (ROOT / "samples" / "tewkesbury" / "CREDITS.md").read_text("utf-8")
    assert "scripts/river_forecast.py" in credits and "docs/forecast-river.md" in credits


def test_the_borrowed_designs_page_says_what_was_kept_and_what_was_not():
    page = (ROOT / "docs" / "borrowed-designs.md").read_text("utf-8")
    for heading in ("## Already in the model", "## Added on 10 October 2026", "## Tried on the real flood and not kept",
                    "## Not tried, and why", "## What this comes to", "## Sources"):
        assert heading in page, heading
    flat = " ".join(page.split())
    for must_say in ("Naming a design does not make the model closer", "One was kept, as a design choice",
                     "which the river did not confirm", "None went as far as the test camera",
                     "The rest are given as they are commonly cited and were not checked that day"):
        assert must_say in flat, must_say
    kept = page.split("## Tried on the real flood and not kept")[0]
    for module in ("depthmodel.py", "waterline.py", "state.py", "bands.py", "predict.py", "multiview.py", "volume.py", "workflow.py", "alerts.py", "gauge.py"):
        assert f"`{module}`" in kept and (ROOT / "src" / "nirmaldhara" / module).exists(), module
    for name in ("clear_rise", "rise_rate"):
        assert f"predict.{name}" in kept and f"def {name}(" in (ROOT / "src" / "nirmaldhara" / "predict.py").read_text("utf-8")
    assert "track.py" not in page and not (ROOT / "src" / "nirmaldhara" / "track.py").exists()      # the tracker that was tried is not in the repository
    assert "docs/borrowed-designs.md" in (ROOT / "README.md").read_text("utf-8") and "docs/borrowed-designs.md" in (ROOT / "METHOD.md").read_text("utf-8")
