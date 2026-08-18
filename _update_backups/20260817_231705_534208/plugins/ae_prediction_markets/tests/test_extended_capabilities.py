import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ae_prediction_markets.contracts import ProviderQuery, ProviderResult
from ae_prediction_markets.detectors.opportunities import opportunities_from_signals
from ae_prediction_markets.detectors.signals import detect_fee_regime_change, detect_market_status_risk, detect_price_divergence, detect_rule_change
from ae_prediction_markets.domain.enums import MarketKind, MarketStatus, SettlementState
from ae_prediction_markets.domain.models import PMEvent, PMFeeSchedule, PMMarket, PMOutcome, PMOutcomeSet, PMRuleVersion
from ae_prediction_markets.normalization.kalshi import normalize_kalshi_markets, settlement_from_market
from ae_prediction_markets.fixtures.reference import fixture_now, kalshi_fixture_responses
from ae_prediction_markets.providers.fixture import FixtureProviderAdapter

NOW=fixture_now()

class ExtendedCapabilityTests(unittest.TestCase):
    def test_event_time_invariant(self):
        PMEvent('e','q',(),NOW,NOW+timedelta(hours=1),'en')
        with self.assertRaises(ValueError):
            PMEvent('e','q',(),NOW,NOW-timedelta(seconds=1),'en')

    def test_price_divergence_to_opportunity(self):
        signal=detect_price_divergence(subject_ref='m1',reference_probability=Decimal('0.70'),executable_probability=Decimal('0.55'),fee_cost=Decimal('0.01'),slippage=Decimal('0.01'),uncertainty_buffer=Decimal('0.02'),now=NOW,evidence_refs=('ev1',))
        self.assertIsNotNone(signal)
        opps=opportunities_from_signals((signal,),now=NOW)
        self.assertEqual(opps[0].family,'MODEL_VS_MARKET_DIVERGENCE')
        self.assertEqual(opps[0].actionability,'ACTIONABLE_FOR_PAPER_REVIEW')

    def test_small_divergence_suppressed(self):
        self.assertIsNone(detect_price_divergence(subject_ref='m',reference_probability=Decimal('0.51'),executable_probability=Decimal('0.50'),now=NOW))

    def test_status_risk(self):
        outcomes=PMOutcomeSet('o',(PMOutcome('YES','Yes',Decimal('1')),PMOutcome('NO','No',Decimal('1'))),True,True,'binary')
        m=PMMarket('m','v','e','t','q',None,MarketKind.BINARY_YES_NO,outcomes,'r',NOW,NOW+timedelta(hours=1),NOW+timedelta(hours=1),MarketStatus.HALTED)
        sig=detect_market_status_risk(m,now=NOW)
        self.assertEqual(sig.signal_type,'PM_MARKET_STATUS_RISK')
        self.assertTrue(sig.blockers)

    def test_fee_regime_change(self):
        old=PMFeeSchedule('f1','m',NOW,None,'flat',{'rate':Decimal('0.01')},'ev1')
        new=PMFeeSchedule('f2','m',NOW+timedelta(days=1),None,'flat',{'rate':Decimal('0.02')},'ev2')
        sig=detect_fee_regime_change(old,new,now=NOW+timedelta(days=1))
        self.assertEqual(sig.signal_type,'PM_FEE_REGIME_CHANGE')

    def test_rule_change(self):
        old=PMRuleVersion('m','a','old',NOW,NOW,'ev1')
        new=PMRuleVersion('m','b','new',NOW,NOW,'ev2',supersedes='a')
        self.assertEqual(detect_rule_change(old,new,now=NOW).signal_type,'PM_RULE_CHANGE')

    def test_settlement_normalization_final(self):
        provider=FixtureProviderAdapter(kalshi_fixture_responses(), observed_at=NOW)
        market=normalize_kalshi_markets(provider.execute(ProviderQuery('markets'), None)).markets[0]
        payload={'market':{'ticker':market.provider_market_ref,'status':'settled','settlement_value_dollars':'1.0000','settlement_ts':NOW.isoformat()}}
        result=ProviderResult('kalshi.fixture','1',ProviderQuery('market',provider_market_ref=market.provider_market_ref),payload,NOW)
        batch=settlement_from_market(result,market)
        self.assertEqual(batch.settlements[0].state,SettlementState.FINAL)
        self.assertEqual(batch.settlements[0].outcome_id,'YES')

if __name__ == '__main__': unittest.main()
