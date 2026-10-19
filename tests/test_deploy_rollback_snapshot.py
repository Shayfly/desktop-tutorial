"""deploy-worker: rollback images are snapshotted from the RUNNING consumers before `docker compose build` (2026-10-19).

Run 39262167302: the build moved the compose tags, the running containers' image objects vanished, and the drain could
no longer save a rollback image. Runs the real snapshot-rollback.sh against a fake `docker` (no Docker, no network)."""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'infra' / 'worker-host'
SERVICES = ('worker', 'intake-worker', 'intake-maintain', 'preview-worker')

FAKE = r"""#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
st = os.environ['FAKE_STATE']
open(os.path.join(st, 'calls.log'), 'a').write(' '.join(a) + '\n')
cfg = json.load(open(os.path.join(st, 'cfg.json')))
svc_of = lambda ref: ref.split('/')[1].split(':')[0]
def notfound(what): sys.stderr.write('Error response from daemon: NotFound: content digest sha256:' + what + ': not found\n'); sys.exit(1)
if a[0] == 'compose' and 'ps' in a:
    if a[-1] in cfg['services']: print('cid-' + a[-1])
    sys.exit(0)
if a[0] == 'inspect':
    svc = a[-1][4:]; fmt = a[2]
    if fmt == '{{.Image}}': print('sha256:run-' + svc)
    elif 'Labels' in fmt: print(cfg.get('label_rev', '<no value>'))
    else: print('PATH=/usr/bin\nOMNI_SOURCE_COMMIT=' + cfg.get('env_rev', '') + '\nOMNI_S3_SECRET_KEY=s3cr3t')
    sys.exit(0)
if a[:2] == ['image', 'inspect']:
    svc = svc_of(a[-1])
    if svc not in cfg.get('rollback_exists', []): sys.exit(1)
    print(cfg.get('rollback_id', {}).get(svc, 'sha256:old-' + svc)); sys.exit(0)
if a[0] == 'tag':
    if a[1].startswith('sha256:run-') and svc_of(a[2]) in cfg.get('tag_notfound', []): notfound('tag')
    sys.exit(0)
if a[0] == 'commit':
    if svc_of(a[-1]) in cfg.get('commit_notfound', []): notfound('commit')
    sys.exit(0)
if a[0] == 'build':
    df = a[a.index('-f') + 1]
    print('sha256:built-' + ('preview' if 'preview-worker' in df else 'worker')); sys.exit(0)
if a[0] == 'exec': print('H-run'); sys.exit(0)
if a[0] == 'run':
    img = a[a.index('--entrypoint') + 2]
    print(cfg.get('built_hash', 'H-run') if img.startswith('sha256:built-') else cfg.get('rollback_hash', 'H-old')); sys.exit(0)
if a[0] in ('stop', 'kill', 'rm', 'rmi', 'restart', 'pause') or (a[0] == 'compose' and any(x in a for x in ('stop', 'down', 'up', 'restart', 'rm'))):
    open(os.path.join(st, 'FORBIDDEN'), 'a').write(' '.join(a) + '\n'); sys.exit(0)
sys.exit(0)
"""


def git_repo(tmp):
    """A tiny real repository: the rebuild rung must `git archive` the running container's revision."""
    repo = tmp / 'repo'
    (repo / 'infra' / 'preview-worker').mkdir(parents=True)
    (repo / 'Dockerfile').write_text('FROM scratch\n')
    (repo / 'infra' / 'preview-worker' / 'Dockerfile').write_text('FROM scratch\n')
    g = lambda *c: subprocess.run(['git', '-C', str(repo), *c], check=True, capture_output=True, text=True).stdout.strip()
    g('init', '-q'); g('-c', 'user.email=t@t', '-c', 'user.name=t', 'add', '.')
    g('-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'running revision')
    return repo, g('rev-parse', 'HEAD')


def run(cfg, env_file='OMNI_S3_SECRET_KEY=s3cr3t\nOPENAI_API_KEY=sk-x\n# c\n'):
    tmp = Path(tempfile.mkdtemp())
    host = tmp / 'host'
    host.mkdir()
    shutil.copy(HOST / 'snapshot-rollback.sh', host / 'snapshot-rollback.sh')
    (host / '.env').write_text(env_file)
    (tmp / 'bin').mkdir()
    d = tmp / 'bin' / 'docker'
    d.write_text(FAKE)
    d.chmod(d.stat().st_mode | stat.S_IEXEC)
    repo, rev = git_repo(tmp)
    cfg = {'services': list(SERVICES), **cfg}
    cfg = json.loads(json.dumps(cfg).replace('@REV@', rev))
    (tmp / 'cfg.json').write_text(json.dumps(cfg))
    env = {**os.environ, 'PATH': f'{tmp / "bin"}:{os.environ["PATH"]}', 'FAKE_STATE': str(tmp), 'SNAPSHOT_REPO_ROOT': str(repo)}
    r = subprocess.run(['bash', str(host / 'snapshot-rollback.sh')], env=env, capture_output=True, text=True, timeout=60)
    calls = (tmp / 'calls.log').read_text().splitlines() if (tmp / 'calls.log').exists() else []
    return r, calls, tmp, rev


ALL_GONE = {'tag_notfound': list(SERVICES), 'commit_notfound': list(SERVICES)}
OTHER_REV = 'f' * 40


class SnapshotLadderTests(unittest.TestCase):
    def assertNothingStopped(self, tmp):
        f = tmp / 'FORBIDDEN'
        self.assertFalse(f.exists(), f.read_text() if f.exists() else '')

    def only(self, calls, verb):
        return [c for c in calls if c.split(' ')[0] == verb]

    def test_rung_1_tag_is_taken_quietly_and_nothing_else_runs(self):
        r, calls, tmp, _ = run({})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for s in SERVICES:
            self.assertIn(f'tag sha256:run-{s} omni-rollback/{s}:prev', calls)
            self.assertIn(f'::notice title=snapshot::{s}: rung 1 (tag)', r.stdout)
        self.assertNotIn('::warning', r.stdout)
        self.assertFalse(self.only(calls, 'commit') + self.only(calls, 'build'))
        self.assertNothingStopped(tmp)

    def test_rung_2_commit_when_the_tag_fails_with_labels_no_pause_no_secrets(self):
        r, calls, tmp, rev = run({'tag_notfound': list(SERVICES), 'label_rev': '@REV@'})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        commits = self.only(calls, 'commit')
        self.assertEqual(len(commits), 4)
        for s, c in zip(SERVICES, commits):
            self.assertIn('--pause=false', c)
            self.assertIn(f'LABEL org.opencontainers.image.revision={rev}', c)
            self.assertIn('ENV OMNI_S3_SECRET_KEY=', c)
            self.assertNotIn('s3cr3t', c)
            self.assertNotIn('sk-x', c)
            self.assertTrue(c.endswith(f'cid-{s} omni-rollback/{s}:prev'), c)
        self.assertIn('rung 1 (tag) failed: Error response from daemon: NotFound', r.stdout)
        self.assertFalse(self.only(calls, 'build'))
        self.assertNotIn('s3cr3t', r.stdout + r.stderr)
        self.assertNothingStopped(tmp)

    def test_rung_3_tag_and_commit_notfound_rebuilds_from_the_running_containers_label_revision(self):
        r, calls, tmp, rev = run({**ALL_GONE, 'label_rev': '@REV@', 'env_rev': OTHER_REV})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        builds = self.only(calls, 'build')
        self.assertEqual(len(builds), 2, builds)                       # one per Dockerfile, not per service
        for b in builds:
            self.assertIn(f'--label org.opencontainers.image.revision={rev}', b)
            self.assertNotIn(OTHER_REV, b)                             # the label wins over the env
            self.assertNotIn('--build-arg', b)
        self.assertTrue(any('infra/preview-worker/Dockerfile' in b for b in builds))
        for s in SERVICES:
            built = 'preview' if s == 'preview-worker' else 'worker'
            self.assertIn(f'tag sha256:built-{built} omni-rollback/{s}:prev', calls)
            self.assertIn(f'::warning title=snapshot::{s}: rebuilt rollback from revision {rev[:7]}', r.stdout)
            self.assertIn(f'{s}: rung 2 (commit) failed: Error response from daemon: NotFound', r.stdout)
        self.assertNothingStopped(tmp)

    def test_rung_3_without_a_label_uses_the_running_containers_own_env_revision_never_head(self):
        r, calls, tmp, rev = run({**ALL_GONE, 'env_rev': '@REV@'})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('has no revision label; using its own OMNI_SOURCE_COMMIT', r.stdout)
        self.assertTrue(all(f'revision={rev}' in b for b in self.only(calls, 'build')))
        r, calls, tmp, rev = run({**ALL_GONE, 'env_rev': OTHER_REV})        # a revision this repo does not have
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(f'rebuild from revision {OTHER_REV[:7]} failed', r.stdout)
        self.assertFalse(self.only(calls, 'build'))

    def test_rung_3_with_mismatching_hashes_is_not_accepted_and_fails_loudly(self):
        r, calls, tmp, rev = run({**ALL_GONE, 'label_rev': '@REV@', 'built_hash': 'H-different'})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('::error title=snapshot::NO SAFE ROLLBACK, nothing was stopped', r.stdout)
        self.assertIn('does not match the running code (3 hashes); not accepted', r.stdout)
        self.assertFalse([c for c in calls if c.startswith('tag sha256:built-')])
        self.assertNothingStopped(tmp)

    def test_no_revision_anywhere_fails_loudly(self):
        r, calls, tmp, _ = run(ALL_GONE)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('records no revision; cannot rebuild', r.stdout)
        self.assertNothingStopped(tmp)

    def test_idempotent_already_snapshotted_or_same_code_kept_without_rebuild(self):
        ids = {s: f'sha256:run-{s}' for s in SERVICES}
        r, calls, tmp, _ = run({'rollback_exists': list(SERVICES), 'rollback_id': ids})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(self.only(calls, 'tag') + self.only(calls, 'commit') + self.only(calls, 'build'))
        r, calls, tmp, _ = run({**ALL_GONE, 'rollback_exists': list(SERVICES), 'rollback_hash': 'H-run', 'label_rev': '@REV@'})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(self.only(calls, 'build'))
        self.assertIn('has the same 3 code hashes as the running container, kept', r.stdout)


class WorkflowOrderTests(unittest.TestCase):
    def steps(self):
        wf = yaml.safe_load((ROOT / '.github' / 'workflows' / 'deploy-worker.yml').read_text())
        return [st.get('name', '') for st in wf['jobs']['deploy']['steps']]

    def idx(self, names, prefix):
        hits = [i for i, n in enumerate(names) if n.startswith(prefix)]
        self.assertEqual(len(hits), 1, (prefix, names))
        return hits[0]

    def test_snapshot_runs_after_the_env_file_and_before_the_build(self):
        n = self.steps()
        snap = self.idx(n, 'Snapshot running consumers as rollback images')
        self.assertLess(self.idx(n, 'Write environment file'), snap)
        self.assertLess(snap, self.idx(n, 'Build images'))
        self.assertLess(snap, self.idx(n, 'Drain workers'))

