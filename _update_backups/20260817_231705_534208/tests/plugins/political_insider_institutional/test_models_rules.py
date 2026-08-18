from datetime import datetime, timezone, date
from decimal import Decimal
import pytest

from alpha_engine.plugins.political_insider_institutional.canonical import canonical_sha256
from alpha_engine.plugins.political_insider_institutional.contracts import RangeMoney, DisclosureTimes
from alpha_engine.plugins.political_insider_institutional.domain.rules import BusinessCalendar, FilingRuleSet


def test_range_preserves_bounds_and_exactness():
    r = RangeMoney(lower=Decimal("1001"), upper=Decimal("15000"), source_label="$1,001-$15,000")
    assert r.lower == Decimal("1001")
    assert r.upper == Decimal("15000")
    assert not r.exact


def test_range_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        RangeMoney(lower=Decimal("2"), upper=Decimal("1"))


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        DisclosureTimes(ingested_at=datetime(2026, 1, 1))


def test_canonical_hash_is_deterministic():
    a = {"b": Decimal("1.00"), "a": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    b = {"a": datetime(2026, 1, 1, tzinfo=timezone.utc), "b": Decimal("1.00")}
    assert canonical_sha256(a) == canonical_sha256(b)


def test_business_day_rule():
    cal = BusinessCalendar(holidays=frozenset({date(2026, 7, 3)}))
    rules = FilingRuleSet("us.sec.form4@1", "US", "sec_edgar", "4", date(2020, 1, 1), expected_business_days=2, calendar=cal)
    start = datetime(2026, 7, 2, tzinfo=timezone.utc)
    assert rules.expected_deadline(start) == date(2026, 7, 7)
