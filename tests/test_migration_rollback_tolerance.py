"""Safe return to older code after migration 038 (founder directive 2026-10-11): no DROP TABLE, no deleted data, no hidden
DB version, and the migration checks are NOT weakened -- only exact, explicitly named, newer-than-package versions are
tolerated. Live PG (isolated throw-away database)."""
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from omni_prod.migrate import parse_accept_newer
from omni_prod.migration_runner import apply_migrations, _load_applied
from omni_prod.migrations import discover_migrations, verify_applied, Migration

ROOT = Path(__file__).resolve().parents[1]
PG = ROOT / 'infra' / 'postgres'


def mig(v, sha='x'):
    return Migration(version=v, name=f'{v:03d}_x', sql='', sha256=sha, path=Path('x.sql'))


class VerifyAppliedTests(unittest.TestCase):
    pkg = [mig(36), mig(37)]

    def test_default_still_aborts_on_a_newer_database(self):
        with self.assertRaisesRegex(RuntimeError, 'missing from package: 38'):
            verify_applied(self.pkg, {36: 'x', 37: 'x', 38: 'y'})

    def test_only_the_exact_named_newer_version_is_tolerated(self):
        verify_applied(self.pkg, {36: 'x', 37: 'x', 38: 'y'}, frozenset({38}))
        with self.assertRaises(RuntimeError):                                    # 39 not named
            verify_applied(self.pkg, {36: 'x', 37: 'x', 38: 'y', 39: 'z'}, frozenset({38}))
        with self.assertRaises(RuntimeError):                                    # naming 38 does not cover 40
            verify_applied(self.pkg, {36: 'x', 37: 'x', 40: 'y'}, frozenset({38}))

    def test_a_version_below_the_newest_package_migration_is_never_tolerated(self):
        with self.assertRaises(RuntimeError):                                    # a hole in history is not "newer"
            verify_applied([mig(36), mig(37)], {36: 'x', 37: 'x', 20: 'y'}, frozenset({20}))
        with self.assertRaises(RuntimeError):
            verify_applied([mig(36), mig(37)], {36: 'x', 37: 'x', 30: 'y'}, frozenset({30}))

    def test_checksum_drift_still_aborts_even_with_the_exception(self):
        with self.assertRaisesRegex(RuntimeError, 'checksum drift'):
            verify_applied(self.pkg, {36: 'x', 37: 'CHANGED', 38: 'y'}, frozenset({38}))

    def test_argument_parsing_is_strict(self):
        self.assertEqual(parse_accept_newer(['--accept-newer', '38,39'], {}), frozenset({38, 39}))
        self.assertEqual(parse_accept_newer([], {'OMNI_ACCEPT_NEWER_MIGRATIONS': '38'}), frozenset({38}))
        self.assertEqual(parse_accept_newer([], {}), frozenset())
        for bad in (['--accept-newer'], ['--accept-newer', 'all'], ['--accept-newer', '38-40'], ['--accept-newer', '*']):
            with self.assertRaises(ValueError):
                parse_accept_newer(bad, {})


@unittest.skipUnless(os.getenv('M4D2_DATABASE_URL'), 'BLOCKED: M4D2_DATABASE_URL (isolated PostgreSQL) not configured')
class LiveRollbackTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        base = os.environ['M4D2_DATABASE_URL']
        self.admin = psycopg.connect(base, autocommit=True)
        self.name = 'rb_' + uuid.uuid4().hex[:10]
        self.admin.execute(f'CREATE DATABASE {self.name}')
        self.url = base.rsplit('/', 1)[0] + '/' + self.name
        self.conn = psycopg.connect(self.url)
        self.all = discover_migrations(PG)
        # the OLD package: the same files without 038 (what the deployed worker contains)
        self.old = [m for m in self.all if m.version <= 37]

    def tearDown(self):
        self.conn.close()
        self.admin.execute(f'DROP DATABASE IF EXISTS {self.name} WITH (FORCE)')
        self.admin.close()

    def _upgrade_to_038_with_data(self):
        apply_migrations(self.conn, self.old)
        self.conn.execute("INSERT INTO creator_accounts (id,email,password_hash,salt_b64) VALUES ('a1','a@x.test','x','x')")
        self.conn.execute("INSERT INTO creator_projects (id,owner_id,title) VALUES ('p1','a1','t')")
        self.conn.commit()
        apply_migrations(self.conn, self.all)                                   # the release that ships 038
        cols = [r[0] for r in self.conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name='conversation_attachments'")]
        self.assertTrue(cols)
        return cols

    def test_old_package_against_a_038_database(self):
        self._upgrade_to_038_with_data()
        before = _load_applied(self.conn.cursor())
        self.assertIn(38, before)
        # 1. without the explicit exception the old package still aborts: nothing was weakened
        with self.assertRaisesRegex(RuntimeError, 'missing from package: 38'):
            apply_migrations(self.conn, self.old)
        self.conn.rollback()
        # 2. with the exact version named it is a no-op: nothing applied, nothing changed
        run = apply_migrations(self.conn, self.old, frozenset({38}))
        self.assertEqual(run.applied_versions, ())
        # 3. the DB version is still reported truthfully and the 038 table and its schema_migrations row are intact
        self.assertEqual(_load_applied(self.conn.cursor()), before)
        self.assertIsNotNone(self.conn.execute("SELECT to_regclass('conversation_attachments')").fetchone()[0])
        # 4. a different unknown version is still refused
        self.conn.execute("INSERT INTO schema_migrations(version,name,sha256) VALUES (39,'039_future','z')")
        self.conn.commit()
        with self.assertRaisesRegex(RuntimeError, 'missing from package: 39'):
            apply_migrations(self.conn, self.old, frozenset({38}))

    def test_the_command_in_check_and_apply_mode(self):
        import subprocess
        import sys
        self._upgrade_to_038_with_data()
        env = {**os.environ, 'OMNI_DATABASE_URL': self.url}
        # The CURRENT package knows 038, so the command passes with or without the flag and never writes.
        for extra in ([], ['--accept-newer', '38'], ['--check']):
            r = subprocess.run([sys.executable, '-m', 'omni_prod.migrate', *extra], env=env, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, '-m', 'omni_prod.migrate', '--accept-newer', 'all'], env=env, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_attachments_survive_the_whole_round_trip(self):
        self._upgrade_to_038_with_data()
        att = 'att_' + '0' * 32
        self.conn.execute("INSERT INTO conversation_attachments (id,project_id,account_id,kind,mime,size_bytes,width,height,sha256,storage_key) "
                          "VALUES (%s,'p1','a1','image','image/png',10,1,1,%s,'attachments/a1/p1/x')", (att, 'a' * 64))
        self.conn.commit()
        apply_migrations(self.conn, self.old, frozenset({38}))                  # the older code runs its migrate step
        apply_migrations(self.conn, self.all)                                   # and the new code again
        row = self.conn.execute('SELECT id, storage_key, deleted_at FROM conversation_attachments').fetchall()
        self.assertEqual(row, [(att, 'attachments/a1/p1/x', None)])             # row and its object key untouched


if __name__ == '__main__':
    unittest.main()
