"""Find the waterline on a vertical object without a vision model (METHOD.md C2, estimator 1).

The input is a narrow strip of the image running down a gauge, pillar or wall: object at the
top, water (if any) below. The question is one number, the row where the water starts, and how
sure we are of it.

For a fixed camera, the top of the strip is known to be dry, so it tells us what "dry" looks like
for this camera, in this light, right now. Every row is then scored against that, cue by cue:

    structure   does the row still show the pattern it shows in the dry view? Shadows and wet
                stains keep the pattern; water replaces it
    flicker     does the row change from frame to frame? Water moves; a wall does not
    level       is the row's brightness what the dry view predicts? (weak: shadows fool it)

Each cue is first averaged over a few neighbouring rows, so faint evidence that is consistent adds
up. Then each row gets a bounded vote from each cue, wet or dry, so no single cue, and no patch of
glare or a painted mark, can outvote the rest. The votes become a likelihood for every possible
waterline row, including "no water at all". The result is a distribution, not a point: the
estimate, a 90% interval, and whether a line was found.

Medians over the frames of one reading keep a vehicle that passes through from being read as water.
A sequence of readings is filtered with a hidden Markov model, because water rises and falls slowly.

For a single photo with no dry view there is nothing to compare with, so a weaker model is used:
a Bayesian change point between two materials on brightness, texture and colour. It is easily
fooled and is here to show the limit, not to be relied on.

Tested on rendered scenes with known waterlines (scripts/simulate_waterline.py). It has not been
measured against a real flood.
"""

from dataclasses import dataclass

import numpy as np

MARGIN = 4                 # rows at each end that cannot be the boundary
DRY_TOP = 0.2              # share of the strip, from the top, taken as known dry
WINDOW = 2                 # rows each side used when comparing a row's pattern with the dry view
SHAKE = 4                  # rows of vertical camera shake searched when lining up with the dry view
POOL = 6                   # rows each side averaged into a row's cue before it votes
VOTE_AT = 4.0              # how many dry-noise deviations a pooled row must stand out before it votes "wet"
VOTE_LIMIT = 4.0           # the most one cue can say about one row, in log-odds
RAW_VOTE_AT = 5.0          # the same test for a single row on its own, which must stand out further
MIN_WET = 8                # fewer rows of water than this at the foot of the strip are not reported
WEIGHTS = {"structure": 1.0, "flicker": 1.0, "level": 0.3}
TEMPER = 0.3               # neighbouring rows are not independent evidence
FOUND_AT = 0.5             # posterior probability of "there is water" needed to report a line
OCCLUDED = 0.25            # correlation with the dry view, in the rows that must be dry, below which the view is blocked
TEXTURED = 0.04            # contrast the dry view needs there for that test to mean anything
DRIFT_ROWS = 2.0           # how far the waterline may move between readings, as a standard deviation
JUMP = 0.02                # chance per reading that the line is somewhere new
PHOTO_TEMPER = 0.08        # the single-photo model is far less sure of itself
PHOTO_EVIDENCE = 40.0      # log Bayes factor for "two materials" a single photo needs


@dataclass(frozen=True)
class Waterline:
    found: bool
    row: float              # posterior mean; rows from the top of the strip
    low: float              # 5% and 95% points of the posterior
    high: float
    confidence: float       # posterior mass within 3 rows of the estimate
    reason: str             # "ok", "dry", "occluded", "unreadable", "held: ..."
    log_posterior: np.ndarray


def _luminance(frames):
    return np.asarray(frames)[..., :3].astype(np.float32).mean(axis=-1) / 255.0


def _robust(values):
    """Centre and spread of the dry rows, not moved by a few odd ones."""
    centre = float(np.median(values))
    spread = 1.4826 * float(np.median(np.abs(values - centre)))
    return centre, max(spread, 1e-4 + 0.05 * abs(centre))


def _pooled(values):
    """Each row averaged with its neighbours: POOL rows each side, shrinking at the ends."""
    padded = np.concatenate([np.full(POOL, values[0]), values, np.full(POOL, values[-1])])
    return np.convolve(padded, np.ones(2 * POOL + 1) / (2 * POOL + 1), mode="valid")


def _votes(values, dry_rows):
    """Bounded log-odds, per row, that the row is not like the dry rows (one-sided: larger is wetter).

    A row votes wet when its pooled cue is past the half-way point between the dry level and the
    wet level just below it. Half-way is where an averaged edge really is, whatever the contrast, so pooling
    does not shift the line.
    """
    pooled = _pooled(np.asarray(values, dtype=np.float64))
    centre, spread = _robust(pooled[:dry_rows])
    z = (pooled - centre) / spread
    # The wet level is read just below each row, not once for the strip: glare makes it uneven.
    reach = 2 * POOL + 1
    padded = np.concatenate([z, np.full(3 * reach, z[-1])])
    below = np.array([np.median(padded[row + POOL:row + POOL + reach]) for row in range(len(z))])
    threshold = np.maximum(VOTE_AT, 0.5 * below)
    pooled_vote = np.clip(z - threshold, -VOTE_LIMIT, VOTE_LIMIT)
    # A row that stands out by itself needs no help from its neighbours, and its vote is not smeared.
    raw = np.asarray(values, dtype=np.float64)
    raw_centre, raw_spread = _robust(raw[:dry_rows])
    raw_vote = np.clip((raw - raw_centre) / raw_spread - RAW_VOTE_AT, -VOTE_LIMIT, VOTE_LIMIT)
    return np.maximum(pooled_vote, raw_vote)


def _line_up(frame, reference, dry_rows):
    """The dry view shifted and re-lit to match this frame, judged on the rows known to be dry."""
    best = None
    for shift in range(-SHAKE, SHAKE + 1):
        moved = np.roll(reference, shift, axis=0)
        a, b = moved[:dry_rows].ravel(), frame[:dry_rows].ravel()
        gain = float(np.cov(a, b)[0, 1] / a.var()) if a.var() > 1e-6 else 1.0
        gain = gain if 0.05 < gain < 4.0 else float(b.mean() / max(a.mean(), 1e-3))
        fitted = gain * (moved - a.mean()) + b.mean()
        miss = float(np.abs(fitted[:dry_rows] - frame[:dry_rows]).mean())
        if best is None or miss < best[0]:
            best = (miss, fitted)
    return best[1]


def _pattern_loss(frame, fitted):
    """1 - correlation between each row's neighbourhood and the same neighbourhood in the dry view."""
    rows = frame.shape[0]
    out = np.zeros(rows)
    for row in range(rows):
        a = frame[max(0, row - WINDOW):row + WINDOW + 1].ravel()
        b = fitted[max(0, row - WINDOW):row + WINDOW + 1].ravel()
        a, b = a - a.mean(), b - b.mean()
        denominator = float(np.sqrt((a * a).sum() * (b * b).sum()))
        out[row] = 1.0 - (float((a * b).sum()) / denominator if denominator > 1e-9 else 0.0)
    return out


def cues(frames, reference=None):
    """Per-row cues for a strip. frames: (T, rows, columns, 3) or (rows, columns, 3), values 0-255."""
    frames = np.asarray(frames)
    if frames.ndim == 3:
        frames = frames[None]
    lum = _luminance(frames)
    still = np.median(lum, axis=0)                          # a passing vehicle is not in the median
    dry_rows = max(2 * MARGIN, int(lum.shape[1] * DRY_TOP))
    out = {}
    if len(frames) >= 3:
        steps = np.abs(np.diff(lum, axis=0)).mean(axis=2)   # (T-1, rows)
        # The lower quartile: water flickers in every step, a vehicle driving through only in some.
        out["flicker"] = np.percentile(steps, 25, axis=0)
    if reference is not None:
        fitted = _line_up(still, _luminance(reference), dry_rows)
        out["level"] = np.abs(still - fitted).mean(axis=1)
        out["structure"] = _pattern_loss(still, fitted)
    return out, still, dry_rows


def _change_point(values):
    """Log Bayes-factor profile for a boundary at each row: two Gaussian segments against one."""
    v = np.asarray(values, dtype=np.float64)
    n = len(v)
    k = np.arange(n + 1)
    total, squares = np.concatenate([[0.0], np.cumsum(v)]), np.concatenate([[0.0], np.cumsum(v * v)])
    floor = max(1e-6, 0.002 * float(v.var()))
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_above, mean_below = total / k, (total[-1] - total) / (n - k)
        var_above = squares / k - mean_above ** 2
        var_below = (squares[-1] - squares) / (n - k) - mean_below ** 2
        two = -0.5 * (k * np.log(np.maximum(var_above, floor)) + (n - k) * np.log(np.maximum(var_below, floor)))
    out = np.nan_to_num(two - (-0.5 * n * np.log(max(float(v.var()), floor))), nan=0.0, posinf=0.0, neginf=0.0)[:n]
    out[:MARGIN] = out[n - MARGIN:] = 0.0
    return out


def _photo(frames):
    """One frame, no dry view: where do two different-looking materials meet?"""
    frame = np.asarray(frames)
    frame = frame[0] if frame.ndim == 4 else frame
    lum = _luminance(frame)
    colour = frame[..., :3].astype(np.float32)
    evidence = (_change_point(lum.mean(axis=1)) + _change_point(np.abs(np.diff(lum, axis=1)).mean(axis=1))
                + _change_point((colour.max(axis=-1) - colour.min(axis=-1)).mean(axis=1) / 255.0))
    rows = len(evidence)
    if evidence.max() < PHOTO_EVIDENCE:
        return Waterline(False, float("nan"), 0.0, float(rows), 0.0, "unreadable", np.full(rows, -np.log(rows)))
    log_post = PHOTO_TEMPER * evidence
    log_post[:MARGIN] = log_post[rows - MARGIN:] = -np.inf
    return _describe(log_post)


def locate(frames, reference=None):
    """Where the water starts in this strip, as a distribution over rows."""
    summaries, still, dry_rows = cues(frames, reference)
    rows = still.shape[0]
    flat = np.full(rows, -np.log(rows))
    if not summaries:
        return _photo(frames)
    if reference is not None:
        ref = _luminance(reference)
        fitted = _line_up(still, ref, dry_rows)
        a, b = still[:dry_rows].ravel() - still[:dry_rows].mean(), fitted[:dry_rows].ravel() - fitted[:dry_rows].mean()
        patterned = float(ref[:dry_rows].std()) > TEXTURED
        match = float((a * b).sum() / max(np.sqrt((a * a).sum() * (b * b).sum()), 1e-9))
        if patterned and match < OCCLUDED:                  # the part that must be dry is not what was enrolled
            return Waterline(False, float("nan"), 0.0, float(rows), 0.0, "occluded", flat)
    wet = sum(WEIGHTS[name] * _votes(values, dry_rows) for name, values in summaries.items())
    # Log-likelihood of "water starts at row k", relative to "dry": the wet votes of every row from k down.
    log_like = TEMPER * np.concatenate([np.cumsum(wet[::-1])[::-1], [0.0]])
    log_like[:dry_rows] = -np.inf                           # the top is dry by assumption
    log_like[rows - MIN_WET:rows] = -np.inf                 # too little water showing to tell from noise
    total = np.logaddexp.reduce(log_like)
    if float(np.exp(log_like[rows] - total)) > 1 - FOUND_AT:
        return Waterline(False, float("nan"), 0.0, float(rows), 0.0, "dry", flat)
    return _describe(log_like[:rows])


def _describe(log_post, reason="ok"):
    p = np.exp(log_post - np.logaddexp.reduce(log_post))
    index = np.arange(len(p))
    row = float((p * index).sum())
    cumulative = np.cumsum(p)
    low, high = float(np.searchsorted(cumulative, 0.05)), float(np.searchsorted(cumulative, 0.95))
    near = float(p[max(0, int(round(row)) - 3):int(round(row)) + 4].sum())
    return Waterline(True, row, low, high, near, reason, np.log(p + 1e-300))


def track(readings):
    """Filter a sequence of readings: each is read in the light of the ones before it.

    A reading that found nothing carries the estimate forward, a little less sure. Returns one
    Waterline per reading; not found until the first reading that sees a line.
    """
    out, belief, kernel = [], None, None
    for reading in readings:
        rows = len(reading.log_posterior)
        if belief is not None:
            if kernel is None:
                index = np.arange(rows)
                kernel = np.exp(-0.5 * ((index[:, None] - index[None, :]) / DRIFT_ROWS) ** 2)
                kernel /= kernel.sum(axis=0, keepdims=True)
            belief = (1 - JUMP) * kernel @ belief + JUMP / rows
        if reading.found:
            likelihood = np.exp(reading.log_posterior - reading.log_posterior.max())
            belief = likelihood if belief is None else belief * likelihood
            belief = belief / belief.sum()
        if belief is None:
            out.append(reading)
        else:
            out.append(_describe(np.log(belief + 1e-300), "ok" if reading.found else f"held: {reading.reason}"))
    return out


def depth_cm(row, base_row, cm_per_row):
    """Rows up from the object's base, in centimetres. base_row is where the object meets the road."""
    return max(0.0, (base_row - row) * cm_per_row)
