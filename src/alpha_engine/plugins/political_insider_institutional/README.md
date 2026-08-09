# Political, Insider, and Institutional Activity Cylinder

Implementation scope: deterministic Levels 0–2 domain intelligence. The package contains SEC ownership (Forms 3/4/5) XML normalization, SEC 13F holding normalization and flow-proxy logic, identity resolution, filing-delay/accumulation/cluster detectors, opportunity detectors, named scoring features, a paper-only translator, outcome evaluation, dashboard/CLI descriptors, a host-only namespaced persistence seam, diagnostics, and deterministic tests.

Boundary: this code deliberately does **not** implement a second scheduler, evidence store, canonical DB, permission/budget system, ranking/Radar, review store, paper ledger, notification system, audit system, or another cylinder's storage. External HTTP is possible only through an injected host transport and an admitted request context.

Current integration status: self-contained cylinder logic is runnable and tested. Repository activation remains blocked until the exact Central Hub source baseline and frozen PDK/public contracts are supplied and the integration requests in `CENTRAL_HUB_INTEGRATION_REQUESTS.md` are dispositioned.
