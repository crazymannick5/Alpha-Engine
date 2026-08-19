from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable

from ..cli.descriptors import cli_contributions
from ..contracts import Descriptor
from ..diagnostics.health import health_snapshot
from ..manifest import MANIFEST
from ..providers.kalshi import KalshiReadOnlyAdapter
from ..ui.descriptors import dashboard_contributions


class RegistrationReport(dict):
    """Simple mapping so the host compatibility harness can inspect registrations."""


def _call_first(registry: Any, names: Iterable[str], *args: Any) -> str | None:
    for name in names:
        fn = getattr(registry, name, None)
        if callable(fn):
            fn(*args)
            return name
    return None


def register_with_central(registry: Any) -> RegistrationReport:
    """Register using only public-style method names.

    The function deliberately avoids importing core-private modules. It supports a small
    compatibility vocabulary because the exact executable PDK was not mounted into this
    builder sandbox. The core's own compatibility harness remains authoritative.
    """
    report = RegistrationReport(plugin_id=MANIFEST.plugin_id, registered=[], deferred=[])
    manifest_method = _call_first(registry, ("register_manifest", "add_manifest", "register_plugin_manifest"), MANIFEST)
    if manifest_method:
        report["registered"].append(f"manifest:{manifest_method}")
    else:
        report["deferred"].append("manifest")

    provider = KalshiReadOnlyAdapter()
    method = _call_first(registry, ("register_provider", "register_provider_adapter", "add_provider"), provider)
    (report["registered"] if method else report["deferred"]).append(f"provider:{method or 'missing_contract'}")

    for descriptor in dashboard_contributions():
        method = _call_first(registry, ("register_dashboard", "register_dashboard_contribution", "add_dashboard"), descriptor)
        (report["registered"] if method else report["deferred"]).append(f"dashboard:{descriptor.id}:{method or 'missing_contract'}")
    for descriptor in cli_contributions():
        method = _call_first(registry, ("register_cli", "register_cli_contribution", "add_cli"), descriptor)
        (report["registered"] if method else report["deferred"]).append(f"cli:{descriptor.id}:{method or 'missing_contract'}")
    return report


def descriptor_as_mapping(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("descriptor must be dataclass or mapping")
