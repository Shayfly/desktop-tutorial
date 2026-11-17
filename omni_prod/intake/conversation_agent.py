"""The conversation agent, phase 1 (the owner, 2026-11-17: "I don't want the customer talking to a ready-made
questionnaire; the first conversation is with a live model that knows the work").

With OMNI_INTAKE_AGENT=1 the customer never sees a question card. Every question -- the ones only the customer may
answer included (does the site store visitors' details, sign-in, who sees personal details) -- is asked in words, in
the reply, and the customer answers by typing. The deterministic layer is unchanged underneath: it still decides what
is open, what is material and when the brief is complete, and the two approvals (spec, budget) stay server-bound
buttons -- they protect the customer's money, they are not a questionnaire.

A typed answer counts for a question only when that question was asked in the previous turn, and only when:
  1. the customer's words name exactly one of its options (`typed_choice`, closed word lists per option), or
  2. the model proposed that field with high confidence and an evidence quote from this very message
     (the interpreter already drops a quote that is not in the message).
Otherwise nothing is set and the question stays open -- never a guess, never a default.
"""
from __future__ import annotations

import contextvars
import os
import re

FLAG = 'OMNI_INTAKE_AGENT'
ACCOUNTS = 'OMNI_INTAKE_AGENT_ACCOUNTS'
MAX_QUESTION_CHARS = 400
# The owner, 2026-11-17: the flag is per account -- the agent runs for the listed accounts only, everyone else keeps
# the conversation as it was, one environment change away. Production is not the laboratory.
_ACCOUNT: contextvars.ContextVar = contextvars.ContextVar('conversation_agent_account', default=None)


def for_account(account_id):
    """Set the account of the turn being answered; returns the token for `release`."""
    return _ACCOUNT.set(str(account_id) if account_id else None)


def release(token) -> None:
    _ACCOUNT.reset(token)


def enabled(account_id=None) -> bool:
    """The flag: '1' on for everyone, '0' or unset off, 'accounts' on only for the accounts in
    OMNI_INTAKE_AGENT_ACCOUNTS (comma separated). Any other value is an error, never a silent default."""
    value = os.environ.get(FLAG, '0').strip()
    if value not in ('0', '1', 'accounts'):
        raise ValueError(f'{FLAG} must be 0, 1 or accounts, not {value!r}')
    if value != 'accounts':
        return value == '1'
    allowed = {a.strip() for a in os.environ.get(ACCOUNTS, '').split(',') if a.strip()}
    if not allowed:
        raise ValueError(f'{FLAG}=accounts needs {ACCOUNTS}; none is listed')
    account = account_id if account_id is not None else _ACCOUNT.get()
    return account is not None and str(account) in allowed


# per question id: option -> the words that name it. A message naming two different options names none.
_YES = r'(?:^|\W)(?:כן|נכון|בטח|ודאי|כמובן|yes|yep|sure|correct)(?:\W|$)'
_NO = r'(?:^|\W)(?:לא|אין|בלי|no|nope|not)(?:\W|$)'
WORDS: dict[str, dict[str, str]] = {
    'personal_data': {'yes': _YES, 'no': _NO},
    'content_only': {'yes': _YES + r'|תוכן בלבד|רק מידע|רק להציג|לא שומר', 'no': r'(?:^|\W)(?:לא|no)(?:\W|$)|שומר|טופס|הרשמה|הזמנות'},
    'login': {'none': r'בלי (?:התחברות|כניסה|סיסמה)|אין צורך ב(?:התחברות|כניסה)|לא צריך (?:התחברות|כניסה)|no (?:login|sign-?in)',
              'simple': r'כניסה (?:פשוטה|עם סיסמה)|התחברות פשוטה|משתמש אחד|simple (?:login|sign-?in)',
              'roles': r'הרשאות|מנהל ועובד|תפקידים|roles'},
    'audience': {'internal': r'צוות|עובדים|פנימי|רק אני|internal|staff',
                 'public': r'לקוחות|ציבור|כולם|מבקרים|גולשים|public|customers|visitors',
                 'both': r'שניהם|גם וגם|both'},
    'storage_intent': {'business': r'רק פרטי העסק|פרטי העסק|הטלפון שלי|לא נשמר|business',
                       'visitors': r'פרטים של (?:מבקרים|לקוחות|גולשים)|טופס|לשמור פרטים|visitors|form'},
    'access_scope': {'internal_link': r'כלי פנימי|רק אנחנו|פנימי|internal',
                     'add_login': r'(?:להוסיף )?התחברות למנהל|כניסה למנהל|add (?:a )?login',
                     'no_personal': r'לא לשמור פרטים|בלי פרטים אישיים|no personal'},
    'unavailable': {'build_without': r'בלי זה|לבנות בלי|לוותר|build without',
                    'wait': r'לחכות|נחכה|wait'},
}


# Phrases that decide on their own, checked first: "לא שומרים כלום" contains "לא" and still means content only
# (conversation rehearsal 2026-11-17: "כן, רק להציג מידע ומחירים, לא שומרים כלום" named yes AND no, so nothing was
# set and the doors conversation dead-ended).
DECIDING: dict[str, tuple[tuple[str, str], ...]] = {
    'content_only': (('yes', r'תוכן בלבד|רק (?:להציג|מידע)|לא (?:שומר|שומרים|נשמר|נשמרים) כלום|לא שומר(?:ים)? (?:נתונים|פרטים)'),
                     ('no', r'(?:יש|צריך|עם) (?:טופס|הרשמה|הזמנות)|שומר(?:ים)? (?:פרטים|נתונים|הזמנות)')),
    'personal_data': (('no', r'רק (?:הטלפון|הכתובת|פרטי העסק)|לא (?:שומר|שומרים|נשמר)'),),
}


# A question asked as yes/no ("האם צריך התחברות עם סיסמה?") is answered by a leading "לא" -- but only when the message
# names no option of its own ("לא, צריך הרשאות למנהל ועובד" names roles). The owner, 2026-11-17: "לא אני משנה את האתר
# דרך כאן בעתיד" was not read, the model's guess (roles) stayed and became a blocker. "לא יודע", "לא בטוח" and "לא משנה"
# are not a no.
LEADING_NO = r'^\s*(?:לא(?!\s+(?:יודע|יודעת|בטוח|בטוחה|הבנתי|ברור|משנה))|no(?!\s+idea)|nope)(?:\W|$)'
YES_NO_QUESTIONS = {'login': 'none'}


def typed_choice(question, text: str) -> str | None:
    """The option a typed message names for this question, or None (none named, or two different ones)."""
    words = WORDS.get(getattr(question, 'id', ''))
    t = (text or '').strip().lower()
    if not words or not t:
        return None
    deciding = [value for value, rx in DECIDING.get(question.id, ()) if re.search(rx, t, re.I)]
    if len(set(deciding)) == 1:
        return deciding[0]
    hits = {value for value, rx in words.items() if re.search(rx, t, re.I)}
    if len(hits) == 2 and {'yes', 'no'} <= hits:
        return None                                    # "כן... לא" -- not an answer
    if not hits and question.id in YES_NO_QUESTIONS and re.search(LEADING_NO, t, re.I):
        return YES_NO_QUESTIONS[question.id]
    return hits.pop() if len(hits) == 1 else None


def model_choice(question, interp) -> str | None:
    """The model's high-confidence proposal for this question's field, with an evidence quote from this message."""
    allowed = {o.value for o in getattr(question, 'options', ()) or ()}
    for p in getattr(interp, 'proposals', ()) or ():
        if p.field == question.field and p.confidence == 'high' and (p.evidence or '').strip() and p.value in allowed:
            return p.value
    return None


def asked_in_words(question, lang: str) -> str:
    """The question as one sentence of the reply."""
    text = (question.he if lang == 'he' else question.en).strip()
    return text[:MAX_QUESTION_CHARS]


def has_question(reply: str) -> bool:
    return '?' in (reply or '')


# Rehearsal 44126201300 (2026-11-17, the live model): a customer who wrote only "אתר" reached the approval in three
# turns -- nobody asked what the site is about, and the build would start from one word. A request names its subject
# when it says what the business or topic is: a quoted name, a catalogue category, or at least two words beyond the
# product word and filler (a phone or a street alone says where, not what).
SUBJECT_ID = 'subject'
_FILLER = frozenset('''
אתר אתרים דף דפים נחיתה אפליקציה אפליקציית מערכת תוכנה אפ app site website page landing
לי לנו את של עם בלי ללא כן לא רק גם זה זאת זו אני אנחנו אתם שלי שלנו שלך רוצה רוצים צריך צריכה צריכים
תבנה תבנו בנה לבנות תעשה תעשו לעשות תכין תכינו חדש חדשה פשוט פשוטה יפה יפים טוב טובה מהר בבקשה היי שלום
אפשר יש בשביל עבור כמו תדמית תדמיתי עסק לעסק העסק עסקי טלפון משהו קצת מאוד ממש איזה בסיסי בסיסית מקצועי מקצועית a an the for my me i we need want build make please
'''.split())
_WORDS = re.compile(r'[א-תA-Za-z]{2,}')
_QUOTED_NAME = re.compile(r'["״“”][^"״“”]{2,40}["״“”]')


def _content_words(text: str) -> list[str]:
    out = []
    for w in _WORDS.findall((text or '').lower()):
        bare = w[1:] if w[0] in 'הובשלמכ' and len(w) > 3 and w[1:] in _FILLER else w
        if w not in _FILLER and bare not in _FILLER:
            out.append(w)
    return out


def names_a_subject(text: str) -> bool:
    """Does the request say what the site or app is about?"""
    text = text or ''
    if _QUOTED_NAME.search(text):
        return True
    from ..vertical_palettes import category_of
    if category_of(text):
        return True
    return len(_content_words(text)) >= 2


SUBJECT_QUESTION = {'he': 'ספרו לי במשפט או שניים על מה זה: שם העסק או הנושא, מה אתם עושים, ולמי זה מיועד?',
                    'en': 'Tell me in a sentence or two what this is about: the business or topic, what you do, and '
                          'who it is for?'}
