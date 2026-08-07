from dataclasses import dataclass,field
from typing import Any
@dataclass
class PluginContributions:
    providers:list[Any]=field(default_factory=list); normalizers:list[Any]=field(default_factory=list); signal_detectors:list[Any]=field(default_factory=list); opportunity_detectors:list[Any]=field(default_factory=list); scoring_features:list[Any]=field(default_factory=list); outcome_evaluators:list[Any]=field(default_factory=list); dashboard_views:list[dict]=field(default_factory=list); cli_commands:list[dict]=field(default_factory=list)
@dataclass
class PluginBundle:
    manifest: Any
    contributions: PluginContributions
