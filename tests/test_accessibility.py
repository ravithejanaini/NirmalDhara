"""Static guards for what was checked by hand in a browser (TASKS.md WEB-09).

These read the pages and style sheets. They cannot replace a person with a screen reader or a real
phone, and say so: they stop the specific faults found from coming back.
"""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = ["index.html", "offenders.html", "wheel.html", "styleguide.html", "glyph-gallery.html"]
CSS = sorted(WEB.glob("*.css"))
FLOOR_REM = 0.875                       # 14 px


def text(name):
    return (WEB / name).read_text("utf-8")


@pytest.mark.parametrize("page", PAGES)
def test_every_page_declares_its_language_scaling_and_title(page):
    html = text(page)
    assert '<html lang="en">' in html
    assert re.search(r'<meta name="viewport" content="width=device-width, initial-scale=1', html)
    assert re.search(r"<title>[^<]{3,}</title>", html)
    assert "user-scalable=no" not in html and "maximum-scale=1" not in html     # never block pinch zoom


@pytest.mark.parametrize("page", ["index.html", "offenders.html", "wheel.html"])
def test_the_public_pages_have_exactly_one_h1(page):
    assert len(re.findall(r"<h1[ >]", text(page))) == 1


def test_the_controls_come_before_the_map_in_the_page_so_the_keyboard_reaches_them_first():
    html = text("index.html")
    position = {k: html.index(k) for k in ('class="masthead"', 'id="guide"', 'id="map"', 'id="sheet"')}
    assert position['class="masthead"'] < position['id="guide"'] < position['id="map"'] < position['id="sheet"']


def rem(value):
    return float(value[:-3]) if value.endswith("rem") else float(value[:-2]) / 16


def test_no_text_is_set_below_fourteen_pixels_except_the_legal_credit():
    below = []
    for path in CSS:
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", path.read_text("utf-8")):
            for value in re.findall(r"font-size:\s*([\d.]+(?:rem|px))", body):
                if rem(value) < FLOOR_REM - 1e-9 and "ctrl-attrib" not in selector:
                    below.append((path.name, selector.strip().splitlines()[-1], value))
    assert below == []
    # inside the cross-section the type is set in drawing units; at phone width it must still reach 14 px
    section = text("sheet.css")
    units = float(re.search(r"\.section-limit text \{[^}]*font-size:\s*([\d.]+)px", section).group(1))
    assert units * 328 / 420 >= 14                                              # a 360 px phone: 328 px wide


def test_the_touch_target_token_is_forty_four_pixels_and_the_controls_use_it():
    tokens = text("tokens.css")
    assert re.search(r"--touch:\s*2\.75rem", tokens)
    combined = "".join(p.read_text("utf-8") for p in CSS)
    for selector in (".site-marker", ".sheet-close", ".key-button", ".button", ".back", ".masthead-link"):
        block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", combined)
        assert block and "var(--touch)" in block.group(1), selector


def test_the_sheets_close_button_is_pinned_where_a_thumb_reaches_it():
    css = text("sheet.css")
    block = re.search(r"\.sheet-done \{([^}]*)\}", css).group(1)
    assert "position: sticky" in block and "bottom:" in block
    assert re.search(r"@media \(min-width: 46rem\)\s*\{\s*\.sheet-done\s*\{\s*display: none", css)   # hidden on wide screens
    assert ".sheet-grab" in css and "touch-action: none" in css


def test_the_sheet_handle_is_tappable_not_only_drawn():
    js = text("sheet.js")
    assert "sheet-grab" in js and "pointerdown" in js and "dy >= 80" in js


@pytest.mark.parametrize("sheet", ["tokens.css", "base.css", "glyph.css", "sheet.css"])
def test_every_style_sheet_that_moves_things_also_switches_it_off(sheet):
    css = text(sheet)
    moves = re.search(r"\b(animation|transition)\s*:", css) is not None
    if moves and sheet not in ("tokens.css", "base.css"):
        assert "prefers-reduced-motion: reduce" in css, sheet


def test_reduced_motion_zeroes_the_shared_durations_and_stops_everything_else():
    tokens, base = text("tokens.css"), text("base.css")
    block = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{\s*:root\s*\{([^}]*)\}", tokens).group(1)
    for name in ("--rise", "--drift", "--quick"):
        assert re.search(name + r":\s*0", block), name
    assert "animation-duration: 0.001ms !important" in base and "transition-duration: 0.001ms !important" in base
    assert "prefers-reduced-motion" in text("sheet.js")                          # the close delay
    assert "prefers-reduced-motion: reduce" in text("section.js") or "prefers-reduced-motion: reduce" in text("sheet.css")


def test_focus_is_visible_and_never_removed_without_a_replacement():
    css = "".join(p.read_text("utf-8") for p in CSS)
    assert ":focus-visible" in css
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "outline: none" in body or "outline:none" in body:
            # allowed only where a script sends focus to a heading so it can be announced
            assert "h2" in selector or "title" in selector, selector


def test_every_icon_only_button_has_a_name():
    sheet_js, guide_js = text("sheet.js"), text("guide.js")
    assert 'class="sheet-close" type="button" aria-label="Close"' in sheet_js
    assert 'aria-label="Close the key"' in guide_js
    assert 'role: "img"' in text("glyph.js") and "aria-label" in text("section.js")
