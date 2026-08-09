from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..canonical import canonical_sha256
from ..contracts import ActivityCandidate, ActivitySemantic, HoldingSnapshot, SignalCandidate
from ..domain.rules import FilingRuleSet


def _confidence(activity: ActivityCandidate) -> Decimal:
    identity = activity.identity_confidence if activity.identity_confidence is not None else Decimal("0.5")
    return min(activity.parser_confidence, identity, activity.completeness)


class FilingDelayDetector:
    detector_id = "pii.filing_delay"
    version = "1.0.0"

    def detect(self, activity: ActivityCandidate, rules: FilingRuleSet) -> list[SignalCandidate]:
        effective = activity.times.effective_at or activity.times.transaction_at
        if effective is None:
            return []
        availability = activity.earliest_availability()
        elapsed = rules.delay_business_days(effective, availability)
        if elapsed is None:
            return []
        expected = rules.expected_business_days or 0
        excess = max(0, elapsed - expected)
        strength = min(Decimal("1"), Decimal(excess) / Decimal(max(1, expected * 3 or 3)))
        if excess <= 0:
            return []
        return [SignalCandidate(
            detector_id=self.detector_id,
            detector_version=self.version,
            signal_type="FILING_DELAY",
            subject_refs=tuple(x for x in (activity.actor.core_ref or activity.actor.source_key, activity.subject_ref) if x),
            effective_at=effective,
            earliest_availability_at=availability,
            strength=strength,
            confidence=_confidence(activity),
            evidence_hashes=(activity.evidence.artifact_hash,),
            activity_hashes=(activity.deterministic_hash(),),
            explanation=f"Disclosure became publicly available {elapsed} business days after activity; configured expected window is {expected} business days. This is a research timing feature, not a legal conclusion.",
            features={"elapsed_business_days": elapsed, "expected_business_days": expected, "legal_conclusion": False},
        )]


class AccumulationDetector:
    detector_id = "pii.accumulation_distribution"
    version = "1.0.0"

    def detect(self, activities: list[ActivityCandidate], *, min_count: int = 2) -> list[SignalCandidate]:
        groups: dict[tuple[str, str], list[ActivityCandidate]] = defaultdict(list)
        for a in activities:
            if a.semantic not in {ActivitySemantic.ACQUISITION, ActivitySemantic.DISPOSITION}:
                continue
            groups[(a.subject_ref or "unknown", a.direction)].append(a)
        out: list[SignalCandidate] = []
        for (subject, direction), rows in sorted(groups.items()):
            if len(rows) < min_count:
                continue
            rows.sort(key=lambda a: a.earliest_availability())
            values = [r.value.lower for r in rows if r.value and r.value.lower is not None]
            total = sum(values, Decimal("0")) if values else None
            strength = min(Decimal("1"), Decimal(len(rows)) / Decimal("5"))
            confidence = min((_confidence(r) for r in rows), default=Decimal("0"))
            out.append(SignalCandidate(
                detector_id=self.detector_id,
                detector_version=self.version,
                signal_type="ACCUMULATION" if direction == "POSITIVE" else "DISTRIBUTION",
                subject_refs=(subject,),
                effective_at=max((r.times.effective_at or r.times.transaction_at or r.times.ingested_at) for r in rows),
                earliest_availability_at=max(r.earliest_availability() for r in rows),
                strength=strength,
                confidence=confidence,
                evidence_hashes=tuple(sorted({r.evidence.artifact_hash for r in rows})),
                activity_hashes=tuple(r.deterministic_hash() for r in rows),
                explanation=f"{len(rows)} same-direction disclosed activities were observed for the subject under comparable transaction semantics.",
                features={"activity_count": len(rows), "known_lower_value_total": str(total) if total is not None else None},
                warnings=("value_total_excludes_unknown_or_ranged_upper_values",) if len(values) != len(rows) else (),
            ))
        return out


class ClusterDetector:
    detector_id = "pii.clustered_insiders"
    version = "1.0.0"

    def detect(
        self,
        activities: list[ActivityCandidate],
        *,
        window_days: int = 14,
        min_independent_actors: int = 3,
        minimum_identity_confidence: Decimal = Decimal("0.90"),
    ) -> list[SignalCandidate]:
        eligible = [a for a in activities if a.semantic in {ActivitySemantic.ACQUISITION, ActivitySemantic.DISPOSITION}]
        eligible.sort(key=lambda a: (a.earliest_availability(), a.actor.source_key))
        out: list[SignalCandidate] = []
        seen: set[str] = set()
        for i, anchor in enumerate(eligible):
            cutoff = anchor.earliest_availability() + timedelta(days=window_days)
            rows = [a for a in eligible[i:] if a.subject_ref == anchor.subject_ref and a.direction == anchor.direction and a.earliest_availability() <= cutoff]
            actors = {a.actor.core_ref or a.actor.source_key for a in rows if (a.identity_confidence or Decimal("0")) >= minimum_identity_confidence}
            if len(actors) < min_independent_actors:
                continue
            key = canonical_sha256({"subject": anchor.subject_ref, "direction": anchor.direction, "actors": sorted(actors), "start": anchor.earliest_availability(), "end": cutoff})
            if key in seen:
                continue
            seen.add(key)
            out.append(SignalCandidate(
                detector_id=self.detector_id,
                detector_version=self.version,
                signal_type="CLUSTERED_DISCLOSED_ACTIVITY",
                subject_refs=(anchor.subject_ref or "unknown",),
                effective_at=max((a.times.effective_at or a.times.ingested_at) for a in rows),
                earliest_availability_at=max(a.earliest_availability() for a in rows),
                strength=min(Decimal("1"), Decimal(len(actors)) / Decimal(max(min_independent_actors + 2, 5))),
                confidence=min((_confidence(a) for a in rows), default=Decimal("0")),
                evidence_hashes=tuple(sorted({a.evidence.artifact_hash for a in rows})),
                activity_hashes=tuple(a.deterministic_hash() for a in rows),
                explanation=f"{len(actors)} independently resolved actors disclosed same-direction activity within {window_days} days. The cluster is a pattern hypothesis and does not imply shared motive or coordination.",
                features={"independent_actor_count": len(actors), "window_days": window_days, "direction": anchor.direction},
                warnings=("coordination_not_inferred",),
            ))
        return out


class InstitutionalFlowDetector:
    detector_id = "pii.institutional_flow_proxy"
    version = "1.0.0"

    def detect(self, previous: list[HoldingSnapshot], current: list[HoldingSnapshot]) -> list[SignalCandidate]:
        prev = {(h.manager_source_key, h.security_key): h for h in previous}
        out: list[SignalCandidate] = []
        for cur in current:
            old = prev.get((cur.manager_source_key, cur.security_key))
            if old is None or old.shares == 0:
                continue
            delta = cur.shares - old.shares
            pct = delta / abs(old.shares)
            if abs(pct) < Decimal("0.10"):
                continue
            strength = min(Decimal("1"), abs(pct))
            availability = cur.filing_at
            out.append(SignalCandidate(
                detector_id=self.detector_id,
                detector_version=self.version,
                signal_type="INSTITUTIONAL_FLOW_PROXY",
                subject_refs=(cur.manager_source_key, cur.security_key),
                effective_at=datetime.combine(cur.period_end, datetime.min.time(), tzinfo=timezone.utc),
                earliest_availability_at=availability,
                strength=strength,
                confidence=Decimal("0.90"),
                evidence_hashes=(old.evidence.artifact_hash, cur.evidence.artifact_hash),
                activity_hashes=(canonical_sha256(old), canonical_sha256(cur)),
                explanation="Comparable 13F holding snapshots changed materially. This is a delayed snapshot-derived flow proxy, not direct trade evidence and not an intraperiod timing claim.",
                features={"share_delta": str(delta), "share_delta_fraction": str(pct), "previous_period": old.period_end.isoformat(), "current_period": cur.period_end.isoformat()},
                warnings=("13f_delayed_snapshot", "not_direct_trade_evidence"),
            ))
        return out
