"""Preview/Production isolation verdicts from non-secret identities; secrets never appear in the output."""
import json
import unittest

from omni_prod.isolation_check import compare, identities, parse_env

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
        self.assertEqual(sorted(out['blocking']), ['database', 'queues', 'redis'])

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
