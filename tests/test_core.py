from nirmaldhara.bands import (NO_ANSWER, NOT_SAFE, PASSABLE, UNKNOWN, answer_for,
                               band_for, passability)
from nirmaldhara.predict import clear_fall, clear_rise, depth_at, minutes_to_no_go, rain_factor, rise_rate


def test_bands():
    assert band_for(0) == "B0"
    assert band_for(5) == "B1"
    assert band_for(12) == "B2"
    assert band_for(25) == "B3"
    assert band_for(49) == "B4"
    assert band_for(50) == "B5"


def test_passable_needs_upper_end_below_limit():
    assert answer_for("car", 5, 10, 0.8) == PASSABLE
    # Range straddles the 20 cm car limit.
    assert answer_for("car", 15, 25, 0.9) == NOT_SAFE
    assert answer_for("two_wheeler", 5, 10, 0.8) == PASSABLE
    assert answer_for("two_wheeler", 10, 16, 0.9) == NOT_SAFE


def test_low_confidence_is_never_passable():
    assert answer_for("car", 5, 10, 0.5) == UNKNOWN


def test_buses_get_no_answer_until_everyone_is_unsafe():
    assert answer_for("bus", 20, 30, 0.9) == NO_ANSWER
    assert answer_for("bus", 40, 55, 0.9) == NOT_SAFE
    assert set(passability(40, 55, 0.9).values()) == {NOT_SAFE}


def test_moving_water_lowers_every_limit():
    assert answer_for("suv", 10, 14, 0.9) == PASSABLE
    assert answer_for("suv", 10, 14, 0.9, moving=True) == NOT_SAFE


def test_a_rise_is_clear_only_when_the_newest_range_lies_wholly_above_the_oldest():
    assert clear_rise([(3, 8), (6, 11), (9, 14)])                 # 9 is above 8
    assert not clear_rise([(2, 12), (5, 15), (8, 18)])            # 8 is not above 12: the rise is inside the doubt
    assert not clear_rise([(9, 14), (6, 11), (3, 8)]) and clear_fall([(9, 14), (6, 11), (3, 8)])
    assert not clear_fall([(3, 8), (6, 11), (9, 14)])
    assert not clear_rise([(3, 8)]) and not clear_rise([]) and not clear_fall([(3, 8)])
    assert not clear_rise([(3, 8), (8, 12)])                      # touching is not clear


def test_rise_rate_ignores_one_outlier():
    readings = [(0, 10), (5, 20), (10, 30), (15, 90), (20, 50)]
    assert rise_rate(readings) == 2.0
    assert rise_rate(readings[:2]) is None


def test_rain_factor_is_clipped():
    assert rain_factor(30, 5) == 3.0
    assert rain_factor(0, 10) == 0.25
    assert rain_factor(5, 0) == 3.0


def test_time_to_no_go():
    minutes = minutes_to_no_go(10, 1.0)
    assert minutes["car"] == 10
    assert minutes["two_wheeler"] == 5
    assert minutes_to_no_go(25, 1.0)["car"] is None
    assert minutes_to_no_go(10, 0)["car"] is None
    assert depth_at(40, 2.0, 30, 80) == 80
