from dataclasses import dataclass
from typing import Any
from alpha_engine.contracts.plugin import ProviderAdapter
@dataclass
class ProviderRegistration:
    provider_id:str; adapter:ProviderAdapter; qualified:bool=True; enabled:bool=True; priority:int=100
class ProviderRegistry:
    def __init__(self): self._items:dict[str,ProviderRegistration]={}
    def register(self,provider_id:str,adapter:ProviderAdapter,**kw): self._items[provider_id]=ProviderRegistration(provider_id,adapter,**kw)
    def eligible(self): return sorted((x for x in self._items.values() if x.qualified and x.enabled),key=lambda x:x.priority)
