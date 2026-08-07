from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class SecretRef:
    provider:str; key:str; purpose:str
class SecretResolver:
    def resolve(self,ref:SecretRef)->str: raise NotImplementedError('production adapter must resolve through OS protected secret store')
class ConfigurationService:
    def __init__(self,defaults:dict|None=None): self._values=dict(defaults or {}); self._history=[]
    def get(self,key,default=None): return self._values.get(key,default)
    def set(self,key,value,actor='user',reason='manual'):
        old=self._values.get(key); self._values[key]=value; self._history.append({'key':key,'old':old,'new':value,'actor':actor,'reason':reason}); return len(self._history)
    def history(self): return tuple(self._history)
