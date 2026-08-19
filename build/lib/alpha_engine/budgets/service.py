from decimal import Decimal
from alpha_engine.kernel.ids import BudgetId, BudgetReservationId
from alpha_engine.kernel.errors import BudgetDenied
from alpha_engine.storage.models import BudgetRow, ReservationRow
class BudgetService:
    def __init__(self,sf): self.sf=sf
    def define(self,scope:str,hard_limit:Decimal,currency='USD')->str:
        bid=str(BudgetId.new())
        with self.sf() as s: s.add(BudgetRow(id=bid,scope=scope,currency=currency,hard_limit=str(hard_limit),committed='0',reserved='0')); s.commit()
        return bid
    def reserve(self,scope:str,amount:Decimal,currency='USD')->str|None:
        if amount==0: return None
        with self.sf() as s:
            budgets=s.query(BudgetRow).filter(BudgetRow.scope.in_([scope,'*']),BudgetRow.currency==currency).all()
            if not budgets: raise BudgetDenied('No applicable monetary budget')
            for b in budgets:
                if Decimal(b.committed)+Decimal(b.reserved)+amount>Decimal(b.hard_limit): raise BudgetDenied()
            b=sorted(budgets,key=lambda x:x.scope=='*')[0]; rid=str(BudgetReservationId.new()); b.reserved=str(Decimal(b.reserved)+amount); s.add(ReservationRow(id=rid,budget_id=b.id,amount=str(amount),status='RESERVED')); s.commit(); return rid
    def commit(self,reservation_id:str|None,actual:Decimal|None=None):
        if not reservation_id: return
        with self.sf() as s:
            r=s.get(ReservationRow,reservation_id); b=s.get(BudgetRow,r.budget_id); amt=Decimal(r.amount); actual=amt if actual is None else actual; b.reserved=str(Decimal(b.reserved)-amt); b.committed=str(Decimal(b.committed)+actual); r.status='COMMITTED'; s.commit()
