"""The CI status snapshot is never pushed to main (Michael 2026-11-15).

Main was protected, so the scheduled 'refresh' job of repo-control-health-status.yml failed on every run since
2026-10-25 at "git push origin HEAD:main" (GH006); main carried a permanently red check. Real inputs: the workflow file
itself, and the snapshot script run on the real API response for main of 2026-11-15
(tests/fixtures/main_runs_2026_11_15.json)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows' / 'repo-control-health-status.yml'
FIXTURE = ROOT / 'tests' / 'fixtures' / 'main_runs_2026_11_15.json'


def run_snapshot(**env):
    base = {k: v for k, v in os.environ.items() if k not in ('GITHUB_STEP_SUMMARY', 'CI_STATUS_OUT')}
    base.update({'GH_REPO': 'Shayfly/desktop-tutorial', 'GH_TOKEN': 'unused', 'CI_STATUS_HEAD': 'e32f332f2bf6',
                 'CI_STATUS_RUNS_JSON': str(FIXTURE), 'HEALTH_HTTP_CODE': '200'})
    base.update(env)
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'ci_status_snapshot.py')], cwd=tempfile.mkdtemp(),
                          env=base, capture_output=True, text=True)


class NeverPushedToMain(unittest.TestCase):
    def test_the_workflow_cannot_write_to_the_repository(self):
        wf = yaml.safe_load(WF.read_text())
        self.assertEqual(wf['permissions']['contents'], 'read')
        steps = wf['jobs']['refresh']['steps']
        self.assertFalse(any('git push' in (s.get('run') or '') or 'git commit' in (s.get('run') or '') for s in steps))
        self.assertFalse(steps[0]['with']['persist-credentials'])

    def test_the_snapshot_goes_to_the_summary_and_one_annotation_per_workflow(self):
        out = Path(tempfile.mkdtemp()) / 'summary.md'
        p = run_snapshot(CI_STATUS_OUT=str(out))
        self.assertEqual(p.returncode, 0, p.stderr)
        text = out.read_text(encoding='utf-8')
        self.assertIn('**main SHA at snapshot:** e32f332f2bf6', text)
        runs = json.loads(FIXTURE.read_text())['workflow_runs']
        names = {r['name'] for r in runs} - {'Repo Control Health and CI Status'}
        for name in names:
            self.assertIn(f'title=main {name[:60]}::', p.stdout)
            self.assertIn(f'| {name.replace("|", "/")[:80]} |', text)
        self.assertNotIn('title=main Repo Control Health and CI Status', p.stdout)
        failing = {r['name'] for r in runs if r['conclusion'] == 'failure'} & names
        latest = {}
        for r in runs:
            latest.setdefault(r['name'], r)
        for name in names:
            level = 'warning' if latest[name]['conclusion'] == 'failure' else 'notice'
            self.assertIn(f'::{level} title=main {name[:60]}::', p.stdout)
        self.assertFalse((Path(p.args[1]).parent / 'CI_STATUS.md').exists())
        from tests.evidence_notice import notice
        notice('ci status snapshot', f'{len(names)} workflows to the summary; failing on main now: {sorted(failing)}')

    def test_a_red_workflow_on_main_is_a_warning(self):
        # the same API response with the newest 'Backup and restore test' run turned red (no run is red at capture)
        data = json.loads(FIXTURE.read_text())
        newest = next(r for r in data['workflow_runs'] if r['name'] == 'Backup and restore test')
        newest['conclusion'] = 'failure'
        path = Path(tempfile.mkdtemp()) / 'runs.json'
        path.write_text(json.dumps(data))
        p = run_snapshot(CI_STATUS_OUT=str(Path(tempfile.mkdtemp()) / 's.md'), CI_STATUS_RUNS_JSON=str(path))
        self.assertIn(f"::warning title=main Backup and restore test::run {newest['id']}", p.stdout)

    def test_without_a_summary_it_fails_loudly_and_writes_no_file(self):
        cwd = tempfile.mkdtemp()
        p = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'ci_status_snapshot.py')], cwd=cwd,
                           env={**{k: v for k, v in os.environ.items() if k not in ('GITHUB_STEP_SUMMARY', 'CI_STATUS_OUT')},
                                'GH_REPO': 'x/y', 'GH_TOKEN': 't', 'CI_STATUS_HEAD': 'h',
                                'CI_STATUS_RUNS_JSON': str(FIXTURE)}, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('never committed to main', p.stdout + p.stderr)
        self.assertFalse((Path(cwd) / 'CI_STATUS.md').exists())


if __name__ == '__main__':
    unittest.main()
