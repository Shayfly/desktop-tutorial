"""Wave A A3-A6 + Unified Conversation OS: intake, contract, Chief Architect,
execution graph, feasibility, departments, Conversation Supervisor, durable
memory and the plan-bound agent recorder.

Model interpretation is exercised ONLY with test doubles here (scripted
gateway outputs). No provider is called; nothing here is evidence of a live
AI conversation. Live PostgreSQL tests run against a real database
(M4D2_DATABASE_URL) and are skipped -- not faked -- without one.
"""
import dataclasses
import json
import os
import unittest
import uuid
from decimal import Decimal
from unittest import mock

from omni_prod import discovery as d
from omni_prod.agent_os import departments as DEP
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor, classify_intent
from omni_prod.intake import agent as A, contract as C
from omni_prod.intake.benchmark import FIXTURES, score
from omni_prod.intake.families import classify_family
from omni_prod.intake.interpreter import DeterministicInterpreter, ModelInterpreter, validate_model_output
from omni_prod.planning import feasibility as F, registry_view as R
from omni_prod.planning.architect import ChiefArchitect
from omni_prod.planning.graph import ExecutionGraph, GraphInvalid, PlanTask

DI = DeterministicInterpreter()


def turn(brief, msg):
    return A.apply(brief, DI.interpret(msg, brief))


def complete_brief(msg='I need a simple internal tool for my team to track equipment loans, in English, no login. '
                       'No personal data. You decide the rest'):
    b = d.start(msg)
    r = turn(b, msg)
    return r.brief


class InterpreterTests(unittest.TestCase):
    def test_benchmark_fixtures_hebrew_and_english(self):
        cases = json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']
        res = score(DI, cases)
        self.assertEqual(res['by_language'], {'he': 6, 'en': 6})
        self.assertEqual(res['hallucinations'], 0)
        self.assertEqual(res['wrong_values'], 0)
        self.assertGreaterEqual(res['field_recall'], 0.95)
        self.assertEqual(res['family_accuracy'], 1.0)

    def test_language_and_families(self):
        self.assertEqual(DI.interpret('מערכת תורים').language, 'he')
        self.assertEqual(DI.interpret('a booking system').language, 'en')
        self.assertEqual(classify_family('משחק פלטפורמה'), 'game')
        self.assertEqual(classify_family('android app for drivers'), 'mobile_app')
        self.assertEqual(classify_family('מערכת לניהול לקוחות'), 'web_app')

    def test_model_output_is_validated_against_the_message(self):
        msg = 'מערכת תורים בלי התחברות בצבע ירוק'
        raw = {'language': 'he', 'product_family': 'web_app', 'proposals': [
            {'field': 'login', 'value': 'none', 'confidence': 'high', 'evidence': 'בלי התחברות'},
            {'field': 'color', 'value': 'red', 'confidence': 'high', 'evidence': 'ירוק'},              # not an option
            {'field': 'audience', 'value': 'public', 'confidence': 'high', 'evidence': 'ללקוחות רבים'},  # quote not in message
            {'field': 'salary', 'value': '1', 'confidence': 'high', 'evidence': 'x'},                   # unknown field
        ]}
        interp, dropped = validate_model_output(raw, msg)
        self.assertEqual([(p.field, p.value) for p in interp.proposals], [('login', 'none')])
        self.assertEqual(len(dropped), 3)
        self.assertEqual(validate_model_output('not json', msg), (None, ['output is not a JSON object']))

    def test_model_interpreter_with_test_double_merges_and_falls_back(self):
        class Double:
            last_usage = None
            def __init__(self, out): self.out, self.calls = out, []
            def complete_json(self, **kw):
                self.calls.append(kw['task'])
                if isinstance(self.out, Exception):
                    raise self.out
                return self.out
        msg = 'I need a booking site in English, no login'
        dbl = Double({'language': 'en', 'product_family': 'web_app', 'proposals': [
            {'field': 'login', 'value': 'simple', 'confidence': 'medium', 'evidence': 'no login'},
            {'field': 'dates', 'value': 'future_year', 'confidence': 'medium', 'evidence': 'booking'}]})
        it = ModelInterpreter(dbl).interpret(msg)
        self.assertEqual(dbl.calls, ['conversation'])               # cheap task class only
        got = {p.field: p.value for p in it.proposals}
        self.assertEqual(got['login'], 'none')                      # deterministic HIGH wins the conflict
        self.assertEqual(got['dates'], 'future_year')
        self.assertEqual(it.interpreter, 'model+deterministic')
        down = ModelInterpreter(Double(RuntimeError('provider down'))).interpret(msg)
        self.assertEqual(down.interpreter, 'deterministic')
        self.assertIn('model unavailable', down.dropped[0])
        bad = ModelInterpreter(Double(['x'])).interpret(msg)
        self.assertIn('malformed', bad.dropped[-1])


class ConfidencePolicyTests(unittest.TestCase):
    def test_material_medium_is_asked_not_assumed(self):
        msg = 'מערכת תורים למספרה, הלקוחות ישאירו טלפון, בלי התחברות'
        r = turn(d.start(msg), msg)
        self.assertNotIn('personal_data', r.brief.fields)
        self.assertEqual(r.brief.hints['personal_data'], 'yes')
        self.assertEqual(r.asked[0].id, 'personal_data')
        self.assertLessEqual(len(r.asked), A.ASK_PER_TURN)

    def test_non_material_defaults_are_marked_as_assumptions(self):
        r = turn(d.start('task tracker for my team'), 'task tracker for my team')
        self.assertEqual(r.brief.fields['style']['source'], 'default')
        self.assertTrue(any(a['field'] == 'font' for a in r.assumed))

    def test_you_decide_never_covers_material_choices(self):
        msg = 'דף נחיתה לסטודיו יוגה, תחליט אתה על הכל'
        r = turn(d.start(msg), msg)
        self.assertNotIn('login', {k for k, f in r.brief.fields.items() if f['source'] == 'delegated'})
        self.assertIn('login', [q.id for q in r.asked])

    def test_correction_updates_and_is_recorded(self):
        b = turn(d.start('crm in blue'), 'crm in blue').brief
        r = turn(b, 'actually make it green')
        self.assertEqual(r.brief.fields['color']['value'], 'green')
        self.assertEqual(r.corrected, [{'field': 'color', 'old': 'blue', 'new': 'green'}])

    def test_contradiction_is_always_asked(self):
        b = d.start('אתר תורים ללקוחות')
        b = d.answer(b, {'audience': 'public', 'personal_data': 'yes', 'login': 'none'})
        r = turn(b, 'תחליט אתה')
        self.assertEqual(r.asked[0].id, 'access_scope')
        self.assertFalse(d.complete(r.brief))


class ContractTests(unittest.TestCase):
    def test_complete_brief_gives_a_valid_versioned_contract(self):
        c = C.build(complete_brief())
        self.assertEqual(c.schema, 'intake-requirements/1')
        self.assertEqual(C.validate(c), [])
        self.assertEqual(c.authentication_requirements['mode'], 'none')
        self.assertIn('login=none', c.explicit_constraints)
        self.assertTrue(c.inferred_defaults)
        self.assertEqual(set(c.confidence_by_requirement), {r.id for r in c.functional_requirements + c.nonfunctional_requirements})

    def test_malformed_contract_is_rejected(self):
        c = C.from_brief(complete_brief())
        bad = dataclasses.replace(c, product_family='spaceship', languages=['fr'], authentication_requirements={'mode': 'x'})
        problems = C.validate(bad)
        self.assertTrue(any('product_family' in p for p in problems))
        self.assertTrue(any('languages' in p for p in problems))
        self.assertTrue(any('authentication' in p for p in problems))


def _task(tid, deps=(), cap='0', it=1, policy='block_dependents'):
    return PlanTask(tid, 't', 'D12', 'qa_agent', ('unit_test_execution',), (), (), tuple(deps), (), (), (), 'v', 'low',
                    Decimal('0'), None if cap is None else Decimal(cap), 'r', 't', policy, 'r', 'e', 'unit_tests',
                    max_iterations=it)


class GraphTests(unittest.TestCase):
    def test_layers_parallelism_and_critical_path(self):
        g = ExecutionGraph((_task('A'), _task('B', ['A']), _task('C', ['A']), _task('D', ['B', 'C'])), Decimal('1'))
        self.assertEqual(g.layers(), [['A'], ['B', 'C'], ['D']])
        self.assertEqual(len(g.critical_path()), 3)
        self.assertEqual(g.ready({'A'}), ['B', 'C'])

    def test_cycles_unknown_deps_and_missing_cost_are_rejected(self):
        g = ExecutionGraph((_task('A', ['B']), _task('B', ['A']), _task('C', ['Z']), _task('E', cap=None)), Decimal('1'))
        p = g.problems()
        self.assertTrue(any('cycle' in x for x in p))
        self.assertTrue(any('unknown dependency Z' in x for x in p))
        self.assertTrue(any('missing price is never zero' in x for x in p))
        with self.assertRaises(GraphInvalid):
            g.validate()

    def test_aggregate_budget_and_fan_out_cap(self):
        many = tuple(_task(f'T{i}', cap='0.02') for i in range(30))
        self.assertTrue(any('graph authorizes' in x for x in ExecutionGraph(many, Decimal('0.50')).problems()))
        fan = tuple(_task(f'T{i}') for i in range(61))
        self.assertTrue(any('fan-out' in x for x in ExecutionGraph(fan, Decimal('1')).problems()))
        it = ExecutionGraph((_task('R', cap='0.04', it=5),), Decimal('0.10'))
        self.assertEqual(it.authorized_total(), Decimal('0.20'))   # iterations count toward the budget

    def test_failure_invalidates_only_downstream(self):
        g = ExecutionGraph((_task('A'), _task('B', ['A']), _task('C'), _task('D', ['B']),
                            _task('X', ['C'], policy='continue_advisory'), _task('Y', ['X'])), Decimal('1'))
        self.assertEqual(g.invalidated_by({'A'}), {'B', 'D'})
        self.assertEqual(g.invalidated_by({'X'}), set())
        self.assertEqual(g.ready(set(), failed={'A'}), ['C'])

    def test_registry_permission_closure(self):
        g = ExecutionGraph((dataclasses.replace(_task('A'), required_skills=('video_render',)),), Decimal('1'))
        p = g.problems(agents=R.allowed_skills(), skills=R.skill_keys())
        self.assertTrue(any('may not use skill video_render' in x for x in p))


class ArchitectTests(unittest.TestCase):
    def test_web_plan_is_validated_and_bound_to_real_engine_stages(self):
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        self.assertEqual(plan['graph_problems'], [])
        self.assertTrue(plan['executable'])
        self.assertIn(plan['feasibility']['outcome'], F.BUILDABLE)
        stages = {t['stage'] for t in plan['execution_graph']['tasks']}
        from omni_prod.agent_os.recorder import MODEL_TASK_STAGE, STAGE_CHECK
        bound = set(MODEL_TASK_STAGE.values()) | set(STAGE_CHECK) | {'intake', 'planning', 'unit_tests', 'quality_gate',
                                                                     'release', 'cost'}
        self.assertLessEqual(stages, bound)          # every task maps to something the engine really does
        for a in plan['assignments']:
            self.assertTrue(a['executable'], a)
            self.assertNotEqual(a['department'], 'UNASSIGNED')
        self.assertEqual(plan['layers'][0], ['T01'])
        self.assertLessEqual(Decimal(plan['budget']['graph_authorized_usd']), Decimal(plan['budget']['budget_usd']))
        self.assertEqual(plan['brief_fingerprint'], complete_brief().fingerprint())

    def test_architecture_and_code_tasks_route_to_strong_models_first(self):
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        by = {a['task_id']: a for a in plan['assignments']}
        self.assertEqual(by['T04']['model_candidates'][0], 'gemini-3.8-flash')
        self.assertEqual(by['T03']['model_candidates'][0], 'gemini-3.8-flash')

    def test_unsupported_family_is_planned_but_not_executable(self):
        b = d.answer(complete_brief(), {})
        b = dataclasses.replace(b, prompt='an android app for my delivery drivers') if False else b
        b.prompt = 'an android app for my delivery drivers'
        plan = ChiefArchitect().plan(C.build(b))
        self.assertEqual(plan['feasibility']['outcome'], F.UNSUPPORTED)
        self.assertFalse(plan['executable'])
        self.assertTrue(any(not t['executable'] for t in plan['execution_graph']['tasks']))

    def test_sign_in_and_payments_block_until_connected(self):
        b = complete_brief()
        b.fields['login'] = {'value': 'roles', 'source': 'answer', 'question_id': 'login', 'confidence': 'confirmed'}
        b.prompt += ' with stripe payments'
        plan = ChiefArchitect().plan(C.build(b))
        items = {f['item']: f['outcome'] for f in plan['feasibility']['findings']}
        self.assertEqual(items['sign-in (roles)'], F.BLOCKED)
        self.assertEqual(items['integration: payments'], F.BLOCKED)
        self.assertFalse(plan['executable'])

    def test_unreadable_registries_are_unknown_never_feasible(self):
        with mock.patch.object(R, 'snapshot', return_value={'loaded': False}):
            self.assertEqual(F.assess(C.build(complete_brief())).outcome, F.UNKNOWN)


class DepartmentTests(unittest.TestCase):
    def test_every_agent_in_exactly_one_department_and_files_current(self):
        m = DEP.build()
        self.assertEqual(DEP.problems(m), [])
        self.assertEqual(len(m['departments']), 18)
        js, md = DEP.render(m)
        self.assertEqual(DEP.JSON_OUT.read_text(encoding='utf-8'), js,
                         'DEPARTMENT_MATRIX.json is stale: python -m omni_prod.agent_os.departments --write')
        self.assertEqual(DEP.MD_OUT.read_text(encoding='utf-8'), md)

    def test_readiness_is_computed_not_declared(self):
        dep = DEP.BY_KEY['D14']
        self.assertEqual(DEP.readiness(dep, {}), 'NOT_IMPLEMENTED')
        self.assertEqual(DEP.readiness(DEP.BY_KEY['D12'], {a: 'REAL_SERVER_VERIFIED' for a in DEP.BY_KEY['D12'].core_agents}),
                         'PARTIAL')   # a missing adapter keeps it PARTIAL even with all agents verified
        self.assertEqual(DEP.readiness(DEP.BY_KEY['D15'], {a: 'BLOCKED' for a in DEP.BY_KEY['D15'].core_agents}), 'BLOCKED')


class MemoryBriefs:
    """In-process stand-in for PostgresBriefRepository (same contract)."""
    class Row:
        def __init__(self, rev, brief):
            self.revision, self.brief = rev, brief
            self.complete, self.fingerprint = d.complete(brief), brief.fingerprint()

    def __init__(self):
        self.rows = {}

    def latest(self, pid):
        return (self.rows.get(pid) or [None])[-1]

    def save(self, *, project_id, account_id, brief, expected_revision, request_key=None):
        cur = self.latest(project_id)
        if (cur.revision if cur else 0) != expected_revision:
            from omni_prod.brief_repository import StaleBrief
            raise StaleBrief('stale')
        row = self.Row(expected_revision + 1, d.Brief.from_dict(json.loads(json.dumps(brief.to_dict()))))
        self.rows.setdefault(project_id, []).append(row)
        return row


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.ctx = {}
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: self.ctx)

    def say(self, msg, **kw):
        return self.sup.turn(project_id='p1', account_id='a1', message=msg, **kw)

    def test_hebrew_multi_turn_to_an_approvable_plan(self):
        t1 = self.say('אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון')
        self.assertEqual(t1.language, 'he')
        self.assertEqual(t1.questions[0].id, 'personal_data')
        self.assertIsNone(t1.plan_id)
        t2 = self.sup.turn(project_id='p1', account_id='a1', answers={'personal_data': 'yes'}, lang='he')
        self.assertEqual(t2.questions[0].id, 'access_scope')   # contradiction surfaced, never assumed
        t3 = self.sup.turn(project_id='p1', account_id='a1', answers={'access_scope': 'internal_link'}, lang='he')
        self.assertTrue(t3.brief_row.complete)
        self.assertIsNotNone(t3.plan_id)
        self.assertEqual(t3.actions, [{'type': 'show_plan', 'brief_revision': t3.brief_row.revision}])
        self.assertEqual([r.revision for r in self.briefs.rows['p1']], [1, 2, 3])   # every change is a revision
        roles = [m['role'] for m in self.store.messages_for('p1')]
        self.assertEqual(roles.count('assistant'), 3)

    def test_english_questions_cost_missing_status_approve(self):
        self.say('I need a simple internal tool for my team to track equipment loans, in English, no login, no personal data')
        self.assertIn('Nothing is missing', self.say('what is missing?').reply)
        cost = self.say('how much will it cost?')
        self.assertEqual(cost.intent, 'cost')
        self.assertIn('10 credits', cost.reply)
        self.assertIn('$0.50', cost.reply)
        self.assertIn('No build has started', self.say("what's the status?").reply)
        ok = self.say('go ahead and build it')
        self.assertEqual(ok.intent, 'approve')
        self.assertEqual(ok.actions[0]['type'], 'approve_build')   # an action for the customer, never a started build
        rec = self.say('what do you recommend?')
        self.assertIn('recommend', rec.reply.lower())

    def test_can_we_add_payments_later_answered_from_registries(self):
        self.say('internal tool for my team, no login, in English')
        r = self.say('can we add payments later?')
        self.assertEqual(r.intent, 'feasibility')
        self.assertIn('payments: not available right now', r.reply)
        self.assertIn('integration_agent is NOT_IMPLEMENTED', r.reply)
        he = self.sup.turn(project_id='p1', account_id='a1', message='אפשר להוסיף תשלומים בהמשך?')   # plural, final letters
        self.assertEqual(he.intent, 'feasibility')
        self.assertIn('תשלומים: לא זמין כרגע — עוד לא מחובר בפלטפורמה', he.reply)
        self.assertIn('integration_agent is NOT_IMPLEMENTED', he.reply)   # the registry fact stays visible

    def test_existing_product_change_goes_to_the_modification_offer(self):
        self.say('internal tool for my team, no login, in English')
        self.ctx = {'latest_version_id': 'ver_1', 'latest_build': {'status': 'ready', 'phase': 'DONE'},
                    'task_counts': {'SUCCEEDED': 12, 'CANCELLED': 1}}
        r = self.say('change the button colour to green and add a search field')
        self.assertEqual(r.intent, 'modify')
        self.assertEqual(r.actions[0], {'type': 'confirm_modification', 'version_id': 'ver_1',
                                        'request': 'change the button colour to green and add a search field'})
        self.assertIn('12 done', self.say('status?').reply)

    def test_no_paid_inference_without_a_conversation_budget(self):
        class Boom:
            def complete_json(self, **kw):
                raise AssertionError('a paid model call happened')
        sup = ConversationSupervisor(briefs=self.briefs, store=self.store, gateway=Boom(), context=lambda p: {})
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0'}):
            sup.turn(project_id='p2', account_id='a', message='crm for my team')
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0', 'OMNI_INTAKE_MODEL_BUDGET_USD': '1'}):
            sup.turn(project_id='p2', account_id='a', message='blue please')

    def test_intent_classifier(self):
        self.assertEqual(classify_intent('כמה זה יעלה?', has_version=False, has_brief=True), 'cost')
        self.assertEqual(classify_intent('מה חסר?', has_version=False, has_brief=True), 'missing')
        self.assertEqual(classify_intent('תוסיף כפתור מחיקה', has_version=True, has_brief=True), 'modify')
        self.assertEqual(classify_intent('תוסיף כפתור מחיקה', has_version=False, has_brief=True), 'requirements')
        self.assertEqual(classify_intent('אפשר להוסיף תשלומים בהמשך?', has_version=False, has_brief=True), 'feasibility')


class WorkspaceAssetTests(unittest.TestCase):
    """The conversation-first workspace (founder UI directive 2026-10-11). The
    rendered page is exercised in a real browser by tools/ui_conversation_walkthrough.py."""

    def setUp(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets'
        self.html = (root / 'index.html').read_text(encoding='utf-8')
        self.js = (root / 'app.js').read_text(encoding='utf-8')

    def test_three_regions_and_controls_exist(self):
        for el in ('id="sidebar"', 'id="sbProjects"', 'id="sbSearch"', 'id="chatForm"', 'id="thread"',
                   'id="splitter"', 'role="separator"', 'id="stage"', 'id="expandPreviewBtn"', 'id="closePreviewBtn"',
                   'id="togglePreviewBtn"', 'id="sbCollapse"'):
            self.assertIn(el, self.html)

    def test_old_mode_choice_entry_is_gone(self):
        for old in ('name="mode"', 'id="modeChoice"', 'id="planBtn"', 'id="prompt"'):
            self.assertNotIn(old, self.html)

    def test_chat_uses_the_real_conversation_api(self):
        self.assertIn('/conversation', self.js)
        self.assertIn('/builds/${encodeURIComponent(S.build.id)}/plan', self.js)
        self.assertIn('/modifications', self.js)       # changes still go through the existing pipeline

    def test_no_fake_sidebar_items(self):
        lowered = self.html.lower()
        for fake in ('scheduled', 'artifacts', 'codex', 'gpts', 'sora', 'chatgpt'):
            self.assertNotIn(fake, lowered)


DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '')


def _live_skip():
    if not DATABASE_URL:
        return 'needs PostgreSQL (M4D2_DATABASE_URL)'
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            if conn.execute("SELECT to_regclass('public.agent_runs')").fetchone()[0] is None:
                return 'schema through migration 034 not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


@unittest.skipIf(_live_skip(), _live_skip())
class LiveConversationTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.creator_accounts import PostgresAccountService
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        sql = open(os.path.join(os.path.dirname(__file__), '..', 'infra', 'postgres', '036_intelligence_plane.sql')).read()
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(sql)
        accounts = PostgresAccountService(token_secret='t' * 48, pool=self.pool)
        self.account, _ = accounts.register(email=f'c-{uuid.uuid4().hex[:8]}@example.com', password='a-long-password-123')
        self.project = f'prj_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            conn.execute("INSERT INTO creator_projects (id, owner_id, title) VALUES (%s, %s, 't')", (self.project, self.account.id))
            conn.commit()
        self.briefs = PostgresBriefRepository

    def tearDown(self):
        getattr(self.pool, 'close', lambda: None)()

    def sup(self):
        """A fresh supervisor over fresh repositories = a process restart."""
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.conversation.store import PostgresConversationStore
        return ConversationSupervisor(briefs=PostgresBriefRepository(self.pool), store=PostgresConversationStore(self.pool),
                                      credits=10, context=lambda p: {})

    def test_memory_survives_restart_and_retries_are_idempotent(self):
        self.sup().turn(project_id=self.project, account_id=self.account.id, request_key='k1',
                        message='I need a simple internal tool for my team to track equipment loans, in English, no login')
        t = self.sup().turn(project_id=self.project, account_id=self.account.id, answers={'personal_data': 'no'}, request_key='k2')
        self.assertTrue(t.brief_row.complete)
        from omni_prod.conversation.store import PostgresConversationStore
        store = PostgresConversationStore(self.pool)
        before = len(store.messages_for(self.project))
        store.add_message(project_id=self.project, account_id=self.account.id, role='customer', content='dup', request_key='k1')
        self.assertEqual(len(store.messages_for(self.project)), before)          # same request_key: no duplicate
        plan = store.plan_for(self.project, t.brief_row.fingerprint)
        self.assertEqual(plan['plan']['schema'], 'architecture-plan/1')
        from omni_prod.conversation.memory import snapshot
        from omni_prod.brief_repository import PostgresBriefRepository
        mem = snapshot(self.pool, project_id=self.project, internal_key='none', store=store,
                       briefs=PostgresBriefRepository(self.pool))
        self.assertEqual(mem['approved_requirements']['login'], 'none')
        self.assertIn('style', mem['assumptions'])
        self.assertEqual([h['revision'] for h in mem['history']], [1, 2])
        self.assertEqual(len(mem['execution_plan']['tasks']), 15)
        self.assertEqual(mem['open_items']['questions'], [])

    def test_plan_bound_recorder_tracks_the_real_stages(self):
        from omni_prod.agent_os.recorder import PlanBoundRecorder
        from omni_prod.agent_os.runtime import AgentRuntime
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        rec = PlanBoundRecorder(self.pool, f'bld_{uuid.uuid4().hex}', plan=plan['execution_graph'], plan_id='pln_x')
        rec.start(from_brief=True)
        rt = AgentRuntime(self.pool)
        rows = {t['evidence']['plan_task']: t for t in rt.tasks(rec.run_id)}
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows['T01']['state'], 'SUCCEEDED')
        self.assertEqual(rows['T04']['state'], 'PENDING')
        self.assertEqual(rows['T04']['depends_on'], [rows['T03']['id']])     # real dependency ids
        rec.on_model('architecture'); rec.on_model('codegen')
        rec.on_check(False, 'tests failed')
        rec.on_model('repair')
        rec.on_check(True, 'tests pass')
        checks = [{'check': c, 'status': 'PASS'} for c in ('preview_starts', 'behavioural_acceptance', 'browser_flow',
                                                           'visual_layout_desktop_mobile', 'static_security_scan',
                                                           'qa_review_blocking_findings')]
        rec.finish(status='ready', evidence={'quality_report': {'decision': 'READY', 'checks': checks},
                                             'economics_settlement': {'cost_basis': {'llm': 'metered'}}})
        st = {t['evidence']['plan_task']: t['state'] for t in rt.tasks(rec.run_id)}
        self.assertEqual(set(st.values()), {'SUCCEEDED'})
        coding = next(t for t in rt.tasks(rec.run_id) if t['evidence']['plan_task'] == 'T04')
        self.assertIsNotNone(coding['verified_by_task'])                       # verified by the release gate

    def test_failure_blocks_downstream_and_unreached_tasks_are_not_success(self):
        from omni_prod.agent_os.recorder import PlanBoundRecorder
        from omni_prod.agent_os.runtime import AgentRuntime
        plan = ChiefArchitect().plan(C.build(complete_brief()))
        rec = PlanBoundRecorder(self.pool, f'bld_{uuid.uuid4().hex}', plan=plan['execution_graph'])
        rec.start(from_brief=True)
        rec.on_model('architecture'); rec.on_model('codegen'); rec.on_check(True, 'ok')
        checks = [{'check': 'preview_starts', 'status': 'FAIL'}]
        rec.finish(status='failed', evidence={'quality_report': {'decision': 'FAILED', 'checks': checks}})
        st = {t['evidence']['plan_task']: (t['state'], t['evidence']) for t in AgentRuntime(self.pool).tasks(rec.run_id)}
        self.assertEqual(st['T07'][0], 'FAILED')
        for downstream in ('T08', 'T09', 'T10', 'T15', 'T12', 'T13'):
            self.assertIn(st[downstream][0], ('CANCELLED',), downstream)
        self.assertNotIn('SUCCEEDED', {st[k][0] for k in ('T08', 'T09', 'T10', 'T12', 'T13')})
        self.assertEqual(st['T06'][0], 'CANCELLED')     # repair never needed


if __name__ == '__main__':
    unittest.main()
