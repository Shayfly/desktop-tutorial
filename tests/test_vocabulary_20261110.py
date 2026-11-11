"""CEO 2026-11-10: Hebrew-aware vocabulary -- whole words with prefixes, more words, no substring traps."""
import unittest

from omni_prod import discovery as d
from omni_prod import vocabulary as v
from omni_prod import web_saas_acceptance as wsa
from omni_prod.intake.interpreter import DeterministicInterpreter
from omni_prod.product_architect import _requires_outbound_delivery, no_login_requested

CAFE = ('דף נחיתה לבית קפה שכונתי בחיפה. קפה חם, לחם טרי ומאפים, נשמח לראות אתכם. פתוח כל יום 07:00-14:00. '
        'טלפון 04-8123456, מייל cafe@example.org, משלוחים בשכונה, הזמנה ב-WhatsApp. העלאת מחירים לא צפויה.')


def proposals(msg):
    return {p.field: p.value for p in DeterministicInterpreter().interpret(msg).proposals}


class MatcherTests(unittest.TestCase):
    def test_whole_words_with_prefixes(self):
        self.assertTrue(v.has_any('ולמחוק את ההזמנה', v.DELETE_WORDS))
        self.assertTrue(v.has_any('אפשר לבטל', v.DELETE_WORDS))
        self.assertTrue(v.has_any('כשמבטלים', ('מבטל*',)))
        self.assertFalse(v.has_any('נראה טוב בטלפון', v.DELETE_WORDS))
        self.assertFalse(v.has_any('מחקר שוק והסרטון', v.DELETE_WORDS))
        self.assertFalse(v.has_any('במצב רוח טוב', v.UPDATE_WORDS))
        self.assertFalse(v.has_any('a market for done-for-you exchanges', ('mark', 'change')))

    def test_english_stems_and_geresh(self):
        self.assertTrue(v.has_any('cancellation policy', v.DELETE_WORDS))
        self.assertTrue(v.has_any("צבע בז׳", ("בז'",)))
        self.assertTrue(v.has_any('כחול-כהה', ('כחול כהה',)))

    def test_sandbox_copy_is_identical(self):
        self.assertEqual(wsa._UPDATE_WORDS, v.UPDATE_WORDS)
        self.assertEqual(wsa._DELETE_WORDS, v.DELETE_WORDS)
        for text in ('בטלפון', 'לבטל', 'ולמחוק', 'status', 'במצב', 'cancelled', 'לעדכן'):
            self.assertEqual(wsa._has_any(text, wsa._DELETE_WORDS), v.has_any(text, v.DELETE_WORDS), text)
            self.assertEqual(wsa._has_any(text, wsa._UPDATE_WORDS), v.has_any(text, v.UPDATE_WORDS), text)


class CafeDoesNotGetWhatItNeverAskedFor(unittest.TestCase):
    def test_intake(self):
        got = proposals(CAFE)
        self.assertNotIn('style', got)            # "קפה חם" / "לחם" are not a warm style
        self.assertNotIn('personal_data', got)    # the cafe's own phone is not collecting data
        self.assertNotIn('dates', got)            # "הזמנה ב-WhatsApp" alone is not a booking calendar
        known, hints = d.extract_from_message(CAFE)
        self.assertEqual(hints.get('content_only'), 'yes')
        self.assertNotIn('personal_data', hints)
        self.assertNotIn('dates', hints)

    def test_architect(self):
        low = CAFE.casefold()
        self.assertFalse(v.has_any(low, v.SCHEDULE_WORDS))   # "פתוח כל יום" is opening hours
        self.assertFalse(v.has_any(low, v.UPLOAD_WORDS))     # "העלאת מחירים" is a price rise
        self.assertFalse(_requires_outbound_delivery(CAFE))  # deliveries + an e-mail address send nothing

    def test_acceptance(self):
        self.assertFalse(wsa._has_any(CAFE, wsa._DELETE_WORDS))
        self.assertFalse(wsa._has_any(CAFE, wsa._UPDATE_WORDS))


class NewWordsAreKnown(unittest.TestCase):
    def test_booking_app(self):
        got = proposals('מערכת לקביעת תורים לקוסמטיקאית. הלקוחות ישאירו טלפון ושם מלא, בלי להירשם. '
                        'אווירה חמימה ומזמינה. אפשר לדחות או לבטל תור.')
        self.assertEqual(got['login'], 'none')
        self.assertEqual(got['personal_data'], 'yes')
        self.assertEqual(got['style'], 'warm')
        self.assertEqual(got['dates'], 'future_year')
        self.assertEqual(got['audience'], 'public')

    def test_styles_and_roles(self):
        self.assertEqual(proposals('אתר יוקרתי ומכובד')['style'], 'formal')
        self.assertEqual(proposals('משהו כיפי ועליז לילדים')['style'], 'playful')
        self.assertEqual(proposals('עיצוב סקנדינבי פשוט ונקי')['style'], 'clean')
        self.assertEqual(proposals('כלי לאנשי הצוות עם אזור אישי')['login'], 'simple')

    def test_architect_infrastructure_words(self):
        self.assertTrue(v.has_any('הלקוחות יעלו תמונות של העבודות', v.UPLOAD_WORDS))
        self.assertTrue(v.has_any('לשלוח תזכורת יום לפני התור', v.SCHEDULE_WORDS))
        self.assertTrue(v.has_any('דוח שבועי למנהל', v.SCHEDULE_WORDS))
        self.assertTrue(_requires_outbound_delivery('לשלוח אישור במייל לכל לקוח'))
        self.assertTrue(no_login_requested('אין צורך בחשבון'))
        self.assertTrue(no_login_requested('בלי להתחבר'))

    def test_acceptance_words(self):
        self.assertTrue(wsa._has_any('המנהל יכול לעדכן את הסטטוס', wsa._UPDATE_WORDS))
        self.assertTrue(wsa._has_any('mark tasks as done', wsa._UPDATE_WORDS))
        self.assertTrue(wsa._has_any('הלקוח יכול להסיר את עצמו מהרשימה', wsa._DELETE_WORDS))


if __name__ == '__main__':
    unittest.main()
