"""Evidence dependency collapse and independent support aggregation."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN

from ..contracts import AlignedContribution, IndependenceGroup, ONE, ZERO
from ..hashing import sha256_canonical

_Q = Decimal("0.000001")


class _UnionFind:
    def __init__(self, keys: list[str]) -> None:
        self.parent = {k: k for k in keys}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def build_independence_groups(contributions: tuple[AlignedContribution, ...]) -> tuple[IndependenceGroup, ...]:
    keys = [c.record.identity for c in contributions]
    uf = _UnionFind(keys)
    roots_by_key = {c.record.identity: set(c.record.ancestry_roots) for c in contributions}
    evidence_by_key = {c.record.identity: set(c.record.evidence_refs) for c in contributions}
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            shared_known_root = bool(roots_by_key[a] and roots_by_key[b] and (roots_by_key[a] & roots_by_key[b]))
            shared_evidence = bool(evidence_by_key[a] & evidence_by_key[b])
            if shared_known_root or shared_evidence:
                uf.union(a, b)
    grouped: dict[str, list[AlignedContribution]] = defaultdict(list)
    by_key = {c.record.identity: c for c in contributions}
    for key in keys:
        grouped[uf.find(key)].append(by_key[key])

    result: list[IndependenceGroup] = []
    for _, members in sorted(grouped.items(), key=lambda kv: min(m.record.identity for m in kv[1])):
        member_refs = tuple(sorted(m.record.identity for m in members))
        ancestry_known = all(bool(m.record.ancestry_roots or m.record.evidence_refs) for m in members)
        # Correlated members do not compound: use the strongest quality/support member.
        quality = max(m.record.quality for m in members)
        support = max((m.record.quality * m.record.support) for m in members)
        gid = "mdep_" + sha256_canonical(member_refs)[:16]
        result.append(
            IndependenceGroup(
                group_id=gid,
                member_refs=member_refs,
                quality=quality.quantize(_Q, rounding=ROUND_HALF_EVEN),
                support=support.quantize(_Q, rounding=ROUND_HALF_EVEN),
                ancestry_known=ancestry_known,
            )
        )
    return tuple(result)


def effective_independent_support(groups: tuple[IndependenceGroup, ...]) -> Decimal | None:
    if not groups:
        return None
    # Unknown ancestry is not promoted to strong independence: discount group support.
    residual = ONE
    for group in groups:
        support = group.support if group.ancestry_known else group.support * Decimal("0.5")
        support = max(ZERO, min(ONE, support))
        residual *= ONE - support
    return (ONE - residual).quantize(_Q, rounding=ROUND_HALF_EVEN)
