"""Worker deploy: drain every consumer, fail closed on 137/OOM/failed stop, restore the previous consumers, never touch
data. Runs the real shell scripts against a fake `docker` on PATH (no Docker, no network, no spend)."""
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'infra' / 'worker-host'
SERVICES = ('worker', 'intake-worker', 'intake-maintain', 'preview-worker')

FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
st = os.environ['FAKE_STATE']; log = open(os.path.join(st, 'calls.log'), 'a'); log.write(' '.join(a) + '\n'); log.close()
cfg = json.load(open(os.path.join(st, 'cfg.json')))
stopped = os.path.exists(os.path.join(st, 'stopped'))
if a[:2] == ['compose', 'ps'] and '-q' in a:
    svc = a[-1]
    if svc in cfg.get('services', []): print('cid-' + svc)
    sys.exit(0)
if a[0] == 'inspect':
    fmt, cid = a[2], a[3]; svc = cid[4:]
    if fmt == '{{.Image}}': print('sha256:img-' + svc)
    elif fmt == '{{.State.Running}}': print('false' if stopped else 'true')
    else:
        e = cfg.get('exit', {}).get(svc, 0); o = cfg.get('oom', {}).get(svc, False)
        print(('true' if cfg.get('still_running') == svc else 'false'), e, 'true' if o else 'false')
    sys.exit(0)
if a[0] == 'tag': sys.exit(0)
if a[:2] == ['image', 'inspect']: sys.exit(0 if not cfg.get('no_rollback_image') else 1)
if a[:2] == ['compose', 'stop']:
    open(os.path.join(st, 'stopped'), 'w').close(); sys.exit(cfg.get('stop_rc', 0))
if 'up' in a:
    sys.exit(cfg.get('up_rc', 0))
sys.exit(0)
'''


def run(script, cfg):
    tmp = tempfile.mkdtemp()
    bindir = Path(tmp) / 'bin'
    bindir.mkdir()
    state = Path(tmp) / 'fake'
    state.mkdir()
    docker = bindir / 'docker'
    docker.write_text(FAKE_DOCKER)
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    (state / 'cfg.json').write_text(json.dumps(cfg))
    deploy = Path(tmp) / 'deploy-state'
    env = {**os.environ, 'PATH': f'{bindir}:{os.environ["PATH"]}', 'FAKE_STATE': str(state),
           'DEPLOY_STATE_DIR': str(deploy), 'DRAIN_DEADLINE_SECONDS': '5', 'RECOVER_WAIT_TRIES': '1'}
    return (subprocess.run(['bash', str(HOST / script)], env=env, capture_output=True, text=True, timeout=60),
            state / 'calls.log', deploy)


class DrainTests(unittest.TestCase):
    def test_clean_drain_stops_all_four_consumers_and_records_images(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stop = [l for l in log.read_text().splitlines() if l.startswith('compose stop')][0]
        for s in SERVICES:
            self.assertIn(s, stop)
        self.assertEqual(len((st / 'prev-images').read_text().splitlines()), 4)
        self.assertFalse((st / 'drain-failed').exists())

    def test_exit_137_oom_or_failed_stop_fail_the_deploy(self):
        for cfg, text in (({'exit': {'worker': 137}}, '137'), ({'oom': {'preview-worker': True}}, 'OOM'),
                          ({'stop_rc': 1}, 'exited 1'), ({'still_running': 'intake-worker'}, 'still running')):
            r, log, st = run('drain.sh', {'services': list(SERVICES), **cfg})
            self.assertEqual(r.returncode, 1, (cfg, r.stdout))
            self.assertIn(text, (st / 'drain-failed').read_text())
            self.assertIn('::error title=drain', r.stdout)

    def test_a_host_with_no_previous_consumers_still_drains(self):
        r, log, st = run('drain.sh', {'services': []})
        self.assertEqual(r.returncode, 0, r.stdout)


class RecoverTests(unittest.TestCase):
    def prepare(self, cfg):
        r, log, st = run('drain.sh', {'services': list(SERVICES), **cfg})
        return st

    def test_recover_restarts_previous_images_without_touching_data(self):
        tmp = tempfile.mkdtemp()
        # same fake docker, reuse the drain state directory
        r, log, st = run('drain.sh', {'services': list(SERVICES), 'exit': {'worker': 137}})
        self.assertEqual(r.returncode, 1)
        bindir = log.parent.parent / 'bin'
        env = {**os.environ, 'PATH': f'{bindir}:{os.environ["PATH"]}', 'FAKE_STATE': str(log.parent), 'DEPLOY_STATE_DIR': str(st), 'RECOVER_WAIT_TRIES': '1'}
        rr = subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(rr.returncode, 0, rr.stdout + rr.stderr)
        calls = log.read_text()
        up = [l for l in calls.splitlines() if ' up ' in l][0]
        self.assertIn('--no-build', up)
        for s in SERVICES:
            self.assertIn(s, up)
        override = yaml.safe_load((st / 'rollback.yml').read_text())
        self.assertEqual(override['services']['worker']['image'], 'omni-rollback/worker:prev')
        for forbidden in (' down', ' -v', 'prune', ' rm ', 'volume'):
            self.assertNotIn(forbidden, calls)
        self.assertIn('::warning title=recover', rr.stdout)

    def test_nothing_to_restore_is_not_an_error_and_missing_images_are(self):
        tmp = Path(tempfile.mkdtemp())
        env = {**os.environ, 'DEPLOY_STATE_DIR': str(tmp)}
        self.assertEqual(subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True).returncode, 0)
        r, log, st = run('drain.sh', {'services': list(SERVICES), 'no_rollback_image': True})
        bindir = log.parent.parent / 'bin'
        env = {**os.environ, 'PATH': f'{bindir}:{os.environ["PATH"]}', 'FAKE_STATE': str(log.parent), 'DEPLOY_STATE_DIR': str(st), 'RECOVER_WAIT_TRIES': '1'}
        rr = subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True)
        self.assertEqual(rr.returncode, 1)
        self.assertIn('::error title=recover', rr.stdout)


class WorkflowWiringTests(unittest.TestCase):
    def setUp(self):
        self.wf = yaml.safe_load((ROOT / '.github/workflows/deploy-worker.yml').read_text())
        self.steps = self.wf['jobs']['deploy']['steps']

    def test_drain_runs_the_script_before_migrations_and_recovery_covers_each_failure_point(self):
        ids = [s.get('id') for s in self.steps]
        self.assertLess(ids.index('drain'), ids.index('migrate'))
        self.assertLess(ids.index('migrate'), ids.index('start'))
        drain = self.steps[ids.index('drain')]
        self.assertIn('drain.sh', drain['run'])
        rec = [s for s in self.steps if 'recover.sh' in s.get('run', '')][0]
        for sid in ('drain', 'migrate', 'start', 'listen'):
            self.assertIn(f"steps.{sid}.outcome == 'failure'", rec['if'])
        self.assertTrue(rec['if'].lstrip('${{ ').startswith('failure()'))
        self.assertIn('DEPLOY_STATE_DIR', self.wf['jobs']['deploy']['env'])

    def test_every_queue_consumer_service_is_drained(self):
        compose = yaml.safe_load((HOST / 'docker-compose.yml').read_text())['services']
        consumers = {n for n, s in compose.items() if 'omni_prod.worker' in ' '.join(s.get('command', []))
                     or 'reservation_worker' in ' '.join(s.get('command', []))}
        self.assertTrue(consumers <= set(SERVICES), consumers - set(SERVICES))
        script = (HOST / 'drain.sh').read_text()
        for s in consumers:
            self.assertIn(s, script)


class BackupSchedulerTests(unittest.TestCase):
    def test_scheduler_dispatches_the_milestone_workflow_and_checks_freshness(self):
        text = (ROOT / 'infra/backup-scheduler/backup-scheduler.yml').read_text()
        d = yaml.safe_load(text)
        self.assertEqual(d[True]['schedule'][0]['cron'], '17 2 * * *')
        self.assertEqual(d['permissions']['actions'], 'write')
        self.assertIn('gh workflow run "$TARGET_WORKFLOW"', text)
        self.assertIn('--ref "$TARGET_REF"', text)
        self.assertIn('backup-stale', text)
        # the real workflow must exist on the target ref and must be dispatchable
        backup = yaml.safe_load((ROOT / '.github/workflows/backup-restore.yml').read_text())
        self.assertIn('workflow_dispatch', backup[True])
        self.assertEqual(d['env']['TARGET_WORKFLOW'], 'backup-restore.yml')
        # inactive on this branch: it is not under .github/workflows
        self.assertFalse((ROOT / '.github/workflows/backup-scheduler.yml').exists())


if __name__ == '__main__':
    unittest.main()
