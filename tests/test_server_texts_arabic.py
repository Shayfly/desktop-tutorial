"""The server's fixed customer texts in Arabic (2026-11-22).

The platform speaks Hebrew, English and Arabic (assets/app.js LANGS; investor_app._lang). Until now the server's own
sentences -- the conversation, the approval, a failed build, the fact check, the discovery questions -- existed in
Hebrew and English only, and an Arabic customer read English, or, where a selector read `lang != 'en'`, Hebrew. The
Arabic was translated from the Hebrew and checked by an independent reviewer; omni_prod/customer_lang.py holds the one
rule that picks it (he -> he, ar -> ar, anything else -> en; never Hebrew for a customer who is not Hebrew).

Checked here, on the real modules (no network, no database, no model):
  * every language table that has English has Arabic, with the same keys (a missing key FAILS, it never falls back);
  * no Arabic text holds a Hebrew letter; every Arabic text holds Arabic letters unless its English is only a name,
    a number or a placeholder; the placeholders are the English ones;
  * every discovery question and option has its Arabic, and the card the customer sees carries it;
  * a button the server names is named exactly as app.js's Arabic screen names it (T.ar, executed in node);
  * end to end: a conversation turn and an approval made through the real ConversationSupervisor with lang='ar' are
    Arabic; with lang='fr' they are the English ones, never Hebrew.
Mutations: tests/negative_controls/server_texts_arabic.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import build_announcement as BA
from omni_prod import customer_lang as CL
from omni_prod import discovery as d
from omni_prod import fact_canon as FC
from omni_prod import ui_translations as UI
from omni_prod.conversation import supervisor as SUP
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.intake import approval_flow as AF
from omni_prod.intake import conversation_agent as CA
from omni_prod.intake import gaps as G
from omni_prod.intake import venice as V
from tests.test_conversation_os import MemoryBriefs

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'omni_prod' / 'assets' / 'app.js'
HEBREW = re.compile(r'[֐-׿]')
ARABIC = re.compile(r'[؀-ۿ]')
PLACEHOLDER = re.compile(r'\{[^{}]*\}|%[sdr]')
LETTER = re.compile(r'[^\W\d_]')                     # a letter of any script
NAME_OR_URL = re.compile(r'^(?:https?://\S+|148AI|Google Fonts|OFL)$')

# Every language-keyed table of fixed customer texts. ui_translations._LIVE_RUNNER_COPY keeps its English apart.
TABLES = {
    'approval_flow.TEXT': AF.TEXT, 'approval_flow.CONFIRM_BUTTON': AF.CONFIRM_BUTTON,
    'approval_flow.APPROVE_BUTTON': AF.APPROVE_BUTTON, 'approval_flow.EDIT_BUTTON': AF.EDIT_BUTTON,
    'build_announcement.TEXT': BA.TEXT, 'build_announcement.RETRY_BUTTON': BA.RETRY_BUTTON,
    'build_announcement.EDIT_BUTTON': BA.EDIT_BUTTON, 'build_announcement.MORE': BA.MORE,
    'supervisor._TXT': SUP._TXT, 'supervisor.SHORT': SUP.SHORT,
    'conversation_agent.SUBJECT_QUESTION': CA.SUBJECT_QUESTION, 'conversation_agent.NAME_QUESTION': CA.NAME_QUESTION,
    'conversation_agent.COLOUR_QUESTION': CA.COLOUR_QUESTION,
    'fact_canon._LABELS': FC._LABELS, 'fact_canon._TEXT': FC._TEXT, 'fact_canon._NEEDED_TEXT': FC._NEEDED_TEXT,
    'fact_canon._OR': FC._OR,
    'gaps.FALLBACK': G.FALLBACK, 'venice._TEXT': V._TEXT,
    'ui_translations.UI_COPY': {'en': UI.UI_COPY['en'], 'ar': UI.UI_COPY['ar']},
    'ui_translations._LIVE_RUNNER_COPY': {'en': UI._LIVE_RUNNER_COPY_EN, 'ar': UI._LIVE_RUNNER_COPY['ar']},
}
# Tables written in Hebrew only, whose English side is the raw key or the registry's own words: Arabic has the same keys.
HEBREW_TABLES = {
    'supervisor._CAP': (SUP._CAP_HE, SUP._CAP_AR), 'supervisor._REASON': (SUP._REASON_HE, SUP._REASON_AR),
    'supervisor._INTEGRATION': (SUP._INTEGRATION_HE, SUP._INTEGRATION_AR), 'supervisor._ALT': (SUP._ALT_HE, SUP._ALT_AR),
    'discovery.IMAGE_PLACES': (d.IMAGE_PLACES_HE, d.IMAGE_PLACES_AR), 'discovery._KIND': (d._KIND_HE, d._KIND_AR),
    'discovery.GROUP_TITLES': (d.GROUP_TITLES, d.GROUP_TITLES_AR),
}
# app.js keys of the buttons and screens the server names in its sentences
UI_KEYS = ('actApproveSpec', 'approveBuild', 'confirm', 'actApprove', 'propApprove', 'editAll', 'actRetryBuild',
           'delegateShort', 'tab_req')


def _keys(a, b, path=''):
    """The key paths where two nested tables differ (dicts by key; tuples by length)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f'{path}/{k}: only in English' for k in a if k not in b] + [f'{path}/{k}: only in Arabic' for k in b if k not in a]
        return out + [x for k in a if k in b for x in _keys(a[k], b[k], f'{path}/{k}')]
    if isinstance(a, tuple) and isinstance(b, tuple):
        return [f'{path}: {len(a)} items in English, {len(b)} in Arabic'] if len(a) != len(b) else \
            [x for i, (p, q) in enumerate(zip(a, b)) for x in _keys(p, q, f'{path}[{i}]')]
    return []


def _pairs(en, ar, path=''):
    """(path, English text, Arabic text) for every text both tables hold. A function (the image count) is called."""
    if isinstance(en, dict) and isinstance(ar, dict):
        for k in en:
            if k in ar:
                yield from _pairs(en[k], ar[k], f'{path}/{k}')
    elif isinstance(en, tuple) and isinstance(ar, tuple):
        for i, (p, q) in enumerate(zip(en, ar)):
            yield from _pairs(p, q, f'{path}[{i}]')
    elif callable(en) and callable(ar):
        for n in (1, 2, 3, 11):
            yield f'{path}({n})', en(n), ar(n)
    elif isinstance(en, str) and isinstance(ar, str):
        yield path, en, ar


def every_pair():
    for name, table in TABLES.items():
        yield from _pairs(table['en'], table['ar'], name)
    for name, (he, ar) in HEBREW_TABLES.items():
        for k in he:
            if k in ar:
                yield f'{name}/{k}', (he[k][1] if isinstance(he[k], tuple) else str(k)), ar[k]
    for q in d.QUESTIONS:
        yield f'Question({q.id}).text', q.en, q.ar
        yield f'Question({q.id}).why', q.why_en, q.why_ar
        for o in q.options:
            yield f'Question({q.id}).options[{o.value}]', o.en, o.ar
    for he, ar in d._STORED_AR.items():
        yield f'discovery._STORED_AR[{he[:20]}]', he, ar
    for k, ar in d._SEMANTIC_NAMES_AR.items():
        yield f'discovery._SEMANTIC_NAMES_AR[{k}]', k, ar


def _only_a_name(english: str) -> bool:
    """A source text with nothing to translate: once its placeholders are out, no letter is left (a number, a symbol
    such as the paperclip), or what is left is a URL or a product name."""
    rest = PLACEHOLDER.sub(' ', english).strip()
    return not LETTER.search(rest) or bool(NAME_OR_URL.match(rest))


class TheLanguageRule(unittest.TestCase):
    def test_hebrew_and_arabic_as_asked_every_other_language_english(self):
        self.assertEqual(CL.pick('he'), 'he')
        self.assertEqual(CL.pick('ar'), 'ar')
        for other in ('en', 'fr', 'ru', None, '', 'he_en', 'other', 'HE', 'he-IL'):
            with self.subTest(lang=other):
                self.assertEqual(CL.pick(other), 'en')

    def test_a_table_without_the_language_raises_never_falls_back(self):
        with self.assertRaises(KeyError):
            CL.of({'he': 'שלום', 'en': 'hello'}, 'ar')
        self.assertEqual(CL.of({'he': 'שלום', 'en': 'hello', 'ar': 'مرحبا'}, 'fr'), 'hello')
        self.assertEqual(CL.say('ar', he='שלום', ar='مرحبا', en='hello'), 'مرحبا')
        self.assertEqual(CL.say('fr', he='שלום', ar='مرحبا', en='hello'), 'hello')

    def test_a_question_without_arabic_says_so_loudly(self):
        bare = d.Option('x', 'איקס', 'ex')
        self.assertEqual(bare.label_in('fr'), 'ex')
        with self.assertRaises(LookupError):
            bare.label_in('ar')


class EveryTableHasArabic(unittest.TestCase):
    def test_every_language_table_has_arabic_with_the_same_keys(self):
        problems = []
        for name, table in TABLES.items():
            problems += [name + p for p in _keys(table['en'], table['ar'])]
        for name, (he, ar) in HEBREW_TABLES.items():
            problems += [f'{name}: {sorted(set(he) ^ set(ar), key=str)}'] if set(he) != set(ar) else []
        self.assertEqual(problems, [])

    def test_every_stored_hebrew_value_a_customer_reads_has_arabic(self):
        stored = [q.recommended for q in d.QUESTIONS if q.kind == 'text' and q.recommended and HEBREW.search(q.recommended)]
        stored += [v for v in d._WEBSITE_DEFAULTS.values() if HEBREW.search(v)]
        stored += [d._website_screens('')]
        stored += d._website_screens('homepage, search for flights, contact form, about us, gallery, price list').split(', ')
        self.assertGreaterEqual(len(stored), 10)
        self.assertEqual([s for s in stored if s not in d._STORED_AR], [])

    def test_no_arabic_text_has_a_hebrew_letter(self):
        bad = [(path, ar) for path, _, ar in every_pair() if HEBREW.search(ar)]
        self.assertEqual(bad, [])

    def test_every_arabic_text_has_arabic_letters(self):
        bad = [(path, en, ar) for path, en, ar in every_pair() if not ARABIC.search(ar) and not _only_a_name(en)]
        self.assertEqual(bad, [])
        self.assertGreater(len(list(every_pair())), 360)

    def test_placeholders_are_the_english_ones(self):
        bad = [(path, en, ar) for path, en, ar in every_pair()
               if set(PLACEHOLDER.findall(en)) != set(PLACEHOLDER.findall(ar))]
        self.assertEqual(bad, [])


class EveryQuestionHasArabic(unittest.TestCase):
    def test_each_question_and_option_has_arabic(self):
        missing = [q.id for q in d.QUESTIONS if not q.ar or not q.why_ar]
        missing += [f'{q.id}/{o.value}' for q in d.QUESTIONS for o in q.options if not o.ar]
        self.assertEqual(missing, [])
        self.assertIs(d.IMAGE_QUESTIONS[0], d.BY_ID[d.IMAGE_QUESTIONS[0].id])     # one object per question

    def test_the_card_carries_the_arabic(self):
        for q in d.QUESTIONS:
            with self.subTest(q=q.id):
                card = q.to_dict('ar')
                self.assertEqual((card['text'], card['why']), (q.ar, q.why_ar))
                self.assertEqual([o['label'] for o in card['options']], [o.ar for o in q.options])
                self.assertEqual(q.to_dict('fr'), q.to_dict('en'))                   # never Hebrew for French
                self.assertEqual(CA.asked_in_words(q, 'ar'), q.ar[:CA.MAX_QUESTION_CHARS])
        self.assertEqual(d.BY_ID['references'].to_dict('ar')['recommended'], 'لا يوجد')
        self.assertEqual(d.BY_ID['references'].to_dict('he')['recommended'], 'אין')     # the stored value itself

    def test_the_summary_and_the_image_lines_are_arabic(self):
        b = d.start('أحتاج أداة داخلية بسيطة لفريقي لتتبع إعارة المعدات')
        b = d.answer(b, {q.id: q.options[0].value if q.kind == 'choice' else d.DELEGATE for q in d.pending(b)})
        b.assets['images'] = [{'kind': 'person', 'alt': 'الجد', 'use': 'as_is', 'place': 'hero'},
                              {'kind': 'other', 'alt': 'شعار', 'use': 'inspiration', 'place': None}]
        s = d.summary(b, 'ar')
        texts = [*s['included'], *s['excluded'], *s['group_titles'].values(),
                 *(x['question'] for g in s['sections'].values() for x in g),
                 *(x['value'] for g in s['sections'].values() for x in g), *d.image_canon_lines(b, 'ar')]
        self.assertGreater(len(texts), 15)
        self.assertEqual([t for t in texts if HEBREW.search(str(t)) or not ARABIC.search(str(t))], [])
        self.assertEqual(d.summary(b, 'fr'), d.summary(b, 'en'))


def _app_js_labels() -> dict:
    """app.js's own string tables, as the browser builds them (T, then every Object.assign onto it), for each language."""
    source = APP.read_text(encoding='utf-8')
    tables = source[source.index('const T ='):source.index('const S =')]
    assigns = '\n'.join(re.findall(r'^Object\.assign\(T\.(?:he|en|ar), \{.*?\}\);$', source, re.S | re.M))
    code = '\n'.join([tables, 'const S = {lang: "he"};', assigns,
                      f'console.log(JSON.stringify(Object.fromEntries(["he", "en", "ar"].map(l => [l, '
                      f'Object.fromEntries({json.dumps(list(UI_KEYS))}.map(k => [k, T[l][k]]))]))));'])
    done = subprocess.run(['node', '-'], input=code, capture_output=True, text=True, timeout=50)
    assert done.returncode == 0, done.stderr[-1500:]
    return json.loads(done.stdout)


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js')
class TheButtonsAreNamedAsTheScreenNamesThem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = _app_js_labels()

    def test_button_names_match_app_js(self):
        ar = self.ui['ar']
        self.assertEqual(AF.CONFIRM_BUTTON['ar'], ar['actApproveSpec'])
        self.assertEqual({AF.APPROVE_BUTTON['ar']}, {ar[k] for k in ('approveBuild', 'confirm', 'actApprove', 'propApprove')})
        self.assertEqual(AF.EDIT_BUTTON['ar'], ar['editAll'])
        self.assertEqual(BA.EDIT_BUTTON['ar'], ar['editAll'])
        self.assertEqual(BA.RETRY_BUTTON['ar'], ar['actRetryBuild'])

    def test_the_sentences_quote_the_buttons_and_screens_by_their_arabic_names(self):
        ar, T = self.ui['ar'], SUP._TXT['ar']
        quote = lambda s: f'"{s}"'
        for text, name in ((AF.text('ar')['gate1'], ar['actApproveSpec']), (AF.text('ar')['refused'], ar['editAll']),
                           (AF.text('ar')['gate2'], ar['approveBuild']), (T['approve'], ar['approveBuild']),
                           (T['ready_again'], ar['approveBuild']), (T['limit_incomplete_any'], ar['editAll']),
                           (T['unsure'], ar['delegateShort']), (T['unsure_norec'], ar['delegateShort']),
                           (T['more'], ar['tab_req']), (T['safe_default'], ar['tab_req']), (T['card_blocked'], ar['tab_req'])):
            with self.subTest(text=text[:40]):
                self.assertIn(quote(name), text)

    def test_the_customer_message_of_a_button_is_the_button_name(self):
        """approve_spec stores the confirm button's name as the customer's message; a delegate press its label."""
        sup, t = _conversation('ar')
        approve = sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=t.brief_row.fingerprint, lang='ar',
                                   canon_ack=True)
        said = [m['content'] for m in sup.store.messages_for('p') if m['role'] == 'customer']
        self.assertIn(self.ui['ar']['actApproveSpec'], said)
        self.assertTrue(approve.reply)
        sup2 = SUP.ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), credits=200)
        sup2.turn(project_id='p', account_id='a', message=REQUEST_AR, lang='ar')
        sup2.turn(project_id='p', account_id='a', answers={'style': d.DELEGATE}, lang='ar')
        said = [m['content'] for m in sup2.store.messages_for('p') if m['role'] == 'customer']
        self.assertIn(self.ui['ar']['delegateShort'], said[-1])


REQUEST_AR = 'أحتاج أداة داخلية بسيطة لفريقي لتتبع إعارة المعدات، بدون تسجيل دخول وبدون بيانات شخصية'
REQUEST_EN = 'I need a simple internal tool for my team to track equipment loans, in English, no login, no personal data'


def _conversation(lang, request=None):
    """The real supervisor, offline (the deterministic interpreter; memory stores), driven to gate 1 by pressing the
    first option of every card: (supervisor, the gate-1 turn)."""
    sup = SUP.ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), credits=200)
    say = lambda msg='', answers=None: sup.turn(project_id='p', account_id='a', message=msg, answers=answers, lang=lang)
    t = say(request or (REQUEST_AR if lang == 'ar' else REQUEST_EN))
    turns = [t]
    for _ in range(12):                                   # bounded: a conversation that does not reach gate 1 fails
        if any(a['type'] == 'approve_spec' for a in t.actions):
            sup.turns = turns
            return sup, t
        q = t.questions[0] if t.questions else None
        assert q is not None, t.reply
        t = say(answers={q.id: q.options[0].value if q.kind == 'choice' else d.DELEGATE})
        turns.append(t)
    raise AssertionError('never reached gate 1')


# The Latin words an Arabic text may carry: names (fonts, the product), never an English sentence.
LATIN_NAMES = {'Heebo', 'Assistant', 'Rubik', 'SMS', 'Google', 'Fonts', 'OFL', '148AI'}


def _arabic_only(test, text):
    test.assertFalse(HEBREW.search(text), text)
    test.assertTrue(ARABIC.search(text), text)
    test.assertEqual(set(re.findall(r'[A-Za-z0-9]*[A-Za-z][A-Za-z0-9]*', text)) - LATIN_NAMES, set(), text)


class EndToEnd(unittest.TestCase):
    """The cheapest real entry point: ConversationSupervisor.turn / approve_spec with memory stores (no network, no
    database, no model call -- the deterministic interpreter answers), as tests/test_question_in_words.py drives it."""

    def test_a_conversation_turn_in_arabic_is_arabic(self):
        sup, gate1 = _conversation('ar')
        self.assertTrue(any(SUP._TXT['ar']['ask_one'] in t.reply for t in sup.turns))
        for t in sup.turns:
            with self.subTest(reply=t.reply[:40]):
                _arabic_only(self, t.reply)
                for q in t.to_dict('ar')['questions']:
                    _arabic_only(self, q['text'] + ' ' + ' '.join(o['label'] for o in q['options']))
        self.assertIn(AF.text('ar')['gate1'], gate1.reply)
        self.assertIn(AF.text('ar')['stage1'], gate1.reply)

    def test_an_approval_in_arabic_is_arabic(self):
        sup, gate1 = _conversation('ar')
        approve = sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=gate1.brief_row.fingerprint,
                                   lang='ar', canon_ack=True)
        _arabic_only(self, approve.reply)
        for key in ('stage2', 'planned', 'gate2'):
            self.assertIn(AF.text('ar')[key], approve.reply)
        self.assertEqual([a['type'] for a in approve.actions], ['show_plan', 'approve_build'])

    def test_a_french_customer_reads_the_english_never_hebrew(self):
        fr, fr_gate1 = _conversation('fr', REQUEST_EN)
        en, en_gate1 = _conversation('en', REQUEST_EN)
        self.assertEqual([t.reply for t in fr.turns], [t.reply for t in en.turns])
        self.assertEqual([t.to_dict('fr')['questions'] for t in fr.turns], [t.to_dict('en')['questions'] for t in en.turns])
        self.assertFalse(HEBREW.search(fr.turns[0].reply), fr.turns[0].reply)
        approve = [s.approve_spec(project_id='p', account_id='a', brief_fingerprint=g.brief_row.fingerprint, lang=lang,
                                  canon_ack=True) for s, g, lang in ((fr, fr_gate1, 'fr'), (en, en_gate1, 'en'))]
        self.assertEqual(approve[0].reply, approve[1].reply)
        self.assertFalse(HEBREW.search(approve[0].reply), approve[0].reply)
        self.assertIn('To start building, press "Approve and start building".', approve[0].reply)

    def test_the_supervisors_own_sentences_in_arabic(self):
        T = SUP._TXT['ar']
        said = [SUP.ConversationSupervisor._finding_message(f, 'ar', T) for f in (
                    {'item': 'sign-in: roles'}, {'item': 'integration: payments'}, {'item': 'integration: maps'})]
        for text in said:
            _arabic_only(self, text)
        blocked = SUP.ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), admission=lambda *a: {
            'can_build': False, 'blocked_reason': {'message': 'م', 'next': 'ن'}})
        _arabic_only(self, blocked._admission_block('p', None, 'ar'))
        self.assertTrue(blocked._admission_block('p', None, 'fr').startswith('The build cannot start yet'))
        answer = SUP.ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())._feasibility_answer(
            'can we add payments and email?', SimpleNamespace(brief=d.start(REQUEST_AR)), T)
        _arabic_only(self, answer)

    def test_the_build_choice_quotes_the_cards_own_label(self):
        """'wait' on an unavailable capability: the sentence names the card's 'build without it' button as it is."""
        brief = d.start(REQUEST_AR)
        brief.hints['unpriced'] = 'payments'
        brief.fields['unavailable'] = {'value': 'wait', 'source': 'answer', 'question_id': 'unavailable', 'confidence': 'confirmed'}
        sup = SUP.ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), admission=lambda *a: {})
        for lang in ('he', 'ar', 'en'):
            with self.subTest(lang=lang):
                [line] = sup._unpriced_gate('p', 'a', SimpleNamespace(brief=brief, revision=1), lang, SimpleNamespace())
                label = d.BY_ID['unavailable'].options[0].label_in(lang)
                self.assertIn(f'"{label}"', line)
        [line] = sup._unpriced_gate('p', 'a', SimpleNamespace(brief=brief, revision=1), 'ar', SimpleNamespace())
        self.assertFalse(HEBREW.search(line), line)

    def test_a_failed_build_is_said_in_arabic_and_in_english_for_french(self):
        for code in ('verification_failed', 'needs_customer_input', None):
            for billing in ('released', None):
                with self.subTest(code=code, billing=billing):
                    ar = BA.message_for(build_id='bld_1', error_code=code, billing=billing, lang='ar')['content']
                    _arabic_only(self, ar)
                    fr = BA.message_for(build_id='bld_1', error_code=code, billing=billing, lang='fr')
                    self.assertEqual(fr, BA.message_for(build_id='bld_1', error_code=code, billing=billing, lang='en'))

    def test_the_fact_check_and_the_open_questions_in_arabic(self):
        lines = FC.gate_view('', customer_text='أريد زر واتساب وساعات العمل', family='website', lang='ar',
                             needs=('phone', 'hours'), waived=('hours',))['lines']
        self.assertEqual(len(lines), 3)
        for line in lines:
            _arabic_only(self, line)
        for mode in ('ask', 'explain', 'short', 'confirm'):
            _arabic_only(self, G.fallback_text('link_scope', 'ar', mode, 'internal_link'))
        self.assertEqual(G.fallback_text('link_scope', 'fr'), G.fallback_text('link_scope', 'en'))


if __name__ == '__main__':
    unittest.main()
