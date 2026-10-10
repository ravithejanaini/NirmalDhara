"""SIMULATED: what several known dimensions, several reference objects and several cameras are worth.

    python scripts/simulate_multiview.py            # prints the results and writes docs/multiview-simulation.md

No real camera, photo or flood is behind any number this prints. It tries the geometry in
nirmaldhara/multiview.py with the errors a real camera would add: marks placed a pixel or two off,
a lens that bends straight lines, a waterline found a couple of pixels out. Four questions:

    1  One camera, one post. Is a depth closer when the camera is fixed from every known height,
       length and width in view than when the scale is taken from one height, as METHOD C2 does?
    2  One camera, three posts. Is the depth closer when three are read and joined?
    3  One post, up to three cameras at different angles. The same question.
    4  Something floating. How well do two cameras give the water's speed, against one camera that
       has to be told the level?

Questions 2 and 3 are asked twice: with every reading a couple of pixels out, and with one reading
in ten far out, because that is what the detector did on a real flood (docs/waterline-river.md).
It does not test finding a waterline or a floating thing in a real picture.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara import multiview  # noqa: E402

OUT = ROOT / "docs" / "multiview-simulation.md"
SEED, CAMERAS, IMAGE = 7, 300, (1920, 1080)
CLICK_PX = 1.5                     # error in placing a mark on the dry view, as in scripts/simulate_cameras.py
WATERLINE_PX = 2.0                 # error in finding where the water meets a post
TRACK_PX = 2.0                     # error in finding a floating thing in one picture
FAR_OUT = (0.15, 0.60)             # metres: how far out a wild reading is, in the second run of questions 2 and 3
FAR_OUT_SHARE = 0.1                # one reading in ten, as on the real flood
DEPTHS = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60)
POSTS = ((0.0, 4.0), (6.0, -4.0), (-5.0, 4.2))             # where three posts stand, metres
POST_MARKS = (0.0, 0.5, 1.0, 1.5)                          # heights marked on each post
GROUND = [(x, y, 0.0) for x in (-6.0, 0.0, 6.0) for y in (-3.5, 3.5)]      # lane edges: lengths and widths
MARKS = np.array(GROUND + [(x, y, z) for x, y in POSTS for z in POST_MARKS if z > 0] + [(x, y, 0.0) for x, y in POSTS])
TILTS = ((0, 15), (15, 30), (30, 60))


def make_camera(rng):
    """One camera on a pole or a building somewhere round the site, with a lens that bends a little."""
    for _ in range(200):
        height, distance, bearing = rng.uniform(3.0, 7.0), rng.uniform(8.0, 20.0), rng.uniform(0, 2 * np.pi)
        at = np.array([distance * np.cos(bearing), distance * np.sin(bearing), height])
        look = np.array([rng.uniform(-1.0, 3.0), rng.uniform(-2.0, 2.0), 0.4])
        forward = (look - at) / np.linalg.norm(look - at)
        right = np.cross(forward, [0.0, 0.0, 1.0])
        right /= np.linalg.norm(right)
        camera = {"at": at, "turn": np.array([right, np.cross(forward, right), forward]), "focal": rng.uniform(900, 1700),
                  "bend": rng.uniform(-0.10, 0.0), "tilt": float(np.degrees(np.arctan2(height - 0.4, np.linalg.norm((look - at)[:2]))))}
        seen = picture(camera, MARKS)
        if (seen[:, 0] > 20).all() and (seen[:, 0] < IMAGE[0] - 20).all() and (seen[:, 1] > 20).all() and (seen[:, 1] < IMAGE[1] - 20).all():
            return camera
    raise RuntimeError("no camera found that sees every mark")


def picture(camera, points):
    """Where points appear to a real lens: pinhole, then barrel distortion."""
    local = (np.atleast_2d(points) - camera["at"]) @ camera["turn"].T
    flat = local[:, :2] / local[:, 2:3]
    flat = flat * (1 + camera["bend"] * (flat ** 2).sum(axis=1, keepdims=True))
    return camera["focal"] * flat + np.array(IMAGE) / 2


def enrol(rng, camera):
    """The marks as a person would place them once on the dry view."""
    return picture(camera, MARKS) + rng.normal(0, CLICK_PX, (len(MARKS), 2))


def post_marks(placed, post):
    """The placed pixels of one post's marks, lowest first, with their heights."""
    x, y = POSTS[post]
    rows = [i for i, m in enumerate(MARKS) if m[0] == x and m[1] == y]
    rows.sort(key=lambda i: MARKS[i][2])
    return placed[rows], MARKS[rows, 2]


def read_three_ways(rng, camera, placed, fixed, post, depth):
    """One waterline on one post, turned into a depth three ways: (one scale, the post's four marks, the fixed camera)."""
    x, y = POSTS[post]
    waterline = picture(camera, [x, y, depth])[0] + rng.normal(0, WATERLINE_PX, 2)
    pixels, heights = post_marks(placed, post)
    one_scale = (pixels[0][1] - waterline[1]) * heights[-1] / (pixels[0][1] - pixels[-1][1])       # METHOD C2 as written: rows only
    along = lambda p: float(np.linalg.norm(p - pixels[0]))                                           # noqa: E731
    four_marks = multiview.height_map([(along(p), h) for p, h in zip(pixels, heights)])(along(waterline))
    return one_scale, four_marks, multiview.height_on_post(fixed, waterline, x, y)


def far_out(rng, value, share):
    """A reading that, once in a while, is far from the truth, as the detector's were on the real flood."""
    return value + rng.choice([-1, 1]) * rng.uniform(*FAR_OUT) if rng.random() < share else value


def question_one(rng, cameras):
    out = {tilt: [[], [], []] for tilt in TILTS}
    for camera in cameras:
        group = next((t for t in TILTS if t[0] <= camera["tilt"] < t[1]), None)
        if group is None:
            continue
        for _ in range(3):
            placed = enrol(rng, camera)
            fixed = multiview.camera_from_points(MARKS, placed)
            for depth in DEPTHS:
                for k, value in enumerate(read_three_ways(rng, camera, placed, fixed, 0, depth)):
                    out[group][k].append(abs(value - depth))
    return {tilt: [np.array(v) for v in values] for tilt, values in out.items()}


def question_two_and_three(rng, cameras, wide, share):
    """Errors of: one post; three posts in one camera; one post in two cameras; one post in three cameras."""
    out = {"one": [], "three posts": [], "two cameras": [], "three cameras": []}
    agreed = {"three posts": 0, "three cameras": 0}
    for n, camera in enumerate(cameras):
        others = [cameras[(n + 1) % len(cameras)], cameras[(n + 2) % len(cameras)]]
        fixed = [multiview.camera_from_points(MARKS, enrol(rng, c)) for c in [camera] + others]
        for depth in DEPTHS:
            def read(view, matrix, post):
                x, y = POSTS[post]
                waterline = picture(view, [x, y, depth])[0] + rng.normal(0, WATERLINE_PX, 2)
                return far_out(rng, multiview.height_on_post(matrix, waterline, x, y), share)
            posts = [read(camera, fixed[0], post) for post in range(3)]
            views = [read(view, matrix, 0) for view, matrix in zip([camera] + others, fixed)]
            out["one"].append(abs(posts[0] - depth))
            for name, values in (("three posts", posts), ("two cameras", views[:2]), ("three cameras", views)):
                low, high, agree = multiview.combine([(v - wide, v + wide, 1.0) for v in values])
                out[name].append(abs(multiview.best_guess(values, [1.0] * len(values)) - depth))
                if name in agreed:
                    agreed[name] += agree
    return {name: np.array(v) for name, v in out.items()}, {name: count / len(out["one"]) for name, count in agreed.items()}


def question_four(rng, cameras):
    out = {"two cameras": [], "one camera, told the true level": [], "one camera, level from its own reading": [], "one camera, told the road is dry": []}
    for n, camera in enumerate(cameras):
        other = cameras[(n + 1) % len(cameras)]
        fixed = [multiview.camera_from_points(MARKS, enrol(rng, c)) for c in (camera, other)]
        for _ in range(6):
            depth, speed, heading = rng.uniform(0.05, 0.5), rng.uniform(0.2, 2.0), rng.uniform(0, 2 * np.pi)
            start = np.array([rng.uniform(-3, 3), rng.uniform(-2.5, 2.5), depth])
            end = start + np.array([speed * np.cos(heading), speed * np.sin(heading), 0.0])           # one second later
            seen = [[picture(c, p)[0] + rng.normal(0, TRACK_PX, 2) for c in (camera, other)] for p in (start, end)]
            out["two cameras"].append(abs(multiview.surface_speed(fixed, seen[0], seen[1], 1.0)[0] - speed))
            own = read_three_ways(rng, camera, enrol(rng, camera), fixed[0], 0, depth)[2]
            for name, level in (("one camera, told the true level", depth), ("one camera, level from its own reading", own), ("one camera, told the road is dry", 0.0)):
                out[name].append(abs(multiview.speed_on_plane(fixed[0], seen[0][0], seen[1][0], level, 1.0)[0] - speed))
    return {name: np.array(v) for name, v in out.items()}


def cm(errors):
    return f"{100 * np.median(errors):.1f} cm, 95% under {100 * np.percentile(errors, 95):.1f} cm"


def run(seed=SEED, count=CAMERAS):
    rng = np.random.default_rng(seed)
    cameras = [make_camera(rng) for _ in range(count)]
    one = question_one(rng, cameras)
    every = np.concatenate([values[2] for values in one.values()])
    wide = float(np.percentile(every, 80))
    return {"cameras": cameras, "one": one, "wide": wide,
            "clean": question_two_and_three(rng, cameras, wide, 0.0), "wild": question_two_and_three(rng, cameras, wide, FAR_OUT_SHARE),
            "flow": question_four(rng, cameras)}


def report(r, seed=SEED):
    lines = [
        "# Several dimensions, several objects, several cameras: a simulation",
        "",
        f"**SIMULATED. No real camera, photo or flood is behind any number here.** Written by `scripts/simulate_multiview.py` (seed {seed}).",
        "It tries the geometry in `nirmaldhara/multiview.py` with the errors a real camera would add. It does not test",
        "finding a waterline or a floating thing in a real picture, which is where the real error was (see",
        "[waterline-river.md](waterline-river.md)).",
        "",
        "## What was simulated",
        "",
        f"- {len(r['cameras'])} cameras, each 3 to 7 m up and 8 to 20 m from the site at a random bearing, with its own focal length and a lens",
        "  that bends straight lines by up to 10% at the edge. The calculation assumes a lens that does not bend.",
        "- A site with three posts carrying marks at 50, 100 and 150 cm, and lane edges 7 m apart marked at three",
        f"  places along 12 m of road: {len(MARKS)} marks of known height, length and width in all.",
        f"- Each mark placed on the dry view {CLICK_PX} px out, a waterline found {WATERLINE_PX} px out, a floating thing {TRACK_PX} px out.",
        "- Depths from 5 to 60 cm.",
        "",
        "## 1. One camera, one post: one height against every known dimension",
        "",
        "Error in the depth: the middle value, and the value 95% of readings stay under.",
        "",
        "| Camera tilt below horizontal | Readings | One scale from the post's height (METHOD C2 as written) | The post's four marks | Camera fixed from all the marks |",
        "|---|---|---|---|---|",
    ]
    for tilt, values in r["one"].items():
        lines.append(f"| {tilt[0]}° to {tilt[1]}° | {len(values[0])} | {cm(values[0])} | {cm(values[1])} | {cm(values[2])} |")
    for name, title in (("clean", "## 2 and 3. Joining readings, each a couple of pixels out"),
                        ("wild", f"## 2 and 3 again, with one reading in {round(1 / FAR_OUT_SHARE)} far out")):
        errors, agreed = r[name]
        lines += ["", title, "",
                  ("Each reading here is right to within its pixels." if name == "clean" else
                   f"Each reading is, one time in {round(1 / FAR_OUT_SHARE)}, between {round(100 * FAR_OUT[0])} and {round(100 * FAR_OUT[1])} cm out, high or low, "
                   "which is how the detector's readings were spread on the real flood."),
                  "", "| Read by | Error in the depth | More than 10 cm out |", "|---|---|---|"]
        for label, key in (("One camera, one post", "one"), ("One camera, three posts joined", "three posts"),
                           ("Two cameras, one post, joined", "two cameras"), ("Three cameras, one post, joined", "three cameras")):
            lines.append(f"| {label} | {cm(errors[key])} | {np.mean(errors[key] > 0.10):.1%} |")
        lines += ["", f"Three posts agreed in {agreed['three posts']:.0%} of readings, and three cameras in {agreed['three cameras']:.0%}. "
                  f"A reading's range was taken as ± {100 * r['wide']:.1f} cm, which held 80% of single readings in question 1."]
    lines += ["", "## 4. The speed of the water, from something floating on it", "",
              "A thing moving at 0.2 to 2 m/s on water 5 to 50 cm deep, seen twice one second apart.", "",
              "| Seen by | Error in the speed | More than 0.2 m/s out |", "|---|---|---|"]
    for name, errors in r["flow"].items():
        lines.append(f"| {name.capitalize()} | {np.median(errors):.2f} m/s, 95% under {np.percentile(errors, 95):.2f} m/s | {np.mean(errors > 0.2):.1%} |")
    lines += [
        "",
        "## How to read this",
        "",
        "- **These are the errors of the geometry, not of the method.** Every number assumes the waterline has",
        "  already been found to within two pixels. On a real flood that was the hard part: the detector was 13 cm",
        "  out, typically, and one reading in ten was more than half a metre out. No geometry mends that.",
        "- **Question 1 is about the camera's angle.** One scale from one height is right for a camera that looks",
        "  level and wrong for one that looks down. Fixing the camera from heights, lengths and widths together",
        "  solves the angle and does not have to assume it.",
        "- **The second run of questions 2 and 3 is the one that matters.** When readings are only a pixel or two",
        "  out, joining three gains little. When one in ten is far out, the middle of three throws the wild one away.",
        "  That gain depends on the three being wrong at different times. Three posts in one picture share its",
        "  light, its rain and its lens, so they will be wrong together more often than this assumes. Cameras at",
        "  different angles share less.",
        "- **Two readings are not enough.** Two cannot outvote a wild one: the answer is pulled halfway towards it,",
        "  and with two readings a wild one turns up twice as often. Three is the least that can throw one away.",
        "- **Two cameras need no level to give a speed; one camera does.** Told the road is dry when it is not,",
        "  one camera puts the floating thing in the wrong place and gets the speed wrong by that much.",
        "- **Nothing here is a camera at a site.** No site has two cameras on one water, and none has its marks",
        "  surveyed. This shows what would be gained if they had, and nothing more.",
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
