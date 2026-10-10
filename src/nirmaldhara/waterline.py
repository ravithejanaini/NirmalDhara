"""Find the waterline on a vertical object without a vision model (METHOD.md C2, estimator 1).

The input is a narrow strip of the image running down a gauge, pillar or wall: object at the
top, water (if any) below. The question is one number, the row where the water starts, and how
sure we are of it.

It is answered in two stages.

Stage 1: where does the surface stop? Going down the strip, the surface is seen first, in some
light. The light is a hidden state: a gain, 1 at the top, that may drift from row to row (a
gradient) or change outright (a shadow edge, a wet stain). At some row the surface may give way
to something else, which lasts to the bottom of the strip. The something else has a hidden
brightness that may drift in the same way, and each of its rows is either quiet (still and
featureless) or busy (anything). Both halves are hidden Markov chains, and the row where one
hands over to the other is what we are after. "It never hands over" is one of the outcomes.

The two halves are given equally sharp models of brightness on purpose. A hypothesis that may
re-light every row as it likes explains anything; here the surface must follow the dry view
times a slowly varying gain, the rest must follow a slowly varying brightness, and neither gets
credit the other could not earn.

What each row is judged on. The top fifth of the strip is taken to be dry, so it shows what dry
looks like for this camera, in this light, with this noise, right now. Against that:

    level      is the row as bright as the dry view, times the gain, predicts?
    pattern    does the row carry the texture the dry view has there, and how strongly? The
               expected strength is worked out row by row from the dry view's own texture and
               the noise, so a plain patch of wall is simply uninformative, not a false alarm
    texture    is there as much texture in the row as the surface should show: no less (it has
               been covered) and no more (something has appeared)?
    flicker    does the row change between frames more than the camera's own noise and shake
               explain?
    colour     has the row's colour moved off the surface's own colour? Shadows scale colour;
               water tints it

Every likelihood carries a small flat part, so glare, a rain streak or a painted mark costs a
bounded amount. Columns that do not match the dry view in the rows known to be dry (a pole or a
cable in front) are dropped before anything is measured.

Stage 2: is what replaced the surface water? Rows that move are water. Rows that are still and
featureless are water. Rows that are still and textured are water only if the texture is the
mirror image of the rows the same distance above the line. Still texture that nothing explains
is an object: a parked vehicle, a box. Then the view is reported blocked and no line is given.
Still water needs one more step. Just below the line, a mirror image of a surface looks like the
surface, so stage 1 runs on too far; the line is then the row about which the rows below really
are a mirror image, and stage 2 looks for it.

Before any of this the dry view is shifted, blurred and re-lit to match the frame, judged on the
rows known to be dry: rain, a soft focus or a trembling camera smear a frame, and a sharp dry
view would no longer predict it.

What comes out is a distribution: the row, a 90% interval, and the probabilities of water,
blocked and dry. The interval's width is set by a conformal calibration, so that it holds 90% of
the time on scenes it was not fitted to. A sequence of readings is filtered through time with a
third hidden Markov model, because water rises and falls slowly.

Without a dry view there are two weaker modes. A short clip can still use flicker. A single photo
has only its own appearance and cannot tell a waterline from a painted line; it is here to show
the limit.

Measured on rendered scenes (scripts/simulate_waterline.py), on real video with a made line
(scripts/real_strip_test.py), and on a real flood with measured levels
(scripts/river_camera_test.py). On the real flood it was 13 cm out, typically, at one river lock,
and of no use at another camera: tens of centimetres, where the renders had said fractions of one.
It has not been measured on a street.
"""

from dataclasses import dataclass

import numpy as np

DRY_TOP = 0.2              # share of the strip, from the top, taken as known dry
MIN_WET = 8                # fewer rows of water than this at the foot of the strip are not reported
SHAKE = 4                  # rows of vertical camera shake searched when lining up with the dry view
SLACK = 0.15               # how far a dry pattern's strength may be from the predicted one, as a share
STEP = 0.077               # the grid of gains and of brightnesses, in log: each is 8% more than the last
GAINS = np.exp(STEP * np.arange(-14, 11))     # 0.34 to 2.16; number 14 is exactly 1
LEVEL_KERNEL = 0.04        # how closely a row's brightness must match a prediction, as a share
P_DRIFT = 0.04             # chance, per row, that the light or the brightness moves one step
P_EDGE = 0.001             # chance, per row, that it changes outright
P_SWITCH = 0.05            # chance, per row, that what replaced the surface turns from quiet to busy or back
TEXTURE_SCALE = 0.45       # how far a featureless row's texture may sit above pure noise, in log
SURFACE_TEXTURE = 0.8      # how far the surface's texture may sit from what the dry view predicts, in log
UNEXPLAINED = float(np.log(1 / 16))   # what a row costs when nothing predicts its texture
FLAT = 0.02                # share of every likelihood that is flat: nothing is ever impossible
STILL_FLAT = 0.01          # the same for flicker on a still surface: wild flicker is seldom a mistake
MIN_KNOWN = 12             # rows known to be dry, and in one light, needed to calibrate on
QUANTISED = 0.5 / 255      # an 8-bit picture cannot show less noise than this
OFFSET_EARNS = 0.8         # an offset is fitted only if it cuts the squared miss to this share
COLOUR_SHARE = 0.5         # share of the colour wander of rows still showing the pattern that is a floor under the dry rows' own
MISALIGNED = 0.25          # pixels by which the dry view is always taken to be out of line, at least
EVIDENCE = 0.35            # rows are not independent evidence: the weights of all outcomes are tempered by this
BAD_COLUMN = 4.0           # a column this many times worse than typical in the dry rows is dropped
MIN_COLUMNS = 0.5          # with fewer columns than this left, the view is blocked
TOP_MATCH = 0.1            # the dry rows must show at least this share of their enrolled pattern
TOP_LIKENESS = 0.5         # and be at least this share as like the dry view as their texture and noise allow
SINGLE_LIKENESS = 0.1      # with one frame there is no measure of noise: the dry rows' texture must be this like the dry view's
BLUR = ((1, 2, 3, 4, 5, 6), (1, 2, 3))   # box blurs tried on the dry view: rows, then columns
TREMBLE = 2                # pixels each way searched when the frames of a reading are lined up with each other
KNOWN_MARGIN = -0.5        # on the rows known to be dry, anything else may not beat the surface by this much a row, in log
MIRROR_BACK = 40           # rows above stage 1's line searched for the line of a mirror image
MOVING = 3.0               # flicker this far above the dry level means the row is moving
REGION_MOVING = 1.0        # and a region whose typical row is this far above it is moving as a whole
PLAIN = 1.0                # texture within this much of pure noise, in log, counts as featureless
OBJECT_PRIOR = 0.05        # chance that what replaced the surface is an object, before looking
OBJECT_TEMPER = 0.3        # rows of one object are not independent evidence
# What a row of water, and a row of an object, looks like: moving, still and plain, still and mirrored,
# still with texture nothing explains. A fifth kind, a row whose mirror image would lie above the top
# of the strip, cannot be checked and says nothing.
WATER_ROWS = np.array([0.50, 0.30, 0.15, 0.05, 1.0])
OBJECT_ROWS = np.array([0.02, 0.25, 0.03, 0.70, 1.0])
WAVE_ROWS = 1.5            # the line itself is not sharp: waves, a meniscus
FOUND_AT = 0.5             # probability of water needed to report a line
LOW_LIGHT = 15.0           # brightness of the dry rows over the noise, below which it counts as low light
MIN_SPREAD = 1.0           # rows; the interval is never built on a spread smaller than this
# Half-width of the 90% interval, in spreads: the 90% point of |error| / spread on 120 rendered scenes of
# each design condition (scripts/simulate_waterline.py --calibrate, seed 11), checked on other scenes.
# "normal" came out below 1 and is held at 1. On real pictures these have to be fitted again.
QUANTILE = {"normal": 1.0, "soft": 1.50, "low light": 2.50, "tracked": 1.14}
DRIFT_ROWS = 2.0           # how far the waterline may move between readings, as a standard deviation
JUMP = 0.02                # chance per reading that the line is somewhere new
MISREAD = 0.05             # chance that a reading is simply wrong, however sure it is
CLIP_APPEARANCE = 0.05     # weight of the look of the image when there is no dry view, only flicker
PHOTO_TEMPER = 0.08        # the single-photo model is far less sure of itself
PHOTO_EVIDENCE = 40.0      # log Bayes factor for "two materials" a single photo needs


@dataclass(frozen=True)
class Waterline:
    found: bool
    row: float                  # posterior mean; rows from the top of the strip
    low: float                  # the 90% interval
    high: float
    confidence: float           # probability that there is water in the strip
    reason: str                 # "ok", "dry", "occluded", "unsure", "unreadable", "held: ..."
    log_posterior: np.ndarray   # over rows, given water
    spread: float = 0.0         # posterior standard deviation, rows
    group: str = "normal"       # which calibration applies
    p_blocked: float = 0.0
    p_dry: float = 0.0


def _nothing(rows, reason, p_blocked=0.0, p_dry=0.0, group="normal"):
    return Waterline(False, float("nan"), 0.0, float(rows), 0.0, reason, np.full(rows, -np.log(rows)),
                     0.0, group, p_blocked, p_dry)


def _lum(image):
    return image[..., :3].mean(axis=-1)


def _robust(values):
    """Centre and spread, not moved by a few odd values."""
    centre = float(np.median(values))
    return centre, 1.4826 * float(np.median(np.abs(values - centre)))


def _log_normal(x, mean, var):
    return -0.5 * ((x - mean) ** 2 / var + np.log(2 * np.pi * var))


def _with_flat(log_density, flat, share=FLAT):
    """Mix a likelihood with a flat one, so that no observation is impossible."""
    return np.logaddexp(np.log1p(-share) + log_density, np.log(share * flat))


def _shift_rows(image, shift):
    """Move the picture down by `shift` rows, repeating the edge row."""
    if shift == 0:
        return image
    out = np.empty_like(image)
    if shift > 0:
        out[shift:], out[:shift] = image[:-shift], image[:1]
    else:
        out[:shift], out[shift:] = image[-shift:], image[-1:]
    return out


def _shift(image, down, across):
    """Move the picture down and across by whole pixels, repeating the edges."""
    return np.swapaxes(_shift_rows(np.swapaxes(_shift_rows(image, down), 0, 1), across), 0, 1)


def _fit(x, y):
    """How the dry view's brightness maps to the frame's: y = a x + b, by least squares.

    A gain alone (b = 0) unless an offset clearly earns its place, as haze does. The rows fitted on
    are a small part of the strip and may span a narrow range of brightness, and a line fitted there
    is then used on rows far outside it. A wrong gain is something the chain down the strip can absorb,
    one step at a time; a wrong offset is not.

    Plain least squares on purpose, with no pixel left out. On a gauge the marks are a small share of
    the pixels and carry all the information, and a fit that discards what it misses discards exactly
    those. Rows and columns that do not belong (a shadow, a pole) are left out by the caller, whole.
    """
    x, y = np.ravel(x).astype(np.float64), np.ravel(y).astype(np.float64)
    power = float((x * x).sum())
    if power < 1e-9:
        return 1.0, 0.0
    gain = float((x * y).sum() / power)
    alone = float(((y - gain * x) ** 2).sum())
    spread = float(x.var())
    if spread > 1e-7:
        a = float(((x - x.mean()) * (y - y.mean())).mean() / spread)
        b = float(y.mean() - a * x.mean())
        if 0.02 < a < 20 and float(((y - a * x - b) ** 2).sum()) < OFFSET_EARNS * alone:
            return a, b
    return (gain if 0.02 < gain < 20 else 1.0), 0.0


def _box(image, down, across):
    """Average over a box `down` rows by `across` columns, repeating the edges."""
    out = image
    for axis, width in ((0, down), (1, across)):
        if width > 1:
            pad = [(0, 0)] * out.ndim
            pad[axis] = ((width - 1) // 2 + 1, width // 2)
            total = np.cumsum(np.pad(out, pad, mode="edge"), axis=axis, dtype=np.float64)
            upper, lower = [slice(None)] * out.ndim, [slice(None)] * out.ndim
            upper[axis], lower[axis] = slice(width, None), slice(0, -width)
            out = (total[tuple(upper)] - total[tuple(lower)]) / width
    return out


def _smooth(p, sigma):
    reach = int(3 * sigma) + 1
    kernel = np.exp(-0.5 * (np.arange(-reach, reach + 1) / sigma) ** 2)
    out = np.convolve(p, kernel / kernel.sum(), mode="same")
    return out / out.sum()


def _describe(p, confidence, group, reason="ok", p_blocked=0.0, p_dry=0.0, quantile=None):
    """Turn a distribution over rows into the estimate and its calibrated 90% interval."""
    p = p / p.sum()
    index = np.arange(len(p))
    row = float((p * index).sum())
    spread = float(np.sqrt((p * (index - row) ** 2).sum()))
    half = (QUANTILE[group] if quantile is None else quantile) * max(spread, MIN_SPREAD)
    return Waterline(True, row, max(0.0, row - half), min(len(p) - 1.0, row + half), confidence, reason,
                     np.log(p + 1e-300), spread, group, p_blocked, p_dry)


def _decide(p_end, lines, object_chance, group, rows, fuzz=WAVE_ROWS):
    """From the chance that the surface stops, where (log weights over rows), and the chance that what
    replaced it is an object, to a result: a line, or the reason there is none."""
    p_water, p_blocked, p_dry = p_end * (1 - object_chance), p_end * object_chance, 1 - p_end
    if p_water >= FOUND_AT:
        p = _smooth(np.exp(lines - np.max(lines)), fuzz)
        return _describe(p, p_water, group, p_blocked=p_blocked, p_dry=p_dry)
    reason = "occluded" if p_blocked >= 0.5 else "dry" if p_dry >= 0.5 else "unsure"
    return _nothing(rows, reason, p_blocked, p_dry, group)


def _moves(count, p_leave=0.0):
    """How a gain or a brightness on the log grid changes from one row to the next: it stays, drifts
    to a neighbour, or jumps anywhere."""
    move = np.full((count, count), P_EDGE / count)
    index = np.arange(count)
    move[index, index] += 1 - P_DRIFT - P_EDGE - p_leave
    move[index[:-1], index[1:]] += P_DRIFT / 2
    move[index[1:], index[:-1]] += P_DRIFT / 2
    return move


def _down(emit, p_leave):
    """Follow the surface down the strip through every light it may be in.

    emit: (gains, rows). Returns, for each row, the log weight of "every row down to here is the surface".
    """
    log_move = np.log(_moves(len(emit), p_leave))
    start = int(np.argmin(np.abs(np.log(GAINS))))
    # Most likely the light at the very top is the light the calibration found; it need not be.
    alpha = emit[:, 0] + np.log(np.where(np.arange(len(emit)) == start, 0.5, 0.5 / (len(emit) - 1)))
    above = np.empty(emit.shape[1])
    above[0] = np.logaddexp.reduce(alpha)
    for row in range(1, emit.shape[1]):
        alpha = emit[:, row] + np.logaddexp.reduce(alpha[:, None] + log_move, axis=0)
        above[row] = np.logaddexp.reduce(alpha)
    return above


def _up(emit, first):
    """Follow what replaced the surface, from the bottom of the strip up to row `first`.

    emit: (states, rows), quiet states then busy ones. Returns, for each row from `first` down, the log
    weight of "from here to the bottom is not the surface".
    """
    half = len(emit) // 2
    log_move = np.log(np.kron(np.array([[1 - P_SWITCH, P_SWITCH], [P_SWITCH, 1 - P_SWITCH]]), _moves(half)))
    rows = emit.shape[1]
    below = np.full(rows, -np.inf)
    beta = emit[:, -1].copy()
    below[-1] = np.logaddexp.reduce(beta) - np.log(len(emit))
    for row in range(rows - 2, first - 1, -1):
        beta = emit[:, row] + np.logaddexp.reduce(log_move + beta[None, :], axis=1)
        below[row] = np.logaddexp.reduce(beta) - np.log(len(emit))
    return below


def _flicker(frame_lum, still_lum, dry, good=None):
    """How much each row changes between frames, in units of what a dry row with its texture should.

    Returns (z, per-pixel noise). z is 0 +- 1 on dry rows. A camera that trembles makes textured rows
    flicker more, so the dry level is fitted as noise plus shake times the row's own gradients.
    """
    select = slice(None) if good is None else good
    # Across the row, a mean without the highest and lowest tenth: a rain streak or a glint in a few
    # columns does not count, and the result is not as coarse as a median of 8-bit differences.
    change = np.sort(np.abs(np.diff(frame_lum, axis=0))[:, :, select], axis=2)
    trim = max(1, change.shape[2] // 10)
    steps = change[:, :, trim:-trim].mean(axis=2)
    # The lower quartile over time: water flickers in every step, a vehicle driving through only in some.
    flicker = np.percentile(steps, 25, axis=0)
    down, across = np.zeros_like(still_lum), np.zeros_like(still_lum)
    down[1:-1] = (still_lum[2:] - still_lum[:-2]) / 2
    across[:, 1:-1] = (still_lum[:, 2:] - still_lum[:, :-2]) / 2
    gradient = (down ** 2 + across ** 2)[:, select].mean(axis=1)
    top = slice(SHAKE, dry)
    design = np.stack([np.ones(dry - SHAKE), gradient[top]], axis=1)
    noise2, shake2 = np.linalg.lstsq(design, flicker[top] ** 2, rcond=None)[0]
    if shake2 < 0 or noise2 <= 0:
        noise2, shake2 = float(np.mean(flicker[top] ** 2)), 0.0
    expected = np.sqrt(noise2 + shake2 * gradient)
    spread = max(_robust((flicker - expected)[top])[1], 0.05 * float(np.median(expected[top])), QUANTISED / 4)
    # Less flicker than expected is not evidence of anything: only the excess is kept.
    return np.maximum(flicker - expected, 0.0) / spread, float(np.sqrt(noise2))


def _still(z):
    """Log-likelihood of each row's flicker if the row does not move."""
    return _with_flat(_log_normal(z, 0.0, 1.0), 1 / 150, STILL_FLAT)


def _mirrored(gram, own_row, floor, line):
    """For each row below `line`: the log, above noise, of the texture left once the row the same
    distance above the line has explained what it can, and whether there is such a row in the strip.
    Still water shows the surface upside down."""
    rows = len(own_row)
    y = np.arange(line, rows)
    m = 2 * line - 1 - y
    valid = m >= 0
    cross, source = gram[y[valid], m[valid]], own_row[m[valid]]
    usable = (source > 1.5 * floor[m[valid]]) & (cross > 0) & (cross < 1.3 * source)
    left = own_row[y].copy()
    left[valid] -= np.where(usable, cross ** 2 / source, 0.0)
    return np.log(np.maximum(left, 1e-12) / floor[y]), valid


def _kinds(line, z, texture, gram, own_row, floor, moving_at):
    """What each row is, from three below `line` down (the waves at the line are left out):
    0 moving, 1 still and plain, 2 still and a mirror image, 3 still with texture nothing explains,
    4 a mirror image could not be checked."""
    start = line + 3
    # Faint ripples show as a whole region flickering a little, not as any one row flickering a lot.
    moving = (z[start:] > moving_at[0]) | (np.median(z[start:]) > moving_at[1])
    plain = texture[start:] < PLAIN
    left, checked = _mirrored(gram, own_row, floor, line)
    return np.where(moving, 0, np.where(plain, 1, np.where(~checked[3:], 4, np.where(left[3:] < PLAIN, 2, 3))))


def _replaced_by(ends, dry, z, texture, gram, own_row, floor):
    """Stage 2: what lies below the line. ends: stage 1's log weights over rows.

    Returns (chance it is an object, log weights over rows, adjusted where a mirror image fixes the
    line better than stage 1 could).
    """
    rows, line = len(texture), int(np.argmax(ends))
    last = rows - MIN_WET
    if z is None or line + 3 >= rows - 4:
        return OBJECT_PRIOR, ends
    # What counts as moving is set by the rows known to be dry, which do not move.
    moving_at = (max(MOVING, float(np.percentile(z[SHAKE:dry], 99)) + 1.0),
                 max(REGION_MOVING, float(np.percentile(z[SHAKE:dry], 90))))
    found = _kinds(line, z, texture, gram, own_row, floor, moving_at)

    def for_water(k):
        """How far the rows below line k favour water over an object, in log odds."""
        kind = _kinds(k, z, texture, gram, own_row, floor, moving_at)
        # A row this line cannot check keeps what stage 1's line found for it: a line has to explain
        # the rows below it, not put them out of reach.
        if k < line:
            kind[line - k:] = np.where(kind[line - k:] == 4, found, kind[line - k:])
        elif k > line:
            kind = np.where(kind == 4, found[k - line:], kind)
        return np.log((1 - OBJECT_PRIOR) / OBJECT_PRIOR) + OBJECT_TEMPER * float(np.log(WATER_ROWS / OBJECT_ROWS)[kind].sum())

    chance = lambda odds: float(1 / (1 + np.exp(np.clip(odds, -500, 500))))      # noqa: E731
    near = {k: for_water(k) for k in range(max(dry, line - 3), min(line + 3, last) + 1)}
    if max(near.values()) > 0:
        # Water. A mirror image fixes the line to the row; let it, within the rows either side.
        lines = ends.copy()
        for k, odds in near.items():
            lines[k] += odds - near[line]
        return chance(near[int(np.argmax(lines))]), lines
    # Still, textured, and not a mirror image about any line here. Just below the line a mirror image
    # of a surface looks like the surface, so stage 1 overruns by as far as the surface resembles
    # itself. Is this a mirror image about a line a little higher up?
    higher = {k: for_water(k) for k in range(max(dry, line - MIRROR_BACK), line - 3)}
    if higher and max(higher.values()) > 0:
        lines = np.full(rows, -np.inf)
        for k, odds in higher.items():
            lines[k] = ends[k] + odds
        return chance(higher[int(np.argmax(lines))]), lines
    return chance(near[line]), ends


def _with_reference(frames, still, reference, ref_noise, tremble=0.0, trace=None):
    rows = still.shape[0]
    dry = max(2 * SHAKE + 4, int(rows * DRY_TOP))
    last = rows - MIN_WET
    top = np.arange(SHAKE, dry)                               # the rows to calibrate on
    still_lum, ref_lum = _lum(still), _lum(reference)

    # Line the dry view up with this frame: the blur, shift and brightness that best explain the dry rows.
    tried = []
    for down in BLUR[0]:
        for across in BLUR[1]:
            soft, best = _box(ref_lum, down, across), None
            for shift in sorted(range(-SHAKE, SHAKE + 1), key=abs):
                moved = _shift_rows(soft, shift)
                a, b = _fit(moved[top], still_lum[top])
                miss = float(np.mean((still_lum[top] - (a * moved[top] + b)) ** 2))     # not a median: see _fit
                if best is None or miss < 0.97 * best[0]:     # a larger shift has to be clearly better
                    best = (miss, shift, a)
            tried.append((down * across, down, across) + best)
    # Blurring the dry view also quiets its own noise, which lowers the miss whether or not the frame is
    # blurred. Take that part out before comparing, and let more blur win only if it is clearly better.
    sharp = tried[0]
    frame_noise = max(sharp[3] - sharp[5] ** 2 * ref_noise, 0.0)
    chosen, least = sharp, sharp[3] - frame_noise - sharp[5] ** 2 * ref_noise
    for candidate in sorted(tried[1:]):
        excess = candidate[3] - frame_noise - candidate[5] ** 2 * ref_noise / candidate[0]
        if excess < least - 0.03 * sharp[3]:
            chosen, least = candidate, excess
    _, down, across, _, shift, _ = chosen
    reference = _shift_rows(_box(reference, down, across), shift)
    ref_lum, ref_noise = _lum(reference), ref_noise / (down * across)

    # The rows taken as dry may not all be in one light: a shadow's edge can fall among them. Calibrate
    # on those that agree with most; the chain handles the rest like any other row.
    a, b = _fit(ref_lum[top], still_lum[top])
    row_miss = (still_lum[top] - (a * ref_lum[top] + b)).mean(axis=1)
    centre, spread = _robust(row_miss)
    agree = np.abs(row_miss - centre) <= max(4 * spread, 0.02)
    if MIN_KNOWN <= agree.sum() < len(top):
        top = top[agree]
        a, b = _fit(ref_lum[top], still_lum[top])

    # Drop columns that do not show the surface even where it must be dry: something is in front.
    column_miss = np.abs(still_lum[top] - (a * ref_lum[top] + b)).mean(axis=0)
    typical = float(np.median(column_miss))
    good = column_miss <= max(BAD_COLUMN * typical, typical + 0.02)
    if good.mean() < MIN_COLUMNS:
        return _nothing(rows, "occluded", p_blocked=1.0)
    a, b = _fit(ref_lum[top][:, good], still_lum[top][:, good])
    count = int(good.sum())
    s, r = still_lum[:, good].astype(np.float64), ref_lum[:, good].astype(np.float64)
    # A saturated pixel shows no noise at all, so what the frames show from one to the next, anywhere in
    # the strip, sets a floor under the noise that is measured further down.
    least_noise = QUANTISED
    if len(frames) >= 3:
        lum = _lum(frames)[:, :, good]
        unsaturated = (lum.min(axis=0) > 0.02) & (lum.max(axis=0) < 0.98)
        if unsaturated.sum() > 50:
            quietest = float(np.percentile(np.abs(np.diff(lum, axis=0)).mean(axis=0)[unsaturated], 20))
            least_noise = max(least_noise, 0.4 * quietest / 1.128)   # the median of the frames is that much quieter than one
    # With enough noise allowed, anything fits. So before trusting the fit: are the rows taken as dry as
    # like the dry view as they should be, given its texture and the noise the frames show from one to
    # the next? If not, this is not the surface that was enrolled, or something stands in front of it.
    if len(frames) >= 3:
        between = float(np.median(np.abs(np.diff(_lum(frames)[:, top][:, :, good], axis=0)))) / 0.954
        still_noise = 1.2533 * between / np.sqrt(2 * len(frames))
        pattern = a * float(np.sqrt(max(r[top].var() - ref_noise, 0.0)))
        should = pattern / np.sqrt(pattern ** 2 + still_noise ** 2 + 1e-12)
        does = float(np.corrcoef(r[top].ravel(), s[top].ravel())[0, 1]) if r[top].std() > 0 and s[top].std() > 0 else 0.0
        if should > 0.3 and does < TOP_LIKENESS * should:
            return _nothing(rows, "occluded", p_blocked=1.0)
    else:
        # One frame gives no measure of noise to hold the likeness against. What can still be asked is that
        # the texture of the dry rows, with each row's own brightness taken out, is at least faintly the dry
        # view's. Where the dry view has no texture to speak of there is nothing to ask.
        was, now = r[top] - r[top].mean(axis=1, keepdims=True), s[top] - s[top].mean(axis=1, keepdims=True)
        if was.std() > 1.5 * np.sqrt(ref_noise):
            alike = float((was * now).sum() / np.sqrt((was * was).sum() * (now * now).sum() + 1e-12))
            if alike < SINGLE_LIKENESS:
                return _nothing(rows, "occluded", p_blocked=1.0)
    # Noise is not the same everywhere. A fraction of a pixel out of line, or a codec, misses by more
    # where the picture changes faster. So the miss is a constant plus a share of the dry view's own
    # gradients, fitted on the rows known to be dry; from here on each row has its own noise.
    lean_down, lean_across = np.zeros_like(r), np.zeros_like(r)
    lean_down[1:-1] = (r[2:] - r[:-2]) / 2
    lean_across[:, 1:-1] = (r[:, 2:] - r[:, :-2]) / 2
    steep = a ** 2 * (lean_down ** 2 + lean_across ** 2).mean(axis=1)
    row_miss2 = ((s[top] - (a * r[top] + b)) ** 2).mean(axis=1)
    typical_miss2, typical_steep = float(np.median(row_miss2)), float(np.median(steep[top]))
    slip2 = MISALIGNED ** 2
    if steep[top].std() > 0.3 * steep[top].mean() > 0:        # only when the dry rows differ enough to tell the two apart
        slip2 = max(slip2, float(np.linalg.lstsq(np.stack([np.ones(len(top)), steep[top]], axis=1), row_miss2, rcond=None)[0][1]))
    slip2 = min(slip2, typical_miss2 / max(typical_steep, 1e-12))            # never more than all of the miss
    noise = max(float(np.sqrt(max(typical_miss2 - slip2 * typical_steep, 0.0))), least_noise)   # the constant part
    noise_row = np.sqrt(noise ** 2 + slip2 * steep)
    floor = (count - 1) * noise_row ** 2                      # the texture a row of pure noise has, row by row

    # Level: each row's brightness, and the surface's share of what the dry view predicts for it.
    level, surface = s.mean(axis=1), a * r.mean(axis=1)
    level_noise = max(_robust((level - surface - b)[top])[1], 0.5 * noise / np.sqrt(count))
    level_var = level_noise ** 2 + (LEVEL_KERNEL * level) ** 2
    # Which calibration applies: the detector knows when the light was low and when the picture was soft.
    soft = down * across > 1 or tremble > 0.3
    group = "low light" if float(level[top].mean()) / noise < LOW_LIGHT else "soft" if soft else "normal"

    # Pattern and texture, row by row, with each row's own mean taken out.
    s_c, r_c = s - level[:, None], r - r.mean(axis=1, keepdims=True)
    gram = s_c @ s_c.T
    own_row = np.maximum(np.diag(gram), 1e-12)                # the texture each row shows now
    energy = np.maximum((r_c * r_c).sum(axis=1), 1e-12)       # and the texture the dry view has there
    real = np.clip(1 - (count - 1) * ref_noise / energy, 0.0, 1.0)   # the share of that which is not the dry view's own noise
    expected = a * real * np.sqrt(energy) / noise_row         # how strongly the pattern should show if the row is dry
    q = (r_c * s_c).sum(axis=1) / (noise_row * np.sqrt(energy))   # and how strongly it does
    telling = expected[top] > 3
    if telling.sum() >= 5:
        match = float(np.clip(np.median(q[top][telling] / expected[top][telling]), 0.02, 1.3))
        if match < TOP_MATCH:                                 # the part that must be dry is not what was enrolled
            return _nothing(rows, "occluded", p_blocked=1.0, group=group)
        expected = expected * match                           # blur and haze weaken every pattern alike
    # Blur and compression make neighbouring pixels move together, which widens q. Learn by how much.
    widen = max(1.0, float(np.median(((q - expected) ** 2 / (1 + (SLACK * expected) ** 2))[top])) / 0.455)
    flat_q = 1 / (2 * (expected + 20))
    texture = np.log(own_row / floor)
    surface_texture = a ** 2 * real * energy                  # what the surface should add to a row's texture
    kept = surface_texture[top] > floor[top]
    share = (own_row - floor) / np.maximum(surface_texture, 1e-12)
    keeps = float(np.clip(np.median(share[top][kept]), 0.05, 1.5)) if kept.sum() >= 5 else 1.0   # blur takes texture away too

    # Flicker and colour, when the frames allow them.
    z, still_row, busy_row = None, np.zeros(rows), np.zeros(rows)
    if len(frames) >= 3:
        z, _ = _flicker(_lum(frames), still_lum, dry, good)
        still_row = _still(z)
        busy_row = np.log(0.3 * np.exp(_log_normal(z, 0.0, 1.5 ** 2)) + 0.7 / 153)   # anything from still to wild
    # Each channel is the brightness fit times one number of its own (the white balance may have moved).
    # No line is fitted per channel: on rows of another colour it would be far outside what it was fitted on.
    seen = np.stack([still[:, good, k].mean(axis=1) for k in range(3)], axis=1)
    told = np.stack([a * reference[:, good, k].mean(axis=1) + b for k in range(3)], axis=1)
    balance = seen[top].mean(axis=0) / np.maximum(told[top].mean(axis=0), 1e-6)
    off = seen - told * balance
    surface_colour = (told - b) * balance
    length = np.linalg.norm(surface_colour, axis=1, keepdims=True)
    along = np.where(length > 1e-6, surface_colour / np.maximum(length, 1e-6), 0.0)
    off = off - (off * along).sum(axis=1, keepdims=True) * along          # shadows only move colour along itself
    moved = (off ** 2).sum(axis=1)
    # How far colour wanders on a dry row is learnt on the rows known to be dry. Rows of another material
    # wander more, with nothing having changed. So rows further down that still carry the dry view's
    # pattern, and are therefore still the surface, have a say too: half of what is typical of them is a
    # floor. Water is left out of that by construction, since its pattern is gone.
    still_surface = (expected > 3) & (q > 0.5 * expected)
    still_surface[:dry] = False
    wander = float(np.median(moved[still_surface])) if still_surface.sum() >= 10 else 0.0
    scale = max(float(np.median(moved[top])), COLOUR_SHARE * wander) / 1.386
    coloured = scale > 1e-12
    c2 = (off ** 2).sum(axis=1) / scale if coloured else np.zeros(rows)
    flat_c = 1 / (np.pi * 40 ** 2)
    any_colour = np.log(np.maximum(np.exp(-c2 / 24.5) / (24.5 * np.pi), flat_c)) if coloured else np.zeros(rows)

    # The surface, at every gain: brightness, pattern and texture all scaled by the one gain.
    gain = GAINS[:, None]
    emit = (_with_flat(_log_normal(level[None, :], b + gain * surface[None, :], level_var[None, :]), 1.0)
            + _with_flat(_log_normal(q[None, :], gain * expected[None, :],
                                     widen * (1 + (SLACK * gain * expected[None, :]) ** 2)), flat_q[None, :])
            + still_row[None, :])
    predicted = np.log1p(gain ** 2 * keeps * surface_texture[None, :] / floor)
    emit = emit + np.log((1 - FLAT) * np.exp(-(np.maximum(texture, 0.0)[None, :] - predicted) ** 2 / (2 * SURFACE_TEXTURE ** 2))
                         + FLAT * np.exp(UNEXPLAINED))
    if coloured:
        same_light = np.abs(np.log(gain)) < 2 * STEP          # only an unchanged light pins the colour down
        tight = _with_flat(-c2[None, :] / 2 - np.log(2 * np.pi), flat_c)
        emit = emit + np.where(same_light, tight, _with_flat(-c2[None, :] / 24.5 - np.log(24.5 * np.pi), flat_c))
    p_leave = 1.0 / rows
    above = _down(emit, p_leave)

    # What replaced the surface, at every brightness: its pattern is gone and its colour is free.
    reflected = np.where((q >= -1) & (q <= expected + 1), 0.2 / (expected + 2), 0.0)
    own_var = np.maximum(1.0, own_row / floor)                # water and vehicles have texture of their own
    gone = _with_flat(np.log(0.8 * np.exp(_log_normal(q, 0.0, widen * (own_var + (0.05 * expected) ** 2)))
                             + reflected + 1e-300), flat_q)
    low_level = max(0.004, float(np.percentile(level[dry:], 1)))
    steps = min(64, int(np.log(max(float(np.percentile(level[dry:], 99)), low_level) / low_level) / STEP) + 2)
    brightness = low_level * np.exp(STEP * np.arange(steps))
    as_bright = _with_flat(_log_normal(level[None, :], brightness[:, None], level_var[None, :]), 1.0)
    plain = np.log((1 - FLAT) * np.exp(-np.maximum(texture, 0.0) ** 2 / (2 * TEXTURE_SCALE ** 2)) + FLAT * np.exp(UNEXPLAINED))
    quiet = gone + any_colour + still_row + plain
    busy = gone + any_colour + busy_row + UNEXPLAINED
    other = np.concatenate([as_bright + quiet[None, :], as_bright + busy[None, :]])
    # A check on the whole method: where the answer is known, does it at least not prefer something else?
    # A plain surface and still water of the same brightness are honestly close; a clear miss is not.
    if float(np.mean(emit[:, top].max(axis=0) - other[:, top].max(axis=0))) < KNOWN_MARGIN:
        return _nothing(rows, "unreadable", group=group)
    below = _up(other, dry)

    ends = np.full(rows, -np.inf)
    ends[dry:last + 1] = EVIDENCE * (above[dry - 1:last] + np.log(p_leave) + below[dry:last + 1])
    all_ends, never = np.logaddexp.reduce(ends), EVIDENCE * above[-1]
    p_end = float(np.exp(all_ends - np.logaddexp(all_ends, never)))
    object_chance, lines = _replaced_by(ends, dry, z, texture, gram, own_row, floor)
    if trace is not None:                                     # what the reading rested on, for whoever asks
        trace.update(level=level, predicted=b + surface, level_noise=level_noise, q=q, expected=expected, widen=widen,
                     texture=texture, texture_predicted=np.log1p(keeps * surface_texture / floor), flicker=z, colour=c2,
                     noise=noise, blur=(down, across), shift=shift, calibrated_on=top, surface=emit, other=other,
                     ends=ends, never=never, columns=good, noise_row=noise_row)
    # The line is only as sharp as the picture: waves, a camera that trembled, a soft focus.
    fuzz = float(np.sqrt(WAVE_ROWS ** 2 + tremble ** 2 + (down ** 2 - 1) / 12))
    return _decide(p_end, lines, object_chance, group, rows, fuzz)


def _register(frames, search=TREMBLE):
    """Line the frames of one reading up with each other, on the top fifth of the strip: whole-pixel
    shifts that best match the median frame. Returns the frames and how far each was moved.

    Twice over: the first median is of frames still out of line, so it is blurred and a one-pixel shift
    hardly shows against it. The second is sharp.
    """
    frames = np.asarray(frames)
    lum = _lum(frames.astype(np.float32))
    rows, columns = max(2 * search + 8, int(lum.shape[1] * DRY_TOP)), lum.shape[2]
    reach = sorted(((dy, dx) for dy in range(-search, search + 1) for dx in range(-search, search + 1)),
                   key=lambda move: abs(move[0]) + abs(move[1]))
    moves = np.zeros((len(frames), 2), dtype=int)
    for _ in range(2):
        anchor = np.median(np.array([_shift(grey, -dy, -dx) for grey, (dy, dx) in zip(lum, moves)]), axis=0)
        for index, grey in enumerate(lum):
            best = None
            for dy, dx in reach:
                miss = float(np.abs(anchor[search:rows, search:columns - search]
                                    - grey[search + dy:rows + dy, search + dx:columns - search + dx]).mean())
                if best is None or miss < 0.97 * best[0]:
                    best = (miss, dy, dx)
            moves[index] = best[1:]
    return np.array([_shift(frame, -dy, -dx) for frame, (dy, dx) in zip(frames, moves)]), moves


def stabilise(frames, search=TREMBLE):
    """The frames of one reading, lined up with each other. A camera on a pole trembles, and a hand shakes."""
    return _register(frames, search)[0]


def _change_point(values):
    """Log Bayes-factor profile for a boundary at each row: two Gaussian segments against one."""
    v = np.asarray(values, dtype=np.float64)
    n = len(v)
    k = np.arange(n + 1)
    total, squares = np.concatenate([[0.0], np.cumsum(v)]), np.concatenate([[0.0], np.cumsum(v * v)])
    floor = max(1e-9, 0.002 * float(v.var()))
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_above, mean_below = total / k, (total[-1] - total) / (n - k)
        var_above = squares / k - mean_above ** 2
        var_below = (squares[-1] - squares) / (n - k) - mean_below ** 2
        two = -0.5 * (k * np.log(np.maximum(var_above, floor)) + (n - k) * np.log(np.maximum(var_below, floor)))
    out = np.nan_to_num(two - (-0.5 * n * np.log(max(float(v.var()), floor))), nan=0.0, posinf=0.0, neginf=0.0)[:n]
    out[:MIN_WET // 2] = out[n - MIN_WET // 2:] = 0.0
    return out


def _clip(frames, still):
    """Several frames, no dry view: water is where the picture keeps changing. Still water is not seen."""
    rows = still.shape[0]
    dry = max(2 * SHAKE + 4, int(rows * DRY_TOP))
    last = rows - MIN_WET
    still_lum = _lum(still)
    z, pixel_noise = _flicker(_lum(frames), still_lum, dry)
    still_row = _still(z)
    moving = _with_flat(np.where((z > 2) & (z < 150), -np.log(148.0), -np.inf), 1 / 150)
    look = _change_point(still_lum.mean(axis=1)) + _change_point(np.abs(np.diff(still_lum, axis=1)).mean(axis=1))
    above = np.cumsum(still_row)
    ends = np.full(rows, -np.inf)
    ends[dry:last + 1] = above[dry - 1:last] - np.log(rows) + np.cumsum(moving[::-1])[::-1][dry:last + 1]
    ends = ends + CLIP_APPEARANCE * (look - look.max())       # prefer a row where the picture also changes
    group = "low light" if float(still_lum[SHAKE:dry].mean()) / max(pixel_noise, 1e-4) < LOW_LIGHT else "normal"
    all_ends = np.logaddexp.reduce(ends)
    return _decide(float(np.exp(all_ends - np.logaddexp(all_ends, above[-1]))), ends, 0.0, group, rows)


def _photo(still):
    """One frame, no dry view: where do two different-looking materials meet? Easily fooled."""
    lum = _lum(still)
    evidence = (_change_point(lum.mean(axis=1)) + _change_point(np.abs(np.diff(lum, axis=1)).mean(axis=1))
                + _change_point((still.max(axis=-1) - still.min(axis=-1)).mean(axis=1)))
    rows = len(evidence)
    if evidence.max() < PHOTO_EVIDENCE:
        return _nothing(rows, "unreadable")
    log_post = PHOTO_TEMPER * evidence
    log_post[:MIN_WET // 2] = log_post[rows - MIN_WET // 2:] = -np.inf
    return _describe(np.exp(log_post - log_post.max()), 0.5, "normal")


def locate(frames, reference=None, trace=None):
    """Where the water starts in this strip, as a distribution over rows.

    frames: (T, rows, columns, 3) or (rows, columns, 3), values 0-255. Six frames a second or so
    apart make one reading. reference: the same strip on a dry day, one image or several. trace: a
    dict to be filled with what the reading rested on, row by row.
    """
    frames = np.asarray(frames, dtype=np.float32)
    if frames.ndim == 3:
        frames = frames[None]
    frames = frames[..., :3] / 255.0
    tremble = 0.0
    if len(frames) >= 3:
        frames, moves = _register(frames)
        tremble = float(moves[:, 0].std())
    still = np.median(frames, axis=0)                         # a vehicle driving through is not in the median
    if reference is None:
        return _clip(frames, still) if len(frames) >= 3 else _photo(still)
    reference = np.asarray(reference, dtype=np.float32)[..., :3] / 255.0
    if reference.ndim == 4 and len(reference) > 1:
        ref_noise = float(np.median(_lum(reference).var(axis=0, ddof=1))) * min(1.0, 1.5708 / len(reference))
        reference = np.median(reference, axis=0)
    else:
        reference = reference[0] if reference.ndim == 4 else reference
        steps = np.diff(_lum(reference), axis=1)
        ref_noise = (1.4826 * float(np.median(np.abs(steps - np.median(steps))))) ** 2 / 2
    return _with_reference(frames, still, reference, ref_noise, tremble, trace)


def track(readings):
    """Filter a sequence of readings: each is read in the light of the ones before it.

    The belief is over every row and one more place, "below the strip", which is dry. A reading that
    saw water sharpens it; one that saw a dry strip moves it toward dry; one that was blocked or
    unsure changes nothing, and the estimate is carried forward a little less sure. Returns one
    Waterline per reading; nothing is reported until some reading has said something.
    """
    out, belief, kernel = [], None, None
    for reading in readings:
        rows = len(reading.log_posterior)
        if kernel is None:
            index = np.arange(rows + 1)
            kernel = np.exp(-0.5 * ((index[:, None] - index[None, :]) / DRIFT_ROWS) ** 2)
            kernel /= kernel.sum(axis=0, keepdims=True)
        if belief is not None:
            belief = (1 - JUMP) * kernel @ belief + JUMP / (rows + 1)
        if reading.found:
            widen = max(1.0, QUANTILE[reading.group] / 1.645) ** 2            # a calibrated reading is a flatter one
            seen = np.exp((reading.log_posterior - reading.log_posterior.max()) / widen)
            p_water, p_dry = reading.confidence, reading.p_dry
        else:
            seen = np.ones(rows)
            p_water, p_dry = (0.0, 1.0) if reading.reason == "dry" else (0.0, 0.0)
        # What the reading says, less what it leaves open and the chance that it is simply wrong.
        unknown = MISREAD + (1 - MISREAD) * max(0.0, 1.0 - p_water - p_dry)
        like = (1 - MISREAD) * np.concatenate([p_water * seen / seen.sum(), [p_dry]]) + unknown / (rows + 1)
        if p_water + p_dry > 0:
            belief = like if belief is None else belief * like
            belief = belief / belief.sum()
        if belief is None:
            out.append(reading)
            continue
        on_rows = float(belief[:rows].sum())
        held = "ok" if reading.found else f"held: {reading.reason}"
        if on_rows >= FOUND_AT:
            out.append(_describe(belief[:rows], on_rows, reading.group, held, reading.p_blocked,
                                 float(belief[rows]), QUANTILE["tracked"]))
        else:
            out.append(_nothing(rows, "dry" if reading.reason == "dry" else held, reading.p_blocked,
                                float(belief[rows]), reading.group))
    return out


def depth_cm(row, base_row, cm_per_row):
    """Rows up from the object's base, in centimetres. base_row is where the object meets the road."""
    return max(0.0, (base_row - row) * cm_per_row)
