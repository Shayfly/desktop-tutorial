"""Warehouse 113 (owner 2026-11-16): the image-question loop that kept customers from building.

Found: a customer uploaded a photo of the shop's door; asked "what is in it?" they typed "זאת הדלת של החנות", then
"דלת עם ידית", then "מוצר". None of it was read (the question was a choice, only a button answered it), the question came
back, and after three cards the buttons were replaced by "חסרה החלטה על קיבלתי את התמונה. מה יש בה?" -- the topic
printed as the whole question, the way forward only in another tab. Reproduced on main d496a92 with the probe in
STATUS (2026-11-16).

Real path: ConversationSupervisor.turn with the deterministic interpreter (the in-memory stores stand in for SQL only),
discovery.panel_group (what the Requirements panel shows) and app.js's own stillMissingLine() run in node.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from omni_prod import discovery as d
from omni_prod.intake import image_answers as A
from tests.test_uploaded_main_image import PHOTO, _conversation

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


def uploaded():
    s, briefs = _conversation()
    t = s.turn(project_id='p', account_id='a', message='התמונה של החנות', attachments=[PHOTO], lang='he')
    assert [q.id for q in t.questions] == ['image_kind'], t.questions
    return s, briefs


def say(s, text):
    return s.turn(project_id='p', account_id='a', message=text, lang='he')


class TypedWordsAreRead(unittest.TestCase):
    def test_the_category_words_of_the_owner(self):
        for text, kind in (('זאת הדלת של החנות', 'product'), ('דלת עם ידית', 'product'), ('מוצר', 'product'),
                           ('הבעלים של העסק', 'person'), ('זה אני', 'person'), ('השם שלו שמעון', 'person'),
                           ('החנות מבפנים', 'place'), ('מקום', 'place'), ('הלוגו שלי', 'logo'), ('משהו אחר', 'other'),
                           ('the shop door', 'product'), ('our owner', 'person')):
            with self.subTest(text):
                self.assertEqual(A.kind_of(text), kind)

    def test_no_category_word_is_no_guess(self):
        for text in ('שלום', 'לא יודע', 'בדיקה', ''):
            with self.subTest(text):
                self.assertIsNone(A.kind_of(text))
                self.assertEqual(A.answers_for(d.BY_ID['image_kind'], text), {})

    def test_the_description_is_kept_in_the_customers_words(self):
        self.assertEqual(A.answers_for(d.BY_ID['image_kind'], 'זאת הדלת של החנות'),
                         {'image_kind': 'product', 'image_who_product': 'הדלת של החנות'})
        self.assertEqual(A.answers_for(d.BY_ID['image_kind'], 'מוצר'), {'image_kind': 'product'})   # asked "what" next
        self.assertEqual(A.answers_for(d.BY_ID['image_kind'], 'הלוגו שלי'), {'image_kind': 'logo'})
        self.assertEqual(A.answers_for(d.BY_ID['image_use'], 'כמו שהיא'), {'image_use': 'as_is'})
        self.assertEqual(A.answers_for(d.BY_ID['image_use'], 'רק השראה'), {'image_use': 'inspiration'})
        self.assertEqual(A.answers_for(d.BY_ID['image_place_product'], 'למעלה, תמונה ראשית'), {'image_place_product': 'hero'})


class TheLoopEnds(unittest.TestCase):
    def test_the_production_sentence_moves_the_conversation_to_the_end(self):
        s, briefs = uploaded()
        t = say(s, 'זאת הדלת של החנות')
        v = briefs.latest('p').brief.values()
        self.assertEqual((v['image_kind'], v['image_identity']), ('product', 'הדלת של החנות'))
        self.assertEqual([q.id for q in t.questions], ['image_use'])          # "who/what" is not asked again
        t = say(s, 'כמו שהיא')
        self.assertEqual([q.id for q in t.questions], ['image_place_product'])
        t = say(s, 'למעלה, תמונה ראשית')
        brief = briefs.latest('p').brief
        self.assertIsNone(d.next_image_question(brief))
        [img] = d.placed_images(brief)
        self.assertEqual((img['kind'], img['alt'], img['use'], img['place']), ('product', 'הדלת של החנות', 'as_is', 'hero'))

    def test_a_message_nobody_asked_for_is_not_read_as_an_answer(self):
        s, briefs = _conversation()
        say(s, 'מוצרים טריים כל יום')                              # no image, no image question: an ordinary message
        self.assertIsNone(briefs.latest('p').brief.values().get('image_kind'))

    def test_the_card_keeps_its_buttons_and_the_chat_says_how_to_answer(self):
        s, _ = uploaded()
        for text in ('בדיקה', 'עוד בדיקה', 'עוד אחת', 'ושוב'):
            t = say(s, text)
        self.assertEqual([q.id for q in t.questions], ['image_kind'])          # the buttons are still in the chat
        self.assertNotIn('open_requirements', [a['type'] for a in t.actions])
        self.assertNotIn('לשונית', t.reply)
        self.assertNotIn('קיבלתי את התמונה. מה יש בה?,', t.reply)               # the question printed as a topic
        last_two = [m['content'] for m in s.store.messages_for('p', limit=50) if m['role'] == 'assistant'][-2:]
        self.assertTrue(any('מה בתמונה' in r for r in last_two), last_two)    # says what is missing (rephrased in turn)
        t = say(s, 'מוצר')                                                     # and the words still answer it
        self.assertEqual([q.id for q in t.questions], ['image_who_product'])

    def test_the_same_message_is_never_sent_twice_in_a_row(self):
        s, _ = uploaded()
        for text in ('בדיקה', 'עוד בדיקה', 'עוד אחת', 'ושוב', 'ושוב פעם'):
            say(s, text)
        replies = [m['content'] for m in s.store.messages_for('p', limit=50) if m['role'] == 'assistant']
        for a, b in zip(replies, replies[1:]):
            self.assertNotEqual(a, b)


class OneSourceForChatAndPanel(unittest.TestCase):
    def test_the_panel_shows_the_chats_question_and_only_it(self):
        s, briefs = uploaded()
        brief = briefs.latest('p').brief
        group, questions = d.panel_group(brief)
        self.assertEqual([q.id for q in questions], ['image_kind'])
        self.assertTrue(len(d.next_group(brief)[1]) >= 1)
        say(s, 'זאת הדלת של החנות')
        brief = briefs.latest('p').brief
        self.assertEqual([q.id for q in d.panel_group(brief)[1]], [d.next_image_question(brief).id])

    def test_without_an_open_image_question_the_panel_is_unchanged(self):
        _, briefs = _conversation()
        brief = briefs.latest('p').brief
        self.assertEqual(d.panel_group(brief), d.next_group(brief))


def js_still_missing(disc, lang):
    source = APP.read_text(encoding='utf-8')
    translations = source[source.index('const T ='):source.index('const S =')]
    extra = ''.join(re.findall(r'Object\.assign\(T\.(?:he|en), \{.*?\}\);\n', source, re.S))
    fn = re.search(r'function stillMissingLine\(.*?\n\}', source, re.S).group()
    js = (translations + extra + f'\nconst S={{lang:{json.dumps(lang)}}};\nfunction t(k){{return T[S.lang][k];}}\n' + fn +
          f'\nconsole.log(JSON.stringify(stillMissingLine({json.dumps(disc, ensure_ascii=False)})));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js stillMissingLine()')
class UpdateThePlanSaysWhatIsMissing(unittest.TestCase):
    def test_an_incomplete_brief_names_what_is_missing(self):
        disc = {'complete': False, 'questions': [{'text': 'קיבלתי את התמונה. מה יש בה?'}]}
        self.assertEqual(js_still_missing(disc, 'he'), 'כדי להמשיך חסר עוד: קיבלתי את התמונה. מה יש בה?')
        self.assertEqual(js_still_missing({'complete': False, 'questions': []}, 'he'),
                         'כדי להמשיך חסרה עוד תשובה אחת בשיחה.')

    def test_a_complete_brief_says_nothing(self):
        self.assertEqual(js_still_missing({'complete': True, 'questions': []}, 'he'), '')


if __name__ == '__main__':
    unittest.main()
