from __future__ import annotations
from typing import Protocol, Sequence

from .dto import OperationContext, ProviderRequest, ProviderResult

class CanonicalProjectionReader(Protocol):
    def read_instruments(self, query: object) -> Sequence[object]: ...
    def read_observations(self, query: object) -> Sequence[object]: ...

class ProviderAdapter(Protocol):
    provider_id: str
    def fetch(self, request: ProviderRequest, context: OperationContext) -> ProviderResult: ...

class NamespacedRepositoryPort(Protocol):
    namespace: str
    def put(self, collection: str, key: str, value: object) -> None: ...
    def get(self, collection: str, key: str) -> object | None: ...
