"""Strict mapping adapter for the future frozen public core boundary.

No core-private imports appear here.  The adapter accepts plain mappings or objects
already serialized by a public PDK and validates them into plugin-private views.
When the frozen PDK supplies exact classes, only this plugin-owned adapter should
need revision.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from ..contracts import (
    CanonicalRecord,
    CanonicalRelationship,
    CanonicalSnapshot,
    Direction,
    MetaCandidate,
    RecordType,
)


class CoreBoundaryError(ValueError):
    pass


def _dt(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise CoreBoundaryError(f"{field}: expected datetime/ISO string")
    if dt.tzinfo is None:
        raise CoreBoundaryError(f"{field}: timezone required")
    return dt


def _decimal(value: Any, field: str, default: str) -> Decimal:
    try:
        return Decimal(str(default if value is None else value))
    except Exception as exc:  # noqa: BLE001 - boundary wraps exact failure
        raise CoreBoundaryError(f"{field}: invalid decimal") from exc


def _enum(enum_type: type, value: Any, field: str):
    try:
        return enum_type(str(value))
    except Exception as exc:  # noqa: BLE001
        raise CoreBoundaryError(f"{field}: unsupported value {value!r}") from exc


def record_from_mapping(row: Mapping[str, Any]) -> CanonicalRecord:
    relationships = tuple(
        CanonicalRelationship(
            target_subject_ref=str(rel["target_subject_ref"]),
            relation_type=str(rel["relation_type"]),
            confidence=_decimal(rel.get("confidence"), "relationship.confidence", "0"),
            evidence_refs=tuple(map(str, rel.get("evidence_refs", ()))),
            valid_from=_dt(rel["valid_from"], "relationship.valid_from") if rel.get("valid_from") else None,
            valid_to=_dt(rel["valid_to"], "relationship.valid_to") if rel.get("valid_to") else None,
            causal_claim=bool(rel.get("causal_claim", False)),
        )
        for rel in row.get("relationships", ())
    )
    try:
        return CanonicalRecord(
            ref=str(row["ref"]),
            version=str(row["version"]),
            record_type=_enum(RecordType, row["record_type"], "record_type"),
            source_plugin_id=str(row["source_plugin_id"]),
            capability_family=str(row["capability_family"]),
            subject_refs=tuple(map(str, row.get("subject_refs", ()))),
            effective_at=_dt(row["effective_at"], "effective_at"),
            available_at=_dt(row["available_at"], "available_at"),
            direction=_enum(Direction, row.get("direction", "UNKNOWN"), "direction"),
            support=_decimal(row.get("support"), "support", "0.5"),
            quality=_decimal(row.get("quality"), "quality", "0.5"),
            normalized_value=_decimal(row.get("normalized_value"), "normalized_value", "0") if row.get("normalized_value") is not None else None,
            unit=str(row["unit"]) if row.get("unit") is not None else None,
            currency=str(row["currency"]) if row.get("currency") is not None else None,
            horizon_start=_dt(row["horizon_start"], "horizon_start") if row.get("horizon_start") else None,
            horizon_end=_dt(row["horizon_end"], "horizon_end") if row.get("horizon_end") else None,
            evidence_refs=tuple(map(str, row.get("evidence_refs", ()))),
            ancestry_roots=tuple(map(str, row.get("ancestry_roots", ()))),
            relationships=relationships,
            rights_tags=tuple(map(str, row.get("rights_tags", ()))),
            producer_generation=int(row.get("producer_generation", 0)),
            metadata={str(k): str(v) for k, v in dict(row.get("metadata", {})).items()},
        )
    except KeyError as exc:
        raise CoreBoundaryError(f"missing required field: {exc.args[0]}") from exc


def snapshot_from_mapping(payload: Mapping[str, Any]) -> CanonicalSnapshot:
    try:
        records = tuple(record_from_mapping(row) for row in payload.get("records", ()))
        return CanonicalSnapshot(
            snapshot_id=str(payload["snapshot_id"]),
            snapshot_version=str(payload["snapshot_version"]),
            as_of=_dt(payload["as_of"], "as_of"),
            capability_inventory_hash=str(payload["capability_inventory_hash"]),
            records=records,
        )
    except KeyError as exc:
        raise CoreBoundaryError(f"missing required snapshot field: {exc.args[0]}") from exc


def candidate_to_core_mapping(candidate: MetaCandidate) -> dict[str, Any]:
    """Return a structured, lossless handoff mapping for core validation.

    This deliberately does not pretend to instantiate an unfrozen central
    OpportunityCandidate class.  It is the exact plugin-owned payload that the
    future PDK adapter can map field-for-field.
    """
    return {
        "origin_plugin_id": "ae.meta_opportunity_discovery",
        "candidate_type": candidate.candidate_type,
        "family": candidate.family,
        "detector_id": candidate.detector_id,
        "detector_version": candidate.detector_version,
        "title": candidate.title,
        "thesis": candidate.thesis,
        "subject_refs": list(candidate.subject_refs),
        "contributor_refs": list(candidate.contributor_refs),
        "source_capabilities": list(candidate.source_capabilities),
        "direction": candidate.direction.value,
        "confidence": str(candidate.confidence),
        "actionability": candidate.actionability.value,
        "blockers": list(candidate.blockers),
        "deduplication_fingerprint": candidate.fingerprint,
        "features": [
            {
                "name": f.name,
                "value": None if f.value is None else str(f.value),
                "missing_reason": f.missing_reason,
                "algorithm_version": f.algorithm_version,
                "evidence_refs": list(f.evidence_refs),
            }
            for f in candidate.features
        ],
        "explanation": {
            "graph_hash": candidate.explanation.graph_hash,
            "contributor_refs": list(candidate.explanation.contributor_refs),
            "relationship_ids": list(candidate.explanation.relationship_ids),
            "counter_evidence_refs": list(candidate.explanation.counter_evidence_refs),
            "warnings": list(candidate.explanation.warnings),
            "assumptions": list(candidate.explanation.assumptions),
            "reproducibility_key": candidate.explanation.reproducibility_key,
            "independence_groups": [
                {
                    "group_id": g.group_id,
                    "member_refs": list(g.member_refs),
                    "quality": str(g.quality),
                    "support": str(g.support),
                    "ancestry_known": g.ancestry_known,
                }
                for g in candidate.explanation.independence_groups
            ],
        },
    }
