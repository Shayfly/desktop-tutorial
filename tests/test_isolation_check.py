"""Preview/Production isolation verdicts from non-secret identities; secrets never appear in the output."""
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from omni_prod.isolation_check import compare, compare_staging, identities, main, parse_env

PROD = {'OMNI_DATABASE_URL': 'postgresql://u:SECRETPW1@ep-aaa-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require',
        'OMNI_REDIS_URL': 'rediss://default:SECRETPW2@good-owl-1.upstash.io:6379',
        'OMNI_S3_ENDPOINT': 'https://acct.r2.cloudflarestorage.com', 'OMNI_S3_BUCKET': 'omni-prod',
        'OMNI_SECRET_KEY': 'k-prod'}


class IsolationTests(unittest.TestCase):
    def test_same_neon_endpoint_pooled_or_direct_is_shared(self):
        prev = {**PROD, 'OMNI_DATABASE_URL': 'postgresql://u:other@ep-aaa.eu-central-1.aws.neon.tech/neondb', 'OMNI_S3_BUCKET': 'omni-prev'}
        out = compare(PROD, prev, ('production', 'preview'))
        self.assertEqual(out['resources']['database']['verdict'], 'SHARED')
        self.assertEqual(out['resources']['redis']['verdict'], 'SHARED')
        self.assertEqual(out['resources']['queues']['verdict'], 'SHARED')
        self.assertEqual(out['resources']['object_storage']['verdict'], 'ISOLATED')
        self.assertEqual(out['resources']['secrets_equality']['OMNI_SECRET_KEY'], 'SAME')
        self.assertFalse(out['all_isolated'])
        self.assertEqual(sorted(out['blocking']),
                         ['database', 'queues', 'redis', 'secrets_equality:OMNI_SECRET_KEY'])

    def test_different_logical_databases_on_same_service_instances_are_shared(self):
        other_db = {
            **PROD,
            'OMNI_DATABASE_URL': 'postgresql://test:fake@ep-aaa.eu-central-1.aws.neon.tech/staging',
            'OMNI_REDIS_URL': 'redis://:fake@good-owl-1.upstash.io:6379/4',
            'OMNI_S3_BUCKET': 'omni-prev',
        }
        out = compare(PROD, other_db, ('production', 'staging'))
        self.assertEqual(out['resources']['database']['verdict'], 'SHARED')
        self.assertEqual(out['resources']['redis']['verdict'], 'SHARED')
        self.assertEqual(out['resources']['queues']['verdict'], 'SHARED')
        self.assertFalse(out['all_isolated'])

    def test_fully_separate_environments_are_isolated(self):
        prev = {'OMNI_DATABASE_URL': 'postgresql://u:p@ep-zzz.neon.tech/preview', 'OMNI_REDIS_URL': 'rediss://d:p@other.upstash.io:6379',
                'OMNI_S3_ENDPOINT': 'https://acct.r2.cloudflarestorage.com', 'OMNI_S3_BUCKET': 'omni-prev', 'OMNI_SECRET_KEY': 'k-prev'}
        out = compare(PROD, prev)
        self.assertTrue(out['all_isolated'], out)

    def test_missing_values_are_unknown_never_isolated(self):
        out = compare(PROD, {'OMNI_DATABASE_URL': 'postgresql://u:p@ep-zzz.neon.tech/preview'})
        self.assertEqual(out['resources']['redis']['verdict'], 'UNKNOWN')
        self.assertEqual(out['resources']['object_storage']['verdict'], 'UNKNOWN')
        self.assertFalse(out['all_isolated'])

    def test_staging_must_be_isolated_from_both_existing_environments(self):
        staging = {
            'OMNI_ENV': 'staging',
            'OMNI_DATABASE_URL': 'postgresql://test:fake@ep-stage.neon.tech/staging',
            'OMNI_REDIS_URL': 'redis://:fake@stage.upstash.io:6379',
            'OMNI_S3_ENDPOINT': 'https://stage.r2.cloudflarestorage.com',
            'OMNI_S3_BUCKET': 'omni-stage',
            'OMNI_SECRET_KEY': 'k-stage',
        }
        production = {**PROD, 'OMNI_ENV': 'production'}
        preview = {
            **PROD,
            'OMNI_ENV': 'preview',
            'OMNI_DATABASE_URL': 'postgresql://test:fake@ep-preview.neon.tech/preview',
            'OMNI_REDIS_URL': 'redis://:fake@preview.upstash.io:6379',
            'OMNI_S3_BUCKET': 'omni-preview',
            'OMNI_SECRET_KEY': 'k-preview',
        }
        result = compare_staging(staging, production, preview)
        self.assertTrue(result['all_isolated'], result)
        self.assertEqual(set(result['comparisons']), {'staging_vs_production', 'staging_vs_preview'})

    def test_staging_sharing_either_target_or_missing_staging_label_blocks(self):
        staging = {
            'OMNI_ENV': 'staging',
            'OMNI_DATABASE_URL': 'postgresql://test:fake@ep-aaa.eu-central-1.aws.neon.tech/staging',
            'OMNI_REDIS_URL': 'redis://:fake@stage.upstash.io:6379',
            'OMNI_S3_ENDPOINT': 'https://stage.r2.cloudflarestorage.com',
            'OMNI_S3_BUCKET': 'omni-stage',
            'OMNI_SECRET_KEY': 'k-stage',
        }
        production = {**PROD, 'OMNI_ENV': 'production'}
        preview = {
            **PROD,
            'OMNI_ENV': 'preview',
            'OMNI_DATABASE_URL': 'postgresql://test:fake@ep-aaa-pooler.eu-central-1.aws.neon.tech/preview',
            'OMNI_REDIS_URL': 'redis://:fake@preview.upstash.io:6379',
            'OMNI_S3_BUCKET': 'omni-preview',
            'OMNI_SECRET_KEY': 'k-preview',
        }
        result = compare_staging(staging, production, preview)
        self.assertFalse(result['all_isolated'])
        self.assertIn('staging_vs_preview:database', result['blocking'])
        staging.pop('OMNI_ENV')
        result = compare_staging(staging, production, preview)
        self.assertIn('OMNI_ENV must be exactly staging', result['blocking'])

    def test_three_environment_cli_requires_and_checks_staging_label(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = {
                'staging': 'OMNI_ENV=staging\nOMNI_DATABASE_URL=postgresql://u:p@staging-db.example/stage\n'
                           'OMNI_REDIS_URL=redis://u:p@staging-redis.example:6379\n'
                           'OMNI_S3_ENDPOINT=https://stage.example\nOMNI_S3_BUCKET=stage\nOMNI_SECRET_KEY=s1\n',
                'production': 'OMNI_ENV=production\nOMNI_DATABASE_URL=postgresql://u:p@prod-db.example/prod\n'
                              'OMNI_REDIS_URL=redis://u:p@prod-redis.example:6379\n'
                              'OMNI_S3_ENDPOINT=https://prod.example\nOMNI_S3_BUCKET=prod\nOMNI_SECRET_KEY=s2\n',
                'preview': 'OMNI_ENV=preview\nOMNI_DATABASE_URL=postgresql://u:p@preview-db.example/preview\n'
                           'OMNI_REDIS_URL=redis://u:p@preview-redis.example:6379\n'
                           'OMNI_S3_ENDPOINT=https://preview.example\nOMNI_S3_BUCKET=preview\nOMNI_SECRET_KEY=s3\n',
            }
            files = {}
            for name, content in values.items():
                files[name] = root / f'{name}.env'
                files[name].write_text(content, encoding='utf-8')
            args = []
            for name in ('staging', 'production', 'preview'):
                args.extend(('--env-file', str(files[name]), '--label', name))
            output = StringIO()
            with redirect_stdout(output):
                result = main(args + ['--fingerprints'])
        self.assertEqual(result, 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report['all_isolated'])
        db_row = report['comparisons']['staging_vs_production']['resources']['database']
        self.assertEqual(len(db_row['staging_fingerprint']), 64)
        self.assertEqual(len(db_row['production_fingerprint']), 64)
        self.assertNotIn('staging-db.example', output.getvalue())
        self.assertNotIn('prod-db.example', output.getvalue())
        self.assertNotIn('preview-db.example', output.getvalue())
        self.assertNotIn('u:p', output.getvalue())

    def test_disagreeing_variables_on_one_side_are_unknown(self):
        env = {**PROD, 'DATABASE_URL': 'postgresql://u:p@ep-different.neon.tech/neondb'}
        ids, notes = identities(env)
        self.assertIsNone(ids['database'])
        self.assertTrue(notes)

    def test_no_secret_value_is_ever_printed(self):
        text = json.dumps(compare(PROD, PROD))
        for secret in ('SECRETPW1', 'SECRETPW2', 'k-prod'):
            self.assertNotIn(secret, text)

    def test_dotenv_parser(self):
        env = parse_env('# c\nexport A="x y"\nB=\'z\'\nC=1\n')
        self.assertEqual(env, {'A': 'x y', 'B': 'z', 'C': '1'})


if __name__ == '__main__':
    unittest.main()
