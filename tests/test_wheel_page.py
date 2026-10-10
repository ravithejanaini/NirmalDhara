"""web/wheel.js and web/wheel.html: the wheel reading in the browser must be the Python's, and must never clear a road.

Three checks, as for the rules: the figures and words in wheel.js are those of
src/nirmaldhara/wheel.py; where Node is installed, wheel.js is run on every wheel and every answer;
and the page says what it is. The page was looked at in a browser on localhost, at phone width.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from nirmaldhara import bands, wheel

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
JS = (WEB / "wheel.js").read_text("utf-8")
PAGE = (WEB / "wheel.html").read_text("utf-8")


def js_constant(name):
    match = re.search(rf"export const {name} = (.+?);\n", JS, re.S)
    assert match, name
    literal = re.sub(r"([{,]\s*)(\w+):", r'\1"\2":', match.group(1))            # bare keys to quoted ones
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", literal))                    # and no trailing commas


def test_the_figures_and_words_in_wheel_js_are_the_pythons():
    assert js_constant("ASK") == wheel.ASK
    assert js_constant("MARKS") == wheel.MARKS and list(js_constant("MARKS")) == list(wheel.MARKS)
    assert js_constant("TABLE") == {name: {mark: list(ends) for mark, ends in table.items()} for name, table in wheel.TABLE.items()}
    assert js_constant("SAME_AS") == wheel.SAME_AS and js_constant("WHEELS") == wheel.WHEELS
    assert js_constant("SOMEWHERE") == wheel.SOMEWHERE < bands.MIN_CONFIDENCE


def test_the_rows_and_words_are_the_ones_the_map_sheet_uses():
    sheet = (WEB / "sheet.js").read_text("utf-8")
    for row in re.findall(r'\{ id: "(\w+)", row: "([^"]+)" \}', JS):
        assert f'id: "{row[0]}"' in sheet and f'row: "{row[1]}"' in sheet, row
    assert len(re.findall(r'\{ id: "\w+", row: "[^"]+" \}', JS)) == len(bands.NO_GO_CM)
    assert f'word: "{js_constant("WORD_NOT_SAFE")}"' in sheet and f'word: "{js_constant("WORD_UNSURE")}"' in sheet


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
def test_wheel_js_gives_the_pythons_answer_for_every_wheel_and_every_mark():
    script = f"""
import {{ depth, answers, verdicts, depthWords, WHEELS, MARKS }} from "{(WEB / 'wheel.js').as_uri()}";
const out = {{}};
for (const wheel of Object.keys(WHEELS)) for (const mark of Object.keys(MARKS)) {{
  out[`${{wheel}} ${{mark}}`] = {{ depth: depth(wheel, mark), answers: answers(wheel, mark), verdicts: verdicts(wheel, mark), words: depthWords(wheel, mark) }};
}}
let refused = false;
try {{ depth("bus", "rim"); }} catch (error) {{ refused = true; }}
console.log(JSON.stringify({{ out, refused }}));
"""
    ran = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
    result = json.loads(ran.stdout)
    assert result["refused"] and len(result["out"]) == len(wheel.WHEELS) * len(wheel.MARKS)
    for key, got in result["out"].items():
        name, mark = key.split()
        assert tuple(got["depth"]) == wheel.depth(name, mark), key
        assert got["answers"] == wheel.answers(name, mark), key
        assert [v["ruledOut"] for v in got["verdicts"]] == [wheel.answers(name, mark)[c] == bands.NOT_SAFE for c in ("two_wheeler", "auto", "car", "suv", "pedestrian")]
        assert {v["word"] for v in got["verdicts"]} <= {"Not safe", "Unsure: treat as not safe"}, key      # never a word that clears a road
    assert result["out"]["car rim"]["words"] == "12 to 20 cm" and result["out"]["car tyre"]["words"] == "Under 12 cm"
    assert result["out"]["scooter over"]["words"] == "Over 43 cm"


def test_the_code_refuses_to_show_a_road_as_passable():
    assert 'throw new Error("a wheel alone must never clear a road")' in JS
    assert "Passable" not in JS.replace("PASSABLE", "") and "passable with care" not in PAGE.lower()


def test_the_page_asks_two_things_and_says_what_it_cannot_do():
    assert '<html lang="en">' in PAGE and len(re.findall(r"<h1[ >]", PAGE)) == 1
    assert re.search(r'<meta name="viewport" content="width=device-width, initial-scale=1', PAGE)
    flat = " ".join(PAGE.split())
    for must_say in ("It never says who may", "Do not walk or ride into water to look", "Do not enter moving water at any depth",
                     "Nobody has yet tested how well people read a wheel this way", "Nothing you choose here is sent anywhere"):
        assert must_say in flat, must_say
    assert PAGE.count("<fieldset") == 2 and PAGE.count("<legend") == 2           # two questions, each named
    assert 'role="status" aria-live="polite"' in PAGE                             # the answer is announced when it changes
    assert 'type="radio"' in JS and "<label" in JS                                # every choice is a real radio inside its label
    assert "fetch(" not in JS and "XMLHttpRequest" not in JS and "sendBeacon" not in JS      # nothing is sent


def test_the_page_can_be_reached_and_is_kept_for_when_there_is_no_signal():
    worker = (WEB / "sw.js").read_text("utf-8")
    shell = re.search(r"const SHELL = \[(.*?)\];", worker, re.S).group(1)
    for name in ("wheel.html", "wheel.css", "wheel.js"):
        assert f'"{name}"' in shell, name
    assert 'navigator.serviceWorker.register("sw.js")' in PAGE
    assert 'href="wheel.html"' in (WEB / "guide.js").read_text("utf-8")           # from the key on the map
    assert 'href="./"' in PAGE                                                    # and back


def test_every_choice_is_big_enough_for_a_thumb():
    css = (WEB / "wheel.css").read_text("utf-8")
    block = re.search(r"\.pick-one \{([^}]*)\}", css).group(1)
    assert "min-height: var(--touch)" in block
    assert "font-size" not in css                                                 # every size comes from the shared sheets
