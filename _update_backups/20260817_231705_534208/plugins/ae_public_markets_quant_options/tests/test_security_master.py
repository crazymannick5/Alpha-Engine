from datetime import date
import pytest
from ae_public_markets_quant_options.fixtures import fixture_security_master
from ae_public_markets_quant_options.errors import IdentityNotFound


def test_symbol_reuse_resolves_by_time():
    sm = fixture_security_master()
    assert sm.resolve_symbol("XYZ", date(2020, 6, 1), venue="XNYS").subject_id == "SUBJ-OLD"
    assert sm.resolve_symbol("XYZ", date(2026, 1, 1), venue="XNYS").subject_id == "SUBJ-NEW"


def test_identifier_temporal_resolution():
    sm = fixture_security_master()
    assert sm.resolve_identifier("FIGI", "OLD123", date(2019, 1, 1)).subject_id == "SUBJ-OLD"
    with pytest.raises(IdentityNotFound):
        sm.resolve_identifier("FIGI", "OLD123", date(2026, 1, 1))


def test_listing_history_is_sorted():
    sm = fixture_security_master()
    hist = sm.listing_history("SUBJ-NEW")
    assert hist[0].symbol == "XYZ"
