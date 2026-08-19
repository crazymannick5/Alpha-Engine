from __future__ import annotations
from decimal import Decimal

from ..domain.legs import ComparisonSnapshot
from ..domain.relationships import RelationshipEvaluation, RelationshipSpec
from ..domain.states import RelationshipStatus, RelationshipType


class ConservativeRelationshipResolver:
    algorithm_version = "1.0.0"

    def evaluate(self, spec: RelationshipSpec, snapshot: ComparisonSnapshot) -> RelationshipEvaluation:
        blockers: list[str] = []
        warnings: list[str] = []
        terms = []
        for leg in spec.legs:
            term = snapshot.terms.get(leg.leg_id)
            if term is None:
                blockers.append(f"MISSING_TERMS:{leg.leg_id}")
                continue
            terms.append((leg, term))
            if term.quantity_unit != leg.quantity_unit:
                blockers.append(f"UNIT_MISMATCH:{leg.leg_id}")
            if not term.authoritative:
                blockers.append(f"TERMS_UNVERIFIED:{leg.leg_id}")

        identity = Decimal("1") if not any(b.startswith("MISSING_TERMS") for b in blockers) else Decimal("0")
        payoff = Decimal("1")
        settlement = Decimal("1")
        transfer = Decimal("1")
        legal = Decimal("1")

        if terms:
            payoff_hashes = {term.payoff_hash for _, term in terms}
            settlement_rules = {term.settlement_rule_hash for _, term in terms}
            settlement_sources = {term.settlement_source for _, term in terms}
            legal_hashes = {term.legal_claim_hash for _, term in terms}
            transferability = {term.transferability for _, term in terms}
            maturities = {term.maturity_at for _, term in terms}

            if len(payoff_hashes) > 1 and spec.relationship_type not in {RelationshipType.SYNTHETIC_REPLICATION, RelationshipType.TERM_LOCATION_BASIS}:
                payoff = Decimal("0")
                blockers.append("PAYOFF_MISMATCH")
            if len(legal_hashes) > 1 and spec.relationship_type != RelationshipType.TERM_LOCATION_BASIS:
                legal = Decimal("0")
                blockers.append("LEGAL_CLAIM_MISMATCH")
            if len(transferability) > 1:
                transfer = Decimal("0.5")
                warnings.append("TRANSFERABILITY_MISMATCH")

            strict_semantics = spec.relationship_type in {
                RelationshipType.DIRECT_EQUIVALENCE,
                RelationshipType.PARITY,
                RelationshipType.PROBABILITY_CONSISTENCY,
            }
            if strict_semantics and (len(settlement_rules) > 1 or len(settlement_sources) > 1 or len(maturities) > 1):
                settlement = Decimal("0")
                blockers.append("SETTLEMENT_MISMATCH")
            elif len(settlement_rules) > 1 or len(settlement_sources) > 1 or len(maturities) > 1:
                settlement = Decimal("0.7")
                warnings.append("SETTLEMENT_BASIS_DIFFERENCE")

            delays = [term.transfer_delay_seconds for _, term in terms]
            if delays and max(delays) > 0:
                transfer = min(transfer, Decimal("0.8"))
                warnings.append("TRANSFER_DELAY")

        status = RelationshipStatus.VALIDATED if not blockers else RelationshipStatus.DISPUTED
        term_evidence = tuple(ref for _, term in terms for ref in term.evidence_refs)
        evidence = tuple(sorted(set(spec.evidence_refs + tuple(ref for quote in snapshot.quotes.values() for ref in quote.evidence_refs) + term_evidence)))
        return RelationshipEvaluation(
            relationship_id=spec.relationship_id,
            relationship_version=spec.version,
            status=status,
            identity_confidence=identity,
            payoff_confidence=payoff,
            settlement_confidence=settlement,
            transfer_confidence=transfer,
            legal_claim_confidence=legal,
            basis_risk_bound=spec.basis_risk_bound,
            blockers=tuple(sorted(set(blockers))),
            warnings=tuple(sorted(set(warnings))),
            evidence_refs=evidence,
            input_hash=snapshot.input_hash,
            algorithm_version=self.algorithm_version,
        )
