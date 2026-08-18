# Bounded implementation status

## Materially implemented in this overlay

- immutable/versioned cylinder DTOs with Decimal/ranged-value and multi-time semantics;
- deterministic canonical serialization/hashing;
- jurisdiction/source-family configuration gates;
- deterministic temporal identity resolver with explicit MATCHED/AMBIGUOUS/UNRESOLVED outcomes;
- filing rule/business-calendar logic;
- host-admitted SEC EDGAR transport adapter (no direct unmanaged HTTP client);
- secure bounded XML parsing with DTD/entity rejection;
- SEC Forms 3/4/5 ownership XML normalization, including derivative/non-derivative separation and unknown-code preservation;
- SEC 13F information-table normalization and comparable-vintage institutional flow-proxy detection;
- source-neutral official-record envelope normalization for beneficial-ownership, public-official, lobbying and procurement records once an approved adapter/manual import has produced the admitted envelope;
- filing-delay, accumulation/distribution, clustered-actor and 13F flow-proxy signals;
- unusual-activity and cluster opportunity candidates with motive/wrongdoing-neutral wording;
- named deterministic scoring features only (no local ranking engine);
- paper-only action proposal translation with earliest-public-availability guard;
- directional outcome evaluation that explicitly avoids actor-intent/legal labels;
- host-only namespaced persistence port/projection repository (no DB/session ownership);
- dashboard/CLI contribution descriptors and safe wording policy;
- deterministic unit/integration/security/boundary fixtures.

## Deliberately unfinished / carried forward

These are not replaced by placeholders or a shadow central system:

1. exact Central Hub PDK registration/activation, because the current repository/PDF-contract bytes were not mounted in this session;
2. live/official adapters for Schedule 13D/13G, House PTR, Senate PTR, LDA, USAspending, UK Companies House PSC, and UK Parliament RMFI;
3. production source-policy/terms enforcement, which requires the central source-policy hook;
4. durable plugin migrations, which require the central namespaced persistence host;
5. canonical temporal relationship adoption, correction propagation, fine-grained provenance adoption, and instrument linkage, which require the Central Hub requests documented separately;
6. Central Hub scheduling, operation registration, canonical persistence, Radar/review, real dashboard wiring, and paper ledger/outcome persistence; these remain core-owned and must not be duplicated here.

The next implementation pass should use the exact repository baseline and frozen PDK to wire these existing cylinder functions into the host, then add remaining qualified official source adapters rather than redesigning the domain logic.
