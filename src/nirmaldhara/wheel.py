"""A wheel read by a person: where the water stands on a wheel, as a depth (METHOD.md section 6, C11).

METHOD C2 turns the water's place on a wheel into a depth by the size of wheels, which are much the
same from one car to the next (section 17). There a model is to look at a photo and has never done
so. Here a person looks at the wheel. Someone already standing at the place is asked one thing:
where the water has come to on the wheel of a vehicle standing in it. Five answers, no typing.

Why it is worth having
    Every way this project has of reading a fixed camera needs depths measured at the place, and no
    place has any (docs/gauge-river.md, docs/depth-model-river.md). An answer here is a depth with
    the photo it came with, from the one person who can see the wheel. Nobody is sent anywhere.

What an answer is
    A range, from the table below, which is METHOD C2's. It is the depth where the vehicle stands,
    and a road is usually deeper further in. So by itself an answer can say a class of road user
    must not enter and can never say that one may: its confidence is set under the mark at which
    the engine will call a road passable (bands.MIN_CONFIDENCE). Where the vehicle's place on the
    ramp is known, ramp.at_lowest carries the depth to the lowest point and the answer counts in
    full.

How well people read a wheel is not known. Volunteers reading a water level against a picture of a
gauge did it better than they estimated flow (Strobl and others 2020). That is a river bank and not
a wheel. The confidences below are design choices, and nothing here has been tried on a person.
Nothing calls this module: there is no page yet that sends an answer anywhere.
"""

from . import bands, ramp, state

# What the person is shown, in order from shallow to deep, and what is asked.
ASK = "Find a parked car, auto or bike standing in the water. Where has the water come to on its wheel?"
MARKS = {
    "tyre": "Only the tyre is wet. The rim is dry.",
    "rim": "The rim is wet, less than halfway from its edge to the hub.",
    "third": "More than halfway to the hub. The hub is still dry.",
    "axle": "The hub is under water. The top of the tyre still shows.",
    "over": "The tyre is covered.",
}
# Depth in centimetres for each answer, from standard tyre sizes (METHOD C2 and section 17).
TABLE = {
    "car": {"tyre": (0, 12), "rim": (12, 20), "third": (20, 31), "axle": (31, 62), "over": (62, 62)},
    "motorcycle": {"tyre": (0, 9), "rim": (9, 20), "third": (20, 31), "axle": (31, 61), "over": (61, 61)},
    "scooter": {"tyre": (0, 9), "rim": (9, 14), "third": (14, 22), "axle": (22, 43), "over": (43, 43)},
}
SAME_AS = {"auto": "scooter"}      # an auto-rickshaw's wheel is about a scooter's (METHOD C2)
WHEELS = {"car": "Car", "auto": "Auto", "motorcycle": "Motorcycle", "scooter": "Scooter"}
SOMEWHERE = 0.5                    # the vehicle's place on the road is not known: under bands.MIN_CONFIDENCE, so never "passable"
PLACED = 0.7                       # its place is known and the depth has been carried to the lowest point. A design choice


def depth(wheel, mark):
    """(low, high) in centimetres where the vehicle stands. "over" is a floor: the tyre's height and no
    more is claimed."""
    try:
        return TABLE[SAME_AS.get(wheel, wheel)][mark]
    except KeyError:
        raise ValueError(f"no such wheel or mark: {wheel!r}, {mark!r}") from None


def estimate(wheel, mark, profile=None, near=None, far=None):
    """One answer as the engine takes an estimate: (low cm, high cm, confidence).

    With a road profile and the stretch of ramp the vehicle stands on, between `near` and `far` metres
    along it, the depth is carried to the lowest point (ramp.at_lowest) and counts in full. Without, it
    is the depth where the vehicle stands, at a confidence that can never make a road passable.
    """
    low, high = depth(wheel, mark)
    if profile is None:
        return float(low), float(high), SOMEWHERE
    low, high = ramp.at_lowest(profile, near, far, low, high)
    return low, high, PLACED


def together(estimates):
    """Several answers at one place and time as one: (low, high, confidence), by the engine's own rule for
    several estimates from one picture (state.fuse). None for no answers."""
    return state.fuse(list(estimates))


def to_reading(found, ts, source, device):
    """An estimate, or several together, as the reading the engine takes. source: "resident" or "guardian"."""
    low, high, confidence = found
    return state.Reading(float(ts), float(low), float(high), float(confidence), source, device)


def answers(wheel, mark):
    """What one answer by itself says of each class of road user: the engine's own words. It is "not safe"
    or "unknown: treat as not safe" and never "passable", because the road may be deeper further in."""
    low, high, confidence = estimate(wheel, mark)
    return bands.passability(low, high, confidence)


def label(wheel, mark):
    """An answer as a measured depth to teach a camera with: (middle, how far either way), in centimetres,
    at the spot where the vehicle stands. gauge.learn and depthmodel.learn take the second as the doubt."""
    low, high = depth(wheel, mark)
    return (low + high) / 2.0, (high - low) / 2.0
