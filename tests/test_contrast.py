"""Every colour pairing the pages use meets its contrast minimum (web/contrast-pairs.json).

The colours are read from web/tokens.css, so changing a token there is what this checks.
web/styleguide.html computes the same ratios in the browser.
"""

import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
TOKENS = dict(re.findall(r"--([a-z-]+):\s*(#[0-9A-Fa-f]{6});", (WEB / "tokens.css").read_text("utf-8")))
PAIRS = json.loads((WEB / "contrast-pairs.json").read_text("utf-8"))["pairs"]


def luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_the_formula_on_known_values():
    assert ratio("#000000", "#FFFFFF") == pytest.approx(21)
    assert ratio("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: f"{p['fg']} on {p['bg']} ({p['min']})")
def test_pair_meets_its_minimum(pair):
    value = ratio(TOKENS[pair["fg"]], TOKENS[pair["bg"]])
    if pair["min"] is not None:
        assert value >= pair["min"], f"{value:.2f} to 1; needs {pair['min']}: {pair['use']}"


def test_text_colours_in_base_css_are_all_listed():
    """A colour given to text in base.css must have its pairing listed, so it is checked."""
    css = (WEB / "base.css").read_text("utf-8")
    listed = {(p["fg"], p["bg"]) for p in PAIRS}
    for selector, name in re.findall(r"([^{}]+)\{[^{}]*?\bcolor:\s*var\(--([a-z-]+)\)", css):
        selector = selector.strip().splitlines()[-1]
        if ":hover" in selector:
            continue                        # hover swaps to the opposite ground, both listed
        ground = "paper" if ".paper" in selector and selector.strip() != ".paper" else "night"
        if selector.strip() in (".paper",):
            ground = "paper"
        assert (name, ground) in listed, f"{selector}: {name} on {ground} is not in contrast-pairs.json"
