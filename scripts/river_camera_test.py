"""REAL FLOOD, MEASURED LEVELS: the waterline detector on fixed river cameras, Tewkesbury, November 2012.

    python scripts/river_camera_test.py                 # prints the results and writes docs/waterline-river.md
    python scripts/river_camera_test.py --camera Tewkesbury

The pictures are the hourly images of four river cameras through a real flood, published with the
water level that the dataset's authors read from each against surveyed points (credits and licence in
samples/tewkesbury/CREDITS.md). The pictures are not in the repository; the levels are, in
data/tewkesbury-levels.json. To get the pictures, download the dataset (doi:10.17632/769cyvdznp.1)
into samples/tewkesbury/data/.

What is done with each camera:

    1  A strip of the picture is chosen once, by eye, running from ground that stays dry to water that
       is always there. The pictures of one day at low water are taken as the dry view.
    2  Every other picture with a measured level is given to the detector, one frame at a time.
    3  The row it reports is turned into a level by a rising-only curve fitted on half of the days and
       judged on the other half, then the other way round. So the error is always on days the curve
       did not see.

This is harder than what the detector was built for, in three ways. There is one frame an hour, so
nothing can be learnt from flicker, and nothing is lined up between frames. The dry view is from
another day, in other light. And the water's edge here runs across ground and structures, not up one
vertical surface.

One camera was used to find out how to use the detector here, and is marked so. The other was run with
a strip fixed beforehand.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import waterline  # noqa: E402

DATA = ROOT / "samples" / "tewkesbury" / "data"
LEVELS = ROOT / "data" / "tewkesbury-levels.json"
OUT = ROOT / "docs" / "waterline-river.md"
NOTES = ROOT / "docs" / "waterline-river-notes.md"
# box: left, top, right, bottom in the picture (2048 x 1536). shrink: the strip is averaged over this many pixels
# each way. from_bottom: the dry ground is at the bottom of the box, so
# the strip is read upwards. dry_view: month, day, and the hours of the pictures that together make the dry view.
CAMERAS = {
    "Tewkesbury": {"role": "used to find out how to use the detector here", "box": (1400, 700, 1508, 1536), "shrink": 3,
                   "from_bottom": True, "dry_view": (11, 21, (9, 10, 11, 12, 13, 14)),
                   "scene": "a grass bank in the foreground, read from the near side up to the river"},
    "Strensham": {"role": "run once, with the strip fixed beforehand", "box": (690, 300, 798, 1140), "shrink": 3,
                  "from_bottom": False, "dry_view": (12, 3, (10, 11, 12, 13, 14)),
                  "scene": "a lock: far fields at the top, the gates and walls, then the water in the foreground"},
}


def strip_of(path, camera):
    """The camera's strip from one picture: (rows, columns, 3), dry end first."""
    left, top, right, bottom = CAMERAS[camera]["box"]
    pixels = np.asarray(Image.open(path).convert("RGB").crop((left, top, right, bottom)), dtype=np.float32)
    shrink = CAMERAS[camera]["shrink"]
    rows, columns = pixels.shape[0] // shrink, pixels.shape[1] // shrink
    small = pixels[:rows * shrink, :columns * shrink].reshape(rows, shrink, columns, shrink, 3).mean(axis=(1, 3))
    return small[::-1] if CAMERAS[camera]["from_bottom"] else small


def readings(camera, data=DATA):
    """Every picture with a measured level, read by the detector: a list of dicts."""
    table = json.loads(LEVELS.read_text("utf-8"))["cameras"][camera]
    folder = Path(data) / "FarsonDigital_CameraImages_NovDec2012" / table["folder"]
    stamp = {(r["month"], r["day"], r["hour"]): r for r in table["readings"]}
    month, day, hours = CAMERAS[camera]["dry_view"]
    dry = [stamp[(month, day, hour)] for hour in hours if (month, day, hour) in stamp and stamp[(month, day, hour)]["image"]]
    dry_view = np.array([strip_of(folder / row["image"], camera) for row in dry])
    out = []
    for key, row in sorted(stamp.items()):
        if row["level_m"] is None or row["image"] is None or (key[:2] == (month, day) and key[2] in hours):
            continue
        result = waterline.locate(strip_of(folder / row["image"], camera), dry_view)
        out.append({"day": (key[0], key[1]), "hour": key[2], "level": row["level_m"], "std": row["std_m"],
                    "found": result.found, "row": result.row, "low": result.low, "high": result.high, "reason": result.reason})
    return out, [row["level_m"] for row in dry if row["level_m"] is not None]


def rising_curve(rows, levels):
    """A curve of level against row that only ever goes one way, fitted by pooling neighbours that
    disagree with that. Returns a function from row to level."""
    rows, levels = np.asarray(rows, dtype=float), np.asarray(levels, dtype=float)
    order = np.argsort(rows)
    x, y = rows[order], levels[order]
    if np.corrcoef(x, y)[0, 1] < 0:                           # the level falls as the row grows: fit the mirror image
        return (lambda fit: lambda r: -fit(r))(rising_curve(rows, -levels))
    blocks = [[value, 1, position] for value, position in zip(y, x)]       # mean level, count, mean row
    merged = []
    for block in blocks:
        merged.append(block)
        while len(merged) > 1 and merged[-2][0] > merged[-1][0]:
            high, low = merged.pop(), merged.pop()
            count = high[1] + low[1]
            merged.append([(high[0] * high[1] + low[0] * low[1]) / count, count, (high[2] * high[1] + low[2] * low[1]) / count])
    at, value = np.array([b[2] for b in merged]), np.array([b[0] for b in merged])
    return lambda r: np.interp(r, at, value)


def judged(found):
    """Errors in metres on days the curve did not see: fitted on odd days and judged on even, then the
    other way round. Also the errors of always guessing the middle level of the days fitted on."""
    errors, guesses = [], []
    for parity in (0, 1):
        seen = [r for r in found if r["day"][1] % 2 == parity]
        unseen = [r for r in found if r["day"][1] % 2 != parity]
        if len(seen) < 5 or not unseen:
            continue
        curve = rising_curve([r["row"] for r in seen], [r["level"] for r in seen])
        middle = float(np.median([r["level"] for r in seen]))
        errors += [abs(float(curve(r["row"])) - r["level"]) for r in unseen]
        guesses += [abs(middle - r["level"]) for r in unseen]
    return np.array(errors), np.array(guesses)


def in_order(found):
    """Of all pairs of readings whose measured levels differ by more than their stated error, the share
    the detector put in the right order."""
    right = total = 0
    rows, levels = np.array([r["row"] for r in found]), np.array([r["level"] for r in found])
    stds = np.array([r["std"] or 0.0 for r in found])
    sign = np.sign(np.corrcoef(rows, levels)[0, 1])
    for i in range(len(found)):
        apart = np.abs(levels - levels[i]) > stds + stds[i]
        apart[:i + 1] = False
        total += int(apart.sum())
        right += int((np.sign(rows[apart] - rows[i]) == sign * np.sign(levels[apart] - levels[i])).sum())
    return right / max(1, total), total


def summary(camera, out, dry_level):
    found = [r for r in out if r["found"]]
    reasons = {}
    for r in out:
        if not r["found"]:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    errors, guesses = judged(found) if len(found) >= 12 else (np.array([]), np.array([]))
    share, pairs = in_order(found) if len(found) >= 3 else (float("nan"), 0)
    stds = [r["std"] for r in out if r["std"] is not None]
    return {"camera": camera, "pictures": len(out), "found": len(found), "reasons": reasons, "errors": errors, "guesses": guesses,
            "in_order": share, "pairs": pairs, "levels": (min(r["level"] for r in out), max(r["level"] for r in out)),
            "found_levels": (min(r["level"] for r in found), max(r["level"] for r in found)) if found else None,
            "std": float(np.median(stds)) if stds else float("nan"), "dry_level": dry_level}


def report(summaries):
    lines = [
        "# The waterline detector on a real flood",
        "",
        "**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_camera_test.py` on the",
        "hourly pictures of river cameras near Tewkesbury, 21 November to 5 December 2012, published with the water",
        "level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The",
        "pictures are not in the repository. This is a river, not a street, and not Hyderabad.",
        "",
        "One frame an hour, a dry view from another day, and a water's edge that runs across ground and structures:",
        "each of these is outside what the detector was built for. The row it reports is turned into a level by a",
        "rising-only curve fitted on half of the days, and the error is measured on the other half.",
        "",
        "| Camera | | Pictures with a measured level | Line reported | Withheld | Pairs put in the right order | Error on days not fitted, typical | 90% under | Guessing the middle level | The dataset's own error |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        withheld = ", ".join(f"{count} {reason}" for reason, count in sorted(s["reasons"].items())) or "none"
        error = (f"{100 * np.median(s['errors']):.0f} cm | {100 * np.percentile(s['errors'], 90):.0f} cm | "
                 f"{100 * np.median(s['guesses']):.0f} cm") if len(s["errors"]) else "too few lines | | "
        lines.append(f"| {s['camera']} | {CAMERAS[s['camera']]['role']} | {s['pictures']}, {s['levels'][0]:.2f} to {s['levels'][1]:.2f} m | "
                     f"{s['found']} ({s['found'] / s['pictures']:.0%}) | {withheld} | {s['in_order']:.0%} of {s['pairs']} | {error} | "
                     f"± {100 * s['std']:.0f} cm typical |")
    lines += ["", "Each camera's strip, and the picture taken as its dry view:", ""]
    for s in summaries:
        camera = CAMERAS[s["camera"]]
        month, day, hours = camera["dry_view"]
        seen = "none" if s["found_levels"] is None else f"{s['found_levels'][0]:.2f} to {s['found_levels'][1]:.2f} m"
        low = f"{min(s['dry_level']):.2f} to {max(s['dry_level']):.2f} m" if s["dry_level"] else "below what could be measured"
        lines.append(f"- **{s['camera']}**: {camera['scene']}. Columns {camera['box'][0]} to {camera['box'][2]}, rows {camera['box'][1]} to "
                     f"{camera['box'][3]}. Dry view: the {len(hours)} pictures of {day}/{month} from {hours[0]}:00 to {hours[-1]}:00, level "
                     f"{low}. Lines were reported at levels from {seen}.")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--camera", choices=sorted(CAMERAS), action="append")
    parser.add_argument("--data", default=str(DATA))
    args = parser.parse_args()
    if not (Path(args.data) / "FarsonDigital_CameraImages_NovDec2012").is_dir():
        print(f"The pictures are not in {args.data}. See the top of this file for where to get them.")
        return 1
    summaries = [summary(camera, *readings(camera, args.data)) for camera in (args.camera or CAMERAS)]
    text = report(summaries)
    print(text)
    if not args.camera:
        OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
