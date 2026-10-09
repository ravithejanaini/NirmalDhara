"""The guide's words (web/guide.js): the summary line and what the key explains. Run with Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from nirmaldhara import alerts

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")


def site(state="CLEAR", high=0):
    return {"id": "x", "name": "X", "state": state, "low": max(0, high - 5), "high": high, "trusted": True,
            "confidence": 0.8, "updated": 0}


def run(expression, sites=()):
    script = f"""
import {{ summaryModel, legendItems, WELCOME_LINES }} from "{(ROOT / 'web' / 'guide.js').as_uri()}";
import {{ glyphState }} from "{(ROOT / 'web' / 'glyph.js').as_uri()}";
const sites = {json.dumps(list(sites))};
console.log(JSON.stringify({expression}));
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_all_clear_says_there_is_no_water_and_no_heavy_rain_forecast():
    out = run("summaryModel(sites)", [site() for _ in range(9)])
    assert out == {"text": "No water reported in Hyderabad right now. No heavy rain is forecast near the 9 places watched.",
                   "tone": "clear"}


def test_a_watch_with_no_water_gives_the_rain_outlook_not_an_all_clear():
    out = run("summaryModel(sites)", [site("WATCH"), site("WATCH"), site()])
    assert out["text"] == "No water reported yet. Heavy rain is forecast near 2 of 3 places." and out["tone"] == "watch"


def test_water_is_counted_and_critical_is_named():
    one = run("summaryModel(sites)", [site("WARNING", 15), site(), site()])
    assert one == {"text": "1 of 3 places have water", "tone": "water"}
    two = run("summaryModel(sites)", [site("CRITICAL", 30), site("WARNING", 15), site()])
    assert two == {"text": "2 of 3 places have water · 1 critical", "tone": "critical"}


def test_singular_and_no_sites_are_worded_correctly():
    assert run("summaryModel(sites)", [site()])["text"].endswith("near the 1 place watched.")
    assert run("summaryModel(sites)", [])["text"] == "No places are being watched yet."
    assert run("summaryModel(sites)", [site("WATCH")])["text"] == "No water reported yet. Heavy rain is forecast near 1 of 1 place."


def test_a_receding_site_with_water_counts_as_having_water():
    assert run("summaryModel(sites)", [site("RECEDING", 9), site()])["text"] == "1 of 2 places have water"


def test_the_summary_never_claims_safety():
    for sites in ([], [site()], [site("WATCH")], [site("WARNING", 15)], [site("CRITICAL", 40)]):
        text = run("summaryModel(sites)", sites)["text"].lower()
        assert not any(w in text for w in ("safe", "open", "closed", "clear to"))


def test_the_welcome_has_three_lines_and_the_moving_water_warning():
    lines = run("WELCOME_LINES")
    assert len(lines) == 3 and "moving water" in lines[2] and "moving water" in alerts.MOVING_WATER


def test_the_key_explains_every_state_the_glyph_can_show_and_each_example_looks_as_it_says():
    items = run("legendItems(1000).map((i) => ({word: i.word, state: glyphState(i.site, 1000)}))")
    assert [i["word"] for i in items] == ["Clear", "Watch", "Shallow", "Water", "One photo", "Critical", "Falling", "Old"]
    by = {i["word"]: i["state"] for i in items}
    assert by["Watch"]["ring"] == "watch" and by["Critical"]["ring"] == "critical"
    assert by["One photo"]["unconfirmed"] and by["Falling"]["falling"] and by["Old"]["stale"]
    assert by["Shallow"]["tone"] == "shallow" and by["Water"]["tone"] == "water" and by["Clear"]["tone"] == "none"
    # no two examples are the same drawing: each must be told apart
    signature = lambda s: (s["tone"], s["ring"], s["unconfirmed"], s["stale"], s["falling"])  # noqa: E731
    assert len({signature(s) for s in by.values()}) == 8
