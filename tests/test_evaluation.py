"""The evaluation and photo scripts, run on drawn scenes and a stand-in reader.

Nothing here says how well a model reads a real photograph. It shows the tools do what they claim,
and that a dangerous miss, if one happened, would be counted and named.
"""

import csv
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate  # noqa: E402
import make_synthetic_photos as scenes  # noqa: E402
import photo  # noqa: E402
import simulated_reader as sim  # noqa: E402

LABELS = list(csv.DictReader(open(ROOT / "samples" / "synthetic" / "labels.csv", encoding="utf-8")))
BY_FILE = {row["file"]: row for row in LABELS}


def read(name):
    return sim.read_depth(str(ROOT / "samples" / "synthetic" / name))


# --- the drawn scenes ---------------------------------------------------------------------------

def test_there_are_22_scenes_each_labelled_with_the_band_of_the_depth_it_was_drawn_at():
    from nirmaldhara.bands import band_for
    assert len(LABELS) == 22
    for row in LABELS:
        assert row["band_low"] == row["band_high"] == band_for(float(row["true_depth_cm"]))
        assert row["licence"] == "not a photograph"


def test_the_committed_scenes_are_what_the_generator_draws():
    for row in LABELS:
        drawn = scenes.draw_scene(int(row["true_depth_cm"]), row["condition"],
                                  seed=int(row["true_depth_cm"]) * 31 + len(row["condition"]))
        kept = Image.open(ROOT / "samples" / "synthetic" / row["file"]).convert("RGB")
        assert ImageChops.difference(drawn, kept).getbbox() is None, row["file"]


# --- the simulated reader -----------------------------------------------------------------------

@pytest.mark.parametrize("name", [r["file"] for r in LABELS if r["condition"] == "normal"])
def test_a_clear_scene_is_read_within_two_centimetres(name):
    out = read(name)
    true = float(BY_FILE[name]["true_depth_cm"])
    assert not out["cannot_tell"]
    assert abs((out["depth_cm_low"] + out["depth_cm_high"]) / 2 - true) <= 2.0 + 0.06 * true
    assert out["depth_cm_low"] <= true <= out["depth_cm_high"] or true == 0


@pytest.mark.parametrize("name", [r["file"] for r in LABELS if r["readable"] == "no"])
def test_dark_blurred_and_wheelless_scenes_are_declined(name):
    out = read(name)
    assert out["cannot_tell"] and out["confidence"] == 0


def test_glare_makes_it_underestimate_and_it_knows_it_is_unsure():
    for name in ("glare-18cm.png", "glare-24cm.png", "glare-36cm.png"):
        out = read(name)
        true = float(BY_FILE[name]["true_depth_cm"])
        assert (out["depth_cm_low"] + out["depth_cm_high"]) / 2 < true      # the failure is real
        assert out["confidence"] < 0.6                                       # and it says so


def test_a_hidden_wheel_makes_it_overestimate_not_underestimate():
    for name in ("occluded-14cm.png", "occluded-26cm.png"):
        out = read(name)
        true = float(BY_FILE[name]["true_depth_cm"])
        assert (out["depth_cm_low"] + out["depth_cm_high"]) / 2 > true       # the safe direction


def test_every_answer_says_it_is_simulated_and_has_the_real_readers_fields():
    from nirmaldhara import reader
    for row in LABELS:
        out = read(row["file"])
        assert out["reason"].startswith("SIMULATED")
        assert set(out) == set(reader.CANNOT_TELL) | {"reason"}


# --- the scoring ----------------------------------------------------------------------------------

def reading(low, high, confidence=0.9, cannot_tell=False):
    return {"cannot_tell": cannot_tell, "depth_cm_low": low, "depth_cm_high": high,
            "confidence": confidence, "reason": ""}


def row(low="B3", high=None, **extra):
    return {"file": "x.jpg", "band_low": low, "band_high": high or low, **extra}


def test_a_dangerous_miss_is_counted_and_named():
    """The photo is knee deep (B4, at least 30 cm); the reader calls it ankle deep with confidence."""
    scored = evaluate.score_one(row("B4"), reading(4, 8))
    assert scored["dangerous"] == ["two_wheeler", "car", "pedestrian"]
    summary = evaluate.summarise([scored])
    assert summary["dangerous_photos"] == 1 and summary["dangerous_by_vehicle"]["car"] == 1
    assert "DANGEROUS MISS" in evaluate.render([scored], summary, False, "reader")


def test_low_confidence_turns_what_would_be_a_dangerous_miss_into_a_cautious_answer():
    scored = evaluate.score_one(row("B4"), reading(4, 8, confidence=0.5))
    assert scored["dangerous"] == []


def test_an_error_in_the_safe_direction_is_not_a_dangerous_miss_but_is_counted_as_cautious():
    scored = evaluate.score_one(row("B1"), reading(15, 25))             # ankle deep, read as below the knee
    assert scored["dangerous"] == [] and "car" in scored["cautious"] and scored["within_one"] is False


def test_the_label_interval_decides_agreement():
    assert evaluate.score_one(row("B2", "B3"), reading(14, 24))["exact"] is True       # B3 is inside B2-B3
    assert evaluate.score_one(row("B2", "B3"), reading(35, 45))["within_one"] is True  # B4 is one from B3
    assert evaluate.score_one(row("B2"), reading(35, 45))["within_one"] is False


def test_declining_is_right_for_an_unreadable_photo_and_wrong_for_a_readable_one():
    unreadable = evaluate.score_one(row(readable="no"), reading(0, 0, 0, cannot_tell=True))
    readable = evaluate.score_one(row(), reading(0, 0, 0, cannot_tell=True))
    answered = evaluate.score_one(row(object_used="none"), reading(10, 15))
    s = evaluate.summarise([unreadable, readable, answered])
    assert (s["declined_correctly"], s["declined_but_readable"], s["answered_when_it_should_decline"]) == (1, 1, 1)


def test_the_simulated_table_on_the_drawn_scenes():
    scored = [evaluate.score_one(r, read(r["file"])) for r in LABELS]
    s = evaluate.summarise(scored)
    assert (s["photos"], s["read"], s["unreadable"], s["declined_correctly"]) == (22, 18, 4, 4)
    assert s["within_one"] == 18 and s["dangerous_photos"] == 0 and s["answered_when_it_should_decline"] == 0


# --- what the script will and will not write -----------------------------------------------------------

def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["evaluate.py", *argv])
    return evaluate.main()


def test_a_simulated_run_never_writes_the_real_evaluation(monkeypatch):
    real = ROOT / "EVALUATION.md"
    assert not real.exists()
    assert run(monkeypatch, "--reader", "simulated", "--synthetic") == 0
    assert not real.exists()
    text = (ROOT / "docs" / "evaluation-simulated.md").read_text("utf-8")
    assert text.startswith("# Depth reading: evaluation (SIMULATED)") and "Nothing below is evidence" in text
    assert '"simulated": true' in (ROOT / "data" / "eval-results-simulated.json").read_text("utf-8")


def test_the_committed_simulated_table_is_current():
    scored = [evaluate.score_one(r, read(r["file"])) for r in LABELS]
    text = evaluate.render(scored, evaluate.summarise(scored), True, "scripts/simulated_reader.py")
    assert (ROOT / "docs" / "evaluation-simulated.md").read_text("utf-8") == text


def test_the_two_readers_cannot_be_pointed_at_the_wrong_pictures(monkeypatch, capsys):
    assert run(monkeypatch, "--reader", "simulated") == 2                  # the stand-in needs the drawn scenes
    assert run(monkeypatch, "--reader", "bedrock", "--synthetic") == 2     # the model is not tested on drawings
    assert run(monkeypatch, "--reader", "bedrock", "--labels", "no-such-file.csv") == 1
    assert "No labels file" in capsys.readouterr().out


# --- the photo script ------------------------------------------------------------------------------------

def prepare(name, **kw):
    return photo.prepare(ROOT / "samples" / "synthetic" / name, "hyd-006", sim.read_depth, simulated=True, now=1_800_000_000, **kw)


def test_a_readable_photo_becomes_an_unconfirmed_resident_reading_from_the_simulated_device():
    out = prepare("normal-16cm.png")
    assert out["status"] == "ok"
    message = out["message"]
    assert message["site_id"] == "hyd-006" and message["type"] == "reading"
    r = message["reading"]
    assert (r["source"], r["device"], r["ts"]) == ("resident", "simulated-reader", 1_800_000_000)
    assert 11 < r["low"] < r["high"] < 21 and r["confidence"] == 0.85


def test_a_photo_the_gates_refuse_sends_nothing():
    dark, blurred = prepare("dark-22cm.png"), prepare("blurred-28cm.png")
    assert (dark["status"], dark["reason"], dark["message"]) == ("refused", "too dark", None)
    assert (blurred["status"], blurred["reason"], blurred["message"]) == ("refused", "too blurred", None)


def test_a_photo_the_reader_declines_sends_nothing_and_says_why():
    out = prepare("no_wheel-20cm.png")
    assert out["status"] == "declined" and out["message"] is None and "nothing of known size" in out["reason"]


def test_the_script_refuses_to_put_a_simulated_reading_on_the_real_map_without_being_told(monkeypatch, capsys):
    base = ["photo.py", str(ROOT / "samples" / "synthetic" / "normal-16cm.png"), "hyd-006", "--reader", "simulated"]
    monkeypatch.setattr(sys, "argv", [*base, "--go"])
    assert photo.main() == 2 and "made-up depth" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", [*base, "--source", "guardian"])
    assert photo.main() == 2 and "never sent as a trusted source" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", base)                                  # a dry run is fine, and says what it is
    assert photo.main() == 0 and "SIMULATED" in capsys.readouterr().out
