"""Alpha Engine Prediction Markets cylinder.

The package is intentionally plugin-owned.  It does not import core-private modules
or mutate Central Hub state directly.  External side effects are exposed through
ports that the Hub must admit and supply.
"""
from .engine import PredictionMarketsEngine
from .manifest import MANIFEST, PLUGIN_ID, PLUGIN_VERSION
from .plugin import build_registration

__all__ = ["PredictionMarketsEngine", "MANIFEST", "PLUGIN_ID", "PLUGIN_VERSION", "build_registration"]
