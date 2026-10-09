"""Checks and clean-up applied to a photo before anything reads it.

METHOD.md section 5 (acceptance checks) and section 6 C1 (pre-checks);
ARCHITECTURE.md section 6.2 step 4.
"""

import hashlib
from math import asin, cos, radians, sin, sqrt

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MAX_DISTANCE_M = 150
MAX_AGE_S = 300
MIN_BRIGHTNESS = 25      # mean grey level, 0-255
MIN_SHARPNESS = 20.0     # variance of the Laplacian on a 320-pixel-wide copy
BLUR_RADIUS_SHARE = 0.5  # blur radius as a share of the box's shorter side

OK = "ok"
TOO_FAR = "too far from the site"
TOO_OLD = "taken too long ago"
DUPLICATE = "already received"
TOO_DARK = "too dark"
TOO_BLURRED = "too blurred"


def distance_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def content_hash(data):
    return hashlib.sha256(data).hexdigest()


def sharpness(image):
    """Variance of the Laplacian: low for a blurred or featureless picture."""
    width = 320
    small = image.convert("L").resize((width, max(1, image.height * width // image.width)))
    g = np.asarray(small, dtype=np.float32)
    laplacian = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
                 - 4 * g[1:-1, 1:-1])
    return float(laplacian.var())


def check(image, data_hash, photo_lat, photo_lon, site_lat, site_lon,
          requested_at, received_at, seen_hashes):
    """Return OK or the reason the photo is refused.

    Age is judged from when the upload link was issued to when the photo arrived,
    both on the server's clock. The phone's own clock is not trusted.
    """
    if distance_m(photo_lat, photo_lon, site_lat, site_lon) > MAX_DISTANCE_M:
        return TOO_FAR
    if received_at - requested_at > MAX_AGE_S:
        return TOO_OLD
    if data_hash in seen_hashes:
        return DUPLICATE
    if np.asarray(image.convert("L")).mean() < MIN_BRIGHTNESS:
        return TOO_DARK
    if sharpness(image) < MIN_SHARPNESS:
        return TOO_BLURRED
    return OK


def crop_to_region(image, polygon):
    """Keep only the owner's shared region: black outside it, cropped to its bounds.

    `polygon` is a list of (x, y) pixel points.
    """
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon], fill=255)
    kept = Image.composite(image, Image.new(image.mode, image.size, 0), mask)
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    return kept.crop((min(xs), min(ys), max(xs), max(ys)))


def blur_boxes(image, boxes):
    """Blur each box. Boxes are (left, top, width, height) as shares of the image,
    the form face and text detection return them in.
    """
    out = image.copy()
    for left, top, width, height in boxes:
        box = (int(left * image.width), int(top * image.height),
               int((left + width) * image.width) + 1, int((top + height) * image.height) + 1)
        box = (max(0, box[0]), max(0, box[1]),
               min(image.width, box[2]), min(image.height, box[3]))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        radius = max(2, int(min(box[2] - box[0], box[3] - box[1]) * BLUR_RADIUS_SHARE))
        out.paste(out.crop(box).filter(ImageFilter.GaussianBlur(radius)), box)
    return out
