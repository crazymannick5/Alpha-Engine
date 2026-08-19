"""Arbitrage and cross-market comparison cylinder.

The package intentionally has no dependency on core-private Alpha Engine modules.
A thin host adapter can bind :func:`registration_bundle` to the frozen PDK.
"""
from .registration import registration_bundle

PLUGIN_ID = "ae.arbitrage_cross_market"
__version__ = "0.9.0.dev0"

__all__ = ["PLUGIN_ID", "__version__", "registration_bundle"]
