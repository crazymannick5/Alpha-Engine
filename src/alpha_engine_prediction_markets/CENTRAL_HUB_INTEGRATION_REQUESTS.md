# CENTRAL_HUB_INTEGRATION_REQUESTS — ae.prediction_markets

The cylinder does **not** edit any shared/core file. The following shared capabilities are required to fully attach this implementation to the Central Hub. These preserve the stable PM-CCR identifiers from the governing cylinder architecture.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-001 — Generic multi-leg/contingent paper action
- **Required shared change:** expose versioned generic paper action groups with legs, sequencing/dependency/atomicity policy and fill-policy metadata.
- **Reason:** cross-contract PM research can require multiple hypothetical legs; separate single-leg actions cannot be represented as atomic.
- **Expected contract:** `PaperActionGroup`/leg dependency DTO accepted by the central paper engine; Level 2 only.
- **Files likely affected:** central public paper contracts/services and associated schemas/migrations/tests.
- **Cylinder expectation afterward:** `ae.prediction_markets` will translate strict multi-leg research plans through that public contract; until then it emits research plans only.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-002 — Typed canonical extension records
- **Required shared change:** freeze a versioned extension-record mechanism for plugin-specific instrument/payoff/rule structures on canonical observations/subjects.
- **Reason:** minimal string/dict fields cannot safely convey binary/multi-outcome/threshold/temporal PM semantics across providers.
- **Expected contract:** opaque but schema-registered/versioned extension payload with size validation and provenance refs.
- **Files likely affected:** public observation/subject/plugin contracts, validators/schema registry.
- **Cylinder expectation afterward:** map `PMMarket`, `PMRuleVersion`, `PMOutcomeSet`, and related typed payloads through sanctioned extension records without core-private imports.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-003 — Plugin namespaced repository/UoW API
- **Required shared change:** freeze plugin repository/UoW and migration-runner interfaces for namespaced tables.
- **Reason:** this overlay includes plugin-owned migration SQL and repository protocols but intentionally does not open the core database.
- **Expected contract:** host-applied migration descriptors and transaction-scoped namespaced repository handle without access to unrelated tables.
- **Files likely affected:** public PDK persistence contracts, plugin migration runner, compatibility tests.
- **Cylinder expectation afterward:** bind `ae_pm_*` projections/checkpoints through the host implementation; no direct SQLAlchemy/core DB access.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-004 — Host-managed bounded stream provider
- **Required shared change:** expose a cancellation/lease-aware host-managed stream/subscription provider protocol, or freeze poll-only v1.
- **Reason:** efficient orderbook streaming requires sequence/gap/reconnect lifecycle beyond synchronous one-shot provider calls.
- **Expected contract:** admitted stream context, bounded messages, checkpointed sequence, cancellation, resnapshot request.
- **Files likely affected:** public provider/operation contracts and host wrappers.
- **Cylinder expectation afterward:** add WebSocket adapter without an independent daemon/event loop; REST polling remains valid meanwhile.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-005 — Typed source-terms enforcement context
- **Required shared change:** pass current source-policy/retention/export/model-use decisions into admitted provider/artifact operations.
- **Reason:** provider terms/retention rules must gate acquisition, artifact capture and export; route availability is not legal permission.
- **Expected contract:** `SourcePolicyDecision`/rights profile with retention/export restrictions and qualification version.
- **Files likely affected:** provider qualification, data query, artifact retention/export public contracts.
- **Cylinder expectation afterward:** production Kalshi/other adapters activate only when the exact provider capability is currently qualified.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-006 — Outcome candidate and correction contract
- **Required shared change:** freeze rich outcome candidate state/finality/conflict/supersession/evidence fields.
- **Reason:** prediction markets require provisional/disputed/final/void/unresolvable/corrected settlement semantics.
- **Expected contract:** versioned `OutcomeCandidate` supporting evidence refs, state, supersedes, correction/conflict and finality.
- **Files likely affected:** public outcome/evaluation contracts, validators, persistence/migration and paper settlement reconciliation.
- **Cylinder expectation afterward:** map `PMOutcomeEvaluation` directly through central outcome validation and correction handling.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-007 — Read-only subject relationship/graph interface
- **Required shared change:** expose sanctioned read-only subject/event relation queries and relation-candidate contribution.
- **Reason:** instrument relations can stay plugin-local, but shared real-world subject/event relations should not be duplicated.
- **Expected contract:** point-in-time typed relation query/candidate service.
- **Files likely affected:** public registry/identity/query contracts and relation validation.
- **Cylinder expectation afterward:** use canonical subject/event links for cross-domain relation resolution while keeping PM payoff relations plugin-local.

## CENTRAL_HUB_INTEGRATION_REQUEST PM-CCR-008 — Material-change internal event contribution
- **Required shared change:** expose validated internal-event candidate submission/notification eligibility for plugin-detected material changes.
- **Reason:** rule/close/source/settlement corrections must surface centrally without the plugin sending notifications itself.
- **Expected contract:** versioned material-change event candidate committed by core, then central notification policy decides delivery.
- **Files likely affected:** public event/plugin contracts and notification-intent bridge.
- **Cylinder expectation afterward:** rule/settlement correction detectors contribute events; no direct email/notification code.

## Implementation-specific registration note
`alpha_engine_prediction_markets.plugin.register()` currently accepts the plugin-owned `PublicPluginRegistrationPort` with a single `register_prediction_markets(PMRegistration)` method. The actual repository PDK was not available in this runtime, so this is intentionally an outward port rather than an edit to central registry code. Primary Development should adapt/freeze this at the public PDK layer during integration, not inside this cylinder.
