from __future__ import annotations
import argparse, json
from pathlib import Path
from decimal import Decimal
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.artifacts.store import ArtifactStore
from alpha_engine.evidence.service import EvidenceService
from alpha_engine.providers.registry import ProviderRegistry
from alpha_engine.data_queries.gateway import DataQueryGateway
from alpha_engine.contracts.plugin import ProviderRequest
from alpha_engine.observations.service import ObservationService
from alpha_engine.signals.service import SignalService
from alpha_engine.opportunities.service import OpportunityService
from alpha_engine.ranking.service import RankingService
from alpha_engine.radar.service import RadarService
from alpha_engine.reviews.service import DecisionService
from alpha_engine.permissions.service import PermissionService
from alpha_engine.budgets.service import BudgetService
from alpha_engine.operations.service import OperationService
from alpha_engine.simulation.service import SimulationService
from alpha_engine.outcomes.service import OutcomeService
from alpha_engine.evaluation.service import EvaluationService
from alpha_engine.learning.service import LearningService
from .fixture import FixtureProvider,FixtureNormalizer,FixtureSignalDetector,FixtureOpportunityDetector

def run(db,artifacts):
    _,sf=initialize(db); store=ArtifactStore(artifacts,sf); evidence=EvidenceService(sf); provider=FixtureProvider(); registry=ProviderRegistry(); registry.register('reference.fixture',provider,priority=1); gateway=DataQueryGateway(registry); ops=OperationService(sf); budgets=BudgetService(sf); perms=PermissionService(sf)
    budget_id=budgets.define('reference.fixture',Decimal('5.00')); perm_id=perms.grant('PAPER_ACTION','resource:A',max_uses=10)
    op_id,_=ops.admit('reference-script','REFERENCE_LOOP','reference-loop-v1',{'subject':'resource:A'}); ops.transition(op_id,'RUNNING')
    result=gateway.execute(ProviderRequest(query_type='synthetic_resource_forecast',payload={'subject':'resource:A'})); raw=json.dumps(result.payload,sort_keys=True).encode(); artifact_id=store.adopt_bytes(raw,'application/json'); evidence_id=evidence.register('resource:A',artifact_id,metadata={'provider':'reference.fixture'})
    normalizer=FixtureNormalizer(); oc=normalizer.normalize(result,[evidence_id])[0]; obs_id=ObservationService(sf).persist_candidate(oc)
    signal_candidates=FixtureSignalDetector().detect([{'id':obs_id,'subject':oc.subject,'value':oc.value,'evidence_refs':oc.evidence_refs}]); sc=signal_candidates[0]; sig_id=SignalService(sf).persist_candidate(sc)
    oppc=FixtureOpportunityDetector().detect([{'id':sig_id,'subject':sc.subject}])[0]; opp_id=OpportunityService(sf).persist_candidate(oppc,[evidence_id])
    score_id,total=RankingService(sf).score(opp_id,{'magnitude':'0.90','confidence':'0.95','freshness':'1.00'}); radar_id=RadarService(sf).evaluate(opp_id,score_id,total); decision_id=DecisionService(sf).record(opp_id,'APPROVE_PAPER_ACTION','Deterministic reference approval')
    perms.require_and_use('PAPER_ACTION','resource:A'); reservation=budgets.reserve('reference.fixture',Decimal('0.10')); action_id=SimulationService(sf).paper_action(opp_id,decision_id,Decimal('10'),Decimal('1'),Decimal('10')); budgets.commit(reservation,Decimal('0.05'))
    outcome_art=store.adopt_bytes(b'{"realized":"0.80"}','application/json'); out_evi=evidence.register(opp_id,outcome_art); outcome_id=OutcomeService(sf).finalize(action_id,{'realized':'0.80'},[out_evi]); eval_id=EvaluationService(sf).evaluate(opp_id,outcome_id,total,Decimal('0.80')); learning_id=LearningService(sf).recommend(eval_id,'ranking.reference.confidence_weight','0.35','0.34'); ops.transition(op_id,'SUCCEEDED',{'learning_id':learning_id})
    manifest={'operation_id':op_id,'budget_id':budget_id,'permission_id':perm_id,'artifact_id':artifact_id,'evidence_id':evidence_id,'observation_id':obs_id,'signal_id':sig_id,'opportunity_id':opp_id,'score_id':score_id,'score_total':str(total),'radar_id':radar_id,'decision_id':decision_id,'paper_action_id':action_id,'outcome_id':outcome_id,'evaluation_id':eval_id,'learning_recommendation_id':learning_id,'artifact_integrity':store.verify(artifact_id),'learning_auto_applied':False}
    return manifest

def main():
    p=argparse.ArgumentParser(); p.add_argument('--db',default='alpha-reference.sqlite3'); p.add_argument('--artifacts',default='alpha-reference-artifacts'); args=p.parse_args(); print(json.dumps(run(args.db,args.artifacts),indent=2))
if __name__=='__main__': main()
