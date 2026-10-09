"""The rehearsal tools: the local replay shows the real replay's moments, and the pre-flight only reads."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import preflight  # noqa: E402
import rehearse  # noqa: E402
import replay  # noqa: E402

SCENARIO = json.loads((ROOT / "data" / "scenarios" / "evening.json").read_text("utf-8"))
FRAMES = rehearse.frames(SCENARIO)


def moments(sample):
    return [(round(t), f["state"], f["low"], f["high"], f["trusted"]) for t, s, f in FRAMES if s == sample]


def test_the_local_rehearsal_shows_the_moments_in_the_video_script():
    a = moments("sample-05")                                # stands in for Lakdikapul railway bridge
    assert a[0] == (0, "WATCH", 0, 0, 0)
    assert (28, "WARNING", 7, 12, 1) in a and (36, "WARNING", 14, 19, 1) in a
    assert (40, "CRITICAL", 19, 24, 1) in a and (60, "RECEDING", 19, 24, 1) in a
    assert a[-1] == (72, "CLEAR", 3, 8, 1)
    b = moments("sample-04")                                # one resident's photos: never trusted
    assert (40, "WARNING", 12, 17, 0) in b and all(m[4] == 0 for m in b)
    assert moments("sample-02")[-1][:2] == (100, "CLEAR")   # the dry watch ends
    assert moments("sample-01") == []                       # the fourth place never changes


def test_the_rehearsal_keeps_the_real_replays_clock():
    real = {round(step["delay_s"], 3) for step in replay.plan(SCENARIO, replay.DEFAULT_SITES, 0, 45)}
    assert {round(t, 3) for t, _, _ in FRAMES} <= real
    assert [t for t, _, _ in FRAMES] == sorted(t for t, _, _ in FRAMES)


def test_the_rehearsal_only_ever_talks_to_this_machine():
    source = (ROOT / "scripts" / "rehearse.py").read_text("utf-8")
    assert 'default="http://127.0.0.1:8080"' in source
    for remote in ("boto3", "import stack", "import send", "amazonaws", "lambda-url"):
        assert remote not in source, remote
    assert all(name.startswith("Rehearsal:") for _, name in rehearse.STAND_INS.values())


def test_the_preflight_never_writes_sends_or_deletes():
    source = (ROOT / "scripts" / "preflight.py").read_text("utf-8")
    for call in (".put_", ".delete_", ".send_message", ".publish(", ".invoke(", ".stop_execution", ".update_",
                 ".create_", ".subscribe(", ".attach_", ".detach_", "write_text", '"push"', '"commit"'):
        assert call not in source, call


def test_the_secret_pattern_catches_keys_and_not_their_names():
    assert preflight.SECRET.search("AKIA" + "ABCDEFGHIJKLMNOP")
    assert preflight.SECRET.search("sk-ant-" + "a" * 30)
    assert preflight.SECRET.search("aws_secret_access_key = " + "x" * 40)
    for harmless in ("ANTHROPIC_API_KEY", "the key AKIA is the prefix", "aws_secret_access_key = <yours>", "sk-ant"):
        assert not preflight.SECRET.search(harmless), harmless


def test_the_preflight_counts_and_reports_each_kind():
    preflight.RESULTS.clear()
    preflight.say("ok", "a")
    preflight.say("TODO", "b", "detail")
    preflight.say("FAIL", "c")
    assert preflight.RESULTS == ["ok", "TODO", "FAIL"]
    preflight.RESULTS.clear()


def test_the_event_window_is_the_one_the_rules_give():
    assert (preflight.EVENT_START.isoformat(), preflight.EVENT_END.isoformat()) == ("2026-10-08", "2026-10-11")
    assert re.search(r"Oct 8 . 11|8 to 11 Oct|8.11 October", (ROOT / "README.md").read_text("utf-8"))
