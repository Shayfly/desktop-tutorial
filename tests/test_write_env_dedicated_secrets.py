"""OMNI_DATABASE_URL (and the provider keys) from their own GitHub secrets.

When the dedicated secret is set it REPLACES the value from WORKER_ENV(_OVERRIDES); when it is empty the
WORKER_ENV value stays. The value is never printed. deploy-worker.yml passes the secret to write-env.sh.
The real infra/worker-host/write-env.sh runs on a copy in a temporary directory, as in
test_write_env_secret_lengths.py.
"""
import json
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


class ReplicateTokenSecret(unittest.TestCase):
    """#324 (Michael 2026-11-12): a real build makes its image on the worker, whose .env had no REPLICATE_API_TOKEN
    (deploy 274ad82 listed no such name), so media.image stayed NOT_CONFIGURED in every build. The token arrives as
    its own GitHub secret, like the other provider keys."""

    def test_the_secret_is_written_once_and_never_printed(self):
        token = 'r8_' + 'Q' * 37
        code, out, dotenv = run({'REPLICATE_API_TOKEN': token}, REPLICATE_API_TOKEN='r8_' + 'o' * 37)
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'REPLICATE_API_TOKEN'), [token])
        self.assertIn('REPLICATE_API_TOKEN from its GitHub secret (replaced the WORKER_ENV(_OVERRIDES) value)', out)
        self.assertNotIn('QQQQ', out)
        self.assertNotIn('oooo', out)

    def test_without_it_the_log_says_images_stay_not_configured(self):
        code, out, dotenv = run()
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'REPLICATE_API_TOKEN'), [])
        self.assertIn('REPLICATE_API_TOKEN not set; image generation in builds stays NOT_CONFIGURED', out)
        self.assertNotIn('REPLICATE_API_TOKEN not set; its catalog models', out)


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



OLD_REDIS = 'rediss://default:OLDREDISPASSxyz@old-satyr-1.upstash.io:6379'
NEW_REDIS = 'rediss://default:NEWREDISPASSabc@new-otter-2.upstash.io:6379'


class RedisUrlSecret(unittest.TestCase):
    """Founder 2026-11-01 19:18: OMNI_REDIS_URL becomes a dedicated secret. WORKER_ENV_OVERRIDES cannot be safely
    re-saved (its 14 values are unreadable), so the new Redis arrives as its own secret and must win."""

    def test_secret_replaces_the_worker_env_value(self):
        code, out, dotenv = run({'OMNI_REDIS_URL': NEW_REDIS}, OMNI_REDIS_URL=OLD_REDIS)
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_REDIS_URL'), [NEW_REDIS])          # exactly one line, the secret's
        self.assertIn('OMNI_REDIS_URL from its GitHub secret (replaced the WORKER_ENV(_OVERRIDES) value)', out)

    def test_secret_also_replaces_an_overrides_value_and_keeps_the_other_overrides(self):
        code, out, dotenv = run({'OMNI_REDIS_URL': NEW_REDIS},
                                overrides=f'OMNI_REDIS_URL={OLD_REDIS}\nOMNI_S3_BUCKET=override-bucket')
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_REDIS_URL'), [NEW_REDIS])
        self.assertEqual(values(dotenv, 'OMNI_S3_BUCKET'), ['override-bucket'])

    def test_without_secret_the_worker_env_value_stays(self):
        code, out, dotenv = run(OMNI_REDIS_URL=OLD_REDIS)
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_REDIS_URL'), [OLD_REDIS])
        self.assertIn('OMNI_REDIS_URL already present in WORKER_ENV(_OVERRIDES); its GitHub secret was not used', out)

    def test_neither_set_says_so(self):
        code, out, dotenv = run()
        self.assertEqual(code, 0, out)
        self.assertEqual(values(dotenv, 'OMNI_REDIS_URL'), [])
        self.assertIn('OMNI_REDIS_URL not set in its GitHub secret nor in WORKER_ENV(_OVERRIDES)', out)
        self.assertNotIn('OMNI_REDIS_URL not set; its catalog models', out)          # not the provider-key wording

    def test_value_is_never_printed(self):
        code, out, _ = run({'OMNI_REDIS_URL': NEW_REDIS}, OMNI_REDIS_URL=OLD_REDIS)
        self.assertEqual(code, 0, out)
        for secret in ('NEWREDISPASSabc', 'OLDREDISPASSxyz', 'new-otter-2', 'old-satyr-1'):
            self.assertNotIn(secret, out)

    def test_deploy_worker_passes_the_secret_and_the_loop_lists_it(self):
        step = re.search(r'- name: Write environment file\n(.*?)run: bash infra/worker-host/write-env.sh',
                         WORKFLOW.read_text(), re.S)
        self.assertIn('OMNI_REDIS_URL: ${{ secrets.OMNI_REDIS_URL }}', step.group(1))
        loop = re.search(r'^for key_name in (.+); do$', (HOST / 'write-env.sh').read_text(), re.M)
        self.assertIn('OMNI_REDIS_URL', loop.group(1).split())



def dedicated_names() -> list[str]:
    """The dedicated secrets, read from write-env.sh's own loop (the script is the source of truth)."""
    loop = re.search(r'^for key_name in (.+); do$', (HOST / 'write-env.sh').read_text(), re.M)
    return loop.group(1).split()


def steps_running_write_env(workflow: dict):
    for job_name, job in (workflow.get('jobs') or {}).items():
        for i, step in enumerate(job.get('steps') or []):
            if 'write-env.sh' in str(step.get('run') or ''):
                yield f"{job_name}/{step.get('name') or i}", step


def missing_dedicated_secrets(workflow: dict) -> list[str]:
    """Every step that runs write-env.sh must pass each dedicated secret as NAME: ${{ secrets.NAME }}."""
    problems = []
    for where, step in steps_running_write_env(workflow):
        env = step.get('env') or {}
        for name in dedicated_names():
            if str(env.get(name, '')).replace(' ', '') != '${{secrets.%s}}' % name:
                problems.append(f'{where}: {name}')
    return problems


class EveryWorkflowPassesTheDedicatedSecrets(unittest.TestCase):
    """Founder 2026-11-01 19:24: a workflow that runs write-env.sh without the dedicated secrets rewrites the host's
    .env with the WORKER_ENV values (e.g. the exhausted Redis). The test fails such a workflow; documentation does not."""

    def workflows(self):
        import yaml
        return {p.name: yaml.safe_load(p.read_text()) for p in sorted((ROOT / '.github' / 'workflows').glob('*.y*ml'))}

    def test_the_five_names_come_from_the_script(self):
        self.assertEqual(dedicated_names(), ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'VENICE_API_KEY1',
                                             'REPLICATE_API_TOKEN', 'OMNI_DATABASE_URL', 'OMNI_REDIS_URL'])

    def test_every_workflow_that_runs_write_env_passes_all_of_them(self):
        runners = {name: [w for w, _ in steps_running_write_env(wf)] for name, wf in self.workflows().items()}
        runners = {k: v for k, v in runners.items() if v}
        print('\n[write-env.sh callers] ' + json.dumps(runners))
        self.assertEqual(sorted(runners), ['148ai-prototype-intake-enable.yml', 'deploy-worker.yml',
                                           'internal-entitlement.yml'])           # a new caller must be added here
        problems = {name: missing_dedicated_secrets(wf) for name, wf in self.workflows().items()}
        self.assertEqual({k: v for k, v in problems.items() if v}, {})

    def test_negative_control_a_caller_without_one_secret_is_caught(self):
        env = {n: '${{ secrets.%s }}' % n for n in dedicated_names()}
        good = {'jobs': {'j': {'steps': [{'name': 'Write environment file', 'env': dict(env),
                                          'run': 'bash infra/worker-host/write-env.sh'}]}}}
        self.assertEqual(missing_dedicated_secrets(good), [])
        for drop in dedicated_names():
            bad = {'jobs': {'j': {'steps': [{'name': 'Write environment file',
                                             'env': {k: v for k, v in env.items() if k != drop},
                                             'run': 'bash infra/worker-host/write-env.sh'}]}}}
            self.assertEqual(missing_dedicated_secrets(bad), [f'j/Write environment file: {drop}'], drop)
        wrong = {'jobs': {'j': {'steps': [{'env': {**env, 'OMNI_REDIS_URL': '${{ secrets.WORKER_ENV }}'},
                                           'run': 'bash infra/worker-host/write-env.sh'}]}}}
        self.assertEqual(missing_dedicated_secrets(wrong), ['j/0: OMNI_REDIS_URL'])


if __name__ == '__main__':
    unittest.main()
