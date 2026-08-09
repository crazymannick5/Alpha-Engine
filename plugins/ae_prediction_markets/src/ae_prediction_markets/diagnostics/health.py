from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    plugin_id: str
    status: str
    checked_at: datetime
    provider_status: dict[str, str]
    warnings: tuple[str, ...] = ()


def health_snapshot(*, now: datetime, provider_status: dict[str,str] | None = None, warnings: tuple[str,...] = ()) -> HealthSnapshot:
    statuses = provider_status or {}
    state = "DEGRADED" if warnings or any(v != "HEALTHY" for v in statuses.values()) else "HEALTHY"
    return HealthSnapshot("ae.prediction_markets", state, now, statuses, warnings)
