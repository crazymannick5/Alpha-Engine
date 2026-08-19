from __future__ import annotations

from copy import deepcopy
from typing import Mapping


class InMemoryProjectionStore:
    """Deterministic test adapter only; not a replacement for central persistence."""
    namespace = "ae_prediction_markets.test"

    def __init__(self) -> None:
        self._data: dict[tuple[str,str], tuple[int, dict[str,object]]] = {}

    def get(self, collection: str, key: str) -> Mapping[str, object] | None:
        row = self._data.get((collection,key))
        return deepcopy(row[1]) if row else None

    def put(self, collection: str, key: str, value: Mapping[str, object], *, expected_version: int | None = None) -> int:
        current = self._data.get((collection,key))
        current_version = current[0] if current else 0
        if expected_version is not None and expected_version != current_version:
            raise RuntimeError("optimistic version mismatch")
        version = current_version + 1
        self._data[(collection,key)] = (version, dict(value))
        return version

    def delete(self, collection: str, key: str, *, expected_version: int | None = None) -> None:
        current = self._data.get((collection,key))
        if current is None:
            return
        if expected_version is not None and expected_version != current[0]:
            raise RuntimeError("optimistic version mismatch")
        del self._data[(collection,key)]


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._data: dict[tuple[str,str], dict[str,str]] = {}

    def load_checkpoint(self, provider_id: str, stream_key: str):
        value = self._data.get((provider_id,stream_key))
        return dict(value) if value else None

    def save_checkpoint(self, provider_id: str, stream_key: str, checkpoint: Mapping[str, str]) -> None:
        self._data[(provider_id,stream_key)] = dict(checkpoint)
