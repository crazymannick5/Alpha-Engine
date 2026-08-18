PERSONAL ALPHA ENGINE — PREDICTION MARKETS CYLINDER IMPLEMENTATION OVERLAY

Package scope
- This overlay owns only: plugins/ae_prediction_markets/**
- It does not create, replace, modify, or delete Central Hub files or any other cylinder files.
- It is intentionally structured as a separately installable Python package so parallel cylinder work cannot collide.

Source basis
- Governing implementation directive supplied by the user on 2026-08-07.
- Prediction Markets Architecture and Implementation Specification v0.9 Draft.
- Central Hub Architecture v0.9 Draft public boundary and repository structure.
- The exact current repository ZIP/source tree was not mounted into this builder sandbox; therefore central integration is implemented through public/protocol adapters and guarded compatibility hooks rather than guessed core edits.

Apply
1. Extract this ZIP at the repository root. It only adds plugins/ae_prediction_markets/**.
2. Do not merge any file from this package into src/alpha_engine/**.
3. Install for development with:
   python -m pip install -e plugins/ae_prediction_markets
4. Run verification:
   python plugins/ae_prediction_markets/scripts/verify.py

Expected result
- Deterministic fixture/reference loop passes end to end.
- Unit, contract, failure, security, and resource tests pass.
- Kalshi read-only adapter is available but never performs network I/O without an admitted operation context.
- No live order submission code is present.

Central integration
- Run the central plugin-host compatibility harness against ae_prediction_markets.plugin:register.
- Review CENTRAL_HUB_INTEGRATION_REQUESTS.md before enabling production persistence, central Outcome finalization, streaming, or multi-leg paper semantics.
- If the actual core PDK exposes a different registration method shape, adapt only this plugin's integration/central.py or plugin.py; do not edit core from this workstream.

Rollback
- Because the overlay owns a new isolated tree, rollback is removal of plugins/ae_prediction_markets/** after confirming the core plugin is disabled and no plugin-owned persisted namespace is in use.
- No deletions are required by this package.

Known limitations / blockers
- Exact live repository/PDK source was unavailable in the builder sandbox, so final core-host registration is not claimed as qualified.
- Core namespaced persistence/UoW is represented by protocols only until the hub contract is verified.
- Multi-leg atomic paper action remains a CENTRAL_HUB_INTEGRATION_REQUEST.
- Production source-terms qualification and authenticated Kalshi order-book access require central secret/terms facilities.
