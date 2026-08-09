from __future__ import annotations

from typing import Mapping, Protocol


class PluginProjectionStore(Protocol):
    """Host-supplied, namespace-confined persistence port.

    The plugin never receives a core SQLAlchemy session or raw core DB handle.
    """

    namespace: str

    def get(self, collection: str, key: str) -> Mapping[str, object] | None: ...
    def put(self, collection: str, key: str, value: Mapping[str, object], *, expected_version: int | None = None) -> int: ...
    def delete(self, collection: str, key: str, *, expected_version: int | None = None) -> None: ...


class CheckpointStore(Protocol):
    def load_checkpoint(self, provider_id: str, stream_key: str) -> Mapping[str, str] | None: ...
    def save_checkpoint(self, provider_id: str, stream_key: str, checkpoint: Mapping[str, str]) -> None: ...
