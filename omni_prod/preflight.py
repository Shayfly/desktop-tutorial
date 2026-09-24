from __future__ import annotations
from dataclasses import dataclass
import importlib.util
import os
import shutil

@dataclass(frozen=True)
class PreflightIssue:
    code: str
    message: str
    blocking: bool = True

@dataclass(frozen=True)
class PreflightReport:
    ready: bool
    issues: tuple[PreflightIssue, ...]
    capabilities: dict[str, bool]

def _non_placeholder(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return not any(x in lowered for x in (
        "change_me", "changeme", "example", "placeholder", "your_"
    ))

def _module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None

def _binary_exists(name: str) -> bool:
    return shutil.which(name) is not None

def run_preflight(env: dict[str, str] | None = None) -> PreflightReport:
    e = dict(os.environ if env is None else env)
    issues: list[PreflightIssue] = []

    secret = e.get("OMNI_SECRET_KEY")
    if not secret or len(secret) < 48 or not _non_placeholder(secret):
        issues.append(PreflightIssue(
            "weak_secret_key",
            "OMNI_SECRET_KEY must be >=48 chars and not a placeholder."
        ))

    db_url = e.get("OMNI_DATABASE_URL", "")
    if not db_url.startswith(("postgresql://", "postgres://")):
        issues.append(PreflightIssue(
            "database_url",
            "Production database must use PostgreSQL."
        ))

    redis_url = e.get("OMNI_REDIS_URL", "")
    if not redis_url.startswith(("redis://", "rediss://")):
        issues.append(PreflightIssue(
            "redis_url",
            "Redis URL is missing or invalid."
        ))

    origins = [
        x.strip() for x in e.get("OMNI_ALLOWED_ORIGINS", "").split(",") if x.strip()
    ]
    if not origins or any(not x.startswith("https://") for x in origins):
        issues.append(PreflightIssue(
            "https_origins",
            "Production allowed origins must be explicit HTTPS origins."
        ))

    for key in ("OMNI_S3_ACCESS_KEY", "OMNI_S3_SECRET_KEY"):
        if not _non_placeholder(e.get(key)):
            issues.append(PreflightIssue(
                key.lower(),
                f"{key} must be configured with a non-placeholder value."
            ))

    capabilities = {
        "python_psycopg": _module_exists("psycopg"),
        "python_redis": _module_exists("redis"),
        "python_rq": _module_exists("rq"),
        "python_boto3": _module_exists("boto3"),
        "docker_or_podman": _binary_exists("docker") or _binary_exists("podman"),
        "java": _binary_exists("java"),
        "node": _binary_exists("node"),
        "gradle": _binary_exists("gradle"),
    }

    for capability in (
        "python_psycopg", "python_redis", "python_rq",
        "python_boto3", "docker_or_podman"
    ):
        if not capabilities[capability]:
            issues.append(PreflightIssue(
                f"missing_{capability}",
                f"Required production capability is unavailable: {capability}."
            ))

    return PreflightReport(
        ready=not any(i.blocking for i in issues),
        issues=tuple(issues),
        capabilities=capabilities,
    )
