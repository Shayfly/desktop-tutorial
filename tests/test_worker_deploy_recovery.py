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
upped = os.path.exists(os.path.join(st, 'upped'))
is_compose = a[0] == 'compose'
if is_compose and 'ps' in a and '-q' in a:
    svc = a[-1]
    if cfg.get('ps_rc'): sys.exit(cfg['ps_rc'])
    if svc in cfg.get('services', []): print('cid-' + svc)
    sys.exit(0)
if a[0] == 'inspect':
    fmt, cid = a[2], a[3]; svc = cid[4:]
    if svc in cfg.get('inspect_fails', []) and fmt == '{{.Image}}': sys.exit(1)
    if fmt == '{{.Image}}': print('sha256:img-' + svc)
    elif fmt == '{{.State.Running}}':
        if upped: print('false' if svc in cfg.get('not_running_after_up', []) else 'true')
        else: print('false' if stopped else 'true')
    else:
        e = cfg.get('exit', {}).get(svc, 0); o = cfg.get('oom', {}).get(svc, False)
        print(('true' if cfg.get('still_running') == svc else 'false'), e, 'true' if o else 'false')
    sys.exit(0)
if a[0] == 'tag':
    sys.exit(1 if a[2].split('/')[1].split(':')[0] in cfg.get('tag_fails', []) else 0)
if a[:2] == ['image', 'inspect']:
    svc = a[2].split('/')[1].split(':')[0]
    sys.exit(1 if (cfg.get('no_rollback_image') or svc in cfg.get('missing_images', [])) else 0)
if a[:2] == ['compose', 'stop']:
    open(os.path.join(st, 'stopped'), 'w').close(); sys.exit(cfg.get('stop_rc', 0))
if is_compose and 'up' in a:
    open(os.path.join(st, 'upped'), 'w').close(); sys.exit(cfg.get('up_rc', 0))
if is_compose and 'logs' in a:
    if not cfg.get('no_listen'): print('worker | Listening on omni-builds')
    sys.exit(0)
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
           'DEPLOY_STATE_DIR': str(deploy), 'DRAIN_DEADLINE_SECONDS': '5', 'RECOVER_WAIT_TRIES': '1', 'RECOVER_WAIT_SLEEP': '0'}
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
        env = {**os.environ, 'PATH': f'{bindir}:{os.environ["PATH"]}', 'FAKE_STATE': str(log.parent), 'DEPLOY_STATE_DIR': str(st), 'RECOVER_WAIT_TRIES': '1', 'RECOVER_WAIT_SLEEP': '0'}
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
        env = {**os.environ, 'PATH': f'{bindir}:{os.environ["PATH"]}', 'FAKE_STATE': str(log.parent), 'DEPLOY_STATE_DIR': str(st), 'RECOVER_WAIT_TRIES': '1', 'RECOVER_WAIT_SLEEP': '0'}
        rr = subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True)
        self.assertEqual(rr.returncode, 1)
        self.assertIn('::error title=recover', rr.stdout)


def recover(log, st):
    bindir = log.parent.parent / 'bin'
    env = {**os.environ, 'PATH': f'{bindir}:{os.environ["PATH"]}', 'FAKE_STATE': str(log.parent), 'DEPLOY_STATE_DIR': str(st),
           'RECOVER_WAIT_TRIES': '1', 'RECOVER_WAIT_SLEEP': '0'}
    return subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True, timeout=60)


class ReviewFindingRegressionTests(unittest.TestCase):
    """Review findings 2026-10-11: each of these passed (or was not covered) before the fix."""

    def test_an_existing_consumer_that_cannot_be_inspected_or_tagged_blocks_the_drain(self):
        for cfg, text in (({'inspect_fails': ['intake-worker']}, 'cannot inspect the image of intake-worker'),
                          ({'tag_fails': ['worker']}, 'cannot save a rollback image for worker'),
                          ({'ps_rc': 1}, 'cannot list container')):
            r, log, st = run('drain.sh', {'services': list(SERVICES), **cfg})
            self.assertEqual(r.returncode, 1, (cfg, r.stdout))
            self.assertIn(text, (st / 'drain-failed').read_text())
            self.assertNotIn('compose stop', log.read_text(), 'nothing may be stopped when no rollback is possible')

    def test_recovery_fails_when_a_recorded_service_has_no_rollback_image_but_restores_the_rest(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES), 'exit': {'worker': 137}})
        # image of one service disappears between drain and recovery
        cfg = json.loads((log.parent / 'cfg.json').read_text())
        (log.parent / 'cfg.json').write_text(json.dumps({**cfg, 'missing_images': ['intake-maintain']}))
        rr = recover(log, st)
        self.assertEqual(rr.returncode, 1, rr.stdout)
        self.assertIn('no rollback image for: intake-maintain', rr.stdout)
        up = [l for l in log.read_text().splitlines() if ' up ' in l][0]
        self.assertIn('worker', up)                                  # the others are still restored
        self.assertNotIn('intake-maintain', up)

    def test_recovery_fails_when_a_service_does_not_come_back_or_the_worker_is_not_listening(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES)})
        cfg = json.loads((log.parent / 'cfg.json').read_text())
        (log.parent / 'cfg.json').write_text(json.dumps({**cfg, 'not_running_after_up': ['preview-worker']}))
        rr = recover(log, st)
        self.assertEqual(rr.returncode, 1, rr.stdout)
        self.assertIn('preview-worker is not running after recovery', rr.stdout)
        r, log, st = run('drain.sh', {'services': list(SERVICES)})
        cfg = json.loads((log.parent / 'cfg.json').read_text())
        (log.parent / 'cfg.json').write_text(json.dumps({**cfg, 'no_listen': True}))
        rr = recover(log, st)
        self.assertEqual(rr.returncode, 1)
        self.assertIn('not listening on its queue', rr.stdout)

    def test_recovery_up_failure_is_a_failure(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES)})
        cfg = json.loads((log.parent / 'cfg.json').read_text())
        (log.parent / 'cfg.json').write_text(json.dumps({**cfg, 'up_rc': 1}))
        self.assertEqual(recover(log, st).returncode, 1)

    def test_a_full_recovery_succeeds_and_says_so(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES)})
        rr = recover(log, st)
        self.assertEqual(rr.returncode, 0, rr.stdout)
        self.assertIn('restored and running', rr.stdout)


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
    def setUp(self):
        self.text = (ROOT / 'infra/backup-scheduler/backup-scheduler.yml').read_text()
        self.d = yaml.safe_load(self.text)

    def test_scheduler_targets_the_real_dispatchable_workflow_and_is_not_active_here(self):
        self.assertEqual(self.d[True]['schedule'][0]['cron'], '17 2 * * *')
        self.assertEqual(self.d['permissions']['actions'], 'write')
        backup = yaml.safe_load((ROOT / '.github/workflows/backup-restore.yml').read_text())
        self.assertIn('workflow_dispatch', backup[True])
        self.assertEqual(self.d['env']['TARGET_WORKFLOW'], 'backup-restore.yml')
        self.assertFalse((ROOT / '.github/workflows/backup-scheduler.yml').exists())
        self.assertIn('NOT ACTIVE', self.text.splitlines()[0])

    def test_dispatch_is_not_success_the_new_run_must_start_and_succeed(self):
        steps = {s['name']: s for s in self.d['jobs']['dispatch-and-verify']['steps']}
        self.assertGreaterEqual(self.d['jobs']['dispatch-and-verify']['timeout-minutes'], 45)
        wait = [s for n, s in steps.items() if 'NEW run' in n][0]['run']
        self.assertIn('--event workflow_dispatch', wait)
        self.assertIn('select(.createdAt >= ', wait)                  # only a run created after the dispatch counts
        self.assertIn('gh run watch "$run_id"', wait)
        self.assertIn('--exit-status', wait)
        self.assertIn('backup-not-started', wait)
        self.assertIn('backup-failed', wait)
        dispatch = [s for n, s in steps.items() if n.startswith('Dispatch')][0]['run']
        self.assertIn('DISPATCHED (not yet a backup)', dispatch)
        self.assertNotIn('backup-succeeded', dispatch)
        # an older success is context only: it never decides the outcome
        prev = [s for n, s in steps.items() if n.startswith('Previous')][0]['run']
        self.assertNotIn('exit 1', prev)

    def test_nothing_presents_the_scheduler_as_running(self):
        readme = (ROOT / 'infra/backup-scheduler/README_HE.md').read_text()
        self.assertIn('לא הותקן ולא פעיל', readme)
        self.assertIn('לא מאומת', readme)
        self.assertIn('default branch אינו מוצע', readme)


if __name__ == '__main__':
    unittest.main()
