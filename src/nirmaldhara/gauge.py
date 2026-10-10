"""A water-level gauge that a fixed camera learns from its own pictures.

waterline.py is told what the surface looks like dry and works the rest out from first principles.
This module is told nothing about the scene. It is given pictures from one fixed camera, each with
the water level that somebody measured at the time, and from those it learns two things:

    1  For each small patch of the picture, the level at which that patch goes under water. Put in
       order of level, the days show a patch looking one way up to some level and another way above
       it; the place where that step falls is the height of whatever the patch shows. All the
       patches together are a map of heights in the camera's own view.
    2  What each patch looks like dry and what it looks like wet. Nothing about water is assumed.
       What water does to this patch is read off the pictures.

A new picture is then read by asking which level best explains which patches look wet.

Only two things are kept about a patch: how like its dry self its pattern still is, and its
contrast. Both are unchanged when the patch as a whole gets brighter or dimmer. Brightness and
colour were tried and thrown out: water is grey under cloud and dark blue under a clear sky, and a
gauge that had learnt one called the other dry.

Four things keep it honest.

A step is only ever known to lie between two days whose levels were measured. A patch that was dry
on a day at 11.5 m and wet on a day at 12.1 m went under somewhere between, and the gauge does not
pretend to know where: at a level in that gap the patch is counted as under with a chance that
rises across the gap. So in a gap the reading comes from the share of such patches that look wet.

It cannot read past what it has seen. Below its lowest step it says "below what was learnt" and
gives a ceiling; above its highest, "above what was learnt" and a floor. The floor is the lowest
level the picture fits as well as it fits "above everything", so it claims no more than is shown.
And if the water covers the patches the gauge knows the view by, it says "unreadable": it cannot
tell that from a cover over the lens.

Light is the main way to be fooled. The pictures of one day share their light, so a step is never
put inside a day, and each side of it must hold more than one day. How much a patch's look moves
from one day to the next is measured over all the patches together and added to every patch's
spread. And a patch is used only if its neighbours agree with it about the height: the height of
a scene changes smoothly from one patch to the next, and the weather does not.

A level is given only if it explains the picture. If the patches that should be dry at that level
look wet and the ones that should be wet look dry, no level explains it, and the answer is
"unreadable".

How far out it is, is measured and not assumed: `learn` leaves each day out in turn, learns from
the rest, reads the day left out, and keeps the errors. The interval on a reading comes from those.

Measured on a real flood by scripts/learn_river_cameras.py. It has not been used on a street, and
it needs measured levels to learn from, which no site in this project has yet.
"""

from dataclasses import dataclass

import numpy as np

LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)
PATCH = 8                  # pixels each way in a patch
STEP = 4                   # pixels between one patch and the next
NOISE = 2.0                # grey levels: below this a patch's own variation is taken as noise
DRY_SHARE = 0.1            # the lowest tenth of the pictures, by level, make the dry look
FLOORS = np.array([0.08, 0.15], dtype=np.float32)   # the least spread allowed in likeness and in contrast
FEW = 4                    # a step needs at least this many pictures on each side
DAYS_EACH_SIDE = 2         # and whole days on each side: a step is never put inside a day
GAIN = 0.3                 # a step must explain the pictures better than no step by this much a picture, in log
APART = 2.5                # and move likeness or contrast by this many spreads
NEIGHBOURS = 3             # of the eight patches around it, this many must be used too and agree on the height
AGREE = 0.25               # agreeing means within this share of the range of levels learnt from
LIMIT = 3.0                # one patch may not say more than this, in log, for or against being under
GRID = 600                 # levels tried when a picture is read
EVIDENCE = 0.1             # neighbouring patches overlap and share their light: their evidence is not independent
EDGE = 0.05                # a level must beat "below every step" and "above every step" by this much a patch, in log
EXPLAINED = 0.6            # and this share of the patches must look the way that level says they should
ANCHOR_LIKE = 0.6          # a patch whose pattern stays at least this like the dry look in every picture is an anchor
ANCHOR_LOST = 0.5          # the view is refused if the anchors are less than this share as like it as they were


@dataclass
class Level:
    """One reading. `level`, `low` and `high` are in the units the gauge was taught in.

    reason: "ok"; "below what was learnt" (level is then a ceiling); "above what was learnt" (a floor);
    "unreadable" (not this camera's view, or no level explains the picture).
    """
    found: bool
    level: float
    low: float
    high: float
    reason: str
    explained: float = float("nan")    # the share of patches that look the way the reading says they should


def _means(image):
    """The mean of every PATCH by PATCH window, one every STEP pixels."""
    total = np.cumsum(np.cumsum(image, axis=0, dtype=np.float64), axis=1)
    total = np.pad(total, ((1, 0), (1, 0)))
    sums = total[PATCH:, PATCH:] - total[:-PATCH, PATCH:] - total[PATCH:, :-PATCH] + total[:-PATCH, :-PATCH]
    return sums[::STEP, ::STEP] / (PATCH * PATCH)


def _grey(picture):
    return np.asarray(picture, dtype=np.float32)[..., :3] @ LUMA


def describe(picture, dry):
    """What is kept about each patch of one picture: (patches down, patches across, 2).

    `dry` is the camera's dry look in grey. First, how like the dry look the patch's pattern is: 1 for
    the same pattern at any brightness, about 0 for no relation. Second, its contrast, as the log of
    spread over mean. Neither moves when the patch as a whole is lit more or less.
    """
    grey = _grey(picture)
    mean, dry_mean = _means(grey), _means(dry)
    spread = np.maximum(_means(grey * grey) - mean * mean, 0.0)
    dry_spread = np.maximum(_means(dry * dry) - dry_mean * dry_mean, 0.0)
    together = _means(grey * dry) - mean * dry_mean
    like = together / np.sqrt((spread + NOISE ** 2) * (dry_spread + NOISE ** 2))
    contrast = 0.5 * np.log((spread + NOISE ** 2) / (mean * mean + 1.0))
    return np.stack([like, contrast], axis=-1).astype(np.float32)


def dry_look(pictures, levels):
    """The camera's view at its driest, in grey: the middle value, pixel by pixel, of the lowest tenth of
    the pictures, each first brought to the same overall brightness."""
    order = np.argsort(np.asarray(levels, dtype=float), kind="stable")
    lowest = order[:max(5, int(round(DRY_SHARE * len(order))))]
    greys = np.array([_grey(pictures[i]) for i in lowest])
    typical = np.median(greys.reshape(len(greys), -1), axis=1)
    return np.median(greys * (np.median(typical) / np.maximum(typical, 1.0))[:, None, None], axis=0).astype(np.float32)


def _in_days(levels, days):
    """The pictures put in order with each day kept together and the days sorted by their middle level.

    Returns (order, where each later day starts in that order, the middle level of each day).
    """
    names = np.unique(days)
    middles = np.array([np.median(levels[days == name]) for name in names])
    rank = np.argsort(middles, kind="stable")
    members = [np.flatnonzero(days == names[r]) for r in rank]
    order = np.concatenate([m[np.argsort(levels[m], kind="stable")] for m in members])
    return order, np.cumsum([len(m) for m in members])[:-1], middles[rank]


def _steps(described, order, starts):
    """For every patch, the best place to cut the days, sorted by level, into dry below and wet above.

    Returns (gain a picture in log, which day is the first wet one), with a gain of zero where no cut
    is allowed. A cut is only ever made between two days: the pictures of one day share their light, and
    a cut inside a day would as readily find the morning and the afternoon.
    """
    count = len(order)
    x = described[order].astype(np.float64)
    floor = FLOORS.astype(np.float64) ** 2
    running, running_squares = np.cumsum(x, axis=0), np.cumsum(x * x, axis=0)
    whole = np.log(np.maximum(running_squares[-1] / count - (running[-1] / count) ** 2, 0.0) + floor)
    best_gain = np.zeros(x.shape[1])
    best_day = np.zeros(x.shape[1], dtype=int)
    for day, cut in enumerate(starts, start=1):
        rest = count - cut
        if min(cut, rest) < FEW or day < DAYS_EACH_SIDE or len(starts) + 1 - day < DAYS_EACH_SIDE:
            continue
        below = np.maximum(running_squares[cut - 1] / cut - (running[cut - 1] / cut) ** 2, 0.0) + floor
        above = np.maximum((running_squares[-1] - running_squares[cut - 1]) / rest
                           - ((running[-1] - running[cut - 1]) / rest) ** 2, 0.0) + floor
        gain = 0.5 * (count * whole - cut * np.log(below) - rest * np.log(above)).sum(axis=-1) / count
        better = gain > best_gain
        best_gain[better], best_day[better] = gain[better], day
    return best_gain, best_day


def _looks(described, order, starts, chosen, first_wet):
    """What each chosen patch looks like dry and wet: [dry middle, dry spread, wet middle, wet spread].

    The day is the unit. A patch's middle is the middle of its days' middles, and its spread has two
    parts: how much it varies within a day, which each patch shows for itself, and how much a patch's look
    moves from one day to the next, which no single patch has enough days to show and so is taken from all
    the chosen patches together.
    """
    edges = np.concatenate([[0], starts, [len(order)]])
    by_day = np.array([np.median(described[order[a:b]][:, chosen], axis=0) for a, b in zip(edges[:-1], edges[1:])])
    within = np.array([1.4826 * np.median(np.abs(described[order[a:b]][:, chosen] - by_day[i]), axis=0)
                       for i, (a, b) in enumerate(zip(edges[:-1], edges[1:]))])
    days = np.arange(len(edges) - 1)[:, None]
    out = []
    for side in (days < first_wet[None, :], days >= first_wet[None, :]):
        masked = np.where(side[:, :, None], by_day, np.nan)
        middle = np.nanmedian(masked, axis=0)
        between = 1.4826 * np.nanmedian(np.abs(masked - middle), axis=(0, 1))          # one figure for likeness, one for contrast
        inside = np.nanmedian(np.where(side[:, :, None], within, np.nan), axis=0)
        out += [middle.astype(np.float32), np.maximum(np.sqrt(inside ** 2 + between[None, :] ** 2), FLOORS).astype(np.float32)]
    return out


@dataclass
class Gauge:
    dry: np.ndarray            # the dry look, grey
    shape: tuple               # patches down and across
    where: np.ndarray          # which patches are used, counted along the rows
    below: np.ndarray          # for each, the level up to which it is known to have been dry
    above: np.ndarray          # and the level from which it is known to have been wet
    dry_middle: np.ndarray     # what each looks like dry: (patches used, 2)
    dry_spread: np.ndarray
    wet_middle: np.ndarray     # and wet
    wet_spread: np.ndarray
    anchors: np.ndarray        # patches that never change, to check the view is still this camera's
    anchor_like: float         # how like the dry look they were in the pictures learnt from
    learnt: tuple              # the lowest and highest level in the pictures learnt from
    pictures: int              # how many pictures it learnt from
    error: float = float("nan")    # 90% of the readings of days left out were within this
    left_out: tuple = ()       # (measured, read) for each picture given a level on a day left out

    FIELDS = ("dry", "where", "below", "above", "dry_middle", "dry_spread", "wet_middle", "wet_spread", "anchors")

    def reads(self):
        """The lowest and highest level it can tell apart, or None if it learnt nothing."""
        return (float(self.below.min()), float(self.above.max())) if len(self.where) else None

    def read(self, picture, trace=None):
        """The level in one picture."""
        nowhere = Level(False, float("nan"), float("-inf"), float("inf"), "unreadable")
        if np.asarray(picture).shape[:2] != self.dry.shape or len(self.where) == 0:
            return nowhere
        seen = describe(picture, self.dry).reshape(-1, len(FLOORS))
        if len(self.anchors) and float(np.median(seen[self.anchors, 0])) < ANCHOR_LOST * self.anchor_like:
            return nowhere                                            # moved, covered, or too dark to know
        x = seen[self.where]
        as_dry = (-0.5 * ((x - self.dry_middle) / self.dry_spread) ** 2 - np.log(self.dry_spread)).sum(axis=1)
        as_wet = (-0.5 * ((x - self.wet_middle) / self.wet_spread) ** 2 - np.log(self.wet_spread)).sum(axis=1)
        odds = np.exp(np.clip(as_wet - as_dry, -LIMIT, LIMIT))
        lowest, highest = self.reads()
        pad = 0.02 * (highest - lowest)
        grid = np.linspace(lowest - pad, highest + pad, GRID)
        under = np.clip((grid[:, None] - self.below[None, :]) / (self.above - self.below)[None, :], 0.0, 1.0)
        fit = np.log(under * odds[None, :] + 1.0 - under).sum(axis=1)
        if trace is not None:
            trace.update(grid=grid, fit=fit, odds=odds)
        best = np.flatnonzero(fit >= fit.max() - 1e-9)
        # Below its lowest step and above its highest the gauge has nothing to tell levels apart with. A
        # picture is only given a level if it is clearly neither.
        edge = EDGE * len(odds)
        as_good = fit >= fit.max() - edge                             # levels the picture cannot tell from the best
        if fit.max() - fit[0] < edge or grid[best[0]] <= lowest:
            level, reason = lowest, "below what was learnt"
        elif fit.max() - fit[-1] < edge or grid[best[-1]] >= highest:
            level, reason = highest, "above what was learnt"
        else:
            level, reason = float(0.5 * (grid[best[0]] + grid[best[-1]])), "ok"
        # Does that level explain the picture? Of the patches it puts clearly under or clearly clear,
        # the share that look it.
        wet, clear = self.above <= level, self.below >= level
        explained = float(((odds[wet] > 1.0).sum() + (odds[clear] < 1.0).sum()) / max(1, wet.sum() + clear.sum()))
        if explained < EXPLAINED:
            return Level(False, float("nan"), float("-inf"), float("inf"), "unreadable", explained)
        # Past its last step all it can give is a ceiling or a floor, and that is where the picture stops
        # fitting as well as it does beyond the step: the near end of what it cannot tell apart. The far
        # end of the step would claim more than the picture shows.
        if reason == "below what was learnt":
            ceiling = float(grid[np.argmin(as_good) - 1]) if not as_good.all() else highest
            return Level(False, ceiling, float("-inf"), ceiling, reason, explained)
        if reason == "above what was learnt":
            floor = float(grid[len(grid) - np.argmin(as_good[::-1])]) if not as_good.all() else lowest
            return Level(False, floor, floor, float("inf"), reason, explained)
        weight = np.exp(EVIDENCE * (fit - fit.max()))
        cumulative = np.cumsum(weight / weight.sum())
        low = float(grid[min(np.searchsorted(cumulative, 0.05), GRID - 1)])
        high = float(grid[min(np.searchsorted(cumulative, 0.95), GRID - 1)])
        if np.isfinite(self.error):
            low, high = min(low, level - self.error), max(high, level + self.error)
        return Level(True, level, low, high, "ok", explained)

    def save(self, path):
        """Everything needed to read a picture later, in one file of plain arrays."""
        np.savez_compressed(path, **{name: getattr(self, name) for name in self.FIELDS},
                            numbers=np.array([*self.shape, self.anchor_like, *self.learnt, self.pictures, self.error]))

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as kept:
            down, across, anchor_like, lowest, highest, pictures, error = kept["numbers"]
            return cls(kept["dry"], (int(down), int(across)), *(kept[name] for name in cls.FIELDS[1:]), float(anchor_like),
                       (float(lowest), float(highest)), int(pictures), float(error))


def with_fallback(reading, other):
    """One level for a picture from the gauge's reading and another method's level for it (or None).

    The gauge's level is used when it gave one. When it could only say below or above what it had learnt,
    the other method's level is used, kept on the gauge's side of that line. When the gauge had no answer,
    the other level stands as it is. Returns (level or None, "learnt", "other, held" or "other").
    """
    if reading.found:
        return reading.level, "learnt"
    if other is None:
        return None, None
    if reading.reason.startswith("below"):
        return min(other, reading.level), "other, held"
    if reading.reason.startswith("above"):
        return max(other, reading.level), "other, held"
    return other, "other"


def learn(pictures, levels, days=None, doubt=0.0, check=True):
    """A gauge for one camera from its pictures and the level measured in each.

    pictures: (count, rows, columns, 3), 0 to 255, every one the same view. levels: one number each.
    days: something that is the same for pictures taken in the same light, usually the date; left out,
    every picture is taken as its own day. doubt: how far out the measured levels may be, one figure or
    one a picture; a step is never taken as known more closely than that. With `check`, each day is left
    out in turn to measure how far out the gauge is, which takes as many times longer as there are days.
    """
    levels = np.asarray(levels, dtype=float)
    days = np.arange(len(levels)) if days is None else np.unique(np.asarray(days), return_inverse=True)[1]
    doubt = np.broadcast_to(np.asarray(doubt, dtype=float), levels.shape)
    dry = dry_look(pictures, levels)
    described = np.array([describe(picture, dry) for picture in pictures])
    shape = described.shape[1:3]
    described = described.reshape(len(levels), -1, len(FLOORS))
    order, starts, middles = _in_days(levels, days)
    edges = np.concatenate([[0], starts, [len(order)]])
    unsure = np.array([np.median(doubt[order[a:b]]) for a, b in zip(edges[:-1], edges[1:])])
    gain, first_wet = _steps(described, order, starts)
    span = float(levels.max() - levels.min())
    chosen = np.flatnonzero(gain >= GAIN)
    if len(chosen):
        dry_middle, dry_spread, wet_middle, wet_spread = _looks(described, order, starts, chosen, first_wet[chosen])
        moved = (np.abs(wet_middle - dry_middle) / np.sqrt(0.5 * (dry_spread ** 2 + wet_spread ** 2))).max(axis=1)
    else:
        dry_middle = dry_spread = wet_middle = wet_spread = np.zeros((0, len(FLOORS)), np.float32)
        moved = np.zeros(0)
    keep = moved >= APART
    # The height of a scene changes smoothly from one patch to the next. A patch whose step no neighbour
    # shares is a patch that changed with the weather.
    height = np.full(shape[0] * shape[1], np.nan)
    height[chosen[keep]] = 0.5 * (middles[first_wet[chosen[keep]] - 1] + middles[first_wet[chosen[keep]]])
    padded = np.pad(height.reshape(shape), 1, constant_values=np.nan)
    around = np.stack([padded[1 + dy:1 + dy + shape[0], 1 + dx:1 + dx + shape[1]]
                       for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)])
    with np.errstate(invalid="ignore"):
        agreeing = (np.abs(around - height.reshape(shape)[None]) <= AGREE * span).sum(axis=0).ravel()
    keep &= agreeing[chosen] >= NEIGHBOURS
    used = chosen[keep]
    # Patches that keep their pattern in every picture: if these stop looking like the dry look, the camera
    # has moved or something is in front of it.
    steady = np.flatnonzero((np.percentile(described[:, :, 0], 10, axis=0) >= ANCHOR_LIKE) & (gain < 0.5 * GAIN))
    anchor_like = float(np.median(described[:, steady, 0])) if len(steady) else float("nan")
    gauge = Gauge(dry, tuple(int(n) for n in shape), used, middles[first_wet[used] - 1] - unsure[first_wet[used] - 1],
                  middles[first_wet[used]] + unsure[first_wet[used]],
                  dry_middle[keep], dry_spread[keep], wet_middle[keep], wet_spread[keep], steady, anchor_like,
                  (float(levels.min()), float(levels.max())), len(levels))
    if check:
        pairs = []
        for day in np.unique(days):
            rest = days != day
            if len(np.unique(days[rest])) < 2 * DAYS_EACH_SIDE:
                continue
            without = learn([p for p, r in zip(pictures, rest) if r], levels[rest], days[rest], doubt[rest], check=False)
            for index in np.flatnonzero(~rest):
                reading = without.read(pictures[index])
                if reading.found:
                    pairs.append((float(levels[index]), reading.level))
        gauge.left_out = tuple(pairs)
        if len(pairs) >= 10:
            gauge.error = float(np.percentile([abs(read - measured) for measured, read in pairs], 90))
    return gauge
