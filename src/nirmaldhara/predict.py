"""Rise rate and time to no-go (METHOD.md section 7)."""

from statistics import median

from .bands import NO_GO_CM

MIN_READINGS = 3


def rise_rate(readings):
    """Theil-Sen slope in cm per minute from (minute, depth_cm) pairs, or None."""
    if len(readings) < MIN_READINGS:
        return None
    slopes = [
        (d2 - d1) / (t2 - t1)
        for i, (t1, d1) in enumerate(readings)
        for t2, d2 in readings[i + 1:]
        if t2 != t1
    ]
    return median(slopes) if slopes else None


def rain_factor(next60_mm, last60_mm):
    """How the coming rain compares with the recent rain, clipped to 0.25..3."""
    return max(0.25, min(3.0, next60_mm / max(last60_mm, 1.0)))


def depth_at(depth_now_cm, rate, minutes, max_depth_cm):
    return min(depth_now_cm + rate * minutes, max_depth_cm)


def minutes_to_no_go(depth_now_cm, rate):
    """Minutes until each class loses passage; None if already lost or not rising."""
    out = {}
    for vehicle, limit in NO_GO_CM.items():
        if rate is None or rate <= 0 or depth_now_cm >= limit:
            out[vehicle] = None
        else:
            out[vehicle] = (limit - depth_now_cm) / rate
    return out
