"""One water level from everything that can see it, followed through time.

waterline.py reads one strip of one camera. gauge.py learns one camera's whole view. multiview.py
joins finished readings. This module is the model underneath all three: at one place and one
moment there is one water level, and every reference object in every camera is a witness to it.

What a witness is
-----------------
A witness is anything that reports on the water: one strip read by waterline.py, or one camera read
by gauge.py. From the moments at which the level was measured, the model learns for each witness:

    its curve      the row it reports at each level, which only ever goes one way as the water
                   rises. Where the curve is steep the witness is sharp: a small change of level
                   moves its row a lot. Where the curve is flat the witness is blind: the water's
                   edge is hidden behind something, or has run off the end of the strip, and its
                   row says nothing about the level there.
    its spread     how far its row usually lies from the curve, in rows. This has two parts: how
                   much it wanders within a day, and how far a whole day sits from the curve
                   because of that day's light. Both are measured on days the curve did not see.
    its wild rate  the share of its reports that are nowhere near the curve.
    what it says   how often, at each level, it reports a line, reports "dry", or reports
                   neither. A strip that goes quiet above some level is saying something by it.

One level from many witnesses
-----------------------------
For any level, each witness's report has a likelihood: near its curve at that level it is likely,
far from it unlikely, and never less likely than its wild rate allows, so that no single witness can
veto the rest. The likelihoods are multiplied over the witnesses. Three things follow that joining
finished readings cannot give:

    a blind witness says nothing, and does not vote for wherever it happens to point;
    a sharp witness outweighs a blunt one by exactly as much as it is sharper;
    a wild report is outvoted by degrees and is not thrown away by a rule.

Witnesses in one camera share its light, its rain and its lens, so they are wrong together more
often than strangers would be. Their evidence is therefore counted at a share of its face value.
That share is not chosen: it is the one under which days left out of the learning are predicted
best. Witnesses in different cameras are multiplied at full value, each camera with its own share.

Through time
------------
Water rises and falls at a limited rate. The level at one moment is therefore evidence about the
next: what was believed is spread out by as much as the level could have moved in the time gone by,
and then multiplied by what the witnesses say now. One wild moment among steady ones is outvoted by
its neighbours in time, as one wild witness is by its neighbours in space. The rate is learnt from
the measured levels. Only the past is used, so this can run as the pictures arrive.

A witness that is wrong at ten o'clock is usually wrong the same way at eleven, in the same light.
Hour after hour it is not new evidence each time. So when the level is followed through time the
witnesses' evidence is counted at a second, smaller share, learnt the same way as the first.

What comes out
--------------
A level, and a range that is as wide as the model has been wrong. Each day is left out in turn,
learnt without and then read; the range is stretched until it would have held nine in ten of those.
`to_reading` turns the answer into the depth range and confidence that the site engine takes
(state.Reading), measured up from the level of the road.

Past what it has seen
---------------------
A curve learnt from measured levels ends where those levels end, and the model cannot read past
them. Water higher than anything it learnt from is read as a level inside what it learnt, and it
does not know that this has happened. Making it say so was tried: a row lying past the end of a
curve was counted as evidence of water past the end of the levels. That worked on made witnesses.
On the real cameras it never fired, because the strips there are blind at both ends of their range,
and it was taken out. A witness whose curve comes from the known size of what it looks at, and not
from levels seen, would not have this limit. multiview.py has that arithmetic, untried on a real
camera.

Measured on a real flood by scripts/river_depth_model.py, and on rendered scenes with several
cameras by scripts/simulate_site.py. It learns from measured levels, which no site in this project
has yet, and nothing calls it.
"""

from dataclasses import dataclass, field

import numpy as np

from .state import Reading as SiteReading

STEP = 0.01                # the levels tried are this far apart, in the units of the measured levels (metres)
PAD = 0.15                 # and run this far beyond the lowest and highest level learnt from
LEAST_SPREAD = 1.0         # rows: no witness is taken to be more exact than this
WILD_AT = 3.0              # a report this many spreads from the curve is counted as wild
SMOOTH = 0.08              # what a witness says at a level is learnt from levels within this share of the whole range
SHARES = (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0)      # the shares of face value tried for the witnesses of one camera
EXTRA_SHARES = (0.0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0)      # and for a witness that brings its own likelihood
LEAST_RATE = 0.01          # per hour: the level is never taken to be steadier than this
JUMP = 0.02                # each hour, the chance that the level has moved by any amount at all
NEAR = 0.05                # a prediction is scored by the belief it put within this of the measured level
KINDS = ("line", "dry", "other")


@dataclass
class Witness:
    """What one reference object has been seen to report at known levels. Arrays run along the model's grid."""
    name: str
    camera: str
    row: np.ndarray            # the row it reports at each level, when it reports a line
    spread: float              # rows: within a day and between days together
    wild: float                # the share of its lines that are nowhere near the curve
    rows: int                  # how many rows its strip has: a wild line could be in any of them
    says: np.ndarray           # (levels, 3): the chance it reports a line, "dry", or neither, at each level
    lines: int                 # how many lines it was learnt from
    within: float = 0.0        # rows: how much it wanders inside one day
    between: float = 0.0       # rows: how far a whole day sits from the curve

    def sharpness(self):
        """How many spreads its row moves for each step of level: zero where it is blind."""
        return np.abs(np.gradient(self.row)) / self.spread


@dataclass
class Reading:
    """One answer. `level`, `low` and `high` are in the units the model was taught in."""
    level: float
    low: float
    high: float
    belief: np.ndarray         # along the grid, adding to one
    informed: float            # 0 when the witnesses said nothing that tells levels apart, towards 1 as they did


@dataclass
class SiteModel:
    grid: np.ndarray
    witnesses: dict
    share: dict                # camera -> the share of face value its witnesses' evidence is counted at, one moment alone
    through: dict              # the same when the level is followed through time
    rate: float                # how far the level typically moves in an hour
    stretch: float = 1.0       # the range of a moment alone is this many times as wide as the belief alone would make it
    stretch_through: float = 1.0
    extras: dict = field(default_factory=dict)       # name -> (share alone, share through time), for witnesses that bring their own likelihood
    left_out: tuple = ()       # (measured, read, low, high) through time, for each moment of each day left out in turn


def one_way(levels, values):
    """The curve of `values` against `levels` that only ever goes one way and is nearest in the sense
    that a few wild values do not move it: neighbours that disagree are pooled and given their middle
    value. Returns (levels of the pooled groups, their values), ready to be read between.
    """
    levels, values = np.asarray(levels, dtype=float), np.asarray(values, dtype=float)
    order = np.argsort(levels, kind="stable")
    levels, values = levels[order], values[order]
    falling = bool(np.corrcoef(levels, values)[0, 1] < 0) if len(levels) > 2 and values.std() > 0 and levels.std() > 0 else False
    if falling:
        values = -values
    merged = []
    for level, value in zip(levels, values):
        merged.append([[level], [value]])
        while len(merged) > 1 and np.median(merged[-2][1]) > np.median(merged[-1][1]):
            last = merged.pop()
            merged[-1][0] += last[0]
            merged[-1][1] += last[1]
    at = np.array([np.mean(g[0]) for g in merged])
    value = np.array([np.median(g[1]) for g in merged])
    return at, (-value if falling else value)


def _spreads(apart, days):
    """A witness's misses split into how much it wanders inside a day and how far whole days sit off
    the curve: (within, between), in rows. Middle values throughout, so a wild report or a wild day
    does not set the figure."""
    apart = np.asarray(apart, dtype=float)
    if days is None or len(np.unique(days)) < 3:
        return 1.4826 * float(np.median(np.abs(apart - np.median(apart)))), 0.0
    names = np.unique(days)
    middles = np.array([np.median(apart[days == day]) for day in names])
    inside = [1.4826 * np.median(np.abs(apart[days == day] - middle)) for day, middle in zip(names, middles) if (days == day).sum() >= 3]
    within = float(np.median(inside)) if inside else 0.0
    between = 1.4826 * float(np.median(np.abs(middles - np.median(middles))))
    return within, between


def learn_witness(name, grid, levels, reports, rows, camera="", days=None):
    """One witness from the moments it was watched at a known level.

    reports: one (kind, row) for each level, kind being "line", "dry" or anything else. days: which
    moments share a day. With days, how far the witness lies from its curve is measured on each day by a
    curve that did not see that day: a curve fitted through a day's own rows flatters itself. Returns
    None for a witness that reported fewer than six lines, or always the same row: it has nothing to teach.
    """
    levels = np.asarray(levels, dtype=float)
    kinds = np.array([KINDS.index(kind) if kind in KINDS[:2] else 2 for kind, _ in reports])
    line = kinds == 0
    seen = np.array([row for (_, row), is_line in zip(reports, line) if is_line], dtype=float)
    if line.sum() < 6 or np.ptp(seen) < 1e-9:
        return None
    at, value = one_way(levels[line], seen)
    curve = np.interp(grid, at, value)
    apart = seen - np.interp(levels[line], at, value)
    its_days = None if days is None else np.asarray(days)[line]
    if its_days is not None and len(np.unique(its_days)) >= 3:
        for day in np.unique(its_days):
            rest = its_days != day
            if rest.sum() >= 5 and np.ptp(seen[rest]) > 1e-9:
                apart[~rest] = seen[~rest] - np.interp(levels[line][~rest], *one_way(levels[line][rest], seen[rest]))
    within, between = _spreads(apart, its_days)
    spread = max(float(np.hypot(within, between)), LEAST_SPREAD)
    wild = (float((np.abs(apart - np.median(apart)) > WILD_AT * spread).sum()) + 1.0) / (line.sum() + 10.0)
    width = max(SMOOTH * float(np.ptp(grid)), 5 * STEP)
    near = np.exp(-0.5 * ((grid[:, None] - levels[None, :]) / width) ** 2)
    says = np.stack([(near * (kinds == k)[None, :]).sum(axis=1) for k in range(3)], axis=1) + 1.0
    return Witness(name, camera, curve, spread, wild, int(rows), says / says.sum(axis=1, keepdims=True), int(line.sum()), within, between)


def evidence(witness, kind, row=None):
    """How likely this report is at each level, in log. A line far from the curve is never less likely
    than the witness's wild rate allows."""
    if kind == "line":
        apart = (row - witness.row) / witness.spread
        near = np.exp(-0.5 * apart * apart) / (witness.spread * np.sqrt(2 * np.pi))
        return np.log(witness.says[:, 0]) + np.log((1.0 - witness.wild) * near + witness.wild / witness.rows)
    return np.log(witness.says[:, 1 if kind == "dry" else 2])


def _spread_by(grid, hours, rate):
    """How belief about the level spreads over `hours`: the chance of ending at each level from each."""
    scale = max(rate * hours, STEP)
    drift = np.exp(-np.abs(grid[:, None] - grid[None, :]) / scale)
    drift /= drift.sum(axis=0, keepdims=True)
    jumped = 1.0 - (1.0 - JUMP) ** hours
    return (1.0 - jumped) * drift + jumped / len(grid)


def _summary(grid, belief, stretch, start):
    running = np.cumsum(belief)
    pick = lambda share: float(grid[min(int(np.searchsorted(running, share)), len(grid) - 1)])       # noqa: E731
    level, low, high = pick(0.5), pick(0.05), pick(0.95)
    gained = float(np.sum(belief * (np.log(belief + 1e-300) - np.log(start + 1e-300))))
    return Reading(level, level - stretch * (level - low), level + stretch * (high - level), belief, float(1.0 - np.exp(-max(gained, 0.0))))


def believe(model, reports, before=None, hours=None, extra=None, through=False):
    """The level at one moment.

    reports: {witness name: (kind, row)} for the witnesses that were looked at. extra: {name: log
    likelihood along the grid} for witnesses that bring their own, such as a learnt gauge. before: the
    belief at an earlier moment, and hours: how long ago that was. through: this moment is one of a run
    being followed through time, so the evidence is counted at the share learnt for that.
    """
    grid = model.grid
    flat = np.full(len(grid), 1.0 / len(grid))
    start = flat if before is None else _spread_by(grid, max(hours, 0.0), model.rate) @ before
    shares = model.through if through else model.share
    total = np.log(start + 1e-300)
    for name, (kind, row) in reports.items():
        witness = model.witnesses.get(name)
        if witness is not None:
            total = total + shares.get(witness.camera, 1.0) * evidence(witness, kind, row)
    for name, said in (extra or {}).items():
        if said is not None and name in model.extras:
            total = total + model.extras[name][1 if through else 0] * (np.asarray(said, dtype=float) - np.max(said))
    belief = np.exp(total - total.max())
    return _summary(grid, belief / belief.sum(), model.stretch_through if through else model.stretch, flat)


def follow(model, moments, extras=None):
    """The level at each of a run of moments, each using only what came before it.

    moments: [(hours on any clock, {witness: (kind, row)})] in order of time. extras: for each moment,
    {name: log likelihood along the grid} or None. Returns one Reading each.
    """
    out, before, last = [], None, None
    for index, (when, reports) in enumerate(moments):
        reading = believe(model, reports, before, None if last is None else when - last,
                          None if extras is None else extras[index], through=True)
        out.append(reading)
        before, last = reading.belief, when
    return out


def _witnesses(grid, levels, reports, rows, cameras, days):
    out = {}
    for name, said in reports.items():
        witness = learn_witness(name, grid, levels, said, rows[name], cameras.get(name, ""), days)
        if witness is not None:
            out[name] = witness
    return out


def _score(grid, belief, level):
    """How much belief was put near the measured level, in log."""
    return float(np.log(belief[np.abs(grid - level) <= NEAR].sum() + 1e-12))


def learn(levels, reports, rows, days, hours, cameras=None, extras=None, check=True):
    """A model of one place from the moments at which its level was measured.

    levels: the measured level at each moment. reports: {witness: [(kind, row) at each moment]}.
    rows: {witness: rows in its strip}. days: which moments share a day's light; hours: each moment's
    time on one running clock. cameras: {witness: camera name}; the witnesses of one camera share a
    share. extras: {name: for each moment, the log likelihood along `grid_for(levels)` or None}, for a
    witness that brings its own; each moment's must have been made without that moment's day. With
    `check`, each day is left out in turn to set the shares and the stretch of the range.
    """
    levels, days, hours = np.asarray(levels, dtype=float), np.asarray(days), np.asarray(hours, dtype=float)
    cameras, extras = cameras or {}, extras or {}
    grid = grid_for(levels)
    witnesses = _witnesses(grid, levels, reports, rows, cameras, days)
    order = np.argsort(hours)
    gaps, moved = np.diff(hours[order]), np.abs(np.diff(levels[order]))
    close = (gaps > 0) & (gaps <= 24)
    rate = max(float(moved[close].sum() / gaps[close].sum()) if close.any() else LEAST_RATE, LEAST_RATE)
    names = sorted({cameras.get(name, "") for name in witnesses})
    ones = {camera: 1.0 for camera in names}
    model = SiteModel(grid, witnesses, dict(ones), dict(ones), rate, extras={name: (0.0, 0.0) for name in extras})
    if not check or len(np.unique(days)) < 3:
        return model
    without = {}
    for day in np.unique(days):
        rest = days != day
        without[day] = _witnesses(grid, levels[rest], {n: [s for s, r in zip(said, rest) if r] for n, said in reports.items()},
                                  rows, cameras, days[rest])

    def left_out(share, extra_share, through):
        """Every moment of every day, read by witnesses learnt without that day."""
        trial = SiteModel(grid, {}, share, share, rate, extras=extra_share)
        out = []
        for day, learnt in without.items():
            trial.witnesses = learnt
            chosen = np.flatnonzero(days == day)
            chosen = chosen[np.argsort(hours[chosen])]
            before, last = None, None
            for i in chosen:
                reading = believe(trial, {n: reports[n][i] for n in learnt}, before if through else None,
                                  None if last is None else hours[i] - last, {n: extras[n][i] for n in extras}, through)
                out.append((float(levels[i]), reading))
                before, last = reading.belief, hours[i]
        return out

    def best(through):
        """The shares under which the left-out days are predicted best, one camera at a time and then
        each witness that brought its own likelihood."""
        share, extra_share = dict(ones), {name: (0.0, 0.0) for name in extras}
        mean = lambda s, e: float(np.mean([_score(grid, r.belief, level) for level, r in left_out(s, e, through)]))      # noqa: E731
        for _ in range(2):                                                       # twice round, since each depends on the others
            for camera in names:
                share[camera] = max(SHARES, key=lambda value: mean(dict(share, **{camera: value}), extra_share))
            for name in extras:
                extra_share[name] = max(((v, v) for v in EXTRA_SHARES), key=lambda pair: mean(share, dict(extra_share, **{name: pair})))
        return share, extra_share

    def stretch(rows):
        ratios = [abs(level - r.level) / max(0.5 * (r.high - r.low), STEP) for level, r in rows]
        return max(1.0, float(np.percentile(ratios, 90)))

    model.share, alone_extras = best(False)
    model.through, through_extras = best(True)
    model.extras = {name: (alone_extras[name][0], through_extras[name][0]) for name in extras}
    model.stretch = stretch(left_out(model.share, alone_extras, False))
    final = left_out(model.through, through_extras, True)
    model.stretch_through = stretch(final)
    model.left_out = tuple((level, r.level, r.level - model.stretch_through * (r.level - r.low),
                            r.level + model.stretch_through * (r.high - r.level)) for level, r in final)
    return model


def to_reading(answer, road, ts, device, per_unit=100.0):
    """The model's answer as the reading the site engine takes: a depth range in centimetres above the
    road, and a confidence.

    road: the level of the road's lowest point, in the units the model was taught in. per_unit: how many
    centimetres one of those units is. The confidence is how much the witnesses told the model, from 0
    when they said nothing that tells levels apart: a belief that is no narrower than not looking is
    never a reason to call a road passable.
    """
    low = max(0.0, (answer.low - road) * per_unit)
    high = max(low, (answer.high - road) * per_unit)
    return SiteReading(float(ts), float(low), float(high), float(min(answer.informed, 0.95)), "cctv", device)


def grid_for(levels):
    """The levels a model taught on these levels will try."""
    levels = np.asarray(levels, dtype=float)
    return np.arange(levels.min() - PAD, levels.max() + PAD + STEP / 2, STEP)
