"""Michael 2026-11-13, production run "מאפייה" (prj_zKPxOjgRWXpePg):

1. personal_data was asked twice in ONE turn: a yes/no card ("האם יישמרו פרטים אישיים...?") and access_scope's three
   options ("...איך להמשיך?" -- one of them "לא לשמור פרטים אישיים"). Rule: one field, one question per turn; the
   question that also decides the field (access_scope) wins, and its answer settles personal_data too.
2. The text asked what the card asked ("רק לוודא: ...? (הבנתי מהבקשה: לא.)" above the content_only card). Rule: when a
   card is shown, the question comes from the card only; the text is context and restates only confirmed facts.
3. "בחרתי עבורכם: תאריכים: אין תאריכים; כפילויות: לאפשר; גופן: Heebo — נקי ומודרני" wrapped in the RTL bubble and
   read as a swapped label/value, a duplicate key and a key without a value. Rule: one decision per line.
"""
import os
import re
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor, _no_question
from omni_prod.intake.interpreter import DeterministicInterpreter, merge, validate_model_output
from tests.test_conversation_os import MemoryBriefs

ENV = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
       'OMNI_INTAKE_DAILY_BUDGET_USD': '0.50', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.005'}
BAKERY = ('דף נחיתה למאפייה ללקוחות, בלי התחברות, טלפון להזמנות 08-9461234, '
          'עם שמירת פרטים אישיים של לקוחות')


class BothSensitiveFields:
    """The production pattern: the model proposes personal_data AND access_scope in a sensitive (RISKY) turn."""

    def interpret(self, message, brief=None):
        model, _ = validate_model_output({
            'language': 'he', 'product_family': 'website', 'reply': 'מאפייה — נשמע מצוין. יש עוד משהו?',
            'proposals': [{'field': 'personal_data', 'value': 'yes', 'confidence': 'high', 'evidence': 'פרטים אישיים'},
                          {'field': 'access_scope', 'value': 'no_personal', 'confidence': 'high',
                           'evidence': 'בלי התחברות'},
                          {'field': 'audience', 'value': 'public', 'confidence': 'high', 'evidence': 'ללקוחות'}]},
            message)
        return merge(DeterministicInterpreter().interpret(message, brief), model, interpreter='model:fake',
                     cost_usd='0', cost_state='CONFIRMED_ZERO')


def fields(turn):
    return [q.field for q in turn.questions]


class OneFieldOneQuestion(unittest.TestCase):
    def setUp(self):
        self.s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(),
                                        worker_interpreter=BothSensitiveFields())
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def turn(self, **kw):
        return self.s.turn(project_id='p', account_id='a', lang='he', **kw)

    def test_the_production_turn_asks_personal_data_once(self):
        t = self.turn(message=BAKERY)
        self.assertEqual(len(fields(t)), len(set(fields(t))))                       # never two for one field
        self.assertEqual(fields(t), ['access_scope'])                                # the covering question wins
        self.assertNotIn(d.BY_ID['personal_data'].he, t.reply)
        self.assertEqual(t.reply.count('זה נושא רגיש'), 1)                         # one confirmation line ...
        self.assertNotIn('?', t.reply)                                              # ... naming the topic, not asking

    def test_the_covering_answer_settles_the_covered_field(self):
        self.turn(message=BAKERY)
        t = self.turn(answers={'access_scope': 'no_personal'})
        brief = self.s.briefs.latest('p').brief
        self.assertTrue(d.confirmed(brief, 'personal_data'))
        self.assertEqual(brief.fields['personal_data']['value'], 'no')
        self.assertNotIn('personal_data', fields(t))
        for value in ('internal_link', 'add_login'):                                # the other two store personal data
            b = d.answer(d.Brief(prompt='x'), {'access_scope': value})
            self.assertEqual((b.fields['personal_data']['value'], b.fields['personal_data']['confidence']),
                             ('yes', 'confirmed'))

    def test_a_turn_never_holds_two_questions_for_one_field(self):
        q = d.BY_ID
        self.assertEqual([x.field for x in d.one_question_per_field(
            [q['personal_data'], q['access_scope'], q['content_only'], q['content_only']])],
            ['access_scope', 'content_only'])
        for message in (BAKERY, 'אולי', 'בסדר', 'לא יודע'):
            t = self.turn(message=message)
            self.assertEqual(len(fields(t)), len(set(fields(t))), message)
            self.assertFalse({'personal_data', 'access_scope'} <= set(fields(t)), message)


class TheCardAsksTheTextDoesNot(unittest.TestCase):
    def test_the_production_sentence(self):
        said = 'רק לוודא: האתר רק מציג מידע, או שגם נשמר בו משהו מהמבקרים — טופס, הזמנה או רשימה? ' \
               '(הבנתי מהבקשה: לא.) אפשר גם לכתוב "תחליט אתה".'
        self.assertEqual(_no_question(said), '')
        self.assertEqual(_no_question('מאפייה עם לחם מחמצת — נשמע מצוין! יישמרו פרטים של לקוחות?'),
                         'מאפייה עם לחם מחמצת — נשמע מצוין!')

    def test_whenever_a_card_is_shown_the_text_has_no_question_about_its_field(self):
        s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            for message in ('אני רוצה מערכת תורים למספרה, בלי התחברות, הלקוחות ישאירו טלפון',
                            'מה?', 'לא יודע', 'בסדר'):
                t = s.turn(project_id='p', account_id='a', lang='he', message=message)
                for q in t.questions:
                    self.assertNotIn('?', t.reply, message)
                    self.assertNotIn(q.he, t.reply, message)
                    self.assertNotIn('הבנתי מהבקשה', t.reply, message)              # a guess is not a fact


class TheModelIsToldWhatTheCardAsks(unittest.TestCase):
    def test_the_context_names_the_card_fields_and_only_confirmed_facts(self):
        import json
        from omni_prod.intake.interpreter import SYSTEM, contextual_user
        b = d.start('דף נחיתה למאפייה')
        b.fields['style'] = {'value': 'warm', 'source': 'default', 'confidence': 'inferred'}
        b.fields['goal'] = {'value': 'להציג את המאפייה', 'source': 'message', 'confidence': 'stated'}
        b.open_material = ['content_only']
        ctx = json.loads(contextual_user('בסדר', b, ()).split('\n')[1])
        self.assertEqual(ctx['confirmed'], {'goal': 'להציג את המאפייה'})        # an assumed value is not a fact
        self.assertIn('style', ctx['assumed_not_confirmed'])
        self.assertIn('content_only', ctx['asked_with_buttons'])
        self.assertIn('context.asked_with_buttons', SYSTEM)
        self.assertIn('never phrase it as a question', SYSTEM)


class DecisionsOnePerLine(unittest.TestCase):
    def test_each_decision_is_its_own_line_with_one_key_and_its_value(self):
        s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            t = s.turn(project_id='p', account_id='a', lang='he',
                       message='אני רוצה מערכת תורים למספרה, בלי התחברות, הלקוחות ישאירו טלפון')
        head, _, rest = t.reply.partition('בחרתי עבורכם (אפשר לשנות בכל רגע):\n')
        self.assertTrue(rest, t.reply)
        lines = [x for x in rest.split('\n') if x.startswith('• ')]
        self.assertGreaterEqual(len(lines), 1)
        for line in lines:
            self.assertEqual(line.count(': '), 1, line)                             # one key, one value
            key, value = line[2:].split(': ')
            self.assertTrue(key.strip() and value.strip(), line)                    # never a key without a value
            self.assertNotIn(';', line)
        keys = [x[2:].split(': ')[0] for x in lines]
        self.assertEqual(len(keys), len(set(keys)))                                 # no duplicate key
        self.assertIsNone(re.search(r'\n ', t.reply))                               # no stray indentation


if __name__ == '__main__':
    unittest.main()
