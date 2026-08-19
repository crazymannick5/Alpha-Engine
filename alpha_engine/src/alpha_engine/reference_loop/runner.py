from __future__ import annotations

import argparse
import json
from decimal import Decimal

from alpha_engine.contracts.plugin import ProviderRequest
from alpha_engine.runtime.application import ApplicationRuntime, build_runtime
from .fixture import (
    FixtureNormalizer,
    FixtureOpportunityDetector,
    FixtureProvider,
    FixtureSignalDetector,
)


def run_with_runtime(runtime: ApplicationRuntime) -> dict:
    """Execute the deterministic reference workflow through the composed public service authorities."""

    runtime.providers.register("reference.fixture", FixtureProvider(), priority=1)
    operation_id, created = runtime.operations.admit(
        "reference-script", "REFERENCE_LOOP", "reference-loop-v2", {"subject": "resource:A"}
    )
    if not created:
        existing = runtime.operations.snapshot(operation_id)
        if existing and existing["state"] == "SUCCEEDED" and existing["result"]:
            return existing["result"]
        raise RuntimeError(
            f"reference operation already exists in non-terminal reusable state: {existing}"
        )

    runtime.operations.transition(operation_id, "RUNNING")
    budget_id = runtime.budgets.define("reference.fixture", Decimal("5.00"))
    permission_id = runtime.permissions.grant(
        "PAPER_ACTION", "resource:A", max_uses=10
    )

    result = runtime.data_queries.execute(
        ProviderRequest(query_type="synthetic_resource_forecast", payload={"subject": "resource:A"})
    )
    raw = json.dumps(result.payload, sort_keys=True).encode()
    artifact_id = runtime.artifacts.adopt_bytes(raw, "application/json")
    evidence_id = runtime.evidence.register(
        "resource:A", artifact_id, metadata={"provider": "reference.fixture"}
    )

    observation_candidate = FixtureNormalizer().normalize(result, [evidence_id])[0]
    observation_id = runtime.observations.persist_candidate(observation_candidate)
    signal_candidate = FixtureSignalDetector().detect(
        [
            {
                "id": observation_id,
                "subject": observation_candidate.subject,
                "value": observation_candidate.value,
                "evidence_refs": observation_candidate.evidence_refs,
            }
        ]
    )[0]
    signal_id = runtime.signals.persist_candidate(signal_candidate)
    opportunity_candidate = FixtureOpportunityDetector().detect(
        [{"id": signal_id, "subject": signal_candidate.subject}]
    )[0]
    opportunity_id = runtime.opportunities.persist_candidate(opportunity_candidate, [evidence_id])
    score_id, total = runtime.ranking.score(
        opportunity_id, {"magnitude": "0.90", "confidence": "0.95", "freshness": "1.00"}
    )
    radar_id = runtime.radar.evaluate(opportunity_id, score_id, total)
    decision_id = runtime.decisions.record(
        opportunity_id, "APPROVE_PAPER_ACTION", "Deterministic reference approval"
    )
    runtime.permissions.require_and_use("PAPER_ACTION", "resource:A")
    reservation = runtime.budgets.reserve("reference.fixture", Decimal("0.10"))
    action_id = runtime.simulation.paper_action(
        opportunity_id, decision_id, Decimal("10"), Decimal("1"), Decimal("10")
    )
    runtime.budgets.commit(reservation, Decimal("0.05"))
    outcome_artifact = runtime.artifacts.adopt_bytes(b'{"realized":"0.80"}', "application/json")
    outcome_evidence = runtime.evidence.register(opportunity_id, outcome_artifact)
    outcome_id = runtime.outcomes.finalize(action_id, {"realized": "0.80"}, [outcome_evidence])
    evaluation_id = runtime.evaluation.evaluate(
        opportunity_id, outcome_id, total, Decimal("0.80")
    )
    learning_id = runtime.learning.recommend(
        evaluation_id, "ranking.reference.confidence_weight", "0.35", "0.34"
    )

    manifest = {
        "operation_id": operation_id,
        "budget_id": budget_id,
        "permission_id": permission_id,
        "artifact_id": artifact_id,
        "evidence_id": evidence_id,
        "observation_id": observation_id,
        "signal_id": signal_id,
        "opportunity_id": opportunity_id,
        "score_id": score_id,
        "score_total": str(total),
        "radar_id": radar_id,
        "decision_id": decision_id,
        "paper_action_id": action_id,
        "outcome_id": outcome_id,
        "evaluation_id": evaluation_id,
        "learning_recommendation_id": learning_id,
        "artifact_integrity": runtime.artifacts.verify(artifact_id),
        "learning_auto_applied": False,
        "runtime_mode": runtime.mode,
    }
    runtime.operations.transition(operation_id, "SUCCEEDED", manifest)
    return manifest


def run(db: str, artifacts: str) -> dict:
    """Backward-compatible lower-level runner preserving the historical CLI contract."""

    from pathlib import Path
    import tempfile

    # The legacy two-path contract is preserved by composing a temporary profile and overriding the
    # storage/artifact locations only for this compatibility runner. It remains lower-level than `alpha demo`.
    from alpha_engine.storage.bootstrap import initialize
    from alpha_engine.artifacts.store import ArtifactStore
    from alpha_engine.evidence.service import EvidenceService
    from alpha_engine.providers.registry import ProviderRegistry
    from alpha_engine.data_queries.gateway import DataQueryGateway
    from alpha_engine.operations.service import OperationService
    from alpha_engine.operations.scheduler import SchedulerService
    from alpha_engine.operations.outbox import OutboxService
    from alpha_engine.permissions.service import PermissionService
    from alpha_engine.budgets.service import BudgetService
    from alpha_engine.plugin_host.registry import PluginRegistry
    from alpha_engine.observations.service import ObservationService
    from alpha_engine.signals.service import SignalService
    from alpha_engine.opportunities.service import OpportunityService
    from alpha_engine.ranking.service import RankingService
    from alpha_engine.radar.service import RadarService
    from alpha_engine.reviews.service import DecisionService
    from alpha_engine.simulation.service import SimulationService
    from alpha_engine.outcomes.service import OutcomeService
    from alpha_engine.evaluation.service import EvaluationService
    from alpha_engine.learning.service import LearningService
    from alpha_engine.notifications.service import NotificationService
    from alpha_engine.registries.service import RegistryService
    from alpha_engine.health.service import HealthService
    from alpha_engine.bootstrap.profile import ensure_profile

    profile = ensure_profile(Path(tempfile.gettempdir()) / "alpha-engine-reference-compat")
    engine, sf = initialize(db)
    providers = ProviderRegistry()
    runtime = ApplicationRuntime(
        profile=profile,
        engine=engine,
        sf=sf,
        artifacts=ArtifactStore(artifacts, sf),
        evidence=EvidenceService(sf),
        providers=providers,
        data_queries=DataQueryGateway(providers),
        operations=OperationService(sf),
        scheduler=SchedulerService(sf),
        outbox=OutboxService(sf),
        permissions=PermissionService(sf),
        budgets=BudgetService(sf),
        plugins=PluginRegistry(sf),
        observations=ObservationService(sf),
        signals=SignalService(sf),
        opportunities=OpportunityService(sf),
        ranking=RankingService(sf),
        radar=RadarService(sf),
        decisions=DecisionService(sf),
        simulation=SimulationService(sf),
        outcomes=OutcomeService(sf),
        evaluation=EvaluationService(sf),
        learning=LearningService(sf),
        notifications=NotificationService(sf),
        registries=RegistryService(sf),
        health=HealthService(engine, artifacts),
        mode="reference-compat",
    )
    try:
        return run_with_runtime(runtime)
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="alpha-reference.sqlite3")
    parser.add_argument("--artifacts", default="alpha-reference-artifacts")
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.artifacts), indent=2))


if __name__ == "__main__":
    main()
