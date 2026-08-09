from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class PluginCheckpoint:
    operation_id: str
    provider_id: str
    request_hash: str
    page_no: int
    opaque_cursor: str | None
    state: str
    updated_at: datetime


class RetailPluginRepository(Protocol):
    """Host-supplied namespaced repository. Implementations belong to Central Hub, not this plugin."""
    def get_checkpoint(self, operation_id: str, provider_id: str, request_hash: str) -> PluginCheckpoint | None: ...
    def save_checkpoint(self, checkpoint: PluginCheckpoint) -> None: ...
    def save_plugin_record(self, record_type: str, record_id: str, payload: Mapping[str, Any], content_hash: str) -> None: ...
    def get_plugin_record(self, record_type: str, record_id: str) -> Mapping[str, Any] | None: ...
