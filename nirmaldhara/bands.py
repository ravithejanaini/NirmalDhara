"""Depth bands and per-vehicle passability (METHOD.md section 6, C3 and C4)."""

# Upper edge of each band in cm. B0 is dry road; B5 has no upper edge.
BAND_EDGES_CM = [("B1", 12), ("B2", 20), ("B3", 30), ("B4", 50)]

# Depth at which each class must not enter still water, in cm.
NO_GO_CM = {
    "two_wheeler": 15,
    "auto": 15,
    "car": 20,
    "pedestrian": 30,
    "suv": 30,
}
# Above this depth nobody is told "passable". Buses and trucks get no answer below it.
EVERYONE_NO_GO_CM = 50
NO_ANSWER_CLASSES = ("bus", "truck")

MIN_CONFIDENCE = 0.6
# Moving water: every class is not safe from the bottom of band B2.
MOVING_NO_GO_CM = 12

PASSABLE = "passable"
NOT_SAFE = "not safe"
UNKNOWN = "unknown: treat as not safe"
NO_ANSWER = "no answer: depth reported only"


def band_for(depth_cm):
    """Band that a single depth falls in."""
    if depth_cm <= 0:
        return "B0"
    for name, upper in BAND_EDGES_CM:
        if depth_cm < upper:
            return name
    return "B5"


def answer_for(vehicle, low_cm, high_cm, confidence, moving=False):
    """Passability for one class from a depth range.

    "Passable" needs the upper end of the range below the no-go depth and enough
    confidence. A range that straddles the limit is "not safe".
    """
    if high_cm >= EVERYONE_NO_GO_CM:
        return NOT_SAFE
    if vehicle in NO_ANSWER_CLASSES:
        return NO_ANSWER
    limit = NO_GO_CM[vehicle]
    if moving:
        limit = min(limit, MOVING_NO_GO_CM)
    if high_cm >= limit:
        return NOT_SAFE
    if confidence < MIN_CONFIDENCE:
        return UNKNOWN
    return PASSABLE


def passability(low_cm, high_cm, confidence, moving=False):
    """Answers for every class."""
    classes = list(NO_GO_CM) + list(NO_ANSWER_CLASSES)
    return {v: answer_for(v, low_cm, high_cm, confidence, moving) for v in classes}
