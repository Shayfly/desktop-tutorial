"""DECISIONS 14 (a), 2026-11-22: a content-only site is offered the question widget only when the question has somewhere
to go -- the customer's WhatsApp or e-mail. The owner's build bld_ab78f528 (a salon with a phone only) was offered it,
he ticked it, and the browser check failed the build on that form (dead_form 'q-form').
Real path: discovery.start on the customer's request, the must-ask answers the conversation gives, window_offer."""
from __future__ import annotations

import unittest

from omni_prod import discovery as d

SALON = ('אתר תדמית למספרה "סטודיו נועה", רחוב הרצל 12, חולון. טלפון 03-5551234. '
         'שעות: א׳–ה׳ 09:00–19:00, ו׳ 08:00–13:00. שירותים: תספורת, פן, צבע. כפתור להתקשרות.')


def brief(request: str, *, content_only: str = 'yes', login: str = 'none', personal: str = 'no') -> d.Brief:
    b = d.start(request)
    for field, value in (('login', login), ('personal_data', personal), ('content_only', content_only)):
        b.fields[field] = {'value': value, 'source': 'answer', 'question_id': field}
    return b


def offered(b: d.Brief) -> list[str]:
    return [w['id'] for w in d.window_offer(b)]


class TheQuestionWidgetNeedsAChannel(unittest.TestCase):
    def test_the_owners_salon_with_a_phone_only_is_not_offered_it(self):
        self.assertEqual(offered(brief(SALON)), ['cookie_banner'])

    def test_whatsapp_or_email_brings_it_back(self):
        for extra in (' וואטסאפ: 050-5551234.', ' מייל: noa@studio-noa.co.il'):
            with self.subTest(extra):
                self.assertEqual(offered(brief(SALON + extra)), ['cookie_banner', 'question_widget'])

    def test_a_negated_whatsapp_is_no_channel(self):
        self.assertEqual(offered(brief(SALON + ' אין לנו וואטסאפ.')), ['cookie_banner'])

    def test_a_site_that_is_not_content_only_keeps_it(self):
        self.assertEqual(offered(brief(SALON, content_only='no')), ['cookie_banner', 'question_widget'])
        self.assertEqual(offered(brief(SALON, login='simple')), ['cookie_banner', 'question_widget'])

    def test_a_decision_already_made_is_never_hidden(self):
        b = brief(SALON)
        d.decide_windows(b, {'question_widget': True})
        self.assertEqual(offered(b), ['cookie_banner', 'question_widget'])


if __name__ == '__main__':
    unittest.main()
