# CENTRAL_HUB_INTEGRATION_REQUESTS — Political / Insider / Institutional Activity

This cylinder does **not** modify shared/core files. The following integration work is requested from the Central Hub owner before repository-level activation is considered complete.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-001 — Canonical plugin ID alias/freeze
- Required shared change: freeze `ae.political_insider_institutional` as the canonical ID or provide an explicit alias/migration from `ae.institutional_activity`.
- Reason: the architecture assignment and master catalog currently disagree.
- Expected contract: plugin manifest validator accepts the frozen ID and, if necessary, a versioned alias map.
- Likely core files: plugin manifest schema/registry and central feature catalog bindings.
- Cylinder expectation afterward: `manifest.plugin_id` can be validated without local renaming or duplicate installation identity.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-002 — Temporal relation assertion/query contract
- Required shared change: public core relation DTO/API for subject/object relation type, valid-from/to, evidence refs, confidence, correction/supersession.
- Reason: identity/role/ownership relations must be shareable without a plugin-owned global graph.
- Expected contract: versioned relation candidate + as-of query service.
- Likely core files: public contracts and subject/identity service surfaces.
- Cylinder expectation afterward: resolver outputs can be adopted/queryable by other cylinders through core only.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-003 — Ranged numeric canonical value
- Required shared change: canonical range value with lower/upper/open bounds, currency/unit, source label.
- Reason: public-official, PSC, lobbying and other disclosures often publish brackets rather than exact values.
- Expected contract: range type accepted in observation/evidence extension fields without midpoint coercion.
- Likely core files: canonical value contracts and serialization/schema files.
- Cylinder expectation afterward: `RangeMoney` maps losslessly to core.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-004 — Named availability timestamps / information cutoff
- Required shared change: public DTO semantics for transaction/execution/effective/filing/accepted/published/ingested and an explicit earliest-known/public-availability cutoff.
- Reason: look-ahead safety and paper simulation must not backdate delayed disclosures.
- Expected contract: core candidate validation and paper admission enforce the information cutoff.
- Likely core files: observation/evidence/time contracts and paper admission.
- Cylinder expectation afterward: `DisclosureTimes` maps directly and earliest paper time is enforceable centrally.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-005 — Source terms/use-policy hook
- Required shared change: source policy registry/evaluator callable at acquire/store/export/report stages.
- Reason: House/FEC and other public datasets can carry use restrictions beyond acquisition.
- Expected contract: versioned policy decision with deny/degrade reason.
- Likely core files: provider/source policy and export services.
- Cylinder expectation afterward: restricted export can be centrally denied without plugin-specific bypass logic.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-006 — Correction propagation API
- Required shared change: public correction/supersession service that accepts old/new canonical refs, reason/evidence, and triggers dependency refresh.
- Reason: amendments, cancellations, parser corrections and identity corrections must invalidate/recompute dependent outputs.
- Expected contract: durable correction record + outbox event + dependent refresh semantics.
- Likely core files: observation/fact/signal/opportunity services and outbox contracts.
- Cylinder expectation afterward: historical revisions remain immutable while dependent signals/opportunities are refreshed centrally.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-007 — Namespaced plugin persistence host
- Required shared change: host-owned plugin persistence/UoW interface with namespace isolation and migration execution.
- Reason: this cylinder needs rebuildable projections/resolver evidence without direct DB/session access.
- Expected contract: key/value or repository-style namespaced service plus migration registration; no raw SQLAlchemy session exposure.
- Likely core files: plugin host PDK/persistence service/migration coordinator.
- Cylinder expectation afterward: `persistence.NamespacedPersistencePort` is replaced/adapted to the frozen host interface.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-008 — Paper action translator registration
- Required shared change: frozen PDK registration and input/output contract for Level-2 paper action translators.
- Reason: the cylinder produces proposals but must not mutate the paper ledger.
- Expected contract: capability-gated translator registration; output hard-carries `paper_only=true` and core handles admission/fills/ledger.
- Likely core files: PDK contribution descriptors and paper service boundary.
- Cylinder expectation afterward: `PaperTranslator.translate()` is host-invoked only after review/permission checks.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-009 — Canonical instrument/subject linkage
- Required shared change: sanctioned query/registry for canonical instruments and public subject relationships.
- Reason: paper opportunities may target securities or prediction subjects without reading another plugin's private storage.
- Expected contract: canonical ref resolution through core public services.
- Likely core files: domain registry/instrument query contract.
- Cylinder expectation afterward: unresolved opportunities can become paper-eligible without cross-plugin imports.

## CENTRAL_HUB_INTEGRATION_REQUEST PIIA-CHR-010 — Fine-grained provenance attachment
- Required shared change: evidence relation extension carrying source field/path/page/row and parser version.
- Reason: public record detail must reconstruct normalized fields, not only artifact-level lineage.
- Expected contract: versioned provenance attachment accepted by evidence service.
- Likely core files: evidence/provenance public DTOs and persistence.
- Cylinder expectation afterward: field paths emitted by normalizers can be centrally persisted and displayed.
