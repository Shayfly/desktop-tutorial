"""What the customer wrote reaches the build (production 2026-11-17, "148 דלתות", build bld_a875456f).

The owner pasted a full brief for a doors company's site. Its line "טון: ישיר, מקצועי" (a DIRECT tone) contains the
letters of "שיר" (a song): the router classified the message as media and refused it -- "שיר, סרטון או מוזיקה עוד
לא ... ההודעה שלכם נשמרה בשיחה". The customer answered "אתר", and the brief started from that one word.

The text below is an excerpt of the production message (intake_messages, read only), lines as written."""
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.families import classify_family
from tests.test_conversation_os import MemoryBriefs

PASTED = '''הבריף — להעתקה
שם העסק: 148 דלתות בהנהלת: נסים אוחנה טלפון: 050-345-6723 אזור שירות: אשקלון, אשדוד, קרית גת, שדרות והסביבה מה זה: התקנת דלתות ממד פולימריות ודלתות פנים. המבצע: דלת ממד פולימרית ברמה הגבוהה ביותר, בלי לצמצם את פתח החדר, 1,390 ₪ כולל הובלה והרכבה, אחריות שנה על ההתקנה. טון: ישיר, מקצועי, בגובה העיניים. קהל: בעלי דירות באזור, זוגות צעירים, משפחות בשיפוץ

מבנה הדף:
הירו — "דלת ממד פולימרית. 1,390 ₪ כולל הובלה והרכבה." שני כפתורים: וואטסאפ ראשי, חיוג משני.
שאלות נפוצות — חמש, עם תשובות אמיתיות.
צור קשר — טלפון לחיץ, כפתור וואטסאפ גדול, שם, אזור. בלי טופס.

החלטות מפורשות: דף סטטי. בלי סל, בלי תשלום, בלי טופס הרשמה. בלי קרוסלה.'''


class AWordInsideAnotherWordIsNotARequest(unittest.TestCase):
    def test_the_pasted_brief_is_a_site_not_a_song(self):
        self.assertIn(classify_family(PASTED), ('website', 'web_app'))

    def test_direct_rich_and_tied_are_not_songs(self):
        for text in ('טון: ישיר, מקצועי', 'עשיר בתוכן', 'קשר ישיר עם הלקוח', 'שירות מהיר'):
            self.assertEqual(classify_family(text), 'web_app', text)

    def test_a_song_is_still_a_song(self):
        for text in ('שיר ליום הולדת', 'אני צריך שיר לחתונה', 'תכתוב לי שירים', 'השיר שלי', 'לשיר בקול', 'ושיר לסיום'):
            self.assertEqual(classify_family(text), 'media', text)

    def test_a_passing_video_in_a_text_that_describes_a_page_is_a_site(self):
        self.assertEqual(classify_family('בריף: עסק דלתות. מבנה הדף: הירו ושאלות נפוצות. סרטון קצר בסוף'), 'website')
        self.assertEqual(classify_family('סרטון תדמית לעסק'), 'media')          # asked for, and no site named
        self.assertEqual(classify_family('פודקאסט על כלכלה'), 'media')
        self.assertEqual(classify_family('משחק זיכרון לילדים באתר שלי'), 'game')  # the message opens with the game


class AMessageSaidToBeKeptIsPartOfTheRequest(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {})

    def say(self, msg):
        return self.sup.turn(project_id='p1', account_id='a1', message=msg, lang='he')

    def test_the_production_conversation_now_starts_the_brief_from_the_pasted_text(self):
        first = self.say(PASTED)
        self.assertIsNone(getattr(first, 'unsupported', None))                  # no refusal
        prompt = self.briefs.latest('p1').brief.prompt
        for said in ('148 דלתות', '1,390 ₪', 'אשקלון, אשדוד, קרית גת, שדרות', 'טון: ישיר', 'בלי קרוסלה'):
            self.assertIn(said, prompt, said)

    def test_after_a_real_refusal_the_next_message_does_not_replace_what_was_written(self):
        refused = self.say('סרטון תדמית לעסק שלי: 148 דלתות, אשקלון, דלת ממד ב-1,390 ₪, טלפון 050-345-6723')
        self.assertEqual(refused.unsupported, 'media')
        self.assertIsNone(self.briefs.latest('p1'))                             # a refusal saves no brief
        self.say('אתר')
        prompt = self.briefs.latest('p1').brief.prompt
        self.assertIn('אתר', prompt)
        for said in ('148 דלתות', '1,390 ₪', '050-345-6723'):
            self.assertIn(said, prompt, said)

    def test_a_first_message_is_the_request_as_written(self):
        self.say('אתר תדמית למספרה בשם תספורת טובה')
        self.assertEqual(self.briefs.latest('p1').brief.prompt, d.start('אתר תדמית למספרה בשם תספורת טובה').prompt)

    def test_what_is_carried_is_bounded(self):
        # the owner, 2026-11-26: 20 messages and 48,000 characters (5 and 12,000 before); a drop is also said to the
        # customer (tests/test_silent_cuts.py)
        n = self.sup.MAX_CARRIED_MESSAGES + 3
        for i in range(n):
            self.say(f'סרטון מספר {i} ' + 'א' * 3000)
        self.assertIsNone(self.briefs.latest('p1'))
        with self.assertLogs('omni_prod.conversation.supervisor', 'WARNING') as logs:
            self.say('אתר')
        prompt = self.briefs.latest('p1').brief.prompt
        self.assertLessEqual(len(prompt), self.sup.MAX_REQUEST_CHARS)
        self.assertNotIn('סרטון מספר 0 ', prompt)                                # the oldest are left out
        self.assertIn('REQUEST_CUT', logs.output[0])
        self.assertTrue(prompt.rstrip().endswith('אתר'))                         # the newest words are never cut
        self.assertIn(f'סרטון מספר {n - 1} ', prompt)


if __name__ == '__main__':
    unittest.main()
