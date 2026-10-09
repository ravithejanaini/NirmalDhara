"""The rules behind the depth glyph (web/glyph.js, `glyphState`), run with Node.

The drawing itself is checked by eye in web/glyph-gallery.html. This checks what decides the
drawing: where the water sits, which blue, which ring, and when a reading counts as stale or
unconfirmed.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOW = 1_760_000_000

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")


def states(sites):
    script = f"""
import {{ glyphState, levelY }} from "{(ROOT / 'web' / 'glyph.js').as_uri()}";
const sites = {json.dumps(sites)};
console.log(JSON.stringify({{ states: sites.map((s) => glyphState(s, {NOW})),
                             levels: [0, 30, 60, 90].map(levelY) }}));
"""
    out = subprocess.run(["node", "--input-type=module", "-e", script],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def site(state, low, high, trusted=True, age_min=4, name="Malakpet underpass"):
    return {"name": name, "state": state, "low": low, "high": high, "trusted": trusted,
            "updated": NOW - age_min * 60}


def test_the_disc_fills_from_bottom_to_top_over_sixty_centimetres():
    levels = states([])["levels"]
    assert levels[0] > 36                    # no water: parked below the 28 px disc (8 to 36)
    assert levels[1:] == [22, 8, 8]          # half way, full, and still full above 60 cm


def test_colour_follows_the_cautious_end_of_the_range():
    result = states([site("WARNING", 2, 11.9), site("WARNING", 5, 12), site("WARNING", 20, 30),
                     site("CRITICAL", 20, 30.1), site("CLEAR", 0, 0)])["states"]
    assert [s["tone"] for s in result] == ["shallow", "water", "water", "deep", "none"]


def test_solid_reaches_the_low_end_and_the_band_the_high_end():
    [s] = states([site("WARNING", 15, 30)])["states"]
    assert s["lowY"] == 29 and s["highY"] == 22 and s["highY"] < s["lowY"]


def test_rings_perforation_staleness_and_the_falling_mark():
    watch, wet_watch, critical, one_photo, stale, receding, clear = states([
        site("WATCH", 0, 0, trusted=False), site("WATCH", 3, 8), site("CRITICAL", 28, 38),
        site("WARNING", 12, 17, trusted=False), site("WARNING", 13, 18, age_min=31),
        site("RECEDING", 8, 13), site("CLEAR", 0, 0, trusted=False, age_min=600)])["states"]
    assert watch["ring"] == "watch" and not watch["unconfirmed"]   # nothing to confirm yet
    assert wet_watch["ring"] == "none"                             # water shows by itself
    assert critical["ring"] == "critical"
    assert one_photo["unconfirmed"] and not critical["unconfirmed"]
    assert stale["stale"] and not critical["stale"]
    assert not clear["stale"]                                      # a dry site is not "old"
    assert receding["falling"] and not critical["falling"]


def test_the_spoken_label_says_what_the_eye_sees():
    one_photo, clear = states([site("WARNING", 12.4, 16.6, trusted=False, age_min=6),
                               site("CLEAR", 0, 0)])["states"]
    assert one_photo["label"] == ("Malakpet underpass, warning, 12 to 17 centimetres, "
                                  "from one unconfirmed photo, seen 6 minutes ago")
    assert clear["label"] == "Malakpet underpass, clear, no water reported"
