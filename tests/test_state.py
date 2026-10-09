from nirmaldhara.state import (CLEAR, CRITICAL, RECEDING, WARNING, WATCH, Reading, Site,
                               apply_rain, apply_reading, fuse, rain_index)

MIN = 60


def reading(minute, high, source="guardian", device="g1", low=None, confidence=0.8):
    return Reading(minute * MIN, high - 5 if low is None else low, high, confidence,
                   source, device)


def feed(site, readings):
    for r in readings:
        site = apply_reading(site, r)
    return site


def test_rain_index_weights_older_rain_by_half():
    assert rain_index(10, 16, 8) == 10 + 3 + 8


def test_rain_starts_a_watch():
    site = apply_rain(Site("s1"), 25, 0)
    assert site.state == WATCH
    assert site.events == (("SiteStateChanged", CLEAR, WATCH, 0),)
    assert site.version == 1


def test_dry_watch_ends_after_an_hour_of_light_rain():
    site = apply_rain(Site("s1"), 25, 0)
    site = apply_rain(site, 5, 15 * MIN)
    assert site.state == WATCH
    site = apply_rain(site, 5, 80 * MIN)
    assert site.state == CLEAR


def test_watch_with_water_is_not_ended_by_light_rain():
    site = apply_rain(Site("s1"), 25, 0)
    site = apply_reading(site, reading(5, 15))
    site = apply_rain(site, 5, 10 * MIN)
    site = apply_rain(site, 5, 90 * MIN)
    assert site.state == WARNING


def test_guardian_reading_moves_watch_to_warning_then_critical():
    site = apply_rain(Site("s1"), 25, 0)
    site = apply_reading(site, reading(5, 15))
    assert site.state == WARNING
    site = feed(site, [reading(10, 22), reading(15, 26)])
    assert site.state == CRITICAL


def test_one_resident_cannot_make_a_site_critical():
    site = apply_reading(Site("s1", state=WATCH), reading(5, 28, "resident", "phone-a"))
    assert site.state == WARNING
    assert not site.trusted


def test_two_residents_on_different_phones_can():
    site = Site("s1", state=WATCH)
    site = apply_reading(site, reading(5, 28, "resident", "phone-a"))
    site = apply_reading(site, reading(8, 26, "resident", "phone-b"))
    assert site.state == CRITICAL


def test_same_phone_twice_is_still_one_witness():
    site = Site("s1", state=WATCH)
    site = apply_reading(site, reading(5, 28, "resident", "phone-a"))
    site = apply_reading(site, reading(8, 26, "resident", "phone-a"))
    assert site.state == WARNING


def test_critical_is_not_withdrawn_by_a_later_resident_reading():
    site = feed(Site("s1", state=WATCH), [reading(5, 25), reading(10, 27)])
    assert site.state == CRITICAL
    site = apply_reading(site, reading(15, 28, "resident", "phone-a"))
    assert site.state == CRITICAL


def test_sudden_jump_is_held_until_confirmed():
    site = apply_reading(Site("s1", state=WATCH), reading(5, 8))
    site = apply_reading(site, reading(6, 45))          # two bands up within 2 minutes
    assert site.held is not None
    assert site.high == 8
    site = apply_reading(site, reading(7, 44))          # agrees with the held reading
    assert site.held is None
    assert site.high == 44


def test_falling_water_recedes_then_clears():
    site = feed(Site("s1", state=WATCH), [reading(5, 30), reading(10, 35), reading(15, 40)])
    assert site.state == CRITICAL
    site = feed(site, [reading(25, 32), reading(35, 24), reading(45, 16)])
    assert site.state == RECEDING
    site = feed(site, [reading(55, 8), reading(65, 5)])
    assert site.state == CLEAR


def test_water_rising_again_leaves_receding():
    site = feed(Site("s1", state=WATCH), [reading(5, 30), reading(10, 35), reading(15, 40),
                                          reading(25, 32), reading(35, 24), reading(45, 16)])
    assert site.state == RECEDING
    site = feed(site, [reading(55, 30), reading(65, 38)])
    assert site.state == CRITICAL


def test_fuse_takes_the_highest_credible_upper_end():
    low, high, confidence = fuse([(12, 20, 0.8), (15, 25, 0.6), (5, 60, 0.2)])
    assert (low, high) == (12, 25)      # the 0.2-confidence outlier does not set the top
    assert fuse([]) is None


def test_fuse_halves_confidence_when_estimates_disagree_widely():
    _, _, confidence = fuse([(2, 8, 0.8), (40, 70, 0.8)])
    assert confidence == 0.4
