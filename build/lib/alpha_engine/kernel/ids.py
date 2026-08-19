from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from uuid import UUID, uuid4
@dataclass(frozen=True, slots=True)
class TypedId:
    value: UUID
    prefix: ClassVar[str] = "id"
    @classmethod
    def new(cls) -> Self: return cls(uuid4())
    @classmethod
    def parse(cls, raw: str) -> Self:
        marker=f"{cls.prefix}_"
        if not raw.startswith(marker): raise ValueError(f"Expected {marker} identifier")
        return cls(UUID(raw[len(marker):]))
    def __str__(self)->str: return f"{self.prefix}_{self.value}"

def _make(name,prefix): return dataclass(frozen=True,slots=True)(type(name,(TypedId,),{'prefix':prefix,'__module__':__name__}))
OperationId=_make('OperationId','op'); QueryId=_make('QueryId','qry'); ArtifactId=_make('ArtifactId','art')
EvidenceId=_make('EvidenceId','evi'); ObservationId=_make('ObservationId','obs'); SignalId=_make('SignalId','sig')
OpportunityId=_make('OpportunityId','opp'); ScoreId=_make('ScoreId','sco'); DecisionId=_make('DecisionId','dec')
ActionId=_make('ActionId','act'); OutcomeId=_make('OutcomeId','out'); PermissionId=_make('PermissionId','perm')
BudgetId=_make('BudgetId','bud'); BudgetReservationId=_make('BudgetReservationId','budres')
NotificationId=_make('NotificationId','not'); EventId=_make('EventId','ev'); CorrelationId=_make('CorrelationId','cor')
PluginId=_make('PluginId','plg'); ActorId=_make('ActorId','actor')
