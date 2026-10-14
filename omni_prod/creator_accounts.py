from __future__ import annotations

from datetime import datetime, timezone
import base64, hmac, re, secrets
from .account_tenant import Account, ProjectRecord, _hash_password, _EMAIL_RE, AccountService
from .auth import issue_token, verify_token, AuthError
from .db import DatabasePool
from .identity_lifecycle import IdentityService, PostgresIdentityRepository
from .project_lifecycle import ProjectLifecycleService, PostgresProjectLifecycleRepository


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
        self.project_lifecycle = ProjectLifecycleService(PostgresProjectLifecycleRepository(pool))

    def register(self, *, email: str, password: str) -> tuple[Account, str]:
        return self.identity.register(email=email, password=password)

    def login(self, *, email: str, password: str) -> tuple[Account, str]:
        return self.identity.login(email=email, password=password)

    def authenticate(self, token: str) -> Account:
        return self.identity.authenticate(token)

    def create_project(self, *, owner_id: str, title: str) -> ProjectRecord:
        return self.project_lifecycle.create_project(owner_id=owner_id, title=title)

    def require_project(self, *, owner_id: str, project_id: str) -> ProjectRecord:
        return self.project_lifecycle.require_project(owner_id=owner_id, project_id=project_id)

    def list_projects(self, *, owner_id: str) -> tuple[ProjectRecord, ...]:
        return self.project_lifecycle.list_projects(owner_id=owner_id)

    def rename_project(self, *, owner_id: str, project_id: str, title: str) -> ProjectRecord:
        return self.project_lifecycle.rename_project(owner_id=owner_id, project_id=project_id, title=title)

    def search_projects(self, *, owner_id: str, query: str, include_archived: bool = False) -> tuple[ProjectRecord, ...]:
        return self.project_lifecycle.search_projects(owner_id=owner_id, query=query, include_archived=include_archived)

    def archive_project(self, *, owner_id: str, project_id: str):
        return self.project_lifecycle.archive_project(owner_id=owner_id, project_id=project_id)

    def unarchive_project(self, *, owner_id: str, project_id: str):
        return self.project_lifecycle.unarchive_project(owner_id=owner_id, project_id=project_id)

    def delete_project(self, *, owner_id: str, project_id: str, reason: str = 'user_request'):
        return self.project_lifecycle.delete_project(owner_id=owner_id, project_id=project_id, reason=reason)

    def project_state(self, *, owner_id: str, project_id: str):
        return self.project_lifecycle.project_state(owner_id=owner_id, project_id=project_id)

    internal_project_key = staticmethod(AccountService.internal_project_key)
