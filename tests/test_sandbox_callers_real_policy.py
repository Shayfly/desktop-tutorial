"""The four in-sandbox scripts must pass the REAL J2 request policy (2026-10-19).

Rehearsal 39280924963 and the deploy browser-probe failed with "invalid command arguments": every caller sent
`('python', '-c', <multi-line script>)` and `validate_command` rejects any argument containing a newline. The unit tests
did not see it because they used a fake `_run` that skips the policy.

Here each caller goes through the real `RemoteSandboxRepositoryExecutor._run` (validate_snapshot + validate_command,
JSON body, HMAC signature). Only the HTTP transport is replaced: a stub runner that validates the request AGAIN exactly
as `sandbox_service` does, then for the default profile really runs the argv in a copy of the snapshot (the browser
profile needs Chromium, so it answers with a canned report). On the old code no request ever reaches the runner.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor
from omni_prod.browser_probe import BROWSER_PROFILE, BrowserFlowExecutor
from omni_prod.preview_smoke import PreviewReadyExecutor
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.sandbox_request_policy import validate_command, validate_snapshot
from omni_prod.visual_qa import VisualQAExecutor

from tests.test_behavior_acceptance_in_build import NO_LOGIN_SCOPE, SPEC, repository

CANNED = {'browser-probe': 'OMNI_BROWSER_PROBE ' + json.dumps({'findings': [], 'forms': []}),
          'visual': 'OMNI_VISUAL_QA ' + json.dumps({'findings': [], 'controls': 1, 'text_elements': 1})}


class StubRunner:
    """Stands in for the sandbox runner's HTTP endpoint."""

    def __init__(self):
        self.requests = []

    def __call__(self, req, timeout=None):
        payload = json.loads(req.data.decode())
        argv, profile = payload['argv'], payload.get('profile', 'default')
        validate_snapshot(payload['repository'])                     # the runner's own checks (sandbox_service.py)
        validate_command(argv, build_id=payload['build_id'], profile=profile, repository=payload['repository'])
        self.requests.append(payload)
        if profile == BROWSER_PROFILE:
            out = CANNED['visual' if payload['build_id'].startswith('visual-') else 'browser-probe']
            result = {'returncode': 0, 'stdout': out + '\n', 'stderr': ''}
        else:
            with tempfile.TemporaryDirectory() as root:
                for path, text in payload['repository'].items():
                    full = os.path.join(root, path)
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, 'w', encoding='utf-8') as fh:
                        fh.write(text)
                cmd = [sys.executable if argv[0] == 'python' else argv[0], *argv[1:]]
                p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=120)
                result = {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
        body = json.dumps(result).encode()

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return Resp(body)


class Inner:
    """The inner chain passed; `_run` is the REAL remote executor's."""

    def __init__(self, runner):
        self._remote = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox.invalid', 'x' * 40),
                                                       urlopen=runner)
        self._run = self._remote._run

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'inner ok')


class FourCallersThroughTheRealPolicyTests(unittest.TestCase):
    def setUp(self):
        self.runner = StubRunner()
        self.repo = repository(bug=False)

    def sent(self, build_prefix):
        return [r for r in self.runner.requests if r['build_id'].startswith(build_prefix)]

    def assertSingleLineScriptFile(self, req, name):
        argv = req['argv']
        self.assertEqual(argv[:2], ['python', f'.omni/_sandbox/{name}.py'], argv)
        self.assertNotIn('-c', argv)
        for arg in argv:
            self.assertNotIn('\n', arg)
        self.assertIn(argv[1], req['repository'])                    # the script travels in the snapshot

    def test_preview_smoke(self):
        repo = dict(self.repo)   # the smoke test refuses placeholder pages (< 400 chars): give it a real interface
        small = '<h1>Bookings</h1><form><input name=n><button>Add</button></form>'
        rows = ''.join(f'<tr><td>booking {i}</td><td>2026-10-{i:02d}</td><td><button>cancel</button></td></tr>' for i in range(1, 9))
        repo['app.py'] = repo['app.py'].replace(small, small + '<table><tr><th>name</th><th>date</th><th></th></tr>' + rows + '</table>')
        self.assertNotEqual(repo['app.py'], self.repo['app.py'])
        ex = PreviewReadyExecutor(Inner(self.runner))
        report = ex.execute(repository=repo, spec=SPEC)
        self.assertNotIn('invalid command arguments', json.dumps(ex.last_smoke))
        [req] = self.sent('preview-smoke')
        self.assertSingleLineScriptFile(req, 'preview_smoke')
        self.assertEqual(ex.last_smoke, {'status': 'PASS'}, report)   # it really ran as a file and passed

    def test_browser_probe(self):
        ex = BrowserFlowExecutor(Inner(self.runner))
        ex.execute(repository=self.repo, spec=SPEC)
        self.assertEqual(ex.last_probe.get('status'), 'passed', ex.last_probe)
        [req] = self.sent('browser-probe')
        self.assertEqual(req['profile'], BROWSER_PROFILE)
        self.assertSingleLineScriptFile(req, 'browser_probe')

    def test_behavior_acceptance(self):
        ex = BehaviorAcceptanceExecutor(Inner(self.runner))
        ex.scope = NO_LOGIN_SCOPE
        report = ex.execute(repository=self.repo, spec=SPEC)
        [req] = self.sent('behavior-acceptance')
        self.assertSingleLineScriptFile(req, 'behavior_acceptance')
        self.assertIn('.omni/_behavior_run.json', req['repository'])
        self.assertEqual((ex.last_report or {}).get('status'), 'PASS', (ex.last_report, report))

    def test_visual_qa(self):
        ex = VisualQAExecutor(Inner(self.runner))
        ex.execute(repository=self.repo, spec=SPEC)
        reqs = self.sent('visual-')
        self.assertEqual(sorted(r['argv'][-1] for r in reqs), ['desktop', 'mobile'])
        for req in reqs:
            self.assertSingleLineScriptFile(req, 'visual_qa')
        self.assertNotEqual(ex.last_visual.get('status'), 'NOT_RUN', ex.last_visual)

    def test_the_product_repository_itself_is_not_changed(self):
        before = dict(self.repo)
        PreviewReadyExecutor(Inner(self.runner)).execute(repository=self.repo, spec=SPEC)
        self.assertEqual(self.repo, before)


if __name__ == '__main__':
    unittest.main()
