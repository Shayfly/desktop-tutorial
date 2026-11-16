"""Warehouse 111, the worker half (owner 2026-11-16): the build worker is deployed only on a release.

Real path: scripts/release_gate.py is run as the workflow runs it (a subprocess with GITHUB_EVENT_NAME, a real event
JSON file and a GITHUB_OUTPUT file), and the deploy job of .github/workflows/deploy-worker.yml is read to prove it
depends on that output. Acceptance (owner): a push without [release] -> the worker is not deployed; with -> deployed."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'release_gate.py'
WF = ROOT / '.github' / 'workflows' / 'deploy-worker.yml'


def gate(event, message=''):
    with tempfile.TemporaryDirectory() as tmp:
        ev, out = Path(tmp) / 'event.json', Path(tmp) / 'out'
        ev.write_text(json.dumps({'head_commit': {'message': message}}))
        out.write_text('')
        env = {k: v for k, v in os.environ.items() if not k.startswith('GITHUB_')}
        env.update(GITHUB_EVENT_NAME=event, GITHUB_EVENT_PATH=str(ev), GITHUB_OUTPUT=str(out))
        p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env, timeout=30)
        return p.returncode, p.stdout, out.read_text()


class TheGate(unittest.TestCase):
    def test_a_push_without_the_marker_is_not_deployed_and_says_so(self):
        code, out, written = gate('push', 'Merge pull request #409 from x/y')
        self.assertEqual((code, written), (0, 'release=false\n'))
        self.assertIn('::notice title=release gate::SKIP', out)
        self.assertIn('NOT deployed', out)

    def test_a_push_with_the_marker_is_deployed(self):
        for message in ('Merge pull request #406 from x/y [release]', 'title [release]\n\nbody'):
            with self.subTest(message):
                code, out, written = gate('push', message)
                self.assertEqual((code, written), (0, 'release=true\n'))
                self.assertIn('RELEASE', out)

    def test_the_mark_counts_only_at_the_end_of_the_title_line(self):
        # 2026-11-16: #413's merge (c38fbb4) deployed the worker because its body quoted a title mentioning the mark
        m413 = ('Merge pull request #413: warehouse 111 completed, the worker deploys only on a release\n\n'
                'warehouse 111 completed: the build worker deploys only on a release ([release] or a manual run)')
        for message in (m413, 'title\n\nbody [release]', 'about the [release] rule', '[release] at the start'):
            with self.subTest(message[:30]):
                self.assertEqual(gate('push', message)[2], 'release=false\n')

    def test_a_manual_run_is_a_release(self):
        self.assertEqual(gate('workflow_dispatch')[2], 'release=true\n')

    def test_an_unknown_event_fails_loudly(self):
        code, out, written = gate('pull_request', '[release]')
        self.assertEqual((code, written), (2, ''))
        self.assertIn('::error title=release gate::', out)


class TheWorkflowObeysIt(unittest.TestCase):
    def test_the_deploy_job_runs_only_on_a_release(self):
        wf = yaml.safe_load(WF.read_text(encoding='utf-8'))
        gate_job, deploy = wf['jobs']['release-gate'], wf['jobs']['deploy']
        self.assertEqual(deploy['needs'], 'release-gate')
        self.assertEqual(deploy['if'], "needs.release-gate.outputs.release == 'true'")
        self.assertEqual(gate_job['outputs']['release'], '${{ steps.gate.outputs.release }}')
        self.assertIn('python3 scripts/release_gate.py', [s.get('run', '') for s in gate_job['steps']])

    def test_the_frozen_browser_probe_step_is_untouched(self):
        names = [s.get('name', '') for s in yaml.safe_load(WF.read_text(encoding='utf-8'))['jobs']['deploy']['steps']]
        self.assertIn('Prove the browser sandbox clicks through a product', names)


if __name__ == '__main__':
    unittest.main()
