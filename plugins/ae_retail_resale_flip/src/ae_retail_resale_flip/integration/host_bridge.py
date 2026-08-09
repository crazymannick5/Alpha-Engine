from __future__ import annotations

"""Narrow adapter to the Central Hub public PDK.

The plugin never imports core-private storage or service modules. Until the PDK is frozen,
this bridge offers deterministic payload export and a conservative compatibility probe.
"""

from dataclasses import asdict, is_dataclass
import importlib
from typing import Any, Mapping

from ..serialization import canonical_json

PUBLIC_PLUGIN_CONTRACT_MODULE = "alpha_engine.contracts.plugin"


def probe_public_pdk() -> tuple[bool, str]:
    try:
        mod = importlib.import_module(PUBLIC_PLUGIN_CONTRACT_MODULE)
    except Exception as exc:  # safe compatibility probe, no entrypoint side effects expected
        return False, f"public contract unavailable: {type(exc).__name__}"
    required_any = ("ObservationCandidate", "SignalCandidate", "OpportunityCandidate", "PluginManifest")
    found = [name for name in required_any if hasattr(mod, name)]
    if not found:
        return False, "public contract module lacks known plugin DTOs"
    return True, "available:" + ",".join(found)


def extension_payload(value: Any) -> Mapping[str, Any]:
    import json
    return json.loads(canonical_json(value))


def adapt_candidate(candidate_type: str, value: Any) -> Any:
    """Best-effort additive adapter to generic PDK DTOs; fails closed when shape is unknown."""
    mod = importlib.import_module(PUBLIC_PLUGIN_CONTRACT_MODULE)
    cls = getattr(mod, candidate_type, None)
    if cls is None:
        raise RuntimeError(f"central PDK does not expose {candidate_type}")
    payload = extension_payload(value)
    # Draft PDK evidence indicates candidate DTOs are payload-oriented. Support only explicit public fields.
    annotations = getattr(cls, "__annotations__", {}) or {}
    kwargs: dict[str, Any] = {}
    if "payload" in annotations:
        kwargs["payload"] = payload
    if "plugin_id" in annotations:
        kwargs["plugin_id"] = "ae.retail_resale_flip"
    if "schema_version" in annotations:
        kwargs["schema_version"] = "retail.v1"
    if not kwargs:
        raise RuntimeError(f"unsupported {candidate_type} public shape; submit CENTRAL_HUB_INTEGRATION_REQUEST")
    return cls(**kwargs)
