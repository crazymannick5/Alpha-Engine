# ADR-0001: Central Hub Implementation Freeze Choices
Status: DRAFT-FROZEN-FOR-IMPLEMENTATION-CANDIDATE

1. Python 3.12 is the governing language.
2. SQLAlchemy 2 synchronous sessions + SQLite WAL are the first persistence implementation.
3. FastAPI/Uvicorn provide the loopback internal API adapter; application services remain transport-independent.
4. PySide6 is the native desktop technology and an optional install extra so headless/core qualification does not require Qt.
5. The OS credential manager is the target for production secrets; secret values are never persisted in SQLite.
6. Plugin compatibility contract starts at 1.0 and uses explicit manifests plus candidate-return interfaces.
7. Production cylinder code is excluded from the hub.
