import unittest

from ae_prediction_markets.contracts import AdmittedOperationContext, ProviderQuery
from ae_prediction_markets.errors import ProviderAuthFailed, ProviderNetworkDenied
from ae_prediction_markets.providers.kalshi import KalshiEnvironment, KalshiReadOnlyAdapter


class ProviderSecurityTests(unittest.TestCase):
    def test_network_requires_admission(self):
        a = KalshiReadOnlyAdapter()
        with self.assertRaises(ProviderNetworkDenied):
            a.execute(ProviderQuery("markets"), AdmittedOperationContext("o","c",network_allowed=False,provider_id=a.provider_id))

    def test_orderbook_requires_host_signer(self):
        a = KalshiReadOnlyAdapter()
        with self.assertRaises(ProviderAuthFailed):
            a.execute(ProviderQuery("order_book",provider_market_ref="ABC"), AdmittedOperationContext("o","c",network_allowed=True,provider_id=a.provider_id))

    def test_base_url_allowlist(self):
        with self.assertRaises(ValueError):
            KalshiEnvironment(base_url="http://127.0.0.1:8000")

    def test_path_traversal_ticker_rejected_before_network(self):
        a = KalshiReadOnlyAdapter(auth_headers=lambda m,p:{})
        with self.assertRaises(ValueError):
            a.execute(ProviderQuery("order_book",provider_market_ref="../secret"), AdmittedOperationContext("o","c",network_allowed=True,provider_id=a.provider_id))
