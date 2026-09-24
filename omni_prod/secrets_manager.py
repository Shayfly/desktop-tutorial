from __future__ import annotations
from dataclasses import dataclass
import os
from urllib import request
import json

class SecretResolutionError(RuntimeError): pass

class SecretResolver:
    def resolve(self, reference:str)->str: raise NotImplementedError

class EnvSecretResolver(SecretResolver):
    def __init__(self, *, production:bool=False): self.production=production
    def resolve(self,reference:str)->str:
        if not reference.startswith('env:'): raise SecretResolutionError('unsupported reference')
        name=reference[4:]
        if not name or any(x not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for x in name): raise SecretResolutionError('invalid env reference')
        value=os.getenv(name,'')
        if not value: raise SecretResolutionError('secret not configured')
        return value

@dataclass(frozen=True)
class VaultHttpConfig:
    base_url:str
    token_env:str='OMNI_VAULT_TOKEN'
    timeout_seconds:float=5

class VaultHttpSecretResolver(SecretResolver):
    def __init__(self,config:VaultHttpConfig,*,urlopen=None): self.config=config; self.urlopen=urlopen or request.urlopen
    def resolve(self,reference:str)->str:
        if not reference.startswith('vault:'): raise SecretResolutionError('unsupported reference')
        path=reference[6:].strip('/')
        if not path or '..' in path.split('/'): raise SecretResolutionError('invalid vault path')
        token=os.getenv(self.config.token_env,'')
        if not token: raise SecretResolutionError('vault token unavailable')
        req=request.Request(self.config.base_url.rstrip('/')+'/v1/'+path,headers={'X-Vault-Token':token})
        try:
            with self.urlopen(req,timeout=self.config.timeout_seconds) as r: payload=json.loads(r.read().decode())
            value=payload['data']['data']['value']
        except Exception as exc: raise SecretResolutionError('vault resolution failed') from exc
        if not isinstance(value,str) or not value: raise SecretResolutionError('empty secret')
        return value
