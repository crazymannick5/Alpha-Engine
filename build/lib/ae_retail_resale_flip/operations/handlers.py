from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from ..contracts import EvidenceRef, OperationContext, RetailProviderAdapter, RetailQuery
from ..normalization.normalizer import normalize_records
from ..persistence.repositories import PluginCheckpoint, RetailPluginRepository
from ..serialization import stable_hash


@dataclass(frozen=True, slots=True)
class AcquisitionBatchResult:
    normalized_count: int
    next_cursor: str | None
    request_hash: str
    record_hashes: tuple[str, ...]


def acquire_and_normalize(adapter: RetailProviderAdapter, query: RetailQuery, ctx: OperationContext, *, payload: bytes | str | None = None, evidence_refs: Sequence[EvidenceRef] = (), repository: RetailPluginRepository | None = None) -> AcquisitionBatchResult:
    request_hash = stable_hash((query, adapter.descriptor.provider_id, adapter.descriptor.adapter_version, ctx.policy_version))
    result = adapter.execute(query, ctx, payload)
    normalized = normalize_records(result, evidence_refs)
    hashes = tuple(stable_hash(x) for x in normalized)
    if repository is not None:
        repository.save_checkpoint(PluginCheckpoint(ctx.operation_id, adapter.descriptor.provider_id, request_hash, 0, result.source_cursor, "NORMALIZED", datetime.now(timezone.utc)))
    return AcquisitionBatchResult(len(normalized), result.source_cursor, request_hash, hashes)
