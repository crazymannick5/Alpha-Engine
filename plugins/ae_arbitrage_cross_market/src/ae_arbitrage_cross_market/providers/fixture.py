from __future__ import annotations
from datetime import datetime, timezone
from typing import Mapping

from ..canonical import canonical_hash
from ..contracts.dto import OperationContext, ProviderRequest, ProviderResult
from .base import GuardedProviderMixin, ProviderDescriptor

class FixtureQuoteProvider(GuardedProviderMixin):
    provider_id = "arb.fixture"
    descriptor = ProviderDescriptor(
        provider_id=provider_id,
        query_intents=("arb.fixture.quote_batch.v1",),
        supports_live_network=False,
        requires_budget_reservation=False,
        qualification_status="FIXTURE_ONLY",
        retention_policy_ref="fixture.permanent",
        adapter_version="1.0.0",
    )

    def __init__(self, payloads: Mapping[str, Mapping[str, object]]):
        self._payloads = dict(payloads)

    def fetch(self, request: ProviderRequest, context: OperationContext) -> ProviderResult:
        self._require_admission(request, context)
        key = str(request.params.get("fixture_id", ""))
        if key not in self._payloads:
            raise KeyError(f"unknown fixture {key}")
        payload = self._payloads[key]
        request_id = canonical_hash(self.provider_id, request.query_intent, key, request.as_of, schema="arb.provider_request.v1")
        evidence_ref = f"fixture:{key}:{canonical_hash(payload, schema='arb.fixture_payload.v1')[:16]}"
        return ProviderResult(self.provider_id, request_id, payload, (evidence_ref,), request.as_of, request.as_of)
