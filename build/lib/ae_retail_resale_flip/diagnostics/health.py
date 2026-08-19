from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    state: HealthState
    reasons: tuple[str, ...]
    metrics: Mapping[str, int | float | str]


def health_snapshot(*, host_contract_available: bool, provider_count: int, unresolved_identities: int = 0, adapter_errors: int = 0) -> HealthSnapshot:
    reasons: list[str] = []
    if not host_contract_available:
        reasons.append("CENTRAL_HOST_CONTRACT_UNVERIFIED")
    if provider_count <= 0:
        reasons.append("NO_QUALIFIED_PROVIDER")
    if adapter_errors:
        reasons.append("ADAPTER_ERRORS")
    state = HealthState.HEALTHY if not reasons else HealthState.DEGRADED
    return HealthSnapshot(state, tuple(reasons), {"provider_count": provider_count, "unresolved_identities": unresolved_identities, "adapter_errors": adapter_errors})
