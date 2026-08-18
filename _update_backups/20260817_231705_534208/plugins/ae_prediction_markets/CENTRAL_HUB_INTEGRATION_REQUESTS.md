# CENTRAL_HUB_INTEGRATION_REQUESTS — ae.prediction_markets

This file records shared changes the Prediction Markets workstream requires or may require. No shared/core file is modified by this overlay.

## PM-INT-001 — Verify/freeze plugin registration contract
**Required shared change:** Confirm the exact frozen `PluginManifest`, registration registry, descriptor, and candidate DTO interfaces exposed by the active Central Hub source baseline.

**Reason:** The builder sandbox did not contain the executable repository/PDK files. The plugin therefore exposes a guarded `register(registry)` implementation and host-neutral DTO mappings without guessing private core internals.

**Expected contract:** Core should accept registrations for provider adapters, normalizers, subject/instrument resolvers, signal detectors, opportunity detectors, scoring feature providers, paper translators, outcome evaluators, UI/CLI contributions, operation descriptors, deterministic fixtures, and compatibility tests.

**Likely affected core files:** `src/alpha_engine/contracts/plugin.py` or `plugins.py`; `src/alpha_engine/plugin_host/pdk.py`; `src/alpha_engine/plugin_host/registry.py`; compatibility tests.

**Cylinder expectation afterward:** `ae_prediction_markets.plugin:register` can be exercised against the real registry without private imports.

## PM-INT-002 — Namespaced plugin repository/UoW contract
**Required shared change:** Provide/confirm namespaced plugin repository and migration APIs without exposing core ORM/session internals.

**Reason:** This overlay deliberately does not open the core database. Provider checkpoints, relation graph projections, qualification state, and settlement working state need durable plugin-owned storage for production use.

**Expected contract:** A bounded key/value or repository/UoW surface scoped to `ae_prediction_markets`, transactional with core operation boundaries where required, plus host-applied namespaced migrations.

**Likely affected core files:** plugin storage contracts/UoW/migration runner only.

**Cylinder expectation afterward:** `persistence/ports.py` receives a concrete host adapter; no plugin SQL against core tables.

## PM-INT-003 — Outcome candidate state/correction contract
**Required shared change:** Confirm a versioned OutcomeCandidate capable of `UNRESOLVED`, `PROVISIONAL`, `DISPUTED`, `FINAL`, `VOID`, `UNRESOLVABLE`, and `CORRECTED`, with evidence refs and supersession.

**Reason:** Prediction-market settlement cannot safely collapse these states to a flat mapping.

**Expected contract:** Core-owned Outcome persistence validates the candidate and preserves correction history.

**Likely affected core files:** outcome/evaluation public contracts and validators.

**Cylinder expectation afterward:** `settlement/evaluator.py` can be mapped losslessly into the core outcome pipeline.

## PM-INT-004 — Generic multi-leg paper action group
**Required shared change:** Add/confirm a generic paper-only multi-leg action group with sequencing/atomicity assumptions.

**Reason:** Cross-contract logic opportunities can require synchronized hypothetical legs. Separate single-leg paper actions must not be misrepresented as atomic.

**Expected contract:** PaperActionGroup with leg dependency/fill policy metadata; no real-order permission.

**Likely affected core files:** paper public DTOs and simulator only.

**Cylinder expectation afterward:** relation opportunities may produce honest multi-leg paper plans; until then this plugin returns research plans only.

## PM-INT-005 — Source terms/rights decision in admitted provider context
**Required shared change:** Confirm typed source-terms/rights constraints in provider operation admission and artifact retention/export.

**Reason:** Production provider activation must honor current terms, retention, and redistribution policy.

**Expected contract:** `SourcePolicyDecision`/equivalent available in admitted provider context, with may-read/capture/derive/export/retain fields and policy version.

**Likely affected core files:** provider registry, operation admission, artifact/evidence policy.

**Cylinder expectation afterward:** provider routes can fail closed before side effects when source policy disallows requested usage.

## PM-INT-006 — Host-managed streaming contract (optional for initial polling)
**Required shared change:** Provide a host-managed bounded stream/subscription capability if high-frequency book monitoring is enabled.

**Reason:** The plugin must not create an independent daemon/event loop.

**Expected contract:** operation lease/cancellation-aware stream callback or subscription protocol with snapshot reconciliation.

**Likely affected core files:** provider host/worker public contracts.

**Cylinder expectation afterward:** WebSocket order-book deltas can be supported without violating operation ownership. Initial implementation remains REST/poll capable.
