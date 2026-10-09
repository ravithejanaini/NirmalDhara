"""SIMULATED cameras: does the reference-object method hold up when cameras sit at different angles?

    python scripts/simulate_cameras.py                 # the table, written to docs/camera-simulation.md
    python scripts/simulate_cameras.py --play          # also: pick one camera at random and play a
                                                       # flood from it into the local map (serve_web.py)

No real camera is involved, and nothing reaches AWS. Each simulated camera is a pinhole camera at a
random height, distance, sideways offset, tilt, roll and lens distortion, looking at a vertical
gauge 150 cm tall. The gauge's marks are "clicked" once on a dry view with a little error, as a
person would at enrolment. Water then rises up the gauge and two methods read the depth:

  two marks    METHOD.md C2, estimator 1: top and base marked, one centimetres-per-pixel scale
  three marks  top, middle and base marked, which lets the method undo perspective exactly

This measures the geometry only. It says nothing about finding the waterline in a real image at
night or in rain, which is the hard part and has never been tested.
"""

import argparse
import math
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

GAUGE_CM = 150.0
DEPTHS_CM = (5, 10, 15, 20, 25, 30, 40, 50, 60)
CLICK_SD_PX = 1.5          # error in marking the gauge on the dry view
WATERLINE_SD_PX = 2.0      # error in finding where the water meets the gauge
IMAGE = (1280, 720)
TILT_GROUPS = ((0, 15), (15, 30), (30, 45), (45, 70))
SIZE_GROUPS = ((60, 120), (120, 250), (250, 2000))      # how tall the gauge is in the image, in pixels
OUT = ROOT / "docs" / "camera-simulation.md"


def make_camera(rng, number):
    """One camera at a random place and angle, aimed roughly at the gauge."""
    height = rng.uniform(2.5, 7.0)                 # metres above the road
    distance = rng.uniform(3.0, 25.0)              # metres along the ground to the gauge
    aim = rng.uniform(0.0, 1.2)                    # the height on the gauge it is pointed at
    return {
        "id": f"sim-cam-{number:03d}",
        "height_m": height, "distance_m": distance,
        "side_m": rng.uniform(-3.0, 3.0),
        "tilt": math.atan2(height - aim, distance),            # radians below the horizontal
        "roll": math.radians(rng.uniform(-4.0, 4.0)),
        "focal_px": rng.uniform(700, 1800),
        "distortion": rng.uniform(-0.12, 0.02),                # barrel distortion, as wide lenses have
    }


def project(camera, height_cm):
    """Where the point `height_cm` up the gauge lands in the image, in pixels."""
    tilt = camera["tilt"]
    dx, dy, dz = camera["distance_m"], camera["side_m"], height_cm / 100.0 - camera["height_m"]
    depth = dx * math.cos(tilt) - dz * math.sin(tilt)           # along the camera's axis
    up = dx * math.sin(tilt) + dz * math.cos(tilt)
    x, y = dy / depth, up / depth
    bend = 1 + camera["distortion"] * (x * x + y * y)
    x, y = x * bend, y * bend
    c, s = math.cos(camera["roll"]), math.sin(camera["roll"])
    x, y = x * c - y * s, x * s + y * c
    width, height = camera.get("image", IMAGE)
    return width / 2 + camera["focal_px"] * x, height / 2 - camera["focal_px"] * y


def clicked(rng, point, sd):
    return point[0] + rng.gauss(0, sd), point[1] + rng.gauss(0, sd)


def enrol(rng, camera):
    """The marks a person makes once on the dry view: base, middle and top of the gauge."""
    return {name: clicked(rng, project(camera, cm), CLICK_SD_PX)
            for name, cm in (("base", 0.0), ("middle", GAUGE_CM / 2), ("top", GAUGE_CM))}


def two_marks(marks, waterline):
    """METHOD.md C2 estimator 1, exactly as written: rows only, one scale."""
    scale = GAUGE_CM / (marks["base"][1] - marks["top"][1])
    return (marks["base"][1] - waterline[1]) * scale


def three_marks(marks, waterline):
    """Distance along the gauge in the image, turned into height by the map that perspective obeys."""
    along = lambda p: math.dist(p, marks["base"])                         # noqa: E731
    t_mid, t_top, t = along(marks["middle"]), along(marks["top"]), along(waterline)
    h_mid, h_top = GAUGE_CM / 2, GAUGE_CM
    # h(t) = a t / (1 + b t), fixed by the middle and top marks.
    b = (h_top * t_mid - h_mid * t_top) / (t_mid * t_top * (h_mid - h_top))
    a = h_mid * (1 + b * t_mid) / t_mid
    return a * t / (1 + b * t)


def measure(camera, rng, trials=40):
    """Absolute errors in cm for each method, over every depth and several enrolments."""
    errors = {"two": [], "three": []}
    for _ in range(trials):
        marks = enrol(rng, camera)
        for depth in DEPTHS_CM:
            waterline = clicked(rng, project(camera, depth), WATERLINE_SD_PX)
            errors["two"].append(abs(two_marks(marks, waterline) - depth))
            errors["three"].append(abs(three_marks(marks, waterline) - depth))
    return errors


def usable(camera):
    """A view too distant or too steep to resolve the gauge is refused at enrolment."""
    base, top = project(camera, 0.0), project(camera, GAUGE_CM)
    inside = all(0 <= p[0] <= IMAGE[0] and 0 <= p[1] <= IMAGE[1] for p in (base, top))
    return inside and math.dist(base, top) >= 60            # at least 60 px of gauge: 2.5 cm a pixel


# --- A handheld phone ---------------------------------------------------------------------
# Nominal figures for a recent iPhone's main camera: a 12-megapixel photo of 4032 x 3024 pixels
# and a lens equal to 26 mm on a 36 mm-wide frame. Taken from the published specification, not
# measured on a phone.
PHONE_IMAGE = (4032, 3024)
PHONE_FOCAL_PX = PHONE_IMAGE[0] * 26 / 36
ASSUMED_WHEEL_CM = 62.0                  # METHOD.md section 17: a car wheel is about 62 cm
WHEEL_RANGE_CM = (56.0, 70.0)            # small hatchback to SUV: the photo does not say which
PHONE_DEPTHS_CM = (5, 10, 15, 20, 25)    # above about 31 cm the hub is under water and this fails
PHONE_CLICK_SD_PX = 4.0                  # finding the wheel's top and hub in a 12-megapixel photo
PHONE_WATERLINE_SD_PX = 8.0              # ripples and reflection at the tyre
DISTANCE_GROUPS = ((3, 6), (6, 10), (10, 15))


def make_phone(rng, number):
    """One photo position: a person standing or on a two-wheeler, some metres from a car."""
    height, distance = rng.uniform(1.0, 1.6), rng.uniform(3.0, 15.0)
    aim = rng.uniform(0.0, 0.9)                              # nobody aims exactly at the wheel
    return {"id": f"sim-phone-{number:03d}", "height_m": height, "distance_m": distance,
            "side_m": rng.uniform(-2.0, 2.0), "tilt": math.atan2(height - aim, distance),
            "roll": math.radians(rng.uniform(-8.0, 8.0)),    # handheld: never level
            "focal_px": PHONE_FOCAL_PX, "distortion": rng.uniform(-0.01, 0.01), "image": PHONE_IMAGE,
            "wheel_cm": rng.uniform(*WHEEL_RANGE_CM)}


def wheel_depth(top, hub, waterline, wheel_cm):
    """Depth from what stays visible: the wheel's top, its hub, and where the water meets the tyre.

    The wheel's base is under water, so it cannot be marked. The hub-to-top distance is half the
    wheel and gives the scale; the depth is the wheel's height less the part still showing.
    """
    cm_per_px = (wheel_cm / 2) / math.dist(hub, top)
    return wheel_cm - math.dist(waterline, top) * cm_per_px


def measure_phone(phone, rng, trials=20):
    """Absolute errors in cm: with the wheel's true size known, and with 62 cm assumed."""
    errors = {"known": [], "assumed": []}
    true = phone["wheel_cm"]
    for _ in range(trials):
        top = clicked(rng, project(phone, true), PHONE_CLICK_SD_PX)
        hub = clicked(rng, project(phone, true / 2), PHONE_CLICK_SD_PX)
        for depth in PHONE_DEPTHS_CM:
            waterline = clicked(rng, project(phone, depth), PHONE_WATERLINE_SD_PX)
            errors["known"].append(abs(wheel_depth(top, hub, waterline, true) - depth))
            errors["assumed"].append(abs(wheel_depth(top, hub, waterline, ASSUMED_WHEEL_CM) - depth))
    return errors


def run_phones(seed=7, count=300):
    rng = random.Random(seed + 1000)                        # its own stream: the camera table is unchanged
    phones = [make_phone(rng, n) for n in range(count)]
    for phone in phones:
        phone["errors"] = measure_phone(phone, rng)
    return phones


def phone_summary(phones):
    rows = []
    for low, high in DISTANCE_GROUPS + ((3, 15),):
        group = [p for p in phones if low <= p["distance_m"] < high or (low, high) == (3, 15)]
        row = {"distance": "**All**" if (low, high) == (3, 15) else f"{low} to {high} m", "photos": len(group),
               "wheel_px": statistics.median(math.dist(project(p, 0.0), project(p, p["wheel_cm"])) for p in group)}
        for kind in ("known", "assumed"):
            errors = [e for p in group for e in p["errors"][kind]]
            row[kind] = (statistics.median(errors), percentile(errors, 0.95))
        rows.append(row)
    return rows


def phone_report(phones):
    cell = lambda pair: f"{pair[0]:.1f} cm, 95% under {pair[1]:.1f} cm"                 # noqa: E731
    lines = [
        "## A handheld phone (an iPhone's main camera)",
        "",
        "A resident's photo has no gauge and no dry view to mark, so the depth is read against a car's",
        "wheel, as METHOD.md C2 estimator 2 intends. The wheel's base is under water, so only its top, its",
        "hub and the waterline can be found.",
        "",
        f"- {len(phones)} photo positions: held 1.0 to 1.6 m above the road, 3 to 15 m from the car, tilted to look",
        "  at it, never level (roll up to 8°).",
        f"- The camera is nominal: {PHONE_IMAGE[0]} x {PHONE_IMAGE[1]} pixels, a lens equal to 26 mm. These are",
        "  the published figures for a recent iPhone's main camera, not measurements of one.",
        f"- The car's wheel is anywhere from {WHEEL_RANGE_CM[0]:.0f} to {WHEEL_RANGE_CM[1]:.0f} cm; the method assumes {ASSUMED_WHEEL_CM:.0f} cm.",
        f"- Depths of {PHONE_DEPTHS_CM[0]} to {PHONE_DEPTHS_CM[-1]} cm. Above about 31 cm the hub is under water and this reading fails.",
        "",
        "| Distance to the car | Photos | Wheel height in the image | If the wheel's size were known | Assuming 62 cm |",
        "|---|---|---|---|---|",
    ]
    for row in phone_summary(phones):
        lines.append(f"| {row['distance']} | {row['photos']} | about {row['wheel_px']:.0f} px | {cell(row['known'])} | {cell(row['assumed'])} |")
    lines += [
        "",
        "- **Distance decides it.** From within 6 m the wheel is about 400 pixels tall and the reading is",
        "  within about 4 cm 95% of the time. From 10 to 15 m it is about 150 pixels and the same slip in",
        "  finding the waterline costs up to 9 cm. Standing closer is worth more than any correction.",
        "- **Not knowing the car matters less than expected.** The wheel sets both the scale and the height",
        "  the depth is taken from, so a wrong wheel size shifts the answer only in proportion to the depth:",
        "  at most about 3 cm at 25 cm deep, and under 1 cm in shallow water.",
        "- **The tilt and roll of a handheld shot cost little**, because the phone is low and looks almost",
        "  level at the wheel.",
        "- This is why a resident's photo gives a range, and why the capture page should ask for a photo from",
        "  a few metres, not from across the road.",
        "",
    ]
    return lines


def percentile(values, share):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def run(seed=7, count=400):
    rng = random.Random(seed)
    cameras = [make_camera(rng, n) for n in range(count)]
    kept = [c for c in cameras if usable(c)]
    for camera in kept:
        camera["errors"] = measure(camera, rng)
    return cameras, kept


def gauge_px(camera):
    return math.dist(project(camera, 0.0), project(camera, GAUGE_CM))


def summary(kept, by="tilt"):
    rows = []
    groups, value, label = ((TILT_GROUPS, lambda c: math.degrees(c["tilt"]), "{}° to {}°") if by == "tilt"
                            else (SIZE_GROUPS, gauge_px, "{} to {} px"))
    for low, high in groups:
        group = [c for c in kept if low <= value(c) < high]
        if not group:
            continue
        row = {"tilt": label.format(low, high) if high < 2000 else f"over {low} px", "cameras": len(group)}
        for method in ("two", "three"):
            errors = [e for c in group for e in c["errors"][method]]
            row[method] = (statistics.median(errors), percentile(errors, 0.95))
        rows.append(row)
    return rows


def report(cameras, kept, seed):
    every = {m: [e for c in kept for e in c["errors"][m]] for m in ("two", "three")}
    lines = [
        "# Camera angles: a simulation",
        "",
        "**SIMULATED. No real camera, photo or flood is behind any number here.** Written by",
        f"`scripts/simulate_cameras.py` (seed {seed}). It tests one narrow thing: whether the geometry of the",
        "reference-object method in METHOD.md still gives the right depth when cameras are mounted at",
        "different heights, distances and angles. It does not test finding the waterline in a real image.",
        "",
        "## What was simulated",
        "",
        f"- {len(cameras)} cameras, each at a random height (2.5 to 7 m), distance (3 to 25 m), sideways offset,",
        "  tilt, roll (up to 4°), focal length and barrel distortion.",
        f"- {len(cameras) - len(kept)} were refused at enrolment because the 150 cm gauge was out of frame or under 60",
        f"  pixels tall. {len(kept)} were kept.",
        f"- The gauge was marked by hand with an error of about {CLICK_SD_PX} px, 40 times per camera, and the",
        f"  waterline found with an error of about {WATERLINE_SD_PX} px, at depths from {DEPTHS_CM[0]} to {DEPTHS_CM[-1]} cm.",
        "",
        "## Result",
        "",
        "Error in centimetres: the middle value, and the value 95% of readings stay under.",
        "",
        "| Camera tilt below horizontal | Cameras | Two marks (as designed) | Three marks |",
        "|---|---|---|---|",
    ]
    cell = lambda pair: f"{pair[0]:.1f} cm, 95% under {pair[1]:.1f} cm"                 # noqa: E731
    for row in summary(kept):
        lines.append(f"| {row['tilt']} | {row['cameras']} | {cell(row['two'])} | {cell(row['three'])} |")
    overall = {m: (statistics.median(every[m]), percentile(every[m], 0.95)) for m in every}
    lines += [
        f"| **All** | {len(kept)} | {cell(overall['two'])} | {cell(overall['three'])} |",
        "",
        "The same readings, grouped by how large the gauge appears (a distant camera sees it small):",
        "",
        "| Gauge height in the image | Cameras | Two marks (as designed) | Three marks |",
        "|---|---|---|---|",
    ]
    for row in summary(kept, by="size"):
        lines.append(f"| {row['tilt']} | {row['cameras']} | {cell(row['two'])} | {cell(row['three'])} |")
    lines += [
        "",
        "## What it means",
        "",
        "- **Distance matters most.** When the 150 cm gauge covers under 120 pixels, one pixel is more than",
        "  1.25 cm, so a two-pixel slip in finding the waterline is already several centimetres. Neither",
        "  method can fix that; only a closer camera, a longer lens or a larger image can.",
        "- **Angle matters for the designed method.** Two marks and one scale need no angle to be calculated,",
        "  but they assume every centimetre of the gauge covers the same number of pixels. A camera looking",
        "  steeply down breaks that, and the error grows at the steepest tilts.",
        "- **A third mark removes the angle error.** Three known points fix the exact mapping from image",
        "  position to height, so steep cameras read as well as level ones. What is left is the marking and",
        "  waterline error and lens distortion.",
        "- The depth bands are 8 to 20 cm wide and a reading is always a range. The 95% figures above say how",
        "  wide that range must be for a camera of each kind to be honest.",
        "",
    ]
    lines += phone_report(run_phones(seed))
    lines += [
        "## What it does not show",
        "",
        "- Whether a model or a segmentation step can find the waterline at night, in rain, with reflections",
        "  or with a vehicle in front of the gauge. That is the dominant error in practice and is untested.",
        "- Any real lens, mounting, or camera that has been knocked out of position since it was enrolled.",
        "- That sites have a gauge. None of the nine sites has a reference object recorded.",
        "",
    ]
    return "\n".join(lines)


def play(kept, seed, server):
    """Pick one camera at random and play a flood, read by that camera, into the local map."""
    import rehearse
    from nirmaldhara.state import Reading, Site, apply_reading
    from nirmaldhara.workflow import confidence

    rng = random.Random()                                   # a different camera each run
    camera = rng.choice(kept)
    spread = max(2.5, percentile(camera["errors"]["three"], 0.95))
    try:
        rehearse.call(server, "/__dev/reset")
    except Exception:
        print("The development server is not running. Start it first: python scripts/serve_web.py")
        return 1
    sample, name = "sample-05", f"SIMULATED camera {camera['id']}"
    rehearse.call(server, "/__dev/set", site=sample, name=name, state="CLEAR", low=0, high=0, trusted=0, confidence=0)
    print(f"Picked {camera['id']} at random: {camera['height_m']:.1f} m up, {camera['distance_m']:.1f} m away, "
          f"tilted {math.degrees(camera['tilt']):.0f}° down. Its readings carry ±{spread:.1f} cm.")
    print(f"Open {server}/ and watch \"{name}\".")
    marks, site, start = enrol(rng, camera), Site("sim"), 1_800_000_000
    truths = [0, 4, 9, 14, 19, 24, 29, 33, 33, 27, 20, 13, 7, 2, 0, 0]
    for step, truth in enumerate(truths):
        seen = three_marks(marks, clicked(rng, project(camera, truth), WATERLINE_SD_PX)) if truth else 0.0
        low, high = max(0.0, seen - spread), (seen + spread if truth else 0.0)
        site = apply_reading(site, Reading(start + step * 120, low, high, 0.85, "cctv", camera["id"]))
        rehearse.call(server, "/__dev/set", site=sample, state=site.state, low=round(site.low), high=round(site.high),
                      trusted=1 if site.trusted else 0, confidence=round(confidence(site), 2))
        print(f"  frame {step + 1:2}: true {truth:2} cm, camera read {seen:5.1f} cm -> {site.state:9} "
              f"{round(site.low)}-{round(site.high)} cm", flush=True)
        time.sleep(3)
    print("Done. This was a simulated camera on the local map only.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--play", action="store_true", help="play one random camera into the local map")
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    cameras, kept = run(args.seed)
    text = report(cameras, kept, args.seed)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(text.split("## Result")[1].split("## What it means")[0].strip())
    print(f"\nWritten to {OUT.relative_to(ROOT)}")
    return play(kept, args.seed, args.server) if args.play else 0


if __name__ == "__main__":
    sys.exit(main())
