"""Canonical verification verdict (Continuous Verification P0.3, directive Part 19).

One machine-readable result for every verification run, whatever produced it
(build release policy, post-deployment smoke, replay). Rules:

  * never VERIFIED by default: a result with no executed mandatory check is BLOCKED,
    and so is one missing (or downgrading to optional) a declared required check
  * any mandatory check FAIL                         -> FAILED  (promotion stops)
  * any mandatory check NOT_RUN / UNKNOWN            -> BLOCKED (cannot be verified)
  * only optional (advisory) checks failed/skipped   -> VERIFIED_WITH_ADVISORIES
  * otherwise                                        -> VERIFIED
  * stale evidence never promotes: the result must be for the exact commit /
    artifact being promoted and not past its expiry.

Check statuses reuse release_policy's vocabulary (PASS, FAIL, NOT_RUN, UNKNOWN,
NOT_APPLICABLE) so a quality-report/1 maps onto this contract unchanged.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

SCHEMA = 'verification-result/1'
POLICY_VERSION = 'verification-policy/1'

PENDING, RUNNING = 'PENDING', 'RUNNING'
VERIFIED, VERIFIED_WITH_ADVISORIES = 'VERIFIED', 'VERIFIED_WITH_ADVISORIES'
FAILED, BLOCKED, CANCELLED, EXPIRED = 'FAILED', 'BLOCKED', 'CANCELLED', 'EXPIRED'
VERDICTS = (PENDING, RUNNING, VERIFIED, VERIFIED_WITH_ADVISORIES, FAILED, BLOCKED, CANCELLED, EXPIRED)
PROMOTABLE = (VERIFIED, VERIFIED_WITH_ADVISORIES)

PASS, FAIL, NOT_RUN, UNKNOWN, NA = 'PASS', 'FAIL', 'NOT_RUN', 'UNKNOWN', 'NOT_APPLICABLE'
CHECK_STATUSES = (PASS, FAIL, NOT_RUN, UNKNOWN, NA)

# Directive Part 19 "blocking categories". A mandatory check carries one of these.
BLOCKING_CATEGORIES = (
    'startup', 'critical_api', 'auth_bypass', 'cross_user_exposure', 'data_integrity', 'security',
    'migration_compatibility', 'mandatory_feature', 'core_journey', 'artifact', 'deployment_identity',
)

DEFAULT_TTL_SECONDS = 24 * 3600


@dataclass(frozen=True)
class CheckResult:
    check: str
    status: str
    mandatory: bool = True
    category: str = 'core_journey'
    evidence: dict = field(default_factory=dict)
    reason: str = ''          # required when NOT_RUN / NOT_APPLICABLE (skipped with reason)

    def __post_init__(self):
        if self.status not in CHECK_STATUSES:
            raise ValueError(f'unknown check status {self.status!r}')
        if self.status in (NOT_RUN, NA) and not self.reason:
            raise ValueError(f'check {self.check!r} skipped without a reason')


def decide(checks: list[CheckResult], required: tuple[str, ...] = ()) -> tuple[str, str]:
    """(verdict, reason) under the rules in the module docstring. `required`
    names checks that must be present: a missing one blocks VERIFIED."""
    missing = [n for n in required if n not in {c.check for c in checks}]
    if missing:
        return BLOCKED, 'required checks missing: ' + ', '.join(missing)
    for name in required:
        if not next(c for c in checks if c.check == name).mandatory:
            return BLOCKED, f'required check {name} reported as optional'
    mandatory = [c for c in checks if c.mandatory]
    failed = [c.check for c in mandatory if c.status == FAIL]
    if failed:
        return FAILED, 'failed: ' + ', '.join(failed)
    if not any(c.status == PASS for c in mandatory):
        return BLOCKED, 'no mandatory check passed (never verified by default)'
    unverified = [c.check for c in mandatory if c.status in (NOT_RUN, UNKNOWN)]
    if unverified:
        return BLOCKED, 'not verified: ' + ', '.join(unverified)
    advisories = [c.check for c in checks if not c.mandatory and c.status in (FAIL, NOT_RUN, UNKNOWN)]
    if advisories:
        return VERIFIED_WITH_ADVISORIES, 'advisories: ' + ', '.join(advisories)
    return VERIFIED, 'all mandatory checks passed'


@dataclass
class VerificationResult:
    kind: str                         # 'deployment' | 'build' | 'replay'
    target: str                       # URL or build id
    environment: str
    commit_sha: str | None
    checks: list[CheckResult]
    artifact_sha256: str | None = None
    build_id: str | None = None
    project_id: str | None = None
    suites: dict = field(default_factory=dict)      # suite name -> version
    cost_usd: str = '0'
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    required: tuple = ()                            # check names that must be present and mandatory
    verdict: str = PENDING
    reason: str = ''

    def finish(self) -> 'VerificationResult':
        self.finished_at = time.time()
        self.verdict, self.reason = decide(self.checks, tuple(self.required))
        return self

    def to_dict(self) -> dict:
        d = asdict(self)
        d['schema'], d['policy_version'] = SCHEMA, POLICY_VERSION
        by = lambda *s: [c.check for c in self.checks if c.status in s]  # noqa: E731
        d['summary'] = {'executed': sum(c.status in (PASS, FAIL) for c in self.checks), 'passed': len(by(PASS)),
                        'failed': by(FAIL), 'skipped': [{'check': c.check, 'reason': c.reason}
                                                       for c in self.checks if c.status in (NOT_RUN, NA)],
                        'critical_blockers': [c.check for c in self.checks if c.mandatory and c.status != PASS
                                              and c.status != NA],
                        'warnings': [c.check for c in self.checks if not c.mandatory and c.status != PASS]}
        return d


def may_promote(result: dict, *, commit_sha: str | None = None, artifact_sha256: str | None = None,
                now: float | None = None) -> tuple[bool, str]:
    """Promotion gate. Refuses unverified, stale or mismatched evidence."""
    if result.get('schema') != SCHEMA:
        return False, 'not a verification-result/1'
    if result.get('verdict') not in PROMOTABLE:
        return False, f"verdict {result.get('verdict')}: {result.get('reason', '')}"
    if commit_sha and not (result.get('commit_sha') or '').startswith(commit_sha[:12]):
        return False, 'evidence is for a different commit (stale)'
    if artifact_sha256 and result.get('artifact_sha256') != artifact_sha256:
        return False, 'evidence is for a different artifact (stale)'
    finished = result.get('finished_at') or 0
    if (now or time.time()) - finished > int(result.get('ttl_seconds') or DEFAULT_TTL_SECONDS):
        return False, 'evidence expired'
    return True, 'promotable'


def from_quality_report(report: dict, *, environment: str, commit_sha: str | None = None) -> VerificationResult:
    """Map a release_policy quality-report/1 dict onto the canonical contract."""
    checks = []
    for c in report.get('checks', []):
        status = c.get('status', UNKNOWN)
        reason = c.get('detail') or ('not run' if status in (NOT_RUN, NA) else '')
        checks.append(CheckResult(check=f"{c.get('stage', 'check')}/{c.get('check', '?')}", status=status,
                                  mandatory=bool(c.get('required')), category=c.get('stage', 'core_journey'),
                                  evidence={'verifier': c.get('verifier'), 'independent': c.get('independent')},
                                  reason=reason))
    return VerificationResult(kind='build', target=report.get('build_id') or '?', environment=environment,
                              commit_sha=commit_sha, checks=checks, build_id=report.get('build_id'),
                              artifact_sha256=report.get('artifact_sha256'),
                              suites={'release_policy': report.get('policy_version', '?')}).finish()
