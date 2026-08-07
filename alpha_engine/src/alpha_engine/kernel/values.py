from dataclasses import dataclass
from decimal import Decimal
@dataclass(frozen=True,slots=True)
class Money:
    amount: Decimal
    currency: str
    def __post_init__(self):
        if not self.currency or self.currency != self.currency.upper(): raise ValueError("currency must be uppercase")
    def __add__(self, other:"Money")->"Money":
        if self.currency != other.currency: raise ValueError("currency mismatch")
        return Money(self.amount+other.amount,self.currency)
@dataclass(frozen=True,slots=True)
class Probability:
    value: Decimal
    def __post_init__(self):
        if self.value<0 or self.value>1: raise ValueError("probability outside [0,1]")
