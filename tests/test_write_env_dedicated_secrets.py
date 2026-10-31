"""OMNI_DATABASE_URL (and the provider keys) from their own GitHub secrets.

When the dedicated secret is set it REPLACES the value from WORKER_ENV(_OVERRIDES); when it is empty the
WORKER_ENV value stays. The value is never printed. deploy-worker.yml passes the secret to write-env.sh.
The real infra/worker-host/write-env.sh runs on a copy in a temporary directory, as in
test_write_env_secret_lengths.py.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'infra' / 'worker-host'
WORKFLOW = ROOT / '.github' / 'workflows' / 'deploy-worker.yml'
R2 = 'https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com'
OLD_DB = 'postgresql://old_user:OLDPASSWORDxyz@old-host.example/db'
NEW_DB = 'postgresql://new_user:NEWPASSWORDabc@new-host.example/db?sslmode=require'


def worker_env(**over):
    v = {'OMNI_ENV': 'staging', 'OMNI_S3_ENDPOINT': R2, 'OMNI_S3_BUCKET': 'omni-artifacts',
         'OMNI_S3_ACCESS_KEY': 'a' * 32, 'OMNI_S3_SECRET_KEY': 'b' * 64, 'OMNI_SANDBOX_SHARED_SECRET': 's' * 40,
         'OMNI_MODEL_CATALOG_JSON': '[]', 'OMNI_PREVIEW_HOST_SUFFIX': '127-0-0-1.sslip.io',
         'OMNI_PREVIEW_RUNTIME_HOST': 'test-host', 'OMNI_INTAKE_MODEL': '0'}
    v.update(over)
    return '\n'.join(f'{k}={x}' for k, x in v.items() if x is not None)


def run(extra_env=None, overrides=None, **over):
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(HOST / 'write-env.sh', d)
        shutil.copy(HOST / 'model-catalog.json', d)
        env = {'PATH': os.environ['PATH'], 'HOME': d, 'WORKER_ENV': worker_env(**over), 'GITHUB_SHA': 'test'}
        if overrides:
            env['WORKER_ENV_OVERRIDES'] = overrides
        env.update(extra_env or {})
        p = subprocess.run(['bash', os.path.join(d, 'write-env.sh')], env=env, capture_output=True, text=True, timeout=60)
        dotenv = Path(d, '.env').read_text() if Path(d, '.env').exists() else ''
        return p.returncode, p.stdout + p.stderr, dotenv


def values(dotenv, name):
    return [line.split('=', 1)[1] for line in dotenv.splitlines() if line.startswith(name + '=')]


class DatabaseUrlSecret(unittest.TestCase):
    def test_secret_replaces_the_worker_env_value(self):
        code, out, dotenv = run({'OMNI_DATABASE_URL': NEW_DB}, OMNI_DATABASE_URL=OLD_DB)
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_DATABASE_URL'), [NEW_DB])     # exactly one line, the secret's
        self.assertIn('OMNI_DATABASE_URL from its GitHub secret (replaced the WORKER_ENV(_OVERRIDES) value)', out)

    def test_secret_also_replaces_an_overrides_value(self):
        code, out, dotenv = run({'OMNI_DATABASE_URL': NEW_DB}, overrides=f'OMNI_DATABASE_URL={OLD_DB}')
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_DATABASE_URL'), [NEW_DB])

    def test_secret_added_when_worker_env_has_none(self):
        code, out, dotenv = run({'OMNI_DATABASE_URL': NEW_DB})
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_DATABASE_URL'), [NEW_DB])
        self.assertIn('OMNI_DATABASE_URL from its GitHub secret (added)', out)

    def test_without_secret_the_worker_env_value_stays(self):
        code, out, dotenv = run(OMNI_DATABASE_URL=OLD_DB)
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_DATABASE_URL'), [OLD_DB])
        self.assertIn('OMNI_DATABASE_URL already present in WORKER_ENV(_OVERRIDES); its GitHub secret was not used', out)

    def test_was_not_used_appears_only_without_a_secret(self):
        for name in ('OMNI_DATABASE_URL', 'OPENAI_API_KEY'):
            code, out, _ = run({name: 'secret-value-123'}, **{name: 'worker-env-value-456'})
            self.assertEqual(code, 0, out)
            line = next(l for l in out.splitlines() if 'dedicated secrets::' + name in l)
            self.assertNotIn('was not used', line)

    def test_value_is_never_printed(self):
        for kw in ({'extra_env': {'OMNI_DATABASE_URL': NEW_DB}, 'OMNI_DATABASE_URL': OLD_DB},
                   {'OMNI_DATABASE_URL': OLD_DB}):
            code, out, _ = run(**kw)
            self.assertEqual(code, 0, out)
            for secret in ('NEWPASSWORDabc', 'OLDPASSWORDxyz', 'new-host.example', 'old-host.example'):
                self.assertNotIn(secret, out)


class ProviderKeySecret(unittest.TestCase):
    def test_provider_key_secret_now_replaces_the_worker_env_value(self):
        code, out, dotenv = run({'ANTHROPIC_API_KEY': 'sk-new-zzz'}, ANTHROPIC_API_KEY='sk-old-yyy')
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'ANTHROPIC_API_KEY'), ['sk-new-zzz'])
        self.assertNotIn('sk-new-zzz', out)
        self.assertNotIn('sk-old-yyy', out)


class WorkflowPassesTheSecret(unittest.TestCase):
    def test_deploy_worker_passes_omni_database_url_to_write_env(self):
        text = WORKFLOW.read_text()
        step = re.search(r'- name: Write environment file\n(.*?)run: bash infra/worker-host/write-env.sh', text, re.S)
        self.assertIsNotNone(step)
        self.assertIn('OMNI_DATABASE_URL: ${{ secrets.OMNI_DATABASE_URL }}', step.group(1))

    def test_write_env_loop_lists_omni_database_url(self):
        script = (HOST / 'write-env.sh').read_text()
        loop = re.search(r'^for key_name in (.+); do$', script, re.M)
        self.assertIsNotNone(loop)
        self.assertIn('OMNI_DATABASE_URL', loop.group(1).split())


if __name__ == '__main__':
    unittest.main()
