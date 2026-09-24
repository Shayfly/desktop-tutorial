from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac, sha256
import base64, hmac, re, secrets, threading
from .auth import issue_token, verify_token, AuthError

_EMAIL_RE=re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def _hash_password(password:str,salt:bytes)->str:
    return base64.urlsafe_b64encode(pbkdf2_hmac('sha256',password.encode(),salt,250_000)).decode()

@dataclass(frozen=True)
class Account:
    id:str
    email:str
    password_hash:str
    salt_b64:str
    created_at:str

@dataclass(frozen=True)
class ProjectRecord:
    id:str
    owner_id:str
    title:str
    created_at:str
    updated_at:str

class AccountService:
    """Thread-safe account + project ownership service for the V26 control plane.

    The in-memory implementation is deterministic/reviewer-friendly. Production
    wiring must persist the same contract in PostgreSQL; no cross-user lookup is
    permitted without explicit organization membership in a future extension.
    """
    def __init__(self,*,token_secret:str):
        if len(token_secret)<32: raise ValueError('token_secret must be at least 32 chars')
        self._secret=token_secret
        self._accounts:dict[str,Account]={}
        self._email_to_id:dict[str,str]={}
        self._projects:dict[str,ProjectRecord]={}
        self._lock=threading.RLock()

    def register(self,*,email:str,password:str)->tuple[Account,str]:
        email=email.strip().lower()
        if not _EMAIL_RE.match(email): raise ValueError('valid email required')
        if len(password)<10: raise ValueError('password must be at least 10 characters')
        with self._lock:
            if email in self._email_to_id: raise ValueError('account already exists')
            salt=secrets.token_bytes(16)
            aid='usr_'+secrets.token_urlsafe(12)
            acct=Account(aid,email,_hash_password(password,salt),base64.urlsafe_b64encode(salt).decode(),datetime.now(timezone.utc).isoformat())
            self._accounts[aid]=acct; self._email_to_id[email]=aid
            return acct,issue_token(user_id=aid,org_id='omni-control',role='creator',secret=self._secret,ttl_seconds=7*24*3600)

    def login(self,*,email:str,password:str)->tuple[Account,str]:
        email=email.strip().lower()
        with self._lock:
            aid=self._email_to_id.get(email)
            if not aid: raise PermissionError('invalid credentials')
            acct=self._accounts[aid]
            salt=base64.urlsafe_b64decode(acct.salt_b64.encode())
            if not hmac.compare_digest(acct.password_hash,_hash_password(password,salt)): raise PermissionError('invalid credentials')
            return acct,issue_token(user_id=aid,org_id='omni-control',role='creator',secret=self._secret,ttl_seconds=7*24*3600)

    def authenticate(self,token:str)->Account:
        try: claims=verify_token(token,secret=self._secret)
        except AuthError as exc: raise PermissionError('invalid authentication') from exc
        acct=self._accounts.get(claims.user_id)
        if not acct: raise PermissionError('account not found')
        return acct

    def create_project(self,*,owner_id:str,title:str)->ProjectRecord:
        title=' '.join(title.split()).strip()
        if not title: raise ValueError('title required')
        with self._lock:
            pid='prj_'+secrets.token_urlsafe(10)
            now=datetime.now(timezone.utc).isoformat()
            rec=ProjectRecord(pid,owner_id,title[:120],now,now)
            self._projects[pid]=rec; return rec

    def require_project(self,*,owner_id:str,project_id:str)->ProjectRecord:
        rec=self._projects.get(project_id)
        if not rec or rec.owner_id!=owner_id: raise PermissionError('project not found or access denied')
        return rec

    def list_projects(self,*,owner_id:str)->tuple[ProjectRecord,...]:
        return tuple(sorted((p for p in self._projects.values() if p.owner_id==owner_id),key=lambda p:p.updated_at,reverse=True))

    @staticmethod
    def internal_project_key(*,owner_id:str,project_id:str)->str:
        digest=sha256((owner_id+'\0'+project_id).encode()).hexdigest()[:24]
        return 'tenant_'+digest
