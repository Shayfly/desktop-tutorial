"""Fail-closed read-only post-deployment verification; no integration side effects."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from time import monotonic
from urllib.parse import quote

from .checks import validate
from .http_client import SafeHttpClient
from .models import CheckResult, CheckStatus, ErrorClass, ExecutionMode, RunConfig, Verdict, VerificationResult


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(value: str | None) -> bool:
    return bool(value is not None and re.fullmatch(r"[0-9a-fA-F]{40}", value))


def run_postdeploy_checks(config: RunConfig) -> VerificationResult:
    """Validate a caller-authorized deployment. No writes or model calls."""
    if config.execution_mode != ExecutionMode.SAFE_READ_ONLY:
        raise ValueError("CANARY is reserved and deliberately not executable")
    if not config.target_environment or len(config.target_environment) > 64:
        raise ValueError("target_environment required")
    if config.project_id is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", config.project_id):
        raise ValueError("Invalid project ID")
    for sha in (config.expected_commit_sha, config.trusted_observed_commit_sha):
        if sha is not None and not _sha(sha):
            raise ValueError("Commit SHA must be a complete 40-character SHA-1")
    start = _timestamp()
    client = SafeHttpClient(config.base_url, token=config.bearer_token,
                            allowed_hosts=config.allowed_hosts, timeout=config.timeout_seconds,
                            max_bytes=config.max_response_bytes)
    checks: list[CheckResult] = []

    cases = [
        ("public_pricing", "/api/v28/pricing", True, False),
        ("auth_me", "/api/v28/me", True, True),
        ("auth_projects", "/api/v28/projects", True, True),
        ("proj_conversation", "/api/v28/projects/{project_id}/conversation", True, True),
        ("proj_memory", "/api/v28/projects/{project_id}/memory", True, True),
        ("proj_discovery", "/api/v28/projects/{project_id}/discovery", False, True),
    ]
    for name, template, required, auth in cases:
        path = template.replace("{project_id}", quote(config.project_id, safe="") if config.project_id else "{project_id}")
        if auth and not config.bearer_token:
            checks.append(CheckResult(name, "GET", path, CheckStatus.NOT_RUN, required, None,
                                      ErrorClass.AUTHENTICATION_MISSING, 0, "Authenticated check not run: credentials missing"))
            continue
        if "{project_id}" in path:
            checks.append(CheckResult(name, "GET", path, CheckStatus.NOT_RUN, required, None,
                                      ErrorClass.ENVIRONMENT_MISCONFIGURED, 0, "Project ID missing"))
            continue
        before = monotonic()
        outcome = client.get(path, require_auth=auth)
        elapsed = round((monotonic() - before) * 1000)
        classification, summary = outcome.error, outcome.summary
        if classification == ErrorClass.NONE:
            ok, summary = validate(name, outcome.data)
            status = CheckStatus.PASS if ok else CheckStatus.FAIL
            if not ok:
                classification = ErrorClass.INVALID_RESPONSE_CONTRACT
        elif classification in (ErrorClass.MIGRATION_NOT_APPLIED, ErrorClass.DATABASE_NOT_READY,
                                ErrorClass.HTTP_403):
            status = CheckStatus.BLOCKED
        else:
            status = CheckStatus.FAIL
        checks.append(CheckResult(name, "GET", path, status, required,
                                  outcome.code, classification, elapsed, summary))

    if config.expected_commit_sha is not None:
        match = (config.trusted_observed_commit_sha is not None and
                 config.trusted_observed_commit_sha.lower() == config.expected_commit_sha.lower())
        checks.append(CheckResult("deployment_commit", "METADATA", "", CheckStatus.PASS if match else CheckStatus.BLOCKED,
                                  True, None, ErrorClass.NONE if match else ErrorClass.DEPLOYMENT_SHA_UNVERIFIED,
                                  0, "Trusted deployment SHA matches" if match else "Trusted deployment SHA missing or mismatched"))

    failed = [c for c in checks if c.required and c.status == CheckStatus.FAIL]
    blocked = [c for c in checks if c.required and c.status in (CheckStatus.BLOCKED, CheckStatus.NOT_RUN)]
    verdict = Verdict.FAILED if failed else (Verdict.BLOCKED if blocked else Verdict.VERIFIED)
    blockers = [f"{c.check_id}:{c.status.value}:{c.classification.value}" for c in checks
                if c.required and c.status != CheckStatus.PASS]
    return VerificationResult(target_environment=config.target_environment, base_url=client.base_url,
                              expected_commit_sha=config.expected_commit_sha,
                              observed_commit_sha=config.trusted_observed_commit_sha,
                              started_at=start, completed_at=_timestamp(), checks=checks,
                              blocking_reasons=blockers, verdict=verdict)
