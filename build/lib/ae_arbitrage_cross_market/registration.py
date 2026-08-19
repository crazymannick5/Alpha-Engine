from __future__ import annotations
from dataclasses import dataclass

from .detectors.arbitrage import ArbitrageDetector
from .diagnostics.health import self_check
from .outcomes.evaluator import ArbitrageOutcomeEvaluator
from .learning.recommendations import recommend_min_edge_bps
from .paper.translator import PaperPlanTranslator
from .presentation.descriptors import CLI_COMMANDS, DASHBOARD_VIEWS, OPERATION_DESCRIPTORS, PERMISSION_SCOPES
from .resolution.resolver import ConservativeRelationshipResolver
from .scoring.features import FEATURE_DESCRIPTORS

@dataclass(frozen=True, slots=True)
class RegistrationBundle:
    plugin_id: str
    version: str
    resolver: object
    detector: object
    paper_translator: object
    outcome_evaluator: object
    learning_recommender: object
    feature_descriptors: tuple[dict, ...]
    dashboard_views: tuple[dict, ...]
    cli_commands: tuple[dict, ...]
    operation_descriptors: tuple[dict, ...]
    permission_scopes: tuple[str, ...]
    live_execution_supported: bool


def registration_bundle() -> RegistrationBundle:
    return RegistrationBundle(
        plugin_id="ae.arbitrage_cross_market",
        version="0.9.0-dev",
        resolver=ConservativeRelationshipResolver(),
        detector=ArbitrageDetector(),
        paper_translator=PaperPlanTranslator(),
        outcome_evaluator=ArbitrageOutcomeEvaluator(),
        learning_recommender=recommend_min_edge_bps,
        feature_descriptors=FEATURE_DESCRIPTORS,
        dashboard_views=DASHBOARD_VIEWS,
        cli_commands=CLI_COMMANDS,
        operation_descriptors=OPERATION_DESCRIPTORS,
        permission_scopes=PERMISSION_SCOPES,
        live_execution_supported=False,
    )
