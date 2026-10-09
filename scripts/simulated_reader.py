"""A stand-in for the photo reader that works ONLY on the drawn scenes in samples/synthetic/.

It measures what a person would: the height of the water line against the height of a wheel of
known size (62 cm), then scales. That is the method the real reader is asked to follow, done in a
few lines of pixel arithmetic on drawings where the wheel is dark and the water is blue. It
returns the same dictionary as `nirmaldhara.reader.read_depth`.

It is not a model, it cannot read a photograph, and its results are not evidence of how well any
model reads real floods. Every answer says SIMULATED in its reason.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nirmaldhara import intake  # noqa: E402

WHEEL_CM = 62
TAG = "SIMULATED reader on a drawn scene: "


def _answer(**fields):
    base = {"flood_present": False, "cannot_tell": True, "objects": [], "depth_cm_low": 0,
            "depth_cm_high": 0, "confidence": 0, "reason": ""}
    base.update(fields)
    base["reason"] = TAG + base["reason"]
    return base


def read_depth(image_path, region=None):
    image = Image.open(image_path).convert("RGB")
    # The same gates a real photo meets before anything reads it.
    gray = np.asarray(image.convert("L"))
    if gray.mean() < intake.MIN_BRIGHTNESS:
        return _answer(reason="the picture is too dark to read.")
    if intake.sharpness(image) < intake.MIN_SHARPNESS:
        return _answer(reason="the picture is too blurred to read.")

    a = np.asarray(image, dtype=np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    tyre = (r < 60) & (g < 60) & (b < 60) & (b - r < 30)
    water = (b - r > 35) & (b - g > 10)

    rows_with_tyre = np.where(tyre.sum(axis=1) >= 8)[0]
    if rows_with_tyre.size == 0:
        return _answer(reason="nothing of known size is visible, so there is nothing to measure against.")
    tyre_top = int(rows_with_tyre.min())

    columns = np.where(water.sum(axis=0) >= 6)[0]
    if columns.size < 40:                                        # no water: a dry road
        return _answer(flood_present=False, cannot_tell=False,
                       objects=[{"type": "car wheel", "level": "dry", "confidence": 0.8}],
                       depth_cm_low=0, depth_cm_high=0, confidence=0.8, reason="no water is visible.")
    tops = np.array([int(np.argmax(water[:, c])) for c in columns])
    bottoms = np.array([int(len(water) - 1 - np.argmax(water[::-1, c])) for c in columns])
    ground = float(np.median(bottoms))
    surface = float(np.median(tops))
    q1, q3 = np.percentile(tops, [25, 75])
    wheel_px = ground - tyre_top
    if wheel_px < 40:
        return _answer(reason="the wheel is too small in the picture to measure.")

    depth = max(0.0, (ground - surface) / wheel_px * WHEEL_CM)
    spread_cm = (q3 - q1) / wheel_px * WHEEL_CM                    # how ragged the water line looks
    half = 2.5 + 0.06 * depth + 1.5 * spread_cm
    confidence = 0.85 if spread_cm < 2.0 else 0.55                 # a ragged line is a doubtful one
    return _answer(
        flood_present=True, cannot_tell=False,
        objects=[{"type": "car wheel", "level": f"{depth:.0f} cm", "confidence": confidence}],
        depth_cm_low=max(0.0, round(depth - half, 1)), depth_cm_high=round(depth + half, 1),
        confidence=confidence,
        reason=f"water line {depth:.0f} cm up a {WHEEL_CM} cm wheel; the line's raggedness is {spread_cm:.1f} cm.")
