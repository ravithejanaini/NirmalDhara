import pytest

from nirmaldhara.alerts import (GUARDIANS, LEVEL, PUMP, REPEAT_AFTER_S, RESIDENTS, RULES,
                                TRAFFIC, due, template)
from nirmaldhara.state import CLEAR, CRITICAL, RECEDING, WARNING, WATCH


def test_a_watch_asks_guardians_and_tells_nobody_else():
    assert due(WATCH, 0, False, {}, 0) == {GUARDIANS: "photo_request"}


def test_warning_alerts_everyone_once():
    first = due(WARNING, 16, True, {}, 0)
    assert first[RESIDENTS] == "warning" and first[TRAFFIC] == "advisory"

    sent = {a: (LEVEL[WARNING], 0) for a in first}
    assert due(WARNING, 16, True, sent, 5 * 60) == {}
    assert set(due(WARNING, 16, True, sent, REPEAT_AFTER_S)) == set(first)


def test_a_rise_in_level_alerts_again_at_once():
    sent = {a: (LEVEL[WARNING], 0) for a in RULES[WARNING]}
    again = due(CRITICAL, 30, True, sent, 60)
    assert again[RESIDENTS] == "do_not_enter"
    assert again[TRAFFIC] == "closure_recommendation"
    assert again[PUMP] == "pump_urgent"


def test_one_unconfirmed_photo_warns_the_public_but_recommends_no_closure():
    alerts = due(WARNING, 28, False, {}, 0)
    assert alerts[RESIDENTS] == "do_not_enter"
    assert alerts[TRAFFIC] == "advisory"


def test_clear_sends_nothing():
    assert due(CLEAR, 0, False, {}, 0) == {}


def test_warning_text_names_who_must_not_enter():
    text = template("warning", "AMB Mall underpass", 10, 16, 0.8, "5:42 pm",
                    cars_lose_passage_min=(15, 25))
    assert "shin deep (10-16 cm, seen 5:42 pm)" in text
    assert "Not safe for bikes and scooters and autos." in text
    assert "Passable with care for cars, SUVs and people on foot." in text
    assert "Cars are likely to lose passage in 15 to 25 minutes." in text
    assert "Do not enter moving water at any depth." in text


def test_time_to_lose_passage_is_dropped_once_cars_cannot_pass():
    text = template("warning", "AMB Mall underpass", 15, 25, 0.8, "5:42 pm",
                    cars_lose_passage_min=(15, 25))
    assert "Not safe for bikes and scooters, autos and cars." in text
    assert "lose passage" not in text


def test_unconfirmed_alerts_say_so():
    text = template("do_not_enter", "AMB Mall underpass", 22, 28, 0.7, "5:51 pm",
                    trusted=False)
    assert text.startswith("DO NOT ENTER AMB Mall underpass.")
    assert text.endswith("This is from one unconfirmed photo.")


@pytest.mark.parametrize("kind", sorted({k for kinds in RULES.values() for k in kinds.values()}
                                        | {"do_not_enter"}))
def test_no_message_ever_says_the_road_is_closed(kind):
    text = template(kind, "Site", 45, 60, 0.9, "6:00 pm").lower()
    assert "road closed" not in text and "is closed" not in text


def test_every_rule_has_a_template():
    for state in (WATCH, WARNING, CRITICAL, RECEDING):
        for kind in RULES[state].values():
            assert template(kind, "Site", 10, 14, 0.8, "6:00 pm")
