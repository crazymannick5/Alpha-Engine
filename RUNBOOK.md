# Personal Alpha Engine — Source Development Runbook

The repository root is the authoritative source-development doorway. The historical nested `alpha_engine/` project remains the core component source tree, but normal development installation and runtime commands should be invoked from the repository root.

## Requirements

- Python 3.12 or newer.
- No provider credentials are required for deterministic demo or verification.
- Desktop use requires the optional PySide6 extra.

## Install from the repository root

```bash
python -m pip install -e ".[dev,desktop]"
```

For headless/core development only:

```bash
python -m pip install -e ".[dev]"
```

## Supported operator/developer doorway

```bash
alpha start
alpha demo
alpha status
alpha verify quick
alpha verify feature AE-RUN-003
alpha verify full
alpha qualify
alpha stop
```

Useful development options:

```bash
alpha start --headless --profile ./profiles/dev --port 8765
alpha demo --reset --seed-only --profile ./profiles/demo
alpha demo --headless --profile ./profiles/demo --port 8766
```

`alpha demo` is offline and deterministic. It uses the same composed Central Hub service authorities as normal runtime and never requires live provider credentials. `--reset` destroys only the explicitly selected demo profile and refuses to operate while a runtime discovery record is present.

## Runtime profiles

Default profile: `~/.alpha_engine/default` (or `ALPHA_PROFILE` when set).

Default demo profile: `~/.alpha_engine/demo`.

A profile contains its SQLite database, artifact store, cache, exports, backups, logs, and bounded runtime discovery files. The runtime lock/discovery files are removed on clean shutdown. A dead-process stale lock is reconciled on the next start and reported in status.

## Verification evidence

`alpha verify ...` writes a timestamped directory under `.alpha_verification_evidence/` at the repository root. Each run retains:

- `verification.json`;
- `VERIFICATION_REPORT.md`;
- per-check stdout/stderr under `raw/`.

Verification is non-fail-fast. Independent checks continue after failures. Missing prerequisites are reported as `BLOCKED`; zero-test collection and verifier exceptions are not green.

## Current known convergence boundaries

The root package now installs the central core plus the four standalone plugin distributions under `plugins/`. Historical root `src/` cylinder trees are deliberately **not** silently installed as production candidates because they contain unfrozen/duplicate integration shapes (including the duplicate Prediction Markets implementation). `alpha verify full` exposes those compatibility facts instead of choosing a winner implicitly.

Numbered core migrations, worker subprocess supervision, a frozen universal plugin PDK activation path, full original-purpose traceability, and opt-in live-provider qualification remain unfinished convergence work. Their absence must remain visible in qualification rather than being converted into false READY claims.
