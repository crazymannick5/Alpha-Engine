import pytest
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.operations.service import OperationService
from alpha_engine.kernel.errors import IdempotencyConflict

def test_idempotency(tmp_path):
    _,sf=initialize(tmp_path/'a.db'); o=OperationService(sf); a=o.admit('u','X','k',{'x':1}); b=o.admit('u','X','k',{'x':1}); assert a[0]==b[0] and b[1] is False
    with pytest.raises(IdempotencyConflict): o.admit('u','X','k',{'x':2})
