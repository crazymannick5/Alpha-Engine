from __future__ import annotations

from ..domain.relationships import RelationshipEvaluation, RelationshipSpec

class InMemoryRelationshipRepository:
    def __init__(self) -> None:
        self._specs: dict[tuple[str, int], RelationshipSpec] = {}
        self._evaluations: dict[str, list[RelationshipEvaluation]] = {}

    def save_spec(self, spec: RelationshipSpec) -> None:
        key = (spec.relationship_id, spec.version)
        existing = self._specs.get(key)
        if existing is not None and existing != spec:
            raise ValueError("relationship versions are immutable")
        self._specs[key] = spec

    def get_spec(self, relationship_id: str, version: int | None = None) -> RelationshipSpec | None:
        if version is not None:
            return self._specs.get((relationship_id, version))
        versions = [v for (rid, v) in self._specs if rid == relationship_id]
        return None if not versions else self._specs[(relationship_id, max(versions))]

    def save_evaluation(self, evaluation: RelationshipEvaluation) -> None:
        items = self._evaluations.setdefault(evaluation.relationship_id, [])
        if evaluation not in items:
            items.append(evaluation)

    def evaluations(self, relationship_id: str) -> tuple[RelationshipEvaluation, ...]:
        return tuple(self._evaluations.get(relationship_id, ()))

class InMemoryCheckpointRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict[str, str]] = {}

    def put(self, operation_id: str, partition_key: str, cursor: str, output_hash: str, status: str) -> None:
        self._items[(operation_id, partition_key)] = {"cursor": cursor, "output_hash": output_hash, "status": status}

    def get(self, operation_id: str, partition_key: str) -> dict[str, str] | None:
        item = self._items.get((operation_id, partition_key))
        return None if item is None else dict(item)
