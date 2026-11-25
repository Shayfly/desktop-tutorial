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
# The owner, 2026-11-23: "לבטל את עניין התורות... הצ'אט לא נגמר לעולם והלקוח תמיד מדבר עם הצ'אט מתי שהוא רוצה".
# No turn cap: the 8-turn cap of 2026-11-18 ended the ShayFly conversation after 8 messages that cost $0.003 in all
# (intake_reservations, prj_5wRH_CceL2aSeQ). What still bounds the spend is money, not turns: the cost cap below per
# conversation (about 390 messages at that conversation's measured cost) and the daily budget, which pauses until the
# next day and closes nothing. None = no cap (budget.Caps.project_turns).
MAX_TURNS = None
# ... and at most $0.15 per conversation: the agent's own cap, never above the global OMNI_INTAKE_MODEL_BUDGET_USD (it is
# the smaller of the two), so raising the global cap for other accounts never raises the agent's (D10 review).
from decimal import Decimal as _D
MAX_COST_USD = _D('0.15')
# The owner, 2026-11-18: Sonnet for the conversation agent in production only; decision 10 (2026-11-17): when it is not
# available, the regular model, never below 70. On Venice that is an ordered list -- the first model Venice offers
# within the ceiling wins, chosen before any request (a reservation is one call, so this is not a second call). Both are
# tagged anonymized on Venice (IRON_LAWS א.1: the owner's decision is the explicit founder decision). The ceiling is the
# live list price of the first model, never above it, because every agent turn is quoted at the ceiling: Venice's
# pricing page, read 2026-11-18, claude-sonnet-5-5 $2.00 / $10.00 per 1M tokens (claude-haiku-5-5 $0.10 / $0.50).
# In code, not in an environment variable: the quote (Vercel) and the rehearsal (the worker) read the same source, and
# a change of the agent's model is the owner's decision, made in a reviewed change.
# The owner, 2026-11-19 (after the measurement, runs 44602428561..44616521276): openai-gpt-6-luna first -- 3/3
# conversations, 0 failed calls, $0.0011-0.0016 a conversation (Sonnet $0.029-0.041) -- and Sonnet when Venice does not
# offer luna. The ceiling stays Sonnet's list price so the fallback is never refused; a turn settles at its actual cost.
# Owner 2026-11-24, issue #523 (A1): Gemini Flash-Lite first; Haiku when the primary is ineligible. STAGED, not active:
# the 2026-11-19 order is measure, then switch. The rehearsal measures a model only when the worker's deployed code
# lists it in CANDIDATES below, so this profile stays the measured one (luna, then Sonnet) until both A1 models pass
# the live rehearsal as candidates; the switch is then these two lines (#524's values: the two A1 models, '0.38', '3.13').
VENICE_MODELS = ('openai-gpt-6-luna', 'claude-sonnet-5-5')
VENICE_CEILING_USD_PER_M = ('2', '10')


def venice_profile() -> dict:
    """The agent's Venice profile, as budget.quote takes it."""
    from decimal import Decimal
    return {'models': VENICE_MODELS, 'ceiling': tuple(Decimal(x) for x in VENICE_CEILING_USD_PER_M), 'select': 'order'}


# The owner, 2026-11-19: measure cheap Venice models for the conversation agent before choosing one ("a model inside
# Venice that is free or very cheap and good at understanding the customer"). REHEARSAL ONLY: production quotes with
# venice_profile() above, and a change of the agent's model stays the owner's decision. One model per candidate, its
# ceiling = its list price on Venice's pricing page (docs/venice_prices_snapshot.md, read 2026-10-19): if Venice now
# asks more, select_model refuses it before any request -- loud, never a pricier call.
CANDIDATES = {
    'gemini-3-5-flash-lite': ('0.38', '3.13'),
    'deepseek-v4-flash': ('0.14', '0.28'),
    'openai-gpt-oss-120b': ('0.07', '0.30'),
    'qwen3-235b-a22b-instruct-2507': ('0.15', '0.75'),
    'openai-gpt-6-luna': ('0.10', '0.50'),
    'claude-haiku-5-5': ('0.10', '0.50'),
}


def candidate_profile(model: str) -> dict:
    """One candidate's Venice profile for a rehearsal. An unknown name raises: never a free-typed model or price."""
    from decimal import Decimal
    if model not in CANDIDATES:
        raise ValueError(f'unknown candidate {model!r}; known: {sorted(CANDIDATES)}')
    return {'models': (model,), 'ceiling': tuple(Decimal(x) for x in CANDIDATES[model]), 'select': 'order'}
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
    'content_only': (('yes', r'תוכן בלבד|רק (?:להציג|מידע)|(?:לא|בלי) (?:ל)?(?:שמור|שומר|שומרים|נשמר|נשמרים) כלום|לא שומר(?:ים)? (?:נתונים|פרטים)'),
                     ('no', r'(?:יש|צריך|עם) (?:טופס|הרשמה|הזמנות)|שומר(?:ים)? (?:פרטים|נתונים|הזמנות)')),
    # Production 2026-11-19 (the owner's law-firm site): "כן, 03-5551234 נכון. לא לשמור פרטים" and "כן, אתר תוכן
    # בלבד ... בלי לשמור כלום" were not read -- "כן" confirmed the phone, "לא/בלי לשמור" answered this question --
    # and the agent asked the same question a third time. A negated "store" decides on its own.
    'personal_data': (('no', r'רק (?:הטלפון|הכתובת|פרטי העסק)|(?:לא|בלי|אל)\s+(?:ל|ת|י)?(?:שמור|שומר|שומרים|נשמר|נשמרים|שמרו|ישמרו|תשמרו)'
                             r'|שלא (?:נשמר|נשמרים|ישמרו|יישמרו|נשמור)'),),
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


# ---- the business name (2026-11-22). The content route builds a site only under a name the CUSTOMER declared -- a
# "שם העסק:" line or a span they quoted (site_content.facts; "the model never chooses the business name"). In 30 days of
# production (292 briefs) the conversation never asked for it, so a name written without quotes ("למורה ... נועה ברק")
# sent the build to the old path as name_not_declared. The agent now asks once, and the answer -- the customer's own
# words, never the model's -- joins the request as a "שם העסק:" line.
NAME_ID = 'business_name'
NAME_QUESTION = {'he': 'איך קוראים לעסק? כתבו את השם בדיוק כמו שהוא צריך להופיע באתר.',
                 'en': 'What is the business called? Write the name exactly as it should appear on the site.'}
_NAME_LEAD = re.compile(r'^\s*(?:(?:קוראים|קוראות)\s+(?:לו|לה|לנו|לי|לעסק)|השם(?:\s+(?:הוא|שלנו|שלי|של\s+העסק))?|שם\s+העסק(?:\s+הוא)?|'
                        r"(?:it'?s\s+)?called|the\s+name\s+is|name)\s*[:\-–]?\s*", re.I)
_NAME_REFUSED = re.compile(r'[0-9@/\\<>{}\[\]|]|https?:|www\.')
# an answer that hands the choice back, or says yes/no, is not a name (found by the conversation test: "תחליטו אתם על
# השאר" became "שם העסק: תחליטו אתם על השאר")
_NOT_A_NAME = re.compile(r'תחליט|תבחר|החליט|בחרו|לא\s+יודע|לא\s+משנה|מה\s+ש(?:בא|תרצו|מתאים)|על\s+השאר|בלי\s+שם|אין\s+(?:לי\s+|לנו\s+)?שם|'
                         r'דלג|^\s*(?:כן|לא|אין|אוקיי?|בסדר|סבבה|נכון|יאללה)\s*[.!]?\s*$|you\s+decide|whatever|'
                         r"^\s*(?:yes|no|none|ok|skip|idk)\s*[.!]?\s*$", re.I)
ASK_NAME_AT_MOST = 2       # then the approval opens without it, and the route says name_not_declared -- never a guess


def declares_a_name(customer_text: str) -> bool:
    """Does the customer's own text already give the business name the content route accepts: a "שם העסק:" line or a
    quoted span (fact_canon._NAME; site_content.facts.name_candidates)?"""
    from ..fact_canon import _NAME
    text = customer_text or ''
    return bool(_NAME.search(text) or _QUOTED_NAME.search(text))


def name_line(answer: str) -> str | None:
    """The "שם העסק:" line for a customer's answer to NAME_QUESTION, or None when the answer is not a name (a long
    sentence, digits, a link, a line break): the agent then asks again in the next turn, never guesses."""
    text = ' '.join((answer or '').split())
    if _NOT_A_NAME.search(text):
        return None
    text = _NAME_LEAD.sub('', text).strip().strip('"״“”\'').rstrip('.!').strip()
    if not 2 <= len(text) <= 40 or len(text.split()) > 6 or _NAME_REFUSED.search(text) or '\n' in (answer or '').strip():
        return None
    return f'שם העסק: {text}.'



# ---- colours for a business we do not know (the owner, 2026-11-22, DECISIONS). A recognised category takes its own
# palette (vertical_palettes). For any other business the agent asks once, in plain words: which colours they like,
# which should take the most space and which less -- or to leave it to us. Left to us, the palette is always one we
# have (vertical_palettes.design_colours: the nearest category, else the neutral one). The answer is recorded as the
# brief's "color" field with source "answer", so every choice stays in the build evidence (what a later learning step
# reads). Plural address: registration has no gender field (asked the owner).
COLOUR_ID = 'colour_preference'
COLOUR_QUESTION = {'he': 'יש צבעים שאתם אוהבים לאתר? כתבו איזה צבע יתפוס הכי הרבה מקום ואיזה פחות, '
                         'או כתבו "תבחרו אתם" ואבחר בשבילכם מתוך הצבעים שמתאימים לעסקים כמו שלכם.',
                   'en': 'Are there colours you like for the site? Write which colour should take the most space and '
                         'which less, or write "you choose" and I will pick from the palettes that fit businesses like '
                         'yours.'}
ASK_COLOUR_AT_MOST = 1     # one question; with no usable answer the build takes the nearest palette, said as such
_LEAVE_IT_TO_US = re.compile(r'תבחר|תחליט|בחר(?:ו)?\s+(?:לי|לנו|אתם|בשביל)|החליט|לא\s+משנה|לא\s+יודע|מה\s+ש(?:מתאים|תרצו|בא)|'
                             r'אין\s+(?:לי\s+|לנו\s+)?העדפ|בלי\s+העדפ|על\s+דעתכם|you\s+(?:choose|decide|pick)|'
                             r"whatever|no\s+preference|don'?t\s+mind|up\s+to\s+you", re.I)
_LESS = re.compile(r'מעט|קצת|פחות|נגיעו|משני|little|less|touch|accent|hint', re.I)


def colour_answer(answer: str) -> str | None:
    """The "color" field value for a customer's answer to COLOUR_QUESTION: the colours they named, the one that should
    take the most space first (a colour said with "a little / less" goes after the others), or "category" when they
    left it to us. None when the answer is neither: the question is not asked again, and the build takes the nearest
    palette. Never a colour the customer did not write."""
    from ..discovery import colour_palette
    text = ' '.join((answer or '').split())
    named = colour_palette(text, preserve_words=True)
    if not named:
        return 'category' if _LEAVE_IT_TO_US.search(text) else None
    clauses = re.split(r'[,.;\n]|\s+(?:ו?אבל|ועם|but|and)\s+', text)
    minor = {w for c in clauses if _LESS.search(c) for w in colour_palette(c, preserve_words=True)}
    ordered = [w for w in named if w not in minor] + [w for w in named if w in minor]
    return ', '.join(ordered)


def colour_unknown_business(brief) -> bool:
    """A website whose customer stated no colour and whose business is not a catalogue category."""
    from .. import discovery as d
    from ..vertical_palettes import category_of
    field = brief.fields.get('color') or {}
    if field.get('source') in ('answer', 'message'):
        return False
    return category_of(brief.prompt + '\n' + d.customer_text(brief)) is None

SUBJECT_QUESTION = {'he': 'ספרו לי במשפט או שניים על מה זה: שם העסק או הנושא, מה אתם עושים, ולמי זה מיועד?',
                    'en': 'Tell me in a sentence or two what this is about: the business or topic, what you do, and '
                          'who it is for?'}
