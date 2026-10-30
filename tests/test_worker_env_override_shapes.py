"""Worker env read-back by shape (2026-10-27), print-only ::notice PASS|FAIL annotations, never a value:
override-shape per applied override line; venice-key (prefix + length band); database-url (eu-central-1 + ASCII)."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = 'OMNI_ENV=staging\nOMNI_SANDBOX_SHARED_SECRET=' + 'a' * 32 + '\nOMNI_SECRET_KEY=' + 'k' * 48
GOOD = {'OMNI_DATABASE_URL': 'postgresql://u:pw@ep-x-pooler.eu-central-1.aws.neon.tech/db?sslmode=require',
        'OMNI_S3_ACCESS_KEY': '0123456789abcdef' * 2, 'OMNI_S3_SECRET_KEY': '0123456789abcdef' * 4,
        'OMNI_PLAN_DRIVEN': '1', 'OMNI_INTAKE_PROVIDER': 'venice',
        'VENICE_API_KEY1': 'VENICE_INFERENCE_KEY_' + 'Z' * 40}


def run(overrides: dict, title='override-shape') -> list[str]:
    d = tempfile.mkdtemp()
    try:
        shutil.copy(ROOT / 'infra/worker-host/write-env.sh', d)
        env = {**os.environ, 'WORKER_ENV': BASE,
               'WORKER_ENV_OVERRIDES': '\n'.join(f'{k}={v}' for k, v in overrides.items())}
        out = subprocess.run(['bash', 'write-env.sh'], cwd=d, env=env, capture_output=True, text=True).stdout
        return [l for l in out.splitlines() if f'title={title}::' in l]
    finally:
        shutil.rmtree(d)


class OverrideShapes(unittest.TestCase):
    def test_six_expected_lines_all_ok_and_no_value_is_printed(self):
        lines = run(GOOD)
        self.assertEqual(len(lines), 6)
        self.assertTrue(all(l.startswith('::notice title=override-shape::PASS ') for l in lines), lines)
        joined = '\n'.join(lines)
        for name in ('OMNI_DATABASE_URL', 'OMNI_S3_ACCESS_KEY', 'OMNI_S3_SECRET_KEY', 'VENICE_API_KEY1'):
            self.assertNotIn(GOOD[name], joined)
            self.assertNotIn(GOOD[name][-12:], joined)
        self.assertIn('OMNI_S3_ACCESS_KEY len=32', joined)
        self.assertIn('OMNI_S3_SECRET_KEY len=64', joined)
        self.assertIn('region=eu-central-1', joined)
        self.assertIn('prefix=VENICE_INFERENCE_KEY_', joined)

    def test_each_wrong_shape_is_a_fail_notice(self):
        cases = {'OMNI_S3_ACCESS_KEY': GOOD['OMNI_S3_ACCESS_KEY'] + 'xy',
                 'OMNI_S3_SECRET_KEY': 'short',
                 'OMNI_DATABASE_URL': 'postgresql://u:pw@ep-x.us-east-2.aws.neon.tech/db',
                 'VENICE_API_KEY1': 'sk-' + 'Z' * 40}
        for name, bad in cases.items():
            with self.subTest(name=name):
                line = next(l for l in run({**GOOD, name: bad}) if f' {name} ' in l)
                self.assertTrue(line.startswith('::notice title=override-shape::FAIL '), line)
                self.assertNotIn(bad, line)

    def test_non_english_character_is_flagged(self):
        line = next(l for l in run({**GOOD, 'VENICE_API_KEY1': GOOD['VENICE_API_KEY1'] + 'ש'})
                    if ' VENICE_API_KEY1 ' in l)
        self.assertIn('ascii=NO', line)
        self.assertIn('::FAIL ', line)

    def test_venice_key_pass_and_each_fail(self):
        self.assertEqual(run(GOOD, 'venice-key'),
                         ['::notice title=venice-key::PASS prefix VENICE_INFERENCE_KEY_=PASS; length 61 in 40-128=PASS'])
        for bad, why in (('sk-' + 'Z' * 50, 'prefix VENICE_INFERENCE_KEY_=FAIL'),
                         ('VENICE_INFERENCE_KEY_abc', 'in 40-128=FAIL'),
                         ('VENICE_INFERENCE_KEY_' + 'Z' * 200, 'in 40-128=FAIL')):
            with self.subTest(why=why):
                (line,) = run({**GOOD, 'VENICE_API_KEY1': bad}, 'venice-key')
                self.assertTrue(line.startswith('::notice title=venice-key::FAIL '), line)
                self.assertIn(why, line)
                self.assertNotIn(bad, line)
        no_key = {k: v for k, v in GOOD.items() if k != 'VENICE_API_KEY1'}
        self.assertEqual(run(no_key, 'venice-key'), ['::notice title=venice-key::FAIL VENICE_API_KEY1 is not set'])

    def test_database_url_pass_and_each_fail(self):
        (line,) = run(GOOD, 'database-url')
        self.assertTrue(line.startswith('::notice title=database-url::PASS contains eu-central-1=PASS; '
                                        'non-ASCII characters=0 (PASS)'), line)
        self.assertNotIn('neon.tech', line)
        for bad, why in (('postgresql://u:pw@ep-x.us-east-2.aws.neon.tech/db', 'eu-central-1=FAIL'),
                         (GOOD['OMNI_DATABASE_URL'] + '\u05e9', 'non-ASCII characters=1 (FAIL)')):
            with self.subTest(why=why):
                (line,) = run({**GOOD, 'OMNI_DATABASE_URL': bad}, 'database-url')
                self.assertTrue(line.startswith('::notice title=database-url::FAIL '), line)
                self.assertIn(why, line)


if __name__ == '__main__':
    unittest.main()
