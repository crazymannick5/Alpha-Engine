from __future__ import annotations

from typing import Protocol

from .contracts import OperationDescriptor, PMRegistration, ScheduleContribution
from .manifest import MANIFEST
from .presentation import CLI_CONTRIBUTIONS, DASHBOARD_CONTRIBUTIONS
from .providers.fixture import FixtureProviderAdapter
from .scoring import FEATURE_NAMES
from .signals import SignalKind
from .opportunities import OpportunityFamily


SCHEDULES = (
    ScheduleContribution(schedule_id="pm.metadata.default", operation_type="PM_SYNC_METADATA", default_interval_seconds=300, scope="enabled_universe", description="Refresh market metadata/rules; disabled until profile explicitly enables the provider/universe."),
    ScheduleContribution(schedule_id="pm.books.default", operation_type="PM_SYNC_BOOKS", default_interval_seconds=15, scope="watched_open_markets", description="Refresh watched open-market books under provider/resource admission."),
    ScheduleContribution(schedule_id="pm.settlement.default", operation_type="PM_SETTLEMENT_CHECK", default_interval_seconds=300, scope="closing_or_unresolved_markets", description="Check settlement evidence for eligible unresolved/closing markets."),
)

OPERATIONS = (
    OperationDescriptor(operation_type="PM_PROVIDER_QUALIFY", permission_scopes=("pm.provider.read.public",), external_side_effects=True, checkpointable=True, resource_class="io"),
    OperationDescriptor(operation_type="PM_SYNC_METADATA", permission_scopes=("pm.provider.read.public", "pm.artifact.capture"), external_side_effects=True, checkpointable=True, resource_class="io"),
    OperationDescriptor(operation_type="PM_SYNC_BOOKS", permission_scopes=("pm.provider.read.public", "pm.artifact.capture"), external_side_effects=True, checkpointable=True, resource_class="io"),
    OperationDescriptor(operation_type="PM_SYNC_TRADES", permission_scopes=("pm.provider.read.public", "pm.artifact.capture"), external_side_effects=True, checkpointable=True, resource_class="io"),
    OperationDescriptor(operation_type="PM_RULE_REFRESH", permission_scopes=("pm.provider.read.public", "pm.artifact.capture"), external_side_effects=True, checkpointable=True, resource_class="io"),
    OperationDescriptor(operation_type="PM_REBUILD_RELATIONS", permission_scopes=("pm.plugin_state.write",), external_side_effects=False, checkpointable=True, resource_class="cpu"),
    OperationDescriptor(operation_type="PM_DETECT", permission_scopes=("pm.signal.propose", "pm.opportunity.propose"), external_side_effects=False, checkpointable=True, resource_class="cpu"),
    OperationDescriptor(operation_type="PM_BACKFILL", permission_scopes=("pm.backfill.request", "pm.provider.read.public", "pm.artifact.capture"), external_side_effects=True, checkpointable=True, resource_class="mixed"),
    OperationDescriptor(operation_type="PM_SETTLEMENT_CHECK", permission_scopes=("pm.provider.read.public", "pm.artifact.capture"), external_side_effects=True, checkpointable=True, resource_class="io"),
)


def build_registration() -> PMRegistration:
    fixture = FixtureProviderAdapter()
    return PMRegistration(
        plugin_id=MANIFEST.plugin_id, plugin_version=MANIFEST.version,
        providers=(fixture.descriptor,),
        signal_detectors=tuple(x.value for x in SignalKind),
        opportunity_detectors=tuple(x.value for x in OpportunityFamily),
        scoring_features=FEATURE_NAMES,
        paper_translators=("pm.paper.translate.v1",), outcome_evaluators=("pm.outcome.evaluate.v1",),
        dashboard=DASHBOARD_CONTRIBUTIONS, cli=CLI_CONTRIBUTIONS, operations=OPERATIONS, schedules=SCHEDULES,
        migration_namespace=MANIFEST.persistence_namespace,
    )


class PublicPluginRegistrationPort(Protocol):
    """Tiny outward port; a PDK adapter must implement it without exposing core-private objects."""
    def register_prediction_markets(self, registration: PMRegistration) -> None: ...


def register(host: PublicPluginRegistrationPort) -> None:
    host.register_prediction_markets(build_registration())
