from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class AlphaError(Exception):
    code: str
    message: str
    retryable: bool=False
    def __str__(self): return f"{self.code}: {self.message}"
class PermissionDenied(AlphaError):
    def __init__(self,msg='No active grant matches the action'): super().__init__('PERMISSION_DENIED',msg,False)
class BudgetDenied(AlphaError):
    def __init__(self,msg='Budget hard limit exceeded'): super().__init__('BUDGET_HARD_LIMIT_EXCEEDED',msg,False)
class IdempotencyConflict(AlphaError):
    def __init__(self): super().__init__('IDEMPOTENCY_CONFLICT','Key reused with different payload',False)
