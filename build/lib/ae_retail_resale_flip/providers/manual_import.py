from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from ..contracts import CostQuotaEstimate, OperationContext, ProviderDescriptor, ProviderResult, QueryIntent, RetailQuery
from .base import require_admitted


class ManualImportAdapter:
    descriptor = ProviderDescriptor(
        provider_id="retail.manual_import",
        adapter_version="1.0.0",
        capabilities=frozenset(QueryIntent),
        terms_version="user-provided-v1",
        qualified_at=None,
        live_network=False,
        retention_class="user-controlled",
        machine_learning_use_allowed=None,
    )

    def estimate(self, request: RetailQuery) -> CostQuotaEstimate:
        return CostQuotaEstimate(Decimal("0"), Decimal("0"), 0)

    def execute(self, request: RetailQuery, ctx: OperationContext, payload: bytes | str | None = None) -> ProviderResult:
        require_admitted(ctx)
        if payload is None:
            raise ValueError("manual import requires payload")
        raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if len(raw.encode("utf-8")) > 5_000_000:
            raise ValueError("manual import payload exceeds 5 MB safety bound")
        stripped = raw.lstrip()
        records: list[Mapping[str, Any]]
        media = "application/json"
        if stripped.startswith("[") or stripped.startswith("{"):
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                parsed = parsed.get("records", [parsed])
            if not isinstance(parsed, list) or not all(isinstance(x, dict) for x in parsed):
                raise ValueError("JSON payload must be an object or array of objects")
            records = parsed
        else:
            media = "text/csv"
            reader = csv.DictReader(io.StringIO(raw))
            records = [dict(row) for row in reader]
        if len(records) > 10_000:
            raise ValueError("manual import exceeds 10,000 record safety bound")
        return ProviderResult(self.descriptor.provider_id, self.descriptor.adapter_version, media, tuple(records), datetime.now(timezone.utc))
