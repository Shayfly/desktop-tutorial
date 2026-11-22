"""Input by image and voice (warehouse 128, first slice): a reading of the customer's file becomes a DRAFT the customer
sees and approves before anything is built.

Three purposes, and an unknown one raises:
  handwritten_note       a photo of the customer's own note -> the note's text, verbatim, in its own language
  competitor_screenshot  a screenshot of another site     -> a SKELETON only: sections, order, hierarchy
  voice_recording        the customer speaking            -> the transcript, verbatim, in the speaker's language

What this module guarantees, with no model involved:
  * 128.2 -- `skeleton_only` keeps exactly the closed-vocabulary skeleton of docs/spec/reference_card.schema.json
    (section_order, hero, traits; enums and bounded integers, no free-text field) and drops everything else the reading
    returns -- text, names, colours, logo, fonts, images -- recording only the NAMES of what it dropped, never a value.
    What survives is validated against the schema; a value outside it fails the reading.
  * 128.3 -- the draft of a note or a recording IS the text read, in the language it is written or spoken in (the
    script decides; a declared language that disagrees with the script fails the reading). A translation or summary
    the reader adds is never used.
  * 128.4 -- every draft names its source: the attachment id and the sha256 of the bytes that were read, and the
    approval re-checks that the stored file still exists with that digest.
  * 128.5 -- a reading that fails returns one sentence in the customer's language with the next action
    (`failure_sentence`); the technical detail goes to the log and the stored evidence, never to the customer.
  * 128.1 (the gate) -- a draft is stored in an ASSISTANT message: it is not the customer's words until approved, so
    nothing reads it into the brief (discovery.note_customer_texts reads customer messages only). While a draft awaits
    the customer's decision no spec approval stands (approval_flow.spec_invalid_reason) and gate 1 refuses.

What it does NOT do: read anything. The reader is an interface (`Reader`). `NotConnectedReader` (the default,
OMNI_MEDIA_READER=off) fails every reading with 'not_connected' -- the customer is told to type the details instead.
`GatewayReader` sends an image through the routed model gateway (complete_json with images, vision models only) but is
not wired on the API host: paid calls run on the worker with a reservation, and that route is not built yet. Audio has
no route at all: the gateway takes no audio input and no speech-to-text provider is connected.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from functools import lru_cache

SCHEMA = '148ai.reading_draft/1'
NOTE, COMPETITOR, VOICE = 'handwritten_note', 'competitor_screenshot', 'voice_recording'
PURPOSES = (NOTE, COMPETITOR, VOICE)
TEXT_PURPOSES = (NOTE, VOICE)              # the draft is the customer's own words
IMAGE_MIMES = ('image/png', 'image/jpeg', 'image/webp')
AUDIO_MIMES = ('audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/wav', 'audio/mp4')
MIMES = {NOTE: IMAGE_MIMES, COMPETITOR: IMAGE_MIMES, VOICE: AUDIO_MIMES}
LANGS = ('he', 'en', 'ar')
MAX_TEXT = {NOTE: 4000, VOICE: 8000}
SKELETON_KEYS = ('section_order', 'hero', 'traits')
REQUIRED_SKELETON = ('section_order', 'hero')
FAILURES = ('not_connected', 'unreadable', 'empty', 'invalid_answer', 'language_mismatch', 'unsupported_type',
            'evidence_missing')
READER_MODES = ('off', 'gateway')
_LOG = logging.getLogger(__name__)


class ReadingFailed(Exception):
    """A reading that did not produce a draft. `code` is one of FAILURES (the customer sentence); `detail` is for the
    log and the stored evidence only."""

    def __init__(self, code: str, detail: str = ''):
        if code not in FAILURES:
            raise ValueError(f'unknown reading failure {code!r}; one of {FAILURES}')
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code, self.detail = code, detail


def check_purpose(purpose: str) -> str:
    if purpose not in PURPOSES:
        raise ValueError(f'unknown reading purpose {purpose!r}; one of {PURPOSES}')
    return purpose


def check_lang(lang: str) -> str:
    if lang not in LANGS:
        raise ValueError(f'no customer texts in language {lang!r}; one of {LANGS}')
    return lang


# ------------------------------------------------------------------ the bytes

def sniff_audio(data: bytes) -> str | None:
    """The audio type from the file's own bytes (never the declared type or name), like attachments.sniff."""
    if data[:4] == b'\x1aE\xdf\xa3':
        return 'audio/webm'
    if data[:4] == b'OggS':
        return 'audio/ogg'
    if data[:3] == b'ID3' or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return 'audio/mpeg'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        return 'audio/wav'
    if len(data) >= 12 and data[4:8] == b'ftyp':
        return 'audio/mp4'
    return None


def source_of(purpose: str, attachment: dict, data: bytes) -> dict:
    """The evidence a draft is bound to: the stored attachment's id and digest, checked against the bytes read."""
    check_purpose(purpose)
    from ..attachments import sniff
    mime = sniff(data or b'') or sniff_audio(data or b'')
    if mime not in MIMES[purpose]:
        raise ReadingFailed('unsupported_type', f'{purpose} needs one of {MIMES[purpose]}, the bytes are {mime}')
    digest = hashlib.sha256(data).hexdigest()
    att_id, stored = str((attachment or {}).get('id') or ''), str((attachment or {}).get('sha256') or '')
    if not re.fullmatch(r'att_[0-9a-f]{32}', att_id) or stored != digest:
        raise ReadingFailed('evidence_missing', f'the bytes read are not the stored attachment {att_id!r}')
    return {'attachment_id': att_id, 'sha256': digest, 'mime': mime, 'kind': str(attachment.get('kind') or '')}


# ------------------------------------------------------------------ the skeleton filter (128.2)

@lru_cache(maxsize=1)
def _skeleton_schema() -> dict:
    """The skeleton part of the reference card schema -- the same closed vocabulary the reference scout stores."""
    from ..reference_store import CARD_SCHEMA
    card = json.loads(CARD_SCHEMA.read_text(encoding='utf-8'))
    props = card['properties']['skeleton']['properties']
    return {'type': 'object', 'additionalProperties': False, 'required': list(REQUIRED_SKELETON),
            'properties': {k: props[k] for k in SKELETON_KEYS}}


def section_vocabulary() -> tuple[str, ...]:
    return tuple(_skeleton_schema()['properties']['section_order']['items']['enum'])


def trait_vocabulary() -> tuple[str, ...]:
    return tuple(_skeleton_schema()['properties']['traits']['items']['enum'])


def hero_keys() -> tuple[str, ...]:
    return tuple(_skeleton_schema()['properties']['hero']['properties'])


def _vocab_list(value, vocab, where: str, dropped: list) -> list:
    if not isinstance(value, list):
        raise ReadingFailed('invalid_answer', f'{where} is not a list')
    kept = []
    for i, item in enumerate(value):
        if isinstance(item, str) and item in vocab:
            kept.append(item)
        else:
            dropped.append(f'{where}[{i}]')          # the position only: the value may be the competitor's words
    return kept


def skeleton_only(answer) -> tuple[dict, list[str]]:
    """(the skeleton, the names of everything dropped). Keeps only section_order / hero / traits values from the closed
    vocabulary; every other key, at every level, is dropped and named. The result must satisfy the schema."""
    if not isinstance(answer, dict):
        raise ReadingFailed('invalid_answer', 'the reading is not a JSON object')
    if answer.get('unreadable') is True:
        raise ReadingFailed('unreadable', 'the reader could not read the screenshot')
    dropped = sorted(str(k) for k in answer if k != 'skeleton')
    raw = answer.get('skeleton')
    if not isinstance(raw, dict):
        raise ReadingFailed('invalid_answer', 'the reading has no skeleton object')
    out: dict = {}
    for key in sorted(raw, key=str):
        value = raw[key]
        if key == 'section_order':
            out[key] = _vocab_list(value, section_vocabulary(), 'skeleton.section_order', dropped)
        elif key == 'traits':
            out[key] = list(dict.fromkeys(_vocab_list(value, trait_vocabulary(), 'skeleton.traits', dropped)))
        elif key == 'hero':
            if not isinstance(value, dict):
                raise ReadingFailed('invalid_answer', 'skeleton.hero is not an object')
            out[key] = {k: value[k] for k in hero_keys() if k in value}
            dropped += [f'skeleton.hero.{k}' for k in sorted(value, key=str) if k not in hero_keys()]
        else:
            dropped.append(f'skeleton.{key}')
    from jsonschema import Draft202012Validator
    errors = sorted(Draft202012Validator(_skeleton_schema()).iter_errors(out), key=lambda e: list(e.absolute_path))
    if errors:
        where = '/'.join(str(p) for p in errors[0].absolute_path) or '(root)'
        # the message names the schema rule, never the rejected value (it may be the competitor's text)
        raise ReadingFailed('invalid_answer', f'skeleton outside the schema at {where} ({errors[0].validator})')
    return out, dropped


# ------------------------------------------------------------------ the text of a note or a recording (128.1, 128.3)

def script_language(text: str) -> str | None:
    """he / ar / en by the letters' script; None when the text has no letters (a phone number alone)."""
    counts = {'he': len(re.findall(r'[֐-׿]', text or '')),
              'ar': len(re.findall(r'[؀-ۿ]', text or '')),
              'en': len(re.findall(r'[A-Za-z]', text or ''))}
    best = max(counts, key=counts.get)
    return best if counts[best] else None


def _text_reading(purpose: str, answer) -> tuple[str, str, list[str]]:
    if not isinstance(answer, dict):
        raise ReadingFailed('invalid_answer', 'the reading is not a JSON object')
    if answer.get('unreadable') is True:
        raise ReadingFailed('unreadable', 'the reader could not read the file')
    field_ = 'text' if purpose == NOTE else 'transcript'
    text = answer.get(field_)
    if not isinstance(text, str):
        raise ReadingFailed('invalid_answer', f'the reading has no {field_} string')
    text = text.strip()
    if not text:
        raise ReadingFailed('empty', f'the {field_} is empty')
    if len(text) > MAX_TEXT[purpose]:
        raise ReadingFailed('invalid_answer', f'the {field_} is longer than {MAX_TEXT[purpose]} characters')
    declared = answer.get('language')
    if declared not in LANGS:
        raise ReadingFailed('invalid_answer', f'the reading declares no supported language ({LANGS})')
    written = script_language(text)
    if written is not None and written != declared:
        # a reader that says "Hebrew" and hands back English translated the customer: the reading failed
        raise ReadingFailed('language_mismatch', f'declared {declared}, the {field_} is written in {written}')
    # anything else the reader returned (a summary, a translation, "facts") is not the customer's words: never used
    return text, written or declared, sorted(str(k) for k in answer if k not in (field_, 'language'))


_FACT_KEYS = ('phone', 'email', 'address', 'hours')


def _facts(text: str) -> list[dict]:
    from ..fact_canon import build_canon
    seen, out = set(), []
    for f in build_canon(text).facts:
        if f.key in _FACT_KEYS and (f.key, f.source_ref) not in seen:
            seen.add((f.key, f.source_ref))
            out.append({'key': f.key, 'span': f.source_ref})
    return out


# ------------------------------------------------------------------ the draft

def _fingerprint(draft: dict) -> str:
    body = {k: v for k, v in draft.items() if k != 'fingerprint'}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                          .encode('utf-8')).hexdigest()


def draft_from_reading(purpose: str, answer, *, source: dict, lang: str, reader: str) -> dict:
    """The draft the customer sees. `lang` is the conversation's language (the skeleton is described in it); a note
    or a recording is described in the language it was written or spoken in."""
    check_purpose(purpose)
    check_lang(lang)
    answer_sha = hashlib.sha256(json.dumps(answer, sort_keys=True, ensure_ascii=False, default=str)
                                .encode('utf-8')).hexdigest()
    draft = {'schema': SCHEMA, 'purpose': purpose, 'source': dict(source), 'reader': str(reader)[:80],
             'answer_sha256': answer_sha}
    if purpose == COMPETITOR:
        skeleton, dropped = skeleton_only(answer)
        draft.update(language=lang, skeleton=skeleton, dropped=dropped)
    else:
        text, language, dropped = _text_reading(purpose, answer)
        draft.update(language=language, text=text, facts=_facts(text), dropped=dropped)
    draft['fingerprint'] = _fingerprint(draft)
    return draft


def checked_draft(draft) -> dict:
    """A stored draft, re-checked before it is used: its fingerprint, its source, and -- for a skeleton -- the filter
    again (a stored row is data; nothing forged into it reaches the brief)."""
    if not isinstance(draft, dict) or draft.get('schema') != SCHEMA or draft.get('fingerprint') != _fingerprint(draft):
        raise ValueError('the stored reading draft does not match its fingerprint')
    check_purpose(draft['purpose'])
    src = draft.get('source') or {}
    if not (re.fullmatch(r'att_[0-9a-f]{32}', str(src.get('attachment_id') or ''))
            and re.fullmatch(r'[0-9a-f]{64}', str(src.get('sha256') or ''))):
        raise ValueError('the stored reading draft names no attachment evidence')
    if draft['purpose'] == COMPETITOR:
        try:
            skeleton, dropped = skeleton_only({'skeleton': draft.get('skeleton')})
        except ReadingFailed as exc:
            raise ValueError(f'the stored skeleton is outside the schema: {exc.detail}') from exc
        if skeleton != draft.get('skeleton') or dropped:
            raise ValueError('the stored skeleton holds more than the closed vocabulary')
    return draft


def actions(draft: dict) -> list[dict]:
    return [{'type': 'approve_reading', 'draft_fingerprint': draft['fingerprint'], 'purpose': draft['purpose']},
            {'type': 'discard_reading', 'draft_fingerprint': draft['fingerprint']}]


# ------------------------------------------------------------------ the draft in the conversation log

def drafts(messages) -> list[dict]:
    return [m['interpretation']['reading_draft'] for m in messages or ()
            if m.get('role') == 'assistant' and isinstance((m.get('interpretation') or {}).get('reading_draft'), dict)]


def decisions(messages) -> dict[str, dict]:
    """{draft fingerprint: the customer's decision} -- only the customer's own messages decide."""
    out = {}
    for m in messages or ():
        dec = (m.get('interpretation') or {}).get('reading_decision')
        if m.get('role') == 'customer' and isinstance(dec, dict) and dec.get('decision') in ('approved', 'discarded'):
            out[str(dec.get('fingerprint'))] = dec
    return out


def pending_drafts(messages) -> list[dict]:
    decided = decisions(messages)
    return [dr for dr in drafts(messages) if dr.get('fingerprint') not in decided]


def find_draft(messages, fingerprint: str) -> dict | None:
    return next((dr for dr in reversed(drafts(messages)) if dr.get('fingerprint') == fingerprint), None)


ASSET = 'reference_skeleton'


def collect_skeleton(brief, messages) -> bool:
    """The skeleton the customer approved last is the brief's (idempotent, like discovery.note_customer_texts).
    Returns whether the brief changed. Re-validated: a stored decision is data."""
    approved = [dec for dec in decisions(messages).values()
                if dec['decision'] == 'approved' and dec.get('purpose') == COMPETITOR]
    if not approved:
        return False
    dec = approved[-1]
    try:
        skeleton, dropped = skeleton_only({'skeleton': dec.get('skeleton')})
    except ReadingFailed as exc:
        raise ValueError(f'an approved skeleton is outside the schema: {exc.detail}') from exc
    if dropped:
        raise ValueError('an approved skeleton holds more than the closed vocabulary')
    src = dec.get('source') or {}
    value = {'skeleton': skeleton, 'draft': str(dec.get('fingerprint')),
             'source': {'attachment_id': str(src.get('attachment_id')), 'sha256': str(src.get('sha256'))}}
    if brief.assets.get(ASSET) == value:
        return False
    brief.assets[ASSET] = value
    return True


def requirements_line(brief) -> str | None:
    """The binding brief line of an approved skeleton (English, for the models; vocabulary words only)."""
    ref = brief.assets.get(ASSET)
    if not ref:
        return None
    sk, src = ref['skeleton'], ref['source']
    hero = sk.get('hero') or {}
    parts = [f'sections in this order: {", ".join(sk["section_order"])}']
    if hero:
        parts.append('hero: ' + ', '.join(f'{k} {hero[k]}' for k in hero_keys() if k in hero))
    if sk.get('traits'):
        parts.append('traits: ' + ', '.join(sk['traits']))
    return (f'Reference skeleton (structure only, from a screenshot of another site the customer uploaded; attachment '
            f'{src["attachment_id"]}; sha256={src["sha256"]}): ' + '; '.join(parts) + '. Follow this order and '
            'hierarchy only. Nothing else from that screenshot is given: never imitate its wording, colours, '
            'brand marks, pictures or name.')


# ------------------------------------------------------------------ what the customer reads

_SECTION_NAMES = {
    'he': {'nav': 'תפריט עליון', 'hero': 'פתיח', 'trust': 'סימני אמון', 'products': 'מוצרים', 'services': 'שירותים',
           'story': 'הסיפור שלנו', 'gallery': 'גלריה', 'hours': 'שעות פתיחה', 'location': 'כתובת ומפה',
           'contact': 'יצירת קשר', 'cta': 'קריאה לפעולה', 'testimonials': 'המלצות', 'faq': 'שאלות נפוצות',
           'pricing_table': 'מחירון', 'team': 'הצוות', 'footer': 'תחתית'},
    'en': {'nav': 'top menu', 'hero': 'opening', 'trust': 'trust signs', 'products': 'products', 'services': 'services',
           'story': 'our story', 'gallery': 'gallery', 'hours': 'opening hours', 'location': 'address and map',
           'contact': 'contact', 'cta': 'call to action', 'testimonials': 'testimonials', 'faq': 'questions and answers',
           'pricing_table': 'price list', 'team': 'team', 'footer': 'footer'},
    'ar': {'nav': 'القائمة العلوية', 'hero': 'الافتتاحية', 'trust': 'علامات الثقة', 'products': 'المنتجات',
           'services': 'الخدمات', 'story': 'قصتنا', 'gallery': 'معرض الصور', 'hours': 'ساعات العمل',
           'location': 'العنوان والخريطة', 'contact': 'التواصل', 'cta': 'دعوة إلى إجراء', 'testimonials': 'التوصيات',
           'faq': 'أسئلة شائعة', 'pricing_table': 'قائمة الأسعار', 'team': 'الفريق', 'footer': 'التذييل'},
}
_FACT_NAMES = {'he': {'phone': 'טלפון', 'email': 'דוא״ל', 'address': 'כתובת', 'hours': 'שעות'},
               'en': {'phone': 'phone', 'email': 'e-mail', 'address': 'address', 'hours': 'hours'},
               'ar': {'phone': 'الهاتف', 'email': 'البريد الإلكتروني', 'address': 'العنوان', 'hours': 'الساعات'}}
_WHAT = {'he': {NOTE: 'הפתק', COMPETITOR: 'צילום המסך', VOICE: 'ההקלטה'},
         'en': {NOTE: 'the note', COMPETITOR: 'the screenshot', VOICE: 'the recording'},
         'ar': {NOTE: 'الملاحظة', COMPETITOR: 'لقطة الشاشة', VOICE: 'التسجيل'}}
# what to type instead, per purpose (the next action of every failure)
_INSTEAD = {
    'he': {NOTE: 'כתבו לי במשפט או שניים מה כתוב בו: שם העסק, טלפון, כתובת ושעות',
           COMPETITOR: 'כתבו לי אילו חלקים אהבתם בו ובאיזה סדר, למשל: פתיח, שירותים, המלצות, יצירת קשר',
           VOICE: 'כתבו לי במשפט או שניים את מה שאמרתם'},
    'en': {NOTE: 'type what it says in a sentence or two: the business name, phone, address and hours',
           COMPETITOR: 'tell me which parts you liked and in what order, for example: opening, services, '
                       'testimonials, contact',
           VOICE: 'type what you said in a sentence or two'},
    'ar': {NOTE: 'اكتبوا لي في جملة أو جملتين ما كُتب فيها: اسم المصلحة والهاتف والعنوان والساعات',
           COMPETITOR: 'اكتبوا لي الأجزاء التي أعجبتكم وبأي ترتيب، مثلًا: الافتتاحية، الخدمات، التوصيات، التواصل',
           VOICE: 'اكتبوا لي في جملة أو جملتين ما قلتموه'},
}
_UPLOAD = {'he': {NOTE: 'העלו תמונה של הפתק', COMPETITOR: 'העלו צילום מסך של האתר', VOICE: 'העלו הקלטה קולית'},
           'en': {NOTE: 'Upload a picture of the note', COMPETITOR: 'Upload a screenshot of the site',
                  VOICE: 'Upload a voice recording'},
           'ar': {NOTE: 'ارفعوا صورة للملاحظة', COMPETITOR: 'ارفعوا لقطة شاشة للموقع', VOICE: 'ارفعوا تسجيلًا صوتيًا'}}
_READ = {'he': {NOTE: 'לקרוא את הפתק', COMPETITOR: 'לקרוא את צילום המסך', VOICE: 'לשמוע את ההקלטה'},
         'en': {NOTE: 'read the note', COMPETITOR: 'read the screenshot', VOICE: 'hear the recording'},
         'ar': {NOTE: 'قراءة الملاحظة', COMPETITOR: 'قراءة لقطة الشاشة', VOICE: 'سماع التسجيل'}}
_RETRY = {'he': {NOTE: 'צלמו את הפתק שוב מקרוב ובאור טוב', COMPETITOR: 'צלמו את המסך שוב',
                 VOICE: 'הקליטו שוב במקום שקט'},
          'en': {NOTE: 'Take the picture again, closer and in good light', COMPETITOR: 'Take the screenshot again',
                 VOICE: 'Record again somewhere quiet'},
          'ar': {NOTE: 'صوّروا الملاحظة مرة أخرى عن قرب وفي إضاءة جيدة', COMPETITOR: 'التقطوا لقطة الشاشة مرة أخرى',
                 VOICE: 'سجّلوا مرة أخرى في مكان هادئ'}}
_FAILED = {
    'he': {'not_connected': 'שמרתי את {what} בפרויקט, אבל עדיין אין לי קריאה אוטומטית של קבצים כאלה. {instead}, ונמשיך משם.',
           'unreadable': 'לא הצלחתי {read}. {retry}, או {instead}.',
           'empty': 'לא מצאתי כלום ב{what_in}. בדקו שהעליתם את הקובץ הנכון, או {instead}.',
           'invalid_answer': 'לא הצלחתי {read} כמו שצריך. נסו שוב, או {instead}.',
           'language_mismatch': 'לא הצלחתי {read} בשפה שלכם. נסו שוב, או {instead}.',
           'unsupported_type': 'הקובץ הזה לא מתאים כאן. {upload}, או {instead}.',
           'evidence_missing': 'הקובץ המקורי כבר לא שמור בפרויקט, ולכן אי אפשר להשתמש בו. העלו אותו שוב, או {instead}.'},
    'en': {'not_connected': 'I saved {what} in the project, but I cannot read files like this automatically yet. '
                            'Please {instead}, and we will go on from there.',
           'unreadable': 'I could not {read}. {retry}, or {instead}.',
           'empty': 'I found nothing in {what}. Check that you uploaded the right file, or {instead}.',
           'invalid_answer': 'I could not {read} properly. Try again, or {instead}.',
           'language_mismatch': 'I could not {read} in your language. Try again, or {instead}.',
           'unsupported_type': 'This file does not fit here. {upload}, or {instead}.',
           'evidence_missing': 'The original file is no longer saved in the project, so it cannot be used. Upload it '
                               'again, or {instead}.'},
    'ar': {'not_connected': 'حفظتُ {what} في المشروع، لكن لا أستطيع بعد قراءة ملفات كهذه تلقائيًا. {instead}، ونكمل من هناك.',
           'unreadable': 'لم أتمكن من {read}. {retry}، أو {instead}.',
           'empty': 'لم أجد شيئًا في {what}. تأكدوا أنكم رفعتم الملف الصحيح، أو {instead}.',
           'invalid_answer': 'لم أتمكن من {read} كما يجب. حاولوا مرة أخرى، أو {instead}.',
           'language_mismatch': 'لم أتمكن من {read} بلغتكم. حاولوا مرة أخرى، أو {instead}.',
           'unsupported_type': 'هذا الملف لا يناسب هنا. {upload}، أو {instead}.',
           'evidence_missing': 'الملف الأصلي لم يعد محفوظًا في المشروع، لذلك لا يمكن استخدامه. ارفعوه مرة أخرى، أو {instead}.'},
}
_TEXT = {
    'he': {'uploaded': {NOTE: '📎 פתק בכתב יד', COMPETITOR: '📎 צילום מסך של אתר אחר', VOICE: '📎 הקלטה קולית'},
           'draft_text': {NOTE: 'זה מה שקראתי מהפתק. בדקו אותו: שום דבר לא נבנה לפני שתאשרו.',
                          VOICE: 'זה מה ששמעתי בהקלטה. בדקו אותו: שום דבר לא נבנה לפני שתאשרו.'},
           'draft_skeleton': 'זה השלד שלקחתי מצילום המסך: רק החלקים, הסדר והמבנה. טקסט, צבעים ולוגו של האתר ההוא '
                             'לא נלקחו. בדקו אותו: שום דבר לא נבנה לפני שתאשרו.',
           'found': 'מצאתי בו: {facts}.',
           'hero': 'הפתיח: {type}; שורות בכותרת: {lines}; כפתורים: {ctas}.',
           'decide': 'אם משהו לא נכון, בטלו וכתבו לי את הנכון.',
           'approved_shown': 'אישרתי את הטיוטה',
           'discarded_shown': 'ביטלתי את הטיוטה',
           'skeleton_in': 'המבנה מצילום המסך נכנס לבקשה: רק החלקים והסדר שלהם.',
           'describe': 'עכשיו ספרו לי על העסק שלכם במשפט או שניים, והמבנה ישמש אותו.',
           'continue': 'ספרו לי עוד על העסק, וכשהכול יהיה ברור אציג את האפיון לאישור.',
           'discarded': 'בסדר, לא השתמשתי בזה. הקובץ נשאר שמור בפרויקט.',
           'already': 'כבר החלטתם על הטיוטה הזו.',
           'pending': 'לפני שמאשרים את האפיון: יש טיוטה מקובץ שהעליתם שמחכה להחלטה שלכם. אשרו אותה או בטלו אותה, '
                      'ואז נמשיך.'},
    'en': {'uploaded': {NOTE: '📎 A handwritten note', COMPETITOR: '📎 A screenshot of another site',
                        VOICE: '📎 A voice recording'},
           'draft_text': {NOTE: 'This is what I read from the note. Check it: nothing is built before you approve it.',
                          VOICE: 'This is what I heard in the recording. Check it: nothing is built before you '
                                 'approve it.'},
           'draft_skeleton': 'This is the skeleton I took from the screenshot: only the parts, their order and the '
                             'structure. That site\'s text, colours and logo were not taken. Check it: nothing is '
                             'built before you approve it.',
           'found': 'I found in it: {facts}.',
           'hero': 'The opening: {type}; headline lines: {lines}; buttons: {ctas}.',
           'decide': 'If something is wrong, discard it and type the right version.',
           'approved_shown': 'I approved the draft',
           'discarded_shown': 'I discarded the draft',
           'skeleton_in': 'The structure from the screenshot is now in the request: only the parts and their order.',
           'describe': 'Now tell me about your business in a sentence or two; the structure will be used for it.',
           'continue': 'Tell me more about the business; when everything is clear I will show the spec for approval.',
           'discarded': 'OK, I did not use it. The file stays saved in the project.',
           'already': 'You already decided on this draft.',
           'pending': 'Before the spec is approved: a draft from a file you uploaded is waiting for your decision. '
                      'Approve it or discard it, and then we go on.'},
    'ar': {'uploaded': {NOTE: '📎 ملاحظة مكتوبة بخط اليد', COMPETITOR: '📎 لقطة شاشة لموقع آخر', VOICE: '📎 تسجيل صوتي'},
           'draft_text': {NOTE: 'هذا ما قرأته من الملاحظة. راجعوه: لا يُبنى شيء قبل موافقتكم.',
                          VOICE: 'هذا ما سمعته في التسجيل. راجعوه: لا يُبنى شيء قبل موافقتكم.'},
           'draft_skeleton': 'هذا هو الهيكل الذي أخذته من لقطة الشاشة: الأجزاء وترتيبها وبنيتها فقط. لم يُؤخذ نص ذلك '
                             'الموقع ولا ألوانه ولا شعاره. راجعوه: لا يُبنى شيء قبل موافقتكم.',
           'found': 'وجدت فيه: {facts}.',
           'hero': 'الافتتاحية: {type}؛ أسطر العنوان: {lines}؛ الأزرار: {ctas}.',
           'decide': 'إذا كان هناك خطأ، ألغوها واكتبوا لي الصحيح.',
           'approved_shown': 'وافقت على المسودة',
           'discarded_shown': 'ألغيت المسودة',
           'skeleton_in': 'دخلت البنية من لقطة الشاشة إلى الطلب: الأجزاء وترتيبها فقط.',
           'describe': 'الآن أخبروني عن مصلحتكم في جملة أو جملتين، وستُستخدم البنية لها.',
           'continue': 'أخبروني المزيد عن المصلحة، وعندما يتضح كل شيء سأعرض المواصفات للموافقة.',
           'discarded': 'حسنًا، لم أستخدمها. يبقى الملف محفوظًا في المشروع.',
           'already': 'لقد قررتم بشأن هذه المسودة من قبل.',
           'pending': 'قبل الموافقة على المواصفات: هناك مسودة من ملف رفعتموه تنتظر قراركم. وافقوا عليها أو ألغوها، '
                      'ثم نكمل.'},
}
_HERO_TYPES = {'he': {'split': 'מחולק לשניים', 'full_bleed': 'תמונה לכל הרוחב', 'centered': 'ממורכז',
                      'stacked': 'בשכבות', 'none': 'בלי פתיח גדול'},
               'en': {'split': 'split in two', 'full_bleed': 'full-width picture', 'centered': 'centred',
                      'stacked': 'stacked', 'none': 'no large opening'},
               'ar': {'split': 'مقسومة إلى قسمين', 'full_bleed': 'صورة بعرض كامل', 'centered': 'في الوسط',
                      'stacked': 'طبقات', 'none': 'بلا افتتاحية كبيرة'}}


def text(lang: str) -> dict:
    return _TEXT[check_lang(lang)]


def section_names(lang: str) -> dict:
    return _SECTION_NAMES[check_lang(lang)]


def failure_sentence(code: str, purpose: str, lang: str) -> str:
    """One sentence in the customer's language with the next action. Never the technical detail."""
    check_purpose(purpose)
    if code not in FAILURES:
        raise ValueError(f'unknown reading failure {code!r}')
    what = _WHAT[check_lang(lang)][purpose]
    return _FAILED[lang][code].format(what=what, what_in=what[1:] if lang == 'he' and what.startswith('ה') else what,
                                      instead=_INSTEAD[lang][purpose], upload=_UPLOAD[lang][purpose],
                                      read=_READ[lang][purpose], retry=_RETRY[lang][purpose])


def draft_reply(draft: dict) -> str:
    """The draft in words, in the draft's language: what was read, and that nothing is built before approval."""
    lang = check_lang(draft['language'])
    T = _TEXT[lang]
    if draft['purpose'] == COMPETITOR:
        names, sk = _SECTION_NAMES[lang], draft['skeleton']
        lines = [T['draft_skeleton'], ' '.join(f'{n}. {names[s]}' for n, s in enumerate(sk['section_order'], 1))]
        hero = sk.get('hero') or {}
        if {'type', 'headline_lines', 'cta_count'} <= set(hero):
            lines.append(T['hero'].format(type=_HERO_TYPES[lang][hero['type']], lines=hero['headline_lines'],
                                          ctas=hero['cta_count']))
        lines.append(T['decide'])
        return '\n'.join(lines)
    lines = [T['draft_text'][draft['purpose']], '«' + draft['text'] + '»']
    if draft['facts']:
        names = _FACT_NAMES[lang]
        lines.append(T['found'].format(facts='; '.join(f'{names[f["key"]]} {f["span"]}' for f in draft['facts'])))
    lines.append(T['decide'])
    return '\n'.join(lines)


# ------------------------------------------------------------------ the reader (the model behind an interface)

class NotConnectedReader:
    """OMNI_MEDIA_READER=off: no reading model is connected. Every reading fails as 'not_connected', out loud."""
    name = 'not_connected'

    def read(self, *, purpose: str, data: bytes, mime: str) -> dict:
        check_purpose(purpose)
        raise ReadingFailed('not_connected', 'no reading model is connected (OMNI_MEDIA_READER=off)')


_NOTE_SYSTEM = ('You read a photo of a handwritten note a business owner wrote about their business. Copy the text '
                'exactly as written, in the language it is written in (often Hebrew). Do not translate, summarise, '
                'correct or add anything. Answer ONE JSON object: {"language": "he"|"en"|"ar", "text": "<the note, '
                'line breaks kept>"}. If you cannot read it, answer {"unreadable": true}.')


def _competitor_system() -> str:
    hero = _skeleton_schema()['properties']['hero']['properties']
    return ('You see a screenshot of a website. Return ONLY its skeleton, from closed lists: never any text, name, '
            'colour, logo, picture or font from the site. Answer ONE JSON object: {"skeleton": {"section_order": '
            '[3 to 12 of: ' + ', '.join(section_vocabulary()) + '], "hero": {"type": one of: '
            + ', '.join(hero['type']['enum']) + '; "image_ratio": one of: ' + ', '.join(hero['image_ratio']['enum'])
            + '; "headline_lines": 1 to 4; "cta_count": 0 to 2}, "traits": [0 to 8 of: '
            + ', '.join(trait_vocabulary()) + ']}}. If you cannot read it, answer {"unreadable": true}.')


class GatewayReader:
    """An image read through the routed model gateway (complete_json with images: vision models only, under the
    gateway's budget and ledger). Not wired on the API host -- paid calls run on the worker with a reservation."""

    def __init__(self, gateway):
        if gateway is None:
            raise ValueError('GatewayReader needs a model gateway')
        self.gateway, self.name = gateway, 'gateway'

    def _system(self, purpose: str) -> str:
        return _NOTE_SYSTEM if purpose == NOTE else _competitor_system()

    def read(self, *, purpose: str, data: bytes, mime: str) -> dict:
        check_purpose(purpose)
        if purpose == VOICE:
            raise ReadingFailed('not_connected', 'the model gateway takes no audio input; no speech-to-text provider')
        return self.gateway.complete_json(task='review', system=self._system(purpose),
                                          user=json.dumps({'purpose': purpose, 'mime': mime}), max_tokens=1500,
                                          images=(data,))


def reader_from_env(gateway=None):
    """OMNI_MEDIA_READER: 'off' (the default: nothing reads; the customer is told to type) or 'gateway' (needs a
    model gateway). Any other value raises."""
    mode = os.environ.get('OMNI_MEDIA_READER', 'off').strip().lower()
    if mode not in READER_MODES:
        raise ValueError(f'OMNI_MEDIA_READER must be one of {READER_MODES}, not {mode!r}')
    if mode == 'off':
        return NotConnectedReader()
    if gateway is None:
        raise ValueError('OMNI_MEDIA_READER=gateway needs a model gateway; the API host builds none '
                         '(paid calls run on the worker with a reservation)')
    return GatewayReader(gateway)


def read(reader, purpose: str, data: bytes, mime: str):
    """The reader's answer; any exception the reader raises is a failed reading ('unreadable' unless it says which),
    logged with its detail at ERROR -- loud for us, one sentence for the customer."""
    try:
        return reader.read(purpose=purpose, data=data, mime=mime)
    except ReadingFailed:
        raise
    except Exception as exc:          # a provider error, a timeout, a refusal: the customer gets the sentence
        _LOG.error('MEDIA_READING_FAILED purpose=%s reader=%s: %s', purpose, getattr(reader, 'name', '?'), exc)
        raise ReadingFailed('unreadable', f'{type(exc).__name__}: {str(exc)[:300]}') from exc
