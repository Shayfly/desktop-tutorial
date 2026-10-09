"""Preview product data: persistent per project, acceptance on a scratch copy
(directive 2026-10-09 §13). The real-container proof runs on the preview host
(deploy-worker step "preview data"); these tests pin the logic."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

from omni_prod import worker_tasks
from omni_prod.preview_durability import selftest
from omni_prod.preview_runtime import (DockerPreviewProvider, PreviewContract, StartedPreview, build_run_argv,
                                       project_data_dir)

CONTRACT = PreviewContract(runtime='python:3.11-slim', start=('python', 'app.py'), port=8000, health_path='/')
REPO = {'app.py': 'print(1)', '.omni/project.json': '{"schema_version":2,"runtime":"python:3.11-slim",'
                                                     '"start":["python","app.py"],"port":8000}'}


class ArgvTests(unittest.TestCase):
    def test_data_dir_is_mounted_and_announced(self):
        argv = build_run_argv(preview_id='prv_1', contract=CONTRACT, workdir='/w', data_dir='/var/d/p-x')
        self.assertIn('DATA_DIR=/data', argv)
        self.assertIn('type=bind,src=/var/d/p-x,dst=/data', argv)
        self.assertIn('--read-only', argv)  # the rest of the envelope is unchanged

    def test_without_data_dir_data_stays_in_tmpfs(self):
        argv = build_run_argv(preview_id='prv_1', contract=CONTRACT, workdir='/w')
        self.assertIn('DATA_DIR=/tmp', argv)
        self.assertFalse(any('dst=/data' in a for a in argv))

    def test_one_directory_per_project_without_user_text(self):
        a = project_data_dir('/root', 'tenant_a')
        self.assertEqual(a, project_data_dir('/root', 'tenant_a'))
        self.assertNotEqual(a, project_data_dir('/root', 'tenant_b'))
        self.assertNotIn('tenant', a)
        self.assertTrue(a.startswith('/root/p-'))


class ProviderTests(unittest.TestCase):
    def _provider(self, root):
        calls = []

        def runner(argv, **kw):
            calls.append(argv)
            if argv[:2] == ['docker', 'run']:
                return subprocess.CompletedProcess(argv, 0, 'cid123\n', '')
            if argv[:2] == ['docker', 'port']:
                return subprocess.CompletedProcess(argv, 0, '127.0.0.1:49999\n', '')
            return subprocess.CompletedProcess(argv, 0, '', '')
        return DockerPreviewProvider(workspace=None, runner=runner, data_root=root), calls

    def test_persistent_start_creates_the_project_directory(self):
        with tempfile.TemporaryDirectory() as root:
            provider, calls = self._provider(root)
            self.assertTrue(provider.persistent_data)
            s = provider.start(preview_id='prv_1', project_id='tenant_a', version_id='v', repository=REPO)
            self.assertEqual(s.data_dir, project_data_dir(root, 'tenant_a'))
            self.assertTrue(os.path.isdir(s.data_dir))
            self.assertIn(f'type=bind,src={s.data_dir},dst=/data', calls[0])
            provider.remove_workdir(s.workdir)
            self.assertTrue(os.path.isdir(s.data_dir))  # stopping a preview never deletes product data

    def test_scratch_start_has_no_data_mount(self):
        with tempfile.TemporaryDirectory() as root:
            provider, calls = self._provider(root)
            s = provider.start(preview_id='prv_1-qa', project_id='tenant_a', version_id='v', repository=REPO,
                               persistent=False)
            self.assertIsNone(s.data_dir)
            self.assertIn('DATA_DIR=/tmp', calls[0])
            provider.remove_workdir(s.workdir)

    def test_without_a_data_root_previews_are_temporary(self):
        provider = DockerPreviewProvider(workspace=None, data_root='')
        self.assertFalse(provider.persistent_data)
        self.assertEqual(selftest(provider)['status'], 'NOT_CONFIGURED')


class _Repo:
    def __init__(self):
        self.runtime = None
        self.acceptance = None
        self.crashed = None

    def record_runtime(self, preview_id, **kw):
        self.runtime = kw
        return True

    def mark_running(self, preview_id, url):
        return True

    def mark_failed(self, preview_id, **kw):
        raise AssertionError(kw)

    def record_acceptance(self, preview_id, project_id, version_id, report):
        self.acceptance = report
        return 'b'

    def mark_crashed(self, preview_id, error):
        self.crashed = error
        return True

    def mark_cleaned(self, preview_id):
        pass


class _PersistentProvider:
    persistent_data = True

    def __init__(self, scratch_alive=True):
        self.started, self.stopped, self.removed, self.swept = [], [], [], 0
        self.scratch_alive = scratch_alive

    def sweep_scratch(self):
        self.swept += 1

    def start(self, *, preview_id, project_id, version_id, persistent=True, repository=None):
        self.started.append((preview_id, persistent))
        port = 41000 if persistent else 42000
        return StartedPreview(f'cid-{preview_id}', port, f'/tmp/omni-preview-{preview_id}', CONTRACT,
                              data_dir='/d/p' if persistent else None)

    def is_running(self, cid):
        return (self.scratch_alive, 3) if cid.endswith('-qa') else (True, None)

    def stop(self, cid):
        self.stopped.append(cid)

    def logs(self, cid, tail=50):
        return 'boom'

    def remove_workdir(self, path):
        self.removed.append(path)
        return True


class _Runner:
    def __init__(self):
        self.urls = []

    def verify(self, preview, contract, personas):
        from omni_prod.web_saas_acceptance import AcceptanceReport
        self.urls.append(preview['preview_url'])
        return AcceptanceReport(status='PASS', release_eligible=True, summary='ok', checks=(),
                                covered_acceptance_ids=('A1',), missing_acceptance_ids=(),
                                covered_kinds=(), missing_kinds=(), runtime_logs=None)


class LaunchTests(unittest.TestCase):
    def _launch(self, provider, repo, runner):
        return worker_tasks._run_preview_launch(
            'prv_1', 'tenant_a', 'v', repo=repo, provider=provider, runtime_host='h',
            url_template='https://{preview_id}.preview.example', probe_host='127.0.0.1',
            probe_timeout=1, probe_interval=0, http_get=lambda url, timeout: 200, sleep=lambda _: None,
            acceptance_runner=runner, acceptance_contract=SimpleNamespace(), acceptance_personas=())

    def test_acceptance_probes_a_scratch_copy_and_the_product_keeps_running(self):
        provider, repo, runner = _PersistentProvider(), _Repo(), _Runner()
        self.assertEqual(self._launch(provider, repo, runner), 'RUNNING')
        self.assertEqual(provider.started, [('prv_1', True), ('prv_1-qa', False)])
        self.assertEqual(runner.urls, ['http://127.0.0.1:42000'])  # not the customer's preview URL
        self.assertEqual(provider.stopped, ['cid-prv_1-qa'])         # only the copy is removed
        self.assertEqual(repo.runtime['data_storage'], 'persistent')
        self.assertEqual(repo.acceptance.status, 'PASS')
        self.assertEqual(provider.swept, 1)

    def test_a_crash_of_the_copy_fails_the_preview_like_before(self):
        provider, repo, runner = _PersistentProvider(scratch_alive=False), _Repo(), _Runner()
        # The copy is "dead" from the start: it never becomes healthy -> ERROR report, preview stays.
        self.assertEqual(self._launch(provider, repo, runner), 'RUNNING')
        self.assertEqual(repo.acceptance.status, 'ERROR')
        self.assertFalse(repo.acceptance.release_eligible)
        self.assertIn('cid-prv_1-qa', provider.stopped)


class SelfTestLogicTests(unittest.TestCase):
    def test_selftest_passes_only_when_data_survives_and_stays_separate(self):
        with tempfile.TemporaryDirectory() as root:
            store: dict[str, int] = {}
            ports: dict[int, tuple] = {}

            class P:
                persistent_data = True
                data_root = root

                def start(self, *, preview_id, project_id, version_id, repository, persistent=True):
                    port = 50000 + len(ports)
                    key = project_id if persistent else f'scratch-{port}'
                    ports[port] = (key, version_id)
                    return StartedPreview(f'c{port}', port, '/tmp/x', CONTRACT)

                def stop(self, cid):
                    pass

                def remove_workdir(self, path):
                    return True

            def http(method, url, timeout=5):
                port = int(url.split(':')[2].split('/')[0])
                key, version = ports[port]
                if method == 'POST':
                    store[key] = store.get(key, 0) + 1
                    return 'hit'
                return f'{version}:{store.get(key, 0)}'

            result = selftest(P(), http=http, wait=lambda url: None)
            self.assertEqual(result['status'], 'PASS', result)


if __name__ == '__main__':
    unittest.main()
