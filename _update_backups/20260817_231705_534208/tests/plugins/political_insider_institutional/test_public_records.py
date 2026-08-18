from datetime import datetime, timezone
from decimal import Decimal

from alpha_engine.plugins.political_insider_institutional.contracts import SourceFamily, ActivitySemantic
from alpha_engine.plugins.political_insider_institutional.normalization.public_records import normalize_public_record

NOW = datetime(2026, 7, 10, 15, tzinfo=timezone.utc)


def test_public_official_range_stays_range():
    record = {
        "source_family": "public_official", "semantic": "ACQUISITION",
        "provider_id": "us_house", "source_id": "house_ptr", "jurisdiction_id": "US", "native_id": "ptr-1",
        "actor_source_key": "house:member:1", "subject_ref": "issuer:example", "filing_type": "PTR",
        "transaction_at": datetime(2026, 6, 20, tzinfo=timezone.utc),
        "published_at": NOW, "artifact_hash": "sha256:ptr", "source_label": "House PTR ptr-1",
        "ruleset_id": "us.house.ptr@1", "direction": "POSITIVE",
        "value": {"lower": "1001", "upper": "15000", "currency": "USD", "source_label": "$1,001-$15,000"},
        "field_paths": ["transactions[0].amount"],
    }
    row = normalize_public_record(record, ingested_at=NOW)
    assert row.source_family == SourceFamily.PUBLIC_OFFICIAL
    assert row.semantic == ActivitySemantic.ACQUISITION
    assert row.value.lower == Decimal("1001") and row.value.upper == Decimal("15000")
    assert not row.value.exact


def test_lobbying_and_procurement_semantics_are_supported():
    common = {
        "provider_id": "official", "jurisdiction_id": "US", "native_id": "1",
        "actor_source_key": "org:1", "subject_ref": "agency:1", "filing_type": "report",
        "effective_at": NOW, "published_at": NOW, "artifact_hash": "sha256:x",
        "source_label": "official record", "ruleset_id": "rule@1", "direction": "NEUTRAL",
    }
    lobbying = normalize_public_record({**common, "source_id":"lda", "source_family":"lobbying", "semantic":"LOBBYING_ACTIVITY"}, ingested_at=NOW)
    procurement = normalize_public_record({**common, "native_id":"2", "source_id":"usaspending", "source_family":"procurement", "semantic":"PROCUREMENT_AWARD"}, ingested_at=NOW)
    assert lobbying.semantic == ActivitySemantic.LOBBYING_ACTIVITY
    assert procurement.semantic == ActivitySemantic.PROCUREMENT_AWARD
