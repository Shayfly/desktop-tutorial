"""Agent OS / Skills OS (autonomous completion §6-15)."""
import os
import unittest
import uuid
from decimal import Decimal

from omni_prod.agent_os import audit, meta
from omni_prod.agent_os.agents import AGENTS, BY_KEY, SEPARATION_OF_DUTIES
from omni_prod.agent_os.contracts import LIVE, NOT_IMPLEMENTED
from omni_prod.agent_os.providers import BLOCKED, COMMERCIAL_APPROVED, DEV_ONLY, commercial_status, filter_routable
from omni_prod.agent_os.resolver import AVAILABLE, MISSING, resolve
from omni_prod.agent_os.runtime import PermissionEngine, RuntimeViolation, VerificationEngine
from omni_prod.agent_os.skills import SKILLS, TAXONOMY, UNKNOWN_IMPL_KEYS
from omni_prod.runtime_bindings import Evidence


class CatalogTests(unittest.TestCase):
    def test_all_agents_and_skills_of_the_directive_exist_with_full_contracts(self):
        self.assertEqual(len(AGENTS), 52)
        self.assertEqual(len(SKILLS), sum(len(v) for v in TAXONOMY.values()))
        self.assertEqual(len(TAXONOMY), 33)
        self.assertEqual(UNKNOWN_IMPL_KEYS, [])
        for a in AGENTS:
            self.assertEqual(a.missing_fields(), [], a.agent_key)
            for skill in a.allowed_skills:
                self.assertIn(skill, {s.skill_key for s in SKILLS}, (a.agent_key, skill))
        for s in SKILLS:
            self.assertEqual(s.missing_fields(), [], s.skill_key)

    def test_separation_of_duties_names_real_agents(self):
        for producer, verifiers in SEPARATION_OF_DUTIES.items():
            self.assertIn(producer, BY_KEY)
            for v in verifiers:
                self.assertIn(v, BY_KEY)


class AuditTests(unittest.TestCase):
    def test_committed_registry_is_current_and_not_inflated(self):
        result = audit.audit()
        self.assertEqual(audit.inflation_findings(result), [])
        committed = __import__('json').loads(audit.REGISTRY_JSON.read_text())
        self.assertEqual(committed['summary'], result['summary'],
                         'run python -m omni_prod.agent_os.audit --write')

    def test_live_requires_fresh_live_evidence(self):
        from omni_prod.agent_os.contracts import SkillContract
        base = next(s for s in SKILLS if s.skill_key == 'preview_access_protect')
        unit_only = SkillContract(**{**base.__dict__, 'evidence': (Evidence('unit', 'tests/x.py'),)})
        self.assertEqual(audit.status_of(unit_only, {})['status'], 'PARTIAL')
        no_code = SkillContract(**{**base.__dict__, 'implementation_location': ()})
        self.assertEqual(audit.status_of(no_code, {})['status'], NOT_IMPLEMENTED)
        broken = SkillContract(**{**base.__dict__, 'implementation_location': ('omni_prod.nope:Missing',)})
        self.assertEqual(audit.status_of(broken, {})['status'], NOT_IMPLEMENTED)
        blocked = SkillContract(**{**base.__dict__, 'blocked_by': 'no provider'})
        self.assertEqual(audit.status_of(blocked, {})['status'], 'BLOCKED')

    def test_unimplemented_families_are_not_live(self):
        result = {r['agent_key']: r['status'] for r in audit.audit()['agents']}
        for key in ('game_engineering_2d_agent', 'automation_agent', 'performance_agent', 'identity_auth_agent'):
            self.assertEqual(result[key], NOT_IMPLEMENTED, key)
        self.assertEqual(result['video_agent'], 'BLOCKED')


class EngineTests(unittest.TestCase):
    def test_permission_engine(self):
        PermissionEngine.check('coding_agent', ('file_create',))
        with self.assertRaises(RuntimeViolation):
            PermissionEngine.check('coding_agent', ('credit_settlement',))
        with self.assertRaises(RuntimeViolation):
            PermissionEngine.check('nobody', ())

    def test_verification_engine_enforces_independence_and_duties(self):
        with self.assertRaises(RuntimeViolation):
            VerificationEngine.check('coding_agent', 'coding_agent')
        with self.assertRaises(RuntimeViolation):
            VerificationEngine.check('coding_agent', 'release_agent')   # must be review or QA
        VerificationEngine.check('coding_agent', 'qa_agent')
        VerificationEngine.check('repair_agent', 'qa_agent')

    def test_commercial_safety(self):
        self.assertEqual(commercial_status('gemini-3-8-flash')[0], COMMERCIAL_APPROVED)
        self.assertEqual(commercial_status('local-llama')[0], DEV_ONLY)
        Entry = lambda n: type('E', (), {'endpoint': type('P', (), {'name': n})()})()  # noqa: E731
        kept = filter_routable([Entry('gemini-x'), Entry('local-y')])
        self.assertEqual([e.endpoint.name for e in kept], ['gemini-x'])

    def test_resolver_marks_missing_capabilities(self):
        statuses = {k: 'LIVE' for k in ('requirement_extraction',)}
        out = resolve({'prompt': 'משחק פלטפורמה דו-ממדי', 'user_roles': ['user']}, statuses)
        self.assertEqual(out['skills']['requirement_extraction'], AVAILABLE)
        self.assertEqual(out['skills']['collision'], MISSING)
        self.assertEqual(out['overall'], MISSING)


class MetaTests(unittest.TestCase):
    def test_required_layers(self):
        layers = meta.required_layers(['omni_prod/worker_tasks.py', 'omni_prod/assets/app.js'])
        for layer in ('unit', 'worker/queue', 'real-server', 'browser'):
            self.assertIn(layer, layers)
        self.assertEqual(meta.required_layers(['README.md']), ['static', 'unit'])

    def test_regression_guardian_catches_a_failure_and_a_dropped_test(self):
        import tempfile
        xml = ('<testsuites><testsuite>'
               '<testcase classname="tests.test_x.T" name="test_a"/>'
               '<testcase classname="tests.test_x.T" name="test_b"><failure message="x"/></testcase>'
               '</testsuite></testsuites>')
        with tempfile.NamedTemporaryFile('w', suffix='.xml', delete=False) as f:
            f.write(xml)
        matrix = {'areas': {'x': {'files': {'tests/test_x.py': {'min_tests': 3}}}}}
        problems = meta.regression_guardian(f.name, matrix)
        self.assertTrue(any('requires 3' in p for p in problems))
        self.assertTrue(any('test_b failed' in p for p in problems))
        os.unlink(f.name)

    def test_quality_gate_refuses_without_regression_run(self):
        result = audit.audit()
        verdict = meta.quality_gate(result=result, regression_problems=None, inflation=[])
        self.assertEqual(verdict['verdict'], 'NOT_VERIFIED')
        self.assertIn('regression guardian has not run on this commit', verdict['reasons'])


DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as c:
            if c.execute("SELECT to_regclass('public.agent_tasks')").fetchone()[0] is None:
                return 'schema through 034 not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


@unittest.skipIf(_skip(), _skip())
class RuntimeLivePostgresTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.agent_os.runtime import AgentRuntime
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        self.rt = AgentRuntime(self.pool)

    def test_task_graph_dependencies_states_and_verification(self):
        run = self.rt.create_run('build', f'bld_{uuid.uuid4().hex[:8]}', budget_usd=Decimal('0.10'))
        code = self.rt.add_task(run, 'coding_agent', skills=('file_create',), budget_usd=Decimal('0.05'))
        qa = self.rt.add_task(run, 'qa_agent', skills=('unit_test_execution',), depends_on=(code,))
        with self.assertRaises(RuntimeViolation):
            self.rt.transition(qa, 'RUNNING')                      # PENDING cannot run
        self.rt.transition(code, 'RUNNING')
        self.rt.handoff(code, 'qa_agent', {'repository': 'ref'})
        self.rt.transition(code, 'SUCCEEDED', cost_usd=Decimal('0.02'))
        self.assertEqual(self.rt.get(qa)['state'], 'READY')         # dependency released it
        self.rt.transition(qa, 'RUNNING')
        self.rt.transition(qa, 'SUCCEEDED')
        self.rt.verify(code, qa)
        self.assertEqual(self.rt.get(code)['verified_by_task'], qa)
        with self.assertRaises(RuntimeViolation):
            self.rt.verify(qa, qa)

    def test_recovered_build_supersedes_the_lost_workers_run(self):
        from omni_prod.agent_os.recorder import BuildAgentRecorder
        bid = f'bld_{uuid.uuid4().hex[:8]}'
        lost = BuildAgentRecorder(self.pool, bid)
        lost.start(from_brief=True)
        lost.on_model('codegen')                 # worker killed here: coding task stays RUNNING
        again = BuildAgentRecorder(self.pool, bid)
        again.start(from_brief=True)
        again.on_model('codegen')
        again.on_check(True, 'tests passed')
        again.finish(status='ready', evidence={})
        with self.pool.connection() as conn:
            runs = dict(conn.execute('SELECT id, outcome FROM agent_runs WHERE subject_id = %s', (bid,)).fetchall())
            stuck = conn.execute("SELECT count(*) FROM agent_tasks t JOIN agent_runs r ON r.id = t.run_id WHERE r.subject_id = %s "
                                 "AND t.state IN ('RUNNING', 'PENDING', 'READY')", (bid,)).fetchone()[0]
            verified = conn.execute('SELECT t.agent_key, v.agent_key FROM agent_tasks t JOIN agent_tasks v ON v.id = t.verified_by_task '
                                    'WHERE t.run_id = %s', (again.run_id,)).fetchall()
        self.assertEqual(runs[lost.run_id], 'superseded')
        self.assertEqual(runs[again.run_id], 'ready')
        self.assertEqual(stuck, 0)
        self.assertIn(('coding_agent', 'qa_agent'), verified)
        self.assertTrue(all(a != b for a, b in verified))

    def test_budget_blocks_and_restart_resumes(self):
        run = self.rt.create_run('build', f'bld_{uuid.uuid4().hex[:8]}')
        t = self.rt.add_task(run, 'coding_agent', skills=('file_create',), budget_usd=Decimal('0.01'))
        self.rt.transition(t, 'RUNNING')
        with self.assertRaises(RuntimeViolation):
            self.rt.transition(t, 'SUCCEEDED', cost_usd=Decimal('0.02'))
        self.assertEqual(self.rt.get(t)['state'], 'BLOCKED')
        r = self.rt.add_task(run, 'repair_agent', skills=('repair_execution',))
        self.rt.transition(r, 'RUNNING')
        self.assertEqual(self.rt.resume(run), [r])                 # interrupted work is redone
        self.assertEqual(self.rt.get(r)['attempt'], 2)
        self.rt.remember('p1', 'coding_agent', 'stack', {'lang': 'python'})
        self.assertEqual(self.rt.recall('p1', 'coding_agent', 'stack'), {'lang': 'python'})

    def test_recorder_turns_a_build_into_verified_agent_tasks(self):
        from omni_prod.agent_os.recorder import BuildAgentRecorder
        rec = BuildAgentRecorder(self.pool, f'bld_{uuid.uuid4().hex[:8]}')
        rec.start(from_brief=True)
        for step in ('architecture', 'codegen'):
            rec.on_model(step)
        rec.on_check(False, 'tests failed')
        rec.on_model('repair')
        rec.on_check(True, 'all checks passed')
        rec.on_model('review')
        rec.finish(status='ready', evidence={'browser_check': {'status': 'passed'},
                                             'behavior_acceptance': {'last': {'status': 'PASS', 'summary': 'ok'}},
                                             'gates': {'security': {'passed': True}},
                                             'economics_settlement': {'cost_basis': {'llm': 'METERED'}}})
        tasks = self.rt.tasks(rec.run_id)
        agents = [t['agent_key'] for t in tasks]
        for agent in ('discovery_agent', 'architecture_agent', 'coding_agent', 'qa_agent', 'repair_agent',
                      'code_review_agent', 'browser_rehearsal_agent', 'behavioral_acceptance_agent', 'release_agent',
                      'quality_gate_agent'):
            self.assertIn(agent, agents)
        repair = next(t for t in tasks if t['agent_key'] == 'repair_agent')
        self.assertIsNotNone(repair['verified_by_task'])            # QA verified the repair
        self.assertTrue(any(t['state'] == 'FAILED' and t['agent_key'] == 'qa_agent' for t in tasks))


if __name__ == '__main__':
    unittest.main()
