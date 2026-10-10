"""scripts/simulate_inflow.py: the storage equation on made floods, and what its report may say.

A short run is made here, of six storms, to check that the figures the floods were made with come
back and that a forecast from too little rain fails. The report in docs/ is the full run. It is
labelled as made up and is never quoted where accuracy is claimed.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_inflow as sim  # noqa: E402


@pytest.fixture(scope="module")
def result():
    return sim.run(count=6)


def test_the_figures_the_floods_were_made_with_come_back(result):
    for label in sim.DOUBTS:
        found = result["revealed"][label]["three floods"]
        assert found.area_m2.low < sim.AREA < found.area_m2.high, label
        assert found.drain_m3s.low < sim.DRAIN < found.drain_m3s.high, label
    close, loose = (result["revealed"][label]["three floods"].area_m2 for label in sim.DOUBTS)
    assert loose.high - loose.low > close.high - close.low                     # looser readings, a wider answer


def test_a_flood_is_foretold_from_the_ones_before_it_when_the_rain_is_right_and_not_when_it_is_a_fifth(result):
    for label in sim.DOUBTS:
        exact, fifth = (sim.held(result["forward"][(label, how)]) for how in ("known exactly", "a fifth of what fell"))
        assert exact[1] == fifth[1] == 5 and exact[0] == 5 and fifth[0] == 0, label


def test_the_rain_that_closes_the_road_is_found_to_within_its_range(result):
    for vehicle, (true, (least, most)) in result["guidance"].items():
        assert least <= true <= most and most - least < 0.3 * true, vehicle
    assert result["guidance"]["two_wheeler"][0] < result["guidance"]["car"][0] < result["guidance"]["suv"][0]


def test_the_made_site_is_the_methods_worked_example_and_the_storms_differ(result):
    assert sim.PROFILE == [(-60, 2.4), (0, 0.0), (40, 2.0)] and sim.WIDTH == 14
    totals = [total for total, _ in result["storms"]]
    assert len(totals) == 6 and min(totals) >= 15 and max(totals) <= 80 and len({round(t) for t in totals}) > 3
    assert sim.run(count=3)["storms"] == result["storms"][:3]                  # the same storms every time it is run


def test_the_report_is_labelled_simulated_and_says_what_it_is_not():
    report = sim.OUT.read_text("utf-8")
    assert report.splitlines()[2].startswith("**SIMULATED. No real place, rain or flood is behind any number here.**")
    flat = " ".join(report.split())
    for must_say in ("It cannot show that a real underpass behaves this way", "No place in this project has a flood on record",
                     "The figures come back because the water was made by the same equation", "A forecast from rain is no better than the rain",
                     "Neither knows that the rain will ease or grow", "Not a test of the equation", "Not connected to anything",
                     "| A painted gauge, 3 cm | A fifth of what fell | 0 of 23 |"):
        assert must_say in flat, must_say
    for name in ("README.md", "docs/submission-writeup.md", "docs/video-script.md"):
        assert "inflow-simulation" not in (ROOT / name).read_text("utf-8"), name       # made floods are never quoted as accuracy
