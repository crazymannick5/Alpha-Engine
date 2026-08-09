from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .domain import PMRelation
from .utils import stable_hash

MIGRATION_NAMESPACE = "ae_prediction_markets"


@dataclass(frozen=True, slots=True)
class MigrationDescriptor:
    migration_id: str
    namespace: str
    relative_path: str
    sha256: str


def migration_descriptors() -> tuple[MigrationDescriptor, ...]:
    path = Path(__file__).with_name("migrations") / "001_initial.sql"
    content = path.read_text(encoding="utf-8")
    return (MigrationDescriptor(
        migration_id="001_initial", namespace=MIGRATION_NAMESPACE,
        relative_path="alpha_engine_prediction_markets/migrations/001_initial.sql",
        sha256=stable_hash("pm.migration.sql.v1", {"sql": content}),
    ),)


class RelationRepository(Protocol):
    """Plugin namespace repository port.  The Central Hub/PDK supplies the implementation."""
    def replace_relation_version(self, relation: PMRelation) -> None: ...
    def list_relations_for_market(self, market_ref: str) -> Sequence[PMRelation]: ...


class ProviderCheckpointRepository(Protocol):
    def load_checkpoint(self, provider_id: str, stream_key: str) -> dict | None: ...
    def save_checkpoint(self, provider_id: str, stream_key: str, payload: dict, adapter_version: str) -> None: ...


class QualificationProjectionRepository(Protocol):
    def get_capability(self, provider_id: str, capability: str) -> dict | None: ...
    def upsert_capability(self, provider_id: str, capability: str, projection: dict) -> None: ...
