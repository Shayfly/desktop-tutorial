"""Worker deploy: drain every consumer, fail closed on 137/OOM/failed stop, restore the previous consumers, never touch
data. Runs the real shell scripts against a fake `docker` on PATH (no Docker, no network, no spend)."""
import json
import os
import stat
import subprocess
import sys
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
    svc = a[-1].split('/')[1].split(':')[0]
    if cfg.get('no_rollback_image') or svc in cfg.get('missing_images', []): sys.exit(1)
    if '-f' in a: print(cfg.get('rollback_label', {}).get(svc, ''))
    sys.exit(0)
if a[0] == 'exec':
    svc = a[1][4:]
    if svc in cfg.get('exec_fails', []): sys.exit(1)
    print(cfg.get('running_hash', {}).get(svc, '')); sys.exit(0)
if a[0] == 'run':
    ref = next(x for x in a if x.startswith('omni-rollback/')); svc = ref.split('/')[1].split(':')[0]
    print(cfg.get('image_hash', {}).get(svc, '')); sys.exit(0)
if a[:2] == ['compose', 'stop']:
    open(os.path.join(st, 'stopped'), 'w').close(); sys.exit(cfg.get('stop_rc', 0))
if is_compose and 'up' in a:
    open(os.path.join(st, 'upped'), 'w').close(); sys.exit(cfg.get('up_rc', 0))
if is_compose and 'logs' in a:
    if not cfg.get('no_listen'): print('worker | Listening on omni-builds')
    sys.exit(0)
sys.exit(0)
'''


def run(script, cfg, extra_env=None):
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
           'DEPLOY_STATE_DIR': str(deploy), 'DRAIN_DEADLINE_SECONDS': '5', 'RECOVER_WAIT_TRIES': '1', 'RECOVER_WAIT_SLEEP': '0', **(extra_env or {})}
    return (subprocess.run(['bash', str(HOST / script)], env=env, capture_output=True, text=True, timeout=60),
            state / 'calls.log', deploy)


class DrainTests(unittest.TestCase):
    def test_clean_drain_stops_all_four_consumers_and_records_images(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stop = ' '.join(l for l in log.read_text().splitlines() if l.startswith('compose stop'))   # maintain first, then the rest
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
        # The `runner` context does not exist at job level (GitHub rejects the whole file); the scripts default to
        # $RUNNER_TEMP/deploy-state, which every step of the job shares.
        self.assertNotIn('runner.', str(self.wf['jobs']['deploy'].get('env', {})))
        self.assertIn('RUNNER_TEMP', (HOST / 'drain.sh').read_text())
        self.assertIn('RUNNER_TEMP', (HOST / 'recover.sh').read_text())

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



def gate_stub(codes):
    """A stand-in for the gate command: returns the exit codes in order (the last one repeats)."""
    d = Path(tempfile.mkdtemp())
    (d / 'codes').write_text(' '.join(str(c) for c in codes))
    (d / 'n').write_text('0')
    stub = d / 'gate.sh'
    stub.write_text('#!/usr/bin/env bash\nn=$(cat "%s/n"); read -ra c < "%s/codes"\n'
                    'echo $((n+1)) > "%s/n"; echo "$n $*" >> "%s/args"\n'
                    'i=$n; [ "$i" -lt "${#c[@]}" ] || i=$((${#c[@]}-1)); exit "${c[$i]}"\n' % ((d,) * 4))
    return f'bash {stub}', d


class GateInDrainTests(unittest.TestCase):
    """The race between the workflow's idle gate and the stop, and every way the gate can fail."""

    def drain(self, codes, **cfg):
        cmd, d = gate_stub(codes)
        r, log, st = run('drain.sh', {'services': list(SERVICES), **cfg}, {'ACTIVE_JOBS_CMD': cmd})
        return r, log, st, d

    def test_quiet_before_and_after_is_a_clean_drain_that_checks_twice(self):
        r, log, st, d = self.drain([0, 0])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual((d / 'n').read_text().strip(), '2')                    # before AND after the stop
        self.assertIn('--wait-minutes 0', (d / 'args').read_text())

    def test_running_work_or_an_unverifiable_state_before_the_stop_refuses_without_stopping_anything(self):
        for code, text in ((3, 'running work appeared'), (2, 'could not verify'), (1, 'could not verify'), (127, 'could not verify')):
            r, log, st, d = self.drain([code])
            self.assertEqual(r.returncode, 1, (code, r.stdout))
            self.assertNotIn('compose stop', log.read_text())                   # nothing was stopped
            self.assertIn(text, (st / 'drain-failed').read_text())
            self.assertTrue((st / 'not-stopped').exists())
            rr = recover(log, st)                                               # and recovery must not touch anything
            self.assertEqual(rr.returncode, 0, rr.stdout)
            self.assertNotIn(' up ', log.read_text())
            self.assertIn('untouched', rr.stdout)

    def test_work_that_starts_between_the_gate_and_the_stop_fails_the_deploy_and_recovery_restores_the_workers(self):
        r, log, st, d = self.drain([0, 3])                                      # quiet at the check, running afterwards
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('compose stop', log.read_text())
        self.assertIn('still recorded as running', (st / 'drain-failed').read_text())
        self.assertFalse((st / 'not-stopped').exists())
        rr = recover(log, st)
        self.assertEqual(rr.returncode, 0, rr.stdout)
        self.assertIn(' up ', log.read_text())

    def test_a_gate_that_cannot_verify_after_the_stop_also_fails_the_deploy(self):
        r, log, st, d = self.drain([0, 2])
        self.assertEqual(r.returncode, 1)
        self.assertIn('could not verify', (st / 'drain-failed').read_text())


class _Redis:
    def __init__(self, fail=False):
        self.fail = fail

    def ping(self):
        if self.fail:
            raise ConnectionError('down')
        return True


class ActiveJobGateTests(unittest.TestCase):
    def seed(self, conn, u):
        conn.execute('DELETE FROM build_jobs')            # rolled back by the caller; isolates the snapshot
        for f in ('014_real_running_preview.sql', '037_intake_budget_reservations.sql'):      # idempotent; rolled back too
            conn.execute((ROOT / 'infra' / 'postgres' / f).read_text())
        conn.execute("UPDATE modification_requests SET status='CANCELLED' WHERE status IN ('QUEUED','RUNNING')")
        conn.execute("DELETE FROM intake_outbox"); conn.execute("DELETE FROM intake_reservation_events")
        conn.execute("DELETE FROM intake_reservation_scopes"); conn.execute("DELETE FROM intake_reservations")
        conn.execute("DELETE FROM project_previews")
        conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)', (f'a{u}', f'{u}@x.test', 'x', 'x'))
        conn.execute('INSERT INTO creator_projects (id, owner_id, title) VALUES (%s,%s,%s)', (f'p{u}', f'a{u}', 't'))

    def snap(self, conn, redis=None, **kw):
        from omni_prod import active_jobs as A
        return A.snapshot(conn, redis or _RqFree(), **kw)

    @unittest.skipUnless(os.environ.get('M4D2_DATABASE_URL'), 'BLOCKED: M4D2_DATABASE_URL (isolated PostgreSQL) not configured')
    def test_database_state_blocks_regardless_of_heartbeat_and_queued_work_does_not(self):
        import psycopg
        import uuid
        u = uuid.uuid4().hex[:8]
        with psycopg.connect(os.environ['M4D2_DATABASE_URL']) as conn:
            try:
                self.seed(conn, u)
                self.assertTrue(self.snap(conn)['safe_to_drain'])
                conn.execute("INSERT INTO build_jobs (id, project_id, status) VALUES (%s,%s,'queued')", (f'bld_q{u}', f'p{u}'))
                s = self.snap(conn)
                self.assertTrue(s['safe_to_drain'])                                 # queued work waits for the new worker
                self.assertEqual(s['queued_builds'], [f'bld_q{u}'])
                conn.execute("INSERT INTO build_jobs (id, project_id, status, heartbeat_at) VALUES (%s,%s,'running', now() - interval '2 hours')",
                             (f'bld_s{u}', f'p{u}'))
                s = self.snap(conn)
                self.assertTrue(s['busy'])                                          # an old heartbeat is NOT proof it ended
                self.assertFalse(s['safe_to_drain'])
                self.assertEqual(s['running_builds_with_old_heartbeat'], [f'bld_s{u}'])
                # only an exact, explicit operator acknowledgement releases it
                self.assertTrue(self.snap(conn, acknowledge_stale=[f'bld_s{u}'])['safe_to_drain'])
                self.assertFalse(self.snap(conn, acknowledge_stale=['bld_other'])['safe_to_drain'])
                conn.execute("INSERT INTO build_jobs (id, project_id, status, heartbeat_at) VALUES (%s,%s,'running', now())", (f'bld_r{u}', f'p{u}'))
                s = self.snap(conn, acknowledge_stale=[f'bld_s{u}'])
                self.assertEqual(s['running_builds'], [f'bld_r{u}'])
            finally:
                conn.rollback()

    @unittest.skipUnless(os.environ.get('M4D2_DATABASE_URL'), 'BLOCKED: M4D2_DATABASE_URL (isolated PostgreSQL) not configured')
    def test_intake_and_preview_consumers_are_covered(self):
        import psycopg
        import uuid
        u = uuid.uuid4().hex[:8]
        with psycopg.connect(os.environ['M4D2_DATABASE_URL']) as conn:
            try:
                self.seed(conn, u)
                for state in ('CLAIMED', 'EXECUTING'):
                    conn.execute('DELETE FROM intake_reservations')
                    conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, quoted_usd, quote, state, claim_token, lease_expires_at) "
                                 "VALUES (%s,%s,%s,%s,'production',0.01,'{}'::jsonb,%s,'t', now() - interval '1 hour')",
                                 (f'r{u}', f'k{u}', f'a{u}', f'p{u}', state))   # an EXPIRED lease still blocks
                    s = self.snap(conn)
                    self.assertEqual(s['running_intake'], [f'r{u}'], state)
                    self.assertFalse(s['safe_to_drain'])
                conn.execute('DELETE FROM intake_reservations')
                conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, quoted_usd, quote, state) "
                             "VALUES (%s,%s,%s,%s,'production',0.01,'{}'::jsonb,'RESERVED')", (f'r{u}', f'k{u}', f'a{u}', f'p{u}'))
                s = self.snap(conn)
                self.assertTrue(s['safe_to_drain'])
                self.assertEqual(s['queued_intake'], [f'r{u}'])
                conn.execute("INSERT INTO project_previews (id, project_id, version_id, status, expires_at) VALUES (%s,%s,'v','STARTING', now() + interval '1 hour')", (f'pv{u}', f'p{u}'))
                s = self.snap(conn)
                self.assertEqual(s['starting_previews'], [f'pv{u}'])
                self.assertFalse(s['safe_to_drain'])
                conn.execute("UPDATE project_previews SET status='RUNNING'")
                self.assertTrue(self.snap(conn)['safe_to_drain'])                  # a running preview container is not a consumer job
            finally:
                conn.rollback()

    @unittest.skipUnless(os.environ.get('M4D2_DATABASE_URL'), 'BLOCKED: M4D2_DATABASE_URL (isolated PostgreSQL) not configured')
    def test_missing_information_blocks_and_is_never_quiet(self):
        import psycopg
        from omni_prod import active_jobs as A
        # no DB connection
        s = A.snapshot(None, _RqFree())
        self.assertFalse(s['safe_to_drain']); self.assertTrue(s['unverified'])
        with psycopg.connect(os.environ['M4D2_DATABASE_URL']) as conn:
            try:
                for f in ('014_real_running_preview.sql', '037_intake_budget_reservations.sql'):
                    conn.execute((ROOT / 'infra' / 'postgres' / f).read_text())
                # no Redis URL / Redis down
                s = A.snapshot(conn, None)
                self.assertTrue(s['unverified']); self.assertFalse(s['safe_to_drain'])
                self.assertTrue(any('OMNI_REDIS_URL' in e for e in s['errors']))
                s = A.snapshot(conn, _Redis(fail=True))
                self.assertTrue(s['unverified']); self.assertFalse(s['safe_to_drain'])
                self.assertTrue(any(e.startswith('redis:') for e in s['errors']))
                # a table that cannot be read (here: renamed inside the rolled-back transaction)
                conn.execute('ALTER TABLE intake_reservations RENAME TO intake_reservations_x')
                s = A.snapshot(conn, _RqFree())
                self.assertTrue(s['unverified']); self.assertFalse(s['safe_to_drain'])
                self.assertTrue(any('intake_reservations' in e for e in s['errors']))
            finally:
                conn.rollback()

    def test_exit_codes_of_the_command(self):
        env = {k: v for k, v in os.environ.items() if k not in ('OMNI_DATABASE_URL', 'OMNI_REDIS_URL')}
        py = [sys.executable, '-m', 'omni_prod.active_jobs']
        r = subprocess.run(py, env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)                 # nothing configured = cannot verify
        self.assertIn('OMNI_DATABASE_URL', r.stdout)
        env['OMNI_DATABASE_URL'] = 'postgresql://postgres@127.0.0.1:1/none'      # unreachable DB
        r = subprocess.run(py, env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        r = subprocess.run(py + ['--wait-minutes', 'abc'], env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(r.returncode, 2)

    @unittest.skipUnless(os.getenv('OMNI_TEST_REDIS_URL'), 'BLOCKED: OMNI_TEST_REDIS_URL (real Redis) not configured')
    def test_real_rq_started_registry_busy_worker_and_host_queue_block(self):
        from redis import Redis
        from rq import Queue
        from rq.registry import StartedJobRegistry
        from omni_prod import active_jobs as A
        r = Redis.from_url(os.environ['OMNI_TEST_REDIS_URL'])
        r.flushdb()
        try:
            s = A.snapshot(None, r)
            self.assertEqual(s['rq_started_jobs'], [])
            for qname in ('omni-intake', 'omni-preview-host-h1', 'omni-builds'):
                q = Queue(qname, connection=r)
                reg = StartedJobRegistry(queue=q)
                r.zadd(reg.key, {'job1': 9999999999})
                s = A.snapshot(None, r)
                self.assertIn(f'{qname}:job1', s['rq_started_jobs'], qname)    # the unregistered host queue is found too
                self.assertTrue(s['busy'])
                r.delete(reg.key)
        finally:
            r.flushdb()

    def test_the_gate_runs_before_the_drain_in_the_workflow_and_again_inside_it(self):
        wf = yaml.safe_load((ROOT / '.github/workflows/deploy-worker.yml').read_text())
        ids = [s.get('id') for s in wf['jobs']['deploy']['steps']]
        self.assertLess(ids.index('idle'), ids.index('drain'))
        step = wf['jobs']['deploy']['steps'][ids.index('idle')]
        self.assertIn('omni_prod.active_jobs --wait-minutes', step['run'])
        drain = (HOST / 'drain.sh').read_text()
        self.assertEqual(drain.count('eval "$GATE_CMD'), 2)                      # before the stop and after it
        self.assertLess(drain.index('eval "$GATE_CMD'), drain.index('docker compose stop'))


class _RqFree:
    """A Redis stand-in that answers ping and holds no RQ state (the RQ part is covered with a real Redis below)."""
    def ping(self):
        return True

    def __getattr__(self, name):                       # rq calls: smembers/zrange/... -> empty
        return lambda *a, **k: []



class VerifiedExistingRollbackTests(unittest.TestCase):
    """2026-10-19: a running consumer whose image object is gone may be drained only if an existing
    omni-rollback/<svc>:prev carries a revision label and its worker_tasks.py, model_gateway.py and
    preview_router.py hash identically to the running container. Anything else refuses as before."""

    REV = '2a2bba6645bb05f4889420760f11127441a0d253'
    HASH = 'aaa bbb ccc'

    def cfg(self, **over):
        c = {'services': list(SERVICES), 'tag_fails': list(SERVICES),
             'rollback_label': {s: self.REV for s in SERVICES},
             'running_hash': {s: self.HASH for s in SERVICES}, 'image_hash': {s: self.HASH for s in SERVICES}}
        c.update(over)
        return c

    def test_verified_existing_rollback_images_allow_the_drain(self):
        r, log, st = run('drain.sh', self.cfg())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((st / 'drain-failed').exists())
        self.assertIn('compose stop', log.read_text())
        recorded = (st / 'prev-images').read_text().split('\n')
        for s in SERVICES:
            self.assertIn(f'{s} cid-{s} omni-rollback/{s}:prev', recorded)
            self.assertIn(f'{s}: its image object is gone; using the existing omni-rollback/{s}:prev (revision {self.REV}', r.stdout)
        # the image check runs offline
        self.assertIn('run --rm --network none --entrypoint python omni-rollback/worker:prev', log.read_text())

    def test_each_unverified_condition_refuses_and_stops_nothing(self):
        cases = (
            ({'rollback_label': {**{s: self.REV for s in SERVICES}, 'worker': ''}}, 'omni-rollback/worker:prev has no revision label'),
            ({'rollback_label': {**{s: self.REV for s in SERVICES}, 'worker': '<no value>'}}, 'has no revision label'),
            ({'image_hash': {**{s: self.HASH for s in SERVICES}, 'preview-worker': 'aaa bbb XXX'}},
             'omni-rollback/preview-worker:prev code differs from the running preview-worker'),
            ({'exec_fails': ['intake-worker']}, 'cannot hash the code of the running intake-worker'),
            ({'image_hash': {**{s: self.HASH for s in SERVICES}, 'intake-maintain': ''}}, 'cannot hash the code of omni-rollback/intake-maintain:prev'),
            ({'missing_images': ['worker']}, 'no existing omni-rollback/worker:prev'),
        )
        for over, text in cases:
            with self.subTest(text=text):
                r, log, st = run('drain.sh', self.cfg(**over))
                self.assertEqual(r.returncode, 1, (over, r.stdout))
                failed = (st / 'drain-failed').read_text()
                self.assertIn('cannot save a rollback image for', failed)
                self.assertIn(text, failed)
                self.assertNotIn('compose stop', log.read_text(), 'nothing may be stopped when no rollback is verified')
                self.assertEqual((st / 'prev-images').read_text(), '')

    def test_a_successful_tag_never_uses_the_fallback(self):
        r, log, st = run('drain.sh', self.cfg(tag_fails=[]))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn('its image object is gone', r.stdout)
        self.assertNotIn('exec ', log.read_text())

class TolerateUnverifiedTests(unittest.TestCase):
    """Deploy build worker #127: a DB outage made the drain gate exit 2 and killed the deploy although nothing ran.
    --tolerate-unverified (explicit, never the default) turns an unverified state into a warned quiet ONLY when every
    error is a real connection failure, classified by exception type. Configuration (a missing URL), a failed or
    missing query, and any other exception (RuntimeError, TypeError, KeyError ...) still refuse (2); running work
    still refuses (3). Without the flag nothing changes. (Matt REJECT on #136: every Redis exception was "redis:".)"""

    CONN = ['db: connection failed (OperationalError)', 'redis: ConnectionError']

    def run_main(self, snap, *flags):
        import contextlib, io
        from unittest import mock
        from omni_prod import active_jobs as A
        full = {'blocking': [], 'busy': False, 'safe_to_drain': False, 'error_kinds': [], **snap}
        full['unverified'] = bool(full.get('errors'))
        out = io.StringIO()
        with mock.patch.object(A, 'check_once', lambda ack: dict(full)), contextlib.redirect_stdout(out):
            rc = A.main(['--wait-minutes', '0', *flags])
        return rc, out.getvalue()

    def test_the_flag_turns_connection_only_unverified_into_a_warned_quiet(self):
        rc, out = self.run_main({'errors': list(self.CONN), 'error_kinds': ['connection', 'connection']},
                                '--tolerate-unverified')
        self.assertEqual(rc, 0, out)
        self.assertIn('::warning title=active-jobs::draining WITHOUT verification', out)
        self.assertIn('covers ONLY not being able to know', out)               # the relief is about knowing, only
        self.assertIn('does NOT say nothing is running', out)
        for e in self.CONN:
            self.assertIn(e, out)
        rc, out = self.run_main({'errors': [self.CONN[0]], 'error_kinds': ['connection'],
                                 'blocking': ['rq_busy_workers:w1'], 'busy': True}, '--tolerate-unverified')
        self.assertEqual(rc, 3, out)                                           # running work seen still refuses

    def test_regression_a_redis_runtime_error_stays_unverified(self):
        cases = ((['redis: RuntimeError'], ['logic']), (['redis: TypeError'], ['logic']),
                 ([self.CONN[0], 'redis: KeyError'], ['connection', 'logic']),
                 (['redis: OMNI_REDIS_URL is not set, RQ state cannot be read'], ['config']),
                 (['db: OMNI_DATABASE_URL is not set'], ['config']),
                 (['intake_reservations: UndefinedTable'], ['query']), (['gate: RuntimeError'], ['logic']),
                 (['db: connection failed (OperationalError)'], []))                # unclassified is never tolerated
        for errors, kinds in cases:
            with self.subTest(errors=errors):
                rc, out = self.run_main({'errors': errors, 'error_kinds': kinds}, '--tolerate-unverified')
                self.assertEqual(rc, 2, out)
                self.assertNotIn('::warning', out)

    def test_classification_is_by_exception_type(self):
        from omni_prod import active_jobs as A
        for exc in (ConnectionError('x'), TimeoutError('x')):
            self.assertEqual(A.classify(exc), A.CONNECTION, exc)
        for exc in (RuntimeError('x'), TypeError('x'), KeyError('x'), ValueError('x')):
            self.assertEqual(A.classify(exc), A.LOGIC, exc)
        try:
            import psycopg
        except ImportError:
            psycopg = None
        if psycopg is not None:
            self.assertEqual(A.classify(psycopg.OperationalError('down'), A.QUERY), A.CONNECTION)
            self.assertEqual(A.classify(psycopg.errors.UndefinedTable('x'), A.QUERY), A.QUERY)
            self.assertEqual(A.classify(psycopg.ProgrammingError('x'), A.QUERY), A.QUERY)

        class Boom:
            def __init__(self, exc):
                self.exc = exc

            def ping(self):
                raise self.exc
        for exc, kind in ((RuntimeError('queue scan'), A.LOGIC), (ConnectionError('refused'), A.CONNECTION)):
            s = A.snapshot(None, Boom(exc), db_error=('db: connection failed (OperationalError)', A.CONNECTION))
            self.assertEqual(s['error_kinds'], [A.CONNECTION, kind], exc)
        s = A.snapshot(None, None, db_error=('db: OMNI_DATABASE_URL is not set', A.CONFIG))
        self.assertEqual(s['error_kinds'], [A.CONFIG, A.CONFIG])               # no URL is configuration, not a failure

    def test_without_the_flag_the_behaviour_is_exactly_todays(self):
        rc, out = self.run_main({'errors': list(self.CONN), 'error_kinds': ['connection', 'connection']})
        self.assertEqual(rc, 2, out)
        self.assertIn('::error title=active-jobs::NOT draining: the state could not be verified', out)
        self.assertNotIn('::warning', out)
        rc, _ = self.run_main({'errors': [self.CONN[0]], 'error_kinds': ['connection'],
                               'blocking': ['rq_busy_workers:w1'], 'busy': True})
        self.assertEqual(rc, 2)                                                # unverified wins, as today
        self.assertEqual(self.run_main({'errors': [], 'blocking': ['running_builds:b1'], 'busy': True})[0], 3)
        self.assertEqual(self.run_main({'errors': [], 'safe_to_drain': True})[0], 0)

    def test_the_real_command_with_an_unreachable_database_and_redis(self):
        env = {k: v for k, v in os.environ.items() if k not in ('OMNI_DATABASE_URL', 'OMNI_REDIS_URL')}
        py = [sys.executable, '-m', 'omni_prod.active_jobs', '--wait-minutes', '0']
        unset = subprocess.run(py + ['--tolerate-unverified'], env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(unset.returncode, 2, unset.stdout + unset.stderr)       # missing URLs: configuration
        env['OMNI_DATABASE_URL'] = 'postgresql://postgres@127.0.0.1:1/none'
        env['OMNI_REDIS_URL'] = 'redis://127.0.0.1:1/0'
        strict = subprocess.run(py, env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
        tolerant = subprocess.run(py + ['--tolerate-unverified'], env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
        self.assertEqual(strict.returncode, 2, strict.stdout + strict.stderr)
        self.assertEqual(tolerant.returncode, 0, tolerant.stdout + tolerant.stderr)
        self.assertIn('db: connection failed (OperationalError)', tolerant.stdout)
        self.assertIn('redis: ConnectionError', tolerant.stdout)

    def test_the_workflow_passes_the_flag_only_to_the_pre_drain_gate(self):
        wf = yaml.safe_load((ROOT / '.github/workflows/deploy-worker.yml').read_text())
        steps = {s.get('id'): s for s in wf['jobs']['deploy']['steps']}
        self.assertIn('--tolerate-unverified', steps['idle']['run'])
        self.assertNotIn('--tolerate-unverified', (HOST / 'drain.sh').read_text())   # the gates inside the drain stay strict


if __name__ == '__main__':
    unittest.main()


class MaintainStoppedFirstTests(unittest.TestCase):
    """2026-10-19: intake-maintain (no jobs of its own) is stopped first with a short timeout, so an old container that
    ignores SIGTERM as PID 1 no longer holds the drain for the whole deadline."""

    def _stops(self, log):
        return [l for l in log.read_text().splitlines() if l.startswith('compose stop')]

    def test_maintain_is_stopped_first_with_a_short_timeout_then_the_rest(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES)}, {'MAINTAIN_STOP_SECONDS': '3'})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        stops = self._stops(log)
        self.assertEqual(stops[0], 'compose stop -t 3 intake-maintain')
        self.assertNotIn('intake-maintain', stops[1])
        for s in ('worker', 'intake-worker', 'preview-worker'):
            self.assertIn(s, stops[1])
        self.assertEqual(len((st / 'prev-images').read_text().splitlines()), 4)

    def test_maintain_exit_137_after_its_short_timeout_does_not_fail_the_drain(self):
        r, log, st = run('drain.sh', {'services': list(SERVICES), 'exit': {'intake-maintain': 137}})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('intake-maintain exit 137: killed after', r.stdout)

    def test_a_job_consumer_exit_137_still_fails_and_maintain_still_running_fails(self):
        for cfg, text in (({'exit': {'worker': 137, 'intake-maintain': 137}}, 'worker exit 137'),
                          ({'still_running': 'intake-maintain'}, 'intake-maintain still running')):
            r, log, st = run('drain.sh', {'services': list(SERVICES), **cfg})
            self.assertEqual(r.returncode, 1, (cfg, r.stdout))
            self.assertIn(text, (st / 'drain-failed').read_text())

    def test_a_refusal_before_the_stop_still_stops_nothing(self):
        cmd, _ = gate_stub([3])
        r, log, st = run('drain.sh', {'services': list(SERVICES)}, {'ACTIVE_JOBS_CMD': cmd})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('running work appeared', r.stdout)
        self.assertEqual(self._stops(log), [])

    def test_compose_runs_intake_maintain_under_init(self):
        svc = yaml.safe_load((HOST / 'docker-compose.yml').read_text())['services']['intake-maintain']
        self.assertIs(svc.get('init'), True)
