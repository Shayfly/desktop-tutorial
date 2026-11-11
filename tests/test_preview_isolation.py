"""72: a Vercel Preview never writes to Production's database."""
import pathlib
import unittest

from omni_prod import preview_isolation as P

PROD = 'postgresql://u:p@ep-delicate-wind-b9cgx8fb-pooler.c-7.eu-central-1.aws.neon.tech/neondb?sslmode=require'
BRANCH = 'postgresql://u:q@ep-old-lake-b9pn86mf-pooler.c-7.eu-central-1.aws.neon.tech/neondb?sslmode=require'


class Isolation(unittest.TestCase):
    def test_preview_uses_its_own_branch(self):
        env = {'VERCEL_ENV': 'preview', 'OMNI_DATABASE_URL': PROD, 'DB2_DATABASE_URL': BRANCH}
        self.assertEqual(P.apply(env), 'branch')
        self.assertEqual(env['OMNI_DATABASE_URL'], BRANCH)

    def test_production_and_the_worker_are_untouched(self):
        for vercel_env in ('production', None):
            env = {'OMNI_DATABASE_URL': PROD, 'DB2_DATABASE_URL': BRANCH}
            if vercel_env:
                env['VERCEL_ENV'] = vercel_env
            self.assertEqual(P.apply(env), 'not_preview')
            self.assertEqual(env['OMNI_DATABASE_URL'], PROD)

    def test_no_branch_means_no_database_never_production(self):
        env = {'VERCEL_ENV': 'preview', 'OMNI_DATABASE_URL': PROD}
        self.assertEqual(P.apply(env), 'no_database')
        self.assertNotIn('OMNI_DATABASE_URL', env)

    def test_a_branch_that_is_production_is_refused(self):
        env = {'VERCEL_ENV': 'preview', 'OMNI_DATABASE_URL': PROD, 'DB2_DATABASE_URL': PROD.replace('-pooler', '')}
        self.assertEqual(P.apply(env), 'no_database')
        self.assertNotIn('OMNI_DATABASE_URL', env)

    def test_shared_is_an_explicit_choice(self):
        env = {'VERCEL_ENV': 'preview', 'OMNI_DATABASE_URL': PROD, 'DB2_DATABASE_URL': BRANCH,
               'OMNI_PREVIEW_DATABASE': 'shared'}
        with self.assertLogs('omni_prod.preview_isolation', level='WARNING'):
            self.assertEqual(P.apply(env), 'shared')
        self.assertEqual(env['OMNI_DATABASE_URL'], PROD)

    def test_it_runs_before_the_app_is_imported(self):
        src = (pathlib.Path(__file__).resolve().parents[1] / 'app.py').read_text()
        self.assertLess(src.index('_preview_isolation.apply()'), src.index('from omni_prod.investor_app import app'))


if __name__ == '__main__':
    unittest.main()
