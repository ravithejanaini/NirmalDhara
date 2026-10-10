"""Water in, water out: what a flood reveals about a place, and the depth ahead (METHOD.md section 15).

A dip in a road is a tank. The water in it changes by what runs in less what drains out, and the
shape of the road says how deep a given amount of water stands (volume.py). That one equation is
used here three ways.

Backwards, after a flood (`reveal`)
    From the depths read during one flood and the rain that fell: how fast the place empties once
    the rain has stopped, and how much ground the water came from. The second is the "effective
    catchment": the rain that reached the dip, as an area. Each depth is a range, so both come out
    as ranges, by working the sum a thousand times with every depth drawn from within its range
    (METHOD 15.4).

Forwards, from what is running in now (`at_this_inflow`)
    The prediction stage carries the depth forward in a straight line (predict.py). A dip widens
    as it fills, so the same inflow raises the water more slowly the deeper it gets, and a straight
    line in depth says a road will be lost sooner than it will. Here the line is drawn through the
    volume, and the depth is read back off the road's shape. No rain figure is needed.

Forwards, from rain (`ahead`, `rain_to_reach`)
    With what earlier floods revealed, the depth that a given rain would bring, and the other way
    about: the rain in the next hour that would close the road to each class of user. The second
    needs no forecast. It is a figure a person can hold a forecast against.

`check` plays each recorded flood forward from the floods before it, which is how this is to be
judged once a place has floods on record. None has. Tried on made floods only, by
scripts/simulate_inflow.py. A forecast from rain is no better than the rain: docs/watch-history.md
shows the forecast the live system is fed holding a fraction of what gauges recorded. Nothing calls
this module.
"""

from dataclasses import dataclass
from random import Random
from statistics import median

from .bands import NO_GO_CM
from .predict import rise_rate

DRAWS = 1000               # times the sum is worked, each with every depth drawn from within its range (METHOD 15.4)
SETTLE_S = 1800            # inflow is taken to have stopped this long after the rain did (METHOD 15.1)
MIN_READINGS = 4           # a flood with fewer readings is not used (METHOD 15.7)
MIN_FALLING = 3            # readings needed after the rain to say how fast the place empties
MOST_FALLING = 12          # and no more than about this many of them are used, spread evenly
INTERVAL = (0.1, 0.9)      # the ends of the range each figure is given with: it holds four in five of the draws
STEP_S = 60                # the depth ahead is worked out in steps of this length


@dataclass(frozen=True)
class Range:
    low: float
    mid: float
    high: float


@dataclass(frozen=True)
class Revealed:
    """What one flood, or several, revealed about a place."""
    area_m2: Range | None          # the ground the water came from: rain that reached the dip, as an area
    drain_m3s: Range | None        # how fast the place empties when nothing is running in
    floods: int = 1
    peak_cm: float = 0.0           # the deepest reading's high end
    rain_mm: float = 0.0           # the rain up to that peak


def _spread(values):
    values = sorted(values)
    pick = lambda share: values[min(int(share * len(values)), len(values) - 1)]      # noqa: E731
    return Range(pick(INTERVAL[0]), median(values), pick(INTERVAL[1]))


def stored(curve, depth_cm):
    """Cubic metres standing in the dip when the water is this deep at its lowest point."""
    return curve.volume(depth_cm / 100.0)


def depth_of(curve, volume_m3):
    """The depth in centimetres at which this much water stands."""
    return 100.0 * curve.depth(volume_m3)


def _rain_between(rain, start, end):
    """Millimetres that fell between two times. rain: [(time an interval ended, mm in it)], in order."""
    total, before = 0.0, None
    for ts, mm in rain:
        opened = before if before is not None else ts - (rain[1][0] - rain[0][0] if len(rain) > 1 else 3600)
        overlap = min(ts, end) - max(opened, start)
        if overlap > 0 and ts > opened:
            total += mm * overlap / (ts - opened)
        before = ts
    return total


def _one_way(values):
    """The nearest list that never goes down: neighbours that do are pooled and given their mean."""
    blocks = []
    for value in values:
        blocks.append([value, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            last, count = blocks.pop()
            blocks[-1] = [(blocks[-1][0] * blocks[-1][1] + last * count) / (blocks[-1][1] + count), blocks[-1][1] + count]
    return [value for value, count in blocks for _ in range(count)]


def _shaped(depths, top):
    """The depths as a flood's must be: only rising to the deepest reading and only falling after it
    (METHOD 15.4). Readings that err one way and then the other are averaged, where taking the largest of
    them as the peak would always say too much."""
    rise = _one_way(depths[:top + 1])
    fall = [-value for value in _one_way([-depth for depth in depths[top:]])]
    return rise[:-1] + [(rise[-1] + fall[0]) / 2.0] + fall[1:]


def _deepest(readings):
    """Which reading is the deepest, judged by the middle one of each three so that one high reading is not it."""
    mids = [(r[1] + r[2]) / 2.0 for r in readings]
    calm = [median(mids[max(i - 1, 0):i + 2]) for i in range(len(mids))]
    return max(range(len(calm)), key=calm.__getitem__)


def _one(curve, times, depths, rain, rain_end, top):
    """One working of the sum from one set of depths: (area in square metres, drain in cubic metres a second);
    either is None where the readings cannot say."""
    depths = _shaped(depths, top)
    volumes = [stored(curve, d) for d in depths]
    after = [(t / 60.0, v) for t, v, d in zip(times, volumes, depths) if t >= rain_end + SETTLE_S and d > 0]
    after = after[::max(len(after) // MOST_FALLING, 1)]                # every pair's slope is taken: a few readings well apart are enough
    fall = rise_rate(after) if len(after) >= MIN_FALLING else None
    drain = None if fall is None or fall >= 0 else -fall / 60.0
    fell = _rain_between(rain, times[0], times[top]) / 1000.0
    if top == 0 or fell <= 0:
        return None, drain
    wet = sum(b - a for a, b, d in zip(times[:top], times[1:top + 1], depths[1:top + 1]) if d > 0)
    ran_in = volumes[top] - volumes[0] + (drain or 0.0) * wet
    return (ran_in / fell if ran_in > 0 else None), drain


def reveal(curve, readings, rain, seed=0):
    """What one flood reveals. readings: [(seconds, low cm, high cm)] in order of time. rain: [(seconds at
    which an interval ended, mm in it)] on the same clock. Returns None for a flood with too few readings.

    The drain rate comes from readings taken at least half an hour after the last rain, while water
    still stood. The area comes from the water that had run in by the deepest reading, counting what
    drained meanwhile, over the rain that had fallen by then. Without a drain rate the area is a floor.
    """
    if len(readings) < MIN_READINGS or not rain:
        return None
    times = [r[0] for r in readings]
    wet = [ts for ts, mm in rain if mm > 0]
    if not wet:
        return None
    rain_end, rng, deepest = wet[-1], Random(seed), _deepest(readings)
    areas, drains = [], []
    for _ in range(DRAWS):
        area, drain = _one(curve, times, [rng.uniform(r[1], r[2]) for r in readings], rain, rain_end, deepest)
        if area is not None:
            areas.append(area)
        if drain is not None:
            drains.append(drain)
    enough = DRAWS // 2                                                # a figure most draws could not give is not given
    top = readings[deepest]
    return Revealed(_spread(areas) if len(areas) >= enough else None, _spread(drains) if len(drains) >= enough else None,
                    1, float(top[2]), _rain_between(rain, times[0], top[0]))


def together(floods):
    """Several floods' findings as one: each range runs from the lowest low end to the highest high end,
    about the middle one of the middles. None if no flood gave both figures."""
    full = [f for f in floods if f is not None and f.area_m2 is not None and f.drain_m3s is not None]
    if not full:
        return None
    join = lambda ranges: Range(min(r.low for r in ranges), median(r.mid for r in ranges), max(r.high for r in ranges))      # noqa: E731
    return Revealed(join([f.area_m2 for f in full]), join([f.drain_m3s for f in full]), len(full),
                    max(f.peak_cm for f in full), max(f.rain_mm for f in full))


def _run(curve, depth_cm, area_m2, drain_m3s, rain_ahead, seconds):
    """The depth at each step from now, for one area and one drain rate: [(seconds, cm)]."""
    volume, out, t = stored(curve, depth_cm), [], 0
    while t < seconds:
        falling = _rain_between(rain_ahead, t, t + STEP_S) / 1000.0
        volume = max(volume + area_m2 * falling - (drain_m3s * STEP_S if volume > 0 or falling > 0 else 0.0), 0.0)
        t += STEP_S
        out.append((t, depth_of(curve, volume)))
    return out


def ahead(found, curve, low_cm, high_cm, rain_ahead, seconds=3600):
    """The depth from now on if this rain falls: [(seconds from now, low cm, high cm)].

    found: what earlier floods revealed. rain_ahead: [(seconds from now at which an interval ends, mm in
    it)]. The low end starts from the low depth with the smallest area and the fastest drain, the high
    end from the high depth with the largest area and the slowest drain.
    """
    low = _run(curve, low_cm, found.area_m2.low, found.drain_m3s.high, rain_ahead, seconds)
    high = _run(curve, high_cm, found.area_m2.high, found.drain_m3s.low, rain_ahead, seconds)
    return [(t, a, b) for (t, a), (_, b) in zip(low, high)]


def minutes_to_no_go(path, low_cm, high_cm):
    """From a path of depths ahead, the minutes until each class loses passage: {class: (sooner, later)}.
    sooner is when the high end reaches the class's limit and later when the low end does. Either is
    None if that does not come on the path, and 0 if it is so already."""
    out = {}
    for vehicle, limit in NO_GO_CM.items():
        first = lambda now, column: 0.0 if now >= limit else next((t / 60.0 for t, *ends in path if ends[column] >= limit), None)      # noqa: E731
        out[vehicle] = (first(high_cm, 1), first(low_cm, 0))
    return out


def rain_to_reach(found, curve, low_cm, high_cm, limit_cm, minutes=60):
    """The rain, in millimetres over the next `minutes`, that would bring the water to `limit_cm`:
    (least, most). The least is from the high depth with the largest area and the slowest drain. 0 where
    the water is there already."""
    def needed(depth, area, drain):
        short = stored(curve, limit_cm) - stored(curve, depth)
        return 0.0 if short <= 0 else 1000.0 * (short + drain * 60.0 * minutes) / area
    return (needed(high_cm, found.area_m2.high, found.drain_m3s.low), needed(low_cm, found.area_m2.low, found.drain_m3s.high))


def guidance(found, curve, low_cm=0.0, high_cm=0.0, minutes=60):
    """The rain in the next `minutes` that would close the road to each class: {class: (least mm, most mm)}."""
    return {vehicle: rain_to_reach(found, curve, low_cm, high_cm, limit, minutes) for vehicle, limit in NO_GO_CM.items()}


def at_this_inflow(curve, readings):
    """Minutes until each class loses passage if water keeps running in as it has been: {class: (sooner,
    later)}, or None when the water is not rising.

    readings: the last few, [(seconds, low cm, high cm)]. The rate is the middle of the slopes of every
    pair, as predict.rise_rate takes it, but through the volume stored and not through the depth. sooner
    is from the high ends and later from the low ends.
    """
    ends = []
    for column in (2, 1):
        rate = rise_rate([(r[0] / 60.0, stored(curve, r[column])) for r in readings])       # cubic metres a minute
        if rate is None or rate <= 0:
            return None
        ends.append((stored(curve, readings[-1][column]), rate))
    out = {}
    for vehicle, limit in NO_GO_CM.items():
        full = stored(curve, limit)
        sooner, later = (max(full - now, 0.0) / rate for now, rate in ends)
        out[vehicle] = (sooner, later)
    return out


def check(curve, floods):
    """Each recorded flood played forward from the floods before it: [{peak read, peak said (low, high),
    held}] for the second flood on. floods: [(readings, rain)] in order of date, or [(readings, rain,
    the rain as it was foretold)] where the two differ: a flood is revealed by the rain that fell and
    played forward by the rain that was expected. A flood is left out where the ones before it gave no
    figures.

    This is the test this module is to be judged by. It needs a place with floods on record.
    """
    out, known = [], []
    for readings, rain, *foretold in floods:
        found = together(known)
        if found is not None and len(readings) >= MIN_READINGS:
            start, last = readings[0], readings[-1][0] - readings[0][0]
            shifted = [(ts - start[0], mm) for ts, mm in (foretold[0] if foretold else rain)]
            path = ahead(found, curve, start[1], start[2], shifted, last)
            said = (max(low for _, low, _ in path), max(high for _, _, high in path)) if path else (start[1], start[2])
            top = max(readings, key=lambda r: r[2])
            out.append({"peak read": (top[1], top[2]), "peak said": said, "held": said[0] <= top[2] and said[1] >= top[1]})
        known.append(reveal(curve, readings, rain))
    return out
