"""Decide whether a camera frame is worth sending (ARCHITECTURE.md section 6.6).

The threshold is not fixed. Each camera learns its own noise level from the
differences between consecutive frames, so a noisy camera and a clean one are
both handled without tuning.

A change is sent only once it persists: the scene must match the previous frame
and differ from the last frame sent. A passing vehicle differs from the frame
before it and is ignored; waste that has settled does not, and is sent.
"""

from collections import deque

import numpy as np
from PIL import Image

SIGNATURE_SIZE = (32, 32)
KEEPALIVE_SECONDS = 300
NOISE_WINDOW = 60       # consecutive-frame differences remembered
NOISE_MULTIPLIER = 3.0  # how far above the quiet-frame noise counts as change
MIN_THRESHOLD = 1.0     # grey levels; floor, above 8-bit rounding effects
WARM_UP = 5             # noise samples needed before differences are trusted


def signature(image):
    """Small greyscale summary of a frame with overall brightness removed."""
    small = image.convert("L").resize(SIGNATURE_SIZE, Image.BILINEAR)
    values = np.asarray(small, dtype=np.float32)
    return values - values.mean()


def difference(a, b):
    """Mean absolute difference between two signatures, in grey levels."""
    return float(np.abs(a - b).mean())


class ChangeGate:
    """Send a frame when it differs from the last frame sent by more than the noise."""

    def __init__(self):
        self.last_sent = None
        self.last_sent_at = None
        self.previous = None
        self.noise = deque(maxlen=NOISE_WINDOW)

    def threshold(self):
        if len(self.noise) < WARM_UP:
            return float("inf")  # still learning this camera's noise
        # Lower quartile: frames with traffic in them must not raise the noise level.
        quiet = float(np.percentile(list(self.noise), 25))
        return max(MIN_THRESHOLD, NOISE_MULTIPLIER * quiet)

    def should_send(self, image, now):
        """True if this frame should be uploaded. `now` is seconds on any clock."""
        current = signature(image)
        step = None
        if self.previous is not None:
            step = difference(current, self.previous)
            self.noise.append(step)
        self.previous = current

        limit = self.threshold()
        settled = step is not None and step <= limit
        send = (
            self.last_sent is None
            or now - self.last_sent_at >= KEEPALIVE_SECONDS
            # Compared with the last frame sent, so slow build-up adds up.
            or (settled and difference(current, self.last_sent) > limit)
        )
        if send:
            self.last_sent = current
            self.last_sent_at = now
        return send
