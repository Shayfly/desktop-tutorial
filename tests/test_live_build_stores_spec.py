"""A READY live build stores its ProductSpec with the version, atomically.

Golden E2E #1 (2026-10-07): the first READY build's version could not be
modified -- "this version predates spec tracking (M4B)" -- because the live
build never saved its spec.
"""
import unittest
from contextlib import contextmanager
from types import SimpleNamespace

from tests.test_m3_preview_logic import BuildHarness
from tests.policy_fixtures import ACCEPTED_SPEC
from omni_prod import worker_tasks


class _Pool:
    def __init__(self, log):
        self.log = log

    @contextmanager
    def connection(self):
        log = self.log

        class _Conn:
            @contextmanager
            def transaction(self):
                log.append('begin'); yield; log.append('commit')

            @contextmanager
            def cursor(self):
                yield 'CUR'
        yield _Conn()


class _SpecRepo:
    def __init__(self, log):
        self.log = log

    def save(self, **kw):
        self.log.append(('spec', kw['version_id'], kw['project_id'], kw['spec'], kw['cur']))


class StoresSpecTests(unittest.TestCase):
    def test_version_and_spec_share_one_transaction(self):
        h = BuildHarness()
        log = []
        h.workspace.pool = _Pool(log)
        h.workspace.commit.side_effect = lambda **kw: (log.append(('commit', kw.get('cur'))),
                                                       SimpleNamespace(id='ver_1', artifact_key='k'))[1]
        status = worker_tasks._run_live_build_job(
            'bld_1', jobs=h.jobs, platform=h.platform, workspace=h.workspace,
            components_factory=h.factory, quality_fn=lambda **kw: h.quality,
            security_fn=lambda repo: h.security, spec_repo=_SpecRepo(log))
        self.assertEqual(status, 'ready')
        self.assertEqual(log, ['begin', ('commit', 'CUR'), ('spec', 'ver_1', 'tenant_abc', ACCEPTED_SPEC, 'CUR'), 'commit'])

    def test_without_spec_repo_commit_is_unchanged(self):
        h = BuildHarness()
        self.assertEqual(h.run(), 'ready')
        self.assertNotIn('cur', h.workspace.commit.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
