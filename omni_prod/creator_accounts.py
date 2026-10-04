from __future__ import annotations

from datetime import datetime, timezone
import base64, hmac, re, secrets
from .account_tenant import Account, ProjectRecord, _hash_password, _EMAIL_RE, AccountService
from .auth import issue_token, verify_token, AuthError
from .db import DatabasePool
from .identity_lifecycle import IdentityService, PostgresIdentityRepository


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
        self.identity = IdentityService(
            token_secret=token_secret,
            repository=PostgresIdentityRepository(pool),
        )

    def register(self, *, email: str, password: str) -> tuple[Account, str]:
        return self.identity.register(email=email, password=password)

    def login(self, *, email: str, password: str) -> tuple[Account, str]:
        return self.identity.login(email=email, password=password)

    def authenticate(self, token: str) -> Account:
        return self.identity.authenticate(token)

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
