"""Tests for the lookup structures, and properties that must hold for any input."""

import json
import random

import pytest

from nirmaldhara import geo
from nirmaldhara.bands import NO_GO_CM, PASSABLE, answer_for
from nirmaldhara.intake import distance_m
from nirmaldhara.publish import city_document, site_entry, to_json
from nirmaldhara.state import (CLEAR, CRITICAL, CRITICAL_DEPTH_CM, RECEDING, WARNING, WATCH,
                               Reading, Site, apply_rain, apply_reading, fuse)
from nirmaldhara.volume import VolumeCurve

HYDERABAD = (17.385, 78.4867)


# --- geo ---------------------------------------------------------------------

def test_geohash_matches_a_known_value():
    # Published example: 57.64911, 10.40744 -> u4pruydqqvj; first six characters.
    assert geo.encode(57.64911, 10.40744) == "u4pruy"


def test_cells_cover_every_point_inside_the_radius():
    rng = random.Random(1)
    lat, lon = HYDERABAD
    cells = geo.cells_covering(lat, lon, 500)
    assert len(cells) <= 9
    for _ in range(2000):
        plat = lat + rng.uniform(-0.006, 0.006)
        plon = lon + rng.uniform(-0.006, 0.006)
        if distance_m(lat, lon, plat, plon) <= 500:
            assert geo.encode(plat, plon) in cells


def test_exact_filter_drops_points_in_the_cell_but_outside_the_radius():
    lat, lon = HYDERABAD
    points = [("near", lat + 0.001, lon), ("far", lat + 0.02, lon)]
    assert geo.within(points, lat, lon, 500) == ["near"]


# --- volume ------------------------------------------------------------------

def v_trough():
    # Ramps of 4% and 5% meeting at the lowest point, 14 m wide.
    return VolumeCurve([(-60, 2.4), (0, 0.0), (40, 2.0)], 14)


def test_volume_matches_the_closed_form_for_a_v_trough():
    assert v_trough().volume(0.5) == pytest.approx(78.75)


def test_depth_is_the_inverse_of_volume():
    curve = VolumeCurve([(-60, 2.4), (-40, 1.5), (-20, 0.7), (0, 0.0), (20, 0.9), (40, 1.9)], 14)
    for depth in (0.0, 0.05, 0.12, 0.5, 0.9, 1.4, 1.9):
        assert curve.depth(curve.volume(depth)) == pytest.approx(depth, abs=1e-6)


def test_volume_never_falls_as_depth_rises():
    curve = VolumeCurve([(-50, 2.0), (-30, 1.6), (-5, 0.0), (5, 0.0), (35, 1.2)], 12)
    volumes = [curve.volume(d / 100) for d in range(0, 201)]
    assert all(b >= a for a, b in zip(volumes, volumes[1:]))
    assert curve.volume(-1) == 0 and curve.volume(99) == volumes[-1]


def test_flat_bottom_holds_water_from_the_first_centimetre():
    curve = VolumeCurve([(-10, 1.0), (0, 0.0), (10, 0.0), (20, 1.0)], 10)
    assert curve.volume(0.01) == pytest.approx(10 * (10 * 0.01 + 20 * 0.01 * 0.01 / 2))


# --- publish -----------------------------------------------------------------

def test_map_file_is_sorted_compact_and_small():
    readings = tuple(Reading(1760000000 - 60 * k, 14, 19, c, "guardian", "g1")
                     for k, c in enumerate((0.9, 0.75, 0.8)))
    site = Site("x", state=WARNING, low=14.4, high=18.6, trusted=True, readings=readings)
    entries = [site_entry(f"hyd-{i:03d}", f"Underpass {i}", 17.3 + i / 1e4, 78.4, site, 1760000000)
               for i in range(499, -1, -1)]
    text = to_json(city_document("hyderabad", 1760000000, entries))
    document = json.loads(text)
    assert [e[0] for e in document["sites"][:2]] == ["hyd-000", "hyd-001"]
    assert document["sites"][0][4:9] == [WARNING, "B2", 14, 19, 1]
    assert document["fields"][-1] == "c" and document["sites"][0][10] == 0.75
    assert len(text.encode()) < 50_000        # 500 sites, before compression


def test_confidence_column_is_the_weakest_of_the_smoothed_readings():
    weak = tuple(Reading(t, 10, 15, c, "resident", "p") for t, c in ((1, 0.9), (2, 0.5), (3, 0.8)))
    assert site_entry("a", "A", 17.3, 78.4, Site("a", readings=weak), 3)[10] == 0.5
    assert site_entry("a", "A", 17.3, 78.4, Site("a"), 3)[10] == 0.0   # no reading yet


# --- properties that must hold for any input ---------------------------------

def test_deeper_water_is_never_more_passable():
    for vehicle in NO_GO_CM:
        for moving in (False, True):
            answers = [answer_for(vehicle, d, d, 0.9, moving) == PASSABLE for d in range(0, 80)]
            first_no = answers.index(False)
            assert not any(answers[first_no:])


def test_lower_confidence_is_never_more_passable():
    for vehicle in NO_GO_CM:
        for depth in range(0, 60, 3):
            high = answer_for(vehicle, depth, depth, 0.9) == PASSABLE
            low = answer_for(vehicle, depth, depth, 0.3) == PASSABLE
            assert high or not low


def test_fuse_always_returns_an_ordered_range():
    rng = random.Random(2)
    for _ in range(500):
        estimates = []
        for _ in range(rng.randint(1, 6)):
            low = rng.uniform(0, 80)
            estimates.append((low, low + rng.uniform(0, 30), rng.uniform(0.1, 1.0)))
        low, high, confidence = fuse(estimates)
        assert 0 <= low <= high
        assert 0 < confidence <= 1


def test_state_engine_invariants_hold_for_random_histories():
    rng = random.Random(3)
    for _ in range(300):
        site, ts = Site("s"), 0
        for _ in range(40):
            ts += rng.choice([30, 60, 300, 900])
            before = site
            if rng.random() < 0.3:
                site = apply_rain(site, rng.uniform(0, 60), ts)
            else:
                high = rng.uniform(0, 90)
                site = apply_reading(site, Reading(
                    ts, max(0, high - rng.uniform(0, 15)), high, rng.uniform(0.3, 1.0),
                    rng.choice(["guardian", "cctv", "resident"]), rng.choice(["a", "b", "c"])))

            assert site.version == before.version + 1
            assert site.state in (CLEAR, WATCH, WARNING, CRITICAL, RECEDING)
            assert site.low <= site.high
            assert len(site.readings) <= 12
            changed = [e for e in site.events if e[0] == "SiteStateChanged"]
            assert bool(changed) == (site.state != before.state)
            # A site can only reach CRITICAL on critical depth vouched for by a trusted source.
            if site.state == CRITICAL and before.state != CRITICAL:
                assert site.high >= CRITICAL_DEPTH_CM and site.trusted
