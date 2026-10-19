"""The post-build checks report together, so the repairer gets every failure in the same round (2026-10-19).

Rehearsal 39295707756: preview -> behaviour -> browser -> visual were nested and each returned as soon as anything
inside it failed. Behaviour passed only after repair 3; the browser then ran for the first time, found a dead form, and
no repair round was left. These tests drive the REAL production chain composition (`investor_app._verification_executor`)
through `AutonomousProductEngine`, with only the sandbox transport faked, and look at what the REPAIRER received.
On the old chain the browser failure never reaches the repairer while an earlier check fails.
"""
import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from omni_prod import investor_app
from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import FilePatch

MANIFEST = {"schema_version": 2, "runtime": "python:3.11-slim", "start": ["python", "app.py"], "port": 8000,
            "health_path": "/", "web_saas_acceptance": {
                "product_family": "managed_web_saas_v1", "required_kinds": ["api_smoke"],
                "personas": [{"id": "visitor", "steps": [{"id": "s1", "kind": "api_smoke", "acceptance_ids": ["A1"],
                                                           "method": "GET", "path": "/", "expect_status": 200}]}]}}
SPEC = SimpleNamespace(acceptance=[SimpleNamespace(id="A1", text="the page opens")], requirements=[])

BEHAVIOUR_FAIL = 'BEHAVIOR-ACCEPTANCE ' + json.dumps({"status": "FAIL", "summary": "1 failed check(s)", "checks": [
    {"id": "s1", "passed": False, "kind": "api_smoke", "detail": "GET / returned 500"}]})
BEHAVIOUR_PASS = 'BEHAVIOR-ACCEPTANCE ' + json.dumps({"status": "PASS", "summary": "1 checks", "checks": []})
BROWSER_DEAD_FORM = 'OMNI_BROWSER_PROBE ' + json.dumps({"forms": [], "findings": [
    {"kind": "dead_form", "message": "form 'addMatchForm': submitting it sent no request and changed nothing on the page"}]})
BROWSER_OK = 'OMNI_BROWSER_PROBE ' + json.dumps({"forms": [], "findings": []})
VISUAL_OK = 'OMNI_VISUAL_QA ' + json.dumps({"findings": [], "controls": 1, "text_elements": 1})


def fake_remote(script, calls):
    """Stands in for RemoteSandboxRepositoryExecutor: build/verify per `script['threshold_passes']`, canned stage output."""
    class FakeRemote:
        def __init__(self, config, **_):
            pass

        def execute(self, *, repository, spec):
            calls.append('threshold')
            if script.get('threshold_passes', True):
                return ExecutionReport(True, (), 'unit tests ok')
            return ExecutionReport(False, (AcceptanceFailure('A1', 'remote build failed', 'SyntaxError'),), 'x')

        def _run(self, repository, argv, build_id, profile='default'):
            calls.append(build_id)
            if build_id == 'preview-smoke':
                ok = script.get('preview_ok', True)
                return {'returncode': 0 if ok else 1, 'stdout': '' if ok else 'PREVIEW-SMOKE app exited before answering',
                        'stderr': ''}
            if build_id == 'behavior-acceptance':
                return {'returncode': 0, 'stdout': BEHAVIOUR_PASS if script.get('behaviour_ok', True) else BEHAVIOUR_FAIL,
                        'stderr': ''}
            if build_id == 'browser-probe':
                return {'returncode': 0, 'stdout': BROWSER_OK if script.get('browser_ok', True) else BROWSER_DEAD_FORM,
                        'stderr': ''}
            return {'returncode': 0, 'stdout': VISUAL_OK, 'stderr': ''}
    return FakeRemote


class Architect:
    def create_spec(self, prompt):
        return SPEC


class Generator:
    def generate(self, spec):
        return (FilePatch('app.py', 'print("v0")\n'), FilePatch('.omni/project.json', json.dumps(MANIFEST)))


class Repairer:
    def __init__(self):
        self.received = []                    # the failure ids handed to each repair call
        self.messages = []                    # and their messages

    def repair(self, *, spec, repo_summary, failures):
        self.received.append([f['acceptance_id'] for f in failures])
        self.messages.append({f['acceptance_id']: f['message'] for f in failures})
        return (FilePatch('app.py', f'print("v{len(self.received)}")\n'),)


class PostBuildChecksReachTheRepairerTogether(unittest.TestCase):
    ENV = {'OMNI_SANDBOX_RUNNER_URL': 'http://sandbox.invalid', 'OMNI_SANDBOX_SHARED_SECRET': 'x' * 40,
           'OMNI_CONSISTENCY_GATE': '0', 'OMNI_MIN_QUALITY_SCORE': '0'}

    def build(self, script):
        calls = []
        with mock.patch.dict(os.environ, self.ENV), \
                mock.patch.object(investor_app, 'RemoteSandboxRepositoryExecutor', fake_remote(script, calls)):
            executor = investor_app._verification_executor(None)
            repairer = Repairer()
            engine = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=repairer,
                                             executor=executor, max_repair_rounds=1)
            result = engine.build('league table')
        return result, repairer, calls

    GROUP = {'PREVIEW', 'BEHAVIOR', 'BROWSER', 'VISUAL', 'ALSO_FAILING'}

    def test_8_a_browser_failure_reaches_the_repairer_while_an_earlier_check_also_fails(self):
        # Old chain: preview failed -> behaviour, browser and visual never ran; the repairer saw only PREVIEW.
        result, repairer, calls = self.build({'preview_ok': False, 'browser_ok': False})
        self.assertIn('browser-probe', calls)
        self.assertEqual(repairer.received[0], ['PREVIEW', 'ALSO_FAILING'])      # most severe in full + one line
        also = repairer.messages[0]['ALSO_FAILING']
        self.assertIn('BROWSER', also)
        self.assertIn('addMatchForm', also)

    def test_9_behaviour_and_browser_failures_of_one_round_reach_the_repairer_together(self):
        result, repairer, calls = self.build({'behaviour_ok': False, 'browser_ok': False})
        self.assertEqual(repairer.received[0], ['BEHAVIOR', 'ALSO_FAILING'])     # neither swallowed
        self.assertIn('BROWSER: the product misbehaves in a real browser', repairer.messages[0]['ALSO_FAILING'])
        self.assertEqual(AutonomousProductEngine.progress(result.report)[0], 5)   # ranked by the most severe

    def test_10_a_build_failure_does_not_run_the_group(self):
        result, repairer, calls = self.build({'threshold_passes': False, 'browser_ok': False})
        self.assertEqual(set(calls), {'threshold'})                          # no post-build check ran
        self.assertEqual(repairer.received[0], ['A1'])

    def test_all_four_run_in_order_and_the_summary_lists_the_rest_most_severe_first(self):
        result, repairer, calls = self.build({'preview_ok': False, 'behaviour_ok': False, 'browser_ok': False})
        stage_calls = [c for c in calls if c != 'threshold']
        self.assertEqual(stage_calls[:5], ['preview-smoke', 'behavior-acceptance', 'browser-probe',
                                           'visual-desktop', 'visual-mobile'])
        self.assertEqual(repairer.received[0], ['PREVIEW', 'ALSO_FAILING'])
        also = repairer.messages[0]['ALSO_FAILING']
        self.assertLess(also.index('BEHAVIOR'), also.index('BROWSER'))
        self.assertEqual(AutonomousProductEngine.progress(result.report)[0], 4)

    def test_a_single_failing_check_is_reported_alone_without_a_summary(self):
        result, repairer, calls = self.build({'browser_ok': False})
        self.assertEqual(repairer.received[0], ['BROWSER'])

    def test_when_every_post_build_check_passes_none_reaches_the_repairer(self):
        result, repairer, calls = self.build({})
        for ids in repairer.received:                                         # (the quality gate is outside the group)
            self.assertFalse(set(ids) & self.GROUP, ids)

if __name__ == '__main__':
    unittest.main()
