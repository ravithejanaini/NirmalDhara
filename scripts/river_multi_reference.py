"""REAL FLOOD, MEASURED LEVELS: one camera, several reference surfaces, read together.

    python scripts/river_multi_reference.py                 # prints the results and writes docs/multi-reference-river.md
    python scripts/river_multi_reference.py --camera Tewkesbury

The same pictures and levels as scripts/river_camera_test.py (credits and licence in
samples/tewkesbury/CREDITS.md; the pictures are not in the repository). There the waterline
detector read each camera through one strip. Here it reads the same camera through several strips,
each on a different surface that the water climbs, and nirmaldhara.multiview.combine joins them.
The question is the one METHOD.md C5 leaves open: does reading several reference objects in one
view give a closer depth than reading one?

What is done with each camera:

    1  Several strips are chosen once, by eye, on the dry view only. Each is read by the detector
       exactly as before, one frame at a time.
    2  Half of the days are learnt from. On those, each strip gets its own curve from row to level,
       and its own record: how far out that curve was on each learnt day when that day was left
       out. The record sets how much the strip counts for, and how wide its range is.
    3  On the other half of the days, every strip that reports a line gives a level and a range,
       and they are joined. The level is the weighted middle one of three or more, and the
       weighted mean of two. The range is the middle one when three or more agree, and the
       cautious one otherwise. Then the halves are swapped.

One camera was used to work out how to join strips, and is marked so. On the other, the three new
strips were fixed on its dry view before any of its other pictures had been read through them, and
it was run once. Its first strip is the one river_camera_test.py used, whose figures were known.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import river_camera_test as river  # noqa: E402
from nirmaldhara import multiview, waterline  # noqa: E402

OUT = ROOT / "docs" / "multi-reference-river.md"
NOTES = ROOT / "docs" / "multi-reference-river-notes.md"
FEW = 12                           # a strip needs this many lines on the learnt days to be given a curve
RANGE_SHARE = 80                   # a strip's range is as wide as this share of its left-out errors
# name: (box left, top, right, bottom; dry ground at the bottom?; what the strip runs over)
STRIPS = {
    "Tewkesbury": {
        "role": "used to work out how to join strips",
        "strips": {
            "A": ((1400, 700, 1508, 1536), True, "the grass bank, right of the tables (the strip used before)"),
            "B": ((300, 700, 408, 1536), True, "the gravel and grass at the left"),
            "C": ((1620, 700, 1728, 1536), True, "the grass bank at the far right"),
        },
    },
    "Strensham": {
        "role": "run once, with the new strips fixed beforehand",
        "strips": {
            "A": ((690, 300, 798, 1140), False, "the lock gates (the strip used before)"),
            "B": ((266, 300, 374, 1140), False, "the left lock wall and its red marker post"),
            "C": ((986, 300, 1094, 1140), False, "the right bank and its white post"),
            "D": ((1200, 300, 1308, 1140), False, "the steps down to the water"),
        },
    },
}


def read_strip(camera, name, data=river.DATA):
    """Every picture with a measured level, read through one strip: {(month, day, hour): reading}."""
    box, from_bottom, _ = STRIPS[camera]["strips"][name]
    return read_box(camera, box, from_bottom, data)


def read_box(camera, box, from_bottom, data=river.DATA):
    """The same for any box in the camera's picture: dry ground at the bottom of it, or at the top."""
    river.CAMERAS["__strip__"] = {"box": box, "shrink": 3, "from_bottom": from_bottom}
    table = json.loads(river.LEVELS.read_text("utf-8"))["cameras"][camera]
    folder = Path(data) / "FarsonDigital_CameraImages_NovDec2012" / table["folder"]
    stamp = {(r["month"], r["day"], r["hour"]): r for r in table["readings"]}
    month, day, hours = river.CAMERAS[camera]["dry_view"]
    dry = [stamp[(month, day, hour)] for hour in hours if (month, day, hour) in stamp and stamp[(month, day, hour)]["image"]]
    dry_view = np.array([river.strip_of(folder / row["image"], "__strip__") for row in dry])
    out = {}
    for key, row in sorted(stamp.items()):
        if row["level_m"] is None or row["image"] is None or (key[:2] == (month, day) and key[2] in hours):
            continue
        result = waterline.locate(river.strip_of(folder / row["image"], "__strip__"), dry_view)
        out[key] = {"day": (key[0], key[1]), "hour": key[2], "level": row["level_m"], "std": row["std_m"],
                    "found": bool(result.found), "row": float(result.row) if result.found else None, "reason": result.reason}
    return out


def record(found):
    """A strip's curve from row to level on the days learnt from, and how far out it was on each of
    those days when that day was left out: (curve, errors in metres). None if there is too little."""
    days = sorted({r["day"] for r in found})
    if len(found) < FEW or len(days) < 3:
        return None
    errors = []
    for day in days:
        rest = [r for r in found if r["day"] != day]
        if len(rest) < 5:
            continue
        curve = river.rising_curve([r["row"] for r in rest], [r["level"] for r in rest])
        errors += [abs(float(curve(r["row"])) - r["level"]) for r in found if r["day"] == day]
    if len(errors) < 5:
        return None
    return river.rising_curve([r["row"] for r in found], [r["level"] for r in found]), np.array(errors)


def joined(readings):
    """Every unseen picture, with what each strip said and what they say together.

    readings: {strip: {key: reading}}. Returns [{key, level, std, alone: {strip: level}, together, low, high, agreed, used}].
    """
    out = []
    for parity in (0, 1):
        learnt = {}
        for name, by_key in readings.items():
            kept = record([r for r in by_key.values() if r["found"] and r["day"][1] % 2 == parity])
            if kept is not None:
                curve, errors = kept
                learnt[name] = [curve, float(np.percentile(errors, RANGE_SHARE)), float(np.median(errors))]
        # A strip counts for more the better its record, but a record from a few days is itself uncertain, so
        # every strip's typical error is first mixed with the typical error of them all.
        shared = float(np.median([typical for _, _, typical in learnt.values()])) if learnt else 0.0
        for kept in learnt.values():
            kept[2] = 1.0 / (kept[2] ** 2 + shared ** 2 + 1e-6)
        keys = sorted({key for by_key in readings.values() for key, r in by_key.items() if r["day"][1] % 2 != parity})
        for key in keys:
            first = next(by_key[key] for by_key in readings.values() if key in by_key)
            alone, ranges = {}, []
            for name, (curve, wide, weight) in learnt.items():
                r = readings[name].get(key)
                if r is not None and r["found"]:
                    alone[name] = float(curve(r["row"]))
                    ranges.append((alone[name] - wide, alone[name] + wide, weight))
            row = {"key": key, "level": first["level"], "std": first["std"], "alone": alone, "used": len(ranges),
                   "best": min(learnt, key=lambda n: -learnt[n][2]) if learnt else None}
            if ranges:
                low, high, agreed = multiview.combine(ranges)
                row.update(together=multiview.best_guess([0.5 * (a + b) for a, b, _ in ranges], [w for _, _, w in ranges]),
                           low=low, high=high, agreed=agreed)
            out.append(row)
    return out


def cm(values, share=None):
    if not len(values):
        return "-"
    return f"{100 * (np.median(values) if share is None else np.percentile(values, share)):.0f} cm"


def summary(camera, rows):
    names = list(STRIPS[camera]["strips"])
    lines = [f"### {camera}: {STRIPS[camera]['role']}", "",
             "| Read through | Pictures given a level | Typical error | 90% under | Within 10 / 20 cm |", "|---|---|---|---|---|"]

    def line(label, errors, total):
        errors = np.array(errors)
        within = f"{np.mean(errors <= 0.10):.0%} / {np.mean(errors <= 0.20):.0%}" if len(errors) else "-"
        return f"| {label} | {len(errors)} of {total} | {cm(errors)} | {cm(errors, 90)} | {within} |"

    total = len(rows)
    for name in names:
        errors = [abs(r["alone"][name] - r["level"]) for r in rows if name in r["alone"]]
        lines.append(line(f"Strip {name} alone: {STRIPS[camera]['strips'][name][2]}", errors, total))
    best = [abs(r["alone"][r["best"]] - r["level"]) for r in rows if r["best"] in r["alone"]]
    lines.append(line("The one strip with the best record on the days learnt from", best, total))
    together = [r for r in rows if "together" in r]
    lines.append(line("**All strips together**", [abs(r["together"] - r["level"]) for r in together], total))
    three = [r for r in together if r["used"] >= 3]
    lines.append(line("All strips together, where three or more gave a line", [abs(r["together"] - r["level"]) for r in three], total))
    agreed = [r for r in together if r["agreed"]]
    inside = sum(r["low"] <= r["level"] <= r["high"] for r in together)
    inside_agreed = sum(r["low"] <= r["level"] <= r["high"] for r in agreed)
    width = np.median([r["high"] - r["low"] for r in together]) if together else float("nan")
    width_agreed = np.median([r["high"] - r["low"] for r in agreed]) if agreed else float("nan")
    lines += ["", f"The joined range held the measured level in {inside} of {len(together)} pictures, and was {100 * width:.0f} cm wide, typically. "
              + (f"Where three or more strips agreed ({len(agreed)} pictures) it held it in {inside_agreed} and was {100 * width_agreed:.0f} cm wide."
                 if agreed else "In no picture did three strips agree."), ""]
    return "\n".join(lines)


def report(results):
    lines = [
        "# Several reference surfaces in one view, on a real flood",
        "",
        "**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_multi_reference.py` on the",
        "hourly pictures of two river cameras near Tewkesbury, 21 November to 5 December 2012, published with the",
        "water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The",
        "pictures are not in the repository. This is a river, not a street, and not Hyderabad.",
        "",
        "The waterline detector reads each camera through several strips, each on a different surface that the water",
        "climbs. Each strip is given a curve from row to level, and a record, on half of the days.",
        "`nirmaldhara.multiview.combine` joins what the strips say on the other half. Every error is on days not",
        "learnt from.",
        "",
    ]
    for camera, rows in results.items():
        lines.append(summary(camera, rows))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--camera", choices=sorted(STRIPS), action="append")
    parser.add_argument("--data", default=str(river.DATA))
    parser.add_argument("--keep", help="a folder to keep each strip's rows in, so a second run does not read the pictures again")
    args = parser.parse_args()
    if not (Path(args.data) / "FarsonDigital_CameraImages_NovDec2012").is_dir():
        print(f"The pictures are not in {args.data}. See the top of scripts/river_camera_test.py for where to get them.")
        return 1
    results = {}
    for camera in (args.camera or STRIPS):
        readings = {}
        for name in STRIPS[camera]["strips"]:
            kept = Path(args.keep) / f"{camera}-{name}.json" if args.keep else None
            if kept is not None and kept.exists():
                readings[name] = {tuple(json.loads(k)): {**v, "day": tuple(v["day"])} for k, v in json.loads(kept.read_text("utf-8")).items()}
            else:
                readings[name] = read_strip(camera, name, args.data)
                if kept is not None:
                    kept.parent.mkdir(parents=True, exist_ok=True)
                    kept.write_text(json.dumps({json.dumps(list(k)): v for k, v in readings[name].items()}), encoding="utf-8")
            print(f"{camera} strip {name}: a line in {sum(r['found'] for r in readings[name].values())} of {len(readings[name])} pictures", flush=True)
        results[camera] = joined(readings)
    text = report(results)
    print(text)
    if not args.camera:
        OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
