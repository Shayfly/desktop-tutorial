"""C9 (CEO 2026-10-27, LANG-001): the product language follows the customer's language; Arabic and other
unsupported languages are told so honestly and are never assumed to want a Hebrew product."""
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import UNSUPPORTED_NOTICE, ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

HE = 'אני רוצה אתר למספרה שלי'
EN = 'I want a website for my barbershop'
AR = 'أريد موقعًا لصالون الحلاقة الخاص بي'


def first_turn(message):
    return ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore()).turn(
        project_id='p', account_id='a', message=message)


def product_language(turn):
    f = turn.brief_row.brief.fields.get('languages')
    return f and f['value']


class ProductLanguageFollowsTheCustomer(unittest.TestCase):
    def test_hebrew_customer_gets_a_hebrew_product(self):
        t = first_turn(HE)
        self.assertEqual(t.language, 'he')
        self.assertEqual(product_language(t), 'he')

    def test_english_customer_gets_an_english_product_not_hebrew(self):
        t = first_turn(EN)
        self.assertEqual(t.language, 'en')
        self.assertEqual(product_language(t), 'en')
        self.assertNotIn('language: Hebrew', t.reply)

    def test_an_explicit_choice_wins_over_the_writing_language(self):
        t = first_turn('I want a website for my barbershop, in Hebrew')
        self.assertEqual(product_language(t), 'he')

    def test_the_default_function(self):
        self.assertEqual(d.product_language_default(HE), 'he')
        self.assertEqual(d.product_language_default(EN), 'en')
        self.assertIsNone(d.product_language_default(AR))
        self.assertIsNone(d.product_language_default('Хочу сайт для моей парикмахерской'))


class UnsupportedLanguagesAreBlockedHonestly(unittest.TestCase):
    def test_arabic_is_not_read_as_hebrew(self):
        self.assertEqual(first_turn(AR).language, 'ar')

    def test_arabic_gets_the_honest_notice_first_and_no_hebrew_text(self):
        t = first_turn(AR)
        self.assertTrue(t.reply.startswith(UNSUPPORTED_NOTICE['ar']))
        self.assertNotIn('בחרתי עבורכם', t.reply)
        self.assertIsNone(__import__('re').search(r'[\u0590-\u05ff]', t.reply), t.reply)   # no Hebrew at all

    def test_arabic_is_never_assumed_to_want_a_hebrew_product(self):
        t = first_turn(AR)
        self.assertNotEqual(product_language(t), 'he')
        self.assertIn('languages', [q.field for q in d.pending(t.brief_row.brief)] + [q.field for q in t.questions]
                      if product_language(t) is None else ['languages'])

    def test_another_script_gets_the_english_notice(self):
        t = first_turn('Хочу сайт для моей парикмахерской')
        self.assertTrue(t.reply.startswith(UNSUPPORTED_NOTICE['other']))

    def test_supported_languages_get_no_notice(self):
        for m in (HE, EN):
            self.assertNotIn('Honest note', first_turn(m).reply)


if __name__ == '__main__':
    unittest.main()
