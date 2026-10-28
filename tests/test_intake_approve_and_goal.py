"""Emergency fix 2026-10-28 (fix/intake-approve-and-goal).

BLOCKER 1: the spec approval rode on the conversation route with message='' and was refused as `empty_message`; the
spec was never approved, so the build gate (spec_not_approved) stayed closed -- "לא ניתן להתחיל בבנייה כרגע".
BLOCKER 2: the goal came from the first sentence by rule and the model could not replace it; a pasted
"OMNI_REDIS_URL" became "Main action: OMNI_REDIS_URL".
BLOCKER 3: a brief-bound plan showed the architect's English build spec as its summary.
ARCHITECTURE: a refused model proposal is dropped with a reason; the turn continues.
"""
import json
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import agent as A
from omni_prod.intake import approval_flow as AF
from omni_prod.intake.interpreter import (DeterministicInterpreter, Interpretation, Proposal, first_sentence,
                                          validate_model_output)
from tests.evidence_notice import notice
from tests.test_conversation_os import MemoryBriefs

BARBER = ('אני רוצה מערכת לניהול תורים למספרה שלי. הלקוחות יקבעו תור לפי שעות פנויות, ישאירו שם וטלפון, '
          'ואני אראה את כל התורים של היום. בלי התחברות ללקוחות.')
PASTED = 'OMNI_REDIS_URL\n' + BARBER
GOAL = 'אני רוצה מערכת לניהול תורים למספרה שלי.'


def first_turn(message):
    s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
    t = s.turn(project_id='p', account_id='a', message=message, lang='he')
    return s, t, s.briefs.latest('p').brief


class TheGoal(unittest.TestCase):
    def test_a_pasted_token_does_not_become_the_goal(self):                      # NC (a)
        _, _, b = first_turn(PASTED)
        self.assertEqual(b.fields['goal']['value'], GOAL)
        self.assertNotIn('OMNI_REDIS_URL', d.requirements_text(b).split('Main action:')[1].splitlines()[0])

    def test_with_the_model_off_the_deterministic_goal_still_appears(self):      # NC (b)
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            _, _, b = first_turn(BARBER)
        self.assertEqual((b.fields['goal']['value'], b.fields['goal']['source']), (GOAL, 'default'))

    def test_the_model_owns_the_goal_over_the_rule(self):
        _, _, b = first_turn(BARBER)
        model = Interpretation('he', 'web_app', [Proposal('goal', 'לקוחות קובעים תור לבד לפי שעות פנויות', 'medium',
                                                          'יקבעו תור', 'model')], False, [], 'model:x')
        self.assertEqual(A.apply(b, model).brief.fields['goal']['value'], 'לקוחות קובעים תור לבד לפי שעות פנויות')

    def test_a_model_goal_that_is_technical_text_is_dropped_with_a_reason(self):
        _, _, b = first_turn(BARBER)
        model = Interpretation('he', 'web_app', [Proposal('goal', 'OMNI_REDIS_URL', 'high', 'OMNI_REDIS_URL', 'model')],
                               False, [], 'model:x')
        r = A.apply(b, model)
        self.assertEqual(r.brief.fields['goal']['value'], GOAL)
        self.assertTrue(any('technical text' in x for x in r.dropped))

    def test_the_customers_own_goal_is_kept_over_the_model(self):
        _, _, b = first_turn(BARBER)
        b = A.answer_question(b, 'goal', 'קביעת תור בשתי לחיצות')
        model = Interpretation('he', 'web_app', [Proposal('goal', 'משהו אחר לגמרי', 'high', 'x', 'model')], False, [],
                               'model:x')
        r = A.apply(b, model)
        self.assertEqual(r.brief.fields['goal']['value'], 'קביעת תור בשתי לחיצות')     # asked back as a conflict
        self.assertEqual([c['field'] for c in r.conflicts], ['goal'])

    def test_first_sentence_skips_technical_lines(self):
        self.assertEqual(first_sentence(PASTED), GOAL)
        self.assertEqual(first_sentence('export OMNI_REDIS_URL=redis://x:6379\nI need a booking site for my salon.'),
                         'I need a booking site for my salon.')
        self.assertEqual(first_sentence('אתר תדמית לעסק שלי עם קישור https://x.co להזמנה'),
                         'אתר תדמית לעסק שלי עם קישור https://x.co להזמנה')    # a link inside a real sentence stays


class TheModelPathReproduction(unittest.TestCase):
    """The symptom as the customer saw it, through the model path: on main a0436061 this gives
    'Main action: OMNI_REDIS_URL' and 'Initial content: OMNI_REDIS_URL' (both proposals pass the evidence check,
    because the customer's message does contain the token)."""
    MSG = ('אני רוצה מערכת לניהול תורים למספרה שלי. הלקוחות יקבעו תור לפי שעות פנויות, ישאירו שם וטלפון. '
           'בלי התחברות ללקוחות. בנוסף, מה זה OMNI_REDIS_URL? קיבלתי הודעה שהוא חסר.')
    RAW = {'language': 'he', 'product_family': 'web_app', 'reply': 'הבנתי.',
           'proposals': [{'field': 'goal', 'value': 'OMNI_REDIS_URL', 'confidence': 'high', 'evidence': 'OMNI_REDIS_URL'},
                         {'field': 'content', 'value': 'OMNI_REDIS_URL', 'confidence': 'high',
                          'evidence': 'OMNI_REDIS_URL'}]}

    def test_goal_and_initial_content_never_become_the_pasted_token(self):
        from omni_prod.intake.interpreter import merge
        raw = self.RAW

        class FakeModel:
            def interpret(self, message, brief=None):
                model, _ = validate_model_output(raw, message)
                return merge(DeterministicInterpreter().interpret(message, brief), model, interpreter='model:fake',
                             cost_usd='0', cost_state='CONFIRMED_ZERO')
        env = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
               'OMNI_INTAKE_DAILY_BUDGET_USD': '0.50', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.005'}
        s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), worker_interpreter=FakeModel())
        with mock.patch.dict(os.environ, env):
            t = s.turn(project_id='p', account_id='a', message=self.MSG, lang='he')
        self.assertEqual(t.interpretation['interpreter'], 'model:fake')          # the model path really ran
        b = s.briefs.latest('p').brief
        lines = {l.split(':', 1)[0]: l.split(':', 1)[1].strip() for l in d.requirements_text(b).splitlines()
                 if l.startswith(('Main action:', 'Initial content:'))}
        self.assertEqual(lines['Main action'], GOAL)
        self.assertNotIn('OMNI_REDIS_URL', lines['Initial content'])
        self.assertEqual(len([x for x in t.interpretation['dropped'] if 'technical text' in x]), 2)   # with reasons
        self.assertTrue(t.reply)                                                   # the turn still answers


class ValidationDegrades(unittest.TestCase):
    def test_a_proposal_without_evidence_is_dropped_and_the_answer_stays(self):
        raw = {'language': 'he', 'product_family': 'web_app', 'reply': 'הבנתי, מערכת תורים למספרה.',
               'proposals': [{'field': 'audience', 'value': 'public', 'confidence': 'high', 'evidence': 'לא נאמר כך'},
                             {'field': 'login', 'value': 'none', 'confidence': 'high', 'evidence': 'בלי התחברות'}]}
        interp, dropped = validate_model_output(raw, BARBER)
        self.assertIsNotNone(interp)                                             # the turn continues
        self.assertEqual(interp.reply, 'הבנתי, מערכת תורים למספרה.')            # a natural answer
        self.assertEqual([p.field for p in interp.proposals], ['login'])
        self.assertTrue(any('audience' in x and 'evidence' in x for x in dropped))   # dropped WITH its reason


def _api():
    try:
        import fastapi  # noqa: F401
        from fastapi.testclient import TestClient
    except Exception as exc:                                                     # v24-ci has fastapi
        raise unittest.SkipTest(f'fastapi not installed here ({exc})')
    from omni_prod import investor_app as IA
    return IA, TestClient(IA.app)


class TheApprovalIsAnAction(unittest.TestCase):
    """The real FastAPI routes over in-memory stores."""

    def setUp(self):
        self.IA, self.client = _api()
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        account = mock.Mock(id='a1')
        sup = ConversationSupervisor(briefs=self.briefs, store=self.store)
        patches = [mock.patch.object(self.IA, '_v28_bearer', lambda r: 'tok'),
                   mock.patch.object(self.IA._v28, 'resolve_project_key', lambda **kw: (account, 'k')),
                   mock.patch.object(self.IA, '_conversation_store', lambda: self.store),
                   mock.patch.object(self.IA, '_brief_repo', lambda: self.briefs),
                   mock.patch.object(self.IA, '_supervisor', lambda key, aid=None: sup),
                   mock.patch.object(self.IA, '_conversation_view',
                                     lambda pid, lang, turn=None: {'turn': turn.to_dict(lang) if turn else None})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def post(self, path, body):
        return self.client.post(f'/api/v28/projects/p1/{path}?lang=en', json=body)

    def ready_spec(self):
        self.post('conversation', {'message': 'I need a simple internal tool for my team to track equipment loans, '
                                              'in English, no login, no personal data'})
        r = self.post('conversation', {'message': 'you decide'})
        acts = [a for a in r.json()['turn']['actions'] if a['type'] == 'approve_spec']
        self.assertTrue(acts, r.json())
        return acts[0]['brief_fingerprint']

    def test_an_empty_chat_turn_is_still_an_explicit_error(self):               # NC (b)
        r = self.post('conversation', {'message': ''})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()['detail']['error'], 'empty_message')
        notice('approve-action NC(b) PASS', 'POST conversation with message="" -> 422 empty_message (explicit)')

    def test_approve_with_an_empty_message_opens_the_build(self):              # NC (a)
        fp = self.ready_spec()
        r = self.post('spec-approval', {'brief_fingerprint': fp})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(AF.spec_approved(self.store.messages, fp))             # the build gate's own check
        self.assertIn('approve_build', [a['type'] for a in r.json()['turn']['actions']])
        notice('approve-action NC(a) PASS', f'POST spec-approval (no message) -> 200; spec_approved={fp[:12]} recorded; '
               'approve_build offered')

    def test_an_old_client_approving_on_the_conversation_route_is_not_empty_message(self):
        fp = self.ready_spec()
        r = self.post('conversation', {'message': '', 'approve_spec': fp})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(AF.spec_approved(self.store.messages, fp))

    def test_a_double_click_makes_one_plan_and_one_approval_path(self):          # idempotency NC
        fp = self.ready_spec()
        same = {'brief_fingerprint': fp, 'request_key': 'click-1'}
        r1, r2 = self.post('spec-approval', same), self.post('spec-approval', same)    # the same click retried
        self.assertEqual((r1.status_code, r2.status_code), (200, 200))
        approvals = [m for m in self.store.messages if (m.get('interpretation') or {}).get('spec_approved') == fp]
        self.assertEqual(len(approvals), 1)                                       # one approval recorded
        r3 = self.post('spec-approval', {'brief_fingerprint': fp, 'request_key': 'click-2'})   # a second, new click
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(len(self.store.plans), 1)                                 # still ONE plan to build
        # the spec approval itself never creates a build: a build needs POST .../approvals (one approval -> one
        # build, brief_repository.consume marks it USED) and POST .../builds (idempotency_key -> the same build_id)

    def test_a_fingerprint_that_is_not_this_projects_current_spec_is_refused(self):
        fp = self.ready_spec()
        other = 'f' * 64                                                          # another project's / an old spec
        r = self.post('spec-approval', {'brief_fingerprint': other})
        self.assertEqual(r.status_code, 200)                                      # answered in the conversation ...
        self.assertFalse(AF.spec_approved(self.store.messages, other))            # ... but nothing is approved
        self.assertFalse(AF.spec_approved(self.store.messages, fp))
        self.assertNotIn('approve_build', [a['type'] for a in r.json()['turn']['actions']])

    def test_a_spec_that_changed_after_it_was_shown_is_refused(self):
        fp = self.ready_spec()
        self.post('conversation', {'answers': {'style': 'warm'}})                  # the default look was 'clean'
        self.assertNotEqual(self.briefs.latest('p1').fingerprint, fp)              # the spec DID change (no skip)
        r = self.post('spec-approval', {'brief_fingerprint': fp})
        self.assertFalse(AF.spec_approved(self.store.messages, fp))
        self.assertNotIn('approve_build', [a['type'] for a in r.json()['turn']['actions']])

    def test_the_route_needs_the_projects_owner(self):
        def deny(**kw):
            raise PermissionError('not your project')
        with mock.patch.object(self.IA._v28, 'resolve_project_key', deny):
            r = self.post('spec-approval', {'brief_fingerprint': 'a' * 64})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.store.messages, [])

    def test_a_malformed_fingerprint_is_refused(self):
        self.assertEqual(self.post('spec-approval', {'brief_fingerprint': 'x'}).status_code, 422)


class ThePlanSpeaksTheCustomersLanguage(unittest.TestCase):
    def test_summary_and_questions_follow_the_customer(self):
        IA, _ = _api()
        _, _, b = first_turn(BARBER)
        preview = {'product': {'summary': 'M5 managed Web/SaaS contract for: ... Main action: x'},
                   'clarification_questions': [{'id': 'clarify-primary-workflow', 'question': 'What is the primary '
                                                'business workflow and who will use it?', 'reason': 'r'}]}
        IA._plan_in_customer_language(preview, b, 'he')
        self.assertEqual(preview['product']['summary'], GOAL)
        self.assertTrue(preview['product']['technical_summary'].startswith('M5 managed'))
        self.assertFalse(preview['clarification_questions'][0]['question'].isascii())


class ThePlanNamesAndTheAssets(unittest.TestCase):
    def test_roles_and_data_are_named_for_the_customer_tokens_stay_for_the_machine(self):
        IA, _ = _api()
        _, _, b = first_turn(BARBER)
        preview = {'product': {'summary': 's', 'user_roles': ['admin', 'customer'], 'data_requirements': ['bookings']},
                   'clarification_questions': []}
        IA._plan_in_customer_language(preview, b, 'he')
        self.assertEqual(preview['product']['user_roles'], ['מנהל המערכת', 'לקוח'])
        self.assertEqual(preview['product']['data_requirements'], ['הזמנות ותורים'])
        self.assertEqual(preview['product']['user_roles_keys'], ['admin', 'customer'])

    def test_every_token_is_named(self):
        IA, _ = _api()
        import inspect
        from omni_prod import product_architect, unified_engine
        import re as _re
        src = inspect.getsource(product_architect.ProductArchitect._infer_roles)
        roles = set(_re.findall(r'\("([a-z_]+)", \(', src)) | {'admin', 'member'}
        src = inspect.getsource(product_architect.ProductArchitect._infer_data_requirements) + \
            inspect.getsource(unified_engine)
        data = set(_re.findall(r"""\(["']([a-z_]+)["'], \(""", src)) | {
            x for m in _re.findall(r"modules = \[([^\]]+)\]", inspect.getsource(unified_engine))
            for x in _re.findall(r"'([a-z_]+)'", m)}
        self.assertFalse(roles - set(IA._ROLE_NAMES), roles - set(IA._ROLE_NAMES))
        self.assertFalse(data - set(IA._DATA_NAMES) - {'maps', 'realtime', 'notifications', 'messaging'},
                         data - set(IA._DATA_NAMES))

    def test_the_page_references_this_deploys_asset_version_and_assets_revalidate(self):
        IA, client = _api()
        html = client.get('/').text
        self.assertIn(f'/assets/app.js?v={IA._ASSET_VERSION}', html)
        self.assertEqual(client.get('/assets/app.js').headers.get('cache-control'), 'no-cache')

class TheFlowMark(unittest.TestCase):
    """Founder 2026-10-28, option (b): a conversation that starts now is marked flow='two_gate' on its first message;
    on that flow a build needs the spec approval AND a plan with the verifier's gate. An earlier project (no mark,
    no gate) keeps the earlier path."""

    EQUIPMENT = 'I need a simple internal tool for my team to track equipment loans, in English, no login, no personal data'

    def setUp(self):
        self.IA, _ = _api()
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        for p in (mock.patch.object(self.IA, '_brief_repo', lambda: self.briefs),
                  mock.patch.object(self.IA, '_conversation_store', lambda: self.store),
                  mock.patch('omni_prod.conversation.store.schema_ready', lambda pool: True)):
            p.start()
            self.addCleanup(p.stop)

    def new_project(self):
        s = ConversationSupervisor(briefs=self.briefs, store=self.store)
        s.turn(project_id='p1', account_id='a1', message=self.EQUIPMENT, lang='en')
        s.turn(project_id='p1', account_id='a1', message='you decide', lang='en')
        row = self.briefs.latest('p1')
        self.assertTrue(row.complete)
        return row

    def plan_without_gate(self, row):
        from omni_prod.intake import contract as C
        from omni_prod.planning.architect import ChiefArchitect
        from decimal import Decimal
        plan = ChiefArchitect().plan(C.build(row.brief), budget_usd=Decimal('0.50'), status='PROPOSED')
        self.assertNotIn(AF.GATE_KEY, plan)
        self.store.save_plan(project_id='p1', brief_revision=row.revision, brief_fingerprint=row.fingerprint, plan=plan)

    def bind_error(self, fp):
        from fastapi import HTTPException
        try:
            self.IA._bind_execution_plan('p1', fp)
        except HTTPException as exc:
            return exc.status_code, exc.detail.get('error')
        return None

    def test_the_flow_mark_names_match(self):
        from omni_prod.conversation import supervisor as SV
        self.assertEqual(SV.AF_FLOW, AF.FLOW)

    def test_a_new_conversation_is_marked_and_on_the_two_gate_flow(self):
        self.new_project()
        self.assertEqual((self.store.messages[0].get('interpretation') or {}).get('flow'), 'two_gate')
        self.assertTrue(AF.on_two_gate_flow(self.store.messages))

    def test_new_project_build_without_spec_approval_is_409_spec_not_approved(self):
        row = self.new_project()
        self.assertEqual(self.bind_error(row.fingerprint), (409, 'spec_not_approved'))

    def test_new_project_saved_plan_without_gate_is_409_plan_not_verified(self):
        row = self.new_project()
        self.store.add_message(project_id='p1', account_id='a1', role='customer', content='approve',
                               interpretation={'spec_approved': row.fingerprint, 'flow': 'two_gate'})
        self.plan_without_gate(row)
        self.assertEqual(self.bind_error(row.fingerprint), (409, 'plan_not_verified'))

    def test_earlier_project_without_mark_and_a_plan_without_gate_still_passes(self):
        from omni_prod import discovery as dd
        brief = A.apply(dd.start(self.EQUIPMENT, dd.GUIDED), DeterministicInterpreter().interpret(self.EQUIPMENT, None),
                        ).brief
        brief = dd.answer(brief, {q.id: dd.DELEGATE for q in dd.pending(brief)}) if dd.pending(brief) else brief
        row = self.briefs.save(project_id='p1', account_id='a1', brief=brief, expected_revision=0)
        self.store.add_message(project_id='p1', account_id='a1', role='assistant', content='old reply',
                               interpretation={'intent': 'requirements', 'actions': [{'type': 'show_plan'}]})
        self.assertFalse(AF.on_two_gate_flow(self.store.messages))
        self.plan_without_gate(row)
        self.assertIsNone(self.bind_error(row.fingerprint))


DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()


class ADoubleClickInParallel(unittest.TestCase):
    """Two approvals of the same spec with the SAME request_key, racing (a double click while the first is in
    flight): both pass find_reply, so the durable stores must keep it at ONE approval and ONE plan. Real Postgres
    (PostgresConversationStore + PostgresBriefRepository, every migration). Runs in intake-budget-pg (no skip)."""

    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import pathlib
        import uuid
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'dbl_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def test_same_request_key_in_parallel_is_one_approval_and_one_plan(self):
        import threading
        import uuid
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.conversation.store import PostgresConversationStore
        account, project = f'acc_{uuid.uuid4().hex[:10]}', f'prj_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                         (account, f'{account}@example.com', 'x', 'x'))
            conn.execute("INSERT INTO creator_projects (id, owner_id, title) VALUES (%s, %s, 't')", (project, account))
            conn.commit()

        def sup():                                         # a new supervisor per request = another server
            return ConversationSupervisor(briefs=PostgresBriefRepository(self.pool),
                                          store=PostgresConversationStore(self.pool))
        sup().turn(project_id=project, account_id=account, lang='en',
                   message='I need a simple internal tool for my team to track equipment loans, in English, '
                           'no login, no personal data')
        t = sup().turn(project_id=project, account_id=account, message='you decide', lang='en')
        fp = next(a['brief_fingerprint'] for a in t.actions if a['type'] == 'approve_spec')
        barrier, errors = threading.Barrier(2), []

        def click():
            try:
                barrier.wait()
                sup().approve_spec(project_id=project, account_id=account, brief_fingerprint=fp,
                                   request_key='double-click', lang='en')
            except Exception as exc:                       # a refusal is fine; a second approval is not
                errors.append(f'{type(exc).__name__}: {exc}')
        ts = [threading.Thread(target=click) for _ in range(2)]
        [x.start() for x in ts]
        [x.join(60) for x in ts]
        messages = PostgresConversationStore(self.pool).messages_for(project)
        approvals = [m for m in messages if (m.get('interpretation') or {}).get('spec_approved') == fp]
        replies = [m for m in messages if m['role'] == 'assistant' and m.get('request_key') == 'double-click']
        with self.pool.connection() as conn:
            plans = conn.execute('SELECT count(*) FROM execution_plans WHERE project_id = %s', (project,)).fetchone()[0]
        self.assertEqual(len(approvals), 1, errors)
        self.assertEqual(len(replies), 1, errors)
        self.assertEqual(plans, 1, errors)
        notice('approve-action double-click PASS', f'2 parallel approvals, same request_key -> approvals=1 replies=1 '
                                                   f'plans={plans} errors={len(errors)}')


if __name__ == '__main__':
    unittest.main()
