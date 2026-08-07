from alpha_engine.contracts.plugin import ProviderRequest,ProviderResult,ObservationCandidate,SignalCandidate,OpportunityCandidate
class FixtureProvider:
    descriptor={'provider_id':'reference.fixture','capabilities':['synthetic_resource_forecast']}
    def execute(self,request:ProviderRequest)->ProviderResult:
        return ProviderResult(provider_id='reference.fixture',status='OK',payload={'subject':'resource:A','capacity':'100','demand':'145','observed_at':'2026-01-01T12:00:00Z'},cost_amount='0')
class FixtureNormalizer:
    descriptor={'normalizer_id':'reference.normalizer','version':'1.0'}
    def normalize(self,result,evidence_refs):
        return [ObservationCandidate(subject=result.payload['subject'],kind='capacity_demand',value={'capacity':result.payload['capacity'],'demand':result.payload['demand']},observed_at=result.payload['observed_at'],evidence_refs=tuple(evidence_refs))]
class FixtureSignalDetector:
    descriptor={'detector_id':'reference.signal','version':'1.0'}
    def detect(self,observations):
        o=observations[0]; cap=float(o['value']['capacity']); dem=float(o['value']['demand'])
        if dem/cap < 1.20: return []
        return [SignalCandidate(kind='resource_pressure',subject=o['subject'],magnitude='0.90',confidence='0.95',evidence_refs=tuple(o['evidence_refs']))]
class FixtureOpportunityDetector:
    descriptor={'detector_id':'reference.opportunity','version':'1.0'}
    def detect(self,signals):
        if not signals:return []
        s=signals[0]; return [OpportunityCandidate(kind='resource_allocation',title='Synthetic capacity reallocation',thesis='Synthetic demand materially exceeds synthetic capacity.',subject=s['subject'],horizon='P1D',signal_refs=(s['id'],))]
