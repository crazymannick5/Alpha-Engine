from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from ..canonical import canonical_sha256
from ..contracts import OpportunityCandidate, SignalCandidate


class ClusterOpportunityDetector:
    version = "1.0.0"

    def detect(self, signals: list[SignalCandidate], *, horizon_days: int = 30) -> list[OpportunityCandidate]:
        out: list[OpportunityCandidate] = []
        for s in signals:
            if s.signal_type != "CLUSTERED_DISCLOSED_ACTIVITY":
                continue
            direction = "LONG" if s.features.get("direction") == "POSITIVE" else "SHORT"
            blockers = []
            if s.confidence < Decimal("0.75"):
                blockers.append("LOW_EVIDENCE_OR_IDENTITY_CONFIDENCE")
            actionability = "PAPER_ELIGIBLE" if not blockers else "BLOCKED"
            dedupe = canonical_sha256({"type": "cluster", "subjects": s.subject_refs, "availability": s.earliest_availability_at.date().isoformat(), "direction": direction})
            out.append(OpportunityCandidate(
                opportunity_type="COORDINATED_OR_CLUSTER_DISCLOSURE",
                thesis="Multiple independently resolved public actors disclosed same-direction activity in a bounded window; this may justify further research. No coordination, motive, wrongdoing, or privileged knowledge is inferred.",
                subject_refs=s.subject_refs,
                signal_hashes=(s.deterministic_hash(),),
                evidence_hashes=s.evidence_hashes,
                earliest_availability_at=s.earliest_availability_at,
                expires_at=s.earliest_availability_at + timedelta(days=horizon_days),
                actionability=actionability,
                direction=direction,
                blockers=tuple(blockers),
                uncertainty={"signal_confidence": Decimal("1") - s.confidence},
                detector_version=self.version,
                dedupe_key=dedupe,
            ))
        return out


class UnusualActivityOpportunityDetector:
    version = "1.0.0"

    def detect(self, signals: list[SignalCandidate], *, min_strength: Decimal = Decimal("0.45"), horizon_days: int = 21) -> list[OpportunityCandidate]:
        out = []
        for s in signals:
            if s.signal_type not in {"ACCUMULATION", "DISTRIBUTION", "INSTITUTIONAL_FLOW_PROXY"} or s.strength < min_strength:
                continue
            direction = "SHORT" if s.signal_type == "DISTRIBUTION" else "LONG"
            blockers = ["FLOW_PROXY_DELAY_CAVEAT"] if s.signal_type == "INSTITUTIONAL_FLOW_PROXY" else []
            dedupe = canonical_sha256({"type": "unusual_activity", "signal": s.deterministic_hash(), "direction": direction})
            out.append(OpportunityCandidate(
                opportunity_type="UNUSUAL_DISCLOSED_ACTIVITY",
                thesis="Publicly disclosed activity differs materially from the configured comparison baseline and may warrant research. The detector does not infer intent, legality, causation, or privileged information.",
                subject_refs=s.subject_refs,
                signal_hashes=(s.deterministic_hash(),),
                evidence_hashes=s.evidence_hashes,
                earliest_availability_at=s.earliest_availability_at,
                expires_at=s.earliest_availability_at + timedelta(days=horizon_days),
                actionability="RESEARCH" if blockers else "PAPER_ELIGIBLE",
                direction=direction,
                blockers=tuple(blockers),
                uncertainty={"signal_confidence": Decimal("1") - s.confidence},
                detector_version=self.version,
                dedupe_key=dedupe,
            ))
        return out
