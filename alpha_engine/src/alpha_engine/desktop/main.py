from __future__ import annotations

import json
from typing import Any


def _record_counts(runtime: Any) -> dict[str, int]:
    if runtime is None:
        return {}
    from alpha_engine.storage.models import CoreRecord

    with runtime.sf() as session:
        rows = session.query(CoreRecord.record_type).all()
    counts: dict[str, int] = {}
    for (record_type,) in rows:
        counts[record_type] = counts.get(record_type, 0) + 1
    return counts


def run_desktop(runtime: Any | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget
    except ImportError as exc:
        raise SystemExit('Desktop extra not installed: pip install -e ".[desktop]"') from exc
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("Personal Alpha Engine")
    tabs = QTabWidget()
    counts = _record_counts(runtime)
    health = runtime.health.snapshot() if runtime is not None else {"status": "UNBOUND"}
    views = [
        ("Overview", f"Runtime: {health['status']}\nMode: {getattr(runtime, 'mode', 'standalone-shell')}"),
        ("Opportunity Radar", f"Radar entries: {counts.get('RADAR', 0)}\nOpportunities: {counts.get('OPPORTUNITY', 0)}"),
        ("Review Queue", f"Decisions: {counts.get('DECISION', 0)}"),
        ("Evidence & Data", f"Evidence: {counts.get('EVIDENCE', 0)}\nObservations: {counts.get('OBSERVATION', 0)}"),
        ("Paper Portfolio", f"Paper actions: {counts.get('PAPER_ACTION', 0)}"),
        ("Outcomes & Evaluation", f"Outcomes: {counts.get('OUTCOME', 0)}\nEvaluations: {counts.get('EVALUATION', 0)}\nLearning: {counts.get('LEARNING', 0)}"),
        ("Operations", "Use `alpha status` or the loopback API for current operation details."),
        ("Providers & Data Queries", "Provider routes are owned by the composed Central Hub registry."),
        ("Budgets", "Budget authority is active in the composed runtime."),
        ("Permissions", "Permission authority is active in the composed runtime."),
        ("Notifications", "Notification intents are local-first; email transport remains separately configured."),
        ("Registries", "Canonical registries are available through the Central Hub."),
        ("Health & Recovery", json.dumps(health, indent=2)),
        ("Settings", "Configuration remains local to the selected profile."),
    ]
    for name, text in views:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        tabs.addTab(page, name)
    win.setCentralWidget(tabs)
    win.resize(1200, 800)
    win.show()
    return int(app.exec())


def main() -> None:
    raise SystemExit(run_desktop())


if __name__ == "__main__":
    main()
