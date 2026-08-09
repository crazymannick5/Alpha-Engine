from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class HealthFinding:
    code: str
    status: str
    detail: str

@dataclass(frozen=True, slots=True)
class HealthReport:
    state: str
    findings: tuple[HealthFinding, ...]


def self_check(*, host_persistence_available: bool, canonical_projection_available: bool, paper_multileg_available: bool) -> HealthReport:
    findings = []
    if not canonical_projection_available:
        findings.append(HealthFinding("ARB_HOST_CANONICAL_PROJECTION_MISSING", "BLOCKED", "Cross-cylinder production reads unavailable; fixture/local inputs remain usable."))
    if not host_persistence_available:
        findings.append(HealthFinding("ARB_HOST_PERSISTENCE_MISSING", "DEGRADED", "Durable relationship/checkpoint persistence unavailable; in-memory mode only."))
    if not paper_multileg_available:
        findings.append(HealthFinding("ARB_HOST_MULTILEG_PAPER_MISSING", "DEGRADED", "Paper translator/preview works, but authoritative core multi-leg simulation cannot be registered."))
    state = "HEALTHY" if not findings else ("DEGRADED_COMPATIBILITY" if all(f.status == "DEGRADED" for f in findings) else "DEGRADED_COMPATIBILITY")
    return HealthReport(state, tuple(findings))
