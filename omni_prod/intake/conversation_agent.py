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

import os
import re

FLAG = 'OMNI_INTAKE_AGENT'
MAX_QUESTION_CHARS = 400


def enabled() -> bool:
    """The flag. '1' on, '0' or unset off; any other value is an error, never a silent default."""
    value = os.environ.get(FLAG, '0').strip()
    if value not in ('0', '1'):
        raise ValueError(f'{FLAG} must be 0 or 1, not {value!r}')
    return value == '1'


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


def typed_choice(question, text: str) -> str | None:
    """The option a typed message names for this question, or None (none named, or two different ones)."""
    words = WORDS.get(getattr(question, 'id', ''))
    t = (text or '').strip().lower()
    if not words or not t:
        return None
    hits = {value for value, rx in words.items() if re.search(rx, t, re.I)}
    if len(hits) == 2 and {'yes', 'no'} <= hits:
        return None                                    # "כן... לא" -- not an answer
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
