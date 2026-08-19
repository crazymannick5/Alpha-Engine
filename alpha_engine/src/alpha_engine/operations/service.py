from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from alpha_engine.kernel.errors import IdempotencyConflict
from alpha_engine.kernel.ids import OperationId
from alpha_engine.kernel.serialization import canonical_hash, canonical_json
from alpha_engine.storage.models import JournalRow, OperationRow


class OperationService:
    def __init__(self, sf):
        self.sf = sf

    def admit(self, actor: str, op_type: str, idempotency_key: str, payload: dict) -> tuple[str, bool]:
        request_hash = canonical_hash(payload)
        with self.sf() as session:
            existing = (
                session.query(OperationRow)
                .filter_by(actor=actor, op_type=op_type, idempotency_key=idempotency_key)
                .one_or_none()
            )
            if existing:
                if existing.request_hash != request_hash:
                    raise IdempotencyConflict()
                return existing.id, False
            operation_id = str(OperationId.new())
            now = datetime.now(timezone.utc)
            session.add(
                OperationRow(
                    id=operation_id,
                    actor=actor,
                    op_type=op_type,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    state="ADMITTED",
                    created_at=now,
                )
            )
            session.add(
                JournalRow(
                    operation_id=operation_id,
                    seq=1,
                    event_type="ADMITTED",
                    details_json=canonical_json(payload),
                    recorded_at=now,
                )
            )
            session.commit()
            return operation_id, True

    def transition(self, operation_id: str, state: str, details: dict | None = None) -> None:
        with self.sf() as session:
            operation = session.get(OperationRow, operation_id)
            if operation is None:
                raise KeyError(f"unknown operation: {operation_id}")
            seq = session.query(JournalRow).filter_by(operation_id=operation_id).count() + 1
            operation.state = state
            if state in {"SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}:
                operation.result_json = canonical_json(details or {})
            session.add(
                JournalRow(
                    operation_id=operation_id,
                    seq=seq,
                    event_type=state,
                    details_json=canonical_json(details or {}),
                    recorded_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def snapshot(self, operation_id: str) -> dict[str, Any] | None:
        with self.sf() as session:
            row = session.get(OperationRow, operation_id)
            if row is None:
                return None
            return {
                "id": row.id,
                "actor": row.actor,
                "type": row.op_type,
                "state": row.state,
                "result": json.loads(row.result_json) if row.result_json else None,
            }
