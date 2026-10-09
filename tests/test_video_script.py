"""docs/video-script.md: short enough to say in the time, and honest in the ways that matter.

Whether it reads well aloud is for a person with a timer. These check the things that would be
embarrassing or misleading to get wrong: length, the disclosures, the timings and the commands.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

SCRIPT = (ROOT / "docs" / "video-script.md").read_text("utf-8")
SHOTS = re.findall(r"^### (\d) · (\d):(\d\d)–(\d):(\d\d) · (.+)$", SCRIPT, re.M)
NARRATION = " ".join(line[2:] for line in SCRIPT.splitlines() if line.startswith("> "))
WORDS_PER_MINUTE = 150


def test_seven_shots_in_order_with_no_gap_and_under_three_minutes():
    assert [int(s[0]) for s in SHOTS] == [1, 2, 3, 4, 5, 6, 7]
    times = [(int(a) * 60 + int(b), int(c) * 60 + int(d)) for _, a, b, c, d, _ in SHOTS]
    assert times[0][0] == 0 and times[-1][1] <= 170                      # ends by 2:50
    assert all(end == times[i + 1][0] for i, (_, end) in enumerate(times[:-1]))


def test_the_narration_can_be_said_in_the_time():
    words = len(NARRATION.split())
    assert 300 <= words <= 400, words
    total_s = int(SHOTS[-1][3]) * 60 + int(SHOTS[-1][4])
    assert words / WORDS_PER_MINUTE * 60 <= total_s - 15, "no room to breathe"


def test_each_shot_can_be_said_within_its_own_time():
    blocks = re.split(r"^### \d · ", SCRIPT, flags=re.M)[1:]
    for (_, a, b, c, d, title), block in zip(SHOTS, blocks):
        words = sum(len(line[2:].split()) for line in block.splitlines() if line.startswith("> "))
        seconds = (int(c) * 60 + int(d)) - (int(a) * 60 + int(b))
        assert words / WORDS_PER_MINUTE * 60 <= seconds + 1, (title, words, seconds)


def test_it_says_aloud_that_this_is_a_replay_and_what_has_not_run():
    said = NARRATION.lower()
    assert "replay of a scripted evening, not a real flood" in said
    assert "has not yet read a real photo" in said and "no accuracy figure" in said
    assert "designed, not built" in said
    assert "came from the replay" in said


def test_it_does_not_say_what_is_not_true():
    said = NARRATION.lower()
    for claim in ("reads photos", "from cctv", "camera network is", "road is closed", "road closed",
                  "guarantee", "in real time", "accurate to", "% accura", "live flood"):
        assert claim not in said, claim
    assert "guardians" not in said                 # no person receives the photo request yet
    assert not re.search(r"\b\d{2,4} tests\b", said) and "hundred" not in said      # no count to go stale


def test_the_caption_the_credit_and_the_clean_up_are_required():
    assert SCRIPT.count("Replay of a scripted evening · 45× speed") >= 1
    assert "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" in SCRIPT
    assert "reset.py --go --forget-floods" in SCRIPT.split("## After recording")[1]
    assert "Do not show a secret" in SCRIPT


def test_the_cut_points_are_the_moments_the_replay_really_produces():
    import replay
    from nirmaldhara.state import Reading, Site, apply_rain, apply_reading
    scenario = json.loads((ROOT / "data" / "scenarios" / "evening.json").read_text("utf-8"))

    def changes(key):
        site, out = Site(key), {}
        for e in (e for e in scenario["events"] if e["site"] == key):
            ts, before = e["t_min"] * 60, site.state
            site = (apply_rain(site, e["index_mm"], ts) if e["type"] == "rain" else
                    apply_reading(site, Reading(ts, e["low"], e["high"], e["confidence"], e["source"], e["device"])))
            if site.state != before:
                out[site.state] = round(e["t_min"] * 60 / 45)
            if e["type"] == "reading":
                out.setdefault("first_water", round(e["t_min"] * 60 / 45))
                out[f"range@{round(e['t_min'] * 60 / 45)}"] = (round(site.low), round(site.high))
        return out

    a, b = changes("a"), changes("b")
    table = dict(re.findall(r"^\| (\d+) \| (.+) \|$", SCRIPT, re.M))
    assert a["first_water"] == 24 and "first water" in table["24"]
    assert a["WARNING"] == 28 and "warning" in table["28"]
    assert a["range@36"] == (14, 19) and "14–19 cm" in table["36"]
    assert a["CRITICAL"] == 40 and "critical" in table["40"] and b["first_water"] == 40
    assert a["RECEDING"] == 60 and "recede" in table["60"]
    assert a["CLEAR"] == 72 and "clears" in table["72"]
    assert replay.DEFAULT_SITES["a"] == "hyd-006" and "Lakdikapul railway bridge" in SCRIPT


def test_every_command_in_the_script_is_a_real_script_with_real_options():
    for name, options in re.findall(r"python scripts/(\w+\.py)((?: --[\w-]+(?: \d+)?)*)", SCRIPT):
        source = (ROOT / "scripts" / name).read_text("utf-8")
        for option in re.findall(r"--[\w-]+", options):
            assert f'"{option}"' in source, f"{name} has no {option}"
    assert (ROOT / "docs" / "smoke-test.md").exists() and "## Alerts as delivered" in (ROOT / "docs" / "smoke-test.md").read_text("utf-8")
