from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from .domain import PMMarket, PMProviderAlias
from .errors import PMError, PMErrorCode
from .utils import require_utc, stable_hash


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    canonical_market_ref: str | None
    confidence: Decimal
    status: str
    candidates: tuple[str, ...]
    reason: str


def resolve_provider_alias(provider_id: str, provider_market_key: str, as_of: datetime,
                           aliases: Sequence[PMProviderAlias]) -> ResolutionResult:
    as_of = require_utc(as_of)
    matches = [a for a in aliases if a.provider_id == provider_id and a.provider_market_key == provider_market_key
               and a.valid_from <= as_of and (a.valid_to is None or as_of < a.valid_to)]
    if not matches:
        return ResolutionResult(None, Decimal("0"), "UNRESOLVED", (), "no active provider alias")
    canonical = sorted({a.canonical_market_ref for a in matches})
    if len(canonical) > 1:
        return ResolutionResult(None, max(a.confidence for a in matches), "AMBIGUOUS", tuple(canonical),
                                "multiple active canonical market aliases")
    confidence = max(a.confidence for a in matches)
    return ResolutionResult(canonical[0], confidence, "RESOLVED", tuple(canonical), "active provider alias")


def propose_alias(provider_id: str, provider_market_key: str, market: PMMarket, as_of: datetime,
                  *, confidence: Decimal, evidence_refs: tuple[str, ...]) -> PMProviderAlias:
    as_of = require_utc(as_of)
    if confidence < Decimal("0.5"):
        raise PMError(PMErrorCode.IDENTITY_AMBIGUOUS, "confidence below deterministic alias proposal threshold")
    ref = stable_hash("pm.provider_alias.v1", {
        "provider": provider_id, "key": provider_market_key, "canonical": market.market_ref,
        "valid_from": as_of, "evidence": evidence_refs,
    })
    return PMProviderAlias(alias_ref=ref, provider_id=provider_id, provider_market_key=provider_market_key,
                           canonical_market_ref=market.market_ref, valid_from=as_of, confidence=confidence,
                           evidence_refs=evidence_refs)


def compare_semantics(left: PMMarket, right: PMMarket) -> ResolutionResult:
    if left.semantic_fingerprint() == right.semantic_fingerprint():
        return ResolutionResult(left.market_ref, Decimal("1"), "SAME_PAYOFF", (left.market_ref, right.market_ref),
                                "normalized payoff semantics are identical")
    same_event = left.event_ref == right.event_ref
    same_kind = left.market_kind == right.market_kind
    if same_event and same_kind:
        return ResolutionResult(None, Decimal("0.7"), "NEAR_EQUIVALENT", (left.market_ref, right.market_ref),
                                "shared event/kind but differing payoff window/rules/threshold")
    return ResolutionResult(None, Decimal("1"), "NONE", (left.market_ref, right.market_ref), "payoff semantics differ")
