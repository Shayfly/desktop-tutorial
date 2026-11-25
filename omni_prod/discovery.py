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

from . import vocabulary as _vocab

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

IMAGE_KINDS = ('person', 'product', 'place', 'logo', 'other')
IMAGE_PLACES = ('hero', 'story', 'products', 'gallery')
IMAGE_PLACES_HE = {'hero': 'התמונה הראשית בראש הדף', 'story': 'ליד הסיפור שלנו', 'products': 'באזור המוצרים',
                   'gallery': 'בגלריה'}
_IMAGE_WHO = {   # the identity question, by kind (Michael 2026-11-15)
    'person': ('מי בתמונה, ומה התפקיד שלו או שלה בעסק?', 'Who is in the photo, and what is their role in the business?',
               'למשל: "סבא שמעון, הבעלים". זה ייכתב בתיאור התמונה בדף.'),
    'product': ('איזה מוצר בתמונה, ומה מיוחד בו?', 'Which product is it, and what is special about it?',
                'למשל: "שיפודי פרגית, מתובלים אצלנו". זה ייכתב בתיאור התמונה בדף.'),
    'place': ('איזה מקום בתמונה, ומה קורה בו?', 'Which place is it, and what happens there?',
              'למשל: "הדלפק בחנות, כאן חותכים מול הלקוח". זה ייכתב בתיאור התמונה בדף.'),
    'other': ('מה יש בתמונה, ואיפה היא צריכה להופיע?', 'What is in the image, and where should it appear?',
              'כך נדע מה לעשות איתה.'),
}
_IMAGE_USE_OPTIONS = (_o('as_is', 'להשתמש בה כמו שהיא', 'Use it as is'),
                      _o('change', 'לשנות אותה (עוד לא זמין)', 'Change it (not available yet)'),
                      _o('inspiration', 'רק השראה — לא להציג בדף', 'Inspiration only, not shown'))
_IMAGE_USE_WHY = ('כמו שהיא: התמונה תופיע בדף בדיוק כפי שהעלית, בלי ליצור תמונה אחרת. שינוי של התמונה עצמה '
                  '(למשל להכניס אותה לסצנה אחרת) עוד לא זמין.')
_IMAGE_USE_WHY_EN = ('As is: the image appears exactly as uploaded and no other image is generated. Changing the image '
                     'itself (e.g. placing it in another scene) is not available yet.')
IMAGE_QUESTIONS = (
    Question('image_kind', 'image_kind', 'design', 'קיבלתי את התמונה. מה יש בה?', 'I got the image. What is in it?',
             'כל תמונה שמעלים מקבלת תפקיד, כדי שנדע איך להשתמש בה.',
             'Every uploaded image gets a role, so we know how to use it.',
             options=(_o('person', 'אדם', 'A person'), _o('product', 'מוצר', 'A product'), _o('place', 'מקום', 'A place'),
                      _o('logo', 'הלוגו שלי', 'My logo'), _o('other', 'משהו אחר', 'Something else')),
             delegable=False, ask_if=lambda v: bool(v.get('_image'))),
    *(Question(f'image_who_{kind}', 'image_identity', 'design', he, en, why, why, kind='text', delegable=False,
               ask_if=lambda v, k=kind: bool(v.get('_image')) and v.get('image_kind') == k)
      for kind, (he, en, why) in _IMAGE_WHO.items()),
    # then, always, what to do with it -- with a suggested choice by kind (an "other" image: inspiration)
    Question('image_use', 'image_use', 'design', 'ומה לעשות עם התמונה? ההמלצה שלי: להשתמש בה כמו שהיא.',
             'And what should I do with it? I suggest using it as is.', _IMAGE_USE_WHY, _IMAGE_USE_WHY_EN,
             options=_IMAGE_USE_OPTIONS, recommended='as_is', delegable=False,
             ask_if=lambda v: bool(v.get('_image')) and v.get('image_kind') in ('person', 'product', 'place')
             and bool(v.get('image_identity'))),
    Question('image_use_other', 'image_use', 'design', 'ומה לעשות עם התמונה? ההמלצה שלי: רק השראה.',
             'And what should I do with it? I suggest inspiration only.', _IMAGE_USE_WHY, _IMAGE_USE_WHY_EN,
             options=_IMAGE_USE_OPTIONS, recommended='inspiration', delegable=False,
             ask_if=lambda v: bool(v.get('_image')) and v.get('image_kind') == 'other' and bool(v.get('image_identity'))),
    # Michael 2026-11-15 (step 3): a page holds several images, and "where" decides the place -- suggested by kind
    *(Question(f'image_place_{kind}', 'image_place', 'design',
               f'איפה בדף היא תופיע? ההמלצה שלי: {IMAGE_PLACES_HE[rec]}.', f'Where on the page? I suggest: {rec}.',
               'תמונה ראשית יש אחת בדף; בשאר המקומות אפשר כמה.', 'A page has one main image; other places take several.',
               options=tuple(_o(p, IMAGE_PLACES_HE[p], p) for p in IMAGE_PLACES), recommended=rec, delegable=False,
               ask_if=lambda v, k=kind: bool(v.get('_image')) and v.get('image_kind') == k and v.get('image_use') == 'as_is')
      for kind, rec in (('person', 'hero'), ('product', 'products'), ('place', 'hero'), ('other', 'gallery'))),
)


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
             # R1/8.2 (run 10b): no family condition. It was `_family == 'website'`, so a brief the classifier called
             # web_app ("תבנה דף לעסק שלי") had no slot: the customer's "מידע" was lost and _drop_inapplicable removed
             # the field even when given. Asked as soon as nothing rules it out, from the first turn.
             # A STRONG storing cue (8.1) settles it without a question -- unless a "stores nothing" answer just went
             # stale (8.4), which is asked again.
             ask_if=lambda v: v.get('login', 'none') == 'none' and v.get('personal_data') != 'yes'
             and v.get('access_scope') != 'add_login' and (not v.get('_strong') or v.get('_stale'))),
    # Production 2026-11-17 ("148 דלתות"): "content only: yes", then "personal details: yes" -- the first answer was
    # dropped in silence (_drop_inapplicable) and the site became a leads database. Neither answer is dropped now:
    # the conflict is asked once, in words, and the customer's choice settles both fields (answer()).
    Question('storage_intent', 'storage_intent', 'access',
             'אמרתם קודם שהאתר לא שומר כלום מהמבקרים, ועכשיו שיישמרו פרטים אישיים. מה נכון?',
             'You said the site stores nothing from visitors, and now that personal details are stored. Which is it?',
             'אם רק פרטי העסק שלכם (טלפון, כתובת) מוצגים באתר — זה אתר תוכן, ולא נשמר כלום.',
             'If only your business details (phone, address) are shown, it is a content site and nothing is stored.',
             options=(_o('business', 'רק פרטי העסק מוצגים באתר — לא נשמר כלום מהמבקרים',
                         'Only the business details are shown; nothing from visitors is stored'),
                      _o('visitors', 'האתר שומר פרטים של מבקרים (למשל טופס פנייה)',
                         'The site stores visitors\' details (e.g. a contact form)')),
             delegable=False, ask_if=lambda v: bool(v.get('_storage_conflict'))),
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
             kind='text', options=(_o('category', 'לפי סוג העסק', 'By the type of business'),
                      _o('blue', 'כחול', 'Blue'), _o('green', 'ירוק', 'Green'), _o('purple', 'סגול', 'Purple'),
                      _o('orange', 'כתום', 'Orange'), _o('teal', 'טורקיז', 'Teal'), _o('neutral', 'אפור/שחור', 'Neutral')),
             recommended='category'),   # warehouse 105: no single default blue; the category's palette (data file)
    Question('font', 'font', 'design', 'איזה גופן?', 'Which font?',
             'כל האפשרויות תומכות בעברית ורישיונן ידוע (Google Fonts, OFL).', 'All support Hebrew and have a known licence (OFL).',
             options=(_o('heebo', 'Heebo — נקי ומודרני', 'Heebo — clean'), _o('assistant', 'Assistant — רך וקריא', 'Assistant — soft'),
                      _o('rubik', 'Rubik — מעוגל וידידותי', 'Rubik — rounded'), _o('system', 'גופן המערכת (הכי מהיר)', 'System font')),
             recommended='heebo'),
    Question('logo', 'logo', 'design', 'לוגו?', 'Logo?', 'אפשר להתחיל בלוגו טקסטואלי ולהחליף אחר כך.',
             'A text logo now can be replaced later.',
             options=(_o('text', 'לוגו טקסטואלי עם שם המוצר', 'Text logo with the product name'), _o('none', 'בלי לוגו', 'No logo'),
                      _o('uploaded', 'הלוגו שהעליתם', 'The logo you uploaded'),
                      _o('later', 'יש לי לוגו — אעלה אחר כך', 'I have one — will upload later')), recommended='text'),
    # 77 (Michael 2026-11-11): a capability with no price never blocks silently. When the platform finds one before
    # gate 1 it records the keys in hints['unpriced'] and asks this ONE question. "Build without" binds a customer
    # exclusion into the contract (Customer exclusions v1, read by product_architect); "wait" is said plainly.
    Question('unavailable', 'unavailable', 'purpose',
             'חלק ממה שביקשת עדיין לא זמין אצלנו. לבנות בלעדיו?',
             'Part of what you asked for is not available yet. Build without it?',
             'אם תבחרו לבנות בלעדיו, זה ייכתב בסיכום שתאשרו. אפשר להוסיף אותו אחר כך כשיהיה זמין.',
             'If you build without it, the summary you approve says so. It can be added later once available.',
             options=(_o('build_without', 'כן, לבנות בלעדיו', 'Yes, build without it'),
                      _o('wait', 'לא, אחכה שזה יהיה זמין', 'No, I will wait for it')),
             delegable=False, ask_if=lambda v: bool(v.get('_unpriced'))),
    Question('references', 'references', 'design', 'יש אתר שאהבתם את המראה שלו? (קישור או תיאור)',
             'A site whose look you like? (link or description)', 'נשתמש בו כהשראה בלבד, לא נעתיק.',
             'Used as inspiration only, never copied.', kind='text', recommended='אין'),
    # Production 2026-11-15 (bld_09482b26, "סבא שמעון"): the customer uploaded his grandfather's photo; only "one image
    # + the word logo" was ever bound, so the photo was dropped silently and a different man was generated from the
    # text. Michael 2026-11-15 16:15: EVERY uploaded image gets an explicit role -- first WHAT it is (by its kind),
    # only then what to do with it. Never delegated, never assumed; the role goes into the alt and the canon.
    *IMAGE_QUESTIONS,
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
    (_vocab.terms('דף נחיתה', 'עמוד נחיתה', 'אתר תדמית', 'אתר תוכן', 'אתר עסקי', 'כרטיס ביקור דיגיטלי', 'אתר הצגה',
                  'landing page', 'brochure site', 'one-page site', 'one page site'), 'content_only', 'yes', 'hint'),
    (_vocab.PERSONAL_DATA_COLLECT, 'personal_data', 'yes', 'hint'),
    (_vocab.terms('לקוחות', 'ציבור', 'הציבור', 'מטופלים', 'גולשים', 'מבקרים', 'אורחים', 'סועדים'), 'audience', 'public', 'hint'),
    (_vocab.terms('צוות', 'עובדים', 'פנימי', 'פנימית', 'שלי בלבד', 'לשימוש פנימי'), 'audience', 'internal', 'hint'),
    (r'בעברית', 'languages', 'he', 'high'),
    (r'(באנגלית|in english)', 'languages', 'en', 'high'),
    (_vocab.terms('כחול'), 'color', 'blue', 'high'), (_vocab.terms('ירוק'), 'color', 'green', 'high'),
    (_vocab.terms('סגול'), 'color', 'purple', 'high'),
    (_vocab.terms('כתום'), 'color', 'orange', 'high'), (_vocab.terms('טורקיז'), 'color', 'teal', 'high'),
    (_vocab.terms(*_vocab.BOOKING_WORDS), 'dates', 'future_year', 'hint'),
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
    palette = colour_palette(prompt)
    if palette:
        if len(palette) > 1:
            palette = colour_palette(prompt, preserve_words=True)
        known['color'] = {'value': ', '.join(palette), 'source': 'message',
                          'question_id': 'color', 'confidence': 'stated'}
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
    semantic_decisions: list[dict] = field(default_factory=list)  # validated model evidence, reviewed on brief approval
    # C6 (CEO 2026-10-27): the gap detector decides completeness. `detector` marks a brief written by the detector-led
    # conversation; `open_material` = the material fields the detector still asks for (empty = nothing material
    # missing). Briefs without the flag keep the catalog rule, so their fingerprints and approvals are unchanged.
    detector: bool = False
    open_material: list[str] = field(default_factory=list)
    structure: list[dict] = field(default_factory=list)  # first agent (2026-11-15): the approved structure cards

    def values(self) -> dict[str, str]:
        return {k: v['value'] for k, v in self.fields.items()}

    def to_dict(self) -> dict:
        out = {'prompt': self.prompt, 'mode': self.mode, 'fields': self.fields, 'skipped': list(self.skipped),
               'hints': dict(self.hints)}
        if self.assets:
            out['assets'] = self.assets
        if self.semantic_decisions:
            out['semantic_decisions'] = list(self.semantic_decisions)
        if self.detector:
            out['detector'] = True
            out['open_material'] = list(self.open_material)
        if self.structure:
            out['structure'] = list(self.structure)
        return out

    @classmethod
    def from_dict(cls, d: Mapping) -> 'Brief':
        return cls(str(d.get('prompt', '')), str(d.get('mode', GUIDED)), dict(d.get('fields') or {}), list(d.get('skipped') or []),
                   dict(d.get('hints') or {}), dict(d.get('assets') or {}),
                   list(d.get('semantic_decisions') or []), bool(d.get('detector')),
                   list(d.get('open_material') or []), list(d.get('structure') or []))

    def fingerprint(self) -> str:
        # C6: which field the detector asks next is conversation state, not a requirement; it never changes the
        # fingerprint an approval binds to (completeness itself is stored per revision, see BriefRepository.save).
        data = {k: v for k, v in self.to_dict().items() if k != 'open_material'}
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


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
    'screens': '__from_request__',
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
    from .persistence import strong_cues
    v['_strong'] = bool(strong_cues(brief.prompt))           # R1/8.1, read by the persistence question
    v['_stale'] = brief.hints.get('persistence_stale') == 'yes'
    v['_unpriced'] = unpriced_keys(brief)                     # 77, read by the "unavailable" question
    v['_image'] = bool(brief.assets.get('image'))             # an uploaded image waits for its role
    v['_storage_conflict'] = brief.hints.get('storage_conflict') == 'yes'
    return v


CUSTOMER_EXCLUSIONS_PREFIX = 'Customer exclusions v1: '


# #330 (Michael 2026-11-12 20:11): three classes of field. (1) delegable: 148AI may decide. (2) delegable=False:
# only the customer sets it (content_only, access_scope, unavailable). (3) SENSITIVE, INFERABLE BUT CONFIRMED: the
# value may be inferred from the request, but it counts only once the customer CONFIRMED it (a button answer).
CONFIRM_REQUIRED = ('personal_data', 'login', 'access_scope')

# Michael 2026-11-13 (production, bakery): one field, one question per turn. A question that also decides another
# field COVERS it: access_scope's three options decide whether personal data is stored ("no_personal" = no; the
# other two store it), so while access_scope is asked, the yes/no personal_data question is not asked beside it.
COVERS = {'access_scope': ('personal_data',)}


def one_question_per_field(questions) -> list:
    """The questions of one turn, at most one per field, without a question another one in the turn covers."""
    covered = {f for q in questions for f in COVERS.get(q.field, ())}
    out, seen = [], set()
    for q in questions:
        if q.field in covered or q.field in seen:
            continue
        seen.add(q.field)
        out.append(q)
    return out


def confirmed(brief: 'Brief', field_: str) -> bool:
    """The brief holds a value the customer confirmed (their own button answer), not one inferred or typed."""
    return (brief.fields.get(field_) or {}).get('confidence') == 'confirmed'


# Michael 2026-11-13 (#339): after the card limit a privacy-safe default settles a sensitive field. It is said in the
# turn it is applied, marked on the gate-1 summary, and approving that summary is the customer's confirmation.
SAFE_DEFAULT_CONFIDENCE = 'safe_default'


def needs_customer(q: 'Question', brief: 'Brief') -> bool:
    """Class 2 or class 3, not yet confirmed by the customer: they must see this exact question and its buttons."""
    if (brief.fields.get(q.field) or {}).get('confidence') == SAFE_DEFAULT_CONFIDENCE:
        return False
    return (not q.delegable or q.field in CONFIRM_REQUIRED) and not confirmed(brief, q.field)


def unpriced_keys(brief: 'Brief') -> list[str]:
    """77: the capabilities the platform found unpriced for this brief (set by the supervisor before gate 1)."""
    raw = (brief.hints or {}).get('unpriced') or ''
    return [k for k in str(raw).split(',') if k]


def customer_exclusions(brief: 'Brief') -> list[str]:
    """77: what the customer chose to build without -- only their own button answer counts."""
    f = brief.fields.get('unavailable') or {}
    if f.get('value') != 'build_without' or f.get('source') != 'answer':
        return []
    from .build_readiness import excludable
    return [k for k in unpriced_keys(brief) if excludable(k)]


UPLOAD_MARKER = '148ai-asset://upload/'
UPLOADED_IMAGE_PREFIX = 'Uploaded image '
MAIN_IMAGE_MARKER = UPLOAD_MARKER + '1'      # the first placed image (kept for readers of #385/#388)
# 2026-11-16: the place is checked (uploaded_assets.place_state): the photo must be INSIDE a <section> of that kind
_SECTION = {'hero': 'the main (hero) image at the top of the page',
            'story': 'part of the story/about section -- inside a <section> whose heading is "הסיפור שלנו"',
            'products': 'part of the products section -- inside a <section> whose heading is "המוצרים שלנו"',
            'gallery': 'part of a gallery section -- inside a <section> whose heading is "גלריה"'}


def placed_images(brief: 'Brief') -> list[dict]:
    """The customer's images with their full role (kind, words, as is, place), in the order they were decided.
    Each has its own marker 148ai-asset://upload/<n>."""
    out = [dict(img) for img in brief.assets.get('images') or () if img.get('use') == 'as_is' and img.get('place')]
    for n, img in enumerate(out, start=1):
        img['marker'] = f'{UPLOAD_MARKER}{n}'
    return out


def main_image(brief: 'Brief') -> dict | None:
    """The image the customer placed as the main image, or None."""
    return next((img for img in placed_images(brief) if img['place'] == 'hero'), None)


_KIND_HE = {'person': 'אדם', 'product': 'מוצר', 'place': 'מקום', 'other': 'אחר'}


def image_role(brief: 'Brief') -> dict | None:
    """kind + the customer's own words for it (the alt) + what to do with it; None while not fully answered."""
    v = brief.values()
    if not brief.assets.get('image') or v.get('image_kind') not in _KIND_HE or not v.get('image_identity'):
        return None
    alt = ' '.join(str(v['image_identity']).replace('"', '״').split())[:160]
    return {'kind': v['image_kind'], 'alt': alt, 'use': v.get('image_use')}


def image_canon_lines(brief: 'Brief', lang: str = 'he') -> list[str]:
    """One line per decided image: what it is, the customer's words, and what happens to it (where it appears)."""
    out = []
    for img in brief.assets.get('images') or ():
        if img.get('use') == 'as_is':
            use = (f'תופיע בדף כמו שהיא, {IMAGE_PLACES_HE[img["place"]]}' if lang == 'he'
                   else f'shown on the page as is, {img["place"]}')
        else:
            use = 'השראה בלבד, לא מוצגת בדף' if lang == 'he' else 'inspiration only, not shown'
        out.append(f'תמונה שהעלית ({_KIND_HE[img["kind"]]}): {img["alt"]} — {use}.' if lang == 'he'
                   else f'Your image ({img["kind"]}): {img["alt"]} -- {use}.')
    return out


def image_exclusions(brief: 'Brief') -> list[str]:
    """The customer's own photo, shown as is, replaces generation: no image is generated for this brief."""
    return ['media.image.generate'] if main_image(brief) else []


def _website_screens(prompt: str) -> str:
    """Derive only explicitly requested site sections; never invent CRUD pages."""
    patterns = (
        (r'(דף בית|עמוד הבית|homepage|home page)', 'דף בית'),
        (r'(חיפוש חופשות|חיפוש טיסות|חיפוש מלונות|search (?:for )?(?:vacations|holidays|flights|hotels))', 'חיפוש חופשות / שירותים'),
        (r'(טופס יצירת קשר|טופס צור קשר|contact form)', 'טופס יצירת קשר'),
        (r'(אודות|about us|about page)', 'אודות'),
        (r'(גלריה|gallery)', 'גלריה'),
        (r'(מחירון|pricing page|price list)', 'מחירון'),
    )
    screens = [label for pattern, label in patterns if re.search(pattern, prompt, re.I)]
    return ', '.join(screens) if screens else 'אזורים בהתאם לבקשת הלקוח; אין להוסיף מסכי ניהול או CRUD שלא התבקשו'


def _recommended(q: Question, brief: 'Brief', hints: Mapping[str, str]) -> str:
    if q.recommended == '__from_request__':
        if q.field == 'goal':                    # the first business sentence, never a pasted technical line
            from .intake.text_noise import first_sentence
            return (first_sentence(brief.prompt) or brief.prompt)[:300]
        return _website_screens(brief.prompt) if q.field == 'screens' and is_website(brief) else brief.prompt[:300]
    if q.field in _WEBSITE_DEFAULTS and q.field not in hints and is_website(brief):
        value = _WEBSITE_DEFAULTS[q.field]
        return _website_screens(brief.prompt) if value == '__from_request__' else value
    return hints.get(q.field, q.recommended)


def _expire_stale_persistence(brief: Brief) -> None:
    """R1/8.4: "stores nothing" was answered, then the brief gained something that stores ("עם הרשמה"). The answer is
    moved out and the question is asked again, pre-selected to "stores". The strong cues present when the customer
    answered are remembered, so an answer given knowingly is never re-asked for the same words."""
    f = brief.fields.get('content_only')
    if not f or f.get('value') != 'yes':
        return
    from .persistence import strong_cues
    v = brief.values()
    now = set(strong_cues(' '.join([brief.prompt] + [str(v.get(k) or '') for k in ('goal', 'screens', 'content')])))
    if 'cues_at_answer' not in f:
        f['cues_at_answer'] = sorted(now)
        return
    if now - set(f['cues_at_answer']):
        del brief.fields['content_only']
        brief.hints['content_only'] = 'no'
        brief.hints['persistence_stale'] = 'yes'   # read by the turn record (8.6 trigger), cleared on the next answer
    elif brief.hints.get('persistence_stale'):
        brief.hints.pop('persistence_stale', None)


def _drop_inapplicable(brief: Brief) -> None:
    """A changed answer can make a dependent question irrelevant: its answer goes."""
    _expire_stale_persistence(brief)
    changed = True
    while changed:
        changed = False
        vals = _ctx(brief)
        # a field several questions share (the image's identity and use, one question per kind) goes only when NONE
        # of its questions applies; every other field has exactly one question, as before
        for fld in dict.fromkeys(q.field for q in QUESTIONS):
            if fld == 'content_only' and vals.get('_storage_conflict'):
                continue                                   # kept until the customer settles storage_intent
            if fld in brief.fields and not any(q.ask_if(vals) for q in QUESTIONS if q.field == fld):
                del brief.fields[fld]
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
            own_content_only = (new.fields.get('content_only') or {})
            stated_content_only = (own_content_only.get('value') if own_content_only.get('source') in ('answer', 'message')
                                   else None)
            new.fields[q.field] = {'value': value[:2000], 'source': 'answer', 'question_id': qid, 'confidence': 'confirmed'}
            if qid == 'personal_data' and value == 'yes' and stated_content_only == 'yes':
                new.hints['storage_conflict'] = 'yes'           # asked (storage_intent); nothing is dropped meanwhile
            if qid == 'storage_intent':
                new.hints.pop('storage_conflict', None)
                if value == 'business':
                    new.fields['personal_data'] = {'value': 'no', 'source': 'answer', 'question_id': qid,
                                                   'confidence': 'confirmed'}
                    new.fields['content_only'] = {'value': 'yes', 'source': 'answer', 'question_id': qid,
                                                  'confidence': 'confirmed'}
                else:
                    new.fields['content_only'] = {'value': 'no', 'source': 'answer', 'question_id': qid,
                                                  'confidence': 'confirmed'}
            # The answer decides the covered field too (one question). Michael 2026-11-14 (b4): the LATEST answer wins.
            # Before, a personal_data already confirmed "yes" was kept, so "לא לשמור פרטים אישיים" changed nothing and
            # the conversation asked again; access_scope is only asked BECAUSE personal_data is "yes", so it always
            # met a confirmed value and its "no" was never applied.
            for covered in COVERS.get(q.field, ()):
                if covered == 'personal_data':
                    new.fields[covered] = {'value': 'no' if value == 'no_personal' else 'yes', 'source': 'answer',
                                           'question_id': qid, 'confidence': 'confirmed'}
        if qid in new.skipped:
            new.skipped.remove(qid)
    _drop_inapplicable(new)
    if 'logo' in answers and new.values().get('logo') not in ('later', 'uploaded'):
        new.assets.pop('logo', None)
    return _settle_image(brief, new, answers)


IMAGE_FIELDS = ('image_kind', 'image_identity', 'image_use', 'image_place')


def next_image_question(brief: 'Brief') -> 'Question | None':
    """The next question of the image's role, in order: what is in it -> who/what exactly -> what to do with it."""
    ids = {q.id for q in IMAGE_QUESTIONS}
    return next((q for q in pending(brief) if q.id in ids), None)


def _settle_image(before: 'Brief', new: 'Brief', answers: Mapping[str, str]) -> 'Brief':
    """The role of an uploaded image, in order (Michael 2026-11-15): a new kind asks who/what again and what to do
    again; "my logo" takes the existing logo path; "change it" is not available yet -- it is NOT recorded (the
    question stays open and the reply says so), never turned into a silent "as is"."""
    if 'image_kind' in answers and before.values().get('image_kind') != new.values().get('image_kind'):
        for f in ('image_identity', 'image_use'):
            new.fields.pop(f, None)
    if new.values().get('image_kind') == 'logo' and new.assets.get('image'):
        img = new.assets.pop('image')
        for f in IMAGE_FIELDS:
            new.fields.pop(f, None)
        new.assets['logo'] = {k: img[k] for k in ('id', 'sha256', 'mime', 'size_bytes') if k in img}
        new.fields['logo'] = {'value': 'uploaded', 'source': 'answer', 'question_id': 'image_kind', 'confidence': 'confirmed'}
    if new.values().get('image_use') == 'change':
        new.fields.pop('image_use', None)
        new.hints['image_change'] = 'asked'
    new.hints.pop('image_hero_taken', None)
    v, img = new.values(), new.assets.get('image')
    if img and v.get('image_kind') in _KIND_HE and v.get('image_identity') and v.get('image_use') in ('as_is', 'inspiration'):
        place = v.get('image_place') if v['image_use'] == 'as_is' else None
        if v['image_use'] == 'as_is' and not place:
            return new                                   # "where" is the next question
        if place == 'hero' and main_image(new) is not None:
            new.fields.pop('image_place', None)          # one main image per page: asked again, said why
            new.hints['image_hero_taken'] = 'yes'
            return new
        role = image_role(new)
        new.assets['images'] = list(new.assets.get('images') or ()) + [
            {**{k: img.get(k) for k in ('id', 'sha256', 'mime', 'size_bytes', 'width', 'height')},
             'kind': role['kind'], 'alt': role['alt'], 'use': v['image_use'], **({'place': place} if place else {})}]
        new.assets.pop('image')                          # decided: the next upload starts a new role
        for f in IMAGE_FIELDS:
            new.fields.pop(f, None)
    return new


def pending(brief: Brief) -> list[Question]:
    vals = _ctx(brief)
    return [q for q in QUESTIONS if q.field not in brief.fields and q.id not in brief.skipped and q.ask_if(vals)]


def panel_group(brief: Brief, limit: int = 4) -> tuple[str | None, list[Question]]:
    """What the Requirements panel asks next -- the same source as the chat (warehouse 113, owner 2026-11-16). While an
    uploaded image's role is open, the chat asks exactly that one question, so the panel shows only it: never two
    different questions open at once in two places."""
    image_q = next_image_question(brief)
    if image_q is not None:
        return image_q.group, [image_q]
    return next_group(brief, limit)


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
    return out


def must_ask(brief: Brief) -> list[Question]:
    """C6: catalog questions that stay open even when the detector has nothing material left -- the fallback.
    A security/privacy choice (intake.agent.material), a question that cannot be delegated, or one with no honest
    default (e.g. the product language of an Arabic request) is never filled as an assumption."""
    from .intake.agent import material                     # lazy: intake.agent imports this module
    vals = brief.values()
    return [q for q in pending(brief)
            if material(q.field, vals) or not q.delegable or q.recommended is None
            or _recommended(q, brief, brief.hints) is None]


def catalog_complete(brief: Brief) -> bool:
    """The catalog's own rule (every catalog question answered, no contradiction). Since C6 it decides nothing on a
    detector-led brief; it only says when a provisional plan can already be shown (e.g. to surface a blocker early)."""
    return not pending(brief) and not contradictions(brief)


def complete(brief: Brief) -> bool:
    if brief.detector:                                     # C6: the detector decides; the catalog is the fallback
        return not brief.open_material and not contradictions(brief) and not must_ask(brief)
    return not pending(brief) and not contradictions(brief)


def missing(brief: Brief) -> dict:
    """O10 (founder 2026-10-21): what keeps the brief from being complete, so the gate says WHAT is missing, not only
    that something is. Same two sources as complete(): the pending questions and the contradictions."""
    open_qs = must_ask(brief) if brief.detector else pending(brief)
    return {'pending': [{'id': q.id, 'group': q.group, 'he': q.he, 'en': q.en} for q in open_qs]
                       + [{'id': f, 'group': 'detector', 'he': f, 'en': f} for f in (brief.open_material if brief.detector else ())
                          if f not in {q.id for q in open_qs}],
            'contradictions': contradictions(brief)}


# ---- what the builders receive ----------------------------------------------

_COLOR_HEX = {'blue': '#1e40af', 'green': '#15803d', 'purple': '#7c3aed', 'orange': '#c2410c', 'teal': '#0f766e',
              'neutral': '#334155', 'white': '#ffffff', 'black': '#000000', 'red': '#dc2626',
              'yellow': '#facc15', 'pink': '#ec4899', 'cream': '#fffdd0', 'gold': '#ffd700', 'gray': '#808080',
              # CEO 2026-11-09: the cafe brief said "חום, קרם וירוק" and the summary showed only green.
              'brown': '#6b4226', 'beige': '#e8dcc4', 'navy': '#1e3a5f', 'burgundy': '#7f1d1d',
              'lightblue': '#7dd3fc', 'silver': '#c0c0c0'}
_COLOUR_ALIASES = {'כחול': 'blue', 'ירוק': 'green', 'סגול': 'purple', 'כתום': 'orange',
                   'טורקיז': 'teal', 'לבן': 'white', 'שחור': 'black', 'אדום': 'red', 'צהוב': 'yellow',
                   'ורוד': 'pink', 'שמנת': 'cream', 'זהב': 'gold', 'אפור': 'gray', 'grey': 'gray',
                   'turquoise': 'teal', 'חום': 'brown', 'קרם': 'cream', "בז'": 'beige', 'בז׳': 'beige',
                   'בורדו': 'burgundy', 'נייבי': 'navy', 'כחול כהה': 'navy', 'תכלת': 'lightblue',
                   'light blue': 'lightblue', **{name: name for name in _COLOR_HEX}}


def colour_palette(text: str, *, preserve_words: bool = False) -> list[str]:
    """Ordered, bounded tokens from stated colour words or hex colours."""
    words = '|'.join(re.escape(word) for word in sorted(_COLOUR_ALIASES, key=len, reverse=True))   # "כחול כהה" before "כחול"
    pattern = r'(#[0-9a-f]{6}\b|#[0-9a-f]{3}\b)|(?<!\w)(?:וב|ו|ב)?(' + words + r')(?!\w)'
    tokens = []
    words_seen = []
    for match in re.finditer(pattern, text or '', re.I):
        token = match.group(1).lower() if match.group(1) else _COLOUR_ALIASES[match.group(2).lower()]
        if token not in tokens:
            tokens.append(token)
            words_seen.append((match.group(1) or match.group(2)).lower())
    return (words_seen if preserve_words else tokens)[:6]


def palette_css(text: str) -> list[str]:
    return [_COLOR_HEX.get(token, token) for token in colour_palette(text)]
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


def stores_by_own_answer(brief) -> str | None:
    """The customer's OWN answer that already says the product stores records, or None. Each of these also makes the
    content_only question inapplicable, so without this the brief carried no persistence decision at all: the build
    contract then asked "does the site store data?" with no card, and nothing the customer typed could answer it
    (2026-11-16). A delegated or defaulted value is not the customer's answer and decides nothing."""
    own = {k: f.get('value') for k, f in brief.fields.items() if f.get('source') in ('answer', 'message')}
    if own.get('access_scope') == 'add_login':
        return 'access_scope=add_login'
    if own.get('login') in ('simple', 'roles'):
        return f"login={own['login']}"
    if own.get('personal_data') == 'yes' and brief.values().get('access_scope') != 'no_personal':
        return 'personal_data=yes'
    return None


# #335 (Michael 2026-11-13): facts the customer stated in ANY message, verbatim, bound into the approved request.
CUSTOMER_FACTS_PREFIX = ('Customer facts (the customer\'s own words from the conversation; show exactly these '
                         'values and never other or additional ones): ')


def customer_text(brief: Brief) -> str:
    """The customer's own words: the request and the fact spans from every later message (#335)."""
    return '\n'.join([brief.prompt or ''] + list((brief.assets.get('facts') or {}).get('spans') or ()))


def _facts(brief: Brief) -> dict:
    f = brief.assets.get('facts') or {}
    return {'spans': list(f.get('spans') or ()), 'needs': list(f.get('needs') or ()),
            'waived': list(f.get('waived') or ())}


def _store_facts(brief: Brief, facts: dict) -> None:
    kept = {k: v for k, v in facts.items() if v}          # empty lists are not stored (no fingerprint change)
    if kept:
        brief.assets['facts'] = kept
    else:
        brief.assets.pop('facts', None)


# task 62 (the owner's build prj_9c357UySW645bg, 2026-11-22): the agent asked "מה מספר הוואטסאפ שתרצו שיופיע באתר?" in
# its own words, the customer answered "0503456723", and the bare span left the content route two main phones
# (phone_not_one -> the old path). A WhatsApp number keeps its role: a mobile number the customer labelled WhatsApp keeps
# the label in its span, and a bare number answering a question about WhatsApp is that label's answer.
WHATSAPP_LABEL = 'וואטסאפ: '
_WA_WORD = re.compile(r'וואטסאפ|ווטסאפ|וואצאפ|ווצאפ|whats\s*app', re.I)
_WA_BEFORE = re.compile(r'(?:וואטסאפ|ווטסאפ|וואצאפ|ווצאפ|whats\s*app)[^\d\n.!?;]{0,15}$', re.I)
_OTHER_PHONE_WORD = re.compile(r'טלפון|נייד|קווי|להתקשר|חיוג|phone|mobile|landline|call', re.I)


def answer_in_context(message: str, asked_before: str | None) -> str:
    """The customer's message as the facts read it: a message that is only a phone number, answering a question whose
    last sentence asks about WhatsApp and no other phone, is "וואטסאפ: <number>". Anything else is unchanged."""
    from .fact_canon import _PHONE, parse_phone
    text = (message or '').strip().rstrip('.!')
    questions = re.findall(r'[^.!?\n]*\?', asked_before or '')
    last = questions[-1] if questions else ''
    if not (_WA_WORD.search(last) and not _OTHER_PHONE_WORD.search(_WA_WORD.sub(' ', last))):
        return message
    m = _PHONE.fullmatch(text)
    return WHATSAPP_LABEL + m.group(0) if m and parse_phone(m.group(0)).ok else message


def _labelled_spans(text: str, spans: list[str]) -> list[str]:
    """fact_spans(text), with a mobile number the customer labelled WhatsApp ("וואטסאפ: 050-...") kept with its label."""
    from .fact_canon import _PHONE, parse_phone
    out = []
    for span in spans:
        at = text.find(span)
        p = parse_phone(span) if _PHONE.fullmatch(span) else None
        labelled = (at > 0 and p is not None and p.ok and p.kind == 'mobile'
                    and _WA_BEFORE.search(text[max(0, at - 25):at])
                    and not _OTHER_PHONE_WORD.search(_WA_BEFORE.search(text[max(0, at - 25):at]).group(0)))
        out.append(WHATSAPP_LABEL + span if labelled else span)
    return out


def note_customer_texts(brief: Brief, texts) -> bool:
    """Merge what the customer's own messages state into the brief (Michael 2026-11-13): the fact spans (phone,
    e-mail, address, hours) and what the page needs (a call button -> phone, an hours section -> hours), from EVERY
    message given. Idempotent: the same messages never change the brief twice. Returns whether it changed."""
    from .fact_canon import fact_spans, needs_in
    facts = _facts(brief)
    before = json.dumps(facts, sort_keys=True, ensure_ascii=False)
    own = needs_in(brief.prompt)                           # read from the request itself: not stored again
    for text in texts:
        clean = ' '.join((text or '').split())
        facts['spans'] += [x for x in _labelled_spans(clean, fact_spans(text or '')) if x not in facts['spans']]
        facts['needs'] += [k for k in needs_in(text or '') if k not in facts['needs'] and k not in own]
    if json.dumps(facts, sort_keys=True, ensure_ascii=False) == before:
        return False
    _store_facts(brief, facts)
    return True


def customer_messages(messages) -> list[str]:
    """The stored customer messages' text, in the order the store returns them. A platform LABEL stored on the
    customer's side ("📎 a handwritten note", "I approved the draft" -- warehouse 128) is not their words. A bare number
    answering a question about WhatsApp is read with that label (answer_in_context)."""
    out, asked = [], None
    for m in messages or ():
        if m.get('role') == 'assistant':
            asked = str(m.get('content') or '')
        elif m.get('role') == 'customer' and not (m.get('interpretation') or {}).get('label'):
            out.append(answer_in_context(str(m.get('content') or ''), asked))
    return out


def missing_facts(brief: Brief) -> tuple[list[str], list[str]]:
    """(needed facts the customer gave neither a value nor a waiver for, needed facts they waived)."""
    from .fact_canon import build_canon, missing_needed
    facts, customer = _facts(brief), customer_text(brief)
    missing = missing_needed(customer, build_canon(customer), facts['needs'])
    return [k for k in missing if k not in facts['waived']], [k for k in missing if k in facts['waived']]


def waive_missing(brief: Brief) -> list[str]:
    """The customer ticked "build without the missing details": record exactly which facts they gave up."""
    open_, _ = missing_facts(brief)
    if open_:
        facts = _facts(brief)
        facts['waived'] += [k for k in open_ if k not in facts['waived']]
        _store_facts(brief, facts)
    return open_


def gate_canon(brief: Brief, lang: str = 'he') -> dict:
    """The fact canon as gate 1 shows it for this brief (one place: gate 1, approve_spec, build admission)."""
    from .fact_canon import gate_view
    facts = _facts(brief)
    view = gate_view(brief.prompt + '\n' + requirements_text(brief), customer_text=customer_text(brief),
                     family='website' if is_website(brief) else 'app', lang=lang,
                     needs=facts['needs'], waived=facts['waived'])
    images = image_canon_lines(brief, lang)
    if images:   # Michael 2026-11-15: the image's role is part of what the customer approves
        view['lines'] = list(view['lines']) + images
    return view


def approved_windows(brief: 'Brief') -> list[str]:
    """The in-page windows the customer approved (A2 step 9): `fields.windows`, set by the customer only (an answer or
    their own message). An unknown window id raises -- never silently dropped."""
    f = brief.fields.get('windows') or {}
    if f.get('source') not in ('answer', 'message'):
        return []
    from .window_catalog import known
    value = f.get('value') or []
    ids = value if isinstance(value, list) else [x.strip() for x in str(value).split(',') if x.strip()]
    return [known(w).id for w in ids]


def rejected_windows(brief: 'Brief') -> list[str]:
    """The windows the customer rejected on the approval screen (owner 2026-11-16): never built."""
    f = brief.fields.get('windows_rejected') or {}
    from .window_catalog import known
    customer = f.get('source') in ('answer', 'message')       # only the customer rejects a window
    return [known(w).id for w in (f.get('value') or [])] if customer else []


def decide_windows(brief: 'Brief', decisions: dict) -> bool:
    """Record the customer's approve/reject of each offered window (the approval screen). `decisions` maps a window id
    to True (approved) or False (rejected); an id not in it keeps its earlier decision. An unknown id raises KeyError
    and a value that is not a bool raises ValueError -- nothing is guessed. Returns True when the brief changed."""
    from .window_catalog import CATALOG, known
    for wid, ok in (decisions or {}).items():
        known(wid)
        if not isinstance(ok, bool):
            raise ValueError(f'window {wid!r}: the decision must be true or false, not {ok!r}')
    approved, rejected = set(approved_windows(brief)), set(rejected_windows(brief))
    for wid, ok in (decisions or {}).items():
        (approved if ok else rejected).add(wid)
        (rejected if ok else approved).discard(wid)
    before = (approved_windows(brief), rejected_windows(brief))
    after = ([w for w in CATALOG if w in approved], [w for w in CATALOG if w in rejected])
    if after == before:
        return False
    for key, value in zip(('windows', 'windows_rejected'), after):
        brief.fields[key] = {'value': value, 'source': 'answer', 'question_id': 'windows', 'confidence': 'confirmed'}
    return True


def window_offer(brief: 'Brief', lang: str = 'he') -> list[dict]:
    """What the approval screen offers: the catalogue windows the request gives a reason for (and every one already
    decided), each with its benefit and the current decision, for a website brief; nothing for other products."""
    if not is_website(brief):
        return []
    from .window_catalog import offer
    out = offer(lang, approved_windows(brief), rejected_windows(brief), text=brief.prompt)   # only what fits
    v = brief.values()
    if _content_only(v, 'none' if v.get('login') == 'none' else 'x') and not _question_channel(brief.prompt):
        # DECISIONS 14 (a), 2026-11-22: the question widget opens a form, and a content-only site saves nothing, so with
        # no WhatsApp and no e-mail the question has nowhere to go -- the owner's build bld_ab78f528 failed the browser
        # check on exactly that form (dead_form 'q-form'). It is not offered; a decision already made stays shown.
        out = [w for w in out if w['id'] != 'question_widget' or w['state'] is not None]
    return out


def _question_channel(prompt: str) -> bool:
    """A channel the question widget can hand a question to: the customer's WhatsApp number or e-mail address, read by
    the content route's own fact sheet (a negated WhatsApp, 'אין לנו וואטסאפ', is no channel)."""
    from .site_content.facts import fact_sheet
    sheet = fact_sheet(prompt or '')
    return bool(sheet.whatsapp or sheet.email)


def requirements_text(brief: Brief) -> str:
    """Binding block appended to the build prompt (English for the models,
    user wording quoted). Includes the brief fingerprint so the contract, and
    hence the approval, is bound to this exact revision."""
    v = brief.values()
    lines = ['', BRIEF_MARKER + ' (binding; fingerprint ' + brief.fingerprint()[:16] + ') ---']
    facts = list((brief.assets.get('facts') or {}).get('spans') or ())
    if facts:   # #335: the customer's own words for phone / e-mail / address / hours, from every message
        lines.append(CUSTOMER_FACTS_PREFIX + ' | '.join(facts))
    # #335 (c): a fact the page needs that the customer never gave -- the approved spec says to OMIT that part
    # The spec says to OMIT a part ONLY for a fact the customer waived (ticked the box; assets.facts.waived). A
    # needed fact with no waiver is listed as MISSING: a build must not start on it (approval_flow.spec_valid), and
    # if one does, QA stops and asks (d) -- never a silent omission (production 2026-11-13, the cafe).
    from .fact_canon import MISSING_PREFIX, OMIT, build_canon, needs_in
    unwaived, missing = missing_facts(brief)
    if 'phone' in set(_facts(brief)['needs']) | set(needs_in(brief.prompt)) and 'phone' not in unwaived + missing:
        # production bld_cf406df6: the "הזמנת שולחן" button was dead. The customer said it dials their number.
        phone = sorted(build_canon(customer_text(brief)).values('phone'))
        if phone:
            lines.append(f'Call button: the button the customer asked for dials their phone -- a tel: link to {phone[0]}; '
                         'never a dead button or a "#" link.')
    if unwaived:
        lines.append(MISSING_PREFIX + '; '.join(unwaived) + '.')
    if missing:
        lines.append('Not given by the customer (approved without it; never invent it): '
                     + '; '.join(OMIT[k] for k in missing) + '.')
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
    # R1: the customer's own answer is bound as a typed decision (product_architect reads it via persistence.resolve).
    # Only a non-delegated answer is ever in fields['content_only'] (see the question's comment above).
    from .persistence import NONE as _P_NONE, RECORDS as _P_RECORDS, decision_line as _decision_line
    if _content_only(v, login):
        lines.append(_decision_line(_P_NONE))
    elif v.get('content_only') == 'no' or stores_by_own_answer(brief):
        lines.append(_decision_line(_P_RECORDS))
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
    style, color, font = v.get('style', 'clean'), v.get('color', 'category'), v.get('font', 'heebo')
    tokens = palette_css(color)
    stated = (brief.fields.get('color') or {}).get('source') in ('answer', 'message') and color != 'category'
    if tokens and stated:
        colours = f'primary colour {tokens[0]}; palette {", ".join(tokens)}; requested colour description {color!r}'
    elif stated:
        colours = f'requested colour description {color!r}; resolve it to valid CSS colours'
    else:   # warehouse 105: no colour from the customer -> the business category's palette (vertical_palettes.json)
        from .vertical_palettes import design_colours
        colours = design_colours(brief.prompt + '\n' + customer_text(brief))
    lines.append(f'Design: style {style}; {colours}; font {_FONT.get(font, font)} '
                 '(load it from Google Fonts with a system fallback); define these as CSS custom properties.')
    if v.get('logo') == 'text':
        lines.append('Logo: a text logo with the product name in the header.')
    logo = brief.assets.get('logo')
    if logo:
        lines.append(f'Uploaded logo attachment: {logo["id"]}; sha256={logo["sha256"]}. '
                     'Use the original uploaded logo in a visible img element with src="148ai-asset://logo". '
                     'The worker replaces this marker with the verified image bytes before tests; do not recreate the logo.')
    for n, img in enumerate(placed_images(brief), start=1):
        # Michael 2026-11-15: several images; each in the place the customer chose, its alt the customer's own words
        lines.append(f'{UPLOADED_IMAGE_PREFIX}{n} attachment: {img["id"]}; sha256={img["sha256"]}; '
                     f'src="{img["marker"]}"; placement: {img["place"]}; role {img["kind"]}: "{img["alt"]}". '
                     f"The customer's own photo: use it AS IS as {_SECTION[img['place']]}, in a visible img element "
                     'with exactly this src and this alt. Do not generate, draw, edit or replace it; the worker replaces '
                     'the marker with the verified image bytes before tests.')
    for img in brief.assets.get('images') or ():
        if img.get('use') == 'inspiration':
            lines.append(f'Uploaded image {img["id"]}: the customer chose inspiration only. Do not show it on the page.')
    from .intake.media_reading import requirements_line as _skeleton_line   # warehouse 128: an approved skeleton
    skeleton = _skeleton_line(brief)
    if skeleton:
        lines.append(skeleton)
    delegated = [k for k, f in brief.fields.items() if f.get('source') == 'delegated']
    if delegated:
        lines.append('Chosen by 148AI on the user\'s behalf (recommended defaults): ' + ', '.join(sorted(delegated)) + '.')
    if brief.semantic_decisions:
        from .semantic_capabilities import encode_approved
        lines.append(encode_approved(brief.semantic_decisions))
    excluded = customer_exclusions(brief)
    excluded = excluded + image_exclusions(brief)    # the customer's photo shown as is: nothing is generated
    if excluded:   # 77: bound into the fingerprinted contract; product_architect reads only this generated line
        lines.append(CUSTOMER_EXCLUSIONS_PREFIX + json.dumps(sorted(excluded)))
    from .window_catalog import prompt_lines, rejected_lines   # A2 step 8: the spec of every approved window
    lines.extend(prompt_lines(approved_windows(brief)))
    lines.extend(rejected_lines(rejected_windows(brief)))      # owner 2026-11-16: a rejected window is not built
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
    # Plain-language semantic review before approval. Do not expose internal
    # capability keys, model diagnostics or provider pricing to the customer.
    names = {
        'target.agent': ('סוכן AI', 'AI agent'),
        'ai.agent.tools': ('כלי פעולה של סוכן AI', 'AI agent tools'),
        'ai.agent.memory': ('זיכרון סוכן AI', 'AI agent memory'),
        'ai.agent.eval': ('בדיקות סוכן AI', 'AI agent evaluation'),
        'integration.maps': ('מפות אינטראקטיביות', 'Interactive maps'),
        'integration.email': ('שליחת דואר אלקטרוני', 'Email sending'),
        'integration.webhook': ('התממשקות Webhook', 'Webhook integration'),
        'integration.messaging': ('מערכת הודעות', 'Messaging service'),
        'media.audio.tts': ('יצירת קול וקריינות', 'Speech and narration'),
        'media.audio.stt': ('תמלול דיבור', 'Speech recognition'),
        'media.audio.realtime_voice': ('שיחה קולית בזמן אמת', 'Real-time voice'),
        'media.image.generate': ('יצירת תמונות', 'Image generation'),
        'media.video.generate': ('יצירת וידאו', 'Video generation'),
        'target.automation': ('אוטומציה', 'Automation'),
    }
    semantic_review = [
        {'label': names[d['key']][0 if he else 1],
         'included': d['decision'] == 'required',
         'uncertain': d['decision'] == 'uncertain',
         'evidence': str(d['evidence'])[:160],
         'reason': str(d['reason'])[:180]}
        for d in brief.semantic_decisions if isinstance(d, dict) and d.get('key') in names
        and d.get('decision') in ('required','not_required','uncertain')
    ]
    return {'goal': v.get('goal') or brief.prompt[:200], 'sections': sections,
            'group_titles': {g: GROUP_TITLES[g][0 if he else 1] for g in GROUPS},
            'included': included, 'excluded': excluded, 'assumptions': assumptions,
            'semantic_review': semantic_review,
            'contradictions': contradictions(brief), 'complete': complete(brief)}
