"""SIMULATED: the storage equation on a made underpass with made storms (nirmaldhara/inflow.py).

    python scripts/simulate_inflow.py        # prints the results and writes docs/inflow-simulation.md

No place in this project has a flood on record, so nirmaldhara/inflow.py cannot be judged on a real
one. This makes floods whose true figures are known and asks the module for them. The dip is the
worked example of METHOD.md section 15.1. The water in it is moved by the same equation the module
uses, so this shows that the arithmetic holds together and how it bends when the readings and the
rain are worse. It cannot show that a real underpass behaves this way.

Four things are tried:

    what the floods reveal    the ground the water came from and the rate it drains at, against the
                              figures the floods were made with, from readings as close as a painted
                              gauge gives (3 cm) and as loose as a wheel or a kerb gives (8 cm)
    each flood from the       every flood after the first played forward from the ones before it,
    ones before               with the rain known exactly, known to a tenth, and a fifth of what fell,
                              which is how far short docs/watch-history.md found the forecast
    minutes to no-go          when cars will lose passage, said while the water is still shallow: by
                              the straight line of predict.py and by the same line through the volume
    the rain that closes      the rain in an hour that would close the dry road to each class
    the road
"""

import sys
from pathlib import Path
from random import Random
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import inflow  # noqa: E402
from nirmaldhara.bands import NO_GO_CM  # noqa: E402
from nirmaldhara.predict import minutes_to_no_go, rise_rate  # noqa: E402
from nirmaldhara.volume import VolumeCurve  # noqa: E402

OUT = ROOT / "docs" / "inflow-simulation.md"
PROFILE, WIDTH = [(-60, 2.4), (0, 0.0), (40, 2.0)], 14         # METHOD 15.1: ramps of 4% and 5%
AREA, DRAIN = 8000.0, 0.04                                     # the ground that drains to it; 40 litres a second out
STORMS, EVERY, READ_EVERY, SEED = 24, 300, 120, 11       # rain in five-minute steps; a reading every two minutes
DOUBTS = {"a painted gauge, 3 cm": 3.0, "a wheel or a kerb, 8 cm": 8.0}
RAINS = ("known exactly", "known to a tenth", "a fifth of what fell")
SAID_AT_CM = 8.0                                               # the forecast is made when the reading first passes this


def storm(rng):
    """One made storm: [(seconds an interval ended, mm in it)] in five-minute steps, rising to a peak and falling."""
    total, steps = rng.uniform(15, 80), rng.choice((6, 9, 12, 18))
    shape = [min(i + 1, steps - i) for i in range(steps)]
    return [(EVERY * (i + 1), total * part / sum(shape)) for i, part in enumerate(shape)]


def readings_of(dip, rain, doubt, rng):
    """(readings, true depths by second) of the flood a storm makes, read every two minutes to within `doubt`."""
    truth = dict(inflow._run(dip, 0.0, AREA, DRAIN, rain, 8 * 3600))
    out = []
    for t in range(READ_EVERY, 8 * 3600 + 1, READ_EVERY):
        if truth[t] > 1.0:
            seen = truth[t] + rng.uniform(-doubt / 2, doubt / 2)
            out.append((t, max(seen - doubt, 0.0), seen + doubt))
    return out, truth


def as_known(rain, how, rng):
    factor = {"known exactly": 1.0, "known to a tenth": rng.uniform(0.9, 1.1), "a fifth of what fell": 0.2}[how]
    return [(ts, mm * factor) for ts, mm in rain]


def run(seed=SEED, count=STORMS):
    dip = VolumeCurve(PROFILE, WIDTH)
    rng = Random(seed)
    storms = [storm(rng) for _ in range(count)]
    out = {"revealed": {}, "forward": {}, "minutes": {}, "storms": [(sum(mm for _, mm in s), len(s) * EVERY // 60) for s in storms]}
    for label, doubt in DOUBTS.items():
        made = [readings_of(dip, s, doubt, Random(seed + i)) for i, s in enumerate(storms)]
        each = [inflow.reveal(dip, readings, s, seed=i) for i, ((readings, _), s) in enumerate(zip(made, storms))]
        out["revealed"][label] = {"one flood": each[0], "three floods": inflow.together(each[:3]), "all of them": inflow.together(each)}
        for how in RAINS:
            known = Random(seed + 100)
            floods = [(readings, s, as_known(s, how, known)) for (readings, _), s in zip(made, storms)]
            out["forward"][(label, how)] = inflow.check(dip, floods)
        early, late = [], []
        for (readings, truth), s in zip(made, storms):
            lost = next((t for t in sorted(truth) if truth[t] >= NO_GO_CM["car"]), None)
            at = next((i for i, r in enumerate(readings) if i >= 2 and r[2] >= SAID_AT_CM), None)
            if lost is None or at is None or readings[at][0] >= lost:
                continue
            recent, left = readings[max(0, at - 5):at + 1], (lost - readings[at][0]) / 60.0
            rate = rise_rate([(r[0] / 60.0, r[2]) for r in recent])
            straight = minutes_to_no_go(recent[-1][2], rate)["car"] if rate and rate > 0 else None
            stored = inflow.at_this_inflow(dip, recent)
            if straight is not None and stored is not None:
                early.append(straight - left)
                late.append(stored["car"][0] - left)
        out["minutes"][label] = (early, late)
    exact = inflow.Revealed(inflow.Range(AREA, AREA, AREA), inflow.Range(DRAIN, DRAIN, DRAIN))
    close = out["revealed"]["a painted gauge, 3 cm"]["three floods"]
    out["guidance"] = {vehicle: (inflow.guidance(exact, dip)[vehicle][0], inflow.guidance(close, dip)[vehicle]) for vehicle in NO_GO_CM}
    return out


def held(played):
    return sum(p["held"] for p in played), len(played)


def report(result):
    show = lambda r, unit, scale=1.0: "not given" if r is None else f"{scale * r.low:.0f} to {scale * r.high:.0f} {unit}, about {scale * r.mid:.0f}"      # noqa: E731
    lines = [
        "# The storage equation on a made underpass",
        "",
        "**SIMULATED. No real place, rain or flood is behind any number here.** Written by `scripts/simulate_inflow.py`. The underpass is the worked example of",
        f"METHOD.md section 15.1: ramps of 4% and 5%, 14 m wide. {len(result['storms'])} storms were made, of "
        f"{min(t for t, _ in result['storms']):.0f} to {max(t for t, _ in result['storms']):.0f} mm in "
        f"{min(m for _, m in result['storms'])} to {max(m for _, m in result['storms'])} minutes, and the water was moved by the",
        "same equation `nirmaldhara/inflow.py` uses. So this shows the arithmetic holding together, and how it bends as",
        "the readings and the rain get worse. It cannot show that a real underpass behaves this way. No place in this",
        "project has a flood on record.",
        "",
        f"The floods were made with {AREA:.0f} square metres of ground draining to the dip and {1000 * DRAIN:.0f} litres a second leaving it.",
        "",
        "## What the floods reveal",
        "",
        "| Depth read by | From | The ground the water came from | The rate it drains at |", "|---|---|---|---|",
    ]
    for label, by_count in result["revealed"].items():
        for count, found in by_count.items():
            lines.append(f"| {label[0].upper() + label[1:]} | {count[0].upper() + count[1:]} | {show(found.area_m2, 'sq m')} | {show(found.drain_m3s, 'litres a second', 1000.0)} |")
    lines += ["", "## Each flood from the ones before it", "",
              "Every flood after the first, played forward from its first reading by what the floods before it revealed.", "",
              "| Depth read by | The rain | The deepest water said held the deepest read | Width of what was said |", "|---|---|---|---|"]
    for (label, how), played in result["forward"].items():
        caught, count = held(played)
        width = median(p["peak said"][1] - p["peak said"][0] for p in played) if played else 0.0
        lines.append(f"| {label[0].upper() + label[1:]} | {how[0].upper() + how[1:]} | {caught} of {count} | {width:.0f} cm |")
    lines += ["", "## Minutes until cars lose passage", "",
              f"Said when the reading first passes {SAID_AT_CM:.0f} cm, in the floods that went on to 20 cm. Minus is too soon.", "",
              "| Depth read by | Floods | The straight line of `predict.py` | The same line through the volume |", "|---|---|---|---|"]
    for label, (early, late) in result["minutes"].items():
        both = lambda values: "-" if not values else f"{round(median(values)):+d} minutes, typically; {round(min(values)):+d} to {round(max(values)):+d}"      # noqa: E731
        lines.append(f"| {label[0].upper() + label[1:]} | {len(early)} | {both(early)} | {both(late)} |")
    lines += ["", "## The rain that closes the road", "",
              "The rain in one hour that would bring a dry road to the depth at which each class loses passage.", "",
              "| Class | With the true figures | With what three floods revealed, read by a painted gauge |", "|---|---|---|"]
    for vehicle, (true, (least, most)) in result["guidance"].items():
        lines.append(f"| {vehicle.replace('_', ' ')} | {true:.1f} mm | {least:.1f} to {most:.1f} mm |")
    lines += ["", "## How to read this", "",
              "- **The figures come back because the water was made by the same equation.** That is a check on the arithmetic and",
              "  on nothing else.",
              "- **Loose readings give wide answers, not wrong ones.** Read to 8 cm, the ground the water came from is known to",
              "  within a wide range, and what is said ahead is as wide.",
              "- **A forecast from rain is no better than the rain.** With a fifth of the rain that fell, which is how far short",
              "  [watch-history.md](watch-history.md) found the forecast the live system is fed, the deepest water said held the",
              "  deepest read in none of the floods.",
              "- **With water running in steadily the straight line says cars are lost sooner than they are**, because a dip",
              "  widens as it fills: 16 minutes where it is 27, in the case `tests/test_inflow.py` works by hand. In these made",
              "  storms the rain was still building when the forecast was made, and the two lines came out within a minute or",
              "  two of each other. Neither knows that the rain will ease or grow.",
              "- **The rain that closes the road needs no forecast.** It is a figure for this place that a person can hold any",
              "  forecast, warning or gauge reading against.",
              "", "## What this is not", "",
              "- **Not a real underpass.** A real one has drains that block, pumps that start late, and water arriving from",
              "  streets around it after the rain has stopped.",
              "- **Not a test of the equation.** The made water obeys it by construction.",
              "- **Not connected to anything.** Nothing calls `nirmaldhara/inflow.py`, and no place in the registry has a road",
              "  profile, without which it cannot run.",
              ""]
    return "\n".join(lines)


def main():
    text = report(run())
    print(text)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
