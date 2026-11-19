"""A long request is a request, even when a line of it reads like a question (production 2026-11-19).

The owner's law-firm brief (project prj_4tizfrqJkgO-Eg, intake_messages 19:14:36): its FAQ line "כמה עולה ייעוץ
ראשון (250 ₪)" made the whole message a cost question -- interpretation {"intent": "cost"}, no model call, and the
reply "לא זיהיתי פרטים חדשים". The message below is that message as the customer sent it.
"""
import os
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.conversation.supervisor import _TXT, classify_intent

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted      # noqa: E402

BRIEF = '''אני רוצה אתר תדמית מקצועי למשרד עורכי דין "כהן ושות׳ – דיני עבודה" בתל אביב.
כתובת: דרך מנחם בגין 132, תל אביב. טלפון: 03-5551234. מייל: office@cohen-law.co.il
שעות: א׳–ה׳ 09:00–18:00.

מבנה הדף:
1. פתיח: "מייצגים עובדים ומעסיקים בדיני עבודה מאז 2008", עם כפתור "לתיאום פגישת ייעוץ".
2. תחומי התמחות: פיטורים שלא כדין, הטרדה במקום העבודה, זכויות סוציאליות, ייצוג מעסיקים.
3. על המשרד: 3 עורכי דין, יותר מ-1,500 תיקים.
4. איך זה עובד: שיחת ייעוץ, בדיקת מסמכים, ליווי עד סיום ההליך.
5. שאלות נפוצות: כמה עולה ייעוץ ראשון (250 ₪), כמה זמן לוקח הליך, האם צריך להגיע למשרד.
6. צור קשר: טופס עם שם, טלפון ונושא, וכפתור וואטסאפ.

עיצוב: נקי ורציני, כחול כהה ולבן, בלי תמונות מלאי של פטישים. נראה טוב בטלפון.
בלי המלצות לקוחות, כי אין לי עדיין.'''


class TheBriefIsARequest(unittest.TestCase):
    def test_the_production_brief_is_requirements(self):
        for has_brief in (False, True):
            self.assertEqual(classify_intent(BRIEF, has_version=False, has_brief=has_brief), 'requirements')

    def test_a_long_change_request_after_a_version_is_a_modification(self):
        change = 'תוסיף ' + BRIEF
        self.assertEqual(classify_intent(change, has_version=True, has_brief=True), 'modify')

    def test_short_questions_are_still_questions(self):
        for text, intent in (('כמה זה יעלה?', 'cost'), ('מה חסר?', 'missing'), ('מה המצב?', 'status'),
                             ('מה אתה ממליץ?', 'recommend'), ('האם אפשר להוסיף תשלומים?', 'feasibility')):
            self.assertEqual(classify_intent(text, has_version=False, has_brief=True), intent, text)

    def test_through_the_real_supervisor_the_model_reads_the_brief(self):
        class Counting(Scripted):
            calls = 0

            def interpret(self, message, brief=None):
                Counting.calls += 1
                return super().interpret(message, brief)
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_INTAKE_MODEL': '1'}):
            sup = R._Supervisor(Counting())
            t = sup.turn(project_id='law', account_id='a', message=BRIEF, lang='he')
        self.assertEqual(Counting.calls, 1)
        self.assertNotEqual(t.interpretation.get('intent'), 'cost')
        self.assertNotIn(_TXT['he']['nothing'], t.reply)


if __name__ == '__main__':
    unittest.main()
