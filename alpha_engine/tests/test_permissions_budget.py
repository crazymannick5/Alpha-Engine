from decimal import Decimal
import pytest
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.permissions.service import PermissionService
from alpha_engine.budgets.service import BudgetService
from alpha_engine.kernel.errors import PermissionDenied,BudgetDenied

def test_permission_and_budget(tmp_path):
    _,sf=initialize(tmp_path/'a.db'); p=PermissionService(sf); b=BudgetService(sf)
    with pytest.raises(PermissionDenied): p.require_and_use('PAPER_ACTION','x')
    p.grant('PAPER_ACTION','x',max_uses=1); p.require_and_use('PAPER_ACTION','x')
    with pytest.raises(PermissionDenied): p.require_and_use('PAPER_ACTION','x')
    b.define('p',Decimal('1')); r=b.reserve('p',Decimal('.4')); b.commit(r,Decimal('.3'))
    with pytest.raises(BudgetDenied): b.reserve('p',Decimal('.8'))
