from nirmaldhara.rain import build_url, grid_cells, parse

SITES = [("hyd-001", 17.385, 78.4867), ("hyd-002", 17.44, 78.38)]


def location(values):
    return {"hourly": {"time": [], "precipitation": values}}


def test_one_request_covers_every_site():
    url = build_url(SITES)
    assert "latitude=17.385%2C17.44" in url
    assert "longitude=78.4867%2C78.38" in url


def test_parse_splits_past_and_coming_hours():
    payload = [location([1.0, 2.0, 4.0, 6.0, 9.0, 3.0]),
               location([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    amounts = parse(SITES, payload)
    # Last complete hour, total of the three complete hours, larger of the next two.
    assert amounts["hyd-001"] == (4.0, 7.0, 9.0)
    assert amounts["hyd-002"] == (0.0, 0.0, 0.0)


def test_single_site_response_is_not_a_list():
    assert parse(SITES[:1], location([0.5, 0.5, 0.5, 2.0, 1.0, 0.0])) == {
        "hyd-001": (0.5, 1.5, 2.0)}


def test_missing_values_count_as_no_rain():
    assert parse(SITES[:1], location([None, 1.0, None, None, 2.0, 0.0])) == {
        "hyd-001": (0.0, 1.0, 2.0)}


def test_nearby_sites_share_one_forecast_point():
    sites = [("a", 17.401, 78.401), ("b", 17.412, 78.398), ("c", 17.52, 78.40)]
    cells = grid_cells(sites)
    assert cells == {(17.4, 78.4): ["a", "b"], (17.5, 78.4): ["c"]}
