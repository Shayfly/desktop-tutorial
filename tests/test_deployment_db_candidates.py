"""72 step 0: /api/v28/deployment names the database behind each candidate variable -- never a password."""
import ast
import os
import pathlib
import unittest
from unittest import mock

from omni_prod.isolation_check import DB_KEYS, db_identity

ROOT = pathlib.Path(__file__).resolve().parents[1]


def candidates():
    """The function body from investor_app (FastAPI is CI-only), run on its own."""
    tree = ast.parse((ROOT / 'omni_prod' / 'investor_app.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_database_candidates')
    ns = {'os': os}
    src = ast.unparse(fn).replace('from .isolation_check import', 'from omni_prod.isolation_check import')
    exec(src, ns)
    return ns['_database_candidates']()


class Candidates(unittest.TestCase):
    def test_hosts_only_never_secrets(self):
        env = {'OMNI_DATABASE_URL': 'postgresql://u:s3cret-pw@ep-main-pooler.c-7.aws.neon.tech/neondb?sslmode=require',
               'DATABASE_URL': 'postgresql://u:other-pw@ep-preview-branch.c-7.aws.neon.tech/neondb'}
        with mock.patch.dict(os.environ, env, clear=False):
            out = candidates()
        self.assertEqual(out['OMNI_DATABASE_URL'], 'ep-main.c-7.aws.neon.tech:5432/neondb')
        self.assertEqual(out['DATABASE_URL'], 'ep-preview-branch.c-7.aws.neon.tech:5432/neondb')
        self.assertNotIn('pw', repr(out))
        self.assertNotIn('u:', repr(out))

    def test_every_key_is_the_isolation_checks_own(self):
        self.assertIn('OMNI_DATABASE_URL', DB_KEYS)
        self.assertIsNone(db_identity(None))


if __name__ == '__main__':
    unittest.main()
