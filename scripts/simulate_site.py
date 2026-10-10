"""SIMULATED: one flooding place watched by three cameras, from frames to the site engine's answer.

    python scripts/simulate_site.py            # prints the results and writes docs/site-simulation.md

No real camera, photo or flood is behind any number this prints. It runs the whole chain on rendered
scenes, to check that the parts fit and to see what several cameras are worth when they do not share
their light:

    rendered frames  ->  waterline.locate (the real detector)  ->  depthmodel (one depth from all the
    cameras, through time)  ->  depthmodel.to_reading  ->  state.apply_reading and bands.passability

Three cameras look at the same water from different places, each at its own wall or pillar and its
own distance. On each evening the water rises and falls. Each camera has that evening's conditions:
its own light, rain or murk, and now and then a vehicle parked across its view. On some evenings
it is dark for all three. Half of the evenings are learnt from, with the true depth known; the other
half are read.

The scenes are scripts/simulate_waterline.py's. What they leave out is listed in
docs/waterline-simulation.md, and the detector did far worse on a real flood than on them.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_waterline as sim  # noqa: E402
from nirmaldhara import bands, depthmodel, state, waterline  # noqa: E402

OUT = ROOT / "docs" / "site-simulation.md"
SEED = 2026
EVENINGS, MOMENTS = 20, 6
EVERY = 10                                         # minutes between one moment and the next
SHAPE = (0.3, 0.6, 0.9, 1.0, 0.8, 0.5)             # how an evening's flood rises and falls, as shares of its peak
PEAKS = (0, 6, 10, 14, 18, 22, 26, 30, 35, 40, 45, 50)   # cm: the peak depth of an evening is one of these
BASE_ROW = 215                                     # the row of each strip at which the road is
CAMERAS = {"north": 0.45, "east": 0.6, "south": 0.9}     # cm of height that one row of each camera's strip covers
BY_DAY = (("clear", 0.3), ("murky", 0.2), ("rain", 0.2), ("shadow", 0.1), ("mirror", 0.1), ("vehicle passing", 0.1))
DARK_SHARE, PARKED_SHARE = 0.25, 0.12              # evenings that are dark for all three; a camera's evenings with its view parked across


def make_camera(rng):
    """A camera's own surface and the dry view of it that is kept."""
    scene = sim.make_scene(rng, "clear")
    return {"obj": scene["obj"], "kind": scene["kind"], "reference": scene["reference"]}


def look(rng, camera, condition, depth_cm, cm_per_row):
    """What the detector reports through one camera at one moment: (kind, row)."""
    scene = sim.make_scene(rng, condition)
    scene.update(obj=camera["obj"], kind=camera["kind"], reference=camera["reference"])
    line = None if depth_cm < 2.0 else int(round(BASE_ROW - depth_cm / cm_per_row))
    result = waterline.locate(sim.render_frames(rng, scene, line), camera["reference"])
    if result.found:
        return "line", float(result.row)
    return ("dry" if result.reason == "dry" else "other"), None


def make_history(seed=SEED, evenings=EVENINGS):
    """Every moment of every evening: (depths in cm, days, hours, {camera: [(kind, row)]}, {camera: [condition]})."""
    rng = np.random.default_rng(seed)
    cameras = {name: make_camera(rng) for name in CAMERAS}
    names, shares = [c for c, _ in BY_DAY], np.array([s for _, s in BY_DAY])
    depths, days, hours = [], [], []
    reports = {name: [] for name in CAMERAS}
    conditions = {name: [] for name in CAMERAS}
    for evening in range(evenings):
        peak = PEAKS[int(rng.integers(len(PEAKS)))]
        dark = rng.random() < DARK_SHARE
        tonight = {}
        for name in CAMERAS:
            if rng.random() < PARKED_SHARE:
                tonight[name] = "parked at night" if dark else "vehicle parked"
            elif dark:
                tonight[name] = "storm at night" if rng.random() < 0.3 else "night"
            else:
                tonight[name] = str(rng.choice(names, p=shares / shares.sum()))
        for moment, share in enumerate(SHAPE[:MOMENTS]):
            depth = peak * share
            depths.append(depth)
            days.append(evening)
            hours.append(evening * 24 + 17 + moment * EVERY / 60.0)
            for name, cm_per_row in CAMERAS.items():
                reports[name].append(look(rng, cameras[name], tonight[name], depth, cm_per_row))
                conditions[name].append(tonight[name])
    return np.array(depths), np.array(days), np.array(hours, dtype=float), reports, conditions


def car_answer(low_cm, high_cm, confidence):
    return bands.passability(low_cm, high_cm, confidence)["car"]


def run(seed=SEED, evenings=EVENINGS):
    depths, days, hours, reports, conditions = make_history(seed, evenings)
    levels = depths / 100.0                                              # the model works in metres
    seen = days % 2 == 0
    pick = lambda mask, chosen: {n: [s for s, k in zip(reports[n], mask) if k] for n in chosen}        # noqa: E731
    rows = {name: sim.ROWS for name in CAMERAS}
    unseen = np.flatnonzero(~seen)
    out = {"errors": {}, "known": {}, "answers": {}}
    sets = {"north alone": ["north"], "east alone": ["east"], "south alone": ["south"], "north and east": ["north", "east"],
            "all three": ["north", "east", "south"]}
    for label, chosen in sets.items():
        model = depthmodel.learn(levels[seen], pick(seen, chosen), rows, days[seen], hours[seen], cameras={n: n for n in chosen})
        for way in ("each moment", "through time"):
            if way == "each moment":
                answers = [depthmodel.believe(model, {n: reports[n][i] for n in chosen}) for i in unseen]
            else:
                answers = depthmodel.follow(model, [(hours[i], {n: reports[n][i] for n in chosen}) for i in unseen])
            key = f"{label}, {way}"
            out["errors"][key] = np.array([abs(a.level - levels[i]) * 100 for a, i in zip(answers, unseen)])
            out["known"][key] = float(np.mean([a.informed >= 0.6 for a in answers]))
            if key == "all three, through time":
                # The last link: the model's answer handed to the site engine, and the engine's answer for a car
                # set beside the answer the true depth would give.
                site, verdicts = state.Site("simulated"), []
                for a, i in zip(answers, unseen):
                    reading = depthmodel.to_reading(a, road=0.0, ts=hours[i] * 3600, device="three cameras")
                    site = state.apply_reading(site, reading)
                    verdicts.append((car_answer(reading.low, reading.high, reading.confidence), car_answer(depths[i], depths[i], 1.0), site.state))
                out["answers"] = verdicts
                out["model"] = model
    out["blocked"] = {name: float(np.mean([c in ("vehicle parked", "parked at night") for c in conditions[name]])) for name in CAMERAS}
    out["dark"] = float(np.mean([c in ("night", "storm at night", "parked at night") for c in conditions["north"]]))
    out["moments"] = (int(seen.sum()), int((~seen).sum()))
    return out


def report(r, seed=SEED):
    line = lambda errors: f"{np.median(errors):.1f} cm | {np.percentile(errors, 90):.1f} cm | {np.mean(errors > 10):.0%}"       # noqa: E731
    lines = [
        "# One flooding place, three cameras, from frames to the engine's answer: a simulation",
        "",
        f"**SIMULATED. No real camera, photo or flood is behind any number here.** Written by `scripts/simulate_site.py` (seed {seed}).",
        "Rendered scenes are read by the real detector, joined by `nirmaldhara/depthmodel.py`, and handed to the site",
        "engine. It checks that the chain holds together, and shows what several cameras are worth when each has its",
        "own light. On a real flood the detector was tens of centimetres out, where on these scenes it is fractions",
        "of one ([waterline-river.md](waterline-river.md)).",
        "",
        "## What was simulated",
        "",
        f"- Three cameras on the same water, at {', '.join(f'{v} cm' for v in CAMERAS.values())} of height to a row.",
        f"- {EVENINGS} evenings of {MOMENTS} moments each, {EVERY} minutes apart. On each the water rises to a peak of 0 to 50 cm and falls again.",
        f"- Each camera has its own conditions each evening: clear, murky, rain, a shadow, a mirror-like surface or a passing vehicle. A vehicle",
        f"  was parked across a camera's view on {', '.join(f'{v:.0%}' for v in r['blocked'].values())} of its moments, and it was dark for all three on {r['dark']:.0%}.",
        f"- {r['moments'][0]} moments were learnt from, with the true depth known, and {r['moments'][1]} read.",
        "",
        "## Depth",
        "",
        "| Read by | Typical error | 90% under | More than 10 cm out | Moments with a confidence of 0.6 or more |",
        "|---|---|---|---|---|",
    ]
    for key, errors in r["errors"].items():
        lines.append(f"| {key.capitalize()} | {line(errors)} | {r['known'][key]:.0%} |")
    answers = r["answers"]
    agree = sum(model == truth for model, truth, _ in answers)
    unsafe = sum(model == bands.PASSABLE and truth != bands.PASSABLE for model, truth, _ in answers)
    cautious = sum(model != bands.PASSABLE and truth == bands.PASSABLE for model, truth, _ in answers)
    states = sorted({s for _, _, s in answers})
    lines += [
        "",
        "## The engine's answer for a car",
        "",
        "All three cameras, through time, handed to the site engine as readings. The answer for a car from the",
        "model's range is set beside the answer the true depth would give.",
        "",
        f"- The same answer in {agree} of {len(answers)} moments.",
        f"- **Passable when the true depth said not: {unsafe}.**",
        f"- Not passable when the true depth said it was: {cautious}. A range's upper end decides, so a wide range errs this way.",
        f"- The site passed through these states: {', '.join(states)}.",
        "",
        "## How to read this",
        "",
        "- **This is a check that the parts fit, and a statement of what independence is worth.** Each camera here has",
        "  its own light, drawn apart from the others. That is what cameras at different angles would have to be like",
        "  for these numbers to mean anything outside the simulation, and no real pair has been looked at.",
        "- **One camera is blind when a vehicle parks across it. Three are not.** The share of moments at which the",
        "  model was confident enough for the engine to call a road passable is the plainest gain, with the readings",
        "  more than 10 cm out.",
        "- **Following the level through time did not help here.** A camera keeps its conditions for a whole evening,",
        "  so what it gets wrong it gets wrong at every moment of it, and repeating a mistake is not evidence. And the",
        "  water here rises by up to 15 cm between one moment and the next: a model that expects the level to stay",
        "  near where it was lags behind a fast rise. On the river, where the level moved a centimetre or two an",
        "  hour, following it through time did help.",
        "- **The errors are the renderer's.** The detector reads these scenes to within a centimetre or two. It read a",
        "  real flood to within 13 cm, typically, at the better of two cameras.",
        "- Nothing here is a camera at a site, and nothing in the system calls this chain.",
        "",
    ]
    return "\n".join(lines)


def main():
    text = report(run())
    print(text)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
