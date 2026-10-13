"""REAL Docker drain / recovery rehearsal (founder directive 2026-10-11, item 3).

Runs the production scripts infra/worker-host/drain.sh and recover.sh unmodified, against a real Docker engine and real
`docker compose`, with four stand-in consumers (worker, intake-worker, intake-maintain, preview-worker) that obey SIGTERM
like an RQ warm shutdown, and against an ISOLATED throw-away PostgreSQL database plus a real Redis (never the live ones).

What this proves: the script logic, signals, `compose stop -t`, exit 137, OOM kill, tagging, `up --no-build` with the
rollback override, and that every required service is running again afterwards -- on a real engine.
What it does NOT prove: the Oracle host itself, the production images, the production .env, the runner's permissions.
Those still need the GO-gated rehearsal on the real host (docs/DEPLOY_RECOVERY_REHEARSAL_HE.md).

Skipped (BLOCKED, not passed) when there is no Docker daemon, no isolated PostgreSQL (M4D2_DATABASE_URL) or no Redis
(OMNI_TEST_REDIS_URL). Fault injection around real Docker is labelled where used.
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'infra' / 'worker-host'
SERVICES = ('worker', 'intake-worker', 'intake-maintain', 'preview-worker')
BASE_IMAGE = 'omni-e2e-base'

JOB_SH = r'''#!/bin/bash
svc="$1"; ctl=/ctl
[ "${GEN:-old}" = new ] && [ -f $ctl/startfail ] && { echo "startup failure of the new image"; exit 1; }
[ "$svc" = worker ] && echo "*** Listening on omni-builds..."
term() {
  [ -f $ctl/$svc.oom ] && exec /bin/oom-allocate
  [ -f $ctl/$svc.ignore-term ] && return
  [ -f $ctl/$svc.finish-seconds ] && { read n < $ctl/$svc.finish-seconds; sleep "$n"; }
  exit 0
}
trap term TERM
# Container .State.Running can precede trap installation. A stop arriving
# during that window is ignored by PID 1 and looks like a 137 deadline kill,
# NOT an OOM. Publish readiness only after the handler is installed.
printf '1\\n' > "$ctl/$svc.ready"
while :; do sleep 1; done
'''

# Deterministic CI-only workload: allocate and TOUCH resident pages in 8 MiB
# increments until the isolated container's 64 MiB cgroup actually OOM-kills
# its PID 1. Bash string doubling can be optimized/fail in userspace instead.
# No production code or Oracle worker image uses this executable.
OOM_C = r'''#include <stdlib.h>
#include <stdint.h>
int main(void) {
    for (;;) {
        const size_t bytes = 8u * 1024u * 1024u;
        volatile unsigned char *p = (volatile unsigned char *)malloc(bytes);
        if (!p) return 42; /* Explicit failure, never fake OOM evidence */
        for (size_t i = 0; i < bytes; i += 4096u) p[i] = 0x5a;
    }
}
'''

COMPOSE = '''name: %(project)s
services:
''' + ''.join(f'''  {s}:
    image: ${{IMG:-omni-e2e-base:1}}
    command: ["/bin/bash", "/ctl/job.sh", "{s}"]
    restart: unless-stopped
    network_mode: none
    stop_grace_period: 30s
    volumes: ["%(ctl)s:/ctl"]
    mem_limit: 64m
    memswap_limit: 64m
''' for s in SERVICES)


def docker_ok():
    try:
        return subprocess.run(['docker', 'info'], capture_output=True, timeout=20).returncode == 0
    except Exception:
        return False


def sh(*cmd, env=None, cwd=None, timeout=240):
    return subprocess.run(list(cmd), env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def ensure_images():
    """Two local images built from the host's bash (no registry pull): :1 = previous release, :2 = new release."""
    if (sh('docker', 'image', 'inspect', f'{BASE_IMAGE}:1').returncode == 0
            and sh('docker', 'image', 'inspect', f'{BASE_IMAGE}:2').returncode == 0):
        probe = sh('docker', 'run', '--rm', '--network', 'none', '--entrypoint', '/bin/bash',
                   f'{BASE_IMAGE}:1', '-c', 'test -x /bin/oom-allocate')
        if probe.returncode == 0:
            return
    work = Path(tempfile.mkdtemp())
    oom_source = work / 'oom-allocate.c'
    oom_source.write_text(OOM_C)
    oom_binary = work / 'oom-allocate'
    compiler = shutil.which('cc')
    if compiler is None:
        raise RuntimeError('real OOM rehearsal requires the host C compiler')
    compile_result = sh(compiler, '-O0', '-o', str(oom_binary), str(oom_source))
    if compile_result.returncode != 0:
        raise RuntimeError('could not compile the real OOM workload')
    rootfs = work / 'rootfs'
    (rootfs / 'bin').mkdir(parents=True)
    libs = set()
    for b in ('bash', 'sleep', 'cat', 'date', 'env', 'true', str(oom_binary)):
        p = shutil.which(b)
        if p:
            shutil.copy(os.path.realpath(p), rootfs / 'bin' / b)
            for line in sh('ldd', p).stdout.splitlines():
                for tok in line.split():
                    if tok.startswith('/') and os.path.exists(tok):
                        libs.add(tok)
    for lib in libs:
        dst = rootfs / lib.lstrip('/')
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.realpath(lib), dst)
    (rootfs / 'bin' / 'sh').symlink_to('bash')
    tar = work / 'rootfs.tar'
    sh('tar', '-C', str(rootfs), '-cf', str(tar), '.')
    for tag, gen in ((1, 'old'), (2, 'new')):
        r = sh('docker', 'import', '--change', f'ENV GEN={gen}', str(tar), f'{BASE_IMAGE}:{tag}')
        assert r.returncode == 0, r.stderr


@unittest.skipUnless(docker_ok(), 'BLOCKED: no reachable Docker daemon (this test needs a real engine; nothing was simulated)')
@unittest.skipUnless(os.getenv('M4D2_DATABASE_URL'), 'BLOCKED: M4D2_DATABASE_URL (isolated PostgreSQL) not configured')
@unittest.skipUnless(os.getenv('OMNI_TEST_REDIS_URL'), 'BLOCKED: OMNI_TEST_REDIS_URL (real Redis) not configured')
class RealDockerDrainRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_images()

    def setUp(self):
        import psycopg
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        self.tmp = Path(tempfile.mkdtemp())
        self.ctl = self.tmp / 'ctl'
        self.ctl.mkdir()
        (self.ctl / 'job.sh').write_text(JOB_SH)
        self.host = self.tmp / 'host'
        self.host.mkdir()
        for f in ('drain.sh', 'recover.sh'):
            shutil.copy(HOST / f, self.host / f)
        self.project = 'e2e' + uuid.uuid4().hex[:8]
        (self.host / 'docker-compose.yml').write_text(COMPOSE % {'project': self.project, 'ctl': self.ctl})
        self.state = self.tmp / 'state'
        # isolated database with the real schema
        base = os.environ['M4D2_DATABASE_URL']
        self.admin = psycopg.connect(base, autocommit=True)
        self.db = 'e2e_' + uuid.uuid4().hex[:10]
        self.admin.execute(f'CREATE DATABASE {self.db}')
        self.db_url = base.rsplit('/', 1)[0] + '/' + self.db
        self.conn = psycopg.connect(self.db_url)
        apply_migrations(self.conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        self.redis_url = os.environ['OMNI_TEST_REDIS_URL']
        # previous release is running
        self.compose('up', '-d', env_extra={'IMG': f'{BASE_IMAGE}:1'})
        self.assertTrue(self.wait_running(SERVICES), "test consumers did not reach running")
        # A running container is not necessarily signal-ready. This is the
        # synchronization barrier for both graceful drains and real OOM tests.
        for _ in range(100):
            if all((self.ctl / (service + '.ready')).exists() for service in SERVICES):
                break
            time.sleep(0.1)
        else:
            self.fail("Docker test consumers never installed their SIGTERM handlers")
        self.before = self.snapshot()

    def tearDown(self):
        self.compose('down', '-v', '--remove-orphans', env_extra={'IMG': f'{BASE_IMAGE}:1'})   # the test's own project only
        for t in ('prev',):
            for s in SERVICES:
                sh('docker', 'rmi', '-f', f'omni-rollback/{s}:{t}')
        self.conn.close()
        self.admin.execute(f'DROP DATABASE IF EXISTS {self.db} WITH (FORCE)')
        self.admin.close()

    # ---- helpers
    def env(self, **extra):
        e = {**os.environ, 'DEPLOY_STATE_DIR': str(self.state), 'COMPOSE_PROJECT_NAME': self.project,
             'OMNI_DATABASE_URL': self.db_url, 'OMNI_REDIS_URL': self.redis_url,
             'ACTIVE_JOBS_CMD': f'{sys.executable} -m omni_prod.active_jobs',
             'PYTHONPATH': f'{ROOT}:{os.environ.get("PYTHONPATH", "")}', 'RECOVER_WAIT_TRIES': '15', 'RECOVER_WAIT_SLEEP': '1'}
        e.update(extra)
        return e

    def compose(self, *args, env_extra=None):
        return sh('docker', 'compose', *args, env=self.env(**(env_extra or {})), cwd=self.host)

    def cid(self, s):
        return self.compose('ps', '-aq', s).stdout.strip().splitlines()[:1] or ['']

    def inspect(self, cid, fmt):
        return sh('docker', 'inspect', '-f', fmt, cid).stdout.strip()

    def snapshot(self):
        out = {}
        for s in SERVICES:
            c = self.cid(s)[0]
            out[s] = {'cid': c, 'image': self.inspect(c, '{{.Image}}'), 'started': self.inspect(c, '{{.State.StartedAt}}')}
        return out

    def wait_running(self, services, tries=30):
        for _ in range(tries):
            if all(self.cid(s)[0] and self.inspect(self.cid(s)[0], '{{.State.Running}}') == 'true' for s in services):
                return True
            time.sleep(1)
        return False

    def all_running_again(self):
        return self.wait_running(SERVICES, 20)

    def drain(self, **extra):
        # Tests may select a distinct deadline; do not pass the same keyword
        # twice into env(). The normal drain deadline remains four seconds.
        deadline = extra.pop('DRAIN_DEADLINE_SECONDS', '4')
        return sh('bash', str(self.host / 'drain.sh'), env=self.env(DRAIN_DEADLINE_SECONDS=deadline, **extra), cwd=self.host, timeout=300)

    def recover(self):
        return sh('bash', str(self.host / 'recover.sh'), env=self.env(), cwd=self.host, timeout=300)

    def migrate(self):
        return sh(sys.executable, '-m', 'omni_prod.migrate', env=self.env(), cwd=ROOT)

    def start_new(self):
        return self.compose('up', '-d', '--remove-orphans', env_extra={'IMG': f'{BASE_IMAGE}:2'})

    def untouched(self):
        now = self.snapshot()
        self.assertEqual(now, self.before, 'a refused drain must not stop, restart or recreate any consumer')

    def seed_running_build(self):
        u = uuid.uuid4().hex[:8]
        self.conn.execute('INSERT INTO creator_accounts (id,email,password_hash,salt_b64) VALUES (%s,%s,%s,%s)', (f'a{u}', f'{u}@x.test', 'x', 'x'))
        self.conn.execute('INSERT INTO creator_projects (id,owner_id,title) VALUES (%s,%s,%s)', (f'p{u}', f'a{u}', 't'))
        self.conn.execute("INSERT INTO build_jobs (id,project_id,status,heartbeat_at) VALUES (%s,%s,'running', now())", (f'bld_{u}', f'p{u}'))
        self.conn.commit()
        return f'bld_{u}'

    # ---- scenarios
    def test_0_clean_deploy_drains_gracefully_then_the_new_release_runs(self):
        (self.ctl / 'worker.finish-seconds').write_text('2')         # the worker finishes an in-flight job after SIGTERM
        d = self.drain()
        self.assertEqual(d.returncode, 0, d.stdout + d.stderr)
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(self.start_new().returncode, 0)
        self.assertTrue(self.wait_running(SERVICES))
        now = self.snapshot()
        for s in SERVICES:
            self.assertNotEqual(now[s]['image'], self.before[s]['image'], s)       # the NEW image is what runs
        self.assertIn('Listening on', self.compose('logs', 'worker', env_extra={'IMG': f'{BASE_IMAGE}:2'}).stdout)

    def test_1_an_active_job_refuses_the_drain_and_nothing_is_touched(self):
        self.seed_running_build()
        d = self.drain()
        self.assertEqual(d.returncode, 1, d.stdout)
        self.assertIn('nothing was stopped', d.stdout)
        self.untouched()
        r = self.recover()                                            # the workflow runs recovery after a drain failure
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('untouched', r.stdout)
        self.untouched()

    def test_2_redis_or_database_failure_blocks_and_nothing_is_touched(self):
        for extra in ({'OMNI_REDIS_URL': 'redis://127.0.0.1:1/0'}, {'OMNI_DATABASE_URL': 'postgresql://postgres@127.0.0.1:1/none'},
                      {'OMNI_REDIS_URL': ''}):
            d = self.drain(**extra)
            self.assertEqual(d.returncode, 1, (extra, d.stdout))
            self.assertIn('could not verify', (self.state / 'drain-failed').read_text())
            self.untouched()
            self.assertEqual(self.recover().returncode, 0)
            self.untouched()

    def test_3_rollback_image_save_failure_blocks_before_stopping(self):
        # FAULT INJECTION around the real docker: `docker tag` for one service fails; everything else is real.
        shim = self.tmp / 'shim'
        shim.mkdir()
        real = shutil.which('docker')
        w = shim / 'docker'
        w.write_text(f'#!/bin/bash\nif [ "$1" = tag ] && [[ "$3" == omni-rollback/intake-worker:* ]]; then exit 1; fi\nexec {real} "$@"\n')
        w.chmod(w.stat().st_mode | stat.S_IEXEC)
        d = self.drain(PATH=f'{shim}:{os.environ["PATH"]}')
        self.assertEqual(d.returncode, 1, d.stdout)
        self.assertIn('cannot save a rollback image for intake-worker', (self.state / 'drain-failed').read_text())
        self.untouched()
        self.assertEqual(self.recover().returncode, 0)
        self.untouched()

    def test_4_a_job_that_outlives_the_deadline_is_killed_137_the_deploy_fails_and_recovery_restores_everything(self):
        (self.ctl / 'worker.ignore-term').write_text('1')            # a job that does not finish within the deadline
        d = self.drain()
        self.assertEqual(d.returncode, 1, d.stdout)
        print('\nEVIDENCE 137 drain-failed:', (self.state / 'drain-failed').read_text().strip())
        self.assertIn('exit 137', (self.state / 'drain-failed').read_text())
        r = self.recover()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.all_running_again(), self.compose('ps', '-a').stdout)
        now = self.snapshot()
        for s in SERVICES:
            self.assertEqual(now[s]['image'], self.before[s]['image'], f'{s} must run the PREVIOUS image again')

    def test_5_an_oom_kill_fails_the_drain_and_recovery_restores_everything(self):
        (self.ctl / 'preview-worker.oom').write_text('1')            # real memory exhaustion inside a 64 MB cgroup on SIGTERM
        # The throwaway /bin/oom-allocate workload touches resident memory
        # until Docker itself reports .State.OOMKilled=true. A timeout-driven
        # exit 137 is explicitly NOT acceptable. Production policy is unchanged.
        d = self.drain(DRAIN_DEADLINE_SECONDS='60')
        reasons = (self.state / 'drain-failed').read_text() if (self.state / 'drain-failed').exists() else ''
        self.assertEqual(d.returncode, 1, d.stdout)
        print('\nEVIDENCE oom drain-failed:', reasons.strip(), '|', [l for l in d.stdout.splitlines() if l.startswith('drain:')])
        self.assertIn('was OOM-killed', reasons)          # the engine's own OOMKilled flag, not just exit 137
        r = self.recover()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.all_running_again())

    def test_6_a_failed_migration_after_a_clean_drain_is_recovered(self):
        self.assertEqual(self.drain().returncode, 0)
        self.conn.execute("UPDATE schema_migrations SET sha256='tampered' WHERE version=37")    # a real checksum-drift failure
        self.conn.commit()
        m = self.migrate()
        self.assertNotEqual(m.returncode, 0)
        self.assertIn('checksum drift', m.stderr + m.stdout)
        r = self.recover()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.all_running_again())
        now = self.snapshot()
        for s in SERVICES:
            self.assertEqual(now[s]['image'], self.before[s]['image'])
        # the database was neither dropped nor rewritten by recovery
        self.assertEqual(self.conn.execute("SELECT sha256 FROM schema_migrations WHERE version=37").fetchone()[0], 'tampered')

    def test_7_a_startup_failure_of_the_new_release_is_recovered(self):
        (self.ctl / 'startfail').write_text('1')                       # the NEW image exits 1 immediately
        self.assertEqual(self.drain().returncode, 0)
        self.assertEqual(self.migrate().returncode, 0)
        self.start_new()
        time.sleep(4)
        logs = self.compose('logs', 'worker', env_extra={'IMG': f'{BASE_IMAGE}:2'}).stdout
        self.assertNotIn('Listening on', logs)                          # the workflow's listen step would fail here
        r = self.recover()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.all_running_again(), self.compose('ps', '-a').stdout)
        for s in SERVICES:
            self.assertEqual(self.snapshot()[s]['image'], self.before[s]['image'])
        self.assertIn('Listening on', self.compose('logs', 'worker').stdout)


if __name__ == '__main__':
    unittest.main()
