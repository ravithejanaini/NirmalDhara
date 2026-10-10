"""REAL FLOOD, MEASURED LEVELS: one level from every reference surface in view, followed through time.

    python scripts/river_depth_model.py                 # prints the results and writes docs/depth-model-river.md
    python scripts/river_depth_model.py --camera Tewkesbury

The same pictures and levels as scripts/river_camera_test.py (credits and licence in
samples/tewkesbury/CREDITS.md; the pictures are not in the repository). Each camera is read by the
waterline detector through several strips, each on a different surface, and nirmaldhara/depthmodel.py
makes one level of them. Four ways of reading the same pictures are set side by side:

    one strip                 the detector through one strip, its row turned into a level by a curve
    strips joined             every strip turned into a level by its own curve, and the middle one taken
                              (nirmaldhara.multiview)
    the model, each moment    every strip as a witness to one level: blind where its curve is flat, sharp
                              where it is steep, outvoted by degrees when it is wild
    the model, through time   the same, with each moment's belief carried to the next
    with the learnt gauge     the same again, with nirmaldhara/gauge.py's reading of the whole picture as
                              one more witness, counted for as much as it earned on the days left out

Half of the days are learnt from and the other half read, then the other way round. Everything the
model uses, the witnesses, the share their evidence is counted at, the rate the level can move and
the stretch of its range, is learnt from the days learnt from and nothing else.

One camera was used to build the model and is marked so. On the other, the strips were fixed on the
dry view and the model was fixed before it was run, and it was run once.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import learn_river_cameras as whole  # noqa: E402
import river_camera_test as river  # noqa: E402
import river_multi_reference as multi  # noqa: E402
from nirmaldhara import depthmodel, gauge  # noqa: E402

OUT = ROOT / "docs" / "depth-model-river.md"
NOTES = ROOT / "docs" / "depth-model-river-notes.md"
# name: (box left, top, right, bottom; dry ground at the bottom?; what the strip runs over). Fixed on the dry view only.
STRIPS = {
    "Tewkesbury": {
        "role": "used to build the model",
        "strips": {
            "A": ((1400, 700, 1508, 1536), True, "the grass bank, right of the tables"),
            "C": ((1620, 700, 1728, 1536), True, "the grass bank at the far right"),
            "D": ((1840, 330, 1948, 760), False, "the concrete pier at the end of the weir"),
            "E": ((1060, 250, 1168, 560), False, "the far lock wall"),
            "G": ((780, 700, 888, 1536), True, "the bank between the tables, down to the gravel"),
        },
    },
    "Strensham": {
        "role": "run once, with the strips and the model fixed beforehand",
        "strips": {
            "A": ((690, 300, 798, 1140), False, "the lock gates, right half"),
            "B": ((266, 300, 374, 1140), False, "the left lock wall and its red marker post"),
            "C": ((986, 300, 1094, 1140), False, "the right bank and its white post"),
            "D": ((1200, 300, 1308, 1140), False, "the steps down to the water"),
            "E": ((540, 300, 648, 1140), False, "the lock gates, left half"),
            "F": ((880, 300, 988, 1140), False, "the right quay, under the hut"),
            "G": ((1500, 400, 1608, 1240), False, "the far right bank and its handrail"),
        },
    },
}


def clock(key):
    """Hours on one running clock from (month, day, hour), November having thirty days."""
    month, day, hour = key
    return float(((month - 11) * 30 + day) * 24 + hour)


def strips_of(camera, data=river.DATA, keep=None):
    """{strip: {key: reading}} for one camera, read by the detector or taken from what was kept."""
    out = {}
    for name, (box, from_bottom, _) in STRIPS[camera]["strips"].items():
        kept = Path(keep) / f"{camera}-{name}.json" if keep else None
        if kept is not None and kept.exists():
            out[name] = {tuple(json.loads(k)): {**v, "day": tuple(v["day"])} for k, v in json.loads(kept.read_text("utf-8")).items()}
        else:
            out[name] = multi.read_box(camera, box, from_bottom, data)
            if kept is not None:
                kept.parent.mkdir(parents=True, exist_ok=True)
                kept.write_text(json.dumps({json.dumps(list(k)): v for k, v in out[name].items()}), encoding="utf-8")
    return out


def said(reading):
    """A strip's reading as a witness's report: a line at a row, "dry", or neither."""
    if reading["found"]:
        return "line", reading["row"]
    return ("dry" if reading.get("reason") == "dry" else "other"), None


def moments_of(readings):
    """Every picture any strip was read in, in order of time: (keys, levels, days, hours, {strip: [report]})."""
    keys = sorted({key for by_key in readings.values() for key in by_key}, key=clock)
    first = lambda key: next(by_key[key] for by_key in readings.values() if key in by_key)      # noqa: E731
    reports = {name: [said(by_key[key]) if key in by_key else ("other", None) for key in keys] for name, by_key in readings.items()}
    return (keys, np.array([first(key)["level"] for key in keys]), np.array([key[0] * 100 + key[1] for key in keys]),
            np.array([clock(key) for key in keys]), reports)


def gauge_says(learnt, picture, grid):
    """The learnt gauge's reading of one picture as a likelihood along the model's levels, in log, or None
    when it could not read it. Beyond the last step it learnt it is flat: it cannot tell those levels apart."""
    if picture is None:
        return None
    trace = {}
    learnt.read(picture, trace)
    return gauge.EVIDENCE * np.interp(grid, trace["grid"], trace["fit"]) if "fit" in trace else None


def gauge_witness(pictures, keys, levels, days, seen, grid):
    """For every moment, what a gauge that never saw that moment's day says of it. For a day learnt from,
    that is a gauge learnt from the other days learnt from; for an unseen day, from all of them."""
    out = [None] * len(keys)
    have = np.array([key in pictures for key in keys])
    stack = lambda mask: [pictures[keys[i]] for i in np.flatnonzero(mask)]         # noqa: E731
    for day in np.unique(days[seen]):
        rest = seen & (days != day) & have
        if len(np.unique(days[rest])) < 2 * gauge.DAYS_EACH_SIDE:
            continue
        without = gauge.learn(stack(rest), levels[rest], days[rest], check=False)
        for i in np.flatnonzero(seen & (days == day)):
            out[i] = gauge_says(without, pictures.get(keys[i]), grid)
    if len(np.unique(days[seen & have])) >= 2 * gauge.DAYS_EACH_SIDE:
        every = gauge.learn(stack(seen & have), levels[seen & have], days[seen & have], check=False)
        for i in np.flatnonzero(~seen):
            out[i] = gauge_says(every, pictures.get(keys[i]), grid)
    return out


def gauge_share(model):
    return model.extras["gauge"][1]


def one_camera(camera, readings, pictures=None):
    """Every unseen picture read several ways: {way: [(measured, read, low, high)]}, and what each model
    learnt. pictures: {key: picture}, for the learnt gauge to be one of the witnesses."""
    keys, levels, days, hours, reports = moments_of(readings)
    rows = {name: (box[3] - box[1]) // 3 for name, (box, _, _) in STRIPS[camera]["strips"].items()}
    out = {"one strip": [], "strips joined": [], "the model, each moment": [], "the model, through time": []}
    if pictures is not None:
        out["with the learnt gauge"] = []
    learnt = []
    for parity in (0, 1):
        seen = (days % 100) % 2 == parity
        taught = (levels[seen], {n: [s for s, k in zip(r, seen) if k] for n, r in reports.items()}, rows, days[seen], hours[seen])
        model = depthmodel.learn(*taught, cameras={n: camera for n in reports})
        learnt.append(model)
        unseen = np.flatnonzero(~seen)
        alone = [depthmodel.believe(model, {n: reports[n][i] for n in reports}) for i in unseen]
        through = depthmodel.follow(model, [(hours[i], {n: reports[n][i] for n in reports}) for i in unseen])
        out["the model, each moment"] += [(levels[i], r.level, r.low, r.high) for i, r in zip(unseen, alone)]
        out["the model, through time"] += [(levels[i], r.level, r.low, r.high) for i, r in zip(unseen, through)]
        if pictures is not None:
            says = gauge_witness(pictures, keys, levels, days, seen, model.grid)
            fuller = depthmodel.learn(*taught, cameras={n: camera for n in reports}, extras={"gauge": [says[i] for i in np.flatnonzero(seen)]})
            learnt[-1] = fuller
            both = depthmodel.follow(fuller, [(hours[i], {n: reports[n][i] for n in reports}) for i in unseen],
                                     extras=[{"gauge": says[i]} for i in unseen])
            out["with the learnt gauge"] += [(levels[i], r.level, r.low, r.high) for i, r in zip(unseen, both)]
        first = next(iter(readings))
        fitted = [r for r in readings[first].values() if r["found"] and (r["day"][1] % 2 == parity)]
        if len(fitted) >= 5:
            curve = river.rising_curve([r["row"] for r in fitted], [r["level"] for r in fitted])
            out["one strip"] += [(levels[i], float(curve(readings[first][keys[i]]["row"])), None, None) for i in unseen
                                 if keys[i] in readings[first] and readings[first][keys[i]]["found"]]
    for row in multi.joined(readings):
        if "together" in row:
            out["strips joined"].append((row["level"], row["together"], row["low"], row["high"]))
    return {"ways": out, "learnt": learnt, "pictures": len(keys), "levels": (float(levels.min()), float(levels.max()))}


def cm(values, share=None):
    if not len(values):
        return "-"
    return f"{100 * (np.median(values) if share is None else np.percentile(values, share)):.0f} cm"


def line(label, rows, total):
    errors = np.array([abs(read - measured) for measured, read, _, _ in rows])
    ranged = [(measured, low, high) for measured, _, low, high in rows if low is not None]
    held = f"{sum(low <= m <= high for m, low, high in ranged)} of {len(ranged)}, {100 * np.median([h - l for _, l, h in ranged]):.0f} cm wide" if ranged else "-"
    within = f"{np.mean(errors <= 0.10):.0%} / {np.mean(errors <= 0.20):.0%}" if len(errors) else "-"
    return f"| {label} | {len(errors)} of {total} | {cm(errors)} | {cm(errors, 90)} | {within} | {held} |"


def report(results):
    lines = [
        "# One level from every reference surface, through time, on a real flood",
        "",
        "**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_depth_model.py` on the",
        "hourly pictures of two river cameras near Tewkesbury, 21 November to 5 December 2012, published with the",
        "water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The",
        "pictures are not in the repository. This is a river, not a street, and not Hyderabad.",
        "",
        "Each camera is read through several strips. `nirmaldhara/depthmodel.py` learns, on half of the days, what",
        "each strip reports at each level, and makes one level of them on the other half. Every error is on days",
        "not learnt from. The range is the model's own, stretched until it would have held nine in ten of the",
        "days left out while it was learning.",
        "",
    ]
    for camera, r in results.items():
        lines += [f"## {camera}: {STRIPS[camera]['role']}", "",
                  f"{r['pictures']} pictures with a measured level, {r['levels'][0]:.2f} to {r['levels'][1]:.2f} m, read through "
                  f"{len(STRIPS[camera]['strips'])} strips.", "",
                  "| Read by | Pictures given a level | Typical error | 90% under | Within 10 / 20 cm | Range held the level |", "|---|---|---|---|---|---|"]
        labels = {"one strip": f"One strip ({next(iter(STRIPS[camera]['strips'].values()))[2]}), its row through a curve",
                  "strips joined": "Every strip through its own curve, the middle one taken",
                  "the model, each moment": "**The model**, each moment by itself",
                  "the model, through time": "**The model, through time**",
                  "with the learnt gauge": "**The model, through time, with the learnt gauge as one more witness**"}
        for way, rows in r["ways"].items():
            lines.append(line(labels[way], rows, r["pictures"]))
        lines += ["", "What the model learnt about each strip, from each half of the days:", "",
                  "| Strip | Runs over | Lines learnt from | Spread, rows | Wild | Levels it can tell apart |", "|---|---|---|---|---|---|"]
        for name, (_, _, what) in STRIPS[camera]["strips"].items():
            cells = []
            for model in r["learnt"]:
                w = model.witnesses.get(name)
                if w is None:
                    cells.append(("-", "-", "-", "nothing learnt"))
                    continue
                sharp = w.sharpness() > 0.02                                    # its row moves a fiftieth of a spread for each centimetre
                where = f"{model.grid[sharp].min():.2f} to {model.grid[sharp].max():.2f} m, {sharp.mean():.0%} of them" if sharp.any() else "none"
                cells.append((str(w.lines), f"{w.spread:.1f}", f"{w.wild:.0%}", where))
            lines.append(f"| {name} | {what} | {' / '.join(c[0] for c in cells)} | {' / '.join(c[1] for c in cells)} | "
                         f"{' / '.join(c[2] for c in cells)} | {' ; '.join(c[3] for c in cells)} |")
        each = lambda pick: " / ".join(pick(m) for m in r["learnt"])                     # noqa: E731
        lines += ["", f"Share of face value the strips' evidence was counted at: {each(lambda m: f'{list(m.share.values())[0]:.2f}')} for a moment by itself, "
                  f"{each(lambda m: f'{list(m.through.values())[0]:.2f}')} through time. Rate the level was taken to move at: "
                  f"{each(lambda m: f'{100 * m.rate:.1f}')} cm an hour. Stretch of the range: {each(lambda m: f'{m.stretch:.1f}')} times by itself, "
                  f"{each(lambda m: f'{m.stretch_through:.1f}')} through time."
                  + (f" The learnt gauge's evidence was counted at {each(lambda m: f'{gauge_share(m):.3f}')} of what it claimed."
                     if all("gauge" in m.extras for m in r["learnt"]) else ""), ""]
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
        shown, _, days, hours, _, _ = whole.load(camera, args.data)
        pictures = {(int(day) // 100, int(day) % 100, int(hour)): picture for picture, day, hour in zip(shown, days, hours)}
        results[camera] = one_camera(camera, strips_of(camera, args.data, args.keep), pictures)
    text = report(results)
    print(text)
    if not args.camera:
        OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
