"""REAL FLOOD, MEASURED LEVELS: is the level ahead better told by the slope of the last readings, or by "no change"?

    python scripts/river_forecast.py                 # prints the results and writes docs/forecast-river.md
    python scripts/river_forecast.py --camera Tewkesbury

The prediction stage (nirmaldhara/predict.py, METHOD.md section 7) takes a slope through the last
three to six readings and carries it forward to say when a road will be lost. That had never been
tried on anything real. Here it is tried on the river cameras of scripts/river_depth_model.py (credits
and licence in samples/tewkesbury/CREDITS.md; the pictures are not in the repository), the way a
forecasting office judges a forecast: against saying that nothing will change.

Three ways of saying where the level will be:

    no change                    the level stays where the last reading put it
    the slope                    predict.rise_rate through the last three to six readings, carried forward
    the slope when it is clear   the same slope, but only when the newest reading's range lies wholly above
                                 or below the oldest's (predict.clear_rise, predict.clear_fall); else no change

from two kinds of reading:

    the camera's                 nirmaldhara/depthmodel.py following the level through time, with every
                                 strip and the learnt gauge as witnesses
    the measured levels          the level the dataset's authors read from each picture, with the doubt
                                 they gave it. The best reading there is here.

Three days in a row are left out together. The model learns from all the other days and then follows
the level through those three as the pictures came, so that a forecast can run across a night. Every
forecast is judged against the level measured at the time it was made for.

One camera was used to choose the guard and is marked so. On the other, the strips, the model and the
guard were fixed before it was run, and it was run once.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import learn_river_cameras as whole  # noqa: E402
import river_camera_test as river  # noqa: E402
import river_depth_model as rdm  # noqa: E402
from nirmaldhara import depthmodel, predict  # noqa: E402

OUT = ROOT / "docs" / "forecast-river.md"
NOTES = ROOT / "docs" / "forecast-river-notes.md"
ROLES = {"Tewkesbury": "used to choose the guard", "Strensham": "run once, with the guard fixed beforehand"}
RUN = 3                    # days in a row left out together
RANGE = 1.645              # a range that holds nine in ten is this many spreads each way
AHEAD = ("1 hour", "3 hours", "6 hours", "the next morning", "24 hours")
WAYS = ("no change", "the slope", "the slope when it is clear")
KINDS = ("the camera's readings", "the measured levels")


def runs(days, size=RUN):
    """The days in order, in runs of `size`. A last run that would be short joins the one before."""
    names = sorted(np.unique(days).tolist())
    out = [names[i:i + size] for i in range(0, len(names), size)]
    if len(out) > 1 and len(out[-1]) < size:
        short = out.pop()
        out[-1] += short
    return out


def pairs(days, hours):
    """Which moment is forecast from which: [(from, to, how far ahead)], for moments in order of time.

    Within a day, one, three and six hours ahead. Across a night, from the last picture of a day to the
    first of the next, and to the same hour the day after.
    """
    out = []
    for i in range(len(hours)):
        for j in range(i + 1, len(hours)):
            gap = hours[j] - hours[i]
            if gap > 30:
                break
            if days[j] == days[i]:
                if gap in (1, 3, 6):
                    out.append((i, j, f"{int(gap)} hour" + ("" if gap == 1 else "s")))
                continue
            if j == i + 1:
                out.append((i, j, "the next morning"))
            if gap == 24:
                out.append((i, j, "24 hours"))
    return out


def told(times, lows, middles, highs, gap):
    """Where the level will be `gap` hours after the last of these readings, each way: {way: (level,
    whether the slope was used)}. None with too few readings for a slope. times are in hours."""
    slope = predict.rise_rate([(60.0 * t, m) for t, m in zip(times, middles)])
    if slope is None:
        return None
    ranges = list(zip(lows, highs))
    clear = predict.clear_rise(ranges) or predict.clear_fall(ranges)
    now, moved = middles[-1], slope * 60.0 * gap
    return {"no change": (now, None), "the slope": (now + moved, None), "the slope when it is clear": (now + (moved if clear else 0.0), clear)}


def one_camera(camera, readings, pictures=None):
    """Every picture read by a model that never saw its day or the two beside it, and every forecast made
    from those readings and from the measured levels: {"now": [(measured, read, low, high)], "ahead":
    {kind: {how far: {way: [(measured then, forecast, slope used)]}}}}."""
    keys, levels, days, hours, reports = rdm.moments_of(readings)
    first = lambda key: next(by_key[key] for by_key in readings.values() if key in by_key)      # noqa: E731
    doubt = np.array([first(key).get("std") or 0.05 for key in keys], dtype=float)
    rows = {name: (box[3] - box[1]) // 3 for name, (box, _, _) in rdm.STRIPS[camera]["strips"].items()}
    cameras = {name: camera for name in reports}
    now, ahead, learnt = [], {kind: {far: {way: [] for way in WAYS} for far in AHEAD} for kind in KINDS}, []
    for run in runs(days):
        seen = ~np.isin(days, run)
        taught = (levels[seen], {n: [s for s, k in zip(r, seen) if k] for n, r in reports.items()}, rows, days[seen], hours[seen])
        unseen = np.flatnonzero(~seen)
        moments = [(hours[i], {n: reports[n][i] for n in reports}) for i in unseen]
        if pictures is None:
            model = depthmodel.learn(*taught, cameras=cameras)
            read = depthmodel.follow(model, moments)
        else:
            says = rdm.gauge_witness(pictures, keys, levels, days, seen, depthmodel.grid_for(levels[seen]))
            model = depthmodel.learn(*taught, cameras=cameras, extras={"gauge": [says[i] for i in np.flatnonzero(seen)]})
            read = depthmodel.follow(model, moments, extras=[{"gauge": says[i]} for i in unseen])
        learnt.append(model)
        now += [(levels[i], r.level, r.low, r.high) for i, r in zip(unseen, read)]
        for i, j, far in pairs(days[unseen], hours[unseen]):
            past = range(max(0, i - 5), i + 1)
            when = [hours[unseen[k]] for k in past]
            gap = hours[unseen[j]] - hours[unseen[i]]
            exact = [levels[unseen[k]] for k in past]
            wide = [RANGE * doubt[unseen[k]] for k in past]
            made = {"the camera's readings": told(when, [read[k].low for k in past], [read[k].level for k in past], [read[k].high for k in past], gap),
                    "the measured levels": told(when, [e - w for e, w in zip(exact, wide)], exact, [e + w for e, w in zip(exact, wide)], gap)}
            for kind, each in made.items():
                for way, (level, used) in (each or {}).items():
                    ahead[kind][far][way].append((levels[unseen[j]], float(level), used))
    return {"now": now, "ahead": ahead, "learnt": learnt, "pictures": len(keys), "runs": len(runs(days)), "days": len(np.unique(days)),
            "levels": (float(levels.min()), float(levels.max())), "doubt": float(np.median(doubt))}


def out_by(rows):
    """Typical miss and the miss nine in ten were under, in centimetres."""
    if not rows:
        return "-"
    miss = np.abs(np.array([r[1] for r in rows]) - np.array([r[0] for r in rows]))
    return f"{100 * np.median(miss):.0f} / {100 * np.percentile(miss, 90):.0f} cm"


def tally(ahead, clear_only):
    """Forecast by forecast, over every distance ahead: (how many, how many the slope was closer in than
    "no change", how many it was further out in). With `clear_only`, only those in which it was clear."""
    count = closer = further = 0
    for far in AHEAD:
        rows = ahead[far]
        for (measured, still, _), (_, slope, _), (_, _, used) in zip(rows["no change"], rows["the slope"], rows["the slope when it is clear"]):
            if used or not clear_only:
                count += 1
                closer += abs(slope - measured) < abs(still - measured) - 1e-9
                further += abs(slope - measured) > abs(still - measured) + 1e-9
    return count, closer, further


def report(results):
    lines = [
        "# The level ahead: the slope of the last readings against \"no change\", on a real flood",
        "",
        "**Real fixed cameras, a real flood, measured water levels.** Written by `scripts/river_forecast.py` on the",
        "hourly pictures of two river cameras near Tewkesbury, 21 November to 5 December 2012, published with the",
        "water level read from each picture against surveyed points ([credits](../samples/tewkesbury/CREDITS.md)). The",
        "pictures are not in the repository. This is a river, not a street, and not Hyderabad.",
        "",
        "The prediction stage takes a slope through the last three to six readings and carries it forward",
        "(`nirmaldhara/predict.py`). Each table sets that against saying the level will stay where the last reading",
        "put it, which is how a forecasting office judges a forecast. Three days in a row are left out together,",
        "the model learns from the rest, and follows the level through those three as the pictures came. Each cell",
        "is the typical miss and the miss nine in ten were under.",
        "",
    ]
    for camera, r in results.items():
        miss = np.array([abs(read - measured) for measured, read, _, _ in r["now"]])
        held = sum(low <= measured <= high for measured, _, low, high in r["now"])
        lines += [f"## {camera}: {ROLES[camera]}", "",
                  f"{r['pictures']} pictures on {r['days']} days, {r['levels'][0]:.2f} to {r['levels'][1]:.2f} m, left out in {r['runs']} runs of three days. "
                  f"Read by the model through time, with the learnt gauge as one more witness, the level now was {100 * np.median(miss):.0f} cm out, typically, "
                  f"and nine in ten within {100 * np.percentile(miss, 90):.0f} cm. Its range held the level in {held} of {len(miss)}. "
                  f"The dataset's own doubt in a measured level is {100 * r['doubt']:.0f} cm, typically.", ""]
        for kind in KINDS:
            head = "From the camera's readings" if kind == KINDS[0] else "From the measured levels themselves, each with the dataset's own doubt as its range"
            lines += [f"**{head}:**", "", "| Ahead by | Forecasts | No change | The slope | The slope when it is clear | Times it was clear |", "|---|---|---|---|---|---|"]
            for far in AHEAD:
                rows = r["ahead"][kind][far]
                clear = [used for _, _, used in rows["the slope when it is clear"]]
                lines.append(f"| {far[0].upper() + far[1:]} | {len(clear)} | {out_by(rows['no change'])} | {out_by(rows['the slope'])} | "
                             f"{out_by(rows['the slope when it is clear'])} | {sum(clear)} of {len(clear)} |")
            every, clear = tally(r["ahead"][kind], False), tally(r["ahead"][kind], True)
            lines += ["", f"Forecast by forecast, the slope was closer than \"no change\" in {every[1]} of {every[0]} and further out in {every[2]}. "
                      f"Of the {clear[0]} in which it was clear, it was closer in {clear[1]} and further out in {clear[2]}.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--camera", choices=sorted(ROLES), action="append")
    parser.add_argument("--data", default=str(river.DATA))
    parser.add_argument("--keep", help="a folder to keep each strip's rows in, so a second run does not read the pictures again")
    args = parser.parse_args()
    if not (Path(args.data) / "FarsonDigital_CameraImages_NovDec2012").is_dir():
        print(f"The pictures are not in {args.data}. See the top of scripts/river_camera_test.py for where to get them.")
        return 1
    results = {}
    for camera in (args.camera or ROLES):
        shown, _, days, hours, _, _ = whole.load(camera, args.data)
        pictures = {(int(day) // 100, int(day) % 100, int(hour)): picture for picture, day, hour in zip(shown, days, hours)}
        results[camera] = one_camera(camera, rdm.strips_of(camera, args.data, args.keep), pictures)
    text = report(results)
    print(text)
    if not args.camera:
        OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
