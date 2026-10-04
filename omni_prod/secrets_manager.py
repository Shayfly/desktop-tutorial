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


# --------------------------------------------------------------------------
# M5 Task 7: generated-app secret store (write side).
#
# Generated apps get their own credentials (database role password, session
# signing key, webhook signing key). Those values are written here and only
# the vault: reference is stored anywhere else. The control-plane resolvers
# above are read-only and are never reused to mint generated-app secrets.
# --------------------------------------------------------------------------

class SecretWriter:
    """Write/read/delete secrets addressed by vault: references."""

    def write(self, reference: str, value: str) -> None: raise NotImplementedError
    def resolve(self, reference: str) -> str: raise NotImplementedError
    def delete(self, reference: str) -> None: raise NotImplementedError


class VaultHttpSecretWriter(SecretWriter):
    """HashiCorp Vault KV v2 writer.

    A reference ``vault:secret/data/148ai/...`` maps to ``{base}/v1/secret/data/148ai/...``
    -- the same path VaultHttpSecretResolver reads -- with body {"data": {"value": ...}}.
    The secret value travels only in the request body, never in a URL, header or error.
    """

    def __init__(self, *, base_url: str, token_env: str = 'OMNI_GENAPP_VAULT_TOKEN',
                 timeout_seconds: float = 5, urlopen=None):
        if not base_url or not base_url.startswith(('https://', 'http://')):
            raise SecretResolutionError('vault base url must be http(s)')
        self.base_url = base_url.rstrip('/')
        self.token_env = token_env
        self.timeout_seconds = timeout_seconds
        self.urlopen = urlopen or request.urlopen

    def _path(self, reference: str) -> str:
        if not reference.startswith('vault:'):
            raise SecretResolutionError('generated-app secrets must use vault: references')
        path = reference[6:].strip('/')
        parts = path.split('/')
        if not path or '..' in parts or len(parts) < 3 or parts[1] != 'data':
            raise SecretResolutionError('vault reference must be a KV v2 <mount>/data/<path> reference')
        return path

    def _token(self) -> str:
        token = os.getenv(self.token_env, '')
        if not token:
            raise SecretResolutionError('vault token unavailable')
        return token

    def _call(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        req = request.Request(self.base_url + '/v1/' + path, data=data, method=method,
                              headers={'X-Vault-Token': self._token(), 'Content-Type': 'application/json'})
        try:
            with self.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read()
        except Exception as exc:
            # never echo the request body (it carries the secret)
            raise SecretResolutionError(f'vault {method} failed: {type(exc).__name__}') from None
        return json.loads(raw.decode() or '{}') if raw else {}

    def write(self, reference: str, value: str) -> None:
        if not isinstance(value, str) or not value:
            raise SecretResolutionError('refusing to write an empty secret')
        self._call('POST', self._path(reference), {'data': {'value': value}})

    def resolve(self, reference: str) -> str:
        payload = self._call('GET', self._path(reference))
        try:
            value = payload['data']['data']['value']
        except (KeyError, TypeError):
            raise SecretResolutionError('vault secret missing') from None
        if not isinstance(value, str) or not value:
            raise SecretResolutionError('empty secret')
        return value

    def delete(self, reference: str) -> None:
        # KV v2: DELETE on .../metadata/<path> removes all versions permanently.
        path = self._path(reference)
        mount, _, rest = path.partition('/data/')
        self._call('DELETE', f'{mount}/metadata/{rest}')
