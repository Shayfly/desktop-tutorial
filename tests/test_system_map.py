"""The system map is derived, never hand-written (the owner's plan v3, S1.5; AGENTS.md rule 3).

SYSTEM_MAP.json and docs/SYSTEM_MAP.md must equal what `python -m omni_prod.system_map --write` gives from the code and
the existing registries. The plan's six states come from one mapping; an unknown status word raises; LIVE is never
derived from the repository."""
from __future__ import annotations

import ast
import json
import unittest

from omni_prod import system_map as S

MAP = S.build()                                       # built once: every test below reads the same map


class TheFilesAreCurrent(unittest.TestCase):
    def test_the_committed_map_is_what_the_code_gives(self):
        js, md = S.render(MAP)
        self.assertEqual(S.JSON_OUT.read_text(encoding='utf-8'), js,
                         'SYSTEM_MAP.json is stale: python -m omni_prod.system_map --write')
        self.assertEqual(S.MD_OUT.read_text(encoding='utf-8'), md)
        self.assertEqual(S.main(['--check']), 0)


class TheStates(unittest.TestCase):
    def test_every_word_a_source_uses_has_a_state(self):
        m = MAP
        for section in ('agents', 'roles', 'skills', 'models'):
            for row in m[section]:
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
        self.assertEqual(S.plan_state('BLOCKED'), 'PARTIAL')
        self.assertEqual(S.plan_state('BLOCKED', has_code=False), 'NOT_IMPLEMENTED')

    def test_live_is_never_derived_here(self):
        self.assertNotIn('LIVE', set(S.PLAN_STATE.values()))
        m = MAP
        for section in ('agents', 'roles', 'skills', 'models'):
            self.assertEqual(m['summary'][section]['LIVE'], 0, section)
        self.assertIn('younger than 7 days', m['live_rule'])

    def test_a_credential_alone_is_not_connected(self):
        m = {r['key']: r for r in MAP['models']}
        matrix = {x['model_key']: x for x in json.loads((S.ROOT / 'PROVIDER_MATRIX.json').read_text())['models']}
        for key, row in m.items():
            if row['state'] == 'CONNECTED':
                self.assertEqual(matrix[key]['connection_state'], 'CONNECTION_TESTED', key)


class TheInventoryIsReadFromTheCode(unittest.TestCase):
    def test_endpoints_are_the_route_decorators(self):
        rows = MAP['endpoints']
        self.assertGreater(len(rows), 150)
        status = [r for r in rows if r['path'] == '/api/status' and r['method'] == 'GET']
        self.assertEqual(len(status), 1)
        source = (S.ROOT / status[0]['file']).read_text(encoding='utf-8')
        self.assertRegex(source, r"@app\.get\('/api/status'\)\s*\n\s*(async )?def " + status[0]['handler'] + r'\(')
        self.assertNotIn('line', status[0])                  # a moved line must not stale the map

    def test_tables_migrations_and_rollbacks(self):
        db = MAP['database']
        self.assertIn({'name': 'build_jobs', 'created_in': db['tables'][[t['name'] for t in db['tables']].index('build_jobs')]['created_in']}, db['tables'])
        self.assertEqual(db['highest'], sorted(db['migrations'])[-1])
        self.assertTrue(set(db['rollback_files']))

    def test_environment_holds_names_only(self):
        env = MAP['environment']
        self.assertTrue(all(set(e) == {'name', 'read_in'} for e in env))
        self.assertIn('OMNI_ENV', [e['name'] for e in env])

    def test_relative_imports_resolve_as_python_does(self):
        cases = [('omni_prod.g_apple.reviewers', 'from ..feature_flags import x', ['omni_prod.feature_flags']),
                 ('omni_prod.g_apple.__init__', 'from . import contract', ['omni_prod.g_apple.contract']),
                 ('omni_prod.intake.agent', 'from ..conversation.supervisor import X',
                  ['omni_prod.conversation.supervisor'])]
        for module, src, want in cases:
            self.assertEqual(S.resolve(module, ast.parse(src).body[0]), want, src)


if __name__ == '__main__':
    unittest.main()
