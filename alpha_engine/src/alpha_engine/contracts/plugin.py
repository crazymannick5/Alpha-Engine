from __future__ import annotations
from typing import Protocol, Sequence, Mapping, Any
from pydantic import BaseModel, Field
class PluginManifest(BaseModel):
    plugin_id: str
    name: str
    version: str
    core_contract: str = "1.0"
    capabilities: tuple[str,...]=()
    entrypoint: str
    sha256: str | None=None
class ProviderRequest(BaseModel):
    query_type: str
    payload: dict[str,Any]
class ProviderResult(BaseModel):
    provider_id: str
    status: str
    media_type: str='application/json'
    payload: dict[str,Any]
    cost_amount: str='0'
    cost_currency: str='USD'
class ObservationCandidate(BaseModel):
    subject: str
    kind: str
    value: dict[str,Any]
    observed_at: str
    evidence_refs: tuple[str,...]
class SignalCandidate(BaseModel):
    kind: str; subject: str; magnitude: str; confidence: str; evidence_refs: tuple[str,...]
class OpportunityCandidate(BaseModel):
    kind: str; title: str; thesis: str; subject: str; horizon: str; signal_refs: tuple[str,...]
class ProviderAdapter(Protocol):
    descriptor: Mapping[str,Any]
    def execute(self, request: ProviderRequest)->ProviderResult: ...
class Normalizer(Protocol):
    descriptor: Mapping[str,Any]
    def normalize(self, result: ProviderResult, evidence_refs: Sequence[str])->Sequence[ObservationCandidate]: ...
class SignalDetector(Protocol):
    descriptor: Mapping[str,Any]
    def detect(self, observations: Sequence[Mapping[str,Any]])->Sequence[SignalCandidate]: ...
class OpportunityDetector(Protocol):
    descriptor: Mapping[str,Any]
    def detect(self, signals: Sequence[Mapping[str,Any]])->Sequence[OpportunityCandidate]: ...
class ScoringFeatureProvider(Protocol):
    descriptor: Mapping[str,Any]
    def features(self, opportunity: Mapping[str,Any])->Mapping[str,str|None]: ...
class OutcomeEvaluator(Protocol):
    descriptor: Mapping[str,Any]
    def evaluate(self, subject: Mapping[str,Any], outcome: Mapping[str,Any])->Mapping[str,str]: ...
