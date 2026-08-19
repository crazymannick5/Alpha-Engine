from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class PluginPersistenceScope(Protocol):
    """Host-issued plugin namespace.  No raw core DB handle is permitted."""

    def put(self, namespace: str, key: str, payload: Mapping[str, Any]) -> None: ...
    def get(self, namespace: str, key: str) -> Mapping[str, Any] | None: ...
    def query(self, namespace: str, prefix: str) -> Sequence[Mapping[str, Any]]: ...


PMQO_NAMESPACES = (
    "pmqo.security_master",
    "pmqo.data_vintages",
    "pmqo.option_contracts",
    "pmqo.experiments",
    "pmqo.feature_snapshots",
    "pmqo.dataset_partitions",
)


class FeatureSnapshotRepository:
    """Repository adapter over the host-issued PMQO persistence scope."""

    namespace = "pmqo.feature_snapshots"

    def __init__(self, scope: PluginPersistenceScope):
        self._scope = scope

    def put_snapshot(self, snapshot_id: str, payload: Mapping[str, Any]) -> None:
        self._scope.put(self.namespace, snapshot_id, payload)

    def get_snapshot(self, snapshot_id: str) -> Mapping[str, Any] | None:
        return self._scope.get(self.namespace, snapshot_id)
