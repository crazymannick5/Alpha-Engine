"""End-to-end deterministic discovery orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from ..alignment.normalize import align_snapshot
from ..config import MetaDiscoveryConfig
from ..contracts import (CandidateSinkPort, CanonicalSnapshot, CanonicalSnapshotReaderPort, CheckpointPort, MetaRunResult, OperationContextPort, RunAccounting)
from ..discovery.engine import run_detectors
from ..graph.builder import build_hypothesis_graph
from ..graph.cycle_guard import validate_support_graph
from ..hashing import sha256_canonical


@dataclass(slots=True)
class MetaDiscoveryService:
    config: MetaDiscoveryConfig
    plugin_id: str = "ae.meta_opportunity_discovery"


    def run_admitted(
        self,
        *,
        as_of: datetime,
        reader: CanonicalSnapshotReaderPort,
        context: OperationContextPort,
        checkpoint_port: CheckpointPort,
        candidate_sink: CandidateSinkPort | None = None,
        submit: bool = True,
    ) -> MetaRunResult:
        """Execute through injected core-owned ports without owning scheduling/storage.

        The host remains responsible for operation admission, permissions, budgets,
        leases, retry policy and durable candidate adoption.
        """
        if context.is_cancelled():
            raise RuntimeError("OPERATION_CANCELLED_BEFORE_START")
        snapshot = reader.read_snapshot(as_of=as_of, max_records=self.config.max_records)
        prior = checkpoint_port.load()
        result = self.run_snapshot(
            snapshot,
            run_id=context.operation_id,
            checkpoint=prior,
        )
        if context.is_cancelled():
            checkpoint_port.save({**result.checkpoint, "status": "INTERRUPTED"})
            raise RuntimeError("OPERATION_CANCELLED_AFTER_COMPUTE")
        checkpoint_port.save({**result.checkpoint, "status": result.status})
        if submit:
            if candidate_sink is None:
                raise ValueError("candidate_sink is required when submit=True")
            candidate_sink.submit_candidates(result.candidates)
        return result

    def run_snapshot(
        self,
        snapshot: CanonicalSnapshot,
        *,
        run_id: str,
        current_generation: int = 1,
        prior_fingerprints: frozenset[str] | None = None,
        checkpoint: Mapping[str, str] | None = None,
    ) -> MetaRunResult:
        if len(snapshot.records) > self.config.max_records:
            raise ValueError("RESOURCE_LIMIT:MAX_RECORDS")
        warnings: list[str] = []
        aligned, alignment_warnings = align_snapshot(snapshot, self.config)
        warnings.extend(alignment_warnings)
        graph = build_hypothesis_graph(aligned, self.config)
        validate_support_graph(graph, current_plugin_id=self.plugin_id, current_generation=current_generation)
        batch = run_detectors(graph, aligned, self.config, prior_fingerprints=prior_fingerprints)
        if batch.hypotheses_tested >= self.config.multiple_testing_warning_at:
            warnings.append("MULTIPLE_TESTING_BREADTH_HIGH")
        if batch.blocked_templates:
            warnings.append("PARTIAL_TEMPLATE_COVERAGE")
        out_checkpoint = {
            "snapshot_id": snapshot.snapshot_id,
            "graph_hash": graph.graph_hash,
            "candidate_count": str(len(batch.candidates)),
            "output_cursor": str(len(batch.candidates)),
        }
        if checkpoint:
            # Prior checkpoint is evidence only; it cannot silently override current deterministic state.
            prior_snapshot = checkpoint.get("snapshot_id")
            if prior_snapshot and prior_snapshot != snapshot.snapshot_id:
                warnings.append("CHECKPOINT_SNAPSHOT_MISMATCH_IGNORED")
        accounting = RunAccounting(
            records_seen=len(snapshot.records),
            records_eligible=len(aligned),
            hypotheses_tested=batch.hypotheses_tested,
            templates_evaluated=batch.templates_evaluated,
            candidates_emitted=len(batch.candidates),
            blocked_templates=batch.blocked_templates,
        )
        output_hash = sha256_canonical(
            {
                "run_id": run_id,
                "snapshot": snapshot.snapshot_id,
                "candidates": [c.fingerprint for c in batch.candidates],
                "accounting": accounting,
                "checkpoint": out_checkpoint,
            }
        )
        status = "PARTIAL" if batch.blocked_templates else "COMPLETE"
        return MetaRunResult(
            run_id=run_id,
            snapshot_id=snapshot.snapshot_id,
            status=status,
            candidates=batch.candidates,
            warnings=tuple(sorted(set(warnings))),
            accounting=accounting,
            output_hash=output_hash,
            checkpoint=out_checkpoint,
        )
