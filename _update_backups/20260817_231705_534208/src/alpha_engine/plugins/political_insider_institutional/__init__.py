"""Political, Insider, and Institutional Activity cylinder.

Cylinder-owned implementation only. Core authority remains responsible for canonical
persistence, operations, permissions, budgets, ranking/Radar, review, paper ledgers,
and outcome records.
"""
from .manifest import PLUGIN_ID, plugin_manifest

__all__ = ["PLUGIN_ID", "plugin_manifest"]
