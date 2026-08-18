from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any


def _canon(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python", exclude_none=False)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime is not canonical")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _canon(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
    if isinstance(value, (list, tuple)):
        return [_canon(v) for v in value]
    if isinstance(value, set):
        return sorted((_canon(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_canon(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
