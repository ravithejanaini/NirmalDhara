"""Who is alerted at each state, how often, and the fallback wording.

METHOD.md section 8. These rules are code, not model output: the model may choose
among the audiences allowed here and reword a message, but it cannot add an
audience or change a level. The templates below are what is sent when the model
is slow or fails (ARCHITECTURE.md section 6.4).
"""

from .bands import PASSABLE, band_for, passability
from .state import CLEAR, CRITICAL, CRITICAL_DEPTH_CM, RECEDING, WARNING, WATCH

RESIDENTS, GUARDIANS, TRAFFIC, PUMP, FLEET = (
    "residents", "guardians", "traffic_control", "pump_operator", "fleet")

LEVEL = {CLEAR: 0, WATCH: 1, RECEDING: 2, WARNING: 3, CRITICAL: 4}
REPEAT_AFTER_S = 20 * 60

# What each audience receives in each state. Guardians are only ever asked for photos.
RULES = {
    CLEAR: {},
    WATCH: {GUARDIANS: "photo_request"},
    WARNING: {RESIDENTS: "warning", GUARDIANS: "photo_request", TRAFFIC: "advisory",
              PUMP: "pump_request", FLEET: "blocked"},
    CRITICAL: {RESIDENTS: "do_not_enter", GUARDIANS: "photo_request",
               TRAFFIC: "closure_recommendation", PUMP: "pump_urgent", FLEET: "blocked"},
    RECEDING: {RESIDENTS: "update", GUARDIANS: "photo_request", TRAFFIC: "update",
               PUMP: "update", FLEET: "blocked"},
}

BAND_LABEL = {"B0": "dry", "B1": "ankle deep", "B2": "shin deep", "B3": "below the knee",
              "B4": "about knee deep", "B5": "above the knee"}
# "bikes, scooters" not "bikes and scooters": the list is joined with commas and one "and",
# and two-wheelers always share their answer with autos, so this label never ends a sentence.
VEHICLE_LABEL = {"two_wheeler": "bikes, scooters", "auto": "autos", "car": "cars",
                 "suv": "SUVs", "pedestrian": "people on foot"}
MOVING_WATER = "Do not enter moving water at any depth."


def due(state, high_cm, trusted, last_sent, now):
    """Audiences to alert now, as {audience: kind}.

    `last_sent` maps audience -> (level, sent_at) for the last alert on this site.
    An audience is alerted again when the level has risen, or after the repeat
    interval.
    """
    kinds = dict(RULES[state])
    # One unconfirmed photo of critical depth warns the public at once, but the
    # closure recommendation to officials waits for a trusted source.
    if state == WARNING and high_cm >= CRITICAL_DEPTH_CM and not trusted:
        kinds[RESIDENTS] = "do_not_enter"

    def is_due(audience):
        if audience not in last_sent:
            return True
        level, sent_at = last_sent[audience]
        return LEVEL[state] > level or now - sent_at >= REPEAT_AFTER_S

    return {audience: kind for audience, kind in kinds.items() if is_due(audience)}


def _join(words):
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _minutes(low, high):
    low, high = round(low), round(high)
    return f"about {low} minutes" if low == high else f"{low} to {high} minutes"


def _advice(low, high, confidence, moving):
    answers = passability(low, high, confidence, moving)
    unsafe = [label for v, label in VEHICLE_LABEL.items() if answers[v] != PASSABLE]
    safe = [label for v, label in VEHICLE_LABEL.items() if answers[v] == PASSABLE]
    text = f"Not safe for {_join(unsafe)}." if unsafe else ""
    if safe:
        text += f" Passable with care for {_join(safe)}."
    return text.strip()


def template(kind, site_name, low, high, confidence, seen_at, trusted=True, moving=False,
             cars_lose_passage_min=None):
    """Fallback wording for one alert. `seen_at` is a clock time such as "5:42 pm".

    Never states that a road is closed: closures are recommended to officials and
    confirmed by them.
    """
    depth = f"{BAND_LABEL[band_for(high)]} ({round(low)}-{round(high)} cm, seen {seen_at})"
    unconfirmed = "" if trusted else " This is from one unconfirmed photo."

    if kind == "photo_request":
        # Before any water is seen the reason is the forecast; after, it is the last reading.
        reason = (f"Water at {site_name} was {depth}." if high > 0
                  else f"Heavy rain is expected at {site_name}.")
        return (f"{reason} Please send a photo of the road from a safe, dry spot. "
                "Do not go near the water.")
    if kind == "cleared":
        # Sent once when a flood ends, to everyone who was warned. It says what was seen and
        # that the warnings have ended. It does not say the road is open or safe.
        level = f"is now {depth}" if high > 0 else f"has gone (seen {seen_at})"
        return (f"{site_name}: water {level}. Earlier warnings for this site have ended. "
                f"{MOVING_WATER}")
    if kind == "pump_request":
        return f"Water at {site_name} is {depth} and rising. Please start the pump."
    if kind == "pump_urgent":
        return f"URGENT: water at {site_name} is {depth}. Pumping is needed now."
    if kind == "blocked":
        return f"{site_name}: {depth}."
    if kind == "update":
        return f"Water at {site_name} is falling. It is now {depth}. {MOVING_WATER}"
    if kind == "do_not_enter":
        return (f"DO NOT ENTER {site_name}. Water is {depth}. Use another route. "
                f"{MOVING_WATER}{unconfirmed}")
    if kind == "closure_recommendation":
        return (f"CRITICAL: {site_name}. Water is {depth}, confidence {confidence:.1f}. "
                "Recommend closing both entries.")

    advice = _advice(low, high, confidence, moving)
    if kind == "warning":
        soon = ""
        cars_can_pass = passability(low, high, confidence, moving)["car"] == PASSABLE
        # Only said while cars can still pass; otherwise it contradicts the advice.
        if cars_lose_passage_min and cars_can_pass:
            soon = f" Cars are likely to lose passage in {_minutes(*cars_lose_passage_min)}."
        return f"Water at {site_name} is {depth}. {advice}{soon} {MOVING_WATER}{unconfirmed}"
    if kind == "advisory":
        return (f"Advisory: {site_name}. Water is {depth}, confidence {confidence:.1f}. "
                f"{advice}{unconfirmed}")
    raise ValueError(kind)
