"""Discovery conversation and the versioned ProjectBrief (master directive
2026-10-09 §4-5).

A professional asks before building -- including the simple things (colours,
font, style, logo, audience, content, references) -- in small groups, goes
deeper based on the answers, never re-asks what is known, lets the user
delegate ("no preference -- choose for you") and change an answer later.
This engine is deterministic: every question maps to a brief field, the order
and branching are rules a test can check, and it costs nothing. A model may
later phrase or extend it; it never turns its own guess into an approved fact.

The brief records for every field: value, source (message | answer |
delegated | default), the question that produced it, and confidence. Its
fingerprint binds a build approval; any change makes a new revision and the
old approval stale.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Callable, Mapping

DELEGATE = '__delegate__'
GUIDED, RECOMMEND = 'guided', 'recommend'
SOURCES = ('message', 'answer', 'delegated', 'default')


@dataclass(frozen=True)
class Option:
    value: str
    he: str
    en: str


@dataclass(frozen=True)
class Question:
    id: str
    field: str
    group: str
    he: str
    en: str
    why_he: str
    why_en: str
    kind: str = 'choice'          # choice | text
    options: tuple[Option, ...] = ()
    recommended: str | None = None  # value used when delegated
    delegable: bool = True
    ask_if: Callable[[Mapping[str, str]], bool] = lambda v: True

    def to_dict(self, lang: str = 'he') -> dict:
        he = lang != 'en'
        return {'id': self.id, 'field': self.field, 'group': self.group,
                'text': self.he if he else self.en, 'why': self.why_he if he else self.why_en,
                'kind': self.kind, 'delegable': self.delegable,
                'recommended': None if self.recommended == '__from_request__' else self.recommended,
                'options': [{'value': o.value, 'label': o.he if he else o.en} for o in self.options]}


def _o(value, he, en):
    return Option(value, he, en)


# Groups are asked in this order, a few questions at a time.
GROUPS = ('purpose', 'access', 'content', 'rules', 'design')
GROUP_TITLES = {
    'purpose': ('מטרה וקהל', 'Purpose and audience'),
    'access': ('גישה ומידע', 'Access and data'),
    'content': ('מסכים ותוכן', 'Screens and content'),
    'rules': ('כללים עסקיים', 'Business rules'),
    'design': ('עיצוב ומיתוג', 'Design and brand'),
}

QUESTIONS: tuple[Question, ...] = (
    Question('audience', 'audience', 'purpose', 'מי ישתמש במערכת?', 'Who will use it?',
             'קובע אם צריך הגנה על מידע, שפה פשוטה ללקוחות או כלים מתקדמים לצוות.',
             'Decides data protection, wording for customers or power tools for staff.',
             options=(_o('internal', 'צוות פנימי (עובדים / אני)', 'Internal team (staff / me)'),
                      _o('public', 'לקוחות או קהל רחב מהאינטרנט', 'Customers / the public'),
                      _o('both', 'גם וגם', 'Both')), recommended='internal'),
    Question('goal', 'goal', 'purpose', 'מה הדבר הכי חשוב שהמערכת צריכה לאפשר?', 'What is the one thing it must do best?',
             'הפעולה המרכזית מקבלת את המקום הבולט במסך ונבדקת ראשונה.',
             'The main action gets the most prominent place and is tested first.', kind='text',
             recommended='__from_request__'),  # delegated -> the request's own words
    Question('login', 'login', 'access', 'האם צריך התחברות עם סיסמה?', 'Does it need sign-in?',
             'בלי התחברות כל מי שיש לו את הקישור יכול לראות ולשנות. עם התחברות — רק משתמשים מורשים.',
             'Without sign-in anyone with the link can see and change data.',
             options=(_o('none', 'בלי התחברות', 'No sign-in'),
                      _o('simple', 'התחברות פשוטה (משתמש אחד או כמה עם אותן הרשאות)', 'Simple sign-in (same rights for all)'),
                      _o('roles', 'משתמשים עם הרשאות שונות (למשל מנהל ועובד)', 'Users with different roles')),
             recommended='none'),
    Question('personal_data', 'personal_data', 'access', 'האם יישמרו פרטים אישיים של אנשים (שם, טלפון, מייל)?',
             'Will it store personal details (name, phone, email)?',
             'פרטים אישיים מחייבים לחשוב מי רשאי לראות אותם.', 'Personal data needs a decision about who may see it.',
             options=(_o('yes', 'כן', 'Yes'), _o('no', 'לא', 'No')), recommended='yes'),
    # Content-only sites (landing pages, brochure sites): the one structured decision that lets acceptance skip
    # "create records" checks. Never delegable and never defaulted: only the customer's own answer (or an
    # unchanged pre-selected hint they confirm) sets it, it is shown in the approval summary, and it is bound
    # into the build contract through requirements_text (see product_architect.content_only_approved).
    Question('content_only', 'content_only', 'access',
             'האם זה אתר תוכן בלבד — מציג מידע, מחירים וקישורים, ולא שומר כלום מהמבקרים?',
             'Is this a content-only site: it shows information, prices and links and stores nothing from visitors?',
             'אתר תוכן לא נבדק על יצירה ועריכה של נתונים. אם יש טופס שנשמר, הזמנות או רשימה שמתעדכנת — ענו "לא".',
             'A content-only site is not tested for creating or editing records. If it has a saved form, orders or a changing list, answer "no".',
             options=(_o('yes', 'כן, אתר תוכן בלבד — בלי שמירת נתונים', 'Yes, content only: nothing is stored'),
                      _o('no', 'לא, יש נתונים שנשמרים או משתנים', 'No, some data is stored or changes')),
             delegable=False,
             ask_if=lambda v: v.get('login') == 'none' and v.get('personal_data') == 'no' and v.get('_family') == 'website'),
    Question('access_scope', 'access_scope', 'access',
             'ביקשתם בלי התחברות, אבל יישמרו פרטים אישיים ואנשים מבחוץ ישתמשו. איך להמשיך?',
             'No sign-in, personal data and outside users: how should we proceed?',
             'בלי התחברות, כל מי שמגיע לקישור יראה את הפרטים של כולם. זו החלטה שלכם, לא שלנו.',
             'Without sign-in anyone with the link sees everyone\'s details. This is your decision.',
             options=(_o('internal_link', 'זה כלי פנימי — רק אנחנו נקבל את הקישור', 'Internal tool: only we get the link'),
                      _o('add_login', 'להוסיף התחברות למנהל, והציבור רק ממלא טופס', 'Add sign-in for staff; public only submits a form'),
                      _o('no_personal', 'לא לשמור פרטים אישיים', 'Do not store personal details')),
             delegable=False,
             ask_if=lambda v: v.get('login') == 'none' and v.get('personal_data') == 'yes' and v.get('audience') in ('public', 'both')),
    Question('screens', 'screens', 'content', 'אילו מסכים או אזורים צריכים להיות?', 'Which screens or areas are needed?',
             'כל מסך שתכתבו ייבנה ויקבל בדיקה. אם לא תכתבו — נציע לפי הבקשה.',
             'Every screen you list is built and tested. Leave it to us and we propose from the request.',
             kind='text', recommended='__from_request__'),
    Question('languages', 'languages', 'content', 'באיזו שפה יהיה המוצר?', 'Which language?',
             'קובע כיוון כתיבה (ימין-לשמאל), פורמט תאריכים וניסוח.', 'Sets direction (RTL), date format and wording.',
             options=(_o('he', 'עברית', 'Hebrew'), _o('he_en', 'עברית ואנגלית', 'Hebrew and English'), _o('en', 'אנגלית', 'English')),
             recommended='he'),
    Question('content', 'content', 'content', 'יש תוכן או נתונים שצריכים להיות שם מההתחלה?', 'Any content or data to start with?',
             'למשל רשימת שירותים, מחירים או קטגוריות. נסמן דוגמאות כדוגמאות.',
             'E.g. services, prices or categories. Sample data is marked as sample.',
             kind='text', recommended='ללא — המערכת תתחיל ריקה עם הסבר מה לעשות'),
    Question('dates', 'dates', 'rules', 'יש תאריכים או שעות? אם כן — מה הטווח ההגיוני?', 'Dates or times? If so, what range is sensible?',
             'כך נמנע תאריכים כמו שנת 2356, ונציג תאריכים בפורמט יום/חודש/שנה.',
             'Prevents dates like year 2356 and shows dates as day/month/year.',
             options=(_o('none', 'אין תאריכים', 'No dates'),
                      _o('future_year', 'תאריכים עתידיים עד שנה קדימה', 'Future dates up to a year ahead'),
                      _o('past_and_future', 'גם עבר וגם עתיד (טווח סביר)', 'Past and future (sensible range)')),
             recommended='future_year'),
    Question('duplicates', 'duplicates', 'rules', 'מה לעשות כשמנסים להוסיף משהו שכבר קיים?', 'What if something already exists?',
             'למשל אותו טלפון פעמיים או שתי הזמנות לאותה שעה.', 'E.g. the same phone twice or two bookings for one slot.',
             options=(_o('block', 'לחסום ולהסביר למה', 'Block and explain why'), _o('allow', 'לאפשר', 'Allow')),
             recommended='block'),
    Question('style', 'style', 'design', 'איזה סגנון מתאים לכם?', 'Which style fits?',
             'הסגנון קובע ריווח, פינות, צללים וטון הטקסט.', 'Style sets spacing, corners, shadows and tone.',
             options=(_o('clean', 'נקי ומודרני', 'Clean and modern'), _o('warm', 'חם ומזמין', 'Warm and friendly'),
                      _o('formal', 'עסקי ורשמי', 'Formal business'), _o('playful', 'צבעוני ושמח', 'Playful and colourful')),
             recommended='clean'),
    Question('color', 'color', 'design', 'אילו צבעים תרצו? אפשר לתאר במילים', 'Which colours? Describe them in your own words',
             'הצבע הראשי משמש לכפתורים ולכותרות; הטקסט תמיד יישאר קריא.', 'Used for buttons and headings; text stays readable.',
             kind='text', options=(_o('blue', 'כחול', 'Blue'), _o('green', 'ירוק', 'Green'), _o('purple', 'סגול', 'Purple'),
                      _o('orange', 'כתום', 'Orange'), _o('teal', 'טורקיז', 'Teal'), _o('neutral', 'אפור/שחור', 'Neutral')),
             recommended='blue'),
    Question('font', 'font', 'design', 'איזה גופן?', 'Which font?',
             'כל האפשרויות תומכות בעברית ורישיונן ידוע (Google Fonts, OFL).', 'All support Hebrew and have a known licence (OFL).',
             options=(_o('heebo', 'Heebo — נקי ומודרני', 'Heebo — clean'), _o('assistant', 'Assistant — רך וקריא', 'Assistant — soft'),
                      _o('rubik', 'Rubik — מעוגל וידידותי', 'Rubik — rounded'), _o('system', 'גופן המערכת (הכי מהיר)', 'System font')),
             recommended='heebo'),
    Question('logo', 'logo', 'design', 'לוגו?', 'Logo?', 'אפשר להתחיל בלוגו טקסטואלי ולהחליף אחר כך.',
             'A text logo now can be replaced later.',
             options=(_o('text', 'לוגו טקסטואלי עם שם המוצר', 'Text logo with the product name'), _o('none', 'בלי לוגו', 'No logo'),
                      _o('later', 'יש לי לוגו — אעלה אחר כך', 'I have one — will upload later')), recommended='text'),
    Question('references', 'references', 'design', 'יש אתר שאהבתם את המראה שלו? (קישור או תיאור)',
             'A site whose look you like? (link or description)', 'נשתמש בו כהשראה בלבד, לא נעתיק.',
             'Used as inspiration only, never copied.', kind='text', recommended='אין'),
)
BY_ID = {q.id: q for q in QUESTIONS}

# ---- what the request already says (source = message) ----------------------
_RULES: tuple[tuple[str, str, str, str], ...] = (
    # (pattern, field, value, strength). 'high' = stated outright -> known, not
    # asked again. 'hint' = only suggests the answer: still asked, pre-selected.
    (r'(בלי|ללא)\s+(התחברות|הרשמה|סיסמ)', 'login', 'none', 'high'),
    (r'\b(no|without)\s+(login|sign[- ]?in)', 'login', 'none', 'high'),
    (r'(הרשאות|תפקידים)', 'login', 'roles', 'hint'),
    (r'(בלי|ללא)\s+(איסוף\s+|שמירת\s+|שמירה\s+של\s+|שמירה\s+)?(של\s+)?(פרטים|מידע|נתונים)\s+אישיים', 'personal_data', 'no', 'high'),
    (r'\b(no|without)\s+(collecting\s+|storing\s+|saving\s+)?(any\s+)?personal\s+(data|details|information)', 'personal_data', 'no', 'high'),
    (r'(דף נחיתה|אתר תדמית|landing page|brochure site)', 'content_only', 'yes', 'hint'),
    (r'(טלפון|מייל|אימייל|דוא"ל|כתובת מגורים|ת\.?ז)', 'personal_data', 'yes', 'hint'),
    (r'(לקוחות|ציבור|מטופלים|גולשים)', 'audience', 'public', 'hint'),
    (r'(צוות|עובדים|פנימי|שלי בלבד)', 'audience', 'internal', 'hint'),
    (r'בעברית', 'languages', 'he', 'high'),
    (r'(באנגלית|in english)', 'languages', 'en', 'high'),
    (r'(כחול)', 'color', 'blue', 'high'), (r'(ירוק)', 'color', 'green', 'high'), (r'(סגול)', 'color', 'purple', 'high'),
    (r'(כתום)', 'color', 'orange', 'high'), (r'(טורקיז)', 'color', 'teal', 'high'),
    (r'(תאריך|תור|הזמנ|שעה)', 'dates', 'future_year', 'hint'),
)


def extract_from_message(prompt: str) -> tuple[dict[str, dict], dict[str, str]]:
    """(known fields, hints). Known = stated outright in the request."""
    known: dict[str, dict] = {}
    hints: dict[str, str] = {}
    for pattern, fld, value, strength in _RULES:
        if not re.search(pattern, prompt or '', re.I):
            continue
        if strength == 'high' and fld not in known:
            known[fld] = {'value': value, 'source': 'message', 'question_id': fld, 'confidence': 'stated'}
        elif strength == 'hint' and fld not in hints:
            hints[fld] = value
    if re.search(r'(לקוחות|ציבור)', prompt or '') and re.search(r'(צוות|עובדים|מנהל)', prompt or ''):
        hints['audience'] = 'both'
    return known, hints


# ---- the brief --------------------------------------------------------------

@dataclass
class Brief:
    prompt: str
    mode: str = GUIDED
    fields: dict[str, dict] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)  # questions the user chose to skip (no preference recorded)
    hints: dict[str, str] = field(default_factory=dict)  # suggested answers read from the request (pre-selected, still asked)
    assets: dict[str, dict] = field(default_factory=dict)  # owner-checked attachment id + digest, never bytes/secrets

    def values(self) -> dict[str, str]:
        return {k: v['value'] for k, v in self.fields.items()}

    def to_dict(self) -> dict:
        out = {'prompt': self.prompt, 'mode': self.mode, 'fields': self.fields, 'skipped': list(self.skipped),
               'hints': dict(self.hints)}
        if self.assets:
            out['assets'] = self.assets
        return out

    @classmethod
    def from_dict(cls, d: Mapping) -> 'Brief':
        return cls(str(d.get('prompt', '')), str(d.get('mode', GUIDED)), dict(d.get('fields') or {}), list(d.get('skipped') or []),
                   dict(d.get('hints') or {}), dict(d.get('assets') or {}))

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def start(prompt: str, mode: str = GUIDED) -> Brief:
    if mode not in (GUIDED, RECOMMEND):
        raise ValueError('mode must be guided or recommend')
    known, hints = extract_from_message(prompt)
    brief = Brief(prompt.strip(), mode, known, [], hints)
    if mode == RECOMMEND:
        # The system recommends and chooses (a hint from the request beats the
        # generic default); the user reviews it all in the summary.
        changed = True
        while changed:  # a choice can make a dependent question applicable
            changed = False
            for q in QUESTIONS:
                if q.field not in brief.fields and q.delegable and q.recommended is not None and q.ask_if(_ctx(brief)):
                    brief.fields[q.field] = {'value': _recommended(q, brief, hints), 'source': 'delegated',
                                             'question_id': q.id, 'confidence': 'recommended'}
                    changed = True
    _drop_inapplicable(brief)
    return brief


# A website (landing page, brochure site) shows content; it is not a list-and-form application. The generic
# defaults below (a list screen with an add form, date ranges, duplicate blocking, an empty start) are right
# for applications and wrong for a website, so a website-family request gets content defaults instead.
# Defaults are only proposals: they are listed as assumptions in the approval summary and can be changed.
_WEBSITE_DEFAULTS = {
    'audience': 'public',
    'screens': 'דף אחד: לוגו וכותרת, תיאור העסק, המוצרים או השירותים עם המחירים שצוינו, וקישורי יצירת קשר שצוינו',
    'content': 'הטקסטים, המחירים והקישורים שצוינו בבקשה, בדיוק כפי שנכתבו',
    'dates': 'none',
    'duplicates': 'allow',
}


def is_website(brief: 'Brief') -> bool:
    from .intake.families import classify_family
    return classify_family(brief.prompt) == 'website'


def _ctx(brief: 'Brief') -> dict:
    """What a question's ask_if may look at: the brief's values plus the platform's family classification."""
    v = brief.values()
    v['_family'] = 'website' if is_website(brief) else 'other'
    return v


def _recommended(q: Question, brief: 'Brief', hints: Mapping[str, str]) -> str:
    if q.recommended == '__from_request__':
        return brief.prompt[:300]
    if q.field in _WEBSITE_DEFAULTS and q.field not in hints and is_website(brief):
        return _WEBSITE_DEFAULTS[q.field]
    return hints.get(q.field, q.recommended)


def _drop_inapplicable(brief: Brief) -> None:
    """A changed answer can make a dependent question irrelevant: its answer goes."""
    changed = True
    while changed:
        changed = False
        vals = _ctx(brief)
        for q in QUESTIONS:
            if q.field in brief.fields and not q.ask_if(vals):
                del brief.fields[q.field]
                changed = True


def answer(brief: Brief, answers: Mapping[str, str]) -> Brief:
    """Apply answers ({question id: value | DELEGATE | free text}). Returns a
    new Brief; the caller stores it as a new revision."""
    new = Brief.from_dict(json.loads(json.dumps(brief.to_dict())))
    for qid, raw in answers.items():
        q = BY_ID.get(qid)
        if q is None:
            raise ValueError(f'unknown question {qid}')
        value = (raw or '').strip() if isinstance(raw, str) else raw
        if value == DELEGATE:
            if not q.delegable or q.recommended is None:
                raise ValueError(f'question {qid} needs your own answer')
            new.fields[q.field] = {'value': _recommended(q, new, new.hints), 'source': 'delegated', 'question_id': qid,
                                   'confidence': 'recommended'}
        elif value == '':
            if not q.delegable:
                raise ValueError(f'question {qid} needs an answer')
            if qid not in new.skipped:
                new.skipped.append(qid)
            continue
        else:
            if q.kind == 'choice' and value not in {o.value for o in q.options}:
                raise ValueError(f'invalid option for {qid}')
            new.fields[q.field] = {'value': value[:2000], 'source': 'answer', 'question_id': qid, 'confidence': 'confirmed'}
        if qid in new.skipped:
            new.skipped.remove(qid)
    _drop_inapplicable(new)
    if 'logo' in answers and new.values().get('logo') != 'later':
        new.assets.pop('logo', None)
    return new


def pending(brief: Brief) -> list[Question]:
    vals = _ctx(brief)
    return [q for q in QUESTIONS if q.field not in brief.fields and q.id not in brief.skipped and q.ask_if(vals)]


def next_group(brief: Brief, limit: int = 4) -> tuple[str | None, list[Question]]:
    """The next small group: contradictions first, then the group order."""
    todo = pending(brief)
    urgent = [q for q in todo if q.id == 'access_scope']
    if urgent:
        return 'access', urgent
    for g in GROUPS:
        qs = [q for q in todo if q.group == g]
        if qs:
            return g, qs[:limit]
    return None, []


def contradictions(brief: Brief) -> list[str]:
    v = brief.values()
    out = []
    if v.get('login') == 'none' and v.get('personal_data') == 'yes' and v.get('audience') in ('public', 'both') \
            and v.get('access_scope') is None:
        out.append('no sign-in + personal data + outside users: decide internal tool vs public site')
    # A contact form may collect visitor identifiers even when storage is disabled.
    # Require an explicit delivery/retention decision rather than silently dropping it.
    if v.get('personal_data') == 'no' and re.search(
        r'(טופס יצירת קשר|טופס צור קשר|contact form|contact us form)', brief.prompt, re.I
    ):
        if not re.search(r'(ללא שליחה|בלי שליחה|תצוגה בלבד|ללא איסוף|no submission|display only)', brief.prompt, re.I):
            out.append('contact form + no stored personal data: clarify submission destination, delivery and retention')
    return out


def complete(brief: Brief) -> bool:
    return not pending(brief) and not contradictions(brief)


# ---- what the builders receive ----------------------------------------------

_COLOR_HEX = {'blue': '#1d4ed8', 'green': '#15803d', 'purple': '#7c3aed', 'orange': '#c2410c', 'teal': '#0f766e',
              'neutral': '#334155'}
_FONT = {'heebo': "'Heebo', system-ui, sans-serif", 'assistant': "'Assistant', system-ui, sans-serif",
         'rubik': "'Rubik', system-ui, sans-serif", 'system': 'system-ui, sans-serif'}


def _label(q: Question, value: str, lang: str = 'he') -> str:
    for o in q.options:
        if o.value == value:
            return o.he if lang != 'en' else o.en
    return value


BRIEF_MARKER = '--- Approved project brief'


def detection_text(prompt: str) -> str:
    """The text keyword-based capability detection may read.

    Post-deploy check 2026-10-09: the brief block is written by 148AI, not by
    the user, and its own wording ("reject ... with a clear message", "Logo:
    a text logo") made the planner add messaging and image-generation
    capabilities nobody asked for, which blocked every discovery build. So
    detection reads the user's request only, plus the sign-in decision taken
    in the conversation (the one brief answer that adds infrastructure)."""
    head, sep, brief = prompt.partition(BRIEF_MARKER)
    if not sep:
        return prompt
    extra = ''
    if 'Sign-in: simple sign-in' in brief:
        extra = ' login'
    elif 'Sign-in: users with different roles' in brief:
        extra = ' login roles admin staff'
    return (head.strip() + extra).strip()


CONTENT_ONLY_LINE = ('Product kind: CONTENT-ONLY website. Visitors only read the page and nothing from visitors is saved; '
                     'no accounts, no record-saving forms and no record APIs. Show the content, prices and links exactly as given.')


def _content_only(v: dict, login: str) -> bool:
    """Only an explicit, non-delegated yes together with no sign-in and no personal data."""
    return (v.get('content_only') == 'yes' and login == 'none'
            and v.get('personal_data') == 'no' and v.get('access_scope') != 'add_login')


def requirements_text(brief: Brief) -> str:
    """Binding block appended to the build prompt (English for the models,
    user wording quoted). Includes the brief fingerprint so the contract, and
    hence the approval, is bound to this exact revision."""
    v = brief.values()
    lines = ['', BRIEF_MARKER + ' (binding; fingerprint ' + brief.fingerprint()[:16] + ') ---']
    login = v.get('login', 'none')
    scope = v.get('access_scope')
    if scope == 'add_login':
        login = 'simple'
    lines.append('Sign-in: ' + {'none': 'NONE. Do not add login, sessions, users or roles.',
                                'simple': 'simple sign-in, all users have the same rights.',
                                'roles': 'users with different roles (e.g. admin and staff).'}.get(login, login))
    if scope == 'internal_link':
        lines.append('Access: internal tool; only the owner gets the link (no public pages).')
    if scope == 'no_personal' or v.get('personal_data') == 'no':
        lines.append('Do not store personal or contact details of people.')
    if _content_only(v, login):
        lines.append(CONTENT_ONLY_LINE)
    for fld, label in (('audience', 'Audience'), ('goal', 'Main action'), ('screens', 'Screens'), ('content', 'Initial content'),
                       ('references', 'Visual references (inspiration only)')):
        if v.get(fld):
            lines.append(f'{label}: {_label(BY_ID[fld], v[fld], "en")}')
    lang = v.get('languages', 'he')
    lines.append('Language: ' + {'he': 'Hebrew, right-to-left', 'he_en': 'Hebrew (RTL) with an English switch',
                                 'en': 'English'}.get(lang, lang) + '; dates shown as DD/MM/YYYY.')
    dates = v.get('dates')
    if dates and dates != 'none':
        lines.append('Dates: ' + {'future_year': 'only from today up to one year ahead; reject others with a clear message',
                                  'past_and_future': 'a sensible range (no year before 1900 or after 10 years ahead)'}.get(dates, dates) + '.')
    if v.get('duplicates') == 'block':
        lines.append('Duplicates: block them on the server (also under two simultaneous requests) and explain why.')
    style, color, font = v.get('style', 'clean'), v.get('color', 'blue'), v.get('font', 'heebo')
    lines.append(f'Design: style {style}; primary colour {_COLOR_HEX.get(color, color)}; font {_FONT.get(font, font)} '
                 '(load it from Google Fonts with a system fallback); define these as CSS custom properties.')
    if v.get('logo') == 'text':
        lines.append('Logo: a text logo with the product name in the header.')
    logo = brief.assets.get('logo')
    if logo:
        lines.append(f'Uploaded logo attachment: {logo["id"]}; sha256={logo["sha256"]}. '
                     'Use the original uploaded logo in a visible img element with src="148ai-asset://logo". '
                     'The worker replaces this marker with the verified image bytes before tests; do not recreate the logo.')
    delegated = [k for k, f in brief.fields.items() if f.get('source') == 'delegated']
    if delegated:
        lines.append('Chosen by 148AI on the user\'s behalf (recommended defaults): ' + ', '.join(sorted(delegated)) + '.')
    return '\n'.join(lines)


def summary(brief: Brief, lang: str = 'he') -> dict:
    """Plain-language understanding for the approval screen (§5)."""
    v = brief.values()
    he = lang != 'en'

    def item(fld):
        f = brief.fields.get(fld)
        if not f:
            return None
        q = BY_ID.get(f.get('question_id') or fld) or BY_ID.get(fld)
        return {'field': fld, 'question': (q.he if he else q.en) if q else fld,
                'value': _label(q, f['value'], lang) if q else f['value'], 'source': f['source']}

    sections = {g: [x for x in (item(q.field) for q in QUESTIONS if q.group == g) if x] for g in GROUPS}
    included, excluded = [], []
    login = v.get('login')
    if login == 'none' and v.get('access_scope') != 'add_login':
        excluded.append('התחברות והרשאות' if he else 'Sign-in and roles')
    else:
        included.append('התחברות' if he else 'Sign-in')
    if v.get('personal_data') == 'no' or v.get('access_scope') == 'no_personal':
        excluded.append('שמירת פרטים אישיים' if he else 'Personal details')
    if _content_only(v, 'none' if login == 'none' else 'x'):
        excluded.append('שמירת נתונים מהמבקרים (אתר תוכן בלבד)' if he else 'Visitor data storage (content-only site)')
    excluded += (['פרסום לכתובת קבועה (בשלב זה: תצוגה מקדימה וקוד להורדה)'] if he
                 else ['Publishing to a permanent address (for now: preview and downloadable code)'])
    excluded += (['שמירת נתונים לאורך זמן — הנתונים בתצוגה המקדימה זמניים'] if he
                 else ['Long-term data storage — preview data is temporary'])
    assumptions = [x for g in sections.values() for x in g if x['source'] in ('delegated', 'default')]
    return {'goal': v.get('goal') or brief.prompt[:200], 'sections': sections,
            'group_titles': {g: GROUP_TITLES[g][0 if he else 1] for g in GROUPS},
            'included': included, 'excluded': excluded, 'assumptions': assumptions,
            'contradictions': contradictions(brief), 'complete': complete(brief)}
