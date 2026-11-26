"""The system map (the owner's plan v3, S1.5; AGENTS.md rule 3; the review of #532, 2026-11-25).

What is committed is only the mapping (docs/SYSTEM_MAP.md), which depends on omni_prod/system_map.py alone: no other
pull request can make it stale. The full map is generated in CI (v24-ci, job `light`: the artifact `system-map` and the
run summary) and locally into a file git ignores. Here: the committed docs equal the render of the mapping; building the
full map works and gives the same map twice; the states follow the mapping (blocked wins, a unit test is not a
connection, LIVE is never derived); and the inventory reads what the code really does."""
from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from unittest import mock

import yaml

from omni_prod import system_map as S

MAP = S.build()                                       # built once: every test below reads the same map


def tree(**modules: str) -> dict:
    """Synthetic sources in the shape S._sources() gives: {module: (path, tree)}."""
    return {name: (name.replace('.', '/') + '.py', ast.parse(src)) for name, src in modules.items()}


class TheCommittedDocs(unittest.TestCase):
    def test_the_committed_docs_are_the_render_of_the_mapping(self):
        self.assertEqual(S.MD_OUT.read_text(encoding='utf-8'), S.render_mapping(),
                         'docs/SYSTEM_MAP.md is stale: python -m omni_prod.system_map --write')
        self.assertEqual(S.main(['--check']), 0)

    def test_the_docs_never_read_the_inventory(self):
        # a pull request that adds a route, a workflow or an env read must not stale the committed file
        with mock.patch.object(S, 'build', side_effect=AssertionError('the inventory was read')):
            self.assertEqual(S.render_mapping(), S.MD_OUT.read_text(encoding='utf-8'))
            self.assertEqual(S.main(['--check']), 0)
        docs = S.render_mapping()
        for word, state in S.PLAN_STATE.items():
            self.assertIn(f'| {word} | {state} |', docs)
        self.assertIn('artifact `system-map`', docs)
        self.assertIn('python -m omni_prod.system_map --write', docs)

    def test_the_full_map_is_not_committed(self):
        ignored = (S.ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
        self.assertIn('/SYSTEM_MAP.json', ignored)
        self.assertEqual(S.JSON_LOCAL, S.ROOT / 'SYSTEM_MAP.json')


class TheFullMap(unittest.TestCase):
    def test_building_twice_gives_the_same_map(self):
        self.assertEqual(S.to_json(S.build()), S.to_json(MAP))

    def test_the_command_line_writes_the_map_and_the_summary(self):
        with tempfile.TemporaryDirectory() as d:
            out, summary = os.path.join(d, 'map.json'), os.path.join(d, 'summary.md')
            with mock.patch.object(S, 'build', return_value=MAP):       # the build itself is tested above
                self.assertEqual(S.main(['--json', out, '--summary', summary]), 0)
            with open(out, encoding='utf-8') as fh:
                self.assertEqual(json.load(fh), json.loads(S.to_json(MAP)))
            with open(summary, encoding='utf-8') as fh:
                text = fh.read()
        self.assertIn('| models (PROVIDER_MATRIX) |', text)
        self.assertIn(f'| endpoints | {MAP["summary"]["endpoints"]} |', text)
        self.assertIn('artifact `system-map`', text)

    def test_ci_publishes_it_on_every_push_and_pull_request(self):
        wf = yaml.safe_load((S.ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8'))
        on = wf[True]
        self.assertIn('pull_request', on)
        self.assertIn('main', on['push']['branches'])
        job = wf['jobs']['light']
        self.assertNotIn('if', job)
        [make] = [s for s in job['steps'] if 'omni_prod.system_map' in s.get('run', '')]
        self.assertIn('python -m omni_prod.system_map --json system-map/SYSTEM_MAP.json --summary '
                      '"$GITHUB_STEP_SUMMARY"', make['run'])
        self.assertIn('set -euo pipefail', make['run'])
        [keep] = [s for s in job['steps'] if str(s.get('uses', '')).startswith('actions/upload-artifact')]
        self.assertEqual(keep['with']['name'], 'system-map')
        self.assertEqual(keep['with']['path'], 'system-map/SYSTEM_MAP.json')
        self.assertEqual(keep['with']['if-no-files-found'], 'error')
        for step in (make, keep):
            self.assertNotIn('continue-on-error', step)          # a failing generator fails the step loudly
        self.assertNotIn('continue-on-error', job)


class TheStates(unittest.TestCase):
    def test_every_word_a_source_uses_has_a_state(self):
        for section in ('agents', 'roles', 'skills', 'models'):
            for row in MAP[section]:
                with self.subTest(section=section, key=row['key']):
                    self.assertIn(row['source_status'], S.PLAN_STATE)
                    self.assertIn(row['state'], S.PLAN_STATES)

    def test_an_unknown_word_raises(self):
        with self.assertRaises(ValueError):
            S.plan_state('ALMOST_DONE')

    def test_the_mapping_of_the_plan(self):
        self.assertEqual(S.plan_state('DEFINED'), 'NOT_IMPLEMENTED')
        self.assertEqual(S.plan_state('TESTED'), 'IMPLEMENTED')
        self.assertEqual(S.plan_state('UNIT_TESTED'), 'IMPLEMENTED')        # a test is not an execution check
        self.assertEqual(S.plan_state('STALE'), 'IMPLEMENTED')              # stale is never LIVE, nor VERIFIED
        self.assertEqual(S.plan_state('REAL_SERVER_VERIFIED'), 'VERIFIED')
        self.assertEqual(S.plan_state('CONNECTION_TESTED'), 'CONNECTED')
        self.assertEqual(S.plan_state('IMPLEMENTED', gaps=True), 'PARTIAL')  # the plan: PARTIAL follows the gap list
        self.assertEqual(S.plan_state('CONNECTED', gaps=True), 'PARTIAL')
        self.assertEqual(S.plan_state('VERIFIED', gaps=True), 'VERIFIED')
        for word in S.BLOCKED_WORDS:
            self.assertEqual(S.plan_state(word), 'PARTIAL', word)
            self.assertEqual(S.plan_state(word, has_code=False), 'NOT_IMPLEMENTED', word)

    def test_live_is_never_derived_here(self):
        self.assertNotIn('LIVE', set(S.PLAN_STATE.values()))
        for section in ('agents', 'roles', 'skills', 'models'):
            self.assertEqual(MAP['summary'][section]['LIVE'], 0, section)
        self.assertIn('younger than 7 days', MAP['live_rule'])

    def test_a_credential_alone_is_not_connected(self):
        matrix = {x['model_key']: x for x in json.loads((S.ROOT / 'PROVIDER_MATRIX.json').read_text())['models']}
        for row in MAP['models']:
            if row['state'] == 'CONNECTED':
                self.assertEqual(matrix[row['key']]['connection_state'], 'CONNECTION_TESTED', row['key'])
        row = {'implementation_status': 'IMPLEMENTED', 'availability': 'NOT_ROUTED', 'health': 'UNKNOWN',
               'connection_state': 'NOT_CONNECTED', 'verification_state': 'UNVERIFIED',
               'credential_state': 'CREDENTIAL_PRESENT'}
        self.assertEqual(S.model_word(row), ('IMPLEMENTED', []))


class BlockedWins(unittest.TestCase):
    BASE = {'implementation_status': 'IMPLEMENTED', 'availability': 'AVAILABLE', 'health': 'HEALTHY',
            'connection_state': 'CONNECTION_TESTED', 'verification_state': 'REAL_EXECUTION_VERIFIED'}

    def test_blocked_wins_over_connection_and_verification(self):
        cases = [({'implementation_status': 'BLOCKED'}, 'BLOCKED'),
                 ({'health': 'CREDIT_EXHAUSTED'}, 'CREDIT_EXHAUSTED'),
                 ({'availability': 'INSUFFICIENT_CREDIT'}, 'INSUFFICIENT_CREDIT')]
        for change, word in cases:
            for verification in ('REAL_EXECUTION_VERIFIED', 'UNVERIFIED'):
                with self.subTest(change=change, verification=verification):
                    got, blocked_by = S.model_word({**self.BASE, **change, 'verification_state': verification})
                    self.assertEqual(got, word)
                    self.assertTrue(blocked_by)
                    self.assertEqual(S.plan_state(got), 'PARTIAL')
        self.assertEqual(S.model_word(self.BASE), ('REAL_EXECUTION_VERIFIED', []))

    def test_no_blocked_model_of_the_matrix_is_connected_or_verified(self):
        matrix = {x['model_key']: x for x in json.loads((S.ROOT / 'PROVIDER_MATRIX.json').read_text())['models']}
        for row in MAP['models']:
            m = matrix[row['key']]
            if (m['implementation_status'] == 'BLOCKED' or m['availability'] == 'INSUFFICIENT_CREDIT'
                    or m['health'] == 'CREDIT_EXHAUSTED'):
                with self.subTest(model=row['key']):
                    self.assertIn(row['state'], ('PARTIAL', 'NOT_IMPLEMENTED'))
                    self.assertTrue(row['blocked_by'])


class AUnitTestIsNotAConnection(unittest.TestCase):
    def test_a_role_with_unit_tests_only_is_not_connected(self):
        unit_only = type('B', (), {'config': ()})()
        configured = type('B', (), {'config': ('a requirement',)})()
        self.assertEqual(S.role_word('CONNECTED', unit_only), 'UNIT_TESTED')
        self.assertEqual(S.role_word('CONNECTED', configured), 'CONNECTED')
        self.assertEqual(S.role_word('VERIFIED', unit_only), 'VERIFIED')
        from omni_prod.runtime_bindings import BY_ROLE
        for row in MAP['roles']:
            binding = BY_ROLE.get(row['key'])
            if row['source_status'] == 'CONNECTED' and binding is not None and not binding.config:
                with self.subTest(role=row['key']):
                    self.assertNotEqual(row['state'], 'CONNECTED')
                    self.assertEqual(row['read_as'], 'UNIT_TESTED')


class TheInventoryIsReadFromTheCode(unittest.TestCase):
    def test_endpoints_are_the_route_decorators(self):
        rows = MAP['endpoints']
        self.assertGreater(len(rows), 150)
        status = [r for r in rows if r['path'] == '/api/status' and r['method'] == 'GET']
        self.assertEqual(len(status), 1)
        source = (S.ROOT / status[0]['file']).read_text(encoding='utf-8')
        self.assertRegex(source, r"@app\.get\('/api/status'\)\s*\n\s*(async )?def " + status[0]['handler'] + r'\(')
        self.assertNotIn('line', status[0])                  # a moved line must not change the map

    def test_endpoints_carry_the_router_prefix(self):
        paths = {(r['method'], r['path']) for r in MAP['endpoints']}
        self.assertIn(('GET', '/_omni/health/live'), paths)     # api_routes.py: APIRouter(prefix="/_omni")
        self.assertIn(('GET', '/_omni/health/ready'), paths)
        self.assertNotIn(('GET', '/health/live'), paths)
        src = tree(**{'omni_prod.r': 'from fastapi import APIRouter\n'
                                     'def make():\n    router = APIRouter(prefix="/v1")\n'
                                     '    @router.get("/items")\n    def items(): pass\n    return router\n',
                      'omni_prod.app': 'from .r import make\napp.include_router(make(), prefix="/api")\n'
                                       '@app.get("/ping")\ndef ping(): pass\n'})
        self.assertEqual([(r['method'], r['path']) for r in S.endpoints(src)], [('GET', '/api/v1/items'),
                                                                                ('GET', '/ping')])
        unknown = tree(**{'omni_prod.app': 'app.include_router(somewhere.router, prefix="/api")\n'})
        with self.assertRaises(ValueError):
            S.endpoints(unknown)

    def test_a_queue_prefix_is_not_a_queue(self):
        names = [q['name'] for q in MAP['queues']]
        self.assertIn('omni-builds', names)
        self.assertIn('omni-intake', names)
        self.assertFalse([n for n in names if n.endswith('-')], names)
        self.assertIn('omni-preview-host-', [p['prefix'] for p in MAP['queue_prefixes']])

    def test_tables_migrations_and_rollbacks(self):
        db = MAP['database']
        self.assertIn('build_jobs', [t['name'] for t in db['tables']])
        self.assertEqual(db['highest'], sorted(db['migrations'])[-1])
        self.assertTrue(set(db['rollback_files']))

    def test_environment_holds_names_only(self):
        env = MAP['environment']
        self.assertTrue(all(set(e) == {'name', 'read_in'} for e in env))
        self.assertIn('OMNI_ENV', [e['name'] for e in env])
        method = MAP['environment_method']
        self.assertEqual(method['unresolved'], len(method['unresolved_at']))
        self.assertEqual(MAP['summary']['environment_names'], len(env))

    def test_environment_names_through_constants_helpers_and_mappings(self):
        names = {e['name']: e['read_in'] for e in MAP['environment']}
        pinned = {'OMNI_SITE_LIBRARY': 'omni_prod/site_content/__init__.py',     # FLAG = ...; os.environ.get(FLAG)
                  'OMNI_DB_POOL_MAX_SIZE': 'omni_prod/config.py',                 # _int("...", 10) -> os.getenv(name)
                  'OMNI_WORKER_QUEUES': 'omni_prod/worker.py',                    # env.get("...") on an injected env
                  'GEMINI_API_KEY': 'omni_prod/providers/google_image.py',        # self.env['...']
                  'OMNI_INTAKE_DAILY_BUDGET_USD': 'omni_prod/intake/mode.py',     # _money('...')
                  'OMNI_PROVIDER_CAP_PRO_USD': 'omni_prod/pricing.py'}            # _env_decimal('...')
        for name, where in pinned.items():
            with self.subTest(name=name):
                self.assertIn(name, names)
                self.assertIn(where, names[name])
        helpers = MAP['environment_method']['helpers']
        for helper in ('omni_prod.config._int(name)', 'omni_prod.pricing._env_decimal(name)',
                       'omni_prod.feature_flags._on(name)'):
            self.assertIn(helper, helpers)
        self.assertNotIn('PORT', names)              # read only inside code that omni_prod writes for generated apps

    def test_the_env_reader_on_synthetic_modules(self):
        src = tree(**{
            'omni_prod.a': "import os\nFLAG = 'OMNI_A'\nNAMES = ('OMNI_T1', 'OMNI_T2')\n"
                           "def f():\n    return os.environ.get(FLAG)\n"
                           "def g():\n    return [os.getenv(n) for n in NAMES]\n"
                           "def built(x):\n    return os.getenv(f'OMNI_{x}')\n",
            'omni_prod.b': "import os\nfrom .a import FLAG as F\n"
                           "def _int(name, default):\n    return int(os.getenv(name) or default)\n"
                           "def _twice(key):\n    return _int(key, 1)\n"
                           "def _either(name, old):\n    for k in (name, old):\n        if os.getenv(k): return k\n"
                           "def _all(required):\n    return [n for n in required if not os.getenv(n)]\n"
                           "X = _twice('OMNI_B') + _int('OMNI_C', 2)\nY = _either('OMNI_NEW', 'OMNI_OLD')\n"
                           "Z = _all(('OMNI_R1', 'OMNI_R2'))\nW = os.environ[F]\n",
            'omni_prod.c': "def _int(problems, where):\n    problems.append(where)\n"
                           "_int(['OMNI_NOT_ENV'], 'x')\n"})
        found = S.env_reads(src)
        self.assertEqual(set(found['names']), {'OMNI_A', 'OMNI_T1', 'OMNI_T2', 'OMNI_B', 'OMNI_C', 'OMNI_NEW',
                                               'OMNI_OLD', 'OMNI_R1', 'OMNI_R2'})
        self.assertEqual(found['names']['OMNI_A'], {'omni_prod/a.py', 'omni_prod/b.py'})
        self.assertEqual(found['unresolved'], ['omni_prod/a.py:9'])            # the f-string, counted, not guessed
        self.assertIn('omni_prod.b._twice(key)', found['helpers'])
        self.assertNotIn('omni_prod.c._int(problems)', found['helpers'])     # same name, another module

    def test_relative_imports_resolve_as_python_does(self):
        cases = [('omni_prod.g_apple.reviewers', 'from ..feature_flags import x', ['omni_prod.feature_flags']),
                 ('omni_prod.g_apple.__init__', 'from . import contract', ['omni_prod.g_apple.contract']),
                 ('omni_prod.intake.agent', 'from ..conversation.supervisor import X',
                  ['omni_prod.conversation.supervisor'])]
        for module, src, want in cases:
            self.assertEqual(S.resolve(module, ast.parse(src).body[0]), want, src)


if __name__ == '__main__':
    unittest.main()
