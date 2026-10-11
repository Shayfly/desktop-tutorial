"""Public, repository-independent contracts for 148AI deployment checks."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ErrorClass(str, Enum):
    NONE = "NONE"
    HTTP_CONNECTION_FAILURE = "HTTP_CONNECTION_FAILURE"
    DNS_FAILURE = "DNS_FAILURE"
    TLS_FAILURE = "TLS_FAILURE"
    TIMEOUT = "TIMEOUT"
    HTTP_401 = "HTTP_401"
    HTTP_403 = "HTTP_403"
    HTTP_500 = "HTTP_500"
    HTTP_502 = "HTTP_502"
    HTTP_503 = "HTTP_503"
    HTTP_504 = "HTTP_504"
    HTTP_OTHER = "HTTP_OTHER"
    INVALID_JSON = "INVALID_JSON"
    INVALID_RESPONSE_CONTRACT = "INVALID_RESPONSE_CONTRACT"
    MIGRATION_NOT_APPLIED = "MIGRATION_NOT_APPLIED"
    DATABASE_NOT_READY = "DATABASE_NOT_READY"
    AUTHENTICATION_MISSING = "AUTHENTICATION_MISSING"
    AUTHENTICATION_INVALID = "AUTHENTICATION_INVALID"
    ENVIRONMENT_MISCONFIGURED = "ENVIRONMENT_MISCONFIGURED"
    UNEXPECTED_REDIRECT = "UNEXPECTED_REDIRECT"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
    DEPLOYMENT_SHA_UNVERIFIED = "DEPLOYMENT_SHA_UNVERIFIED"


class ExecutionMode(str, Enum):
    SAFE_READ_ONLY = "SAFE_READ_ONLY"
    CANARY = "CANARY"  # Reserved, not implemented or executable.


@dataclass(frozen=True)
class RunConfig:
    base_url: str
    target_environment: str
    project_id: str | None = None
    bearer_token: str | None = field(default=None, repr=False)
    expected_commit_sha: str | None = None
    # Must come from a separate TRUSTED deployment metadata API / authenticated CI context.
    # Do not set from an untrusted response header or app-served content.
    trusted_observed_commit_sha: str | None = None
    allowed_hosts: tuple[str, ...] = ()
    execution_mode: ExecutionMode = ExecutionMode.SAFE_READ_ONLY
    timeout_seconds: float = 5.0
    max_response_bytes: int = 1_048_576


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    method: str
    path: str
    status: CheckStatus
    required: bool
    observed_http_status: int | None
    classification: ErrorClass
    elapsed_ms: int
    evidence_summary: str


@dataclass
class VerificationResult:
    target_environment: str
    base_url: str
    expected_commit_sha: str | None
    observed_commit_sha: str | None
    started_at: str
    completed_at: str
    checks: list[CheckResult]
    blocking_reasons: list[str]
    verdict: Verdict
    execution_mode: ExecutionMode = ExecutionMode.SAFE_READ_ONLY
    run_id: str = field(default_factory=lambda: str(uuid4()))
    schema: str = "148ai-postdeploy-check/1"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "checks": [asdict(c) for c in self.checks]}
