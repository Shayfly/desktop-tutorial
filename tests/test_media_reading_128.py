"""Warehouse 128, first slice: input by image and voice becomes a draft the customer sees and approves before any build.

The real ConversationSupervisor, approval flow (gate 1, spec_invalid_reason -- the check build admission runs), Chief
Architect, discovery.requirements_text and ProductArchitect.compile run; only the brief and conversation stores are in
memory (the same stand-ins as tests/test_conversation_os.py). The READING itself is the one thing not run: no model is
called. A fixed answer stands where a vision / speech model would answer -- what this slice guarantees is everything
the platform does with that answer: the skeleton filter, the language rule, the evidence binding, the approval gate and
the customer's sentence when a reading fails. The stored-file evidence on a real PostgreSQL attachment store is in
tests/test_media_reading_128_pg.py.
"""
import hashlib
import json
import os
import re
import struct
import unittest
import zlib
from unittest.mock import patch

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import approval_flow as AF
from omni_prod.intake import media_reading as MR
from omni_prod.product_architect import ProductArchitect
from tests.test_conversation_os import MemoryBriefs


def png(w=4, h=3, shade=b'\x10\x20\x30') -> bytes:
    raw = b''.join(b'\x00' + shade * w for _ in range(h))

    def chunk(t, body):
        return struct.pack('>I', len(body)) + t + body + struct.pack('>I', zlib.crc32(t + body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


WEBM = b'\x1aE\xdf\xa3' + b'\x00' * 60          # the EBML magic of a browser MediaRecorder file


def attachment(data: bytes, n: str = '1', kind: str = 'image') -> dict:
    """The public row of a stored attachment (attachments.public): id, kind and the digest of the stored bytes."""
    return {'id': 'att_' + n * 32, 'kind': kind, 'sha256': hashlib.sha256(data).hexdigest()}


class Fixed:
    """Stands where the vision / speech model answers; returns one fixed answer and counts the calls."""
    name = 'fixed-answer'

    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def read(self, *, purpose, data, mime):
        self.calls += 1
        return self.answer


class Raises:
    name = 'raises'

    def __init__(self, exc):
        self.exc = exc

    def read(self, *, purpose, data, mime):
        raise self.exc


# a handwritten note, as a reader would copy it (Hebrew, line breaks kept)
NOTE = ('מאפיית לחם הבית\n'
        'רחוב הרצל 5, רחובות\n'
        'טלפון 052-7654321\n'
        'פתוחים א׳–ה׳ 07:00–14:00, ו׳ 07:00–12:00\n'
        'לחמי מחמצת, חלות ועוגות. דף נחיתה בלי הרשמה ובלי תשלום.')
REQUEST = ('דף נחיתה למאפייה שלי "לחם הבית" ברחובות. לחמי מחמצת, חלות ועוגות. טלפון 052-7654321, '
           'רחוב הרצל 5, רחובות. שעות: א׳–ה׳ 07:00–14:00. בלי הרשמה, בלי התחברות ובלי תשלום.')
# what a competitor's screenshot holds that must never reach the product: its words, colours, logo, font and name
COMPETITOR_WORDS = ('פיצה נאפולי', 'הפיצה הכי טובה בתל אביב', 'Pizza Napoli', 'napoli-logo.svg', '#d62828',
                    '#1d3557', 'Playfair Display', 'מבצע 1+1 על כל המגשים', 'napoli.co.il')
COMPETITOR_READING = {
    'skeleton': {
        'section_order': ['nav', 'hero', 'services', 'מבצע 1+1 על כל המגשים', 'testimonials',
                          {'name': 'Pizza Napoli', 'kind': 'contact'}, 'contact', 'footer'],
        'hero': {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 2, 'cta_count': 1,
                 'headline': 'הפיצה הכי טובה בתל אביב', 'background': '#d62828'},
        'traits': ['dark_hero', 'sticky_call_button', 'Playfair Display'],
        'palette': {'accent': '#d62828', 'text': '#1d3557'}, 'brand': 'פיצה נאפולי',
    },
    'text': 'פיצה נאפולי — הפיצה הכי טובה בתל אביב. מבצע 1+1 על כל המגשים', 'brand': 'Pizza Napoli',
    'logo': {'file': 'napoli-logo.svg', 'text': 'Pizza Napoli'}, 'colors': ['#d62828', '#1d3557'],
    'fonts': ['Playfair Display'], 'url': 'https://napoli.co.il',
}


def _contains_competitor(blob: str) -> list[str]:
    return [w for w in COMPETITOR_WORDS if w in blob]


class Conversation(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=200)

    def say(self, msg='', answers=None, lang='he'):
        return self.sup.turn(project_id='p', account_id='a', message=msg, answers=answers, lang=lang)

    def to_gate1(self, msg=REQUEST, lang='he'):
        t = self.say(msg, lang=lang)
        for _ in range(12):
            if any(a['type'] == 'approve_spec' for a in t.actions):
                return t
            q = t.questions[0] if t.questions else None
            t = (self.say(answers={q.id: q.options[0].value if q.kind == 'choice' else d.DELEGATE}, lang=lang) if q
                 else self.say('תחליט אתה' if lang == 'he' else 'you decide', lang=lang))
        self.fail('never reached gate 1: ' + t.reply)

    def read(self, purpose, answer, data=None, att=None, lang='he', reader=None):
        data = png() if data is None else data
        return self.sup.read_attachment(project_id='p', account_id='a', attachment=att or attachment(data), data=data,
                                        purpose=purpose, reader=reader or Fixed(answer), lang=lang)

    def approve(self, turn, evidence=None, att=None):
        fp = next(a['draft_fingerprint'] for a in turn.actions if a['type'] == 'approve_reading')
        stored = att or attachment(png())
        return self.sup.approve_reading(project_id='p', account_id='a', draft_fingerprint=fp,
                                        evidence=evidence or (lambda i: stored if i == stored['id'] else {}[i]))

    def messages(self):
        return self.store.messages_for('p', limit=500)

    def fingerprint(self):
        row = self.briefs.latest('p')
        return row.fingerprint if row else None


# --------------------------------------------------------------------------- 128.2: a skeleton only
class CompetitorScreenshotIsASkeletonOnly(Conversation):
    def test_competitor_text_colour_and_logo_never_reach_the_product(self):
        self.to_gate1()
        t = self.read(MR.COMPETITOR, COMPETITOR_READING)
        self.assertEqual(t.intent, 'reading_draft', t.reply)
        draft = t.interpretation['reading_draft']
        self.assertEqual(draft['skeleton'], {
            'section_order': ['nav', 'hero', 'services', 'testimonials', 'contact', 'footer'],
            'hero': {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 2, 'cta_count': 1},
            'traits': ['dark_hero', 'sticky_call_button']})
        self.assertEqual(_contains_competitor(json.dumps(draft, ensure_ascii=False) + t.reply), [])
        self.assertIn('skeleton.hero.headline', draft['dropped'])           # named, never its value
        self.assertIn('1. תפריט עליון 2. פתיח 3. שירותים 4. המלצות 5. יצירת קשר 6. תחתית', t.reply)

        self.approve(t)
        row = self.briefs.latest('p')
        self.assertEqual(row.brief.assets[MR.ASSET]['skeleton'], draft['skeleton'])
        prompt = (row.brief.prompt + '\n' + d.requirements_text(row.brief))[:12000]    # = investor_app._brief_prompt
        self.assertIn('Reference skeleton (structure only', prompt)
        self.assertIn('sections in this order: nav, hero, services, testimonials, contact, footer', prompt)
        contract = ProductArchitect().compile(prompt, project_id='p', contract_version=1)
        everything = '\n'.join([prompt, json.dumps(contract.to_dict(), ensure_ascii=False, default=str),
                                json.dumps(row.brief.to_dict(), ensure_ascii=False),
                                json.dumps(self.messages(), ensure_ascii=False, default=str)])
        self.assertEqual(_contains_competitor(everything), [])

    def test_the_skeleton_is_only_the_closed_vocabulary_of_the_reference_card(self):
        sk, dropped = MR.skeleton_only({'skeleton': {'section_order': ['hero', 'Joe\'s menu', 'faq', 'contact'],
                                                     'hero': {'type': 'centered', 'image_ratio': 'none',
                                                              'headline_lines': 1, 'cta_count': 0, 'font': 'Inter'},
                                                     'notes': 'cosy brand'}, 'title': 'Joe\'s'})
        self.assertEqual(sk['section_order'], ['hero', 'faq', 'contact'])
        self.assertEqual(sorted(dropped), ['skeleton.hero.font', 'skeleton.notes', 'skeleton.section_order[1]', 'title'])
        self.assertNotIn("Joe", json.dumps([sk, dropped]))
        # a value outside the schema fails the reading; the error names the rule, never the rejected value
        for bad in ({'type': 'Joe\'s big banner', 'image_ratio': '4:3', 'headline_lines': 2, 'cta_count': 1},
                    {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 'Joe\'s two lines', 'cta_count': 1}):
            with self.assertRaises(MR.ReadingFailed) as ctx:
                MR.skeleton_only({'skeleton': {'section_order': ['hero', 'faq', 'contact'], 'hero': bad}})
            self.assertEqual(ctx.exception.code, 'invalid_answer')
            self.assertNotIn('Joe', str(ctx.exception))
        # the vocabulary is the reference card schema's, and every word of it has a name in each language
        schema = json.loads(open(os.path.join(os.path.dirname(__file__), '..', 'docs', 'spec',
                                              'reference_card.schema.json'), encoding='utf-8').read())
        self.assertEqual(list(MR.section_vocabulary()),
                         schema['properties']['skeleton']['properties']['section_order']['items']['enum'])
        for lang in MR.LANGS:
            self.assertEqual(set(MR.section_names(lang)), set(MR.section_vocabulary()), lang)

    def test_a_stored_decision_with_text_never_enters_the_brief(self):
        brief = d.start(REQUEST)
        forged = [{'role': 'customer', 'content': 'x', 'interpretation': {'reading_decision': {
            'fingerprint': 'f' * 64, 'decision': 'approved', 'purpose': MR.COMPETITOR,
            'source': {'attachment_id': 'att_' + '1' * 32, 'sha256': '0' * 64},
            'skeleton': {'section_order': ['hero', 'faq', 'contact'],
                         'hero': {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 2, 'cta_count': 1,
                                  'headline': 'הפיצה הכי טובה בתל אביב'}}}}}]
        with self.assertRaises(ValueError):
            MR.collect_skeleton(brief, forged)
        self.assertNotIn(MR.ASSET, brief.assets)


# --------------------------------------------------------------------------- 128.1: seen, then approved, then built
class TheDraftIsSeenAndApprovedBeforeAnyBuild(Conversation):
    def test_the_note_is_shown_before_approval_and_the_brief_is_untouched(self):
        t = self.read(MR.NOTE, {'language': 'he', 'text': NOTE, 'summary': 'A bakery landing page'})
        self.assertEqual(t.intent, 'reading_draft')
        for line in NOTE.splitlines():
            self.assertIn(line, t.reply)                                    # the customer sees every line read
        self.assertIn('טלפון 052-7654321', t.reply)
        self.assertIn('שום דבר לא נבנה לפני שתאשרו', t.reply)
        self.assertNotIn('A bakery landing page', json.dumps(t.interpretation, ensure_ascii=False))
        self.assertEqual([a['type'] for a in t.actions], ['approve_reading', 'discard_reading'])
        self.assertIsNone(self.briefs.latest('p'))                          # nothing entered the request
        self.assertEqual(self.store.plans, {})
        self.assertEqual(len(MR.pending_drafts(self.messages())), 1)

    def test_while_a_draft_waits_gate1_refuses_and_no_build_is_admitted(self):
        t = self.to_gate1()
        fp = t.brief_row.fingerprint
        r = self.sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=fp, lang='he')
        self.assertTrue(AF.spec_approved(self.messages(), fp))
        self.assertIsNone(AF.spec_invalid_reason(self.briefs.latest('p').brief, self.messages(), fp))
        self.assertIn('approve_build', [a['type'] for a in r.actions])
        plans_before = dict(self.store.plans)
        # the customer uploads a note: while its draft waits, the earlier approval does not admit a build
        self.read(MR.NOTE, {'language': 'he', 'text': NOTE})
        self.assertEqual(AF.spec_invalid_reason(self.briefs.latest('p').brief, self.messages(), fp),
                         'reading_draft_pending')                           # what investor_app build admission reads
        # and gate 1 refuses: no approval is recorded, no plan is made, the draft's two buttons come back
        r = self.sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=self.fingerprint(), lang='he')
        self.assertIn('יש טיוטה מקובץ שהעליתם שמחכה להחלטה שלכם', r.reply)
        self.assertEqual([a['type'] for a in r.actions], ['approve_reading', 'discard_reading'])
        self.assertEqual(self.store.plans, plans_before)
        self.assertEqual(self.messages()[-2]['interpretation'].get('reason'), 'reading_draft_pending')
        self.assertNotIn('spec_approved', self.messages()[-2]['interpretation'])

    def test_after_approval_the_note_is_the_request_and_gate1_follows(self):
        t = self.read(MR.NOTE, {'language': 'he', 'text': NOTE})
        self.approve(t)
        row = self.briefs.latest('p')
        self.assertIsNotNone(row)
        self.assertIn('מאפיית לחם הבית', row.brief.prompt)                  # the note IS the request
        self.assertNotIn('📎', row.brief.prompt)                            # the upload label is not their words
        self.assertIn('052-7654321', d.customer_text(row.brief))
        self.assertEqual(MR.pending_drafts(self.messages()), [])
        decision = [m for m in self.messages() if (m['interpretation'] or {}).get('reading_decision')][-1]
        self.assertEqual((decision['role'], decision['content']), ('customer', NOTE))
        # the normal gates follow: gate 1, then a plan only after the spec is approved
        t = self.say('תחליט אתה')
        for _ in range(12):
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            q = t.questions[0] if t.questions else None
            t = self.say(answers={q.id: q.options[0].value if q.kind == 'choice' else d.DELEGATE}) if q \
                else self.say('תחליט אתה')
        r = self.sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=self.fingerprint(), lang='he')
        self.assertIn('approve_build', [a['type'] for a in r.actions], r.reply)

    def test_a_discarded_draft_changes_nothing_and_holds_nothing(self):
        t = self.to_gate1()
        before = self.fingerprint()
        draft = self.read(MR.NOTE, {'language': 'he', 'text': NOTE})
        fp = draft.actions[0]['draft_fingerprint']
        r = self.sup.discard_reading(project_id='p', account_id='a', draft_fingerprint=fp)
        self.assertIn('לא השתמשתי בזה', r.reply)
        self.assertEqual(self.fingerprint(), before)
        self.assertEqual(MR.pending_drafts(self.messages()), [])
        r = self.sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=t.brief_row.fingerprint, lang='he')
        self.assertIn('approve_build', [a['type'] for a in r.actions])

    def test_a_platform_label_is_not_the_customers_words(self):
        # the upload label and the approval label are stored on the customer's side (the conversation shows them
        # there), but nothing reads them as what the customer said: not the facts, not a new brief, not the replay
        t = self.read(MR.COMPETITOR, COMPETITOR_READING)
        self.approve(t)
        shown = [m['content'] for m in self.messages() if m['role'] == 'customer']
        self.assertEqual(shown, ['📎 צילום מסך של אתר אחר', 'אישרתי את הטיוטה'])
        self.assertEqual(d.customer_messages(self.messages()), [])
        self.assertIsNone(self.briefs.latest('p'))

    def test_a_draft_is_decided_once(self):
        t = self.read(MR.NOTE, {'language': 'he', 'text': NOTE})
        self.approve(t)
        again = self.approve(t)
        self.assertEqual(again.intent, 'reading_decided')
        self.assertEqual(len([m for m in self.messages() if (m['interpretation'] or {}).get('reading_decision')]), 1)
        with self.assertRaises(KeyError):
            self.sup.approve_reading(project_id='p', account_id='a', draft_fingerprint='0' * 64, evidence=lambda i: {})

    def test_an_approved_skeleton_before_any_request_joins_the_brief_when_it_is_made(self):
        t = self.read(MR.COMPETITOR, COMPETITOR_READING)
        r = self.approve(t)
        self.assertIn('ספרו לי על העסק שלכם', r.reply)
        self.assertIsNone(self.briefs.latest('p'))
        self.say(REQUEST)
        self.say('תחליט אתה')
        row = self.briefs.latest('p')
        self.assertEqual(row.brief.assets[MR.ASSET]['skeleton']['section_order'],
                         ['nav', 'hero', 'services', 'testimonials', 'contact', 'footer'])
        self.assertNotIn('אישרתי את הטיוטה', row.brief.prompt)
        self.assertEqual(_contains_competitor(row.brief.prompt + d.requirements_text(row.brief)), [])


# --------------------------------------------------------------------------- 128.4: the original file is the evidence
class TheOriginalFileIsTheEvidence(Conversation):
    def test_the_draft_and_the_conversation_name_the_stored_file(self):
        data = png(6, 5)
        att = attachment(data, '7')
        t = self.read(MR.NOTE, {'language': 'he', 'text': NOTE}, data=data, att=att)
        src = t.interpretation['reading_draft']['source']
        self.assertEqual((src['attachment_id'], src['sha256'], src['mime']),
                         (att['id'], hashlib.sha256(data).hexdigest(), 'image/png'))
        upload = [m for m in self.messages() if (m['interpretation'] or {}).get('reading_request')][-1]
        self.assertEqual(upload['role'], 'customer')
        self.assertEqual(upload['interpretation']['attachments'], [{'id': att['id'], 'kind': 'image'}])
        self.assertEqual(upload['interpretation']['reading_request']['sha256'], att['sha256'])

    def test_bytes_that_are_not_the_stored_file_are_not_read(self):
        reader = Fixed({'language': 'he', 'text': NOTE})
        t = self.read(MR.NOTE, None, data=png(), att=attachment(png(5, 5)), reader=reader)
        self.assertEqual(t.intent, 'reading_failed')
        self.assertEqual(t.interpretation['reading_failed']['code'], 'evidence_missing')
        self.assertEqual(reader.calls, 0)
        self.assertEqual(MR.pending_drafts(self.messages()), [])

    def test_a_draft_whose_file_is_gone_cannot_be_approved(self):
        t = self.read(MR.NOTE, {'language': 'he', 'text': NOTE})
        gone = self.approve(t, evidence=lambda i: {}[i])                 # the customer deleted the attachment
        self.assertEqual(gone.intent, 'reading_failed')
        self.assertIn('הקובץ המקורי כבר לא שמור בפרויקט', gone.reply)
        self.assertIsNone(self.briefs.latest('p'))
        self.assertEqual(len(MR.pending_drafts(self.messages())), 1)       # still undecided: still holds every build
        replaced = self.approve(t, evidence=lambda i: {**attachment(png()), 'sha256': '9' * 64})
        self.assertEqual(replaced.intent, 'reading_failed')                 # another file under the same id
        self.assertIsNone(self.briefs.latest('p'))


# --------------------------------------------------------------------------- 128.5: a failure is a sentence
_TECHNICAL = re.compile(r'error|exception|traceback|http|null|none|json|[{}_<>]|\b5\d\d\b|gateway|model', re.I)


class AFailedReadingIsASentenceWithTheNextAction(Conversation):
    def test_production_today_says_what_to_do_instead(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_MEDIA_READER', None)
            reader = MR.reader_from_env()
        t = self.read(MR.NOTE, None, reader=reader)
        self.assertEqual(t.intent, 'reading_failed')
        self.assertEqual(t.reply, 'שמרתי את הפתק בפרויקט, אבל עדיין אין לי קריאה אוטומטית של קבצים כאלה. כתבו לי '
                                  'במשפט או שניים מה כתוב בו: שם העסק, טלפון, כתובת ושעות, ונמשיך משם.')
        self.assertEqual(t.interpretation['reading_failed']['code'], 'not_connected')
        self.assertIsNone(self.briefs.latest('p'))
        self.assertEqual(MR.pending_drafts(self.messages()), [])
        t = self.read(MR.COMPETITOR, None, reader=reader, lang='en')
        self.assertIn('tell me which parts you liked and in what order', t.reply)

    def test_a_provider_error_reaches_the_log_and_never_the_customer(self):
        boom = RuntimeError('ModelGatewayError: all model routes failed: HTTP 503 from api.example (route vision_1)')
        with self.assertLogs('omni_prod.intake.media_reading', 'ERROR') as logs:
            t = self.read(MR.COMPETITOR, None, reader=Raises(boom))
        self.assertEqual(t.intent, 'reading_failed')
        self.assertIsNone(_TECHNICAL.search(t.reply), t.reply)
        self.assertIn('צלמו את המסך שוב', t.reply)                          # the next action
        self.assertIn('503', ' '.join(logs.output))                         # loud for us
        self.assertIn('503', t.interpretation['reading_failed']['detail'])  # and in the stored evidence

    def test_every_failure_in_every_language_is_a_plain_sentence(self):
        for lang in MR.LANGS:
            for code in MR.FAILURES:
                for purpose in MR.PURPOSES:
                    s = MR.failure_sentence(code, purpose, lang)
                    self.assertIsNone(_TECHNICAL.search(s), (lang, code, purpose, s))
                    self.assertNotIn(code, s)
                    self.assertTrue(s.endswith('.'), s)
                    if lang != 'en':                                        # the customer's script, nothing else
                        self.assertIsNone(re.search(r'[A-Za-z]', s), (lang, code, purpose, s))
                    self.assertIn(MR._INSTEAD[lang][purpose], s)           # every failure says what to do next

    def test_unknown_values_raise(self):
        with self.assertRaises(ValueError):
            MR.check_purpose('selfie')
        with self.assertRaises(ValueError):
            MR.failure_sentence('not_connected', MR.NOTE, 'fr')
        with self.assertRaises(ValueError):
            MR.ReadingFailed('timeout')
        with patch.dict(os.environ, {'OMNI_MEDIA_READER': 'on'}):
            with self.assertRaises(ValueError):
                MR.reader_from_env()
        with patch.dict(os.environ, {'OMNI_MEDIA_READER': 'gateway'}):
            with self.assertRaises(ValueError):
                MR.reader_from_env(gateway=None)                            # the API host has no gateway
        with self.assertRaises(ValueError):
            self.read('selfie', {})


# --------------------------------------------------------------------------- 128.3: the speaker's language (our side)
TRANSCRIPT = ('שלום, אני רוצה אתר לסטודיו ליוגה שלי בחיפה, "נשימה". טלפון 054-1112233. '
              'שיעורים בבוקר ובערב, בלי הרשמה ובלי תשלום באתר.')


class ARecordingDraftIsInTheSpeakersLanguage(Conversation):
    def test_the_draft_is_the_transcript_never_a_translation(self):
        answer = {'language': 'he', 'transcript': TRANSCRIPT,
                  'brief': 'A website for a yoga studio in Haifa called Breath.'}
        t = self.read(MR.VOICE, answer, data=WEBM, att=attachment(WEBM, '3', 'voice'), lang='en')
        draft = t.interpretation['reading_draft']
        self.assertEqual((draft['language'], draft['text'], draft['source']['mime']), ('he', TRANSCRIPT, 'audio/webm'))
        self.assertEqual(t.language, 'he')                                   # the conversation said 'en'
        self.assertIn('זה מה ששמעתי בהקלטה', t.reply)
        self.assertNotIn('yoga studio', json.dumps(t.interpretation, ensure_ascii=False) + t.reply)
        self.assertIn('brief', draft['dropped'])
        self.approve(t, att=attachment(WEBM, '3', 'voice'))
        row = self.briefs.latest('p')
        self.assertEqual(row.brief.prompt, TRANSCRIPT)                       # the brief is the speaker's own words
        self.assertEqual(MR.script_language(row.brief.prompt), 'he')

    def test_a_reader_that_translated_the_speaker_fails_the_reading(self):
        t = self.read(MR.VOICE, {'language': 'he', 'transcript': 'Hello, I want a website for my yoga studio.'},
                      data=WEBM, att=attachment(WEBM, '3', 'voice'))
        self.assertEqual(t.intent, 'reading_failed')
        self.assertEqual(t.interpretation['reading_failed']['code'], 'language_mismatch')
        self.assertIn('לא הצלחתי לשמוע את ההקלטה בשפה שלכם', t.reply)
        self.assertEqual(MR.pending_drafts(self.messages()), [])

    def test_a_picture_is_not_a_recording(self):
        t = self.read(MR.VOICE, {'language': 'he', 'transcript': TRANSCRIPT})
        self.assertEqual(t.interpretation['reading_failed']['code'], 'unsupported_type')
        self.assertIn('העלו הקלטה קולית', t.reply)


# --------------------------------------------------------------------------- the model behind the interface
class TheGatewayReaderIsWiredNotCalled(unittest.TestCase):
    def test_an_image_goes_to_a_vision_call_and_audio_has_no_route(self):
        calls = []

        class Recording:
            def complete_json(self, **kw):
                calls.append(kw)
                return {'skeleton': {'section_order': ['hero', 'faq', 'contact'],
                                     'hero': {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 2,
                                              'cta_count': 1}}}
        reader = MR.GatewayReader(Recording())
        data = png()
        answer = MR.read(reader, MR.COMPETITOR, data, 'image/png')
        self.assertEqual(MR.skeleton_only(answer)[1], [])
        self.assertEqual(calls[0]['images'], (data,))                        # vision_models routes only image calls
        self.assertEqual(calls[0]['task'], 'review')
        self.assertIn('never any text, name, colour, logo, picture or font', calls[0]['system'])
        self.assertIn(', '.join(MR.section_vocabulary()), calls[0]['system'])
        with self.assertRaises(MR.ReadingFailed) as ctx:
            MR.read(reader, MR.VOICE, WEBM, 'audio/webm')
        self.assertEqual(ctx.exception.code, 'not_connected')
        self.assertEqual(len(calls), 1)                                      # audio never reached the gateway


_HAS_FASTAPI = __import__('importlib').util.find_spec('fastapi') is not None


@unittest.skipUnless(_HAS_FASTAPI, 'fastapi is required to import the app')
class BuildAdmissionRefusesWhileADraftWaits(Conversation):
    """The build route's own admission (investor_app._bind_execution_plan, which /approvals calls before any build) on
    the conversation the real supervisor wrote. Only the two stores are the in-memory ones (as in
    tests/test_venice_live_wiring.ServerGate); the admission code, the approval flow and the verified plan are real."""

    def bind(self, fingerprint):
        from omni_prod import investor_app as IA
        with patch('omni_prod.conversation.store.schema_ready', return_value=True), \
                patch.object(IA, '_conversation_store', return_value=self.store), \
                patch.object(IA, '_brief_repo', return_value=self.briefs):
            return IA._bind_execution_plan('p', fingerprint)

    def test_an_approved_spec_admits_no_build_while_a_draft_waits(self):
        from omni_prod import investor_app as IA
        self.to_gate1()
        r = self.sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=self.fingerprint(), lang='he')
        self.assertIn('approve_build', [a['type'] for a in r.actions], r.reply)
        fp = self.fingerprint()
        self.assertEqual(self.bind(fp)['status'], 'APPROVED')               # positive control: both gates passed
        draft = self.read(MR.NOTE, {'language': 'he', 'text': NOTE})        # the customer uploads a note
        with self.assertRaises(IA.HTTPException) as ctx:
            self.bind(fp)
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail['error'], ctx.exception.detail['reason']),
                         (409, 'brief_stale', 'reading_draft_pending'))
        self.sup.discard_reading(project_id='p', account_id='a',
                                 draft_fingerprint=draft.actions[0]['draft_fingerprint'])
        self.assertEqual(self.bind(fp)['status'], 'APPROVED')               # decided: the same approval admits again


APP_JS = os.path.join(os.path.dirname(__file__), '..', 'omni_prod', 'assets', 'app.js')


@unittest.skipUnless(__import__('shutil').which('node'), 'node runs app.js')
class TheCustomerCanAnswerTheDraftInTheApp(unittest.TestCase):
    """app.js actionButtons, run in node: the draft's two buttons post to the reading routes by the draft's
    fingerprint. Without them a draft would hold every build with no way for the customer to decide."""

    def test_the_two_buttons_post_the_decision_by_fingerprint(self):
        import subprocess
        src = open(APP_JS, encoding='utf-8').read()

        def grab(pattern):
            return re.search(pattern, src, re.S).group()
        fp = 'a' * 64
        code = '\n'.join([
            'const localStorage = { getItem: () => null };',
            src[src.index('const T ='):src.index('\nconst $ = id')],
            grab(r'\nconst t = key => [^\n]*'), grab(r'\nconst pid = [^\n]*'), grab(r'\nconst readingPath = [^\n]*'),
            grab(r'function actionButtons\(.*?\n\}'),
            'function h(tag, attrs, ...kids) { return { tag, attrs, kids }; }',
            'const calls = []; function sendChat(body, shown, path) { calls.push({ body, shown, path: path() }); }',
            "S.lang = 'he'; S.projectId = 'prj_x';",
            f"const node = actionButtons([{{ type: 'approve_reading', draft_fingerprint: '{fp}', purpose: 'handwritten_note' }},"
            f" {{ type: 'discard_reading', draft_fingerprint: '{fp}' }}]);",
            'const buttons = node.kids[0]; buttons.forEach(b => b.attrs.onclick());',
            'console.log(JSON.stringify({ labels: buttons.map(b => b.kids[0]), calls }));'])
        out = json.loads(subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(out['labels'], ['נכון, להשתמש בזה', 'לא נכון, לבטל'])
        self.assertEqual([c['path'] for c in out['calls']],
                         [f'/api/v28/projects/prj_x/readings/{fp}/approve', f'/api/v28/projects/prj_x/readings/{fp}/discard'])
        self.assertEqual([c['shown'] for c in out['calls']], out['labels'])


@unittest.skipUnless(_HAS_FASTAPI, 'fastapi is required to import the app')
class TheRoutes(unittest.TestCase):
    def test_the_routes_exist_and_refuse_before_touching_anything(self):
        from fastapi.testclient import TestClient
        from omni_prod import investor_app as IA
        paths = {(r.path, tuple(sorted(r.methods))) for r in IA.app.routes if hasattr(r, 'methods')}
        for path in ('/api/v28/projects/{project_id}/attachments/{attachment_id}/reading',
                     '/api/v28/projects/{project_id}/readings/{draft_fingerprint}/approve',
                     '/api/v28/projects/{project_id}/readings/{draft_fingerprint}/discard'):
            self.assertIn((path, ('POST',)), paths)
        client = TestClient(IA.app)
        url = '/api/v28/projects/prj_x/attachments/att_' + '1' * 32 + '/reading'
        # a voice recording is refused here: the attachment store holds images only (migration 038)
        for purpose in ('selfie', MR.VOICE):
            self.assertEqual(client.post(url, json={'purpose': purpose}).status_code, 422, purpose)
        r = client.post('/api/v28/projects/prj_x/readings/not-a-fingerprint/approve', json={})
        self.assertEqual((r.status_code, r.json()['detail']['error']), (422, 'bad_draft'))
        self.assertEqual(client.post(url, json={'purpose': MR.NOTE}).status_code, 401)      # the owner only


if __name__ == '__main__':
    unittest.main()
