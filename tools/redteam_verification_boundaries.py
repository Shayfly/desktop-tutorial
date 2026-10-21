#!/usr/bin/env python3
"""Adversarial transport injection; no providers, R2 writes, fixes or paid work.

Exit 1 when a boundary is bypassed; exit 0 only when every tested boundary
holds. The injected sandbox responses are synthetic, never live E2E evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.attempt_ledger import AttemptLedgerUnavailable
from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor
from omni_prod.browser_probe import BrowserFlowExecutor
from omni_prod.build_control import BuildCancelled
from omni_prod.model_policy import ModelPolicyViolation
from omni_prod.preview_smoke import PreviewReadyExecutor
from omni_prod.verification_group import VerificationGroup
from omni_prod.visual_qa import VisualQAExecutor

PASS = ExecutionReport(True, (), 'threshold passed')
SPEC = SimpleNamespace(acceptance=[SimpleNamespace(id='A1', text='opens')], requirements=[])
REPO = {'app.py': 'print("transport fixture")\n', '.omni/project.json': json.dumps({
    'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'],
    'port': 8000, 'health_path': '/', 'web_saas_acceptance': {
        'product_family': 'managed_web_saas_v1', 'required_kinds': ['api_smoke'],
        'personas': [{'id': 'visitor', 'steps': [{'id': 's1', 'kind': 'api_smoke',
            'acceptance_ids': ['A1'], 'method': 'GET', 'path': '/', 'expect_status': 200}]}]}})}


class Transport:
    def __init__(self, *, error=None, stdout='', returncode=0):
        self.error, self.stdout, self.returncode = error, stdout, returncode

    def execute(self, **kwargs):
        return PASS

    def _run(self, *args, **kwargs):
        if self.error:
            raise self.error
        return {'returncode': self.returncode, 'stdout': self.stdout, 'stderr': ''}


def main():
    findings = []

    def record(case, violated, observed):
        findings.append({'case': case, 'boundary_violated': violated, 'observed': observed})

    def stage_case(name, cls, transport, *, must_propagate=None):
        stage = cls(transport)
        try:
            r = stage.execute(repository=REPO, spec=SPEC)
            if must_propagate:
                record(name, True, {'passed': r.passed, 'control_exception_swallowed': must_propagate.__name__})
            else:
                record(name, bool(r.passed), {'passed': r.passed})
        except Exception as exc:
            if must_propagate:
                record(name, not isinstance(exc, must_propagate), {'exception': type(exc).__name__})
            else:
                # Malformed product evidence must become an explicit failed stage,
                # not abort the group and suppress checks that have not run yet.
                record(name, True, {'uncaught_exception': type(exc).__name__})

    for cls in (BrowserFlowExecutor, VisualQAExecutor):
        stage_case(cls.__name__ + '_timeout', cls, Transport(error=TimeoutError('synthetic')))
        stage_case(cls.__name__ + '_missing_output', cls, Transport(stdout='', returncode=1))
    for cls, marker in ((BrowserFlowExecutor, 'OMNI_BROWSER_PROBE '),
                        (VisualQAExecutor, 'OMNI_VISUAL_QA '),
                        (BehaviorAcceptanceExecutor, 'BEHAVIOR-ACCEPTANCE ')):
        stage_case(cls.__name__ + '_json_list', cls, Transport(stdout=marker + '[]'))
    stage_case('browser_empty_object', BrowserFlowExecutor, Transport(stdout='OMNI_BROWSER_PROBE {}'))
    stage_case('browser_nonzero_exit_with_pass_payload', BrowserFlowExecutor,
               Transport(stdout='OMNI_BROWSER_PROBE {"forms":[],"findings":[]}', returncode=1))
    stage_case('behavior_nonzero_exit_with_pass_payload', BehaviorAcceptanceExecutor,
               Transport(stdout='BEHAVIOR-ACCEPTANCE {"status":"PASS","checks":[]}', returncode=1))
    for cls in (PreviewReadyExecutor, BehaviorAcceptanceExecutor, BrowserFlowExecutor, VisualQAExecutor):
        for error in (BuildCancelled('synthetic cancel'), AttemptLedgerUnavailable('synthetic mandatory ledger failure'),
                      ModelPolicyViolation('synthetic external model budget exceeded')):
            stage_case(cls.__name__ + '_' + type(error).__name__, cls, Transport(error=error),
                       must_propagate=type(error))

    calls = []
    def explode(**kwargs):
        calls.append('first')
        raise TimeoutError('synthetic stage exception')
    def second(**kwargs):
        calls.append('second')
        return PASS
    group = VerificationGroup(Transport(), (SimpleNamespace(check=explode), SimpleNamespace(check=second)))
    try:
        group.execute(repository=REPO, spec=SPEC)
        record('group_exception_suppresses_later_checks', calls != ['first', 'second'], {'calls': calls})
    except Exception as exc:
        record('group_exception_suppresses_later_checks', True, {'exception': type(exc).__name__, 'calls': calls})
    for name, report in (
            ('group_false_with_empty_failures', ExecutionReport(False, (), 'failure')),
            ('group_string_false', ExecutionReport('false', (AcceptanceFailure('BROWSER', 'broken'),))),
            ('group_true_with_failures', ExecutionReport(True, (AcceptanceFailure('BROWSER', 'broken'),)))):
        g = VerificationGroup(Transport(), (SimpleNamespace(check=lambda emitted=report, **kwargs: emitted),))
        result = g.execute(repository=REPO, spec=SPEC)
        record(name, bool(result.passed), {'passed': result.passed})
    report = {'scope': 'synthetic boundary probes; not live E2E', 'cases': len(findings),
              'violations': sum(f['boundary_violated'] for f in findings), 'findings': findings}
    print(json.dumps(report, indent=2))
    return 1 if report['violations'] else 0


if __name__ == '__main__':
    sys.exit(main())
