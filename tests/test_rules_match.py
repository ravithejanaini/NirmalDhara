"""The browser rules (web/rules.js) must give the same answers as src/nirmaldhara/bands.py.

Three checks, each catching a different kind of drift:
- the case file is what bands.py produces now (bands.py changed, cases not regenerated);
- the numbers in rules.js are the numbers in bands.py (a constant edited on one side);
- if Node is installed, rules.js is run on every case (logic edited on one side).
web/rules-check.html does the last check in a browser.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nirmaldhara import bands

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_rule_cases  # noqa: E402


def test_case_file_matches_bands_py():
    stored = json.loads((ROOT / "data" / "rule-cases.json").read_text(encoding="utf-8"))
    assert stored == json.loads(json.dumps(make_rule_cases.build())), \
        "bands.py changed: run python scripts/make_rule_cases.py"
    assert len(stored["cases"]) == 400


def js_constant(name):
    text = (ROOT / "web" / "rules.js").read_text(encoding="utf-8")
    match = re.search(rf"export const {name} = (.+?);\n", text)
    assert match, name
    return json.loads(re.sub(r"([{,]\s*)(\w+):", r'\1"\2":', match.group(1)))


def test_constants_in_rules_js_match_bands_py():
    assert js_constant("BAND_EDGES_CM") == [list(e) for e in bands.BAND_EDGES_CM]
    assert js_constant("NO_GO_CM") == bands.NO_GO_CM
    assert js_constant("NO_ANSWER_CLASSES") == list(bands.NO_ANSWER_CLASSES)
    assert js_constant("EVERYONE_NO_GO_CM") == bands.EVERYONE_NO_GO_CM
    assert js_constant("MIN_CONFIDENCE") == bands.MIN_CONFIDENCE
    assert js_constant("MOVING_NO_GO_CM") == bands.MOVING_NO_GO_CM
    for name in ("PASSABLE", "NOT_SAFE", "UNKNOWN", "NO_ANSWER"):
        assert js_constant(name) == getattr(bands, name)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
def test_rules_js_gives_every_stored_answer(tmp_path):
    runner = tmp_path / "run.mjs"
    runner.write_text(f"""
import {{ readFileSync }} from "node:fs";
import {{ bandFor, passability }} from "{(ROOT / 'web' / 'rules.js').as_uri()}";
const {{ cases }} = JSON.parse(readFileSync({json.dumps(str(ROOT / 'data' / 'rule-cases.json'))}, "utf8"));
let bad = 0;
for (const c of cases) {{
  const a = passability(c.low, c.high, c.confidence, c.moving);
  if (bandFor(c.high) !== c.band || JSON.stringify(a) !== JSON.stringify(c.answers)) bad++;
}}
console.log(JSON.stringify({{ total: cases.length, bad }}));
""", encoding="utf-8")
    out = subprocess.run(["node", str(runner)], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == {"total": 400, "bad": 0}
