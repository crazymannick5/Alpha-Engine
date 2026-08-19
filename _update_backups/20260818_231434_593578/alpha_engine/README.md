# Personal Alpha Engine — Central Hub Draft

This repository is a substantial CORE-only implementation candidate derived from the accepted architecture draft. It deliberately contains no production cylinder. The deterministic reference loop proves acquisition/fixture -> normalization -> evidence -> signal -> opportunity -> ranking -> radar/review -> decision -> paper action -> outcome -> evaluation -> learning recommendation.

## Frozen implementation choices in this draft
- Python 3.12.
- Local-first modular monolith.
- SQLAlchemy 2.x synchronous ORM/unit-of-work with SQLite WAL initially.
- FastAPI + Uvicorn loopback internal API adapter.
- PySide6 native desktop adapter as an optional install extra; core and CLI run without Qt.
- Alembic migration line reserved; schema bootstrap is deterministic in this draft and must be converted to numbered migrations before first release.
- OS keyring is the production secret-store target; this draft never persists secret values and ships only a SecretRef protocol.
- Plugins are in-process Python packages only after manifest/contract compatibility validation; production isolation may later move selected plugin work into subprocesses without changing public contracts.

## Quick proof
```bash
python -m alpha_engine.reference_loop.runner --db ./alpha_demo.sqlite3 --artifacts ./artifacts
pytest
```

The reference loop is synthetic and is not investment, market, political, or commercial advice.
