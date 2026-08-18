from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

from ..domain.enums import MarketKind
from ..domain.models import PMThresholdSpec


@dataclass(frozen=True, slots=True)
class RuleParseResult:
    market_kind: MarketKind
    threshold: PMThresholdSpec | None
    clauses: dict[str, str]
    quality_flags: tuple[str, ...]


_COMPARATORS = [
    (re.compile(r"\bat least\s+(-?\d+(?:\.\d+)?)", re.I), ">="),
    (re.compile(r"\bgreater than or equal to\s+(-?\d+(?:\.\d+)?)", re.I), ">="),
    (re.compile(r"\bmore than\s+(-?\d+(?:\.\d+)?)", re.I), ">"),
    (re.compile(r"\bgreater than\s+(-?\d+(?:\.\d+)?)", re.I), ">"),
    (re.compile(r"\bat most\s+(-?\d+(?:\.\d+)?)", re.I), "<="),
    (re.compile(r"\bless than or equal to\s+(-?\d+(?:\.\d+)?)", re.I), "<="),
    (re.compile(r"\bless than\s+(-?\d+(?:\.\d+)?)", re.I), "<"),
    (re.compile(r"\bexactly\s+(-?\d+(?:\.\d+)?)", re.I), "=="),
]


def parse_rules(*, title: str, primary_rules: str | None, secondary_rules: str | None = None) -> RuleParseResult:
    # Rule text has semantic priority over title. Title is only a fallback source for structure.
    rules_text = "\n".join(x for x in (primary_rules, secondary_rules) if x).strip()
    source = rules_text or title
    flags: list[str] = []
    if not rules_text:
        flags.append("RULE_TEXT_MISSING")
    lowered = source.lower()
    clauses: dict[str, str] = {}
    if "void" in lowered or "cancel" in lowered:
        clauses["void_or_cancel"] = "present"
    if "discretion" in lowered or "determination" in lowered:
        clauses["resolution_discretion"] = "present"
    if "before" in lowered or "by " in lowered or "prior to" in lowered:
        temporal_hint = True
    else:
        temporal_hint = False
    threshold = None
    for pattern, op in _COMPARATORS:
        m = pattern.search(source)
        if m:
            try:
                value = Decimal(m.group(1))
            except InvalidOperation:
                flags.append("RULE_PARSE_PARTIAL")
                break
            threshold = PMThresholdSpec(operator=op, threshold=value)
            clauses["threshold_operator"] = op
            clauses["threshold"] = format(value, "f")
            break
    if threshold is not None:
        kind = MarketKind.THRESHOLD_BINARY
    elif temporal_hint:
        kind = MarketKind.TEMPORAL
    else:
        kind = MarketKind.BINARY_YES_NO
    return RuleParseResult(kind, threshold, clauses, tuple(sorted(set(flags))))
