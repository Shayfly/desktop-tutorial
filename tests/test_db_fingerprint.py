"""db_fingerprint: comparable database identity without exposing a URL."""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from omni_prod import investor_app
from omni_prod.schema_manifest import db_fingerprint, db_identity


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._row


class _Conn:
    def __init__(self, host, dbname, ledger, password='s3cret-pw'):
        self.info = SimpleNamespace(host=host, password=password)
        self.dbname, self.ledger = dbname, ledger

    def execute(self, sql):
        if 'current_database' in sql:
            return _Result((self.dbname,))
        if 'to_regclass' in sql:
            return _Result((self.ledger is not None,))
        return _Result([(v,) for v in self.ledger])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def connection(self):
        return self.conn


class DbFingerprintTests(unittest.TestCase):
    def test_same_host_and_dbname_give_same_fingerprint(self):
        self.assertEqual(db_fingerprint('h.example', 'neondb'), db_fingerprint('h.example', 'neondb'))
        self.assertNotEqual(db_fingerprint('h.example', 'neondb'), db_fingerprint('h.example', 'other'))
        self.assertNotEqual(db_fingerprint('h.example', 'neondb'), db_fingerprint('x.example', 'neondb'))
        self.assertRegex(db_fingerprint('h', 'd'), r'^[0-9a-f]{12}$')

    def test_identity_is_independent_of_credentials(self):
        a = db_identity(_Conn('h.example', 'neondb', [1], password='one'))
        b = db_identity(_Conn('h.example', 'neondb', [1], password='two'))
        self.assertEqual(a, b)

    def test_schema_endpoint_reports_identity_without_password(self):
        old = investor_app._v28_pool
        try:
            investor_app._v28_pool = _Pool(_Conn('h.example', 'neondb', [1, 2]))
            out = investor_app._schema_compatibility()
        finally:
            investor_app._v28_pool = old
        self.assertEqual(out['db_host'], 'h.example')
        self.assertEqual(out['db_fingerprint'], db_fingerprint('h.example', 'neondb'))
        self.assertNotIn('s3cret-pw', json.dumps(out))

    def test_missing_table_is_distinguished_from_empty_table(self):
        old = investor_app._v28_pool
        try:
            investor_app._v28_pool = _Pool(_Conn('h', 'd', None))
            missing_table = investor_app._schema_compatibility()
            investor_app._v28_pool = _Pool(_Conn('h', 'd', []))
            empty_table = investor_app._schema_compatibility()
        finally:
            investor_app._v28_pool = old
        self.assertIs(missing_table['schema_migrations_present'], False)
        self.assertIs(empty_table['schema_migrations_present'], True)
        for out in (missing_table, empty_table):
            self.assertEqual(out['status'], 'MIGRATIONS_PENDING')
            self.assertFalse(out['compatible'])
            self.assertIsNone(out['applied_max'])


if __name__ == '__main__':
    unittest.main()
