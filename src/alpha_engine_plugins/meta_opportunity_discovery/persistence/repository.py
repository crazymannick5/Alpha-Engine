"""Plugin-owned persistence protocol only.

A concrete production implementation must be supplied by the central host's
namespaced plugin-storage/UoW contract.  This cylinder intentionally does not open
SQLite/SQLAlchemy or create a second storage subsystem.
"""

from __future__ import annotations

from typing import Protocol


class MetaHistoryRepository(Protocol):
    def prior_candidate_fingerprints(self, *, limit: int) -> frozenset[str]: ...
    def record_run_fingerprints(self, *, run_id: str, fingerprints: tuple[str, ...]) -> None: ...
