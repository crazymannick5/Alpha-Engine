from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from ..contracts import (
    ActivityCandidate, ActivitySemantic, DisclosureRevisionRef, DisclosureTimes,
    EvidenceLocator, RangeMoney, ResolutionState, SourceFamily, SourceRecordKey, SubjectResolution,
)


def _range(value: Mapping[str, Any] | None, *, currency: str = "USD") -> RangeMoney | None:
    if not value:
        return None
    lower = Decimal(str(value["lower"])) if value.get("lower") is not None else None
    upper = Decimal(str(value["upper"])) if value.get("upper") is not None else None
    if lower is None and upper is None:
        return None
    return RangeMoney(
        lower=lower,
        upper=upper,
        currency=str(value.get("currency") or currency),
        bound_kind=str(value.get("bound_kind") or "closed"),
        source_label=value.get("source_label"),
    )


def normalize_public_record(record: Mapping[str, Any], *, ingested_at: datetime) -> ActivityCandidate:
    """Normalize a sanctioned already-acquired public record envelope.

    The caller/core remains responsible for acquisition, artifact registration, terms/use policy,
    and canonical adoption. This function intentionally accepts a source-neutral mapping so manual
    imports and future official adapters share the same deterministic semantic path.
    """
    family = SourceFamily(str(record["source_family"]))
    semantic = ActivitySemantic(str(record["semantic"]))
    source_record = SourceRecordKey(
        provider_id=str(record["provider_id"]),
        source_id=str(record["source_id"]),
        jurisdiction_id=str(record["jurisdiction_id"]),
        native_id=str(record["native_id"]),
    )
    actor_source_key = str(record["actor_source_key"])
    times = DisclosureTimes(
        transaction_at=record.get("transaction_at"),
        execution_at=record.get("execution_at"),
        effective_at=record.get("effective_at"),
        filing_at=record.get("filing_at"),
        accepted_at=record.get("accepted_at"),
        published_at=record.get("published_at"),
        ingested_at=ingested_at,
        source_timezone=record.get("source_timezone"),
    )
    direction = str(record.get("direction") or "NEUTRAL")
    if direction not in {"POSITIVE", "NEGATIVE", "NEUTRAL"}:
        raise ValueError("PII_DIRECTION_INVALID")
    return ActivityCandidate(
        source_record=source_record,
        source_family=family,
        filing_type=str(record["filing_type"]),
        revision=DisclosureRevisionRef(
            source_record_key=source_record.stable_key(),
            revision_no=int(record.get("revision_no", 1)),
            amendment_kind=str(record.get("amendment_kind") or "original"),
            supersedes_source_key=record.get("supersedes_source_key"),
            source_declared_amendment=bool(record.get("source_declared_amendment", False)),
        ),
        line_key=str(record.get("line_key") or "1"),
        actor=SubjectResolution(source_key=actor_source_key, state=ResolutionState.UNRESOLVED),
        subject_ref=record.get("subject_ref"),
        security_ref=record.get("security_ref"),
        security_title_source=record.get("security_title_source"),
        role=record.get("role"),
        semantic=semantic,
        source_code=record.get("source_code"),
        direction=direction,
        quantity=Decimal(str(record["quantity"])) if record.get("quantity") is not None else None,
        price=_range(record.get("price")),
        value=_range(record.get("value")),
        ownership_percent=Decimal(str(record["ownership_percent"])) if record.get("ownership_percent") is not None else None,
        times=times,
        evidence=EvidenceLocator(
            artifact_hash=str(record["artifact_hash"]),
            field_paths=tuple(str(x) for x in record.get("field_paths", ())),
            source_url=record.get("source_url"),
            source_label=str(record["source_label"]),
        ),
        parser_id=str(record.get("parser_id") or "pii.public_record_envelope"),
        parser_version=str(record.get("parser_version") or "1.0.0"),
        source_schema_version=str(record.get("source_schema_version") or "1"),
        ruleset_id=str(record["ruleset_id"]),
        parser_confidence=Decimal(str(record.get("parser_confidence", "1"))),
        completeness=Decimal(str(record.get("completeness", "1"))),
        quality_flags=tuple(str(x) for x in record.get("quality_flags", ())),
        metadata=dict(record.get("metadata", {})),
    )
