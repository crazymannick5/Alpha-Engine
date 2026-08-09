from __future__ import annotations

CLI_DESCRIPTORS = (
    {"path": "retail status", "mutating": False},
    {"path": "retail providers list", "mutating": False},
    {"path": "retail providers qualify", "mutating": True, "operation": "retail.qualify_provider"},
    {"path": "retail product resolve", "mutating": False},
    {"path": "retail offer refresh", "mutating": True, "operation": "retail.refresh_offer"},
    {"path": "retail scan", "mutating": True, "operation": "retail.scan_universe"},
    {"path": "retail revalue", "mutating": True, "operation": "retail.revalue_product"},
    {"path": "retail import", "mutating": True, "operation": "retail.import_manual"},
    {"path": "retail fixtures", "mutating": False},
    {"path": "retail diagnostics", "mutating": False},
    {"path": "retail export", "mutating": False, "policy_check_required": True},
    {"path": "retail policy explain", "mutating": False},
)
