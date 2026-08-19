from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .manifest import PLUGIN_ID, PLUGIN_VERSION


@dataclass(frozen=True, slots=True)
class HealthReport:
    state: str
    checks: tuple[str, ...]
    blockers: tuple[str, ...]


def health_check(*, core_bridge_bound: bool, persistence_bound: bool, configured_providers: Sequence[str]) -> HealthReport:
    blockers = []
    checks = [f"plugin={PLUGIN_ID}@{PLUGIN_VERSION}"]
    if not core_bridge_bound:
        blockers.append("CORE_PDK_BRIDGE_UNBOUND")
    if not persistence_bound:
        blockers.append("PLUGIN_PERSISTENCE_SCOPE_UNBOUND")
    if not configured_providers:
        checks.append("fixture_only_mode")
    state = "READY" if not blockers else "BLOCKED"
    return HealthReport(state, tuple(checks), tuple(blockers))
