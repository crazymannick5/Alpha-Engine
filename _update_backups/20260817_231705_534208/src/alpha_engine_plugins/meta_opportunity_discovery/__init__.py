"""Cross-Domain Meta-Opportunity Discovery cylinder.

This package is intentionally self-contained inside its plugin-owned namespace.  It
contains deterministic synthesis logic and host-facing adapter protocols, but it
never opens core storage, imports another cylinder, ranks canonical opportunities,
or performs paper/live actions.
"""

from .config import MetaDiscoveryConfig
from .contracts import CanonicalRecord, CanonicalSnapshot, MetaCandidate, MetaRunResult
from .operations.service import MetaDiscoveryService

__all__ = [
    "CanonicalRecord",
    "CanonicalSnapshot",
    "MetaCandidate",
    "MetaDiscoveryConfig",
    "MetaDiscoveryService",
    "MetaRunResult",
]

__version__ = "0.9.0-implementation.1"
