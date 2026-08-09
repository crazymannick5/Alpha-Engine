from ae_retail_resale_flip.contracts import EvidenceRef, OperationContext, QueryIntent, RetailQuery
from ae_retail_resale_flip.operations.handlers import acquire_and_normalize
from ae_retail_resale_flip.providers.fixture import FixtureAdapter

class FakeRepo:
    def __init__(self): self.checkpoint=None
    def get_checkpoint(self,*a): return self.checkpoint
    def save_checkpoint(self,c): self.checkpoint=c
    def save_plugin_record(self,*a): raise AssertionError("not used")
    def get_plugin_record(self,*a): return None

def test_checkpoint_written_only_through_injected_repo():
    repo=FakeRepo()
    a=FixtureAdapter([{"record_type":"offer","manufacturer":"A","brand":"B","model":"C","price":"10","currency":"USD","availability":"IN_STOCK"}])
    q=RetailQuery("q",QueryIntent.OFFER_SEARCH,"u","US")
    r=acquire_and_normalize(a,q,OperationContext("op","corr",True,policy_version="p1"),evidence_refs=(EvidenceRef("ev"),),repository=repo)
    assert r.normalized_count==1
    assert repo.checkpoint is not None and repo.checkpoint.operation_id=="op"
