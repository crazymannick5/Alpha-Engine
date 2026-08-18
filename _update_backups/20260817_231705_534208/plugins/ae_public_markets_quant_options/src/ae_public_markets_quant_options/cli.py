from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from .fixtures import fixture_adapter
from .models import Dataset
from .providers import QueryIntent
from .service import PublicMarketsCylinder


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pmqo-fixture", description="Offline PMQO qualification helper; no core side effects")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify-fixture")
    args = parser.parse_args(argv)
    if args.cmd == "verify-fixture":
        now = datetime(2026, 2, 15, tzinfo=timezone.utc)
        request = QueryIntent(Dataset.OHLCV, ("SUBJ-NEW",), None, None, now, "1D", "PRIMARY")
        scan = PublicMarketsCylinder().fixture_data_to_candidates(fixture_adapter(now), request, now)
        print(json.dumps({
            "bars": len(scan.bars),
            "signals": [asdict(s) for s in scan.signals],
            "opportunities": [asdict(o) for o in scan.opportunities],
        }, default=_json_default, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
