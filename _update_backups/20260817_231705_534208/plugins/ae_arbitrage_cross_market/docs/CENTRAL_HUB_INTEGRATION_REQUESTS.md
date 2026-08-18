# CENTRAL_HUB_INTEGRATION_REQUESTS

These are integration requests, not authorization for this cylinder to edit shared files.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-001 — Frozen plugin registration adapter
- **Required shared change:** freeze the public PDK `PluginContributions`/registration DTO and supported plugin discovery root.
- **Reason:** this overlay exposes a complete `registration_bundle()` but cannot safely import an unfrozen or unavailable core-private registration model.
- **Expected interface/contract:** host maps or directly accepts resolver, detector, feature descriptors, paper translator, outcome evaluator, learning recommender, dashboard/CLI descriptors, operation descriptors, and permission scopes.
- **Files likely affected:** central `src/alpha_engine/contracts/plugins.py`, `src/alpha_engine/plugin_host/**`, possibly root packaging/discovery configuration.
- **Cylinder expectation afterward:** the host can discover `ae.arbitrage_cross_market`, validate manifest compatibility, and bind each contribution without cylinder-side core imports.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-002 — Canonical cross-cylinder read projections
- **Required shared change:** expose permission-filtered, versioned instrument/subject/observation/contract-term projections with evidence and freshness metadata.
- **Reason:** cross-market comparison must consume sanctioned canonical outputs and may not import another cylinder's storage.
- **Expected interface/contract:** `CanonicalProjectionReader`-equivalent query service returning opaque canonical refs plus timestamps/evidence/version.
- **Files likely affected:** central data-query/projection contracts and query services.
- **Cylinder expectation afterward:** production comparison snapshots can be constructed from core projections rather than fixture/local inputs.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-003 — Evidence-backed candidate envelopes
- **Required shared change:** freeze typed candidate envelopes for observations/signals/opportunities and `FeatureValue` missingness/provenance.
- **Reason:** plugin detectors must return candidates while core owns canonical persistence/ranking.
- **Expected interface/contract:** candidate DTOs accept plugin schema ID, input hash, evidence refs, feature unit, quality, uncertainty and missing reason.
- **Files likely affected:** central contracts for observations/signals/opportunities/ranking and plugin compatibility validation.
- **Cylinder expectation afterward:** `DetectorResult` can be mapped losslessly into canonical core candidates without JSON-in-string workarounds.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-004 — Namespaced plugin persistence/UoW
- **Required shared change:** provide host-applied namespaced migrations and a repository/UoW port restricted to the plugin namespace.
- **Reason:** relationship versions, evaluations and checkpoints need durability, while direct DB access is prohibited.
- **Expected interface/contract:** host applies `migrations/0001_arbitrage_namespace.sql` or a semantically equivalent migration and injects a namespaced repository port.
- **Files likely affected:** central plugin-host migration service and storage/UoW surfaces.
- **Cylinder expectation afterward:** replace in-memory repositories in production composition without changing domain/application logic.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-005 — Eligibility/terms capability snapshot
- **Required shared change:** expose effective-dated universe/jurisdiction/account/venue eligibility with reason codes.
- **Reason:** provider availability alone must never imply paper action eligibility.
- **Expected interface/contract:** read-only eligibility snapshot keyed by operation/universe/venue/capability.
- **Files likely affected:** central permissions/registries/provider qualification contracts.
- **Cylinder expectation afterward:** detector policy `eligibility_allowed/reason` is populated from authoritative core state.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-006 — Generic Level-2 multi-leg paper contract
- **Required shared change:** freeze a core-owned non-atomic multi-leg paper plan/action contract with partial fills, contingencies, residual exposure and max inter-leg skew.
- **Reason:** cylinder can translate and preview plans but must not mutate the central paper ledger.
- **Expected interface/contract:** host accepts a `PaperMultiLegPlanCandidate`-equivalent DTO and performs authoritative deterministic simulation/ledger posting.
- **Files likely affected:** central simulation contracts/services, plugin action-translator registry, paper DTOs.
- **Cylinder expectation afterward:** register `PaperPlanTranslator`; plugin preview remains diagnostic only.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-007 — Outcome evaluator registration
- **Required shared change:** freeze an evidence-snapshot outcome evaluator contract supporting pending/provisional/final/disputed/unresolvable/corrected states.
- **Reason:** plugin owns domain evaluation logic but core owns outcome lifecycle and persistence.
- **Expected interface/contract:** evaluator returns candidate metrics/evidence/correction metadata; core validates and persists.
- **Files likely affected:** central outcome/evaluation contracts and plugin registry.
- **Cylinder expectation afterward:** `ArbitrageOutcomeEvaluator` can be registered without direct outcome writes.

## CENTRAL_HUB_INTEGRATION_REQUEST ARB-INT-008 — Declarative dashboard/CLI schema
- **Required shared change:** freeze typed descriptor schemas and route/command registration.
- **Reason:** this cylinder must contribute views/commands without editing the central shell.
- **Expected interface/contract:** declarative descriptors with route/command IDs, permissions, query dependencies, redaction policy and no arbitrary UI bypass.
- **Files likely affected:** central desktop/CLI/plugin-host contribution contracts.
- **Cylinder expectation afterward:** descriptors in `presentation/descriptors.py` are validated and rendered/registered by the host.
