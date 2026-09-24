from __future__ import annotations

from datetime import datetime, timezone
import base64, hmac, re, secrets
from .account_tenant import Account, ProjectRecord, _hash_password, _EMAIL_RE, AccountService
from .auth import issue_token, verify_token, AuthError
from .db import DatabasePool


class PostgresAccountService:
    """PostgreSQL implementation of the V26+ creator-account contract.

    The API deliberately mirrors AccountService so the control plane can switch
    from reviewer-memory mode to persistent production mode through configuration.
    """
    def __init__(self, *, token_secret: str, pool: DatabasePool):
        if len(token_secret) < 32:
            raise ValueError('token_secret must be at least 32 chars')
        self._secret = token_secret
        self._pool = pool

    def register(self, *, email: str, password: str) -> tuple[Account, str]:
        email = email.strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValueError('valid email required')
        if len(password) < 10:
            raise ValueError('password must be at least 10 characters')
        salt = secrets.token_bytes(16)
        aid = 'usr_' + secrets.token_urlsafe(12)
        now = datetime.now(timezone.utc).isoformat()
        acct = Account(aid, email, _hash_password(password, salt), base64.urlsafe_b64encode(salt).decode(), now)
        try:
            with self._pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO creator_accounts(id,email,password_hash,salt_b64,created_at) VALUES(%s,%s,%s,%s,%s)",
                            (acct.id, acct.email, acct.password_hash, acct.salt_b64, acct.created_at),
                        )
        except Exception as exc:
            if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
                raise ValueError('account already exists') from exc
            raise
        return acct, self._issue(acct.id)

    def _issue(self, user_id: str) -> str:
        return issue_token(user_id=user_id, org_id='148ai-control', role='creator', secret=self._secret, ttl_seconds=7*24*3600)

    @staticmethod
    def _row_to_account(row) -> Account:
        return Account(str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))

    def _load_account(self, *, account_id: str | None = None, email: str | None = None) -> Account | None:
        field, value = ('id', account_id) if account_id else ('email', email)
        if not value:
            return None
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id,email,password_hash,salt_b64,created_at FROM creator_accounts WHERE {field}=%s", (value,))
                row = cur.fetchone()
        return self._row_to_account(row) if row else None

    def login(self, *, email: str, password: str) -> tuple[Account, str]:
        acct = self._load_account(email=email.strip().lower())
        if not acct:
            raise PermissionError('invalid credentials')
        salt = base64.urlsafe_b64decode(acct.salt_b64.encode())
        if not hmac.compare_digest(acct.password_hash, _hash_password(password, salt)):
            raise PermissionError('invalid credentials')
        return acct, self._issue(acct.id)

    def authenticate(self, token: str) -> Account:
        try:
            claims = verify_token(token, secret=self._secret)
        except AuthError as exc:
            raise PermissionError('invalid authentication') from exc
        acct = self._load_account(account_id=claims.user_id)
        if not acct:
            raise PermissionError('account not found')
        return acct

    def create_project(self, *, owner_id: str, title: str) -> ProjectRecord:
        title = ' '.join(title.split()).strip()
        if not title:
            raise ValueError('title required')
        pid = 'prj_' + secrets.token_urlsafe(10)
        now = datetime.now(timezone.utc).isoformat()
        rec = ProjectRecord(pid, owner_id, title[:120], now, now)
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO creator_projects(id,owner_id,title,created_at,updated_at) VALUES(%s,%s,%s,%s,%s)",
                        (rec.id, rec.owner_id, rec.title, rec.created_at, rec.updated_at),
                    )
        return rec

    @staticmethod
    def _row_to_project(row) -> ProjectRecord:
        return ProjectRecord(str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))

    def require_project(self, *, owner_id: str, project_id: str) -> ProjectRecord:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id,owner_id,title,created_at,updated_at FROM creator_projects WHERE id=%s AND owner_id=%s", (project_id, owner_id))
                row = cur.fetchone()
        if not row:
            raise PermissionError('project not found or access denied')
        return self._row_to_project(row)

    def list_projects(self, *, owner_id: str) -> tuple[ProjectRecord, ...]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id,owner_id,title,created_at,updated_at FROM creator_projects WHERE owner_id=%s ORDER BY updated_at DESC", (owner_id,))
                rows = cur.fetchall()
        return tuple(self._row_to_project(row) for row in rows)

    internal_project_key = staticmethod(AccountService.internal_project_key)
