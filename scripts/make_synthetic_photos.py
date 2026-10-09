"""Draw synthetic flood scenes with a known water depth, for exercising the evaluation tools.

    python scripts/make_synthetic_photos.py

These are DRAWINGS, not photographs. A car wheel of a known size (62 cm) stands in water of a
known depth; each scene is labelled from the drawing, not from anyone's judgement. They exist so
the evaluation and photo scripts can be run end to end before real photos and a real model are
available. Results on them say nothing about how a model reads real photographs of real floods.

Writes samples/synthetic/*.png and samples/synthetic/labels.csv.
"""

import csv
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nirmaldhara.bands import band_for  # noqa: E402

OUT = ROOT / "samples" / "synthetic"
W, H = 480, 360
PX_PER_CM = 2.2
WHEEL_CM = 62
GROUND_Y = 300
WHEEL_R = WHEEL_CM * PX_PER_CM / 2
WATER = (60, 110, 150)
TYRE = (28, 28, 30)

# (condition, depths in cm). "normal" is a clear scene; the rest each break one thing.
SCENES = [
    ("normal", [0, 4, 8, 12, 16, 20, 25, 30, 38, 46]),
    ("waves", [10, 22, 34]),         # a rippled surface
    ("glare", [18, 24, 36]),         # a bright reflection over most of the water line
    ("occluded", [14, 26]),          # something hides the top of the wheel
    ("no_wheel", [20, 40]),          # water, but nothing of known size
    ("dark", [22]),                  # taken in near darkness
    ("blurred", [28]),               # out of focus
]


def draw_scene(depth_cm, condition, seed):
    rng = random.Random(seed)
    img = Image.new("RGB", (W, H), (205, 215, 225))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 150, W, 250], fill=(120, 120, 125))                     # buildings
    for x in range(10, W, 46):
        d.rectangle([x, 165 + rng.randint(0, 20), x + 24, 235], fill=(98, 98, 104))
    d.rectangle([0, 250, W, H], fill=(92, 92, 96))                           # road
    if condition != "no_wheel":
        cx, cy = 240, GROUND_Y - WHEEL_R
        d.rounded_rectangle([cx - 150, cy - 70, cx + 150, cy - 18], 12, fill=(150, 40, 40))   # body
        d.ellipse([cx - WHEEL_R, cy - WHEEL_R, cx + WHEEL_R, cy + WHEEL_R], fill=TYRE)
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(150, 150, 155))              # hub
    if condition == "occluded":
        d.rectangle([205, int(GROUND_Y - 2 * WHEEL_R) - 6, 275, int(GROUND_Y - 2 * WHEEL_R) + 40], fill=(210, 190, 90))
    if depth_cm > 0:
        top = GROUND_Y - depth_cm * PX_PER_CM
        water = Image.new("RGB", (W, H), (0, 0, 0))
        wd = ImageDraw.Draw(water)
        for x in range(40, 441):
            wobble = 4 * math.sin(x / 11.0) if condition == "waves" else 0
            wd.line([(x, top + wobble), (x, GROUND_Y)], fill=WATER)
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        for x in range(40, 441):
            wobble = 4 * math.sin(x / 11.0) if condition == "waves" else 0
            md.line([(x, top + wobble), (x, GROUND_Y)], fill=235)
        img = Image.composite(water, img, mask)
        d = ImageDraw.Draw(img)
        if condition == "glare":
            for x0 in (60, 150, 250, 330):
                d.rectangle([x0, top - 6, x0 + 60, top + 26], fill=(250, 250, 245))
    if condition == "dark":
        img = Image.eval(img, lambda v: int(v * 0.12))
    if condition == "blurred":
        img = img.filter(ImageFilter.GaussianBlur(9))
    # a little sensor noise, fixed by the seed
    px = img.load()
    for _ in range(2500):
        x, y = rng.randrange(W), rng.randrange(H)
        r, g, b = px[x, y]
        n = rng.randint(-6, 6)
        px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    return img


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for condition, depths in SCENES:
        for depth in depths:
            name = f"{condition}-{depth:02d}cm.png"
            draw_scene(depth, condition, seed=depth * 31 + len(condition)).save(OUT / name)
            band = band_for(depth)
            unreadable = condition in ("no_wheel", "dark", "blurred")
            rows.append({
                "file": name, "band_low": band, "band_high": band, "true_depth_cm": depth,
                "object_used": "none" if condition == "no_wheel" else "car wheel",
                "readable": "no" if unreadable else "yes", "moving": "no",
                "source": "drawn by scripts/make_synthetic_photos.py", "licence": "not a photograph",
                "condition": condition})
    with open(OUT / "labels.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    print(f"wrote {len(build())} drawings to {OUT}")
