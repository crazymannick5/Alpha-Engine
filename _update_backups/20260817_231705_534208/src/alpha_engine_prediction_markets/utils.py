from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def require_utc(value: datetime, *, field: str = "timestamp") -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return require_utc(value).isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return _canonical(value.model_dump(mode="python", exclude_none=False))
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, set):
        return sorted((_canonical(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(schema: str, value: Any) -> str:
    payload = f"{schema}\n{canonical_json(value)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def clamp01(value: Decimal) -> Decimal:
    return min(Decimal("1"), max(Decimal("0"), value))
