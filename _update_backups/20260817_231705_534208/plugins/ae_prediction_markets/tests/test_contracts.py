import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_prediction_markets.integration.central import register_with_central
from ae_prediction_markets.manifest import MANIFEST
from ae_prediction_markets.serialization import stable_hash


class FakeRegistry:
    def __init__(self):
        self.manifests=[]; self.providers=[]; self.dash=[]; self.cli=[]
    def register_manifest(self,x): self.manifests.append(x)
    def register_provider(self,x): self.providers.append(x)
    def register_dashboard(self,x): self.dash.append(x)
    def register_cli(self,x): self.cli.append(x)


class ContractTests(unittest.TestCase):
    def test_manifest_has_no_live_submit(self):
        self.assertIn("live_order_submit", MANIFEST.forbidden_capabilities)
        self.assertNotIn("live_order_submit", MANIFEST.capabilities)

    def test_registration_public_shape(self):
        r=FakeRegistry(); report=register_with_central(r)
        self.assertEqual(len(r.manifests),1)
        self.assertEqual(len(r.providers),1)
        self.assertGreater(len(r.dash),0)
        self.assertGreater(len(r.cli),0)
        self.assertFalse(report["deferred"])

    def test_hash_deterministic(self):
        self.assertEqual(stable_hash({"b":1,"a":Decimal("0.5")}), stable_hash({"a":Decimal("0.5"),"b":1}))
