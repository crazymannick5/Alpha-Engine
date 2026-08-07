# Plugin Development Kit 1.0 — Draft

## Builder mode
Every cylinder begins with `WORKSTREAM_MODE: PLUGIN` and a stable `PLUGIN_ID`.

## Allowed contribution types
- provider adapters
- normalizers
- signal detectors
- opportunity detectors
- scoring feature providers
- outcome evaluators
- dashboard descriptors
- CLI descriptors

The host wraps and validates calls. Plugins return candidates/results. The host persists only after validation.

## Prohibited dependencies
A plugin must not import `alpha_engine.storage.models`, obtain SQLAlchemy sessions, write core tables, create its own permission/budget/audit/notification platform, or perform unmanaged background work. Compatibility tests should scan imports and fail activation when this boundary is violated.

## Contract upgrade rule
A plugin names an exact `core_contract`. Unsupported versions are rejected before entrypoint load. Breaking contract changes require a new major contract version and migration guidance.
