from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Mapping

from .manifest import PLUGIN_ID, PLUGIN_VERSION
from .providers.base import PMProviderAdapter
from .utils import require_utc


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider_id: str
    adapter_version: str
    qualified: bool
    qualification_expires_at: datetime | None
    capabilities: tuple[str, ...]
    read_only: bool
    warnings: tuple[str, ...]


def provider_health(adapter: PMProviderAdapter, qualification: Mapping[str, object] | None, now: datetime) -> ProviderHealth:
    now = require_utc(now)
    expires = None
    qualified = False
    warnings: list[str] = []
    if qualification:
        qualified = bool(qualification.get("qualified", False))
        raw_exp = qualification.get("expires_at")
        if isinstance(raw_exp, datetime):
            expires = require_utc(raw_exp)
            if expires <= now:
                qualified = False
                warnings.append("qualification expired")
    if adapter.descriptor.terms_qualification_required and not qualified:
        warnings.append("production provider requires current terms/source qualification")
    return ProviderHealth(
        provider_id=adapter.descriptor.provider_id,
        adapter_version=adapter.descriptor.adapter_version,
        qualified=qualified,
        qualification_expires_at=expires,
        capabilities=adapter.descriptor.capabilities,
        read_only=adapter.descriptor.read_only,
        warnings=tuple(warnings),
    )


def plugin_health_summary(provider_states: tuple[ProviderHealth, ...]) -> dict[str, object]:
    return {
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "provider_count": len(provider_states),
        "qualified_provider_count": sum(1 for x in provider_states if x.qualified),
        "degraded": any(x.warnings for x in provider_states),
        "providers": [asdict(x) for x in provider_states],
    }
