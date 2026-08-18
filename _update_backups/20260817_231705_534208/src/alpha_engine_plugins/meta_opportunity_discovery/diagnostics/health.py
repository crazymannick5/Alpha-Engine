"""Safe local plugin health diagnostics."""

from __future__ import annotations

from ..manifest import MANIFEST


def health_report(*, available_core_capabilities: frozenset[str]) -> dict[str, object]:
    required = {
        "canonical.read.signal",
        "canonical.read.opportunity",
        "plugin.capabilities.query",
        "evidence.ancestry.query",
        "candidate.opportunity.submit",
    }
    missing = tuple(sorted(required - available_core_capabilities))
    return {
        "plugin_id": MANIFEST.plugin_id,
        "version": MANIFEST.version,
        "status": "READY" if not missing else "BLOCKED",
        "missing_core_capabilities": missing,
        "model_enabled_by_manifest": "model.hypothesis_candidate" in MANIFEST.optional_capabilities,
    }
