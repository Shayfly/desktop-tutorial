from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Callable, Protocol
import base64
import hmac
import secrets

from .account_tenant import Account, _EMAIL_RE, _hash_password
from .auth import AuthError, issue_token, verify_token
from .db import DatabasePool


class IdentityError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _as_iso(value) -> str:
    return _as_datetime(value).isoformat()


def _token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdentityAccount:
    id: str
    email: str
    password_hash: str
    salt_b64: str
    created_at: str
    status: str
    email_verified_at: str | None = None

    def as_account(self) -> Account:
        return Account(self.id, self.email, self.password_hash, self.salt_b64, self.created_at)


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    user_id: str
    token_hash: str
    created_at: str
    expires_at: str
    revoked_at: str | None = None
    last_seen_at: str | None = None


@dataclass(frozen=True)
class SessionView:
    session_id: str
    created_at: str
    expires_at: str
    revoked_at: str | None
    last_seen_at: str | None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "last_seen_at": self.last_seen_at,
        }


@dataclass(frozen=True)
class IdentityTokenRecord:
    token_id: str
    user_id: str
    purpose: str
    token_hash: str
    created_at: str
    expires_at: str
    consumed_at: str | None = None


@dataclass(frozen=True)
class ConsentRecord:
    user_id: str
    consent_type: str
    version: str
    source: str
    accepted_at: str


@dataclass(frozen=True)
class PrivacyRequest:
    request_id: str
    user_id: str
    request_type: str
    status: str
    requested_at: str
    completed_at: str | None = None


class IdentityRepository(Protocol):
    def create_account(self, account: IdentityAccount) -> None: ...
    def account_by_id(self, user_id: str) -> IdentityAccount | None: ...
    def account_by_email(self, email: str) -> IdentityAccount | None: ...
    def mark_email_verified(self, user_id: str, verified_at: str) -> IdentityAccount: ...
    def update_password_and_revoke_sessions(self, user_id: str, password_hash: str, salt_b64: str, revoked_at: str) -> None: ...
    def set_account_status(self, user_id: str, status: str, changed_at: str) -> None: ...
    def create_session(self, session: SessionRecord) -> None: ...
    def session_by_id(self, session_id: str) -> SessionRecord | None: ...
    def touch_session(self, session_id: str, seen_at: str) -> None: ...
    def revoke_session(self, user_id: str, session_id: str, revoked_at: str) -> bool: ...
    def revoke_all_sessions(self, user_id: str, revoked_at: str) -> None: ...
    def list_sessions(self, user_id: str) -> tuple[SessionRecord, ...]: ...
    def create_identity_token(self, record: IdentityTokenRecord) -> None: ...
    def consume_identity_token(self, token_hash: str, purpose: str, now: str) -> str | None: ...
    def record_consent(self, record: ConsentRecord) -> ConsentRecord: ...
    def create_privacy_request(self, request: PrivacyRequest) -> PrivacyRequest: ...


class MemoryIdentityRepository:
    """Shared-state test/reviewer repository. Production wiring uses Postgres."""

    def __init__(self) -> None:
        self._accounts: dict[str, IdentityAccount] = {}
        self._email_to_id: dict[str, str] = {}
        self._sessions: dict[str, SessionRecord] = {}
        self._identity_tokens: dict[str, IdentityTokenRecord] = {}
        self._consents: list[ConsentRecord] = []
        self._privacy_requests: dict[str, PrivacyRequest] = {}

    def create_account(self, account: IdentityAccount) -> None:
        if account.email in self._email_to_id:
            raise ValueError("account already exists")
        self._accounts[account.id] = account
        self._email_to_id[account.email] = account.id

    def account_by_id(self, user_id: str) -> IdentityAccount | None:
        return self._accounts.get(user_id)

    def account_by_email(self, email: str) -> IdentityAccount | None:
        user_id = self._email_to_id.get(email)
        return self._accounts.get(user_id) if user_id else None

    def mark_email_verified(self, user_id: str, verified_at: str) -> IdentityAccount:
        account = self._accounts[user_id]
        account = replace(account, status="ACTIVE", email_verified_at=verified_at)
        self._accounts[user_id] = account
        return account

    def update_password_and_revoke_sessions(self, user_id: str, password_hash: str, salt_b64: str, revoked_at: str) -> None:
        account = self._accounts[user_id]
        self._accounts[user_id] = replace(account, password_hash=password_hash, salt_b64=salt_b64)
        self.revoke_all_sessions(user_id, revoked_at)

    def set_account_status(self, user_id: str, status: str, changed_at: str) -> None:
        account = self._accounts[user_id]
        self._accounts[user_id] = replace(account, status=status)

    def create_session(self, session: SessionRecord) -> None:
        self._sessions[session.session_id] = session

    def session_by_id(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def touch_session(self, session_id: str, seen_at: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            self._sessions[session_id] = replace(session, last_seen_at=seen_at)

    def revoke_session(self, user_id: str, session_id: str, revoked_at: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or session.user_id != user_id:
            return False
        if session.revoked_at is None:
            self._sessions[session_id] = replace(session, revoked_at=revoked_at)
        return True

    def revoke_all_sessions(self, user_id: str, revoked_at: str) -> None:
        for session_id, session in tuple(self._sessions.items()):
            if session.user_id == user_id and session.revoked_at is None:
                self._sessions[session_id] = replace(session, revoked_at=revoked_at)

    def list_sessions(self, user_id: str) -> tuple[SessionRecord, ...]:
        return tuple(sorted((s for s in self._sessions.values() if s.user_id == user_id), key=lambda s: s.created_at, reverse=True))

    def create_identity_token(self, record: IdentityTokenRecord) -> None:
        self._identity_tokens[record.token_hash] = record

    def consume_identity_token(self, token_hash: str, purpose: str, now: str) -> str | None:
        record = self._identity_tokens.get(token_hash)
        if not record or record.purpose != purpose or record.consumed_at is not None:
            return None
        if _as_datetime(record.expires_at) <= _as_datetime(now):
            return None
        self._identity_tokens[token_hash] = replace(record, consumed_at=now)
        return record.user_id

    def record_consent(self, record: ConsentRecord) -> ConsentRecord:
        for existing in self._consents:
            if (existing.user_id, existing.consent_type, existing.version) == (record.user_id, record.consent_type, record.version):
                return existing
        self._consents.append(record)
        return record

    def consents_for(self, user_id: str) -> tuple[ConsentRecord, ...]:
        return tuple(x for x in self._consents if x.user_id == user_id)

    def create_privacy_request(self, request: PrivacyRequest) -> PrivacyRequest:
        self._privacy_requests[request.request_id] = request
        return request


class PostgresIdentityRepository:
    def __init__(self, pool: DatabasePool):
        self._pool = pool

    @staticmethod
    def _account(row) -> IdentityAccount | None:
        if not row:
            return None
        return IdentityAccount(
            id=str(row[0]), email=str(row[1]), password_hash=str(row[2]), salt_b64=str(row[3]),
            created_at=_as_iso(row[4]), status=str(row[5]),
            email_verified_at=_as_iso(row[6]) if row[6] else None,
        )

    @staticmethod
    def _session(row) -> SessionRecord | None:
        if not row:
            return None
        return SessionRecord(
            session_id=str(row[0]), user_id=str(row[1]), token_hash=str(row[2]),
            created_at=_as_iso(row[3]), expires_at=_as_iso(row[4]),
            revoked_at=_as_iso(row[5]) if row[5] else None,
            last_seen_at=_as_iso(row[6]) if row[6] else None,
        )

    def create_account(self, account: IdentityAccount) -> None:
        try:
            with self._pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO creator_accounts(id,email,password_hash,salt_b64,created_at,account_status,email_verified_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (account.id, account.email, account.password_hash, account.salt_b64, account.created_at, account.status, account.email_verified_at),
                        )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise ValueError("account already exists") from exc
            raise

    def account_by_id(self, user_id: str) -> IdentityAccount | None:
        return self._load("id", user_id)

    def account_by_email(self, email: str) -> IdentityAccount | None:
        return self._load("email", email)

    def _load(self, field: str, value: str) -> IdentityAccount | None:
        if field not in {"id", "email"}:
            raise ValueError("invalid account field")
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id,email,password_hash,salt_b64,created_at,account_status,email_verified_at FROM creator_accounts WHERE {field}=%s",
                    (value,),
                )
                return self._account(cur.fetchone())

    def mark_email_verified(self, user_id: str, verified_at: str) -> IdentityAccount:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE creator_accounts SET account_status='ACTIVE', email_verified_at=%s WHERE id=%s RETURNING id,email,password_hash,salt_b64,created_at,account_status,email_verified_at",
                        (verified_at, user_id),
                    )
                    row = cur.fetchone()
        if not row:
            raise IdentityError("account not found")
        return self._account(row)  # type: ignore[return-value]

    def update_password_and_revoke_sessions(self, user_id: str, password_hash: str, salt_b64: str, revoked_at: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE creator_accounts SET password_hash=%s,salt_b64=%s WHERE id=%s", (password_hash, salt_b64, user_id))
                    cur.execute("UPDATE creator_sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE user_id=%s AND revoked_at IS NULL", (revoked_at, user_id))

    def set_account_status(self, user_id: str, status: str, changed_at: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE creator_accounts SET account_status=%s WHERE id=%s", (status, user_id))

    def create_session(self, session: SessionRecord) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO creator_sessions(session_id,user_id,token_hash,created_at,expires_at,revoked_at,last_seen_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (session.session_id, session.user_id, session.token_hash, session.created_at, session.expires_at, session.revoked_at, session.last_seen_at),
                    )

    def session_by_id(self, session_id: str) -> SessionRecord | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT session_id,user_id,token_hash,created_at,expires_at,revoked_at,last_seen_at FROM creator_sessions WHERE session_id=%s", (session_id,))
                return self._session(cur.fetchone())

    def touch_session(self, session_id: str, seen_at: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE creator_sessions SET last_seen_at=%s WHERE session_id=%s AND revoked_at IS NULL", (seen_at, session_id))

    def revoke_session(self, user_id: str, session_id: str, revoked_at: str) -> bool:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE creator_sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE session_id=%s AND user_id=%s RETURNING session_id", (revoked_at, session_id, user_id))
                    return cur.fetchone() is not None

    def revoke_all_sessions(self, user_id: str, revoked_at: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("UPDATE creator_sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE user_id=%s AND revoked_at IS NULL", (revoked_at, user_id))

    def list_sessions(self, user_id: str) -> tuple[SessionRecord, ...]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT session_id,user_id,token_hash,created_at,expires_at,revoked_at,last_seen_at FROM creator_sessions WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
                return tuple(self._session(row) for row in cur.fetchall())  # type: ignore[misc]

    def create_identity_token(self, record: IdentityTokenRecord) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO creator_identity_tokens(id,user_id,purpose,token_hash,created_at,expires_at,consumed_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (record.token_id, record.user_id, record.purpose, record.token_hash, record.created_at, record.expires_at, record.consumed_at),
                    )

    def consume_identity_token(self, token_hash: str, purpose: str, now: str) -> str | None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id,user_id FROM creator_identity_tokens WHERE token_hash=%s AND purpose=%s AND consumed_at IS NULL AND expires_at>%s FOR UPDATE",
                        (token_hash, purpose, now),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    cur.execute("UPDATE creator_identity_tokens SET consumed_at=%s WHERE id=%s AND consumed_at IS NULL", (now, row[0]))
                    return str(row[1])

    def record_consent(self, record: ConsentRecord) -> ConsentRecord:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO creator_consents(user_id,consent_type,version,source,accepted_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(user_id,consent_type,version) DO NOTHING",
                        (record.user_id, record.consent_type, record.version, record.source, record.accepted_at),
                    )
        return record

    def create_privacy_request(self, request: PrivacyRequest) -> PrivacyRequest:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO creator_privacy_requests(id,user_id,request_type,status,requested_at,completed_at) VALUES(%s,%s,%s,%s,%s,%s)",
                        (request.request_id, request.user_id, request.request_type, request.status, request.requested_at, request.completed_at),
                    )
        return request


class IdentityService:
    SESSION_TTL = timedelta(days=7)
    EMAIL_VERIFICATION_TTL = timedelta(hours=24)
    PASSWORD_RESET_TTL = timedelta(hours=1)

    def __init__(self, *, token_secret: str, repository: IdentityRepository, now_fn: Callable[[], datetime] = _utc_now):
        if len(token_secret) < 32:
            raise ValueError("token_secret must be at least 32 chars")
        self._secret = token_secret
        self._repo = repository
        self._now_fn = now_fn

    def _now(self) -> datetime:
        value = self._now_fn()
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _issue_session(self, user_id: str) -> str:
        now = self._now()
        session_id = "ses_" + secrets.token_urlsafe(18)
        expires = now + self.SESSION_TTL
        token = issue_token(
            user_id=user_id,
            org_id="148ai-control",
            role="creator",
            secret=self._secret,
            ttl_seconds=int(self.SESSION_TTL.total_seconds()),
            now=int(now.timestamp()),
            session_id=session_id,
        )
        self._repo.create_session(SessionRecord(
            session_id=session_id,
            user_id=user_id,
            token_hash=_token_hash(token),
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            last_seen_at=now.isoformat(),
        ))
        return token

    def register(self, *, email: str, password: str) -> tuple[Account, str]:
        email = email.strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValueError("valid email required")
        if len(password) < 10:
            raise ValueError("password must be at least 10 characters")
        salt = secrets.token_bytes(16)
        account = IdentityAccount(
            id="usr_" + secrets.token_urlsafe(12),
            email=email,
            password_hash=_hash_password(password, salt),
            salt_b64=base64.urlsafe_b64encode(salt).decode(),
            created_at=self._now().isoformat(),
            status="PENDING_VERIFICATION",
        )
        self._repo.create_account(account)
        return account.as_account(), self._issue_session(account.id)

    def login(self, *, email: str, password: str) -> tuple[Account, str]:
        account = self._repo.account_by_email(email.strip().lower())
        if not account or account.status in {"DELETION_PENDING", "DELETED", "SUSPENDED"}:
            raise PermissionError("invalid credentials")
        salt = base64.urlsafe_b64decode(account.salt_b64.encode())
        if not hmac.compare_digest(account.password_hash, _hash_password(password, salt)):
            raise PermissionError("invalid credentials")
        return account.as_account(), self._issue_session(account.id)

    def authenticate(self, token: str) -> Account:
        now = self._now()
        try:
            claims = verify_token(token, secret=self._secret, now=int(now.timestamp()))
        except AuthError as exc:
            raise PermissionError("invalid authentication") from exc
        if not claims.session_id:
            raise PermissionError("durable session required")
        session = self._repo.session_by_id(claims.session_id)
        if not session or session.user_id != claims.user_id:
            raise PermissionError("session revoked or unavailable")
        if session.revoked_at is not None:
            raise PermissionError("session revoked")
        if _as_datetime(session.expires_at) <= now:
            raise PermissionError("session expired")
        if not hmac.compare_digest(session.token_hash, _token_hash(token)):
            raise PermissionError("invalid authentication")
        account = self._repo.account_by_id(claims.user_id)
        if not account or account.status in {"DELETION_PENDING", "DELETED", "SUSPENDED"}:
            raise PermissionError("account unavailable")
        self._repo.touch_session(session.session_id, now.isoformat())
        return account.as_account()

    def logout(self, token: str) -> None:
        now = self._now()
        try:
            claims = verify_token(token, secret=self._secret, now=int(now.timestamp()))
        except AuthError as exc:
            raise PermissionError("invalid authentication") from exc
        if not claims.session_id or not self._repo.revoke_session(claims.user_id, claims.session_id, now.isoformat()):
            raise PermissionError("session not found")

    def revoke_session(self, user_id: str, session_id: str) -> None:
        if not self._repo.revoke_session(user_id, session_id, self._now().isoformat()):
            raise PermissionError("session not found or access denied")

    def list_sessions(self, user_id: str) -> tuple[SessionView, ...]:
        return tuple(SessionView(s.session_id, s.created_at, s.expires_at, s.revoked_at, s.last_seen_at) for s in self._repo.list_sessions(user_id))

    def account_state(self, user_id: str) -> dict:
        account = self._repo.account_by_id(user_id)
        if not account:
            raise IdentityError("account not found")
        return {
            "status": account.status,
            "email_verified": account.email_verified_at is not None,
            "email_verified_at": account.email_verified_at,
        }

    def _create_one_time_token(self, user_id: str, purpose: str, ttl: timedelta) -> str:
        now = self._now()
        raw = secrets.token_urlsafe(32)
        self._repo.create_identity_token(IdentityTokenRecord(
            token_id="idt_" + secrets.token_urlsafe(12),
            user_id=user_id,
            purpose=purpose,
            token_hash=_token_hash(raw),
            created_at=now.isoformat(),
            expires_at=(now + ttl).isoformat(),
        ))
        return raw

    def request_email_verification(self, user_id: str) -> str:
        account = self._repo.account_by_id(user_id)
        if not account:
            raise IdentityError("account not found")
        if account.email_verified_at:
            raise IdentityError("email already verified")
        return self._create_one_time_token(user_id, "EMAIL_VERIFY", self.EMAIL_VERIFICATION_TTL)

    def verify_email(self, token: str) -> IdentityAccount:
        now = self._now().isoformat()
        user_id = self._repo.consume_identity_token(_token_hash(token), "EMAIL_VERIFY", now)
        if not user_id:
            raise IdentityError("invalid or expired verification token")
        return self._repo.mark_email_verified(user_id, now)

    def request_password_reset(self, email: str) -> str | None:
        account = self._repo.account_by_email(email.strip().lower())
        if not account or account.status in {"DELETED", "SUSPENDED"}:
            return None
        return self._create_one_time_token(account.id, "PASSWORD_RESET", self.PASSWORD_RESET_TTL)

    def reset_password(self, token: str | None, new_password: str) -> None:
        if not token:
            raise IdentityError("invalid or expired reset token")
        if len(new_password) < 10:
            raise ValueError("password must be at least 10 characters")
        now = self._now().isoformat()
        user_id = self._repo.consume_identity_token(_token_hash(token), "PASSWORD_RESET", now)
        if not user_id:
            raise IdentityError("invalid or expired reset token")
        salt = secrets.token_bytes(16)
        self._repo.update_password_and_revoke_sessions(
            user_id,
            _hash_password(new_password, salt),
            base64.urlsafe_b64encode(salt).decode(),
            now,
        )

    def record_consent(self, user_id: str, *, consent_type: str, version: str, source: str = "api") -> ConsentRecord:
        if not consent_type.strip() or not version.strip():
            raise ValueError("consent type and version required")
        if not self._repo.account_by_id(user_id):
            raise IdentityError("account not found")
        return self._repo.record_consent(ConsentRecord(user_id, consent_type.strip(), version.strip(), source.strip() or "api", self._now().isoformat()))

    def request_data_export(self, user_id: str) -> PrivacyRequest:
        return self._privacy_request(user_id, "DATA_EXPORT")

    def request_account_deletion(self, user_id: str) -> PrivacyRequest:
        request = self._privacy_request(user_id, "ACCOUNT_DELETION")
        now = self._now().isoformat()
        self._repo.set_account_status(user_id, "DELETION_PENDING", now)
        self._repo.revoke_all_sessions(user_id, now)
        return request

    def _privacy_request(self, user_id: str, request_type: str) -> PrivacyRequest:
        if not self._repo.account_by_id(user_id):
            raise IdentityError("account not found")
        request = PrivacyRequest(
            request_id="ipr_" + secrets.token_urlsafe(12),
            user_id=user_id,
            request_type=request_type,
            status="REQUESTED",
            requested_at=self._now().isoformat(),
        )
        return self._repo.create_privacy_request(request)
