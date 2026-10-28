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
BASE_IMAGE = 'omni-e2e-oom-base-v2'
# The allocator touches 64 MiB, strictly above the cgroup limit, so reclaiming
# page cache can never let it fit (an equal limit made the kill nondeterministic).
MEM_LIMIT_MIB = 48
OOM_ALLOCATION_MIB = 64

JOB_SH = r'''#!/bin/bash
svc="$1"; ctl=/ctl
[ "${GEN:-old}" = new ] && [ -f $ctl/startfail ] && { echo "startup failure of the new image"; exit 1; }
[ "$svc" = worker ] && echo "*** Listening on omni-builds..."
term() {
  [ -f $ctl/$svc.oom ] && exec /bin/oom-allocator @OOM_MIB@
  [ -f $ctl/$svc.ignore-term ] && return
  [ -f $ctl/$svc.finish-seconds ] && { read n < $ctl/$svc.finish-seconds; sleep "$n"; }
  exit 0
}
trap term TERM
while :; do sleep 1; done
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
    mem_limit: {MEM_LIMIT_MIB}m
    memswap_limit: {MEM_LIMIT_MIB}m
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
    if sh('docker', 'image', 'inspect', f'{BASE_IMAGE}:1').returncode == 0 and sh('docker', 'image', 'inspect', f'{BASE_IMAGE}:2').returncode == 0:
        return
    work = Path(tempfile.mkdtemp())
    rootfs = work / 'rootfs'
    (rootfs / 'bin').mkdir(parents=True)
    libs = set()
    oom_source = work / 'oom-allocator.c'
    oom_source.write_text(r'''#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    char *end = NULL;
    errno = 0;
    unsigned long mib = strtoul(argv[1], &end, 10);
    if (errno || !end || *end || mib == 0 || mib > 64) return 2;
    size_t bytes = (size_t)mib * 1024u * 1024u;
    volatile unsigned char *memory = malloc(bytes);
    if (!memory) return 3;
    for (size_t offset = 0; offset < bytes; offset += 4096u) memory[offset] = 1;
    memory[bytes - 1] = 1;
    return 0;
}
''', encoding='utf-8')
    compiler = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if compiler:
        oom_binary = rootfs / 'bin' / 'oom-allocator'
        result = sh(compiler, '-O0', '-Wall', '-Wextra', '-Werror', str(oom_source), '-o', str(oom_binary))
        if result.returncode:
            raise RuntimeError(f'could not compile bounded OOM allocator: {result.stderr}')
        oom_binary.chmod(oom_binary.stat().st_mode | stat.S_IEXEC)
    for b in ('bash', 'sleep', 'cat', 'date', 'env', 'true'):
        p = shutil.which(b)
        if p:
            shutil.copy(os.path.realpath(p), rootfs / 'bin' / b)
            for line in sh('ldd', p).stdout.splitlines():
                for tok in line.split():
                    if tok.startswith('/') and os.path.exists(tok):
                        libs.add(tok)
    if compiler:
        for line in sh('ldd', str(rootfs / 'bin' / 'oom-allocator')).stdout.splitlines():
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


class _OomProbe:
    """Measurement for the test_5 flake (SMELLS.md, #150), before any fix: peak cgroup memory against the limit, time
    from the drain start to the engine's `oom` and `die` events against the 60 s deadline, the engine's own OOMKilled
    flag, and the cgroup's oom_kill counter. Printed and written as ::notice evidence; it never asserts anything."""

    def __init__(self, cid):
        import threading
        self.cid, self.t0 = cid, time.time()
        self.peak = self.current_max = 0
        self.oom_kill = None
        self.cgroup = self._cgroup()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)
        self.thread.start()

    def _cgroup(self):
        try:
            full = subprocess.run(['docker', 'inspect', '-f', '{{.Id}}', self.cid], capture_output=True, text=True,
                                  timeout=20).stdout.strip()
        except Exception:
            return None
        for base in (f'/sys/fs/cgroup/system.slice/docker-{full}.scope', f'/sys/fs/cgroup/docker/{full}'):
            if Path(base, 'memory.current').exists():
                return Path(base)
        return None

    def _read(self, name):
        try:
            return (self.cgroup / name).read_text()
        except Exception:
            return None

    def _sample(self):
        while not self.stop.is_set() and self.cgroup is not None:
            cur = self._read('memory.current')
            if cur and cur.strip().isdigit():
                self.current_max = max(self.current_max, int(cur))
            peak = self._read('memory.peak')
            if peak and peak.strip().isdigit():
                self.peak = max(self.peak, int(peak))
            ev = self._read('memory.events') or ''
            for line in ev.splitlines():
                if line.startswith('oom_kill '):
                    self.oom_kill = int(line.split()[1])
            time.sleep(0.2)

    def finish(self, state):
        self.stop.set()
        self.thread.join(2)
        t1 = time.time()
        try:                                                         # a measurement never fails the test
            out = subprocess.run(['docker', 'events', '--since', str(int(self.t0) - 1), '--until', str(int(t1) + 1),
                                  '--filter', f'container={self.cid}', '--format', '{{.Status}} {{.TimeNano}}'],
                                 capture_output=True, text=True, timeout=30).stdout.split('\n')
        except Exception as exc:
            out = [f'events-unavailable {type(exc).__name__}']
        first = {}
        for line in out:
            parts = line.split()
            if len(parts) == 2 and parts[0] in ('oom', 'die', 'kill', 'stop') and parts[0] not in first:
                first[parts[0]] = round(int(parts[1]) / 1e9 - self.t0, 1)
        mib = lambda b: round(b / 1048576, 1) if b else None
        line = (f"limit={MEM_LIMIT_MIB}MiB alloc={OOM_ALLOCATION_MIB}MiB peak={mib(self.peak)}MiB "
                f"current_max={mib(self.current_max)}MiB cgroup={'found' if self.cgroup else 'NOT FOUND'} "
                f"oom_kill_counter={self.oom_kill} engine_events_s_after_drain_start={first} "
                f"deadline=60s drain_s={round(t1 - self.t0, 1)} inspect(OOMKilled ExitCode)={state.strip()}")
        print('\nMEASURE test_5:', line, flush=True)
        try:
            from tests.evidence_notice import notice
            notice('oom-measure test_5', line)
        except Exception:
            pass


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
        (self.ctl / 'job.sh').write_text(JOB_SH.replace('@OOM_MIB@', str(OOM_ALLOCATION_MIB)))
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
        self.wait_running(SERVICES)
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
        if not (shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')):
            self.skipTest('BLOCKED: a C compiler is required to build the bounded OOM allocator')
        cid = self.cid('preview-worker')[0]
        limit = MEM_LIMIT_MIB * 1024 * 1024
        self.assertEqual(self.inspect(cid, '{{.HostConfig.Memory}}'), str(limit), 'runner did not apply the memory limit')
        self.assertEqual(self.inspect(cid, '{{.HostConfig.MemorySwap}}'), str(limit), 'runner did not disable swap')
        self.assertGreater(OOM_ALLOCATION_MIB, MEM_LIMIT_MIB)
        (self.ctl / 'preview-worker.oom').write_text('1')            # touches more anonymous memory than the cgroup allows
        probe = _OomProbe(cid)                                       # MEASUREMENT ONLY: changes no assertion
        d = self.drain(DRAIN_DEADLINE_SECONDS='60')
        probe.finish(self.inspect(cid, '{{.State.OOMKilled}} {{.State.ExitCode}}'))
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
