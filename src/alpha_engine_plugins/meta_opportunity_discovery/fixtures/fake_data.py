"""Deterministic fake source-cylinder snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..contracts import CanonicalRecord, CanonicalSnapshot, Direction, RecordType

UTC = timezone.utc
AS_OF = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def _signal(ref: str, plugin: str, capability: str, direction: Direction, ancestry: str, minutes: int) -> CanonicalRecord:
    return CanonicalRecord(
        ref=ref,
        version="1",
        record_type=RecordType.SIGNAL,
        source_plugin_id=plugin,
        capability_family=capability,
        subject_refs=("subject:ACME",),
        effective_at=AS_OF - timedelta(minutes=minutes + 10),
        available_at=AS_OF - timedelta(minutes=minutes),
        direction=direction,
        support=Decimal("0.80"),
        quality=Decimal("0.90"),
        horizon_start=AS_OF,
        horizon_end=AS_OF + timedelta(days=7),
        evidence_refs=(f"evidence:{ref}",),
        ancestry_roots=(ancestry,),
    )


def fixture_valid_confluence() -> CanonicalSnapshot:
    records = (
        _signal("sig:market:1", "fake.market", "market", Direction.POSITIVE, "root:market", 20),
        _signal("sig:macro:1", "fake.macro", "macro", Direction.POSITIVE, "root:macro", 15),
        _signal("sig:narrative:1", "fake.narrative", "narrative", Direction.POSITIVE, "root:narrative", 10),
    )
    return CanonicalSnapshot("snapshot:valid", "1", AS_OF, "cap-hash-valid", records)


def fixture_duplicate_ancestry() -> CanonicalSnapshot:
    records = (
        _signal("sig:narrative:dup", "fake.narrative", "narrative", Direction.POSITIVE, "root:bulletin", 10),
        _signal("sig:institutional:dup", "fake.institutional", "institutional", Direction.POSITIVE, "root:bulletin", 9),
        _signal("sig:market:independent", "fake.market", "market", Direction.POSITIVE, "root:market", 8),
    )
    return CanonicalSnapshot("snapshot:duplicate", "1", AS_OF, "cap-hash-dup", records)


def fixture_lookahead() -> CanonicalSnapshot:
    future = CanonicalRecord(
        ref="sig:future:1",
        version="1",
        record_type=RecordType.SIGNAL,
        source_plugin_id="fake.market",
        capability_family="market",
        subject_refs=("subject:ACME",),
        effective_at=AS_OF - timedelta(hours=1),
        available_at=AS_OF + timedelta(minutes=1),
        direction=Direction.POSITIVE,
        support=Decimal("0.8"),
        quality=Decimal("0.9"),
        evidence_refs=("evidence:future",),
        ancestry_roots=("root:future",),
    )
    base = fixture_valid_confluence().records[:2]
    return CanonicalSnapshot("snapshot:lookahead", "1", AS_OF, "cap-hash-lookahead", (*base, future))


def fixture_event_chain() -> CanonicalSnapshot:
    event = CanonicalRecord(
        ref="event:policy:1",
        version="1",
        record_type=RecordType.EVENT,
        source_plugin_id="fake.macro",
        capability_family="macro_event",
        subject_refs=("subject:ACME",),
        effective_at=AS_OF - timedelta(hours=2),
        available_at=AS_OF - timedelta(hours=2),
        direction=Direction.NEUTRAL,
        support=Decimal("0.9"),
        quality=Decimal("0.95"),
        evidence_refs=("evidence:event:policy:1",),
        ancestry_roots=("root:policy",),
    )
    market = _signal("sig:market:after-event", "fake.market", "market", Direction.POSITIVE, "root:market2", 60)
    narrative = _signal("sig:narrative:after-event", "fake.narrative", "narrative", Direction.POSITIVE, "root:narr2", 45)
    return CanonicalSnapshot("snapshot:event-chain", "1", AS_OF, "cap-hash-event", (event, market, narrative))


def fixture_missing_narrative() -> CanonicalSnapshot:
    records = fixture_valid_confluence().records[:2]
    return CanonicalSnapshot("snapshot:missing-narrative", "1", AS_OF, "cap-hash-missing", records)


def fixture_stale_macro() -> CanonicalSnapshot:
    from dataclasses import replace

    records = list(fixture_valid_confluence().records)
    records[1] = replace(
        records[1],
        effective_at=AS_OF - timedelta(days=10, minutes=10),
        available_at=AS_OF - timedelta(days=10),
        horizon_start=AS_OF - timedelta(days=10),
        horizon_end=AS_OF + timedelta(days=2),
    )
    return CanonicalSnapshot("snapshot:stale", "1", AS_OF, "cap-hash-stale", tuple(records))


def fixture_conflict() -> CanonicalSnapshot:
    records = (
        _signal("sig:market:conflict", "fake.market", "market", Direction.POSITIVE, "root:market-c", 20),
        _signal("sig:macro:conflict", "fake.macro", "macro", Direction.NEGATIVE, "root:macro-c", 15),
        _signal("sig:narrative:conflict", "fake.narrative", "narrative", Direction.POSITIVE, "root:narrative-c", 10),
    )
    return CanonicalSnapshot("snapshot:conflict", "1", AS_OF, "cap-hash-conflict", records)


def fixture_many_hypotheses(subject_count: int = 12) -> CanonicalSnapshot:
    from dataclasses import replace

    records: list[CanonicalRecord] = []
    for i in range(subject_count):
        subject = f"subject:S{i:02d}"
        records.extend(
            replace(record, subject_refs=(subject,), ref=f"{record.ref}:S{i:02d}", evidence_refs=(f"evidence:{record.ref}:S{i:02d}",), ancestry_roots=(f"{record.ancestry_roots[0]}:S{i:02d}",))
            for record in fixture_valid_confluence().records
        )
    return CanonicalSnapshot("snapshot:broad-search", "1", AS_OF, "cap-hash-broad", tuple(records))


def fixture_self_reference() -> CanonicalSnapshot:
    from dataclasses import replace

    records = list(fixture_valid_confluence().records)
    records[0] = replace(
        records[0],
        ref="sig:meta:self",
        source_plugin_id="ae.meta_opportunity_discovery",
        producer_generation=1,
        ancestry_roots=("root:meta-self",),
    )
    return CanonicalSnapshot("snapshot:self-reference", "1", AS_OF, "cap-hash-self", tuple(records))


def fixture_disjoint_horizon() -> CanonicalSnapshot:
    from dataclasses import replace

    records = list(fixture_valid_confluence().records)
    records[2] = replace(
        records[2],
        horizon_start=AS_OF + timedelta(days=30),
        horizon_end=AS_OF + timedelta(days=37),
    )
    return CanonicalSnapshot("snapshot:disjoint", "1", AS_OF, "cap-hash-disjoint", tuple(records))


def fixture_currency_mismatch() -> CanonicalSnapshot:
    from dataclasses import replace

    records = list(fixture_valid_confluence().records)
    records[0] = replace(records[0], normalized_value=Decimal("100"), unit="currency", currency="USD")
    records[1] = replace(records[1], normalized_value=Decimal("100"), unit="currency", currency="EUR")
    return CanonicalSnapshot("snapshot:currency-mismatch", "1", AS_OF, "cap-hash-currency", tuple(records))


def fixture_rights_restricted() -> CanonicalSnapshot:
    from dataclasses import replace

    records = list(fixture_valid_confluence().records)
    records[2] = replace(records[2], rights_tags=("NO_MODEL", "EXPORT_RESTRICTED"))
    return CanonicalSnapshot("snapshot:rights", "1", AS_OF, "cap-hash-rights", tuple(records))


def fixture_cycle() -> CanonicalSnapshot:
    from dataclasses import replace
    from ..contracts import CanonicalRelationship

    a = replace(
        _signal("sig:cycle:a", "fake.market", "market", Direction.POSITIVE, "root:cycle-a", 10),
        subject_refs=("subject:A",),
        relationships=(
            CanonicalRelationship(
                target_subject_ref="subject:B",
                relation_type="SUPPORTS",
                confidence=Decimal("0.95"),
                evidence_refs=("evidence:relation:a-b",),
            ),
        ),
    )
    b = replace(
        _signal("sig:cycle:b", "fake.macro", "macro", Direction.POSITIVE, "root:cycle-b", 9),
        subject_refs=("subject:B",),
        relationships=(
            CanonicalRelationship(
                target_subject_ref="subject:A",
                relation_type="SUPPORTS",
                confidence=Decimal("0.95"),
                evidence_refs=("evidence:relation:b-a",),
            ),
        ),
    )
    return CanonicalSnapshot("snapshot:cycle", "1", AS_OF, "cap-hash-cycle", (a, b))
