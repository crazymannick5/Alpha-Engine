from __future__ import annotations
from dataclasses import dataclass

from ..contracts.dto import DetectorResult
from ..detectors.arbitrage import ArbitrageDetector, DetectorPolicy
from ..domain.costs import CostStack
from ..domain.legs import ComparisonSnapshot
from ..domain.relationships import RelationshipEvaluation, RelationshipSpec
from ..persistence.repositories import RelationshipRepository
from ..resolution.resolver import ConservativeRelationshipResolver

@dataclass(frozen=True, slots=True)
class ComparisonRunResult:
    evaluation: RelationshipEvaluation
    detector_result: DetectorResult

class ArbitrageComparisonService:
    def __init__(self, repository: RelationshipRepository, resolver: ConservativeRelationshipResolver | None = None, detector: ArbitrageDetector | None = None):
        self.repository = repository
        self.resolver = resolver or ConservativeRelationshipResolver()
        self.detector = detector or ArbitrageDetector()

    def run(self, spec: RelationshipSpec, snapshot: ComparisonSnapshot, costs: CostStack, policy: DetectorPolicy) -> ComparisonRunResult:
        self.repository.save_spec(spec)
        evaluation = self.resolver.evaluate(spec, snapshot)
        self.repository.save_evaluation(evaluation)
        detector_result = self.detector.detect(spec, evaluation, snapshot, costs, policy)
        return ComparisonRunResult(evaluation, detector_result)
