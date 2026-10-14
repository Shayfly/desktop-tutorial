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


# Infisical implementation of the existing generated-app SecretWriter contract.
# vault: remains a logical binding reference for schema compatibility; the
# explicitly selected provider determines its backing store. No migration of
# existing Vault values is performed when changing provider.
from hashlib import sha256
import re
import threading
import time
from urllib import error, parse


class _InfisicalHttpError(SecretResolutionError):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f'Infisical request failed (HTTP {status})')


class _NoInfisicalRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Universal Auth credentials and bearer tokens must never follow redirects.
        return None


class InfisicalHttpSecretWriter(SecretWriter):
    """Universal Auth + v4 secrets, with logical KV references mapped to stable names.

    All references include the mount, project and generated-app environment in
    their digest. Values are stored in a dedicated Infisical project/environment,
    at the root, under GA_<sha256(reference)> names. Provider selection is opt-in.
    """

    def __init__(self, *, base_url: str, project_id: str, environment: str,
                 client_id: str, client_secret: str, timeout_seconds: float = 5,
                 urlopen=None, clock=None):
        url = parse.urlsplit(base_url)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.path not in ('', '/')):
            raise SecretResolutionError('Infisical base URL must be an HTTPS origin')
        if not all(isinstance(v, str) and v.strip()
                   for v in (project_id, environment, client_id, client_secret)):
            raise SecretResolutionError('Infisical project, environment and credentials are required')
        self.base_url = base_url.rstrip('/')
        self.project_id = project_id
        self.environment = environment
        self._client_id = client_id
        self._client_secret = client_secret
        self.timeout_seconds = timeout_seconds
        self.urlopen = urlopen or request.build_opener(_NoInfisicalRedirect()).open
        self.clock = clock or time.monotonic
        self._access_token = ''
        self._expires_at = 0.0
        self._token_lock = threading.Lock()

    def _name(self, reference: str) -> str:
        if not isinstance(reference, str) or not reference.startswith('vault:'):
            raise SecretResolutionError('generated-app secrets must use logical vault: references')
        path = reference[6:]
        parts = path.split('/')
        if (not re.fullmatch(r'[A-Za-z0-9_./-]{1,512}', path) or len(parts) < 3
                or parts[1] != 'data' or any(p in ('', '.', '..') for p in parts)):
            raise SecretResolutionError('invalid generated-app secret reference')
        return 'GA_' + sha256(reference.encode('utf-8')).hexdigest()

    def _send(self, method: str, path: str, *, body=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = request.Request(self.base_url + path, method=method, headers=headers,
                              data=None if body is None else json.dumps(body).encode())
        try:
            with self.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read()
            payload = json.loads(raw.decode()) if raw else {}
            if not isinstance(payload, dict):
                raise ValueError('unexpected response shape')
            return payload
        except error.HTTPError as exc:
            # Drop the provider body, URL, headers and exception chain.
            raise _InfisicalHttpError(exc.code) from None
        except Exception:
            raise SecretResolutionError('Infisical request or response failed') from None

    def _token(self) -> str:
        with self._token_lock:
            if self._access_token and self.clock() < self._expires_at:
                return self._access_token
            payload = self._send('POST', '/api/v1/auth/universal-auth/login',
                                 body={'clientId': self._client_id,
                                       'clientSecret': self._client_secret})
            token = payload.get('accessToken')
            ttl = payload.get('expiresIn')
            if (not isinstance(token, str) or not token or '\n' in token or '\r' in token
                    or not isinstance(ttl, (float, int)) or isinstance(ttl, bool)
                    or ttl <= 0):
                raise SecretResolutionError('Infisical authentication response invalid')
            self._access_token = token
            self._expires_at = self.clock() + ttl - min(10, ttl / 10)
            return token

    def _call(self, method: str, name: str, *, value=None):
        scope = {'projectId': self.project_id, 'environment': self.environment,
                 'secretPath': '/', 'type': 'shared'}
        path = '/api/v4/secrets/' + name
        if method == 'GET':
            path += '?' + parse.urlencode(scope)
            body = None
        else:
            body = scope
            if value is not None:
                body = {**scope, 'secretValue': value, 'skipMultilineEncoding': True}
        try:
            return self._send(method, path, body=body, token=self._token())
        except _InfisicalHttpError as exc:
            if exc.status == 401:
                with self._token_lock:
                    self._access_token = ''
                    self._expires_at = 0.0
            raise

    def write(self, reference: str, value: str) -> None:
        name = self._name(reference)
        if not isinstance(value, str) or not value:
            raise SecretResolutionError('refusing to write an empty secret')
        try:
            self._call('GET', name)
        except _InfisicalHttpError as exc:
            if exc.status != 404:
                raise
            self._call('POST', name, value=value)
        else:
            self._call('PATCH', name, value=value)

    def resolve(self, reference: str) -> str:
        payload = self._call('GET', self._name(reference))
        try:
            value = payload['secret']['secretValue']
        except (KeyError, TypeError):
            raise SecretResolutionError('Infisical secret missing') from None
        if not isinstance(value, str) or not value:
            raise SecretResolutionError('empty secret')
        return value

    def delete(self, reference: str) -> None:
        try:
            self._call('DELETE', self._name(reference))
        except _InfisicalHttpError as exc:
            if exc.status != 404:
                raise
