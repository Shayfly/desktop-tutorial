"""M5 Task 7: concrete provisioner for the ``managed_web_saas_v1`` profile.

Implements ``InfrastructureProvisioner`` on top of operator-configured,
generated-app-only infrastructure:

* database        -> a dedicated role + schema per project/environment on a
                     Postgres-compatible server reached through an *admin* DSN
                     reference (never the control-plane database login)
* auth_session    -> a per-app session signing secret
* object_storage  -> an S3-compatible bucket with a per-app/per-environment
                     prefix, using generated-app object credentials that must
                     differ from the control plane's
* scheduled_http  -> a per-app callback signing secret, after a health probe of
                     the operator's scheduler service
* outbound        -> a per-app webhook signing secret plus (optionally) a
                     generated-app email key reference

Every generated secret is written to the generated-app Vault and only its
``vault:`` reference leaves this module. A binding is ``LIVE`` only after the
resource was verified (login, read-back, probe object, health probe).
Missing configuration is ``NOT_CONFIGURED``; reuse of control-plane
credentials or a failed verification is ``BLOCKED``.

Environment variables (all optional; absence yields NOT_CONFIGURED):

  OMNI_GENAPP_SECRET_STORE_PROVIDER  vault (default) or infisical (explicit opt-in)
  OMNI_INFISICAL_BASE_URL            HTTPS origin (EU: https://eu.infisical.com)
  OMNI_INFISICAL_PROJECT_ID / _CLIENT_ID / _CLIENT_SECRET
  OMNI_INFISICAL_ENVIRONMENT         Infisical environment slug (default dev)
  OMNI_GENAPP_SECRET_STORE_URL       Vault base URL for generated-app secrets
  OMNI_GENAPP_SECRET_STORE_TOKEN_ENV name of the env var holding the Vault token
                                     (default OMNI_GENAPP_VAULT_TOKEN)
  OMNI_GENAPP_SECRET_MOUNT           KV v2 mount (default "secret")
  OMNI_GENAPP_DATABASE_ADMIN_DSN_REF env:/vault: reference to the admin DSN
  OMNI_GENAPP_S3_ENDPOINT / _BUCKET / _REGION
  OMNI_GENAPP_S3_ACCESS_KEY_REF / OMNI_GENAPP_S3_SECRET_KEY_REF
  OMNI_GENAPP_SCHEDULER_URL / OMNI_GENAPP_SCHEDULER_HEALTH_URL
  OMNI_GENAPP_SCHEDULER_TOKEN_REF
  OMNI_GENAPP_EMAIL_API_KEY_REF / OMNI_GENAPP_EMAIL_FROM_DOMAIN
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from datetime import datetime, timezone
import json
import logging
import os
import secrets as _secrets
from typing import Any, Callable, Mapping
from urllib import parse, request

from ..infrastructure_contracts import (
    BindingStatus,
    InfrastructureBinding,
    InfrastructureEnvironment,
    InfrastructureKind,
    InfrastructureQuote,
    deterministic_resource_name,
    validate_secret_reference,
)

LOG = logging.getLogger(__name__)

PROFILE_KEY = "managed_web_saas_v1"
PROVISIONER_NAME = "managed_web_saas"

_STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
_STATUS_BLOCKED = "BLOCKED"
_STATUS_PARTIAL = "PARTIAL"


def _clean(env: Mapping[str, str], name: str) -> str:
    return str(env.get(name, "") or "").strip()


@dataclass(frozen=True)
class ManagedWebSaaSConfig:
    secret_store_url: str = ""
    secret_store_token_env: str = "OMNI_GENAPP_VAULT_TOKEN"
    secret_store_token_present: bool = False
    secret_mount: str = "secret"
    database_admin_dsn_ref: str = ""
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_region: str = "auto"
    s3_access_key_ref: str = ""
    s3_secret_key_ref: str = ""
    s3_role_arn: str = ""
    s3_sts_endpoint: str = ""
    s3_credential_ttl_seconds: int = 3600
    scheduler_url: str = ""
    scheduler_health_url: str = ""
    scheduler_token_ref: str = ""
    email_api_key_ref: str = ""
    email_from_domain: str = ""
    provisioning_estimated_usd: Decimal | None = None
    provisioning_maximum_usd: Decimal | None = None
    secret_store_provider: str = "vault"
    infisical_base_url: str = ""
    infisical_project_id: str = ""
    infisical_environment: str = "dev"
    infisical_client_id: str = ""
    infisical_client_secret_present: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ManagedWebSaaSConfig":
        env = os.environ if env is None else env
        token_env = _clean(env, "OMNI_GENAPP_SECRET_STORE_TOKEN_ENV") or "OMNI_GENAPP_VAULT_TOKEN"
        scheduler_url = _clean(env, "OMNI_GENAPP_SCHEDULER_URL")
        return cls(
            secret_store_provider=_clean(env, "OMNI_GENAPP_SECRET_STORE_PROVIDER") or "vault",
            infisical_base_url=_clean(env, "OMNI_INFISICAL_BASE_URL"),
            infisical_project_id=_clean(env, "OMNI_INFISICAL_PROJECT_ID"),
            infisical_environment=_clean(env, "OMNI_INFISICAL_ENVIRONMENT") or "dev",
            infisical_client_id=_clean(env, "OMNI_INFISICAL_CLIENT_ID"),
            infisical_client_secret_present=bool(_clean(env, "OMNI_INFISICAL_CLIENT_SECRET")),
            secret_store_url=_clean(env, "OMNI_GENAPP_SECRET_STORE_URL"),
            secret_store_token_env=token_env,
            secret_store_token_present=bool(_clean(env, token_env)),
            secret_mount=_clean(env, "OMNI_GENAPP_SECRET_MOUNT") or "secret",
            database_admin_dsn_ref=_clean(env, "OMNI_GENAPP_DATABASE_ADMIN_DSN_REF"),
            s3_endpoint=_clean(env, "OMNI_GENAPP_S3_ENDPOINT"),
            s3_bucket=_clean(env, "OMNI_GENAPP_S3_BUCKET"),
            s3_region=_clean(env, "OMNI_GENAPP_S3_REGION") or "auto",
            s3_access_key_ref=_clean(env, "OMNI_GENAPP_S3_ACCESS_KEY_REF"),
            s3_secret_key_ref=_clean(env, "OMNI_GENAPP_S3_SECRET_KEY_REF"),
            s3_role_arn=_clean(env, "OMNI_GENAPP_S3_ROLE_ARN"),
            s3_sts_endpoint=_clean(env, "OMNI_GENAPP_S3_STS_ENDPOINT"),
            s3_credential_ttl_seconds=int(_clean(env, "OMNI_GENAPP_S3_CREDENTIAL_TTL_SECONDS") or 3600),
            scheduler_url=scheduler_url,
            scheduler_health_url=_clean(env, "OMNI_GENAPP_SCHEDULER_HEALTH_URL") or scheduler_url,
            scheduler_token_ref=_clean(env, "OMNI_GENAPP_SCHEDULER_TOKEN_REF"),
            email_api_key_ref=_clean(env, "OMNI_GENAPP_EMAIL_API_KEY_REF"),
            email_from_domain=_clean(env, "OMNI_GENAPP_EMAIL_FROM_DOMAIN"),
            provisioning_estimated_usd=_money(_clean(env, "OMNI_GENAPP_PROVISIONING_ESTIMATED_USD")),
            provisioning_maximum_usd=_money(_clean(env, "OMNI_GENAPP_PROVISIONING_MAXIMUM_USD")),
        )

    @property
    def secret_store_configured(self) -> bool:
        if self.secret_store_provider == "infisical":
            url = parse.urlsplit(self.infisical_base_url)
            valid_origin = (url.scheme == "https" and bool(url.hostname) and not url.username
                            and not url.password and not url.query and not url.fragment
                            and url.path in ("", "/"))
            return bool(valid_origin and self.infisical_project_id and self.infisical_environment
                        and self.infisical_client_id and self.infisical_client_secret_present)
        return bool(self.secret_store_provider == "vault" and self.secret_store_url
                    and self.secret_store_token_present)

    @property
    def secret_store_configuration_reason(self) -> str:
        if self.secret_store_provider == "infisical":
            return ("generated-app Infisical secret store is not configured: HTTPS "
                    "OMNI_INFISICAL_BASE_URL, OMNI_INFISICAL_PROJECT_ID, "
                    "OMNI_INFISICAL_CLIENT_ID and OMNI_INFISICAL_CLIENT_SECRET are required")
        if self.secret_store_provider != "vault":
            return "OMNI_GENAPP_SECRET_STORE_PROVIDER must be vault or infisical"
        return "generated-app secret store (OMNI_GENAPP_SECRET_STORE_URL + token) is not configured"

    # -- configuration-level readiness (no network) -------------------------
    def config_status(self, kind: InfrastructureKind, control_env: Mapping[str, str]) -> tuple[str, str]:
        """Static readiness. Never LIVE: live truth comes only from a verified binding."""
        if not self.secret_store_configured:
            if kind != InfrastructureKind.OBJECT_STORAGE:
                return _STATUS_NOT_CONFIGURED, self.secret_store_configuration_reason
        if kind == InfrastructureKind.DATABASE:
            if not self.database_admin_dsn_ref:
                return _STATUS_NOT_CONFIGURED, "OMNI_GENAPP_DATABASE_ADMIN_DSN_REF is not configured"
            if not _valid_ref(self.database_admin_dsn_ref):
                return _STATUS_BLOCKED, "OMNI_GENAPP_DATABASE_ADMIN_DSN_REF is not an env:/vault: reference"
            admin = _offline_resolve(self.database_admin_dsn_ref, control_env)
            if admin and admin == _clean(control_env, "OMNI_DATABASE_URL"):
                return _STATUS_BLOCKED, "generated apps must not use the control-plane database login"
        elif kind == InfrastructureKind.OBJECT_STORAGE:
            missing = [n for n, v in (("OMNI_GENAPP_S3_ENDPOINT", self.s3_endpoint),
                                      ("OMNI_GENAPP_S3_BUCKET", self.s3_bucket),
                                      ("OMNI_GENAPP_S3_ACCESS_KEY_REF", self.s3_access_key_ref),
                                      ("OMNI_GENAPP_S3_SECRET_KEY_REF", self.s3_secret_key_ref)) if not v]
            if missing:
                return _STATUS_NOT_CONFIGURED, "missing " + ", ".join(missing)
            if not self.s3_role_arn:
                return _STATUS_NOT_CONFIGURED, ("object storage isolation requires scoped per-app/environment credentials: "
                                                "set OMNI_GENAPP_S3_ROLE_ARN (STS AssumeRole with a prefix-scoped session policy)")
            if not (_valid_ref(self.s3_access_key_ref) and _valid_ref(self.s3_secret_key_ref)):
                return _STATUS_BLOCKED, "generated-app object credential settings must be env:/vault: references"
            if self.s3_bucket == _clean(control_env, "OMNI_S3_BUCKET"):
                return _STATUS_BLOCKED, "generated apps must not share the control-plane bucket"
            access = _offline_resolve(self.s3_access_key_ref, control_env)
            if access and access == _clean(control_env, "OMNI_S3_ACCESS_KEY"):
                return _STATUS_BLOCKED, "generated apps must not reuse control-plane object credentials"
        elif kind == InfrastructureKind.SCHEDULED_HTTP:
            if not self.scheduler_url or not self.scheduler_token_ref:
                return _STATUS_NOT_CONFIGURED, "OMNI_GENAPP_SCHEDULER_URL / OMNI_GENAPP_SCHEDULER_TOKEN_REF not configured"
            if not _valid_ref(self.scheduler_token_ref):
                return _STATUS_BLOCKED, "OMNI_GENAPP_SCHEDULER_TOKEN_REF is not an env:/vault: reference"
        elif kind == InfrastructureKind.OUTBOUND:
            if self.email_api_key_ref:
                if not _valid_ref(self.email_api_key_ref):
                    return _STATUS_BLOCKED, "OMNI_GENAPP_EMAIL_API_KEY_REF is not an env:/vault: reference"
                key = _offline_resolve(self.email_api_key_ref, control_env)
                if key and key == _clean(control_env, "RESEND_API_KEY"):
                    return _STATUS_BLOCKED, "generated apps must not reuse the control-plane email key"
        return _STATUS_PARTIAL, "configured; LIVE only after a per-binding verification succeeds"


def _money(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        amount = Decimal(value)
    except Exception:
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def _valid_ref(reference: str) -> bool:
    try:
        validate_secret_reference(reference)
        return True
    except ValueError:
        return False


def _offline_resolve(reference: str, env: Mapping[str, str]) -> str:
    """Resolve env: references from a mapping only (no network)."""
    if reference.startswith("env:"):
        return _clean(env, reference[4:])
    return ""


def _probe_url(url: str, *, token: str, timeout: float = 5.0, urlopen=None) -> int:
    opener = urlopen or request.urlopen
    req = request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with opener(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200))
    except Exception as exc:  # status codes from HTTPError, otherwise unreachable
        return int(getattr(exc, "code", 0) or 0)


class PostgresAdminBackend:
    """Real database backend (psycopg). Identifiers/passwords go through psycopg.sql."""

    def __init__(self, *, connect_timeout: int = 5) -> None:
        self.connect_timeout = connect_timeout

    def _connect(self, dsn: str):
        import psycopg
        return psycopg.connect(dsn, autocommit=True, connect_timeout=self.connect_timeout)

    def ensure_role_and_schema(self, *, admin_dsn: str, role: str, schema: str, password: str) -> dict:
        from psycopg import sql
        created = False
        with self._connect(admin_dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
                created = True
            else:
                cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION {}").format(
                sql.Identifier(schema), sql.Identifier(role)))
            cur.execute(sql.SQL("ALTER ROLE {} SET search_path = {}").format(sql.Identifier(role), sql.Identifier(schema)))
        return {"role": role, "schema": schema, "created": created}

    def verify_login(self, app_dsn: str, *, schema: str) -> bool:
        from psycopg import sql
        with self._connect(app_dsn) as conn, conn.cursor() as cur:
            table = sql.Identifier(schema, "_148ai_binding_probe")
            cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} (id integer)").format(table))
            cur.execute(sql.SQL("DROP TABLE {}").format(table))
            cur.execute("SELECT current_user")
            return cur.fetchone() is not None

    def disable_role(self, *, admin_dsn: str, role: str) -> None:
        from psycopg import sql
        with self._connect(admin_dsn) as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("ALTER ROLE {} NOLOGIN").format(sql.Identifier(role)))


_OBJECT_ACTIONS = ("s3:GetObject", "s3:PutObject", "s3:DeleteObject")


def scoped_object_policy(bucket: str, prefix: str) -> str:
    """Least-privilege session policy: object CRUD and listing under one prefix only."""
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "AppObjects", "Effect": "Allow", "Action": list(_OBJECT_ACTIONS),
             "Resource": [f"arn:aws:s3:::{bucket}/{prefix}*"]},
            {"Sid": "AppListing", "Effect": "Allow", "Action": ["s3:ListBucket"],
             "Resource": [f"arn:aws:s3:::{bucket}"], "Condition": {"StringLike": {"s3:prefix": [f"{prefix}*"]}}},
        ],
    }, sort_keys=True, separators=(",", ":"))


def scoped_policy_allows(policy, *, action: str, bucket: str, key: str) -> bool:
    """Evaluate the subset of IAM semantics scoped_object_policy uses (Allow + prefix wildcard)."""
    doc = json.loads(policy) if isinstance(policy, str) else dict(policy)
    target = f"arn:aws:s3:::{bucket}/{key}"
    for statement in doc.get("Statement", ()):
        if statement.get("Effect") != "Allow":
            continue
        actions = statement.get("Action")
        actions = actions if isinstance(actions, list) else [actions]
        if action not in actions or action == "s3:ListBucket":
            continue
        for resource in statement.get("Resource", ()):
            if resource.endswith("*") and target.startswith(resource[:-1]):
                return True
            if resource == target:
                return True
    return False


class StsCredentialIssuer:
    """Short-lived, prefix-scoped credentials via STS AssumeRole (AWS S3, MinIO and
    other S3-compatible stores that implement AssumeRole with session policies)."""

    def __init__(self, *, endpoint: str = "", region: str = "auto") -> None:
        self.endpoint = endpoint
        self.region = region

    def issue(self, *, operator_access_key, operator_secret_key, role_arn, policy, session_name, ttl_seconds) -> dict:
        import boto3
        client = boto3.client("sts", endpoint_url=self.endpoint or None,
                              region_name=None if self.region == "auto" else self.region,
                              aws_access_key_id=operator_access_key, aws_secret_access_key=operator_secret_key)
        out = client.assume_role(RoleArn=role_arn, RoleSessionName=session_name[:64], Policy=policy,
                                 DurationSeconds=int(ttl_seconds))["Credentials"]
        expires = out["Expiration"]
        return {"access_key_id": out["AccessKeyId"], "secret_access_key": out["SecretAccessKey"],
                "session_token": out["SessionToken"],
                "expires_at": expires.isoformat().replace("+00:00", "Z") if hasattr(expires, "isoformat") else str(expires)}


class S3ProbeBackend:
    """Real S3-compatible verification with the app's scoped credentials."""

    @staticmethod
    def _client(endpoint, region, access_key, secret_key, session_token):
        import boto3
        return boto3.client("s3", endpoint_url=endpoint, region_name=None if region == "auto" else region,
                            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                            aws_session_token=session_token)

    def verify(self, *, endpoint, bucket, prefix, region, access_key, secret_key, session_token=None) -> dict:
        key = prefix + ".148ai-probe"
        try:
            client = self._client(endpoint, region, access_key, secret_key, session_token)
            client.put_object(Bucket=bucket, Key=key, Body=b"148ai")
            client.delete_object(Bucket=bucket, Key=key)
        except Exception as exc:
            return {"probe_object": key, "ok": False, "error": type(exc).__name__}
        return {"probe_object": key, "ok": True}

    def verify_denied(self, *, endpoint, bucket, key, region, access_key, secret_key, session_token=None) -> bool:
        """True only if the store refuses access (403). A 404 means access was allowed."""
        try:
            self._client(endpoint, region, access_key, secret_key, session_token).get_object(Bucket=bucket, Key=key)
        except Exception as exc:
            code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
            status = getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
            return code in {"AccessDenied", "403", "Forbidden"} or status == 403
        return False


class ManagedWebSaaSProvisioner:
    name = PROVISIONER_NAME
    profile_key = PROFILE_KEY
    supported_kinds: tuple[InfrastructureKind, ...] = tuple(InfrastructureKind)

    def __init__(self, *, config: ManagedWebSaaSConfig, secret_store, resolve_reference: Callable[[str], str],
                 database_backend=None, storage_backend=None, http_probe: Callable[..., int] | None = None,
                 control_plane_env: Mapping[str, str] | None = None, credential_issuer=None) -> None:
        self.config = config
        self.secret_store = secret_store
        self.resolve_reference = resolve_reference
        self.database_backend = database_backend or PostgresAdminBackend()
        self.storage_backend = storage_backend or S3ProbeBackend()
        self.credential_issuer = credential_issuer or StsCredentialIssuer(
            endpoint=config.s3_sts_endpoint or config.s3_endpoint, region=config.s3_region)
        self.http_probe = http_probe or (lambda url, *, token: _probe_url(url, token=token))
        self.control_plane_env = os.environ if control_plane_env is None else control_plane_env

    # -- helpers ------------------------------------------------------------
    def _generated_ref(self, project_id: str, environment: InfrastructureEnvironment,
                       kind: InfrastructureKind, name: str) -> str:
        app = deterministic_resource_name(project_id=project_id, environment=environment, kind=kind).split("_")[1]
        return (f"vault:{self.config.secret_mount}/data/148ai/generated-apps/{app}/"
                f"{environment.value}/{kind.value}/{name}")

    def _is_generated_ref(self, reference: str) -> bool:
        return reference.startswith(f"vault:{self.config.secret_mount}/data/148ai/generated-apps/")

    def _binding(self, requirement, *, tenant_id, project_id, environment, idempotency_key, status,
                 refs=None, public=None, evidence=None, reason=None) -> InfrastructureBinding:
        kind = InfrastructureKind(requirement.kind)
        return InfrastructureBinding(
            binding_id="ib_" + idempotency_key[:24], profile_key=self.profile_key, tenant_id=tenant_id,
            project_id=project_id, environment=environment, kind=kind, status=status,
            resource_name=deterministic_resource_name(project_id=project_id, environment=environment, kind=kind),
            idempotency_key=idempotency_key, provisioner=self.name,
            secret_references=refs or {}, public_config=public or {},
            evidence={"verified": status == BindingStatus.LIVE, **(evidence or {})}, status_reason=reason,
        )

    def _resolve(self, reference: str) -> str | None:
        try:
            value = self.resolve_reference(reference)
        except Exception:
            return None
        return value or None

    def _store_generated(self, reference: str, value: str) -> bool:
        """Write then read back. True only if the secret store returns the same value."""
        self.secret_store.write(reference, value)
        try:
            return self.secret_store.resolve(reference) == value
        except Exception:
            return False

    # -- protocol -----------------------------------------------------------
    def quote(self, requirement, *, project_id, environment) -> InfrastructureQuote:
        maximum = self.config.provisioning_maximum_usd
        estimate = self.config.provisioning_estimated_usd if self.config.provisioning_estimated_usd is not None else maximum
        if maximum is not None and estimate is not None and estimate > maximum:
            estimate = maximum
        return InfrastructureQuote(
            profile_key=self.profile_key, kind=requirement.kind, environment=environment,
            estimated_monthly_usd=None, maximum_monthly_usd=None,
            basis=("operator-configured per-kind provisioning maximum (OMNI_GENAPP_PROVISIONING_MAXIMUM_USD)"
                   if maximum is not None else
                   "provisioning cost not configured (OMNI_GENAPP_PROVISIONING_MAXIMUM_USD); unknown, not zero"),
            provisioning_estimated_usd=estimate, provisioning_maximum_usd=maximum,
        )

    def provision(self, requirement, *, tenant_id, project_id, environment, idempotency_key) -> InfrastructureBinding:
        env = environment if isinstance(environment, InfrastructureEnvironment) else InfrastructureEnvironment(environment)
        kind = InfrastructureKind(requirement.kind)
        common = dict(tenant_id=tenant_id, project_id=project_id, environment=env, idempotency_key=idempotency_key)
        status, reason = self.config.config_status(kind, self.control_plane_env)
        if status == _STATUS_NOT_CONFIGURED:
            return self._binding(requirement, status=BindingStatus.NOT_CONFIGURED, reason=reason, **common)
        if status == _STATUS_BLOCKED:
            return self._binding(requirement, status=BindingStatus.BLOCKED, reason=reason, **common)
        handler = {
            InfrastructureKind.DATABASE: self._provision_database,
            InfrastructureKind.AUTH_SESSION: self._provision_auth_session,
            InfrastructureKind.OBJECT_STORAGE: self._provision_object_storage,
            InfrastructureKind.SCHEDULED_HTTP: self._provision_scheduled_http,
            InfrastructureKind.OUTBOUND: self._provision_outbound,
        }[kind]
        try:
            binding = handler(requirement, **common)
        except Exception as exc:
            # Exception text may contain DSNs or endpoints; record the class only.
            LOG.warning("generated-app %s provisioning failed for %s: %s",
                        kind.value, deterministic_resource_name(project_id=project_id, environment=env, kind=kind),
                        type(exc).__name__)
            return self._binding(requirement, status=BindingStatus.BLOCKED,
                                 reason=f"provisioning failed: {type(exc).__name__}", **common)
        LOG.info("generated-app %s binding %s -> %s", kind.value, binding.resource_name, binding.status.value)
        return binding

    def _provision_database(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
        admin_dsn = self._resolve(self.config.database_admin_dsn_ref)
        if not admin_dsn:
            return self._binding(requirement, status=BindingStatus.NOT_CONFIGURED,
                                 reason="admin DSN reference does not resolve", **common)
        if admin_dsn == _clean(self.control_plane_env, "OMNI_DATABASE_URL"):
            return self._binding(requirement, status=BindingStatus.BLOCKED,
                                 reason="generated apps must not use the control-plane database login", **common)
        name = deterministic_resource_name(project_id=project_id, environment=environment, kind=InfrastructureKind.DATABASE)
        password = _secrets.token_urlsafe(32)
        created = self.database_backend.ensure_role_and_schema(admin_dsn=admin_dsn, role=name, schema=name, password=password)
        parts = parse.urlsplit(admin_dsn)
        host, port = parts.hostname or "", parts.port or 5432
        database = parts.path.lstrip("/") or "postgres"
        query = dict(parse.parse_qsl(parts.query))
        query["options"] = f"-csearch_path={name}"
        app_dsn = parse.urlunsplit((parts.scheme or "postgresql",
                                    f"{parse.quote(name)}:{parse.quote(password, safe='')}@{host}:{port}",
                                    "/" + database, parse.urlencode(query), ""))
        ref = self._generated_ref(project_id, environment, InfrastructureKind.DATABASE, "database_url")
        stored = self._store_generated(ref, app_dsn)
        public = {"engine": "postgres-compatible", "host": host, "port": port, "database": database,
                  "schema": name, "role": name}
        if not stored:
            return self._binding(requirement, status=BindingStatus.BLOCKED, refs={"database_url": ref}, public=public,
                                 reason="secret store read-back verification failed", **common)
        if not self.database_backend.verify_login(app_dsn, schema=name):
            return self._binding(requirement, status=BindingStatus.BLOCKED, refs={"database_url": ref}, public=public,
                                 reason="generated-app role could not log in and write to its schema", **common)
        return self._binding(requirement, status=BindingStatus.LIVE, refs={"database_url": ref}, public=public,
                             evidence={"role_created": bool(created.get("created")), "login_verified": True,
                                       "schema_write_verified": True}, **common)

    def _provision_auth_session(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
        ref = self._generated_ref(project_id, environment, InfrastructureKind.AUTH_SESSION, "session_signing_secret")
        if not self._store_generated(ref, _secrets.token_urlsafe(48)):
            return self._binding(requirement, status=BindingStatus.BLOCKED, reason="secret store read-back failed", **common)
        return self._binding(requirement, status=BindingStatus.LIVE, refs={"session_signing_secret": ref},
                             public={"signing": "HMAC-SHA256", "rotation": "re-provision to rotate"},
                             evidence={"secret_read_back_verified": True}, **common)

    def _provision_object_storage(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
        """Per app/environment scoped credentials; LIVE only after the store itself
        allows the app prefix and DENIES the sibling environment's prefix."""
        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
        access = self._resolve(self.config.s3_access_key_ref)
        secret = self._resolve(self.config.s3_secret_key_ref)
        if not access or not secret:
            return self._binding(requirement, status=BindingStatus.NOT_CONFIGURED,
                                 reason="generated-app object credential references do not resolve", **common)
        if access == _clean(self.control_plane_env, "OMNI_S3_ACCESS_KEY"):
            return self._binding(requirement, status=BindingStatus.BLOCKED,
                                 reason="generated apps must not reuse control-plane object credentials", **common)
        name = deterministic_resource_name(project_id=project_id, environment=environment,
                                           kind=InfrastructureKind.OBJECT_STORAGE)
        app = name.split("_")[1]
        prefix = f"generated-apps/{app}/{environment.value}/"
        sibling_env = (InfrastructureEnvironment.PRODUCTION if environment == InfrastructureEnvironment.PREVIEW
                       else InfrastructureEnvironment.PREVIEW)
        sibling_key = f"generated-apps/{app}/{sibling_env.value}/.148ai-isolation-sentinel"
        policy = scoped_object_policy(self.config.s3_bucket, prefix)
        # The operator credentials only mint scoped credentials; they never reach the app.
        creds = self.credential_issuer.issue(
            operator_access_key=access, operator_secret_key=secret, role_arn=self.config.s3_role_arn,
            policy=policy, session_name=name, ttl_seconds=self.config.s3_credential_ttl_seconds)
        refs = {}
        for field in ("access_key_id", "secret_access_key", "session_token"):
            ref = self._generated_ref(project_id, environment, InfrastructureKind.OBJECT_STORAGE, field)
            if not self._store_generated(ref, str(creds[field])):
                return self._binding(requirement, status=BindingStatus.BLOCKED,
                                     reason="secret store read-back failed", **common)
            refs[field] = ref
        public = {"endpoint": self.config.s3_endpoint, "bucket": self.config.s3_bucket, "region": self.config.s3_region,
                  "prefix": prefix, "environment_isolation": "SCOPED_CREDENTIALS",
                  "access_policy": json.loads(policy), "scoped_access_expires_at": creds.get("expires_at")}
        scoped = dict(endpoint=self.config.s3_endpoint, bucket=self.config.s3_bucket, region=self.config.s3_region,
                      access_key=creds["access_key_id"], secret_key=creds["secret_access_key"],
                      session_token=creds.get("session_token"))
        probe = self.storage_backend.verify(prefix=prefix, **scoped)
        if not probe.get("ok"):
            return self._binding(requirement, status=BindingStatus.BLOCKED, refs=refs, public=public,
                                 evidence={"probe": {k: v for k, v in probe.items() if k != "ok"}},
                                 reason="object storage probe with scoped credentials failed", **common)
        denied = bool(self.storage_backend.verify_denied(key=sibling_key, **scoped))
        if not denied:
            return self._binding(requirement, status=BindingStatus.BLOCKED, refs=refs, public=public,
                                 evidence={"cross_environment_denied": False},
                                 reason="storage isolation not enforced: scoped credentials could access the "
                                        f"{sibling_env.value} prefix", **common)
        return self._binding(requirement, status=BindingStatus.LIVE, refs=refs, public=public,
                             evidence={"probe_object": probe.get("probe_object"), "write_delete_verified": True,
                                       "cross_environment_denied": True, "isolation": "SCOPED_CREDENTIALS"}, **common)

    def _provision_scheduled_http(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
        token = self._resolve(self.config.scheduler_token_ref)
        if not token:
            return self._binding(requirement, status=BindingStatus.NOT_CONFIGURED,
                                 reason="scheduler token reference does not resolve", **common)
        status_code = int(self.http_probe(self.config.scheduler_health_url, token=token))
        public = {"scheduler_endpoint": self.config.scheduler_url, "callback_verification": "HMAC-SHA256"}
        if not 200 <= status_code < 300:
            return self._binding(requirement, status=BindingStatus.BLOCKED, public=public,
                                 evidence={"health_status": status_code},
                                 reason=f"scheduler health probe returned {status_code}", **common)
        ref = self._generated_ref(project_id, environment, InfrastructureKind.SCHEDULED_HTTP, "callback_signing_secret")
        if not self._store_generated(ref, _secrets.token_urlsafe(48)):
            return self._binding(requirement, status=BindingStatus.BLOCKED, public=public,
                                 reason="secret store read-back failed", **common)
        # The scheduler's own token stays platform-side; the generated app only
        # receives the secret it needs to verify callbacks.
        return self._binding(requirement, status=BindingStatus.LIVE, refs={"callback_signing_secret": ref},
                             public=public, evidence={"health_status": status_code}, **common)

    def _provision_outbound(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
        refs: dict[str, str] = {}
        email_configured = False
        if self.config.email_api_key_ref:
            key = self._resolve(self.config.email_api_key_ref)
            if key and key == _clean(self.control_plane_env, "RESEND_API_KEY"):
                return self._binding(requirement, status=BindingStatus.BLOCKED,
                                     reason="generated apps must not reuse the control-plane email key", **common)
            if key:
                refs["email_api_key"] = self.config.email_api_key_ref
                email_configured = True
        ref = self._generated_ref(project_id, environment, InfrastructureKind.OUTBOUND, "webhook_signing_secret")
        if not self._store_generated(ref, _secrets.token_urlsafe(48)):
            return self._binding(requirement, status=BindingStatus.BLOCKED, reason="secret store read-back failed", **common)
        refs["webhook_signing_secret"] = ref
        public = {"webhook_signing": "HMAC-SHA256"}
        if email_configured:
            public["isolation_policy"] = ("the generated-app email key is shared across environments; "
                                          "webhook signing secrets are per environment")
        if self.config.email_from_domain:
            public["email_from_domain"] = self.config.email_from_domain
        return self._binding(requirement, status=BindingStatus.LIVE, refs=refs, public=public,
                             evidence={"webhook_secret_read_back_verified": True, "email_configured": email_configured,
                                       # No harmless send exists; email delivery is NOT claimed verified.
                                       "email_live_verified": False}, **common)

    def status(self, binding: InfrastructureBinding, *, now: str | None = None) -> InfrastructureBinding:
        if binding.status != BindingStatus.LIVE:
            return binding
        expires = binding.public_config.get("scoped_access_expires_at")
        current = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if expires and str(expires) <= current:
            return replace(binding, status=BindingStatus.BLOCKED,
                           status_reason="scoped credentials expired; re-provision to issue new ones")
        try:
            if binding.kind == InfrastructureKind.DATABASE:
                dsn = self.secret_store.resolve(binding.secret_references["database_url"])
                ok = self.database_backend.verify_login(dsn, schema=binding.public_config.get("schema", binding.resource_name))
            elif binding.kind == InfrastructureKind.OBJECT_STORAGE:
                probe = self.storage_backend.verify(
                    endpoint=binding.public_config["endpoint"], bucket=binding.public_config["bucket"],
                    prefix=binding.public_config["prefix"], region=binding.public_config.get("region", "auto"),
                    access_key=self.secret_store.resolve(binding.secret_references["access_key_id"]),
                    secret_key=self.secret_store.resolve(binding.secret_references["secret_access_key"]),
                    session_token=self.secret_store.resolve(binding.secret_references["session_token"]))
                ok = bool(probe.get("ok"))
            else:
                ok = all(self.secret_store.resolve(ref) for ref in binding.secret_references.values()
                         if self._is_generated_ref(ref))
        except Exception as exc:
            return replace(binding, status=BindingStatus.BLOCKED, status_reason=f"re-verification failed: {type(exc).__name__}")
        if not ok:
            return replace(binding, status=BindingStatus.BLOCKED, status_reason="re-verification failed")
        return binding

    def revoke(self, binding: InfrastructureBinding) -> InfrastructureBinding:
        if binding.kind == InfrastructureKind.DATABASE and binding.status == BindingStatus.LIVE:
            admin_dsn = self._resolve(self.config.database_admin_dsn_ref)
            if admin_dsn:
                self.database_backend.disable_role(admin_dsn=admin_dsn, role=binding.public_config.get("role", binding.resource_name))
        for reference in binding.secret_references.values():
            if self._is_generated_ref(reference):
                try:
                    self.secret_store.delete(reference)
                except Exception as exc:
                    LOG.warning("could not delete generated secret for %s: %s", binding.resource_name, type(exc).__name__)
        return binding.revoked(reason="revoked by platform")

    def readiness(self) -> dict[str, str]:
        return {kind.value: self.config.config_status(kind, self.control_plane_env)[0] for kind in self.supported_kinds}


def managed_web_saas_readiness(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Public, secret-free readiness surface for the first infrastructure profile."""
    env = os.environ if env is None else env
    config = ManagedWebSaaSConfig.from_env(env)
    kinds = {}
    for kind in InfrastructureKind:
        status, reason = config.config_status(kind, env)
        kinds[kind.value] = {"status": status, "reason": reason}
    return {
        "profile_key": PROFILE_KEY,
        "kinds": kinds,
        "truth_note": ("Configuration presence is at most PARTIAL. A kind is LIVE only on a binding whose "
                       "resource was provisioned and verified for a specific project and environment."),
    }


def build_managed_web_saas_provisioner(env: Mapping[str, str] | None = None):
    """Production wiring. Returns an explicit NOT_CONFIGURED provisioner when nothing is set up."""
    from ..infrastructure_provisioner import UnconfiguredInfrastructureProvisioner
    from ..secrets_manager import InfisicalHttpSecretWriter, VaultHttpSecretWriter

    env = os.environ if env is None else env
    config = ManagedWebSaaSConfig.from_env(env)
    if not config.secret_store_configured:
        return UnconfiguredInfrastructureProvisioner(
            reason=config.secret_store_configuration_reason)
    if config.secret_store_provider == "infisical":
        store = InfisicalHttpSecretWriter(
            base_url=config.infisical_base_url, project_id=config.infisical_project_id,
            environment=config.infisical_environment, client_id=config.infisical_client_id,
            client_secret=_clean(env, "OMNI_INFISICAL_CLIENT_SECRET"))
    else:
        store = VaultHttpSecretWriter(base_url=config.secret_store_url, token_env=config.secret_store_token_env)

    def resolve(reference: str) -> str:
        if reference.startswith("env:"):
            value = _clean(env, reference[4:])
            if not value:
                raise RuntimeError("secret not configured")
            return value
        return store.resolve(reference)

    return ManagedWebSaaSProvisioner(config=config, secret_store=store, resolve_reference=resolve,
                                     control_plane_env=env)
