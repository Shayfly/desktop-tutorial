"""Backup verification logic (autonomous completion directive §5); the real
dump/restore runs in .github/workflows/backup-restore.yml on the host."""
import io
import os
import tarfile
import tempfile
import unittest

from omni_prod import backup


class DataArchiveTests(unittest.TestCase):
    def _tree(self, root, files):
        for rel, data in files.items():
            path = os.path.join(root, 'data', rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'wb').write(data)

    def test_archive_matches_the_snapshot_and_detects_a_changed_file(self):
        with tempfile.TemporaryDirectory() as root:
            self._tree(root, {'p-a/count.txt': b'2', 'p-b/db.sqlite': b'\x00\x01'})
            expected = backup._data_digests(os.path.join(root, 'data'))
            self.assertEqual(len(expected), 2)
            tgz = os.path.join(root, 'd.tgz')
            with tarfile.open(tgz, 'w:gz') as tar:
                tar.add(os.path.join(root, 'data'), arcname='data')
            n, missing = backup.compare_data_archive(tgz, expected)
            self.assertEqual((n, missing), (2, []))
            expected['p-a/count.txt'] = 'different'
            self.assertEqual(backup.compare_data_archive(tgz, expected)[1], ['p-a/count.txt'])

    def test_missing_data_root_is_an_empty_snapshot(self):
        self.assertEqual(backup._data_digests('/nonexistent/omni'), {})

    def test_keys_are_grouped_by_stamp(self):
        self.assertEqual(backup._key('20261009T120000Z', 'db.dump'), 'backups/20261009T120000Z/db.dump')


if __name__ == '__main__':
    unittest.main()
