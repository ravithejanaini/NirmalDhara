"""Depth from where the water's edge sits on the ramp (METHOD.md section 6, C10).

Still water is level. Where its edge crosses a ramp, the road at that spot is as high as the water
is, and the road's height along the ramp is known from its profile (METHOD 15.1, the same profile
volume.py takes). So one spot on the ground gives the level, and the level less the height of the
lowest point is the depth there. On a ramp of 4%, each metre of ramp under water is 4 cm of depth.

Three things are different from reading a line on something upright:

    it does not end     A curve learnt from measured levels cannot read past them: on a real river
                        the model was 42 to 82 cm out on water higher than any it had learnt from
                        (docs/depth-model-river.md). A profile runs to the top of the ramp.
    it needs no levels  The profile is measured once, dry. No flood has to be watched first.
    it checks itself    A dip has two ramps. The edges on both must give the same level. Where they
                        do not, the profile is wrong or an edge was misread, and that is said.

What it costs is that everything rests on the profile. A profile guessed from a map, with slopes
taken as somewhere between 2% and 6%, turns the same edge into depths three times apart; `doubt`
says so in centimetres.

`depth_from_edge` is plain arithmetic and takes an edge placed by anyone: a camera, or a person who
says which lamp post the water has reached. `distance_map` and `depth_from_rows` take the edge from
a strip of a fixed camera laid along the ramp, by marks at known distances. `witness` makes that
strip a witness for depthmodel.py whose curve comes from the road and not from levels seen, and
`site_model` makes a model of such witnesses alone, which needs no measured level at all.
`at_lowest` turns a depth read at a known spot on the ramp, a wheel's for one, into the depth at
the lowest point.

Tested on made roads only. No place in the registry has a profile, and no edge on a real road has
been read. Nothing calls it.
"""

from bisect import bisect_right

GUESSED_SLOPES = (0.02, 0.06)     # a profile taken from a map: ramps assumed between 2% and 6% (METHOD 15.1)


def _points(profile):
    points = sorted((float(x), float(h)) for x, h in profile)
    if len(points) < 2:
        raise ValueError("a profile needs at least two points")
    return points


def lowest(profile):
    """(distance, height) of the lowest point of the road."""
    return min(_points(profile), key=lambda point: point[1])


def height_at(profile, distance):
    """The road's height at a distance along it, read between the profile's points. Beyond its ends the
    last stretch is carried on."""
    points = _points(profile)
    i = min(max(bisect_right([x for x, _ in points], distance) - 1, 0), len(points) - 2)
    (x1, h1), (x2, h2) = points[i], points[i + 1]
    return h1 + (h2 - h1) * (distance - x1) / (x2 - x1)


def slope_at(profile, distance):
    """How steeply the road rises at a distance along it: metres up for each metre along, as a size."""
    points = _points(profile)
    i = min(max(bisect_right([x for x, _ in points], distance) - 1, 0), len(points) - 2)
    (x1, h1), (x2, h2) = points[i], points[i + 1]
    return abs(h2 - h1) / (x2 - x1)


def depth_from_edge(profile, near, far):
    """The depth at the lowest point, in centimetres, when the water's edge lies between two distances
    along the road: (low, high). An edge that may lie either side of the lowest point may be no water."""
    base_x, base = lowest(profile)
    start, end = sorted((near, far))
    heights = [height_at(profile, start), height_at(profile, end)]
    heights += [h for x, h in _points(profile) if start < x < end]
    low = 0.0 if start <= base_x <= end else min(heights) - base
    return 100.0 * max(low, 0.0), 100.0 * max(max(heights) - base, 0.0)


def together(ranges):
    """One depth from the edges on several ramps: (low, high, agreed).

    The water is level, so every edge must give the same depth. Where the ranges share some depths, those
    are the answer. Where they do not, the answer runs from the lowest to the highest of them and
    `agreed` is False: the profile is wrong or an edge was misread.
    """
    low, high = max(r[0] for r in ranges), min(r[1] for r in ranges)
    if low <= high:
        return low, high, True
    return min(r[0] for r in ranges), max(r[1] for r in ranges), False


def at_lowest(profile, near, far, low_cm, high_cm):
    """The depth at the lowest point from a depth read somewhere else on the road: (low, high) in
    centimetres. near, far: between which distances the thing stands whose depth was read, a parked car
    for one. The water there is shallower by as much as the road is higher."""
    base = lowest(profile)[1]
    start, end = sorted((near, far))
    heights = [height_at(profile, start), height_at(profile, end)] + [h for x, h in _points(profile) if start < x < end]
    return low_cm + 100.0 * (min(heights) - base), high_cm + 100.0 * (max(heights) - base)


def doubt(profile, distance, edge_m, heights_cm=0.0):
    """How far out the depth may be, in centimetres either way, for an edge placed to within `edge_m`
    metres at `distance`, on a profile whose heights are known to within `heights_cm`."""
    return 100.0 * slope_at(profile, distance) * edge_m + heights_cm


def guessed(distance_from_lowest):
    """The depth an edge would mean on a profile taken from a map, with nothing known of the ramp but
    that it rises between 2% and 6%: (low, high) in centimetres."""
    return tuple(100.0 * slope * abs(distance_from_lowest) for slope in GUESSED_SLOPES)


def distance_map(marks):
    """Distance along the road from a place in the picture, from marks at known distances.

    marks: [(row or pixel along the strip, distance along the road in metres)], two or more: lane dashes,
    pillars, lamp posts. Two give one scale. Three or more give the map that perspective obeys, fitted to
    all of them. A strip along a road runs towards the horizon, where a row is any distance at all, so
    the map is fitted in the form that allows that anywhere in the picture.
    """
    import numpy as np
    marks = np.asarray(sorted(marks), dtype=float)
    if len(marks) < 2:
        raise ValueError("two marks are the least that give a scale")
    rows, distances = marks[:, 0], marks[:, 1]
    if len(marks) == 2:
        slope = (distances[1] - distances[0]) / (rows[1] - rows[0])
        return lambda row: float(distances[0] + slope * (row - rows[0]))
    # distance = (a r + c) / (b r + d) with r and distance first brought to a like size: the four numbers
    # are found up to their scale, as the direction in which every mark's equation is nearest to nothing.
    mid_r, size_r = rows.mean(), max(np.ptp(rows) / 2.0, 1e-9)
    mid_d, size_d = distances.mean(), max(np.ptp(distances) / 2.0, 1e-9)
    r, x = (rows - mid_r) / size_r, (distances - mid_d) / size_d
    a, c, b, d = (float(v) for v in np.linalg.svd(np.column_stack([r, np.ones(len(r)), -x * r, -x]))[2][-1])

    def along(row):
        at = (row - mid_r) / size_r
        below = b * at + d
        return float("inf") if below == 0 else mid_d + size_d * (a * at + c) / below      # at the horizon a row is no distance
    return along


def depth_from_rows(profile, marks, row_low, row_high):
    """The depth at the lowest point when a strip laid along the ramp shows the water's edge between two
    rows: (low, high) in centimetres."""
    along = distance_map(marks)
    return depth_from_edge(profile, along(row_low), along(row_high))


def witness(name, grid, profile, marks, rows, spread, camera="", wild=0.05, seen=0.9):
    """A strip laid along a ramp as a witness for depthmodel.py, its curve taken from the road.

    grid: the depths tried, in metres above the lowest point. marks: [(row, distance along the road)] on
    the strip's side of the lowest point. rows: how many rows the strip has. spread: how far the detector's
    row usually lies from the true edge, in rows. Where the edge would fall between the first mark and the
    last the witness is taken to report a line `seen` of the time; where the water would lie past them it
    is taken to report nothing that tells depths apart. wild: the share of its lines taken to be nowhere
    near the edge. With one witness alone that share shows as a long upper end to the range in shallow
    water, where the strip's rows are few to the centimetre; a second ramp removes it.
    """
    import numpy as np

    from .depthmodel import Witness
    base_x, base = lowest(profile)
    along = distance_map(marks)
    side = 1.0 if sum(distance for _, distance in marks) / len(marks) >= base_x else -1.0
    points = _points(profile)
    first, last = min(row for row, _ in marks), max(row for row, _ in marks)
    places = [(along(row), float(row)) for row in range(int(rows)) if first - 1 <= row <= last + 1]      # only between the marks: beyond
    places = [(d, row) for d, row in places if points[0][0] <= d <= points[-1][0]]                         # them the map is a guess
    ordered = sorted((height_at(profile, d) - base, row) for d, row in places if (d - base_x) * side >= 0)
    heights, at_rows = [h for h, _ in ordered], [r for _, r in ordered]
    curve = np.interp(grid, heights, at_rows)
    inside = (grid >= heights[0]) & (grid <= heights[-1])
    says = np.where(inside[:, None], [seen, (1 - seen) / 2, (1 - seen) / 2], [1 / 3, 1 / 3, 1 / 3])
    return Witness(name, camera, curve, max(float(spread), 1.0), float(wild), int(rows), says, 0)


def site_model(profile, witnesses, rate_per_hour=0.5, step=0.01):
    """A depthmodel.SiteModel made of witnesses whose curves come from the road, so that it needs no
    measured level. witnesses: {name: a function from the grid to a Witness}, as `witness` with every
    argument but the grid filled in. The depths tried run from none to the top of the lower ramp.
    rate_per_hour: how far the water is taken to move in an hour, in metres. It is a guess, half a metre,
    until a place has floods on record to learn it from."""
    import numpy as np

    from .depthmodel import SiteModel
    points, base = _points(profile), lowest(profile)[1]
    top = min(points[0][1], points[-1][1]) - base
    grid = np.arange(0.0, top + step / 2, step)
    made = {name: make(grid) for name, make in witnesses.items()}
    cameras = {w.camera for w in made.values()}
    return SiteModel(grid, made, {c: 1.0 for c in cameras}, {c: 1.0 for c in cameras}, rate_per_hour)
