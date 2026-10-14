"""Listing versions must not download every artifact.

Golden E2E #1 (2026-10-07): the build reached READY with its archive in R2,
but the web app's version list came back empty: history() computed
len(v.files), which downloads each archive, and the web tier's storage
credential was wrong, so the list call failed and the UI showed "no versions".
The durable file_count column is used when present.
"""
import unittest
from types import SimpleNamespace

from omni_prod.v26_platform import V26UniversalPlatform


class _Version:
    id = 'v1'; parent_id = None; created_at = '2026-10-07'; message = 'build'; checksum = 'c'; file_count = 7

    @property
    def files(self):
        raise AssertionError('history must not download the artifact')


class HistoryTests(unittest.TestCase):
    def test_history_uses_durable_file_count(self):
        plat = V26UniversalPlatform.__new__(V26UniversalPlatform)
        plat._key = lambda *, token, project_id: (None, 'k')
        plat.engine = SimpleNamespace(workspace=SimpleNamespace(history=lambda key: (_Version(),)))
        rows = plat.history(token='t', project_id='p')
        self.assertEqual(rows[0]['file_count'], 7)


if __name__ == '__main__':
    unittest.main()
