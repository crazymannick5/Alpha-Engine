from decimal import Decimal
from alpha_engine.kernel.values import Money,Probability
from alpha_engine.kernel.serialization import canonical_hash

def test_money_and_probability():
    assert (Money(Decimal('1.10'),'USD')+Money(Decimal('2.20'),'USD')).amount==Decimal('3.30')
    assert Probability(Decimal('.5')).value==Decimal('.5')
def test_hash_stable(): assert canonical_hash({'b':2,'a':1})==canonical_hash({'a':1,'b':2})
