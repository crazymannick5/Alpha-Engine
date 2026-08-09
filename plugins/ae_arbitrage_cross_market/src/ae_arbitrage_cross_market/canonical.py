from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any, Mapping


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite Decimal is not canonical")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def canonical_value(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Decimal):
        return {"$decimal": _decimal_text(value)}
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime is not canonical")
        utc = value.astimezone(timezone.utc)
        return {"$datetime": utc.isoformat(timespec="microseconds").replace("+00:00", "Z")}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): canonical_value(value[k]) for k in sorted(value, key=lambda x: str(x))}
    if isinstance(value, (tuple, list)):
        return [canonical_value(v) for v in value]
    if isinstance(value, (set, frozenset)):
        normalized = [canonical_value(v) for v in value]
        return sorted(normalized, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    if isinstance(value, float):
        raise TypeError("float is forbidden at canonical/hash boundaries")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported canonical type: {type(value)!r}")


def canonical_json(value: Any) -> str:
    return json.dumps(canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(*values: Any, schema: str = "arb.canonical.v1") -> str:
    payload = {"schema": schema, "values": [canonical_value(v) for v in values]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
