from __future__ import annotations

"""Live Docker test of the M3 Rev2 preview runtime: real `docker run` with the
production argv, real Docker-allocated port, real HTTP health probe, real
teardown. Skipped unless OMNI_RUN_LIVE_PREVIEW=1.

    OMNI_RUN_LIVE_PREVIEW=1 python3 -m unittest tests.integration.test_live_preview_runtime -v

Runtime image: OMNI_PREVIEW_TEST_RUNTIME (default python:3.11-slim). It must
contain `python` and be listed in OMNI_PREVIEW_ALLOWED_RUNTIMES if it is not
one of the defaults. The durable Postgres repository is replaced by an
in-memory one with the same STARTING-conditional semantics; everything that
touches Docker or the network is real.
"""

import json
import os
import shutil
import subprocess
import unittest
import urllib.request
from pathlib import Path

from omni_prod import worker_tasks
from omni_prod.preview_runtime import DockerPreviewProvider

RUNTIME = os.getenv('OMNI_PREVIEW_TEST_RUNTIME', 'python:3.11-slim')
LIVE = os.getenv('OMNI_RUN_LIVE_PREVIEW') == '1'


class MemoryPreviewRepo:
    def __init__(self):
        self.status, self.error, self.url, self.runtime, self.cleaned = 'STARTING', None, None, {}, False

    def record_runtime(self, preview_id, **kw):
        if self.status != 'STARTING':
            return False
        self.runtime = kw
        return True

    def mark_running(self, preview_id, *, url):
        if self.status != 'STARTING':
            return False
        self.status, self.url = 'RUNNING', url
        return True

    def mark_failed(self, preview_id, *, error, status='FAILED'):
        if self.status != 'STARTING':
            return False
        self.status, self.error = status, error
        return True

    def mark_cleaned(self, preview_id):
        self.cleaned = True

    def get_runtime(self, preview_id):
        return {'status': self.status, 'container_id': self.runtime.get('container_id'),
                'runtime_host': self.runtime.get('runtime_host'), 'workdir': self.runtime.get('workdir'),
                'cleaned_at': 'x' if self.cleaned else None}


def app_repo(start, port=3000, health='/', extra=None):
    files = {
        '.omni/project.json': json.dumps({'schema_version': 2, 'runtime': RUNTIME, 'start': start,
                                          'port': port, 'health_path': health}),
        'index.html': '<h1>148AI live preview</h1>',
    }
    files.update(extra or {})
    return files


def container_exists(cid: str) -> bool:
    return subprocess.run(['docker', 'inspect', cid], capture_output=True).returncode == 0


@unittest.skipUnless(LIVE and shutil.which('docker'), 'requires Docker and OMNI_RUN_LIVE_PREVIEW=1')
class LivePreviewRuntimeTests(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.get('OMNI_PREVIEW_ALLOWED_RUNTIMES')
        os.environ['OMNI_PREVIEW_ALLOWED_RUNTIMES'] = ','.join({RUNTIME, 'python:3.11-slim', 'node:20-slim'})

    def tearDown(self):
        if self._env is None:
            os.environ.pop('OMNI_PREVIEW_ALLOWED_RUNTIMES', None)
        else:
            os.environ['OMNI_PREVIEW_ALLOWED_RUNTIMES'] = self._env

    def launch(self, preview_id, repository, timeout=20.0):
        provider = DockerPreviewProvider(workspace=None, bind_address='127.0.0.1')
        original_start = provider.start
        provider.start = lambda **kw: original_start(repository=repository, **kw)
        repo = MemoryPreviewRepo()
        status = worker_tasks._run_preview_launch(
            preview_id, 'tenant', 'ver', repo=repo, provider=provider, runtime_host='live-test-host',
            url_template='https://{preview_id}.preview.148ai.test', probe_host='127.0.0.1',
            probe_timeout=timeout, probe_interval=0.5)
        return status, repo, provider

    def test_healthy_app_runs_hardened_and_is_fully_cleaned_up(self):
        status, repo, provider = self.launch('prv_live_ok', app_repo(['python', '-m', 'http.server', '3000', '--bind', '0.0.0.0']))
        self.assertEqual(status, 'RUNNING', repo.error)
        cid, port, workdir = repo.runtime['container_id'], repo.runtime['host_port'], repo.runtime['workdir']
        try:
            self.assertEqual(repo.url, 'https://prv_live_ok.preview.148ai.test')
            body = urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=5).read().decode()
            self.assertIn('148AI live preview', body)

            info = json.loads(subprocess.run(['docker', 'inspect', cid], capture_output=True, text=True, check=True).stdout)[0]
            hc = info['HostConfig']
            self.assertTrue(hc['ReadonlyRootfs'])
            self.assertEqual(hc['CapDrop'], ['ALL'])
            self.assertIn('no-new-privileges', hc['SecurityOpt'])
            self.assertEqual(hc['Memory'], 512 * 1024 * 1024)
            self.assertEqual(hc['NanoCpus'], 500_000_000)
            self.assertEqual(hc['PidsLimit'], 64)
            self.assertIn('/tmp', hc['Tmpfs'])
            self.assertEqual(info['Config']['User'], '65534:65534')
            binding = hc['PortBindings']['3000/tcp'][0]
            self.assertEqual((binding['HostIp'], binding['HostPort']), ('127.0.0.1', ''))  # Docker chose the port
            live_binding = info['NetworkSettings']['Ports']['3000/tcp'][0]
            self.assertEqual(int(live_binding['HostPort']), port)

            def sh(code):
                return subprocess.run(['docker', 'exec', cid, 'python', '-c', code], capture_output=True, text=True)
            self.assertNotEqual(sh("open('/workspace/x','w')").returncode, 0)  # read-only source
            self.assertNotEqual(sh("open('/x','w')").returncode, 0)            # read-only root
            self.assertEqual(sh("open('/tmp/x','w').write('ok')").returncode, 0)  # tmpfs scratch
            self.assertEqual(sh("import os;print(os.getuid())").stdout.strip(), '65534')
        finally:
            repo.status = 'STOPPED'  # what DELETE does
            out = worker_tasks._run_preview_stop('prv_live_ok', repo=repo, provider=provider, this_host='live-test-host')
        self.assertTrue(out['cleaned'])
        self.assertFalse(container_exists(cid))
        self.assertFalse(Path(workdir).exists())

    def test_crashing_app_is_failed_with_exit_code_and_logs_then_removed(self):
        status, repo, _ = self.launch('prv_live_crash', app_repo(
            ['python', '-c', "import sys; print('booting'); sys.stderr.write('fatal: config missing\\n'); sys.exit(3)"]))
        self.assertEqual(status, 'FAILED')
        self.assertIn('exit code 3', repo.error)
        self.assertIn('fatal: config missing', repo.error)
        self.assertFalse(container_exists(repo.runtime['container_id']))
        self.assertFalse(Path(repo.runtime['workdir']).exists())

    def test_unhealthy_app_times_out_and_is_removed(self):
        server = ("import http.server\n"
                  "class H(http.server.BaseHTTPRequestHandler):\n"
                  "    def do_GET(self): self.send_response(500); self.end_headers()\n"
                  "http.server.HTTPServer(('0.0.0.0', 3000), H).serve_forever()\n")
        status, repo, _ = self.launch('prv_live_500', app_repo(['python', 'server.py'], extra={'server.py': server}), timeout=4)
        self.assertEqual(status, 'FAILED')
        self.assertIn('HTTP 500', repo.error)
        self.assertFalse(container_exists(repo.runtime['container_id']))

    def test_app_bound_to_container_loopback_is_not_reported_running(self):
        status, repo, _ = self.launch('prv_live_lo', app_repo(['python', '-m', 'http.server', '3000', '--bind', '127.0.0.1']), timeout=4)
        self.assertEqual(status, 'FAILED')
        self.assertIsNone(repo.url)


if __name__ == '__main__':
    unittest.main()
