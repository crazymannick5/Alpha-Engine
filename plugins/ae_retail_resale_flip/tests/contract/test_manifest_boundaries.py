from pathlib import Path
from ae_retail_resale_flip.manifest import PLUGIN_ID, plugin_bundle

def test_manifest_identity_and_owned_capabilities():
    b=plugin_bundle()
    assert PLUGIN_ID=="ae.retail_resale_flip"
    assert b["default_enabled"] is False
    assert "retail.opportunity_detector" in b["capabilities"]

def test_no_private_core_imports():
    src=Path(__file__).parents[2]/"src"/"ae_retail_resale_flip"
    bad=[]
    for p in src.rglob("*.py"):
        text=p.read_text(encoding="utf-8")
        for token in ("alpha_engine.persistence", "alpha_engine.db", "alpha_engine.storage", "sqlalchemy", "smtplib", "requests.", "httpx."):
            if token in text: bad.append((str(p),token))
    assert bad==[]
