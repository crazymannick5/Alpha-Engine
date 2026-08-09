from alpha_engine_prediction_markets.fixtures import fixture_by_id, fixture_catalog


def test_all_15_required_fixtures_are_present_and_unique():
    fixtures = fixture_catalog()
    assert len(fixtures) == 15
    ids = [x.fixture_id for x in fixtures]
    assert ids == [f"PM-FIX-{i:03d}" for i in range(1, 16)]
    assert len(ids) == len(set(ids))


def test_fixture_lookup():
    assert fixture_by_id("PM-FIX-014").expected == ("PM_BOOK_SEQUENCE_GAP", "resnapshot_required")
