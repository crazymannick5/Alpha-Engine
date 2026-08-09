import unittest
from decimal import Decimal

from ae_prediction_markets.config.schema import DetectorConfig, PaperConfig, PredictionMarketsConfig, UniverseConfig
from ae_prediction_markets.persistence.memory import InMemoryProjectionStore


class ConfigPersistenceTests(unittest.TestCase):
    def test_universe_default_disabled(self):
        c=PredictionMarketsConfig(universes=(UniverseConfig("US","kalshi"),))
        self.assertFalse(c.validate_action_universe("US","kalshi"))

    def test_enabled_paper_universe(self):
        c=PredictionMarketsConfig(universes=(UniverseConfig("US","kalshi",enabled=True),))
        self.assertTrue(c.validate_action_universe("US","kalshi"))

    def test_bad_participation_rejected(self):
        with self.assertRaises(ValueError): PaperConfig(participation_fraction=Decimal("1.1"))

    def test_test_store_optimistic_version(self):
        s=InMemoryProjectionStore(); v=s.put("x","k",{"a":1},expected_version=0)
        self.assertEqual(v,1)
        with self.assertRaises(RuntimeError): s.put("x","k",{"a":2},expected_version=0)
