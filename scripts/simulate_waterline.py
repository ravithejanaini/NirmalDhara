"""SIMULATED: how well does the statistical waterline detector find the water, and when does it fail?

    python scripts/simulate_waterline.py            # prints the table and writes docs/waterline-simulation.md
    python scripts/simulate_waterline.py --quick    # fewer scenes, for a fast look

Scenes are rendered here, so the true waterline is known exactly. Each scene is a strip down a
gauge, a concrete pillar or a painted wall, with water rising up it, under one hard condition at a
time: murky water, a mirror-calm reflection, night, rain, a shadow edge, a wet tide mark above the
water, a vehicle passing or parked in the way, a shaking camera with changed light, and all of the bad weather at once.

The detector is src/nirmaldhara/waterline.py. Three ways of using it are compared:

    fixed camera, tracked    a dry reference view, six frames per reading, eight readings filtered
    fixed camera, one go     a dry reference view and six frames, no history
    one photo                a single frame and nothing else, which is all a phone photo gives

These scenes are my own renderings. They are harder than a clean test and easier than a real street
in ways nobody has listed. This measures the method against stated difficulties, not against a flood.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import waterline  # noqa: E402

ROWS, COLUMNS, FRAMES = 240, 36, 6
CM_PER_ROW = 0.6                      # a 150 cm gauge about 250 pixels tall: a camera at middle distance
OUT = ROOT / "docs" / "waterline-simulation.md"
CONDITIONS = ("clear", "murky", "mirror", "night", "rain", "shadow", "tide mark", "vehicle passing", "vehicle parked", "shake and light", "storm at night")


def smooth(rng, shape, scale):
    """A random field with structure at about `scale` pixels."""
    small = rng.normal(size=(shape[0] // scale + 2, shape[1] // scale + 2))
    rows = np.linspace(0, small.shape[0] - 1.001, shape[0])
    cols = np.linspace(0, small.shape[1] - 1.001, shape[1])
    r0, c0 = rows.astype(int), cols.astype(int)
    fr, fc = (rows - r0)[:, None], (cols - c0)[None, :]
    return ((1 - fr) * (1 - fc) * small[r0][:, c0] + (1 - fr) * fc * small[r0][:, c0 + 1]
            + fr * (1 - fc) * small[r0 + 1][:, c0] + fr * fc * small[r0 + 1][:, c0 + 1])


def make_object(rng):
    """The dry surface: a painted gauge, a concrete pillar, or a stained wall. Grey levels 0-255, 3 channels."""
    kind = rng.choice(["gauge", "pillar", "wall"])
    if kind == "gauge":
        base = np.full((ROWS, COLUMNS), 205.0)
        for row in range(0, ROWS, 8):
            base[row:row + 2, : COLUMNS // (1 if row % 40 == 0 else 2)] = 45.0
        tint = np.array([1.0, 1.0, 0.92])
    elif kind == "pillar":
        base = 130.0 + 18 * smooth(rng, (ROWS, COLUMNS), 12) + 6 * rng.normal(size=(ROWS, COLUMNS))
        tint = np.array([1.0, 0.99, 0.96])
    else:
        base = 165.0 + 25 * smooth(rng, (ROWS, COLUMNS), 30) + 10 * smooth(rng, (ROWS, COLUMNS), 5)
        tint = np.array([1.0, 0.93, 0.80])
    return np.clip(base, 0, 255)[..., None] * tint


def render(rng, condition, line, frames=FRAMES, obj=None):
    """(frames, dry reference, object). `line` is the true waterline row, or None for a dry scene."""
    obj = make_object(rng) if obj is None else obj
    storm = condition == "storm at night"
    night = condition == "night" or storm
    rain = condition == "rain" or storm
    gain = 0.13 if night else rng.uniform(0.55, 1.4) if condition == "shake and light" else rng.uniform(0.85, 1.1)
    noise = 9.0 if night else 3.0
    reflect = 0.75 if condition == "mirror" else 0.0 if condition == "murky" else rng.uniform(0.15, 0.45)
    calm = condition == "mirror"
    shift = int(rng.integers(-3, 4)) if condition == "shake and light" else 0
    shadow_row = int(rng.integers(30, ROWS - 30)) if condition == "shadow" else None
    reference = np.clip(obj + rng.normal(0, 3, obj.shape), 0, 255)
    water_colour = np.array([118.0, 100.0, 76.0]) * rng.uniform(0.75, 1.15)
    lit = obj.copy()
    if shadow_row is not None:
        lit[shadow_row:] *= 0.68                                         # a shadow falls across the lower part
    if condition == "tide mark" and line is not None:
        lit[max(0, line - int(rng.integers(6, 22))):] *= 0.84            # still wet from an earlier, higher level
    out = []
    parked_top = int(rng.integers(ROWS // 3, ROWS // 2))
    phase = rng.uniform(0, 6.28)
    for t in range(frames):
        frame = lit.copy()
        if line is not None:
            wave = 0.0 if calm else 1.5 * np.sin(phase + 1.3 * t)
            edge = int(round(line + wave))
            below = np.arange(edge, ROWS)
            mirrored = np.clip(2 * edge - below - 1, 0, ROWS - 1)
            ripple = (0 if calm else 2.5) * np.sin(0.35 * below + 0.9 * t + phase)
            reflection = np.stack([np.roll(lit[m], int(round(r)), axis=0) for m, r in zip(mirrored, ripple)]) if len(below) else lit[:0]
            surface = water_colour + (4 if calm else 14) * smooth(rng, (len(below) + 1, COLUMNS), 6)[: len(below), :, None]
            frame[edge:] = (1 - reflect) * surface + reflect * reflection
            if night and len(below):                                      # a headlight's glare lying on the water
                rows_in = (below - edge)[:, None] / max(1, len(below))
                frame[edge:] += 900 * rng.uniform(0.2, 1.0) * np.exp(-((rows_in - rng.uniform(0.2, 0.8)) / 0.12) ** 2)[..., None]
        if (condition == "vehicle passing" and t in (1, 2)) or condition == "vehicle parked":
            top = parked_top if condition == "vehicle parked" else int(rng.integers(ROWS // 3, ROWS // 2))
            frame[top:] = np.array([60.0, 62.0, 70.0]) + 25 * smooth(rng, (ROWS - top, COLUMNS), 8)[..., None]
        frame = frame * gain
        if rain:
            frame = (frame + np.roll(frame, 1, axis=0) + np.roll(frame, -1, axis=0) + np.roll(frame, 2, axis=0)) / 4
            frame = 0.75 * frame + 0.25 * frame.mean()
            for column in rng.integers(0, COLUMNS, size=5):
                start = int(rng.integers(0, ROWS - 40))
                frame[start:start + 40, column] += 45 * (0.4 if night else 1.0)
        frame = np.roll(frame, shift, axis=0) + rng.normal(0, noise, frame.shape)
        out.append(np.clip(frame, 0, 255))
    return np.array(out), reference, obj


def one_scene(rng, condition):
    """Errors in cm for the three ways of using the detector, for one random scene."""
    line = int(rng.integers(40, ROWS - 30))
    frames, reference, obj = render(rng, condition, line)
    result = {}
    single = waterline.locate(frames, reference)
    result["one go"] = single
    history = [single]
    for step in range(7):                                                # seven more readings of the same level
        more, _, _ = render(rng, condition, line, obj=obj)
        history.append(waterline.locate(more, reference))
    result["tracked"] = waterline.track(history)[-1]
    result["photo"] = waterline.locate(frames[0])
    return line, result


def measure(condition, scenes, seed):
    rng = np.random.default_rng(seed)
    rows = {mode: {"errors": [], "covered": 0, "found": 0} for mode in ("tracked", "one go", "photo")}
    for _ in range(scenes):
        line, result = one_scene(rng, condition)
        for mode, reading in result.items():
            if reading.found:
                rows[mode]["found"] += 1
                rows[mode]["errors"].append(abs(reading.row - line) * CM_PER_ROW)
                rows[mode]["covered"] += reading.low - 1 <= line <= reading.high + 1
    return rows


def dry_false_alarms(scenes, seed):
    """A dry strip must not be given a waterline. Returns the share that were, per mode."""
    rng = np.random.default_rng(seed)
    alarms = {"one go": 0, "photo": 0}
    kinds = ("clear", "night", "rain", "shadow", "shake and light")
    by_kind = {kind: 0 for kind in kinds}
    for n in range(scenes):
        condition = kinds[n % 5]
        frames, reference, _ = render(rng, condition, None)
        found = waterline.locate(frames, reference).found
        alarms["one go"] += found
        by_kind[condition] += found
        alarms["photo"] += waterline.locate(frames[0]).found
    out = {mode: count / scenes for mode, count in alarms.items()}
    out["by kind"] = {kind: count / (scenes / 5) for kind, count in by_kind.items()}
    return out


def cell(stats, scenes):
    if not stats["errors"]:
        return "nothing found"
    errors = np.array(stats["errors"])
    return (f"{np.median(errors):.1f} cm, 95% under {np.percentile(errors, 95):.1f} cm; "
            f"found {stats['found'] / scenes:.0%}, interval right {stats['covered'] / max(1, stats['found']):.0%}")


def report(results, alarms, scenes, seed):
    lines = [
        "# Finding the waterline without a model: a simulation",
        "",
        "**SIMULATED. Every scene here was rendered by the script, so no real camera, photo or flood is behind",
        f"any number.** Written by `scripts/simulate_waterline.py` (seed {seed}, {scenes} scenes per condition).",
        "",
        "The detector is `src/nirmaldhara/waterline.py`: a Bayesian change-point model over several cues (the",
        "difference from a dry view of the same spot, frame-to-frame flicker, brightness, texture and colour),",
        "combined into one distribution over rows, then filtered through time with a hidden Markov model.",
        f"One row is {CM_PER_ROW} cm, as for a 150 cm gauge about 250 pixels tall.",
        "",
        "## Result",
        "",
        "Each cell: typical error, the error 95% of readings stay under, how often a waterline was reported,",
        "and how often the true line was inside the 90% interval the detector gave.",
        "",
        "| Condition | Fixed camera, tracked over 8 readings | Fixed camera, one reading | One photo, nothing else |",
        "|---|---|---|---|",
    ]
    for condition in CONDITIONS:
        row = results[condition]
        lines.append(f"| {condition} | {cell(row['tracked'], scenes)} | {cell(row['one go'], scenes)} | {cell(row['photo'], scenes)} |")
    lines += [
        "",
        f"On dry scenes, a waterline was wrongly reported in {alarms['one go']:.0%} of fixed-camera readings and",
        f"{alarms['photo']:.0%} of single photos.",
        "",
    ]
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--seed", type=int, default=2026)       # the settings were chosen on seed 11
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    scenes = 30 if args.quick else 150
    results = {condition: measure(condition, scenes, args.seed + n) for n, condition in enumerate(CONDITIONS)}
    alarms = dry_false_alarms(scenes, args.seed + 100)
    lines = report(results, alarms, scenes, args.seed)
    print("\n".join(lines[lines.index("## Result"):]))
    print("dry false alarms by kind:", {k: f"{v:.0%}" for k, v in alarms["by kind"].items()})
    if not args.quick and not args.no_write:
        notes = (ROOT / "docs" / "waterline-notes.md")
        OUT.write_text("\n".join(lines) + (notes.read_text("utf-8") if notes.exists() else ""), encoding="utf-8", newline="\n")
        print(f"Written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
