"""The contract's picture questions are answered in the customer's own words, asked at most twice, and worded for the
product (release review of 550320c, finding S1, 2026-11-26).

Found: `image_items` ("לאילו פריטים לשים תמונה?") and `image_subject` ("מה התמונה באתר צריכה להראות?") were asked in
place of the summary (supervisor._open_question_instead_of_gate1), but nothing wrote the customer's answer to where the
capability planner reads (capability_planner._brief_items reads only a labelled list in the brief's "Initial content:"
line; _image_subject only the customer's clause or a semantic decision). So the answer the question asks for re-asked,
forever -- bounded only by the conversation's $0.15 cost cap. Labels like "תפריט:", "Menu:", "מוצרי החנות:" were missed,
and a 3D game was asked about "the picture on the site".

Now: the supervisor records the answer on the brief (discovery.record_picture_answer), requirements_text writes it into
the approved brief, and the planner reads it there; each question is asked at most ASK_PICTURE_AT_MOST (2) times, then
the stated default is recorded, said in the summary and carried by the contract's notes.

The real path: conversation_rehearsal._Supervisor (the production ConversationSupervisor, no database) with the real
ModelInterpreter and a model double that never contacts a provider (tests.test_name_asked_once.FollowsThePrompt), and
ProductArchitect.compile on the brief the conversation saved -- the compile gate 2 runs (investor_app._brief_prompt).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from omni_prod import a4
from omni_prod import capability_planner as CP
from omni_prod import conversation_rehearsal as R
from omni_prod import discovery as d
from omni_prod.build_contract import BuildContractStatus
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.product_architect import ProductArchitect
from tests.test_name_asked_once import FollowsThePrompt

HEAD = 'אתר למסעדה "השף" עם תמונה לכל מנה.\n--- Approved project brief (binding; fingerprint 0123456789abcdef) ---\n'
RESTAURANT = ('תבנה לי אתר למסעדה שלי "השף הקטן" עם תמונות של המנות. אתר תוכן בלבד, לא שומרים כלום. '
              'טלפון 03-5551234')
CLOTHES = ('אתר לחנות הבגדים שלי "בגדי נועה" עם תמונות של המוצרים. אתר תוכן בלבד, לא שומרים כלום. טלפון 03-5551234')
ITEMS_QUESTION = 'לאילו פריטים לשים תמונה? כתבו את רשימת הפריטים, מופרדת בפסיקים.'


def compile_brief(brief):
    """The compile gate 2 runs on the saved brief (investor_app._brief_prompt)."""
    return ProductArchitect().compile((brief.prompt + '\n' + d.requirements_text(brief))[:12000],
                                      project_id='prj_pictures', contract_version=1)


def item_subjects(contract):
    return [r.constraints['subject'] for r in contract.capability_plan.requirements
            if r.key == CP.IMAGE_KEY and r.purpose == a4.ITEM_PURPOSE]


class Conversation:
    """Drives the real supervisor: the request, then each question in R.TYPED words, and `answers` for the contract's
    picture question; it stops at a picture question when `answers` is used up. Bounded by `max_turns`."""

    def __init__(self, first, answers, max_turns=12):
        self.sup = R._Supervisor(ModelInterpreter(FollowsThePrompt()))
        self.replies, self.picture_asks = [], 0
        queue = list(answers)
        t = self.say(first)
        for _ in range(max_turns):
            self.replies.append(t.reply)
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            asked = list(getattr(t, 'asked_in_words', None) or [])
            if (t.interpretation or {}).get('contract_asked') in d.PICTURE_QUESTIONS:
                self.picture_asks += 1
                if not queue:                      # asked and nothing left to answer: the caller goes on from here
                    break
                t = self.say(queue.pop(0))
            else:
                t = self.say(R.TYPED.get(asked[0], 'תחליטו אתם על השאר') if asked else 'תחליטו אתם על השאר')
        self.last = t

    def say(self, message):
        return self.sup.turn(project_id='p', account_id='a', message=message, lang='he')

    @property
    def brief(self):
        return self.sup.briefs.latest('p').brief

    @property
    def summary(self):
        return self.last.reply if any(a['type'] == 'approve_spec' for a in self.last.actions) else None


class OnTheRealPath(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'})
        p.start()
        self.addCleanup(p.stop)

    def test_the_restaurant_is_asked_once_and_the_answer_is_the_items(self):
        c = Conversation(RESTAURANT, ['שקשוקה, חומוס ופלאפל'])
        self.assertEqual(c.picture_asks, 1, c.replies)
        self.assertIsNotNone(c.summary, c.replies)
        self.assertIn('תמונה לכל פריט: שקשוקה, חומוס ופלאפל.', c.summary)
        contract = compile_brief(c.brief)
        self.assertEqual(contract.status, BuildContractStatus.READY, contract.unresolved_questions)
        self.assertEqual(item_subjects(contract), ['שקשוקה', 'חומוס', 'פלאפל'])

    def test_the_answer_the_question_asks_for_clears_it_for_the_clothes_shop(self):
        c = Conversation(CLOTHES, ['חולצות, מכנסיים ושמלות'])
        self.assertEqual(c.picture_asks, 1, c.replies)
        self.assertIsNotNone(c.summary, c.replies)
        self.assertEqual(item_subjects(compile_brief(c.brief)), ['חולצות', 'מכנסיים', 'שמלות'])

    def test_no_answer_is_asked_twice_then_the_stated_default(self):
        c = Conversation(RESTAURANT, ['תעשו מה שנראה לכם יפה ומתאים למסעדה שלנו בבקשה', 'אין לי מושג, תחליטו אתם'])
        self.assertEqual(c.picture_asks, 2, c.replies)
        self.assertEqual(sum(ITEMS_QUESTION in r for r in c.replies), 2)
        # the second ask says it was not read, and what happens without an answer (never "nothing new")
        second = [r for r in c.replies if ITEMS_QUESTION in r][1]
        self.assertIn('לא הצלחתי לקרוא מההודעה רשימת פריטים', second)
        self.assertIsNotNone(c.summary, c.replies)
        self.assertIn('לא קיבלנו רשימת פריטים, ולכן לא תיווצר תמונה לכל פריט. הפריטים יוצגו כטקסט.', c.summary)
        contract = compile_brief(c.brief)
        self.assertEqual(contract.status, BuildContractStatus.READY, contract.unresolved_questions)
        self.assertIn(CP.IMAGE_ITEMS_DEFAULTED, contract.capability_plan.notes)        # in the evidence
        self.assertNotIn(CP.IMAGE_ITEMS_UNREAD, contract.capability_plan.notes)
        self.assertIn(CP.PICTURE_ITEMS_DEFAULT, contract.prompt.splitlines())
        self.assertEqual(item_subjects(contract), [])

    def test_an_approve_press_after_two_asks_records_the_default_and_shows_it(self):
        c = Conversation(RESTAURANT, ['תעשו מה שנראה לכם'])          # stops at the second ask, unanswered
        sup = c.sup
        self.assertEqual(c.picture_asks, 2, c.replies)
        self.assertEqual((c.last.interpretation or {}).get('contract_asked'), 'image_items')
        row = sup.briefs.latest('p')
        t = sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=row.fingerprint, lang='he')
        self.assertIn('לא קיבלנו רשימת פריטים', t.reply)
        self.assertTrue(any(a['type'] == 'approve_spec' for a in t.actions), t.reply)
        self.assertEqual(sup.briefs.latest('p').brief.assets['pictures'], {'image_items': {'default': True}})


class TheLabelReader(unittest.TestCase):
    def test_common_labels_in_three_languages_case_and_spacing_tolerant(self):
        for label in ('מנות', 'המנות שלנו', 'תפריט', 'סוגי מנות', 'מוצרי החנות', 'שירותי המספרה', 'פריטים', 'Dishes',
                      'Menu', 'MENU ', '  our   menu', 'Products', 'القائمة', 'قائمة الطعام', 'منتجاتنا', 'الخدمات'):
            with self.subTest(label):
                p = HEAD + f'Initial content: השף; {label}: שקשוקה, חומוס ופלאפל\n'
                self.assertEqual(CP._brief_items(p), ('שקשוקה', 'חומוס', 'פלאפל'))

    def test_an_arabic_list_with_arabic_commas_and_wa(self):
        p = HEAD + 'Initial content: الشيف؛ الأطباق: شكشوكة، حمص وفلافل\n'
        self.assertEqual(CP._brief_items(p), ('شكشوكة', 'حمص', 'فلافل'))

    def test_a_word_that_is_not_a_label_is_still_not_read(self):
        p = HEAD + 'Initial content: השף; כתובת: הרצל 1, חיפה ותל אביב\n'
        self.assertEqual(CP._brief_items(p), ())

    def test_the_answer_reader(self):
        self.assertEqual(CP.answer_items('חולצות, מכנסיים ושמלות'), ('חולצות', 'מכנסיים', 'שמלות'))
        self.assertEqual(CP.answer_items('מוצרים: חולצות, מכנסיים'), ('חולצות', 'מכנסיים'))
        self.assertEqual(CP.answer_items('פיצה'), ('פיצה',))
        for sentence in ('תעשו מה שנראה לכם יפה ומתאים למסעדה שלנו בבקשה', 'לא יודע', 'מה זה אומר?', 'you decide',
                         'אני רוצה שהאתר יראה מאוד מקצועי ומזמין לכל מי שנכנס אליו'):
            with self.subTest(sentence):
                self.assertEqual(CP.answer_items(sentence), ())


class TheSubjectQuestion(unittest.TestCase):
    GAME = 'תבנה לי משחק תלת מימד של מרוץ מכוניות בדפדפן'

    def _compile(self, request, answer=None, default=False):
        brief = d.start(request)
        if answer or default:
            d.record_picture_answer(brief, 'image_subject', None if default else answer)
        return compile_brief(brief)

    def test_a_game_is_asked_about_the_games_picture_never_the_site(self):
        contract = self._compile(self.GAME)
        (q,) = [q for q in contract.unresolved_questions if q.id == 'image_subject']
        self.assertEqual(q.question, 'מה התמונה של המשחק צריכה להראות? כתבו במשפט אחד מה רואים בה.')
        self.assertNotIn('אתר', q.question)
        (en,) = [q for q in self._compile('Build me a 3D racing game in the browser').unresolved_questions
                 if q.id == 'image_subject']
        self.assertEqual(en.question, "What should the game's picture show? Describe it in one sentence.")

    def test_the_customers_answer_is_the_pictures_subject(self):
        contract = self._compile(self.GAME, 'בתמונה רואים מכונית מרוץ אדומה')
        self.assertEqual([q.id for q in contract.unresolved_questions if q.id.startswith('image')], [])
        self.assertNotIn(CP.IMAGE_SUBJECT_UNRESOLVED, contract.capability_plan.notes)
        (img,) = [r for r in contract.capability_plan.requirements if r.key == CP.IMAGE_KEY]
        self.assertEqual(img.constraints['subject'], 'בתמונה רואים מכונית מרוץ אדומה')

    def test_the_default_leaves_the_picture_out_and_says_so(self):
        contract = self._compile(self.GAME, default=True)
        self.assertEqual([q.id for q in contract.unresolved_questions if q.id.startswith('image')], [])
        self.assertIn(CP.IMAGE_SUBJECT_DEFAULTED, contract.capability_plan.notes)
        self.assertEqual([r for r in contract.capability_plan.requirements if r.key == CP.IMAGE_KEY], [])

    def test_the_wording_per_product_kind(self):
        from omni_prod.product_architect import ProductArchitect as PA
        for keys, word in ((('target.web',), 'באתר'), (('target.game.3d',), 'של המשחק'),
                           (('target.android.source',), 'של האפליקציה'), (('target.ios.source',), 'של האפליקציה')):
            with self.subTest(keys):
                self.assertIn(word, PA._image_subject_question('תמונה', keys).question)
        self.assertIn('اللعبة', PA._image_subject_question('لعبة سباق', ('target.game.3d',)).question)
        self.assertIn('التطبيق', PA._image_subject_question('تطبيق', ('target.android.source',)).question)
        self.assertEqual(PA._image_items_question('موقع لمطعم').question, 'لأي عناصر نضع صورة؟ اكتبوا قائمة العناصر مفصولة '
                                                                          'بفواصل.')


class TheRecord(unittest.TestCase):
    def test_an_unknown_question_or_an_empty_answer_raises(self):
        brief = d.start('אתר')
        with self.assertRaises(ValueError):
            d.record_picture_answer(brief, 'colour', 'x')
        with self.assertRaises(ValueError):
            d.record_picture_answer(brief, 'image_items', '   ')

    def test_the_answer_changes_the_fingerprint_the_approval_binds_to(self):
        brief = d.start('אתר למסעדה')
        before = brief.fingerprint()
        self.assertTrue(d.record_picture_answer(brief, 'image_items', 'שקשוקה, חומוס'))
        self.assertNotEqual(brief.fingerprint(), before)
        self.assertFalse(d.record_picture_answer(brief, 'image_items', 'שקשוקה, חומוס'))     # idempotent
        self.assertIn(CP.PICTURE_ITEMS_ANSWER + 'שקשוקה, חומוס', d.requirements_text(brief).splitlines())


if __name__ == '__main__':
    unittest.main()
