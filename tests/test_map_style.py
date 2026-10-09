"""web/style.json may only use colours that are tokens in web/tokens.css.

MapLibre cannot read CSS variables, so the map style repeats the hex values. This keeps the
two in step: change a token and forget the style, or the other way round, and this fails.
"""

import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def test_every_colour_in_the_map_style_is_a_token():
    tokens = {v.upper() for v in re.findall(r"--[a-z-]+:\s*(#[0-9A-Fa-f]{6});",
                                            (WEB / "tokens.css").read_text("utf-8"))}
    style = (WEB / "style.json").read_text("utf-8")
    used = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}", style)}
    assert used and used <= tokens, f"not tokens: {sorted(used - tokens)}"


def test_the_style_is_valid_and_keeps_water_the_only_colour():
    style = json.loads((WEB / "style.json").read_text("utf-8"))
    assert style["version"] == 8 and style["layers"][0]["type"] == "background"
    ids = [layer["id"] for layer in style["layers"]]
    assert len(ids) == len(set(ids))
    # The flood palette is for flood water. None of it may appear in the ground.
    flood = {"#7FB7BE", "#2F7F93", "#134B66", "#E4572E", "#8A9A5B"}
    assert not flood & {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}", json.dumps(style))}
