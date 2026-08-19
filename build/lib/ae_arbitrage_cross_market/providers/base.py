from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from ..contracts.dto import OperationContext, ProviderRequest, ProviderResult

class ProviderPolicyError(RuntimeError):
    pass

@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    query_intents: tuple[str, ...]
    supports_live_network: bool
    requires_budget_reservation: bool
    qualification_status: str
    retention_policy_ref: str
    adapter_version: str

class GuardedProviderMixin:
    descriptor: ProviderDescriptor

    def _require_admission(self, request: ProviderRequest, context: OperationContext) -> None:
        if context.cancelled:
            raise ProviderPolicyError("operation is cancelled")
        if not context.permission_allowed:
            raise ProviderPolicyError("provider request denied by permission snapshot")
        if self.descriptor.requires_budget_reservation and not context.budget_reservation_ref:
            raise ProviderPolicyError("provider request has no budget reservation")
        if request.query_intent not in self.descriptor.query_intents:
            raise ProviderPolicyError("provider does not support requested query intent")
