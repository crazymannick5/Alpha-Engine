# CENTRAL_HUB_INTEGRATION_REQUESTS — ae.meta_opportunity_discovery

These are shared/core changes required for full production integration.  This plugin workstream does **not** modify the listed central files or invent replacements.

## CHIR-META-001 — Point-in-time canonical snapshot/query facade
- **Required shared change:** public immutable cross-cylinder read API with `as_of`, stable snapshot ID/version, cursor pagination, typed canonical envelopes, availability/effective time, lineage, rights metadata, score components, and capability inventory hash.
- **Reason:** meta discovery cannot lawfully or safely read another cylinder's private tables and must prevent look-ahead across a long scan.
- **Expected contract:** `CanonicalSnapshotQuery -> CanonicalSnapshotPage`; stable cursor within one snapshot.
- **Likely central files:** `docs/contracts/PLUGIN_DEVELOPMENT_KIT_*.md`, public core query contracts, plugin-host PDK/registry adapters.
- **Cylinder expectation afterward:** `adapters/core_boundary.py` maps public DTOs into `CanonicalSnapshot`; no detector changes.

## CHIR-META-002 — Qualified plugin capability inventory
- **Required shared change:** public query of enabled/qualified plugin capabilities, schema versions, universe coverage and health.
- **Reason:** templates are capability-gated and must degrade cleanly when a cylinder is absent.
- **Expected contract:** immutable capability inventory bound to the snapshot/admission context.
- **Likely central files:** public plugin contract/registry query surfaces.
- **Cylinder expectation afterward:** blocked template reasons become host-derived rather than inferred from record types.

## CHIR-META-003 — Evidence ancestry/dependency contract
- **Required shared change:** typed evidence relations and upstream-root query for `DERIVED_FROM`, `SYNDICATED_FROM`, `DUPLICATE_OF`, `COMMON_UPSTREAM`.
- **Reason:** independent support must not double count syndicated evidence.
- **Expected contract:** canonical ancestry root IDs plus dependency reason/provenance.
- **Likely central files:** evidence/lineage public DTOs and query service.
- **Cylinder expectation afterward:** fill `ancestry_roots` from core; current union-find policy remains unchanged.

## CHIR-META-004 — Shared subject relationship read/propose contract
- **Required shared change:** public typed relationships with temporal validity, confidence, provenance, jurisdiction, and governed proposal path.
- **Reason:** broad cross-domain linkage cannot create a rival global identity graph.
- **Expected contract:** `SubjectRelationshipQuery` and optional `RelationshipCandidate` submission.
- **Likely central files:** subject/registry contracts and PDK registration surfaces.
- **Cylinder expectation afterward:** populate `CanonicalRelationship`; unresolved links stay review-only.

## CHIR-META-005 — Multi-source OpportunityCandidate + explanation extension
- **Required shared change:** candidate supports `subject_refs`, contributor canonical refs, structured plugin explanation extension, blockers, and detector fingerprint.
- **Reason:** one subject string + signal refs cannot faithfully represent meta hypotheses.
- **Expected contract:** versioned multi-source opportunity candidate validated by core.
- **Likely central files:** public opportunity contract and plugin PDK.
- **Cylinder expectation afterward:** replace mapping shim in `adapters/core_boundary.candidate_to_core_mapping` with exact public DTO construction.

## CHIR-META-006 — Host-managed plugin storage/migrations
- **Required shared change:** namespaced plugin repository/UoW and migration registrar; no SQLAlchemy session exposed.
- **Reason:** durable run/graph history and novelty calibration cannot directly open the core database.
- **Expected contract:** plugin namespace, migration history, backup/quarantine/export/remove behavior.
- **Likely central files:** plugin host PDK/storage/migration contracts.
- **Cylinder expectation afterward:** implement a production adapter satisfying `persistence.repository.MetaHistoryRepository`.

## CHIR-META-007 — Dependency invalidation feed
- **Required shared change:** cursor/event query for contributor correction, retraction, invalidation, and supersession.
- **Reason:** accepted meta outputs require bounded deterministic re-evaluation when contributors change.
- **Expected contract:** typed dependency event carrying old/new canonical refs and cause ID.
- **Likely central files:** canonical lifecycle/outbox public contract.
- **Cylinder expectation afterward:** schedule `META_REEVALUATE_DEPENDENCY` through the core operation system.

## CHIR-META-008 — Plugin operation context/checkpoint facade
- **Required shared change:** admitted plugin invocation context with operation/correlation IDs, cancellation, checkpoint read/write, resource limits, and injected clock/as-of.
- **Reason:** graph scans need safe cancellation/resume without owning a scheduler.
- **Expected contract:** host-owned `OperationContext` and checkpoint facade.
- **Likely central files:** operation/plugin host public PDK.
- **Cylinder expectation afterward:** wrap `MetaDiscoveryService.run_snapshot` in the host handler and persist its checkpoint through core.

## CHIR-META-009 — Rights/retention allowed-use metadata
- **Required shared change:** machine-readable rights tags propagated through canonical evidence/records with inheritance rules.
- **Reason:** meta derivation must not erase source restrictions; model/export use needs strictest-source gating.
- **Expected contract:** allowed-use/retention tags on canonical envelopes and artifacts.
- **Likely central files:** evidence/provider public DTOs.
- **Cylinder expectation afterward:** enforce host policy before model/export operations; deterministic local synthesis remains available where permitted.

## CHIR-META-010 — Core-mediated paper action translation broker
- **Required shared change:** resolve sanctioned translators by capability + canonical target + universe and execute them through core paper admission.
- **Reason:** the meta plugin must not import source-cylinder action mechanics or mutate paper ledgers.
- **Expected contract:** `ActionTranslationRegistry.resolve(...) -> translator`; core invokes translator and simulator.
- **Likely central files:** public paper/plugin PDK contracts.
- **Cylinder expectation afterward:** opportunities may move from `WATCH_ONLY` to paper-ready only when all required translators are qualified.

## CHIR-META-011 — Outcome evaluator registration
- **Required shared change:** thesis predicate/evaluator registration with horizon, availability cutoff, provisional/final/corrected states.
- **Reason:** meta success is not necessarily one instrument settlement.
- **Expected contract:** plugin evaluator returns typed evaluation result; core persists outcome/evaluation history.
- **Likely central files:** outcome/evaluation PDK contracts.
- **Cylinder expectation afterward:** register `outcomes/evaluator.py` policies instead of invoking them privately.

## CHIR-META-012 — Stable plugin ID reconciliation
- **Required shared change:** reconcile master catalog `ae.meta_opportunity` with cylinder directive `ae.meta_opportunity_discovery`.
- **Reason:** plugin identity must be stable before install/upgrade history exists.
- **Expected contract:** accept `ae.meta_opportunity_discovery` as canonical ID, with migration alias only if an installed prior identity exists.
- **Likely central files:** accepted feature catalog/design contract/PDK identity registry.
- **Cylinder expectation afterward:** no code rename unless Primary Development chooses the alternate ID.
