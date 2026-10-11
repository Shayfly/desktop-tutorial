"""Founder build "חגית" (2026-10-11): a Hebrew landing page with no sign-in and no personal data failed behavioural
acceptance on data_create/responsive. These tests pin the structured, fail-closed handling of a content-only site:
only an explicit customer answer plus no sign-in plus no personal data waives data_create; everything else keeps
the full floor. No model, no network, no paid call."""
import http.server
import threading
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor, classify_intent
from omni_prod.product_architect import ProductArchitect, content_only_approved, strip_whatsapp_links
from omni_prod.web_saas_acceptance import WEB_SAAS_REQUIRED_KINDS, WebSaaSAcceptanceRunner, acceptance_scope
from tests.test_conversation_os import MemoryBriefs

PROMPT = ('אני רוצה דף נחיתה בעברית לעסק של כיסויי ראש. בלי התחברות, בלי איסוף פרטים אישיים, '
          'קישור לוואטסאפ, לוגו וטקסט, ומחירון')


def approved_brief(content_only='yes', personal='no', login='none'):
    b = d.start(PROMPT)
    b = d.answer(b, {'login': login, 'personal_data': personal, 'content_only': content_only}) if content_only else \
        d.answer(b, {'login': login, 'personal_data': personal})
    return b


def compile_contract(brief):
    text = brief.prompt + d.requirements_text(brief)
    return ProductArchitect().compile(text, project_id='p', contract_version=1).to_dict()


class ExtractionTests(unittest.TestCase):
    def test_no_personal_data_is_read_from_hebrew_and_english(self):
        self.assertEqual(d.start(PROMPT).values().get('personal_data'), 'no')
        self.assertEqual(d.start('A landing page, no login, without collecting personal data').values().get('personal_data'), 'no')

    def test_delegation_never_decides_content_only(self):
        b = d.start(PROMPT, d.RECOMMEND)
        self.assertNotEqual(b.values().get('content_only'), 'yes')
        self.assertNotIn('Product kind: CONTENT-ONLY', d.requirements_text(b))

    def test_marker_needs_explicit_yes_no_login_no_personal_data(self):
        self.assertIn('CONTENT-ONLY', d.requirements_text(approved_brief()))
        self.assertNotIn('CONTENT-ONLY', d.requirements_text(approved_brief(content_only='no')))
        self.assertNotIn('CONTENT-ONLY', d.requirements_text(approved_brief(personal='yes')))
        self.assertNotIn('CONTENT-ONLY', d.requirements_text(approved_brief(login='simple')))


class ContractScopeTests(unittest.TestCase):
    def test_free_text_alone_never_marks_a_static_site(self):
        self.assertFalse(content_only_approved(PROMPT))
        self.assertFalse(content_only_approved('Product kind: CONTENT-ONLY website. Sign-in: NONE'))   # no brief block
        c = ProductArchitect().compile(PROMPT, project_id='p', contract_version=1).to_dict()
        self.assertNotIn('static_content_site', c['defaults_applied'])
        self.assertIn('data_create', acceptance_scope(c)[0])

    def test_approved_content_only_waives_data_create_and_nothing_else_of_the_floor(self):
        c = compile_contract(approved_brief())
        self.assertIn('static_content_site', c['defaults_applied'])
        required, waived = acceptance_scope(c)
        self.assertNotIn('data_create', required)
        self.assertEqual(set(required), {'data_read', 'responsive', 'api_smoke'})
        self.assertIn('data_create', waived)

    def test_whatsapp_link_is_not_a_messaging_integration(self):
        c = compile_contract(approved_brief())
        self.assertNotIn('messaging', c['required_integrations'])
        self.assertIn('integration', acceptance_scope(c)[1])
        self.assertNotIn('wa.me', strip_whatsapp_links('כפתור וואטסאפ https://wa.me/972500000000'))
        # real messaging is still messaging
        self.assertIn('messaging', ProductArchitect._infer_integrations('send whatsapp message reminders', _NoCaps()))

    def test_every_other_case_keeps_the_full_floor(self):
        base = compile_contract(approved_brief())
        self.assertEqual(acceptance_scope(None), (WEB_SAAS_REQUIRED_KINDS, ()))
        no_prompt = {k: v for k, v in base.items() if k != 'prompt'}
        self.assertIn('data_create', acceptance_scope(no_prompt)[0])
        with_login = dict(base, user_roles=['admin', 'staff'])
        self.assertIn('data_create', acceptance_scope(with_login)[0])
        external = dict(base, required_integrations=['payments'])
        self.assertIn('data_create', acceptance_scope(external)[0])
        storage = dict(base, infrastructure=[{'kind': 'object_storage', 'required': True}])
        self.assertIn('data_create', acceptance_scope(storage)[0])
        crud_app = compile_contract(approved_brief(content_only='no'))
        self.assertIn('data_create', acceptance_scope(crud_app)[0])
        self.assertIn('data_read', acceptance_scope(base)[0])
        self.assertIn('responsive', acceptance_scope(base)[0])


class _NoCaps:
    requirements = ()


class _Static(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = ('<html><head><meta name="viewport" content="width=device-width"></head>'
                '<body dir="rtl">כיסויי ראש — מחירון: 120 ₪</body></html>').encode()
        self.send_response(200 if self.path in ('/', '/health') else 404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Static)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.srv.server_address[1]}'

    def tearDown(self):
        self.srv.shutdown()

    def plan(self, with_create=False):
        steps = [
            {'id': 'content', 'kind': 'data_read', 'acceptance_ids': ['A1'], 'method': 'GET', 'path': '/',
             'expect_status': 200, 'expect_text_contains': '120'},
            {'id': 'mobile', 'kind': 'responsive', 'acceptance_ids': ['A2'], 'method': 'GET', 'path': '/',
             'expect_status': 200, 'expect_text_contains': 'viewport'},
            {'id': 'health', 'kind': 'api_smoke', 'acceptance_ids': ['A3'], 'method': 'GET', 'path': '/health',
             'expect_status': 200},
        ]
        if with_create:
            steps.append({'id': 'create', 'kind': 'data_create', 'acceptance_ids': ['A4'], 'method': 'POST',
                          'path': '/api/items', 'json': {'x': 1}, 'expect_status': 201})
        return [{'id': 'visitor', 'steps': steps}]

    def spec(self, n):
        return {'acceptance': [{'id': f'A{i}'} for i in range(1, n + 1)]}

    def test_static_site_passes_without_a_fake_create_but_a_crud_contract_does_not(self):
        static = compile_contract(approved_brief())
        preview = {'id': 'prv', 'project_id': 'p', 'version_id': 'v', 'preview_url': self.url}
        rep = WebSaaSAcceptanceRunner(build_contract=static).verify(preview, self.spec(3), self.plan())
        self.assertEqual(rep.status, 'PASS', rep.summary)
        self.assertIn('data_create', rep.not_required_kinds)
        crud = compile_contract(approved_brief(content_only='no'))
        rep2 = WebSaaSAcceptanceRunner(build_contract=crud).verify(preview, self.spec(3), self.plan())
        self.assertEqual(rep2.status, 'FAIL')
        self.assertIn('data_create', rep2.missing_kinds)

    def test_a_real_defect_still_fails_for_the_static_site(self):
        static = compile_contract(approved_brief())
        plan = self.plan()
        plan[0]['steps'][0]['expect_text_contains'] = '999 ₪'            # the page does not show that price
        rep = WebSaaSAcceptanceRunner(build_contract=static).verify(
            {'id': 'prv', 'project_id': 'p', 'version_id': 'v', 'preview_url': self.url}, self.spec(3), plan)
        self.assertEqual(rep.status, 'FAIL')
        self.assertTrue(any(not c.passed for c in rep.checks))


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())

    def say(self, m=None, answers=None):
        return self.s.turn(project_id='p', account_id='a', message=m or '', answers=answers, lang='he')

    def complete(self):
        t = self.say(PROMPT)
        for _ in range(8):
            if not t.questions:
                break
            q = t.questions[0]
            val = {'content_only': 'yes'}.get(q.id) or (q.options[0].value if getattr(q, 'options', None) else d.DELEGATE)
            t = self.say(answers={q.id: val})
        return t

    def test_bare_start_asks_for_approval_only_once_a_brief_exists(self):
        for m in ('תתחיל', 'בוא נתחיל', 'תתחיל לבנות עכשיו', 'go'):
            self.assertEqual(classify_intent(m, has_version=False, has_brief=True), 'approve', m)
        self.assertEqual(classify_intent('תבנה לי דף נחיתה לעסק', has_version=False, has_brief=False), 'requirements')
        self.assertEqual(classify_intent('תבנה לי דף נחיתה לעסק', has_version=False, has_brief=True), 'requirements')

    def test_start_gives_the_approval_action_and_does_not_repeat_the_ready_text(self):
        t = self.complete()
        self.assertTrue(t.brief_row.complete, t.reply)
        t2 = self.say('תתחיל')
        self.assertEqual(t2.intent, 'approve')
        self.assertTrue(any(a['type'] == 'approve_build' for a in t2.actions))

    def test_prices_after_completion_are_recorded_and_change_the_fingerprint(self):
        t = self.complete()
        before = t.brief_row.fingerprint
        t2 = self.say('המחירון: כיסוי ראש רגיל 120 ₪, כיסוי פרימיום 180 ₪')
        self.assertNotEqual(t2.brief_row.fingerprint, before)                 # a previous approval no longer matches
        self.assertIn('180', t2.brief_row.brief.values()['content'])
        self.assertIn('בוטל', t2.reply)
        self.assertNotEqual(t2.reply, t.reply)

    def test_whatsapp_link_question_is_not_an_sms_blocker(self):
        self.complete()
        r = self.say('אפשר להוסיף קישור לוואטסאפ?').reply
        self.assertNotIn('SMS', r)


if __name__ == '__main__':
    unittest.main()
