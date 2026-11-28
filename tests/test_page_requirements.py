"""Warehouse 122 (the owner's expert, 2026-11-21): the fields a page must have, per kind of page.

Keyed by the page type of warehouse 123 (output_profile/page_types.json, the stable key `page_type`). The conversation
agent reads the required fields from what the customer already said, asks ONE question in its own words only for a
field that is still missing (each at most once; the page type first when the words name none or two), and the page
shows every other field from a default the domain file declares, marked as a default. Nothing is invented: a required
field that stays unanswered is left off the page and listed as "not given".

Real path: required_fields.json and page_types.json as committed, domain_registry.json and docs/domains/*.md; the fact
sheet's own extractors; gaps.Spec and Questioner; ConversationSupervisor with its in-memory stores;
discovery.requirements_text; the fact sheet of the approved prompt; the content route's render and the section
library's HTML."""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import customer_words as CW
from omni_prod.intake import conversation_agent as agent
from omni_prod import discovery as d
from omni_prod import domain_registry as DR
from omni_prod import page_requirements as PR
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.gaps import FALLBACK, Questioner, Spec
from omni_prod.intake.interpreter import SYSTEM, contextual_user
from omni_prod.output_profile import page_types as PT
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R
from tests.test_conversation_os import MemoryBriefs

ROOT = Path(__file__).resolve().parent.parent
AGENT = {'OMNI_INTAKE_AGENT': '1', 'OMNI_INTAKE_MODEL': '0'}
BUTCHER = 'אני רוצה אתר לאטליז "בשר השכונה" בחיפה'
BUSINESS_FIELDS = ['phone', 'address', 'hours', 'kashrut', 'delivery']
LANGS = ('he', 'ar', 'en')
SCRIPT = {'he': r'[֐-׿]', 'ar': r'[؀-ۿ]'}
TYPE_REPLY = {'he': 'עסק או שירות', 'ar': 'عمل تجاري أو خدمة', 'en': 'business or service'}
DONT_KNOW = {'he': 'לא יודע', 'ar': 'لا أعرف', 'en': "don't know"}


def agent_on(test):
    patcher = mock.patch.dict(os.environ, AGENT)
    patcher.start()
    test.addCleanup(patcher.stop)


def section4(slug: str) -> list[str]:
    """The first column of the rows of "## 4. Declared defaults" in a domain file."""
    text = (ROOT / 'docs' / 'domains' / f'{slug}.md').read_text(encoding='utf-8')
    body = text.split('## 4. Declared defaults', 1)[1].split('## 5.', 1)[0]
    return [line.split('|')[1].strip() for line in body.splitlines() if line.startswith('|')][2:]


class TheTable(unittest.TestCase):
    def test_it_is_keyed_by_the_stable_page_type_of_the_typology(self):
        self.assertEqual(PR.KEYED_BY, 'page_type')
        self.assertEqual(list(PR.data()['page_types']), list(PT.TYPES))
        self.assertEqual(len(PT.TYPES), 8)

    def test_the_types_labels_are_the_typologys_own(self):
        raw = json.loads(PT.DATA.read_text(encoding='utf-8'))['types']
        for t in PT.TYPES:
            self.assertEqual((PR.TYPE_LABEL[t]['he'], PR.TYPE_LABEL[t]['en']), (raw[t]['label_he'], raw[t]['label_en']))

    def test_the_fields_of_the_three_types_the_owners_expert_named(self):
        got = {t: [r['key'] for r in v['required']] for t, v in PR.data()['page_types'].items()}
        self.assertEqual(got['business'], ['phone', 'address', 'hours'])
        self.assertEqual(got['portfolio'], ['projects'])
        self.assertEqual(got['event'], ['date', 'venue', 'registration'])
        for t in ('community', 'documentation', 'product', 'personal', 'landing'):
            self.assertEqual(got[t], [], t)                      # none defined yet: said, not guessed

    def test_the_category_fields_are_rows_of_the_domain_registry_and_are_not_copied(self):
        registry = DR.load()['domains']
        for slug, spec in PR.data()['domains'].items():
            facts = {f['n']: f['fact'].lower() for f in registry[slug]['mandatory_facts']}
            for r in spec['required']:
                with self.subTest(slug=slug, field=r['key']):
                    self.assertIn(r['domain_fact'], facts)
                    self.assertIn({'kashrut': 'kosher', 'delivery': 'delivery'}[r['key']], facts[r['domain_fact']])
                    self.assertFalse({'question', 'why', 'fact'} & set(r), 'the registry owns the question and the reason')

    def test_every_default_is_a_row_of_the_domain_files_declared_defaults(self):
        for slug, spec in PR.data()['domains'].items():
            for dflt in spec['defaults']:
                with self.subTest(slug=slug, default=dflt['key']):
                    self.assertIn(dflt['domain_row'], section4(slug))

    def test_a_required_field_is_never_also_a_default(self):
        for slug, spec in PR.data()['domains'].items():
            self.assertFalse({r['key'] for r in spec['required']} & {x['key'] for x in spec['defaults']})

    def test_a_broken_file_stops_the_module(self):
        raw = json.loads(PR.DATA.read_text(encoding='utf-8'))
        for broken, why in ((lambda x: x['page_types'].pop('event'), 'typology'),
                            (lambda x: x['domains']['butcher-deli']['required'][0].update(domain_fact=99), 'no mandatory fact'),
                            (lambda x: x['domains'].update(nowhere={'required': [], 'defaults': []}), 'has no file')):
            data = json.loads(json.dumps(raw))
            broken(data)
            fake = Path(tempfile.mkdtemp()) / 'required_fields.json'
            fake.write_text(json.dumps(data), encoding='utf-8')
            with self.subTest(why), mock.patch.object(PR, 'DATA', fake):
                PR.data.cache_clear()
                try:
                    with self.assertRaisesRegex(RuntimeError, why):
                        PR.data()
                finally:
                    PR.data.cache_clear()
        PR.data()

    def test_the_texts_are_in_three_languages_in_the_customers_words(self):
        for key, texts in PR.TEXT.items():
            for lang in LANGS:
                label, question, why = texts[lang]
                for text in (label, question, why):
                    with self.subTest(key=key, lang=lang, text=text[:20]):
                        self.assertNotRegex(text, r'שרת')
                        if lang in SCRIPT:
                            self.assertRegex(text, SCRIPT[lang])
                        else:
                            self.assertTrue(text.isascii())
                self.assertEqual(CW.machine_terms(question + ' ' + why + ' ' + label), [])
        for lang in LANGS:
            self.assertNotRegex(PR.SKIP[lang], r'שרת')
            for by_key in PR.DEFAULTS.values():
                for label, text in by_key.values():
                    self.assertNotRegex(text[lang] + label[lang], r'שרת')
        self.assertTrue(all(PR.MARK[lang] for lang in LANGS))

    def test_the_module_is_part_of_the_customer_text_the_platform_words_check_reads(self):
        self.assertIn('omni_prod/page_requirements.py', CW.CUSTOMER_TEXT)
        self.assertIn('omni_prod/page_requirements.py', CW.CONVERSATION)
        self.assertEqual(CW.scan('omni_prod/page_requirements.py', root=ROOT), [])


class TheProfile(unittest.TestCase):
    def keys(self, text):
        p = PR.profile_of(text)
        return p.page_type, p.found, p.domain, [r.key for r in p.required]

    def test_a_business_gets_the_types_fields_then_its_categorys(self):
        self.assertEqual(self.keys(BUTCHER), ('business', 'named', 'butcher-deli', BUSINESS_FIELDS))

    def test_a_category_with_no_row_gets_only_the_types_fields(self):
        self.assertEqual(self.keys('אני רוצה אתר לעורך דין'), ('business', 'named', None, ['phone', 'address', 'hours']))

    def test_a_portfolio_and_an_event_are_not_asked_for_opening_hours(self):
        self.assertEqual(self.keys('אתר תיק עבודות של מעצבת')[3], ['projects'])
        self.assertEqual(self.keys('אתר לאירוע חתונה')[3], ['date', 'venue', 'registration'])

    def test_no_type_or_a_tie_names_none_and_the_category_fields_wait_for_the_type(self):
        self.assertEqual(self.keys('אני רוצה אתר'), (None, 'none', None, []))
        self.assertEqual(self.keys('אירוע ותיק עבודות')[:2], (None, 'tie'))

    def test_the_customers_answer_to_the_type_question_names_it_in_any_language(self):
        for lang, reply in TYPE_REPLY.items():
            with self.subTest(lang):
                self.assertEqual(self.keys('אני רוצה אתר\n' + reply)[:2], ('business', 'named'))
        self.assertEqual(self.keys('אירוע ותיק עבודות\nתיק עבודות')[:2], ('portfolio', 'named'))
        self.assertEqual(self.keys('אני רוצה אתר\nלא יודע')[:2], (None, 'none'))


class TheExtraction(unittest.TestCase):
    """The agent reads a field from free speech first: the fact sheet's own extractors and a cue in the words."""

    def missing(self, text):
        return PR.missing_keys(PR.profile_of(text), text)

    def test_a_butcher_who_said_everything_is_asked_nothing(self):
        said = ('אטליז בשר השכונה, כשר בהשגחת הרבנות. פתוח א׳–ה׳ 07:00–19:00, טלפון 04-8123456, '
                'רחוב הרצל 12 חיפה. משלוחים בכל הארץ.')
        self.assertEqual(self.missing(said), [])

    def test_a_butcher_who_said_only_the_phone_is_asked_for_the_rest(self):
        self.assertEqual(self.missing('אטליז, טלפון 04-8123456'), ['address', 'hours', 'kashrut', 'delivery'])

    def test_no_delivery_is_an_answer_and_delivery_without_a_place_is_not(self):
        self.assertNotIn('delivery', self.missing('אטליז, אין משלוחים'))
        self.assertNotIn('delivery', self.missing('אטליז, משלוחים באזור המרכז'))
        self.assertNotIn('delivery', self.missing('אטליז, משלוחים עד 20 ק"מ'))
        self.assertIn('delivery', self.missing('אטליז, אנחנו עושים משלוחים'))

    def test_kosher_or_halal_in_each_language(self):
        for said in ('אטליז כשר למהדרין', 'אטליז, المحل حلال', 'אטליז, we are kosher', 'אטליז halal certified'):
            with self.subTest(said):
                self.assertNotIn('kashrut', self.missing(said))
        self.assertIn('kashrut', self.missing('אטליז מעולה'))

    def test_three_projects_are_a_list_and_two_are_not(self):
        self.assertEqual(self.missing('תיק עבודות. הפרויקטים שלי: לוגו לפסטיבל, פוסטר לתערוכה, ספר ילדים'), [])
        self.assertEqual(self.missing('תיק עבודות. הפרויקטים שלי: לוגו לפסטיבל, פוסטר לתערוכה'), ['projects'])
        self.assertEqual(self.missing('my portfolio. my projects: a logo, a site and a label'), [])

    def test_an_event_states_its_date_place_and_registration(self):
        self.assertEqual(self.missing('אירוע חתונה'), ['date', 'venue', 'registration'])
        self.assertEqual(self.missing('אירוע חתונה ב-12.5, באולם הגפן, הרשמה בטלפון'), [])

    def test_the_words_kept_are_the_customers_own_clause_not_the_whole_message(self):
        said = 'אטליז בחיפה, כשר בהשגחת הרבנות, פתוח כל יום. משלוחים עד 20 ק"מ מהחנות'
        with mock.patch.dict(os.environ, AGENT):
            got = PR.capture(said, said, {})
        self.assertEqual(got, {'kashrut': 'כשר בהשגחת הרבנות', 'delivery': 'משלוחים עד 20 ק"מ מהחנות'})


class TheQuestion(unittest.TestCase):
    def setUp(self):
        agent_on(self)

    def walk(self, opening, replies):
        """Ask until nothing is left; the customer answers each question with the next reply."""
        spec, asked = Spec('website', [opening]), []
        replies = iter(replies)
        while (q := Questioner().next(spec)) is not None and q.field in PR.TEXT:      # the page's own questions
            asked.append((q.field, q.text))
            self.assertLess(len(asked), 14)
            spec.hear(next(replies, 'לא יודע'))
        return spec, asked

    def page_fields(self, asked):
        return [f for f, _ in asked if f in PR.TEXT]

    def test_one_question_per_missing_required_field_each_asked_once_then_the_summary(self):
        spec, asked = self.walk(BUTCHER, ['04-8123456', 'רחוב הרצל 12 חיפה', 'א-ה 07:00-19:00',
                                          'כשר בהשגחת הרבנות', 'אין משלוחים'])
        self.assertEqual(self.page_fields(asked), BUSINESS_FIELDS)        # one question each, in order, none twice
        self.assertEqual(spec.value('kashrut'), 'כשר בהשגחת הרבנות')
        self.assertEqual(spec.value('delivery'), 'אין משלוחים')

    def test_what_the_customer_already_said_is_never_asked(self):
        opening = (BUTCHER + ', כשר בהשגחת הרבנות, פתוחים א-ה 07:00-19:00, טלפון 04-8123456, רחוב הרצל 12 חיפה, '
                   'משלוחים בכל הארץ')
        _, asked = self.walk(opening, [])
        self.assertEqual(self.page_fields(asked), [])

    def test_dont_know_leaves_the_field_off_with_no_default_and_it_is_not_asked_again(self):
        spec, asked = self.walk(BUTCHER + ', טלפון 04-8123456, פתוחים א-ה 07:00-19:00, רחוב הרצל 12 חיפה',
                                ['לא יודע', 'תחליט אתה'])
        self.assertEqual(self.page_fields(asked), ['kashrut', 'delivery'])
        self.assertEqual(spec.value('kashrut'), '')                      # no value was invented
        self.assertEqual(spec.value('delivery'), '')
        self.assertEqual(spec.ledger.current('kashrut').status, 'assumed')

    def test_no_type_the_type_is_asked_first_listing_the_types_and_a_reply_names_it(self):
        spec = Spec('website', ['אני רוצה אתר'])
        q = Questioner().next(spec)
        self.assertEqual(q.field, PR.TYPE_KEY)
        for label in PR.TYPE_LABEL.values():
            self.assertIn(label['he'], q.text)
        spec.hear('תיק עבודות')
        self.assertEqual([f.name for f in spec.fields if f.reason.startswith(PR.REASON)], ['projects'])
        self.assertEqual(Questioner().next(spec).field, 'projects')

    def test_a_tie_asks_the_type_too_and_a_reply_that_names_none_ends_the_question(self):
        spec = Spec('website', ['אירוע ותיק עבודות'])
        self.assertEqual(Questioner().next(spec).field, PR.TYPE_KEY)
        spec.hear('לא יודע')
        self.assertIsNone(spec.value(PR.TYPE_KEY) or None)
        self.assertNotEqual((Questioner().next(spec) or Spec('website', [])).__dict__.get('field'), PR.TYPE_KEY)
        self.assertEqual(spec.metrics()['unmapped'], 0)

    def test_the_fixed_questions_are_the_tables_in_the_customers_language_and_offer_no_default(self):
        openings = {'he': 'אני רוצה אתר', 'ar': 'أريد موقعًا', 'en': 'I want a website'}
        for lang, opening in openings.items():
            with self.subTest(lang):
                spec = Spec('website', [opening])
                q = Questioner().next(spec)
                self.assertEqual((q.field, q.language, q.source), (PR.TYPE_KEY, lang, 'fallback'))
                label, question, why = PR.TEXT[PR.TYPE_KEY][lang]
                self.assertIn(question, q.text)
                self.assertIn(PR.SKIP[lang], q.text)
                self.assertNotIn(FALLBACK[lang]['_delegate'], q.text)
                spec.hear(TYPE_REPLY[lang])
                q = Questioner().next(spec)
                self.assertEqual((q.field, q.language), ('phone', lang))
                self.assertIn(PR.TEXT['phone'][lang][1], q.text)

    def test_the_model_phrases_the_question_in_its_own_words_and_is_told_not_to_offer_a_default(self):
        seen = []

        def model(system, user):
            seen.append((system, user))
            return {'field': 'hours', 'question': 'ומתי אפשר למצוא אתכם בדלפק?'}

        spec = Spec('website', [BUTCHER + ', טלפון 04-8123456, רחוב הרצל 12 חיפה, כשר, משלוחים בכל הארץ'])
        q = Questioner(model).next(spec)
        self.assertEqual((q.field, q.source, q.text), ('hours', 'model', 'ומתי אפשר למצוא אתכם בדלפק?'))
        self.assertIn('"may_delegate": false', seen[0][1])
        self.assertIn('may_delegate', seen[0][0])

    def test_with_the_agent_off_nothing_is_asked_and_the_card_flow_is_unchanged(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '0'}):
            spec = Spec('website', [BUTCHER])
            self.assertEqual([f.name for f in spec.fields if f.reason.startswith(PR.REASON)], [])
            self.assertEqual(PR.capture('כשר בהשגחת הרבנות', BUTCHER, {}), {})

    def test_the_hebrew_arabic_and_english_butcher_ask_the_same_fields_after_the_type(self):
        openings = {'he': 'אני רוצה אתר לאטליז שלי', 'ar': 'أريد موقعًا لملحمة', 'en': 'I want a website for my butcher'}
        traces = {}
        for lang, opening in openings.items():
            spec, seen = Spec('website', [opening]), []
            while (q := Questioner().next(spec)) is not None and len(seen) < 14:
                seen.append(q.field)
                spec.hear(TYPE_REPLY[lang] if q.field == PR.TYPE_KEY else DONT_KNOW[lang])
            traces[lang] = [f for f in seen if f in PR.TEXT]
        self.assertEqual(traces['he'], BUSINESS_FIELDS)
        self.assertEqual(traces['ar'], [PR.TYPE_KEY] + BUSINESS_FIELDS)     # 123's detector reads no Arabic: type asked
        self.assertEqual(traces['en'], [PR.TYPE_KEY] + BUSINESS_FIELDS)


class TheConversation(unittest.TestCase):
    """The real supervisor: what the customer says reaches the brief, and the approved prompt carries it."""

    def setUp(self):
        agent_on(self)
        self.s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())

    def say(self, message):
        return self.s.turn(project_id='p', account_id='a', lang='he', message=message)

    def brief(self):
        return self.s.briefs.latest('p').brief

    def test_the_customers_words_for_a_required_field_are_kept_and_bound_into_the_approved_brief(self):
        self.say(BUTCHER + ', טלפון 04-8123456, רחוב הרצל 12 חיפה')
        self.say('כשר בהשגחת הרבנות, פתוחים א-ה 07:00-19:00')
        self.say('משלוחים עד 20 ק"מ מהחנות')
        facts = self.brief().assets['facts']
        self.assertEqual(facts['page'], {'kashrut': 'כשר בהשגחת הרבנות', 'delivery': 'משלוחים עד 20 ק"מ מהחנות'})
        text = d.requirements_text(self.brief())
        self.assertIn(PR.PAGE_LINE + 'kashrut=כשר בהשגחת הרבנות | delivery=משלוחים עד 20 ק"מ מהחנות', text)
        self.assertNotIn(PR.NOT_GIVEN_LINE, text)                # all five were stated: nothing is "not given"

    def test_a_field_the_customer_did_not_give_is_listed_as_not_given_and_never_invented(self):
        self.say(BUTCHER + ', טלפון 04-8123456')
        for _ in range(8):                                  # the cards first, then the page's own questions
            if d.page_asked(self.brief()):
                break
            self.say('כן')
        text = d.requirements_text(self.brief())
        self.assertIn(PR.NOT_GIVEN_LINE + 'address, hours, kashrut, delivery.', text)
        self.assertNotIn(PR.PAGE_LINE, text)

    def test_the_detector_asks_each_required_field_once_and_records_that_it_did(self):
        self.say(BUTCHER + ', טלפון 04-8123456, פתוחים א-ה 07:00-19:00, רחוב הרצל 12 חיפה')
        asked = []
        for _ in range(8):
            q = ((self.say('כן').gaps or {}).get('question') or {}).get('field')
            if q in ('kashrut', 'delivery'):
                asked.append(q)
        self.assertEqual(asked.count('kashrut'), 1)
        self.assertEqual(asked.count('delivery'), 1)
        self.assertEqual(sorted(d.page_asked(self.brief())), ['delivery', 'kashrut'])

    def test_a_required_field_marked_as_asked_was_put_to_the_customer_not_swallowed_by_the_name_or_colour_question(self):
        """Found by the controls of ask-colours, ask-name and agent-subject on this change: a required field is not a
        catalogue card, so `turn.questions` stayed empty and the in-words name / colour question replaced the reply that
        carried it -- after the detector had marked the field asked. It was never asked again and the approval opened
        without it. A field counts as asked only in a turn whose reply says it."""
        for request in ('אני רוצה אתר לאטליז בחיפה, טלפון 04-8123456, רחוב הרצל 12 חיפה',            # no business name
                        'אתר תדמית למורה פרטית למתמטיקה "נועה ברק". טלפון 054-7712345. רחוב הרצל 30, רחובות.'):  # unknown business
            with self.subTest(request[:20]):
                s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
                t, shown = s.turn(project_id='p', account_id='a', lang='he', message=request), {}
                for _ in range(10):
                    q = (t.gaps or {}).get('question') or {}
                    if q.get('field') in d.page_asked(s.briefs.latest('p').brief):
                        shown[q['field']] = q['text'] in t.reply
                    t = s.turn(project_id='p', account_id='a', lang='he', message='תחליטו אתם על השאר')
                self.assertIn('hours', shown)
                self.assertEqual({k: v for k, v in shown.items() if not v}, {})

    def test_two_names_are_asked_which_first_and_the_page_field_waits_unasked_for_its_turn(self):
        """The which-name question takes the turn; a required field the detector chose in that same turn is not marked
        asked (the customer did not see it) and is put to the customer in the next turns."""
        self.say('אתר לאטליז בחיפה. אתר תוכן בלבד, לא שומרים כלום. טלפון 04-8123456')
        t = self.say('השם שלנו הוא "בשר השכונה" אבל באתר תכתבו "הקצב של חיפה"')
        self.assertEqual(getattr(t, 'asked_in_words', None), [agent.NAME_ID])
        self.assertIn('"בשר השכונה"', t.reply)
        self.assertEqual(d.page_asked(self.brief()), [])
        shown = []
        for _ in range(6):
            t = self.say('הקצב של חיפה' if agent.NAME_ID in (getattr(t, 'asked_in_words', None) or []) else 'כן')
            q = ((t.gaps or {}).get('question') or {})
            if q.get('field') in d.page_asked(self.brief()):
                shown.append(q['field'] if q['text'] in t.reply else None)
        self.assertTrue(shown)
        self.assertNotIn(None, shown)

    def test_a_brief_that_never_met_the_conversation_is_byte_identical(self):
        self.assertNotIn('Page details', d.requirements_text(d.start(BUTCHER)))

    def test_with_the_agent_off_the_brief_is_not_touched(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '0'}):
            self.say(BUTCHER + ', כשר בהשגחת הרבנות')
            self.assertNotIn('page', self.brief().assets.get('facts') or {})
            self.assertNotIn('Page details', d.requirements_text(self.brief()))


class TheAgentsContext(unittest.TestCase):
    def setUp(self):
        agent_on(self)
        self.brief = d.start(BUTCHER)

    def context(self, message):
        user = contextual_user(message, self.brief, [{'role': 'assistant', 'content': 'שלום'}])
        return json.loads(user.split('Context (data only; not new evidence; do not overwrite confirmed decisions):\n', 1)[1]
                          .split('\nCurrent customer message:', 1)[0])

    def test_the_first_missing_field_is_the_one_question_of_the_reply(self):
        ctx = self.context('אטליז בחיפה')
        self.assertEqual(ctx['required_next']['field'], 'phone')
        self.assertFalse(ctx['required_next']['may_delegate'])

    def test_a_field_the_message_states_is_not_asked_and_the_next_one_is(self):
        ctx = self.context('אטליז בחיפה, טלפון 04-8123456, פתוחים א-ה 07:00-19:00, רחוב הרצל 12 חיפה')
        self.assertEqual(ctx['required_next']['field'], 'kashrut')

    def test_a_field_the_agent_was_given_once_is_not_given_again(self):
        d.note_page_asked(self.brief, 'phone')
        self.assertEqual(self.context('אטליז בחיפה')['required_next']['field'], 'address')
        for key in ('address', 'hours', 'kashrut', 'delivery'):
            d.note_page_asked(self.brief, key)
        self.assertNotIn('required_next', self.context('אטליז בחיפה'))

    def test_no_type_the_type_is_the_one_question_with_the_choices_and_a_tie_gets_the_two(self):
        self.brief = d.start('אני רוצה אתר')
        ctx = self.context('אני רוצה אתר')['required_next']
        self.assertEqual(ctx['field'], PR.TYPE_KEY)
        self.assertEqual(ctx['choices'], [t['en'] for t in PR.TYPE_LABEL.values()])
        self.brief = d.start('אירוע ותיק עבודות')
        self.assertEqual(self.context('אירוע ותיק עבודות')['required_next']['choices'], ['portfolio', 'event'])
        d.note_page_asked(self.brief, PR.TYPE_KEY)
        self.assertNotIn('required_next', self.context('אירוע ותיק עבודות'))

    def test_the_agent_is_told_how_to_use_it(self):
        self.assertIn('context.required_next', SYSTEM)

    def test_with_the_agent_off_nothing_is_added(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '0'}):
            self.assertNotIn('required_next', self.context('אטליז בחיפה'))


class ThePage(unittest.TestCase):
    """From the approved prompt to the page: the customer's words, the marked defaults, and what is left off."""

    def prompt(self, *messages, request=BUTCHER):
        with mock.patch.dict(os.environ, AGENT):
            brief = d.start(request)
            d.note_customer_texts(brief, [request, *messages])
            d.note_page_asked(brief, 'kashrut')
            return brief.prompt + '\n' + d.requirements_text(brief)

    def test_the_sheet_holds_the_customers_words_the_marked_defaults_and_what_is_not_given(self):
        sheet = Fx.fact_sheet(self.prompt('כשר בהשגחת הרבנות', 'טלפון 04-8123456'))
        self.assertEqual(sheet.page.said, {'kashrut': 'כשר בהשגחת הרבנות'})
        self.assertEqual(sheet.page.not_given, ['address', 'hours', 'delivery'])
        self.assertEqual(sheet.page.defaults, ['order', 'price'])
        self.assertEqual(sheet.page.rows('he'), [('כשרות', 'כשר בהשגחת הרבנות'),
                                                 ('הזמנות', 'התקשרו להזמנה (ברירת מחדל)'),
                                                 ('מחירים', 'המחיר בדלפק (ברירת מחדל)')])

    def test_the_rows_are_in_hebrew_arabic_and_english_and_every_default_carries_the_mark(self):
        page = Fx.fact_sheet(self.prompt('כשר בהשגחת הרבנות', 'טלפון 04-8123456')).page
        for lang in LANGS:
            rows = page.rows(lang)
            self.assertEqual(len(rows), 3)
            for label, value in rows[1:]:
                self.assertTrue(value.endswith(f'({PR.MARK[lang]})'), value)
            self.assertNotIn(PR.MARK[lang], rows[0][1])                  # the customer's own words are not marked
        with self.assertRaises(ValueError):
            page.rows('fr')

    def test_a_default_is_not_shown_where_the_customer_said_it(self):
        said = self.prompt('טלפון 04-8123456', request=BUTCHER + ', אפשר להזמין בטלפון, נקניקיה 50 ₪')
        self.assertEqual(Fx.fact_sheet(said).page.defaults, [])

    def test_a_page_with_no_phone_shows_no_order_default(self):
        self.assertEqual(Fx.fact_sheet(self.prompt('כשר בהשגחת הרבנות')).page.defaults, ['price'])

    def test_a_category_with_no_row_gets_no_default_rows(self):
        sheet = Fx.fact_sheet('אתר לעורך דין "כהן ושות׳". טלפון 03-5551234')
        self.assertEqual((sheet.page.page_type, sheet.page.domain, sheet.page.rows('he')), ('business', None, []))

    def test_the_page_shows_the_rows_in_the_hero_panel_and_marks_the_defaults(self):
        from omni_prod import vertical_palettes as VP
        prompt = self.prompt('כשר בהשגחת הרבנות', 'טלפון 04-8123456, פתוחים א-ה 07:00-19:00')
        sheet = Fx.fact_sheet(prompt)
        contract = R.render_contract(prompt, VP.palette_for('butcher')[1])[0]
        doc = {'name': 'בשר השכונה', 'tagline': 'בשר טרי כל יום', 'description': 'אטליז שכונתי בחיפה',
               'sections': {'hero': {'title': 'בשר השכונה', 'lead': 'בשר טרי, חיתוך לפי הזמנה', 'cta': 'התקשרו אלינו'},
                            'services': {'title': 'מה יש אצלנו', 'nav': 'מוצרים', 'items': [
                                {'title': 'בקר', 'desc': 'נתחים טריים'}, {'title': 'עוף', 'desc': 'עוף טרי'}]},
                            'about': {'title': 'עלינו', 'nav': 'עלינו', 'paragraphs': ['אטליז שכונתי בחיפה']},
                            'contact': {'title': 'צרו קשר', 'nav': 'צור קשר'}}}
        html, _ = R.render(doc, sheet, contract, expect_fp=contract['fingerprint'], direction='warm', year='2026',
                           outline_titles={}, order=['hero', 'services', 'about', 'contact'], windows=())
        text = ' '.join(re.sub(r'<[^>]+>', ' ', html).split())
        self.assertIn('כשרות', text)
        self.assertIn('כשר בהשגחת הרבנות', text)
        self.assertIn('התקשרו להזמנה (ברירת מחדל)', text)
        self.assertIn('המחיר בדלפק (ברירת מחדל)', text)
        self.assertNotIn('משלוחים', text)                      # not given: left off, never filled in

    def test_the_route_report_names_what_the_page_did(self):
        from types import SimpleNamespace
        from omni_prod import site_content as S
        sheet = Fx.fact_sheet(self.prompt('כשר בהשגחת הרבנות', 'טלפון 04-8123456'))
        route = S.Route(S.ROUTE, 'ok', palette='x', direction='warm', contract={'fingerprint': 'fp'},
                        contract_fp='fp', font_pair='p')
        out = S.report(SimpleNamespace(site_route=route, site_sheet=sheet, repairer=None, generator=None))
        self.assertEqual(out['page_fields'], {'keyed_by': 'page_type', 'page_type': 'business', 'found': 'named',
                                              'domain': 'butcher-deli', 'said': {'kashrut': 'כשר בהשגחת הרבנות'},
                                              'not_given': ['address', 'hours', 'delivery'],
                                              'defaults': ['order', 'price']})


if __name__ == '__main__':
    unittest.main()
