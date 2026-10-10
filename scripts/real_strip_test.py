"""REAL VIDEO: three checks of the waterline detector on steady stretches of licensed news footage.

    python scripts/real_strip_test.py          # prints the results and writes docs/waterline-real.md

The frames are cut from two clips listed in samples/footage/CREDITS.md. They are not in the
repository. To make them (any ffmpeg will do):

    ffmpeg -ss 39.25 -t 2.5 -i samples/footage/izJR0sCbfPg.mp4 -q:v 1 samples/footage/frames/compound/%04d.jpg
    ffmpeg -ss 75.05 -t 2.7 -i samples/footage/izJR0sCbfPg.mp4 -q:v 1 samples/footage/frames/street/%04d.jpg

What is checked, and what is real in each:

    1  nothing changed    Real video of things that do not move, hand-held, compressed, one shot in rain.
                          The first frames are the "dry view", later frames the reading. Nothing has
                          changed, so no waterline may be reported.
    2  a made line        A real surface (a fence, a gate) in real video, with real moving water from
                          the same frames put over its lower part from a chosen row down. Both sides of
                          the line are real pixels; only where the line is has been made up, so it is known.
    3  a real line        A fence and a gate standing in real flood water. There is no dry view of
                          them, so only the clip mode (flicker) can be used. The true line was marked by
                          eye on one frame before the detector was run on this shot.

None of this is a depth: nothing in these pictures has a known size. It is about finding the line.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import waterline  # noqa: E402

FRAMES = ROOT / "samples" / "footage" / "frames"
OUT = ROOT / "docs" / "waterline-real.md"
NOTES = ROOT / "docs" / "waterline-real-notes.md"
WIDTH = 36
HAND = 6                              # pixels each way a hand-held shot is allowed to move
# Two ways of cutting a reading out of a shot. In the first the camera has hardly moved between the dry
# view and the reading, as on a pole. In the second a hand has drifted it by a few pixels, and not
# evenly: the top and bottom of a strip move by different amounts, which no single shift undoes.
SPANS = {
    "camera nearly still (0.4 s)": [(slice(start, start + 6), list(range(start + 6, start + 12))) for start in (0, 12, 24, 36, 48, 60)],
    "hand-held drift (2 s)": [(slice(0, 12), list(range(24, 60, 6))), (slice(0, 12), list(range(33, 69, 6)))],
}
# Check 1: strips of things that do not move: a gate's panel, a fence above the water, the fronts of
# buildings. (shot, left edge, top row, bottom row)
STILL = ([("compound", x, 140, 380) for x in (900, 1000, 1150)] + [("compound", x, 330, 530) for x in (40, 100)]
         + [("street", x, top, top + 240) for x in (950, 1050, 1180) for top in (120, 360)]
         + [("street", x, 40, 280) for x in (20, 120)])
# Check 2: real surfaces in the compound shot, all above the real water. (name, left edge, top row, bottom row)
SURFACES = [("fence, left", 40, 330, 540), ("fence, middle", 100, 320, 530), ("gate panel", 900, 150, 390)]
WATER_COLUMNS = (330, 480, 620)       # where the water put over them is taken from, from row 480 down
MADE_LINES = (70, 100, 130, 160)
# Check 3: the real line. (name, left edge, width, top row, bottom row, the line marked by eye, how sure in rows)
# Marked on frame 30 of the compound shot, from a four-times enlargement, before the detector was run on it.
REAL_LINES = [("fence, left", 40, 20, 330, 620, 562, 3), ("fence, middle", 100, 20, 330, 620, 555, 3),
              ("fence, right", 170, 20, 330, 620, 540, 3), ("gate bars", 900, 30, 400, 600, 523, 6)]
CLIPS = {"six frames in a row (0.2 s)": [list(range(start, start + 6)) for start in range(0, 66, 12)],
         "six frames over 1.2 s": [list(range(start, start + 36, 6)) for start in range(0, 37, 12)]}


def load(shot):
    """Every frame of a shot, 8-bit: (frames, rows, columns, 3)."""
    files = sorted((FRAMES / shot).glob("*.jpg"))
    if not files:
        raise SystemExit(f"No frames in {FRAMES / shot}. See the top of this file for how to cut them.")
    return np.array([np.asarray(Image.open(path).convert("RGB")) for path in files])


def steady(strip):
    """A hand-held strip, lined up frame to frame on its top fifth."""
    return waterline.stabilise(strip.astype(np.float32), HAND)


def nothing_changed(shots):
    """{span: [(shot, left edge, top row, what was reported, whether it was a line)]}"""
    out = {span: [] for span in SPANS}
    for shot, x, top, bottom in STILL:
        strip = steady(shots[shot][:, top:bottom, x:x + WIDTH])
        for span, cuts in SPANS.items():
            for dry_view, frames in cuts:
                result = waterline.locate(strip[[t for t in frames if t < len(strip)]], strip[dry_view])
                out[span].append((shot, x, top, result.reason if not result.found else "line", result.found))
    return out


def made_line(compound):
    """{span: [(surface, row the line was put at, result)]}"""
    out = {span: [] for span in SPANS}
    for name, x, top, bottom in SURFACES:
        surface = steady(compound[:, top:bottom, x:x + WIDTH])
        rows = bottom - top
        for water_x in WATER_COLUMNS:
            for line in MADE_LINES:
                frames = surface.copy()
                frames[:, line:] = compound[:, 480:480 + rows - line, water_x:water_x + WIDTH]
                for span, cuts in SPANS.items():
                    for dry_view, reading in cuts:
                        out[span].append((name, line, waterline.locate(frames[reading], surface[dry_view])))
    return out


def real_line(compound):
    """{way of cutting the clip: [(strip, row marked by eye, how sure, row the detector gave or None)]}"""
    out = {way: [] for way in CLIPS}
    for name, x, width, top, bottom, marked, sure in REAL_LINES:
        strip = steady(compound[:, top:bottom, x:x + width])
        for way, cuts in CLIPS.items():
            for frames in cuts:
                result = waterline.locate(strip[frames])                         # no dry view: the clip mode
                out[way].append((name, marked, sure, top + result.row if result.found else None))
    return out


def report(still, made, real):
    lines = [
        "# The waterline detector on real video",
        "",
        "**Real video, but not a real measurement of depth.** Written by `scripts/real_strip_test.py` on steady",
        "stretches of a licensed news clip ([credits](../samples/footage/CREDITS.md)). The frames are not in",
        "the repository. Nothing in these pictures has a known size, so this is about finding the line, in",
        "rows of the picture, not about centimetres.",
        "",
        "The footage is hand-held. Each check is run twice: with the reading cut so close to the dry view that",
        "the camera has hardly moved, which is what a camera on a pole gives, and with two seconds between them,",
        "over which a hand drifts the picture by a few pixels and not evenly.",
        "",
        "## 1. Nothing changed: no waterline may be reported",
        "",
        f"{len(STILL)} strips of things that do not move (a gate's panel, a fence above the water, the fronts of",
        "buildings, one shot in rain). The first frames are the dry view, later frames the reading.",
        "",
        "| | Readings | A waterline was reported | Reported dry | Withheld |",
        "|---|---|---|---|---|",
    ]
    for span, rows in still.items():
        wrong = sum(1 for row in rows if row[4])
        dry = sum(1 for row in rows if row[3] == "dry")
        lines.append(f"| {span} | {len(rows)} | **{wrong}** ({wrong / len(rows):.0%}) | {dry} | {len(rows) - wrong - dry} |")
    lines += [
        "",
        "## 2. A made line between real pixels",
        "",
        "A real fence and a real gate, with real moving flood water from the same frames put over the lower",
        f"part of each from a chosen row down: {len(SURFACES)} surfaces, {len(WATER_COLUMNS)} patches of water, {len(MADE_LINES)} lines.",
        "Both sides of the line are real video; where the line is, is known.",
        "",
        "| | Readings | Line reported | Typical error, rows | 95% under | Worst | True line inside the 90% interval |",
        "|---|---|---|---|---|---|---|",
    ]
    for span, rows in made.items():
        found = [row for row in rows if row[2].found]
        if not found:
            lines.append(f"| {span} | {len(rows)} | 0 | | | | |")
            continue
        errors = np.array([abs(row[2].row - row[1]) for row in found])
        inside = sum(1 for row in found if row[2].low <= row[1] <= row[2].high)
        lines.append(f"| {span} | {len(rows)} | {len(found)} ({len(found) / len(rows):.0%}) | {np.median(errors):.1f} | "
                     f"{np.percentile(errors, 95):.1f} | {errors.max():.1f} | {inside} of {len(found)} ({inside / len(found):.0%}) |")
    lines += [
        "",
        "What this is not: the water was put there, so it has no reflection of the fence in it and no wet edge",
        "where they meet. A real line has both.",
        "",
        "## 3. A real line, with no dry view",
        "",
        "A fence and a gate standing in real flood water. No dry view of them exists, so only the clip mode can",
        "run: six frames, flicker only. The true line was marked by eye on one enlarged frame before the detector",
        "was run on this shot.",
        "",
        "| Strip | Marked by eye | " + " | ".join(real) + " |",
        "|---|---|" + "---|" * len(real),
    ]
    for name, _, _, _, _, marked, sure in REAL_LINES:
        cells = []
        for rows in real.values():
            mine = [row[3] for row in rows if row[0] == name]
            seen = [value for value in mine if value is not None]
            cells.append((", ".join(f"{value:.0f}" for value in seen) or "no line")
                         + (f"; {len(mine) - len(seen)} not reported" if seen and len(seen) < len(mine) else ""))
        lines.append(f"| {name} | {marked} ± {sure} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "The readings of a strip overlap or follow each other within one shot, so they are one piece of evidence, not several.",
        "",
    ]
    return "\n".join(lines)


def main():
    shots = {shot: load(shot) for shot in ("compound", "street")}
    text = report(nothing_changed(shots), made_line(shots["compound"]), real_line(shots["compound"]))
    OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
