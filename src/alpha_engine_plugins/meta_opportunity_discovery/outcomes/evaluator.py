"""Bias-resistant thesis predicate evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Mapping


class PredicateState(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class Predicate:
    metric: str
    operator: str
    threshold: Decimal


@dataclass(frozen=True, slots=True)
class PredicateResult:
    predicate: Predicate
    state: PredicateState
    observed: Decimal | None


def evaluate_predicates(predicates: tuple[Predicate, ...], metrics: Mapping[str, Decimal | None]) -> tuple[PredicateResult, ...]:
    out: list[PredicateResult] = []
    for pred in predicates:
        observed = metrics.get(pred.metric)
        if observed is None:
            out.append(PredicateResult(pred, PredicateState.INDETERMINATE, None))
            continue
        if pred.operator == ">=":
            state = PredicateState.TRUE if observed >= pred.threshold else PredicateState.FALSE
        elif pred.operator == "<=":
            state = PredicateState.TRUE if observed <= pred.threshold else PredicateState.FALSE
        elif pred.operator == ">":
            state = PredicateState.TRUE if observed > pred.threshold else PredicateState.FALSE
        elif pred.operator == "<":
            state = PredicateState.TRUE if observed < pred.threshold else PredicateState.FALSE
        elif pred.operator == "==":
            state = PredicateState.TRUE if observed == pred.threshold else PredicateState.FALSE
        else:
            raise ValueError(f"unsupported predicate operator: {pred.operator}")
        out.append(PredicateResult(pred, state, observed))
    return tuple(out)
