from __future__ import annotations

from typing import Any, Mapping, Protocol


class NamespacedPersistencePort(Protocol):
    """Host-provided persistence seam; no database/session ownership in the plugin."""
    def get(self, namespace: str, key: str) -> Mapping[str, Any] | None: ...
    def put(self, namespace: str, key: str, value: Mapping[str, Any], *, expected_version: int | None = None) -> int: ...
    def delete(self, namespace: str, key: str, *, expected_version: int | None = None) -> None: ...


class ProjectionRepository:
    namespace = "plugin_pii_projection_activity"

    def __init__(self, host: NamespacedPersistencePort):
        self._host = host

    def get_projection(self, key: str) -> Mapping[str, Any] | None:
        return self._host.get(self.namespace, key)

    def upsert_projection(self, key: str, payload: Mapping[str, Any], *, expected_version: int | None = None) -> int:
        return self._host.put(self.namespace, key, payload, expected_version=expected_version)
