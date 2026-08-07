# Core Design Contract 1.0 — Draft Freeze Candidate

This contract freezes the plugin-facing meaning of the central hub for parallel cylinder development.

## Authority
The core alone owns persistence of canonical records, operations, budgets, permissions, audit, paper ledgers, notifications, and plugin lifecycle. Plugins return candidates/results. They do not open the core database.

## Stable plugin-facing sequence
`ProviderAdapter -> ProviderResult -> Normalizer -> ObservationCandidate -> SignalDetector -> SignalCandidate -> OpportunityDetector -> OpportunityCandidate -> ScoringFeatureProvider -> core Ranking/Radar/Review -> plugin action translator (future) -> core paper simulation -> OutcomeEvaluator -> core evaluation/learning`.

## Frozen v1 compatibility points
- `core_contract = "1.0"` in every manifest.
- Stable plugin IDs use `ae.<domain>.<name>` and never `core` namespaces.
- Plugin calls are synchronous in-process in this draft, but contracts do not expose DB sessions or transport details.
- Candidate objects are Pydantic boundary DTOs and are validated again by core before persistence.
- Every provider result retains raw artifact/evidence linkage before normalization.
- Production plugins may not write canonical tables, send notifications directly, or schedule unmanaged background work.
- All future real-money Level 3+ integration requires a later contract version and explicit authorization.

## Core Compatibility Request
A plugin unable to implement against these public surfaces must emit a structured request rather than importing private modules or modifying core files.
