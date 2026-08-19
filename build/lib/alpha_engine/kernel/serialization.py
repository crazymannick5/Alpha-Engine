import hashlib, json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from dataclasses import asdict, is_dataclass

def _default(o):
    if isinstance(o, Decimal): return format(o,'f')
    if isinstance(o, datetime): return o.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    if isinstance(o, Enum): return o.value
    if is_dataclass(o): return asdict(o)
    return str(o)
def canonical_json(value)->str:
    return json.dumps(value,default=_default,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def canonical_hash(value)->str: return hashlib.sha256(canonical_json(value).encode()).hexdigest()
