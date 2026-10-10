"""Several reference objects in one view, and several cameras at one place.

waterline.py and gauge.py read one camera through one surface. METHOD.md C2 takes the scale from
one object's height. This module is the arithmetic for using more than that, in three steps.

    1  Everything known about the scene fixes the camera. Heights alone cannot (they say nothing
       of how far away a thing is), and lengths and widths on the ground alone cannot (they say
       nothing of height). Marks whose height, length and width are all known, six or more and
       not all in one plane, fix where the camera is, which way it points and how it magnifies:
       `camera_from_points`. From then on any pixel on a known post is a height (`height_on_post`)
       and any pixel on the water is a place (`meet_plane`). No angle is assumed. It is solved.
    2  Several readings of the same water are one reading: `combine`. Each reference object, and
       each camera, gives its own range. With three or more that agree, the middle one stands,
       so a single reading that is far out, high or low, cannot move the answer. With fewer, or
       when they disagree, the cautious rule of METHOD C5 stands: the highest high end.
    3  Two cameras that see the same thing place it in space: `locate`. A thing floating on the
       water, placed twice a known time apart, gives the water's speed and direction in metres a
       second (`surface_speed`), where METHOD C6 has only yes or no. One camera can do the same
       if the water level is already known (`speed_on_plane`), and is wrong by as much as that
       level is.

Step 2 was measured on a real flood by scripts/river_multi_reference.py. Steps 1 and 3 have only
been checked on made scenes (scripts/simulate_multiview.py): no site has two cameras on one
water, and none has its marks surveyed. Nothing here installs a camera. It applies where cameras
that already exist happen to see the same water.
"""

import numpy as np

MAJORITY = 0.5             # more than this share of the weight must overlap the middle range for it to stand


def _normalised(points):
    """Points moved and scaled to sit around the origin, with the matrix that did it. This keeps the
    sums below from being swamped by the size of the numbers."""
    points = np.asarray(points, dtype=float)
    centre = points.mean(axis=0)
    spread = np.mean(np.linalg.norm(points - centre, axis=1))
    scale = np.sqrt(points.shape[1]) / max(spread, 1e-12)
    matrix = np.eye(points.shape[1] + 1)
    matrix[:-1, :-1] *= scale
    matrix[:-1, -1] = -scale * centre
    return (points - centre) * scale, matrix


def camera_from_points(world, image):
    """The camera, as a 3 by 4 matrix, from marks of known position and where each appears.

    world: (count, 3) positions in any one unit (x and y on the ground, z up). image: (count, 2) pixels.
    Six marks are the least, and they must not all lie in one plane: that is why height, length and
    width are all needed. Raises ValueError when the marks cannot fix a camera.
    """
    world, image = np.asarray(world, dtype=float), np.asarray(image, dtype=float)
    if len(world) < 6 or len(world) != len(image):
        raise ValueError("six marks of known position are the least that fix a camera")
    flat = np.linalg.svd(world - world.mean(axis=0), compute_uv=False)
    if flat[-1] < 1e-6 * flat[0]:
        raise ValueError("the marks all lie in one plane: heights and ground distances are both needed")
    w, to_w = _normalised(world)
    i, to_i = _normalised(image)
    rows = []
    for (x, y, z), (u, v) in zip(w, i):
        point = np.array([x, y, z, 1.0])
        rows.append(np.concatenate([point, np.zeros(4), -u * point]))
        rows.append(np.concatenate([np.zeros(4), point, -v * point]))
    camera = np.linalg.svd(np.array(rows))[2][-1].reshape(3, 4)
    return np.linalg.inv(to_i) @ camera @ to_w


def project(camera, world):
    """Where points in the world appear: (count, 2) pixels, or one pixel for one point."""
    world = np.asarray(world, dtype=float)
    points = np.atleast_2d(world)
    seen = (camera @ np.column_stack([points, np.ones(len(points))]).T).T
    pixels = seen[:, :2] / seen[:, 2:3]
    return pixels[0] if world.ndim == 1 else pixels


def misfit(camera, world, image):
    """How far, in pixels, the marks land from where they were seen: the typical distance."""
    return float(np.median(np.linalg.norm(project(camera, world) - np.asarray(image, dtype=float), axis=1)))


def height_on_post(camera, pixel, x, y):
    """The height at which the upright line standing on ground point (x, y) passes nearest a pixel.

    This is the water's height when the pixel is where the water meets a post, a wall or a wheel
    standing at (x, y). It is exact whatever the camera's angle.
    """
    u, v = pixel
    foot = camera @ np.array([x, y, 0.0, 1.0])
    rise = camera[:, 2]
    slope = np.array([u * rise[2] - rise[0], v * rise[2] - rise[1]])
    gap = np.array([foot[0] - u * foot[2], foot[1] - v * foot[2]])
    return float(slope @ gap / (slope @ slope))


def meet_plane(camera, pixel, level):
    """The ground position (x, y) where a pixel's line of sight meets the level surface at height `level`."""
    u, v = pixel
    first, second = camera[0] - u * camera[2], camera[1] - v * camera[2]
    left = np.array([first[:2], second[:2]])
    right = -np.array([first[2] * level + first[3], second[2] * level + second[3]])
    return np.linalg.solve(left, right)


def locate(cameras, pixels):
    """Where in the world a thing is, from where two or more cameras see it: (x, y, z)."""
    if len(cameras) < 2 or len(cameras) != len(pixels):
        raise ValueError("two cameras are the least that place a thing in space")
    rows = []
    for camera, (u, v) in zip(cameras, pixels):
        rows += [u * camera[2] - camera[0], v * camera[2] - camera[1]]
    point = np.linalg.svd(np.array(rows))[2][-1]
    return point[:3] / point[3]


def surface_speed(cameras, before, after, seconds):
    """The speed of something floating, seen by two or more cameras at two moments.

    before, after: one pixel for each camera. Returns (speed along the surface in world units a second,
    direction in degrees anticlockwise from the x axis, height of the surface it floats on).
    """
    start, end = locate(cameras, before), locate(cameras, after)
    moved = end[:2] - start[:2]
    return (float(np.linalg.norm(moved) / seconds), float(np.degrees(np.arctan2(moved[1], moved[0]))),
            float(0.5 * (start[2] + end[2])))


def speed_on_plane(camera, before, after, level, seconds):
    """The same from one camera, which needs the water's height given. An error in that height becomes
    an error in the speed."""
    moved = meet_plane(camera, after, level) - meet_plane(camera, before, level)
    return float(np.linalg.norm(moved) / seconds), float(np.degrees(np.arctan2(moved[1], moved[0])))


def height_map(marks):
    """Height along one upright object from distance along it in the picture, from its marks.

    marks: [(distance in pixels from any fixed point on the object, height)], two or more. Two marks
    give one scale, which is METHOD C2 as written and is right only when the camera looks level. Three
    or more give the map that perspective obeys, fitted to all of them, so one badly placed mark
    matters less. Returns a function from distance to height.
    """
    marks = np.asarray(marks, dtype=float)
    if len(marks) < 2:
        raise ValueError("two marks are the least that give a scale")
    t, h = marks[:, 0], marks[:, 1]
    if len(marks) == 2:
        slope = (h[1] - h[0]) / (t[1] - t[0])
        return lambda distance: float(h[0] + slope * (distance - t[0]))
    # h = (a t + c) / (1 + b t), which is  a t + c - b (h t) = h : a straight fit for a, c and b.
    a, c, b = np.linalg.lstsq(np.column_stack([t, np.ones(len(t)), -h * t]), h, rcond=None)[0]
    return lambda distance: float((a * distance + c) / (1 + b * distance))


def middle(values, weights):
    """The weighted middle value: half the weight lies at or below it."""
    order = np.argsort(values)
    running = np.cumsum(np.asarray(weights, dtype=float)[order])
    return float(np.asarray(values, dtype=float)[order][np.searchsorted(running, 0.5 * running[-1])])


def best_guess(values, weights):
    """One figure from several readings of the same thing.

    Three or more: the weighted middle one, which a single wild reading cannot move. Two: their weighted
    mean, because two cannot say which of them is wrong. One: itself.
    """
    values, weights = np.asarray(values, dtype=float), np.asarray(weights, dtype=float)
    if (weights <= 0).all():
        weights = np.ones_like(weights)
    if len(values) >= 3:
        return middle(values, weights)
    return float(values @ weights / weights.sum())


def combine(readings):
    """One range from several readings of the same water at the same moment.

    readings: [(low, high, weight)], each from its own reference object or its own camera. Returns
    (low, high, agreed), or None for no readings.

    With three or more, the range runs from the weighted middle of the low ends to the weighted middle
    of the high ends, provided the readings carrying most of the weight overlap it. One reading that is
    far out cannot then move either end. Otherwise `agreed` is False and the range is the cautious one
    of METHOD C5: the weighted middle of the low ends up to the highest high end.
    """
    if not readings:
        return None
    lows, highs, weights = (np.asarray(column, dtype=float) for column in zip(*readings))
    if (weights <= 0).all():
        weights = np.ones_like(weights)
    low = middle(lows, weights)
    if len(readings) >= 3:
        high = max(middle(highs, weights), low)
        overlap = (lows <= high) & (highs >= low)
        if weights[overlap].sum() > MAJORITY * weights.sum():
            return low, high, True
    return low, float(max(highs.max(), low)), False
