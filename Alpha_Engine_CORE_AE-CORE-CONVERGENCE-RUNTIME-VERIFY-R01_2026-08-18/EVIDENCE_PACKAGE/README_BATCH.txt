PERSONAL ALPHA ENGINE — BUILDER RETURN
Package: Alpha_Engine_CORE_AE-CORE-CONVERGENCE-RUNTIME-VERIFY-R01_2026-08-18
Status: BUILDER_INCOMPLETE
Workstream: CORE
Source binding: repo context export hashes recorded in EVIDENCE_PACKAGE/source_state.json

WHAT THIS PACKAGE DOES
- Adds one root-level source-development install/run doorway.
- Adds authoritative composed runtime lifecycle for start/demo/status/stop while reusing existing Central Hub authorities.
- Replaces false shallow health with explicit mandatory readiness checks.
- Preserves/refactors the deterministic reference loop through the composed runtime and makes it idempotent within a profile.
- Adds canonical Python non-fail-fast verification, feature traceability, retained evidence, verifier self-tests, plugin discovery qualification, and readiness computation.
- Adds durable purpose/provider-decision/defect convergence records.

APPLICATION
Use apply_update_package_v2.py with **APPLY_PACKAGE** as the selected package directory. Choose **Standard** mode because this overlay contains both CREATE and REPLACE files. Do not use Replacements Only. There are no requested deletions.

Apply only after the independent reviewer / Primary Development authority accepts this builder return for integration. The package is mechanically ready to overlay, but its builder status is incomplete because qualification blockers remain.

POST-APPLY
From the authoritative repository root:
  python -m pip install -e ".[dev]"
  alpha demo --reset --seed-only --profile ./profiles/reviewer-demo
  alpha status --profile ./profiles/reviewer-demo
  alpha verify quick
  alpha verify feature AE-RUN-003
  alpha verify full
  alpha qualify

Expected deterministic result for this builder state: feature/quick/full are green. Qualification remains NOT_QUALIFIED with the blockers listed in limitations/known_blockers.md until their owning capabilities/environments are completed.

ROLLBACK / PARTIAL APPLY
The current installer is not package-transactional. Preserve the pre-apply repository snapshot. Use its replacement backups/rollback manifest for REPLACE files. If a partial apply must be reversed, remove CREATE paths only after checking they still match the package source_sha256 values in apply_manifest.json; do not delete a file that has changed since application. Re-run the post-apply verification after recovery.
