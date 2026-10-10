"""SIMULATED: how well does the statistical waterline detector find the water, and when does it fail?

    python scripts/simulate_waterline.py                # the full table, written to docs/waterline-simulation.md
    python scripts/simulate_waterline.py --quick        # fewer scenes, the design conditions only
    python scripts/simulate_waterline.py --calibrate    # fit the interval widths (see waterline.QUANTILE)

Scenes are rendered here, so the true waterline is known exactly. Each scene is a strip down a
gauge, a concrete pillar or a painted wall, with water rising up it, under one hard condition.

Two sets of conditions are kept apart on purpose:

    design      the detector was built and adjusted while looking at these
    held out    written before the detector was finished and never used to adjust it; they are
                run once, at the end, to see what happens on difficulties it was not shaped for

Four ways of using the detector (src/nirmaldhara/waterline.py) are compared:

    tracked     a dry reference view, six frames per reading, eight readings filtered through time
    one reading a dry reference view and six frames, no history
    clip        six frames and no dry view: flicker only, as from a phone held still for two seconds
    photo       one frame and nothing else

These scenes are my own renderings. They are harder than a clean test and easier than a real street
in ways nobody has listed. This measures the method against stated difficulties, not against a flood.
"""

import argparse
import io
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import waterline  # noqa: E402

ROWS, COLUMNS, FRAMES, READINGS = 240, 36, 6, 8
CM_PER_ROW = 0.6                      # a 150 cm gauge about 250 pixels tall: a camera at middle distance
OUT = ROOT / "docs" / "waterline-simulation.md"
NOTES = ROOT / "docs" / "waterline-notes.md"
DESIGN = ("clear", "murky", "mirror", "night", "rain", "shadow", "tide mark", "vehicle passing",
          "vehicle parked", "shake and light", "storm at night")
HELD_OUT = ("fog", "foam line", "sun glint", "pole in front", "compressed", "night shadow",
            "parked at night", "dusk flat water", "rising")
DRY_DESIGN = ("clear", "night", "rain", "shadow", "shake and light")
DRY_HELD_OUT = ("fog", "pole in front", "compressed", "night shadow")
DRY_KINDS = DRY_DESIGN + DRY_HELD_OUT
MODES = ("tracked", "single", "clip", "photo")
CALIBRATION_SEED, REPORT_SEED = 11, 2026


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
    kind = str(rng.choice(["gauge", "pillar", "wall"]))
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
    return kind, np.clip(base, 0, 255)[..., None] * tint


def jpeg(frame, quality=35):
    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, "JPEG", quality=quality)
    return np.asarray(Image.open(io.BytesIO(buffer.getvalue())).convert("RGB"))


def as_picture(frame, compressed):
    frame = np.rint(np.clip(frame, 0, 255)).astype(np.uint8)
    return jpeg(frame) if compressed else frame


def make_scene(rng, condition):
    """Everything about a scene that stays the same from frame to frame and reading to reading."""
    night = condition in ("night", "storm at night", "night shadow", "parked at night")
    dusk = condition == "dusk flat water"
    kind, obj = make_object(rng)
    scene = {
        "condition": condition, "kind": kind, "obj": obj, "night": night,
        "rain": condition in ("rain", "storm at night"),
        "gain": 0.13 if night else 0.5 if dusk else rng.uniform(0.55, 1.4) if condition == "shake and light" else rng.uniform(0.85, 1.1),
        "noise": 9.0 if night else 4.0 if dusk else 3.0,
        "reflect": 0.75 if condition == "mirror" else 0.0 if condition == "murky" or dusk else rng.uniform(0.15, 0.45),
        "calm": condition == "mirror",
        "ripple": 4.0 if condition == "mirror" else 3.0 if dusk else 14.0,
        "shift": int(rng.integers(-3, 4)) if condition == "shake and light" else 0,
        "tremble": condition == "shake and light",
        "shadow_row": int(rng.integers(30, ROWS - 30)) if condition in ("shadow", "night shadow") else None,
        "shadow_gain": 0.6 if condition == "night shadow" else 0.68,
        "tide": int(rng.integers(6, 22)) if condition == "tide mark" else None,
        "water": np.array([118.0, 100.0, 76.0]) * rng.uniform(0.75, 1.15),
        "parked_top": int(rng.integers(ROWS // 3, ROWS // 2)) if condition in ("vehicle parked", "parked at night") else None,
        "vehicle": np.array([60.0, 62.0, 70.0]) + 25 * smooth(rng, (ROWS, COLUMNS), 8)[..., None],      # parked: it does not change
        "pole": int(rng.integers(2, COLUMNS - 13)) if condition == "pole in front" else None,
        "pole_look": 55.0 + 10 * smooth(rng, (ROWS, 11), 6)[..., None] * np.array([1.0, 1.0, 1.05]),
        "phase": float(rng.uniform(0, 6.28)),
        "compressed": condition == "compressed",
    }
    if dusk:                                                            # water exactly as bright as the surface
        scene["water"] = np.array([1.06, 1.0, 0.86]) / 0.9733 * float(obj.mean())
    scene["reference"] = np.array([as_picture(obj + rng.normal(0, 3, obj.shape), scene["compressed"]) for _ in range(4)])
    return scene


def render_frames(rng, scene, line, frames=FRAMES):
    """The frames of one reading, 8-bit. `line` is the true waterline row, or None for a dry scene."""
    condition, lit = scene["condition"], scene["obj"].copy()
    if scene["shadow_row"] is not None:
        lit[scene["shadow_row"]:] *= scene["shadow_gain"]                # a shadow falls across the lower part
    if scene["tide"] is not None and line is not None:
        lit[max(0, line - scene["tide"]):] *= 0.84                      # still wet from an earlier, higher level
    out = []
    for t in range(frames):
        frame = lit.copy()
        if line is not None:
            wave = 0.0 if scene["calm"] else 1.5 * np.sin(scene["phase"] + 1.3 * t)
            edge = int(round(line + wave))
            below = np.arange(edge, ROWS)
            if len(below):
                mirrored = np.clip(2 * edge - below - 1, 0, ROWS - 1)
                sway = np.rint((0.0 if scene["calm"] else 2.5) * np.sin(0.35 * below + 0.9 * t + scene["phase"])).astype(int)
                columns = (np.arange(COLUMNS)[None, :] - sway[:, None]) % COLUMNS
                reflection = lit[mirrored[:, None], columns]
                surface = scene["water"] + scene["ripple"] * smooth(rng, (len(below) + 1, COLUMNS), 6)[: len(below), :, None]
                frame[edge:] = (1 - scene["reflect"]) * surface + scene["reflect"] * reflection
                if scene["night"]:                                       # a headlight's glare lying on the water
                    depth = (below - edge)[:, None] / max(1, len(below))
                    frame[edge:] += 900 * rng.uniform(0.2, 1.0) * np.exp(-((depth - rng.uniform(0.2, 0.8)) / 0.12) ** 2)[..., None]
                if condition == "sun glint":
                    frame[edge:][rng.random((len(below), COLUMNS)) < 0.04] += 140.0
                if condition == "foam line":                             # a band of froth and litter at the line
                    band = slice(max(0, edge - 2), min(ROWS, edge + 3))
                    covered = rng.random(COLUMNS) < 0.7
                    froth = 225 + 25 * rng.normal(size=(band.stop - band.start, COLUMNS, 1))
                    frame[band][:, covered] = froth[:, covered]
        if scene["parked_top"] is not None:
            frame[scene["parked_top"]:] = scene["vehicle"][scene["parked_top"]:]
        if condition == "vehicle passing" and t in (1, 2):
            top = int(rng.integers(ROWS // 3, ROWS // 2))
            frame[top:] = np.array([60.0, 62.0, 70.0]) + 25 * smooth(rng, (ROWS - top, COLUMNS), 8)[..., None]
        if scene["pole"] is not None:
            frame[:, scene["pole"]:scene["pole"] + 11] = scene["pole_look"]
        frame = frame * scene["gain"]
        if scene["rain"]:
            frame = (frame + np.roll(frame, 1, axis=0) + np.roll(frame, -1, axis=0) + np.roll(frame, 2, axis=0)) / 4
            frame = 0.75 * frame + 0.25 * frame.mean()
            for column in rng.integers(0, COLUMNS, size=5):
                start = int(rng.integers(0, ROWS - 40))
                frame[start:start + 40, column] += 45 * (0.4 if scene["night"] else 1.0)
        if condition == "fog":
            frame = 0.4 * frame + 0.6 * 170 * scene["gain"]
        down = scene["shift"] + (int(rng.integers(-1, 2)) if scene["tremble"] else 0)
        frame = np.roll(frame, down, axis=0)
        if scene["tremble"]:
            frame = np.roll(frame, int(rng.integers(-1, 2)), axis=1)
        out.append(as_picture(frame + rng.normal(0, scene["noise"], frame.shape), scene["compressed"]))
    return np.array(out)


def render(rng, condition, line, frames=FRAMES, scene=None):
    """One reading of a new or given scene: (frames, dry reference views, scene)."""
    scene = make_scene(rng, condition) if scene is None else scene
    return render_frames(rng, scene, line, frames), scene["reference"], scene


def one_scene(rng, condition):
    """For one random scene: each way of using the detector, with the true line it should have found."""
    line = int(rng.integers(64, ROWS - 30))
    scene = make_scene(rng, condition)
    readings, first = [], None
    for step in range(READINGS):
        frames = render_frames(rng, scene, line - step if condition == "rising" else line)
        first = frames if step == 0 else first
        readings.append(waterline.locate(frames, scene["reference"]))
    last = line - (READINGS - 1) if condition == "rising" else line
    return {"tracked": (waterline.track(readings)[-1], last), "single": (readings[0], line),
            "clip": (waterline.locate(first), line), "photo": (waterline.locate(first[0]), line)}


def measure(job):
    """All scenes of one condition. Returns plain lists, so it can cross a process boundary."""
    condition, scenes, seed = job
    rng = np.random.default_rng(seed)
    out = {mode: {"errors": [], "scores": [], "groups": [], "covered": 0, "found": 0, "blocked": 0} for mode in MODES}
    for _ in range(scenes):
        for mode, (reading, truth) in one_scene(rng, condition).items():
            stats = out[mode]
            stats["blocked"] += "occluded" in reading.reason
            if reading.found:
                stats["found"] += 1
                stats["errors"].append((reading.row - truth) * CM_PER_ROW)
                stats["scores"].append(abs(reading.row - truth) / max(reading.spread, waterline.MIN_SPREAD))
                stats["groups"].append(reading.group)
                stats["covered"] += reading.low <= truth <= reading.high
    return condition, out


def dry_scenes(job):
    """Dry strips must not be given a waterline. Returns, per kind, how many of `scenes` were."""
    kind, scenes, seed = job
    rng = np.random.default_rng(seed)
    alarms = {"single": 0, "clip": 0, "photo": 0}
    for _ in range(scenes):
        scene = make_scene(rng, kind)
        frames = render_frames(rng, scene, None)
        alarms["single"] += waterline.locate(frames, scene["reference"]).found
        alarms["clip"] += waterline.locate(frames).found
        alarms["photo"] += waterline.locate(frames[0]).found
    return kind, alarms


def run_all(conditions, scenes, seed, dry_count, dry_kinds=DRY_KINDS):
    jobs = [(condition, scenes, seed + n) for n, condition in enumerate(conditions)]
    dry_jobs = [(kind, dry_count, seed + 500 + n) for n, kind in enumerate(dry_kinds)]
    workers = int(os.environ.get("WATERLINE_WORKERS", "4"))     # each worker loads numpy; too many exhausts memory
    with ProcessPoolExecutor(max_workers=max(1, min(workers, (os.cpu_count() or 2) - 1))) as pool:
        results = dict(pool.map(measure, jobs))
        alarms = dict(pool.map(dry_scenes, dry_jobs))
    return results, alarms


def cell(stats, scenes):
    blocked = f"; blocked {stats['blocked'] / scenes:.0%}" if stats["blocked"] else ""
    if not stats["errors"]:
        return f"no line reported{blocked}"
    errors = np.abs(stats["errors"])
    return (f"{np.median(errors):.1f} cm, 95% under {np.percentile(errors, 95):.1f}; line {stats['found'] / scenes:.0%}, "
            f"in range {stats['covered'] / max(1, stats['found']):.0%}{blocked}")


def table(results, conditions, scenes):
    lines = ["| Condition | Tracked over 8 readings | One reading | Clip, no dry view | One photo |", "|---|---|---|---|---|"]
    for condition in conditions:
        row = results[condition]
        lines.append(f"| {condition} | " + " | ".join(cell(row[mode], scenes) for mode in MODES) + " |")
    return lines


def suggest(results):
    """The 90% quantile of |error| / spread: how many spreads wide the interval has to be."""
    out = {}
    for name, mode, group in (("normal", "single", "normal"), ("soft", "single", "soft"), ("low light", "single", "low light"),
                              ("tracked", "tracked", None)):
        scores = [score for row in results.values()
                  for score, g in zip(row[mode]["scores"], row[mode]["groups"]) if group is None or g == group]
        out[name] = (float(np.percentile(scores, 90)) if scores else float("nan"), len(scores))
    return out


def report(results, alarms, scenes, dry_count, seed):
    worst = max(alarms[kind]["single"] / dry_count for kind in DRY_KINDS)
    lines = [
        "# Finding the waterline without a model: a simulation",
        "",
        "**SIMULATED. Every scene here was rendered by the script, so no real camera, photo or flood is behind",
        f"any number.** Written by `scripts/simulate_waterline.py` (seed {seed}, {scenes} scenes per condition).",
        "",
        "The detector is `src/nirmaldhara/waterline.py`: a hidden Markov model down the rows of a strip, with four",
        "states (dry, dry but re-lit, water, blocked), likelihoods calibrated on the rows known to be dry, a second",
        f"filter through time, and intervals set by conformal calibration. One row is {CM_PER_ROW} cm, as for a 150 cm",
        "gauge about 250 pixels tall.",
        "",
        "Each cell: typical error and the error 95% of readings stay under; how often a waterline was reported;",
        "how often the true line was inside the 90% interval; and how often the view was reported blocked.",
        "",
        "## Conditions the detector was designed on",
        "",
        *table(results, DESIGN, scenes),
        "",
        "## Conditions held out",
        "",
        "Written before the detector was finished and not used to adjust it.",
        "",
        *table(results, HELD_OUT, scenes),
        "",
        "## Dry scenes",
        "",
        "How often a waterline was reported on a strip with no water in it:",
        "",
        "| Kind of dry scene | One reading | Clip, no dry view | One photo |",
        "|---|---|---|---|",
        *[f"| {kind} | {alarms[kind]['single'] / dry_count:.0%} | {alarms[kind]['clip'] / dry_count:.0%} | {alarms[kind]['photo'] / dry_count:.0%} |"
          for kind in DRY_KINDS],
        "",
        f"With a dry view, the worst kind gave a false waterline {worst:.0%} of the time.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quick", action="store_true", help="30 scenes of each design condition")
    parser.add_argument("--calibrate", action="store_true", help="print the interval widths that give 90% on the design conditions")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--scenes", type=int)
    args = parser.parse_args()
    if args.calibrate or args.quick:
        scenes = args.scenes or (120 if args.calibrate else 30)
        seed = args.seed or CALIBRATION_SEED
        results, alarms = run_all(DESIGN, scenes, seed, 40, DRY_DESIGN)
        print("\n".join(table(results, DESIGN, scenes)))
        print("dry false alarms, one reading:", {kind: f"{alarms[kind]['single'] / 40:.0%}" for kind in DRY_DESIGN})
        print("dry false alarms, clip:", {kind: f"{alarms[kind]['clip'] / 40:.0%}" for kind in DRY_DESIGN})
        for name, (value, count) in suggest(results).items():
            print(f"QUANTILE[{name!r}] = {value:.2f}   (from {count} readings; now {waterline.QUANTILE[name]})")
        return 0
    scenes, seed = args.scenes or 150, args.seed or REPORT_SEED
    results, alarms = run_all(DESIGN + HELD_OUT, scenes, seed, 60)
    text = report(results, alarms, scenes, 60, seed)
    print(text[text.index("## Conditions the detector"):])
    OUT.write_text(text + (NOTES.read_text("utf-8") if NOTES.exists() else ""), encoding="utf-8", newline="\n")
    print(f"Written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
