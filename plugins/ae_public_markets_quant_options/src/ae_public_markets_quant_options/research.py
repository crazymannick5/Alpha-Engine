from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Mapping, Sequence

from .errors import LookaheadDetected, ResourceLimit
from .models import Bar
from .point_in_time import require_available


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_id: str
    subjects: tuple[str, ...]
    start: datetime
    end: datetime
    lookback: int
    rebalance_every: int
    cost_bps: Decimal
    seed: int = 0
    max_rows: int = 250_000

    def canonical_hash(self) -> str:
        payload = {
            "experiment_id": self.experiment_id,
            "subjects": self.subjects,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "lookback": self.lookback,
            "rebalance_every": self.rebalance_every,
            "cost_bps": str(self.cost_bps),
            "seed": self.seed,
            "max_rows": self.max_rows,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    spec_hash: str
    total_return: Decimal
    trades: int
    observations_used: int
    result_hash: str
    diagnostics: tuple[str, ...]


def run_momentum_research(spec: ExperimentSpec, bars: Sequence[Bar]) -> ExperimentResult:
    selected = [b for b in bars if b.subject_id in spec.subjects and spec.start <= b.effective_at <= spec.end]
    if len(selected) > spec.max_rows:
        raise ResourceLimit(f"{len(selected)} rows exceeds {spec.max_rows}")
    by_subject: dict[str, list[Bar]] = {}
    for b in selected:
        # Point-in-time hard gate: observation cannot be used before it was available.
        if b.available_at > b.effective_at:
            # We can still use it only from available_at forward.  This compact runner
            # uses the bar date itself as decision time, so delayed availability is illegal.
            raise LookaheadDetected(f"bar {b.evidence_ref} available after its decision timestamp")
        by_subject.setdefault(b.subject_id, []).append(b)
    cash = Decimal("1")
    trades = 0
    diagnostics = []
    for sid, rows in sorted(by_subject.items()):
        rows.sort(key=lambda b: b.effective_at)
        if len(rows) <= spec.lookback + 1:
            diagnostics.append(f"{sid}:insufficient_history")
            continue
        # Long if trailing lookback return was positive, applied to NEXT bar return.
        for i in range(spec.lookback, len(rows)-1, max(1, spec.rebalance_every)):
            signal = rows[i].close / rows[i-spec.lookback].close - Decimal("1")
            next_ret = rows[i+1].close / rows[i].close - Decimal("1")
            if signal > 0:
                cost = spec.cost_bps / Decimal("10000")
                cash *= Decimal("1") + next_ret - cost
                trades += 1
    total = cash - Decimal("1")
    result_payload = f"{spec.canonical_hash()}|{total}|{trades}|{len(selected)}"
    result_hash = sha256(result_payload.encode()).hexdigest()
    return ExperimentResult(spec.canonical_hash(), total, trades, len(selected), result_hash, tuple(diagnostics))
