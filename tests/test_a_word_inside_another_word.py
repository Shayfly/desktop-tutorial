"""Hebrew words are matched as words (2026-11-17, found by the conversation rehearsal on the "148 דלתות" brief):
"פירוק" (dismantling) is not "ירוק" (green), "כפתורים" (buttons) is not "תורים" (appointments), and "בלי טופס הרשמה"
(no sign-up form) does not ask for sign-up. A request that opens with "אתר", or describes a page, is a website."""
import unittest

from omni_prod import discovery as d
from omni_prod.intake.families import classify_family
from omni_prod.intake.interpreter import DeterministicInterpreter


def colours(text):
    return [p.value for p in DeterministicInterpreter().interpret(text, None).proposals if p.field == 'color']


class Words(unittest.TestCase):
    def test_dismantling_is_not_green(self):
        self.assertEqual(colours('הובלה, הרכבה, פירוק הדלת הישנה'), [])
        self.assertEqual(colours('בצבע ירוק'), ['green'])
        self.assertEqual(colours('גם וירוק'), ['green'])
        known, _ = d.extract_from_message('פירוק הדלת הישנה')
        self.assertNotIn('color', known)

    def test_buttons_are_not_appointments_and_a_refused_form_is_not_asked_for(self):
        self.assertEqual(classify_family('אתר: שני כפתורים, וואטסאפ וחיוג'), 'website')
        self.assertEqual(classify_family('אתר לדלתות, דף סטטי, בלי טופס הרשמה'), 'website')
        self.assertEqual(classify_family('אתר למספרה עם קביעת תורים'), 'web_app')

    def test_a_request_that_opens_with_a_site_is_a_website(self):
        self.assertEqual(classify_family('אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה'), 'website')
        self.assertEqual(classify_family('אתר'), 'website')
        self.assertEqual(classify_family('שם העסק: 148 דלתות. מבנה הדף: הירו, צור קשר'), 'website')

    def test_a_system_to_run_is_still_an_app(self):
        for text in ('אתר לניהול ספרייה עם מנויים', 'מערכת לניהול לקוחות', 'אתר לאטליז עם התחברות ללקוחות',
                     'אתר בעברית לניהול טבלת ליגת כדורגל'):
            self.assertEqual(classify_family(text), 'web_app', text)

    def test_a_business_site_gets_the_public_audience_not_internal(self):
        b = d.start('אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה')
        self.assertTrue(d.is_website(b))


if __name__ == '__main__':
    unittest.main()
