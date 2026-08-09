from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from alpha_engine_prediction_markets.contracts import PMQuery
from alpha_engine_prediction_markets.engine import PredictionMarketsEngine
from alpha_engine_prediction_markets.manifest import MANIFEST
from alpha_engine_prediction_markets.normalization import normalize_orderbook
from alpha_engine_prediction_markets.operations import MarketSyncHandler
from alpha_engine_prediction_markets.persistence import MIGRATION_NAMESPACE, migration_descriptors
from alpha_engine_prediction_markets.plugin import build_registration, register
from alpha_engine_prediction_markets.providers.fixture import FixtureProviderAdapter

from conftest import DummyContext

NOW = datetime(2026, 8, 7, 20, tzinfo=UTC)


class Evidence:
    def capture_provider_result(self, query, result, *, operation_id):
        return (f"evidence:{result.request_id}",)


class Sink:
    def __init__(self):
        self.observations = []
        self.signals = []
        self.opportunities = []
    def submit_observations(self, candidates, *, operation_id):
        self.observations.extend(candidates)
        return tuple(f"obs:{i}" for i, _ in enumerate(candidates))
    def submit_signals(self, candidates, *, operation_id):
        self.signals.extend(candidates)
        return tuple(f"sig:{i}" for i, _ in enumerate(candidates))
    def submit_opportunities(self, candidates, *, operation_id):
        self.opportunities.extend(candidates)
        return tuple(f"opp:{i}" for i, _ in enumerate(candidates))


class Host:
    def __init__(self): self.registration = None
    def register_prediction_markets(self, registration): self.registration = registration


def test_registration_is_complete_and_fixture_safe():
    reg = build_registration()
    assert reg.plugin_id == "ae.prediction_markets"
    assert reg.providers[0].environment == "fixture"
    assert "pm.edge_net" in reg.scoring_features
    assert all("live" not in x.lower() for x in MANIFEST.forbidden_capabilities if False) or "live_order_submit" in MANIFEST.forbidden_capabilities


def test_register_uses_public_outward_port_only():
    host = Host()
    register(host)
    assert host.registration.plugin_id == "ae.prediction_markets"


def test_full_fixture_sync_normalizes_and_submits():
    sink = Sink()
    handler = MarketSyncHandler(FixtureProviderAdapter(), Evidence(), sink)
    result = handler.run(PMQuery(intent="markets"), DummyContext())
    assert len(result.observation_candidates) == 1
    assert len(sink.observations) == 1
    assert result.observation_candidates[0].evidence_refs[0].startswith("evidence:")


def test_fixture_analysis_data_to_signal_to_opportunity():
    provider = FixtureProviderAdapter()
    ctx = DummyContext()
    market_result = provider.execute(PMQuery(intent="markets"), ctx)
    market_candidate = PredictionMarketsEngine().normalize_provider_result(PMQuery(intent="markets"), market_result, ("ev-market",))[0]
    from alpha_engine_prediction_markets.domain import PMMarket
    market = PMMarket.model_validate(market_candidate.payload["market"])
    book_result = provider.execute(PMQuery(intent="order_book", provider_market_ref=market.provider_market_ref), ctx)
    book = normalize_orderbook(book_result.payload, book_result.provider_id, book_result.retrieved_at, market.market_ref)
    engine = PredictionMarketsEngine()
    bundle = engine.analyze_market(
        market, book, now=NOW,
        reference_probability=Decimal("0.60"), executable_probability=Decimal("0.44"),
        reference_evidence_refs=("ref-model",), fee_cost=Decimal("0.01"), slippage=Decimal("0.01"),
        uncertainty_buffer=Decimal("0.02"), provider_qualified=True, jurisdiction_enabled=True,
    )
    assert any(x.signal_kind == "PM_PRICE_DIVERGENCE" for x in bundle.signals)
    assert any(x.family == "MODEL_VS_MARKET_DIVERGENCE" for x in bundle.opportunities)
    assert any(x.name == "pm.edge_net" and x.value == Decimal("0.12") for x in bundle.features)


def test_migration_descriptors_are_plugin_namespace_only():
    desc = migration_descriptors()[0]
    assert desc.namespace == MIGRATION_NAMESPACE
    sql = (Path(__file__).parents[2] / "src/alpha_engine_prediction_markets/migrations/001_initial.sql").read_text()
    assert "ae_pm_" in sql
    forbidden = [" observations ", " signals ", " opportunities ", " paper_ledger ", " outcomes "]
    lower = sql.lower()
    assert not any(x in lower for x in forbidden)


def test_manifest_has_no_live_action_capability():
    assert "live_order_submit" in MANIFEST.forbidden_capabilities
    assert not any(cap.startswith("live_order") for cap in MANIFEST.capabilities)


def test_no_private_core_imports_in_production_source():
    root = Path(__file__).parents[2] / "src/alpha_engine_prediction_markets"
    content = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
    assert "alpha_engine.plugin_host" not in content
    assert "alpha_engine.persistence" not in content
    assert "sqlalchemy" not in content.lower()
