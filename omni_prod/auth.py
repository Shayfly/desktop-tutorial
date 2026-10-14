from __future__ import annotations
from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
import time

def _b64(data: bytes)->str: return base64.urlsafe_b64encode(data).decode().rstrip('=')
def _unb64(text:str)->bytes: return base64.urlsafe_b64decode(text + '='*((4-len(text)%4)%4))

@dataclass(frozen=True)
class AuthClaims:
    user_id: str
    org_id: str
    role: str
    exp: int
    session_id: str | None = None

class AuthError(RuntimeError): pass

def issue_token(*, secret:str,user_id:str,org_id:str,role:str,ttl_seconds:int=3600,now:int|None=None,session_id:str|None=None)->str:
    if len(secret)<32: raise ValueError('auth secret must be at least 32 chars')
    if ttl_seconds<1: raise ValueError('ttl_seconds must be positive')
    if not all(x.strip() for x in (user_id,org_id,role)): raise ValueError('claims required')
    ts=int(time.time() if now is None else now)
    header=_b64(json.dumps({'alg':'HS256','typ':'OMNI'},separators=(',',':')).encode())
    claims={'sub':user_id,'org':org_id,'role':role,'exp':ts+ttl_seconds}
    if session_id is not None:
        if not session_id.strip(): raise ValueError('session_id must not be blank')
        claims['sid']=session_id
    payload=_b64(json.dumps(claims,separators=(',',':')).encode())
    msg=f'{header}.{payload}'.encode(); sig=_b64(hmac.new(secret.encode(),msg,hashlib.sha256).digest())
    return f'{header}.{payload}.{sig}'

def verify_token(token:str,*,secret:str,now:int|None=None)->AuthClaims:
    if len(secret)<32: raise AuthError('auth secret unavailable')
    try:
        header,payload,sig=token.split('.')
        msg=f'{header}.{payload}'.encode(); expected=_b64(hmac.new(secret.encode(),msg,hashlib.sha256).digest())
        if not hmac.compare_digest(sig,expected): raise AuthError('invalid signature')
        h=json.loads(_unb64(header)); data=json.loads(_unb64(payload))
        if h.get('alg')!='HS256' or h.get('typ')!='OMNI': raise AuthError('invalid token header')
        exp=int(data['exp']); ts=int(time.time() if now is None else now)
        if exp<=ts: raise AuthError('token expired')
        return AuthClaims(str(data['sub']),str(data['org']),str(data['role']),exp,str(data['sid']) if data.get('sid') else None)
    except AuthError: raise
    except Exception as exc: raise AuthError('invalid token') from exc
