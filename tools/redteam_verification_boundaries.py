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
from omni_prod.verification_verdict import verdict as stage_verdict
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

    def record(case, violated, observed, *, expected='FAIL'):
        findings.append({'case': case, 'expected': expected, 'boundary_violated': violated, 'observed': observed})

    def stage_case(name, cls, transport, *, must_propagate=None):
        stage = cls(transport)
        try:
            r = stage.execute(repository=REPO, spec=SPEC)
            if must_propagate:
                record(name, True, {'passed': r.passed, 'verdict': stage_verdict(r),
                                    'control_exception_swallowed': must_propagate.__name__},
                       expected='PROPAGATES ' + must_propagate.__name__)
            else:
                record(name, stage_verdict(r) != 'FAIL', {'passed': r.passed, 'verdict': stage_verdict(r),
                                                          'failure_ids': [f.acceptance_id for f in r.failures]})
        except Exception as exc:
            if must_propagate:
                record(name, not isinstance(exc, must_propagate), {'exception': type(exc).__name__},
                       expected='PROPAGATES ' + must_propagate.__name__)
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
        # T4 case 23, sharpened (Matt 2026-10-21): continuity alone is not enough; the group must also FAIL and name the
        # crashed check. Before, a group that ran both checks and then reported passed=True was counted as held.
        result = group.execute(repository=REPO, spec=SPEC)
        ids = [f.acceptance_id for f in result.failures]
        record('group_exception_suppresses_later_checks',
               calls != ['first', 'second'] or result.passed is not False or not any(i.endswith('_EXCEPTION') for i in ids),
               {'calls': calls, 'passed': result.passed, 'verdict': stage_verdict(result), 'failure_ids': ids},
               expected='FAIL, both checks ran, the crashed check named')
    except Exception as exc:
        record('group_exception_suppresses_later_checks', True, {'exception': type(exc).__name__, 'calls': calls})
    for name, report in (
            ('group_false_with_empty_failures', ExecutionReport(False, (), 'failure')),
            ('group_string_false', ExecutionReport('false', (AcceptanceFailure('BROWSER', 'broken'),))),
            ('group_true_with_failures', ExecutionReport(True, (AcceptanceFailure('BROWSER', 'broken'),)))):
        g = VerificationGroup(Transport(), (SimpleNamespace(check=lambda emitted=report, **kwargs: emitted),))
        result = g.execute(repository=REPO, spec=SPEC)
        record(name, stage_verdict(result) != 'FAIL', {'passed': result.passed, 'verdict': stage_verdict(result)})

    # ---- T4 (Matt 2026-10-21): NO_CHECKS is its own verdict, and the positive controls hold at least one real check.
    extra = []

    def judged(case, stage_or_group, expected):
        try:
            r = stage_or_group.execute(repository=REPO, spec=SPEC)
            got = stage_verdict(r)
            extra.append({'case': case, 'expected': expected, 'observed': {'verdict': got, 'passed': r.passed,
                          'failure_ids': [f.acceptance_id for f in r.failures]}, 'boundary_violated': got != expected})
        except Exception as exc:
            extra.append({'case': case, 'expected': expected, 'observed': {'exception': type(exc).__name__},
                          'boundary_violated': True})

    form = {'form': 'f1', 'rounds': [{'submitted': True, 'requests': ['POST /api/items 201'], 'ok_write': True,
                                      'text_changed': True, 'revealed': ['נשמר']}] * 2}
    browser_ok = 'OMNI_BROWSER_PROBE ' + json.dumps({'forms': [form], 'findings': [], 'page_errors': [], 'server_errors': []})
    check_ok = {'persona_id': 'visitor', 'step_id': 's1', 'kind': 'api_smoke', 'acceptance_ids': ['A1'], 'passed': True,
                'detail': 'GET / -> 200', 'http_status': 200}
    behavior_ok = 'BEHAVIOR-ACCEPTANCE ' + json.dumps({'status': 'PASS', 'summary': '1/1', 'checks': [check_ok]})
    visual_ok = 'OMNI_VISUAL_QA ' + json.dumps({'findings': [], 'controls': 3, 'text_elements': 7, 'scroll_width': 1280})
    judged('no_checks_browser_zero_forms', BrowserFlowExecutor(Transport(stdout='OMNI_BROWSER_PROBE {"forms":[],"findings":[]}')),
           'NO_CHECKS')
    judged('no_checks_behavior_pass_with_zero_checks',
           BehaviorAcceptanceExecutor(Transport(stdout='BEHAVIOR-ACCEPTANCE {"status":"PASS","checks":[]}')), 'NO_CHECKS')
    judged('no_checks_visual_nothing_inspected',
           VisualQAExecutor(Transport(stdout='OMNI_VISUAL_QA {"findings":[],"controls":0,"text_elements":0}')), 'NO_CHECKS')
    judged('positive_browser_one_form_exercised', BrowserFlowExecutor(Transport(stdout=browser_ok)), 'PASS')
    judged('positive_behavior_one_passing_check', BehaviorAcceptanceExecutor(Transport(stdout=behavior_ok)), 'PASS')
    judged('positive_visual_controls_inspected', VisualQAExecutor(Transport(stdout=visual_ok)), 'PASS')
    judged('positive_group_real_stages', VerificationGroup(Transport(), (
        BrowserFlowExecutor(Transport(stdout=browser_ok)), BehaviorAcceptanceExecutor(Transport(stdout=behavior_ok)),
        VisualQAExecutor(Transport(stdout=visual_ok)))), 'PASS')
    judged('positive_group_fails_when_one_real_stage_reports_no_checks', VerificationGroup(Transport(), (
        BrowserFlowExecutor(Transport(stdout='OMNI_BROWSER_PROBE {"forms":[],"findings":[]}')),
        BehaviorAcceptanceExecutor(Transport(stdout=behavior_ok)))), 'NO_CHECKS')
    # ---- Matt's #103 HOLD: a content site is judged (not refused), and no path returns the input report unjudged.
    page_ok = 'OMNI_BROWSER_PROBE ' + json.dumps({'forms': [], 'findings': [], 'page_errors': [], 'server_errors': []})
    page_js = 'OMNI_BROWSER_PROBE ' + json.dumps({'forms': [], 'page_errors': ['TypeError: x is undefined'],
        'server_errors': [], 'findings': [{'kind': 'page_error', 'message': 'uncaught JavaScript error: TypeError'}]})
    judged('positive_content_site_page_observed_no_forms', BrowserFlowExecutor(Transport(stdout=page_ok)), 'PASS')
    judged('content_site_with_a_javascript_error', BrowserFlowExecutor(Transport(stdout=page_js)), 'FAIL')
    no_plan_repo = {k: v for k, v in REPO.items() if k != '.omni/project.json'}
    no_plan_repo['.omni/project.json'] = json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim',
                                                     'start': ['python', 'app.py'], 'port': 8000, 'health_path': '/'})
    node_repo = dict(REPO)
    node_repo['.omni/project.json'] = json.dumps({**json.loads(REPO['.omni/project.json']), 'runtime': 'node:20-slim',
                                                  'start': ['node', 'app.js']})
    no_acceptance = SimpleNamespace(acceptance=[], requirements=[])

    def judged_on(case, stage, repo, spec, expected):
        try:
            r = stage.execute(repository=repo, spec=spec)
            got = stage_verdict(r)
            extra.append({'case': case, 'expected': expected, 'observed': {'verdict': got, 'passed': r.passed,
                          'failure_ids': [f.acceptance_id for f in r.failures]}, 'boundary_violated': got != expected})
        except Exception as exc:
            extra.append({'case': case, 'expected': expected, 'observed': {'exception': f'{type(exc).__name__}: {exc}'[:200]},
                          'boundary_violated': True})
    judged_on('behavior_no_acceptance_and_no_plan', BehaviorAcceptanceExecutor(Transport(stdout=behavior_ok)),
              no_plan_repo, no_acceptance, 'NO_CHECKS')
    judged_on('behavior_non_python_runtime', BehaviorAcceptanceExecutor(Transport(stdout=behavior_ok)),
              node_repo, SPEC, 'FAIL')
    judged_on('preview_non_python_runtime', PreviewReadyExecutor(Transport()), node_repo, SPEC, 'FAIL')
    for error in (BuildCancelled('synthetic cancel'), AttemptLedgerUnavailable('synthetic ledger down'),
                  ModelPolicyViolation('synthetic budget')):        # the GROUP re-raises control exceptions too
        def raises(exc=error, **kwargs):
            raise exc
        try:
            VerificationGroup(Transport(), (SimpleNamespace(check=raises),)).execute(repository=REPO, spec=SPEC)
            extra.append({'case': 'group_propagates_' + type(error).__name__, 'expected': 'PROPAGATES ' + type(error).__name__,
                          'observed': {'swallowed': True}, 'boundary_violated': True})
        except Exception as exc:
            extra.append({'case': 'group_propagates_' + type(error).__name__, 'expected': 'PROPAGATES ' + type(error).__name__,
                          'observed': {'exception': type(exc).__name__}, 'boundary_violated': not isinstance(exc, type(error))})
    report = {'scope': 'synthetic boundary probes; not live E2E', 'cases': len(findings),
              'violations': sum(f['boundary_violated'] for f in findings), 'findings': findings,
              't4_extra_cases': len(extra), 't4_extra_violations': sum(e['boundary_violated'] for e in extra),
              't4_extra': extra}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report['violations'] or report['t4_extra_violations'] else 0


if __name__ == '__main__':
    sys.exit(main())
