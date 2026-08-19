from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperationDescriptor:
    operation_type: str
    idempotency_basis: str
    checkpoint_boundary: str
    resource_class: str
    permission_scope: str


def operation_descriptors() -> tuple[OperationDescriptor, ...]:
    """Declarations consumed by the Central Hub operation/scheduler layer.

    These are metadata only; this plugin does not own a scheduler or worker.
    """
    return (
        OperationDescriptor("pmqo.provider_query", "canonical_query_hash+route+provider", "page_or_high_water_mark", "IO", "public_markets.acquire.dataset"),
        OperationDescriptor("pmqo.historical_backfill", "dataset+provider+universe_snapshot+range+adapter_version", "partition", "IO_DISK", "public_markets.backfill.dataset"),
        OperationDescriptor("pmqo.normalize_partition", "artifact_hash+normalizer_version", "record_chunk", "CPU_LIGHT", "public_markets.import"),
        OperationDescriptor("pmqo.compute_features", "snapshot_hash+feature_set_version", "subject_batch", "CPU_MEDIUM", "public_markets.run_experiment"),
        OperationDescriptor("pmqo.run_experiment", "experiment_spec_hash+dataset_manifest_hash", "partition", "CPU_DISK_HEAVY", "public_markets.run_experiment"),
        OperationDescriptor("pmqo.compute_option_surface", "chain_snapshot_hash+model_version", "expiration", "CPU_MEDIUM", "public_markets.compute_surface"),
        OperationDescriptor("pmqo.detect", "input_snapshot_hash+detector_version", "subject_batch", "CPU_LIGHT", "public_markets.run_experiment"),
        OperationDescriptor("pmqo.translate_paper_action", "opportunity_version+strategy_spec_hash", "atomic", "CPU_LIGHT", "public_markets.create_paper_action"),
        OperationDescriptor("pmqo.evaluate_market_outcome", "target+evaluation_definition+evidence_version", "target", "CPU_LIGHT", "public_markets.run_experiment"),
    )
