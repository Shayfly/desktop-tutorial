"""Canonical verification verdict (Continuous Verification P0.3, directive Part 19).

One machine-readable result for every verification run, whatever produced it
(build release policy, post-deployment smoke, replay). Rules:

  * never VERIFIED by default: a result with no executed mandatory check is BLOCKED,
    and so is one missing (or downgrading to optional) a declared required check
  * any mandatory check FAIL                         -> FAILED  (promotion stops)
  * any mandatory check NOT_RUN / UNKNOWN            -> BLOCKED (cannot be verified)
  * only optional (advisory) checks failed/skipped   -> VERIFIED_WITH_ADVISORIES
  * otherwise                                        -> VERIFIED
  * a mandatory check NOT_APPLICABLE                -> BLOCKED, unless an explicitly
    versioned NA policy (`na_policy`) names that check; then the verdict is
    VERIFIED_WITH_ADVISORIES and the policy version is recorded (fail closed)
  * stale evidence never promotes: the result must be bound to the exact full
    40-hex commit SHA and/or artifact digest being promoted, carry valid
    timestamps (started <= finished <= now + skew) and be inside its TTL.
    The verdict is recomputed from the checks at promotion time.

Check statuses reuse release_policy's vocabulary (PASS, FAIL, NOT_RUN, UNKNOWN,
NOT_APPLICABLE) so a quality-report/1 maps onto this contract unchanged.
"""
from __future__ import annotations

import math
import re
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

# Mandatory checks of a post-deployment verification (tools/deployment_verify.py).
# The promotion gate takes required lists from code like this, never from evidence.
DEPLOYMENT_REQUIRED_CHECKS = (
    'deployment_endpoint', 'commit_sha', 'schema_compatible', 'register_synthetic_user', 'create_project',
    'conversation_turn', 'conversation_persists', 'project_memory', 'unauthenticated_denied',
    'cross_user_isolation')

DEFAULT_TTL_SECONDS = 24 * 3600
MAX_TTL_SECONDS = 7 * 24 * 3600
CLOCK_SKEW_SECONDS = 60
_SHA_RE = re.compile(r'[0-9a-f]{40}')
_POLICY_VERSION_RE = re.compile(r'[a-z0-9][a-z0-9-]{0,63}/[1-9][0-9]{0,5}')


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


def validate_na_policy(policy) -> frozenset[str] | None:
    """Checks a NOT_APPLICABLE exception policy authorizes, or None if the
    policy is absent or malformed (malformed never authorizes anything).
    Shape: {'version': 'name/N', 'allowed': ['check', ...], 'reason': '...'}"""
    if policy is None or not isinstance(policy, dict):
        return None
    version, allowed, reason = policy.get('version'), policy.get('allowed'), policy.get('reason')
    if not (isinstance(version, str) and _POLICY_VERSION_RE.fullmatch(version)):
        return None
    if not isinstance(reason, str) or not reason.strip():
        return None
    if not isinstance(allowed, (list, tuple, frozenset, set)) or not all(isinstance(a, str) and a for a in allowed):
        return None
    return frozenset(allowed)


def decide(checks: list[CheckResult], required: tuple[str, ...] = (), na_policy: dict | None = None
           ) -> tuple[str, str]:
    """(verdict, reason) under the rules in the module docstring. `required`
    names checks that must be present: a missing one blocks VERIFIED.
    `na_policy` is the only way a mandatory NOT_APPLICABLE check can pass."""
    names = [c.check for c in checks]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        return BLOCKED, 'duplicate check names: ' + ', '.join(duplicates)
    missing = [n for n in required if n not in set(names)]
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
    na = [c.check for c in mandatory if c.status == NA]
    authorized = validate_na_policy(na_policy) or frozenset()
    unauthorized = [n for n in na if n not in authorized]
    if unauthorized:
        return BLOCKED, 'mandatory checks not applicable without an authorizing NA policy: ' + ', '.join(unauthorized)
    if na:
        return VERIFIED_WITH_ADVISORIES, f"not applicable under {na_policy['version']}: " + ', '.join(na)
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
    na_policy: dict | None = None                   # versioned NOT_APPLICABLE exceptions (None = none)
    verdict: str = PENDING
    reason: str = ''

    def finish(self) -> 'VerificationResult':
        self.finished_at = time.time()
        self.verdict, self.reason = decide(self.checks, tuple(self.required), self.na_policy)
        return self

    def to_dict(self) -> dict:
        d = asdict(self)
        d['schema'], d['policy_version'] = SCHEMA, POLICY_VERSION
        by = lambda *s: [c.check for c in self.checks if c.status in s]  # noqa: E731
        d['summary'] = {'executed': sum(c.status in (PASS, FAIL) for c in self.checks), 'passed': len(by(PASS)),
                        'failed': by(FAIL), 'skipped': [{'check': c.check, 'reason': c.reason}
                                                       for c in self.checks if c.status in (NOT_RUN, NA)],
                        'critical_blockers': [c.check for c in self.checks if c.mandatory and c.status != PASS
                                              and not (c.status == NA and c.check in
                                                       (validate_na_policy(self.na_policy) or ()))],
                        'warnings': [c.check for c in self.checks if not c.mandatory and c.status != PASS]}
        return d


def _number(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def may_promote(result: dict, *, required: tuple[str, ...], na_policy: dict | None = None,
                commit_sha: str | None = None, artifact_sha256: str | None = None,
                now: float | None = None) -> tuple[bool, str]:
    """Promotion gate. Refuses unverified, unbound, forged, stale or mismatched evidence.

    `required` and `na_policy` are the caller's trusted policy (e.g.
    DEPLOYMENT_REQUIRED_CHECKS). The evidence's own `required` / `na_policy`
    fields are never trusted: the verdict is recomputed under the caller's."""
    if not isinstance(required, tuple) or not required or not all(isinstance(r, str) and r for r in required):
        return False, 'caller must supply the trusted required-check list'
    if not isinstance(result, dict) or result.get('schema') != SCHEMA:
        return False, 'not a verification-result/1'
    if result.get('verdict') not in PROMOTABLE:
        return False, f"verdict {result.get('verdict')}: {result.get('reason', '')}"
    if not commit_sha and not artifact_sha256:
        return False, 'promotion target not bound (commit SHA or artifact digest required)'
    if commit_sha is not None:
        if not (isinstance(commit_sha, str) and _SHA_RE.fullmatch(commit_sha.lower())):
            return False, 'promotion commit must be a full 40-character SHA'
        ev = result.get('commit_sha')
        if not (isinstance(ev, str) and _SHA_RE.fullmatch(ev.lower()) and ev.lower() == commit_sha.lower()):
            return False, 'evidence is for a different or unidentified commit (exact 40-character match required)'
    if artifact_sha256 is not None and result.get('artifact_sha256') != artifact_sha256:
        return False, 'evidence is for a different artifact (stale)'
    started, finished = _number(result.get('started_at')), _number(result.get('finished_at'))
    ttl = result.get('ttl_seconds')
    clock = time.time() if now is None else now
    if started is None or finished is None:
        return False, 'evidence timestamps missing or invalid'
    if started > finished:
        return False, 'evidence finished before it started'
    if finished > clock + CLOCK_SKEW_SECONDS:
        return False, 'evidence is dated in the future'
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not 0 < ttl <= MAX_TTL_SECONDS:
        return False, 'evidence TTL missing or invalid'
    if clock - finished > ttl:
        return False, 'evidence expired'
    try:   # never trust the stored verdict: recompute it from the checks
        checks = [CheckResult(check=c['check'], status=c['status'], mandatory=c['mandatory'] is True,
                              category=c.get('category', 'core_journey'), reason=c.get('reason') or '')
                  for c in result.get('checks') or []]
        verdict, why = decide(checks, required, na_policy)
    except (KeyError, TypeError, ValueError):
        return False, 'evidence checks malformed'
    if verdict not in PROMOTABLE:
        return False, f'recomputed under the trusted policy: {verdict} ({why})'
    if verdict != result.get('verdict'):
        return False, f'stored verdict does not match its checks (recomputed {verdict})'
    return True, 'promotable'


def from_quality_report(report: dict, *, environment: str, commit_sha: str | None = None,
                        na_policy: dict | None = None) -> VerificationResult:
    """Map a release_policy quality-report/1 dict onto the canonical contract.
    release-policy/1 treats a required NOT_APPLICABLE check as non-blocking;
    here it blocks unless `na_policy` explicitly authorizes it (fail closed)."""
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
                              suites={'release_policy': report.get('policy_version', '?')},
                              na_policy=na_policy).finish()
