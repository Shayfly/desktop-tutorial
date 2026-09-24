from __future__ import annotations
from urllib.parse import urlparse

def parse_and_validate_origins(raw:str,*,production:bool)->list[str]:
    origins=[x.strip().rstrip('/') for x in raw.split(',') if x.strip()]
    if not origins: raise ValueError('at least one allowed origin is required')
    if '*' in origins: raise ValueError('wildcard CORS origin is forbidden')
    if len(origins)!=len(set(origins)): raise ValueError('duplicate CORS origin')
    for origin in origins:
        p=urlparse(origin)
        allowed=('https',) if production else ('http','https')
        if p.scheme not in allowed: raise ValueError(f'invalid origin scheme: {origin}')
        if not p.netloc or p.path not in ('','/') or p.query or p.fragment:
            raise ValueError(f'origin must contain only scheme + host + optional port: {origin}')
        if production and p.hostname in {'localhost','127.0.0.1','::1'}:
            raise ValueError('localhost CORS origin forbidden in production')
    return origins
