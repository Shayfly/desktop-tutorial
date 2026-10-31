"""Run the actual cron shell step; only the remote HTTP transport is replaced."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class AgentLoopWorkflowTests(unittest.TestCase):
    def run_retarget(self, payload, curl_exit=0):
        workflow = yaml.safe_load((ROOT / '.github/workflows/agent-loop.yml').read_text())
        step = next(s for s in workflow['jobs']['loop']['steps'] if s.get('name') == 'retarget stale bases')
        command = step['run'].replace('${{ secrets.SERVICE_TOKEN }}', 'test-service-credential')
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            curl = base / 'curl'
            curl.write_text('#!/bin/sh\ncat "$TEST_RESPONSE"\nexit "$TEST_CURL_EXIT"\n')
            curl.chmod(0o700)
            response = base / 'response.json'
            response.write_text(json.dumps(payload) if not isinstance(payload, str) else payload)
            summary = base / 'summary.md'
            env = dict(os.environ, PATH=directory + os.pathsep + os.environ['PATH'],
                       TEST_RESPONSE=str(response), TEST_CURL_EXIT=str(curl_exit),
                       GITHUB_STEP_SUMMARY=str(summary), SERVICE_TOKEN='test-service-credential')
            proc = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', command],
                                  cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
            return proc, summary.read_text() if summary.exists() else ''

    def test_all_ten_retarget_failures_fail_the_real_step_and_reach_summary(self):
        actions = [f'{n} retarget old/base -> fail' for n in range(10)]
        proc, summary = self.run_retarget({'ok': True, 'op': 'retarget', 'count': 10, 'actions': actions})
        self.assertNotEqual(proc.returncode, 0)
        for action in actions:
            self.assertIn(action, summary)

    def test_one_failed_action_among_successes_also_fails(self):
        proc, summary = self.run_retarget({'ok': True, 'op': 'retarget', 'count': 2,
                                          'actions': ['1 retarget old -> ok', '2 retarget old -> fail']})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('2 retarget old -> fail', summary)

    def test_success_and_no_work_pass(self):
        for actions in ([], ['1 retarget fix/fail-label -> ok'],
                        ['1 retarget old -> skip contained in main', '2 retarget old -> skip no commits between']):
            with self.subTest(actions=actions):
                proc, summary = self.run_retarget({'ok': True, 'op': 'retarget', 'count': len(actions), 'actions': actions})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn('PASS', summary)

    def test_bad_payload_http_error_and_wrong_operation_fail(self):
        for payload, curl_exit in [('not json', 0), ({'ok': False}, 22),
                                   ({'ok': True, 'op': 'sweep', 'count': 0, 'actions': []}, 0),
                                   ({'ok': True, 'op': 'retarget', 'count': 1, 'actions': []}, 0)]:
            with self.subTest(payload=payload):
                proc, summary = self.run_retarget(payload, curl_exit)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('FAIL', summary)


if __name__ == '__main__':
    unittest.main()
