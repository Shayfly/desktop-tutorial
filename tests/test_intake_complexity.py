"""Issue #12: deterministic contextual complexity classification. Corpus of
Hebrew (and mixed) turns with conversation context. Zero false negatives are
required for the sensitive cases (expected RISKY)."""
from __future__ import annotations

import unittest

from omni_prod.intake import complexity as C
from omni_prod.intake import lanes

A = lambda text, *actions: {'role': 'assistant', 'content': text,                       # noqa: E731
                            'interpretation': {'actions': [{'type': a} for a in actions]}}
U = lambda text: {'role': 'customer', 'content': text}                                 # noqa: E731

CTX = {
    'none': [],
    'greeted': [A('שלום! מה תרצו לבנות היום?')],
    'plain_q': [U('אני צריך אתר לחנות פרחים'), A('באיזו שפה האתר יהיה?')],
    'approval': [U('מערכת לניהול ציוד'), A('הכל מוכן. כדי להתחיל, אשרו את הסיכום והעלות בכפתור "אישור והתחלת בנייה".', 'show_plan')],
    'approve_action': [A('התוכנית מוכנה', 'approve_build')],
    'delete_q': [U('תנקה את הפרויקט'), A('למחוק את כל הגרסאות הקודמות של הפרויקט?')],
    'pay_q': [U('חנות אונליין'), A('האם תרצו סליקת אשראי באתר?')],
    'secret_q': [A('יש לכם מפתח API של שירות המיילים? אפשר להזין אותו בהגדרות.')],
    'privacy_q': [A('האם המערכת תשמור מידע אישי של לקוחות, כמו תעודת זהות?')],
    'modify_action': [A('להחיל את השינוי על הגרסה הפעילה?', 'confirm_modification')],
}

# (message, context, expected)
CASES = [
    # --- LOW: greetings without sensitive context -------------------------
    ('שלום', 'none', 'LOW'), ('היי', 'none', 'LOW'), ('בוקר טוב', 'none', 'LOW'), ('ערב טוב', 'greeted', 'LOW'),
    ('תודה', 'plain_q', 'LOW'), ('תודה רבה', 'none', 'LOW'), ('מה שלומך?', 'none', 'LOW'), ('אהלן', 'none', 'LOW'),
    ('שָׁלוֹם', 'none', 'LOW'), ('שלום!!', 'none', 'LOW'), ('hello', 'none', 'LOW'), ('thanks', 'greeted', 'LOW'),
    ('הי', 'none', 'LOW'), ('מה נשמע', 'none', 'LOW'), ('שבת שלום', 'none', 'LOW'),
    # --- greeting / ambiguity never LOW when sensitive context exists --------
    ('שלום', 'approval', 'RISKY'), ('תודה', 'delete_q', 'RISKY'), ('היי', 'pay_q', 'RISKY'),
    ('שלום 😊', 'none', 'MEDIUM'), ('...', 'none', 'MEDIUM'), ('?', 'none', 'MEDIUM'), ('🙂', 'plain_q', 'MEDIUM'),
    ('אמממ', 'plain_q', 'MEDIUM'), ('לא יודע', 'plain_q', 'MEDIUM'), ('אולי', 'none', 'MEDIUM'),
    # --- MEDIUM: ordinary requirements ---------------------------------------
    ('אני צריך אתר לחנות פרחים', 'none', 'MEDIUM'),
    ('מערכת לניהול השאלת ציוד לצוות שלי, בעברית', 'none', 'MEDIUM'),
    ('אפליקציה לרישום תורים למספרה', 'none', 'MEDIUM'),
    ('בלי התחברות', 'plain_q', 'MEDIUM'), ('בעברית', 'plain_q', 'MEDIUM'), ('אנגלית ועברית', 'plain_q', 'MEDIUM'),
    ('צבעים כחול ולבן', 'none', 'MEDIUM'), ('דף נחיתה לסדנת יוגה', 'none', 'MEDIUM'),
    ('רשימת משימות לצוות עם תאריכי יעד', 'none', 'MEDIUM'), ('בלוג אישי עם תמונות', 'none', 'MEDIUM'),
    ('טופס יצירת קשר בדף הבית', 'none', 'MEDIUM'), ('לוח שנה של אירועים בקהילה', 'none', 'MEDIUM'),
    ('אני רוצה שהעיצוב יהיה נקי ומודרני', 'none', 'MEDIUM'), ('מערכת לניהול מלאי למחסן קטן', 'none', 'MEDIUM'),
    ('כאשר משתמש נכנס הוא רואה רשימה', 'none', 'MEDIUM'),           # "כאשר" is not an approval
    ('תציג את המשימות לפי תאריך', 'plain_q', 'MEDIUM'), ('אתר תדמית לעסק', 'none', 'MEDIUM'),
    ('משחק טריוויה לילדים', 'none', 'MEDIUM'), ('ניהול רשימת קניות משותפת', 'none', 'MEDIUM'),
    ('a booking site for my studio', 'none', 'MEDIUM'), ('אתר לחנות פרחים, in English too', 'none', 'MEDIUM'),
    ('מערכת לניהול ספרייה בבית ספר', 'none', 'MEDIUM'), ('מערכת סקרים פנימית', 'none', 'MEDIUM'),
    ('אפליקצייה לניהול השאלת צייוד', 'none', 'MEDIUM'),               # typos
    ('עמוד אודות ועמוד צור קשר', 'plain_q', 'MEDIUM'),
    ('כן', 'plain_q', 'MEDIUM'), ('בסדר', 'plain_q', 'MEDIUM'), ('אוקיי', 'greeted', 'MEDIUM'), ('ok', 'none', 'MEDIUM'),
    # --- HIGH: complex architecture / contradictions ---------------------------
    ('מערכת עם אינטגרציה ל-CRM, סנכרון בזמן אמת ו-SSO לכל העובדים', 'none', 'HIGH'),
    ('פלטפורמה multi-tenant עם API פתוח ו-webhook ללקוחות', 'none', 'HIGH'),
    ('אפליקציה שעובדת אופליין עם סנכרון לשרת', 'none', 'HIGH'),
    ('סוכן AI שמתחבר ל-ERP של החברה', 'none', 'HIGH'),
    ('מערכת שתעמוד במיליון משתמשים עם streaming של וידאו חי', 'none', 'HIGH'),
    ('אינטגרציה עם Salesforce ועם SAP', 'none', 'HIGH'),
    ('ממשק API ומיקרו-שירותים לכל מודול', 'none', 'HIGH'),
    # --- RISKY: payments (negation does not lower risk) ------------------------
    ('אני צריך חנות עם תשלומים באשראי', 'none', 'RISKY'), ('בלי תשלומים', 'plain_q', 'RISKY'),
    ('רוצה סליקה דרך PayPal', 'none', 'RISKY'), ('הלקוחות ישלמו מראש', 'none', 'RISKY'),
    ('תוסיף חיוב חודשי למנוי', 'none', 'RISKY'), ('החזר כספי אם מבטלים', 'none', 'RISKY'),
    ('כמה זה יעלה לי? מה המחיר?', 'none', 'RISKY'), ('מה התקציב שאני צריך?', 'none', 'RISKY'),
    ('checkout with Stripe', 'none', 'RISKY'), ('הפקת חשבונית ללקוח', 'none', 'RISKY'),
    ('עלות של 50 ש"ח לחודש', 'none', 'RISKY'), ('מחיר 100 ₪', 'none', 'RISKY'),
    ('לחייב את הכרטיס של הלקוח', 'none', 'RISKY'), ('אני לא רוצה לשלם על זה', 'none', 'RISKY'),
    # --- RISKY: deletion / destructive ------------------------------------------
    ('תמחק את הפרויקט', 'none', 'RISKY'), ('למחוק את כל המשתמשים', 'none', 'RISKY'),
    ('תאפס את כל הנתונים', 'none', 'RISKY'), ('לדרוס את הגרסה הקיימת', 'none', 'RISKY'),
    ('delete all records', 'none', 'RISKY'), ('wipe the database', 'none', 'RISKY'),
    ('לשחזר לגרסה הקודמת', 'none', 'RISKY'), ('לבטל את הפרויקט לגמרי', 'none', 'RISKY'),
    ('וּמְחַק את הכל', 'none', 'RISKY'),                                  # niqqud + prefix
    # --- RISKY: secrets / credentials -------------------------------------------
    ('הסיסמה שלי היא 1234', 'none', 'RISKY'), ('הנה מפתח API שלי', 'none', 'RISKY'),
    ('תשמור את הטוקן בקוד', 'none', 'RISKY'), ('my password is hunter2', 'none', 'RISKY'),
    ('פרטי ההתחברות לשרת', 'none', 'RISKY'), ('this is the secret token', 'none', 'RISKY'),
    ('סיסמא לכל המשתמשים', 'none', 'RISKY'),
    # --- RISKY: privacy / permissions / security --------------------------------
    ('לשמור תעודת זהות של כל לקוח', 'none', 'RISKY'), ('מידע רפואי של מטופלים', 'none', 'RISKY'),
    ('הרשאות אדמין לכל העובדים', 'none', 'RISKY'), ('personal data of customers', 'none', 'RISKY'),
    ('בלי הצפנה', 'none', 'RISKY'), ('מנהל מערכת יוכל לראות הכל', 'none', 'RISKY'),
    ('פרטים אישיים של התלמידים', 'none', 'RISKY'), ('GDPR compliance', 'none', 'RISKY'),
    # --- RISKY: approvals --------------------------------------------------------
    ('מאשר את הבנייה', 'none', 'RISKY'), ('תתחיל לבנות', 'none', 'RISKY'), ('אני מאשרת', 'none', 'RISKY'),
    ('go ahead and deploy', 'none', 'RISKY'), ('תפרסם את האתר', 'plain_q', 'RISKY'), ('תפרסמו', 'none', 'RISKY'),
    ('לפרסם לאוויר', 'none', 'RISKY'), ('approve the plan', 'none', 'RISKY'),
    # --- RISKY: short replies after sensitive assistant turns -------------------
    ('כן', 'approval', 'RISKY'), ('כן', 'delete_q', 'RISKY'), ('כן', 'pay_q', 'RISKY'), ('כן', 'secret_q', 'RISKY'),
    ('כן', 'privacy_q', 'RISKY'), ('כן', 'approve_action', 'RISKY'), ('כן', 'modify_action', 'RISKY'),
    ('ok', 'approval', 'RISKY'), ('👍', 'delete_q', 'RISKY'), ('סבבה', 'pay_q', 'RISKY'), ('יאללה', 'approval', 'RISKY'),
    ('בטח', 'modify_action', 'RISKY'), ('את שניהם', 'delete_q', 'RISKY'), ('רק את האחרונה', 'delete_q', 'RISKY'),
    ('כןןן', 'approval', 'RISKY'), ('כֵּן', 'approval', 'RISKY'), ('yes please', 'pay_q', 'RISKY'),
    ('לא', 'delete_q', 'RISKY'), ('בסדר גמור', 'approve_action', 'RISKY'), ('✅', 'approval', 'RISKY'),
    ('מעולה, קדימה', 'approval', 'RISKY'), ('תעשה את זה', 'modify_action', 'RISKY'),
]


class ComplexityCorpusTests(unittest.TestCase):
    def test_corpus_size_and_hebrew_share(self):
        self.assertGreaterEqual(len(CASES), 100)
        hebrew = [c for c in CASES if any('א' <= ch <= 'ת' for ch in c[0])]
        self.assertGreaterEqual(len(hebrew), 100)

    def test_every_case(self):
        wrong = []
        for message, ctx, expected in CASES:
            got = C.classify(message, CTX[ctx]).level
            if got != expected:
                wrong.append((message, ctx, expected, got))
        self.assertEqual(wrong, [])

    def test_zero_false_negatives_on_sensitive_cases(self):
        sensitive = [(m, c) for m, c, e in CASES if e == C.RISKY]
        self.assertGreaterEqual(len(sensitive), 60)
        missed = [(m, c) for m, c in sensitive if C.classify(m, CTX[c]).level != C.RISKY]
        self.assertEqual(missed, [])

    def test_ambiguity_is_never_low(self):
        for message in ('', '   ', '😊', 'שלום 😊', 'כן', 'ok', 'hmm', 'שלום, אני צריך משהו', 'היי היי היי מה'):
            with self.subTest(message=message):
                self.assertNotEqual(C.classify(message, []).level, C.LOW)

    def test_contradiction_with_confirmed_requirement_is_high(self):
        c = C.classify('בעצם עם התחברות', [], confirmed={'login': 'none'}, proposed={'login': 'email'})
        self.assertEqual(c.level, C.HIGH)
        self.assertEqual(c.signals['contradictions'], ['login'])
        self.assertEqual(C.classify('עם התחברות', [], confirmed={'login': 'email'}, proposed={'login': 'email'}).level,
                         C.MEDIUM)

    def test_context_is_recent_turns_not_just_last_message(self):
        hist = [A('למחוק את הגרסה?'), U('רגע'), A('בסדר, מחכה לתשובה')]
        self.assertEqual(C.classify('שלום', hist).level, C.MEDIUM)      # sensitive context within recent turns


class LaneTests(unittest.TestCase):
    def test_lanes(self):
        self.assertEqual(lanes.choose(C.LOW)['lane'], lanes.DETERMINISTIC)
        lane = lanes.choose(C.MEDIUM)
        self.assertEqual((lane['lane'], lane['task'], lane['quality_floor']), (lanes.STANDARD, 'conversation', 70))
        # Master directive stage 1: complex/sensitive turns escalate to the strong model
        # first; the mandatory floor is unchanged (never below 70).
        for level in (C.HIGH, C.RISKY):
            lane = lanes.choose(level)
            self.assertEqual((lane['lane'], lane['task'], lane['quality_floor'], lane['preferred_floor']),
                             (lanes.ESCALATED, 'conversation_complex', 70, 85))
        self.assertTrue(lanes.choose(C.RISKY)['requires_explicit_confirmation'])
        self.assertFalse(lanes.choose(C.HIGH)['requires_explicit_confirmation'])
        self.assertTrue(lanes.choose(C.HIGH)['flag_for_review'])
        from omni_prod.intelligence.task_policy import TASK_CLASSES
        tc = TASK_CLASSES['conversation_complex']
        self.assertEqual((tc.preferred_floor, tc.mandatory_floor), (85, 70))

    def test_escalated_turn_is_quoted_reserved_and_executed_as_the_same_task(self):
        from omni_prod.intake.reservation_worker import _reserved_task
        self.assertEqual(_reserved_task({'task': 'conversation_complex'}, {'task': 'conversation_complex'}),
                         'conversation_complex')
        self.assertEqual(_reserved_task({}, {'task': 'conversation'}), 'conversation')        # pre-escalation rows
        for payload, quote in (({'task': 'conversation_complex'}, {'task': 'conversation'}),  # pricier than quoted
                               ({'task': 'codegen'}, {'task': 'codegen'})):                    # not an intake task
            with self.assertRaises(ValueError):
                _reserved_task(payload, quote)

    def test_low_risk_lane_is_disabled_without_qualification(self):
        ok, why = lanes.low_risk_lane_qualified()
        self.assertFalse(ok)
        self.assertIn('benchmark', why)
        for level in (C.LOW, C.MEDIUM, C.HIGH, C.RISKY):
            self.assertNotEqual(lanes.choose(level)['lane'], lanes.LOW_RISK)

    def test_sensitive_never_enters_low_risk_lane_even_if_qualified(self):
        q = {'hebrew_benchmark': {'cases': 200, 'accuracy': 0.99, 'sensitive_false_negatives': 0},
             'pricing_verified': True, 'tool_permissions': 'none'}
        self.assertEqual(lanes.choose(C.LOW, qualification=q)['lane'], lanes.LOW_RISK)
        for level in (C.MEDIUM, C.HIGH, C.RISKY):
            self.assertNotEqual(lanes.choose(level, qualification=q)['lane'], lanes.LOW_RISK)
        bad = {**q, 'tool_permissions': 'write'}
        self.assertEqual(lanes.choose(C.LOW, qualification=bad)['lane'], lanes.DETERMINISTIC)

    def test_global_conversation_floor_stays_70(self):
        from omni_prod.intelligence.task_policy import TASK_CLASSES
        self.assertEqual(TASK_CLASSES['conversation'].mandatory_floor, 70)


if __name__ == '__main__':
    unittest.main()
