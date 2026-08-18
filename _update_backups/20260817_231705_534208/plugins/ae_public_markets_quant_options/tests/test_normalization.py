from datetime import datetime, timezone
from decimal import Decimal
import pytest
from ae_public_markets_quant_options.normalization import normalize_bar, normalize_quote, normalize_option_quote
from ae_public_markets_quant_options.models import QualityFlag


def test_bar_normalizes_decimal_and_time():
    row = {"subject_id":"S","effective_at":"2026-01-01T00:00:00+00:00","available_at":"2026-01-01T00:00:00+00:00","open":"10","high":"11","low":"9","close":"10.5","volume":"100","currency":"USD"}
    b = normalize_bar(row,"E")
    assert b.close == Decimal("10.5") and b.evidence_ref == "E"


def test_bar_rejects_bad_ohlc():
    row = {"subject_id":"S","effective_at":"2026-01-01T00:00:00+00:00","available_at":"2026-01-01T00:00:00+00:00","open":"10","high":"8","low":"9","close":"10.5","volume":"100","currency":"USD"}
    with pytest.raises(ValueError):
        normalize_bar(row,"E")


def test_crossed_quote_is_preserved_and_flagged():
    q = normalize_quote({"subject_id":"S","effective_at":"2026-01-01T00:00:00+00:00","available_at":"2026-01-01T00:00:00+00:00","bid":"11","ask":"10","currency":"USD"}, "E")
    assert QualityFlag.CROSSED_MARKET in q.quality_flags


def test_option_deliverable_unknown_is_flagged():
    q = normalize_option_quote({"contract_id":"O1","underlying_subject_id":"S","expiration":"2026-12-18","strike":"100","right":"CALL","currency":"USD","effective_at":"2026-01-01T00:00:00+00:00","available_at":"2026-01-01T00:00:00+00:00","bid":"1","ask":"2"}, "E")
    assert QualityFlag.OPTION_DELIVERABLE_UNKNOWN in q.quality_flags
