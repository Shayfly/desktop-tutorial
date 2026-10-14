"""Release policy: READY only when every mandatory check PASSED (directive
Production Assurance v2 §4/§5, issue #6 P1 "policy engine").

The verification chain is built from wrappers that may *skip* a check (no
runner, flag off, browser unavailable, plan missing, review rounds exhausted);
a skipped check used to look exactly like a passed one. This module turns the
build's evidence into a schema-versioned QualityReport where every check has

  status     PASS | FAIL | NOT_RUN | UNKNOWN | NOT_APPLICABLE
  required   mandatory checks block READY unless PASS (NOT_RUN/UNKNOWN block too)
  verifier   who decided: platform:<module> (deterministic, platform-owned) or
             model:<name>; `independent` is False when the verifier is the
             model that wrote the code
  severity   critical | high | medium | low

No weighted score can override a mandatory check. The report is bound to the
digest of the exact repository that was checked (`artifact_sha256`).
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field

SCHEMA = 'quality-report/1'
POLICY_VERSION = 'release-policy/1'

PASS, FAIL, NOT_RUN, UNKNOWN, NA = 'PASS', 'FAIL', 'NOT_RUN', 'UNKNOWN', 'NOT_APPLICABLE'

# Stage order of the build (directive §2): used for display and stage rows.
STAGES = ('requirements', 'plan', 'files', 'dependencies', 'build', 'tests', 'repair', 'preview', 'acceptance',
          'visual', 'quality', 'security', 'review', 'rights', 'capabilities', 'release')


@dataclass(frozen=True)
class Check:
    stage: str
    check: str
    status: str
    required: bool
    verifier: str
    independent: bool
    severity: str = 'high'
    detail: str = ''

    @property
    def blocks(self) -> bool:
        return self.required and self.status != PASS and self.status != NA


@dataclass
class QualityReport:
    build_id: str
    artifact_sha256: str
    product_family: str
    checks: list[Check] = field(default_factory=list)
    schema: str = SCHEMA
    policy_version: str = POLICY_VERSION

    @property
    def blocking(self) -> list[Check]:
        return [c for c in self.checks if c.blocks]

    @property
    def decision(self) -> str:
        return 'READY' if not self.blocking else 'FAILED'

    def coverage(self) -> dict:
        out = {s: 0 for s in (PASS, FAIL, NOT_RUN, UNKNOWN, NA)}
        for c in self.checks:
            out[c.status] = out.get(c.status, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {'schema': self.schema, 'policy_version': self.policy_version, 'build_id': self.build_id,
                'artifact_sha256': self.artifact_sha256, 'product_family': self.product_family,
                'decision': self.decision, 'coverage': self.coverage(),
                'blocking': [f'{c.stage}/{c.check}: {c.status}' for c in self.blocking],
                'checks': [asdict(c) for c in self.checks]}


def _status_from(value) -> str:
    if value is None:
        return NOT_RUN
    v = str(value).lower()
    if v in ('pass', 'passed', 'ok', 'verified', 'true'):
        return PASS
    if v in ('fail', 'failed', 'error', 'false'):
        return FAIL
    if v in ('not_run', 'unavailable', 'skipped', 'disabled'):
        return NOT_RUN
    return UNKNOWN


def build_report(*, build_id: str, artifact_sha256: str, result, evidence: dict, quality, security, rights,
                 author_models: set[str] | None = None) -> QualityReport:
    """QualityReport for an async web build from what the chain recorded.

    `result.report.passed` is the outcome of the whole chain; the per-executor
    evidence tells which checks actually ran. Every product the platform builds
    today is a web product (preview contract required), so the web family's
    mandatory set applies."""
    ev = evidence or {}
    chain_passed = bool(result.report.passed and result.status == 'ready')
    failing_ids = {getattr(f, 'acceptance_id', '') for f in getattr(result.report, 'failures', ()) or ()}
    r = QualityReport(build_id=build_id, artifact_sha256=artifact_sha256, product_family='web_saas')
    add = r.checks.append
    authors = author_models or set()

    pre_sandbox = {'CONSISTENCY', 'UNSUPPORTED_DEPENDENCY'}
    after_tests = {'PREVIEW', 'BEHAVIOR', 'BROWSER', 'VISUAL', 'QUALITY', 'REVIEW'}

    def tests_status() -> str:
        # Chain order: consistency/dependencies -> sandbox tests -> preview ->
        # behaviour -> browser -> quality -> review.
        if chain_passed:
            return PASS
        if failing_ids & pre_sandbox:
            return NOT_RUN
        if failing_ids - after_tests:
            return FAIL
        return PASS if failing_ids else UNKNOWN

    spec = getattr(result, 'spec', None)
    acceptance = list(getattr(spec, 'acceptance', ()) or ())
    add(Check('requirements', 'acceptance_criteria_defined', PASS if acceptance else FAIL, True,
              'platform:release_policy', True, 'critical',
              f'{len(acceptance)} acceptance criteria' if acceptance else 'the spec has no acceptance criteria'))

    cons = ev.get('consistency_gate')
    if cons is None:
        add(Check('files', 'cross_file_consistency', NOT_RUN, True, 'platform:consistency_gate', True, 'high',
                  'consistency gate did not run (disabled)'))
    else:
        last = cons.get('last') or {}
        add(Check('files', 'cross_file_consistency', PASS if last.get('passed') else FAIL, True,
                  'platform:consistency_gate', True, 'high',
                  f"{len(last.get('blocking') or [])} blocking, {len(last.get('advisories') or [])} advisories"))

    if 'UNSUPPORTED_DEPENDENCY' in failing_ids:
        dep = FAIL
    elif chain_passed or (failing_ids and not failing_ids & {'CONSISTENCY'}):
        dep = PASS   # the allowlist runs before the sandbox; a later failure means it passed
    else:
        dep = NOT_RUN if 'CONSISTENCY' in failing_ids else UNKNOWN
    add(Check('dependencies', 'dependency_allowlist', dep, True, 'platform:dependency_policy', True, 'high'))
    add(Check('tests', 'sandbox_build_and_tests', tests_status(),
              True, 'platform:sandbox (model-written tests)', False, 'high',
              'tests and verify commands were written by the generating model'))

    smoke = (ev.get('preview_smoke') or {}).get('status')
    add(Check('preview', 'preview_starts', FAIL if 'PREVIEW' in failing_ids else _status_from(smoke),
              True, 'platform:preview_smoke', True, 'critical'))

    beh = (ev.get('behavior_acceptance') or {}).get('last') or {}
    beh_status = FAIL if 'BEHAVIOR' in failing_ids else _status_from(beh.get('status'))
    add(Check('acceptance', 'behavioural_acceptance', beh_status, True,
              'platform:behavior_acceptance (model-written steps, platform floor)', True, 'critical',
              str(beh.get('summary') or '')[:300]))

    approved = ev.get('approved_acceptance')
    if approved is not None:
        # ADWv1 G3: the customer-approved criteria are the test basis of a
        # plan-governed build. Each must be in the spec AND covered by a
        # passing behavioural step; not run is not a pass.
        ids = list(approved.get('ids') or [])
        spec_ids = {getattr(a, 'id', None) for a in acceptance}
        covered = set(beh.get('covered_acceptance_ids') or [])
        not_in_spec = [i for i in ids if i not in spec_ids]
        missing = [i for i in ids if i not in covered]
        if not ids:
            ap_status, ap_detail = FAIL, 'no approved acceptance criteria were bound'
        elif not_in_spec:
            ap_status, ap_detail = FAIL, 'approved criteria missing from the spec: ' + ','.join(not_in_spec)
        elif not beh:
            ap_status, ap_detail = NOT_RUN, 'behavioural acceptance did not run'
        elif missing:
            ap_status, ap_detail = FAIL, 'approved criteria without a passing step: ' + ','.join(missing)
        else:
            ap_status, ap_detail = PASS, f'{len(ids)} approved criteria covered by passing steps'
        add(Check('acceptance', 'approved_criteria_covered', ap_status, True, 'platform:release_policy', True,
                  'critical', ap_detail[:300]))

    probe = ev.get('browser_check') or {}
    add(Check('visual', 'browser_flow', FAIL if 'BROWSER' in failing_ids else _status_from(probe.get('status')),
              True, 'platform:browser_probe', True, 'high', str(probe.get('reason') or '')[:300]))

    vis = ev.get('visual_qa') or {}
    vstat = {'PASS': PASS, 'FINDINGS': FAIL, 'FAIL': FAIL, 'NOT_RUN': NOT_RUN}.get(vis.get('status'), NOT_RUN)
    counts = {}
    for vp in (vis.get('viewports') or {}).values():
        for k, n in (vp.get('counts') or {}).items():
            counts[k] = counts.get(k, 0) + n
    # The executor applies the configured enforced rule set. Its VISUAL
    # failure is authoritative even if detail evidence is absent or stale.
    # Other findings (e.g. advisory contrast/labels) must remain advisory.
    enforced_visual_failure = 'VISUAL' in failing_ids
    if enforced_visual_failure:
        vstat = FAIL
    add(Check('visual', 'visual_layout_desktop_mobile', vstat, enforced_visual_failure, 'platform:visual_qa', True, 'medium',
              ', '.join(f'{k} {n}' for k, n in sorted(counts.items()))[:300] or str(vis.get('reason') or '')))

    add(Check('quality', 'quality_score', PASS if quality.passed else FAIL, True, 'platform:quality_gate', True,
              'medium', f'score {getattr(quality, "score", "?")}/{getattr(quality, "minimum_score", "?")}'))
    add(Check('security', 'static_security_scan', PASS if security.passed else FAIL, True,
              'platform:security_testing', True, 'critical'))

    reviews = ev.get('product_review') or []
    if not reviews:
        add(Check('review', 'qa_review', NOT_RUN, False, 'model:reviewer', False, 'medium', 'no review ran'))
    else:
        last_review = reviews[-1]
        reviewer = str(last_review.get('model') or last_review.get('reviewer') or 'unavailable')
        unresolved = int(last_review.get('blocking') or 0)
        # Blocking findings left after the enforced rounds are a failure,
        # not a pass (audit 2026-10-10: they used to pass silently).
        add(Check('review', 'qa_review_blocking_findings', PASS if unresolved == 0 else FAIL, True,
                  f'model:{reviewer}' if reviewer != 'unavailable' else 'platform:static_review', True, 'high',
                  f'{unresolved} unresolved blocking finding(s) after {len(reviews)} review round(s)'))
        add(Check('review', 'reviewer_independent_of_author',
                  PASS if reviewer not in authors and reviewer != 'unavailable' else NOT_RUN, False,
                  'platform:release_policy', True, 'medium',
                  f'reviewer {reviewer}; authors {sorted(authors)}'))

    add(Check('rights', 'rights_clear', PASS if rights.publish_allowed else FAIL, True, 'platform:rights_ip', True,
              'medium'))
    return r


def enforcement_mode() -> str:
    """`enforce` blocks READY on a failed policy; `shadow` records only.
    Shadow is refused for staging/production environments."""
    mode = os.getenv('OMNI_RELEASE_POLICY', 'enforce').strip().lower()
    if os.getenv('OMNI_ENV', '').strip().lower() in ('staging', 'production'):
        return 'enforce'
    return mode if mode in ('enforce', 'shadow') else 'enforce'


def explain(report: QualityReport) -> str:
    parts = [f'{c.stage}/{c.check} {c.status}' + (f' ({c.detail})' if c.detail else '') for c in report.blocking]
    return ('release policy: mandatory checks not passed: ' + '; '.join(parts))[:2000]


_STAGE_SQL = (
    'INSERT INTO build_stage_results (build_id, job_kind, tenant_key, stage, check_key, status, required, verifier, '
    'independent, severity, detail, artifact_sha256, policy_version, report_schema, decision, source_commit, environment) '
    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) '
    'ON CONFLICT (build_id, artifact_sha256, policy_version, check_key) DO NOTHING')


def persist(pool, report: QualityReport, *, tenant_key: str | None = None, job_kind: str = 'build') -> int:
    """Store every check of the report as an immutable stage row (migration
    035). Idempotent per (build, artifact digest, policy version, check).
    Details are short and contain no repository content or secrets."""
    commit = (os.getenv('OMNI_SOURCE_COMMIT') or '')[:40] or None
    env = (os.getenv('OMNI_ENV') or '')[:40] or None
    rows = [(report.build_id, job_kind, tenant_key, c.stage, c.check, c.status, c.required, c.verifier[:120],
             c.independent, c.severity, c.detail[:1000], report.artifact_sha256, report.policy_version, report.schema,
             report.decision, commit, env) for c in report.checks]
    with pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(_STAGE_SQL, rows)
    return len(rows)
