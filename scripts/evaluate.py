"""Score a depth reader against labelled photos, and write the table.

    python scripts/evaluate.py --reader bedrock                       # real photos, real model
    python scripts/evaluate.py --reader simulated --synthetic         # drawn scenes, stand-in reader

A real run reads samples/labels.csv and writes EVALUATION.md and data/eval-results.json. A
simulated run reads the drawn scenes in samples/synthetic/ and writes docs/evaluation-simulated.md
and data/eval-results-simulated.json instead, with SIMULATED on every page of it: it must never be
mistaken for, or written over, a real evaluation.

Labels are one person's reading of each photo (or, for drawn scenes, the depth they were drawn at),
not measured depth. Columns: file, band_low, band_high, object_used, moving, source, licence. An
optional `readable` column of "no", or an object_used of "none", marks a photo the reader should
decline to read.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nirmaldhara.bands import (NO_GO_CM, PASSABLE, band_for, answer_for,  # noqa: E402
                               BAND_EDGES_CM)

BANDS = ["B0"] + [name for name, _ in BAND_EDGES_CM] + ["B5"]
LOWER_EDGE_CM = {"B0": 0.0, "B1": 0.01, "B2": 12.0, "B3": 20.0, "B4": 30.0, "B5": 50.0}
UPPER_EDGE_CM = {"B0": 0.0, "B1": 12.0, "B2": 20.0, "B3": 30.0, "B4": 50.0, "B5": 1e9}
VEHICLES = ("two_wheeler", "car", "pedestrian")
SIM_BANNER = ("SIMULATED. These are drawn scenes read by a stand-in, not photographs read by a model. "
              "Nothing below is evidence of how accurately any model reads real floods.")


def load_labels(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expected_to_decline(row):
    return row.get("readable", "yes").strip().lower() == "no" or row.get("object_used", "").strip().lower() == "none"


def distance(band, low, high):
    """How many bands `band` is from the label interval [low, high]; 0 if inside it."""
    i, lo, hi = BANDS.index(band), BANDS.index(low), BANDS.index(high)
    return 0 if lo <= i <= hi else min(abs(i - lo), abs(i - hi))


def score_one(row, reading):
    """Everything said about one photo."""
    low_band, high_band = row["band_low"], row["band_high"]
    out = {"file": row["file"], "label": low_band if low_band == high_band else f"{low_band}-{high_band}",
           "declined_expected": expected_to_decline(row), "declined": bool(reading["cannot_tell"]),
           "reason": reading.get("reason", "")}
    if reading["cannot_tell"]:
        out.update(read="declined", band=None, exact=None, within_one=None, dangerous=[], cautious=[])
        return out
    lo, hi, conf = reading["depth_cm_low"], reading["depth_cm_high"], reading["confidence"]
    band = band_for(hi)                                     # the cautious end decides the band
    answers = {v: answer_for(v, lo, hi, conf) for v in VEHICLES}
    # A dangerous miss: the photo is at least as deep as a class's limit even at the label's low
    # end, yet the reader says that class can pass.
    dangerous = [v for v in VEHICLES if LOWER_EDGE_CM[low_band] >= NO_GO_CM[v] and answers[v] == PASSABLE]
    # Over-cautious: the label's high end is under the limit, yet the reader will not say "passable".
    cautious = [v for v in VEHICLES if UPPER_EDGE_CM[high_band] < NO_GO_CM[v] and answers[v] != PASSABLE]
    out.update(read=f"{lo:g}-{hi:g} cm, conf {conf:g}", band=band,
               exact=distance(band, low_band, high_band) == 0,
               within_one=distance(band, low_band, high_band) <= 1, dangerous=dangerous, cautious=cautious)
    return out


def summarise(scored):
    readable = [s for s in scored if not s["declined_expected"]]
    unreadable = [s for s in scored if s["declined_expected"]]
    read = [s for s in readable if not s["declined"]]
    dangerous_photos = [s for s in scored if s["dangerous"]]
    return {
        "photos": len(scored), "readable": len(readable), "unreadable": len(unreadable),
        "read": len(read), "declined_but_readable": len(readable) - len(read),
        "exact": sum(1 for s in read if s["exact"]), "within_one": sum(1 for s in read if s["within_one"]),
        "declined_correctly": sum(1 for s in unreadable if s["declined"]),
        "answered_when_it_should_decline": sum(1 for s in unreadable if not s["declined"]),
        "dangerous_photos": len(dangerous_photos),
        "dangerous_by_vehicle": {v: sum(1 for s in scored if v in s["dangerous"]) for v in VEHICLES},
        "over_cautious_for_cars": sum(1 for s in read if "car" in s["cautious"]),
    }


def render(scored, summary, simulated, reader_name):
    pct = lambda n, d: f"{n} of {d}" + (f" ({100 * n / d:.0f}%)" if d else "")           # noqa: E731
    lines = ["# Depth reading: evaluation" + (" (SIMULATED)" if simulated else ""), ""]
    if simulated:
        lines += [f"> **{SIM_BANNER}**", ""]
    lines += [
        f"Reader: `{reader_name}`. {summary['photos']} photos.", "",
        "**Labels are one person's reading of each photo, not measured depth**"
        + (" (here, the depth each scene was drawn at)." if simulated else "."),
        "The reader's band is the band of the top of its depth range, the cautious end.", "",
        "| Measure | Result |", "|---|---|",
        f"| Band agrees with the label | {pct(summary['exact'], summary['read'])} of the photos it read |",
        f"| Band within one of the label | {pct(summary['within_one'], summary['read'])} |",
        f"| Declined a photo it should decline (dark, blurred, nothing of known size) | {pct(summary['declined_correctly'], summary['unreadable'])} |",
        f"| Answered a photo it should have declined | {summary['answered_when_it_should_decline']} |",
        f"| Declined a photo that was readable | {summary['declined_but_readable']} |",
        f"| **Dangerous misses**: told a class it can pass when the photo was at least as deep as that class's limit | **{summary['dangerous_photos']}** photos"
        f" (two-wheelers {summary['dangerous_by_vehicle']['two_wheeler']}, cars {summary['dangerous_by_vehicle']['car']},"
        f" people on foot {summary['dangerous_by_vehicle']['pedestrian']}) |",
        f"| Over-cautious for cars: would not say \"passable\" though the photo was under the limit | {summary['over_cautious_for_cars']} |",
        "", "## Every photo", "", "| Photo | Label | Reader said | Band | Result |", "|---|---|---|---|---|"]
    for s in scored:
        if s["declined"]:
            result = "declined, as it should" if s["declined_expected"] else "**declined a readable photo**"
        elif s["declined_expected"]:
            result = "**answered; should have declined**"
        elif s["dangerous"]:
            result = "**DANGEROUS MISS: " + ", ".join(s["dangerous"]) + "**"
        else:
            result = ("exact" if s["exact"] else "within one band" if s["within_one"] else "**more than one band out**")
            if s["cautious"]:
                result += "; cautious for " + ", ".join(s["cautious"])
        lines.append(f"| `{s['file']}` | {s['label']} | {s['read']} | {s['band'] or ''} | {result} |")
    lines += ["", "## What this does and does not show", ""]
    if simulated:
        lines += [
            "- It shows the evaluation works from end to end: labels in, a reader run on every photo, the",
            "  measures above out, and a dangerous miss would be counted and named.",
            "- It does **not** show how a model reads a real photograph. The reader here measures the water",
            "  line against a wheel in pictures drawn for the purpose, where the wheel is dark and the water",
            "  blue. The scenes were chosen by the person who wrote the reader.",
            "- When a real route and labelled photos exist, run `python scripts/evaluate.py --reader bedrock`.", ""]
    else:
        lines += ["- A small sample labelled by one person. It says what happened on these photos, not how the",
                  "  reader will do on others.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--reader", choices=["bedrock", "simulated"], required=True)
    parser.add_argument("--synthetic", action="store_true", help="use the drawn scenes in samples/synthetic/")
    parser.add_argument("--labels", help="a labels file (default: samples/labels.csv, or the synthetic one)")
    args = parser.parse_args()

    simulated = args.reader == "simulated"
    if simulated and not args.synthetic:
        print("The simulated reader works only on the drawn scenes: add --synthetic.")
        return 2
    if args.synthetic and not simulated:
        print("Do not point the real reader at the drawn scenes as if they were photographs. "
              "Use --reader simulated, or give it real photos with --labels.")
        return 2
    labels_path = Path(args.labels) if args.labels else (ROOT / "samples" / ("synthetic" if args.synthetic else "") / "labels.csv")
    if not labels_path.exists():
        print(f"No labels file at {labels_path}. See samples/README.md for the columns, then run again.")
        return 1

    if simulated:
        import simulated_reader as reader_module
        reader_name = "scripts/simulated_reader.py"
    else:
        from nirmaldhara import reader as reader_module
        reader_name = f"nirmaldhara.reader ({reader_module.MODEL})"

    rows = load_labels(labels_path)
    scored = [score_one(row, reader_module.read_depth(str(labels_path.parent / row["file"]))) for row in rows]
    summary = summarise(scored)
    text = render(scored, summary, simulated, reader_name)
    doc_path = ROOT / ("docs/evaluation-simulated.md" if simulated else "EVALUATION.md")
    json_path = ROOT / ("data/eval-results-simulated.json" if simulated else "data/eval-results.json")
    doc_path.write_text(text, encoding="utf-8", newline="\n")
    json_path.write_text(json.dumps({"simulated": simulated, "reader": reader_name, "summary": summary,
                                     "photos": scored}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(("SIMULATED: " if simulated else "") + f"{summary['photos']} photos; band agrees on {summary['exact']} of {summary['read']}; "
          f"within one on {summary['within_one']}; dangerous misses {summary['dangerous_photos']}.")
    print(f"wrote {doc_path.relative_to(ROOT)} and {json_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
