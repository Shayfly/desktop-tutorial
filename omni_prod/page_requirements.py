"""Warehouse 122 (the owner's expert, 2026-11-21): the fields a page must have, per kind of page.

A thin page is a generic page. For each kind of page the page needs a few facts without which it says nothing a visitor
came for: a business its phone, address and hours; a portfolio three projects; an event its date, place and how to
register; a butcher's shop also its kosher status and delivery area. This module reads that list and applies two rules:

  required  A field in the list. The conversation agent first reads it from what the customer already said (the same
            extractors the fact sheet uses for a phone, an address and hours; a cue in the words for the rest); only
            when it is still missing does it ask ONE question, in its own words, and each field at most once. A
            required field has NO default: the domain files say "never a default" for hours, kosher status and the like.
            A field that stays unanswered is left off the page and listed as "not given" in the approved brief; it is
            never invented.
  default   Any other field of the page is filled from a default the domain file DECLARES for that category (section 4
            of docs/domains/<slug>.md: "Main action", "Missing price"). It makes no claim, and the page marks it
            ("ברירת מחדל") so a customer can tell it from something they said.

Keyed by `page_type`, the stable key of warehouse 123 (output_profile/page_types.py): the fields every page of a type
needs are in output_profile/required_fields.json under `page_types`; the category-specific ones are rows of the domain
file's mandatory facts (domain_registry.json), named in the same JSON under `domains` by their row number, not copied.
When the customer's words name no type, or two equally, ONE question about the type comes first. Texts are Hebrew,
Arabic and English.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .intake.artifact_fields import Field

LANGS = ('he', 'ar', 'en')
KEYED_BY = 'page_type'
DATA = Path(__file__).with_name('output_profile') / 'required_fields.json'
BASE = 5                            # a missing required field is material, and is asked before every other detector field
TYPE_BASE = 6                       # the question about the type comes before every other
MAX_CLAUSE = 160
PAGE_LINE = "Page details (the customer's own words; show exactly these): "
NOT_GIVEN_LINE = 'Page details not given by the customer (approved without them; never invent them): '
MARK = {'he': 'ברירת מחדל', 'ar': 'الإعداد الافتراضي', 'en': 'default'}
REASON = 'page_'                    # a required field's Questioner reason is REASON + its key
TYPE_KEY = 'page_type'              # the field that asks the page type, when the words name none or two


@dataclass(frozen=True)
class Req:
    """One required field. `kind`: 'fact' (read by the fact sheet's extractors: phone, hours, address, email),
    'words' (a cue in the customer's own words; any reply to its question is the answer) or 'list' (at least
    `min_items` named items). `domain_fact` (category fields) is the row of section 3 of the domain file."""
    key: str
    kind: str
    cue: str = ''
    also: str = ''
    fact: str = ''
    min_items: int = 0
    domain_fact: int = 0


@dataclass(frozen=True)
class Default:
    """A declared category default: `domain_row` is its row in section 4 of the domain file."""
    key: str                        # 'order' | 'price'
    domain_row: str
    label: dict
    text: dict


@dataclass(frozen=True)
class Profile:
    page_type: str | None           # the stable key of warehouse 123; None: the words name none (found says why)
    found: str                      # named | none | tie
    domain: str | None              # the domain file of the category the words name, if it has a row here
    required: tuple = ()
    defaults: tuple = ()


# What each required field is called and how it is asked: {key: {lang: (label, question, why)}}.
TEXT = {
    'phone': {'he': ('טלפון', 'מה מספר הטלפון שהלקוחות יתקשרו אליו?', 'הוא יופיע בעמוד, ובו לקוחות יזמינו'),
              'ar': ('الهاتف', 'ما رقم الهاتف الذي سيتصل به الزبائن؟', 'سيظهر في الصفحة وبه يطلب الزبائن'),
              'en': ('Phone', 'What phone number should customers call?', 'it appears on the page and it is how customers order')},
    'hours': {'he': ('שעות פעילות', 'באילו ימים ושעות אתם פתוחים?', 'בלי זה לקוחות יגיעו לדלת סגורה'),
              'ar': ('ساعات العمل', 'في أي أيام وساعات أنتم مفتوحون؟', 'بدونها قد يصل الزبائن إلى باب مغلق'),
              'en': ('Opening hours', 'Which days and hours are you open?', 'without it customers arrive at a closed door')},
    'address': {'he': ('כתובת', 'מה הכתובת המלאה של העסק?', 'כדי שלקוחות יוכלו להגיע אליכם'),
                'ar': ('العنوان', 'ما العنوان الكامل للمكان؟', 'ليتمكن الزبائن من الوصول إليكم'),
                'en': ('Address', 'What is the full address?', 'so people can find you')},
    'kashrut': {'he': ('כשרות', 'האם העסק כשר או חלאל, ואם כן, מי נותן את ההשגחה?',
                       'לרבים זו ההחלטה לפני כל דבר אחר, ותשובה שגויה פוגעת באמון'),
                'ar': ('الكوشر والحلال', 'هل المكان كوشر أو حلال، وإن كان كذلك فمن يمنح الإشراف؟',
                       'عند كثيرين هذا هو القرار قبل أي شيء، والإجابة الخاطئة تضر بالثقة'),
                'en': ('Kosher or halal', 'Is the business kosher or halal, and if so, who certifies it?',
                       'for many customers this decides everything before price, and a wrong answer costs trust')},
    'delivery': {'he': ('משלוחים', 'האם אתם מבצעים משלוחים, ולאיזה אזור?', 'לקוחות צריכים לדעת אם תגיעו אליהם'),
                 'ar': ('التوصيل', 'هل تقدمون خدمة التوصيل، وإلى أي منطقة؟', 'يحتاج الزبائن إلى معرفة إن كنتم ستصلون إليهم'),
                 'en': ('Delivery', 'Do you deliver, and to which area?', 'customers need to know whether you will reach them')},
    'projects': {'he': ('פרויקטים', 'מהם שלושת הפרויקטים הטובים ביותר שלכם? לכל אחד כתבו מה עשיתם ולמה',
                        'עבודות אמיתיות הן מה שמשכנע לקוח חדש'),
                 'ar': ('المشاريع', 'ما هي أفضل ثلاثة مشاريع لديكم؟ لكل مشروع اكتبوا ماذا فعلتم ولماذا',
                        'الأعمال الحقيقية هي ما يقنع الزبون الجديد'),
                 'en': ('Projects', 'Which are your three best projects? For each one, say what you did and why.',
                        'real work is what convinces a new client')},
    'date': {'he': ('תאריך', 'באיזה תאריך ובאיזו שעה האירוע?', 'בלי תאריך אי אפשר להגיע או להירשם'),
             'ar': ('التاريخ', 'في أي تاريخ وأي ساعة يقام الحدث؟', 'بدون تاريخ لا يمكن الحضور أو التسجيل'),
             'en': ('Date', 'On which date and at what time is the event?', 'without a date nobody can come or sign up')},
    'venue': {'he': ('מקום', 'איפה האירוע מתקיים?', 'אנשים צריכים לדעת לאן להגיע'),
              'ar': ('المكان', 'أين يقام الحدث؟', 'يحتاج الناس إلى معرفة أين يذهبون'),
              'en': ('Venue', 'Where does the event take place?', 'people need to know where to go')},
    'registration': {'he': ('הרשמה', 'איך נרשמים לאירוע, או משיגים כרטיס?', 'זו הפעולה שהעמוד כולו מוביל אליה'),
                     'ar': ('التسجيل', 'كيف يسجّل الناس في الحدث أو يحصلون على تذكرة؟', 'هذا هو الإجراء الذي تقود إليه الصفحة كلها'),
                     'en': ('Registration', 'How do people register or get a ticket?', 'it is the one action the whole page leads to')},
}
# The page types, in the customer's words (the Hebrew and English are page_types.json's labels; a test holds them equal).
TYPE_LABEL = {
    'business': {'he': 'עסק או שירות', 'ar': 'عمل تجاري أو خدمة', 'en': 'business or service'},
    'portfolio': {'he': 'תיק עבודות', 'ar': 'معرض أعمال', 'en': 'portfolio'},
    'event': {'he': 'אירוע', 'ar': 'حدث', 'en': 'event'},
    'community': {'he': 'קהילה', 'ar': 'مجتمع', 'en': 'community'},
    'documentation': {'he': 'תיעוד', 'ar': 'توثيق', 'en': 'documentation'},
    'product': {'he': 'מוצר', 'ar': 'منتج', 'en': 'product'},
    'personal': {'he': 'עמוד אישי', 'ar': 'صفحة شخصية', 'en': 'personal page'},
    'landing': {'he': 'דף נחיתה', 'ar': 'صفحة هبوط', 'en': 'landing page'},
}
_TYPE_ASK = {
    'he': ('סוג העמוד', 'איזה סוג עמוד אתם רוצים: ', 'זה קובע אילו פרטים העמוד חייב לכלול'),
    'ar': ('نوع الصفحة', 'أي نوع من الصفحات تريدون: ', 'هذا يحدد التفاصيل التي يجب أن تتضمنها الصفحة'),
    'en': ('Page type', 'What kind of page do you want: ', 'it decides which details the page has to carry')}
TEXT[TYPE_KEY] = {lang: (_TYPE_ASK[lang][0], _TYPE_ASK[lang][1] + ', '.join(t[lang] for t in TYPE_LABEL.values()) + '?',
                         _TYPE_ASK[lang][2]) for lang in LANGS}
# The declared defaults of a domain, in three languages: {domain: {key: (label, text)}}; each is a row of section 4.
DEFAULTS = {
    'butcher-deli': {'order': ({'he': 'הזמנות', 'ar': 'الطلبات', 'en': 'Orders'},
                               {'he': 'התקשרו להזמנה', 'ar': 'اتصلوا للطلب', 'en': 'Call to order'}),
                     'price': ({'he': 'מחירים', 'ar': 'الأسعار', 'en': 'Prices'},
                               {'he': 'המחיר בדלפק', 'ar': 'السعر في المحل', 'en': 'Price at the counter'})},
    'restaurant': {'order': ({'he': 'שולחנות', 'ar': 'الطاولات', 'en': 'Tables'},
                             {'he': 'התקשרו להזמנת שולחן', 'ar': 'اتصلوا لحجز طاولة', 'en': 'Call to book'}),
                   'price': ({'he': 'מחירים', 'ar': 'الأسعار', 'en': 'Prices'},
                             {'he': 'שאלו אותנו', 'ar': 'اسألونا', 'en': 'Ask us'})},
    'cafe-bakery': {'price': ({'he': 'מחירים', 'ar': 'الأسعار', 'en': 'Prices'},
                              {'he': 'המחיר בדלפק', 'ar': 'السعر في المحل', 'en': 'Ask at the counter'})},
    'hair-salon': {'order': ({'he': 'תורים', 'ar': 'المواعيد', 'en': 'Appointments'},
                             {'he': 'התקשרו לקביעת תור', 'ar': 'اتصلوا لحجز موعد', 'en': 'Call to book'}),
                   'price': ({'he': 'מחירים', 'ar': 'الأسعار', 'en': 'Prices'},
                             {'he': 'המחיר בייעוץ', 'ar': 'السعر عند الاستشارة', 'en': 'Price on consultation'})},
}
# A required field has no default, so the question does not offer one; it says what a non-answer does.
SKIP = {'he': 'אם אין לכם תשובה, כתבו "לא יודע" ולא נציג את זה בעמוד.',
        'ar': 'إن لم يكن لديكم جواب فاكتبوا "لا أعرف" ولن نعرض ذلك في الصفحة.',
        'en': 'If you have no answer, write "don\'t know" and we will leave it off the page.'}
_ORDER = (r'להזמין|הזמנה|הזמנות|הזמנת|תור|לקבוע|order|book|reserve|reservation|appointment|حجز|موعد|طلب|اطلب')

_NON_ANSWER = re.compile(
    r'^\s*(?:לא יודע(?:ת)?|לא בטוח(?:ה)?|אין לי מושג|תחליט(?: אתה|י)?|תבחר אתה|לא משנה לי|no idea|not sure|'
    r'i don.?t know|don.?t know|you decide|your call|up to you|لا أعرف|لا اعرف|لست متأكد(?:ا|ة)?|قرر|اختر أنت)'
    r'\s*[.!?؟]*\s*$', re.I)


def non_answer(text: str) -> bool:
    """A reply that says "I don't know" or hands the decision back: it answers no required field."""
    return not (text or '').strip() or bool(_NON_ANSWER.match(text))


# ------------------------------------------------------------------------------------------------- the data file

@lru_cache(maxsize=1)
def data() -> dict:
    """required_fields.json, checked against the typology (warehouse 123) and the domain registry: a type the typology
    lacks, a domain with no file, a field with no words, or a domain row that is not there stops the module."""
    from . import domain_registry as DR
    from .output_profile import page_types as PT
    d = json.loads(DATA.read_text(encoding='utf-8'))
    if d.get('schema') != '148ai.required_fields/1':
        raise RuntimeError(f"required_fields.json: unknown schema {d.get('schema')!r}")
    if set(d['page_types']) != set(PT.TYPES):
        raise RuntimeError(f"required_fields.json: page types {sorted(d['page_types'])} are not the typology's {list(PT.TYPES)}")
    registry = DR.load()['domains']
    for slug, spec in d['domains'].items():
        if slug not in registry:
            raise RuntimeError(f'required_fields.json: domain {slug!r} has no file')
        rows = {f['n'] for f in registry[slug]['mandatory_facts']}
        for r in spec['required']:
            if r['domain_fact'] not in rows:
                raise RuntimeError(f"required_fields.json: {slug} has no mandatory fact {r['domain_fact']}")
        for x in spec['defaults']:
            if x['key'] not in DEFAULTS.get(slug, {}):
                raise RuntimeError(f"required_fields.json: {slug} default {x['key']!r} has no words")
    every = [r for t in d['page_types'].values() for r in t['required']] + [
        r for s in d['domains'].values() for r in s['required']]
    for r in every:
        if r['key'] not in TEXT or r['kind'] not in ('fact', 'words', 'list'):
            raise RuntimeError(f"required_fields.json: field {r['key']!r} has no words or an unknown kind")
    return d


def _req(raw: dict) -> Req:
    return Req(raw['key'], raw['kind'], raw.get('cue', ''), raw.get('also', ''), raw.get('fact', ''),
               raw.get('min_items', 0), raw.get('domain_fact', 0))


def domain_of(text: str) -> str | None:
    """The domain file of the category the text NAMES (never the nearest: a guessed category asks the wrong things),
    when this table has a row for it."""
    from .domain_registry import CATEGORY_DOMAIN
    from .vertical_palettes import category_of
    slug = CATEGORY_DOMAIN.get(category_of(text or '') or '')
    return slug if slug in data()['domains'] else None


def _answered_type(text: str) -> str | None:
    """The page type the customer ANSWERED with: exactly one type's label (in any of the three languages) in their
    words. The typology's detector reads Hebrew and English cues from what a business says; this reads the customer's
    answer to our own question, whose options are these labels, so an Arabic customer can answer it."""
    lines = [x for x in (text or '').split('\n') if x.strip()]
    for part in ([lines[-1]] if lines else []) + [text or '']:          # the last message first: it is the answer
        named = {t for t, labels in TYPE_LABEL.items() for label in labels.values()
                 if re.search(r'(?<![\w֐-׿؀-ۿ])[הובשלמכ]{0,2}' + re.escape(label) + r'(?![\w֐-׿؀-ۿ])', part, re.I)}
        if len(named) == 1:
            return named.pop()
    return None


@lru_cache(maxsize=512)
def profile_of(text: str) -> Profile:
    """The page type the customer's words name (warehouse 123's detector), and the fields that follow from it and from
    the category: the type's own, then the category's (kosher status, delivery area). With no type named
    (`found` none or tie) only the category's fields; the type is asked first."""
    from .output_profile import page_types as PT
    det = PT.detect_text(text)
    page_type, found = det.page_type, det.found
    if page_type is None and (answered := _answered_type(text)):
        page_type, found = answered, 'named'
    domain = domain_of(text)
    required = [_req(r) for r in data()['page_types'][page_type]['required']] if page_type else []
    defaults = []
    if domain:
        spec = data()['domains'][domain]
        required += [_req(r) for r in spec['required']]
        defaults = [Default(x['key'], x['domain_row'], *DEFAULTS[domain][x['key']]) for x in spec['defaults']]
    return Profile(page_type, found, domain, tuple(required), tuple(defaults))


# ----------------------------------------------------------------------------------------------- reading the words

def _fact_has(text: str, fact: str) -> str | None:
    from .site_content.facts import _fact_spans
    found = [span for key, span in _fact_spans(text or '') if key == fact]
    return ' '.join(found[0].split()) if found else None


def _clause(text: str, cue: str, also: str = '') -> str | None:
    """The part of a customer's text that states a field: the comma-separated piece with the cue, or, when the cue
    needs a second word in the same sentence (a delivery AND where), the whole sentence."""
    for sentence in re.split(r'(?<=[.!?؟])\s+|\n+|;', text or ''):
        if not re.search(cue, sentence, re.I):
            continue
        if also and not re.search(also, sentence, re.I):
            continue
        for piece in re.split(r'[,،]', sentence):
            if re.search(cue, piece, re.I) and (not also or re.search(also, piece, re.I)):
                return ' '.join(piece.split()).strip(' .!?؟')[:MAX_CLAUSE]
        return ' '.join(sentence.split()).strip(' .!?؟')[:MAX_CLAUSE]
    return None


def _items(text: str, cue: str, minimum: int) -> str | None:
    """A list the customer named: after the cue word, at least `minimum` items split by commas, semicolons, new
    lines or bullets. Strict on purpose: when unsure the field is asked once, never taken as given."""
    for line in re.split(r'\n+', text or ''):
        m = re.search(cue, line, re.I)
        if not m:
            continue
        tail = line[m.end():]
        parts = [p.strip(' .:-•*') for p in re.split(r'[,;،•]|\s[-–]\s|\band\b', tail)]
        named = [p for p in parts if len(re.sub(r'[^\w֐-׿؀-ۿ]', '', p)) >= 2]
        if len(named) >= minimum:
            return ' | '.join(named)[:MAX_CLAUSE * 2]
    return None


def reader(req: Req):
    """A function text -> the customer's words stating this field, or None."""
    if req.kind == 'fact':
        return lambda text: _fact_has(text, req.fact)
    if req.kind == 'list':
        return lambda text: _items(text, req.cue, req.min_items)
    return lambda text: _clause(text, req.cue, req.also)


def active() -> bool:
    """The required-field questions belong to the conversation agent (free typing, one question in its own words).
    In the card flow a text question has no button to press, which would be a dead end (tests/test_no_dead_end_
    conversation.py), so with the agent off nothing here asks and nothing is written to the brief."""
    from .intake.conversation_agent import enabled
    return enabled()


def spec_fields(text: str) -> tuple[Field, ...]:
    """The detector's fields for the conversation so far (gaps.Spec adds them to the kind's own fields): the question
    about the page type while the words name none or two, then each required field of the type and the category."""
    if not active():
        return ()
    profile = profile_of(text)
    out = []
    if profile.found in ('none', 'tie'):
        out.append(Field(TYPE_KEY, '', REASON + TYPE_KEY, TYPE_BASE))
    out += [Field(r.key, '', REASON + r.key, BASE, implies=(('stated', reader(r)),), words=r.kind == 'words')
            for r in profile.required]
    return tuple(out)


def fallback_entries(lang: str) -> dict:
    """{reason: (question, why)} for gaps.FALLBACK in one language."""
    return {REASON + key: (t[lang][1], t[lang][2]) for key, t in TEXT.items()}


def is_page_reason(reason: str) -> bool:
    return (reason or '').startswith(REASON)


def missing_keys(profile: Profile | None, customer: str, stored: dict | None = None) -> list[str]:
    """The required keys the customer's words (and the answers stored from the conversation) do not state."""
    if profile is None:
        return []
    stored = stored or {}
    return [r.key for r in profile.required if not stored.get(r.key) and reader(r)(customer) is None]


def capture(text: str, customer: str, stored: dict) -> dict:
    """The words of `text` that state a 'words' or 'list' field of the customer's page and are not stored yet."""
    profile = profile_of(customer) if active() else None
    out = {}
    for r in (profile.required if profile else ()):
        if r.kind != 'fact' and not stored.get(r.key):
            found = reader(r)(text)
            if found:
                out[r.key] = found
    return out


def brief_lines(customer: str, stored: dict | None, asked=()) -> list[str]:
    """The lines the approved brief carries for these fields: what the customer said, and what they did not. Only a
    conversation that engaged with the fields (it recorded words, or asked one) writes them: a brief that never
    went through the conversation is byte-identical to what it was before this warehouse item."""
    if not (stored or asked):
        return []
    profile = profile_of(customer)
    stored = stored or {}
    lines = []
    said = [f'{r.key}={_one_line(stored[r.key])}' for r in profile.required if r.kind != 'fact' and stored.get(r.key)]
    if said:
        lines.append(PAGE_LINE + ' | '.join(said))
    missing = missing_keys(profile, customer, stored)
    if missing:
        lines.append(NOT_GIVEN_LINE + ', '.join(missing) + '.')
    return lines


def parse_page_line(prompt: str) -> dict:
    """{key: the customer's words} from the PAGE_LINE of an approved prompt."""
    out = {}
    for line in (prompt or '').splitlines():
        if line.startswith(PAGE_LINE):
            for part in line[len(PAGE_LINE):].split(' | '):
                key, sep, words = part.partition('=')
                if sep and key.strip() in TEXT and words.strip():
                    out[key.strip()] = words.strip()
    return out


def answers(text: str, detected: dict, value) -> dict:
    """{key: the customer's words} for the 'words' and 'list' fields of the conversation's page that the detector has:
    a reply taken as the value (`value(name)`), or words it found in the conversation (detected['implied'])."""
    out = {}
    for r in profile_of(text).required:
        if r.kind == 'fact':
            continue
        words = value(r.key) or (detected.get('implied', {}).get(r.key) or {}).get('words')
        if words:
            out[r.key] = words
    return out


def next_required(customer: str, stored: dict | None, asked) -> str | None:
    """The field the conversation agent should ask next: the page type while the words name none or two, then the first
    required field the customer's words do not state. Each is offered to the agent once (`asked`): a non-answer ends it."""
    profile = profile_of(customer)
    if profile.found in ('none', 'tie') and TYPE_KEY not in set(asked or ()):
        return TYPE_KEY
    for key in missing_keys(profile, customer, stored):
        if key not in set(asked or ()):
            return key
    return None


def agent_context(key: str, customer: str = '') -> dict:
    """What the conversation agent is given about one field (English: the agent writes the question in the customer's
    language and its own words). For the page type it also gets the types, or the two the words tie between."""
    label, question, why = TEXT[key]['en']
    out = {'field': key, 'topic': label, 'what_to_learn': question, 'why_it_matters': why, 'may_delegate': False,
           'asked_once': True}
    if key == TYPE_KEY:
        from .output_profile import page_types as PT
        det = PT.detect_text(customer)
        out['choices'] = [TYPE_LABEL[t]['en'] for t in (det.candidates if det.found == 'tie' else PT.TYPES)]
    return out


def _one_line(text: str) -> str:
    return ' '.join(str(text).replace('|', '/').split())[:MAX_CLAUSE * 2]


# ------------------------------------------------------------------------------------------- the page's own rows

@dataclass
class PageFacts:
    """What the page shows for its required fields and declared defaults (built from the approved prompt)."""
    page_type: str | None = None
    found: str = 'none'
    domain: str | None = None
    said: dict = field(default_factory=dict)            # key -> the customer's words
    not_given: list = field(default_factory=list)       # required keys the page leaves off
    defaults: list = field(default_factory=list)        # keys of the declared defaults the page shows (marked)
    _specs: tuple = field(default=(), repr=False)       # the Default records behind `defaults`

    def rows(self, lang: str = 'he') -> list[tuple[str, str]]:
        """(label, value) rows for the hero panel: the customer's words first, then the marked defaults."""
        if lang not in LANGS:
            raise ValueError(f'language {lang!r} is not one of {LANGS}')
        out = [(TEXT[k][lang][0], v) for k, v in self.said.items()]
        for d in self._specs:
            out.append((d.label[lang], f'{d.text[lang]} ({MARK[lang]})'))
        return out

    def to_dict(self) -> dict:
        return {'keyed_by': KEYED_BY, 'page_type': self.page_type, 'found': self.found, 'domain': self.domain,
                'said': dict(self.said), 'not_given': list(self.not_given), 'defaults': list(self.defaults)}


def page_facts(prompt: str, customer: str, *, phone: str | None, has_prices: bool) -> PageFacts:
    """The sheet's page facts, from the approved prompt alone. A default row is shown only where the customer said
    nothing: an order default needs a phone and no ordering words; a price default needs no price given."""
    from .site_content.facts import request_text
    profile = profile_of(customer)
    stored = parse_page_line(prompt)
    said = {}
    for r in profile.required:
        if r.kind == 'fact':
            continue
        words = stored.get(r.key) or reader(r)(customer)
        if words:
            said[r.key] = words
    shown = []
    for d in profile.defaults:
        if d.key == 'order' and phone and not re.search(_ORDER, request_text(prompt) + '\n' + customer, re.I):
            shown.append(d)
        if d.key == 'price' and not has_prices:
            shown.append(d)
    return PageFacts(profile.page_type, profile.found, profile.domain, said, missing_keys(profile, customer, said),
                     [d.key for d in shown], tuple(shown))
