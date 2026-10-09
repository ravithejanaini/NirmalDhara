"""Flood event orchestration, as pure logic (DESIGN.md section 9).

One FloodEvent exists per site per flood. Two callers run the same step:
the reactor, when the state engine reports a change, and the ticker, when time
passes. Each step folds the latest site state into the event, decides what is
due, and records it. Decisions are a function of (event, site, now), so two
callers running at once reach the same decision and produce the same alert ids.
"""

from dataclasses import dataclass, field, replace

from . import alerts
from .bands import NO_GO_CM
from .predict import minutes_to_no_go, rise_rate
from .state import CLEAR, CRITICAL, SMOOTH_N, WARNING_DEPTH_CM, WATCH

ASK_EVERY_S = {WATCH: 600}       # photo re-ask interval; 5 minutes in any other state
ASK_EVERY_DEFAULT_S = 300
MAX_UNANSWERED_ASKS = 3
ACK_TIMEOUT_S = 300              # an unacknowledged closure recommendation escalates
MAX_CONTACTS = 3                 # contacts tried for one audience
MAX_FOLD_GAP_S = 300             # a longer silence is not counted as blocked time
TICK_S = {WATCH: 120}            # ticker interval; 60 seconds in any other state
TICK_DEFAULT_S = 60
FLOOD, NO_FLOOD = "flood", "no_flood"


@dataclass(frozen=True)
class FloodEvent:
    site_id: str
    start: int
    version: int = 0
    last_fold_at: int = 0
    peak_low: float = 0.0
    peak_high: float = 0.0
    blocked_two_wheelers_s: int = 0
    blocked_cars_s: int = 0
    water_seen: bool = False
    confirmed: bool = False
    asks: int = 0
    unanswered_asks: int = 0
    last_ask_at: int | None = None
    alerts: dict = field(default_factory=dict)   # audience -> AlertRecord fields
    loops: int = 0
    closed_at: int | None = None
    outcome: str | None = None


@dataclass(frozen=True)
class Plan:
    alerts: dict            # audience -> kind, due now
    escalate: tuple         # audiences whose alert goes to the next contact
    ask_photos: bool
    close: str | None       # FLOOD, NO_FLOOD or None
    wait_s: int


def open_event(site_id, now):
    return FloodEvent(site_id, start=int(now), last_fold_at=int(now))


def fold(event, site, now):
    """Bring the event up to date with the site as it is now."""
    gap = max(0, min(int(now) - event.last_fold_at, MAX_FOLD_GAP_S))
    latest_reading = site.readings[-1].ts if site.readings else None
    answered = (event.last_ask_at is not None and latest_reading is not None
                and latest_reading > event.last_ask_at)
    return replace(
        event,
        last_fold_at=int(now),
        peak_low=max(event.peak_low, site.low),
        peak_high=max(event.peak_high, site.high),
        blocked_two_wheelers_s=event.blocked_two_wheelers_s
        + (gap if site.high >= NO_GO_CM["two_wheeler"] else 0),
        blocked_cars_s=event.blocked_cars_s + (gap if site.high >= NO_GO_CM["car"] else 0),
        water_seen=event.water_seen or site.high >= WARNING_DEPTH_CM,
        confirmed=event.confirmed or (site.trusted and site.high >= WARNING_DEPTH_CM),
        unanswered_asks=0 if answered else event.unanswered_asks,
    )


def plan(event, site, now):
    """What is due now. Does not change anything."""
    if site.state == CLEAR:
        # A flood that ends tells everyone it warned. Without this, "do not enter" is never
        # withdrawn. A watch that saw no water warned nobody, so it ends silently.
        stand_down = {audience: "cleared" for audience in event.alerts} if event.water_seen else {}
        return Plan(stand_down, (), False, FLOOD if event.water_seen else NO_FLOOD, 0)

    last_sent = {a: (r["level"], r["sent_at"]) for a, r in event.alerts.items()}
    due = alerts.due(site.state, site.high, site.trusted, last_sent, now)
    due.pop(alerts.GUARDIANS, None)     # guardians are asked for photos, below

    escalate = tuple(
        audience for audience, record in event.alerts.items()
        if record["kind"] == "closure_recommendation"
        and site.state == CRITICAL
        and record.get("acked_at") is None
        and now - record["sent_at"] >= ACK_TIMEOUT_S
        and record["contact"] < MAX_CONTACTS - 1
        and audience not in due
    )

    interval = ASK_EVERY_S.get(site.state, ASK_EVERY_DEFAULT_S)
    ask = (event.unanswered_asks < MAX_UNANSWERED_ASKS
           and (event.last_ask_at is None or now - event.last_ask_at >= interval))

    return Plan(due, escalate, ask, None, TICK_S.get(site.state, TICK_DEFAULT_S))


def alert_id(event, audience, seq, kind):
    """The same for any caller that reaches the same decision, so repeats are dropped.

    The kind is part of the id: a caller working from an older view of the site may
    decide on a milder alert for the same slot, and that must not be able to stand
    in for the stronger one.
    """
    return f"{event.site_id}#{event.start}#{audience}#{seq}#{kind}"


def messages(event, site, plan_, now):
    """The alerts and photo request this plan sends, as (alert_id, audience, kind, contact)."""
    out = []
    for audience, kind in plan_.alerts.items():
        seq = event.alerts.get(audience, {}).get("seq", -1) + 1
        out.append((alert_id(event, audience, seq, kind), audience, kind, 0))
    for audience in plan_.escalate:
        record = event.alerts[audience]
        out.append((alert_id(event, audience, record["seq"] + 1, record["kind"]), audience,
                    record["kind"], record["contact"] + 1))
    if plan_.ask_photos:
        out.append((alert_id(event, alerts.GUARDIANS, event.asks, "photo_request"),
                    alerts.GUARDIANS, "photo_request", 0))
    return out


def record(event, site, plan_, now):
    """The event after the plan has been carried out."""
    now = int(now)
    sent = dict(event.alerts)
    level = alerts.LEVEL[site.state]
    for audience, kind in plan_.alerts.items():
        seq = sent.get(audience, {}).get("seq", -1) + 1
        sent[audience] = {"kind": kind, "level": level, "sent_at": now, "seq": seq,
                          "contact": 0, "acked_at": None}
    for audience in plan_.escalate:
        previous = sent[audience]
        sent[audience] = {**previous, "sent_at": now, "seq": previous["seq"] + 1,
                          "contact": previous["contact"] + 1}
    event = replace(event, alerts=sent, loops=event.loops + 1, version=event.version + 1)
    if plan_.ask_photos:
        event = replace(event, asks=event.asks + 1,
                        unanswered_asks=event.unanswered_asks + 1, last_ask_at=now)
    if plan_.close:
        event = replace(event, closed_at=now, outcome=plan_.close)
    return event


def acknowledge(event, audience, now):
    """An official has acknowledged the alert to this audience."""
    if audience not in event.alerts or event.alerts[audience].get("acked_at"):
        return event
    sent = dict(event.alerts)
    sent[audience] = {**sent[audience], "acked_at": int(now)}
    return replace(event, alerts=sent, version=event.version + 1)


def confidence(site):
    """The weakest confidence among the readings the current depth is smoothed from."""
    recent = site.readings[-SMOOTH_N:]
    return min(r.confidence for r in recent) if recent else 0.0


def cars_lose_passage_min(site):
    """(sooner, later) minutes until cars lose passage, or None if not rising."""
    points = [(r.ts / 60, r.high) for r in site.readings[-6:]]
    rate = rise_rate(points)
    if rate is None or rate <= 0:
        return None
    sooner = minutes_to_no_go(site.high, rate)["car"]
    later = minutes_to_no_go(site.low, rate)["car"]
    if sooner is None or later is None:
        return None
    return sooner, later


def summary(event):
    """The closed event as stored for the repeat offenders view (METHOD.md section 14)."""
    return {
        "site_id": event.site_id, "start": event.start, "end": event.closed_at,
        "outcome": event.outcome, "confirmed": event.confirmed,
        "peak_depth_cm_low": event.peak_low, "peak_depth_cm_high": event.peak_high,
        "minutes_blocked_two_wheelers": event.blocked_two_wheelers_s // 60,
        "minutes_blocked_cars": event.blocked_cars_s // 60,
        "photo_requests": event.asks,
    }
