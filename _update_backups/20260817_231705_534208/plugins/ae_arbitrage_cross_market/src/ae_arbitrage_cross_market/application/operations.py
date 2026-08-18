from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable

from ..canonical import canonical_hash
from ..domain.costs import CostStack
from ..domain.legs import ComparisonSnapshot
from ..domain.relationships import RelationshipSpec
from ..detectors.arbitrage import DetectorPolicy
from ..persistence.repositories import CheckpointRepository
from .service import ArbitrageComparisonService, ComparisonRunResult

@dataclass(frozen=True, slots=True)
class DetectionWorkItem:
    spec: RelationshipSpec
    snapshot: ComparisonSnapshot
    costs: CostStack
    policy: DetectorPolicy

@dataclass(frozen=True, slots=True)
class BatchRunResult:
    status: str
    processed: int
    output_hash: str
    skipped_completed_partition: bool
    results: tuple[ComparisonRunResult, ...]

class DetectionBatchRunner:
    def __init__(self, service: ArbitrageComparisonService, checkpoints: CheckpointRepository):
        self.service = service
        self.checkpoints = checkpoints

    def run(self, operation_id: str, partition_key: str, items: Iterable[DetectionWorkItem], *, is_cancelled: Callable[[], bool] = lambda: False) -> BatchRunResult:
        bounded = tuple(items)
        watermark = canonical_hash(tuple((item.spec.relationship_id, item.spec.version, item.snapshot.input_hash, item.costs.version) for item in bounded), schema="arb.detect.partition.v1")
        prior = self.checkpoints.get(operation_id, partition_key)
        if prior and prior.get("status") == "COMPLETE" and prior.get("cursor") == watermark:
            return BatchRunResult("COMPLETE", 0, prior["output_hash"], True, ())
        results = []
        fingerprints = []
        for index, item in enumerate(bounded):
            if is_cancelled():
                output_hash = canonical_hash(tuple(fingerprints), schema="arb.detect.outputs.v1")
                self.checkpoints.put(operation_id, partition_key, watermark, output_hash, "CANCELLED")
                return BatchRunResult("CANCELLED", index, output_hash, False, tuple(results))
            result = self.service.run(item.spec, item.snapshot, item.costs, item.policy)
            results.append(result)
            fingerprints.extend(op.fingerprint for op in result.detector_result.opportunities)
        output_hash = canonical_hash(tuple(sorted(fingerprints)), schema="arb.detect.outputs.v1")
        self.checkpoints.put(operation_id, partition_key, watermark, output_hash, "COMPLETE")
        return BatchRunResult("COMPLETE", len(results), output_hash, False, tuple(results))
