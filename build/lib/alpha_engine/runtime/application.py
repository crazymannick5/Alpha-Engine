from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alpha_engine import __version__
from alpha_engine.artifacts.store import ArtifactStore
from alpha_engine.bootstrap.lifecycle import RuntimeLease
from alpha_engine.bootstrap.profile import ProfilePaths, ensure_profile
from alpha_engine.budgets.service import BudgetService
from alpha_engine.data_queries.gateway import DataQueryGateway
from alpha_engine.evaluation.service import EvaluationService
from alpha_engine.evidence.service import EvidenceService
from alpha_engine.health.service import HealthService
from alpha_engine.learning.service import LearningService
from alpha_engine.notifications.service import NotificationService
from alpha_engine.observations.service import ObservationService
from alpha_engine.operations.outbox import OutboxService
from alpha_engine.operations.scheduler import SchedulerService
from alpha_engine.operations.service import OperationService
from alpha_engine.opportunities.service import OpportunityService
from alpha_engine.outcomes.service import OutcomeService
from alpha_engine.permissions.service import PermissionService
from alpha_engine.plugin_host.registry import PluginRegistry
from alpha_engine.providers.registry import ProviderRegistry
from alpha_engine.radar.service import RadarService
from alpha_engine.ranking.service import RankingService
from alpha_engine.registries.service import RegistryService
from alpha_engine.reviews.service import DecisionService
from alpha_engine.signals.service import SignalService
from alpha_engine.simulation.service import SimulationService
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.storage.models import OperationRow, OutboxRow, PluginRow


@dataclass(slots=True)
class ApplicationRuntime:
    profile: ProfilePaths
    engine: Any
    sf: Any
    artifacts: ArtifactStore
    evidence: EvidenceService
    providers: ProviderRegistry
    data_queries: DataQueryGateway
    operations: OperationService
    scheduler: SchedulerService
    outbox: OutboxService
    permissions: PermissionService
    budgets: BudgetService
    plugins: PluginRegistry
    observations: ObservationService
    signals: SignalService
    opportunities: OpportunityService
    ranking: RankingService
    radar: RadarService
    decisions: DecisionService
    simulation: SimulationService
    outcomes: OutcomeService
    evaluation: EvaluationService
    learning: LearningService
    notifications: NotificationService
    registries: RegistryService
    health: HealthService
    mode: str = "normal"
    lease: RuntimeLease | None = None

    def composition_manifest(self) -> dict[str, Any]:
        with self.sf() as session:
            plugins = [
                {
                    "plugin_id": row.plugin_id,
                    "name": row.name,
                    "version": row.version,
                    "contract_version": row.contract_version,
                    "status": row.status,
                }
                for row in session.query(PluginRow).order_by(PluginRow.plugin_id).all()
            ]
        return {
            "manifest_version": 1,
            "product": "Personal Alpha Engine",
            "build_version": __version__,
            "core_contract": self.plugins.CORE_CONTRACT,
            "pdk_version": "1.0-draft",
            "schema_authority": "bootstrap-create-all-dev",
            "profile": str(self.profile.root.resolve()),
            "mode": self.mode,
            "authorities": {
                "storage": "alpha_engine.storage",
                "operations": "alpha_engine.operations.service.OperationService",
                "scheduler": "alpha_engine.operations.scheduler.SchedulerService",
                "outbox": "alpha_engine.operations.outbox.OutboxService",
                "providers": "alpha_engine.providers.registry.ProviderRegistry",
                "data_queries": "alpha_engine.data_queries.gateway.DataQueryGateway",
                "plugins": "alpha_engine.plugin_host.registry.PluginRegistry",
                "permissions": "alpha_engine.permissions.service.PermissionService",
                "budgets": "alpha_engine.budgets.service.BudgetService",
                "ranking": "alpha_engine.ranking.service.RankingService",
                "radar": "alpha_engine.radar.service.RadarService",
                "simulation": "alpha_engine.simulation.service.SimulationService",
            },
            "plugins": plugins,
            "limitations": [
                "numbered core migrations are not yet the schema upgrade authority",
                "worker subprocess supervision is not yet integrated",
                "live-provider qualification remains opt-in and incomplete",
            ],
        }

    def status(self) -> dict[str, Any]:
        with self.sf() as session:
            failed_operations = [
                {"id": row.id, "type": row.op_type, "state": row.state}
                for row in session.query(OperationRow)
                .filter(OperationRow.state.in_(["FAILED", "BLOCKED", "CANCELLED"]))
                .order_by(OperationRow.created_at.desc())
                .limit(20)
                .all()
            ]
            pending_outbox = session.query(OutboxRow).filter(OutboxRow.status == "PENDING").count()
            dead_outbox = session.query(OutboxRow).filter(OutboxRow.status == "DEAD").count()
        return {
            "health": self.health.snapshot(),
            "composition": self.composition_manifest(),
            "runtime": {
                "lease_owned": bool(self.lease and self.lease.acquired),
                "stale_lock_recovered": bool(self.lease and self.lease.stale_recovered),
            },
            "queues": {"outbox_pending": pending_outbox, "outbox_dead": dead_outbox},
            "recent_failed_operations": failed_operations,
        }

    def close(self) -> None:
        try:
            self.engine.dispose()
        finally:
            if self.lease:
                self.lease.release()


def build_runtime(
    profile_root: str | Path,
    *,
    mode: str = "normal",
    acquire_lease: bool = False,
) -> ApplicationRuntime:
    profile = ensure_profile(profile_root)
    lease = RuntimeLease(profile.runtime, profile.root) if acquire_lease else None
    if lease:
        lease.acquire()
    try:
        engine, sf = initialize(profile.db)
        artifacts = ArtifactStore(profile.artifacts, sf)
        evidence = EvidenceService(sf)
        providers = ProviderRegistry()
        runtime = ApplicationRuntime(
            profile=profile,
            engine=engine,
            sf=sf,
            artifacts=artifacts,
            evidence=evidence,
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
            health=HealthService(engine, profile.artifacts, profile.runtime),
            mode=mode,
            lease=lease,
        )
        return runtime
    except Exception:
        if lease:
            lease.release()
        raise
