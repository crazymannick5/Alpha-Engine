"""Validate optional model-suggested hypotheses before deterministic discovery.

The model, if one is ever supplied by the core, receives no tool authority.  Its
output is only a structured proposal.  This validator rejects rights-prohibited,
missing, self-referential, single-domain, or malformed proposals before they can
become detector inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from ..contracts import CanonicalRecord
from ..hashing import sha256_canonical

_FORBIDDEN_MODEL_RIGHTS = frozenset({"NO_MODEL", "MODEL_FORBIDDEN", "NO_AI_PROCESSING"})


@dataclass(frozen=True, slots=True)
class ModelHypothesisProposal:
    proposal_id: str
    contributor_refs: tuple[str, ...]
    hypothesis: str
    confidence: Decimal
    suggested_relation_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.hypothesis.strip():
            raise ValueError("proposal id and hypothesis are required")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("model proposal confidence must be in [0,1]")


@dataclass(frozen=True, slots=True)
class ValidatedModelProposal:
    proposal_id: str
    contributor_refs: tuple[str, ...]
    capability_families: tuple[str, ...]
    hypothesis: str
    model_confidence: Decimal
    validation_fingerprint: str


def validate_model_proposal(
    proposal: ModelHypothesisProposal,
    records_by_identity: Mapping[str, CanonicalRecord],
    *,
    current_plugin_id: str = "ae.meta_opportunity_discovery",
    current_generation: int = 1,
    max_contributors: int = 12,
) -> ValidatedModelProposal:
    refs = tuple(sorted(set(proposal.contributor_refs)))
    if len(refs) < 2:
        raise ValueError("MODEL_PROPOSAL_REQUIRES_MULTI_SOURCE_CONTRIBUTORS")
    if len(refs) > max_contributors:
        raise ValueError("MODEL_PROPOSAL_TOO_MANY_CONTRIBUTORS")

    records: list[CanonicalRecord] = []
    for ref in refs:
        record = records_by_identity.get(ref)
        if record is None:
            raise ValueError(f"MODEL_PROPOSAL_UNKNOWN_CONTRIBUTOR:{ref}")
        if _FORBIDDEN_MODEL_RIGHTS & set(record.rights_tags):
            raise ValueError(f"MODEL_PROPOSAL_RIGHTS_BLOCK:{ref}")
        if record.source_plugin_id == current_plugin_id and record.producer_generation >= current_generation:
            raise ValueError(f"MODEL_PROPOSAL_SELF_REFERENCE:{ref}")
        records.append(record)

    capabilities = tuple(sorted({record.capability_family for record in records}))
    if len(capabilities) < 2:
        raise ValueError("MODEL_PROPOSAL_NOT_CROSS_DOMAIN")
    fingerprint = sha256_canonical(
        {
            "validator": "meta.model_candidate.validator.v1",
            "proposal": proposal.proposal_id,
            "contributors": refs,
            "capabilities": capabilities,
            "hypothesis": proposal.hypothesis.strip(),
            "relations": tuple(sorted(proposal.suggested_relation_types)),
        }
    )
    return ValidatedModelProposal(
        proposal_id=proposal.proposal_id,
        contributor_refs=refs,
        capability_families=capabilities,
        hypothesis=proposal.hypothesis.strip(),
        model_confidence=proposal.confidence,
        validation_fingerprint=fingerprint,
    )
