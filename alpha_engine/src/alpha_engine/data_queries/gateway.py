from decimal import Decimal
from alpha_engine.contracts.plugin import ProviderRequest, ProviderResult
from alpha_engine.providers.registry import ProviderRegistry
class DataQueryGateway:
    def __init__(self,registry:ProviderRegistry): self.registry=registry
    def execute(self,request:ProviderRequest)->ProviderResult:
        failures=[]
        for route in self.registry.eligible():
            try:
                result=route.adapter.execute(request)
                if result.status=='OK': return result
                failures.append(f'{route.provider_id}:{result.status}')
            except Exception as exc: failures.append(f'{route.provider_id}:{type(exc).__name__}')
        raise RuntimeError('No qualified provider succeeded: '+','.join(failures))
