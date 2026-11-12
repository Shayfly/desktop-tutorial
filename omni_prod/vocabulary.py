"""Hebrew-aware keyword matching (CEO 2026-11-10: "we fall a lot on words the system does not know").

Every deterministic keyword list used to match by substring. In Hebrew that is wrong twice over:
  * short stems hide inside unrelated words -- "בטל" in "בטלפון" (on the phone), "חם" in "לחם" (bread),
    "שמח" in "נשמח" (we'll be glad), "העלאת" in "העלאת מחירים" (a price rise), "כל יום" in "פתוח כל יום";
  * a real word arrives with one-letter prefixes (ו/ב/ל/ה/ש/מ/כ and their pairs) and inflections the list
    never had, so the system "does not know" it.

`terms(...)` builds one regex for a vocabulary. Each entry is a whole word or phrase that may carry the usual
Hebrew prefixes; an entry ending in "*" is a stem and may also carry a suffix ("הזמנ*" = הזמנה, הזמנות, להזמין is
listed separately). English entries match on word boundaries; "*" allows any ending. Nothing matches inside a
longer word, so "בטל" can never be found in "בטלפון" again.
"""
from __future__ import annotations

import re
from functools import lru_cache

HE = '֐-׿'
# Common Hebrew one/two-letter prefixes: and, in, to, the, that, from, as, and the pairs they form.
_PREFIX = r'(?:ו|ש|כש|מ|ב|ל|כ|ה|וה|וב|ול|ומ|וש|שה|שב|של|שמ|מה|בה|לה|כה|וכש)?'
_GERESH = '[\'׳]'
_GERSHAYIM = '["״]'


def _entry(word: str) -> str:
    stem = word.endswith('*')
    w = word[:-1] if stem else word
    body = re.escape(w).replace(r'\ ', r'[\s\-]+').replace("'", _GERESH).replace('"', _GERSHAYIM)
    if re.search(f'[{HE}]', w):
        tail = f'[{HE}]*' if stem else ''
        return f'{_PREFIX}{body}{tail}'
    tail = r'\w*' if stem else ''
    return f'{body}{tail}'


@lru_cache(maxsize=None)
def _pattern(words: tuple[str, ...]) -> str:
    # Longest first, so "כחול כהה" wins over "כחול" and "ביטול הזמנה" over "ביטול".
    alts = '|'.join(_entry(w) for w in sorted(set(words), key=len, reverse=True))
    return f'(?<![\\w{HE}])(?:{alts})(?![\\w{HE}])'


def terms(*words: str) -> str:
    """A regex (string) matching any of the words as whole words, with Hebrew prefixes. Use with re.I."""
    return _pattern(tuple(words))


@lru_cache(maxsize=None)
def _compiled(words: tuple[str, ...]):
    return re.compile(_pattern(words), re.I)


def has_any(text: str, words) -> bool:
    return bool(_compiled(tuple(words)).search(text or ''))


def first(text: str, words):
    m = _compiled(tuple(words)).search(text or '')
    return m.group(0) if m else None


# ------------------------------------------------------------------ shared vocabularies
# What a product promises to do with its records (acceptance: data_update / data_delete become mandatory).
UPDATE_WORDS = (
    'edit*', 'update*', 'change', 'changes', 'changing', 'rename*', 'mark', 'marks', 'marked', 'done', 'complete',
    'completed', 'completion', 'toggle*', 'status', 'statuses', 'modify', 'reschedule*',
    'עריכה', 'עריכת', 'לערוך', 'ערוך', 'ערכו', 'עורך', 'עורכת', 'נערך', 'עדכון', 'עדכונים', 'לעדכן', 'עדכן', 'עדכנו',
    'מעדכן', 'מעדכנת', 'מתעדכן', 'שינוי', 'שינויים', 'לשנות', 'סימון', 'לסמן', 'סמן', 'סמנו',
    'מסמן', 'הושלם', 'הושלמה', 'בוצע', 'בוצעה', 'השלמה', 'סטטוס', 'סטטוסים', 'מצב המשימה', 'מצב ההזמנה',
    'מצב הטיפול', 'להזיז', 'הזזה', 'לדחות', 'דחייה', 'לתקן פרטים', 'תיקון פרטים',
)
DELETE_WORDS = (
    'delete*', 'remove*', 'cancel*', 'archive*', 'unsubscribe*',
    'מחיקה', 'מחיקת', 'למחוק', 'מחק', 'מחקו', 'מוחק', 'מוחקת', 'נמחק', 'נמחקת', 'למחיקה', 'להסיר', 'הסר', 'הסירו',
    'הסרה', 'הסרת', 'מסיר', 'ביטול', 'ביטולים', 'לבטל', 'בטל', 'בטלו', 'מבטל', 'מבטלת', 'בוטל', 'בוטלה', 'ארכיון',
    'לארכב', 'ארכוב', 'להוריד מהרשימה', 'הסרה מהרשימה', 'הסרה מרשימת',
)

# Infrastructure the architect adds only when the product itself needs it.
UPLOAD_WORDS = (
    'upload*', 'attachment*', 'file storage', 'store files', 'documents storage', 'file upload*',
    'העלאת קבצים', 'העלאת קובץ', 'העלאת תמונות', 'העלאת תמונה', 'העלאת מסמכים', 'העלאת מסמך', 'העלאת סרטונים',
    'להעלות קבצים', 'להעלות קובץ', 'להעלות תמונות', 'להעלות תמונה', 'להעלות מסמכים', 'להעלות מסמך', 'יעלו תמונות',
    'יעלו קבצים', 'צרופה', 'צרופות', 'קובץ מצורף', 'קבצים מצורפים', 'אחסון קבצים', 'גלריה שהמשתמשים מעלים',
)
SCHEDULE_WORDS = (
    'cron', 'recurring job*', 'background job*', 'scheduled job*', 'scheduled task*', 'daily digest', 'weekly digest',
    'reminder*', 'follow-up*', 'recurring', 'every day at', 'every morning at', 'every week on', 'nightly',
    'תזכורת', 'תזכורות', 'להזכיר', 'יזכיר', 'תזמון', 'מתוזמן', 'מתוזמנת', 'מתוזמנות', 'משימה מתוזמנת',
    'שליחה אוטומטית', 'דוח יומי', 'דוח שבועי', 'סיכום יומי', 'סיכום שבועי', 'כל יום בשעה', 'כל בוקר בשעה',
    'פעם ביום לשלוח', 'פעם בשבוע לשלוח',
)
OUTBOUND_CHANNEL_WORDS = (
    'email*', 'e-mail*', 'sms', 'webhook*', 'newsletter*', 'push notification*',
    'מייל', 'מיילים', 'אימייל', 'אימיילים', 'דוא"ל', 'דואל', 'הודעת sms', 'ניוזלטר', 'וובהוק',
)
# 2026-11-10: "משלוח" (food delivery) and "deliver" were outbound actions: a cafe with deliveries and an e-mail
# address got an outbound e-mail service. Only sending a message counts.
OUTBOUND_ACTION_WORDS = (
    'send', 'sends', 'sending', 'sent automatically', 'notify', 'notifies', 'notification*', 'mailing*',
    'automated email*', 'outbound', 'dispatch email*', 'email blast*',
    'שלח', 'שלחו', 'לשלוח', 'שולח', 'שולחת', 'שליחה', 'שליחת', 'יישלח', 'תישלח', 'נשלח', 'נשלחת', 'התראה',
    'התראות', 'להתריע', 'דיוור', 'דיוורים', 'עדכון במייל', 'עדכונים במייל', 'הודעה אוטומטית', 'הודעות אוטומטיות',
)

# Intake: which fields a message states.
WARM_STYLE_WORDS = ('warm', 'friendly', 'cozy', 'cosy', 'homey', 'אווירה חמה', 'חמים', 'חמימה', 'חמימות', 'מזמין',
                    'מזמינה', 'ביתי', 'ביתית', 'נעים', 'נעימה', 'אינטימי', 'אינטימית', 'משפחתי', 'משפחתית')
CLEAN_STYLE_WORDS = ('minimal*', 'clean', 'modern', 'sleek', 'נקי', 'נקייה', 'מינימליסטי', 'מינימליסטית',
                     'מינימליזם', 'מודרני', 'מודרנית', 'פשוט ונקי', 'אלגנטי', 'אלגנטית', 'מעוצב בפשטות', 'סקנדינבי')
FORMAL_STYLE_WORDS = ('formal', 'corporate', 'professional look', 'רשמי', 'רשמית', 'עסקי', 'עסקית', 'יוקרתי',
                      'יוקרתית', 'מכובד', 'מכובדת', 'ממלכתי')
PLAYFUL_STYLE_WORDS = ('playful', 'colorful', 'colourful', 'fun', 'צבעוני', 'צבעונית', 'שמח ועליז',
                       'עליז', 'עליזה', 'משעשע', 'משעשעת', 'שובב', 'שובבה', 'כיפי', 'כיפית', 'קליל', 'קלילה')
BOOKING_WORDS = (
    'booking*', 'appointment*', 'reservation*', 'schedul*', 'book a', 'book an',
    'תור', 'תורים', 'לקבוע תור', 'קביעת תור', 'קביעת תורים', 'זימון תור', 'זימון תורים', 'הזמנת מקום', 'הזמנת שולחן',
    'הזמנת חדר', 'הזמנת טיפול', 'מערכת הזמנות', 'הזמנת מקומות', 'הזמנת כרטיסים', 'הזמנה מראש', 'הזמנות מראש', 'שריון', 'לשריין', 'שריון מקום', 'פגישה', 'פגישות', 'לקבוע פגישה', 'יומן', 'רישום לשיעור',
    'הרשמה לשיעור', 'הרשמה לסדנה', 'משבצת', 'משבצות', 'מועד', 'מועדים', 'תאריך', 'תאריכים',
)
# Personal data is COLLECTED only when people leave it in the product, not when the business shows its own phone.
PERSONAL_DATA_COLLECT = (
    r'(?:(?:לאסוף|איסוף|לשמור|שמירת|ישאירו|השאירו|להשאיר|ימלאו|למלא|טופס|שדה|שדות|נרשמים|הנרשמים|יזינו|להזין|'
    r'collect|store|save|form|field|sign[- ]?up|register)[^.!?\n]{0,50}'
    r'(?:טלפון|נייד|מייל|אימייל|דוא"ל|כתובת|ת\.?ז|שם מלא|phone|e-?mail|address|full name))|'
    r'(?:(?:טלפון|נייד|מייל|אימייל|כתובת|phone|e-?mail|address)(?:ים)?\s+(?:של|of)\s+'
    r'(?:ה?לקוחות|ה?משתמשים|ה?נרשמים|ה?מטופלים|ה?תלמידים|ה?חברים|customers|users|members|patients|students))'
)
