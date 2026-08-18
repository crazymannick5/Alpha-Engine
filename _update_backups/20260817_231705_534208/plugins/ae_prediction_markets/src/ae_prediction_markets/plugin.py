from __future__ import annotations

from .integration.central import register_with_central
from .manifest import MANIFEST


def register(registry):
    """Central plugin entrypoint."""
    return register_with_central(registry)


__all__ = ["register", "MANIFEST"]
