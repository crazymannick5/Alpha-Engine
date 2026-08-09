"""Cross-domain alignment over already-canonical records."""

from __future__ import annotations

from decimal import Decimal

from ..config import MetaDiscoveryConfig
from ..contracts import AlignedContribution, CanonicalSnapshot, FreshnessStatus
from .temporal import freshness


def align_snapshot(snapshot: CanonicalSnapshot, config: MetaDiscoveryConfig) -> tuple[tuple[AlignedContribution, ...], tuple[str, ...]]:
    aligned: list[AlignedContribution] = []
    warnings: list[str] = []
    for record in sorted(snapshot.records, key=lambda r: (r.available_at, r.ref, r.version)):
        if record.available_at > snapshot.as_of:
            warnings.append(f"LOOKAHEAD_EXCLUDED:{record.identity}")
            continue
        if record.quality < config.min_contributor_quality:
            warnings.append(f"LOW_QUALITY_EXCLUDED:{record.identity}")
            continue
        status, score = freshness(
            record,
            as_of=snapshot.as_of,
            stale_after=config.stale_after,
            expired_after=config.expired_after,
        )
        if status is FreshnessStatus.EXPIRED:
            warnings.append(f"EXPIRED_EXCLUDED:{record.identity}")
            continue
        record_warnings: list[str] = []
        if status is FreshnessStatus.STALE:
            record_warnings.append("STALE")
        if record.rights_tags:
            record_warnings.append("RIGHTS_METADATA_PRESENT")
        aligned.append(
            AlignedContribution(
                record=record,
                freshness_status=status,
                freshness_score=score,
                temporal_score=Decimal("1"),
                warnings=tuple(record_warnings),
            )
        )
    return tuple(aligned), tuple(warnings)
