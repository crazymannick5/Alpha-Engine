"""Public Markets / Quant / Options cylinder.

This package is deliberately plugin-scoped.  It contains domain logic and
host-facing protocols, but no core database, scheduler, permission system,
budget system, ranking engine, or live brokerage connectivity.
"""
from .manifest import PLUGIN_ID, PLUGIN_VERSION, plugin_manifest
from .service import PublicMarketsCylinder

__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "plugin_manifest", "PublicMarketsCylinder"]
