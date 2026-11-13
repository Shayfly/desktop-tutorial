"""#335 part 1 (Michael 2026-11-13): (a) facts come from EVERY customer message; (b) the truth gate checks hours.

Build bld_cf406df6 ("בית קפה", 2026-11-12): the customer wrote "א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור" and a phone
number. Both were lost from the brief's fields in the "מה נכון?" loop, the fact canon was empty, and the page said
"שבת 08:00 - 16:00" -- invented, contradicting an explicit request. The truth gate never compared hours."""
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod import opening_hours as H
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.fact_canon import build_canon, fact_spans
from omni_prod.skills_runtime import _invented_contact
from tests.test_conversation_os import MemoryBriefs

SAID = 'שעות: א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור. טלפון 03-1234567'
# what build bld_cf406df6 put on the page
BUILT = ('<html dir="rtl"><body><h2>שעות פתיחה</h2><p>ראשון - חמישי</p><p>07:30 - 18:00</p>'
         '<p>שישי</p><p>07:30 - 14:00</p><p>שבת</p><p>08:00 - 16:00</p></body></html>')
RIGHT = ('<html><body><h2>שעות פתיחה</h2><p>ראשון–חמישי 07:00–19:00</p><p>שישי 07:00–14:00</p><p>שבת סגור</p>'
         '<a href="tel:03-1234567">התקשרו</a></body></html>')


def hours_findings(page, request):
    return [f for f in _invented_contact({'index.html': page}, {'request': request}) if 'hours' in f.problem]


class ReadingHours(unittest.TestCase):
    def test_the_forms_customers_and_pages_use(self):
        week = {0: (420, 1140), 1: (420, 1140), 2: (420, 1140), 3: (420, 1140), 4: (420, 1140)}
        self.assertEqual(H.parse(SAID), {**week, 5: (420, 840), 6: H.CLOSED})
        self.assertEqual(H.parse('ראשון - חמישי 07:00 - 19:00'), week)
        self.assertEqual(H.parse('א-ה 07:00-19:00'), week)
        self.assertEqual(H.parse("יום ו' 7:00-14:00"), {5: (420, 840)})
        self.assertEqual(H.parse('Sun-Thu 7:00-19:00, Saturday closed'), {**week, 6: H.CLOSED})

    def test_not_hours(self):
        for text in ('שעות פתיחה יפורסמו בקרוב', '08:00-14:00', 'אבא-אמא 10:00-11:00', 'בשני ובשלישי'):
            self.assertEqual(H.parse(text), {}, text)


class FactsFromEveryMessage(unittest.TestCase):                                     # (a)
    def test_the_spans_are_the_customers_own_words(self):
        self.assertEqual(fact_spans(SAID), ['03-1234567', 'א׳–ה׳ 07:00–19:00', 'ו׳ 07:00–14:00', 'שבת סגור'])

    def test_a_fact_in_a_later_message_reaches_the_approved_request_and_the_canon(self):
        s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            s.turn(project_id='p', account_id='a', lang='he',
                   message='דף נחיתה לבית קפה קטן עם תמונה ראשית וכפתור הזמנת שולחן')
            s.turn(project_id='p', account_id='a', lang='he', message=SAID)
            s.turn(project_id='p', account_id='a', lang='he', message='בסדר')        # a later turn keeps them
        brief = s.briefs.latest('p').brief
        self.assertEqual(brief.assets['facts']['spans'], fact_spans(SAID))
        approved = brief.prompt + '\n' + d.requirements_text(brief)
        self.assertIn(d.CUSTOMER_FACTS_PREFIX, approved)
        canon = build_canon(approved)
        self.assertEqual(canon.values('phone'), {'+97231234567'})
        self.assertIn('6:closed', canon.values('hours_day'))

    def test_no_facts_no_line(self):
        brief = d.start('דף נחיתה לבית קפה')
        self.assertNotIn(d.CUSTOMER_FACTS_PREFIX, d.requirements_text(brief))


class TheTruthGateChecksHours(unittest.TestCase):                                  # (b)
    def test_the_production_page_contradicts_the_customer(self):
        found = hours_findings(BUILT, SAID)
        contradicted = [f for f in found if 'contradict' in f.problem]
        self.assertEqual(len(contradicted), 1)
        self.assertEqual(contradicted[0].severity, 'blocking')
        self.assertIn('what the customer wrote: שבת: הדף 08:00-16:00, הלקוח סגור;', contradicted[0].problem)   # first
        self.assertIn('ראשון: הדף 07:30-18:00, הלקוח 07:00-19:00', contradicted[0].problem)

    def test_hours_the_customer_never_gave_are_invented(self):
        [f] = hours_findings(BUILT, 'דף נחיתה לבית קפה קטן')
        self.assertEqual(f.severity, 'blocking')
        self.assertIn('invented', f.problem)

    def test_the_customers_hours_pass(self):
        self.assertEqual(_invented_contact({'index.html': RIGHT}, {'request': SAID}), [])

    def test_a_page_without_hours_passes(self):
        page = '<html><body><h2>שעות פתיחה</h2><p>יפורסמו בקרוב</p></body></html>'
        self.assertEqual(hours_findings(page, 'דף נחיתה לבית קפה'), [])

    def test_a_day_the_customer_did_not_mention_is_invented(self):
        found = hours_findings('<p>א-ה 07:00-19:00</p><p>שבת 09:00-12:00</p>', 'א׳–ה׳ 07:00–19:00')
        self.assertTrue(any('invented' in f.problem and 'שבת' in f.problem for f in found))


if __name__ == '__main__':
    unittest.main()
