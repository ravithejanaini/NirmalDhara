"""nirmaldhara/inflow.py: the storage equation backwards and forwards, on a made dip whose true figures are known.

The dip is METHOD 15.1's example: ramps of 4% and 5%, 14 m wide, so 315 d squared cubic metres at a
depth of d metres. Floods are made by the equation itself or by its closed form, and every test asks
for the figures that went in. Nothing here is a measurement of a real place.
"""

from math import sqrt

import pytest

from nirmaldhara import inflow
from nirmaldhara.bands import NO_GO_CM
from nirmaldhara.predict import minutes_to_no_go, rise_rate
from nirmaldhara.volume import VolumeCurve

DIP = VolumeCurve([(-60, 2.4), (0, 0.0), (40, 2.0)], 14)
AREA, DRAIN = 8000.0, 0.01                                        # square metres; cubic metres a second (10 litres)
QUARTERS = [(900 * (i + 1), 7.5) for i in range(4)]               # 30 mm in an hour, in quarter hours


def flood(rain=QUARTERS, area=AREA, drain=DRAIN, every=300, hours=6, doubt=0.0, start=0.0):
    """Readings of a made flood: [(seconds, low cm, high cm)] every five minutes while water stands."""
    path = inflow._run(DIP, start, area, drain, rain, hours * 3600)
    return [(t, max(cm - doubt, 0.0), cm + doubt) for t, cm in path if t % every == 0 and cm > 0.05]


def test_the_made_dip_holds_what_the_method_says_it_holds():
    assert abs(inflow.stored(DIP, 50) - 78.75) < 1e-9             # METHOD 15.1's worked figure
    assert abs(inflow.depth_of(DIP, 78.75) - 50) < 1e-9 and inflow.stored(DIP, 0) == 0.0


def test_a_flood_gives_back_the_ground_it_came_from_and_the_rate_it_drains_at():
    found = inflow.reveal(DIP, flood(doubt=1.0), QUARTERS)
    assert found.area_m2.low < AREA < found.area_m2.high and abs(found.area_m2.mid - AREA) < 0.1 * AREA
    assert found.drain_m3s.low < DRAIN < found.drain_m3s.high and abs(found.drain_m3s.mid - DRAIN) < 0.1 * DRAIN
    assert found.floods == 1 and found.rain_mm == 27.5 and found.peak_cm > 20      # the rain from the first reading to the deepest
    wide = inflow.reveal(DIP, flood(doubt=8.0), QUARTERS)          # read to eight centimetres either way: a wider answer
    assert wide.area_m2.high - wide.area_m2.low > 2 * (found.area_m2.high - found.area_m2.low)


def test_a_flood_with_too_few_readings_or_no_rain_says_nothing():
    assert inflow.reveal(DIP, flood()[:3], QUARTERS) is None
    assert inflow.reveal(DIP, flood(), []) is None and inflow.reveal(DIP, flood(), [(900, 0.0)]) is None


def test_without_readings_after_the_rain_the_drain_is_not_given_and_the_area_is_a_floor():
    rising = [r for r in flood(doubt=1.0) if r[0] <= 3600]         # the readings stopped when the rain did
    found = inflow.reveal(DIP, rising, QUARTERS)
    assert found.drain_m3s is None and found.area_m2.high < AREA   # what drained meanwhile is not counted
    assert inflow.together([found]) is None                        # and nothing is said ahead from it


def test_a_dip_that_widens_fills_more_slowly_than_a_straight_line_in_depth_says():
    inflow_m3s = 0.005                                             # five litres a second, nothing draining
    depth = lambda seconds: 100 * sqrt(inflow_m3s * seconds / 315)     # noqa: E731   the closed form for this dip
    readings = [(t, depth(t), depth(t)) for t in (300, 600, 900)]
    true_minutes = (315 * 0.20 ** 2 / inflow_m3s - 900) / 60       # until the water is 20 cm deep
    said = inflow.at_this_inflow(DIP, readings)["car"]
    assert abs(said[0] - true_minutes) < 0.01 and said[0] == said[1]
    straight = minutes_to_no_go(readings[-1][2], rise_rate([(t / 60, cm) for t, _, cm in readings]))["car"]
    assert abs(true_minutes - 27.0) < 1e-9 and straight < 0.65 * true_minutes     # the straight line says 16 minutes; it is 27
    falling = [(t, cm, cm) for t, (_, cm, _) in zip((300, 600, 900), reversed(readings))]
    assert inflow.at_this_inflow(DIP, falling) is None             # going down: nothing to say


def test_the_cautious_end_comes_first():
    readings = [(0, 2, 6), (300, 5, 9), (600, 8, 12)]
    said = inflow.at_this_inflow(DIP, readings)
    for vehicle, limit in NO_GO_CM.items():
        sooner, later = said[vehicle]
        assert 0 <= sooner <= later, vehicle
    assert said["two_wheeler"][0] < said["suv"][0]


def test_depths_ahead_from_rain_hold_the_truth_and_fall_once_it_stops():
    found = inflow.reveal(DIP, flood(doubt=1.0), QUARTERS)
    truth = dict(inflow._run(DIP, 0.0, AREA, DRAIN, QUARTERS, 3 * 3600))
    path = inflow.ahead(found, DIP, 0.0, 0.0, QUARTERS, 3 * 3600)
    assert all(low <= truth[t] + 1e-9 and truth[t] <= high + 1e-9 for t, low, high in path)
    peak = max(path, key=lambda step: step[2])
    assert 3300 <= peak[0] <= 3900 and path[-1][2] < peak[2]       # deepest about when the rain stops, lower two hours on
    times = inflow.minutes_to_no_go(path, 0.0, 0.0)
    assert times["car"][0] is not None and times["car"][0] <= (times["car"][1] or 1e9)
    assert inflow.minutes_to_no_go(path, 25.0, 31.0)["car"] == (0.0, 0.0)


def test_the_rain_that_would_close_the_road_is_the_rain_that_does():
    exact = inflow.Revealed(inflow.Range(AREA, AREA, AREA), inflow.Range(DRAIN, DRAIN, DRAIN))
    least, most = inflow.rain_to_reach(exact, DIP, 0.0, 0.0, 20.0, minutes=60)
    assert least == most and abs(least - 1000 * (315 * 0.04 + DRAIN * 3600) / AREA) < 1e-9      # 6.1 mm in the hour
    end = inflow._run(DIP, 0.0, AREA, DRAIN, [(3600, least)], 3600)[-1][1]
    assert abs(end - 20.0) < 0.3                                   # and that rain brings the water to 20 cm at the hour's end
    assert inflow.rain_to_reach(exact, DIP, 22.0, 25.0, 20.0) == (0.0, 0.0)
    found = inflow.reveal(DIP, flood(doubt=1.0), QUARTERS)
    table = inflow.guidance(found, DIP)
    assert table["two_wheeler"][0] < table["car"][0] < table["suv"][0]
    assert all(least <= most for least, most in table.values())


def test_nothing_is_said_ahead_without_both_figures():
    half = inflow.Revealed(inflow.Range(7000, 8000, 9000), None)
    for call in (lambda: inflow.ahead(half, DIP, 0, 0, QUARTERS), lambda: inflow.rain_to_reach(half, DIP, 0, 0, 20),
                 lambda: inflow.ahead(None, DIP, 0, 0, QUARTERS)):
        with pytest.raises(ValueError):
            call()


def test_several_floods_are_joined_by_their_widest_range():
    a = inflow.Revealed(inflow.Range(7000, 7500, 8200), inflow.Range(0.008, 0.01, 0.011), peak_cm=30, rain_mm=20)
    b = inflow.Revealed(inflow.Range(7600, 8100, 9000), inflow.Range(0.009, 0.012, 0.014), peak_cm=45, rain_mm=35)
    both = inflow.together([a, b, None, inflow.Revealed(None, None)])
    assert (both.area_m2.low, both.area_m2.high, both.floods) == (7000, 9000, 2)
    assert both.drain_m3s.mid == 0.011 and both.peak_cm == 45 and both.rain_mm == 35


def test_each_flood_is_played_forward_from_the_ones_before_it():
    storms = [QUARTERS, [(900 * (i + 1), mm) for i, mm in enumerate((4, 12, 16, 6, 2))], [(1800, 9.0), (3600, 14.0)]]
    floods = [(flood(rain, doubt=1.0), rain) for rain in storms]
    played = inflow.check(DIP, floods)
    assert len(played) == 2 and all(p["held"] for p in played)     # the first has nothing before it
    for p in played:
        assert p["peak said"][0] <= p["peak said"][1] and p["peak said"][1] - p["peak said"][0] < 15


def test_a_forecast_from_rain_is_no_better_than_the_rain():
    storm = [(900 * (i + 1), mm) for i, mm in enumerate((4, 12, 16, 6, 2))]
    fifth = [(ts, mm / 5) for ts, mm in storm]                     # as far short as docs/watch-history.md found the forecast
    played = inflow.check(DIP, [(flood(doubt=1.0), QUARTERS), (flood(storm, doubt=1.0), storm, fifth)])
    assert len(played) == 1 and not played[0]["held"] and played[0]["peak said"][1] < 0.5 * played[0]["peak read"][0]
    assert inflow.check(DIP, [(flood(doubt=1.0), QUARTERS), (flood(storm, doubt=1.0), storm, storm)])[0]["held"]


def test_the_module_says_it_has_met_no_real_flood():
    text = " ".join(inflow.__doc__.split())
    for must_say in ("Tried on made floods only", "Nothing calls this module", "A forecast from rain is no better than the rain", "None has."):
        assert must_say in text, must_say
