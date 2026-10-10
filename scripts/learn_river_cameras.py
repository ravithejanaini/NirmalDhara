"""REAL FLOOD, MEASURED LEVELS: a gauge learnt from each camera's own pictures, Tewkesbury, November 2012.

    python scripts/learn_river_cameras.py                 # prints the results and writes docs/gauge-river.md
    python scripts/learn_river_cameras.py --camera Tewkesbury

The same pictures and levels as scripts/river_camera_test.py (credits and licence in
samples/tewkesbury/CREDITS.md; the pictures are not in the repository). There the waterline detector
was given a strip chosen by eye and a dry view. Here nirmaldhara/gauge.py is given nothing but
pictures with their measured levels, and learns for itself which parts of the view go under at which
level. No strip is chosen, so nothing about a camera is decided by a person.

A gauge is always judged on days it did not learn from, three ways:

    each day left out     learn from every other day, read the day left out. The most it can learn.
    half the days         learn from the odd days, read the even ones, then the other way round. The
                          same split the detector's row-to-level curve was judged on, so the two can
                          be set side by side.
    earlier days only     learn from the days so far (at least four), read the next. This is how it
                          would be used, and it is the hardest: on a rising flood every new day is
                          higher than anything seen.

One camera was used to build the gauge and is marked so. The other three were run once, after
gauge.py had been fixed, with nothing chosen for them.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import river_camera_test as river  # noqa: E402
from nirmaldhara import gauge  # noqa: E402

DATA = river.DATA
LEVELS = river.LEVELS
OUT = ROOT / "docs" / "gauge-river.md"
NOTES = ROOT / "docs" / "gauge-river-notes.md"
SHRINK = 4                         # each picture is averaged over this many pixels each way before anything else
UNKNOWN_DOUBT = 0.1                # metres, where the dataset gives a level but no error for it
CAMERAS = {
    "Tewkesbury": "used to build the gauge",
    "Strensham": "run once, after the gauge was fixed",
    "DiglisLock": "run once, after the gauge was fixed",
    "Evesham": "run once, after the gauge was fixed",
}
WAYS = ("each day left out", "half the days", "earlier days only")
AT_LEAST = 4                       # days needed before the next is read, in "earlier days only"


def load(camera, data=DATA):
    """Every picture of one camera that has a measured level: (pictures, levels, days, hours, doubt, left out).

    Pictures are shrunk. A picture that is missing, or not the size of the rest, is left out and counted.
    """
    table = json.loads(LEVELS.read_text("utf-8"))["cameras"][camera]
    folder = Path(data) / "FarsonDigital_CameraImages_NovDec2012" / table["folder"]
    rows = sorted((r for r in table["readings"] if r["level_m"] is not None and r["image"]),
                  key=lambda r: (r["month"], r["day"], r["hour"]))
    listed = len(rows)
    rows = [r for r in rows if (folder / r["image"]).is_file()]
    small = [np.asarray(Image.open(folder / r["image"]).convert("RGB").reduce(SHRINK), dtype=np.uint8) for r in rows]
    sizes = [picture.shape for picture in small]
    usual = max(set(sizes), key=sizes.count)
    kept = [i for i, size in enumerate(sizes) if size == usual]
    rows = [rows[i] for i in kept]
    return (np.array([small[i] for i in kept]), np.array([r["level_m"] for r in rows]),
            np.array([r["month"] * 100 + r["day"] for r in rows]), np.array([r["hour"] for r in rows]),
            np.array([UNKNOWN_DOUBT if r["std_m"] is None else r["std_m"] for r in rows]), listed - len(kept))


def folds(way, days):
    """[(learnt from, read)] as pairs of masks over the pictures."""
    names = sorted(set(days.tolist()))
    if way == "each day left out":
        return [(days != day, days == day) for day in names]
    if way == "half the days":
        return [((days % 100) % 2 == parity, (days % 100) % 2 != parity) for parity in (0, 1)]
    return [(days < day, days == day) for day in names[AT_LEAST:]]


def read_unseen(pictures, levels, days, doubt, way, check=False):
    """One dict for each picture read by a gauge that did not learn from its day."""
    out = []
    for seen, unseen in folds(way, days):
        if len(set(days[seen].tolist())) < 2 * gauge.DAYS_EACH_SIDE or not unseen.any():
            out += [{"index": int(i), "level": float(levels[i]), "doubt": float(doubt[i]), "reason": "too few days to learn from",
                     "found": False, "read": float("nan"), "guess": float(np.median(levels[seen])) if seen.any() else float("nan"),
                     "inside": None} for i in np.flatnonzero(unseen)]
            continue
        learnt = gauge.learn(pictures[seen], levels[seen], days[seen], doubt[seen], check=check)
        guess = float(np.median(levels[seen]))
        for i in np.flatnonzero(unseen):
            reading = learnt.read(pictures[i])
            inside = (reading.low <= levels[i] <= reading.high) if reading.found and np.isfinite(learnt.error) else None
            out.append({"index": int(i), "level": float(levels[i]), "doubt": float(doubt[i]), "reason": reading.reason,
                        "found": reading.found, "read": reading.level, "guess": guess, "inside": inside})
    return out


def wrong_side(row):
    """A reading that only said below or above some level, where the measured level was on the other
    side of it by more than its own error."""
    if row["reason"].startswith("below"):
        return row["level"] > row["read"] + row["doubt"]
    if row["reason"].startswith("above"):
        return row["level"] < row["read"] - row["doubt"]
    return False


def score(rows):
    found = [r for r in rows if r["found"]]
    errors = np.array([abs(r["read"] - r["level"]) for r in found])
    guesses = np.array([abs(r["guess"] - r["level"]) for r in found])
    bounds = [r for r in rows if r["reason"].startswith(("below", "above"))]
    inside = [r["inside"] for r in found if r["inside"] is not None]
    return {"pictures": len(rows), "found": len(found), "errors": errors, "guesses": guesses, "bounds": len(bounds),
            "wrong": sum(wrong_side(r) for r in bounds), "unreadable": sum(r["reason"] == "unreadable" for r in rows),
            "too_few": sum(r["reason"].startswith("too few") for r in rows),
            "inside": (sum(inside), len(inside))}


def with_detector(camera, pictures, levels, days, hours, doubt, data=DATA):
    """Half the days, three ways on the same pictures: the detector's row through a curve fitted on the
    days learnt from, the gauge, and the two together. {name: score}"""
    detected, _ = river.readings(camera, data)
    by_time = {(r["day"][0] * 100 + r["day"][1], r["hour"]): r for r in detected if r["found"]}
    rows = {"the detector, with a strip chosen by eye": [], "the learnt gauge": [], "both together": []}
    for seen, unseen in folds("half the days", days):
        fitted = [by_time[key] for key in zip(days[seen].tolist(), hours[seen].tolist()) if key in by_time]
        curve = river.rising_curve([r["row"] for r in fitted], [r["level"] for r in fitted]) if len(fitted) >= 5 else None
        learnt = gauge.learn(pictures[seen], levels[seen], days[seen], doubt[seen], check=False)
        guess = float(np.median(levels[seen]))
        for i in np.flatnonzero(unseen):
            base = {"index": int(i), "level": float(levels[i]), "doubt": float(doubt[i]), "guess": guess, "inside": None}
            row = by_time.get((int(days[i]), int(hours[i])))
            other = float(curve(row["row"])) if curve is not None and row is not None else None
            reading = learnt.read(pictures[i])
            together, source = gauge.with_fallback(reading, other)
            rows["the detector, with a strip chosen by eye"].append(
                {**base, "found": other is not None, "read": other if other is not None else float("nan"),
                 "reason": "ok" if other is not None else "no line"})
            rows["the learnt gauge"].append({**base, "found": reading.found, "read": reading.level, "reason": reading.reason})
            rows["both together"].append({**base, "found": together is not None,
                                          "read": together if together is not None else float("nan"),
                                          "reason": "ok" if together is not None else "neither"})
    return {name: score(group) for name, group in rows.items()}


def cm(values, share=None):
    if not len(values):
        return "-"
    return f"{100 * (np.median(values) if share is None else np.percentile(values, share)):.0f} cm"


def line(name, s):
    within = (f"{np.mean(s['errors'] <= 0.10):.0%} / {np.mean(s['errors'] <= 0.20):.0%}") if s["found"] else "-"
    sides = f"{s['bounds']} ({s['wrong']} wrong)" if s["bounds"] else "0"
    return (f"| {name} | {s['pictures']} | {s['found']} ({s['found'] / max(1, s['pictures']):.0%}) | {cm(s['errors'])} | {cm(s['errors'], 90)} | "
            f"{within} | {cm(s['guesses'])} | {sides} | {s['pictures'] - s['found'] - s['bounds']} |")


HEAD = ["| | Pictures read | Given a level | Typical error | 90% under | Within 10 / 20 cm | Guessing the middle level | Told only below or above | No answer |",
        "|---|---|---|---|---|---|---|---|---|"]


def report(results):
    lines = [
        "# A gauge the camera learns for itself, on a real flood",
        "",
        "**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/learn_river_cameras.py` on the",
        "hourly pictures of four river cameras near Tewkesbury, 21 November to 5 December 2012, published with the",
        "water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The",
        "pictures are not in the repository. This is a river, not a street, and not Hyderabad.",
        "",
        "`nirmaldhara/gauge.py` is given a camera's pictures with their measured levels and nothing else. It learns",
        "which patches of the view go under at which level, and reads a new picture from which patches look wet. It",
        "is always judged on days it did not learn from. A reading is a level, or only \"below\" or \"above\" what it",
        "had learnt, or no answer.",
        "",
    ]
    for way in WAYS:
        lines += [f"## Learning from {way}" if way != "earlier days only" else "## Learning from earlier days only", "", *HEAD]
        for camera, r in results.items():
            lines.append(line(f"{camera}, {CAMERAS[camera]}", r["ways"][way]))
        lines.append("")
    lines += ["## Against the detector, on the same pictures", "",
              "Half the days learnt from, the other half read. The detector's row is turned into a level by a curve",
              "fitted on the days learnt from. \"Both together\" takes the gauge's level where it gave one and the",
              "detector's otherwise, kept on the gauge's side of the line when the gauge said below or above.", "", *HEAD]
    for camera, r in results.items():
        for name, s in (r["detector"] or {}).items():
            lines.append(line(f"{camera}: {name}", s))
    lines += ["", "## What each gauge learnt, from all of a camera's days", "",
              "| Camera | Pictures, days | Levels | The dataset's own error | Patches used | Levels it can tell apart | 90% of left-out readings within | Intervals that held the measured level |",
              "|---|---|---|---|---|---|---|---|"]
    for camera, r in results.items():
        whole, inside = r["whole"], r["ways"]["half the days"]["inside"]
        tells = f"{whole['reads'][0]:.2f} to {whole['reads'][1]:.2f} m" if whole["reads"] else "none"
        held = f"{inside[0]} of {inside[1]}" if inside[1] else "-"
        skipped = f"; {r['left_out']} missing or of another size left out" if r["left_out"] else ""
        error = f"{100 * whole['error']:.0f} cm" if np.isfinite(whole["error"]) else "-"
        lines.append(f"| {camera} | {r['pictures']}, {r['days']}{skipped} | {r['levels'][0]:.2f} to {r['levels'][1]:.2f} m | "
                     f"± {100 * r['doubt']:.0f} cm typical | {whole['used']} of {whole['patches']} | {tells} | "
                     f"{error} | {held} |")
    lines.append("")
    return "\n".join(lines)


def one_camera(camera, data=DATA):
    pictures, levels, days, hours, doubt, left_out = load(camera, data)
    ways = {way: score(read_unseen(pictures, levels, days, doubt, way, check=(way == "half the days"))) for way in WAYS}
    learnt = gauge.learn(pictures, levels, days, doubt, check=True)
    whole = {"used": len(learnt.where), "patches": learnt.shape[0] * learnt.shape[1], "reads": learnt.reads(), "error": learnt.error}
    detector = with_detector(camera, pictures, levels, days, hours, doubt, data) if camera in river.CAMERAS else None
    return {"ways": ways, "whole": whole, "detector": detector, "pictures": len(levels), "days": len(set(days.tolist())),
            "levels": (float(levels.min()), float(levels.max())), "doubt": float(np.median(doubt)), "left_out": left_out}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--camera", choices=sorted(CAMERAS), action="append")
    parser.add_argument("--data", default=str(DATA))
    args = parser.parse_args()
    if not (Path(args.data) / "FarsonDigital_CameraImages_NovDec2012").is_dir():
        print(f"The pictures are not in {args.data}. See the top of scripts/river_camera_test.py for where to get them.")
        return 1
    results = {camera: one_camera(camera, args.data) for camera in (args.camera or CAMERAS)}
    text = report(results)
    print(text)
    if not args.camera:
        OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
