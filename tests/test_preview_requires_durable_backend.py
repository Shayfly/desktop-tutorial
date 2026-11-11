"""2026-10-30: on a memory backend the plan preview (POST .../build-contracts) succeeded and the build
(POST .../builds) then answered 503. Both now refuse first, with the same status and the same reason."""
from __future__ import annotations

import unittest
from unittest import mock


def _client():
    try:
        from fastapi.testclient import TestClient
        from omni_prod import investor_app as IA
    except ImportError as exc:                                                   # v24-ci has fastapi
        raise unittest.SkipTest(f'fastapi not installed here ({exc})')
    return IA, TestClient(IA.app)


class WithoutADurableBackend(unittest.TestCase):
    def test_the_preview_and_the_build_refuse_alike(self):
        IA, client = _client()
        with mock.patch.object(IA, '_v28_pool', None), \
                mock.patch.dict('os.environ', {'OMNI_CREATOR_PERSISTENCE': 'memory'}):
            preview = client.post('/api/v28/projects/p/build-contracts', json={'prompt': 'Build a simple page'})
            build = client.post('/api/v28/projects/p/builds', json={'prompt': 'Build a simple page', 'build_contract_id': 'bc_1'})
        self.assertEqual(preview.status_code, 503, preview.text)
        self.assertEqual(build.status_code, 503, build.text)
        self.assertEqual(preview.json()['detail'], build.json()['detail'])
        self.assertIn('OMNI_CREATOR_PERSISTENCE=postgres', preview.json()['detail'])   # the backend reason, not validation

    def test_the_check_comes_before_anything_else(self):
        IA, client = _client()
        with mock.patch.object(IA, '_v28_pool', None), \
                mock.patch.object(IA, '_v28_bearer', side_effect=AssertionError('auth ran before the backend check')):
            r = client.post('/api/v28/projects/p/build-contracts', json={'prompt': 'Build a simple page'})
        self.assertEqual(r.status_code, 503, r.text)


if __name__ == '__main__':
    unittest.main()
