"""Site state engine (METHOD.md sections 2, 4 and 6 C5).

Pure logic: no AWS calls. The Lambda handler loads a Site, calls apply_rain or
apply_reading, and writes the result back with a version check.
"""

from dataclasses import dataclass, field, replace
from statistics import median

from .bands import BAND_EDGES_CM, NO_GO_CM, band_for

CLEAR, WATCH, WARNING, CRITICAL, RECEDING = "CLEAR", "WATCH", "WARNING", "CRITICAL", "RECEDING"

WARNING_DEPTH_CM = BAND_EDGES_CM[0][1]   # bottom of B2: two-wheelers at risk
CRITICAL_DEPTH_CM = NO_GO_CM["car"]      # bottom of B3: cars must not enter

TRUSTED_SOURCES = ("cctv", "guardian")
PAIR_WINDOW_S = 600        # two residents within 10 minutes count as trusted
JUMP_BANDS = 2             # a jump this large ...
JUMP_WINDOW_S = 120        # ... this quickly is held until confirmed
DRY_WATCH_S = 3600         # a watch with no water ends after an hour of light rain
SMOOTH_N = 3
MIN_ESTIMATE_CONFIDENCE = 0.4
BANDS = ["B0"] + [name for name, _ in BAND_EDGES_CM] + ["B5"]


def rain_index(past1_mm, past3_mm, next1_mm):
    """Rain in the last hour, half weight for the two hours before, plus the next hour."""
    return past1_mm + 0.5 * (past3_mm - past1_mm) + next1_mm


def band_gap(depth_a, depth_b):
    return abs(BANDS.index(band_for(depth_a)) - BANDS.index(band_for(depth_b)))


def weighted_median(values, weights):
    pairs = sorted(zip(values, weights))
    half = sum(weights) / 2
    running = 0.0
    for value, weight in pairs:
        running += weight
        if running >= half:
            return value
    return pairs[-1][0]


def fuse(estimates):
    """Combine object-level estimates from one image into one range.

    Each estimate is (low_cm, high_cm, confidence). Returns (low, high, confidence)
    or None when there is nothing to combine.
    """
    if not estimates:
        return None
    lows, highs, confidences = zip(*estimates)
    low = weighted_median(lows, confidences)
    usable = [h for h, c in zip(highs, confidences) if c >= MIN_ESTIMATE_CONFIDENCE]
    high = max(usable or highs)
    confidence = sum(confidences) / len(confidences)
    if band_gap(min(lows), high) > 2:
        confidence /= 2
    return low, max(high, low), confidence


@dataclass(frozen=True)
class Reading:
    ts: float              # server receive time, seconds
    low: float
    high: float
    confidence: float
    source: str            # cctv | guardian | resident
    device: str = ""


@dataclass(frozen=True)
class Site:
    site_id: str
    rain_threshold_mm: float = 20.0
    state: str = CLEAR
    version: int = 0
    readings: tuple = ()           # accepted readings, newest last
    held: Reading | None = None    # a sudden jump waiting for confirmation
    low: float = 0.0               # smoothed depth range
    high: float = 0.0
    trusted: bool = False          # a trusted source has confirmed the current depth
    water_seen: bool = False
    rain_low_since: float | None = None
    since: float | None = None     # when the site last left CLEAR
    applied: tuple = ()            # keys of the last messages applied, oldest first
    # Facts produced by the last step. Stored with the record until they have been
    # published, so a saved change cannot lose its events.
    events: tuple = field(default=(), compare=False)


def _is_trusted(reading, earlier):
    """A trusted source, or an earlier reading that independently agrees with this one."""
    if reading.source in TRUSTED_SOURCES:
        return True
    return any(
        reading.ts - other.ts <= PAIR_WINDOW_S
        and band_gap(other.high, reading.high) <= 1
        and (other.source in TRUSTED_SOURCES or other.device != reading.device)
        for other in earlier
    )


def _falling(readings, n=3):
    """True when the last n accepted readings each sit below the one before."""
    if len(readings) < n + 1:
        return False
    tail = [r.high for r in readings[-(n + 1):]]
    return all(later < earlier for earlier, later in zip(tail, tail[1:]))


def _state_for(site):
    """State implied by the smoothed depth, trust and trend."""
    high = site.high
    if site.state in (WARNING, CRITICAL) and _falling(site.readings):
        return RECEDING
    if site.state == RECEDING:
        last_two = site.readings[-2:]
        if len(last_two) == 2 and all(r.high < WARNING_DEPTH_CM for r in last_two):
            return CLEAR
        if len(last_two) == 2 and last_two[1].high <= last_two[0].high:
            return RECEDING
        # Rising again: fall through to the depth rules below.
    if high >= CRITICAL_DEPTH_CM and site.trusted:
        return CRITICAL
    if high >= WARNING_DEPTH_CM:
        return WARNING
    if site.state in (WARNING, CRITICAL):
        return RECEDING
    return site.state if site.state != RECEDING else CLEAR


def _with_state(site, new_state, ts):
    events, since = site.events, site.since
    if new_state != site.state:
        events += (("SiteStateChanged", site.state, new_state, ts),)
        if site.state == CLEAR:
            since = ts
    return replace(site, state=new_state, since=since, events=events,
                   version=site.version + 1)


def apply_rain(site, index_mm, ts):
    """Apply a new rain index. Starts a watch, or ends a dry one."""
    site = replace(site, events=())
    wet = index_mm >= site.rain_threshold_mm
    low_since = None if wet else (site.rain_low_since if site.rain_low_since is not None else ts)
    site = replace(site, rain_low_since=low_since)

    if site.state == CLEAR and wet:
        return _with_state(replace(site, water_seen=False), WATCH, ts)
    if (site.state == WATCH and not site.water_seen
            and low_since is not None and ts - low_since >= DRY_WATCH_S):
        return _with_state(site, CLEAR, ts)
    return replace(site, version=site.version + 1)


def apply_reading(site, reading):
    """Apply one depth reading and return the new Site with any events."""
    site = replace(site, events=())
    # The same reading again (a sender or a queue repeating itself) changes nothing.
    if reading == site.held or reading in site.readings:
        return replace(site, version=site.version + 1)
    last = site.readings[-1] if site.readings else None

    # A sudden jump is held, not rejected, until the next reading agrees with it.
    if (last is not None and site.held is None
            and reading.ts - last.ts <= JUMP_WINDOW_S
            and band_gap(last.high, reading.high) >= JUMP_BANDS):
        events = (("ReadingHeld", reading.ts),)
        return replace(site, held=reading, events=events, version=site.version + 1)

    accepted = [reading]
    if site.held is not None and band_gap(site.held.high, reading.high) <= 1:
        accepted = [site.held, reading]

    readings = (site.readings + tuple(accepted))[-12:]
    recent = readings[-SMOOTH_N:]
    low, high = median(r.low for r in recent), median(r.high for r in recent)
    # Once a trusted source has put the site at CRITICAL, a later untrusted reading
    # that still shows critical depth does not withdraw that trust.
    trusted = _is_trusted(reading, readings[:-1]) or (
        site.state == CRITICAL and high >= CRITICAL_DEPTH_CM)

    site = replace(
        site, readings=readings, held=None, low=low, high=high, trusted=trusted,
        water_seen=site.water_seen or high >= WARNING_DEPTH_CM,
        events=(("ReadingAccepted", reading.ts),),
    )
    return _with_state(site, _state_for(site), reading.ts)
