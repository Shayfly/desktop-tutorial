"""A business name the customer stated is read once and never asked again; a question and the summary never share one
message; and the rehearsal's checker catches both (2026-11-25).

Evidence: the live conversation rehearsals 45702506669 (gemini-3-5-flash-lite) and 45702519795 (claude-haiku-5-5) on the
production worker (ac10e94, path=agent) both reported passed=True and facts_missing=[] while
  * doors -- the first message begins "שם העסק: 148 דלתות" -- was asked "איך קוראים לעסק? כתבו את השם בדיוק ..." twice
    with one model and three times with the other;
  * butcher -- 'אתר לאטליז "בשר השכונה"' -- was asked "מה שם האטליז כפי שתרצו שיופיע באתר?", and the summary had no name;
  * bare -- 'למספרה שלי, "תספורת טובה"' -- was asked "מה השם של המספרה";
  * a question and the summary ("שלב 1 מתוך 2 ...") came in one message.
The recorded transcripts are tests/rehearsal_transcripts_20261125.py.

Root causes (found on this path, see the final report): fact_canon._NAME did not end a name at the next label of a
one-line form ("... בהנהלת: ..."), so the doors name was never read and the supervisor's own NAME_QUESTION was asked up to
its limit; a quoted name was only a yes/no gate, never recorded nor told to the model, whose context had no name in
`confirmed` and the domain checklist's first item "Name -- ask"; and when the approval opened, the model's whole reply
(its question included) was put in front of the summary.

The real path: conversation_rehearsal.run_scenario -- the production ConversationSupervisor -- with the real
ModelInterpreter and its context, and a model double that never contacts a provider. FollowsThePrompt follows SYSTEM's
reply rules literally (context.ask_next, else the first expert_checklist topic not in context.confirmed, else it offers
the summary). AsksTheName asks the name every turn whatever its context says (a model that ignores it).
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod import discovery as d
from omni_prod import fact_canon as F
from omni_prod.intake import conversation_agent as agent
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.site_content import facts as Fx

sys.path.insert(0, os.path.dirname(__file__))
import rehearsal_transcripts_20261125 as REC  # noqa: E402

NAMES = {'doors': '148 דלתות', 'butcher': 'בשר השכונה', 'bare': 'תספורת טובה'}


class _Double:
    accepts_call_id = True          # a double that never contacts a provider: an empty attempt ledger

    def __init__(self):
        self.recorder = type('R', (), {'records': []})()
        self.contexts = []

    def complete_json(self, *, system, user, max_tokens, task, call_id):
        head = user.split('\nCurrent customer message:\n', 1)[0]
        ctx = json.loads(head.split('\n', 1)[1])
        self.contexts.append(ctx)
        return {'language': 'he', 'product_family': 'website', 'proposals': [], 'delegate_rest': False,
                'requirements': [], 'reply': self.reply(ctx), 'semantic_decisions': []}


class FollowsThePrompt(_Double):
    def reply(self, ctx):
        if ctx.get('ask_next'):
            return 'הבנתי. ' + ctx['ask_next']['meaning']
        confirmed = ctx.get('confirmed') or {}
        for item in ctx.get('expert_checklist') or ():
            if 'name' in item.split(' -- ask:', 1)[0].lower() and 'business_name' not in confirmed:
                return 'הבנתי. לפני שנמשיך, מה שם העסק כפי שתרצו שיופיע באתר?'
        return 'הבנתי את כל מה שצריך. האם תרצו שנכין את הסיכום לאישורכם?'


class AsksTheName(_Double):
    def reply(self, ctx):
        return 'מצוין, אז האתר יציג את המידע והמחירים בלבד. לפני שנמשיך, מה שם העסק כפי שתרצו שיופיע באתר?'


def summary_of(result) -> str:
    return next(t['agent'] for t in result['transcript'] if 'שלב 1 מתוך 2' in t['agent'])


class TheNameIsRead(unittest.TestCase):
    def test_the_three_requests_state_their_name(self):
        self.assertEqual(agent.stated_names(R.SCENARIOS['doors']['lines'][0]), ['148 דלתות'])
        self.assertEqual(agent.stated_names(R.SCENARIOS['butcher']['lines'][0]), ['בשר השכונה'])
        self.assertEqual(agent.stated_names('אתר\n' + R.SCENARIOS['bare']['lines'][1]), ['תספורת טובה'])
        self.assertEqual(agent.stated_names('אתר תדמית למורה פרטית למתמטיקה "נועה ברק". טלפון 054-7712345.'), ['נועה ברק'])
        self.assertEqual(agent.stated_names('אנחנו מסעדה, קוראים לנו "זית ולימון".'), ['זית ולימון'])

    def test_the_label_ends_at_the_next_label(self):
        # the canon reads the doors name now (it read none: the first point where the name was lost)
        self.assertEqual(sorted(F.build_canon(R.SCENARIOS['doors']['lines'][0]).values('name')), ['148 דלתות'])
        self.assertEqual(sorted(F.build_canon('שם העסק: קפה גינה אזור שירות: חיפה').values('name')), ['קפה גינה'])
        # an unknown word before a colon never cuts a name: no name is read, and the agent asks
        self.assertEqual(sorted(F.build_canon('שם העסק: Studio 54: the best').values('name')), [])

    def test_a_quote_that_is_not_a_name_is_not_one(self):
        for text in ('אתר עם כפתור "הזמינו עכשיו"', 'הירו — "דלת ממד פולימרית במבצע"', 'אתר תדמית למורה פרטית, נועה ברק'):
            with self.subTest(text):
                self.assertEqual(agent.stated_names(text), [])
                self.assertFalse(agent.declares_a_name(text))

    def test_two_names_are_asked_as_a_choice_quoting_both(self):
        text = 'אתר לאטליז "בשר השכונה", וקוראים לנו "הקצב של חיפה". טלפון 04-8123456.'
        self.assertEqual(agent.stated_names(text), ['בשר השכונה', 'הקצב של חיפה'])
        self.assertFalse(agent.declares_a_name(text))
        q = agent.name_question(text, 'he')
        self.assertIn('"בשר השכונה"', q)
        self.assertIn('"הקצב של חיפה"', q)

    def test_the_answer_to_which_one_is_the_name_it_names(self):
        known = 'אתר לאטליז "בשר השכונה", וקוראים לנו "הקצב של חיפה".'
        self.assertEqual(agent.name_to_record(known, 'את "בשר השכונה" בבקשה', answering=True), 'שם העסק: בשר השכונה.')
        self.assertIsNone(agent.name_to_record(known, 'הראשון', answering=True))        # a pointer is not a name
        self.assertEqual(agent.name_to_record(known, 'קצב הכרמל', answering=True), 'שם העסק: קצב הכרמל.')
        # recorded once: a quoted name becomes the declared line, and a declared name adds nothing more
        self.assertEqual(agent.name_to_record('אתר לאטליז "בשר השכונה".', '', answering=False), 'שם העסק: בשר השכונה.')
        self.assertIsNone(agent.name_to_record('אתר לאטליז "בשר השכונה".\nשם העסק: בשר השכונה.', 'כן', answering=False))

    def test_the_model_sentence_that_asks_the_name_becomes_one_that_says_it(self):
        for asked in ('לפני שנמשיך, מה שם האטליז כפי שתרצו שיופיע באתר?',
                      'נשאר רק לדעת מה תרצו לקרוא לאטליז באתר בדיוק, כי בלי שם קשה להזכר בו.',
                      'כדי שהדף ידבר נכון על העסק, ספרו לי: איך קוראים לעסק, בדיוק כמו שהוא צריך להופיע באתר?',
                      'כדי שהאתר יהיה מלא, מה השם שתרצו שיופיע בראש העמוד למספרה?'):
            with self.subTest(asked):
                out = agent.without_name_question('מצוין, אז האתר יציג את המידע בלבד. ' + asked, 'בשר השכונה', 'he')
                self.assertEqual(out, 'מצוין, אז האתר יציג את המידע בלבד. השם שיופיע באתר: "בשר השכונה".')
        for kept in ('האם יישמרו פרטים אישיים של אנשים (שם, טלפון, מייל)?', 'מה שם המנה הכי פופולרית שלכם?',
                     'האם להציג את שם העסק בגדול בראש העמוד?',
                     'מעולה, רשמתי את הפרטים של אטליז "בשר השכונה" בחיפה.'):
            with self.subTest(kept):
                self.assertEqual(agent.without_name_question(kept, 'בשר השכונה', 'he'), kept)


class OnTheRealPath(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'})
        p.start()
        self.addCleanup(p.stop)

    def run_all(self, double):
        out = {}
        for name in R.SCENARIOS:
            gw = double()
            out[name] = (R.run_scenario(name, ModelInterpreter(gw)), gw)
        return out

    def test_a_stated_name_is_never_asked_and_the_summary_shows_it(self):
        for name, (r, _) in self.run_all(FollowsThePrompt).items():
            with self.subTest(name):
                self.assertTrue(r['approval'], [t['agent'][:80] for t in r['transcript']])
                self.assertFalse(any(agent.NAME_ID in t['asked'] for t in r['transcript']), r['transcript'])
                self.assertEqual(r['asked_again'], [])
                self.assertIn(f'שם: {NAMES[name]}', summary_of(r))
                self.assertTrue(r['passed'], r)

    def test_a_model_that_asks_the_name_anyway_is_not_heard(self):
        for name, (r, _) in self.run_all(AsksTheName).items():
            with self.subTest(name):
                self.assertEqual(r['asked_again'], [], r['transcript'])
                said = ' '.join(t['agent'] for t in r['transcript'][1:])
                self.assertNotIn('מה שם העסק', said)
                self.assertIn(f'השם שיופיע באתר: "{NAMES[name]}"', said)

    def test_the_model_is_told_the_name_and_not_to_ask_it(self):
        for name, (_, gw) in self.run_all(FollowsThePrompt).items():
            with self.subTest(name):
                told = [c for c in gw.contexts if 'confirmed' in c]
                self.assertTrue(told)
                last = told[-1]
                self.assertEqual(last['confirmed'].get('business_name'), NAMES[name])
                self.assertFalse([x for x in last['expert_checklist'] if 'name -- ask' in x.lower()], last)

    def test_the_summary_never_shares_a_message_with_a_question(self):
        for name, (r, _) in self.run_all(FollowsThePrompt).items():
            with self.subTest(name):
                summary = summary_of(r)
                before = summary.split('שלב 1 מתוך 2', 1)[0]
                self.assertNotIn('?', before)
                self.assertEqual(r['question_with_summary'], [])

    def test_a_quoted_name_becomes_the_declared_name_the_build_reads(self):
        r, _ = self.run_all(FollowsThePrompt)['butcher']
        self.assertTrue(r['approval'])
        sup_brief = R._Supervisor(ModelInterpreter(FollowsThePrompt()))   # a fresh conversation: the build's brief
        sup_brief.turn(project_id='p', account_id='a', message=R.SCENARIOS['butcher']['lines'][0], lang='he')
        brief = sup_brief.briefs.latest('p').brief
        self.assertEqual(brief.prompt.count('שם העסק: בשר השכונה.'), 1)
        sheet = Fx.fact_sheet(brief.prompt + '\n' + d.requirements_text(brief))
        self.assertEqual(sheet.name, 'בשר השכונה')

    def test_two_names_are_asked_once_as_a_choice_and_the_answer_settles_it(self):
        sup = R._Supervisor(ModelInterpreter(FollowsThePrompt()))
        say = lambda m: sup.turn(project_id='two', account_id='a', message=m, lang='he')   # noqa: E731
        t = say('אתר לאטליז "בשר השכונה", וקוראים לנו "הקצב של חיפה". טלפון 04-8123456. אתר תוכן בלבד, לא שומרים כלום.')
        replies, asked_which = [], 0
        for _ in range(10):
            replies.append(t.reply)
            asked = list(getattr(t, 'asked_in_words', None) or [])
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            if agent.NAME_ID in asked:
                asked_which += 1
                self.assertIn('"בשר השכונה"', t.reply)
                self.assertIn('"הקצב של חיפה"', t.reply)
                t = say('בשר השכונה')
            else:
                t = say(R.TYPED.get(asked[0], 'תחליטו אתם על השאר') if asked else 'תחליטו אתם על השאר')
        self.assertEqual(asked_which, 1, replies)
        self.assertTrue(any(a['type'] == 'approve_spec' for a in t.actions), replies)
        self.assertIn('שם: בשר השכונה', t.reply)
        self.assertEqual(agent.stated_names(d.customer_text(sup.briefs.latest('two').brief)), ['בשר השכונה'])


class APagePartIsNotTheName(unittest.TestCase):
    """S4 (release review of 550320c): _AFTER let two words stand between the kind of business and a quote, so
    'דף נחיתה למסעדה עם כפתור "הזמינו עכשיו"' was recorded as "שם העסק: הזמינו עכשיו" on every website turn; a correction
    'השם שלנו הוא "השף הקטן"' was ignored (a label wins over a quote), and the two-names question then looped."""
    BUTTON = 'דף נחיתה למסעדה עם כפתור "הזמינו עכשיו". אתר תוכן בלבד, לא שומרים כלום. טלפון 03-5551234'

    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'})
        p.start()
        self.addCleanup(p.stop)

    def test_a_quote_after_a_page_word_is_not_a_name(self):
        for text in ('דף נחיתה למסעדה עם כפתור "הזמינו עכשיו"', 'אתר למספרה עם הסלוגן "תספורת שמחה"',
                     'אתר לאטליז עם כותרת "בשר טרי כל יום"', 'אתר למאפייה עם גלריה "המאפים שלנו"',
                     'a site for my bakery with a button "Order now"', 'a landing page for a cafe, headline "Fresh daily"'):
            with self.subTest(text):
                self.assertEqual(agent.stated_names(text), [])
                self.assertIsNone(agent.name_to_record('', text, answering=False))
        # a name right after the kind of business is still read
        self.assertEqual(agent.stated_names('אתר לאטליז "בשר השכונה" עם כפתור "הזמינו עכשיו"'), ['בשר השכונה'])

    def test_a_stated_name_replaces_the_one_read_earlier_and_adds_no_second(self):
        known = 'אתר למסעדה "פיצה טובה".\nשם העסק: פיצה טובה.'
        for said, name in (('השם שלנו הוא "השף הקטן"', 'השף הקטן'), ('קוראים לעסק השף הקטן', 'השף הקטן'),
                           ('the name is "Little Chef"', 'Little Chef')):
            with self.subTest(said):
                line = agent.name_to_record(known, said, answering=False)
                self.assertEqual(line, f'שם העסק: {name}.')
                prompt = agent.with_name_line(known, line)
                self.assertEqual(prompt.count('שם העסק:'), 1, prompt)
                self.assertEqual(agent.stated_names(prompt), [name])
        self.assertIsNone(agent.name_to_record('שם העסק: השף הקטן.', 'השם שלנו הוא "השף הקטן"', answering=False))
        self.assertIsNone(agent.explicit_name('השם שלנו הוא 0501234567'))

    def test_on_the_real_path_the_button_is_never_the_name_and_the_stated_name_is(self):
        sup = R._Supervisor(ModelInterpreter(FollowsThePrompt()))
        say = lambda m: sup.turn(project_id='btn', account_id='a', message=m, lang='he')   # noqa: E731
        t, replies, name_asks = say(self.BUTTON), [], 0
        self.assertNotIn('שם העסק: הזמינו עכשיו', sup.briefs.latest('btn').brief.prompt)
        for _ in range(10):
            replies.append(t.reply)
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            asked = list(getattr(t, 'asked_in_words', None) or [])
            if agent.NAME_ID in asked:
                name_asks += 1
                t = say('השם שלנו הוא "השף הקטן"')
            else:
                t = say(R.TYPED.get(asked[0], 'תחליטו אתם על השאר') if asked else 'תחליטו אתם על השאר')
        self.assertEqual(name_asks, 1, replies)
        self.assertTrue(any(a['type'] == 'approve_spec' for a in t.actions), replies)
        self.assertIn('שם: השף הקטן', t.reply)
        self.assertNotIn('הזמינו עכשיו"', t.reply.split('פרטי העסק', 1)[-1])
        prompt = sup.briefs.latest('btn').brief.prompt
        self.assertEqual(prompt.count('שם העסק:'), 1, prompt)

    def test_on_the_real_path_a_correction_replaces_the_name_read_earlier(self):
        sup = R._Supervisor(ModelInterpreter(FollowsThePrompt()))
        say = lambda m: sup.turn(project_id='fix', account_id='a', message=m, lang='he')   # noqa: E731
        say('אתר למסעדה "פיצה טובה". אתר תוכן בלבד, לא שומרים כלום. טלפון 03-5551234')
        self.assertEqual(sup.briefs.latest('fix').brief.prompt.count('שם העסק: פיצה טובה.'), 1)
        say('השם שלנו הוא "השף הקטן"')
        brief = sup.briefs.latest('fix').brief
        self.assertEqual(brief.prompt.count('שם העסק:'), 1, brief.prompt)
        self.assertEqual(agent.stated_names(d.customer_text(brief)), ['השף הקטן'])


class AStatementGivesANameOnlyWhenItReadsAsOne(unittest.TestCase):
    """Review of 49d61d3, SF2 and SF3 ($SP/rv-probe/p_s4.py, p_s4b.py): an unquoted statement replaced the right name
    with a sentence ('השם שלנו הוא שם דבר בעיר, כולם מכירים אותנו' -> "שם דבר בעיר", 'the name is not important' ->
    "not important"); two quoted names in one statement recorded the first; a one-letter quote came out malformed."""
    KNOWN = 'אתר למסעדה "השף הקטן". שם העסק: השף הקטן.'
    FIRST = 'דף נחיתה למסעדה שלי "השף הקטן" עם כפתור "הזמינו עכשיו". אתר תוכן בלבד, לא שומרים כלום. טלפון 03-5551234'

    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'})
        p.start()
        self.addCleanup(p.stop)

    def test_the_statements_of_the_review(self):
        cases = {'השם שלנו הוא שם דבר בעיר': ('unclear', None),
                 'השם שלנו הוא שם דבר בעיר, כולם מכירים אותנו': ('unclear', None),
                 'השם שלנו הוא הכי מוכר באזור': ('unclear', None), 'השם שלנו הוא מה שמוכר אותנו': ('unclear', None),
                 'the name is not important': ('unclear', None), 'it is called a soft launch': ('unclear', None),
                 'השם שלנו הוא "א" אבל באתר תכתבו "ב"': ('choice', ['א', 'ב']),
                 'השם שלנו הוא "אב" אבל באתר תכתבו "גד"': ('choice', ['אב', 'גד']),
                 'השם שלנו הוא "א"': ('unclear', None),
                 'השם שלנו הוא "השף הקטן" והסלוגן "טעים"': ('name', 'השף הקטן'),
                 'השם שלנו הוא "השף הקטן"': ('name', 'השף הקטן'), 'קוראים לעסק השף הקטן': ('name', 'השף הקטן'),
                 'the name is "Little Chef"': ('name', 'Little Chef'), 'שלום': None}
        for message, said in cases.items():
            with self.subTest(message):
                self.assertEqual(agent.name_statement(message), said)
                if said and said[0] != 'name':
                    self.assertIsNone(agent.name_to_record(self.KNOWN, message, answering=False))

    def test_on_the_real_path_a_sentence_keeps_the_name_and_says_it(self):
        sup = R._Supervisor(ModelInterpreter(FollowsThePrompt()))
        say = lambda m: sup.turn(project_id='p', account_id='a', message=m, lang='he')   # noqa: E731
        say(self.FIRST)
        t = say('השם שלנו הוא שם דבר בעיר, כולם מכירים אותנו')
        prompt = sup.briefs.latest('p').brief.prompt
        self.assertEqual([x for x in prompt.splitlines() if x.startswith('שם העסק:')], ['שם העסק: השף הקטן.'])
        self.assertIn('השם שיופיע באתר: "השף הקטן".', t.reply)

    def test_on_the_real_path_two_names_are_asked_which_and_the_answer_settles_it(self):
        sup = R._Supervisor(ModelInterpreter(FollowsThePrompt()))
        say = lambda m: sup.turn(project_id='p', account_id='a', message=m, lang='he')   # noqa: E731
        say(self.FIRST)
        t = say('השם שלנו הוא "אב" אבל באתר תכתבו "גד"')
        self.assertIn('כתבתם שני שמות: "אב" ו"גד". איזה מהם יופיע באתר?', t.reply)
        self.assertEqual(t.asked_in_words, [agent.NAME_ID])
        self.assertIn('שם העסק: השף הקטן.', sup.briefs.latest('p').brief.prompt)      # nothing recorded yet
        say('גד')
        prompt = sup.briefs.latest('p').brief.prompt
        self.assertEqual([x for x in prompt.splitlines() if x.startswith('שם העסק:')], ['שם העסק: גד.'])

    def test_a_name_never_holds_a_colon(self):
        self.assertIsNone(agent.name_line('Studio: Noa'))
        self.assertEqual(agent.name_statement('the name is "Studio: Noa"'), ('unclear', None))
        with self.assertRaises(ValueError):
            agent.with_name_line('x', 'שם העסק: Studio: 54.')
        self.assertEqual(agent.with_name_line('x\nשם העסק: א ב.', 'שם העסק: ג ד.'), 'x\nשם העסק: ג ד.')


class InArabic(unittest.TestCase):
    """F3: the name strings of this change are kept in Hebrew, Arabic and English, like the gap detector's questions
    (intake.gaps QUESTIONS) and the gate words (gate_words.LANGS); an Arabic conversation reads them in Arabic."""

    def test_every_name_string_has_the_three_languages(self):
        for strings in (agent.NAME_QUESTION, agent.NAME_WHICH_QUESTION, agent.NAME_SAID):
            self.assertEqual(set(strings), {'he', 'ar', 'en'})
            self.assertRegex(strings['ar'], r'[\u0600-\u06FF]')

    def test_they_are_said_in_arabic(self):
        two = 'אתר לאטליז "בשר השכונה", וקוראים לנו "הקצב של חיפה".'
        self.assertEqual(agent.name_question(two, 'ar'),
                         'كتبتم اسمين: "בשר השכונה" و"הקצב של חיפה". أيهما سيظهر في الموقع؟ اكتبوه تمامًا كما يجب أن يظهر.')
        self.assertEqual(agent.name_question('אתר', 'ar'), agent.NAME_QUESTION['ar'])
        said = agent.without_name_question('מה שם העסק כפי שתרצו שיופיע באתר?', 'بيت الشاي', 'ar')
        self.assertEqual(said, 'الاسم الذي سيظهر في الموقع: "بيت الشاي".')
        self.assertEqual(agent.name_question('אתר', 'fr'), agent.NAME_QUESTION['en'])     # any other: English


class TheChecker(unittest.TestCase):
    """The rehearsal's checks on the recorded transcripts: each recorded run fails, for the turns the logs show."""
    EXPECTED = {   # (model, scenario): (asked again [(turn, fact)], questions with the summary [turn])
        ('flash-lite', 'doors'): ([(3, 'name'), (6, 'name')], []),
        ('flash-lite', 'butcher'): ([], [4]),
        ('flash-lite', 'bare'): ([(5, 'name')], [5]),
        ('haiku', 'doors'): ([(4, 'name'), (5, 'name'), (6, 'name')], [6]),
        ('haiku', 'butcher'): ([(3, 'name'), (4, 'name')], [4]),
        ('haiku', 'bare'): ([(3, 'name'), (5, 'name')], [5]),
    }

    def test_the_recorded_runs_fail(self):
        for (model, name), (again, mixed) in self.EXPECTED.items():
            with self.subTest(model=model, scenario=name):
                tr = REC.transcript((REC.FLASH_LITE if model == 'flash-lite' else REC.HAIKU)[name])
                found = R.asked_again(tr, R.GIVEN[name])
                self.assertEqual([(a['turn'], a['fact']) for a in found], again)
                self.assertEqual([q['turn'] for q in R.question_with_summary(tr)], mixed)
                self.assertFalse(R.accepted(cards=0, reached=True, missing=[], models={'model+deterministic'},
                                            asked_again=found, with_summary=R.question_with_summary(tr)))

    def test_each_new_condition_fails_on_its_own(self):
        ok = dict(cards=0, reached=True, missing=[], models={'model:x'})
        self.assertTrue(R.accepted(**ok, asked_again=[], with_summary=[]))
        self.assertFalse(R.accepted(**ok, asked_again=[{'turn': 3, 'fact': 'name', 'sentence': 'איך קוראים לעסק?'}]))
        self.assertFalse(R.accepted(**ok, with_summary=[{'turn': 4, 'sentence': 'האם תרצו?'}]))

    def test_saying_or_confirming_a_given_fact_is_not_asking_it(self):
        given = R.GIVEN['butcher']
        for reply in ('השם שיופיע באתר: "בשר השכונה".', 'האם השם "בשר השכונה" נכון?',
                      'האם יישמרו פרטים אישיים של אנשים (שם, טלפון, מייל)?',
                      'מעולה, רשמתי את הפרטים של אטליז "בשר השכונה" בחיפה, כולל הכתובת, הטלפון ושעות הפעילות.',
                      'מה מספר הוואטסאפ שתרצו שיופיע באתר?',
                      # about the page, not the fact asked again
                      'האם להציג את הטלפון בראש העמוד?', 'האם להציג את הכתובת עם מפה?',
                      'האם להציג את שעות הפעילות בתחתית?', 'האם להציג את שם העסק בגדול?'):
            with self.subTest(reply):
                self.assertEqual(R.asked_again([{'customer': REC.BUTCHER, 'agent': reply}], given), [])

    def test_a_fact_asked_before_it_was_given_is_not_asked_again(self):
        tr = REC.transcript(REC.HAIKU['bare'][:2])    # turn 1 asks what the business is called, before the name exists
        self.assertEqual(R.asked_again(tr, R.GIVEN['bare']), [])

    def test_the_other_facts_asked_again_are_caught(self):
        for fact, reply in (('phone', 'לפני שנמשיך, מה מספר הטלפון של האטליז?'), ('address', 'מהי הכתובת המלאה שלכם?'),
                            ('hours', 'באילו ימים ושעות אתם פתוחים?')):
            with self.subTest(fact):
                found = R.asked_again([{'customer': REC.BUTCHER, 'agent': reply}], R.GIVEN['butcher'])
                self.assertEqual([a['fact'] for a in found], [fact])

    def test_the_summarys_own_lines_are_not_read_as_asking_again(self):
        # the gate's own needed-fact line asks "מה מספר הטלפון?" after the mark: part of the one approval
        needed = F._NEEDED_TEXT['he']['needed'].format(what='כפתור חיוג או וואטסאפ', fact='מספר הטלפון',
                                                      omit='הכפתור והמספר לא יופיעו')
        reply = 'שלב 1 מתוך 2 — זה מה שהבנתי שאתם רוצים: מטרה: אתר לאטליז. ' + needed
        self.assertEqual(R.asked_again([{'customer': REC.BUTCHER, 'agent': reply}], R.GIVEN['butcher']), [])

    def test_the_summarys_own_needed_line_is_part_of_the_one_approval(self):
        reply = ('שלב 1 מתוך 2 — זה מה שהבנתי שאתם רוצים: מטרה: אתר. ביקשתם כפתור חיוג, אבל לא כתבתם מספר הטלפון. '
                 'מה מספר הטלפון? אפשר לכתוב בהודעה, או לאשר בנייה בלעדיו.')
        self.assertEqual(R.question_with_summary([{'customer': 'אתר', 'agent': reply}]), [])


if __name__ == '__main__':
    unittest.main()
